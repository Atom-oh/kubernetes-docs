# Benchmark de red de Pods: mismo nodo, misma zona de disponibilidad, entre zonas y DNS con `ndots`

> **Entorno registrado**: Kubernetes 1.36 (Amazon EKS), Amazon VPC CNI v1.21.1, kube-proxy en modo iptables
> **Fecha de medición**: 2 de septiembre de 2026 · **Revisión del contenido**: 12 de septiembre de 2026

Esta página conserva el informe del benchmark del 2 de septiembre de 2026 en `fsi-demo-cluster` (Seúl): RTT entre Pods, latencia HTTP/gRPC, rendimiento con iperf3 y cantidad de consultas DNS. En estas ejecuciones, cruzar una zona de disponibilidad (AZ) aumentó la latencia, mientras que las dos rutas entre nodos alcanzaron un rendimiento similar. Esto no establece una garantía de ancho de banda independiente de la AZ. El tráfico de las mediciones 1 y 2 usó directamente las IP de los Pods; la medición 3 modela su coste, mientras que la medición 4 usó el ClusterIP existente de `kube-dns`. El recorrido DNS de 10 consultas depende de este resolvedor, la lista de búsqueda y la secuencia de respuestas; no es aplicable a todos los Pods de EKS. Se conservan las versiones y mediciones históricas: esta revisión no volvió a ejecutar el benchmark en EKS ni verificó una factura.

![El Pod cliente del nodo A (ap-northeast-2a) llega a un Pod servidor del mismo nodo, a otro nodo de la misma AZ y a un nodo del AZ ap-northeast-2b; RTT 0.040 / 0.339 / 0.544 ms, un flujo 29.97 / 4.96 / 4.96 Gbps.](../.gitbook/assets/en-networking-06-pod-network-benchmark-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-0.html)

El diagrama muestra esta topología de prueba. Los +0.21 ms son la diferencia entre estas ejecuciones, y los $4.47 corresponden al modelo histórico de costes con GB decimales explicado más adelante; no son un cargo verificado ni un coste universal por AZ.

## Resumen: qué medimos

1. **RTT informado**: mismo nodo **0.040 ms** → misma AZ **0.339 ms** → entre AZ **0.544 ms** (ping, promedio de 200 sondas). En esta muestra, la diferencia entre las rutas entre nodos fue +0.21 ms y la diferencia respecto al mismo nodo fue +0.50 ms.
2. **HTTP p50 / p99** (fortio, 100 qps, 4 conexiones, keepalive, 60 s): 0.259 / 0.350 ms → 0.461 / 0.667 ms → 0.704 / 0.812 ms; la aplicación muestra la misma secuencia.
3. **Ancho de banda informado**: un flujo TCP alcanzó **4.96 Gbps** en ambas rutas entre nodos; ocho flujos alcanzaron **9.94 Gbps**, cerca del pico de ráfaga de 10 Gbps de m5.xlarge. Esto concuerda con el límite ordinario de 5 Gbps por flujo fuera de un grupo de ubicación de clúster; otros tipos de instancia y rutas pueden tener límites distintos.
4. **Tráfico Pod a Pod en el mismo nodo**: **29.97 Gbps** con un flujo (CPU del proceso cliente 99.8 %, compatible con presión de CPU) y **48.15 Gbps** con ocho. En esta configuración de VPC CNI, el tráfico pasa por los pares veth de los Pods y la pila de red del host, sin usar la NIC física.
5. **Modelo de costes**: la ejecución entre AZ de 180 s transfirió **223.4 GB decimales**. El modelo original basado en la carga útil estima **$4.47** a $0.01/GB en cada extremo; no es una factura. No se observó una caída hacia la línea base de 1.25 Gbps durante esos 180 s.
6. **DNS informado**: este Pod glibc, al resolver `sts.ap-northeast-2.amazonaws.com` con `ndots:5`, envió **10 consultas** (8 respuestas NXDOMAIN); la mediana en caliente fue **3.78 ms**. Un punto final produjo 2 consultas / 0.80 ms; `ndots:1`, 2 / 0.54 ms. Son resultados de estas muestras, no garantías.
7. **Conexiones nuevas**: desactivar keepalive cambió el p50 de 0.259 → 0.664, de 0.461 → 1.079 y de 0.704 → **1.517 ms**. TCP contribuye al aumento, pero la prueba no aisló los costes del handshake, del socket y de la aplicación.

## Entorno de prueba

| Elemento | Valor |
|---|---|
| Clúster | Amazon EKS `fsi-demo-cluster`, ap-northeast-2 (Seúl), plano de control `v1.36.2-eks-bca9cf6`, dos AZ utilizadas (2a, 2b) |
| Nodos | **3 × m5.xlarge** lanzados nuevos por el NodePool `system` de Karpenter para esta prueba: un nodo cliente en 2a, un servidor en 2a y otro servidor en 2b. 4 vCPU, Intel Xeon Platinum 8175M a 2.50 GHz |
| SO del nodo | Amazon Linux 2023.12.20260817, kernel `6.18.41-94.142.amzn2023.x86_64`, containerd 2.2.5, kubelet v1.36.3-eks-cb19647 |
| CNI | Amazon VPC CNI `v1.21.1-eksbuild.8` (+ network-policy-agent v1.3.4); `ENABLE_PREFIX_DELEGATION=false`, `ENABLE_POD_ENI=false`, `AWS_VPC_K8S_CNI_EXTERNALSNAT=false`, `NETWORK_POLICY_ENFORCING_MODE=standard`, `WARM_ENI_TARGET=1`, `WARM_IP_TARGET=3` |
| kube-proxy | `v1.35.3-eksbuild.5`, `mode: "iptables"` |
| CoreDNS | `v1.14.2-eksbuild.4`, 2 réplicas, uno por AZ (`10.0.2.106` / 2a, `10.0.3.14` / 2b); ClusterIP del Service `kube-dns`: `172.20.0.10`; Corefile `kubernetes cluster.local … { pods insecure }`, `forward . /etc/resolv.conf`, `cache 30`, `loadbalance`; **sin NodeLocal DNSCache ni plugin `autopath`** |
| resolv.conf del Pod (predeterminado) | `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` / `nameserver 172.20.0.10` / `options ndots:5` |
| NIC del Pod | eth0, MTU **9001** (tramas jumbo), control de congestión TCP `cubic`, iperf3 `tcp_mss_default: 8949` |
| Especificación de red de EC2 | m5.xlarge «Hasta 10 Gigabit»: línea base **1.25 Gbps**, pico **10 Gbps**, 4 vCPU (como referencia: m5.large, línea base 0.75 Gbps, pico 10 Gbps, 2 vCPU). Verificado con `aws ec2 describe-instance-types`; se requiere ENA |
| Precios | usagetype `APN2-DataTransfer-Regional-Bytes`, «Transferencia regional de datos: entrada/salida/entre AZ o al usar IP pública o Elastic IP», **$0.01/GB** (`aws pricing get-products --region us-east-1`, consulta de 2026-09) |
| Herramientas | `nicolaka/netshoot:v0.14` (iperf **3.19**, fortio **1.69.5**, iputils ping 20250605, tcpdump 4.99.5); cliente DNS `python:3.12-slim` (Debian 13, **glibc 2.41**, Python 3.12.14) |
| Ventana de prueba | 2026-09-02 07:58–08:40 UTC (primer Pod a las 07:58:22Z; Pods DNS a las 08:16:24Z) |

AWS describe el ancho de banda en ráfaga como de mejor esfuerzo, incluso mientras queden créditos de E/S de red; los créditos de entrada y salida se contabilizan por separado. Una instancia nueva comienza con los créditos al máximo, pero la disponibilidad del pico y la duración de la ráfaga varían. Esta ejecución de 180 s solo demuestra que durante esa ventana no se observó una caída hacia la línea base. La línea base de m5.xlarge de 1.25 Gbps y su pico de 10 Gbps también aparecen en las [especificaciones de red de M5](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html); el [manual de ancho de banda de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html) describe el comportamiento actual de los créditos.

Ubicación de los Pods durante la ejecución:

| Pod | IP | Nodo | Zona | Rol / solicitudes |
|---|---|---|---|---|
| `cli` | 10.0.2.109 | ip-10-0-2-128 (nodeclaim `system-76r87`) | ap-northeast-2a | cliente; 2500m / 1Gi |
| `srv-same` | 10.0.2.72 | ip-10-0-2-128, mismo nodo que `cli` (afinidad de Pod requerida) | ap-northeast-2a | servidor; 200m / 256Mi |
| `srv-a` | 10.0.2.37 | ip-10-0-2-20 (nodeclaim `system-ksrbg`, antiafinidad de Pod respecto de `cli`) | ap-northeast-2a | servidor; 2800m / 1Gi |
| `srv-b` | 10.0.3.65 | ip-10-0-3-32 (nodeclaim `system-svdvk`) | ap-northeast-2b | servidor; 2500m / 1Gi |
| `dns-default` | 10.0.2.5 | ip-10-0-2-20 (afinidad de Pod con `srv-a`) | ap-northeast-2a | resolvedor glibc, `ndots:5` predeterminado |
| `dns-ndots1` | 10.0.2.143 | ip-10-0-2-20 | ap-northeast-2a | resolvedor glibc, `dnsConfig.options ndots=1` |

Los Pods servidor ejecutan `sh -c "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"`, y todos los Pods de prueba llevan `karpenter.sh/do-not-disrupt: "true"`. Al principio se solicitó `srv-a` como m5.large / 1500m, pero Karpenter informó `no instance type has enough resources` (la sobrecarga de DaemonSet consume 821m de los 1930m asignables de una m5.large), por lo que se cambió a m5.xlarge / 2800m.

### Manifiesto de la instalación de prueba

El siguiente es el manifiesto registrado, con sus selectores, solicitudes de recursos, imágenes, comandos y anotaciones históricas. No contiene objetos Service de aplicación. Sus selectores no garantizan por sí solos que se creen nodos nuevos o aislados. Antes de otra ejecución, adapte una copia a un NodePool de pruebas autorizado, a las AZ disponibles y al presupuesto de recursos; no lo aplique sin revisar en un NodePool `system` compartido. Registre los digests de las imágenes y las versiones reales de las herramientas: las etiquetas mutables y las descargas de herramientas durante la compilación de netshoot no garantizan los mismos binarios. El procedimiento revisado más adelante es independiente de este artefacto histórico.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-net
  labels:
    bench: net
---
# client: fresh m5.xlarge in ap-northeast-2a
apiVersion: v1
kind: Pod
metadata:
  name: cli
  namespace: bench-net
  labels: { app: cli, role: client }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
---
# same-node: co-located with cli through required podAffinity
apiVersion: v1
kind: Pod
metadata:
  name: srv-same
  namespace: bench-net
  labels: { app: srv-same, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "200m", memory: "256Mi" }
---
# same-AZ: same AZ as cli, different node (podAntiAffinity). m5.large did not fit because of DaemonSet overhead, hence m5.xlarge
apiVersion: v1
kind: Pod
metadata:
  name: srv-a
  namespace: bench-net
  labels: { app: srv-a, role: server, zone: a }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2a
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: cli } }
          topologyKey: kubernetes.io/hostname
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2800m", memory: "1Gi" }
---
# cross-AZ: fresh m5.xlarge in ap-northeast-2b
apiVersion: v1
kind: Pod
metadata:
  name: srv-b
  namespace: bench-net
  labels: { app: srv-b, role: server, zone: b }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  nodeSelector:
    topology.kubernetes.io/zone: ap-northeast-2b
    node.kubernetes.io/instance-type: m5.xlarge
    karpenter.sh/nodepool: system
  terminationGracePeriodSeconds: 5
  containers:
    - name: netshoot
      image: nicolaka/netshoot:v0.14
      command: ["sh", "-c", "iperf3 -s -p 5201 & exec fortio server -http-port 8080 -grpc-port 8079 -tcp-port 8078"]
      ports: [{ containerPort: 8080 }, { containerPort: 5201 }]
      resources:
        requests: { cpu: "2500m", memory: "1Gi" }
```

Se informó que los dos Pods DNS estaban en el mismo nodo que `srv-a`. Se informó que la imagen `app` era Debian 13 / glibc 2.41; no se midió musl ni otro resolvedor. `sniffer` comparte el espacio de nombres de red del Pod, por lo que puede capturar los paquetes DNS coincidentes de la aplicación si el clúster permite la captura. Para crear los dos objetos DNS del ejemplo siguiente, duplique el manifiesto: cambie el nombre y la etiqueta `app` del segundo objeto a `dns-ndots1` y habilite `dnsConfig` solo en ese segundo objeto. Mantenga las imágenes iguales y fije sus digests registrados en una nueva ejecución.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: dns-default          # the second Pod is name: dns-ndots1 plus the dnsConfig block below
  namespace: bench-net
  labels: { app: dns-default, role: dns }
  annotations: { karpenter.sh/do-not-disrupt: "true" }
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector: { matchLabels: { app: srv-a } }
          topologyKey: kubernetes.io/hostname
  # present only in dns-ndots1:
  # dnsConfig:
  #   options:
  #     - name: ndots
  #       value: "1"
  terminationGracePeriodSeconds: 5
  containers:
    - name: app
      image: python:3.12-slim
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
    - name: sniffer
      image: nicolaka/netshoot:v0.14
      command: ["sleep", "infinity"]
      resources: { requests: { cpu: "50m", memory: "64Mi" } }
```

## Medición 1. RTT y latencia HTTP: mismo nodo → misma AZ → entre AZ

Las sondas ICMP (`ping -c 200 -i 0.05 -q`) describen la ruta inactiva, incluido el procesamiento de los extremos en el kernel y la planificación. Después se probaron las mismas rutas con HTTP/1.1 y gRPC. Se incluye como referencia una sola solicitud `curl` con una conexión nueva: tiempo de conexión / tiempo total.

| Ruta | RTT mín. / **prom.** / máx. / mdev (ms) | Pérdida | curl, 1 solicitud en frío: conexión / total |
|---|---|---|---|
| mismo nodo → 10.0.2.72 | 0.021 / **0.040** / 0.089 / 0.007 | 0/200 | 0.194 ms / 0.497 ms |
| misma AZ → 10.0.2.37 | 0.300 / **0.339** / 0.450 / 0.017 | 0/200 | 0.497 ms / 2.333 ms |
| entre AZ → 10.0.3.65 | 0.504 / **0.544** / 0.625 / 0.015 | 0/200 | 0.694 ms / 4.038 ms |

Diferencias observadas: misma AZ − mismo nodo = +0.30 ms; entre AZ − misma AZ = **+0.21 ms**; entre AZ − mismo nodo = +0.50 ms. Los valores mdev informados no superan 0.017 ms en esta muestra. curl mide el tiempo de transferencia con `time_total`, no el inicio del proceso; una sola observación no basta para describir su distribución. Consulte las [definiciones de tiempos de curl](https://curl.se/docs/manpage.html).

### HTTP/1.1: 100 qps, 4 conexiones, keepalive, 60 s (6,000 solicitudes), ms

| Ruta | prom. | **p50** | p90 | p99 | p99.9 | máx. | mín. |
|---|---|---|---|---|---|---|---|
| mismo nodo | 0.260 | **0.259** | 0.299 | 0.350 | 1.267 | 2.080 | 0.111 |
| misma AZ | 0.468 | **0.461** | 0.560 | 0.667 | 0.783 | 2.823 | 0.336 |
| entre AZ | 0.706 | **0.704** | 0.782 | 0.812 | 1.150 | 4.581 | 0.551 |

### Ping gRPC: 100 qps, 4 conexiones, 30 s (3,000 solicitudes), ms

| Ruta | prom. | **p50** | p90 | p99 | p99.9 | máx. | mín. |
|---|---|---|---|---|---|---|---|
| mismo nodo | 0.410 | **0.397** | 0.449 | 0.869 | 1.187 | 1.314 | 0.241 |
| misma AZ | 0.601 | **0.592** | 0.687 | 0.889 | 1.052 | 1.105 | 0.448 |
| entre AZ | 0.878 | **0.865** | 0.967 | 1.209 | 2.582 | 2.826 | 0.692 |

El informe describe un cuerpo de respuesta HTTP de unos 75 bytes, sin carga útil en la solicitud, y cero errores en todas las ejecuciones. Revise por separado los contadores de resultados de cada protocolo: HTTP 200, las respuestas Ping de gRPC y `SERVING` del chequeo de salud de gRPC son respuestas distintas; la opción `-grpc -ping` selecciona Ping, no el chequeo de salud predeterminado.

**Cómo interpretar los datos.** El p50 de HTTP supera la media de ping en aproximadamente 0.22 / 0.12 / 0.16 ms, pero restar estadísticas distintas de protocolos diferentes no aísla la sobrecarga del espacio de usuario. Los incrementos observados en p50 de HTTP son +0.202 ms y +0.243 ms; no son costes constantes por nodo o por AZ. El p50 de gRPC supera al de HTTP en 0.138 / 0.131 / 0.161 ms según estas implementaciones, sin demostrar cuánto corresponde a HTTP/2, la serialización, la planificación o el código cliente/servidor. El p99 de HTTP es 0.350 → 0.667 → 0.812 ms; el p99.9 de gRPC es 1.187 → 1.052 → **2.582 ms**. Son distribuciones informadas para una ejecución por celda.

> **Comparación con el benchmark de malla.** El [informe de Istio sidecar frente a ambient](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) registra una diferencia de p50 de **+1.29 ms** (2.11 − 0.82 ms) para el escenario completo con sidecar, no para un proxy aislado. Usa hardware Graviton, 200 qps, 16 conexiones y Fortio 1.69.4, distintos de esta prueba M5 / 100 qps / cuatro conexiones. No se pueden sumar ni ordenar estas cifras como costes universales de «un salto de malla» frente a «un salto de AZ».

### Coste de una conexión nueva: keepalive=false, 100 qps, 4 conexiones, 30 s (3,000 solicitudes), ms

¿Qué ocurre con la latencia cuando cada solicitud abre una conexión TCP nueva (fortio `-keepalive=false`)?

| Ruta | prom. | **p50** | p90 | p99 | p99.9 | máx. | mín. | frente al p50 con keepalive |
|---|---|---|---|---|---|---|---|---|
| mismo nodo | 0.672 | **0.664** | 0.782 | 0.957 | 1.253 | 1.306 | 0.364 | **+0.405 ms** |
| misma AZ | 1.066 | **1.079** | 1.185 | 1.369 | 1.582 | 1.795 | 0.769 | **+0.618 ms** |
| entre AZ | 1.530 | **1.517** | 1.678 | 1.796 | 1.981 | 2.009 | 1.300 | **+0.813 ms** |

Los aumentos observados son **+0.405 / +0.618 / +0.813 ms**. Abrir una conexión TCP nueva añade trabajo de establecimiento, pero estas mediciones no demuestran una descomposición fija de «un RTT + 0.3 ms». Reutilizar conexiones es una optimización que conviene medir con la carga real, no un requisito para que las conexiones entre AZ funcionen correctamente. Según cómo se cierren las conexiones, la rotación también puede aumentar los sockets en TIME_WAIT del extremo que inicia el cierre; aquí no se midieron sockets ni TIME_WAIT.

### Máximo de qps con un pool fijo de conexiones: la latencia es rendimiento (bucle cerrado, 16 conexiones, 20 s)

Con `-qps 0` (ilimitado, bucle cerrado), la tasa máxima de solicitudes que pueden sostener 16 conexiones convierte la diferencia de latencia en una diferencia de rendimiento.

| Ruta | Solicitudes | **qps alcanzados** | prom. ms | p50 | p90 | p99 | p99.9 | máx. |
|---|---|---|---|---|---|---|---|---|
| mismo nodo | 899,827 | **44,991** | 0.355 | 0.249 | 0.733 | 1.695 | 3.389 | 13.593 |
| misma AZ | 770,156 | **38,507** | 0.415 | 0.396 | 0.537 | 0.728 | 1.147 | 4.502 |
| entre AZ | 512,060 | **25,602** | 0.624 | 0.597 | 0.770 | 0.949 | 1.293 | 4.725 |

En un bucle cerrado estable con unas 16 solicitudes en curso y poco tiempo de espera del cliente, la ley de Little da rendimiento ≈ concurrencia / latencia media: 16 / 0.000355 = 45,070 (se informaron 44,991), 16 / 0.000415 = 38,554 (38,507) y 16 / 0.000624 = 25,641 (25,602). La tasa entre AZ informada es **33.5 % menor** que la de la misma AZ en esta prueba. Esta relación no identifica una causa exclusiva de la latencia ni predice una penalización universal por AZ. La contención de CPU compartida es una explicación posible de la cola más lenta en el mismo nodo, pero no se hizo profiling que la demostrara.

## Medición 2. Rendimiento: el límite de 5 Gbps por flujo y el límite de 10 Gbps de la instancia

iperf3 3.19, TCP, 20 s por ejecución, `-J`, cliente `cli`. Las columnas de CPU son las cifras por proceso de iperf3; 100 % equivale a un vCPU.

| Ruta | Flujos (-P) | Gbps enviados | Gbps recibidos | Retransmisiones | Bytes enviados | CPU cliente | CPU servidor | RTT TCP medio del emisor (flujo 1) | max snd_cwnd |
|---|---|---|---|---|---|---|---|---|---|
| mismo nodo (`cli`→`srv-same`) | 1 | **29.97** | 29.97 | 13 | 74,921,541,632 | **99.8 %** | 80.9 % | 34 µs | 1,861,392 B |
| mismo nodo | 8 | **48.15** | 48.08 | 14,567 | 120,375,083,008 | 179.0 % | 186.9 % | 201 µs / 767 µs (flujos 1, 2) | 5,888,442 B |
| misma AZ (`cli`→`srv-a`, 2a→2a) | 1 | **4.96** | 4.96 | 4 | 12,411,731,968 | 19.5 % | 15.4 % | **5,641 µs** | 4,349,214 B |
| misma AZ | 8 | **9.94** | 9.93 | 5,874 | 24,846,139,392 | 36.3 % | 159.3 % | 2,720 µs / 1,626 µs | 1,163,370 B |
| entre AZ (`cli`→`srv-b`, 2a→2b) | 1 | **4.96** | 4.96 | 2 | 12,411,994,112 | 20.0 % | 22.5 % | **5,420 µs** | 4,304,469 B |
| entre AZ | 8 | **9.94** | 9.93 | 5,979 | 24,845,090,816 | 36.7 % | 138.2 % | 3,671 µs / 3,237 µs | 1,226,013 B |

Hay cuatro aspectos que conviene interpretar:

1. **El tráfico en el mismo nodo no usó la NIC física.** El resultado de un flujo fue 29.97 Gbps con 99.8 % de CPU del proceso cliente; ocho flujos llegaron a 48.15 Gbps. Siguen influyendo el enrutamiento del host, las rutas veth de ambos Pods, el procesamiento del kernel y la planificación de CPU. Es un benchmark de red con indicios de presión de CPU, no una medición de velocidad pura de copia en memoria.
2. **Ambas pruebas de un flujo entre nodos llegaron a 4.96 Gbps.** Esto concuerda con el límite ordinario de 5 Gbps fuera de un grupo de ubicación de clúster. AWS también documenta hasta 10 Gbps para flujos dentro de uno de esos grupos y hasta 25 Gbps con rutas ENA Express aptas en la misma AZ. Que el proceso iperf3 use poca CPU no descarta todos los límites del host o de la red.
3. **Ambas pruebas de ocho flujos llegaron a 9.94 Gbps.** Esto respalda que estas rutas tuvieron un rendimiento observado parecido durante esta ventana. Hubo retransmisiones incluso con un flujo (4 / 2 para las rutas entre nodos); aumentaron a ocho flujos (5,874 / 5,979). Por sí solas, las retransmisiones no identifican un límite de ENA ni dónde se produjeron las pérdidas. No se recopilaron los contadores de allowance de ENA.
4. **El RTT TCP bajo carga superó el RTT ICMP en reposo.** El emisor informó aproximadamente **5.6 / 5.4 ms** con un flujo y una ventana de congestión de unos 4.3 MB, frente a medias de ping en reposo de 0.34 / 0.54 ms. La cola es una posible explicación, pero los protocolos, el muestreo y la carga son distintos. No se midieron la ubicación de la cola ni 5 ms adicionales garantizados para cada RPC multiplexada.

El MSS informado de 8949 concuerda con una MTU de 9001 bytes y la sobrecarga observada de IPv4/TCP; el MSS efectivo también depende de los encabezados y la MTU de la ruta. La columna de bytes enviados es volumen transferido por la aplicación, no volumen facturable verificado de forma independiente.

> En esta ruta EC2 ordinaria, los flujos paralelos aprovecharon más el ancho de banda de ráfaga disponible en la instancia que un flujo. Aumentar el paralelismo también cambia la carga de CPU, la congestión y el coste. Compruebe los límites de la instancia y de la ruta reales antes de cambiar los fetchers de Kafka o el paralelismo de transferencias; estas mediciones no respaldan ni que «cada conexión esté limitada a 5 Gbps» ni que «una AZ siempre duplique el ancho de banda».

### Ejecución sostenida de 3 minutos y créditos de ráfaga

La línea base informada de m5.xlarge es 1.25 Gbps, con un pico de mejor esfuerzo de hasta 10 Gbps. La prueba histórica de cuatro flujos entre AZ duró 180 s, con intervalos de 10 s (`iperf3 -c 10.0.3.65 -p 5201 -t 180 -P 4 -i 10 -J`). Esa IP pertenece al entorno registrado; antes de otra prueba, obtenga las IP actuales de los Pods.

| Elemento | Valor |
|---|---|
| Gbps por intervalo de 10 s (18 intervalos) | 9.94, 9.93 ×12, 9.92, 9.93 ×4 (**mín. 9.92, máx. 9.94**) |
| Total enviado | 223,376,179,200 B = **223.4 GB** en 180.0 s (9.93 Gbps) |
| Retransmisiones | 44,842 (≈ 249/s; 2,273–2,669 por intervalo de 10 s) |
| CPU | cliente 30.7 % (sistema 30.1 %), servidor 54.2 % (sistema 52.2 %) |

**Durante 180 s no se observó una caída hacia 1.25 Gbps.** Esto no demuestra que los créditos sean ilimitados ni que el pico sostenido esté garantizado. AWS documenta ráfagas variables de mejor esfuerzo y una limitación hacia la línea base cuando se agotan los créditos. Dimensione las copias de seguridad y los reequilibrios prolongados según la línea base aplicable y los requisitos medidos de la carga, en lugar de extrapolar esta prueba breve.

## Medición 3. Modelo del coste de transferencia de datos entre AZ

Esta sección conserva la aritmética de costes del informe como estimación. El benchmark aportó bytes de carga útil y un precio de lista público, no un informe de costes y uso (CUR) ni una factura.

Para transferencias directas entre IP privadas de EC2 en AZ de la misma región, la [página de precios de EC2](https://aws.amazon.com/ec2/pricing/on-demand/) documenta $0.01/GB en cada extremo. El elemento informado de la API pública de precios fue `APN2-DataTransfer-Regional-Bytes`, **$0.0100000000 USD/GB**. `get-products` devuelve precios de catálogo, no la tarifa pagada por una cuenta concreta. Una dirección de carga útil puede generar cargos de «salida» en el extremo emisor y de «entrada» en el receptor; no requiere una transferencia de retorno igual de grande. Otras rutas de servicios de AWS pueden tener reglas de cobro diferentes.

| Escenario | Volumen de carga útil del modelo histórico en GB decimales | Coste estimado (GB del modelo × $0.01 × 2) |
|---|---|---|
| Ejecución de 180 s (carga útil medida; coste estimado) | 223.4 GB | 223.4 × $0.01 ≈ **$2.23 en cada extremo; $4.47 en total** |
| Transferencias iperf3 entre AZ de la medición 2 (12.41 + 24.85 + 223.38 GB) | 260.6 GB | ≈ $2.61 en cada extremo; **≈ $5.21 en total** (se excluye otro tráfico) |
| Promedio de 1 Gbps que cruza AZ durante 30 días (**suposición**) | 0.125 GB/s × 86,400 s × 30 días = 324,000 GB ≈ **324 TB** | 324,000 × $0.02 ≈ **$6,480/mes** |
| StatefulSet RF3 repartido entre 3 AZ con 100 MiB/s de ingesta del líder (**suposición**, solo tráfico de replicación) | dos seguidores, cada uno en otra AZ → 2 × 100 MiB/s = 209,715,200 B/s × 2,592,000 s ≈ 543,600 GB ≈ **544 TB/mes** | 543,600 × $0.02 ≈ **$10,870/mes** |

Las cuatro filas usan la conversión decimal original, **1 GB = 10⁹ bytes de carga útil**, como supuesto del modelo. Esta revisión no determinó que la cantidad facturada por EC2 equivalga a esa conversión. Los totales exactos son 223,376,179,200 B para la ejecución sostenida y 260,633,264,128 B para las tres pruebas iperf3 entre AZ. Concilie las unidades realmente medidas, las tarifas, ambos extremos facturados, la sobrecarga y las retransmisiones del protocolo y los créditos o descuentos aplicables con los [registros de transferencia de datos del CUR](https://docs.aws.amazon.com/cur/latest/userguide/cur-data-transfers-charges.html). Las dos últimas filas también suponen tráfico continuo durante 30 días; el volumen de replicación excluye el tráfico de productores y consumidores. **$4.47 y $5.21 son estimaciones, no importes que se haya demostrado que se pagaron.**

**Qué debe hacer el operador:**

- **Preferir extremos locales adecuados cuando sea compatible.** La documentación actual de Kubernetes usa `Service.spec.trafficDistribution: PreferSameZone`; `PreferClose` es el alias obsoleto. Es una preferencia con fallback, no una restricción estricta a una zona. Compruebe la versión del servidor de API, kube-proxy y la compatibilidad de la función; este clúster registrado usó kube-proxy 1.35 con un plano de control 1.36. No se midieron esta preferencia ni una ruta por Service, y no afecta el tráfico directo entre IP de Pods.
- **Equilibrar localidad y tolerancia a fallos.** Las lecturas o clientes con conocimiento de zona pueden reducir transferencias evitables, pero trasladar todas las réplicas RF3 a una AZ sacrifica la protección ante fallos de AZ. Mantenga el diseño requerido de réplicas y failover; consulte [Operaciones de clústeres zonales](../ops/15-zonal-operations-guide.md).
- **Medir ambos extremos facturados.** Registre las AZ de origen y destino y el volumen medido de copias de seguridad, reequilibrios y reprocesamientos. Sume los registros de uso pertinentes de «entrada» y «salida», que pueden pertenecer a cuentas distintas; no deduzca la factura final solo a partir de los bytes de carga útil.

## Medición 4. DNS: amplificación de consultas con `ndots:5`

![Una búsqueda glibc con ndots:5 recorre los cuatro sufijos de búsqueda con pares A+AAAA (8 respuestas NXDOMAIN, 10 consultas) antes de que responda el nombre absoluto, frente a una búsqueda con punto final que termina en 2 consultas.](../.gitbook/assets/en-networking-06-pod-network-benchmark-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-06-pod-network-benchmark-1.html)

Este diagrama muestra la secuencia de búsqueda glibc registrada. Los 4.37 ms terminan en la respuesta A informada, no en la llamada completa a `getaddrinfo`; las flechas ascendentes son explicativas, porque la captura en el Pod no observó ese tramo. «cache 30» es un TTL máximo, no un acierto garantizado durante 30 segundos.

El Pod registrado tenía cuatro dominios de búsqueda y ndots:5; esa configuración no es universal en EKS ni entre políticas DNS, sistemas operativos o ajustes de nodo. En esta consulta glibc `AF_UNSPEC`, se solicitaron A y AAAA para cada candidato, y los cuatro candidatos de búsqueda devolvieron NXDOMAIN antes de que tuviera éxito el nombre STS absoluto. La concurrencia A/AAAA y el número de consultas pueden cambiar según las opciones del resolvedor, la familia de direcciones, los aciertos tempranos, los reintentos y el fallback a TCP. La captura histórica usó `tcpdump -i eth0 -nn udp port 53`, que solo observa DNS por UDP. El informe describe una primera consulta en un proceso seguida de 20 repeticiones cronometradas; una primera llamada en un proceso no demuestra que las cachés de CoreDNS o de los servidores ascendentes estuvieran vacías. Consulte [la configuración DNS de los Pods en Kubernetes](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/).

### Consultas enviadas para una resolución y latencia en caliente (20 repeticiones), ms

| Pod / ndots | Nombre (puntos) | Consultas enviadas | Respuestas NXDOMAIN | mín. en caliente | **mediana** | p90 | máx. |
|---|---|---|---|---|---|---|---|
| predeterminado / 5 | `kubernetes.default` (1) | 4 | 2 | 0.87 | **1.71** | 1.97 | 2.61 |
| predeterminado / 5 | `kubernetes.default.svc.cluster.local` (4) | **10** | 8 | 1.53 | **3.63** | 4.45 | 6.41 |
| predeterminado / 5 | `kubernetes.default.svc.cluster.local.` (punto final) | 2 | 0 | 0.33 | **0.46** | 1.09 | 1.58 |
| predeterminado / 5 | `sts.ap-northeast-2.amazonaws.com` (3) | **10** | 8 | 3.08 | **3.78** | 4.66 | 4.84 |
| predeterminado / 5 | `sts.ap-northeast-2.amazonaws.com.` (punto final) | 2 | 0 | 0.42 | **0.80** | 1.25 | 2.17 |
| predeterminado / 5 | `www.amazon.com` (2) | **10** | 8 | 2.51 | **3.46** | 3.74 | 5.86 |
| `ndots:1` / 1 | `kubernetes.default` (1) | **6** | 4 | 1.16 | **2.04** | 2.80 | 4.54 |
| `ndots:1` / 1 | `kubernetes.default.svc.cluster.local` (4) | 2 | 0 | 0.35 | **0.97** | 1.08 | 1.35 |
| ndots:1 / 1 | `kubernetes.default.svc.cluster.local.` | 2 | 0 | 0.34 | **0.40** | 0.97 | 1.17 |
| ndots:1 / 1 | `sts.ap-northeast-2.amazonaws.com` (3) | 2 | 0 | 0.45 | **0.54** | 1.22 | 1.42 |
| ndots:1 / 1 | `sts.ap-northeast-2.amazonaws.com.` | 2 | 0 | 0.47 | **0.75** | 1.20 | 1.30 |
| ndots:1 / 1 | `www.amazon.com` (2) | 2 | 0 | 0.63 | **0.90** | 1.27 | 2.74 |

Los tiempos informados de la primera consulta en un proceso fueron: predeterminado / `sts`, 6.22 ms; predeterminado / `sts.`, 2.87 ms; predeterminado / `www.amazon.com`, 9.58 ms; predeterminado / `kubernetes.default.svc.cluster.local`, 7.40 ms; ndots:1 / `kubernetes.default`, 10.52 ms; y ndots:1 / `sts`, 2.84 ms. Incluyen la inicialización del resolvedor y son distintos de las líneas de tiempo de red que aparecen a continuación.

**Cómo interpretarlo.** En estas muestras, los nombres externos y el FQDN del clúster sin punto final produjeron **10 consultas / 8 respuestas NXDOMAIN**. La mediana de STS con punto final bajó de 3.78 a 0.80 ms; la del FQDN del clúster bajó de 3.63 a 0.46 ms. `kubernetes.default` tuvo éxito en el segundo candidato de búsqueda y necesitó solo cuatro consultas: la expansión no siempre recorre la lista completa. [La caché de CoreDNS](https://coredns.io/plugins/cache/) puede almacenar respuestas negativas, pero `cache 30` establece un TTL máximo; siguen aplicándose los TTL y mínimos de respuesta, y cada réplica tiene su propia caché. El TTL predeterminado del plugin de Kubernetes es 5 s si no se configura otro. Las consultas secuenciales persisten incluso si hay aciertos en caché, pero esta captura no demuestra que todas las consultas en caliente evitaran tráfico ascendente.

### Recorrido de una resolución en frío de `sts.ap-northeast-2.amazonaws.com` (ndots:5, tcpdump, ms desde el primer paquete)

| t (ms) | Candidato enviado a 172.20.0.10 (A + AAAA en paralelo) | Respuesta |
|---|---|---|
| 0.00 | `sts.ap-northeast-2.amazonaws.com.bench-net.svc.cluster.local.` | NXDomain (autoritativa, plugin kubernetes de CoreDNS) a 0.92 / 1.14 |
| 1.21 | `sts.ap-northeast-2.amazonaws.com.svc.cluster.local.` | NXDomain a 2.01 / 2.26 |
| 2.32 | `sts.ap-northeast-2.amazonaws.com.cluster.local.` | NXDomain a 3.15 / 3.41 |
| 3.47 | `sts.ap-northeast-2.amazonaws.com.ap-northeast-2.compute.internal.` | NXDomain (reenviado al resolvedor de la VPC, no autoritativo) a 3.68 / 3.93 |
| 3.99 | `sts.ap-northeast-2.amazonaws.com.` | **A 10.0.3.84, A 10.0.2.129** a 4.37 (AAAA: sin datos) |

La tabla registra 10 consultas y 8 respuestas NXDOMAIN. Los **4.37 ms** van desde la primera consulta hasta la respuesta A informada; no aparece el tiempo de finalización de AAAA, así que no son los 6.22 ms de la llamada inicial completa. Los RTT de los candidatos no son uniformemente de 0.8–1.1 ms: el cuarto par tardó 0.21 / 0.46 ms y la A final, 0.38 ms. kube-proxy en modo iptables selecciona un extremo para un flujo conntrack nuevo, no de forma independiente para cada paquete; las solicitudes A/AAAA pueden compartir ese flujo. Con dos extremos seleccionados por igual, cabría esperar que la mitad de los flujos nuevos use uno; es una expectativa ilustrativa, **no una fracción medida de consultas DNS entre AZ**. La captura en el Pod que muestra la VIP `172.20.0.10` no permite identificar la AZ del backend elegido. El informe original atribuye las dos IP privadas de STS a las ENI de endpoints de interfaz y registra, en otra observación, un candidato reenviado de 2.2 ms / un recorrido en red de 5.6 ms para el FQDN del clúster, frente a 0.4–0.5 ms con punto final.

### Qué hace ndots:1 y su efecto secundario

- **Nombres externos en estas muestras**: 10 → **2 consultas**; mediana de aproximadamente 3.5–3.8 → **0.5–0.9 ms**. La mejora depende de los nombres y del comportamiento del resolvedor.
- **Los nombres cortos pueden provocar un intento fallido adicional.** Aquí `kubernetes.default` tiene un punto, por lo que cumple ndots:1 y glibc probó primero `kubernetes.default.`. CoreDNS lo reenvió y recibió NXDOMAIN tras 1.6 ms; después probó el sufijo del espacio de nombres y finalmente tuvo éxito con `svc.cluster.local` en `172.20.0.1`: seis consultas, cuatro respuestas NXDOMAIN y mediana de 2.04 ms frente a 1.71 ms. Esto puede revelar nombres de aspecto interno al servidor ascendente. Antes de cambiar ndots, pruebe los nombres de Service de cada aplicación; los FQDN completos de los Services reducen esta ambigüedad.
- **El punto final convierte el nombre en absoluto para el resolvedor**, y evita la expansión de búsqueda en este resolvedor. No garantiza dos consultas en la red ni una latencia fija con reintentos, otras opciones de familia de direcciones o caché.

### Cálculo de amplificación (derivado)

Con el **mismo patrón de respuestas**, sin caché DNS en la aplicación y una consulta por solicitud, 1,000 resoluciones/s × 10 consultas equivalen a 10,000 consultas/s, frente a 2,000 con el formato de dos consultas. De las 10,000, 8,000 (80 %) recibirían NXDOMAIN. Es un modelo del número de consultas, no una medición de CPU de CoreDNS ni de la fracción entre AZ. Las diferencias de mediana observadas son 3.78 − 0.80 = 2.98 ms para STS y 3.63 − 0.46 = 3.17 ms para el FQDN del clúster; no son penalizaciones fijas por solicitud.

**Opciones para probar con la aplicación real:**

- Use nombres DNS absolutos cuando el cliente los admita. No añada un punto a ciegas a URL HTTPS o endpoints de AWS SDK: deben seguir funcionando correctamente el encabezado Host, SNI, la verificación del certificado y la firma de solicitudes.
- Evalúe `dnsConfig: {options: [{name: ndots, value: "1"}]}` junto con el comportamiento de los nombres cortos y la caché DNS de la aplicación.
- Evalúe [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) cuando corresponda. Los aciertos permanecen en el nodo; los fallos de caché todavía pueden ir aguas arriba. [EKS Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html) ejecuta CoreDNS local al nodo como servicio del sistema; un clúster solo con Auto Mode no necesita un Deployment de CoreDNS, mientras que los nodos no Auto Mode de un clúster mixto sí lo necesitan.
- [CoreDNS autopath](https://coredns.io/plugins/autopath/) puede completar la búsqueda en el servidor, pero su integración con Kubernetes requiere `pods verified`, visibilidad de la IP del Pod de origen y los watches/RBAC/memoria asociados. La configuración registrada `pods insecure` no cumple esos requisitos. Esta optimización no se probó aquí.

## Cómo reproducirlo: procedimiento revisado

Use un laboratorio aislado aprobado y un espacio de nombres exclusivo para esta prueba. Guarde una copia adaptada del primer manifiesto como `bench-net.yaml` y los dos objetos DNS como `bench-dns.yaml`; mantenga coherentes los nombres de los espacios de nombres. Antes de aplicar los manifiestos, compruebe la capacidad del NodePool, las AZ, la planificación y los permisos de captura de paquetes. No debilite los controles de admisión ni de seguridad de producción para ejecutar la prueba. Incluso estos comandos acotados pueden saturar nodos y generar cargos.

Ejecute todos los comandos desde el **shell Bash del operador**, sin abrir un shell interactivo dentro de `cli`. La revisión comprobó la sintaxis y algunos comportamientos locales de las herramientas; no desplegó este manifiesto ni generó esta carga de red en EKS.

**1. Aplique el manifiesto adaptado y verifique la ubicación.**

```bash
set -euo pipefail
BENCH_NS=bench-net
kubectl apply -f bench-net.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready \
  pod/cli pod/srv-same pod/srv-a pod/srv-b --timeout=300s
kubectl -n "$BENCH_NS" get pods -o wide
kubectl get nodes -L topology.kubernetes.io/zone,node.kubernetes.io/instance-type,karpenter.sh/nodepool

SAME_IP=$(kubectl -n "$BENCH_NS" get pod srv-same -o jsonpath='{.status.podIP}')
AZ_IP=$(kubectl -n "$BENCH_NS" get pod srv-a -o jsonpath='{.status.podIP}')
CROSS_IP=$(kubectl -n "$BENCH_NS" get pod srv-b -o jsonpath='{.status.podIP}')
: "${SAME_IP:?missing srv-same IP}" "${AZ_IP:?missing srv-a IP}" "${CROSS_IP:?missing srv-b IP}"
for bench_pod in srv-same srv-a srv-b; do
  kubectl -n "$BENCH_NS" logs "$bench_pod" --tail=30
  kubectl -n "$BENCH_NS" exec "$bench_pod" -- ss -lnt
done
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- \
    curl --fail --silent --show-error --max-time 5 "http://$bench_ip:8080/" >/dev/null
done
```

Antes de continuar, compruebe que cli y srv-same estén en el mismo nodo, que srv-a esté en otro nodo de la misma AZ y que `srv-b` esté en otra AZ. Verifique que los procesos escuchen en 5201/8080/8079 y que no haya errores de inicio: que el Pod esté Ready no demuestra que estos procesos estén escuchando, porque el manifiesto histórico no tiene probes de disponibilidad. Registre los ID de nodo, las IP, los ID de imagen y las salidas reales de `iperf3 --version` y `fortio version`. Si se recrea un Pod, deténgase y actualice las direcciones.

**2. RTT y una solicitud HTTP de referencia.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- ping -c 200 -i 0.05 -q "$bench_ip"
done
kubectl -n "$BENCH_NS" exec cli -- curl --fail --silent --show-error --max-time 5 \
  -o /dev/null -w 'connect=%{time_connect} total=%{time_total}\n' "http://$CROSS_IP:8080/"
```

**3. Rendimiento, con duración acotada y archivos de salida locales del operador.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 1 -J > "t1-$bench_ip-P1.json"
  kubectl -n "$BENCH_NS" exec cli -- iperf3 -c "$bench_ip" -p 5201 -t 20 -P 8 -J > "t1-$bench_ip-P8.json"
done
kubectl -n "$BENCH_NS" exec cli -- \
  iperf3 -c "$CROSS_IP" -p 5201 -t 180 -P 4 -i 10 -J > t1-cross-sustained180-P4.json
```

Compruebe los errores del JSON además del código de salida. Lea `end.sum_sent.bits_per_second`, `end.sum_sent.retransmits`, `end.cpu_utilization_percent.host_total` / `remote_total` y `end.streams[].sender.mean_rtt` / `max_snd_cwnd`. iperf3 3.19 expresa la CPU del proceso como 100 % de un CPU durante el tiempo transcurrido; varios hilos pueden superar 100 %. Los campos de RTT TCP están en microsegundos.

**4. Latencia de solicitudes. Repita para cada dirección del servidor que haya verificado.**

```bash
for bench_ip in "$SAME_IP" "$AZ_IP" "$CROSS_IP"; do
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 60s "http://$bench_ip:8080/" > "http-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 100 -c 4 -t 30s -keepalive=false "http://$bench_ip:8080/" > "new-connection-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -qps 0 -c 16 -t 20s "http://$bench_ip:8080/" > "closed-loop-$bench_ip.json"
  kubectl -n "$BENCH_NS" exec cli -- fortio load -quiet -r 0.00001 -json - \
    -grpc -ping -qps 100 -c 4 -t 30s "$bench_ip:8079" > "grpc-$bench_ip.json"
done
```

En Fortio 1.69.5, `-r` es la resolución del bucket más bajo del histograma, en segundos: el valor predeterminado `0.001` equivale a 1 ms, y `0.00001`, a 10 µs; los buckets más grandes pueden ser más amplios. Los percentiles se interpolan dentro de los límites de cada bucket, incluidos los mínimos y máximos observados en los extremos. Por tanto, un único bucket con datos **no implica p50 = 0.5 ms**. El informe descartó los primeros percentiles de resolución gruesa y repitió la medición con resolución de 10 µs; conserve ese historial sin calificar de falsos todos los percentiles interpolados. Varios valores de cola y medianas con conexión nueva en las tablas superan 1 ms. Guarde el histograma completo y los contadores de errores junto con las medias.

**5. DNS: separe la captura de una consulta de las repeticiones cronometradas.**

```bash
kubectl apply -f bench-dns.yaml
kubectl -n "$BENCH_NS" wait --for=condition=Ready pod/dns-default pod/dns-ndots1 --timeout=300s
for bench_pod in dns-default dns-ndots1; do
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- cat /etc/resolv.conf
  kubectl -n "$BENCH_NS" exec "$bench_pod" -c app -- ldd --version
done
```

En el terminal 1, inicie la captura antes de la única consulta. Este filtro incluye DNS convencional por UDP y TCP en el puerto 53; no incluye DNS cifrado ni el tramo ascendente de CoreDNS. Después de esa consulta, detenga la captura con Ctrl-C antes de hacer las repeticiones en caliente.

```bash
kubectl -n bench-net exec -it dns-default -c sniffer -- \
  tcpdump -l -i eth0 -nn '(udp or tcp) and port 53'
```

En el terminal 2, cree este helper local y páselo por la entrada estándar mediante **`kubectl exec -i`**. El modo inicial realiza exactamente una llamada al resolvedor. El modo en caliente hace primero una llamada no medida y luego 20 llamadas en el mismo proceso; este procedimiento revisado deja explícito el límite de la captura.

```bash
cat > dns-probe.py <<'PY'
import json
import socket
import statistics
import sys
import time

name, mode = sys.argv[1:3]
if mode not in ("first", "warm"):
    raise SystemExit("mode must be first or warm")

def one():
    started = time.perf_counter()
    socket.getaddrinfo(name, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    return (time.perf_counter() - started) * 1000

first = one()
if mode == "first":
    print(json.dumps({"name": name, "first_process_ms": first}))
else:
    samples = [one() for _ in range(20)]
    ordered = sorted(samples)
    print(json.dumps({
        "name": name, "warmup_ms": first, "samples_ms": samples,
        "min_ms": ordered[0], "median_ms": statistics.median(ordered),
        "p90_ms": ordered[17], "max_ms": ordered[-1],
    }))
PY
BENCH_NS=bench-net
DNS_POD=dns-default
DNS_NAME=sts.ap-northeast-2.amazonaws.com
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" first < dns-probe.py
```

Después de detener la captura:

```bash
kubectl -n "$BENCH_NS" exec -i "$DNS_POD" -c app -- \
  python3 - "$DNS_NAME" warm < dns-probe.py
```

Repita con los nombres de la tabla y `DNS_POD=dns-ndots1`, cambiando también el destino de la captura. Cuente los pares de consultas/respuestas de la ventana que contiene solo la primera llamada; no cuente 21 búsquedas como una. Use los mismos digests, versiones del resolvedor y configuración, aunque se esperan diferencias en tiempos y estado de caché. Esta página no incluye los digests originales de las imágenes ni todos los artefactos de paquetes/JSON, por lo que no se garantiza una reproducción exacta.

**6. Limpie solo los recursos de esta prueba.** Si `bench-net` se creó exclusivamente para la ejecución, elimínelo con `kubectl delete namespace bench-net` después de guardar los resultados. Verifique por separado los nodos restantes y los costes. La consolidación de Karpenter depende de la política, los presupuestos y otras cargas; eliminar el espacio de nombres no garantiza que los nodos se retiren inmediatamente. `do-not-disrupt` no protege frente a todos los métodos de interrupción forzada.

## Advertencias

- **Los nodos eran nuevos, pero no estaban completamente aislados.** Poco después de que Karpenter lanzara los tres nodos m5.xlarge para esta prueba, la consolidación trasladó algunos Pods pequeños de otros espacios de nombres (uno al nodo cli, tres al nodo srv-b; pequeños servicios y controladores internos no relacionados con el tráfico del benchmark). Estuvieron inactivos o con poco tráfico durante las pruebas, y la carga se limitó a ráfagas de hasta 180 s. El nodo cli mostró 3901m / 3920m (99 %) de CPU *solicitada*, lo que no indica la utilización real.
- **Una sola ejecución (n = 1 por celda, un día).** No hubo repeticiones independientes para estimar la varianza. Las clasificaciones, proporciones y explicaciones causales también están limitadas por ese tamaño de muestra; ninguna constituye un SLA.
- **No se midieron ClusterIP ni la distribución de tráfico.** El informe indica que la creación de un Service en el espacio de nombres de prueba falló con `failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`. Un webhook con `failurePolicy: Fail` rechaza las solicitudes coincidentes; las reglas, selectores del espacio de nombres/objeto y condiciones de coincidencia determinan el alcance. Este incidente histórico no afirma que el clúster actual no pueda crear ningún Service. El benchmark no evitó el webhook. DNS siguió usando el Service `kube-dns` preexistente. Consulte el [manual de solución de problemas](../ops/16-troubleshooting-playbook.md).
- **No se recopilaron contadores de allowance de ENA.** `ethtool -S` debe apuntar a la interfaz ENA real del host y requiere acceso adecuado; el `eth0` de un Pod suele ser un veth, y `hostNetwork` por sí solo no demuestra que se use el dispositivo correcto ni que haya permisos. Entre los contadores pertinentes están `bw_in_allowance_exceeded`, `bw_out_allowance_exceeded`, `pps_allowance_exceeded`, `conntrack_allowance_exceeded` y `linklocal_allowance_exceeded`. Las retransmisiones no sustituyen estas mediciones.
- **Solo se observó que el crédito de ráfaga no se agotó durante 180 s.** En instancias «Hasta», las transferencias sostenidas más largas pueden limitarse hacia la línea base (1.25 Gbps). No se probó nada más allá de 180 s.
- **No se controló el estado de la caché DNS.** Las consultas de un proceso nuevo y las repeticiones son diferentes, pero `cache 30` no garantiza un acierto durante 30 s. La selección de réplica y el estado ascendente pueden afectar ambos conjuntos de tiempos; la comparación es observacional.
- **Es posible que hubiera presión de CPU en el mismo nodo.** El 99.8 % de CPU del proceso cliente respalda esa interpretación del resultado de 29.97 Gbps, pero no demuestra todos los cuellos de botella ni hace que 29.97 / 48.15 Gbps sean cifras portables a otras instancias.
- **No se compararon otros modos de CNI ni la aplicación de políticas.** La delegación de prefijos y Security Groups for Pods estaban desactivados; el espacio de nombres no tenía NetworkPolicies. Estos Pods sin controladores no validan la aplicación de VPC CNI NetworkPolicy para las cargas cuyo controlador sea compatible.

## Lecturas relacionadas

- [Amazon VPC CNI](./01-vpc-cni.md): el plano de datos de estas mediciones (Pods con IP de VPC directa, delegación de prefijos y calentamiento de ENI/IP).
- [Operaciones de clústeres zonales](../ops/15-zonal-operations-guide.md): ubicación alineada por zona y diseño de failover de AZ que reducen la factura de la medición 3.
- [Manual de solución de problemas](../ops/16-troubleshooting-playbook.md): diagnóstico de fallos de webhook; el incidente de esta página es histórico.
- [Guía para elegir entre sidecar y modo ambient](../service-mesh/istio/comparison/03-sidecar-vs-ambient.md): experimento con hardware y carga distintos; la diferencia de +1.29 ms corresponde al escenario completo.
- [Benchmark medido de EBS gp2 frente a gp3](../storage/01-ebs-gp2-gp3-benchmark.md): la ruta de almacenamiento del mismo clúster, medida.
- [Benchmark medido de Kafka en EKS](../data-on-eks/kafka/09-kafka-benchmark.md): tráfico de replicación, límites de flujo y compromisos de disponibilidad.
- [Hoja de ruta de la guía: serie de benchmarks medidos](../roadmap.md).
- [Cuestionario: benchmark de red de Pods](../quizzes/networking/06-pod-network-benchmark-quiz.md).

### Referencias principales usadas en la revisión

- [Implementación del histograma de Fortio 1.69.5](https://github.com/fortio/fortio/blob/v1.69.5/stats/stats.go) · [opciones de la CLI](https://github.com/fortio/fortio/blob/v1.69.5/cli/fortio_main.go).
- [Orden de búsqueda de glibc 2.41](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_query.c) · [transporte A/AAAA](https://github.com/bminor/glibc/blob/glibc-2.41/resolv/res_send.c).
- [Requisitos de los plugins Kubernetes / autopath de CoreDNS](https://coredns.io/plugins/kubernetes/).
- [Distribución de tráfico de Service en Kubernetes](https://kubernetes.io/docs/concepts/services-networking/service/) · [gestión de IP virtuales](https://kubernetes.io/docs/reference/networking/virtual-ips/).
- [Métricas de red ENA de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html).
- [Condiciones de interrupción y limpieza de Karpenter](https://karpenter.sh/docs/concepts/disruption/).
