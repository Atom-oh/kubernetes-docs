# 1. Tu primera terminal Linux

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Preparación del curso](README.md) | [Cuestionario](../../quizzes/networking/beginner/01-linux-cli-quiz.md) | [Siguiente: Direcciones e interfaces](02-addressing-interfaces.md)

La administración de redes comienza con poder responder tres preguntas: qué máquina estoy usando, qué archivo voy a cambiar y cómo desharé el cambio. En esta lección desarrollarás esos hábitos al crear un pequeño cuaderno, editarlo, inspeccionar sus permisos y leer el estado de un servicio.

## Requisitos previos y objetivos

Usa una **VM local** desechable con una cuenta de usuario normal, su contraseña y permiso para usar `sudo`. Abre la VM desde la consola del hipervisor; un hipervisor es la aplicación que ejecuta máquinas virtuales. Ubuntu Server 24.04 LTS es la ruta principal. Rocky Linux 9 es una alternativa: no hace falta aprender ambos a la vez. Un contenedor típico no proporciona el entorno completo de systemd arrancado que usamos aquí.

Asegúrate de que el sistema invitado tenga Bash, utilidades básicas de GNU, `ps`, systemd, `nano` y una implementación de `vi`. Si falta un editor, usa la sección de preparación de paquetes de más abajo antes de iniciar el cuaderno. En esta lección no se configura la red. Conserva la interfaz de administración NAT/DHCP existente, tal como se preparó en la introducción del curso.

Al terminar, podrás:

- Explicar qué aportan el kernel, las bibliotecas, el shell y la distribución.
- Recorrer rutas y crear, copiar, mover, editar y eliminar tus propios archivos de práctica.
- Guardar o descartar cambios en nano y vi, e interpretar la propiedad y los permisos básicos.
- Elegir las herramientas de paquetes de Ubuntu o Rocky y distinguir el software instalado de un servicio en ejecución.
- Leer ID de procesos, estados de systemd y una selección acotada de mensajes del journal.

**Contrato de ejecución:** cada bloque de shell de abajo se ejecuta **dentro de la VM de práctica**, nunca en el sistema operativo anfitrión de tu portátil, el host de este checkout de documentación ni un servidor en la nube. Los bloques sin `sudo` se ejecutan como usuario normal. Una línea con `sudo` eleva solo ese comando. Ejecuta un paso cada vez y detente ante un error inesperado. Las muestras de salida son ilustrativas, **no transcripciones de VM Ubuntu/Rocky probadas en vivo**.

## Comprende el sistema en el que iniciaste sesión

«Linux» puede referirse al **kernel** o, de manera informal, al sistema operativo completo. El kernel administra el tiempo de CPU, la memoria, los sistemas de archivos, los controladores de dispositivos y los paquetes de red. Proporciona llamadas al sistema para que los programas soliciten estos servicios. El shell y el editor se ejecutan en el **espacio de usuario**, fuera del kernel.

Una **biblioteca** proporciona funciones reutilizables. Por ejemplo, la biblioteca C de GNU (glibc) ofrece funciones que muchos programas utilizan para texto, E/S de archivos y acceso al sistema operativo. Algunas funciones de biblioteca llaman al kernel; otras solo trabajan con datos en memoria. Una biblioteca no es un editor ni un segundo kernel. A menudo hay dependencias de paquetes porque una aplicación necesita una biblioteca determinada.

Una **distribución** reúne el kernel, las bibliotecas, los comandos, el instalador, los repositorios, las actualizaciones y la configuración predeterminada en un sistema instalable. Un repositorio es una fuente administrada de paquetes de software; un paquete contiene software e información sobre su versión y dependencias.

| Distribución | Relación y familia de paquetes | Qué significa para este curso |
| --- | --- | --- |
| Debian | Distribución comunitaria que usa paquetes `.deb`, APT y dpkg | Explica la familia de la que proviene Ubuntu; los valores predeterminados de red/servicios de Debian no se aplican automáticamente a Ubuntu |
| Ubuntu | Distribución derivada de Debian con sus propias versiones y repositorios | Sigue la ruta de comandos de Ubuntu Server 24.04 LTS |
| Rocky Linux | Distribución de Linux empresarial del ecosistema RHEL; paquetes `.rpm`, DNF y RPM | Sigue la ruta alternativa de paquetes de Rocky 9 |

La **terminal** gestiona el teclado y la pantalla de texto. El **shell**, Bash en este curso, interpreta lo que escribes y ejecuta comandos. Escribir `ls` solicita a un programa del espacio de usuario que liste archivos; no es una conversación directa con el kernel. Estas distinciones se basan en la documentación de Debian y GNU que aparece en las referencias.

**VM de práctica, usuario normal; solo inspección:**

```bash
hostname
whoami
id
cat /etc/os-release
uname -r
pwd
```

`hostname` identifica al sistema invitado; compáralo con la ventana de consola que abriste. `whoami` identifica tu cuenta. `id` incluye tu ID numérico de usuario (UID), ID de grupo y grupos. Si UID es `0`, eres root: vuelve a la cuenta normal para estos ejercicios. `cat` muestra un archivo de texto. En `/etc/os-release`, inspecciona `ID` y `VERSION_ID`: la ruta principal debe indicar Ubuntu y `24.04`, y la alternativa Rocky y `9.x`. `uname -r` informa de la **versión del kernel en ejecución**, que no es el número de versión de la distribución. `pwd` imprime el directorio de trabajo actual.

Un prompt ilustrativo es `learner@client:~$`: cuenta, máquina, directorio actual y luego el marcador de prompt. `~` representa tu directorio personal. `$` suele indicar un shell normal y `#` suele indicar root, pero los prompts se pueden personalizar; confía en `id`. **No escribas el marcador de prompt.** En los bloques de comandos, una línea que comienza con `#` es un comentario explicativo de Bash.

## Lee los comandos antes de ejecutarlos

En `ls -la notes`, `ls` es el comando, `-l` y `-a` son opciones y `notes` es el argumento de ruta. `-l` solicita detalles; `-a` incluye nombres que empiezan con un punto. Pulsa Enter para ejecutar un comando, Tab para completar una ruta parcialmente escrita y la flecha arriba para recuperar un comando anterior. Inspecciona los comandos recuperados antes de pulsar Enter.

Las rutas Linux forman un árbol cuyo origen es `/`. Una ruta **absoluta** empieza allí, como `/home/learner`; una **relativa** empieza en el directorio de trabajo, como `notes/draft.txt`. `.` significa el directorio actual y `..` su directorio padre. En los sistemas de archivos Linux habituales de aquí, `Notes` y `notes` son nombres distintos.

`/etc` contiene configuración del sistema, `/var/log` contiene muchos registros y `/home` contiene los directorios personales de usuarios normales. Leeremos información del sistema, pero solo escribiremos archivos de práctica dentro de un directorio privado recién creado.

**VM de práctica, usuario normal; ayuda integrada/local:**

```bash
help cd
ls --help
man ls
```

`cd` es un comando integrado del shell, por lo que `help` de Bash lo explica. `--help` imprime el uso del comando. Si está instalado el programa opcional `man` y sus páginas, `man ls` abre una página en un paginador: Espacio avanza, `/permission` busca y `q` sale. Si `man` no está disponible, siguen sirviendo `ls --help` y las referencias. `Ctrl+C` cancela una línea de shell sin terminar o interrumpe muchos programas en primer plano; no es un comando universal para «guardar y salir».

## Preparación de paquetes: elige una distribución

La gestión de paquetes permite obtener un editor, incluidas sus bibliotecas necesarias, desde repositorios configurados. Primero inspecciona lo que ya está instalado. Estas consultas usan la base de datos local de paquetes y no necesitan conexión a repositorios ni privilegios elevados.

**Solo VM de práctica Ubuntu, usuario normal:**

```bash
dpkg-query -W bash coreutils nano vim-tiny iproute2
```

**Solo VM de práctica Rocky, usuario normal:**

```bash
rpm -q bash coreutils nano vim-minimal iproute
```

Cada paquete instalado muestra su nombre/versión. Un mensaje como «no instalado» o «no se encontraron paquetes» identifica un paquete ausente; no es una invitación a reemplazar todo el sistema. Nombres de paquetes diferentes pueden proporcionar el mismo comando, así que inspecciona también los comandos directamente.

**Cualquiera de las VM de práctica, usuario normal:**

```bash
command -v nano
command -v vi
```

Una ruta de ejecutable como `/usr/bin/vi` significa que el comando está disponible. Si no aparece una ruta, no se encontró en la ruta de búsqueda de comandos del shell.

Si falta un editor, lo siguiente es una **operación opcional de preparación del sistema invitado**. Usa únicamente el bloque correspondiente a la distribución, mediante la conexión de administración que ya funciona. Primero crea en el hipervisor una instantánea identificada de la VM, por ejemplo `before-cli-editors`, para poder restaurar el estado completo anterior a la instalación. Lee la transacción propuesta y confirma solo el editor y las dependencias esperados; responde `n` para cancelar una eliminación o actualización inesperada.

**Solo VM de práctica Ubuntu, usuario normal que invoca sudo:**

```bash
sudo apt update
sudo apt install nano vim-tiny
```

`apt update` actualiza el índice de paquetes disponibles; **no** actualiza todo el software instalado. Continúa con la instalación solo si la actualización del índice termina sin errores de repositorio. `apt install` instala los paquetes indicados y resuelve dependencias. `apt upgrade` tiene otro propósito: actualizar paquetes instalados; no hace falta para esta lección.

**Solo VM de práctica Rocky, usuario normal que invoca sudo:**

```bash
sudo dnf install nano vim-minimal
```

DNF resuelve dependencias de paquetes RPM y actualiza los metadatos de repositorio cuando es necesario. Rocky 9 también ofrece compatibilidad `yum` para comandos conocidos, pero este curso usa `dnf`. No ejecutes ambas familias de comandos en el mismo sistema invitado ni añadas repositorios de terceros para hacer funcionar un ejemplo.

Después de la preparación, repite la consulta local de paquetes y las comprobaciones con `command -v`. Si falla la descarga de paquetes, el problema está en la conexión de administración o el acceso al repositorio; no está relacionado con la interfaz de red aislada que se introduce en la siguiente lección.

**Recuperación:** `apt remove` o `dnf remove` eliminan paquetes, pero no revierten exactamente la instalación: pueden quedar cambios en dependencias, cachés, registros y parte de la configuración. No elimines un editor que ya estuviera instalado. Conserva los editores para las lecciones siguientes o restaura la instantánea `before-cli-editors` cuando termines con el sistema invitado; una instantánea también descarta todo el trabajo posterior. No hace falta eliminar paquetes ni ejecutar `autoremove` para limpiar el cuaderno.

## Crea un cuaderno en un directorio temporal único

Primero define el ámbito del ejercicio. `$HOME` ya nombra tu directorio personal; no lo redefinas. `LAB_DIR` es una variable nueva para esta lección. `$(...)` captura la salida de un comando y las comillas dobles mantienen unida una ruta aunque contenga espacios.

**VM de práctica, usuario normal:**

```bash
LAB_DIR=$(mktemp -d "$HOME/network-beginner-cli.XXXXXX")
printf '%s\n' "$LAB_DIR"
```

`mktemp -d` crea un directorio nuevo y sustituye las seis `X` por un sufijo único. `printf '%s\n'` imprime la ruta almacenada y un salto de línea. Espera una ruta como `/home/learner/network-beginner-cli.aB12Cd`, con **tu** cuenta y sufijo. Registra la ruta real antes de continuar. Si falla la creación o el valor impreso está vacío, detente; no ejecutes los ejercicios de archivos.

**Misma VM y shell, usuario normal:**

```bash
cd -- "$LAB_DIR"
pwd
ls -la
```

Continúa solo si `pwd` coincide con el directorio que registraste. `cd` cambia desde dónde comienzan las rutas relativas; no mueve archivos. `--` termina el análisis de opciones. La lista inicial contiene `.` y `..`, y el nuevo directorio es privado para tu cuenta.

**Misma VM y shell, usuario normal, desde ese directorio:**

```bash
mkdir notes archive
touch notes/draft.txt notes/vi.txt
ls -l notes
cd notes
pwd
cd ..
pwd
```

`mkdir` crea directorios. `touch` crea los dos archivos vacíos porque todavía no existen; si el archivo ya existe, actualiza sus marcas de tiempo sin vaciar su contenido. Inicialmente, ambos archivos tienen tamaño `0`. El primer `pwd` termina en `/notes`; el segundo vuelve a la raíz del directorio temporal. Un `mkdir`, `touch` o `cd` correcto normalmente no imprime nada. El silencio es normal; inspecciona el resultado con `ls` o `pwd`.

## Editar, guardar, copiar y mover

**Misma VM de práctica, usuario normal, raíz temporal:**

```bash
nano notes/draft.txt
```

Escribe estas dos líneas **en el editor**, no en el shell. Son texto de ejemplo y se mantienen en inglés, tal como aparecen abajo:

```text
I am learning Linux networking.
This file belongs to my practice notebook.
```

En nano, `^O` en la barra de ayuda significa **Ctrl+O**, no los caracteres `^` y `O`. Pulsa Ctrl+O, comprueba el nombre del archivo y pulsa Enter para escribirlo. Pulsa Ctrl+X para salir. Para descartar los cambios desde el último guardado, pulsa Ctrl+X y elige `N` cuando pregunte si quieres guardar; los avisos localizados podrían mostrar otra tecla. Si eliges `Y`, los cambios se escriben tras confirmar el nombre del archivo.

**De vuelta en el shell, misma VM, usuario normal:**

```bash
cat notes/draft.txt
cp -i -- notes/draft.txt notes/copy.txt
mv -i -- notes/copy.txt archive/saved.txt
ls -l notes archive
```

`cat` debe mostrar lo que guardaste. `cp` copia el contenido a un segundo archivo; el original permanece. `mv` mueve o cambia de nombre un archivo: `notes/copy.txt` pasa a ser `archive/saved.txt`. En ambos comandos, `-i` pregunta antes de sobrescribir un destino existente; responde `n` si no esperabas encontrar uno. Espera `draft.txt` y `vi.txt` en `notes`, y `saved.txt` en `archive`. Esta copia guardada te permite recuperar el borrador si algo sale mal en una edición posterior.

Para recuperarlo, desde esta misma raíz temporal como usuario normal, `cp -i -- archive/saved.txt notes/draft.txt` reemplaza solo el borrador; confirma únicamente si tienes intención de descartar su contenido más reciente.

**Misma VM de práctica, usuario normal, raíz temporal:**

```bash
vi notes/vi.txt
```

En estos sistemas invitados, `vi` suele ejecutar una variante de Vim. Comienza en **modo normal**, donde las teclas son comandos. Pulsa `i` para entrar en modo de inserción, escribe `I can save and exit vi.` y luego pulsa Esc para volver al modo normal.

| Teclas después de Esc | Resultado |
| --- | --- |
| `:w` y luego Enter | Guarda y continúa editando |
| `:wq` y luego Enter | Guarda y sale de esta sesión con un único archivo |
| `:q` y luego Enter | Sale cuando no quedan cambios sin guardar |
| `:q!` y luego Enter | Descarta los cambios desde el último guardado y sale |

Practica `:wq`, vuelve a abrir el archivo, escribe una palabra adicional tras pulsar `i` y descarta esa edición extra con Esc, `:q!` y Enter. De vuelta al shell, `cat notes/vi.txt` debe mostrar solo la oración guardada. Los comandos con dos puntos se ejecutan **dentro de vi**, no en Bash. Un mensaje «No write since last change» de `:q` protege el trabajo sin guardar.

## Permisos y sudo

Cada archivo tiene propietario y grupo. Los conjuntos básicos de permisos se aplican, en este orden, al propietario, al grupo y a todos los demás. En la salida ilustrativa `-rw-r--r--`, el primer `-` indica un archivo normal; los siguientes tríos significan que el propietario puede leer/escribir, el grupo puede leer y los demás pueden leer. Un directorio comienza con `d`. Un `.` o `+` adicional puede indicar metadatos de seguridad o ACL; esos controles adicionales quedan fuera de este primer ejercicio.

En archivos, `r` permite leer el contenido, `w` modificarlo y `x` ejecutarlo. En directorios, `r` lista nombres, `x` permite recorrer/acceder y `w` junto con permiso de recorrido permite crear/eliminar entradas, sujeto a los otros controles. El permiso de escritura de un archivo por sí solo no determina si se puede eliminar su entrada del directorio.

**Misma VM de práctica, usuario normal, raíz temporal; cambia solo el borrador:**

```bash
ls -l notes/draft.txt
LAB_DRAFT_MODE=$(stat -c '%a' notes/draft.txt)
printf '%s\n' "$LAB_DRAFT_MODE"
chmod 600 notes/draft.txt
ls -l notes/draft.txt
```

`stat` registra el modo numérico original; conserva ese valor. En cada trío, lectura=4, escritura=2 y ejecución=1. Así, `600` concede al propietario `4+2`, al grupo `0` y a los demás `0`: espera `-rw-------`. El directorio temporal que lo contiene ya limita el acceso, así que esto es un ejercicio de interpretación, no una necesidad de crear un archivo realmente secreto.

**Deshaz el cambio ahora, misma VM y shell, usuario normal:**

```bash
chmod "$LAB_DRAFT_MODE" notes/draft.txt
stat -c '%a' notes/draft.txt
```

El número resultante debe coincidir con el modo que registraste. Restauramos el valor registrado en vez de dar por sentado que todos los sistemas usaban originalmente `644`. No necesitas `sudo` para cambiar el modo de un archivo que te pertenece.

`sudo` ejecuta un comando permitido como otro usuario, root de forma predeterminada. Normalmente solicita **la contraseña de tu cuenta**, aunque puede que no se muestre mientras la escribes. No es una solución general para «Permission denied».

**VM de práctica, usuario normal; muestra la identidad con una consulta elevada:**

```bash
sudo whoami
whoami
```

Espera `root` y luego tu nombre de usuario normal. Si no tienes autorización, detente y usa la cuenta preparada para el curso; no edites `sudoers` a ciegas. Si no puedes escribir en el cuaderno, comprueba primero `pwd`, `id` y `ls -ld` para el directorio pertinente. Evita cambios recursivos amplios de permisos: ocultan la causa y afectan a archivos ajenos al ejercicio.

## Programas, procesos, servicios y registros

Un **programa** es software almacenado en disco. Un **proceso** es una instancia en ejecución con un ID de proceso (PID), propietario y memoria. Instalar un programa no necesariamente lo inicia. Un **servicio** es trabajo administrado en segundo plano, a menudo por systemd; un servicio puede tener varios procesos.

**VM de práctica, usuario normal; solo inspección:**

```bash
ps -p $$ -o pid,ppid,user,comm
ps -p 1 -o pid,comm
```

`$$` se expande al PID de este shell Bash. `-p` selecciona un PID y `-o` selecciona las columnas mostradas. `PPID` es el ID del proceso padre; `COMM` es el nombre del comando. En estas VM ya arrancadas, espera ver tu shell en el primer resultado y systemd como PID 1. Los PID distintos de 1 varían. Si PID 1 no es systemd, vuelve al entorno completo de la VM antes de seguir con el ejercicio de servicios.

**VM de práctica, usuario normal; proceso acotado en primer plano:**

```bash
sleep 30
```

El prompt espera mientras se ejecuta `sleep`. Pulsa Ctrl+C para interrumpirlo y recuperar el prompt, o deja que termine tras 30 segundos. No hay archivos ni configuración de servicio que limpiar. Es una práctica más segura que terminar un proceso desconocido. `kill` envía una señal a un proceso concreto; usar un PID copiado de un documento puede afectar al trabajo de otra persona.

Systemd administra **unidades**, incluidas las unidades `.service`. El journal recopila mensajes de systemd y servicios. Empieza por el servicio de registro que usan ambas rutas del sistema invitado.

**VM de práctica, usuario normal; solo inspección:**

```bash
systemctl status systemd-journald.service --no-pager
systemctl is-active systemd-journald.service
systemctl is-enabled systemd-journald.service
```

En `status`, `Loaded` indica si se encontró la definición de la unidad; `Active` describe su estado actual; `Main PID` identifica su proceso principal cuando corresponda. El servicio del journal normalmente debe estar activo. `is-enabled` puede mostrar `static`: significa que no hay una sección de habilitación normal, **no** que el servicio esté roto. Las dependencias o la activación pueden iniciar unidades.

| Operación que debes reconocer | Qué cambia |
| --- | --- |
| `start` / `stop` | Estado de ejecución actual |
| `restart` | Ciclo de detener/iniciar; puede interrumpir a los usuarios |
| `enable` / `disable` | Enlaces de habilitación usados para la activación, a menudo durante el arranque; no inicia/detiene por sí solo |
| `enable --now` | Habilita y también inicia |
| `reload` | Pide a un servicio compatible que vuelva a leer su configuración |

Estos conceptos servirán para la administración posterior; **en este ejercicio no detengas ni reinicies los servicios de registro o de red**. Un servicio habilitado puede haber fallado y uno deshabilitado puede estar ejecutándose. Comprueba por separado el estado de ejecución y la habilitación.

**VM de práctica, usuario normal que invoca sudo para leer los registros del sistema:**

```bash
sudo journalctl -b -u systemd-journald.service -n 20 --no-pager
```

`-b` limita los resultados al arranque actual, `-u` selecciona una unidad y `-n 20` limita la salida a las últimas 20 entradas coincidentes. `--no-pager` vuelve directamente al shell. Lee juntos la marca de tiempo, la máquina, el proceso/unidad y el mensaje. Una entrada del journal es evidencia de un evento; no necesariamente es un error. Si no hay entradas, podría significar que no hay mensajes retenidos que coincidan con este filtro; sin permisos suficientes, también podrías ver menos contenido del journal. Compara con `status` antes de concluir que el servicio falló.

## Comprobación final y limpieza

Antes de eliminar el cuaderno, usa `cat` y `ls -l` desde su raíz para comprobar que:

1. `notes/draft.txt` y `archive/saved.txt` contienen las dos oraciones, y que `notes/copy.txt` no existe.
2. `notes/vi.txt` conserva la oración guardada, pero no la palabra adicional descartada.
3. El modo del borrador coincide con el valor original registrado y puedes explicar cada trío de permisos.
4. Puedes identificar la distribución del sistema invitado, el kernel en ejecución, la cuenta normal, el PID del shell y el estado activo de journald sin confundirlos.
5. Puedes explicar por qué actualizar el índice de paquetes, iniciar un servicio y habilitarlo son tres operaciones distintas.

Ahora elimina solo los archivos creados aquí. Si abriste otro shell, las variables **no** están presentes automáticamente: asigna a `LAB_DIR` la ruta exacta que registraste, inspecciona su contenido y luego continúa. Nunca adivines un sufijo ni selecciones todos los directorios con un comodín.

**VM de práctica, usuario normal, usando el `LAB_DIR` registrado:**

```bash
cd -- "$LAB_DIR"
pwd
ls -la notes archive
```

Después de confirmar que es tu directorio temporal:

```bash
rm -i -- notes/draft.txt notes/vi.txt archive/saved.txt
rmdir -- notes archive
cd -- "$HOME"
rmdir -- "$LAB_DIR"
```

`rm -i` pregunta por cada archivo indicado; confirma solo los archivos de práctica. `rmdir` elimina **directorios vacíos**. Si se niega, inspecciona los archivos restantes, incluidos archivos de intercambio/copia de seguridad del editor o un `copy.txt` sin terminar, y elimina únicamente los archivos de práctica identificados por nombre exacto. No cambies a una eliminación recursiva. Si un archivo ya no existe tras una limpieza parcial, no amplíes por ello el alcance de la eliminación.

**VM de práctica, usuario normal; verifica la limpieza:**

```bash
test ! -e "$LAB_DIR"
echo $?
unset LAB_DIR LAB_DRAFT_MODE
sudo -k
```

`test ! -e` comprueba que la ruta registrada ya no exista; `echo $?` debe imprimir `0`, lo que significa que la comprobación inmediatamente anterior tuvo éxito. `1` significa que todavía existe. `unset` elimina las variables de la lección; `sudo -k` invalida la autorización sudo almacenada en caché, para que un comando elevado posterior pueda volver a solicitarla. Solo se inspeccionó la configuración del sistema invitado; cualquier instalación opcional de editores permanece hasta que elijas la recuperación de snapshot descrita arriba.

## Referencias y lecturas adicionales

Se consultó la documentación principal del 14 al 15 de septiembre de 2026. Estas fuentes explican las herramientas usadas aquí; no son requisitos previos ni sustitutos de los ejercicios.

- [Debian: acerca de Debian](https://www.debian.org/intro/about): distribuciones, kernel, utilidades y paquetes.
- [Introducción a GNU C Library](https://www.gnu.org/software/libc/manual/html_node/Introduction.html): qué proporciona una biblioteca del sistema.
- [Referencia de Debian, tutoriales GNU/Linux](https://www.debian.org/doc/manuals/debian-reference/ch01.en.html): shell, sistemas de archivos, permisos y procesos.
- [Manual de GNU Coreutils](https://www.gnu.org/software/coreutils/manual/coreutils.html), en especial [mktemp](https://www.gnu.org/software/coreutils/manual/html_node/mktemp-invocation.html): operaciones de archivos y directorios temporales privados.
- [Atajos de GNU nano](https://www.nano-editor.org/dist/latest/cheatsheet.html) y [primeros pasos con Vim](https://vimhelp.org/usr_02.txt.html): modos del editor, escritura y salida.
- [Gestión de paquetes de Ubuntu Server](https://ubuntu.com/server/docs/how-to/software/package-management/) y [guía DNF de Rocky Linux 9](https://docs.rockylinux.org/9/guides/package_management/dnf_package_manager/): las dos rutas de paquetes.
- [Manual systemctl de systemd](https://www.freedesktop.org/software/systemd/man/systemctl.html) y [manual journalctl](https://www.freedesktop.org/software/systemd/man/journalctl.html): estado de ejecución, habilitación y filtros de registros.

Continúa con [Direcciones e interfaces](02-addressing-interfaces.md), después de comprobar que entendiste la lección con el [cuestionario](../../quizzes/networking/beginner/01-linux-cli-quiz.md).
