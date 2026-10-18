# Cuestionario sobre la pila de red del kernel

Este cuestionario evalúa su comprensión de las rutas de entrada de socket/VFS, los búferes y las ventanas TCP, las observaciones de colas que dependen del estado, los puntos de enlace y el enrutamiento entre Pods.

## Preguntas de opción múltiple

1. ¿Qué componente pone en cola los paquetes salientes antes de la NIC y muestra sus descartes mediante `tc -s qdisc`?
   - A) La capa física de la NIC
   - B) qdisc: un descarte dentro del nodo, visible como `dropped` en `tc -s qdisc`
   - C) La red de VPC
   - D) El búfer de socket de la aplicación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) qdisc: un descarte dentro del nodo, visible como `dropped` en `tc -s qdisc`**

**Explicación:**
Un qdisc puede poner en cola y planificar paquetes salientes, y descartarlos por límites de cola o por la gestión activa de colas. Un contador `dropped` que aumenta atribuye los descartes a ese qdisc, no a todas las pérdidas de la ruta. Correlacione el intervalo y el tráfico afectados con los datos de la interfaz, el controlador, la pila, y los extremos remotos. `overlimits` puede indicar limitación del tráfico sin un descarte; no equivale a `dropped`.
</details>

2. ¿Qué distinción entre modos de XDP es importante al hablar del rendimiento de los descartes tempranos de paquetes?
   - A) Se ejecuta en hardware, no como módulo del kernel
   - B) XDP nativo o del controlador se ejecuta antes de asignar sk_buff; XDP genérico ya utiliza sk_buff
   - C) Se compila mediante JIT
   - D) No necesita consultar conntrack

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) XDP nativo o del controlador se ejecuta antes de asignar sk_buff; XDP genérico ya utiliza sk_buff**

**Explicación:**
La ventaja del descarte temprano depende del modo. Los mapas de BPF pueden mantener estado y el rendimiento depende del kernel, el programa, el controlador y el hardware; no existe una garantía universal de cuál es la ruta más rápida.
</details>

3. Con mucho tráfico entrante, una sola CPU está al 100 % mientras las demás están inactivas. ¿Qué posible causa y mecanismos relacionados debería investigar?
   - A) Una cola qdisc insuficiente: aumente su longitud
   - B) Procesamiento de recepción concentrado: inspeccione la distribución de colas RSS e IRQ, la asignación de tráfico por software de RPS y la localidad de caché de RFS
   - C) Un búfer de socket insuficiente: aumente `tcp_rmem`
   - D) Una incompatibilidad del control de congestión TCP: cambie a bbr

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Procesamiento de recepción concentrado: inspeccione la distribución de colas RSS e IRQ, la asignación de tráfico por software de RPS y la localidad de caché de RFS**

**Explicación:**
RSS asigna flujos a colas de recepción mediante hashes; la afinidad de IRQ influye en qué CPU los procesa. RPS distribuye por software el procesamiento posterior de recepción y RFS intenta acercarlo a la aplicación consumidora. No todos estos mecanismos trasladan las interrupciones de hardware, y un solo flujo puede permanecer en una cola. Antes de atribuir una causa, inspeccione `/proc/interrupts` y el `%soft` de cada CPU con `mpstat -P ALL`, además del uso de CPU de la aplicación.
</details>

4. ¿Cómo puede NAPI, cuando se usa con interrupciones normales, reducir la sobrecarga por paquete?
   - A) El kernel aumenta automáticamente la frecuencia de la CPU
   - B) El controlador enmascara la interrupción de la cola pertinente y programa un sondeo acotado, distribuyendo el trabajo entre un lote
   - C) Comprime los paquetes antes de procesarlos
   - D) GRO se habilita automáticamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El controlador enmascara la interrupción de la cola pertinente y programa un sondeo acotado, distribuyendo el trabajo entre un lote**

**Explicación:**
El procesamiento por lotes puede repartir la sobrecarga de interrupciones y procesamiento. El controlador enmascara la interrupción correspondiente mientras se programa el sondeo y puede volver a habilitarla cuando este termina; no desactiva todas las interrupciones de la CPU. El sondeo tiene un presupuesto de trabajo, y una sobrecarga aún puede aumentar la latencia o los descartes. El sondeo activo y NAPI con subprocesos usan otras formas de ejecución.
</details>

5. ¿Por qué el tráfico entre Pods del mismo nodo alcanzó 29.97 Gbps con un solo flujo cuando la CPU era el cuello de botella?
   - A) Hay una red dedicada de alta velocidad dentro del nodo
   - B) En la ruta veth/enrutada ordinaria ilustrada para el mismo nodo, los paquetes pueden permanecer en la memoria del kernel sin atravesar la NIC física
   - C) El kernel comprime los paquetes
   - D) El tráfico del mismo nodo no usa TCP

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) En la ruta veth/enrutada ordinaria ilustrada para el mismo nodo, los paquetes pueden permanecer en la memoria del kernel sin atravesar la NIC física**

**Explicación:**
Los dispositivos virtuales también requieren procesamiento del controlador. Distintos CNI, SR-IOV, superposiciones o desvíos por servicios o políticas pueden cambiar la ruta, así que aplique esta afirmación a la configuración real.
</details>

6. Los paquetes pequeños del protocolo de enlace pasan, pero los paquetes IPv4 más grandes con DF habilitado se descartan en un salto de MTU menor y el ICMP de respuesta está bloqueado. ¿Qué mecanismo explica el bloqueo?
   - A) Agotamiento de conntrack
   - B) Fallo de PMTUD: se bloquea el ICMP que informa de la MTU de la ruta, por lo que solo se descartan los paquetes grandes
   - C) Una incompatibilidad del control de congestión TCP
   - D) Un búfer de recepción de socket insuficiente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Fallo de PMTUD: se bloquea el ICMP que informa de la MTU de la ruta, por lo que solo se descartan los paquetes grandes**

**Explicación:**
Con DF habilitado, un enrutador IPv4 no puede fragmentar el paquete demasiado grande y normalmente devuelve el mensaje ICMP «fragmentation needed». Bloquear esta respuesta puede interrumpir PMTUD y crear un agujero negro. Los enrutadores IPv6 no fragmentan y utilizan ICMPv6 «Packet Too Big». Sin los datos que aporta la pregunta, un protocolo de enlace que funciona seguido de un bloqueo es solo una pista, no una prueba; las sondas también podrían permitir la recuperación.
</details>

7. ¿Cuál es el orden recomendado para diagnosticar un problema de red?
   - A) De arriba abajo: desde la aplicación hasta la NIC, en ese orden
   - B) Empiece por los contadores de descartes: `insert_failed` en `conntrack -S`, `dropped` en `tc -s qdisc` y descartes de NIC en `ethtool -S`
   - C) Capture siempre paquetes primero con `tcpdump`
   - D) Empiece por la utilización de CPU

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Empiece por los contadores de descartes: `insert_failed` en `conntrack -S`, `dropped` en `tc -s qdisc` y descartes de NIC en `ethtool -S`**

**Explicación:**
Estos contadores señalan aspectos que investigar, no ofrecen un diagnóstico completo. Correlacione los cambios con el flujo y el intervalo afectados; en conntrack, inspeccione también el recuento y el máximo, así como los registros del kernel, porque `insert_failed` no solo indica agotamiento. Los contadores agregados pueden incluir tráfico ajeno al caso. Que los contadores locales no cambien no descarta descartes remotos, fallos de autenticación ni de la aplicación. Siga los síntomas con comprobaciones como RTT y cwnd en `ss -tin`, errores devueltos y datos del resto de la ruta.
</details>

8. ¿Qué comparación entre `cubic` y `bbr` se puede justificar sin una prueba comparativa de la carga de trabajo?
   - A) cubic es para UDP y bbr para TCP
   - B) cubic ajusta la ventana de congestión tras eventos como pérdidas o ECN; bbr usa estimaciones de la tasa de entrega y RTT, y los resultados dependen de la implementación y la ruta
   - C) bbr siempre es más rápido que cubic
   - D) cubic se eliminó en el kernel 6.x

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) cubic ajusta la ventana de congestión tras eventos como pérdidas o ECN; bbr usa estimaciones de la tasa de entrega y RTT, y los resultados dependen de la implementación y la ruta**

**Explicación:**
Los modelos describen distintos comportamientos de control; no garantizan un orden de rendimiento. BBR también tiene un comportamiento ante pérdidas y recuperación, y ninguno de los algoritmos elimina las limitaciones de la ventana de recepción ni de la aplicación. Antes de interpretar una comparación, identifique la implementación del kernel, el algoritmo activo, el RTT/cwnd, la carga de trabajo y la ruta.
</details>

9. Un proceso usa tanto `write(fd, ...)` como `send(fd, ...)` en un socket TCP. ¿Qué descripción corresponde al puente entre socket y VFS de Linux?
   - A) Ambas llamadas deben pasar por un sistema de archivos de disco antes de entrar en TCP
   - B) `send()` siempre llama a `vfs_write()` y el socket es un archivo de disco
   - C) El FD apunta a un `struct file` vinculado a un socket; `write()` usa las operaciones de archivo de socket de VFS, mientras que `send()` sigue una ruta de entrada específica de sockets
   - D) Un socket no tiene una entrada en la tabla de descriptores de archivo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) El FD apunta a un `struct file` vinculado a un socket; `write()` usa las operaciones de archivo de socket de VFS, mientras que `send()` sigue una ruta de entrada específica de sockets**

**Explicación:**
En el ejemplo de Linux con versión fija, `file->private_data` apunta a `struct socket`. La llamada VFS `write()` se distribuye mediante `socket_file_ops.write_iter` a `sock_write_iter`; `send()` obtiene el socket a partir del FD por su propia ruta de llamada al sistema. Ambas llegan a las operaciones de socket/protocolo. Compartir la abstracción de archivo no implica E/S de disco, y que el envío termine correctamente no demuestra que la aplicación homóloga haya consumido los datos. Consulte el [puente VFS](../../kernel/02-network-stack.md#socket-vfs-bridge).
</details>

10. Una conexión TCP establecida tiene datos útiles sin leer y `ss -m` muestra más memoria de recepción que `Recv-Q`. ¿Qué explicación es válida?
   - A) La contabilidad de memoria incluye la sobrecarga de asignación y, posiblemente, datos fuera de orden; `Recv-Q` cuenta los bytes del flujo ordenados que aún no se han leído
   - B) Cada `sk_buff` es todo el búfer de recepción del socket
   - C) La memoria de recepción, `Recv-Q`, `rwnd` y `cwnd` siempre son iguales
   - D) Cada skb debe representar exactamente un paquete transmitido por la red

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) La contabilidad de memoria incluye la sobrecarga de asignación y, posiblemente, datos fuera de orden; `Recv-Q` cuenta los bytes del flujo ordenados que aún no se han leído**

**Explicación:**
Un skb describe datos y metadatos de paquetes; puede apuntar a fragmentos, clonarse o representar datos agregados o segmentados. Los presupuestos de memoria del socket, los datos útiles de la aplicación, la ventana anunciada por el receptor y la ventana de congestión del emisor representan cantidades o límites distintos. Un valor de memoria de `ss -m` no se puede sustituir por `rwnd`, y aumentar un búfer local no aumenta directamente `cwnd`. Consulte [observaciones de colas](../../kernel/02-network-stack.md#ss-tcp-queues).
</details>

11. `ss` muestra `Recv-Q=3, Send-Q=128` para `LISTEN` y `Recv-Q=4096, Send-Q=8192` para `ESTABLISHED`. ¿Qué significan estos valores?
   - A) Ambas filas cuentan los paquetes que hay en ese momento en el anillo de la NIC
   - B) El listener ha recibido 3 bytes y enviado 128 bytes
   - C) El listener tiene 3 solicitudes SYN incompletas, y se sabe que los 8192 bytes establecidos están en la red
   - D) El listener tiene 3 conexiones que esperan `accept` y una cola máxima de 128; el socket establecido tiene 4096 bytes ordenados sin leer y 8192 bytes escritos aún no reconocidos acumulativamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) El listener tiene 3 conexiones que esperan `accept` y una cola máxima de 128; el socket establecido tiene 4096 bytes ordenados sin leer y 8192 bytes escritos aún no reconocidos acumulativamente**

**Explicación:**
Para un listener, las columnas cuentan conexiones y no indican la ocupación de la cola SYN. En TCP establecido, cuentan bytes del flujo; `Send-Q` puede incluir bytes aún no enviados y bytes enviados pero no reconocidos. No son presupuestos de memoria de socket configurados ni demuestran que se hayan perdido paquetes. Consulte [colas TCP según el estado](../../kernel/02-network-stack.md#ss-tcp-queues).
</details>

12. Una aplicación establece explícitamente `SO_RCVBUF` y `SO_SNDBUF`. Más tarde, un operador solo aumenta `tcp_rmem[2]` y `tcp_wmem[2]`. ¿Qué se puede esperar?
   - A) Todos los sockets existentes asignan de inmediato ambos máximos nuevos
   - B) La configuración explícita del socket permanece bloqueada frente al ajuste automático normal en la dirección correspondiente
   - C) Linux duplica `tcp_rmem[2]` y lo anuncia directamente como `rwnd`
   - D) Cambiar la política del búfer de envío aumenta directamente la ventana de recepción del par

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) La configuración explícita del socket permanece bloqueada frente al ajuste automático normal en la dirección correspondiente**

**Explicación:**
Las opciones del socket establecen `SOCK_RCVBUF_LOCK` y `SOCK_SNDBUF_LOCK`; son indicadores de política, no mutexes. Las solicitudes normales para estas opciones están sujetas a `net.core.rmem_max`/`wmem_max`. Linux normalmente duplica la solicitud aceptada para llevar la contabilidad y devuelve ese valor mediante `getsockopt()`, pero eso no significa que toda esa memoria esté asignada o pueda usarse como datos útiles. Los máximos de ajuste automático de sysctl y los límites de opciones explícitas son controles distintos. Consulte la [política de búferes TCP](../../kernel/02-network-stack.md#tcp-buffer-policy).
</details>

13. Una ruta hipotética ofrece 1 Gbit/s con un RTT de 40 ms. ¿Qué cálculo de BDP y conclusión son válidos?
   - A) 40 MB; establezca cada búfer de envío de socket exactamente en ese valor
   - B) 5 bytes; se pueden multiplicar directamente los milisegundos de latencia por bits por segundo
   - C) 5,000,000 bytes (aproximadamente 4.77 MiB); compare esta escala con las ventanas expresadas en bytes, el avance de la aplicación y la sobrecarga de memoria
   - D) 5 MB; por tanto, queda demostrado que todos los hosts tienen un cuello de botella de búfer

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) 5,000,000 bytes (aproximadamente 4.77 MiB); compare esta escala con las ventanas expresadas en bytes, el avance de la aplicación y la sobrecarga de memoria**

**Explicación:**
`1,000,000,000 bit/s × 0.040 s ÷ 8 bit/byte = 5,000,000 bytes`. El cálculo usa RTT y estima la carga útil en tránsito bajo un modelo idealizado de estado estable. `ss` normalmente muestra `cwnd` en segmentos, así que use MSS para compararlo en bytes. Siguen siendo relevantes las limitaciones de la ventana de recepción, el pacing, las pérdidas, la CPU y el comportamiento de la aplicación; BDP no es una instrucción de ajuste universal. Consulte el [razonamiento sobre BDP](../../kernel/02-network-stack.md#tcp-bdp-reasoning) y el [laboratorio de búferes TCP](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab).
</details>

14. Una interfaz tiene una MTU de IP de 1500, pero una captura en el host muestra una unidad TCP de más de 1500 bytes con una suma de comprobación de transmisión aparentemente incorrecta. ¿Qué debería concluir primero?
   - A) Compruebe el punto de captura y las descargas de trabajo; sin opciones, la carga útil TCP de IPv4 cabe en 1460 bytes, pero las unidades GSO/GRO del host y las sumas de comprobación sin finalizar pueden diferir de los paquetes en la red
   - B) MSS de TCP debe ser de 1500 bytes porque incluye el encabezado IP
   - C) El enrutador IPv6 remoto debe haber fragmentado el paquete
   - D) La captura demuestra corrupción en la red e invalida PMTUD

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Compruebe el punto de captura y las descargas de trabajo; sin opciones, la carga útil TCP de IPv4 cabe en 1460 bytes, pero las unidades GSO/GRO del host y las sumas de comprobación sin finalizar pueden diferir de los paquetes en la red**

**Explicación:**
MSS no incluye los encabezados IP/TCP y PMTU depende de la ruta completa. Sin opciones, `1500 - 20 - 20 = 1460` para IPv4; el encabezado base de IPv6 deja 1440. Las descargas de trabajo pueden aplazar la segmentación o el cálculo de la suma de comprobación, o combinar paquetes recibidos. Una captura en el host por sí sola no demuestra el tamaño ni la corrupción de los paquetes en la red. Continúe con el [laboratorio de MTU/MSS](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab).
</details>
