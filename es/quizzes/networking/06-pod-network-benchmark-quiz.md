# Cuestionario sobre pruebas de rendimiento de la red de Pods

Estas preguntas se refieren al informe del 2 de septiembre de 2026; no describen garantías universales de rendimiento ni de facturación.

1. Según la medición con `ping -c 200 -i 0.05`, ¿cómo cambió el RTT promedio de Pod a Pod al pasar del mismo nodo a otro nodo de la misma AZ y, después, a otra AZ?
   - A) 0.040 ms → 0.544 ms → 0.339 ms: entre AZ fue más rápido que dentro de la misma AZ
   - B) Las tres rutas se mantuvieron dentro del margen de ruido, alrededor de 0.3 ms
   - C) En esta ejecución, 0.040 ms → 0.339 ms → 0.544 ms: unos +0.30 ms y +0.21 ms entre ubicaciones adyacentes
   - D) 0.040 ms → 0.339 ms → 5.4 ms: cruzar el límite de la AZ elevó el RTT a milisegundos enteros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) En esta ejecución, 0.040 ms → 0.339 ms → 0.544 ms: unos +0.30 ms y +0.21 ms entre ubicaciones adyacentes**

**Explicación:**
Los promedios de ping informados se calcularon a partir de 200 sondas por ruta, sin pérdidas (0/200). La diferencia entre el promedio de la ruta entre AZ y el de la ruta dentro de la misma AZ es 0.205 ms, que se redondea a 0.21 ms; entre AZ y la ruta dentro del mismo nodo, la diferencia es 0.504 ms. El p50 de HTTP fue 0.259 → 0.461 → 0.704 ms. Restar una mediana de HTTP a un promedio de ping no permite aislar el coste del espacio de usuario. La cifra de 5.4 ms corresponde al RTT de TCP con carga; no se midió dónde se formó la cola. El aumento de +1.29 ms del informe separado de Istio es una diferencia de p50 para un escenario completo, medida con otro hardware y otra carga de trabajo; no es el coste medido de un solo proxy que pueda sumarse a estos valores.

</details>

2. Un único flujo TCP de iperf3 (`-P 1`) se detuvo en 4.96 Gbps tanto en la ruta dentro de la misma AZ como en la ruta entre AZ, mientras que 8 flujos (`-P 8`) alcanzaron 9.94 Gbps en ambas. ¿Cuál es la mejor explicación de esas dos cifras?
   - A) 4.96 Gbps indica que se saturó un núcleo de CPU del cliente; los 8 flujos son más rápidos porque usan más núcleos
   - B) El resultado de 4.96 Gbps concuerda con el límite habitual de 5 Gbps por flujo único; los flujos paralelos se acercaron al pico de ráfaga de 10 Gbps de esta m5.xlarge
   - C) 4.96 Gbps es el ancho de banda base de la m5.xlarge, y los 8 flujos gastaron créditos de ráfaga para alcanzar el pico
   - D) Las tramas jumbo (MTU 9001) no estaban activas para el flujo único

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El resultado de 4.96 Gbps concuerda con el límite habitual de 5 Gbps por flujo único; los flujos paralelos se acercaron al pico de ráfaga de 10 Gbps de esta m5.xlarge**

**Explicación:**
El ancho de banda base de la m5.xlarge es 1.25 Gbps y su pico de ráfaga de mejor esfuerzo es 10 Gbps; las ejecuciones de 20 s no demuestran que ese pico pueda mantenerse. La CPU del proceso cliente fue del 19.5 % / 20.0 % en las rutas entre nodos, frente al 99.8 % en la prueba de flujo único de 29.97 Gbps dentro del mismo nodo. Estos valores respaldan una interpretación basada en el límite de ancho de banda, pero no descartan todos los posibles cuellos de botella del host. Las retransmisiones aumentaron de 4 / 2 a 5,874 / 5,979; no se recopilaron contadores de ENA, por lo que no se ha demostrado que hubiera limitación de tráfico. AWS también documenta hasta 10 Gbps dentro de un grupo de ubicación en clúster y hasta 25 Gbps para flujos ENA Express elegibles dentro de la misma AZ: 5 Gbps no es un límite universal.

</details>

3. ¿Cómo puede diferir el rendimiento HTTP medido con un pool fijo aunque las dos pruebas de iperf3 con ocho flujos alcanzaran 9.94 Gbps?
   - A) El enlace entre AZ reduce a la mitad el ancho de banda del tráfico de solicitud y respuesta
   - B) Los errores y reintentos aumentaron en la ruta entre AZ
   - C) El nodo que alojaba srv-b tenía una CPU más lenta que el nodo de srv-a
   - D) Un bucle cerrado estable con unas 16 solicitudes en curso concuerda con rendimiento ≈ 16 / latencia media; las tasas observadas difieren un 33.5 %, sin que esto demuestre una penalización universal de las AZ

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Un bucle cerrado estable con unas 16 solicitudes en curso concuerda con rendimiento ≈ 16 / latencia media; las tasas observadas difieren un 33.5 %, sin que esto demuestre una penalización universal de las AZ**

**Explicación:**
Los promedios informados fueron 0.355 / 0.415 / 0.624 ms. Dividir 16 por esas duraciones da 45,070 / 38,554 / 25,641 solicitudes por segundo, valores cercanos a los 44,991 / 38,507 / 25,602 informados. (38,507 − 25,602) / 38,507 ≈ 33.5 %. La ley de Little describe la concurrencia, el rendimiento y el tiempo medio bajo las condiciones de estado estable indicadas; no identifica una causa exclusiva de la demora. El informe registra cero errores y el mismo tipo de instancia para ambos servidores, datos que no respaldan las opciones B o C. La contención de CPU podría contribuir a una cola más lenta dentro del mismo nodo, pero no se confirmó mediante perfiles.

</details>

4. Con los mismos 100 qps / 4 conexiones, ¿cómo cambió el p50 de HTTP entre AZ al cambiar a `-keepalive=false` (una nueva conexión TCP por solicitud)?
   - A) 0.704 ms → 1.517 ms (+0.813 ms), más del doble; establecer la conexión añade trabajo, pero este experimento no aísla cada componente
   - B) No cambió; el kernel reutiliza las conexiones de todos modos
   - C) 0.704 ms → 0.813 ms, un aumento pequeño
   - D) El p50 no cambió; solo empeoró el p99

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) 0.704 ms → 1.517 ms (+0.813 ms), más del doble; establecer la conexión añade trabajo, pero este experimento no aísla cada componente**

**Explicación:**
Las medianas con keepalive desactivado fueron 0.664 / 1.079 / 1.517 ms, con aumentos de 0.405 / 0.618 / 0.813 ms. La última cifra es el aumento, no la nueva mediana, por lo que C es incorrecta. Establecer la conexión contribuye al coste, pero restar un RTT de ping no mide por separado un coste fijo de 0.3 ms por socket. Conviene probar la reutilización de conexiones en la aplicación. No se midió TIME_WAIT; su valor depende del extremo que cierra la conexión y del comportamiento de terminación.

</details>

5. ¿Cuál es la estimación del informe para 223,376,179,200 bytes de carga útil si se usa su conversión explícita a GB decimales y se aplican $0.01/GB en cada extremo EC2?
   - A) $0 (el tráfico dentro de una región es gratuito)
   - B) $2.23 ($0.01 por GB, cobrado una vez)
   - C) Unos $4.47 según el modelo del informe basado en GB decimales de carga útil, aplicando $0.01/GB tanto al extremo emisor como al receptor; no se verificó una factura real
   - D) El tráfico hasta el nivel base de 1.25 Gbps es gratuito; solo se factura la ráfaga que lo supera

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Unos $4.47 según el modelo del informe basado en GB decimales de carga útil, aplicando $0.01/GB tanto al extremo emisor como al receptor; no se verificó una factura real**

**Explicación:**
La carga útil exacta fue de 223,376,179,200 bytes. El modelo histórico divide entre 10⁹ y multiplica por $0.01 dos veces, lo que da unos $4.47; las tres ejecuciones de iperf3 entre AZ suman 260,633,264,128 bytes y unos $5.21 con el mismo modelo. Una dirección de transferencia puede generar cargos en ambos extremos. Los precios públicos de `get-products` no equivalen a la factura pagada de una cuenta, y esta auditoría no demostró que las unidades facturadas de EC2 sean iguales a los GB decimales de carga útil. Concilie las unidades de medición de CUR, la sobrecarga del protocolo, ambos extremos y los descuentos aplicables. Los 18 intervalos a 9.92–9.94 Gbps no crean un nivel de transferencia gratuito hasta el ancho de banda base.

</details>

6. En el Pod predeterminado con `ndots:5` (glibc 2.41), ¿cuántas consultas DNS y respuestas NXDOMAIN produjo tcpdump durante una resolución en frío de `sts.ap-northeast-2.amazonaws.com` (3 puntos)?
   - A) 2 consultas, 0 NXDOMAIN: al tener 3 puntos, el nombre se consulta directamente como absoluto
   - B) En esta resolución registrada, 10 consultas y 8 NXDOMAIN: fallaron cuatro candidatos de búsqueda, cada uno con A+AAAA, y después tuvo éxito el nombre absoluto
   - C) 5 consultas, 4 NXDOMAIN: una consulta A por candidato
   - D) 4 consultas, 2 NXDOMAIN

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) En esta resolución registrada, 10 consultas y 8 NXDOMAIN: fallaron cuatro candidatos de búsqueda, cada uno con A+AAAA, y después tuvo éxito el nombre absoluto**

**Explicación:**
Este Pod tenía la lista de búsqueda registrada con cuatro entradas y el comportamiento AF_UNSPEC de glibc. Fallaron los cuatro primeros candidatos, que generaron ocho NXDOMAIN, y luego se devolvieron los registros A 10.0.3.84 / 10.0.2.129 para el nombre absoluto. La línea de tiempo de 4.37 ms termina con esa respuesta A; el tiempo de finalización de AAAA no aparece en la tabla. Las medianas en caliente informadas fueron 3.78 ms frente a 0.80 ms con un punto final. `cache 30` es el TTL máximo, no una prueba de que no haya consultas upstream. Con el mismo patrón de respuestas, 1,000 resoluciones/s significarían 10,000 consultas/s y 8,000 NXDOMAIN; eso no significa que el 80 % de la CPU de CoreDNS se consuma en ellas. Otros nombres pueden tener éxito antes, como ocurrió con `kubernetes.default`, que necesitó cuatro consultas.

</details>

7. En el mismo Pod con `ndots:5`, el nombre que parece un FQDN `kubernetes.default.svc.cluster.local` (sin punto final) también produjo 10 consultas y 8 NXDOMAIN. ¿Por qué recorrió toda la lista de búsqueda?
   - A) El plugin `kubernetes` de CoreDNS responde de inmediato solo para nombres fuera de la zona `cluster.local`
   - B) glibc siempre trata los nombres que terminan en `svc.cluster.local` como nombres de Service
   - C) El sufijo `.ap-northeast-2.compute.internal` aparece primero en la lista de búsqueda y se prueba antes que los demás
   - D) Tiene cuatro puntos, menos que el umbral ndots 5, así que este resolver probó primero los candidatos de búsqueda; fallaron antes de que el nombre original tuviera éxito, mientras que el punto final evita la expansión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Tiene cuatro puntos, menos que el umbral ndots 5, así que este resolver probó primero los candidatos de búsqueda; fallaron antes de que el nombre original tuviera éxito, mientras que el punto final evita la expansión**

**Explicación:**
El resolver cuenta los puntos; no reconoce que el sufijo de un Service de Kubernetes indique que debe omitir la búsqueda. En esta muestra fallaron los cuatro candidatos expandidos. El informe da 2.2 ms para el candidato reenviado, 5.6 ms para todo ese recorrido en la red, 3.63 ms de mediana en caliente sin el punto y 0.46 ms con él; la primera llamada del proceso, informada por separado, duró 7.40 ms. Un punto final convierte un nombre DNS en absoluto, pero incluirlo en una URL de aplicación también requiere compatibilidad con Host/SNI, el certificado y la firma. No dé por hecho que es seguro con cualquier configuración de endpoint HTTPS o del SDK de AWS.

</details>

8. En el Pod configurado con `dnsConfig.options` `ndots:1`, las consultas para nombres externos bajaron de 10 a 2, pero empeoró el resultado del nombre corto interno `kubernetes.default` (6 consultas, 4 NXDOMAIN, mediana de 2.04 ms frente a 1.71 ms con ndots:5). ¿Qué ocurrió?
   - A) Este resolver probó primero el nombre con un punto como absoluto con ndots:1 y, tras recibir NXDOMAIN, continuó con la lista de búsqueda, por lo que envió upstream un nombre con apariencia interna
   - B) ndots:1 deshabilita la caché de CoreDNS
   - C) `kubernetes.default` no se resolvió con ndots:1
   - D) glibc envía A y AAAA de forma secuencial, lo que duplica el tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Este resolver probó primero el nombre con un punto como absoluto con ndots:1 y, tras recibir NXDOMAIN, continuó con la lista de búsqueda, por lo que envió upstream un nombre con apariencia interna**

**Explicación:**
El orden observado fue `kubernetes.default.` (reenviado, con respuesta NXDOMAIN tras los 1.6 ms informados), luego `kubernetes.default.bench-net.svc.cluster.local` (NXDOMAIN) y, por último, `kubernetes.default.svc.cluster.local` (172.20.0.1). Esto da seis consultas y cuatro NXDOMAIN frente a cuatro y dos con ndots:5. `ndots` cambia el orden que sigue el cliente; no determina si la caché de CoreDNS está habilitada. Esta resolución de glibc usó pares A/AAAA, pero las opciones de familia de direcciones y del resolver pueden cambiar ese comportamiento. Los nombres de Service completos reducen los intentos absolutos fallidos con ndots:1. Un punto final omite la búsqueda, pero no garantiza un número concreto de consultas o una latencia determinada para todos los resolvers y fallos.

</details>

9. ¿Cuál es la interpretación correcta de la repetición histórica de Fortio con `-r 0.00001`?
   - A) La primera ejecución tuvo una tasa alta de errores
   - B) La resolución de 1 ms del bucket inferior predeterminado era demasiado gruesa para la comparación deseada; el informe repitió la prueba con una resolución de 10 µs, pero un único bucket no implica universalmente p50 = 0.5 ms
   - C) Con la resolución predeterminada, Fortio no calcula p99.9
   - D) La primera ejecución se hizo accidentalmente sin keepalive

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La resolución de 1 ms del bucket inferior predeterminado era demasiado gruesa para la comparación deseada; el informe repitió la prueba con una resolución de 10 µs, pero un único bucket no implica universalmente p50 = 0.5 ms**

**Explicación:**
En Fortio 1.69.5, `-r` se expresa en segundos: 0.001 equivale a 1 ms y 0.00001 a 10 µs para los buckets más pequeños. Los buckets mayores pueden ser más amplios. Los percentiles se interpolan dentro de los límites del bucket, y los valores mínimo y máximo observados afectan al primer y al último bucket. Por tanto, era incorrecta la afirmación original de que todas las respuestas inferiores a 1 ms implican p50 = 0.5 ms. Las medianas con keepalive, de 0.259–0.704 ms, son inferiores a 1 ms, pero algunas colas y medianas con conexiones nuevas superan 1 ms. Conserve el historial de repeticiones del informe, los promedios, los histogramas completos y los recuentos de errores en vez de calificar la interpolación como intrínsecamente carente de sentido.

</details>

10. ¿Por qué omitió el benchmark histórico de la aplicación una comparación con Service y distribución de tráfico?
   - A) Fortio no puede dirigirse al DNS de un Service
   - B) kube-proxy estaba en modo IPVS, así que no había un salto de iptables que medir
   - C) Según el informe, un webhook de admisión de LBC que fallaba rechazó las solicitudes de creación de Service del benchmark; las pruebas de la aplicación usaron IP de Pod sin omitir el webhook
   - D) Se midió, pero se omitió de las tablas porque coincidía con los resultados de IP de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Según el informe, un webhook de admisión de LBC que fallaba rechazó las solicitudes de creación de Service del benchmark; las pruebas de la aplicación usaron IP de Pod sin omitir el webhook**

**Explicación:**
El diagnóstico histórico informa de LBC v3.2.1, dos réplicas, 48 días en CrashLoopBackOff, 9,250 reinicios y `no matches for kind "ListenerSet" in version "gateway.networking.k8s.io/v1"`, seguido de un timeout de sincronización de caché tras unos 2m18s. Estos son detalles atribuidos al incidente; esta auditoría no recuperó de forma independiente los registros originales ni inspeccionó un clúster activo. Un webhook con `failurePolicy: Fail` rechaza las solicitudes que coinciden con sus reglas, selectores y condiciones; `namespaceSelector: {}` por sí solo no demuestra que intercepte cada CREATE de Service. El benchmark de la aplicación omitió los Services, mientras que DNS usó el `kube-dns` preexistente. `PreferClose` es ahora el alias obsoleto de `PreferSameZone`; aquí no se probó ninguno de los dos. Tampoco se recopilaron contadores de ENA ni se hicieron repeticiones independientes.

</details>

---

[Volver a los materiales de aprendizaje](../../networking/06-pod-network-benchmark.md) | [Volver al inicio de Networking](../../networking/README.md)
