# 7. Primeros pasos en monitorización y rendimiento de red

> **Base de aprendizaje**: Ubuntu Server 24.04 LTS, con una ruta alternativa para Rocky Linux 9
>
> **Última actualización**: 15 de septiembre de 2026

**Requisitos previos:** Completa las [lecciones 1–6](README.md#course-map). Las dos máquinas virtuales se comunican mediante sus NIC de laboratorio y TCP 8000 en el servidor solo está permitido desde el cliente del laboratorio. Si otro servidor de laboratorio usa el puerto 8000, identifícalo y detenlo según el procedimiento de ese ejercicio.

**Resultados:** Distinguir listeners, conexiones, colas, paquetes y volúmenes de tráfico, y convertir «va lento» en una pregunta que se pueda probar. Reserva aproximadamente 2–3 horas, incluida la práctica.

## Herramientas y puntos de observación {#observation-tools}

| Pregunta | Herramienta | Qué no puede demostrar |
|---|---|---|
| ¿En qué dirección y puerto escucha un programa? | `ss -ltnp` | Si un cliente externo puede alcanzarlo |
| ¿Cuáles son los estados de las conexiones y las colas? | `ss -tinm` | La causa de la pérdida a partir de una sola instantánea |
| ¿Qué paquetes cruzaron esta NIC? | `tcpdump` | Actividad en otras NIC o espacios de nombres que no se capturaron |
| ¿Qué pares de hosts usan ancho de banda? | `iftop` | El tiempo de procesamiento de la aplicación ni el tráfico exacto facturado |
| ¿Cuánto tarda una solicitud HTTP en cada etapa? | `curl -w` | La temporización dentro de funciones concretas del servidor |

Los materiales anteriores pueden usar `netstat`. Este curso utiliza `ss` para observar sockets. `netstat -lnt` y `ss -ltn` responden preguntas similares, pero sus formatos y campos no son idénticos. Que falte `netstat` no es motivo para eliminar herramientas más nuevas ni reconfigurar el sistema.

Comprueba los paquetes necesarios en el servidor. En Ubuntu:

```bash
sudo apt update
sudo apt install iproute2 tcpdump python3
```

En Rocky:

```bash
sudo dnf install iproute tcpdump python3
```

El cliente necesita `curl`; instálalo siguiendo las instrucciones del administrador de paquetes de la [lección 1](01-linux-cli.md).

## Genera una carga HTTP pequeña {#small-http-workload}

**Consola A del servidor:** Crea un archivo de ejercicio en un directorio temporal vacío.

```bash
LAB_WEB=$(mktemp -d /tmp/net-web.XXXXXX)
printf 'network lesson\n' > "$LAB_WEB/index.html"
timeout 300 python3 -m http.server 8000 \
  --bind 192.0.2.20 --directory "$LAB_WEB"
```

Este servidor expone el directorio seleccionado y se detiene tras cinco minutos. El código de salida 124 significa que `timeout` alcanzó el límite. No es un servidor web de producción con TLS ni autenticación de usuarios. No coloques otros archivos ni enlaces simbólicos en el directorio del ejercicio.

**Cliente:** Envía una solicitud y luego diez más a intervalos de un segundo.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
for n in $(seq 1 10); do
  curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
    -sS -o /dev/null http://192.0.2.20:8000/
  sleep 1
done
```

**Criterios de aprobación:** La primera respuesta es HTTP 200 y su cuerpo contiene `network lesson`. Las solicitudes posteriores terminan sin errores y aparecen en el registro del servidor. Si fallan, vuelve a la [secuencia de diagnóstico de la lección 4](04-dns-connectivity.md) en vez de aumentar la carga.

## Lee estados de sockets y colas {#socket-observation}

**Consola B del servidor:** Usa otro terminal.

```bash
sudo ss -ltnp 'sport = :8000'
ss -tinm '( sport = :8000 or dport = :8000 )'
```

Busca el listener `192.0.2.20:8000` en el primer comando. Repite la segunda observación mientras se ejecutan las solicitudes. Las conexiones breves pueden terminar entre instantáneas; la ausencia de una fila ESTABLISHED no demuestra que la solicitud haya fallado. Correlaciona los registros del servidor y las capturas de paquetes.

| Estado o campo | Interpretación |
|---|---|
| `Recv-Q` / `Send-Q` de LISTEN | Conexiones que esperan aceptación / tamaño máximo de la cola de aceptación |
| `Recv-Q` de ESTABLISHED | Bytes en orden que la aplicación aún no ha leído |
| `Send-Q` de ESTABLISHED | Bytes del flujo sin confirmar, incluidos los que aún no se han enviado |
| `rtt` | Estimación de ida y vuelta de TCP, no la duración total de HTTP |
| `cwnd` | Ventana de congestión del emisor; `ss` normalmente la muestra en segmentos |
| `skmem` | Contabilidad de memoria del socket, incluida la sobrecarga, no solo los bytes de carga útil en cola |

Con estas solicitudes pequeñas, las colas vacías son normales. Crear una cola grande no es un criterio de éxito. El [ejercicio de colas TCP de Linux](../07-linux-network-diagnostics.md#tcp-buffer-lab) utiliza una conexión de mayor duración y ofrece más contexto.

## Captura paquetes en una NIC seleccionada {#packet-capture}

**Consola B del servidor:** Identifica la NIC del laboratorio comparando su dirección MAC con la registrada en el hipervisor.

```bash
ip -br link
```

Sustituye el nombre verificado a continuación. `enp0s8` es un ejemplo, no una instrucción para seleccionar tu NIC de administración.

```bash
LAB_IF=enp0s8
ip -br address show dev "$LAB_IF"
sudo timeout 15 tcpdump -ni "$LAB_IF" -c 20 \
  'host 192.0.2.10 and tcp port 8000'
```

Inicia la captura y luego **repite la solicitud curl desde el cliente**. `-n` evita búsquedas de nombres, `-i` selecciona la interfaz y `-c 20` limita la cantidad de paquetes capturados. El límite de 15 segundos puede alcanzarse primero.

Entre las marcas ilustrativas de TCP están `[S]` para SYN, `[S.]` para SYN+ACK, `[.]` para ACK y `[F.]` para FIN+ACK. Los datos y las confirmaciones pueden combinarse de distintas formas. No memorices una regla fija como «una solicitud HTTP siempre consta exactamente de tres paquetes».

Para guardar pruebas, captura solo el tráfico de tu ejercicio durante un periodo breve.

```bash
LAB_CAPTURE=$(mktemp -d /tmp/net-capture.XXXXXX)
sudo timeout 15 tcpdump -Z "$(id -un)" -ni "$LAB_IF" -c 20 \
  -w "$LAB_CAPTURE/http.pcap" 'host 192.0.2.10 and tcp port 8000'
sudo tcpdump -nn -r "$LAB_CAPTURE/http.pcap"
```

Vuelve a enviar la solicitud del cliente mientras se ejecuta el comando de escritura. `-Z "$(id -un)"` cambia al usuario normal actual después de abrir el dispositivo de captura, lo que permite escribir el archivo en el directorio temporal de ese usuario. Un PCAP puede contener direcciones y cargas útiles reales. Usa solo la cadena del ejercicio, nunca credenciales SSH ni tráfico real de usuarios. El comando de lectura usa `sudo` para adaptarse a diferencias de permisos de archivo.

**Interpretación:** Identifica las direcciones y los puertos de la solicitud y la respuesta. Si la captura está vacía, comprueba primero la NIC, el filtro y el intervalo de tiempo. La descarga de trabajo de la NIC puede hacer que los tamaños de paquete y las sumas de comprobación observados en el host difieran de los del cable. Una advertencia de suma de comprobación en una captura no demuestra un fallo de red.

## Ancho de banda y temporización de solicitudes {#bandwidth-and-time}

`iftop` es opcional. En Ubuntu puedes instalarlo con `sudo apt install iftop`. Si los repositorios configurados de Rocky no lo ofrecen, omite este ejercicio o comprueba primero los [requisitos previos de EPEL de la lección 6](06-firewalls-host-security.md). Que falle `sudo dnf install iftop` no es motivo para ejecutar un script de instalación externo arbitrario.

**Servidor:** En el terminal donde está configurada la variable `LAB_IF` verificada:

```bash
sudo iftop -nNP -i "$LAB_IF" -f 'host 192.0.2.10'
```

Repite las solicitudes del cliente, lee las tasas direccionales y pulsa `q` para salir. Las solicitudes pequeñas y breves quizá aparezcan casi en cero. Esto no es una prueba de capacidad del enlace ni de rendimiento de Internet.

**Cliente:** Observa por separado la temporización HTTP.

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -sS -o /dev/null \
  -w 'dns=%{time_namelookup} connect=%{time_connect} first_byte=%{time_starttransfer} total=%{time_total}\n' \
  http://192.0.2.20:8000/
```

Los valores son segundos transcurridos desde el inicio. Esta solicitud usa una IP literal y no mide el rendimiento de DNS. El tiempo hasta el primer byte incluye los pasos anteriores y la preparación del servidor; no sumes todos los campos como si fueran intervalos independientes.

| Medición | Significado | Condiciones que se deben controlar |
|---|---|---|
| Latencia | Duración de una operación o ida y vuelta | Tamaño de la solicitud, ruta y carga del servidor |
| Caudal (throughput) | Cantidad entregada por unidad de tiempo | Concurrencia, dirección, bytes frente a bits y duración |
| Pérdida/retransmisión | Pérdida de paquetes observada o recuperación de TCP | Punto de captura/descartes, cambios de ruta e intervalo de tiempo |
| Uso de recursos | Actividad o espera de CPU, memoria y E/S | Proceso, recursos asignados a la VM y otras cargas de trabajo |

`1 byte = 8 bits`. No equipares `100 Mbit/s` con `100 MB/s`. Para mediciones repetidas, registra las condiciones y los valores mínimo/mediano/máximo u otra distribución adecuada.

## A continuación: estudio del kernel y la E/S {#kernel-next}

Estos comandos **solo observan**:

```bash
uname -r
sysctl net.ipv4.tcp_congestion_control
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem
lsblk -o NAME,TYPE,SIZE
```

Los valores de política de búfer devueltos por `sysctl` no corresponden al uso actual de cada socket. Antes de aumentarlos, distingue entre [búferes de socket, ventanas y BDP](../../kernel/02-network-stack.md#tcp-buffer-policy). Después de identificar un disco con `lsblk`, leer `/sys/block/DEVICE/queue/scheduler` muestra los planificadores de E/S de bloques admitidos/seleccionados; no todos los dispositivos virtuales ofrecen las mismas opciones.

Un planificador de E/S de bloques gestiona solicitudes de almacenamiento, mientras que una qdisc de red gestiona el encolado del tráfico saliente. Que ambas incluyan la palabra «planificador» no las convierte en controles de ajuste intercambiables. Esta lección no cambia sysctl, MTU, qdisc ni planificadores de E/S. El trabajo avanzado requiere un experimento independiente con una sola variable modificada, mediciones y reversión.

## Limpieza y finalización {#completion}

Detén el servidor en la consola A con Ctrl+C o espera a que alcance su límite de tiempo. En **ese mismo terminal**, elimina solo el archivo y el directorio de tu ejercicio.

```bash
rm -- "${LAB_WEB:?}/index.html"
rmdir -- "${LAB_WEB:?}"
```

En el terminal de captura, elimina también la captura.

```bash
sudo rm -- "${LAB_CAPTURE:?}/http.pcap"
rmdir -- "${LAB_CAPTURE:?}"
```

`${VARIABLE:?}` detiene el comando si la variable no está definida o está vacía. Si un directorio no está vacío, investígalo en lugar de usar una eliminación recursiva amplia.

- Explica por qué un listener, una conexión TCP y una respuesta HTTP satisfactoria son tipos de pruebas distintos.
- Identifica en un PCAP las direcciones/puertos de ambos sentidos y registra el punto de captura.
- Explica las unidades de cola/ancho de banda y el límite de medición de DNS de una solicitud con IP literal.
- Distingue la observación de los ajustes que requieren un experimento controlado aparte.

## Referencias y siguiente lección

- [Manual de ss de iproute2](https://man7.org/linux/man-pages/man8/ss.8.html)
- [Manual de tcpdump](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [Manual del autor de iftop](https://www.ex-parrot.com/pdw/iftop/iftop.8.html)
- [Manual de curl](https://curl.se/docs/manpage.html)
- [http.server de Python 3.12](https://docs.python.org/3.12/library/http.server.html)
- [Colas múltiples de bloques de Linux](https://docs.kernel.org/block/blk-mq.html)

[Anterior: Firewalls y seguridad del host](06-firewalls-host-security.md) · [Cuestionario](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) · [Siguiente: Proyecto integrador](08-container-cloud-capstone.md)
