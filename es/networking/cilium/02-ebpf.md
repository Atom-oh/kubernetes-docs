# Análisis profundo de la tecnología eBPF

> **Base de revisión**: Cilium 1.20.3, Linux 5.10+ o un backport equivalente documentado (por ejemplo, el kernel 4.18 de RHEL 8.10) y Kubernetes 1.33–1.36 probado. Cada característica de BPF tiene requisitos propios.
> **Última revisión**: 16 de octubre de 2026

## Preparación del entorno de laboratorio

Usa una máquina virtual de desarrollo Linux desechable, con una distribución mantenida, los tracepoints que se usan a continuación y permisos para cargar programas de tracing. Este entorno es independiente de la instalación de Cilium; no cargues programas experimentales en los nodos del clúster. Linux 6.12 es la versión de referencia para la explicación del verificador; esto no significa que todas las distribuciones con 6.12 habiliten cada función.

Necesitas Clang con backend BPF, los encabezados UAPI para la arquitectura de destino, encabezados y bibliotecas de desarrollo de libbpf 1.x, libelf, zlib, un compilador C y bpftool. BCC y bpftrace son alternativas opcionales. En Debian/Ubuntu, los nombres habituales de los paquetes incluyen `clang`, `libbpf-dev`, `libelf-dev`, `zlib1g-dev`, `build-essential` y `pkg-config`; el paquete de bpftool depende de la distribución y del kernel. No des por sentado que `linux-tools-generic` esté disponible o sea apropiado en todos los sistemas Debian. Cilium documenta hosts AMD64/AArch64; ejecutar Cilium de forma nativa fuera de su imagen de contenedor requiere además Clang/LLVM 18.1 o posterior, un requisito distinto del de este pequeño laboratorio de tracing.

```bash
uname -r
clang --version
clang --print-targets
pkg-config --modversion libbpf
bpftool version
test -r /sys/kernel/tracing/events/syscalls/sys_enter_execve/format
test -r /sys/kernel/tracing/events/sched/sched_process_exec/format
# Active feature probing: run only on the prepared lab VM.
sudo bpftool feature probe kernel
```

Tracefs debe estar montado y ser accesible; algunos sistemas lo exponen en `/sys/kernel/debug/tracing`. La configuración del kernel, las capacidades, las políticas de lockdown/LSM y las restricciones del contenedor pueden impedir la carga o la conexión, incluso con permisos de root dentro del contenedor. `CAP_BPF` por sí sola no concede permisos universales de tracing: los requisitos dependen del kernel, el tipo de programa BPF y la delegación mediante BPF token.

**Límite de validación:** estos ejemplos superaron comprobaciones de sintaxis C en el host con libbpf 1.7, el enlazado de programas de espacio de usuario y simulaciones deterministas de las funciones auxiliares. La compilación de destino Clang BPF, el verificador del kernel en ejecución y la conexión en vivo a tracepoints aún deben validarse en la máquina virtual preparada. No se han probado en producción ni son recetas de tracing sin pérdida de eventos.

## Introducción a la tecnología eBPF y sus antecedentes

eBPF permite ejecutar programas aprobados en hooks compatibles de Linux para observar o influir en el comportamiento del kernel. La verificación restringe el acceso a la memoria y la ejecución, pero siguen existiendo posibles errores en el kernel, el verificador, JIT y las funciones auxiliares. Que un programa sea aceptado no demuestra que el host no pueda fallar ni que el programa aplique la política prevista.

### De BPF a eBPF: evolución histórica

El preprint de *The BSD Packet Filter: A New Architecture for User-level Packet Capture*, de McCanne y Jacobson, está fechado el 19 de diciembre de 1992 e indica que se presentó en Winter USENIX, del 25 al 29 de enero de 1993. Ten presente esta distinción al citar el año. Classic BPF usa los registros A/X de 32 bits y memoria temporal para filtrar, evitando copias innecesarias de paquetes al espacio de usuario. Que su conjunto de instrucciones sea restringido no significa que no pueda ejecutarse en CPU modernas.

eBPF amplió el conjunto de instrucciones a 64 bits, con once registros R0–R10 (R10 es el puntero de marco de solo lectura), una pila normalmente limitada a 512 bytes, mapas y más tipos de programa. No hubo un cambio histórico de diez a once registros de propósito general. Las combinaciones de funciones y tail calls pueden imponer límites adicionales a la pila.

### Evolución técnica de eBPF: funciones clave por versión del kernel

Estos hitos seleccionados de upstream se contrastaron con el código fuente versionado. No constituyen una matriz de compatibilidad de distribuciones: los backports, las opciones de compilación, las arquitecturas y las funciones auxiliares varían.

| Kernel | Hito seleccionado |
|---|---|
| [3.15](https://github.com/torvalds/linux/blob/v3.15/include/linux/filter.h) | Conjunto de instrucciones extendido; traducción interna de classic BPF |
| [3.16](https://github.com/torvalds/linux/blob/v3.16/arch/x86/net/bpf_jit_comp.c) | JIT de BPF extendido para x86 |
| [3.18](https://github.com/torvalds/linux/blob/v3.18/include/uapi/linux/bpf.h) | Infraestructura de syscall/verificación de BPF; aún sin tipos de mapa HASH/ARRAY utilizables |
| [3.19](https://github.com/torvalds/linux/blob/v3.19/include/uapi/linux/bpf.h) | Mapas HASH/ARRAY y tipo de programa socket filter |
| [4.1](https://github.com/torvalds/linux/blob/v4.1/include/uapi/linux/bpf.h) | KPROBE y TC SCHED_CLS/SCHED_ACT |
| [4.2](https://github.com/torvalds/linux/blob/v4.2/include/uapi/linux/bpf.h) | PROG_ARRAY y tail calls |
| [4.8](https://github.com/torvalds/linux/blob/v4.8/include/uapi/linux/bpf.h) | Tipo de programa XDP |
| [4.10](https://github.com/torvalds/linux/blob/v4.10/include/uapi/linux/bpf.h) | Mapas LRU hash |
| [4.16](https://github.com/torvalds/linux/blob/v4.16/include/uapi/linux/bpf.h) | Llamadas de función BPF a BPF |
| [4.17](https://github.com/torvalds/linux/blob/v4.17/include/uapi/linux/bpf.h) | Raw tracepoints |
| [4.18](https://github.com/torvalds/linux/blob/v4.18/include/uapi/linux/bpf.h) | API de carga de BTF |
| [5.2](https://github.com/torvalds/linux/blob/v5.2/include/uapi/linux/bpf.h) | Acceso directo al valor de mapas utilizado para datos globales |
| [5.7](https://github.com/torvalds/linux/blob/v5.7/include/uapi/linux/bpf.h) | API BPF link y BPF LSM |
| [5.8](https://github.com/torvalds/linux/blob/v5.8/include/uapi/linux/bpf.h) | Ring buffer de BPF |
| [5.10](https://github.com/torvalds/linux/blob/v5.10/include/uapi/linux/bpf.h) | Programas que pueden dormir para tipos de conexión compatibles |
| [5.15](https://github.com/torvalds/linux/blob/v5.15/include/uapi/linux/bpf.h) | Funciones auxiliares de temporizador BPF |
| [5.19](https://github.com/torvalds/linux/blob/v5.19/include/uapi/linux/bpf.h) | Funciones auxiliares de punteros dinámicos |
| [6.2](https://github.com/torvalds/linux/blob/v6.2/kernel/bpf/helpers.c) | kfuncs de asignación de objetos tipados; no ofrecen malloc sin restricciones |

Los bucles acotados llegaron con Linux 5.3; el [cambio del verificador en upstream](https://github.com/torvalds/linux/commit/2589726d12a1b12eaaa93c7f1ea64287e383c7a5) explica el análisis de bucles y la poda de estados. Que un párrafo antiguo de la guía de diseño aún diga que «los bucles no están implementados» no constituye información actual sobre las funciones disponibles. Aun siendo acotados, los bucles pueden superar los límites de complejidad del verificador.

### Crecimiento y ámbitos de aplicación

El repositorio público de Cilium se creó en diciembre de 2015; decir que «el proyecto empezó en 2017» es inexacto. La creación del repositorio no fija la fecha exacta del lanzamiento del producto ni demuestra que fuera «el primer gran proyecto» de este tipo.

| Ámbito | Ejemplos y límites |
|---|---|
| Redes | Planos de datos de Cilium/Calico, balanceo de carga de Katran y filtrado XDP |
| Seguridad en tiempo de ejecución | Falco, Tracee y Tetragon usan eventos del kernel; la aplicación de medidas depende del producto y de los hooks |
| Tracing | BCC (incluidas sus interfaces de Python/Lua), bpftrace y tracing de almacenamiento y de E/S de bloques |
| Observabilidad de red | Flujos/eventos de proxy de Hubble; los gráficos de flujos no equivalen al tracing de spans distribuidos de una aplicación |
| Service mesh | Cilium combina el reenvío en el kernel con proxies de espacio de usuario para las funciones L7 compatibles |
| Comunidad | La eBPF Foundation apoya el ecosistema; la financiación y la madurez de los proyectos no determinan la compatibilidad |

`seccomp-bpf` usa la interfaz de filtros classic BPF para tomar decisiones sobre llamadas al sistema. Linux puede traducir internamente esos filtros clásicos, pero no es la API general de programas, mapas y funciones auxiliares de eBPF.

### eBPF frente a los módulos tradicionales del kernel

| Característica | eBPF | Módulo del kernel |
|---|---|---|
| Seguridad | Restringido por el verificador; siguen existiendo errores de implementación y riesgos operativos | Acceso nativo más amplio al kernel; los errores pueden desestabilizar el host |
| Despliegue | Los programas compatibles pueden cargarse y conectarse sin reiniciar | Muchos módulos también pueden cargarse y descargarse sin reiniciar, si las dependencias y el uso lo permiten |
| Compatibilidad | ABI de instrucciones/funciones auxiliares y requisitos de funciones; CO-RE puede reubicar accesos a tipos compatibles | ABI del kernel/módulo, configuración y compatibilidad de la distribución |
| Rendimiento | Suele compilarse con JIT; el hook, el programa y la carga de trabajo determinan el coste | La ejecución nativa también tiene costes que dependen de la carga de trabajo |
| Desarrollo | Contexto restringido, funciones auxiliares/kfuncs y límites del verificador | API del kernel y restricciones habituales del desarrollo del kernel |
| Permisos | Se requieren privilegios o delegación adecuados para la carga y conexión | La carga requiere privilegios; la firma o el lockdown pueden restringirla |

Ambas opciones necesitan pruebas operativas. Los módulos no se limitan a implementaciones de proveedores, y eBPF no hace que un despliegue en producción sea seguro por sí mismo.

## Análisis detallado de la arquitectura eBPF dentro del kernel

### Descripción detallada de los componentes de la arquitectura eBPF

En espacio de usuario, Clang compila C a BPF ELF; Rust usa su propio ecosistema de compilador y herramientas. libbpf procesa secciones ELF, mapas, reubicaciones, carga y las API de conexión compatibles. BCC ofrece API de nivel superior; bpftrace proporciona un lenguaje de tracing.

CO-RE usa BTF y reubicaciones para adaptar los accesos compatibles a tipos y campos. No proporciona funciones auxiliares, tipos de programa o configuración del kernel que falten ni garantiza compatibilidad arbitraria entre arquitecturas y versiones del kernel. Las estructuras internas del kernel, los formatos de tracepoint y las kfuncs no se convierten en ABI estable por el mero hecho de usar BTF.

En el kernel, el verificador comprueba el programa según su tipo, contexto, funciones auxiliares y permisos. El JIT puede traducir el BPF aceptado a instrucciones nativas; cuando está disponible, también puede usarse un intérprete. El resultado del JIT no pasa después por una segunda máquina virtual obligatoria. La conexión vincula el programa cargado a un hook; cargarlo no basta para suscribirse a tracepoints.

### Análisis detallado del ciclo de vida de un programa eBPF

1. **Desarrollo:** selecciona el hook y el contexto, y define los mapas y metadatos de licencia. No todos los programas requieren compatibilidad con GPL, pero las funciones auxiliares exclusivas de GPL y ciertos tipos/kfuncs imponen restricciones. Estas muestras de tracing usan metadatos GPL para sus funciones auxiliares.
2. **Compilación:** crea BPF ELF y la información de depuración/BTF necesaria con la cadena de herramientas y los encabezados de destino.
3. **Apertura/carga:** analiza ELF, crea o reutiliza mapas de forma explícita, aplica las reubicaciones e invoca la API de carga de BPF. La verificación y el JIT opcional se ejecutan durante la carga.
4. **Conexión:** usa la API adecuada. libbpf puede inferir estos tracepoints a partir de `SEC("tracepoint/...")`. Mantén activo el enlace o la conexión.
5. **Ejecución/observación:** los eventos invocan el programa; el espacio de usuario lee mapas o buffers. El muestreo y los límites de capacidad pueden causar pérdida de observaciones.
6. **Actualización/descarga:** conserva mapas, enlaces y pins compatibles solo de manera deliberada. Destruye el enlace de este laboratorio y cierra su objeto para liberar recursos.

En Linux 6.12, la longitud del programa se limita a 1.000.000 de instrucciones para la ruta de carga con capacidad BPF y a 4.096 para la ruta sin privilegios. Por separado, el verificador tiene un límite de **complejidad de análisis** de 1.000.000 de instrucciones. Programas más pequeños también pueden fallar la verificación. A menudo BPF sin privilegios está desactivado; siguen aplicándose las comprobaciones de tokens/capacidades y del tipo de programa.

### Tipos y características de los programas eBPF

| Hook / tipo de programa | Propósito y límites del valor de retorno |
|---|---|
| XDP / `BPF_PROG_TYPE_XDP` | XDP nativo del controlador se ejecuta antes de asignar un skb; los modos genérico y offload son distintos. `XDP_DROP`, `PASS`, `TX` y `REDIRECT` son acciones, no garantías de rendimiento |
| TC / `SCHED_CLS`, `SCHED_ACT` | Clasificación/acciones de paquetes de entrada y salida. La semántica `TC_ACT_*` del clasificador requiere configurar correctamente direct-action |
| Socket filter / `SOCKET_FILTER` | Entrega de paquetes al socket: cero descarta; una longitud de captura positiva puede truncar. Las políticas de creación/conexión usan otros hooks |
| kprobe/uprobe / `KPROBE` | Probes de kernel/espacio de usuario; no existe un `BPF_PROG_TYPE_UPROBE` independiente. La inserción de funciones, las listas de bloqueo y la disponibilidad de símbolos limitan la conexión |
| Tracepoint / `TRACEPOINT` | Contexto de evento declarado estáticamente; inspecciona el formato de destino. No es una ABI estable garantizada del kernel |
| Perf event / `PERF_EVENT` | Muestreo de rendimiento; el comportamiento del valor de retorno depende de su integración con perf events |
| cgroup / `CGROUP_SKB`, `CGROUP_SOCK`, `CGROUP_SOCK_ADDR`, etc. | Control de red/socket; el contexto y las convenciones de permitir/denegar varían |
| LSM / `LSM` | Los programas de estilo MAC suelen conservar errores anteriores y devolver cero/error; cgroup-LSM tiene una semántica de concesión distinta |
| Operaciones de socket / `SOCK_OPS` | Callbacks TCP; importan la operación, los campos de respuesta y la compatibilidad de las funciones auxiliares |
| fentry/fexit / `TRACING` | Tracing de funciones basado en BTF cuando está disponible; siguen aplicándose restricciones sobre el destino y la conexión |

Selecciona los hooks según la visibilidad y el control que necesites. XDP carece de parte del contexto disponible en capas posteriores; TC gestiona tráfico basado en skb; observar tracepoints o probes no aplica automáticamente una política de red. No reutilices estructuras de contexto ni códigos de retorno entre tipos de programa.

### Mapas eBPF: compartir datos y almacenar estado

Los mapas permanecen mientras haya referencias, por ejemplo, desde descriptores de archivo, programas cargados o pins explícitos en bpffs. Los pins no son persistencia en disco ni conservan el contenido del mapa tras reiniciar. Volver a cargar un programa no reutiliza automáticamente el mapa anterior.

| Tipo | Uso y restricción |
|---|---|
| `HASH` | Tabla acotada de claves y valores; la inserción puede fallar si se llena. Que la búsqueda tenga un coste esperado constante no garantiza una latencia determinada |
| `ARRAY` | Valores preasignados e inicializados a cero en índices válidos; cero no equivale a una clave HASH ausente |
| `LRU_HASH` | Caché acotada con expulsión de estilo LRU; no es un contador acumulativo sin pérdidas |
| `RINGBUF` | Varios productores y un consumidor entre CPU; tamaños de clave/valor cero, capacidad en bytes potencia de dos; una reserva fallida no bloquea |
| `PERF_EVENT_ARRAY` | Canales perf por CPU; el espacio de usuario debe aprovisionar/consumir eventos y contabilizar registros perdidos |
| `PROG_ARRAY` | Referencias a programas para tail calls; se aplican restricciones de compatibilidad y límites de llamadas |
| `PERCPU_HASH` / `PERCPU_ARRAY` | Menor contención entre CPU, pero no ausencia universal de condiciones de carrera. El espacio de usuario lee las ranuras de todas las CPU posibles con el relleno requerido |
| `SOCKMAP` / `SOCKHASH` | Referencias a sockets para redirecciones/programas compatibles; no sirven para hooks arbitrarios de operaciones de socket |

libbpf 1.x eliminó `struct bpf_map_def SEC("maps")`. Estas definiciones de estilo BTF muestran ocho categorías de mapas con sus tipos reales. Combina los mapas necesarios con un programa adecuado; las declaraciones, por sí solas, no forman una canalización de eventos.

**`map_types.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

/* Definitions only; combine the needed maps with a suitable program. */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} hash_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} total SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} cache SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __type(key, __u32);
    __type(value, __u32);
    /* libbpf determines max_entries from the number of possible CPUs. */
} perf_events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PROG_ARRAY);
    __uint(max_entries, 10);
    __type(key, __u32);
    __type(value, __u32);
} jump_table SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} cpu_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_SOCKMAP);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u32);
} sockets SEC(".maps");
```

Los contadores compartidos requieren incrementos atómicos. Para claves HASH nuevas, hay que insertarlas con `BPF_NOEXIST` y luego buscar/incrementar la entrada ganadora; inicializar con `BPF_ANY` puede sobrescribir el contador de otra CPU. Las entradas ARRAY ya existen en los índices válidos.

## eBPF en Cilium: innovación en redes de contenedores

### Arquitectura de Cilium y función de eBPF

![Funciones lógicas de Cilium: estado de Kubernetes y Operator, agentes por nodo, programas/mapas del kernel y observaciones de flujos de Hubble.](../../.gitbook/assets/en-networking-cilium-02-ebpf-1.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-02-ebpf-1.html)

El diagrama muestra responsabilidades lógicas, no ubicaciones obligatorias ni una única canalización de compilación. La CLI puede ejecutarse fuera del clúster; los agentes se ejecutan en los nodos gestionados compatibles. Los detalles de compilación/carga de programas varían según la versión y la función. Hubble Relay agrega flujos; las métricas de Prometheus usan endpoints separados.

El agente reconcilia endpoints, identidades, políticas y el estado del plano de datos. Operator gestiona tareas de ámbito de clúster configuradas, como el ciclo de vida de identidades/IPAM; no es la ruta de reenvío de paquetes. Hubble combina información de flujos BPF con eventos de proxies en espacio de usuario.

### Análisis detallado del plano de datos eBPF de Cilium

Estas funciones cooperan, pero no siguen un orden fijo para cada paquete:

1. **Entrada:** los hooks de socket pueden resolver backends de Service antes de que exista un paquete; TC gestiona las rutas de paquetes; la aceleración XDP opcional gestiona el tráfico externo compatible.
2. **Identidad/política:** la política de IP/identidad y de endpoint controla el acceso L3/L4. Las políticas HTTP/gRPC compatibles usan Envoy y las políticas DNS usan el proxy DNS; el análisis/la aplicación de L7 no se realiza exclusivamente en BPF.
3. **Estado/traducción:** conntrack y los mapas de servicio/backend, reverse-NAT y afinidad tienen funciones distintas. No todos los paquetes vuelven a seleccionar un backend.
4. **Reenvío:** el enrutamiento nativo o el overlay configurado transporta el tráfico. Las rutas de despacho y retorno DSR requieren los prerrequisitos de red del modo seleccionado.
5. **Observación:** los contadores/eventos del plano de datos y los eventos del proxy tienen límites de configuración y de pérdida durante la recopilación.

La disponibilidad del backend se obtiene del estado del plano de control y de los mecanismos de salud aplicables, no de un probe universal de aplicaciones BPF. Maglev, afinidad, DSR y aceleración son opciones de funciones, no valores predeterminados universales.

### Descripción de los principales programas eBPF de Cilium

| Código fuente de Cilium 1.20.3 | Función |
|---|---|
| `bpf/bpf_lxc.c` | Ruta de paquetes del endpoint, políticas, conntrack y reenvío |
| `bpf/bpf_overlay.c` | Ruta de paquetes del overlay |
| `bpf/bpf_host.c` | Ruta del host/dispositivo y procesamiento compatible del firewall de host |
| `bpf/bpf_xdp.c` | Ruta XDP, incluida la aceleración configurada del balanceador de carga |
| `bpf/bpf_sock.c` | Hooks cgroup de dirección de socket (IPv4 e IPv6): connect, sendmsg, recvmsg, getpeername, bind/post_bind y sock_release, usados para traducir servicios en el nivel de socket |
| `bpf/bpf_wireguard.c` | Programas del dispositivo `cilium_wg0` (`cil_from_wireguard`/`cil_to_wireguard`) que marcan el tráfico descifrado por WireGuard |
| `bpf/bpf_sock_term.c` | Iteradores BPF (TCP/UDP) que destruyen sockets conectados a backends de Service eliminados |
| `bpf/bpf_probes.c`, `bpf/bpf_alignchecker.c` | No son programas del plano de datos: ejecutan probes de funciones del kernel al iniciar el agente y comprueban la disposición de estructuras C/Go |
| `bpf/lib/lb.h` | Funciones auxiliares compartidas de balanceo de carga |
| `bpf/lib/policy.h` | Funciones auxiliares compartidas de políticas |

Para conocer el cargador, los puntos de conexión, las tail calls y el recorrido de cada programa, consulta [los detalles internos del plano de datos eBPF](08-ebpf-datapath-internals.md).

En esta versión no existen archivos de nivel superior `bpf_lb.c` ni `bpf_network.c`. Los nombres de funciones y los indicadores de funciones disponibles cambian; inspecciona la versión exacta en vez de tratar nombres conceptuales como si fueran archivos del código fuente.

### Uso de mapas eBPF en Cilium

Estos ejemplos no constituyen una API estable para la estructura de los mapas:

| Nombre / familia | Clave y función |
|---|---|
| `cilium_lxc` | Dirección/familia → metadatos de reenvío del endpoint; no es simplemente el ID del endpoint |
| `cilium_ipcache_v2` | Prefijo, familia de direcciones y contexto del clúster → metadatos de identidad/túnel |
| `cilium_policy_v3_<endpoint>` | Identidad, dirección, protocolo, puerto de destino y prefijo → entrada de política |
| `cilium_ct4_global`, `cilium_ct6_global`, `cilium_ct_any4_global`, etc. | Estado de tuplas de conexión; los mapas concretos dependen del protocolo, la familia y la configuración |
| `cilium_lb4_services_v2` / `cilium_lb6_services_v2` | Dirección/puerto, protocolo, ámbito y ranura de backend → metadatos del servicio/referencia al backend; los registros de backend están en mapas separados |
| `cilium_metrics` | Motivo, dirección y clave de ubicación en el código fuente → contadores de paquetes/bytes |

`cilium-dbg map get` muestra contenido almacenado en caché en espacio de usuario, que no necesariamente es un volcado actual del kernel. Usa decodificadores compatibles de `cilium-dbg bpf ...` o bpftool para las vistas del kernel que admiten. No escribas bytes sin procesar en mapas de Cilium como atajo para solucionar problemas.

### Funciones basadas en eBPF y sus límites

- **Políticas:** Kubernetes NetworkPolicy tiene semántica L3/L4; los recursos de Cilium añaden capacidades compatibles. Una regla de permiso L4 sin restricciones puede eludir una regla de permiso L7 restrictiva que se solape; inspecciona la política combinada.
- **Cifrado:** en los modos WireGuard/IPsec, BPF dirige el tráfico a esas funciones del kernel; la criptografía no consiste únicamente en instrucciones BPF. Configura claves, puertos, MTU y cobertura del tráfico según el modo elegido. Las operaciones de claves de IPsec y WireGuard difieren.
- **Service mesh:** los proxies en espacio de usuario proporcionan el procesamiento L7 compatible. La política L7 de Kafka se eliminó. mTLS/ztunnel para cargas de trabajo está en beta y tiene prerrequisitos separados; no se deduce del cifrado de nodos.
- **Ancho de banda:** EDT/bandwidth-manager y el control de congestión no garantizan QoS ni rendimiento de extremo a extremo.
- **Multiclúster:** Cluster Mesh requiere conectividad, identidades, direccionamiento y configuración compatible; no sincroniza automáticamente todos los objetos de política ni resuelve el enrutamiento.

## Laboratorio: desarrollo y depuración de programas eBPF

### 1. Desarrollo básico de un programa eBPF

Guarda los archivos con nombre en un directorio nuevo para el laboratorio. Este programa registra **intentos** de `execve`, incluidos los que luego fallan. `execveat` tiene un tracepoint distinto para la entrada a la llamada al sistema. La salida de depuración es compartida y ruidosa; no es un mecanismo de transporte de eventos de producción. `SEC()` especifica el tipo/hook previsto; los metadatos GPL corresponden a la función auxiliar utilizada aquí.

**`hello.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("tracepoint/syscalls/sys_enter_execve")
int hello_execve(void *ctx)
{
    (void)ctx;
    char message[] = "execve attempt\n";
    bpf_trace_printk(message, sizeof(message));
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

### 2. Programa eBPF avanzado con mapas

`sched_process_exec` se emite después de una transición de ejecución correcta en el kernel de referencia. Cuenta por `comm`, un nombre de tarea corto de como máximo 16 bytes, incluido el terminador; no identifica de forma única una ruta de ejecutable ni un proceso. Los nombres pueden repetirse o cambiar. Esto observa el host; no se limita automáticamente a un Pod.

El mapa admite como máximo 1.024 nombres. `lost_events[0]` cuenta los errores al leer un nombre y `[1]` los eventos sin una entrada de contador utilizable, incluido el agotamiento de capacidad. Estos contadores no cubren todos los posibles fallos de recopilación; los contadores de 64 bits pueden desbordarse. El laboratorio no elimina entradas mientras cuenta.

**`exec_shared.h`**

```c
#ifndef EXEC_SHARED_H
#define EXEC_SHARED_H
#define COMM_BYTES 16
#define MAX_COMMANDS 1024
struct comm_key {
    char comm[COMM_BYTES];
};
#endif
```

**`exec_count.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include "exec_shared.h"

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_COMMANDS);
    __type(key, struct comm_key);
    __type(value, __u64);
} exec_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 2);
    __type(key, __u32);
    __type(value, __u64);
} lost_events SEC(".maps");

static __always_inline void record_loss(__u32 reason)
{
    __u64 *lost = bpf_map_lookup_elem(&lost_events, &reason);
    if (lost)
        __sync_fetch_and_add(lost, 1);
}

SEC("tracepoint/sched/sched_process_exec")
int count_exec(void *ctx)
{
    (void)ctx;
    struct comm_key key = {};
    __u64 zero = 0;
    if (bpf_get_current_comm(key.comm, sizeof(key.comm)) != 0) {
        record_loss(0);
        return 0;
    }

    __u64 *count = bpf_map_lookup_elem(&exec_counts, &key);
    if (!count) {
        /* A competing CPU may insert first; never overwrite its count. */
        bpf_map_update_elem(&exec_counts, &key, &zero, BPF_NOEXIST);
        count = bpf_map_lookup_elem(&exec_counts, &key);
    }
    if (count)
        __sync_fetch_and_add(count, 1);
    else
        record_loss(1);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

#### Aplicación en espacio de usuario y vida útil de la conexión

Este cargador acepta cualquiera de los objetos de ejemplo, carga exactamente un programa, lo conecta y conserva el enlace hasta Ctrl-C/SIGTERM. Lee los descriptores de archivo de los mapas de contador del mismo objeto, en lugar de presuponer que existen pins. La iteración empieza con NULL y obtiene una muestra en vivo acotada y no atómica.

**`run_bpf.c`**

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <bpf/bpf.h>
#include <bpf/libbpf.h>
#include "exec_shared.h"

static volatile sig_atomic_t stopping;

static void stop(int signal_number)
{
    (void)signal_number;
    stopping = 1;
}

static int dump_counts(int map_fd, int lost_fd)
{
    struct comm_key current, next;
    const struct comm_key *previous = NULL;
    unsigned int seen = 0;

    while (seen < MAX_COMMANDS) {
        if (bpf_map_get_next_key(map_fd, previous, &next) != 0) {
            if (errno == ENOENT)
                break;
            perror("get next key");
            return -1;
        }
        __u64 value;
        if (bpf_map_lookup_elem(map_fd, &next, &value) == 0)
            printf("%.*s: %" PRIu64 "\n", COMM_BYTES, next.comm,
                   (uint64_t)value);
        else if (errno != ENOENT) {
            perror("lookup count");
            return -1;
        }
        current = next;
        previous = &current;
        seen++;
    }
    for (__u32 reason = 0; reason < 2; reason++) {
        __u64 value;
        if (bpf_map_lookup_elem(lost_fd, &reason, &value) != 0) {
            perror("lookup loss");
            return -1;
        }
        printf("lost[%u]: %" PRIu64 "\n", reason, (uint64_t)value);
    }
    if (fflush(stdout) != 0) {
        perror("flush output");
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct bpf_object *object = NULL;
    struct bpf_link *link = NULL;
    int result = 1;
    if (argc != 2) {
        fprintf(stderr, "usage: %s OBJECT.bpf.o\n", argv[0]);
        return 2;
    }
    struct sigaction action = {.sa_handler = stop};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) || sigaction(SIGTERM, &action, NULL)) {
        perror("sigaction");
        return 1;
    }
    object = bpf_object__open_file(argv[1], NULL);
    if (!object) {
        perror("open BPF object");
        return 1;
    }
    struct bpf_program *program = bpf_object__next_program(object, NULL);
    if (!program || bpf_object__next_program(object, program)) {
        fprintf(stderr, "expected exactly one program\n");
        goto cleanup;
    }
    if (bpf_object__load(object) != 0) {
        fprintf(stderr, "load failed; inspect libbpf/verifier diagnostics\n");
        goto cleanup;
    }
    int counts = bpf_object__find_map_fd_by_name(object, "exec_counts");
    int losses = bpf_object__find_map_fd_by_name(object, "lost_events");
    if (counts >= 0 && losses < 0) {
        fprintf(stderr, "counter object is missing lost_events\n");
        goto cleanup;
    }
    link = bpf_program__attach(program);
    if (!link) {
        perror("attach tracepoint");
        goto cleanup;
    }
    fprintf(stderr, "Attached; Ctrl-C detaches. Counts are live samples.\n");
    result = 0;
    while (!stopping) {
        if (counts >= 0 && dump_counts(counts, losses) != 0) {
            result = 1;
            break;
        }
        sleep(2);
    }
cleanup:
    bpf_link__destroy(link);
    bpf_object__close(object);
    return result;
}
```

#### Compilar y ejecutar

En instalaciones multiarch de Debian/Ubuntu, el directorio multiarch de GCC proporciona los encabezados UAPI `asm/`; ajusta las rutas para otras distribuciones. `-g` proporciona BTF para `.maps`. En la máquina virtual preparada, compila e inicia el cargador en la terminal A:

```bash
MULTIARCH=$(gcc -print-multiarch)
test -n "$MULTIARCH"
clang -O2 -g -target bpf -I"/usr/include/$MULTIARCH" \
  -c hello.bpf.c -o hello.bpf.o
clang -O2 -g -target bpf -I"/usr/include/$MULTIARCH" \
  -c exec_count.bpf.c -o exec_count.bpf.o
cc -O2 -Wall -Wextra run_bpf.c -o run_bpf \
  $(pkg-config --cflags --libs libbpf)
sudo ./run_bpf hello.bpf.o
```

En la terminal B, ejecuta `sudo cat /sys/kernel/tracing/trace_pipe`; en la terminal C, ejecuta un programa externo como `/usr/bin/true`. Detén el cargador hello con Ctrl-C y luego ejecuta `sudo ./run_bpf exec_count.bpf.o`. Observa cómo cambian los pares nombre/conteo mientras ejecutas comandos en otra terminal. El propio observador y otras actividades del host también generan eventos, por lo que no hay un total ni PID fijo garantizado. En la salida de hello pueden aparecer intentos fallidos de `execve`, pero no deberían emitir `sched_process_exec`.

`bpftool prog load OBJECT PIN` por sí solo no conecta este tracepoint. El ejemplo mantiene deliberadamente un enlace. La decisión de fijar/reutilizar recursos es independiente: `pinmaps` y `map ... pinned ...` no son sintaxis intercambiables. Al cerrar este cargador se liberan los recursos sin pin.

### 3. Exploración y depuración de programas eBPF de Cilium

Usa un clúster ya preparado y el contexto correcto de kubeconfig. Selecciona el agente que se ejecuta en el nodo del Pod afectado; los ID de endpoint son locales al nodo. Sustituye los marcadores de posición explícitos:

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-ACTUAL-POD
export ENDPOINT_ID=REPLACE-WITH-NODE-LOCAL-ID
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint get "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg service list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --frontends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
```

Inspecciona las políticas deseadas con `kubectl get networkpolicy,ciliumnetworkpolicy -n YOUR_NAMESPACE` y consulta por separado las políticas aplicables a todo el clúster. Compara el estado efectivo del endpoint con los flujos reales. `policy trace`, que se eliminó, y `policy get`, obsoleto, no son alternativas equivalentes.

Ejecuta un monitor cada vez y detenlo con Ctrl-C:

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent --   cilium-dbg monitor --related-to "$ENDPOINT_ID" --type drop
```

Usa `--type policy-verdict` para las decisiones de política emitidas o `--type l7` para los eventos de proxy disponibles. La visibilidad depende de la configuración. Un rechazo HTTP puede aparecer como HTTP 403, en lugar de un veredicto de red DROPPED.

Si Hubble Relay está habilitado, deja en ejecución `cilium hubble port-forward` y luego ejecuta:

```bash
hubble status
hubble observe --namespace default --last 20
hubble observe --protocol http --last 20
hubble observe --namespace default --last 20 --output json
```

El JSON canalizado a `jq` no es un grafo de dependencias entre servicios. Si está habilitada, la interfaz Hubble UI ofrece un mapa de servicios (`cilium hubble ui`). La visibilidad HTTP requiere una ruta proxy/L7 compatible; el contenido cifrado de la aplicación no se decodifica automáticamente.

### 4. Análisis y optimización del rendimiento

En un nodo controlado, con permisos/compatibilidad de profiling, inspecciona los ID reales de los programas. Estos comandos consultan el estado del kernel local; esta revisión no los ejecutó:

```bash
sudo bpftool prog show
export PROG_ID=REPLACE-WITH-ACTUAL-ID
sudo bpftool prog show id "$PROG_ID"
sudo bpftool prog dump xlated id "$PROG_ID"
sudo bpftool prog profile id "$PROG_ID" duration 10 cycles instructions
```

El profiling necesita nombres de métricas y soporte adecuado del kernel/PMU. `bpftool -p map dump ...` imprime el contenido con formato; no mide la latencia de búsqueda. `perf`/bpftrace pueden perfilar cargas de trabajo, pero comprueba los símbolos de destino, la disponibilidad de probes y sus argumentos. Un kretprobe no expone de manera fiable el `arg0` de entrada sin correlación explícita.

Al medir la carga de trabajo completa, registra protocolo, tamaño de paquete, concurrencia, política, cifrado, proxy y enrutamiento. Antes de cambiar XDP/enrutamiento nativo, inspecciona los valores de Helm instalados y `cilium-dbg status --verbose`. Un hook más rápido o un resultado sintético no demuestra que la latencia de la aplicación sea menor.

### 5. Consejos para solucionar problemas

| Síntoma | Qué comprobar |
|---|---|
| Falla la compilación C | Encabezados UAPI/libbpf correctos, objetivo del compilador BPF, `__u32`/`__u64` y `-g` para BTF |
| Rechazo del verificador | Salida de error del cargador/registro del verificador, límites, inicialización de pila, funciones auxiliares, licencia y complejidad |
| Cargado, pero sin eventos | Vida útil de la conexión/enlace, tracepoint exacto, evento desencadenante y permisos |
| Faltan datos del mapa | Misma instancia de mapa, errores de inserción/capacidad, significado de la clave y vida útil de referencias/pins |
| Flujo de Cilium incorrecto | Nodo/endpoint correcto, política deseada/efectiva combinada, estado de ruta/backend y comportamiento del proxy L7 |
| Faltan registros de Hubble | Relay, filtros, visibilidad configurada y reporte de eventos perdidos |

`trace_pipe` contiene la salida de tracing, no los diagnósticos del verificador. Para una prueba de carga intencional en la máquina virtual aislada, `-d` de bpftool muestra diagnósticos del cargador/verificador; aun así, cargar no demuestra que el programa esté conectado o funcione. No deshabilites políticas, amplíes privilegios de producción ni reescribas mapas para hacer pasar una prueba.

## Fuentes

- [Artículo original sobre BPF](https://www.tcpdump.org/papers/bpf-usenix93.pdf), [preguntas y respuestas de diseño de BPF en Linux](https://docs.kernel.org/bpf/bpf_design_QA.html), [verificador](https://docs.kernel.org/bpf/verifier.html), [ring buffer](https://docs.kernel.org/bpf/ringbuf.html), [licencias](https://docs.kernel.org/bpf/bpf_licensing.html), [seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [Carga de BPF en Linux 6.12](https://github.com/torvalds/linux/blob/v6.12/kernel/bpf/syscall.c), [ubicación del evento exec](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c), [libbpf 1.7](https://github.com/libbpf/libbpf/tree/v1.7.0), [bpftool 7.7](https://github.com/libbpf/bpftool/releases/tag/v7.7.0)
- [Código fuente BPF de Cilium 1.20.3](https://github.com/cilium/cilium/tree/v1.20.3/bpf), [mapas](https://github.com/cilium/cilium/tree/v1.20.3/pkg/maps), [mapas del balanceador de carga](https://github.com/cilium/cilium/tree/v1.20.3/pkg/loadbalancer/maps), [referencia de comandos](https://github.com/cilium/cilium/tree/v1.20.3/Documentation/cmdref)
- [Requisitos del sistema de Cilium](https://docs.cilium.io/en/v1.20/operations/system_requirements/), [compatibilidad con Kubernetes](https://docs.cilium.io/en/v1.20/network/kubernetes/compatibility/), [sustitución de kube-proxy](https://docs.cilium.io/en/v1.20/network/kubernetes/kubeproxy-free/), [cifrado](https://docs.cilium.io/en/v1.20/security/network/encryption/)

## Prueba de comprensión

[Comprueba lo que aprendiste](../../quizzes/networking/cilium/02-ebpf-quiz.md).
