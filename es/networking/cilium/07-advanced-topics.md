# Temas avanzados y casos de uso reales

> **Línea base de revisión**: Cilium 1.20.3, Cilium CLI 0.20.1 y Hubble CLI 1.20.2.
> **Última revisión**: 16 de octubre de 2026. La compatibilidad de Cilium 1.20 con Kubernetes abarca las versiones 1.33–1.36; las mediciones históricas que siguen conservan el entorno en que se obtuvieron.

## Configuración del entorno de laboratorio

Sigue los [requisitos previos de instalación](README.md) y usa un clúster de pruebas desechable con al menos dos nodos Linux aptos para programar Pods. Registra el sistema operativo, kernel, configuración de Cilium, topología, MTU, políticas, cifrado y carga de prueba junto con cada resultado. Usa kubectl dentro de la desviación de versión admitida respecto del servidor de API. Para los comandos siguientes se necesitan Helm, jq y las CLI de Cilium y Hubble; `kubectl top` también requiere una API de métricas.

### Configuración del entorno para pruebas de rendimiento

Registra el despliegue existente antes de modificarlo:

```bash
cilium version
cilium status --verbose
kubectl version
kubectl get nodes -o wide
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
helm get values cilium --namespace kube-system -o yaml > cilium-current-values.yaml
```

La CLI actual puede crear las cargas de prueba necesarias. Ejecuta este comando solo si es aceptable generar carga de red y crear recursos de prueba:

```bash
cilium connectivity perf --test-namespace cilium-advanced-perf \
  --namespace-labels docs-audit-lab=cilium-advanced-07 \
  --duration 10s --samples 2 --crr --udp \
  --host-net=false --pod-net=true --same-node=true --other-node=true \
  --report-dir ./cilium-advanced-perf-results
```

La ejecución predeterminada de concurrencia única usa **`cilium-advanced-perf-1`**, aunque el argumento no incluya ese sufijo. Antes de la prueba, comprueba que el espacio de nombres no esté en uso. `--duration` se aplica a cada escenario o muestra, no a la ejecución completa; la programación, la preparación y la combinación de casos añaden tiempo. Este comando genera carga activa; no es un diagnóstico de solo lectura.

Compara los resultados en el mismo nodo y entre nodos, las solicitudes y respuestas TCP y el tráfico UDP, además del comportamiento real de CPU, memoria y pérdida de paquetes. Repite la prueba cambiando una sola variable planificada cada vez. Que una ejecución termine correctamente no demuestra que se cumplan los SLO de la aplicación, que se haya alcanzado el límite de capacidad de producción ni que funcione cada ruta de política. La auditoría validó los contratos de estos comandos, pero no ejecutó la prueba ni aprovisionó un clúster.

## Ajuste del rendimiento y solución de problemas

### Arquitectura del ajuste del rendimiento

![Cuatro áreas que conviene investigar para el rendimiento de Cilium: el comportamiento del kernel, los mapas eBPF, la asignación de recursos y la ruta de red seleccionada.](../../.gitbook/assets/en-networking-cilium-07-advanced-topics-0.png)

[Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-07-advanced-topics-0.html)

La figura agrupa áreas de investigación; no recomienda aumentar todos los valores ni desactivar los controles de seguridad.

### Áreas de ajuste del rendimiento

| Área | Qué medir y qué controla el ajuste |
| --- | --- |
| Colas de sockets | `net.core.somaxconn` limita la cola de escucha del socket; `net.ipv4.tcp_max_syn_backlog` se refiere a las solicitudes pendientes en estado SYN_RECV por listener. Comprueba el comportamiento de aceptación del servidor y el espacio de nombres de red correspondiente. |
| Entradas de vecinos | `net.ipv4.neigh.default.gc_thresh1`, `gc_thresh2` y `gc_thresh3` son umbrales de recolección de basura distintos. No existe un único ajuste `gc_thresh`. |
| Seguimiento de conexiones | `nf_conntrack_max` de Netfilter y los mapas BPF CT de Cilium son mecanismos separados. Aumentar el primero no cambia el tamaño de los segundos. |
| Mapas BPF | Examina la presión de los mapas, los fallos de inserción, la rotación de entradas y el uso de memoria. Los mapas de seguimiento de conexiones, NAT, balanceo de carga y políticas por endpoint tienen alcances y reglas de dimensionamiento diferentes. |
| CPU y memoria | Mide por separado el agente, el operador, Envoy y Hubble. Las solicitudes afectan a la programación; los límites de CPU pueden causar throttling y los de memoria pueden provocar terminaciones OOM. Aumentar todos los límites no es un diagnóstico. |
| Ruta de red | Identifica el enrutamiento nativo o por túnel, la MTU, el enmascaramiento, el cifrado y el reenvío de servicios. La aceleración XDP se aplica a rutas y controladores compatibles; no es un requisito para reemplazar kube-proxy. |

Al comparar el rendimiento, mantén constantes los requisitos de seguridad y enrutamiento. Un resultado más rápido obtenido al quitar el cifrado o una política necesaria no corresponde a una configuración equivalente.

### Dimensionamiento de mapas

Después de medir la presión, guarda lo siguiente únicamente como **cambio candidato**. Intégralo en los valores completos y versionados del lanzamiento; no reemplaces todo el ConfigMap de Cilium por un fragmento pequeño.

```yaml
# map-sizing-values.yaml
bpf:
  mapDynamicSizeRatio: 0.005
```

`0.005` es un valor nominal equivalente al **0,5 % de la memoria del nodo** para el dimensionamiento dinámico; no representa el 5 % ni es un límite rígido para toda la memoria de Cilium. Por ejemplo, 32 GiB × 0.005 equivalen a 163,84 MiB antes de aplicar los límites de los mapas, el redondeo y otras asignaciones. Entre los mapas grandes afectados están los de seguimiento de conexiones, NAT, vecinos y reverse NAT de sockets; los demás mapas y la memoria del espacio de usuario se contabilizan por separado.

Los valores explícitos `bpf.ctTcpMax`, `bpf.ctAnyMax` o `bpf.natMax` sustituyen el dimensionamiento dinámico de esos mapas. Mantén la capacidad de NAT compatible con la de seguimiento de conexiones y comprueba los tamaños efectivos al iniciar. Aumentar los mapas puede consumir más memoria; reemplazarlos puede interrumpir conexiones existentes.

LRU distribuido (`bpf.distributedLRU.enabled`) usa grupos por CPU para reducir la contención, con compensaciones de memoria y expulsión de entradas. Requiere dimensionamiento dinámico y, al activarlo, vuelve a crear los mapas. El perfil oficial de alto rendimiento no es un interruptor universal que pueda activarse en un clúster activo: introduce esos cambios del plano de datos en nodos nuevos preparados o sigue el procedimiento de migración documentado.

Los ejemplos antiguos `proxy-max-memory-percentage`, `proxy-max-threads`, `enable-xdp`, `tunnel: disabled` y `kube-proxy-replacement: strict` no son recetas de configuración actuales. Usa ajustes de chart compatibles como `envoy.resources`, `routingMode`, el valor booleano `kubeProxyReplacement` y `loadBalancer.acceleration`, con sus requisitos previos correspondientes.

### Coste de Hubble y pérdida de eventos

Una cola de eventos más grande puede absorber una ráfaga, pero consume memoria y no resuelve un déficit sostenido de procesamiento ni reduce el uso de CPU:

```yaml
# hubble-queue-values.yaml
hubble:
  eventQueueSize: 32768
```

Si el procesamiento está dominado por eventos repetidos de seguimiento, evalúa por separado un intervalo de agregación más largo:

```yaml
# hubble-aggregation-values.yaml
bpf:
  monitorAggregation: medium
  monitorInterval: 10s
```

El campo real del chart es **`bpf.monitorInterval`**, no `bpf.events.monitorInterval`. Antes del despliegue, inspecciona el valor renderizado de `monitor-aggregation-interval`. Una mayor agregación, los límites de tasa de eventos y la desactivación de clases de eventos reducen las observaciones disponibles para la supervisión, las métricas de Hubble y la exportación. Perder un evento de Hubble no significa que se haya descartado un paquete de la aplicación; comprueba tanto la pérdida de observabilidad como los descartes del plano de datos.

### Requisitos previos del plano de datos avanzado

| Función | Requisitos previos y límites que debes comprobar |
| --- | --- |
| netkit | Beta en esta línea base; requiere Linux 6.8 o posterior y enrutamiento BPF en el host. Los Pods existentes que usan veth no pueden cambiar simplemente de tipo de dispositivo al reiniciar el agente. |
| BIG TCP | Requisitos de kernel y NIC específicos de cada familia; el perfil de ajuste combinado requiere Linux 6.8 o posterior y NIC compatibles. No equivale a aumentar la MTU de forma genérica. |
| Enrutamiento BPF en el host | Requiere un reemplazo de kube-proxy y enmascaramiento BPF compatibles. Omite los hooks de Netfilter del host; comprueba las integraciones de Istio y otras que dependan de ellos. |
| Aceleración de servicios con XDP | Dispositivos con capacidad XDP nativa y una ruta externa de reenvío de servicios compatible. Sigue la guía del controlador y la plataforma, y verifica el estado en ejecución. |
| Bandwidth Manager | Para la salida de cada Pod usa EDT; para la entrada, un bucket de tokens eBPF. `10M` en la anotación de ancho de banda significa 10 Mbit/s, no 10 MB/s. |
| BBR para Pods | Requiere Bandwidth Manager, Linux 5.18 o posterior y enrutamiento BPF en el host; los Pods nuevos adoptan el ajuste. BBR solo en el host es una opción distinta. |

La aplicación del ancho de banda tiene limitaciones documentadas con las políticas L7 de salida de Cilium y los espacios de nombres de red anidados, como los de kind. Estas condiciones son distintas de los requisitos habituales de instalación de Cilium. No uses un perfil de ajuste como prueba de compatibilidad con todas las combinaciones de service mesh, nube o kernel.

### Comandos de solución de problemas dirigidos

Usa la CLI independiente `cilium` para las operaciones del clúster y **`cilium-dbg` dentro del agente pertinente** para consultar endpoints, políticas y mapas locales. Selecciona el nodo que investigas en lugar de consultar arbitrariamente el primer agente:

```bash
set -euo pipefail
: "${NODE_NAME:?Set NODE_NAME to the node being investigated}"
CILIUM_POD=$(kubectl -n kube-system get pods -l k8s-app=cilium \
  --field-selector "spec.nodeName=$NODE_NAME,status.phase=Running" -o json |
  jq -er 'if (.items | length) == 1
then .items[0].metadata.name
else error("expected exactly one running Cilium Pod on the selected node")
end')
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy get
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg policy selectors
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf metrics list
kubectl -n kube-system logs "$CILIUM_POD" -c cilium-agent --since=10m --tail=200
```

Los ID de endpoint son locales a ese agente. Usa un ID de la lista de endpoints de ese agente:

```bash
: "${CILIUM_POD:?Select the owning Cilium Pod first}"
: "${ENDPOINT_ID:?Read the endpoint ID from the selected agent endpoint list}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg endpoint get "$ENDPOINT_ID"
# Stream local BPF drop events; stop with Ctrl-C.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- \
  cilium-dbg monitor --type drop
```

`cilium-dbg map list` enumera los mapas abiertos que conoce el administrador de mapas del agente; no es un inventario de todos los mapas BPF del kernel. `cilium-dbg monitor` muestra los eventos BPF emitidos y las trazas capturadas opcionalmente; no es una captura tcpdump sin pérdidas de todos los paquetes. Volcar mapas CT grandes puede ser costoso; examina las métricas y el nodo afectado antes de ejecutar `cilium-dbg bpf ct list global`.

Para Hubble, primero establece la conexión local con Relay que se describe en [Seguridad y visibilidad](06-security-visibility.md):

```bash
hubble status
hubble observe --protocol tcp --verdict DROPPED --since 1h
hubble observe --protocol dns --from-label k8s:app=frontend --last 100
hubble observe --http-status '5+' --from-namespace production --last 100
```

`--type` selecciona tipos de eventos, no el tipo de registro DNS A. Si necesitas distinguir los tipos de consulta, usa los campos de flujo DNS. Los filtros de estado HTTP usan `5+`, no `5xx`. El historial retenido y la disponibilidad de eventos limitan `--since 1h`; esa opción no puede recuperar eventos de hace una hora que ya se sobrescribieron.

### Escenarios habituales de solución de problemas

| Síntoma | Evidencia que debes recopilar | Decisión siguiente |
| --- | --- | --- |
| Presión en CT/NAT | Presión de los mapas, motivos de inserción fallida o descarte, rotación de conexiones y tamaños configurados reales | Investiga la rotación, los tiempos de espera y el margen de memoria antes de cambiar el tamaño. |
| OOM o saturación de CPU | Motivo de terminación del contenedor, historial de memoria y CPU, throttling y carga del proxy y Hubble | Identifica el componente responsable y ajusta sus recursos o su carga. |
| Resultado inesperado de una política | Espacio de nombres y etiquetas correctos, revisión de la política del endpoint, errores del proxy y veredicto de Hubble | Comprueba la dirección, las reglas de permiso acumulativas y la precedencia de denegación; los permisos comunes no forman una lista de reglas de firewall ordenada por prioridad. |
| Fallo entre nodos | DNS, rutas de nodos y Pods, MTU, puertos de túnel o cifrado y firewall de la plataforma | Verifica las rutas de ida y vuelta; una sesión BGP activa por sí sola no demuestra que se pueda alcanzar el plano de datos. |
| Regresión tras una actualización | Valores anteriores y nuevos, notas de versión, versiones de todos los componentes y reconexiones del proxy | Usa la ruta de reversión compatible que preparaste e investiga la compatibilidad de las funciones. |

## Estrategias de despliegue a gran escala

La planificación de capacidad debe incluir la densidad de nodos y Pods, Services y sus backends, identidades, expansión de políticas, tráfico de observación de la API, asignación de IPAM y volumen de flujos. La cantidad de objetos de política por sí sola no determina el coste de los mapas por endpoint.

### Arquitectura de despliegue a gran escala

```text
Management / GitOps / shared monitoring
          | config and collected telemetry
          +-----------------------+
          v                       v
  Workload cluster A       Workload cluster B
  - Cilium Operator        - Cilium Operator
  - agent on each node     - agent on each node
  - local Hubble servers   - local Hubble servers
  - Relay/export setup     - Relay/export setup
          |                       |
          +--- optional ClusterMesh metadata/data paths
```

Un clúster de administración central no sustituye al operador de cada clúster administrado. Dimensiona el operador y los agentes de cada clúster; las réplicas del operador y la anti-afinidad del chart necesitan suficientes nodos aptos. Agrega métricas y registros mediante recopiladores configurados. ClusterMesh requiere diseñar su propio direccionamiento, identidad, confianza y alcance de red; no replica automáticamente todos los recursos de política.

`ciliumEndpointSlice.enabled` es una función opcional de Cilium, distinta de EndpointSlice de Kubernetes. No es la antigua opción del ConfigMap `enable-endpoint-slice`. Evalúa la compatibilidad de versión y de funciones antes de activarla; Egress Gateway no puede combinarse actualmente con CiliumEndpointSlice ni con ClusterMesh.

Egress Gateway aplica **SNAT** al tráfico seleccionado para darle una dirección predecible de gateway; no conserva la dirección de origen original del Pod. Las interfaces e IP del gateway y el enrutamiento deben aprovisionarse de antemano, incluidos los requisitos específicos de la plataforma en AWS. Requiere enmascaramiento BPF, reemplazo de kube-proxy y asignación de identidad mediante CRD. Los Pods recién iniciados pueden enviar tráfico durante un breve período antes de que se aplique la política de salida; no lo trates como una garantía inmediata de cierre ante fallos que preserve la IP de origen.

### Despliegue gradual y recuperación

Mantén bajo controles de versionado y copia de seguridad adecuados los valores deseados, las políticas, las definiciones de grupos de direcciones y el material necesario de confianza y claves. Ensaya la recuperación; una copia de seguridad del ConfigMap no constituye un plan completo de recuperación de IPAM ni de material criptográfico.

Para actualizaciones menores, primero llega al último parche de la versión menor actual y ejecuta las comprobaciones previas requeridas; después avanza **de una versión menor cada vez**. Conserva el `upgradeCompatibility` inicial tal como indica la guía de actualización y migra los valores que hayan cambiado de nombre o se hayan eliminado. No uses `--reuse-values` entre versiones menores. Los agentes, el operador y los demás componentes de Cilium deben converger en la misma versión.

Durante las actualizaciones, el tráfico que atraviesa proxies de espacio de usuario puede reconectarse y pueden perderse eventos de supervisión almacenados en búfer. Antes de una reversión válida, quizá sea necesario eliminar o migrar recursos y funciones nuevas. Un despliegue blue/green genérico de aplicaciones o una reversión de Helm no garantizan una migración de CNI reversible y sin tiempo de inactividad.

## Estudios de casos reales

### Experimento histórico de escalabilidad documentado

El informe oficial de escalabilidad describe **1.000 nodos de trabajo**, tres nodos controladores y el kernel **5.4.0-1009-gcp** en Google Cloud. En la configuración no se identifica una versión de Cilium, por lo que estos resultados no deben presentarse como un benchmark de Cilium 1.20.3. El informe analiza el consumo de recursos y la convergencia para su propia carga de trabajo; no es una matriz de compatibilidad actual ni una promesa de capacidad.

Los cambios de comprobación de estado y la alta concurrencia de los despliegues fueron decisiones del experimento. Conserva las condiciones reales de prueba al citarlo y valida por separado una configuración operativa.

### Escenario de diseño 1: comercio electrónico a gran escala

Para muchos servicios y un alto volumen de solicitudes, evalúa el reenvío de servicios con eBPF, las políticas de identidad y L7, Hubble y ClusterMesh opcional. Mide latencia p95/p99, rendimiento, errores, CPU por solicitud y convergencia de políticas con la misma topología y los mismos requisitos de protección. Aquí no se presentan implementaciones identificadas ni mediciones reproducibles que respalden una mejora porcentual universal.

### Escenario de diseño 2: servicios financieros

Combina políticas de mínimo privilegio, cifrado de transporte y de aplicación con alcance apropiado, y exportación controlada de flujos con registros de auditoría de aplicaciones y API. Prueba la rotación de claves, la pérdida de eventos, la retención y la confianza entre clústeres. Los flujos de Hubble por sí solos no constituyen evidencia de auditoría regulatoria completa ni garantizan auditorías más breves.

### Escenario de diseño 3: telecomunicaciones y edge

Evalúa la compatibilidad de NIC y controladores, la programación de CPU, las rutas de reenvío de servicios, el tamaño de paquetes, la pérdida y la latencia con tráfico realista. XDP puede beneficiar una ruta de reenvío compatible. Por sí solo no implementa una función del plano de usuario 5G ni demuestra una tasa fija de paquetes por segundo en cualquier hardware. Los sitios remotos siguen necesitando una red subyacente y pruebas explícitas de fallos y recuperación.

## Hoja de ruta futura y dirección del desarrollo

La hoja de ruta de la comunidad no incluye **compromisos de fechas**. Para una capacidad concreta, sigue las notas de versión, los diseños aceptados y las incidencias; no trates una lista de integraciones deseadas como un compromiso de entrega.

| Área | Preguntas que conviene investigar |
| --- | --- |
| eBPF y kernels | ¿Qué función del kernel, backport, NIC y arquitectura requiere la ruta propuesta? CO-RE no proporciona capacidades que falten en el kernel. |
| Redes e IPv6 | ¿Qué combinaciones de IPAM, enrutamiento, políticas e integraciones externas admite la versión seleccionada? |
| Seguridad y observabilidad | ¿Se trata de una política de red de Cilium, autenticación o cifrado de cargas Beta, aplicación de seguridad en tiempo de ejecución con Tetragon, o un detector o sistema de almacenamiento externo? |
| Nube, mesh y serverless | ¿Permite la plataforma administrada los hooks de CNI y del host previstos? ¿Se conservan la interceptación y la autenticación del service mesh? |
| Edge, IoT, 5G e IA/ML | ¿Qué integración adicional de dispositivos, transporte, entorno de ejecución o aceleradores se necesita? Una CNI de Kubernetes no proporciona por sí sola todas las capacidades específicas de la aplicación. |

Participa mediante incidencias del proyecto, propuestas de diseño, documentación y debates de la comunidad. El soporte comercial y las distribuciones administradas tienen sus propios contratos de funciones y soporte.

## Configuración actual de BGP

El ejemplo anterior de `CiliumBGPPeeringPolicy` está obsoleto para esta línea base. La configuración actual separa la selección del clúster y los nodos, los ajustes de los peers y los prefijos anunciados en tres recursos **`cilium.io/v2`**. Para profundizar en BGP Control Plane, el anuncio de direcciones IP de LoadBalancer, Egress Gateway y patrones de edge, consulta [BGP, LB, egress y edge](11-bgp-lb-egress-edge.md); para varios clústeres, consulta [Instalación y actualización de ClusterMesh](13-clustermesh-install-upgrade.md).

Este modelo de configuración corresponde a un laboratorio de enrutamiento aislado, no a una configuración completa de router en la nube. Supone IPAM de grupo de clústeres o con alcance de host de Kubernetes para anunciar `PodCIDR`, un router peer alcanzable, la configuración correspondiente en ese router y nodos etiquetados intencionalmente como `cilium-bgp=lab`. `192.0.2.1` es una dirección reservada para documentación; reemplázala por la IP real del peer, sin `/32`. IPAM con varios grupos usa otro tipo de anuncio y selección de grupo.

```yaml
# bgp-values.yaml
bgpControlPlane:
  enabled: true
```
```yaml
# bgp-lab.yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata:
  name: lab-bgp
spec:
  nodeSelector:
    matchLabels:
      cilium-bgp: lab
  bgpInstances:
  - name: asn-64512
    localASN: 64512
    peers:
    - name: router-64513
      peerASN: 64513
      peerAddress: 192.0.2.1
      peerConfigRef:
        name: lab-peer
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata:
  name: lab-peer
spec:
  timers:
    connectRetryTimeSeconds: 120
    holdTimeSeconds: 90
    keepAliveTimeSeconds: 30
  gracefulRestart:
    enabled: true
    restartTimeSeconds: 120
  families:
  - afi: ipv4
    safi: unicast
    advertisements:
      matchLabels:
        advertise: lab
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata:
  name: lab-pod-cidrs
  labels:
    advertise: lab
spec:
  advertisements:
  - advertisementType: PodCIDR
```

El selector del anuncio del peer coincide con `advertise: lab`, y `peerConfigRef` apunta a `lab-peer`. Graceful Restart requiere un comportamiento compatible del peer y temporizadores adecuados; no puede conservar un plano de datos que haya fallado ni garantizar la disponibilidad de la aplicación. BGP anuncia rutas alcanzables, pero **no instala las rutas locales del plano de datos ni crea registros DNS**.

Después de preparar y aplicar una configuración adecuada en tu laboratorio de enrutamiento, inspecciona tanto el estado de Cilium como las rutas recibidas por el router externo:

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements
cilium bgp peers
cilium bgp routes advertised ipv4 unicast
```

Prueba por separado el tráfico real de ida y vuelta. No presentes políticas HTTP existentes desde hace tiempo ni mejoras porcentuales arbitrarias como funciones nuevas de una versión antigua. Consulta las notas de la versión exacta al migrar desde Cilium 1.18 u otra versión menor anterior.

## Próximos pasos

Usa los capítulos sobre [IPAM y políticas](04-ipam-policy.md), [redes L2–L7](05-l2-l7-networking.md) y [seguridad y visibilidad](06-security-visibility.md) para validar rutas individuales. Conserva las condiciones y limitaciones de cada benchmark junto con sus resultados y ensaya un despliegue gradual y la recuperación.

Después de revisar el espacio de nombres exacto creado por la prueba de rendimiento, elimina sus recursos:

```bash
set -eu
PERF_NS=cilium-advanced-perf-1
LAB_OWNER=$(kubectl get namespace "$PERF_NS" -o jsonpath='{.metadata.labels.docs-audit-lab}')
test "$LAB_OWNER" = cilium-advanced-07
kubectl delete namespace "$PERF_NS"
```

## Referencias principales

- [Guía de ajuste](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/performance/tuning.rst)
- [Valores del chart](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Plantilla de ConfigMap del chart](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/install/kubernetes/cilium/templates/cilium-configmap.yaml)
- [Dimensionamiento de mapas](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/ebpf/maps.rst)
- [Implementación del dimensionamiento de mapas](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/pkg/option/config.go)
- [Guía de actualización](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/upgrade.rst)
- [Limitaciones de las actualizaciones](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/upgrade-warning.rst)
- [Configuración de BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst)
- [Operación de BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [Bandwidth Manager](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/kubernetes/bandwidth-manager.rst)
- [Egress Gateway](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/network/egress-gateway/egress-gateway.rst)
- [Informe histórico de escalabilidad](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/operations/performance/scalability/report.rst)
- [Hoja de ruta de la comunidad](https://raw.githubusercontent.com/cilium/cilium/v1.20.3/Documentation/community/roadmap.rst)
- [Sysctls de IP de Linux](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)

[Volver a la página principal](README.md)

## Cuestionario

Repasa los límites operativos y los comandos de diagnóstico en el [cuestionario del tema](../../quizzes/networking/cilium/07-advanced-topics-quiz.md).
