# 6. Firewalls, SELinux y protección SSH acotada

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

[Anterior: SSH](05-ssh-access.md) | [Curso](README.md) | [Cuestionario](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [Siguiente: supervisión](07-monitoring-performance.md)

Una aplicación puede estar escuchando mientras un firewall rechaza la conexión, o puede aceptar una conexión pero no tener permiso para leer un archivo. Esta lección separa la política de red, la política de procesos/archivos y las reacciones ante fallos repetidos de autenticación.

## Requisitos previos y objetivos

Usa los dos sistemas invitados desechables con acceso a consola de las lecciones 1–5: cliente `192.0.2.10/24`, servidor `192.0.2.20/24`, NIC de laboratorio solo internas sin DHCP/enlace ascendente y NIC de administración NAT/DHCP separadas y sin cambios. Si la lección 5 te envió aquí porque está bloqueado TCP 22, completa únicamente la rama de firewall seleccionada y vuelve allí; esa rama no requiere el endurecimiento SSH completo.

Permitirás que el cliente IPv4 previsto se conecte al servidor por los puertos TCP **22 y 8000**, inspeccionarás qué política se aplica de verdad, distinguirás reglas guardadas/de ejecución, restaurarás solo tus cambios, repararás una etiqueta SELinux deliberadamente incorrecta en un archivo temporal y, de manera opcional, configurarás una jaula Fail2ban con límites. Usa la consola del servidor para los cambios y el cliente para las pruebas de conexión. Todos los ejemplos de comandos/salida son ilustrativos, **no son resultados probados en vivo en una VM**.

Crea una instantánea del servidor `before-host-security`. Registra el estado actual del firewall y de ejecución, así como cualquier ruta SSH de administración. Elige **UFW en la ruta de Ubuntu O firewalld en la ruta de Rocky**, según el propietario existente. No instales/actives un administrador en conflicto, vacíes reglas ni desactives servicios de seguridad para superar una prueba. Esta política de laboratorio es IPv4; no constituye una política completa para listeners IPv6 ni una lista de comprobación de endurecimiento de producción.

## 1. Entiende la dirección e identifica quién administra la política

**Entrante** significa tráfico dirigido a este servidor, por ejemplo una conexión SSH nueva. **Saliente** es tráfico generado por este servidor, incluidas sus solicitudes a repositorios de paquetes. El tráfico **reenviado** atraviesa el servidor hacia otro host. Nuestro servidor no es un router: no hace falta cambiar reenvío, NAT ni rutas predeterminadas.

Los firewalls con estado siguen las conversaciones y suelen permitir respuestas a conexiones establecidas. Por eso, una sesión SSH antigua que sigue funcionando no demuestra que se permitan sesiones entrantes nuevas. Una regla de firewall que permite tráfico tampoco crea un programa en escucha.

**Servidor, usuario normal; solo inspección:**

```bash
hostname
cat /etc/os-release
ip -br link
ip -4 -br address
ip -4 route
systemctl is-active ufw firewalld
```

La ausencia/inactividad de una unidad puede producir un estado de salida distinto de cero sin ser un fallo. En UFW, su propio `status` indica si la aplicación de reglas está activa; la unidad de systemd por sí sola no basta. Si hay Docker, Kubernetes, reglas nftables/iptables personalizadas u otro administrador de políticas, usa una VM limpia del curso en vez de suponer que esta política simplificada administra toda la máquina.

**Servidor, usuario normal; introduce nombres solo después de compararlos con las MAC del hipervisor:**

```bash
read -r -p 'Server lab NIC verified by MAC: ' LAB_IF
read -r -p 'Server management NIC verified by MAC: ' MGMT_IF
ip -br link show dev "$LAB_IF"
ip -br link show dev "$MGMT_IF"
FW_NOTE=$(mktemp -d "$HOME/network-beginner-firewall.XXXXXX")
printf '%s\n' "$FW_NOTE"
```

Detente si no se creó el directorio, si los nombres están vacíos/son iguales o si las MAC no coinciden. Registra estos valores fuera del shell. Confirma que `.20/24` pertenece a `LAB_IF` y luego guarda una referencia de administración:

```bash
ip -4 -br address show dev "$MGMT_IF" > "$FW_NOTE/management.before"
ip -4 route > "$FW_NOTE/routes.before"
```

## 2A. Ubuntu: UFW

Usa esta rama solo para el sistema invitado administrado por UFW. Si falta `ufw`, instálalo durante la preparación de paquetes del sistema invitado. Registra si estaba activo o inactivo.

**Servidor Ubuntu, usuario normal que ejecuta sudo:**

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ufw show added
sudo ufw show raw
sudo cat /etc/default/ufw
sudo ufw show added > "$FW_NOTE/ufw-added.before"
```

Inspecciona los archivos locales `/etc/ufw/before.rules`, `after.rules` y los archivos IPv6 correspondientes. Una aceptación personalizada anterior puede saltarse la restricción de reglas de usuario que se muestra abajo. Continúa únicamente con las reglas estándar entendidas y sin políticas personalizadas en conflicto. Una regla general `allow 22/tcp` permite más orígenes que nuestro objetivo; añadir solo un permiso acotado no revoca ese permiso más amplio.

Si UFW está **inactivo**, esta primera activación requiere la política predeterminada prevista de denegar entrada/permitir salida, el manejo estándar de DHCP/respuestas y que **no haya servicios entrantes de administración existentes que dependan de un firewall abierto**. La consola más la conexión de administración saliente NAT/DHCP cumplen esas condiciones. Si los servicios SSH/entrantes de administración existentes deben seguir accesibles, conserva la política acotada ya aprobada antes de activarlo; no inventes un permiso de administración amplio ni supongas que la prueba de consola verifica SSH. Si las condiciones no están claras, deja UFW inactivo mientras se resuelve la política.

Añade permisos independientes desde el cliente para SSH y HTTP, seguidos de una denegación para los mismos endpoints de laboratorio. El orden es **permiso SSH, permiso HTTP, denegación de laboratorio**, delante de las reglas de usuario generales. Las tres se dirigen solo a la NIC de laboratorio. Los permisos separados permiten que el [ejercicio final de firewall](08-container-cloud-capstone.md#firewall-fault) quite el permiso HTTP sin quitar el de SSH.

**Servidor Ubuntu, usuario normal que ejecuta sudo:**

```bash
sudo ufw insert 1 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22 comment 'network-beginner-ssh'
sudo ufw insert 2 allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000 comment 'network-beginner-http'
sudo ufw insert 3 deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000 comment 'network-beginner-other'
sudo ufw show added
```

Si falla algún comando, detente y usa la eliminación exacta de abajo para las reglas que sí se añadieron. No dupliques una regla idéntica ya existente: registra si era anterior a este ejercicio y déjala bajo el control de su configuración original.

Si UFW estaba inactivo y se cumplieron las condiciones de activación, ejecuta **desde la consola del servidor** `sudo ufw enable`; lee la advertencia en vez de usar `--force`. Si ya estaba activo, los cambios de reglas se aplican de inmediato.

**Servidor Ubuntu, usuario normal que ejecuta sudo:**

```bash
sudo ufw status numbered
sudo ufw status verbose
sudo ufw reload
sudo ufw status numbered
```

Comprueba que los dos permisos específicos por origen precedan a la denegación para la misma interfaz/destino, en el orden indicado, y que se conserven después de recargar. Las reglas UFW que se añaden de esta forma se guardan y aplican; en este flujo no tiene la división entre reglas de ejecución y `--permanent` de firewalld ni un timeout por regla. Un número de regla solo indica su posición actual en la lista, así que después la limpieza usa la especificación original.

Realiza las pruebas compartidas de abajo. Para **deshacer solo estas reglas**, desde la consola del servidor Ubuntu:

```bash
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 22
sudo ufw delete allow in on "$LAB_IF" proto tcp \
  from 192.0.2.10 to 192.0.2.20 port 8000
sudo ufw delete deny in on "$LAB_IF" proto tcp \
  from any to 192.0.2.20 port 22,8000
sudo ufw show added
```

Estas son las tres operaciones inversas para la **limpieza completa de la lección**, no tres comandos para ejecutar si solo hay un problema con HTTP. Confirma que solo sean tus reglas. Si activaste UFW, que originalmente estaba inactivo, únicamente para este ejercicio y quieres restaurar su estado base, ejecuta `sudo ufw disable` **después** de eliminar las reglas guardadas. No desactives un firewall que ya estaba activo. Compara con `ufw-added.before`. Para conservar la política del curso durante las lecciones 7–8, vuelve a aplicar las tres reglas en su orden original y verifícalas en vez de dejarlas eliminadas.

## 2B. Rocky: firewalld y una zona dedicada para el laboratorio

Usa esta rama solo cuando firewalld sea el propietario activo existente. Una **zona** agrupa políticas para las interfaces/orígenes asociados. Si la conexión de NetworkManager no especifica una zona, usa la zona predeterminada de firewalld, que quizá ya permita SSH de forma amplia. Añadir un permiso acotado a esa zona no restringiría los permisos existentes.

**Servidor Rocky, usuario normal que ejecuta sudo para inspeccionar el firewall:**

```bash
sudo firewall-cmd --state
sudo firewall-cmd --get-default-zone
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all-zones
sudo firewall-cmd --permanent --list-all-zones
sudo firewall-cmd --list-all-policies
sudo firewall-cmd --permanent --list-all-policies
sudo firewall-cmd --direct --get-all-rules
sudo firewall-cmd --list-all-zones > "$FW_NOTE/firewalld-runtime.before"
sudo firewall-cmd --permanent --list-all-zones > "$FW_NOTE/firewalld-permanent.before"
nmcli -f NAME,UUID,TYPE,DEVICE connection show --active
```

Registra las zonas efectivas de ambas NIC y la zona predeterminada. Inspecciona las asociaciones de origen, políticas, reglas rich y reglas direct personalizadas (la consulta direct sirve para inspeccionar el estado heredado; no recomienda crearlas). Pueden cambiar la clasificación o aceptación más allá de lo que sugiere la zona de la interfaz. Este procedimiento para una VM nueva requiere que no haya asociaciones de origen/políticas en conflicto ni cambios de ejecución ajenos que se perderían con una recarga. No uses `--runtime-to-permanent` para guardar cambios desconocidos.

Busca el UUID del perfil activo de NetworkManager **solo de laboratorio** de la lección 3. Nunca elijas el perfil de administración ni uno compartido.

**Servidor Rocky, usuario normal:**

```bash
read -r -p 'Active lab-only connection UUID: ' LAB_UUID
nmcli connection show uuid "$LAB_UUID"
LAB_OLD_ZONE=$(nmcli -g connection.zone connection show uuid "$LAB_UUID")
printf '%s\n' "$LAB_OLD_ZONE" > "$FW_NOTE/lab-zone.before"
```

Verifica la NIC/MAC del perfil y `.20/24`. Es válido que la zona anterior esté vacía; registra ese valor exacto. Comprueba en los inventarios de zonas de ejecución y permanentes si existe `network-beginner`. Si ya existe, detente en vez de reutilizarla o borrar la zona de otra persona.

**Servidor Rocky, usuario normal que ejecuta sudo:**

```bash
sudo firewall-cmd --permanent --new-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

Una zona nueva debe definirse como permanente y cargarse antes de que este flujo pueda usarla en ejecución. La recarga sustituye la política de ejecución por la permanente; por eso hay que resolver antes los cambios de ejecución ajenos. Todavía no se ha movido ninguna interfaz.

Establece dos cadenas exactas de reglas rich. Seleccionan IPv4, el origen, el destino y el puerto TCP; la asociación de la zona con `LAB_IF` proporciona el límite de interfaz.

**Servidor Rocky, usuario normal:**

```bash
RULE22='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="22" protocol="tcp" accept'
RULE8000='rule family="ipv4" source address="192.0.2.10/32" destination address="192.0.2.20/32" port port="8000" protocol="tcp" accept'
```

**Servidor Rocky, usuario normal que ejecuta sudo; prueba de ejecución de diez minutos:**

```bash
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE22" --timeout=600
sudo firewall-cmd --zone=network-beginner --add-rich-rule="$RULE8000" --timeout=600
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone network-beginner
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
sudo firewall-cmd --zone=network-beginner --list-all
sudo firewall-cmd --permanent --zone=network-beginner --list-all
```

El cambio de `connection.zone` de NetworkManager tiene efecto inmediato en una conexión activa. Solo cambia la zona de firewall del perfil seleccionado, no su IP/DHCP/gateway. Comprueba que `LAB_IF` esté en la nueva zona vacía con solo estas dos reglas rich de aceptación y que la NIC de administración permanezca en su zona original. La nueva zona no tiene el servicio general `ssh` ni un destino trusted/ACCEPT. Su comportamiento predeterminado rechaza conexiones TCP nuevas no aceptadas, mientras que otros protocolos, como ICMP, tienen una política aparte.

Solo las reglas de ejecución deben contener la prueba. Vencen después de 600 segundos y también se pierden con una recarga. Esto no elimina la asociación zona/perfil: sigue siendo esencial tener recuperación por consola. No combines `--timeout` con `--permanent`. Ejecuta las pruebas compartidas durante la prueba temporal.

Para conservar la política, **servidor Rocky, usuario normal que ejecuta sudo**:

```bash
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --add-rich-rule="$RULE8000"
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
sudo firewall-cmd --zone=network-beginner --list-rich-rules
sudo firewall-cmd --permanent --zone=network-beginner --list-rich-rules
```

Continúa solo si entretanto no se introdujeron cambios de ejecución ajenos. Espera las mismas cadenas de reglas guardadas y de ejecución después de la recarga; vuelve a probar una conexión SSH/HTTP **nueva**.

Para **restaurar**, primero termina/detén la jaula Fail2ban opcional de abajo, porque puede añadir reglas a esta zona. Luego, desde la consola del servidor Rocky, restaura la zona registrada del perfil (incluido un valor vacío):

```bash
sudo nmcli connection modify uuid "$LAB_UUID" connection.zone "$LAB_OLD_ZONE"
sudo firewall-cmd --get-zone-of-interface="$LAB_IF"
sudo firewall-cmd --get-zone-of-interface="$MGMT_IF"
```

Inspecciona cuáles de tus adiciones satisfactorias siguen presentes. **Consola del servidor Rocky, sudo:**

```bash
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --query-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --query-rich-rule="$RULE8000"
```

`yes` significa presente; `no` y un estado de salida distinto de cero significan ausente, como después de que venza la prueba temporal. Ejecuta **solo la eliminación que corresponda para cada regla presente que hayas añadido**:

```bash
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --zone=network-beginner --remove-rich-rule="$RULE8000"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE22"
sudo firewall-cmd --permanent --zone=network-beginner --remove-rich-rule="$RULE8000"
```

Por último:

```bash
sudo firewall-cmd --permanent --delete-zone=network-beginner
sudo firewall-cmd --check-config
sudo firewall-cmd --reload
```

Elimina únicamente tu zona ahora sin usar y recarga solo si el estado de ejecución ajeno es seguro. Compara la zona original del perfil, la zona predeterminada, la zona/dirección de administración y las políticas base. Si continúas con las lecciones 7–8, deja en su lugar la zona guardada del laboratorio después de verificarla; tras una reversión, repite las mismas pruebas temporales y pasos de validación.

## 3. Verifica desde el cliente y limita el alcance de la evidencia

Usa desde el cliente una **conexión SSH nueva solo con clave** como en la lección 5. Las sesiones establecidas que continúan abiertas no prueban reglas nuevas. Para TCP 8000, asegúrate de que `python3` esté disponible de la lección HTTP anterior y confirma que ningún otro servicio use el puerto.

**Consola A del servidor, usuario normal:**

```bash
WEB_DIR=$(mktemp -d "$HOME/network-beginner-fw-web.XXXXXX")
printf '%s\n' "$WEB_DIR"
```

Registra la ruta; detente si está vacía o falló. Luego:

```bash
printf 'firewall lesson\n' > "$WEB_DIR/index.html"
timeout 120 python3 -m http.server 8000 --bind 192.0.2.20 --directory "$WEB_DIR"
```

Esto sirve solo el directorio temporal, enlazado a la dirección IPv4 del laboratorio, durante dos minutos como máximo. No pongas secretos ni enlaces simbólicos allí. En la **consola B del servidor**, `sudo ss -ltnp 'sport = :8000'` debería mostrar `.20:8000`.

**Cliente, usuario normal:**

```bash
curl --disable --noproxy '*' --connect-timeout 2 --max-time 5 \
  -i http://192.0.2.20:8000/
```

Se espera HTTP 200 y `firewall lesson` en el cuerpo. Una prueba fallida no justifica un permiso amplio: comprueba listener, ruta, zona/interfaz, origen y registros, en ese orden. Inspecciona la configuración para confirmar la restricción de origen prevista; el éxito desde el cliente permitido **no comprueba el rechazo desde todos los demás orígenes**. Una prueba en localhost/desde el propio servidor no es una prueba de rechazo desde un cliente externo.

Después de que venza el servidor (el código 124 es normal) o lo interrumpas con Ctrl+C, en la **consola A del servidor, usuario normal**: ejecuta `rm -i -- "$WEB_DIR/index.html"` y luego `rmdir -- "$WEB_DIR"`. Comprueba las direcciones/rutas de administración frente a `FW_NOTE`, además de cualquier inicio de sesión SSH nuevo necesario. Las renovaciones DHCP pueden cambiar el tiempo de concesión por separado.

## 4. SELinux en Rocky: corrige una etiqueta, no toda la política

SELinux es una política adicional de procesos/recursos, separada del propietario/modo Unix y del firewall. **Enforcing** aplica la política y registra denegaciones; **permissive** registra las denegaciones potenciales sin aplicarlas; **disabled** significa que SELinux no aplica reglas. Este laboratorio no cambia los modos. Ubuntu suele usar AppArmor; no instales ni cambies a SELinux solo para seguir esta rama alternativa.

**Servidor Rocky, usuario normal; sudo para acceder al registro de auditoría:**

```bash
getenforce
sestatus
ls -Z "$HOME"
sudo ausearch -m AVC,USER_AVC -ts recent -i
```

Haz este ejercicio en el sistema invitado preparado y con SELinux habilitado. Si está deshabilitado, vuelve a una instantánea preparada correctamente en vez de intentar una reetiquetación global en vivo. Para usar `ausearch`, deben estar disponibles las herramientas `audit`. Que no haya coincidencias significa que no hay registros de auditoría conservados que coincidan en ese período, no que la política jamás pueda denegar el acceso.

Un registro AVC identifica el permiso intentado, el proceso, el objeto, el contexto de origen (`scontext`) y el contexto de destino (`tcontext`). Lee juntos el ejecutable/ruta y la hora. Un contexto SELinux suele ser `user:role:type:level`; el **tipo** es fundamental para la política dirigida. No envíes todas las denegaciones a ciegas a `audit2allow`: a menudo la causa es una etiqueta incorrecta o una ruta de aplicación equivocada.

**Servidor Rocky, usuario normal; crea un archivo temporal privado:**

```bash
SEL_DIR=$(mktemp -d "$HOME/network-beginner-selinux.XXXXXX")
printf '%s\n' "$SEL_DIR"
```

Si falla, detente y registra la ruta exacta; luego:

```bash
touch "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
matchpathcon "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

La búsqueda de política indica el contexto esperado para esta ruta. Primero establece esa línea base; no memorices un tipo único para todas las estructuras de directorios personales. Ahora asigna deliberadamente al archivo otro tipo existente y repáralo.

**Servidor Rocky, usuario normal que ejecuta sudo donde se indica:**

```bash
sudo chcon -t httpd_sys_content_t "$SEL_DIR/probe.txt"
ls -Z "$SEL_DIR/probe.txt"
sudo restorecon -n -v "$SEL_DIR/probe.txt"
sudo restorecon -v "$SEL_DIR/probe.txt"
matchpathcon -V "$SEL_DIR/probe.txt"
```

`chcon` cambia la etiqueta de este archivo; no crea una regla persistente de contexto de archivo. `restorecon -n` muestra una vista previa sin cambiarlo y `restorecon` restaura la etiqueta que define la política para la ruta. La verificación final debería coincidir con la política. Como el directorio padre es privado, este ejercicio solo trata de etiquetas, no es un despliegue de contenido web; no se promete un AVC porque no se configuró deliberadamente una aplicación confinada para acceder al archivo.

Las rutas personalizadas persistentes pueden necesitar una asignación `semanage fcontext` deliberadamente acotada antes de `restorecon`, pero aquí no hace falta. Para limpiar, **servidor Rocky, usuario normal**, ejecuta `rm -i -- "$SEL_DIR/probe.txt"` y `rmdir -- "$SEL_DIR"`. Si el ejercicio se detuvo después de `chcon`, ejecuta el mismo `restorecon` acotado antes de limpiar. Nunca deshabilites SELinux globalmente ni reetiquetes todo el sistema de archivos para este archivo.

## 5. Paquetes opcionales y EPEL/CRB de Rocky 9 {#epel-prerequisites}

La lección básica de firewall/SELinux se completa sin Fail2ban ni `iftop`. Esta sección también ofrece los requisitos de Rocky mencionados en la ruta opcional con `iftop` de la lección 7. La instalación de paquetes se realiza **solo en el sistema invitado desechable**, mediante su conexión de administración.

En el **servidor Ubuntu**, inspecciona primero `apt-cache policy fail2ban python3-systemd`. Si hay candidatos en los repositorios Ubuntu configurados, `sudo apt update` seguido de `sudo apt install fail2ban python3-systemd` instala Fail2ban y su backend de journal. Si no hay candidato, inspecciona la configuración de componentes de los repositorios oficiales en vez de añadir una fuente de descarga aleatoria.

En **Rocky 9**, EPEL es el repositorio adicional de Fedora para Enterprise Linux; CRB proporciona dependencias. Esto no justifica usar EPEL Next, otra versión principal de EL ni deshabilitar la comprobación de firmas de paquetes.

**Sistema invitado Rocky, usuario normal; registra el estado original del repositorio/paquetes:**

```bash
dnf repolist --all
rpm -q epel-release dnf-plugins-core fail2ban-server python3-systemd
```

Registra si CRB/EPEL ya estaban habilitados y qué paquetes estaban instalados; crea una instantánea `before-optional-packages`. Luego, **sistema invitado Rocky, usuario normal que ejecuta sudo**:

```bash
sudo dnf install dnf-plugins-core
sudo dnf config-manager --set-enabled crb
sudo dnf install epel-release
dnf repolist --enabled
dnf info fail2ban-server python3-systemd iftop
```

Comprueba que EPEL corresponda a la versión **9**, que se usen los repositorios/firmas previstos y que haya candidatos para la arquitectura del sistema invitado. Para Fail2ban, usa `sudo dnf install fail2ban-server python3-systemd`; para la herramienta opcional de la lección 7, instala allí solo `iftop`. Inspecciona las transacciones y detente ante dependencias sin resolver; las versiones de paquetes cambian, así que no se presupone una compilación exacta.

No deshabilites CRB/EPEL si ya estaban antes del ejercicio o si otro software instalado los necesita. Si fue solo una prueba temporal, restaura `before-optional-packages` después de todas las lecciones dependientes. Esa es la reversión exacta de paquetes/repositorios; deshabilitar un repositorio por sí solo no desinstala los paquetes instalados.

## 6. Jaula Fail2ban opcional con acciones limitadas al laboratorio

Fail2ban lee los registros de fallos de autenticación mediante un **filtro**, cuenta eventos dentro de `findtime` e invoca una **acción** cuando se alcanza `maxretry`. Una **jaula** combina estos ajustes. No corrige claves débiles, no sustituye la política base del firewall ni detiene todos los ataques distribuidos/lentos. Un filtro/backend incorrecto puede dejar en ejecución un servicio que no detecta nada.

Esta configuración opcional supone una **instalación nueva de Fail2ban sin jaulas personalizadas existentes**. Si ya se usa, inspecciona antes sus responsables/configuración; no detengas la protección de otra carga de trabajo. Registra el estado inicial del servicio/habilitación. Una instalación nueva puede iniciarlo automáticamente: usa la consola para detener solo este servicio nuevo durante la preparación con `sudo systemctl stop fail2ban`. Revisa `/etc/fail2ban/jail.conf`, `jail.d` y las acciones instaladas. No edites el `jail.conf` del paquete.

Crea **un** archivo de acción nuevo para el administrador seleccionado, rechazando sobrescrituras.

**Servidor, usuario normal que ejecuta sudo:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/action.d/network-beginner.conf'
sudoedit /etc/fail2ban/action.d/network-beginner.conf
```

**Solo para UFW**, coloca este contenido INI en el archivo nuevo y sustituye `REPLACE_WITH_LAB_NIC` por el nombre de NIC del servidor verificado por MAC. No dejes el marcador.

```ini
[Definition]
actionstart =
actionstop =
actioncheck = LC_ALL=C ufw status | grep -q 'Status: active'
actionban = ufw insert 1 deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22 comment 'network-beginner-ban'
actionunban = ufw delete deny in on REPLACE_WITH_LAB_NIC proto tcp from <ip> to 192.0.2.20 port 22
```

**Solo para firewalld**, usa este contenido en su lugar; la zona del curso debe seguir asignada exclusivamente a la NIC del laboratorio:

```ini
[Definition]
actionstart =
actionstop =
actioncheck = firewall-cmd --zone=network-beginner --list-all
actionban = firewall-cmd --zone=network-beginner --add-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
actionunban = firewall-cmd --zone=network-beginner --remove-rich-rule='rule family="ipv4" priority="-10" source address="<ip>" destination address="192.0.2.20/32" port port="22" protocol="tcp" reject'
```

Estas acciones limitan un origen detectado a **interfaz/zona de laboratorio, destino `.20`, TCP 22**; no bloquean ese origen en la dirección de administración ni en TCP 8000. La inserción de UFW antes del permiso y la prioridad negativa de firewalld hacen que la denegación temporal preceda al permiso del laboratorio. Fail2ban elimina la regla después de `bantime`; no recargues el firewall subyacente durante este experimento opcional. Este temporizador pertenece a Fail2ban, no a la regla UFW: si falla el daemon, inspecciona y elimina solo el bloqueo de curso restante usando su especificación exacta `actionunban`; no supongas que venció.

**Servidor, usuario normal que ejecuta sudo; crea una jaula exclusiva:**

```bash
sudo sh -c 'umask 077; set -C; : > /etc/fail2ban/jail.d/99-network-beginner.local'
sudoedit /etc/fail2ban/jail.d/99-network-beginner.local
```

Usa este INI para **Ubuntu**. En **Rocky**, sustituye solo `ssh.service` por `sshd.service` en `journalmatch`.

```ini
[sshd]
enabled = false

[network-beginner-sshd]
enabled = true
filter = sshd
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service
usedns = no
ignoreip = 127.0.0.0/8 ::/0
port = 22
maxretry = 3
findtime = 60
bantime = 60
action = network-beginner
```

El ajuste `[sshd]` impide que una jaula SSH predeterminada del paquete aplique una segunda acción más amplia en esta **instalación nueva**. Confirma que no haya otra jaula habilitada; no uses esto para desactivar protecciones personalizadas existentes. La jaula nombrada usa explícitamente el filtro `sshd` y tu acción nueva. `backend=systemd` lee el journal, así que **no** añadas `logpath`. `journalmatch` debe coincidir con los metadatos reales de la unidad de registro. `::/0` excluye IPv6 deliberadamente de esta demostración solo IPv4; no es una política de protección para producción.

**Servidor, usuario normal que ejecuta sudo; valida antes de iniciar:**

```bash
sudo journalctl -u ssh.service -b -n 10 -o verbose --no-pager
sudo fail2ban-client -t
sudo fail2ban-client -d
```

En Rocky, usa `-u sshd.service`. Inspecciona `_SYSTEMD_UNIT` en registros reales relacionados con autenticación; si no hay coincidencias, la cobertura del backend no queda demostrada. `-t` prueba la configuración, mientras que `-d` vuelca la configuración interpretada sin iniciar su aplicación. Verifica el nombre de la jaula, backend/coincidencia de journal, una acción prevista, tiempos limitados y ausencia de jaulas habilitadas en conflicto.

**Servidor, usuario normal que ejecuta sudo:**

```bash
sudo systemctl start fail2ban
sudo fail2ban-client status
sudo fail2ban-client status network-beginner-sshd
sudo fail2ban-client get network-beginner-sshd journalmatch
sudo fail2ban-client get network-beginner-sshd actions
sudo fail2ban-client get network-beginner-sshd action network-beginner actionban
sudo journalctl -u fail2ban -b -n 30 --no-pager
```

Espera la jaula prevista y el comando de acción ampliado y acotado, sin errores de inicio. Cero fallos/bloqueos es normal. **No ejecutes un bucle de fuerza bruta ni te bloquees a propósito.** Estas comprobaciones validan la configuración/inicio, no la detección o aplicación demostrada ante un ataque. Hay que resolver metadatos de servicio incorrectos, falta de soporte de journal de Python, un filtro que no coincide o errores al ejecutar la acción antes de afirmar que funciona la protección.

Si un bloqueo accidental incluye al cliente de laboratorio conocido, desde la **consola del servidor, sudo**:

```bash
sudo fail2ban-client set network-beginner-sshd unbanip 192.0.2.10
sudo fail2ban-client status network-beginner-sshd
```

Esto solicita desbloquear exactamente una IP. Verifica que la regla UFW/rich correspondiente ya no esté presente y que funcione una conexión SSH nueva; una sesión existente no basta. No vacíes todos los bloqueos ni reglas del firewall.

Para limpiar, desbloquea las direcciones que realmente aparezcan en **esta jaula**, una dirección exacta a la vez, y confirma que se eliminó la acción. Luego ejecuta `sudo fail2ban-client stop network-beginner-sshd`, detén el servicio solo si originalmente estaba inactivo/era nuevo y elimina únicamente los dos archivos creados aquí con `sudo rm -i -- /etc/fail2ban/jail.d/99-network-beginner.local /etc/fail2ban/action.d/network-beginner.conf`. Verifica que ya no exista la jaula ni quede un bloqueo del curso. Hazlo **antes de eliminar la zona firewalld**. Restaura el estado registrado del servicio/habilitación; la reversión completa de la instalación opcional usa la instantánea.

## Finalización y siguiente lección

Deberías poder mostrar el administrador seleccionado, la interfaz/zona correcta, las reglas exactas TCP 22/8000 de `.10` a `.20`, conexiones SSH/HTTP nuevas permitidas, la administración sin cambios y las operaciones inversas. Explica la diferencia entre las reglas guardadas de UFW y las reglas firewalld de ejecución/permanentes, y entre el modo correcto de archivo y el tipo SELinux correcto. Informa de Fail2ban opcional como «configuración verificada» salvo que tengas pruebas adicionales validadas.

Conserva la **política de firewall guardada y acotada por origen** para la [lección 7](07-monitoring-performance.md). Si practicaste su eliminación, vuelve a aplicarla y verifícala primero. Para la lección siguiente no se necesita ningún proceso HTTP, etiqueta incorrecta deliberada ni jaula Fail2ban temporal.

Cuando ya no hagan falta, elimina los archivos de referencia exactos que creaste en `FW_NOTE` (`management.before`, `routes.before` y los archivos de referencia de la rama elegida), y luego ejecuta `rmdir` en el directorio vacío. Restaura el estado registrado del perfil/firewall solo al terminar el curso. Nunca elimines una zona/regla desconocida solo porque su nombre te resulte familiar.

## Referencias principales

Revisadas el 15 de septiembre de 2026:

- [Manual de UFW para Ubuntu](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html): dirección de reglas, interfaces, orden, persistencia y eliminación exacta.
- [CLI de firewalld](https://firewalld.org/documentation/man-pages/firewall-cmd.html), [lenguaje rich](https://firewalld.org/documentation/man-pages/firewalld.richlanguage.html) y [zonas](https://firewalld.org/documentation/zone/connections-interfaces-and-sources.html): timeouts, recarga, reglas de origen/destino y clasificación.
- [Ajustes de conexiones de NetworkManager](https://networkmanager.dev/docs/api/latest/settings-connection.html): cambios inmediatos de `zone` en conexiones activas y comportamiento vacío/predeterminado.
- [Guía SELinux de Rocky Linux 9](https://docs.rockylinux.org/9/guides/security/learning_selinux/) y [herramientas de etiquetado SELinux](https://github.com/SELinuxProject/selinux/tree/main/policycoreutils/setfiles): diagnóstico AVC y restauración de contexto acotada.
- [Guía de inicio de Fedora EPEL](https://docs.fedoraproject.org/en-US/epel/getting-started/), [documentación de repositorios de Rocky](https://wiki.rockylinux.org/rocky/repo/) y [paquetes EPEL de Fail2ban](https://packages.fedoraproject.org/pkgs/fail2ban/fail2ban-server/): fuentes de paquetes opcionales y requisitos previos.
- [Configuración de jaulas Fail2ban](https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf), [backend systemd](https://github.com/fail2ban/fail2ban/blob/master/fail2ban/server/filtersystemd.py) y [manual del cliente](https://manpages.ubuntu.com/manpages/noble/man1/fail2ban-client.1.html): separación de filtro/backend/acción, pruebas de configuración, estado y desbloqueo acotado.

[Cuestionario](../../quizzes/networking/beginner/06-firewalls-host-security-quiz.md) | [Continuar con supervisión](07-monitoring-performance.md)
