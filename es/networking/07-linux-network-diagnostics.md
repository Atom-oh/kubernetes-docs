# Diagnóstico de red en Linux: HTTP, colas TCP, enrutamiento y MTU

> **Entorno compatible**: Linux, Python 3.9 o posterior, curl e iproute2; Docker Engine local para el ejercicio de enrutamiento
> **Última actualización**: 15 de septiembre de 2026

Empieza con una solicitud en Linux, identifica el socket y el siguiente salto, y luego explica la misma ruta de paquete a través de los espacios de nombres de los contenedores. Estos ejercicios te preparan para distinguir la evidencia de aplicación, transporte y enrutamiento antes de investigar redes de Kubernetes o AWS.

Para practicar primero con la CLI, la configuración IP, DNS, SSH y los firewalls, completa el [curso para principiantes de ocho lecciones](beginner/README.md). Después, esta guía profundiza en la observación de sockets, ICMP y PMTU.

Lee [fundamentos de IPv4 y siguiente salto](../basics/06-network-fundamentals-part1.md#ipv4-cidr-subnet) y [estructura de mensajes HTTP](../basics/06-network-fundamentals-part3.md#http11-message-structure) junto con los ejercicios.

- [Mensajes HTTP](#http-message-lab)
- [Colas y búferes TCP](#tcp-buffer-lab)
- [Enrutamiento e ICMP](#routing-icmp-lab)
- [MTU, PMTU y MSS](#mtu-mss-lab)
- [La ruta de paquetes de Docker](#docker-packet-path)

## Alcance y preparación {#lab-scope}

Ejecuta los comandos desde un clon local de este repositorio. Usa terminales separadas cuando se indique.

| Ejercicio | Requisitos | Alcance |
|---|---|---|
| HTTP | Python 3.9 o posterior, curl | Un servidor en `127.0.0.1:18080`, que se detiene automáticamente |
| Observación TCP | El servidor HTTP, Python, `ss` de iproute2 | Observaciones de solo lectura del puerto de prueba local |
| Enrutamiento y MTU | Docker Engine de Linux, CLI de Docker, iproute2 del host, imagen descargada previamente | Tres contenedores temporales y dos bridges dedicados |

Los helpers son [http_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/http_lab.py) y [routing_lab.py](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/routing_lab.py). Lee sus contratos y el [README de los ejemplos](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md) antes de ejecutarlos.

Los comandos describen el procedimiento; el fragmento de respuesta HTTP es **ilustrativo**. Los fragmentos de enrutamiento señalados explícitamente proceden de una ejecución de referencia registrada, no de tu máquina. Evalúa tu ejecución según los criterios indicados y el registro JSON del helper de enrutamiento.

El helper HTTP es un pequeño servidor educativo HTTP/1.1, no un servidor de producción ni una implementación completa de RFC. Acepta como máximo 4096 bytes de cuerpo de solicitud y solo el encuadre `Content-Length` admitido; rechaza la codificación de transferencia.

El helper de enrutamiento usa solo `unix:///var/run/docker.sock` e ignora las selecciones del entorno de host/contexto remoto de Docker. Requiere un Engine Linux local y acceso a ese socket; un contexto remoto o un socket rootless ubicado en otro lugar no son equivalentes.

Su constante `IMAGE` fija esta referencia, que ya debe estar presente en ese Engine:

```text
nicolaka/netshoot:v0.16@sha256:b09d9b21381f47a79b3cbcb30da25266dc17186ea00ae65e99fdc51396f48e70
```

El helper no descarga la imagen. Antes de crear recursos, compara sus subredes fijas con las rutas IPv4 visibles del host y los rangos de las redes Docker existentes. Ejecuta un ejercicio de enrutamiento cada vez; si hay una colisión, detente en lugar de cambiar rutas compartidas del host.

## Laboratorio 1: lee mensajes HTTP {#http-message-lab}

**Propósito:** Distinguir la línea de solicitud/estado, los campos, el terminador de cabeceras y los bytes del contenido.

En la terminal A, inicia el servidor:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 120
```

Se enlaza solo a `127.0.0.1` y termina después de 120 segundos; la duración máxima permitida es de 600 segundos. Si el puerto está ocupado, usa otro puerto local libre de manera coherente en los comandos y filtros. No detengas un listener ajeno.

En la terminal B, envía una solicitud GET y otra HEAD:

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 -i http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 5 --http1.1 -I http://127.0.0.1:18080/lesson
```

`--disable` como primera opción omite la configuración predeterminada de curl; `--noproxy '*'` evita los proxies configurados. `-i` incluye las cabeceras de respuesta; `-I` envía HEAD, no un GET normal con el cuerpo oculto.

A continuación se muestra un fragmento ilustrativo de respuesta GET; se omiten los campos `Date` y `Server` generados:

```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 6

hello
```

El cuerpo real es `b"hello\n"`: hexadecimal `68 65 6c 6c 6f 0a`. El LF final es el sexto byte. Las líneas de cabecera y el separador entre cabeceras/cuerpo usan CRLF en el flujo HTTP/1.1; esta visualización Markdown usa LF.

Ahora envía esos mismos seis bytes al endpoint de eco:

```bash
printf 'hello\n' | curl --disable --noproxy '*' --max-time 5 --http1.1 -i \
  -H 'Content-Type: text/plain' --data-binary @- \
  http://127.0.0.1:18080/echo
```

`--data-binary @-` lee stdin sin quitar el LF y selecciona POST. El helper devuelve los bytes sin cambios con `Content-Type: application/octet-stream`; no analiza texto, JSON ni formularios.

| Observación | Criterio esperado | Interpretación |
|---|---|---|
| GET `/lesson` | HTTP/1.1 200, longitud 6, seis bytes de contenido | La longitud excluye la línea de inicio y las cabeceras |
| HEAD `/lesson` | HTTP/1.1 200 y longitud 6, sin cuerpo de respuesta | El campo describe la representación GET correspondiente |
| POST `/echo` | HTTP/1.1 200, longitud 6, `hello` intacto más LF | La conservación de bytes es independiente de la interpretación del tipo de medio |

Un carácter no ASCII puede ocupar varios bytes UTF-8. Cuenta los bytes codificados enviados, incluidos los saltos de línea reales, en vez de contar los caracteres visibles.

Inspecciona la traza de depuración del cliente para ver la línea de solicitud y los campos enviados:

```bash
curl --disable --noproxy '*' --max-time 5 --http1.1 --trace-ascii - \
  --output /dev/null http://127.0.0.1:18080/lesson
```

Esta es la **salida de depuración del cliente curl**, no una captura de paquetes. Sus anotaciones no son bytes de la red, límites de segmentos TCP ni prueba de lo que ve un router. Usa solo los datos de demostración al recopilar trazas.

Con HTTPS, el cliente puede mostrar texto HTTP sin cifrar que una captura pasiva de red no puede leer sin los secretos de sesión. HTTP/2 y HTTP/3 también usan un encuadre binario distinto; la salida legible de una herramienta no es su codificación sin procesar.

**Limpieza:** Detén este servidor con Ctrl+C en la terminal A o deja que venza su temporizador. No crea datos de aplicación persistentes. Reinícialo para el siguiente ejercicio si venció el temporizador.

## Laboratorio 2: observa colas y búferes TCP {#tcp-buffer-lab}

**Propósito:** Relacionar una conexión persistente con el estado del socket, las colas del flujo y la contabilidad de memoria.

Inicia el mismo servidor de 120 segundos en la terminal A. En la terminal B, ejecuta este cliente acotado:

```bash
python3 - <<'PY'
import http.client
import time

connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
try:
    for number in range(30):
        connection.request("GET", "/lesson")
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert response.getheader("Content-Length") == "6"
        assert body == b"hello\n"
        if number == 0:
            print("Client endpoint:", connection.sock.getsockname(), flush=True)
        time.sleep(1)
finally:
    connection.close()
PY
```

El cliente consume cada respuesta antes de volver a usar la conexión. Envía 30 solicitudes GET pequeñas a intervalos de un segundo, lo que facilita observar el socket establecido frente a procesos curl breves y separados.

Mientras se ejecuta, usa la terminal C:

```bash
ss -ltn 'sport = :18080'
ss -tinm state established '( sport = :18080 or dport = :18080 )'
```

Repite varias veces el segundo comando. Estos comandos inspeccionan el espacio de nombres de red actual y filtran por el puerto de prueba. Pueden aparecer ambos extremos locales de esta conexión loopback; distingue el puerto del servidor del puerto efímero del cliente.

**Criterio esperado:** Hay un listener en `127.0.0.1:18080` y se ve una conexión establecida mientras se ejecuta el cliente. Los valores exactos de cola, RTT y memoria varían; una cola en cero es normal para esta carga pequeña.

| Campo/estado | Significado |
|---|---|
| `Recv-Q` de ESTABLISHED | Bytes recibidos en orden que la aplicación aún no ha consumido |
| `Send-Q` de ESTABLISHED | Bytes del flujo que aún no se han confirmado, incluidos los que todavía no se enviaron |
| `Recv-Q` de LISTEN | Conexiones en cola para `accept()`, no bytes de carga útil |
| `Send-Q` de LISTEN | Longitud máxima de la cola de aceptación, no tamaño del búfer de envío |
| `skmem` `r` / `rb` | Contabilidad de memoria de recepción / presupuesto de memoria de recepción |
| `skmem` `w` / `tb` | Memoria de envío en cola / presupuesto de memoria de envío |
| `rtt`, `mss`, `cwnd` | RTT, tamaño de datos TCP e información de la ventana de congestión; `cwnd` suele expresarse en segmentos |

La memoria del socket incluye datos contables y no tiene por qué coincidir con las columnas de cola del flujo. La cola del listener también es distinta de la cola SYN incompleta. El [manual ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html) describe los campos disponibles.

Lee la política actual de búferes sin cambiarla:

```bash
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.ipv4.tcp_moderate_rcvbuf
```

Las ternas `tcp_*mem` describen los límites mínimo/predeterminado/ajuste automático, no la ocupación actual de cada socket. El autoajuste de recepción y las opciones explícitas del socket de la aplicación afectan el resultado; un presupuesto no es la ventana de recepción anunciada ni `cwnd`.

Una cola de recepción que crece sugiere investigar el progreso de lectura; una cola de envío persistente requiere evidencia de la aplicación, las confirmaciones y la ruta. Ni una sola instantánea ni un búfer mayor demuestran una mejora de rendimiento.

Esta carga de seis bytes observa el funcionamiento normal; no crea deliberadamente contrapresión ni mide el rendimiento máximo. Continúa con el [análisis de sockets y búferes](../kernel/02-network-stack.md#tcp-buffer-policy) antes de proponer cambios de ajuste.

**Limpieza:** El cliente cierra su conexión tras 30 iteraciones, o mediante `finally` si se interrumpe. Detén el servidor en la terminal A o deja que venza su temporizador. No hay que revertir cambios de sysctl.

## Laboratorio 3: sigue el enrutamiento y el ICMP {#routing-icmp-lab}

**Propósito:** Demostrar el siguiente salto seleccionado, distinguir la resolución de nombres del reenvío y relacionar una prueba con TTL limitado con una respuesta ICMP.

El helper de enrutamiento crea esta topología temporal:

```text
client namespace          router namespace                 server namespace
192.0.2.2/29 --- left --- 192.0.2.3/29
                          198.51.100.2/29 --- right --- 198.51.100.3/29
left bridge: 192.0.2.0/29             right bridge: 198.51.100.0/29
```

Ambos bridges dedicados fijan `com.docker.network.bridge.enable_ip_masquerade=false`. Antes de añadir las rutas explícitas del laboratorio, el helper elimina **todas las rutas IPv4 predeterminadas dentro de sus tres contenedores** y conserva las rutas conectadas.

Los contenedores descartan todas las capacidades y luego añaden solo `NET_ADMIN` y `NET_RAW`; el reenvío se habilita dentro del espacio de nombres del router. El helper no usa contenedores privilegiados ni la red del host, no publica puertos y no crea recursos de AWS.

Docker crea bridges en el host y administra sus reglas de red habituales. El helper no cambia manualmente rutas del host, sysctls ni reglas iptables; esto no significa que el host quede intacto ni establece un aislamiento de red completo.

Añade una ruta del cliente para `198.51.100.0/29` vía `192.0.2.3` y una ruta de retorno del servidor para `192.0.2.0/29` vía `198.51.100.2`.

Elige una ruta de salida que no exista:

```bash
python3 examples/networking/foundations/routing_lab.py \
  --output ./routing-observation-01.json
```

El helper se niega a sobrescribir un archivo existente. **Esta misma invocación ejecuta también el ejercicio de MTU de más abajo**; no inicies una segunda ejecución concurrente para esa sección.

Los siguientes son comandos que el helper ejecuta en el **espacio de nombres del cliente**, mostrados para interpretarlos y no para ejecutarlos en el shell del host:

```text
ip -j route get 198.51.100.3
ip -j neigh show to 192.0.2.3
ip -j neigh show to 198.51.100.3
ping -n -c 1 -W 1 -t 1 198.51.100.3
traceroute -n -I -m 4 -q 1 -w 1 198.51.100.3
```

También resuelve mediante DNS de Docker el nombre generado del contenedor router. El nombre de destino varía según el prefijo de ejecución; una respuesta DNS no es por sí misma una prueba de conectividad.

| Observación JSON | Criterio esperado | Interpretación |
|---|---|---|
| `defaultRoutes` | Listas vacías para cliente, router y servidor | Ninguno de los tres contenedores conserva una ruta IPv4 predeterminada |
| `route` | Gateway `192.0.2.3`, origen `192.0.2.2` | Se alcanza el destino a través del router |
| `dns` | El nombre del router resuelve a `192.0.2.3` en la red izquierda | La resolución de nombres de Docker funciona |
| `nextHopNeighbor` | Una dirección MAC para `192.0.2.3` | ARP resolvió el siguiente salto |
| `remoteNeighbor` | Vacío | El servidor remoto no es un vecino Ethernet del cliente |
| `ttlOne` | Falla la prueba; la captura contiene ICMP Time Exceeded | El TTL vence en el router según lo previsto |
| `traceroute` | Primer salto `192.0.2.3`, destino `198.51.100.3` | Un seguimiento con sondas ICMP alcanza dos saltos IP |

Para `ttlOne`, el helper inicia `tcpdump` real en el espacio de nombres del router con el filtro `icmp[0] == 11`, espera a que la captura esté lista y luego envía el ping con TTL 1. La respuesta prevista es IPv4 ICMP Tipo 11 Código 0, que incluye la sonda original.

Que el ping falle aquí constituye un estímulo diagnóstico satisfactorio cuando esa captura lo confirma. La sonda es ICMP Echo; Time Exceeded es un mensaje de respuesta separado.

Traceroute `-I` usa sondas ICMP Echo. Los métodos UDP y TCP pueden encontrar filtros distintos y recibir respuestas de destino diferentes. Un `*` solo registra que no hubo respuesta coincidente dentro del período de espera; por sí solo no demuestra una pérdida de extremo a extremo. RTT incluye la ruta de retorno de la respuesta.

Inspecciona el archivo de evidencia cuando termine el helper:

```bash
python3 - <<'PY'
import json
from pathlib import Path

record = json.loads(Path("routing-observation-01.json").read_text())
print("Status:", record["status"])
print("Checks:", record.get("checks", {}))
print("Cleanup:", record.get("cleanup", "not reported"))
PY
```

**Criterio de éxito:** El helper termina correctamente y registra `status: passed`; las ocho comprobaciones nombradas son verdaderas y se informa de la limpieza. Que funcionen las rutas y DNS no sustituye las observaciones fallidas de paquetes.

**Limpieza:** Tras la finalización normal, los fallos de observación y las interrupciones gestionadas, el helper intenta quitar los ID de contenedores y redes que creó. Un error de limpieza significa que la ejecución falló. Una terminación abrupta puede impedir la limpieza; usa los ID registrados para identificar recursos residuales y nunca hagas una poda amplia de recursos Docker compartidos. Conserva el JSON mientras interpretas la siguiente sección.

### Ejecución de referencia registrada {#routing-reference-run}

La ejecución del 14 de septiembre de 2026, enlazada desde el [registro de validación de los ejemplos](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/networking/foundations/README.md#validation), pasó en Linux Docker Engine 25.0.16: pasaron las ocho comprobaciones, las tres listas de rutas predeterminadas estaban vacías y se eliminaron los ID creados. Traceroute observó `192.0.2.3` seguido de `198.51.100.3`.

Detalle medido del paquete de error TTL, con la marca de tiempo y el prefijo de interfaz omitidos:

```text
IP 192.0.2.3 > 192.0.2.2: ICMP time exceeded in-transit, length 92
```

Esto es evidencia funcional de ese entorno. No garantiza tiempos, nombres de interfaz, direcciones MAC ni compatibilidad idénticos en otro host.

## Laboratorio 4: distingue MTU, PMTU y MSS {#mtu-mss-lab}

**Propósito:** Explicar un fallo dependiente del tamaño mediante un error ICMP real, sin confundir el tamaño de carga útil ICMP con MSS de TCP.

Usa la misma invocación de enrutamiento y el mismo registro JSON. El helper busca mediante una consulta de ruta la interfaz del router hacia el servidor y luego establece la MTU de **esa interfaz del contenedor en 1280**. No presupone que la interfaz de salida se llame `eth1`.

Para la primera sonda del cliente, captura en el router `icmp[0] == 3 and icmp[1] == 4`. Luego envía la sonda más pequeña:

```text
ping -n -c 1 -W 1 -M do -s 1372 198.51.100.3
ping -n -c 1 -W 1 -M do -s 1200 198.51.100.3
```

`-M do` solicita el comportamiento IPv4 Don't Fragment. Con la cabecera IPv4 habitual de 20 bytes y la cabecera ICMP de 8 bytes usadas aquí:

| Sonda | Tamaño del paquete IP | Criterio esperado |
|---|---|---|
| Datos ICMP de 1372 bytes | `1372 + 8 + 20 = 1400` bytes | Demasiado grande para la salida de MTU 1280; falla y se captura ICMP Tipo 3 Código 4 |
| Datos ICMP de 1200 bytes | `1200 + 8 + 20 = 1228` bytes | Cabe en esa salida; tiene éxito Echo Reply |

Inspecciona `pmtu.probeOutput`, `pmtu.capture`, `smallerPacket` y `routeAfterFeedback`. La evidencia importante es **el aviso Fragmentation Needed junto con el éxito de un paquete más pequeño**, no un RTT determinado ni un texto exacto de salida.

La misma ejecución registrada produjo esta línea de ping medida:

```text
From 192.0.2.3 icmp_seq=1 Frag needed and DF set (mtu = 1280)
```

La sonda con 1200 bytes de datos recibió una respuesta y `routeAfterFeedback` indicó MTU 1280. Son observaciones de esa ejecución, no garantías de tiempo fijo ni de caducidad de caché.

Después de recibir la notificación, Linux puede almacenar en caché la PMTU de destino. Un envío posterior demasiado grande puede fallar localmente con «message too long» en vez de volver a llegar al router. `routeAfterFeedback` puede mostrar información de MTU aprendida; los campos y su caducidad varían.

La captura del helper corresponde al primer fallo inducido deliberadamente en el espacio de nombres temporal del cliente. La ausencia de un mensaje ICMP posterior no invalida la notificación anterior.

**MSS es distinto:** limita los bytes de datos TCP. Para una MTU Ethernet de 1500 y las cabeceras IPv4/TCP base, `1500 − 20 − 20 = 1460` es el cálculo base de MSS. Las opciones IP/TCP y las condiciones de la ruta pueden reducir los datos reales por paquete.

Los valores 1372 y 1200 anteriores son tamaños de datos ICMP, **no valores MSS medidos**. Tampoco cabe esperar que el ejercicio TCP loopback muestre necesariamente MSS 1460: loopback tiene su propia MTU y comportamiento del kernel.

TSO/GSO/GRO y la descarga de checksum pueden hacer que una captura del host difiera de los paquetes de un enlace físico. Comprueba la interfaz, el espacio de nombres y el punto de observación antes de considerar un paquete capturado grande o un error aparente de checksum como un fallo en la red física.

Los routers IPv6 no fragmentan los paquetes reenviados y usan ICMPv6 Packet Too Big. PMTUD clásico y las sondas de capa de paquetización dependen de mecanismos de notificación diferentes; consulta los [fundamentos de ICMP](../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation).

**Limpieza:** El helper de enrutamiento elimina el router temporal, incluido su cambio de MTU, junto con los demás ID creados. No se cambia la MTU de la interfaz física del host. Conserva o elimina solo tu propio archivo de evidencia después del análisis.

## Explica la ruta de paquetes de Docker {#docker-packet-path}

**Propósito:** Relacionar las observaciones con los espacios de nombres Linux, los enlaces Ethernet virtuales y la consulta de rutas.

Reutiliza el registro de enrutamiento existente; no hacen falta más contenedores. Compara `route`, las observaciones de vecinos, las capturas ICMP y los comandos registrados:

1. El espacio de nombres del cliente selecciona `198.51.100.0/29 via 192.0.2.3`; la ruta explícita determina el siguiente salto.
2. El cliente resuelve mediante ARP la MAC del lado izquierdo del router. El destino IP sigue siendo `198.51.100.3`.
3. Un par veth y el bridge izquierdo llevan la trama Ethernet al router. El bridging L2 no consume un salto TTL IP.
4. El espacio de nombres del router reenvía IPv4: reduce el TTL, consulta la ruta al servidor y comprueba la MTU de salida.
5. En la red derecha, el router resuelve la MAC del servidor y envía una nueva trama Ethernet. La ruta enrutada prevista no traduce estas direcciones IP de origen/destino.
6. La ruta de retorno explícita del servidor usa `198.51.100.2`. Que llegue la solicitud no elimina la necesidad de una ruta de respuesta funcional.

**Criterio esperado:** Puedes identificar en el registro el espacio de nombres de cada consulta, su destino IP, el destino ARP local y la ruta de respuesta. No deduzcas nombres de interfaces ni valores MAC a partir de otra ejecución.

La resolución de nombres DNS de Docker y el reenvío de paquetes de Linux son observaciones separadas. Una respuesta DNS correcta puede coexistir con una ruta, política de reenvío o ruta de retorno rota.

Cada espacio de nombres de red también tiene su propio dispositivo loopback. `127.0.0.1` dentro de un contenedor no alcanza el helper HTTP del host; este ejercicio no usa el modo de red del host para alterar esa condición.

Se trata de dos bridges definidos por el usuario y dedicados con un router explícito, masquerading deshabilitado y sin rutas IPv4 predeterminadas en los tres contenedores. Esto define la ruta prevista del laboratorio, no una garantía general de aislamiento de seguridad. El ejercicio no mide el NAT de Internet predeterminado de Docker, el reenvío de puertos publicados ni el rendimiento hacia Internet.

**Limpieza:** Reutiliza el registro completado; el helper de enrutamiento ya intentó limpiar los recursos. Un registro fallido o incompleto indica que debes inspeccionar la etapa que falló, no desactivar controles de firewall compartidos.

Continúa con [tecnología de contenedores](../basics/03-container-technology.md) y luego el [Laboratorio de servicios y redes principales](../labs/core/03-services-networking-lab.md). CNI de Kubernetes, traducción de Service y enrutamiento VPC de AWS añaden sus propias reglas; inspecciona cada una en la capa correspondiente en vez de copiar la topología Docker.

## Referencias y revisión {#references}

- [Semántica HTTP: RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) y [encuadre HTTP/1.1: RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html)
- [Manual de curl](https://curl.se/docs/manpage.html): versión HTTP, HEAD, datos binarios de solicitud y trazas
- [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html), [socket(7)](https://man7.org/linux/man-pages/man7/socket.7.html) y [política de búfer TCP de Linux](https://docs.kernel.org/networking/ip-sysctl.html)
- [ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html), [ip-neighbour(8)](https://man7.org/linux/man-pages/man8/ip-neighbour.8.html) y [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)
- [Manual de ping de iputils](https://github.com/iputils/iputils/blob/master/doc/ping.xml) y [traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html)
- [ICMP: RFC 792](https://www.rfc-editor.org/rfc/rfc792.html), [comportamiento de routers IPv4: RFC 1812](https://www.rfc-editor.org/rfc/rfc1812.html) y [MSS: RFC 6691](https://www.rfc-editor.org/rfc/rfc6691.html)
- [Redes bridge de Docker y opciones del controlador](https://docs.docker.com/engine/network/drivers/bridge/)

[Comprueba lo aprendido](../quizzes/networking/07-linux-network-diagnostics-quiz.md)
