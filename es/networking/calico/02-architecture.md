# Parte 2: Arquitectura

> **Base de revisión**: Calico Open Source 3.32.2 / operator 1.42.6; Calico 3.32 se prueba con Kubernetes 1.34–1.36.
> **Última actualización**: 12 de septiembre de 2026. Los ejemplos son referencias de configuración, no validación en un clúster real.

## Descripción general

Esta sección profundiza en la arquitectura de Calico. Comprender el funcionamiento e interacción de sus componentes es esencial para desplegarlo, diagnosticarlo y optimizarlo eficazmente en producción.

## Diagrama de arquitectura completa

![Distribución simplificada de estado desde Kubernetes API y Typha hacia Felix y la configuración BGP, omitiendo componentes intermedios.](../../.gitbook/assets/en-networking-calico-02-architecture-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-0.html)

Es un esquema simplificado del estado de control. La conexión BIRD omite confd, que genera su configuración; Typha no es una API directa de configuración BIRD. La presencia de BIRD/confd y Typha depende del modo, y no se muestran todos los componentes de control.

## Felix: el agente de Calico

Felix se ejecuta en el agente de nodo de Calico y programa rutas, interfaces y políticas pertinentes en el kernel. En la red Linux completa, el runtime invoca CNI y los plugins CNI/IPAM crean interfaces y asignan direcciones. Felix observa cambios de endpoints de forma asíncrona; no atiende directamente una llamada CNI ADD. Los componentes exactos dependen del operador, plataforma y modo.

### Responsabilidades de Felix

CNI/IPAM Linux crea interfaces y direcciones de Pods. Felix reconcilia endpoints y políticas del kernel. Servir salud HTTP e informar estado al datastore son funciones separadas.

### Funciones principales

1. **Programación de rutas**: Reconcilia rutas de cargas y túneles; en BGP, el protocolo kernel de BIRD también instala rutas aprendidas
2. **Aplicación de ACL**: Programa reglas iptables/nftables/eBPF de políticas
3. **Gestión de interfaces**: Reconcilia estado y ajustes del kernel; crear veth Linux pertenece a CNI
4. **Informes de salud**: Informa al datastore sobre nodos y endpoints
5. **Reconciliación de endpoints**: Observa su estado y programa políticas/rutas; CNI/IPAM asigna direcciones y crea interfaces

### Opciones del plano de datos de Felix

Felix admite varios backends:

| Plano de datos | Descripción | Uso apropiado |
| ------------ | -------------------------- | ------------------------------------------- |
| **iptables** | Firewall Linux tradicional | Compatibilidad y despliegues maduros |
| **nftables** | Implementación nativa | Comprobar kernel, plataforma y funciones compatibles |
| **eBPF** | Programable dentro del kernel | Gestión opcional de Service; requiere migración coordinada y funciones soportadas |

### Recurso FelixConfiguration

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  reportingInterval: 30s
  reportingTTL: 90s
```

Este ejemplo mínimo usa campos aceptados por Calico 3.32.2. Aplique cambios mediante el propietario; no es una migración de dataplane ni una receta de rendimiento. El host de salud predeterminado es localhost. Activar métricas no configura el scrape ni justifica exposición pública.

| Aspecto | Propietario / interpretación correcta |
|---|---|
| Plano de datos Linux | `Installation.spec.calicoNetwork.linuxDataplane` del operador elige `Iptables`, `Nftables` o `BPF` compatibles |
| `bpfEnabled` | Ajuste de bajo nivel; coordine transición, kube-proxy y acceso API, no lo modifique aisladamente |
| `iptablesBackend: NFT` | Elige herramientas iptables-nft, no el dataplane nftables nativo |
| Balanceo al conectar | Campo actual `bpfConnectTimeLoadBalancing: TCP`, `Enabled` o `Disabled`; el booleano `bpfConnectTimeLoadBalancingEnabled` sigue aceptado pero obsoleto |
| Detección de direcciones | `calicoNetwork.nodeAddressAutodetectionV4` / `V6` del operador, o entorno de arranque en instalación por manifiestos; no campos Felix `ipAutoDetectionMethod`/`ipv6AutoDetectionMethod` |
| Visibilidad de flujos | Configuración compatible Goldmane/Whisker; Open Source no acepta los campos de archivo Enterprise del ejemplo anterior |
| MTU y túneles | Derivar de red subyacente, encapsulación y cifrado; coordinar Installation/IPPool, no elegir 1440/1410/1420 arbitrariamente ni habilitar todos los túneles |
| Puertos failsafe de host | Revisar acceso API/BGP/etcd/administrativo antes de sustituir listas; las antiguas listas reducidas podían eliminar excepciones necesarias |
| Duraciones | Usar `reportingInterval`, `reportingTTL`, `iptablesPostWriteCheckInterval`, `iptablesLockProbeInterval`; no añadir `Secs`/`Millis` mecánicamente |

El esquema rechaza los antiguos `iptablesLockFilePath`, `iptablesLockTimeoutSecs`, `iptablesLockProbeIntervalMillis`, `iptablesPostWriteCheckIntervalSecs`, `reportingIntervalSecs` y `reportingTTLSecs`. Consulte [Felix](https://docs.tigera.io/calico/latest/reference/resources/felixconfig) y la [API del operador](https://docs.tigera.io/calico/latest/reference/installation/api). Cambios de dirección/dataplane necesitan comprobaciones de rollout propias.

### Estructura de reglas iptables de Felix

Estos son prefijos seleccionados de las [definiciones publicadas](https://github.com/projectcalico/calico/blob/v3.32.2/felix/rules/rule_defs.go), no el grafo completo. Describen iptables; inspeccione las reglas reales del modo instalado.

| Cadena/prefijo | Función |
|---|---|
| `cali-FORWARD` | Hook de reenvío Calico |
| `cali-from-wl-dispatch` | Distribución desde interfaces de cargas |
| `cali-to-wl-dispatch` | Distribución hacia interfaces de cargas |
| `cali-fw-…` / `cali-tw-…` | Cadenas por carga y dirección |
| `cali-pi-…` / `cali-po-…` | Cadenas de política entrante/saliente |

### Flujo de datos de Felix

Al crear un Pod, el runtime invoca CNI/IPAM, configura la red y registra endpoints. Felix observa cambios y programa políticas/rutas; BGP sigue su vía confd/BIRD cuando está habilitado. Running no demuestra convergencia de rutas o políticas.

## BIRD: demonio de enrutamiento BGP

BIRD (BIRD Internet Routing Daemon) intercambia rutas BGP cuando está habilitado el backend BGP de Calico. BIRD/confd no son obligatorios en instalaciones solo de políticas o VXLAN sin BGP. Las topologías siguientes necesitan un clúster BGP diseñado adecuadamente; no se añaden al laboratorio kind introductorio con BGP desactivado.

### BIRD en Calico

![BIRD en tres nodos forma una malla iBGP completa para rutas de Pods y se conecta por eBGP al switch ToR, que propaga las rutas al router central.](../../.gitbook/assets/en-networking-calico-02-architecture-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-3.html)

Las líneas son sesiones BGP, no tránsito de paquetes de aplicación por BIRD. Los tamaños son orientación ilustrativa, no requisitos del protocolo ni umbrales fijos para reflectores.

### Tipos de sesión BGP

| Tipo | Uso | Configuración |
| --------------------- | --------------------------- | ---------------------- |
| **Malla entre nodos** | Predeterminada en clústeres pequeños | Automática y completa |
| **Reflector de rutas** | Reducir sesiones según la topología | Preparar y verificar primero peers sustitutos |
| **Peering externo** | Integración local | Configuración BGP manual |

### Ejemplos BGP

#### Malla entre nodos (predeterminada)

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### Reflectores de rutas

Siga la [transición BGP oficial](https://docs.tigera.io/calico/latest/networking/configuring/bgp). Asignar un cluster ID de reflector elimina inmediatamente el nodo de la malla y puede interrumpir cargas. Prepare nodos dedicados sin aplicaciones o una migración de mantenimiento explícita. No sustituya un Calico Node existente por un objeto parcial que omita sus demás ajustes.

Con datastore Kubernetes API, la anotación documentada conserva los campos existentes. Sustituya los nombres por los nodos preparados:

```bash
# Existing, prepared RR nodes with no application workloads.
kubectl get nodes rr-1 rr-2 -o yaml > rr-nodes-before.yaml
kubectl get bgpconfiguration.projectcalico.org default -o yaml > bgp-before.yaml
kubectl annotate node rr-1 projectcalico.org/RouteReflectorClusterID=244.0.0.1 --overwrite
kubectl annotate node rr-2 projectcalico.org/RouteReflectorClusterID=244.0.0.2 --overwrite
kubectl label nodes rr-1 rr-2 route-reflector=true --overwrite
kubectl apply -f - <<'YAML'
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: nodes-to-route-reflectors
spec:
  nodeSelector: all()
  peerSelector: route-reflector == 'true'
YAML
```

`all()` hacia el selector RR cubre clientes y conexiones entre RR; verifique ambos reflectores y rutas cliente. Espere sesiones establecidas y confirme conectividad antes de desactivar la malla antigua. Established no demuestra que se aceptaran las rutas necesarias.

```bash
# Only after replacement sessions, routes and test traffic have been verified.
kubectl patch bgpconfiguration.projectcalico.org default --type merge \
  -p '{"spec":{"nodeToNodeMeshEnabled":false}}'
```

Es una transición ordenada, no aplicación simultánea ni garantía sin interrupciones. Conserve configuración y recuperación probada. Direcciones, ASN y números AS reutilizados en la red externa necesitan políticas y manejo de bucles deliberados.

#### Peering BGP externo

Sustituya dirección, ASN y selector de rack por la topología prevista. La contraseña requiere Secret/clave coincidentes en el namespace del componente de nodo y configuración compatible en el router. Autentica la sesión BGP, no los datos de la carga.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### Propagación de rutas

![Diagrama que muestra cómo Felix añade una ruta a la tabla de enrutamiento del kernel, BIRD obtiene esa información mediante su gestión de sesiones BGP y su función de intercambio de rutas anuncia el CIDR del Pod a otros nodos y routers externos mediante un BGP UPDATE; también se muestran la compatibilidad con reflectores de rutas para clústeres grandes y el filtrado de rutas basado en filtros de exportación como funciones adicionales de BIRD.](../../.gitbook/assets/en-networking-calico-02-architecture-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-4.html)

Es una vía de información. El protocolo kernel de BIRD también instala rutas aprendidas, y confd/IPAM contribuye a la configuración generada. Los filtros BGP son política de rutas, no aplicación de Kubernetes NetworkPolicy.

### Comandos de estado BIRD

Seleccione un nodo con BIRD activo. El [script de arranque publicado](https://github.com/projectcalico/calico/blob/v3.32.2/node/filesystem/etc/service/available/bird/run) fija el socket IPv4 indicado. Las instalaciones por manifiestos pueden usar otro namespace.

```bash
CALICO_NODE=worker-node-name
CALICO_POD=$(kubectl -n calico-system get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')
: "${CALICO_POD:?No Calico Pod on the selected node}"
kubectl -n calico-system exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols
kubectl -n calico-system exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
```

Use nombres y prefijos reales para consultas detalladas. Comandos y salida de consola son distintos: los antiguos prompts `birdcl>` no eran comandos Bash. Estas comprobaciones de lectura no configuran rutas.

## confd: gestión de configuración

confd es una herramienta ligera que observa el datastore y genera archivos de BIRD.

### Flujo de confd

Observa la configuración BGP, renderiza la plantilla, comprueba el candidato y solicita a BIRD recargar.

### Procesamiento de plantillas

Use la [plantilla publicada](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/templates/bird.cfg.template), no una estructura inventada `.NodeIP` / `.BGPPeers`. Este extracto ilustra sincronización con el kernel; los filtros y contexto se definen aparte, por lo que no es un `bird.cfg` completo.

```text
protocol kernel {
  learn;
  persist;
  scan time 2;
  import all;
  export filter calico_kernel_programming;
  graceful restart;
  merge paths on;
}
```

La [definición confd](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/conf.d/bird.toml) escribe `/etc/calico/confd/config/bird.cfg`, valida con `bird -p -c {{.src}}` y recarga mediante `sv hup bird || true`. BIRD puede exportar rutas aprendidas seleccionadas al kernel; no recibe simplemente todas de Felix. Recarga y reinicio ordenado necesitan comprobación de estado/tráfico. Gestione BGP mediante el propietario API, no editando el archivo generado.

## Typha: componente de escalado

Typha distribuye actualizaciones entre Kubernetes API y los agentes Felix. Reduce carga del API almacenando y distribuyendo cambios del datastore.

### ¿Por qué Typha?

La caché de estado y el streaming a varios clientes reducen el procesamiento repetido. Además del número de nodos importan la propiedad, TLS y la lógica real de escalado.

### Escalado de Typha en operator 1.42.6

El operador despliega y escala Typha; no existe la regla universal «solo por encima de 50 nodos». La [implementación fijada](https://github.com/tigera/operator/blob/v1.42.6/pkg/controller/installation/typha_autoscaler.go) cuenta nodos no marcados unschedulable, excluye virtuales AKS y comprueba por separado que haya suficientes nodos Linux. Taints y demás restricciones siguen importando.

La [función real](https://github.com/tigera/operator/blob/v1.42.6/pkg/common/autoscale.go), no su comentario abreviado, devuelve:

- 1 réplica para 1–2 nodos contados.
- 2 réplicas para 3–4 nodos contados.
- `max(3, floor(N / 200) + 2)` para 5 o más.

| Nodos contados | Réplicas deseadas en esta versión |
|---|---|
| 50 | 3 |
| 200 | 3 |
| 500 | 4 |
| 1,000 | 7 |
| 2,000 | 12 |

Es un número deseado específico de versión, no capacidad garantizada por réplica ni recomendación universal. El modo non-cluster-host cuenta HostEndpoints elegibles por separado. La antigua tabla `max(3, ceil(N / 200))` no describía este operador.

### Configuración Typha administrada

Mantenga juntos Deployment, ServiceAccount/RBAC, Service, presupuesto de interrupción y TLS. El antiguo Deployment manual omitía dependencias esenciales y podía sobrescribir ajustes administrados. TLS Felix–Typha usa CA fiable, certificado/clave del servidor e identidad esperada del cliente Felix. 5473 es el puerto de sincronización, no un proxy de tráfico de usuario.

```bash
# Change the operator's supported setting through its API.
kubectl patch installation.operator.tigera.io default --type merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl -n calico-system get deployment calico-typha -o yaml
kubectl -n calico-system get service calico-typha -o yaml
kubectl -n calico-system get pdb
```

El endpoint de estado de Typha utiliza localhost:9098 de forma predeterminada. Este operador deriva el puerto de estado restando uno al puerto de estado de Felix configurado y configura las sondas en consecuencia. Un Deployment con red de Pod cuya sonda apunta a la IP del Pod no alcanzará un listener vinculado únicamente a localhost; copiar sondas sin sus ajustes de red/dirección de escucha no es seguro. El código fuente del operador proporciona montajes TLS y ajustes de identidad del cliente ausentes en el antiguo ejemplo independiente.

### Arquitectura de distribución de Typha

Cada Typha conserva estado para sus streams. Los grupos de clientes del dibujo no especifican capacidad fija por instancia.

## kube-controllers: integración Kubernetes

calico-kube-controllers ejecuta funciones de reconciliación seleccionadas. Qué controladores se ejecutan depende del almacén de datos, la edición y la configuración de instalación. La proyección de políticas/espacios de nombres/cuentas de servicio a un almacén de datos etcd es distinta del tratamiento del almacén de datos de la API de Kubernetes.

### Roles disponibles

| Controlador | Propósito |
| ------------------------------- | ------------------------------------------------- |
| **Node Controller** | Sincroniza nodos Kubernetes y recursos Calico |
| **Policy Controller** | Sincroniza NetworkPolicy y políticas Calico |
| **Namespace Controller** | Sincroniza etiquetas de namespace para perfiles |
| **ServiceAccount Controller** | Proyecta etiquetas a perfiles; no concede RBAC Kubernetes |
| **WorkloadEndpoint Controller** | Actualiza metadatos, como etiquetas Pod, en la vía de datastore correspondiente |

### Bucle de reconciliación

![Diagrama de secuencia que muestra cómo kube-controllers enumera repetidamente recursos de Kubernetes y Calico, compara sus diferencias y escribe cambios en el almacén de datos de Calico o no realiza ninguna acción cuando ambos ya están sincronizados.](../../.gitbook/assets/en-networking-calico-02-architecture-8.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-8.html)

Es un esquema lógico entre estado deseado y observado, no una traza que demuestre dos LIST remotos por intervalo. Los controladores reales usan watches/cachés y roles dependientes del datastore/instalación.

### Configuración de kube-controllers

Con el operador use la [API KubeControllersConfiguration](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig). El Deployment de esta guía no consume un ConfigMap arbitrario llamado `calico-kube-controllers-config`.

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type merge \
  -p '{"spec":{"logSeverityScreen":"Info","healthChecks":"Enabled","prometheusMetricsPort":9094}}'
```

Este parche de fusión conserva la configuración existente de `controllers`. Si GitOps gestiona el recurso, realice en su lugar el cambio equivalente en su estado deseado. Un manifiesto de sustitución con objetos de controlador vacíos puede alterar ajustes existentes de reconciliación o asignación.

Operator 1.42.6 selecciona `ENABLED_CONTROLLERS=node,loadbalancer` en Open Source estándar. La lista anterior describe roles disponibles, no cinco controladores siempre activos. Su [renderer](https://github.com/tigera/operator/blob/v1.42.6/pkg/render/kubecontrollers/kube-controllers.go) indica una réplica y `Recreate`; la antigua afirmación de elección de líder no estaba respaldada. Mantenga esta carga bajo el propietario, sin reemplazarla ni escalarla manualmente.

## Opciones de datastore

Los ejemplos usan Kubernetes API. El estado puede incluir CRD Calico y objetos nativos; no todo recurso lógico es un CRD separado. El servidor agregado habitual expone `projectcalico.org/v3` sobre la representación interna. Los CRD v3 nativos son una vista previa técnica separada de 3.32 con migración propia.

Typha distribuye actualizaciones de lectura/observación; no es un proxy general de escritura para Felix. Los componentes que actualizan estados o recursos utilizan su propio acceso al almacén de datos. Kubernetes persiste el estado de su API en su almacén de respaldo, pero los usuarios de Calico no necesitan un clúster etcd de Calico separado para este modo.

El acceso directo etcdv3 es otra elección con límites explícitos. No suponga que es más rápido, ilimitado o necesario por encima de 5,000 nodos. eBPF requiere datastore Kubernetes. etcd directo necesita confianza TLS, credenciales, disponibilidad y copias/restauración coherentes propias.

| Aspecto | Kubernetes API | etcdv3 directo |
|---|---|---|
| Acceso | Autenticación/RBAC Kubernetes y vía Calico adecuada | Autenticación/TLS y permisos etcd |
| Operaciones | Reutilizar API; seguir copias del proveedor | Operar y respaldar el etcd elegido |
| Hosts/VM | Comprobar instalación y edición | Comprobar instalación y edición |
| Selección | Usado en esta guía | Diseño validado aparte, no atajo por número de nodos |

En Kubernetes administrado, «backup Kubernetes» no implica acceso directo a snapshots etcd del control plane. Respalde recursos compatibles con el procedimiento de la plataforma.

## Secuencia entre componentes

Kubelet solicita crear el entorno al runtime, que invoca CNI/IPAM. Los datos de endpoints/políticas llegan a Felix por el datastore/watch seleccionado. En BGP, confd/BIRD configuran rutas por separado. La convergencia es asíncrona: verifique conectividad y aplicación reales.

## Análisis del flujo de paquetes

### Entrada entre Pods del mismo nodo

![Diagrama que muestra un paquete que cruza de un pod a otro en el mismo nodo a través de sus interfaces veth y la comprobación de políticas iptables/eBPF del host.](../../.gitbook/assets/en-networking-calico-02-architecture-12.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-12.html)

El cuadro de política resume salida del origen y entrada del destino en el kernel. Los veth pertenecen a las rutas de ambos Pods; no se envían paquetes a través del proceso Felix.

### Salida entre Pods de distintos nodos con IPIP

![Diagrama de secuencia que muestra cómo un paquete del Pod A pasa la comprobación de política de salida Felix/iptables en el Nodo 1, llega al Nodo 2 encapsulado con IPIP/VXLAN o reenviado directamente mediante una ruta BGP, y después pasa la comprobación de política de entrada y llega al Pod B.](../../.gitbook/assets/en-networking-calico-02-architecture-13.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-13.html)

Las dos rutas son alternativas. «Felix/iptables» son reglas del kernel programadas por Felix, no reenvío del demonio. BIRD aporta control de rutas BGP y no transporta paquetes de aplicación.

### Comparación de estructura de paquetes

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Resumen

La arquitectura busca escalabilidad, rendimiento y sencillez operativa:

1. **Felix**: Agente principal por nodo que programa rutas y ACL
2. **BIRD**: Distribuye rutas BGP para integración nativa
3. **confd**: Conecta datastore y configuración BIRD
4. **Typha**: Escala reduciendo carga del API server
5. **kube-controllers**: Mantiene Kubernetes y Calico sincronizados
6. **Datastore**: Kubernetes API recomendado o etcd para configuración

Comprender componentes e interacciones es esencial para:

* Diagnosticar conectividad
* Optimizar rendimiento a escala
* Planificar capacidad y arquitectura
* Integrar infraestructura de red existente

[Anterior: Parte 1 - Introducción a Calico](01-introduction.md)

[Siguiente: Parte 3 - Modos de red](03-networking-modes.md)

[Volver a la descripción general de Calico](./README.md)

## Cuestionario

Compruebe lo aprendido con el [cuestionario de arquitectura](../../quizzes/networking/calico/02-architecture-quiz.md).
