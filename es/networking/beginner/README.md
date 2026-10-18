# Redes Linux desde cero

> **Referencia de aprendizaje**: Ubuntu Server 24.04 LTS, con una ruta alternativa para Rocky Linux 9
>
> **Última actualización**: 15 de septiembre de 2026

Este curso comienza con su primera terminal. Cree archivos e instale programas; después configure IP y DNS, conéctese mediante SSH, aplique reglas de firewall y observe paquetes. Termine diagnosticando un pequeño servicio web y relacionando lo aprendido con Docker, Kubernetes y las redes en la nube.

No hace falta memorizar todos los comandos. El objetivo es explicar **qué máquina está modificando, cómo comprobar que el cambio funcionó y cómo restaurar el estado anterior**.

## Mapa del curso {#course-map}

Si es principiante, empiece por la lección 1. Incluso quienes ya conocen Linux necesitan el entorno de laboratorio compartido y la identificación de interfaces de la lección 2. Los tiempos son estimaciones de planificación que incluyen la práctica individual; el tiempo real depende de la experiencia.

| Orden | Lección | Qué podrá hacer | Tiempo estimado |
|---|---|---|---|
| 1 | [Linux y la CLI](01-linux-cli.md) · [Cuestionario](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | Identificar una distribución y trabajar con archivos, editores, paquetes y servicios | 2–3 horas |
| 2 | [Direcciones e interfaces](02-addressing-interfaces.md) · [Cuestionario](../../quizzes/networking/beginner/02-addressing-interfaces-quiz.md) | Distinguir las funciones de IP, subred, gateway y DNS, e identificar una NIC | 2–3 horas |
| 3 | [Configuración de red persistente](03-persistent-configuration.md) · [Cuestionario](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) | Configurar Netplan o NetworkManager y comprobar el comportamiento tras reinicios y recuperación | 3–4 horas |
| 4 | [DNS y conectividad](04-dns-connectivity.md) · [Cuestionario](../../quizzes/networking/beginner/04-dns-connectivity-quiz.md) | Investigar por separado nombres, rutas, puertos y HTTP | 2–3 horas |
| 5 | [Acceso remoto con SSH](05-ssh-access.md) · [Cuestionario](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | Verificar claves de host, iniciar sesión con una clave de usuario y comprobar los ajustes efectivos | 2–3 horas |
| 6 | [Firewalls y seguridad del host](06-firewalls-host-security.md) · [Cuestionario](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | Permitir el tráfico necesario y explicar SELinux y Fail2ban | 3–4 horas |
| 7 | [Supervisión y rendimiento](07-monitoring-performance.md) · [Cuestionario](../../quizzes/networking/beginner/07-monitoring-performance-quiz.md) | Observar sockets, paquetes y tráfico y explicar las limitaciones de las mediciones | 2–3 horas |
| 8 | [Proyecto final y conexiones con la nube](08-container-cloud-capstone.md) · [Cuestionario](../../quizzes/networking/beginner/08-container-cloud-capstone-quiz.md) | Reproducir, aislar y recuperar errores pequeños, y elegir el siguiente paso | 3–4 horas |

Antes de continuar, cumpla los criterios de finalización de cada lección y explique con sus propias palabras las respuestas del cuestionario. Después de aprender a gestionar paquetes en la lección 1, vuelva a [preparar las herramientas de los sistemas invitados](#guest-tools) antes de las lecciones 2–4. El ajuste del kernel y las comparaciones de implementaciones de CNI vienen después de los ejercicios principales.

## Preparar las máquinas virtuales de laboratorio {#lab-environment}

### Empezar con una máquina virtual

1. Use una aplicación de virtualización compatible con su PC. Haga coincidir la imagen del sistema operativo con la arquitectura de CPU virtual compatible. Por ejemplo, las máquinas Arm necesitan una imagen Arm compatible con esa herramienta de virtualización.
2. Seleccione una imagen **24.04 LTS** de las [descargas oficiales de Ubuntu Server](https://ubuntu.com/download/server). Si usa otra versión, vuelva a comprobar los valores predeterminados de paquetes y servicios. Siga la [guía de instalación](https://documentation.ubuntu.com/server/tutorial/basic-installation/) y cree un usuario normal con contraseña. Los ejemplos usan `student`; sustitúyalo por su nombre de usuario.
3. Como asignación inicial, use 2 vCPU, 2 GiB de memoria y 20 GiB de disco por máquina virtual. Es una sugerencia de planificación para el laboratorio, no una garantía de rendimiento ni un requisito mínimo para todos los hipervisores.
4. Conecte la primera NIC a la **red NAT del hipervisor con DHCP**. Permite instalar el sistema y descargar paquetes, y no se modifica en los ejercicios posteriores.
5. Inicie sesión desde la **ventana de consola** del hipervisor. Todavía no necesita SSH. Apague el sistema invitado normalmente y tome una instantánea de la instalación limpia.

La lección 1 solo necesita una máquina virtual. Un contenedor normal no sustituye systemd ni los administradores de red de una VM completa. WSL sirve para practicar en la shell, pero no suponga que su entorno de red/firewall posterior es idéntico.

### Preparar dos máquinas virtuales a partir de la lección 2

Usar Ubuntu en ambas máquinas invitadas permite centrarse en una distribución. Rocky Linux 9 es una ruta alternativa. Use las [imágenes oficiales de Rocky](https://rockylinux.org/download) y su [documentación](https://docs.rockylinux.org/); no hace falta aprender ambas distribuciones a la vez.

1. Instale la segunda máquina virtual por separado y asigne a las máquinas invitadas los nombres `net-client` y `net-server`. Una clonación sencilla puede duplicar los identificadores de máquina y las claves de host SSH; por eso, al principio use instalaciones independientes.
2. Apague ambas máquinas invitadas normalmente y añada una **segunda NIC** a cada una.
3. Conecte las segundas NIC a la misma **red virtual interna**, por ejemplo `linux-net-lab`. No conecte un servidor DHCP ni un enlace externo a esa red. Los modos «bridged», «NAT» y «host-only» no son intercambiables: compruebe a qué conecta realmente el modo seleccionado.
4. Anote la dirección MAC de cada NIC en los ajustes del hipervisor. Inicie las máquinas invitadas y, en la lección 2, haga coincidir esas direcciones con `ip -br link`. Los nombres como `eth1`, `enp0s8` y `ens19` varían; no copie un nombre de interfaz a ciegas.
5. Configure las direcciones IP en las lecciones 2 y 3. Durante la instalación no añada una gateway ni un servidor DNS arbitrarios a la segunda NIC.

| Elemento | VM cliente | VM servidor |
|---|---|---|
| Función | Envía solicitudes SSH y curl | Recibe solicitudes SSH y HTTP |
| NIC de administración | Conservar la configuración NAT/DHCP existente | Conservar la configuración NAT/DHCP existente |
| NIC de laboratorio | `192.0.2.10/24` | `192.0.2.20/24` |
| Gateway/DNS de la NIC de laboratorio | Ninguno | Ninguno |
| Acceso de recuperación | Consola e instantánea del hipervisor | Consola e instantánea del hipervisor |

```text
Client lab NIC                       Server lab NIC
192.0.2.10/24 ── internal virtual network ── 192.0.2.20/24
      |                                       |
Separate NAT/DHCP management NIC     Separate NAT/DHCP management NIC
```

`192.0.2.0/24` es un rango reservado para documentación y aquí solo se usa en la red local aislada; no es un diseño de red enrutado públicamente. Las NIC de administración siguen conectando las máquinas invitadas a otra red, por lo que la VM completa no queda aislada de toda red externa.

## Preparar herramientas de los sistemas invitados después de la lección 1 {#guest-tools}

Primero aprenda el [flujo de trabajo de paquetes de la lección 1](01-linux-cli.md) y después complete este punto de control **dentro de cada sistema invitado descartable antes de las lecciones 2–4**. Use la conexión de administración NAT/DHCP existente para acceder a los repositorios; no dé a la NIC interna del laboratorio un enlace externo, gateway o servidor DNS. Una imagen mínima puede no incluir herramientas de diagnóstico aunque la red funcione.

### Identificar los comandos que faltan y sus paquetes

**En cada sistema invitado, como usuario normal; solo inspección:**

```bash
hostname
cat /etc/os-release
command -v ip ss ping getent grep timeout dig tracepath traceroute python3 curl nc ncat
```

Si aparece la ruta del ejecutable, el comando está disponible. Si el resultado no está claro, consulte un nombre; por ejemplo, `command -v dig`. Que no aparezca una ruta o que el estado sea distinto de cero para una alternativa que falta es normal. Anote los comandos que necesita **ese sistema invitado para los ejercicios elegidos**, no todos los nombres ausentes.

| Comando / uso | Paquete de Ubuntu Server 24.04 | Paquete de Rocky Linux 9 | Dónde hace falta |
|---|---|---|---|
| `ip`, `ss`: interfaces, rutas y sockets | `iproute2` | `iproute` | Ambas máquinas |
| `ping`: comprobaciones ICMP acotadas | `iputils-ping` | `iputils` | Ambas máquinas |
| `dig`: consultas del protocolo DNS | `bind9-dnsutils` | `bind-utils` | Cliente en la lección 4 |
| `tracepath`: opción predeterminada para trazar rutas | `iputils-tracepath` | `iputils` | Cliente; elija esta opción o la siguiente |
| `traceroute` de Linux: opción alternativa para trazar rutas | `traceroute` | `traceroute` | Cliente, solo si selecciona esta alternativa |
| `python3`: servidor HTTP temporal | `python3` (instala también los paquetes del intérprete) | `python3` | Servidor |
| `curl`: solicitudes HTTP | `curl` | Proveedor existente `curl-minimal` **o** `curl` | Autocomprobaciones de cliente y servidor |
| OpenBSD `nc` / Ncat `ncat`: prueba TCP | `netcat-openbsd` → use `nc` | `nmap-ncat` → use `ncat` | Cliente |

Este punto de control elige **`tracepath` de forma predeterminada**; si ya tiene instalado Linux `traceroute`, puede usarlo con los comandos correspondientes de la lección 4. No necesita ambos. En Rocky, `iputils` proporciona `ping` y `tracepath`. Use la implementación de netcat indicada: que los nombres de comandos sean similares no garantiza que las opciones sean idénticas.

`getent`, `grep`, `timeout`, sudo y el editor forman parte de las herramientas base de la máquina invitada/lección 1. Si esas comprobaciones fallan, resuelva primero esa base. No instale otro administrador de red ni resolver para cumplir esta tabla. En un **sistema Rocky ya administrado por NetworkManager**, el paquete `NetworkManager-tui` proporciona `nmtui`, de forma opcional; inspecciónelo o instálelo mediante el mismo flujo de trabajo de paquetes seleccionados solo si elige esa interfaz. Un sistema invitado que usa networkd no lo necesita.

### Previsualizar e instalar solo las herramientas seleccionadas que falten

Antes de la primera instalación, tome una instantánea del sistema invitado llamada `before-guest-tools` y anote el estado de paquetes/proveedores instalados. Use **solo la sección de su distribución**. Cada ejemplo da por hecho que falta `dig`. Si ya está disponible, omita esa instalación. Si falta otro comando seleccionado, sustituya `TOOL_PACKAGE` por su único paquete de la tabla y repita las comprobaciones del candidato y la transacción; no pegue toda la matriz en un comando de instalación.

**Sistema invitado Ubuntu, como usuario normal; use sudo solo en las líneas indicadas:**

```bash
TOOL_PACKAGE=bind9-dnsutils
dpkg-query -W "$TOOL_PACKAGE"
sudo apt update
apt-cache policy "$TOOL_PACKAGE"
sudo apt-get --simulate install "$TOOL_PACKAGE"
```

Que la consulta local indique «No packages found» es normal si no está instalado el paquete. Después de actualizar correctamente los índices de los repositorios, inspeccione la versión de `Candidate` y las dependencias, actualizaciones y eliminaciones simuladas. Si no hay ningún candidato o se producen errores de repositorio, deténgase y compruebe los repositorios Ubuntu configurados y la ruta de administración. Si el paquete ya está instalado pero no encuentra el comando, investigue sus archivos y la ruta de búsqueda de comandos en vez de instalar un proveedor que entre en conflicto.

Solo cuando **falte el comando seleccionado** y la vista previa muestre el paquete y sus dependencias previstos, instálelo en el **sistema invitado Ubuntu**:

```bash
sudo apt install "$TOOL_PACKAGE"
```

Revise también el mensaje real antes de aceptar; los metadatos pueden cambiar entre la vista previa y la instalación. No confirme automáticamente actualizaciones o eliminaciones inesperadas.

**Sistema invitado Rocky, como usuario normal:** compruebe el proveedor de curl por separado antes de seleccionar paquetes.

```bash
command -v curl
rpm -q curl curl-minimal
```

Una consulta de paquete puede informar «not installed»; es normal. Si `curl` ya funciona, **conserve el proveedor que lo proporciona** y no solicite el otro paquete. Una vez que la comprobación de disponibilidad tenga éxito, puede identificar al propietario con `rpm -qf "$(command -v curl)"`. Para estos ejercicios HTTP, el `curl-minimal` existente es suficiente. `curl` y `curl-minimal` son incompatibles; no use `--allowerasing` ni cambie de paquete para seguir este curso.

Si falta `curl` y **no está instalado ninguno de los dos proveedores**, seleccione `curl-minimal` mediante el flujo de trabajo siguiente. Si hay un proveedor instalado pero no se encuentra el comando, inspeccione sus archivos y PATH en vez de sustituirlo.

**Sistema invitado Rocky, como usuario normal; ejemplo solo si falta `dig`:**

```bash
TOOL_PACKAGE=bind-utils
rpm -q "$TOOL_PACKAGE"
dnf info "$TOOL_PACKAGE"
sudo dnf --assumeno install "$TOOL_PACKAGE"
```

Compruebe el paquete disponible, la arquitectura, el repositorio y las dependencias/eliminaciones propuestas. `--assumeno` rechaza la transacción sin instalar nada; el estado distinto de cero que devuelve la transacción rechazada no significa que haya fallado una prueba de red. Si no hay ningún candidato, investigue los repositorios configurados de Rocky 9. La tabla obligatoria no requiere EPEL. Después, instale en el **sistema invitado Rocky** **solo el paquete del comando seleccionado que falte**:

```bash
sudo dnf install "$TOOL_PACKAGE"
```

Revise la transacción final antes de confirmarla. Conserve los proveedores de curl instalados y el administrador de red existente. Los candidatos/versiones de los paquetes observados en el sistema invitado no están garantizados por este documento.

### Volver a comprobar comandos y conservar un registro de recuperación

**En ambas máquinas, como usuario normal:** `command -v ip ss ping getent grep timeout` debe encontrar las herramientas base. Para las selecciones predeterminadas de este punto de control, compruebe lo siguiente en la máquina indicada:

```bash
# Client, either distribution; substitute traceroute only if you selected it:
command -v dig tracepath curl
```

```bash
# Ubuntu client only:
command -v nc
```

```bash
# Rocky client only:
command -v ncat
```

```bash
# Server, either distribution:
command -v python3 curl
python3 --version
```

Deberían aparecer las rutas de las herramientas seleccionadas y Python 3.9 o posterior. Anote los paquetes que instaló; estas comprobaciones confirman que están disponibles, no que la comunicación de red funcione. Si en la lección 4 falta una herramienta necesaria, vuelva aquí.

Conserve las herramientas para las lecciones siguientes. Eliminar los paquetes indicados no revierte exactamente las dependencias, la configuración, las cachés ni los registros; nunca quite un proveedor preexistente ni use autoremove general como limpieza. Para revertir por completo esta preparación, una vez terminados los ejercicios que dependen de ella, restaure `before-guest-tools`; tenga presente que la instantánea también descarta el trabajo posterior en la máquina invitada.

Las asignaciones de paquetes se comprobaron con fuentes primarias de las distribuciones el 15 de septiembre de 2026: listas de archivos de Ubuntu Noble para [iproute2](https://packages.ubuntu.com/noble/amd64/iproute2/filelist), [ping](https://packages.ubuntu.com/noble/amd64/iputils-ping/filelist), [dig](https://packages.ubuntu.com/noble/amd64/bind9-dnsutils/filelist), [tracepath](https://packages.ubuntu.com/noble/amd64/iputils-tracepath/filelist), [traceroute](https://packages.ubuntu.com/noble/amd64/traceroute/filelist), [netcat](https://packages.ubuntu.com/noble/amd64/netcat-openbsd/filelist), [curl](https://packages.ubuntu.com/noble/amd64/curl/filelist) y [dependencias del paquete de Python](https://packages.ubuntu.com/noble/python3); especificaciones de paquetes Rocky 9 para [iproute](https://git.rockylinux.org/staging/rpms/iproute/-/blob/r9/SPECS/iproute.spec), [iputils](https://git.rockylinux.org/staging/rpms/iputils/-/blob/r9/SPECS/iputils.spec), [utilidades de BIND](https://git.rockylinux.org/staging/rpms/bind/-/blob/r9/SPECS/bind.spec), [Ncat](https://git.rockylinux.org/staging/rpms/nmap/-/blob/r9/SPECS/nmap.spec) y [proveedores de curl](https://git.rockylinux.org/staging/rpms/curl/-/blob/r9/SPECS/curl.spec). Las consultas en vivo del sistema invitado seleccionan la arquitectura/versión correspondiente; una lista de archivos de ejemplo para x86_64 no obliga a usar esa arquitectura.

## Cómo leer los comandos {#command-conventions}

- **Cliente**, **servidor** y **ambas máquinas** indican dónde ejecutar un comando. Compruebe primero el nombre de host.
- Los bloques de comandos omiten los indicadores `$` y `#`. `sudo` solicita privilegios de administrador para ese comando.
- Los nombres en mayúsculas, como `LAB_IF`, son variables de la shell actual. Asígnelas otra vez en una terminal nueva, después de identificar la NIC real según las instrucciones.
- Los bloques YAML e INI contienen archivos de configuración, no comandos para pegar en la shell.
- La «salida ilustrativa» no garantiza el resultado de su ejecución. Compare las direcciones, interfaces, contadores y horas con su propio entorno.
- Antes de hacer cambios, registre el estado y la configuración anteriores. Cambie una sola cosa cada vez y, si falla una comprobación, use el procedimiento de recuperación de la lección.

Estos ejercicios se ejecutan en máquinas virtuales desechables. No requieren cambiar la red ni el firewall del dispositivo con el que está leyendo o de un servidor de producción remoto.

## Glosario inicial {#starter-glossary}

| Término | Significado inicial |
|---|---|
| Kernel / espacio de usuario | Núcleo que administra el hardware y los recursos / shells y programas que funcionan encima |
| NIC / interfaz | Dispositivo de comunicación / nombre y ajustes del sistema operativo para operarlo |
| MAC / IP | Dirección para entregar tramas en un enlace / dirección para entregar paquetes entre redes |
| Subred / prefijo | Rango de direcciones que comparte los primeros bits / longitud de esos bits |
| Gateway / ruta | Siguiente enrutador al que se reenvía / regla de reenvío seleccionada para un destino |
| DHCP / DNS | Asigna la configuración de red / busca la información asociada a un nombre |
| TCP / UDP / puerto | Dos protocolos de transporte / número que identifica un endpoint de comunicación en un host |
| HTTP / SSH | Protocolo web de solicitud/respuesta / protocolo autenticado y cifrado de acceso remoto |
| Socket / listener | Endpoint de comunicación de un programa / socket que espera conexiones nuevas |
| Firewall / SELinux | Reglas de tráfico / política que controla el acceso de los procesos a recursos |
| NAT / CNI | Traducción de direcciones / ecosistema de interfaz e implementación para configurar la red de contenedores |

## Criterios de finalización {#completion}

Para considerar el curso completado debe haber hecho algo más que «ejecutar el comando».

- Explique su distribución y administrador de paquetes, y edite un archivo.
- Distinga las NIC de laboratorio y de administración, y localice quién administra los ajustes de IP, rutas y DNS.
- Compruebe la identidad del host SSH, el inicio de sesión mediante clave, la configuración efectiva y la recuperación.
- Permita el servicio de laboratorio solo al cliente previsto y revierta las reglas que añadió.
- Distinga, a partir de las observaciones, los fallos de DNS, los de conexión TCP y los errores HTTP.
- Combine datos de socket, paquetes y aplicación en un [informe del proyecto final](08-container-cloud-capstone.md#capstone-report).

Continúe con los [detalles de los protocolos](../../basics/06-network-fundamentals-part1.md), las [rutas de paquetes del kernel](../../kernel/02-network-stack.md), el [diagnóstico avanzado de Linux](../07-linux-network-diagnostics.md) y el [laboratorio de Service de Kubernetes](../../labs/core/03-services-networking-lab.md). Instalar un producto CNI no tiene que ser el primer paso.

## Continuar por la ruta avanzada

La [ruta avanzada de redes](../expert/README.md) sigue este curso para principiantes con seis cuadernos prácticos sobre protocolos, enrutamiento, rutas de paquetes y evidencia de políticas/fallos antes, durante y después. Los entornos varían entre capítulos; empiece con su [comprobación de entrada](../expert/README.md#entry-check).

## Usar cursos externos {#further-study}

Los cursos externos son opcionales. El [curso de redes Linux de Bootlin](https://bootlin.com/training/networking/) puede servir para profundizar después en las redes del kernel; el [catálogo de redes de Linux Foundation](https://training.linuxfoundation.org/networking/) ayuda a encontrar una continuación especializada. Compruebe el alcance, los precios y los horarios con el proveedor.

Al leer material de CentOS 7 o lecciones antiguas basadas en `ifconfig`, separe los conceptos del entorno de ejecución. Este curso usa `ip`, `ss` y las distribuciones indicadas arriba.

**Inicio:** [Lección 1: Linux y la CLI](01-linux-cli.md)
