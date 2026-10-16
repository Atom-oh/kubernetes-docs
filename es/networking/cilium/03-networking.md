# Modelos de networking y VXLAN

> **Línea base revisada**: Cilium 1.20.2, Kubernetes 1.33–1.36 probado, Linux 5.10+ o backports equivalentes documentados, como el kernel 4.18 de RHEL 8.10.
> **Última actualización**: October 15, 2026

## Configuración del entorno de laboratorio

Usa la [guía de instalación](README.md) para preparar un clúster desechable y una Cilium CLI adecuada para la arquitectura. Mantén kubectl dentro de una versión secundaria del API server; “v1.31 or higher” no es una regla de compatibilidad.

Los ejemplos de modo genérico a continuación requieren al menos dos nodos Linux planificables, ningún Pod CNI en competencia, kube-proxy funcional y un Pod CIDR que no se superponga. El ejemplo de native-routing requiere además que los nodos compartan un segmento L2. Estas no son recetas para EKS ENI, GKE Dataplane V2, AKS managed-Cilium ni migración de CNI in situ.

### Herramientas de análisis de red

Instala tcpdump/Wireshark mediante la fuente de paquetes compatible del host de análisis. La captura de paquetes del nodo debe ejecutarse en el nodo/namespace de red pertinente, no simplemente en el portátil que ejecuta kubectl. Un monitor de agente informa eventos BPF emitidos; no es una captura completa de paquetes.

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type trace -v
```

Para el perfil VXLAN explícito a continuación, captura una muestra limitada en el worker pertinente:

```bash
sudo tcpdump -nn -i any -c 50 'udp port 8472'
```

Usa el puerto de túnel configurado si es distinto. Genera tráfico de Pod entre nodos: el tráfico en el mismo nodo no necesita atravesar el overlay. Una captura vacía puede indicar un nodo, interfaz, puerto o ruta de tráfico incorrectos, en lugar de un fallo de red.

## Comparación de modelos de networking de contenedores

Los namespaces de host, los bridges y los transportes entre nodos describen aspectos diferentes del networking y pueden coexistir. No constituyen una clasificación universal de rendimiento o seguridad.

| Modelo | Mecanismo | Contrapartida importante |
|---|---|---|
| Red de host | Un Pod comparte el namespace de red del nodo | Conflictos de puertos y menor aislamiento de namespace de red; no ofrece automáticamente el mejor rendimiento de aplicación |
| Bridge | Un bridge L2 virtual conecta interfaces | La comunicación entre nodos sigue necesitando routing/transporte; Cilium no requiere un bridge de Linux para cada endpoint |
| Overlay | El tráfico encapsulado atraviesa un underlay IP | Cabeceras y procesamiento adicionales, pero el underlay no necesita enrutar cada prefijo de Pod |
| Native/underlay routing | La red puede enrutar direcciones de workload | Requiere rutas correctas de reenvío/retorno y planificación de direcciones; no proporciona ni elimina inherentemente policy/encryption |

### Modos de networking de Cilium

El `routingMode` de Cilium es `tunnel` o `native`. VXLAN/Geneve seleccionan el protocolo de túnel. Las integraciones de Cloud IPAM son otra dimensión de configuración, a menudo emparejada con un datapath native; no son un tercer valor de `routingMode`. BGP es un mecanismo de anuncio de rutas, no un modo independiente de reenvío de paquetes.

## Análisis profundo de la tecnología VXLAN

VXLAN transporta una trama Ethernet interna en UDP sobre una red IP. Un VTEP encapsula/descapsula tráfico; el VNI de 24 bits ofrece un espacio teórico de 2^24 identificadores. Esto no promete que un despliegue de Kubernetes admita 16 millones de tenants.

El puerto de destino VXLAN estandarizado es UDP 4789. **Cilium usa de forma predeterminada UDP 8472** para VXLAN y UDP 6081 para Geneve; ambos son configurables. Cilium puede transportar metadatos de identidad de seguridad en la encapsulación, por lo que no se deben equiparar los conteos genéricos de segmentos VXLAN con los límites de tenant/policy de Cilium.

### Estructura de paquetes VXLAN

```text
Outer Ethernet
  Outer IP (IPv4 or IPv6)
    Outer UDP (Cilium VXLAN default destination 8472; standard 4789)
      VXLAN header (8 bytes, including VNI)
        Inner Ethernet
          Inner IP packet and transport/application payload
```

IP transporta UDP; una cabecera IP externa no se transporta dentro de la cabecera UDP externa. La segmentación VXLAN no proporciona encryption, integridad ni aislamiento automático de NetworkPolicy. Restringe adecuadamente la ruta underlay y configura policy/encryption por separado.

### Presupuesto de MTU

Para VXLAN común sin encapsulación/opciones adicionales, la reducción en el presupuesto de IP interno es:

| Familia IP del underlay | IP externa + UDP + VXLAN + Ethernet interna | Presupuesto de IP interno para una MTU IP underlay de 1,500 bytes |
|---|---|---|
| IPv4 | 20 + 8 + 8 + 14 = 50 bytes | 1,450 bytes |
| IPv6 | 40 + 8 + 8 + 14 = 70 bytes | 1,430 bytes |

La cabecera Ethernet externa está fuera de esa MTU IP underlay. Encryption, las opciones Geneve y otras rutas pueden cambiar el presupuesto. La MTU de ruta efectiva y la MTU del dispositivo veth de un Pod no tienen por qué ser idénticas.

En Cilium 1.20.2, Helm **`MTU` sobrescribe la MTU de la red subyacente**; Cilium calcula entonces el overhead de ruta. `MTU: 0` selecciona la detección. Configurar `MTU: 1450` como si significara «la MTU final de carga útil del Pod» puede restar nuevamente el overhead del túnel. La detección de la interfaz local tampoco demuestra la MTU más pequeña a lo largo de toda la ruta.

### VXLAN frente a otras encapsulaciones

| Tecnología | Portador / identificador | Protocolo o puerto | Límite |
|---|---|---|---|
| VXLAN | Ethernet en UDP; VNI de 24 bits | UDP 4789 estándar; Cilium 8472 predeterminado | Cabecera base fija; no es encryption |
| Geneve | Virtualización de red genérica con opciones extensibles; VNI de 24 bits | UDP 6081 | La longitud de las opciones cambia el overhead |
| GRE | Encapsulación genérica; GRE base no tiene un VNI al estilo VXLAN | Protocolo IP 47, no puerto TCP/UDP 47 | Deben considerarse extensiones opcionales; «redes ilimitadas» no es una capacidad definida |
| NVGRE | Ethernet sobre GRE; VSID de 24 bits dentro de la clave GRE | Protocolo IP 47 | Semántica diferente de identificador/flujo; el soporte depende de la implementación |

## Networking overlay de Cilium

Sin una configuración de plataforma/perfil que la sobrescriba, Cilium usa routing de túnel con VXLAN. El transporte de Pod entre nodos necesita direcciones de nodo alcanzables, tráfico UDP de túnel permitido y una MTU utilizable. El overlay no corrige rangos de direcciones de Pod superpuestos ni hace alcanzables nodos desconectados. Para el recorrido de paquetes, dispositivos de túnel, presupuestos de MTU y variantes de native-routing, consulta [Overlay y native routing](09-overlay-native-routing.md).

![Flujo overlay entre nodos: procesamiento del endpoint, encapsulación del VTEP de origen, tránsito underlay, desencapsulación de destino y entrega al endpoint.](../../.gitbook/assets/en-networking-cilium-03-networking-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-03-networking-2.html)

La figura es un flujo conceptual. Sus direcciones no son un plan de asignación IPAM por nodo; los bloques Pod reales de los nodos deben asignarse de forma coherente y sin superposición. La policy se aplica donde se configure, y los hooks de origen/destino pueden ser distintos.

1. Cilium identifica el endpoint/nodo remoto a partir del estado del control plane y del datapath.
2. El origen encapsula el paquete de Pod pertinente y lo envía mediante direcciones de nodo underlay.
3. El destino desencapsula y procesa/entrega el paquete interno.
4. Los eventos del datapath, el estado de rutas y las capturas ayudan a localizar fallos; un único evento ausente no identifica por sí solo la causa.

## Mecanismos de routing

### Encapsulación

El underlay solo necesita la ruta de nodo/túnel, en lugar de una ruta para cada prefijo de Pod. El coste incluye cabeceras y procesamiento. Las tramas más grandes pueden reducir el overhead relativo únicamente si toda la ruta admite la MTU elegida.

### Native Routing

El nodo y el underlay deben enrutar las direcciones de Pod, incluido el tráfico de retorno. Las rutas pueden provenir de una red Cloud, un router, configuración estática u otro componente de routing. Habilitar el modo native no inicia automáticamente BGP ni anuncia cada Pod CIDR.

`autoDirectNodeRoutes: true` instala rutas PodCIDR directas para nodos que comparten una red L2. Con varios segmentos L2, `directRoutingSkipUnreachable` puede omitir rutas directas inalcanzables mientras una ruta enrutable que funciona independientemente las gestiona. No recurre a túneles overlay.

**No combines el routing de túnel con `autoDirectNodeRoutes: true`: Cilium 1.20.2 rechaza explícitamente esta combinación al inicio.** La antigua receta de «modo híbrido» no era válida. El native routing aún puede coexistir con encapsulación específica de una característica, como una ruta DSR Geneve configurada; esa es una característica de Service independiente.

El Cilium BGP Control Plane anuncia los prefijos Pod/Service configurados a pares. **No programa el datapath local** y no debe tratarse como el componente que suministra automáticamente rutas intra-clúster faltantes.

## Técnicas de optimización de rendimiento

Mide con el mismo protocolo, tamaños de carga útil, concurrencia, ubicación de nodos, policy, encryption y configuración de proxy antes de comparar modos. Eliminar una cabecera de encapsulación no garantiza una menor latencia de aplicación.

- **Datapath:** el balanceo de carga por socket, la aceleración XDP compatible y DSR se aplican a rutas concretas. No se habilitan automáticamente mediante VXLAN o native routing.
- **Connection tracking:** el connection tracking BPF de Cilium y conntrack netfilter de Linux son mecanismos de estado distintos. Omitir una ruta netfilter no significa que todo el tráfico establecido deje de usar el estado de conexión de Cilium.
- **Maps:** dimensiona los maps según la capacidad real y la presión de memoria. La expulsión LRU es útil para cachés, no una optimización universal para todos los maps.
- **Ajuste del host:** la ubicación de CPU/NUMA, la distribución/coalescencia de IRQ y la configuración de colas pueden ayudar o perjudicar a workloads concretos. Las huge pages no son un interruptor general de velocidad de Cilium; requieren evidencia para el consumidor y entorno reales.

## Networking específico de proveedores Cloud

| Entorno | Distinción correcta |
|---|---|
| AWS ENI IPAM | Cilium asigna direcciones ENI enrutables por VPC con requisitos de IAM/API/subred/capacidad de instancia del operator. Los security groups de ENI y la policy de Cilium se complementan; esto no es automáticamente la característica branch-ENI por Pod de AWS VPC CNI |
| Plataformas EKS | El CNI alternativo en nodos EC2 comunes tiene responsabilidades de soporte independientes. Fargate y EKS Auto Mode no admiten sustituir su CNI con este perfil de laboratorio genérico. Hybrid Nodes tienen una ruta de instalación compatible independiente |
| Google Cloud | Cilium upstream autogestionado puede usar IPAM de ámbito de host de Kubernetes y rangos de alias enrutables. GKE Dataplane V2 administrado usa Cilium/`anetd` gestionado por Google; no instales otro datapath upstream encima ni supongas características expuestas idénticas |
| Azure | Azure CNI Powered by Cilium es gestionado por AKS con IPAM delegado. Azure IPAM upstream se dirige a clústeres Azure VM/VMSS autogestionados; AKS BYOCNI es otro modelo de despliegue seleccionado explícitamente |

La configuración de firewall/security-group Cloud no se crea automáticamente con cada policy de Cilium. Selecciona primero la guía de plataforma y el modelo de soporte.

## Laboratorio: configuración del modo de networking de Cilium y pruebas de rendimiento

### Selecciona un modo en un clúster nuevo preparado

Guarda este archivo común, sustituyendo primero el Pod CIDR si se superpone con rangos de nodos, Service, VPC o redes conectadas. Mantén el rango elegido coherente con la configuración de clúster/kube-proxy y con el `ipv4NativeRoutingCIDR` del perfil native; cambiar solo un archivo es insuficiente. `kubeProxyReplacement: false` presupone deliberadamente un kube-proxy funcional. Estos son valores de Helm, no un ConfigMap para aplicar con kubectl.

**`lab-common.yaml`**

```yaml
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
MTU: 0
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
```


Elige exactamente uno de los siguientes archivos de modo. Usa clústeres desechables independientes para las comparaciones en lugar de reinstalar el CNI repetidamente en un clúster activo.

**`mode-vxlan.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
tunnelPort: 8472
autoDirectNodeRoutes: false
```

**`mode-geneve.yaml`**

```yaml
routingMode: tunnel
tunnelProtocol: geneve
tunnelPort: 6081
autoDirectNodeRoutes: false
```

**`mode-native.yaml`**

```yaml
routingMode: native
ipv4NativeRoutingCIDR: 10.244.0.0/16
autoDirectNodeRoutes: true
```


Para el ejemplo VXLAN:

```bash
kubectl config current-context
cilium install --version 1.20.2 --values lab-common.yaml --values mode-vxlan.yaml
cilium status --wait
```

Selecciona `mode-geneve.yaml` o `mode-native.yaml` en su lugar únicamente cuando se cumplan sus requisitos de red. No apliques los ejemplos obsoletos de ConfigMap `tunnel: vxlan`, `ipv4-range` o `ipv4-service-range`; configura IPAM mediante los campos Helm compatibles.

### Pruebas de rendimiento de red

Usa los workloads de rendimiento mantenidos de la CLI en lugar de suponer que un manifiesto no relacionado crea `netperf-client` y `netperf-server`. En el clúster desechable preparado:

```bash
cilium connectivity perf --test-namespace cilium-net-perf \
  --namespace-labels docs-audit-lab=cilium-networking-03 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-net-perf-results
```

La duración es por caso de prueba/muestra, no una ejecución total de diez segundos. Esto crea workloads de prueba y carga de red. La CLI 0.20.1 añade un sufijo de secuencia al namespace (`cilium-net-perf-1` para la suite única predeterminada). Guarda las versiones, la ubicación y la configuración con los resultados; no se garantiza ninguna cifra de rendimiento/latencia.

Las pruebas TCP de request/response, tasa de conexión y flujo responden preguntas distintas. Si usas una configuración iperf3 preparada independientemente, las pruebas UDP aún necesitan la conexión de control TCP y una ruta de datos UDP; un Service que exponga solo TCP 5201 es insuficiente. La tasa UDP ofrecida no es el rendimiento logrado medido.

Estos ejemplos se verificaron con valores oficiales actuales, esquemas de API y código fuente de la CLI. Esta auditoría no renderizó plantillas Helm, desplegó un clúster ni ejecutó un benchmark de red después del reinicio del host; valida el entorno completo de plataforma/laboratorio antes de depender de los resultados.

## Fuentes

- [Routing de Cilium 1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst), [valores Helm](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [validación de inicio](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go), [cálculo de MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go), [opción MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/cell.go)
- [VXLAN RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt), [Geneve RFC 8926](https://www.rfc-editor.org/rfc/rfc8926.txt), [GRE RFC 2784](https://www.rfc-editor.org/rfc/rfc2784.txt), [NVGRE RFC 7637](https://www.rfc-editor.org/rfc/rfc7637.txt)
- [BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst), [AWS ENI](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [CNI alternativo de EKS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html), [GKE Dataplane V2](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2), [Azure IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/azure.rst)
- [Opciones de connectivity/perf de CLI 0.20.1](https://github.com/cilium/cilium-cli/blob/v0.20.1/vendor/github.com/cilium/cilium/cilium-cli/cli/connectivity.go), [invocación de iperf3](https://software.es.net/iperf/invoking.html), [desfase de versiones de kubectl](https://kubernetes.io/releases/version-skew-policy/)


[Volver a la página principal](README.md)

## Cuestionario

Realiza los [ejercicios de validación de networking y resultados esperados](../../quizzes/networking/cilium/03-networking-quiz.md).
