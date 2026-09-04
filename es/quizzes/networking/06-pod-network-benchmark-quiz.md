# Pod Network Benchmark Quiz

1. Medido con `ping -c 200 -i 0.05`, ¿cómo cambió el RTT promedio de Pod a Pod desde el mismo nodo → nodo diferente en la misma AZ → AZ diferente?
   - A) 0.040 ms → 0.544 ms → 0.339 ms — entre AZ fue más rápido que en la misma AZ
   - B) Las tres rutas se mantuvieron dentro del ruido de aproximadamente 0.3 ms
   - C) 0.040 ms → 0.339 ms → 0.544 ms — salir del nodo añade +0.30 ms y salir de la AZ añade otros +0.21 ms, una escalera
   - D) 0.040 ms → 0.339 ms → 5.4 ms — el límite de la AZ llevó el RTT a milisegundos enteros
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 0.040 ms → 0.339 ms → 0.544 ms — salir del nodo añade +0.30 ms y salir de la AZ añade otros +0.21 ms, una escalera**

**Explicación:**
Los promedios de ping (200 sondas a 50 ms, 0/200 pérdidas) fueron 0.040 ms en el mismo nodo, 0.339 ms en la misma AZ y 0.544 ms entre AZ. Misma AZ − mismo nodo = +0.30 ms, entre AZ − misma AZ = +0.21 ms, entre AZ − mismo nodo = +0.50 ms. El p50 de HTTP de fortio (100 qps, 4 conexiones, keepalive) dibujó la misma escalera en 0.259 → 0.461 → 0.704 ms (+0.20 / +0.24 ms), y el p50 de HTTP − promedio de ping fue de aproximadamente 0.22 / 0.12 / 0.16 ms por ruta — la pila de espacio de usuario de cliente+servidor. La cifra de 5.4 ms es el RTT de TCP del emisor durante una ejecución de iperf3 que saturó un único flujo (formación de cola en el shaper), no el RTT entre AZ inactivo (D es incorrecta). Como referencia, la página de comparación de Istio de este repositorio sitúa un salto de sidecar en +1.29 ms p50 — un salto de mesh cuesta más que un salto de AZ.

</details>

2. Un único flujo TCP de iperf3 (`-P 1`) se detuvo en 4.96 Gbps tanto en la ruta de la misma AZ como en la entre AZ, y 8 flujos (`-P 8`) alcanzaron 9.94 Gbps en ambas. ¿Qué explica mejor los dos números?
   - A) 4.96 Gbps es un núcleo de CPU del cliente saturado; 8 flujos son más rápidos porque usan más núcleos
   - B) 4.96 Gbps es el límite documentado por EC2 de 5 Gbps para un solo flujo (fuera de un cluster placement group) y 9.94 Gbps es el pico de instancia de m5.xlarge «Up to 10 Gigabit» — para usar el ancho de banda de la instancia se deben paralelizar los flujos
   - C) 4.96 Gbps es el ancho de banda base de m5.xlarge, y 8 flujos gastaron créditos de burst para alcanzar el pico
   - D) Las jumbo frames (MTU 9001) estaban inactivas para el único flujo
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 4.96 Gbps es el límite documentado por EC2 de 5 Gbps para un solo flujo (fuera de un cluster placement group) y 9.94 Gbps es el pico de instancia de m5.xlarge «Up to 10 Gigabit» — para usar el ancho de banda de la instancia se deben paralelizar los flujos**

**Explicación:**
Un único flujo entre Pods en nodos diferentes fue idéntico en ambas rutas — 4.96 Gbps en la misma AZ (cli→srv-a) y 4.96 Gbps entre AZ (cli→srv-b) — lo que corresponde al límite de 5 Gbps por flujo único que documenta AWS. iperf3 informó una CPU de cliente de solo 19.5 % / 20.0 % (de un núcleo) durante esas ejecuciones, así que la CPU no era el límite (A es incorrecta); el caso limitado por CPU es el único flujo en el mismo nodo a 29.97 Gbps con el cliente al 99.8 %. El ancho de banda base de m5.xlarge es 1.25 Gbps y su pico 10 Gbps (C es incorrecta) — los 9.94 Gbps de 8 flujos son ese pico. MSS 8949 (MTU 9001) se aplicó igualmente a cada ejecución (D es incorrecta). Con un solo flujo fijado en el límite, el RTT de TCP del emisor creció desde un RTT de ping inactivo de 0.34 ms (misma AZ) / 0.54 ms (entre AZ) hasta 5.6 ms / 5.4 ms con una ventana de congestión de aproximadamente 4.3 MB, y las retransmisiones pasaron de 4 / 2 con un flujo a 5,874 / 5,979 con ocho flujos cuando se alcanzó el techo de la instancia — la firma indirecta de la formación de tráfico por concesión de ENA (los contadores en sí no se recopilaron). En la práctica, un flujo de gRPC o una obtención de réplica de Kafka entre Pods en nodos diferentes nunca puede superar aproximadamente 5 Gbps.

</details>

3. El ancho de banda de iperf3 con ocho flujos fue idéntico, 9.94 Gbps, para la misma AZ y entre AZ; sin embargo, el máximo de bucle cerrado de fortio (`-qps 0`, 16 conexiones, 20 s) cayó de 38,507 qps en la misma AZ a 25,602 qps entre AZ. ¿Por qué?
   - A) El enlace entre AZ reduce a la mitad el ancho de banda para el tráfico de solicitud/respuesta
   - B) Los errores y reintentos aumentaron en la ruta entre AZ
   - C) El nodo que aloja srv-b tenía una CPU más lenta que el nodo de srv-a
   - D) La ley de Little — con 16 conexiones fijas, rendimiento = concurrencia ÷ latencia, así que 16 ÷ 0.000624 s ≈ 25,641 qps es el límite; los aproximadamente +0.2 ms de latencia que añade el salto de AZ redujeron el rendimiento en 34 %. Entre AZ cuesta latencia, no ancho de banda
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) La ley de Little — con 16 conexiones fijas, rendimiento = concurrencia ÷ latencia, así que 16 ÷ 0.000624 s ≈ 25,641 qps es el límite; los aproximadamente +0.2 ms de latencia que añade el salto de AZ redujeron el rendimiento en 34 %. Entre AZ cuesta latencia, no ancho de banda**

**Explicación:**
La latencia promedio de bucle cerrado fue 0.355 ms en el mismo nodo, 0.415 ms en la misma AZ y 0.624 ms entre AZ, y la ley de Little se cumple en las tres rutas: 16 ÷ 0.000355 = 45,070 (medido 44,991), 16 ÷ 0.000415 = 38,554 (medido 38,507), 16 ÷ 0.000624 = 25,641 (medido 25,602). Cada ejecución tuvo 0 errores (B es incorrecta) y el cuerpo de respuesta es de aproximadamente 75 bytes, por lo que el ancho de banda es irrelevante (A es incorrecta) — la misma prueba de 8 flujos mostró los mismos 9.94 Gbps en ambas rutas. srv-a y srv-b se ejecutan en el mismo tipo m5.xlarge (C es incorrecta). Para un Service de solicitud/respuesta con un pool de conexiones fijo, el salto de AZ se lleva el 34 % del rendimiento (38.5k → 25.6k qps), y la causa es la latencia. Tenga en cuenta que el p99 1.695 ms / máx. 13.593 ms en el mismo nodo es peor que en la misma AZ (0.728 / 4.502 ms) porque el cliente y el servidor comparten los 4 vCPU de un nodo — contención de CPU a 45k qps, no la red.

</details>

4. Con los mismos 100 qps / 4 conexiones, al cambiar a `-keepalive=false` (una nueva conexión TCP por solicitud), ¿cómo cambió el p50 de HTTP entre AZ?
   - A) 0.704 ms → 1.517 ms (+0.813 ms), más del doble — una nueva conexión cuesta aproximadamente un RTT para el handshake de TCP más unos 0.3 ms de configuración/desmontaje del socket, por lo que cuanto más largo sea el RTT de la ruta mayor será la penalización
   - B) Sin cambios — el kernel reutiliza las conexiones de todos modos
   - C) 0.704 ms → 0.813 ms, un pequeño aumento
   - D) El p50 no cambió; solo empeoró el p99
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) 0.704 ms → 1.517 ms (+0.813 ms), más del doble — una nueva conexión cuesta aproximadamente un RTT para el handshake de TCP más unos 0.3 ms de configuración/desmontaje del socket, por lo que cuanto más largo sea el RTT de la ruta mayor será la penalización**

**Explicación:**
Con keepalive=false (30 s, 3,000 solicitudes) el p50 fue 0.664 ms en el mismo nodo (+0.405), 1.079 ms en la misma AZ (+0.618) y 1.517 ms entre AZ (+0.813): el coste adicional crece con el RTT de la ruta, y equivale aproximadamente a un RTT (el handshake de TCP) más unos 0.3 ms de configuración/desmontaje del socket. Añadir aproximadamente 0.3 ms al promedio de ping entre AZ de 0.544 ms se acerca al +0.813 ms medido. 0.813 ms es el aumento, no el nuevo p50 (C es incorrecta), y el propio p50 se duplicó con creces (D es incorrecta). Para un Service que cruza AZ, mantener vivo un pool de conexiones ahorra más latencia de la que cuesta el propio salto de AZ (+0.24 ms).

</details>

5. La ejecución sostenida de 180 segundos (4 flujos) envió 223.4 GB a través del límite de la AZ. Con el precio verificado (`APN2-DataTransfer-Regional-Bytes`), ¿cuánto costó esa única ejecución?
   - A) $0 — el tráfico dentro de una Region es gratuito
   - B) $2.23 — $0.01 por GB, cobrado una vez
   - C) Aproximadamente $4.47 — se cobra $0.01/GB tanto en el «out» de la AZ emisora como en el «in» de la AZ receptora, así que $2.23 por dirección, $4.47 en total (efectivamente $0.02/GB)
   - D) El tráfico hasta el nivel base de 1.25 Gbps es gratuito; solo se factura el burst por encima de él
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Aproximadamente $4.47 — se cobra $0.01/GB tanto en el «out» de la AZ emisora como en el «in» de la AZ receptora, así que $2.23 por dirección, $4.47 en total (efectivamente $0.02/GB)**

**Explicación:**
`aws pricing get-products` devuelve el usagetype `APN2-DataTransfer-Regional-Bytes` («Regional Data Transfer - in/out/between AZs …») a $0.0100 por GB. La transferencia entre AZ se cobra por los datos que salen de cada AZ, por lo que incluso una transferencia masiva unidireccional dentro de una cuenta paga $0.01/GB «out» en la AZ emisora más $0.01/GB «in» en la AZ receptora — efectivamente $0.02/GB. La ejecución envió 223,376,179,200 bytes (223.4 GB a 9.93 Gbps) en 180 s, por lo que 223.4 × $0.01 = $2.23 por dirección, $4.47 en total. Todos los bytes entre AZ de las pruebas de rendimiento sumaron 12.41 + 24.85 + 223.38 = 260.6 GB, aproximadamente $5.21. Los 18 intervalos de esa ejecución se mantuvieron estables en 9.92–9.94 Gbps sin reducción gradual hacia el nivel base de 1.25 Gbps, pero la factura es por byte independientemente del nivel de ancho de banda (D es incorrecta).

</details>

6. En el Pod predeterminado con `ndots:5` (glibc 2.41), una resolución en frío de `sts.ap-northeast-2.amazonaws.com` (3 puntos) produjo ¿cuántas consultas DNS y respuestas NXDOMAIN en tcpdump?
   - A) 2 consultas, 0 NXDOMAIN — con 3 puntos el nombre se consulta directamente como absoluto
   - B) 10 consultas, 8 NXDOMAIN — A+AAAA para cada uno de los 4 candidatos de la lista de búsqueda devuelve 8 NXDOMAIN antes de que el 5.º candidato (el nombre absoluto) reciba una respuesta A
   - C) 5 consultas, 4 NXDOMAIN — una consulta A por candidato
   - D) 4 consultas, 2 NXDOMAIN
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) 10 consultas, 8 NXDOMAIN — A+AAAA para cada uno de los 4 candidatos de la lista de búsqueda devuelve 8 NXDOMAIN antes de que el 5.º candidato (el nombre absoluto) reciba una respuesta A**

**Explicación:**
El resolv.conf de un Pod de EKS indica `search bench-net.svc.cluster.local svc.cluster.local cluster.local ap-northeast-2.compute.internal` con `options ndots:5`. Primero se prueba con cada uno de los 4 sufijos de búsqueda un nombre con menos de 5 puntos, y glibc envía A y AAAA en paralelo para cada candidato (C es incorrecta). La captura muestra `….bench-net.svc.cluster.local.` → `….svc.cluster.local.` → `….cluster.local.` (los tres NXDomain autoritativos del plugin kubernetes de CoreDNS) → `….ap-northeast-2.compute.internal.` (reenviado al resolver de VPC, NXDomain) → finalmente `sts.ap-northeast-2.amazonaws.com.` respondido con A 10.0.3.84 / 10.0.2.129: 10 consultas, 8 NXDOMAIN, 5 viajes de ida y vuelta secuenciales, 4.37 ms desde el primer paquete, con la respuesta útil llegando en los últimos 0.38 ms. La mediana en caliente de 20 repeticiones seguía siendo 3.78 ms, mientras que la forma con punto final `sts.ap-northeast-2.amazonaws.com.` tomó 2 consultas y una mediana de 0.80 ms. `cache 30` de CoreDNS también almacena en caché los NXDOMAIN, por lo que el coste en caliente son los propios 5 viajes de ida y vuelta secuenciales Pod↔CoreDNS, no las búsquedas upstream. Aritmética derivada: una aplicación que resuelve un nombre externo por solicitud a 1,000 resoluciones/s en todo el cluster envía a CoreDNS 10,000 consultas/s en lugar de 2,000, de las cuales 8,000 se responden NXDOMAIN. 4 consultas / 2 NXDOMAIN es el resultado para `kubernetes.default` (1 punto), no para este nombre (D es incorrecta).

</details>

7. En el mismo Pod con `ndots:5`, el nombre con aspecto de FQDN `kubernetes.default.svc.cluster.local` (sin punto final) también produjo 10 consultas y 8 NXDOMAIN. ¿Por qué recorrió toda la lista de búsqueda?
   - A) El plugin `kubernetes` de CoreDNS responde inmediatamente solo para nombres fuera de la zona `cluster.local`
   - B) glibc siempre trata los nombres que terminan en `svc.cluster.local` como nombres de Service
   - C) El sufijo `.ap-northeast-2.compute.internal` es el primero en la lista de búsqueda y se prueba primero
   - D) El nombre tiene solo 4 puntos, menos que ndots 5, por lo que para glibc es un nombre «corto»: los 4 sufijos de búsqueda se añaden y se prueban antes de enviar el nombre tal cual — un punto final hace que sean 2 consultas
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) El nombre tiene solo 4 puntos, menos que ndots 5, por lo que para glibc es un nombre «corto»: los 4 sufijos de búsqueda se añaden y se prueban antes de enviar el nombre tal cual — un punto final hace que sean 2 consultas**

**Explicación:**
`kubernetes.default.svc.cluster.local` contiene 4 puntos, por debajo de ndots 5. Por lo tanto, glibc prueba primero `….bench-net.svc.cluster.local`, `….svc.cluster.local`, `….cluster.local` y `….ap-northeast-2.compute.internal`, recopilando 8 NXDOMAIN (solo el candidato compute.internal tardó 2.2 ms porque CoreDNS lo reenvió upstream), y únicamente el quinto candidato — el nombre original — recibe la respuesta A: 5.6 ms para el recorrido en frío, mediana en caliente de 3.63 ms. El mismo nombre con un punto final, `kubernetes.default.svc.cluster.local.`, produce 2 consultas y 0 NXDOMAIN — 0.4–0.5 ms en frío, mediana en caliente de 0.46 ms. En el Pod con `ndots:1`, la forma sin punto también produjo 2 consultas (mediana de 0.97 ms). La lista de búsqueda se ejecuta dominio de namespace → `svc.cluster.local` → `cluster.local` → dominio de nodo, por lo que C es incorrecta, y A y B no describen cómo se comportan glibc o CoreDNS. Cuando se incluye un FQDN de Service en un archivo de configuración, escribir el punto final es la opción segura.

</details>

8. En el Pod configurado con `dnsConfig.options` `ndots:1`, los nombres externos bajaron de 10 a 2 consultas, pero el nombre corto dentro del cluster `kubernetes.default` empeoró (6 consultas, 4 NXDOMAIN, mediana de 2.04 ms frente a 1.71 ms con ndots:5). ¿Qué ocurrió?
   - A) Con 1 punto ≥ ndots 1, glibc envió primero `kubernetes.default.` como un nombre absoluto; CoreDNS no tiene zona para él y lo reenvió al resolver de VPC (NXDomain), y solo entonces recorrió la lista de búsqueda para obtener la respuesta en el candidato `svc.cluster.local` — los nombres internos del cluster se filtran al resolver upstream
   - B) ndots:1 deshabilita la caché de CoreDNS
   - C) `kubernetes.default` no se resolvió en absoluto con ndots:1
   - D) glibc envía A y AAAA secuencialmente, duplicando el tiempo
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Con 1 punto ≥ ndots 1, glibc envió primero `kubernetes.default.` como un nombre absoluto; CoreDNS no tiene zona para él y lo reenvió al resolver de VPC (NXDomain), y solo entonces recorrió la lista de búsqueda para obtener la respuesta en el candidato `svc.cluster.local` — los nombres internos del cluster se filtran al resolver upstream**

**Explicación:**
En el Pod con ndots:1, `kubernetes.default` (1 punto) salió primero como el nombre absoluto `kubernetes.default.`; CoreDNS no tiene una zona para él, lo reenvió al resolver de VPC y recibió NXDomain después de 1.6 ms. Luego llegó `kubernetes.default.bench-net.svc.cluster.local` (NXDOMAIN) y finalmente `kubernetes.default.svc.cluster.local`, respondido con 172.20.0.1 — 6 consultas, 4 NXDOMAIN, mediana en caliente de 2.04 ms, peor que las 4 consultas / 2 NXDOMAIN / 1.71 ms con ndots:5 (C es incorrecta). Los nombres externos, en cambio, ganan mucho: `sts.ap-northeast-2.amazonaws.com` y `www.amazon.com` pasaron de 10 a 2 consultas y de una mediana de 3.5–3.8 ms a 0.5–0.9 ms (aproximadamente 4–7× más rápido, 5× menos consultas). glibc envía A y AAAA en paralelo de forma predeterminada (D es incorrecta), y la caché de CoreDNS no tiene nada que ver con el ndots del Pod (B es incorrecta). Si usa ndots:1, escriba los Services dentro del cluster como FQDN con la forma `service.namespace.svc.cluster.local`; la forma con punto final funciona independientemente de ndots — siempre 2 consultas y aproximadamente 0.4–0.8 ms.

</details>

9. Cada tabla de latencia de fortio en la página procede de una repetición con `-r 0.00001` (resolución de histograma de 10 µs). ¿Por qué se descartó la primera ejecución?
   - A) La primera ejecución tuvo una tasa alta de errores
   - B) El valor predeterminado `-r 0.001` de fortio significa buckets de 1 ms, por lo que cada respuesta por debajo de un milisegundo cayó en un único bucket y los percentiles fueron interpolaciones lineales dentro de él (por ejemplo, p50 = 0.5 ms para todo lo que esté por debajo de 1 ms) — los promedios eran válidos, los percentiles no tenían sentido
   - C) Con la resolución predeterminada fortio no calcula p99.9
   - D) La primera ejecución se había realizado accidentalmente sin keepalive
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El valor predeterminado `-r 0.001` de fortio significa buckets de 1 ms, por lo que cada respuesta por debajo de un milisegundo cayó en un único bucket y los percentiles fueron interpolaciones lineales dentro de él (por ejemplo, p50 = 0.5 ms para todo lo que esté por debajo de 1 ms) — los promedios eran válidos, los percentiles no tenían sentido**

**Explicación:**
Los valores p50 reales de este benchmark están todos por debajo de 1 ms — 0.259–0.704 ms para HTTP con keepalive. Con el valor predeterminado `-r 0.001` de fortio, el bucket del histograma es de 1 ms, por lo que todas esas muestras se acumulan en el primer bucket y los percentiles se interpolan linealmente dentro de él, produciendo valores falsos como p50 = 0.5 ms independientemente de la ruta. Los promedios eran válidos, pero los percentiles se descartaron y cada ejecución de fortio se repitió con `-r 0.00001` (buckets de 10 µs). Cada ejecución tuvo 0 errores (A es incorrecta) y la configuración de solicitud/respuesta no cambió (D es incorrecta). La lección: compruebe la resolución del histograma de su herramienta antes de medir una red por debajo de un milisegundo.

</details>

10. ¿Qué afirmación describe correctamente por qué la página NO midió el salto de ClusterIP (iptables de kube-proxy) ni `trafficDistribution: PreferClose`?
   - A) fortio no puede dirigirse a un nombre DNS de Service
   - B) kube-proxy estaba en modo IPVS, por lo que no había un salto de iptables que medir
   - C) El webhook de aws-load-balancer-controller del cluster (`mservice.elbv2.k8s.aws`, `failurePolicy: Fail`) intercepta cada CREATE de Service, pero los Pods del controller llevaban 48 días en CrashLoopBackOff esperando un CRD `ListenerSet` de Gateway API, por lo que el webhook tenía cero endpoints y no se podía crear ningún Service en ninguna parte del cluster — el webhook no se omitió y el fixture usó solo IP de Pod
   - D) Se midió, pero se omitió de las tablas porque coincidía con los números de IP de Pod
<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El webhook de aws-load-balancer-controller del cluster (`mservice.elbv2.k8s.aws`, `failurePolicy: Fail`) intercepta cada CREATE de Service, pero los Pods del controller llevaban 48 días en CrashLoopBackOff esperando un CRD `ListenerSet` de Gateway API, por lo que el webhook tenía cero endpoints y no se podía crear ningún Service en ninguna parte del cluster — el webhook no se omitió y el fixture usó solo IP de Pod**

**Explicación:**
Cada `kubectl apply` de un Service en el namespace de benchmark fue rechazado con `Internal error occurred: failed calling webhook "mservice.elbv2.k8s.aws": … no endpoints available for service "aws-load-balancer-webhook-service"`. Un diagnóstico de solo lectura encontró aws-load-balancer-controller v3.2.1 (kube-system, 2 réplicas) en CrashLoopBackOff durante 48 días con 9,250 reinicios: cada contenedor registraba repetidamente `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"` y salía tras aproximadamente 2m18s por un timeout de sincronización de caché. Su `MutatingWebhookConfiguration` `aws-load-balancer-webhook` coincide con CREATE en cada Service de todo el cluster (`namespaceSelector: {}`) con `failurePolicy: Fail`, por lo que con cero endpoints listos no se puede crear ningún Service en ningún namespace. En lugar de omitir el webhook o reparar el controller, el fixture usó solo IP de Pod, razón por la que la página no tiene números para el salto de ClusterIP ni para `PreferClose` (beta en Kubernetes 1.31, GA en 1.33) (D es incorrecta). kube-proxy estaba en `mode: "iptables"` (B es incorrecta). Tampoco se recopilaron los contadores de concesión de ENA (`ethtool -S`, que necesita un Pod hostNetwork); y cada celda es n = 1 de un único día, por lo que las cifras son referencias de orden de magnitud, no SLA.

</details>

---

[Volver a los materiales de aprendizaje](../../networking/06-pod-network-benchmark.md) | [Volver al inicio de Networking](../../networking/README.md)
