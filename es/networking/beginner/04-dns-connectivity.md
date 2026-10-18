# 04. Diagnóstico de DNS y conectividad

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

«El servidor no está disponible» puede significar que no se resolvió un nombre, que un paquete tomó una ruta incorrecta, que un firewall rechazó una conexión o que una aplicación devolvió un error. Cada prueba siguiente responde una pregunta más acotada. Registra el resultado y sus límites antes de elegir la próxima prueba.

## Requisitos previos y objetivos

Completa [configuración persistente](03-persistent-configuration.md). El [laboratorio del curso](README.md) tiene un cliente en `192.0.2.10/24` y un servidor en `192.0.2.20/24` dentro de la misma red virtual interna. **No tiene DHCP, gateway, servidor DNS ni enlace ascendente**. La NIC de administración NAT/DHCP separada de cada sistema invitado no se modifica.

Usa las consolas de los sistemas invitados e identifica las NIC del laboratorio haciendo coincidir las MAC del hipervisor con `ip -br link`. La lección principal funciona sin DNS público ni acceso a Internet. El ejercicio de consulta pública, marcado por separado, es opcional.

| Herramientas ya preparadas en los sistemas invitados | Propósito |
|---|---|
| `ip`, `ping`, `getent`, `grep`, `timeout`, editor y sudo | Configuración local, nombres y sondeos limitados en duración |
| `dig` | Inspeccionar respuestas del protocolo DNS; lo proporcionan las utilidades de BIND |
| `tracepath` o Linux `traceroute` | Observar respuestas a sondeos con límite de saltos |
| `python3` (3.9+), `curl`, `ss` | Ofrecer una página desechable y observar HTTP/sockets en escucha |
| OpenBSD `nc` de Ubuntu o `ncat` de Rocky | Hacer una prueba de conexión TCP |
| `resolvectl` cuando systemd-resolved está activo | Inspeccionar ese resolvedor; no es un requisito en Rocky |

Comprueba la disponibilidad con `command -v ip ping getent timeout dig tracepath traceroute python3 curl ss nc ncat`. Es normal que falten alternativas opcionales; si falta una herramienta necesaria para el ejercicio elegido, vuelve a [preparación de herramientas del sistema invitado](README.md#guest-tools) para consultar los paquetes e instalar únicamente la herramienta que falte. Este capítulo no contiene comandos para instalar paquetes.

Aprenderás a distinguir una consulta NSS de una consulta DNS, explicar respuestas autoritativas y caché, inspeccionar la ruta elegida, interpretar ICMP y los resultados de traceroute, separar TCP de HTTP y redactar un informe de fallos con un siguiente paso justificado.

## 1. Nombres, DNS y el sistema operativo

DNS es una base de datos distribuida. Un registro **A** contiene una dirección IPv4; **AAAA** contiene IPv6; **CNAME** apunta un alias a otro nombre; **PTR** se utiliza para búsquedas inversas. Ninguno de estos registros demuestra que la aplicación de destino esté en ejecución.

Un **resolvedor recursivo** busca una respuesta para su cliente, usando información en caché o consultando otros servidores DNS. Un **servidor autoritativo** almacena los datos publicados de una zona. Una caché puede reutilizar respuestas positivas y negativas durante el tiempo permitido. El **TTL** de DNS se mide en segundos; el TTL de IP es un límite de saltos y no tiene relación con aquel. Reducir ahora un TTL DNS no elimina de inmediato las copias que ya están en caché con un TTL anterior. Consulta [conceptos de DNS](https://www.rfc-editor.org/rfc/rfc1034.html) y [caché negativa](https://www.rfc-editor.org/rfc/rfc2308.html).

Las aplicaciones Linux pueden pedir a la biblioteca C que resuelva un nombre mediante **NSS**, el conmutador de servicios de nombres. NSS selecciona fuentes mediante `/etc/nsswitch.conf`: `files` lee `/etc/hosts`; `dns` usa DNS; `resolve` se comunica con systemd-resolved si está instalado/configurado. Otros módulos y reglas de retorno entre corchetes pueden cambiar el orden de búsqueda. Las aplicaciones que usan sus propios resolvedores, como un navegador con DNS over HTTPS, pueden comportarse de otra manera.

| Herramienta | Pregunta que responde |
|---|---|
| `getent ahostsv4 NAME` | ¿Qué direcciones IPv4 devuelve la ruta NSS/getaddrinfo de este sistema? |
| `getent hosts NAME` | ¿Qué devuelve la consulta hosts de NSS? Su comportamiento respecto a la familia de direcciones difiere de `ahostsv4` |
| `getent -s files hosts NAME` | ¿La fuente `files` contiene este nombre? |
| `dig @SERVER NAME A` | ¿Qué respuesta DNS devuelve ese servidor? No usa NSS para buscar el nombre consultado |
| `resolvectl query NAME` | ¿Qué devuelve systemd-resolved mediante su propia interfaz de resolución? |

En el **cliente**, inspecciona sin editar:

```bash
grep '^hosts:' /etc/nsswitch.conf
cat /etc/hosts
ls -l /etc/resolv.conf
cat /etc/resolv.conf
systemctl is-active systemd-resolved
```

Por ejemplo, `hosts: files dns` prueba el archivo hosts antes que DNS. No reemplaces tu línea real por este ejemplo. `/etc/resolv.conf` puede ser un enlace simbólico a un archivo stub generado, una lista generada de servidores upstream o un archivo administrado de otra manera. Una entrada `nameserver 127.0.0.53` identifica un stub local de loopback, no el router.

En un **cliente Ubuntu con systemd-resolved activo**:

```bash
resolvectl status
resolvectl statistics
```

Inspecciona los servidores DNS y dominios de búsqueda por enlace, además de las estadísticas de caché. La NIC del laboratorio no debe proporcionar DNS; puede seguir apareciendo el DNS de administración. En un **cliente Rocky administrado por NetworkManager**, usa `nmcli -f GENERAL,IP4,IP6 device show` y la inspección anterior del archivo del resolvedor. No instales resolved ni reescribas el enlace simbólico solo para imitar la disposición de Ubuntu. Toda corrección duradera debe hacerse en la configuración administrada por el propietario confirmado en el capítulo 03.

## 2. Asigna nombres locales a las dos VM

En el **cliente**, usa `/etc/hosts` para que el laboratorio local no necesite un resolvedor externo. Estos nombres son alias locales; no renombran los sistemas invitados, no crean registros DNS ni configuran el servidor remotamente. `.test` está reservado para pruebas; evita `.local`, que tiene un comportamiento especial de DNS multicast.

Primero busca conflictos:

```bash
grep -nE 'netlab\.test|BEGIN network-beginner-04|END network-beginner-04' /etc/hosts
```

En la primera ejecución, lo esperado es que no haya salida y que el código de salida sea 1. Si hay entradas, inspecciónalas antes de continuar; no añadas asignaciones duplicadas. Crea un directorio de recuperación nuevo y una copia de seguridad:

```bash
sudo mkdir -m 700 /root/network-beginner-04
sudo cp -a /etc/hosts /root/network-beginner-04/hosts-before
sudoedit /etc/hosts
```

Si el directorio ya existe, detente e inspecciona el intento anterior. Añade solo este bloque al final; conserva todas las entradas de localhost y del nombre del sistema invitado que ya existan:

```text
# BEGIN network-beginner-04
192.0.2.10 client.netlab.test
192.0.2.20 server.netlab.test
# END network-beginner-04
```

Ahora compara la consulta solo en archivos con la consulta normal de una aplicación:

```bash
getent -s files hosts server.netlab.test
timeout 5s getent ahostsv4 server.netlab.test
timeout 5s getent hosts server.netlab.test
```

Las dos primeras deberían incluir `192.0.2.20`. `ahostsv4` puede repetirlo para `STREAM`, `DGRAM` y `RAW`; estos describen tipos de socket, no tres servidores. `hosts` puede intentar una consulta IPv6 antes que IPv4 y seguir una ruta distinta o tardar más. Un timeout (código 124) es una observación con límite de tiempo, no una prueba de que DNS diga que el nombre no existe.

Si la consulta solo en archivos funciona, pero falla la consulta normal, inspecciona el orden y los módulos de NSS y compara la ortografía exacta y la familia de direcciones. No cambies la ruta para corregir una consulta de nombre. El servidor solo necesita sus propias entradas hosts si también usará estos nombres; si repites esta sección allí, haz una copia de seguridad independiente.

### Comparación con dig sin dependencia externa

En el **cliente Ubuntu**, después de que funcione la entrada hosts y resolved esté activo:

```bash
resolvectl --network=no -4 query server.netlab.test
dig -r @127.0.0.53 server.netlab.test. A +time=2 +tries=1
```

`--network=no` impide que resolved consulte la red; así, una fuente local o la caché bastan, o se devuelve un error local. `dig -r` omite los ajustes personales de `.digrc`, `@127.0.0.53` selecciona el stub, el punto final convierte el nombre DNS en absoluto y las opciones limitan la espera/reintentos. Una configuración normal de resolved lee `/etc/hosts` y puede devolver `.20` a **ambos** comandos. Dig aun así envió una consulta DNS; el stub sintetizó la respuesta a partir de datos locales. Por tanto, decir «dig nunca devuelve entradas del archivo hosts» sería engañoso.

Si el stub está deshabilitado o resolved no lee el archivo hosts, esa rama puede no funcionar. Inspecciona la configuración actual del resolvedor en vez de habilitar un servicio. En **cualquiera de las dos distribuciones**, compara la consulta hosts con una consulta DNS al servidor del laboratorio:

```bash
dig -r @192.0.2.20 server.netlab.test. A +time=2 +tries=1
```

Esta es una **prueba intencional de fallo**: el servidor del curso no ejecuta un servicio DNS, así que se espera rechazo o timeout, no una respuesta. Una entrada hosts en el cliente no convierte al servidor en servidor DNS. Si aparece una respuesta inesperada, inspecciona qué está escuchando en el puerto 53 del servidor. Mantén las aplicaciones normales usando la asignación hosts; no configures DNS del sistema para que apunte a `.20`.

Sin `@SERVER`, dig lee `/etc/resolv.conf`, por lo que una prueba que parece local podría consultar el resolvedor upstream de la red de administración. Los comandos anteriores seleccionan explícitamente el destino.

### Cómo leer una respuesta DNS

La respuesta siguiente es un **ejemplo ilustrativo de un servicio DNS de laboratorio autoritativo hipotético**; no es una salida capturada ni un servicio creado en esta lección:

```text
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1234
;; flags: qr aa; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0
;; ANSWER SECTION:
server.netlab.test. 300 IN A 192.0.2.20
;; SERVER: 192.0.2.53#53(192.0.2.53) (UDP)
```

| Campo/estado | Interpretación |
|---|---|
| `SERVER` | El servidor que respondió a esta consulta, que no necesariamente es el origen autoritativo |
| `300 IN A 192.0.2.20` | TTL en segundos, clase Internet, tipo IPv4 y dirección |
| `aa` | Respuesta marcada como autoritativa para el nombre consultado; no garantiza conectividad ni identidad |
| `rd` / `ra` cuando aparecen | Se solicitó recursión / hay recursión disponible; ninguno demuestra una nueva consulta upstream |
| `NOERROR` con la respuesta esperada | La consulta DNS tuvo éxito; comprueba los datos |
| `NOERROR` sin los datos solicitados | Puede ser NODATA; inspecciona el contexto Authority/CNAME/referencia antes de concluir |
| `NXDOMAIN` | La respuesta DNS indica que el nombre consultado no existe; también puede proceder de caché o de una política |
| `SERVFAIL` | El resolvedor falló, por ejemplo, por problemas upstream o de validación |
| `REFUSED` | La política del servidor rechazó la consulta |
| Timeout | No llegó una respuesta utilizable durante el período de espera; no es NXDOMAIN |

`dig +short` oculta información útil de estado y servidor; durante el diagnóstico, usa la salida completa. Dig puede terminar con código 0 después de recibir una respuesta `NXDOMAIN`; el código de salida por sí solo no significa que se haya encontrado una dirección.

Puede haber caché en una aplicación, un servicio local y un resolvedor recursivo upstream. Que la segunda consulta sea rápida no demuestra por sí solo que hubiera un acierto de caché. En resolved, compara `resolvectl statistics`; las respuestas derivadas de hosts no necesariamente se comportan como registros DNS en caché. `sudo resolvectl flush-caches` vacía la caché DNS local de resolved, no `/etc/hosts`, las cachés de aplicaciones ni las cachés upstream. Cambia un estado efímero que se repuebla con las consultas y no existe una operación significativa para «restaurar la caché». No hace falta para este laboratorio; registra pruebas antes de considerarlo en una investigación de caché separada.

## 3. Inspecciona la ruta elegida y luego prueba la IP

En el **cliente**, vuelve a identificar la MAC del laboratorio y sustituye el nombre:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -br link
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
```

Un resultado de ruta ilustrativo:

```text
192.0.2.20 dev LAB_NIC src 192.0.2.10 uid 1000
```

`dev` selecciona la interfaz de salida, `src` la dirección de origen elegida y `via` indicaría un router de siguiente salto. Aquí el par está en el mismo enlace, así que no se necesita `via`. `LAB_NIC` es una etiqueta explicativa, no un nombre de dispositivo literal. `ip route get` hace una consulta de ruta local; no envía un ping ni demuestra que el par esté disponible o que funcione la ruta de retorno.

Si la consulta selecciona la NIC de administración, detente antes de sondear al par e inspecciona la dirección/prefijo del laboratorio y la configuración guardada. No elimines la ruta predeterminada de administración. En el **servidor**, `ip -4 route get 192.0.2.10` debería seleccionar su NIC de laboratorio con origen `.20`; las respuestas también necesitan una ruta de retorno válida.

En el **cliente**, compara loopback, su propia dirección y la del par:

```bash
ping -n -c 3 -W 2 127.0.0.1
ping -n -c 3 -W 2 192.0.2.10
ping -n -c 3 -W 2 192.0.2.20
```

`-n` suprime la búsqueda inversa de nombres, `-c 3` envía tres solicitudes Echo y `-W 2` limita la espera de respuesta cuando no llegan respuestas. Un destino numérico elimina de esta prueba la búsqueda de nombre hacia delante. `time` es el tiempo de ida y vuelta, no el ancho de banda. El `ttl` de la respuesta mostrada es el TTL restante del paquete recibido; sin conocer su valor inicial, no permite calcular exactamente el número de saltos.

Que responda loopback prueba la pila local. El ping a tu propia dirección de laboratorio normalmente se atiende localmente y no prueba el cable virtual. Las respuestas del par muestran un intercambio ICMP Echo bidireccional en ese momento, no el acceso a un puerto TCP. Tres respuestas ausentes aportan evidencia sobre tres sondeos; hace falta investigar filtrado, límites de respuesta, direccionamiento incorrecto y problemas de ruta de retorno.

Después de sondear al par, inspecciona la entrada de vecinos del **cliente**:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip neigh show to 192.0.2.20 dev "$LAB_IF"
```

Una MAC con `REACHABLE` o `STALE` indica una asignación de vecino conocida; `STALE` no significa fallo. `INCOMPLETE`/`FAILED` sugiere que la resolución ARP no tuvo éxito. Comprueba la conexión de ambos adaptadores a la red interna, la dirección del par, el estado del enlace y la posibilidad de una IP duplicada. DNS no proporciona la MAC de destino Ethernet.

## 4. Interpreta traceroute y tracepath con cuidado

En el **cliente**, ejecuta las herramientas que preparaste:

```bash
traceroute -4 -n -m 4 -q 1 -w 1 192.0.2.20
timeout 15s tracepath -4 -n -m 4 192.0.2.20
```

Linux traceroute normalmente usa sondeos UDP. `-m 4` limita el TTL máximo, `-q 1` usa un sondeo por TTL y `-w 1` limita la espera de cada sondeo. Tracepath también usa UDP e informa sobre MTU de ruta; `timeout` externo limita su duración total. Con un par directo y respuestas permitidas, se espera llegar al destino en TTL 1. Un switch Ethernet virtual no es un router IP y no añade un salto a traceroute.

Los routers pueden devolver ICMP Time Exceeded cuando vence el TTL de un sondeo. Un destino puede devolver ICMP Port Unreachable para un sondeo dirigido a un puerto UDP cerrado. Estas respuestas de control revelan partes de una ruta; no registran la ruta de cada paquete.

Un `*` en traceroute o `no reply` en tracepath significa que no llegó ninguna respuesta coincidente antes del timeout. **No** demuestra que ese salto haya descartado tráfico normal de la aplicación. El filtrado, los límites de frecuencia, los distintos protocolos de sondeo y las rutas asimétricas de retorno pueden explicar la falta de respuestas. Los saltos posteriores o la aplicación todavía podrían responder.

Para comparar opcionalmente **ICMP** con el mismo par, si la versión instalada de Linux traceroute lo admite:

```bash
sudo traceroute -4 -I -n -m 4 -q 1 -w 1 192.0.2.20
```

`-I` usa sondeos ICMP Echo; sudo permite los sondeos sin procesar cuando hace falta. Los resultados distintos pueden reflejar políticas específicas del protocolo. Estos comandos no cambian configuración persistente. No deshabilites el firewall solo para que la traza se vea mejor.

## 5. Distingue TCP de HTTP con un servicio local

No se presupone que SSH o un servidor web ya estén instalados. Crearemos un servicio HTTP temporal con Python ya disponible, enlazado solo a la **dirección del laboratorio del servidor**.

### Inicia un servicio de duración limitada en el servidor

En el **terminal A del servidor**, confirma que `.20` pertenece a la NIC del laboratorio y que ningún listener TCP existente usa el puerto 18080:

```bash
ip -br address
ss -ltn 'sport = :18080'
```

Si hay un listener, identifícalo; no termines otro servicio. Elige un puerto libre y adapta esta sección de forma coherente, o termina primero el laboratorio anterior.

En el mismo **terminal A del servidor**, crea un directorio nuevo y sírvelo como usuario normal:

```bash
LAB_HTTP_DIR=$(mktemp -d /tmp/network-beginner-04.XXXXXX)
printf '%s\n' "$LAB_HTTP_DIR"
printf 'network lab ok\n' > "${LAB_HTTP_DIR:?missing lab directory}/index.html"
timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"
```

Detente si falla `mktemp`. `${variable:?message}` impide usar una variable de ruta vacía. Registra la ruta del directorio que se imprime. Solo el directorio nuevo contiene el archivo servido; no sirvas tu directorio personal ni le añadas enlaces simbólicos. `--bind` evita que el listener use todas las interfaces, `--directory` selecciona la raíz del contenido y `timeout` termina el servidor después de cinco minutos. Ctrl+C lo detiene antes. Se espera el código de salida 124 de timeout cuando se cumple el límite de tiempo.

Si el temporizador vence durante el ejercicio, reinicia desde el mismo terminal A del servidor con `timeout 300s python3 -m http.server 18080 --bind 192.0.2.20 --directory "${LAB_HTTP_DIR:?missing lab directory}"`; reutiliza el directorio registrado en vez de volver a ejecutar `mktemp`.

El servidor HTTP integrado en Python es una herramienta de práctica. Aquí no tiene autenticación/TLS y no es un despliegue de producción. No se crea ningún servicio del sistema ni activación durante el arranque.

En el **terminal B del servidor**, mientras A siga ejecutándose:

```bash
ss -ltn 'sport = :18080'
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
```

Se espera un listener en `192.0.2.20:18080`, HTTP 200 y `network lab ok`. HTTP/1.0 en la respuesta es normal para este servidor Python, incluso en la ruta con Python 3.9 de Rocky. Esta solicitud desde el propio servidor valida el comportamiento local de la aplicación, no la ruta desde el cliente. Si el enlace informa «Cannot assign requested address», inspecciona la dirección del servidor del capítulo 03. Si informa de un permiso denegado, investiga ese fallo en vez de deshabilitar SELinux.

### Prueba TCP desde el cliente

En el **cliente Ubuntu con OpenBSD netcat**:

```bash
nc -n -z -v -w 3 192.0.2.20 18080
```

En el **cliente Rocky con Ncat**, el equivalente es:

```bash
ncat -n -z -v -w 3 192.0.2.20 18080
```

`-n` evita DNS, `-z` prueba el establecimiento de conexión sin una carga de aplicación, `-v` informa del resultado y `-w 3` limita la espera de conexión. El éxito demuestra que se pudo establecer una conexión TCP con ese endpoint, no que HTTP funcione. Un rechazo suele indicar un puerto cerrado o un rechazo activo; un timeout puede deberse a filtrado, vecinos no resueltos, un par caído o un problema de ruta de retorno.

Un firewall del sistema invitado, especialmente una política configurada de firewalld en Rocky, puede bloquear este puerto nuevo. Compara el listener/la solicitud local del servidor con la evidencia de ruta/vecino/TCP del cliente y registra un **posible límite de política**. Este capítulo no modifica reglas del firewall; el [capítulo 06](06-firewalls-host-security.md) enseña cambios de política acotados. Si la prueba remota está bloqueada, completa las observaciones HTTP en el terminal B del servidor y conserva el fallo del cliente para esa lección posterior. No informes que HTTP remoto tuvo éxito basándote en la solicitud del propio servidor.

### Prueba HTTP y luego compara nombres

En el **cliente**, mientras el servicio siga activo:

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://server.netlab.test:18080/
```

La primera opción, `--disable`, omite la configuración predeterminada de curl; `--noproxy '*'` evita un proxy HTTP heredado. `--connect-timeout` limita el establecimiento de conexión, `--max-time` toda la operación e `-i` incluye las cabeceras de respuesta. El segundo comando usa la búsqueda de nombres del cliente. Si funciona la URL numérica pero falla la de nombre, compara `getent ahostsv4` con el error de curl antes de tocar las rutas.

Para aislar la búsqueda en **esta única invocación de curl**, conserva el nombre de host, pero proporciona la dirección conocida del laboratorio:

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  --resolve server.netlab.test:18080:192.0.2.20 \
  -i http://server.netlab.test:18080/
```

`--resolve` solo cambia la asignación de curl para ese nombre de host/puerto; no modifica el archivo hosts ni un registro DNS, y no requiere reversión. La cabecera HTTP Host sigue usando el nombre. En HTTPS real también importan la comprobación de certificados basada en nombre y TLS SNI; sustituir un nombre de host por una IP no siempre equivale a probar la aplicación. No omitas las comprobaciones de certificados para decir que TLS está «arreglado».

Crea un fallo inocuo de la capa de aplicación solicitando un archivo que nunca se creó:

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:18080/missing-page
```

Si se puede acceder al servidor, se espera HTTP **404**. La ruta de nombre/IP y el transporte TCP funcionaron lo suficiente para devolver un error HTTP; la página solicitada no existe. Sin `--fail`, curl puede terminar con código 0 para un HTTP 404, así que lee la línea de estado. `curl -I` enviaría **HEAD**, no GET ocultando simplemente su cuerpo.

## 6. Elige la siguiente prueba según la evidencia

Usa esta tabla de decisiones en orden, pero vuelve a una fila anterior si nueva evidencia contradice una suposición. Los ejemplos describen posibilidades, no diagnósticos automáticos.

| Observación | Qué queda establecido | Siguiente comprobación que permite distinguir causas |
|---|---|---|
| La consulta solo en archivos no encuentra `.20` | Falta la asignación local o es incorrecta | Ortografía exacta, bloque `/etc/hosts` y entradas duplicadas |
| Funciona solo en archivos; falla getent normal | Las fuentes se comportan de manera distinta | Orden/reglas de retorno de NSS, módulos y familia de direcciones |
| Funciona getent; falla dig a `.20` | La asignación local funciona; no se espera que `.20` ofrezca DNS | Usa la entrada hosts; inspecciona el resolvedor real solo si necesitas DNS |
| DNS `NXDOMAIN` | Llegó una respuesta DNS negativa | Ortografía de la consulta, resolvedor/vista, datos autoritativos y caché negativa |
| Timeout DNS | No hubo respuesta DNS utilizable dentro del límite | `ip route get` al resolvedor, conectividad al puerto 53, servicio/política del resolvedor |
| La ruta selecciona la NIC de administración o un origen incorrecto | La selección de reenvío local no corresponde a este laboratorio | Dirección/prefijo del laboratorio, propietario persistente, inventario de rutas/reglas |
| Ruta correcta; vecino `FAILED` | Falló la resolución de MAC del siguiente salto | Red/cable del hipervisor, dirección del par, estado del enlace y conflictos |
| Existe el vecino; falla ping | Se conoce la MAC, pero no llegó respuesta ICMP | Ruta de retorno del servidor, política ICMP y luego el puerto TCP previsto |
| Ping funciona; TCP es rechazado | ICMP funciona; TCP se rechazó activamente | `ss` del servidor, duración/dirección de enlace del servicio, política de rechazo |
| Funciona HTTP local del servidor; el TCP del cliente agota el tiempo | Funciona el servicio local; la ruta remota sigue sin comprobarse | Rutas, vecinos y política de ambos; registra evidencia para el capítulo 06 |
| TCP conecta; HTTP se bloquea o no es válido | Funciona el establecimiento de conexión | Protocolo/puerto correcto, registros de la aplicación y comportamiento de respuesta |
| HTTP 404/403/500 | El endpoint HTTP devolvió un resultado de aplicación | Ruta solicitada, permisos de aplicación o error del servicio; no es una corrección de DNS |
| Funciona HTTP numérico; falla HTTP por nombre | El endpoint conocido funciona sin la consulta normal | Resultado de getent, error de resolución de curl, comparación mediante `--resolve` por solicitud |
| Traceroute muestra `*`; funciona HTTP | Esos sondeos no recibieron respuestas; la aplicación tuvo éxito | Protocolo de sondeo/límites de frecuencia; no hay motivo para afirmar una pérdida total de paquetes |

Entre los códigos de salida útiles de curl están **6** (no pudo resolver el nombre), **7** (no pudo conectarse) y **28** (se agotó el tiempo de la operación). Indican una etapa, no necesariamente la causa raíz. Registra el comando, la VM desde la que se ejecutó, la hora (`date -Is`), destino, salida, código de salida (`echo $?` inmediatamente después), resultado esperado y siguiente prueba. Separa «observado» de «supuesto».

## 7. Observación opcional de DNS público

**Dependencia externa:** ejecútala solo si la red de administración existente y sin cambios del cliente ya proporciona acceso a Internet permitido y permite consultas al resolvedor seleccionado. No es un requisito para completar la lección, y un fallo por sí solo no dice nada sobre el laboratorio aislado `.10` ↔ `.20`. No añadas un enlace ascendente ni un servidor DNS público a la NIC del laboratorio.

```bash
ip -4 route get 1.1.1.1
dig -r @1.1.1.1 example.com. A +time=2 +tries=1
dig -r @1.1.1.1 example.com. AAAA +time=2 +tries=1
dig -r @1.1.1.1 example.com. NS +time=2 +tries=1
```

Inspecciona la ruta antes de enviar las consultas; debería usar la ruta de administración ya existente. Si la política exige otro resolvedor aprobado, sustituye de forma coherente su dirección conocida. Observa el estado DNS, servidor, tipos de registro y TTL sin esperar IP públicas fijas. Repite una vez la consulta A y compara el TTL, pero no deduzcas dónde está la caché basándote solo en el tiempo. `+tcp` permite comparar DNS sobre TCP con la consulta A habitual sobre UDP. No consultes nombres privados/internos a través de resolvedores públicos.

Una respuesta NS identifica información de autoridad; una respuesta recursiva de `1.1.1.1` no se convierte por ello en una respuesta autoritativa de la zona. `dig +trace` sigue delegaciones DNS, no saltos de routers IP como traceroute, y añade dependencias externas; queda fuera de este ejercicio local.

## 8. Limpieza y finalización

En el **terminal A del servidor**, detén el proceso de Python con Ctrl+C o deja que venza su temporizador. En el terminal B, comprueba con `ss -ltn 'sport = :18080'` que ya no esté el listener de esta lección.

En el **mismo shell del terminal A donde creaste el directorio**, inspecciónalo y elimina solo su archivo y el directorio vacío:

```bash
printf '%s\n' "$LAB_HTTP_DIR"
ls -la -- "${LAB_HTTP_DIR:?missing lab directory}"
rm -i -- "${LAB_HTTP_DIR:?missing lab directory}/index.html"
rmdir -- "${LAB_HTTP_DIR:?missing lab directory}"
unset LAB_HTTP_DIR
```

Si cerraste ese shell, asigna a `LAB_HTTP_DIR` la ruta exacta que registraste y verifica su contenido antes de este bloque. Nunca la adivines con un comodín amplio. `rmdir` se niega a borrar un directorio que no esté vacío, lo que ayuda a detectar archivos inesperados.

En cada sistema invitado donde editaste `/etc/hosts`, usa `sudoedit /etc/hosts` para quitar solo las líneas entre `# BEGIN network-beginner-04` y `# END network-beginner-04`, incluidas las dos líneas delimitadoras. Compara con `sudo diff -u /root/network-beginner-04/hosts-before /etc/hosts`; si no hay salida, se restauró el contenido original cuando no hubo ediciones ajenas a la lección. Conserva cualquier edición legítima intercalada en vez de sobrescribirla con la copia de seguridad.

Verifica que `getent -s files hosts server.netlab.test` ya no devuelva la asignación de esta lección. No exijas que todos los resolvedores olviden el nombre de inmediato. Las direcciones estáticas del capítulo 03 y los ajustes de administración permanecen para SSH.

Antes de continuar, deberías poder:

- Explicar getent/NSS, dig y resolved usando las fuentes reales de tu sistema invitado.
- Resolver `.20` localmente sin DNS público y explicar el fallo intencional de dig.
- Interpretar una respuesta DNS, incluidos TTL, estado autoritativo y resultados negativos.
- Mostrar la ruta/origen de laboratorio seleccionados y distinguir la evidencia de loopback, vecino y par.
- Explicar por qué los asteriscos de trace no demuestran pérdida de paquetes de la aplicación.
- Comparar una prueba TCP, HTTP 200 y HTTP 404, e identificar qué sistema invitado produjo cada resultado.
- Clasificar cualquier prueba remota bloqueada con evidencia y una comprobación siguiente; no sustituirla por un éxito local.
- Eliminar el servidor temporal, sus archivos y las entradas hosts sin cambiar ajustes de red/firewall.

## Fuentes principales y lecturas adicionales

- [Ubuntu Server: nombres y NSS](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/), [manual de getent](https://manpages.ubuntu.com/manpages/noble/en/man1/getent.1.html)
- [Manual de BIND dig](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility), [resolvectl en Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/en/man1/resolvectl.1.html)
- [Conceptos de DNS: RFC 1034](https://www.rfc-editor.org/rfc/rfc1034.html), [caché negativa: RFC 2308](https://www.rfc-editor.org/rfc/rfc2308.html), [nombres de prueba: RFC 2606](https://www.rfc-editor.org/rfc/rfc2606.html)
- [ping](https://manpages.ubuntu.com/manpages/noble/en/man8/ping.8.html), [tracepath](https://manpages.ubuntu.com/manpages/noble/en/man8/tracepath.8.html), [manual de Linux traceroute incluido en Ubuntu](https://manpages.ubuntu.com/manpages/noble/en/man1/traceroute.db.1.html)
- [OpenBSD nc](https://man.openbsd.org/nc), [Ncat](https://nmap.org/book/ncat-man.html), [manual de curl](https://curl.se/docs/manpage.html), [servidor HTTP de Python](https://docs.python.org/3.12/library/http.server.html)
- Continúa después con [diagnóstico de red en Linux](../07-linux-network-diagnostics.md) para interpretar paquetes, colas TCP y MTU.

[Anterior: configuración persistente](03-persistent-configuration.md) · [Cuestionario](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) · [Siguiente: acceso SSH](05-ssh-access.md)
