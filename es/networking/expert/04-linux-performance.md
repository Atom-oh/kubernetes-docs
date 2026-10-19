# Rendimiento de red en Linux: medir antes de explicar

> **Base del laboratorio**: sistema invitado Ubuntu Server 24.04 LTS o Rocky Linux 9, propio; observaciones acotadas de loopback
>
> **Última actualización**: 15 de septiembre de 2026

## Propósito y requisitos previos {#purpose}

Este cuaderno pregunta si una transacción lenta está esperando a la aplicación, el transporte, el kernel o la ruta.
El entregable es un informe de medición reproducible con explicaciones alternativas, evidencia negativa y procedimiento de restauración.
No se promete una latencia fija, una mejora del caudal ni una puntuación de benchmark.

Complete el [curso para principiantes](../beginner/README.md), en especial su [lección de supervisión](../beginner/07-monitoring-performance.md).
Lea la [pila de red del kernel](../../kernel/02-network-stack.md), desde socket/VFS hasta transmisión, recepción y ubicación de hooks.
Después, revise el [diagnóstico de redes Linux](../07-linux-network-diagnostics.md#tcp-buffer-lab) para conocer el auxiliar HTTP existente y la interpretación del estado de los sockets.
Los [proyectos de protocolos](01-protocol-projects.md) aportan terminología sobre flujos de bytes y evidencia.
Más adelante, lea la [guía existente de benchmarks de Pods](../06-pod-network-benchmark.md); las cifras de loopback no son un benchmark de CNI.

Necesita habilidades con procesos/archivos Linux, Python básico, conocimientos de secuencias/ventanas TCP y aritmética con bits, bytes y segundos.
La programación C y de controladores son extensiones opcionales, no requisitos previos para el ejercicio acotado de Python.
No se ejecutó ningún experimento de red/nube al redactar este capítulo; los criterios siguientes son instrucciones para una futura ejecución en un sistema invitado propio.

## Mapa de lecturas de Bootlin y fuentes primarias {#readings}

La página de formación de redes Linux de [Bootlin](https://bootlin.com/training/networking/) estaba disponible el **15 de septiembre de 2026**.
Sus [diapositivas](https://bootlin.com/doc/training/networking/networking-slides.pdf) y las [instrucciones de laboratorio de EspressoBin](https://bootlin.com/doc/training/networking/networking-espressobin-labs.pdf), que se pueden descargar gratis, sirven para estudiar.
Los documentos públicos no incluyen acceso gratuito a un instructor, una placa suministrada ni compatibilidad garantizada con hardware arbitrario.

| Lectura | Conocimientos necesarios | Pregunta que se debe responder aquí |
|---|---|---|
| Secciones de Bootlin sobre la pila de red e interfaz de espacio de usuario | Administración de Linux, sockets y capas de protocolo | ¿En qué punto los bytes de aplicación se convierten en trabajo en cola del kernel? |
| Controladores, NAPI y laboratorios de hardware de Bootlin | Dominio sólido de C, desarrollo de kernel/módulos, interrupciones, DMA y preparación de placa/cadena de herramientas del laboratorio | ¿Qué afirmaciones requieren un controlador y una NIC reales? |
| [Documentación NAPI del kernel](https://docs.kernel.org/networking/napi.html) | Diferencia entre interrupciones y sondeo | ¿Qué trabajo se sondea y con qué presupuesto/contexto? |
| [Documentación de escalado del kernel](https://docs.kernel.org/networking/scaling.html) | Colas de CPU y hash de flujos | ¿RSS o RPS selecciona la CPU de procesamiento? |
| [Offloads de segmentación](https://docs.kernel.org/networking/segmentation-offloads.html) | MTU/MSS y puntos de observación de paquetes | ¿Por qué una captura puede mostrar unidades mayores que las de la red? |
| [Documentación sysctl TCP](https://docs.kernel.org/networking/ip-sysctl.html) | Memoria del socket, ventanas y ajuste automático | ¿Qué límite es una política y qué dato es una observación por flujo? |
| [Manual fuente de ss de iproute2](https://github.com/iproute2/iproute2/blob/main/man/man8/ss.8) y [manual fuente de tc](https://github.com/iproute2/iproute2/blob/main/man/man8/tc.8) | Estados TCP y contadores de colas | ¿Qué cuenta exactamente cada valor mostrado? |

Para la ruta de hardware de Bootlin, registre la revisión del PDF del laboratorio, la placa necesaria, la consola serie, el gestor de arranque, el árbol/configuración del kernel y la cadena de herramientas de compilación cruzada.
El curso comprobado utiliza EspressoBin con un procesador Marvell Armada 3720 ARM64; no suponga que la VM de principiantes sustituye ese entorno documentado.
Si no dispone de esa configuración, complete el análisis de ruta de paquetes e indique que las observaciones de hardware no están disponibles.
La inscripción y los certificados de formación son independientes de la finalización de este cuaderno basada en evidencia.

## Diseño de la medición antes de ejecutar comandos {#measurement-design}

Antes de comenzar, complete esta ficha del experimento. Los campos vacíos son tareas pendientes, no permiso para inventar resultados.

| Campo | Elección para el ejercicio principal |
|---|---|
| Hipótesis | Retrasar la lectura del cuerpo por parte del cliente aumenta el tiempo de finalización de la aplicación sin que sea necesario perder paquetes en la ruta |
| Propietario del recurso/observador | Su usuario en un único sistema invitado descartable; anote el nombre del sistema y el espacio de nombres de red |
| Cliente/servidor | Cliente Python y auxiliar HTTP del repositorio; solo `127.0.0.1:18080` |
| Variables | Cuerpo de solicitud/eco de 64 o 4096 bytes; pausa de lectura del cliente de 0 o 0.15 segundos |
| Controles fijos | Una solicitud cada vez, una conexión TCP nueva por solicitud, mismo endpoint/auxiliar |
| Presupuesto | Un calentamiento más 15 solicitudes medidas; menos de 42 KiB de carga útil en cada dirección |
| Plazo | 60 segundos para el cliente, límite de 2 segundos para operaciones de socket; 180 segundos para el servidor |
| Observadores | Duraciones monotónicas del cliente; muestras de `ss` acotadas; contadores de interfaz/qdisc antes y después |
| Regla de fallo | Detenerse ante fallo de contenido/estado, listener inesperado, herramienta ausente o vencimiento del plazo |
| Recuperación | Cerrar los clientes propios, detener el servidor propio en primer plano y verificar que se haya eliminado el listener |

Una pausa de 0.15 segundos es un **parámetro de entrada**, no una demora de red medida.
La carga de trabajo es intencionadamente demasiado pequeña para agotar la ventana de recepción o saturar loopback.
No use el rendimiento útil (goodput) para afirmar capacidad de la NIC, latencia de Internet ni convergencia de enrutamiento.
En lo posible, mantenga inactivo el sistema invitado y anote otras cargas de trabajo; los contadores de loopback incluyen otros procesos.

## Herramientas, funciones y alcance {#readiness}

Siga la [preparación de herramientas de los sistemas invitados para principiantes](../beginner/README.md#guest-tools) para instalar los paquetes que falten, incluida la vista previa de transacciones y el registro de recuperación.
Instale solo las herramientas necesarias para la ruta seleccionada en el sistema invitado propio; la imagen base no garantiza que estén instaladas.

| Herramienta | Paquete de Ubuntu | Paquete de Rocky | Función/privilegios |
|---|---|---|---|
| `python3` 3.9+ | `python3` | `python3` | Cliente/servidor; usuario normal |
| `ip`, `ss` | `iproute2` | `iproute` | Observaciones acotadas; usuario normal |
| `tc` | `iproute2` | `iproute-tc` | Leer contadores de qdisc; usuario normal cuando se permita |
| `timeout`, `sha256sum` | `coreutils` | `coreutils` | Limitar la ejecución e identificar el auxiliar |
| `tcpdump` | `tcpdump` | `tcpdump` | Captura opcional de paquetes; sudo solo para capturar |
| `ethtool` | `ethtool` | `ethtool` | Inspección opcional de una NIC existente; algunas consultas requieren privilegios |
| `pidstat` | `sysstat` | `sysstat` | Muestreo opcional de CPU de procesos |
| `bpftool`, `bpftrace` | Paquetes según el kernel/la distribución | Paquetes según el kernel/la distribución | Opcionales; compruebe por separado el paquete, la compatibilidad del kernel y la autorización |

No instale paquetes de kernel ni habilite trazas solo para cumplir una fila opcional.
Para las herramientas BPF, registre el propietario del paquete instalado, las versiones de herramientas/kernel, la disponibilidad de BTF y cualquier error de acceso.
Que exista un comando no demuestra por sí solo que se disponga de permisos BPF utilizables.

Desde la raíz del repositorio en el sistema invitado:

```bash
command -v python3 ip ss tc timeout sha256sum
python3 --version
uname -r
ip -Version
ss -V
tc -V
sha256sum examples/networking/foundations/http_lab.py
ss -ltn 'sport = :18080'
```

Si el filtro detecta algún socket en escucha, deténgase y elija otro puerto libre; use ese puerto de forma coherente y nunca detenga un servicio ajeno.
Cree un directorio privado nuevo con `mkdir -m 700 linux-evidence-01`; si ya existe, utilice otro nombre.
Dentro de ese directorio, registre la revisión del repositorio, la versión del sistema operativo, las versiones de las herramientas, el espacio de nombres y las horas UTC de inicio y finalización.
Todos los comandos de cliente/servidor que siguen se ejecutan como usuario normal en el mismo sistema invitado y espacio de nombres.

## Seguir la ruta de procesamiento {#packet-path}

Use el diagrama del capítulo existente sobre el kernel y anótelo con estas distinciones.
La ruta habitual de recepción de un controlador nativo es cola de NIC → sondeo NAPI → XDP nativo opcional → pila/transporte → socket → aplicación.
Los modos de offload del controlador/dispositivo y XDP genérico se ubican en otros puntos; etiquete el modo en vez de dibujar cada hook en el mismo lugar.
El trabajo de transmisión pasa del socket/transporte por el enrutamiento y las colas aplicables hasta el dispositivo.

| Mecanismo | Qué cambia | Observación y contraejemplo |
|---|---|---|
| NAPI | Procesamiento de eventos del controlador mediante sondeo, a menudo coordinado con interrupciones | Un presupuesto de sondeo no garantiza la latencia de la aplicación |
| RSS | El hardware distribuye los flujos entre colas de recepción | Un flujo puede seguir asignándose a una sola cola; más colas no dividen todos los flujos |
| RPS | El software selecciona CPU para procesar la recepción | La distribución entre CPU no demuestra que la NIC haya usado RSS |
| GSO / TSO | Segmentación por software/dispositivo de unidades de transmisión mayores | Una unidad grande capturada en el host no tiene por qué ser una trama excesiva en la red |
| GRO | Combina trabajo de recepción antes del procesamiento de capas superiores | El número de unidades en una captura no tiene por qué coincidir con el de tramas físicas |
| qdisc | Pone en cola/planifica el tráfico saliente aplicable | `noqueue` en loopback no demuestra que no haya colas en otra NIC física |
| Ventanas de socket | Control de flujo del receptor y permisos de congestión del emisor | Los búferes configurados grandes no demuestran que se puedan usar completamente ambas ventanas |

Loopback no tiene colas RSS físicas, serialización de enlace ni una ruta de conmutación para medir.
No proyecte sus detalles de procesamiento en un controlador físico.

Para un **flujo preexistente de una VM propia**, elabore un plan de observación por escrito: identifique ambos extremos, la interfaz/ruta existente, la tupla de flujo, el propietario y el presupuesto de tráfico original.
Realice solo estas consultas de lectura con `ethtool -k`, `ethtool -l`, `ethtool -x` y `ethtool -S` en esa interfaz de laboratorio identificada, cuando sean compatibles.
Anote «no compatible» o «permiso denegado» en vez de cambiar controladores, cantidad de canales o funciones de offload.
La ruta principal no requiere comandos generales de interfaz ni recursos nuevos de VM/nube.

## Experimento acotado de loopback {#bounded-experiment}

Guarde el estado previo antes de iniciar el auxiliar:

```bash
ip -s link show dev lo > linux-evidence-01/link-before.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-before.txt
ss -ltn 'sport = :18080' > linux-evidence-01/listener-before.txt
```

Inicie en la terminal A el servidor propio y espere su mensaje de disponibilidad:

```bash
python3 examples/networking/foundations/http_lab.py --port 18080 --duration 180
```

En la terminal C, inicie el observador acotado de sockets justo antes del cliente:

```bash
timeout 25s bash -c '
  for sample in {1..40}; do
    date -u +%FT%T.%NZ
    ss -tinm state established "( sport = :18080 or dport = :18080 )"
    sleep 0.5
  done
' > linux-evidence-01/sockets.txt
```

En la terminal B, ejecute este cliente de medición original. No realiza consultas DNS ni lee la configuración del proxy.
Su número máximo de solicitudes es 16, incluido el calentamiento; cada conexión se cierra en `finally`.
La pausa de 0.25 segundos entre solicitudes también limita su frecuencia.

```bash
timeout --signal=INT --kill-after=2s 60s python3 - <<'PY' \
  > linux-evidence-01/transactions.jsonl
import datetime
import http.client
import json
import time

phases = [("warmup", 64, 0.0, 1),
          ("small", 64, 0.0, 5),
          ("large", 4096, 0.0, 5),
          ("reader_pause", 4096, 0.15, 5)]
for phase, size, pause, count in phases:
    for sample in range(count):
        connection = http.client.HTTPConnection("127.0.0.1", 18080, timeout=2)
        payload = b"x" * size
        row = {"phase": phase, "sample": sample, "bytes": size,
               "pause_s": pause,
               "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        start = time.perf_counter()
        try:
            connection.request("POST", "/echo", body=payload,
                               headers={"Content-Type": "application/octet-stream"})
            response = connection.getresponse()
            headers_at = time.perf_counter()
            time.sleep(pause)
            body = response.read()
            finished = time.perf_counter()
            if response.status != 200 or body != payload:
                raise ValueError("Unexpected status or echo content")
            row.update(status=response.status, ok=True,
                       headers_ms=(headers_at - start) * 1000,
                       read_ms=(finished - headers_at) * 1000,
                       total_ms=(finished - start) * 1000)
        except Exception as error:
            row.update(ok=False, error=type(error).__name__,
                       detail=str(error))
            print(json.dumps(row), flush=True)
            raise SystemExit(1)
        finally:
            connection.close()
        print(json.dumps(row), flush=True)
        time.sleep(0.25)
PY
```

Guarde inmediatamente el estado de salida del cliente. Una ejecución interrumpida o con menos de 16 filas correctas está incompleta.
El límite de tiempo externo puede vencerse sin una fila JSON final; los datos que faltan no equivalen a latencia cero.
`headers_ms` incluye el trabajo de conexión/solicitud hasta que se analizan los encabezados de respuesta; no es un RTT puro ni una métrica TTFB de curl.
`read_ms` incluye la pausa deliberada y el consumo del cuerpo; el almacenamiento en búfer de la biblioteca quizá ya contenga algunos datos.
`total_ms` mide hasta que se consume la respuesta, sin incluir la pausa posterior entre solicitudes.

Después de que terminen el cliente y el observador, recopile el estado posterior:

```bash
ip -s link show dev lo > linux-evidence-01/link-after.txt
tc -s qdisc show dev lo > linux-evidence-01/qdisc-after.txt
ss -tinm state established '( sport = :18080 or dport = :18080 )' \
  > linux-evidence-01/sockets-after.txt
```

**Observaciones esperadas:** todas las solicitudes finalizadas devuelven los mismos bytes de eco; la fase de pausa de lectura debe incluir la demora configurada en el tiempo de finalización.
**Observaciones negativas:** puede que algunas muestras de `ss` estén vacías porque las conexiones son breves; que las colas tengan valor cero no demuestra que el observador esté averiado.
Puede que el pequeño eco no produzca contrapresión visible ni retransmisiones.
Los deltas de contadores abarcan toda la interfaz loopback; no atribuya cada incremento a este cliente.
Si falla el eco, conserve la fila fallida y el estado del servidor antes de diagnosticar; no vuelva a intentarlo silenciosamente hasta que solo queden éxitos.

Para obtener evidencia opcional de paquetes, use la [captura acotada del proyecto B](01-protocol-projects.md#stream-project) en un directorio nuevo de evidencia.
Sus límites de 20 segundos/120 paquetes pueden omitir conexiones de esta ejecución; registre la cobertura parcial en vez de interpretar paquetes ausentes como pérdidas.
No desactive las funciones de offload de sumas de comprobación/segmentación para que la captura resulte más familiar.

**Restauración:** detenga con Ctrl+C solo el servidor propio en primer plano o deje que venza su plazo de 180 segundos.
El cliente y el observador terminan al alcanzar sus límites; si hace falta, interrumpa solo esos procesos en primer plano.
Verifique que `ss -ltn 'sport = :18080'` no devuelva ningún listener; puede que queden sockets TIME_WAIT de forma legítima.
Conserve el directorio de evidencia o elimine solo sus archivos designados tras revisarlos.
Este ejercicio no modificó qdisc, sysctl, funciones de offload de la NIC, rutas ni programas BPF adjuntos.

## Interpretar ventanas, pérdidas y latencia {#interpretation}

Compare la [semántica de las colas de socket](../../kernel/02-network-stack.md#ss-tcp-queues) con las muestras sin procesar de `ss`.
En el estado ESTABLISHED, `Recv-Q` cuenta los datos recibidos que esperan a la aplicación; `Send-Q` cuenta los datos no confirmados, incluidos los aún no enviados.
En LISTEN, las columnas se refieren en cambio a la cola de aceptación/backlog, no a la ocupación de datos útiles.
`skmem` contabiliza memoria y sobrecarga; no tiene por qué coincidir con los bytes del flujo, la ventana anunciada ni `cwnd`.
Si aparece `cwnd`, normalmente se expresa en segmentos; use el MSS y las unidades correspondientes antes de compararlo con bytes.

Para una ruta **hipotética** de 100 Mbit/s con RTT de 40 ms:
`BDP = 100,000,000 bit/s × 0.040 s ÷ 8 = 500,000 bytes`.
Es un ejemplo aritmético, no una medición ni una orden para configurar búferes.
Relaciónelo con [BDP y política de sockets](../../kernel/02-network-stack.md#tcp-bdp-reasoning).
Una ventana efectiva más pequeña puede limitar el rendimiento, pero aumentar un límite global no demuestra que las ventanas causaran la demora de esta ejecución.

Excluya el calentamiento e informe para cada fase el número de muestras, los fallos, el mínimo, la mediana y el máximo de las filas reales.
Cinco muestras no bastan para justificar un objetivo de servicio p99 creíble ni una afirmación de capacidad de producción.
El cociente entre los bits de carga útil de respuesta y los segundos de transacción es el goodput de aplicación de esa operación; incluye la demora de conexión y procesamiento.
No equivale a la velocidad de línea Ethernet ni mide directamente la congestión.

| Observación | Posible explicación | Evidencia necesaria para separar alternativas |
|---|---|---|
| Tiempo de finalización alto, tiempo de encabezados normal | Demora de consumo del cliente | Fases/marcas de tiempo del cliente; no culpe a la ruta basándose solo en el tiempo total |
| Cola de recepción persistente | Lector de aplicación lento o planificación | Avance del lector, datos de CPU y muestras repetidas por flujo |
| Cola de envío persistente | Datos sin enviar, ACK ausentes o limitación del receptor | Campos de ventana/retransmisión y evidencia de ambos extremos |
| Aumentan las retransmisiones | Pérdida, reordenamiento o retransmisión espuria | Evidencia de secuencia/tiempo; un contador no localiza el descarte |
| La captura tcpdump descarta paquetes | El observador no alcanza a procesar los paquetes al ritmo de llegada | Estadísticas de captura; no son directamente una pérdida TCP/de ruta |
| Aumentan los descartes qdisc | Política/presión de una cola local | Mismo intervalo/interfaz y atribución del tráfico |

## Observación y diseño de fallos con eBPF/XDP {#bpf-observation}

Lea la [documentación BPF del kernel](https://docs.kernel.org/bpf/) y la explicación de hooks de Bootlin antes de elegir una herramienta.
En un laboratorio propio ya preparado y con permisos, `bpftool prog show` y `bpftool net show` pueden inventariar programas/asociaciones existentes.
Estas observaciones opcionales son de solo lectura; que falten permisos significa «no observado», no «no hay BPF».
La existencia de un programa no demuestra por sí sola que este flujo lo haya recorrido ni que haya mejorado el rendimiento.

Diseñe, sin cargarlo, un único punto de observación tracepoint/kprobe: nombre del hook, filtro de tupla/espacio de nombres, campos, duración, límite de eventos y comprobación de sobrecarga.
Determine si los campos necesarios existen en el formato de eventos/BTF de ese kernel; nunca invente una firma universal de sonda.
Especifique cómo contabilizar la pérdida de eventos y cómo correlacionar las marcas de tiempo con las muestras del cliente.
Un tracepoint, un programa TC y un programa XDP nativo observan etapas diferentes; que no haya datos en un hook no demuestra que no haya datos en ninguna etapa.
Este cuaderno no adjunta, desasocia ni sustituye programas BPF.

**La extensión opcional de netem solo se diseña aquí.** No ejecute comandos de qdisc, sysctl u offload con alcance global en el host.
Redacte un plan aparte, en un espacio de nombres/VM propios, con la administración fuera de la interfaz afectada.
Anote la identidad del espacio de nombres/VM, la interfaz, la jerarquía, los identificadores y opciones qdisc originales, las rutas, las funciones de offload y todos los cambios propuestos.
Especifique una sola variable, un flujo de duración finita exacta, una referencia y el resultado negativo esperado.
Antes de ejecutar, exija un plan de restauración exacto: eliminar un qdisc raíz no recrea una jerarquía arbitraria original.
En un entorno descartable nuevo, destruir solo los ID de recursos registrados puede ser el límite de restauración.
Si no se puede reconstruir el estado previo o no está claro quién es el propietario, el plan se mantiene como diseño sin ejecución.

## Finalización y entrega {#completion}

- [ ] Explique qué materiales públicos y límites de hardware ofrece Bootlin, y registre las versiones de la fuente/herramientas/auxiliar.
- [ ] Conserve la ficha del experimento, las filas sin procesar, el fallo/estado de salida, la cobertura del observador y los contadores anteriores/posteriores.
- [ ] Distinga la demora de entrada de la duración medida, los bytes de cola de la memoria y el BDP de los búferes configurados.
- [ ] Ofrezca al menos dos explicaciones plausibles para un resultado lento y la evidencia que descartaría cada una.
- [ ] Indique las observaciones de NIC/BPF/paquetes ausentes y evite afirmar ganancias de rendimiento no medidas.
- [ ] Confirme que el servidor se detuvo y que no hay cambios persistentes de configuración.
- [ ] Complete el [cuestionario](../../quizzes/networking/expert/04-linux-performance-quiz.md) con explicaciones.

Entregue estos artefactos al [proyecto final de automatización](06-automation-capstone.md).
Use [EVPN de centros de datos](03-datacenter-evpn.md) para contexto de superposiciones/MTU y el [diseño de nube/CNI](05-cloud-cni-design.md) para más límites de rutas.
Vuelva al [mapa del curso avanzado](README.md) para elegir la siguiente especialización.
