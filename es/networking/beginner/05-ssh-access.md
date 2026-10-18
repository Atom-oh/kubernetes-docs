# 5. Acceso remoto con SSH

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Anterior: DNS y conectividad](04-dns-connectivity.md) | [Curso](README.md) | [Cuestionario](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [Siguiente: Seguridad del host](06-firewalls-host-security.md)

SSH te proporciona una terminal cifrada en otra computadora. El cifrado por sí solo no basta: el cliente debe identificar al servidor y el servidor debe autenticar tu cuenta. Antes de cambiar la política de inicio de sesión, verificaremos por separado ambas identidades.

## Requisitos previos, resultados y límite de recuperación

Completa las lecciones 1–4. El cliente `192.0.2.10/24` y el servidor `192.0.2.20/24` usan sus interfaces internas, verificadas por MAC y de uso exclusivo del laboratorio, sin DHCP de laboratorio, gateway ni enlace de salida. Las interfaces independientes de NAT/DHCP para administración no se modifican. Usa cuentas normales y **mantén abierta la consola del hipervisor del servidor durante todo el ejercicio**. Necesitas sudo en el servidor, la contraseña normal de su cuenta o acceso a la consola para instalar una clave pública y la conexión de administración existente para descargar paquetes.

Crea instantáneas de ambas máquinas invitadas llamadas `before-ssh-lesson`. Registra los sockets SSH en escucha y el estado del servicio/socket antes de la instalación. Una instantánea permite revertir todos los cambios de paquetes/dependencias; eliminar un paquete no restaura exactamente el estado anterior. No reemplaces claves ni archivos de configuración existentes solo para que coincidan con el ejemplo.

## 1. Identificar el cliente y el servidor

El **cliente SSH** es el comando `ssh` que ejecutas para conectarte. El **servidor SSH** es `sshd`, que espera conexiones, normalmente en TCP 22. Una **clave de host** pertenece al servidor y demuestra su identidad. Una **clave de usuario** te pertenece y demuestra que tienes permiso para usar una cuenta. Una huella es una representación abreviada de una clave pública, adecuada para compararla mediante un canal de confianza.

**En ambas máquinas, como usuario normal; primero inspecciona:**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
command -v ssh
```

Compara las MAC de las NIC con los registros del hipervisor y confirma las direcciones asignadas a cada función. En el cliente, `ip -4 route get 192.0.2.20` debería seleccionar la NIC del laboratorio y tener `.10` como dirección de origen; consulta la lección 2 para interpretarlo.

**Servidor Ubuntu, usuario normal; registra el estado y luego instala solo si falta el paquete:**

```bash
dpkg-query -W openssh-server
systemctl status ssh.service ssh.socket --no-pager
```

Si no está instalado, ejecuta `sudo apt update` y luego `sudo apt install openssh-server`. Las instalaciones de Ubuntu 24.04 pueden activar sockets con `ssh.socket`; el nombre del servicio sigue siendo `ssh.service`. Inspecciona ambos en vez de desactivar el socket. Esta lección conserva las direcciones/puertos de escucha existentes, así que no hace falta cambiar la asociación del socket.

**Servidor Rocky, usuario normal; registra el estado y luego instala solo si falta el paquete:**

```bash
rpm -q openssh-server
systemctl status sshd.service --no-pager
```

Si no está instalado, ejecuta `sudo dnf install openssh-server`. En un cliente Ubuntu, las herramientas vienen en `openssh-client`; en un cliente Rocky, en `openssh-clients`. Si falta el paquete, instala el paquete indicado siguiendo el procedimiento del administrador de paquetes de la lección 1. Revisa las transacciones; no añadas repositorios para OpenSSH.

En el **servidor**, establece una variable de servicio después de comprobar la distribución:

```bash
# Ubuntu server only:
SSH_UNIT=ssh.service
```

```bash
# Rocky server only:
SSH_UNIT=sshd.service
```

**Servidor, usuario normal que invoca sudo donde se indica:**

```bash
sudo /usr/sbin/sshd -t
sudo systemctl start "$SSH_UNIT"
systemctl cat "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo ss -ltnp 'sport = :22'
```

`sshd -t` comprueba la configuración y la validez de las claves; normalmente no muestra nada cuando termina correctamente. No inicies ni recargues el servicio si la validación informa un error. `start` afecta el estado de ejecución actual, no si se habilita durante el arranque. `systemctl cat` muestra la unidad y sus overrides: este procedimiento presupone la ruta de configuración normal. Si opciones personalizadas de `ExecStart`/entorno proporcionan `-f` o `-o`, reproduce esas opciones durante la validación y las comprobaciones efectivas posteriores en vez de probar una configuración distinta. Un listener en `0.0.0.0:22`/`[::]:22` abarca más que la dirección del laboratorio; no restringe el origen. No cambies aquí las asociaciones de red, porque podrías perder el acceso de administración. La lección 6 limita el tráfico del laboratorio por origen e interfaz.

Si un firewall bloquea actualmente la conexión del laboratorio, completa **solo la rama correspondiente del firewall en la lección 6** para permitir TCP 22 de `.10` a `.20` y luego regresa aquí. Mantén el acceso a la consola; no desactives el firewall. «Connection refused» suele indicar que no hay un listener o que hubo un rechazo; un timeout puede indicar filtrado o un fallo de ruta. Sigue la secuencia de recopilación de evidencias de la lección 4.
## 2. Verificar la clave de host del servidor desde su consola

**Consola del hipervisor del servidor, usuario normal que invoca sudo:**

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Registra la huella completa `SHA256:...` y anota que es la **clave de host ED25519**. Esta ruta muestra la clave pública de host, no tu futura clave de usuario. Nunca muestres ni copies `/etc/ssh/ssh_host_ed25519_key`, que es su contraparte privada. Esta ruta presupone la configuración normal de una máquina invitada no FIPS; si la política criptográfica no permite Ed25519, necesitas una ruta con un algoritmo aprobado, no desactivar la política de seguridad.

**Cliente, usuario normal:**

```bash
SSH_LAB_DIR=$(mktemp -d "$HOME/network-beginner-ssh.XXXXXX")
printf '%s\n' "$SSH_LAB_DIR"
read -r -p 'Normal account name on the server: ' SERVER_USER
```

Registra el directorio y la cuenta; detente si falla la creación, la ruta está vacía o la cuenta es root. Este directorio privado contendrá una clave propia del curso y un registro de host, sin modificar los archivos `~/.ssh` existentes del cliente.

**Cliente, usuario normal:**

```bash
ssh -o HostKeyAlgorithms=ssh-ed25519 \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=ask \
  "$SERVER_USER@192.0.2.20"
```

Cuando aparezca el primer aviso sobre la clave de host, compara la **huella completa** con la de la consola del servidor. Solo si coincide exactamente debes escribir `yes`. Si es distinta, detente y comprueba la máquina virtual/dirección; no desactives la verificación de claves de host ni borres a ciegas un registro guardado. `ssh-keyscan` puede recopilar una clave, pero por sí solo no demuestra quién la proporcionó.

Si se permite iniciar sesión con contraseña, introduce la **contraseña de la cuenta del servidor** y comprueba remotamente `hostname`, `whoami` y `printf '%s\n' "$SSH_CONNECTION"`; después ejecuta `exit` para volver al cliente. `SSH_CONNECTION` contiene la IP/puerto del cliente y la IP/puerto del servidor; deberían ser `.10` y `.20` del laboratorio. Mantén disponible la consola independiente del hipervisor. Si ya está deshabilitado el acceso por contraseña, la verificación de la clave de host puede completarse antes de que falle la autenticación; usa la alternativa de instalación mediante consola que sigue, sin habilitar contraseñas.

## 3. Crear tu clave de usuario y preparar los permisos del servidor

**Cliente, usuario normal, en la misma shell:**

```bash
ssh-keygen -t ed25519 -a 64 -f "$SSH_LAB_DIR/id_ed25519" \
  -C "network-beginner-$(basename "$SSH_LAB_DIR")"
ssh-keygen -lf "$SSH_LAB_DIR/id_ed25519.pub"
ls -l "$SSH_LAB_DIR"
```

Introduce dos veces una frase de contraseña no vacía. Esta cifra la clave privada en el disco; no es la contraseña de la cuenta del servidor. `-a 64` selecciona el factor de trabajo de derivación de claves. `id_ed25519` permanece en el cliente; solo se envía `id_ed25519.pub` al servidor. El directorio único evita reemplazar accidentalmente una clave existente. Si aparece inesperadamente un aviso de sobrescritura, detente en vez de responder que sí.

Antes de instalarla, prepara un registro de recuperación para la **misma cuenta normal del servidor** indicada en `SERVER_USER`.

**Consola del servidor, con sesión iniciada como esa cuenta normal:**

```bash
SERVER_NOTE=$(mktemp -d "$HOME/network-beginner-ssh-state.XXXXXX")
printf '%s\n' "$SERVER_NOTE"
stat -c '%a %U %n' "$HOME"
ls -ld "$HOME/.ssh" "$HOME/.ssh/authorized_keys"
```

Detente si falla la creación del directorio o la ruta mostrada está vacía. Registra la nueva ruta y los permisos originales del directorio personal. En una cuenta nueva, es normal que no exista `.ssh` o `authorized_keys`; registra cuál faltaba. Si existen, registra sus permisos numéricos con `stat -c '%a %U %n'` e inspecciona la propiedad. Si alguno es un enlace simbólico, pertenece a otra persona, tiene ACL inesperadas o lo administra otro sistema, detente y resuelve la propiedad en lugar de cambiarla recursivamente.

Si ya existe `authorized_keys`, ejecuta como **usuario normal del servidor**: `cp -p -- "$HOME/.ssh/authorized_keys" "$SERVER_NOTE/authorized_keys.before"` para hacer una copia de seguridad en el directorio nuevo. Registra también los permisos de `.ssh` antes de cambiarlos. Crea `.ssh` solo si falta, con `mkdir -m 700 -- "$HOME/.ssh"`. Para esta cuenta, usa `chmod go-w "$HOME"` y `chmod 700 "$HOME/.ssh"`; registra los permisos originales para poder restaurarlos. Las comprobaciones estrictas de OpenSSH rechazan propiedad insegura o rutas con permisos de escritura para grupo/todos. No uses `chmod` recursivo ni muevas claves de otra persona.

## 4. Instalar la clave pública y demostrar acceso solo con clave

**Cliente, usuario normal:**

```bash
ssh-copy-id -i "$SSH_LAB_DIR/id_ed25519.pub" \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes \
  "$SERVER_USER@192.0.2.20"
```

`ssh-copy-id` usa un método de autenticación existente para añadir la clave pública seleccionada a `~/.ssh/authorized_keys` de la cuenta del servidor; no copia la clave privada. Revisa el número de claves añadidas. Debería añadir tu única clave o indicar que ya está instalada. No uses un modo forzado para añadir duplicados.

**Alternativa mediante consola si no se puede usar contraseña/SSH para el arranque:** en el cliente, muestra solo `cat "$SSH_LAB_DIR/id_ed25519.pub"`. En la consola del servidor, como usuario destino, abre `nano "$HOME/.ssh/authorized_keys"` y **añade al final la línea pública completa**, conservando las líneas existentes. Guarda y compara `ssh-keygen -lf "$HOME/.ssh/authorized_keys"` con la huella de la clave de usuario del cliente. No es la huella de la clave de host del paso 2.

**Consola del servidor, usuario normal de destino:**

```bash
chmod 600 "$HOME/.ssh/authorized_keys"
ls -ld "$HOME" "$HOME/.ssh"
ls -l "$HOME/.ssh/authorized_keys"
ssh-keygen -lf "$HOME/.ssh/authorized_keys"
```

El propietario debería ser la cuenta destino; comprueba los permisos privados de `.ssh` y que la huella de la nueva clave pública aparezca junto a las entradas existentes. En Rocky con SELinux enforcing, también ejecuta `sudo restorecon -v "$HOME/.ssh" "$HOME/.ssh/authorized_keys"` si las etiquetas de las rutas normales del directorio personal son incorrectas; la lección 6 explica por qué los permisos Unix no constituyen toda la política.

**Consola A del cliente, usuario normal; abre y mantén esta sesión:**

```bash
ssh -i "$SSH_LAB_DIR/id_ed25519" -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no \
  -o ControlMaster=no -o ControlPath=none \
  -o UserKnownHostsFile="$SSH_LAB_DIR/known_hosts" \
  -o StrictHostKeyChecking=yes "$SERVER_USER@192.0.2.20"
```

Es normal que se solicite la frase de contraseña de la clave privada. En esta prueba de acceso solo con clave no debe pedirse la contraseña de la cuenta remota. `IdentitiesOnly` limita las claves ofrecidas, y desactivar la reutilización de conexiones garantiza que pruebes una autenticación nueva en vez de reutilizar una sesión multiplexada.

En esa **sesión remota del servidor**, ejecuta `whoami` y `printf '%s\n' "$SSH_CONNECTION"` y déjala abierta. Ahora abre la **consola B del cliente**, asigna a `SSH_LAB_DIR` la ruta exacta del directorio de cliente registrado y a `SERVER_USER` la misma cuenta, y repite el **comando completo de acceso solo con clave** anterior. Vuelve a confirmar la cuenta y la conexión `.10`→`.20`. Esta condición solo se cumple si la segunda sesión independiente se inicia correctamente.

Si ya usas SSH a través de la **NIC de administración**, repite la prueba de acceso solo con clave para cada cuenta/ruta de administración que deba seguir funcionando antes de deshabilitar globalmente la autenticación por contraseña del servidor. Mantener una sesión abierta no basta. Si no puedes verificar una ruta necesaria, conserva la política de autenticación actual y termina la preparación; que la IP de la NIC no haya cambiado no garantiza que el acceso siga funcionando.
## 5. Inspeccionar la precedencia de la configuración antes de reforzarla

**Consola del servidor, usuario normal que invoca sudo:**

```bash
sudo cat /etc/ssh/sshd_config
sudo ls -la /etc/ssh/sshd_config.d
sudo grep -RnsE '^[[:space:]]*(Include|Match|PasswordAuthentication|KbdInteractiveAuthentication|PermitRootLogin|PubkeyAuthentication|AuthenticationMethods|AuthorizedKeysFile)' \
  /etc/ssh/sshd_config /etc/ssh/sshd_config.d
```

Lee los archivos incluidos reales, incluidas otras rutas indicadas por `Include`; `grep` ayuda, pero no es un analizador completo. Normalmente, OpenSSH usa **el primer valor obtenido** para cada palabra clave. Los archivos incluidos se procesan donde aparecen y los nombres de archivo coincidentes con glob se ordenan lexicográficamente. Un bloque `Match` coincidente puede anular los valores globales para esa conexión; entre las asignaciones `Match` aplicables, el orden también vuelve a importar. Un archivo `99-...conf` agregado al final no constituye una anulación fiable.

Este ejercicio usa un **archivo drop-in nuevo y solo global**, por lo que requiere un `Include` activo de `/etc/ssh/sshd_config.d/*.conf` en la parte global del archivo principal. Comprueba que ninguna asignación anterior lo anule. No pongas bloques `Match` en el drop-in del curso ni edites archivos incluidos ajenos para forzar la precedencia. Si la disposición instalada no permite usar el archivo nuevo como se espera, detén el endurecimiento e investiga quién administra la configuración y su estructura, pero conserva el acceso que funciona.

**Consola del servidor; vuelve a establecer la cuenta destino en esta shell:**

```bash
read -r -p 'Normal SSH account on this server: ' SERVER_USER
SSH_CASE="user=$SERVER_USER,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22"
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
```

`-T` imprime la configuración efectiva; `-C` especifica una conexión hipotética para evaluar las reglas `Match`. `host` describe el equipo cliente para las coincidencias de hostname, no el hostname del servidor. Este curso no depende de reglas `Match` basadas en hostname; si tu configuración sí depende de ellas, usa el nombre real que evalúa sshd. Comprueba `pubkeyauthentication`, `passwordauthentication`, `kbdinteractiveauthentication`, `permitrootlogin`, `authenticationmethods` y `authorizedkeysfile`. Una configuración válida aún puede rechazar tu cuenta por `AllowUsers`, `DenyUsers`, restricciones de grupos, PAM o el estado de la cuenta.

Guarda la configuración efectiva de referencia antes de añadir nada:

```bash
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.before"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.before"
```

Registra una referencia equivalente para cualquier ruta SSH de administración existente, usando sus direcciones de origen/locales y cuentas reales. No sustituyas un endpoint de administración real por una dirección de ejemplo.

## 6. Añadir un único archivo de política propio, validarlo, recargarlo y volver a probar

Continúa solo después de que funcionen la segunda sesión de acceso solo con clave y las pruebas requeridas de las rutas de administración. Estos ajustes cambian la **autenticación para todo el servidor**, sujetos a las reglas `Match` efectivas; no cambian la configuración de las NIC.

**Consola del servidor, usuario normal que invoca sudo; creación exclusiva:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/ssh/sshd_config.d/00-network-beginner.conf'
sudoedit /etc/ssh/sshd_config.d/00-network-beginner.conf
```

`set -C` impide sobrescribir un archivo existente. Si falla, detente: no edites ni borres un intento anterior sin tener su registro de recuperación. Escribe solo este **texto de configuración** en el archivo que acabas de crear:

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

`PasswordAuthentication no` por sí solo no deshabilita la autenticación PAM/keyboard-interactive similar a contraseña. Mantener el acceso del usuario normal por clave y luego usar sudo evita el acceso SSH directo como root. No deshabilites PAM globalmente.

**Consola del servidor, usuario normal que invoca sudo:**

```bash
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22'
```

Continúa solo si la sintaxis es válida y las conexiones previstas muestran `pubkeyauthentication yes`, `no` para las opciones de contraseña y keyboard-interactive, y `permitrootlogin no`. Repite las comprobaciones efectivas para las rutas de administración necesarias. Si gana una asignación anterior o una regla `Match`, **no recargues el servicio**: elimina solo el archivo nuevo, valida que se restauró la configuración, e investiga la precedencia. Cambiar nombres de archivo al azar no lo soluciona.

**Consola del servidor, usuario normal que invoca sudo:**

```bash
sudo systemctl reload "$SSH_UNIT"
systemctl status "$SSH_UNIT" --no-pager
sudo journalctl -u "$SSH_UNIT" -b -n 30 --no-pager
```

La recarga pide al daemon en ejecución que vuelva a leer su configuración. No recarga el firewall ni cambia las asociaciones de sockets. Mantén abiertas la consola y las sesiones originales; luego inicia **otra sesión nueva del cliente, usando solo la clave**, según el paso 4 y vuelve a comprobar las rutas SSH de administración. Que siga existiendo una sesión autenticada anterior no demuestra que funcionen los nuevos inicios de sesión.

## Finalización y recuperación exacta

El ejercicio se completa al verificar la huella de host, la clave de usuario dedicada protegida por frase de contraseña, la propiedad/permisos correctos, una segunda conexión nueva antes del endurecimiento, los resultados previstos de `-T -C` para las cuentas/rutas relevantes y una conexión nueva que funcione **después** de la recarga. Explica por qué un fallo de autenticación es distinto de un rechazo de conexión TCP.

Practica la reversión de la política desde la **consola del servidor**:

```bash
sudo rm -i -- /etc/ssh/sshd_config.d/00-network-beginner.conf
sudo /usr/sbin/sshd -t
sudo /usr/sbin/sshd -T -C "$SSH_CASE" > "$SERVER_NOTE/effective.restored"
diff -u "$SERVER_NOTE/effective.before" "$SERVER_NOTE/effective.restored"
sudo /usr/sbin/sshd -T -C \
  'user=root,addr=192.0.2.10,host=net-client,laddr=192.0.2.20,lport=22' \
  > "$SERVER_NOTE/root-effective.restored"
diff -u "$SERVER_NOTE/root-effective.before" "$SERVER_NOTE/root-effective.restored"
```

Confirma que se elimine únicamente el archivo que creaste. Que no se produzcan diferencias significa que la configuración efectiva de la cuenta normal coincide con la referencia; comprueba también los casos de root y de administración registrados. Si mientras tanto otros administradores o sistemas de configuración cambiaron el estado, investiga la diferencia en vez de restaurar un directorio antiguo completo. Recarga `$SSH_UNIT` **solo después** de que la sintaxis y los valores restaurados previstos sean válidos; luego verifica un inicio de sesión nuevo. Si tras el endurecimiento fallaron los nuevos inicios de sesión, este mismo procedimiento desde la consola es la vía de recuperación.

Si quieres conservar la configuración endurecida del curso, puedes volver a aplicar el drop-in propio con las mismas puertas de validación. De lo contrario, termina la limpieza en este orden:

1. **Cuenta destino del servidor:** abre `~/.ssh/authorized_keys` en nano y elimina solo la línea de clave indicada por el comentario del curso y la huella de clave de usuario registrada. Conserva todas las claves ajenas. Compárala con `"$SERVER_NOTE/authorized_keys.before"` si existía. Restaura sus permisos numéricos registrados. Si originalmente no existía y ahora está vacía, elimina solo este archivo vacío; elimina `.ssh` con `rmdir` únicamente si la creaste y está vacía. Restaura los permisos registrados del directorio personal/`.ssh` en las rutas que existían originalmente. En una cuenta compartida, reconcilia los cambios concurrentes en vez de sobrescribirlos con la copia de seguridad.
2. **Cliente:** después de cerrar las sesiones del curso y revocar la clave pública, elimina solo `id_ed25519`, `id_ed25519.pub` y `known_hosts` dentro de la ruta `SSH_LAB_DIR` registrada con `rm -i`; luego ejecuta `rmdir "$SSH_LAB_DIR"`. Si existe un archivo adicional, inspecciona su nombre exacto; no uses eliminación recursiva. Nunca se reemplazaron los archivos SSH existentes del cliente.
3. **Servidor:** después de verificarlo, elimina los archivos de referencia/copia de seguridad creados exactamente por la lección dentro de `SERVER_NOTE`; luego elimina ese directorio vacío. Registra los nombres de los archivos de referencia de administración que hayas creado, para limpiar solo esos archivos.
4. Restaura el estado **registrado** de ejecución del servicio/socket solo si lo cambiaste y ninguna lección posterior necesita SSH. Si la activación por socket de Ubuntu ya estaba activa, conserva ese socket; no lo deshabilites solo porque al principio el servicio estuviera inactivo. Si instalaste paquetes nuevos, puedes conservarlos para las lecciones posteriores; revertir los paquetes por completo requiere usar las instantáneas, lo que también descarta los cambios posteriores hechos en las máquinas invitadas.

## Referencias principales

Comprobadas el 15 de septiembre de 2026:

- [OpenSSH en Ubuntu Server](https://documentation.ubuntu.com/server/how-to/security/openssh-server/): instalación, `ssh.service` y precedencia de archivos incluidos.
- [Notas de la versión de Ubuntu 24.04](https://discourse.ubuntu.com/t/noble-numbat-release-notes/39890): activación de sockets de OpenSSH y generador de configuración de sockets.
- [Configuración de claves OpenSSH en Rocky Linux](https://docs.rockylinux.org/9/guides/security/ssh_public_private_keys/): flujo de OpenSSH en Rocky.
- [`ssh` de OpenSSH](https://man.openbsd.org/ssh), [`ssh-keygen`](https://man.openbsd.org/ssh-keygen), [`sshd`](https://man.openbsd.org/sshd) y [`sshd_config`](https://man.openbsd.org/sshd_config): identidad, claves, validación, Include/Match y configuración efectiva.
- [`ssh-copy-id` de Ubuntu 24.04](https://manpages.ubuntu.com/manpages/noble/man1/ssh-copy-id.1.html): instalación de la clave seleccionada y gestión de claves existentes.

[Cuestionario](../../quizzes/networking/beginner/05-ssh-access-quiz.md) | [Continuar a Seguridad del host](06-firewalls-host-security.md)
