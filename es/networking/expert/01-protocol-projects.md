# Proyectos de protocolos: explicar los bytes y las respuestas que faltan

> **Entorno base del laboratorio**: máquina virtual propia con Ubuntu Server 24.04 LTS o Rocky Linux 9; análisis sin conexión y tráfico limitado por loopback
>
> **Última actualización**: 15 de septiembre de 2026

## Propósito y criterios de entrada {#purpose}

Una investigación experta de protocolos relaciona una afirmación de la aplicación con un intercambio específico y señala qué no permiten establecer las pruebas.
Este cuaderno produce un registro de correlación de sondas, un conjunto de evidencias HTTP/TCP y un informe sobre los límites entre protocolos.
Son ejercicios originales, no soluciones de trabajos universitarios evaluados.

Primero, completa las [ocho lecciones para principiantes](../beginner/README.md), incluida la restauración y el diagnóstico final del servicio.
Debes poder distinguir una dirección, el siguiente salto, una respuesta DNS, un socket en escucha y un estado HTTP.
También necesitas conocimientos básicos para leer Python, familiaridad con la notación de bytes/hexadecimal y la capacidad de comparar dos archivos.

Antes de recopilar pruebas, lee estas guías existentes:

- [IP, ICMP y traceroute](../../basics/06-network-fundamentals-part1.md#icmp-traceroute-interpretation): identifica quién envió un error y qué paquete cita.
- [TCP y TLS](../../basics/06-network-fundamentals-part2.md): distingue la entrega del transporte de la autenticación.
- [Estructura de mensajes HTTP/1.1](../../basics/06-network-fundamentals-part3.md#http11-message-structure): localiza el terminador de encabezados y cuenta los bytes del contenido.
- [Diagnóstico de redes Linux](../07-linux-network-diagnostics.md): entiende el helper HTTP limitado existente y el ejercicio de enrutamiento registrado.

## Mapa del plan de estudios público {#readings}

La disponibilidad se comprobó el **15 de septiembre de 2026**.
El sitio de CS168 para otoño de 2026 [está en construcción](https://fa26.cs168.io/).
Usa el [archivo oficial accesible del verano de 2026](https://su26.cs168.io/) para seguir el orden de lectura que se indica a continuación; sus fechas son históricas.
Que una especificación sea accesible no garantiza matrícula, acceso a todas las grabaciones ni acceso a un evaluador institucional.

| Material público | Para qué leerlo | Entregable original aquí |
|---|---|---|
| Archivo Intro 1–3; capas, encabezados y diseño del [libro de texto CS168](https://textbook.cs168.io/) | Demultiplexación y entrega de mejor esfuerzo | Etiquetar cada encabezado y el componente que lo interpreta |
| [Guía del Proyecto 1](https://su26.cs168.io/proj1/guide/) e [instrucciones de Project 1A](https://su26.cs168.io/proj1/proj1a/) | Sondas UDP limitadas por TTL y paquetes citados | Proyecto A: correlacionar respuestas con un registro de envíos |
| [Instrucciones de Project 1B](https://su26.cs168.io/proj1/proj1b/) | Respuestas incompletas, ajenas y repetidas | Rechazar pruebas engañosas sin inventar saltos |
| Archivo Routing 1–7; [instrucciones de Project 2](https://su26.cs168.io/proj2/) | Estado de enrutamiento frente a comportamiento de reenvío | Continuar con [política de enrutamiento y convergencia](02-routing-policy-convergence.md) |
| Archivo Transport 1–4; [instrucciones de Project 3](https://su26.cs168.io/proj3/) | Espacio de secuencia, ventanas de recepción, retransmisión y temporizadores | Proyecto B: distinguir entrega de flujo, entramado y congestión |
| Lecturas del archivo sobre DNS, HTTP/CDN y TLS de extremo a extremo | Nombres, seguridad y límites de las aplicaciones | Proyecto C: elegir las pruebas necesarias para cada límite |

Project 3 de CS168 implementa un **subconjunto de TCP sin control de congestión**.
Lee las clases sobre congestión por separado; aprobar un trabajo de transporte no demuestra que se haya implementado un controlador de congestión apto para producción.
La configuración archivada contiene notas de prueba para Python 3.7 y nombres de directorios mezclados entre semestres.
Si eliges ese trabajo opcional, sigue su propia configuración y registra la revisión exacta que descargaste; no rebajes la versión de Python de la máquina virtual de este cuaderno.
El libro de texto se identifica como beta: usa las especificaciones de protocolos para resolver detalles de implementación.

Como continuación opcional, **CS144 en C++** es adecuado cuando ya puedas razonar sobre flujos de bytes, propiedad de recursos, herramientas de compilación y depuración.
Durante esta comprobación, la entrada histórica `cs144.github.io` no estaba disponible; el error 404 informado no sirve como requisito previo para el laboratorio.
Antes de elegir un período, vuelve a comprobar la oferta oficial de Stanford y las instrucciones actuales.
Registra qué repositorio inicial, licencia, compilador y pruebas están realmente disponibles.
Este cuaderno no promete acceso gratuito a un repositorio/evaluador actual ni una vía de matrícula.
Los criterios para completarlo no exigen CS144 y aquí no se reproduce código de implementaciones evaluadas.

## Disponibilidad de herramientas y contrato de evidencias {#readiness}

Vuelve a las [herramientas para invitados principiantes](../beginner/README.md#guest-tools); poder ejecutar un comando es un requisito que hay que comprobar, no dar por hecho.
Usa el flujo de vista previa/instalación de paquetes seleccionados de esa página solo dentro de tu máquina virtual descartable.
Si el proveedor `curl-minimal` existente de Rocky funciona, consérvalo.

| Función en este cuaderno | Paquete/proveedor de Ubuntu | Paquete/proveedor de Rocky | ¿Se requiere aquí? |
|---|---|---|---|
| Cliente HTTP e informe de versión | `curl` existente | `curl-minimal` o `curl` existente | Sí |
| Servidor limitado y análisis | `python3`, versión 3.9 o posterior | `python3`, versión 3.9 o posterior | Sí |
| Observaciones de sockets/direcciones | `iproute2` | `iproute` | Sí |
| Captura y decodificación sin conexión | `tcpdump` | `tcpdump` | Para evidencia medida de paquetes |
| Límite de tiempo real y hash | `coreutils` | `coreutils` | Sí |
| Sondas de ruta opcionales para más adelante | `traceroute`; `tracepath` de principiantes es otra herramienta | `traceroute`; `tracepath` viene de `iputils` | No, el Proyecto A es sin conexión |
| Investigación DNS opcional | `bind9-dnsutils` | `bind-utils` | No se requiere una consulta DNS en vivo |

Dentro de la máquina virtual, desde una copia local de este repositorio:

```bash
command -v python3 curl ip ss timeout sha256sum tcpdump
python3 --version
curl --version
ip -Version
ss -V
tcpdump --version
sha256sum examples/networking/foundations/http_lab.py
```

Registra la versión del sistema invitado, el kernel, la revisión del repositorio, el hash del helper, las versiones de las herramientas y la lista de funciones de curl.
Si curl no incluye una función HTTP2/HTTP3, es una limitación de capacidad del cliente, no un fallo del servidor.
Antes de empezar, comprueba `ss -ltn 'sport = :18080'`; si hay algún proceso escuchando, detente y elige otro puerto libre que usarás de forma coherente.
No termines nunca un proceso de escucha ajeno al ejercicio.

Usa un directorio de evidencias por intento, creado con `mkdir -m 700 protocol-evidence-01`; si ya existe, elige un nombre nuevo.
Los ejemplos usan ese nombre desde la raíz del repositorio.
Las capturas solo deben incluir contenido sintético de la lección; no se necesitan credenciales, cookies ni tráfico real de usuarios.
Etiqueta cada elemento como `measured`, `imported`, `synthetic` o `design-only` e indica la hora, el observador, el espacio de nombres y el filtro de captura.
Una transcripción proporcionada no es una medición realizada en tu máquina virtual.

## Conceptos que debes aplicar en todos los proyectos {#concepts}

| Límite | Invariante o distinción | Evidencia insuficiente |
|---|---|---|
| IP → transporte | Protocol/Next Header selecciona el siguiente analizador | El puerto 443 por sí solo no demuestra que se use HTTPS o QUIC |
| Sonda → error ICMP | El error cita el paquete que lo desencadenó | La dirección exterior del router por sí sola no identifica una sonda |
| TCP → aplicación | TCP entrega un flujo de bytes ordenado | El límite de una llamada a `send()` o `recv()` no marca el límite de un mensaje HTTP |
| Receptor → emisor | La ventana de recepción anunciada limita la presión sobre el receptor | La asignación del búfer de recepción no es la ventana de congestión |
| Red → emisor | El control de congestión limita la carga en la ruta | Una retransmisión por sí sola no localiza la congestión |
| Aplicación → usuario | El estado/cuerpo HTTP describen el resultado de una aplicación | Establecer TCP no demuestra que la operación solicitada tuviera éxito |

Usa [TCP RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html) para entender la semántica del flujo y el espacio de secuencia.
En una explicación basada en ventanas, la cantidad efectiva permitida en tránsito depende tanto de `cwnd` como de la ventana de recepción, después de descontar los bytes pendientes.
El pacing, los datos disponibles en la aplicación y los detalles de implementación también limitan los envíos.
Un ACK puro no consume espacio de secuencia; SYN y FIN consumen una posición cada uno.
## Proyecto A: registro para correlacionar sondas {#probe-project}

**Propósito:** explicar una observación incompleta de la ruta sin convertir respuestas ajenas en saltos.
**Entorno:** papel o editor local; no se envían paquetes ni se crea ningún router.
Lee la guía de traceroute de CS168 y luego [ICMP RFC 792](https://www.rfc-editor.org/rfc/rfc792.html).
Vuelve a usar la [guía de enrutamiento/ICMP](../07-linux-network-diagnostics.md#routing-icmp-lab) para reconocer el método de sonda ICMP Echo que utiliza; es distinto del método UDP de CS168.

Crea este **registro sintético de envíos** original. Las direcciones siguientes son direcciones reservadas para documentación, no destinos de las sondas:

```text
run,probe,ttl,src,dst,protocol,sport,dport
paper-01,A,1,192.0.2.10,198.51.100.20,UDP,41000,33451
paper-01,B,2,192.0.2.10,198.51.100.20,UDP,41000,33452
paper-01,C,3,192.0.2.10,198.51.100.20,UDP,41000,33453
```

Considera lo siguiente registros decodificados, **no una captura pcap ni tiempos medidos**:

| Registro en orden de recepción | Respuesta exterior | Paquete original citado | Tarea |
|---|---|---|---|
| R1 | `192.0.2.1`, ICMP 11/0 | Encabezado IPv4 + UDP completo de A | Completar |
| R2 | `192.0.2.1`, ICMP 11/0 | Cita idéntica a R1 | Completar |
| R3 | `203.0.113.7`, ICMP 11/0 | Tupla de B, salvo que el destino es `198.51.100.99` | Completar |
| R4 | `198.51.100.20`, ICMP 3/3 | Encabezado IPv4 + UDP completo de C | Completar |
| R5 | `203.0.113.8`, ICMP 11/0 | El encabezado IPv4 citado termina antes de los puertos UDP | Completar |

Crea un registro con los campos `record`, `candidate_probe`, `decision`, `reason`, `confidence` y `missing_fields`.
Usa decisiones distintas para los casos coincidentes, duplicados, ajenos y con evidencia insuficiente.
No inventes una respuesta para B solo para que el diagrama parezca continuo.

Después, añade tres casos propios:

1. Una respuesta tardía de una ejecución anterior que reutilizó los mismos puertos.
2. Un encabezado IPv4 citado válido con opciones, de modo que su longitud supere los 20 bytes.
3. Una respuesta recibida después de la hora límite de observación declarada.

Indica qué identificadores y ventanas de envío/recepción permitirían distinguir cada caso y cuándo la cita disponible no bastaría.
Una cita ICMP puede ser demasiado corta para incluir un nonce de aplicación; no dependas de bytes que no estén disponibles.
Para una sonda ICMP Echo, correlaciona el identificador y número de secuencia citados en vez de inventar puertos UDP.

**Observaciones esperadas:** A respalda una respuesta con TTL 1; el mensaje Port Unreachable correlacionado con C confirma que la sonda UDP llegó al destino.
**Observaciones negativas:** R2 no es el resultado de una sonda nueva; R3 no satisface la evidencia de B; R5 no permite identificar una tupla de forma única.
Si no hay una respuesta coincidente para B dentro de la ventana de captura, se desconoce el resultado, aunque responda un salto posterior.
Esto no demuestra que el router de B descarte el tráfico reenviado de la aplicación.

El RTT de traceroute incluye la ruta de respuesta y el comportamiento del router al responder.
Cambiar los puertos de las sondas puede cambiar la selección ECMP; una lista de direcciones que respondieron no demuestra que exista una única ruta estable de aplicación.
**Restauración:** conserva inalterables los registros originales; si vuelves a empezar, descarta solo el registro de trabajo derivado.
**Finalización:** cada decisión cita los campos recibidos o un campo que falta, y los tres casos añadidos tienen reglas explícitas para rechazar respuestas o indicar incertidumbre.

## Proyecto B: límites HTTP en un único flujo TCP {#stream-project}

**Propósito:** demostrar que la longitud de la aplicación, los bytes TCP y los segmentos observados responden preguntas distintas.
**Entorno:** una máquina virtual propia, cliente/servidor en `127.0.0.1:18080`, sin destino externo ni proxy.
Solo se requiere `sudo` para la captura; ejecuta el servidor y los clientes como usuario normal.
Limita el ejercicio a las solicitudes siguientes, de una en una; envía como máximo diez solicitudes y ningún cuerpo de solicitud puede superar los 4096 bytes.

En una terminal A, inicia el helper existente desde la raíz del repositorio:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 180
```

Cuando aparezca el socket en escucha, inicia la captura en una terminal B, también desde la raíz del repositorio:

```bash
sudo timeout --signal=INT --kill-after=2s 20s \
  tcpdump -i lo -p -nn -U -s 512 -c 120 -w - \
  'tcp port 18080' > protocol-evidence-01/http.pcap \
  2> protocol-evidence-01/capture.log
```

Antes de enviar solicitudes en la terminal C, espera a que el registro muestre la línea «listening on».
El shell crea el archivo de salida con tu usuario; tcpdump escribe los bytes de pcap en stdout.
La captura se detiene al llegar a 120 paquetes o 20 segundos; el código de salida 124 de timeout indica que venció el temporizador, no que haya fallado la red.
Conserva el estado de salida y los contadores finales de la captura. Un snaplen de 512 bytes puede truncar la carga útil; registra ese límite.

```bash
curl --disable --noproxy '*' --max-time 3 --http1.1 -i \
  http://127.0.0.1:18080/lesson
curl --disable --noproxy '*' --max-time 3 --http1.1 -I \
  http://127.0.0.1:18080/lesson
printf 'phase=one\nphase=two\n' | \
  curl --disable --noproxy '*' --max-time 3 --http1.1 -i \
  --data-binary @- http://127.0.0.1:18080/echo
curl --disable --noproxy '*' --max-time 3 --http1.1 -i \
  http://127.0.0.1:18080/missing
```

La entrada del echo tiene **20 bytes**, incluidos los dos caracteres LF.
Guarda cada respuesta por separado en tus notas y localiza el estado, Content-Length y el contenido real.
GET `/lesson` tiene seis bytes de contenido; HEAD describe esa representación sin devolver su cuerpo.
La ruta que falta debería producir HTTP 404; si no se usa `--fail`, curl puede terminar correctamente pese a ese error HTTP.
Eso significa que la comunicación HTTP tuvo éxito, aunque la búsqueda del recurso no.

Decodifica la captura completa sin privilegios:

```bash
tcpdump -nn -tttt -vv -r protocol-evidence-01/http.pcap \
  'tcp port 18080'
sha256sum protocol-evidence-01/http.pcap
```

Usa el [manual de tcpdump](https://www.tcpdump.org/manpages/tcpdump.1.html) para explicar los indicadores, los rangos de secuencia y los descartes de captura.
Elige una conexión mediante sus dos pares de extremos e identifica SYN, SYN-ACK, ACK, los rangos de carga útil y el cierre, si se capturó.
No exijas una cantidad determinada de paquetes ni un segmento por solicitud; señala los handshakes o cierres que falten como límites de la recopilación.
Para las reglas de bytes HTTP sin procesar, consulta [RFC 9112](https://www.rfc-editor.org/rfc/rfc9112.html) y el [manual de curl](https://curl.se/docs/manpage.html).

**Ejercicio original de entramado, sin conexión:** diseña un analizador para un largo sin signo de dos bytes en orden big-endian, seguido de esa cantidad de bytes de carga útil, con un máximo de 64 bytes.
La entrada sintética es `00 03 63 61 74 00 02 6f 6b`; corresponde a tu propio protocolo, no a HTTP.
Traza estas particiones de entrega: todos los bytes a la vez; un byte cada vez; división después del primer byte de longitud; división dentro del primer cuerpo.
Después de cada entrega, registra los bytes almacenados, los bytes que faltan y los registros emitidos.
Añade EOF en medio de un cuerpo y una longitud de 65; define un fallo acotado, no una espera indefinida ni una asignación de memoria ilimitada.
Puedes implementar tu propio analizador sin conexión, pero para cumplir el ejercicio basta con una tabla de estados y todos los casos completos.

**Ejercicio original sobre ventanas, sin conexión:** supón un MSS de 1000 bytes, un `cwnd` de 4 segmentos, una ventana de recepción de 9000 bytes y 3000 bytes ya pendientes.
Calcula el permiso adicional mediante `max(0, min(cwnd × MSS, rwnd) − outstanding)`, sin tener en cuenta el pacing y suponiendo que la aplicación tiene datos listos.
Repite el cálculo cambiando solo `rwnd` a 3500 bytes y luego a cero; identifica qué lado limita en cada caso.
Explica por qué una ventana de recepción igual a cero no demuestra congestión de red y por qué una retransmisión por sí sola no demuestra que se haya agotado la capacidad del receptor.
Son estados sintéticos, no una simulación completa de un emisor TCP ni mediciones de rendimiento.

**Observaciones esperadas:** todas las particiones completas producen los mismos dos registros lógicos; el echo HTTP conserva sus 20 bytes de entrada.
**Observaciones negativas:** no se debe informar como completo un registro incompleto ni aceptar la trama sobredimensionada.
En el modelo simplificado especificado, los estados de ventana permiten enviar 1000, 500 y cero bytes adicionales, respectivamente; cualquier permiso negativo se limita a cero.
Los errores de checksum aparentes en paquetes salientes pueden deberse a la observación de offload; un descarte de captura no equivale automáticamente a pérdida en la ruta.
**Restauración:** detén solo el helper en primer plano con Ctrl+C o deja que venza su temporizador de 180 segundos; la captura tiene su propio límite.
Vuelve a comprobar el filtro del socket en escucha. Conserva la evidencia; si decides descartarla, elimina solo los archivos/directorio indicados por nombre.
## Proyecto C: demostrar un límite, no solo un número de puerto {#boundary-project}

**Propósito:** planificar las pruebas mínimas para distinguir fallos de resolución de nombres, transporte, seguridad y aplicación.
**Entorno:** informe sin conexión basado en trazas propias existentes, si las hay; no hace falta sondear sitios públicos.

| Caso | Evidencia que se debe solicitar | Conclusión errónea que se debe rechazar |
|---|---|---|
| DNS devuelve un registro A; falla la conexión TCP | Resultado del resolver, dirección seleccionada, error de conexión y captura del endpoint | «Si DNS funciona, el servicio funciona» |
| Existe AAAA, pero el invitado no tiene una ruta IPv6 utilizable | Estado de ruta/dirección por familia y selección del cliente | «Una respuesta DNS IPv6 demuestra que IPv6 es accesible» |
| Se establece TCP, pero falla la verificación del certificado TLS | Hostname previsto, error de confianza/verificación e identidad del endpoint TLS | «Desactiva la verificación del certificado para demostrar que se solucionó» |
| La solicitud HTTPS negocia HTTP/1.1 | Funciones del cliente y versión HTTP negociada | «El puerto 443 o `--http2` demuestran que se usa HTTP/2» |
| HTTP/2 transporta varios flujos sobre TCP | ID de flujos y evidencia de pérdidas de conexión/transporte | «La multiplexación elimina el bloqueo de cabecera de línea de TCP» |
| Se sospecha HTTP/3 | Evidencia de QUIC/versión y de negociación de la aplicación obtenida en un endpoint | «Todos los paquetes UDP/443 son HTTP/3» |

Lee [HTTP/2 RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [QUIC RFC 9000](https://www.rfc-editor.org/rfc/rfc9000.html) y [HTTP/3 RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html).
HTTP/2 multiplexa flujos de aplicación sobre TCP; la falta de bytes TCP puede retrasar la entrega en todos esos flujos.
QUIC proporciona flujos, confiabilidad y control de congestión sobre UDP, integrando TLS; HTTP/3 asigna HTTP a QUIC.
La pérdida que afecta a un flujo QUIC no tiene por qué bloquear la entrega de otro, pero siguen existiendo límites de congestión compartidos y dependencias de la aplicación.
Por lo general, una captura cifrada pasiva no puede mostrar el contenido HTTP; los registros de texto sin cifrar de un endpoint se obtienen en otro punto de observación.

Para cada caso, dibuja el límite correspondiente y escribe una afirmación positiva, una negativa y cuál sería la siguiente observación.
Explica cómo `--resolve` de curl podría aislar la búsqueda de direcciones y conservar el hostname de la URL para TLS, sin afirmar que prueba DNS.
Distingue el comportamiento de fallback de `--http3` de `--http3-only`; antes de diseñar esa prueba, comprueba la compatibilidad local.
El helper solo IPv4 del Proyecto B no se convierte en un servidor IPv6/TLS/HTTP2 por cambiar un indicador del cliente.

Usa [IPv6 RFC 8200](https://www.rfc-editor.org/rfc/rfc8200.html) e [ICMPv6 RFC 4443](https://www.rfc-editor.org/rfc/rfc4443.html) para ampliar el Proyecto A en papel.
Sustituye TTL por Hop Limit, el análisis de longitud del encabezado IPv4 por el de IPv6/encabezados de extensión, y los tipos de ICMPv4 por tipos ICMPv6.
Los routers IPv6 no fragmentan los paquetes reenviados; los mensajes Packet Too Big tienen una función distinta de Time Exceeded.
Incluye la familia y el alcance de la dirección en el registro; la detección de vecinos IPv6 no es ARP.

**Observaciones esperadas:** el informe distingue una respuesta de aplicación autenticada de la accesibilidad y las capacidades.
**Observaciones negativas:** las herramientas no compatibles y las trazas ausentes se marcan como no disponibles, nunca como fallos medidos del protocolo remoto.
**Restauración:** no se cambia el estado de ejecución; conserva las evidencias importadas originales y su procedencia.

## Finalización y entrega del portafolio {#completion}

- [ ] Registra las URL/edición de las lecturas, la fecha de acceso, las versiones de la máquina invitada y las herramientas, y la revisión/hash del helper.
- [ ] Explica los cinco registros del Proyecto A y los tres casos añadidos sin inventar los saltos que faltan.
- [ ] Conserva las pruebas HTTP medidas con el estado, las longitudes del contenido, una conexión TCP y las limitaciones de la captura.
- [ ] Demuestra que el entramado no depende de cómo se particionen los bytes y cubre los dos casos negativos de datos malformados/incompletos.
- [ ] Explica la diferencia entre control de flujo de recepción y control de congestión, y por qué esta carga pequeña no permite medir ninguno de los dos.
- [ ] Completa los seis casos de límites y la ampliación de IPv6.
- [ ] Muestra que se detuvieron el socket en escucha y la captura, e identifica las observaciones pendientes.
- [ ] Responde el [cuestionario](../../quizzes/networking/expert/01-protocol-projects-quiz.md) y explica por qué se rechazan las otras opciones.

Si no tienes privilegios para capturar, termina el trabajo sin conexión y marca la captura de paquetes como pendiente.
Una captura importada puede servir para el análisis, pero no se puede presentar como un experimento que acabas de reproducir.
El portafolio demuestra observación y razonamiento sobre fallos; no es un certificado ni una prueba de dominio universal de los protocolos.

Vuelve al [mapa del curso experto](README.md), continúa con [enrutamiento](02-routing-policy-convergence.md) o profundiza en la evidencia del host en [rendimiento de Linux](04-linux-performance.md).
Aplica el contrato de evidencias al [proyecto final de automatización](06-automation-capstone.md).
