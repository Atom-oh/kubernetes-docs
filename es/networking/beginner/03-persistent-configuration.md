# 03. Configuración persistente de red

> **Versiones compatibles**: Ubuntu Server 24.04 LTS (principal), Rocky Linux 9 (alternativa)
> **Última actualización**: 15 de septiembre de 2026

Una dirección añadida con `ip address add` cambia la configuración actual del kernel. No es una instrucción para el siguiente arranque. En este capítulo darás al propietario de la configuración de red una instrucción duradera y luego compararás la configuración guardada con lo que realmente usa la VM.

## Requisitos previos y objetivos

Completa [direcciones e interfaces](02-addressing-interfaces.md) y prepara el [laboratorio del curso](README.md). Usa dos VM desechables y sus consolas de hipervisor. Ambas pueden ejecutar Ubuntu; aprender Rocky a la vez es opcional.

| Elemento | Estado requerido |
|---|---|
| NIC de laboratorio del cliente | `192.0.2.10/24` después de esta lección |
| NIC de laboratorio del servidor | `192.0.2.20/24` después de esta lección |
| Red de laboratorio | La misma red virtual interna, sin servidor DHCP, router ni enlace ascendente |
| NIC de administración | Conexión NAT/DHCP separada y existente; conserva su dirección, rutas y configuración DNS |
| Identidad | Registra la MAC de cada NIC en el hipervisor y hazla coincidir dentro del sistema invitado |
| Acceso y herramientas | Consola del sistema invitado, acceso sudo, editor, `ip` y herramientas del administrador de red instalado |

Ejecuta los comandos **dentro de la VM indicada**, nunca en la estación de trabajo que aloja las VM. No instales ni habilites un segundo administrador de red para seguir una rama alternativa. Si falta una herramienta necesaria, vuelve a la preparación del laboratorio.

Podrás identificar quién es propietario de la configuración, guardar una dirección estática, explicar cuándo corresponden ajustes DHCP/gateway/DNS, verificar el estado después de reiniciar y deshacer solo los cambios del laboratorio. Primero crea una instantánea de la VM y mantén abierta la consola. Haz cada paso por separado; si aparece un error, inspecciónalo antes de continuar.

## 1. Identifica la NIC y quién la administra

En **cada VM**, inspecciona el inventario sin cambiar nada:

```bash
cat /etc/os-release
ip -br link
ip -br address
ip -4 route show
ip -6 route show default
systemctl is-active systemd-networkd NetworkManager
```

`ip -br link` relaciona nombres de interfaz con direcciones MAC. Busca la MAC de **laboratorio** del hipervisor, no la primera interfaz de la lista. La NIC NAT/DHCP normalmente lleva la ruta predeterminada de administración. Registra su identidad y los ajustes actuales de ruta/DNS antes de continuar. `systemctl is-active` puede devolver un estado distinto de cero porque uno de los dos servicios no existe o está inactivo; eso por sí solo no indica un problema.

En todo este capítulo, sustituye `REPLACE_WITH_LAB_NIC` por el nombre que acabas de verificar. Las variables pertenecen al shell actual; los bloques independientes las repiten. No asignes nunca un valor del laboratorio a variables del shell como `HOME` o `PATH`.

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip link show dev "$LAB_IF"
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
```

El segundo comando muestra las direcciones actuales del kernel; no identifica quién las volverá a crear. Completa la limpieza específica de la dirección temporal del capítulo 02 antes de empezar aquí. Una NIC de laboratorio recién añadida no debe conservar ninguna dirección IPv4 temporal. No elimines una dirección que pertenezca a un perfil existente solo porque no la esperabas.

Determina quién administra la NIC a partir de la evidencia:

| Evidencia | Propietario de la configuración y acción |
|---|---|
| El YAML de Netplan de Ubuntu selecciona `networkd`; `networkctl status` identifica el archivo de red correspondiente | Sigue la rama A |
| NetworkManager en Rocky informa de un dispositivo administrado y sus perfiles | Sigue la rama B |
| Netplan selecciona `NetworkManager` | Netplan también es una fuente anterior de configuración; inspecciona el YAML y el perfil generado antes de editar |
| cloud-init, una herramienta de aprovisionamiento, archivos `.network` directos, coincidencias con comodines o varias definiciones administran la misma NIC | Resuelve la propiedad antes de añadir otra definición; usa una VM limpia del curso si el origen no está claro |

Netplan traduce YAML a configuración del backend. `systemd-networkd` y NetworkManager aplican la configuración a los dispositivos; `nmcli` y `nmtui` se comunican con NetworkManager. Que un servicio se esté ejecutando no demuestra que administre todas las NIC. La ruta de Ubuntu Server utilizada aquí no es una afirmación sobre todas las imágenes Ubuntu, Ubuntu Desktop ni instalaciones Debian.

### Comprobaciones de propiedad de la rama A: Ubuntu Netplan/networkd

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
sudo netplan get
sudo ls -l /etc/netplan
networkctl status "$LAB_IF"
sudo ls -l /etc/systemd/network /run/systemd/network
resolvectl status
```

`netplan get` muestra la configuración combinada; inspecciona los archivos YAML reales con `sudo less /etc/netplan/ACTUAL_FILE.yaml`, usando un nombre de archivo de la lista. Inspecciona también los directorios `/lib/netplan` y `/run/netplan` que ya existan. `networkctl status` muestra el archivo de red coincidente, si lo hay. `resolvectl status` registra los servidores DNS y enlaces existentes.

Netplan combina archivos YAML con nombres distintos en orden lexicográfico: los valores escalares posteriores reemplazan los anteriores, pero las listas pueden **concatenarse**. Añadir un archivo posterior con listas de dirección/DNS vacías no es una forma general de borrar una lista anterior. Una definición con otro nombre también puede coincidir con la misma NIC. Consulta [combinación de archivos Netplan](https://netplan.readthedocs.io/en/stable/netplan-generate/).

El procedimiento siguiente requiere una NIC de laboratorio **sin definición persistente existente**, incluidas coincidencias comodín en archivos networkd directos. Si un instalador ya la definió, inspecciona quién es propietario de ese archivo y haz una copia de seguridad antes de editar deliberadamente su sección exacta del laboratorio; no pegues este archivo encima del archivo del instalador ni conserves dos definiciones. Un comentario de cloud-init es motivo para inspeccionar la fuente de aprovisionamiento, no para deshabilitar cloud-init globalmente. En un primer laboratorio, añadir la NIC interna después de la configuración inicial del SO evita muchos conflictos de este tipo.

### Comprobaciones de propiedad de la rama B: Rocky NetworkManager

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
nmcli --version
nmcli device status
nmcli -f GENERAL,IP4,IP6,CONNECTIONS device show "$LAB_IF"
nmcli -f NAME,UUID,TYPE,DEVICE,AUTOCONNECT connection show
```

`device` describe la NIC; `connection` describe un perfil guardado. Sus nombres no tienen por qué coincidir. `GENERAL.CON-UUID` identifica el perfil activo actual, si lo hay. `CONNECTIONS` ayuda a identificar perfiles compatibles, incluidos los inactivos. Registra el UUID del perfil de laboratorio anterior y si estaba activo; conserva el perfil de administración.

Inspecciona cada perfil compatible con `nmcli connection show uuid ACTUAL_UUID`. Registra `connection.interface-name`, `802-3-ethernet.mac-address`, `connection.autoconnect` y `connection.autoconnect-priority`. Las asociaciones vacías de dispositivo/MAC pueden hacer que un perfil Ethernet coincida con varias NIC. No cambies un perfil compartido solo para simplificar el laboratorio.

Rocky 9 admite la configuración keyfile de NetworkManager y puede tener perfiles ifcfg más antiguos. No deduzcas el formato de almacenamiento solo por el nombre de una interfaz. La [guía versionada de Rocky 9](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/) cubre esa versión; la [guía sin versión](https://docs.rockylinux.org/guides/network/basic_network_configuration/) ahora trata Rocky 10.

## 2A. Guarda la dirección con Netplan/networkd

Usa esta rama solo después de las comprobaciones de propiedad de la rama A. Repítela en cliente y servidor con **su propia MAC y dirección**.

### Haz una copia y crea un archivo propio

En cada **VM Ubuntu**, crea un directorio de recuperación nuevo. Si ya existe, detente e inspecciona el intento anterior; no reemplaces su copia de seguridad.

```bash
sudo mkdir -m 700 /root/network-beginner-03
sudo cp -a /etc/netplan /root/network-beginner-03/netplan-before
sudo sh -c 'umask 077; set -C; : > /etc/netplan/90-beginner-lab.yaml'
sudoedit /etc/netplan/90-beginner-lab.yaml
```

`cp -a` conserva los archivos originales y sus permisos. El pequeño comando `sh` crea un archivo vacío que solo puede leer root; `set -C` se niega a sobrescribir un archivo existente. `sudoedit` abre una copia editable con el editor configurado.

Pega este **documento YAML completo**, usando espacios en lugar de tabuladores. Sustituye la MAC de ejemplo por la MAC real de laboratorio del cliente. En el servidor, sustituye la MAC por la MAC de laboratorio del servidor y cambia la dirección a `192.0.2.20/24`.

```yaml
network:
  version: 2
  ethernets:
    beginner-lab:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:10"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 192.0.2.10/24
      optional: true
```

| Ajuste | Significado en este laboratorio |
|---|---|
| `version: 2` | Versión del esquema de configuración de Netplan |
| `beginner-lab` | ID de definición; la coincidencia de MAC selecciona la NIC sin renombrarla |
| `renderer` en el dispositivo | Selecciona networkd para esta definición sin cambiar el renderer global |
| `dhcp4: false` | No solicita DHCP en una red sin servidor DHCP |
| Ajustes IPv6 y de enlace local | Mantienen esta NIC limitada a IPv4 en este ejercicio aislado; no es una recomendación de IPv6 para todo el host |
| `addresses` | Una dirección con prefijo `/24`; la subred conectada no necesita gateway |
| `optional: true` | networkd no retrasa el arranque esperando por esta NIC de laboratorio, pero aun así la configura |

Deliberadamente no hay bloque `routes` ni `nameservers`. Ninguna VM es router ni servidor DNS. Adivinar `192.0.2.1` como gateway no lo crea. La NIC de administración conserva su configuración original.

### Valida, prueba y observa

```bash
sudo chmod 600 /etc/netplan/90-beginner-lab.yaml
sudo netplan generate
sudo netplan get
```

`chmod 600` permite que solo root lea/escriba el archivo. `generate` valida y genera la configuración del backend sin aplicarla en esta sesión normal con el sistema ya arrancado. Normalmente termina sin imprimir nada. Comprueba la salida combinada: exactamente la dirección/MAC de laboratorio prevista, ningún gateway/DNS nuevo para la NIC de laboratorio y la definición de administración original. Un documento YAML válido aún puede tener la MAC o dirección incorrectas.

Desde la **consola de la VM**, inicia la prueba:

```bash
sudo netplan try --timeout 120
```

Mientras espera el mensaje de confirmación, usa una segunda consola o sesión para inspeccionar:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route show dev "$LAB_IF"
ip -4 route show default
ip -6 route show default
networkctl status "$LAB_IF"
resolvectl status
```

Espera una ruta local `192.0.2.0/24`, la dirección `.10` o `.20` correcta, que la NIC de laboratorio no haya añadido ruta predeterminada ni DNS, y que la ruta de administración original siga disponible. Confirma la prueba solo después de estas comprobaciones. Configura ambas VM antes de exigir que el ping al par funcione.

`try` y `apply` operan sobre la **configuración combinada**, no solo sobre el archivo nuevo, y pueden volver a aplicar la configuración de red en varios dispositivos. Sigue haciendo falta acceso a la consola aunque no hayas editado la definición de administración. `try` está pensado para revertir una prueba que no se confirmó, pero [Netplan documenta errores de rollback](https://netplan.readthedocs.io/en/stable/netplan-try/). El timeout o Ctrl+C **no demuestran que la configuración se recuperó**; inspecciona el estado de ejecución y los archivos del disco.

### Recuperación y reversión de Netplan

Conserva la configuración de trabajo del laboratorio para las siguientes lecciones. Para abandonar este cambio, recupérate desde la **consola**:

1. Inspecciona `/etc/netplan/90-beginner-lab.yaml` y confirma que sea el archivo creado aquí.
2. Mueve solo ese archivo fuera de los directorios de entrada de Netplan.
3. Genera y aplica la configuración restante, que funcionaba antes.

```bash
sudo mv -i /etc/netplan/90-beginner-lab.yaml /root/network-beginner-03/90-beginner-lab.failed.yaml
sudo netplan generate
sudo netplan apply
```

`mv -i` pregunta antes de reemplazar una copia de un fallo anterior. Si `generate` falla, detente antes de `apply`. Si decidiste editar un archivo existente que ya tenía propietario en vez de usar la ruta para una NIC nueva, compáralo con su archivo correspondiente en `netplan-before` y restaura **ese mismo archivo editado**; luego ejecuta generate/apply. No reemplaces todo el directorio.

Vuelve a comprobar las direcciones, rutas y acceso de administración. Una NIC de laboratorio que ahora no esté administrada puede conservar estado de ejecución. **Solo si aún está presente la dirección exacta de esta lección**, elimínala:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_CIDR='192.0.2.10/24'
sudo ip address del "$LAB_CIDR" dev "$LAB_IF"
```

En el servidor, establece `LAB_CIDR='192.0.2.20/24'`. Si el inventario inicial indicaba que la NIC de laboratorio estaba deshabilitada administrativamente, restablece ese estado con `sudo ip link set dev "$LAB_IF" down` en el mismo shell. No elimines rutas de administración ni vacíes interfaces. Antes de reiniciar como paso final de recuperación, verifica que la configuración del disco sea la restaurada. Si no está claro quién es el propietario o cómo recuperarse, restaura la instantánea de la VM anterior a la lección.

## 2B. Guarda la dirección con NetworkManager

En cada **VM Rocky**, usa el inventario de la rama B. Esta ruta crea `beginner-lab-static` en cada sistema invitado. Debe ser un nombre nuevo; si ya existe, inspecciona el intento anterior en vez de crear un perfil duplicado.

Conserva como opciones de recuperación los perfiles compatibles más antiguos. Para hacer predecible la selección tras reiniciar, deshabilita autoconnect **solo en los perfiles vinculados exclusivamente a la NIC de laboratorio**, registrando primero cada valor original:

```bash
OLD_LAB_UUID='REPLACE_WITH_CONFIRMED_LAB_PROFILE_UUID'
nmcli -f connection connection show uuid "$OLD_LAB_UUID"
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect no
```

Omite este bloque si no hay un perfil de laboratorio anterior. Repítelo para cualquier otro perfil candidato que pertenezca solo al laboratorio; por ahora deja intacta la activación actual. Si un perfil candidato no está vinculado o es compartido, o su propiedad es incierta, acláralo antes de continuar. `DEVICE=--` solo significa inactivo, no inocuo.

Crea el perfil nuevo; este bloque primero **lo guarda sin activarlo automáticamente**:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_MAC='REPLACE_WITH_LAB_MAC'
LAB_CIDR='192.0.2.10/24'
sudo nmcli connection add type ethernet con-name beginner-lab-static \
  ifname "$LAB_IF" 802-3-ethernet.mac-address "$LAB_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses "$LAB_CIDR" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv6.method disabled
nmcli -f connection,802-3-ethernet,ipv4,ipv6 connection show id beginner-lab-static
```

Usa `.20/24` en el servidor. `manual` requiere una dirección/prefijo. Las asociaciones de interfaz y MAC restringen qué dispositivo puede usar el perfil; `mac-address` coincide con la MAC permanente en vez de cambiarla. El gateway/DNS vacío y `never-default yes` lo mantienen local. `connection add` guarda los datos de forma persistente de manera predeterminada; **guardado aún no significa activo**.

Registra el UUID nuevo de la salida. Activa exactamente este perfil y luego inspecciona el estado de ejecución:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli --wait 30 connection up uuid "$LAB_UUID" ifname "$LAB_IF"
nmcli -f GENERAL,IP4,IP6 device show "$LAB_IF"
ip -4 route show
```

La activación puede reemplazar el perfil activo anterior de esta NIC. Espera la dirección prevista, la ruta a la subred conectada y que no haya gateway/DNS de laboratorio. Compara la ruta de administración con el inventario inicial. Si falla la activación, inspecciona `journalctl -u NetworkManager -b -n 50 --no-pager`. Un timeout no demuestra que el perfil guardado haya desaparecido.

Después de observar resultados correctos, habilita la activación en los siguientes arranques:

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect yes
nmcli -f connection.id,connection.uuid,connection.autoconnect connection show uuid "$LAB_UUID"
```

### El mismo perfil en nmtui

Si `nmtui` ya está disponible, abre el **perfil dedicado existente**:

```bash
sudo nmtui edit beginner-lab-static
```

Usa Tab para moverte, las flechas para elegir, Espacio para alternar y Enter para aceptar. Comprueba el nombre del perfil/dispositivo, establece IPv4 en **Manual**, expándelo y verifica la única dirección `.10/24` o `.20/24`. Deja vacíos Gateway, DNS servers y search domains; en Routes, si aparece, selecciona **Never use this network for default route**. Mantén IPv6 **Disabled** y activa la conexión automática después de validarla.

Elige **Cancel** solo para inspeccionar o **OK** para guardar los cambios previstos. Guardar cambia el mismo perfil de NetworkManager que `nmcli`; no es una capa de configuración diferente. Tras guardar, inspecciona con `nmcli connection show` y activa el UUID registrado usando el bloque anterior. Los menús varían por versión de paquete; si falta una propiedad, establécela con `nmcli` y verifícala. No uses una desactivación/reactivación general de la conexión de administración.

### Recuperación y reversión de NetworkManager

Desde la **consola**, inspecciona el UUID nuevo registrado y elimina solo tu perfil. Si nunca se creó correctamente, omite este bloque de perfil nuevo pero restaura de todas formas los valores anteriores de autoconnect que cambiaras:

```bash
LAB_UUID='REPLACE_WITH_NEW_LAB_PROFILE_UUID'
nmcli -f connection,ipv4 connection show uuid "$LAB_UUID"
sudo nmcli connection modify uuid "$LAB_UUID" connection.autoconnect no
sudo nmcli connection down uuid "$LAB_UUID"
sudo nmcli connection delete uuid "$LAB_UUID"
```

Un resultado «already inactive» de `down` es aceptable después de verificar el UUID; cualquier error distinto requiere investigación. Otros perfiles compatibles pueden activarse automáticamente cuando se desactiva una conexión, así que vuelve a inspeccionar el dispositivo.

Si había un perfil de laboratorio anterior, restaura todos los valores de autoconnect registrados. Reactívalo **solo si estaba activo antes de la lección**:

```bash
LAB_IF='REPLACE_WITH_LAB_NIC'
OLD_LAB_UUID='REPLACE_WITH_PREVIOUS_LAB_PROFILE_UUID'
OLD_AUTOCONNECT='yes'
sudo nmcli connection modify uuid "$OLD_LAB_UUID" connection.autoconnect "$OLD_AUTOCONNECT"
sudo nmcli --wait 30 connection up uuid "$OLD_LAB_UUID" ifname "$LAB_IF"
```

Usa el `yes` o `no` registrado, no un valor supuesto. Si el perfil anterior estaba inactivo, omite la línea `up`. Si no había un perfil anterior, no tienes que restaurar ninguno: comprueba que ya no esté la dirección de la lección. Si hace falta, restaura el estado up/down original del enlace de laboratorio y compara el direccionamiento/rutas/DNS de administración con el registro inicial. No elimines todos los perfiles Ethernet ni reinicies la red globalmente.

## 3. DHCP, gateways y DNS: cuándo corresponden estos ajustes

El direccionamiento estático asigna la dirección elegida por el administrador. DHCP solicita una concesión a un servidor DHCP real, que también puede proporcionar rutas y DNS. Habilitar DHCP en la red interna del curso no obtendrá una concesión. Un servidor DNS responde consultas de nombres; un gateway reenvía paquetes fuera de la red directamente conectada. Un dispositivo puede proporcionar ambos servicios, pero ninguno de esos roles se deduce simplemente de que su IP termine en `.1`.

Los siguientes son **ejemplos opcionales de adaptación, no cambios al laboratorio del curso de dos VM**. Usa una interfaz/VM de práctica desechable y separada, identificada por su MAC en el hipervisor, con acceso a consola, sin propietario en conflicto y conectada a una red virtual que ya tenga DHCP o una red enrutada especificada por un administrador. Nunca uses la NIC de administración de ninguna de las dos VM del curso.

### DHCP en una red que lo proporciona realmente

Para una **NIC administrada por networkd** disponible en una red de práctica con DHCP, una definición completa de Netplan sería:

```yaml
network:
  version: 2
  ethernets:
    practice-dhcp:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:30"
      dhcp4: true
      dhcp4-overrides:
        use-routes: false
        use-dns: false
        use-domains: false
      dhcp6: false
      accept-ra: false
      link-local: []
      optional: true
```

Sustituye la MAC de ejemplo por la MAC de la NIC disponible. Estas anulaciones solicitan una dirección y a la vez rechazan las rutas, DNS y dominios de búsqueda de DHCP, preservando la ruta de administración existente de la VM de práctica. Sigue recibiendo la ruta de la subred conectada. En una interfaz ascendente principal elegida deliberadamente, un administrador puede aceptar en cambio rutas y DNS de DHCP; este curso no cambia una interfaz ascendente existente.

Usa el mismo procedimiento de archivo nuevo/copia de seguridad con un archivo distinto, como `90-beginner-dhcp.yaml`, modo 600, `generate`, inspección de salida combinada y `try`. Comprueba `networkctl status` e `ip address` para ver si hay una concesión. Si no llega ninguna, inspecciona carrier, selección de red virtual y disponibilidad del servicio/ámbito DHCP. Para deshacerlo, elimina solo este archivo y aplica la configuración restaurada; comprueba que no queden direcciones de laboratorio como en la rama A.

Para una **NIC disponible administrada por NetworkManager y aún sin configurar**, el perfil guardado equivalente es:

```bash
PRACTICE_IF='REPLACE_WITH_SPARE_NIC'
PRACTICE_MAC='REPLACE_WITH_SPARE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-dhcp \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no ipv4.method auto \
  ipv4.never-default yes ipv4.ignore-auto-routes yes ipv4.ignore-auto-dns yes \
  ipv6.method disabled
sudo nmcli --wait 60 connection up id beginner-practice-dhcp ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4,DHCP4 device show "$PRACTICE_IF"
```

El nombre no debe estar en uso. Registra su UUID y usa la reversión de la rama B basada en UUID para eliminar únicamente este perfil nuevo. Como este ejemplo usa `autoconnect no`, los ajustes se guardan, pero la activación tras reiniciar es manual. Si adaptas un **perfil de práctica dedicado existente** de estático a DHCP, establece `ipv4.method auto` y borra `ipv4.addresses`, `ipv4.gateway`, `ipv4.routes`, `ipv4.dns` y `ipv4.dns-search` en la misma operación `connection modify`; de lo contrario, los valores estáticos anteriores podrían coexistir con DHCP. Registra los valores antiguos primero y restáuralos para deshacer la adaptación.

### Ajustes persistentes de gateway y DNS en una red de práctica enrutada

Supongamos que una **VM de práctica separada**, no ninguna de las VM del curso, tiene `10.77.0.10/24` asignada por el administrador, un router real en el mismo enlace (`10.77.0.1`) y un resolver accesible (`10.77.0.53`) que sirve `training.example`. La NIC del ejercicio debe ser la interfaz ascendente predeterminada elegida explícitamente, **sin una ruta predeterminada de administración que compita**; usa la consola del hipervisor. El administrador debe confirmar que estos valores de ejemplo describen esa red de práctica antes de que los uses.

Para Netplan/networkd, la definición completa sería:

```yaml
network:
  version: 2
  ethernets:
    practice-uplink:
      renderer: networkd
      match:
        macaddress: "02:00:00:00:00:40"
      dhcp4: false
      dhcp6: false
      accept-ra: false
      link-local: []
      addresses:
        - 10.77.0.10/24
      routes:
        - to: default
          via: 10.77.0.1
      nameservers:
        addresses:
          - 10.77.0.53
        search:
          - training.example
```

`to: default` proporciona una ruta para los destinos sin coincidencia más específica. `via` es la dirección del router en el mismo enlace. `nameservers.addresses` selecciona el resolver; `search` puede expandir un nombre corto como `web` a `web.training.example`. No crea registros DNS. Usa un archivo independiente con copia de seguridad y propietario, sustituye la MAC y repite el proceso de permisos/validación/prueba/recuperación de la rama A.

Con NetworkManager, en una NIC de práctica equivalente, nueva y propia:

```bash
PRACTICE_IF='REPLACE_WITH_PRACTICE_UPLINK'
PRACTICE_MAC='REPLACE_WITH_PRACTICE_MAC'
sudo nmcli connection add type ethernet con-name beginner-practice-routed \
  ifname "$PRACTICE_IF" 802-3-ethernet.mac-address "$PRACTICE_MAC" \
  connection.autoconnect no \
  ipv4.method manual ipv4.addresses 10.77.0.10/24 \
  ipv4.gateway 10.77.0.1 ipv4.never-default no \
  ipv4.dns 10.77.0.53 ipv4.dns-search training.example \
  ipv6.method disabled
sudo nmcli --wait 30 connection up id beginner-practice-routed ifname "$PRACTICE_IF"
nmcli -f GENERAL,IP4 device show "$PRACTICE_IF"
```

Inspecciona el perfil nuevo antes de activarlo, registra su UUID y habilita autoconnect solo después de comprobaciones satisfactorias si quieres que se active en el arranque. Para revertirlo, elimínalo por UUID como en la rama B. Para cualquiera de los backends, verifica `ip route get 10.77.0.53`, la ruta predeterminada y un registro DNS proporcionado por el administrador. Inspecciona `resolvectl status` si resolved está activo; de lo contrario, revisa el DNS activo de NetworkManager y `/etc/resolv.conf`. No edites manualmente un `resolv.conf` generado ni trates un comando temporal `resolvectl dns` como un cambio persistente de perfil.

## 4. Verifica el laboratorio del curso después de reiniciar

Vuelve a la configuración estática de las dos VM del curso. Guarda tu trabajo y luego reinicia cada **sistema invitado desechable** desde su consola con `sudo reboot`. Después de iniciar sesión, vuelve a asociar las MAC con las NIC; las variables del shell no sobreviven al reinicio.

En el **cliente**:

```bash
LAB_IF='REPLACE_WITH_CLIENT_LAB_NIC'
ip -4 address show dev "$LAB_IF"
ip -4 route get 192.0.2.20
ip -4 route show default
ping -n -c 3 -W 2 192.0.2.20
```

En el **servidor**, inspecciona `.20/24` y ejecuta `ip -4 route get 192.0.2.10` y `ping -n -c 3 -W 2 192.0.2.10`. La consulta de ruta debe seleccionar la NIC de laboratorio y la dirección de origen local del laboratorio, sin `via`. La ruta predeterminada de administración puede seguir existiendo y debe coincidir con la configuración original. Es normal que los detalles de la concesión DHCP se renueven.

| Observación | Primera investigación |
|---|---|
| Falta la dirección tras reiniciar | MAC incorrecta, archivo/perfil sin guardar, autoconnect deshabilitado u otro propietario en conflicto |
| Dirección/DNS/ruta predeterminada de laboratorio adicional | Listas YAML combinadas, otra definición/perfil coincidente o estado temporal residual |
| `NO-CARRIER` | Estado del cable/adaptador del hipervisor y conexión a la red interna |
| Ruta correcta, sin respuesta a ping | Dirección del par, misma red interna, detección de vecinos y política ICMP; continúa con el capítulo 04 |
| Cambió el acceso de administración | Usa la consola y la reversión correspondiente; no vacíes las rutas |

## Comprobación final

- Identifica las NIC de laboratorio y administración a partir de evidencia MAC en ambas VM.
- Explica qué archivo/perfil administra la NIC de laboratorio y distingue el estado guardado del activo.
- Comprueba que `.10/24` y `.20/24` sobrevivan al reinicio con una ruta local al par.
- Demuestra que la NIC de laboratorio no añadió gateway/DNS y que se conserva la configuración de administración.
- Registra los resultados de ping entre pares e investiga los fallos en vez de inventar un gateway.
- Identifica el archivo/perfil nuevo exacto que hay que deshacer y el estado anterior que hay que restaurar.
- Explica por qué los ejemplos opcionales de DHCP/enrutamiento requieren una red de práctica preparada aparte.

Deja las direcciones estáticas de laboratorio funcionales para la siguiente lección. Conserva las notas de respaldo hasta terminar el curso.

## Fuentes principales y lecturas adicionales

- [Ubuntu Server: configuración de redes](https://documentation.ubuntu.com/server/explanation/networking/configuring-networks/)
- [Ejemplos de Netplan](https://netplan.readthedocs.io/en/stable/examples/), [referencia YAML](https://netplan.readthedocs.io/en/stable/netplan-yaml/), [permisos de archivos](https://netplan.readthedocs.io/en/stable/security/)
- [Generación y combinación de Netplan](https://netplan.readthedocs.io/en/stable/netplan-generate/), [Netplan try y advertencias de recuperación](https://netplan.readthedocs.io/en/stable/netplan-try/)
- [Ejemplos de nmcli de NetworkManager](https://www.networkmanager.dev/docs/api/latest/nmcli-examples.html), [manual nmcli](https://www.networkmanager.dev/docs/api/latest/nmcli.html), [propiedades de perfiles](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html), [nmtui](https://www.networkmanager.dev/docs/api/latest/nmtui.html)
- [Configuración de red de Rocky Linux 9](https://docs.rockylinux.org/9/guides/network/basic_network_configuration/)

[Anterior: Direcciones e interfaces](02-addressing-interfaces.md) · [Cuestionario](../../quizzes/networking/beginner/03-persistent-configuration-quiz.md) · [Siguiente: DNS y conectividad](04-dns-connectivity.md)
