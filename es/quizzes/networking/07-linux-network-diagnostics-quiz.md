# Cuestionario de diagnóstico de redes en Linux

> **Última actualización**: 14 de septiembre de 2026

Use estas 12 preguntas para interpretar los ejercicios locales de HTTP, sockets, enrutamiento y MTU. Los valores de las preguntas son ilustrativos; no son mediciones registradas.

## Preguntas de opción múltiple {#questions}

1. Su shell selecciona un contexto remoto de Docker, pero usted quiere ejecutar el script auxiliar de enrutamiento. ¿Qué preparación exige el contrato de la herramienta?
   - A) El script auxiliar usa automáticamente el daemon remoto seleccionado
   - B) Prepare la imagen con la versión fijada en el motor local de Docker para Linux, accesible en `/var/run/docker.sock`, y confirme que supera la comprobación previa de colisiones de subredes
   - C) Habilite los contenedores privilegiados y publique los puertos del router
   - D) Inicie varias copias simultáneamente porque sus rangos de subred son aleatorios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prepare la imagen con la versión fijada en el motor local de Docker para Linux, accesible en `/var/run/docker.sock`, y confirme que supera la comprobación previa de colisiones de subredes**

**Explicación:**
El script auxiliar fija el socket Unix local e ignora las selecciones de host/contexto remoto del entorno. Usa subredes de documentación fijas, por lo que las ejecuciones no deben solaparse. La imagen debe estar disponible de antemano. Los puentes dedicados deshabilitan el enmascaramiento NAT; solo los tres contenedores propios pierden sus rutas predeterminadas IPv4. Docker sigue creando puentes en el host y administrando las reglas de red.

</details>

2. GET `/lesson` devuelve el cuerpo `b"hello\n"`. ¿Qué valor de Content-Length es correcto?
   - A) 5, porque solo cuentan las letras visibles
   - B) 7, porque cada salto de línea del cuerpo debe ser CRLF
   - C) 6, porque las cinco letras ASCII y el LF final suman seis bytes
   - D) La longitud de los encabezados de respuesta más el cuerpo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 6, porque las cinco letras ASCII y el LF final suman seis bytes**

**Explicación:**
En hexadecimal, el cuerpo es `68 65 6c 6c 6f 0a`. Las reglas CRLF de las líneas de encabezado HTTP/1.1 no convierten un LF del cuerpo en CRLF. Content-Length cuenta los bytes del contenido, sin incluir la línea inicial, los encabezados ni el separador. El script auxiliar de eco también conserva los bytes suministrados con `--data-binary`.

</details>

3. Una traza de curl muestra que `/lesson` devuelve `Content-Length: 6` cuando se ejecuta `curl --http1.1 -I`, pero no muestra ningún cuerpo. ¿Qué ocurrió?
   - A) curl envió HEAD; la respuesta no tiene cuerpo y la longitud describe la representación GET correspondiente
   - B) curl envió GET y descartó seis bytes del cuerpo después de recibirlos
   - C) El servidor infringió la delimitación de la respuesta al no enviar los seis bytes requeridos
   - D) HEAD siempre exige que Content-Length sea cero

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) curl envió HEAD; la respuesta no tiene cuerpo y la longitud describe la representación GET correspondiente**

**Explicación:**
`-I` selecciona HEAD. Una respuesta a HEAD no tiene cuerpo de mensaje, aunque incluya una longitud de representación permitida. Es distinto de `-i`, que incluye los encabezados en la salida normal. Tratar los metadatos de HEAD como delimitación del cuerpo puede hacer que un cliente interprete mal la siguiente respuesta en una conexión persistente.

</details>

4. Una traza de curl muestra encabezados HTTP legibles para una solicitud HTTPS. ¿Qué demuestra?
   - A) Los encabezados atravesaron la red sin cifrado
   - B) Cada línea de la traza corresponde a un paquete TCP
   - C) HTTP/2 y HTTP/3 transmiten líneas de texto HTTP/1.1 por la red
   - D) El cliente puede mostrar los datos HTTP que procesa; esto no es una captura pasiva de paquetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) El cliente puede mostrar los datos HTTP que procesa; esto no es una captura pasiva de paquetes**

**Explicación:**
La salida de depuración de curl se genera en el cliente y puede exponer datos protegidos en la red por TLS. Sus anotaciones no reflejan la codificación de los datos transmitidos por la red ni los límites de los segmentos. HTTP/2 y HTTP/3 usan un formato binario basado en tramas. La visibilidad de una captura depende del punto de observación y de los secretos de sesión disponibles.

</details>

5. Una instantánea ilustrativa de `ss` muestra LISTEN `Recv-Q=3`, `Send-Q=128` y ESTABLISHED `Recv-Q=6`. ¿Qué interpretación es correcta?
   - A) El socket de escucha contiene tres bytes de carga útil en un búfer de envío de 128 bytes
   - B) El socket de escucha tiene tres SYN incompletos y el socket establecido tiene seis conexiones en cola
   - C) El socket de escucha tiene tres conexiones pendientes de aceptación y un backlog máximo de 128; el socket establecido tiene seis bytes del flujo en cola para ser leídos
   - D) Los tres números son tamaños de la ventana de congestión

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El socket de escucha tiene tres conexiones pendientes de aceptación y un backlog máximo de 128; el socket establecido tiene seis bytes del flujo en cola para ser leídos**

**Explicación:**
Las unidades de las columnas de cola dependen del estado del socket. En LISTEN, las columnas describen la cola de aceptación, no la cola de SYN incompletos. En ESTABLISHED, describen bytes del flujo; el Send-Q del socket incluye bytes que todavía no se han confirmado. Filtre por el puerto de prueba y distinga los endpoints del cliente y del servidor.

</details>

6. El cliente persistente funciona correctamente, ambas colas del flujo suelen mostrar cero y `skmem` sigue mostrando valores de memoria distintos de cero. ¿Qué debería concluir?
   - A) La conexión está rota porque las colas vacías requieren que el uso de memoria del socket sea cero
   - B) La contabilidad y los presupuestos de memoria difieren de la ocupación del flujo; la pequeña carga de trabajo puede vaciarse entre observaciones
   - C) Aumente todos los sysctl de búfer TCP hasta que las colas del flujo dejen de estar vacías
   - D) `rb` es la ventana de recepción exacta anunciada al equipo remoto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La contabilidad y los presupuestos de memoria difieren de la ocupación del flujo; la pequeña carga de trabajo puede vaciarse entre observaciones**

**Explicación:**
El cliente consume cada respuesta de seis bytes antes de su siguiente solicitud. Este es un ejercicio de observación, no de saturación forzada del búfer. `skmem` incluye la contabilidad y los presupuestos del kernel, mientras que las ventanas de recepción y de congestión son cantidades independientes. Los valores consultados en modo de solo lectura y las observaciones repetidas no justifican un ajuste universal.

</details>

7. El cliente tiene `192.0.2.2/29` y su ruta a `198.51.100.3` usa la puerta de enlace `192.0.2.3`. ¿Qué resultado ARP se espera?
   - A) Una MAC para `192.0.2.3`, sin necesidad de una entrada de vecino del cliente para `198.51.100.3`
   - B) Una asignación MAC directa para el servidor remoto en la red izquierda del cliente
   - C) ARP cambia el destino IP a `192.0.2.3`
   - D) DNS proporciona el destino Ethernet, por lo que no se necesita ARP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Una MAC para `192.0.2.3`, sin necesidad de una entrada de vecino del cliente para `198.51.100.3`**

**Explicación:**
La búsqueda de ruta selecciona el siguiente salto en enlace antes de resolver el vecino. La trama Ethernet tiene como destino la MAC del router, mientras que el destino IP sigue siendo el servidor. En la red derecha, el router realiza su propia búsqueda y resolución de vecinos. El servidor también necesita su ruta de retorno explícita.

</details>

8. Un ping con TTL 1 falla, mientras que la captura del router contiene ICMP tipo 11, código 0, que incluye esa sonda. ¿Cómo debe interpretar esto el laboratorio?
   - A) El destino completó una solicitud HTTP
   - B) El router informó de una incompatibilidad de MSS de TCP
   - C) Todos los paquetes de aplicación posteriores tienen que fallar en el mismo router
   - D) El TTL deliberadamente corto expiró en el router y generó la respuesta de diagnóstico prevista

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) El TTL deliberadamente corto expiró en el router y generó la respuesta de diagnóstico prevista**

**Explicación:**
La solicitud Echo saliente y el mensaje Time Exceeded de retorno son mensajes distintos. Correlacionar el error capturado con la sonda confirma que ocurrió el evento previsto. Un simple tiempo de espera no bastaría para demostrarlo: el filtrado, la limitación de frecuencia de respuestas o la pérdida en la ruta de retorno también pueden impedir una respuesta. Para esta comprobación, el script auxiliar captura el tráfico en el espacio de nombres real del router.

</details>

9. La MTU de salida del router es 1280. Un ping IPv4 con DF usa 1372 bytes de datos; otro usa 1200. Incluidos los encabezados IPv4 e ICMP básicos, ¿qué resultado se espera?
   - A) Ambos caben porque solo cuentan los datos ICMP para la MTU
   - B) El primero ocupa 1372 bytes y el segundo 1200 bytes en la capa IP
   - C) El paquete IP de 1400 bytes activa Fragmentation Needed; el paquete de 1228 bytes cabe
   - D) La sonda más grande negocia que el MSS de TCP baje a 1200

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) El paquete IP de 1400 bytes activa Fragmentation Needed; el paquete de 1228 bytes cabe**

**Explicación:**
Añada 20 bytes del encabezado IPv4 y 8 del encabezado ICMP. DF impide que el router fragmente, por lo que el primer fallo debería ir acompañado de ICMP tipo 3, código 4; la sonda más pequeña tiene éxito. Una vez almacenada en caché la información de PMTU, un envío posterior demasiado grande puede fallar localmente en vez de generar otra captura del router.

</details>

10. `ss -i` en la conexión HTTP loopback informa de un MSS superior a 1460. ¿Qué conclusión está justificada?
   - A) El script auxiliar necesariamente habilitó tramas Ethernet jumbo en una interfaz física
   - B) El cálculo de 1460 presupone MTU Ethernet 1500 y encabezados IPv4/TCP básicos; loopback tiene condiciones distintas
   - C) El tamaño de datos de la sonda ICMP es el MSS TCP real
   - D) Toda unidad capturada que supere 1500 demuestra una infracción de MTU en un cable físico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El cálculo de 1460 presupone MTU Ethernet 1500 y encabezados IPv4/TCP básicos; loopback tiene condiciones distintas**

**Explicación:**
MSS describe datos TCP, no datos ICMP ni una trama completa. La MTU de la interfaz, las opciones y el comportamiento de la ruta importan. TSO/GSO/GRO también pueden hacer que las observaciones en el host difieran de los paquetes en el enlace físico. El ejercicio loopback no establece cuál es la MTU de una red Ethernet física.

</details>

11. DNS de Docker resuelve correctamente el nombre del router, pero el ping normal del cliente al servidor falla. ¿Qué se ha establecido?
   - A) La resolución de nombres funciona; aún hay que examinar la selección de ruta, el reenvío y la ruta de retorno
   - B) La aplicación del servidor está en buen estado
   - C) Los dos puentes dedicados proporcionan NAT de Internet funcional
   - D) El servidor HTTP loopback del host debe ser accesible mediante `127.0.0.1` en todos los contenedores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) La resolución de nombres funciona; aún hay que examinar la selección de ruta, el reenvío y la ruta de retorno**

**Explicación:**
DNS y el reenvío ponen a prueba mecanismos distintos. Esta configuración usa enrutamiento explícito entre puentes dedicados con el enmascaramiento NAT deshabilitado, y no evalúa el rendimiento de NAT de Internet. Cada espacio de nombres de red tiene su propio loopback; el servidor loopback del host no es un servicio local de los contenedores. Correlacione las observaciones en el espacio de nombres donde se realiza cada búsqueda.

</details>

12. El JSON de enrutamiento contiene algunas observaciones correctas, pero su estado es fallido o la limpieza está incompleta. ¿Cuál es el resultado correcto?
   - A) Cuente toda la ejecución como aprobada porque funcionó la búsqueda de rutas
   - B) Ignore la limpieza si la imagen sigue almacenada localmente
   - C) Ejecute una limpieza general de Docker para garantizar que el host quede limpio
   - D) Mantenga el estado fallido, inspeccione la fase que falló e identifique solo los ID creados para cualquier limpieza necesaria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Mantenga el estado fallido, inspeccione la fase que falló e identifique solo los ID creados para cualquier limpieza necesaria**

**Explicación:**
Para que una ejecución se apruebe, debe finalizar correctamente, las ocho comprobaciones deben ser verdaderas y la limpieza debe constar en el informe, incluidas las listas vacías de rutas predeterminadas IPv4 en los tres contenedores. El script auxiliar registra los ID creados en lugar de eliminar recursos con nombre que no le pertenecen. Una terminación abrupta puede impedir la limpieza. Conserve la evidencia, use una nueva ruta de salida para una ejecución posterior y no eluda los controles de red compartidos para forzar la aprobación.

</details>

---

[Volver a la guía de diagnóstico](../../networking/07-linux-network-diagnostics.md) · [HTTP](../../networking/07-linux-network-diagnostics.md#http-message-lab) · [Búferes TCP](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab) · [Enrutamiento e ICMP](../../networking/07-linux-network-diagnostics.md#routing-icmp-lab) · [MTU y MSS](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab)
