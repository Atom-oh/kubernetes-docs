# Linux Basics Quiz

Este cuestionario evalúa tu comprensión de los conceptos fundamentales de Linux que forman la base de Kubernetes y la tecnología de contenedores.

## Multiple Choice Questions

1. ¿Cuál de los siguientes NO es un rol principal del kernel de Linux?
   - A) Gestión de procesos
   - B) Gestión de memoria
   - C) Proporcionar interfaz de usuario
   - D) Gestión de dispositivos
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Proporcionar interfaz de usuario**

**Explicación:**
El kernel de Linux es el núcleo del sistema operativo y actúa como intermediario entre el hardware y el software. Los roles principales del kernel incluyen la gestión de procesos, la gestión de memoria, la gestión de dispositivos y proporcionar interfaces de llamadas al sistema. La interfaz de usuario (GUI, CLI) la proporcionan programas separados que se ejecutan en el espacio de usuario y no es responsabilidad del kernel.

</details>

2. ¿Cuál de los siguientes NO es un tipo de namespace de Linux?
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Memory namespace**

**Explicación:**
Linux tiene los siguientes namespaces: PID (Process ID), Network, Mount, UTS (hostname), IPC (Inter-Process Communication), User y cgroup namespaces. Memory namespace no existe. El aislamiento de memoria se gestiona principalmente mediante cgroups.

</details>

3. ¿Cuál es la función principal de cgroups (Control Groups)?
   - A) Limitar y aislar el uso de recursos de grupos de procesos
   - B) Controlar el acceso al sistema de archivos
   - C) Filtrar paquetes de red
   - D) Gestionar la autenticación de usuarios
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Limitar y aislar el uso de recursos de grupos de procesos**

**Explicación:**
cgroups es una característica del kernel de Linux que limita y aísla el uso de recursos de grupos de procesos. Puede limitar y monitorear el uso de recursos como tiempo de CPU, memoria, E/S de bloques y ancho de banda de red. Esta es una tecnología central para implementar límites de recursos en contenedores.
</details>

4. En el permiso de archivo "rwxr-xr--", ¿cuáles son los permisos del usuario del grupo?
   - A) Lectura, escritura, ejecución
   - B) Lectura, ejecución
   - C) Solo lectura
   - D) Solo ejecución
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Lectura, ejecución**

**Explicación:**
En el permiso de archivo "rwxr-xr--":
  - Primeros 3 caracteres (rwx): permisos del propietario: lectura, escritura, ejecución
  - 3 caracteres centrales (r-x): permisos del grupo: lectura, ejecución
  - Últimos 3 caracteres (r--): permisos de otros usuarios: solo lectura

Por lo tanto, los usuarios del grupo tienen permisos de lectura y ejecución.

</details>

5. ¿Qué sistema de archivos se usa principalmente para implementar capas de imagen de contenedores?
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) OverlayFS**

**Explicación:**
OverlayFS es un sistema de archivos de montaje union que superpone múltiples directorios para presentarlos como un único directorio. Lo usan principalmente runtimes de contenedores como Docker para implementar capas de imagen. Esto permite que la imagen base permanezca de solo lectura mientras se añade una capa escribible para cada contenedor.
</details>

6. Al gestionar servicios con el comando systemctl, ¿qué comando configura un servicio para que se inicie automáticamente en el arranque?
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) systemctl enable**

**Explicación:**
`systemctl enable` configura un servicio para que se inicie automáticamente cuando el sistema arranca. `start` inicia el servicio inmediatamente, `restart` reinicia el servicio y `reload` solo vuelve a leer el archivo de configuración. En los nodos de Kubernetes, servicios centrales como kubelet y containerd deben tener el inicio automático configurado con `systemctl enable`.
</details>

7. ¿Qué parámetro del kernel es esencial para configurar un clúster de Kubernetes, ya que habilita el reenvío de paquetes IP para redes de contenedores?
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) net.ipv4.ip_forward**

**Explicación:**
`net.ipv4.ip_forward` es la configuración que habilita el reenvío de paquetes IP en el kernel de Linux. Esta configuración debe establecerse en 1 para habilitar la comunicación entre contenedores y entre contenedores y redes externas. Este parámetro debe habilitarse al configurar nodos de Kubernetes y puede establecerse con el comando `sysctl -w net.ipv4.ip_forward=1`.
</details>

8. En un archivo de unidad systemd, ¿qué directiva se usa para definir que un servicio debe iniciarse después de un servicio específico?
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) After**

**Explicación:**
En los archivos de unidad systemd, `After` define que la unidad actual debe iniciarse después de la unidad especificada. Por ejemplo, `After=network-online.target` garantiza que el servicio se inicie después de que la red esté lista. `Requires` define una dependencia fuerte, `Wants` define una dependencia débil y `Before` indica que la unidad actual debe iniciarse antes de otra unidad.
</details>

9. ¿Qué parámetro del kernel se requiere para que los plugins CNI funcionen correctamente, permitiendo que el tráfico de bridge pase por iptables?
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) net.bridge.bridge-nf-call-iptables**

**Explicación:**
`net.bridge.bridge-nf-call-iptables` configura el tráfico de red bridged para que pase por las reglas de iptables. Esta configuración es esencial para que los plugins CNI de Kubernetes (Calico, Flannel, etc.) apliquen correctamente las políticas de red y el enrutamiento de servicios. Para habilitar esta configuración, primero debes cargar el módulo del kernel `br_netfilter`.
</details>

10. En la gestión de paquetes, ¿qué comando se usa en Ubuntu/Debian para evitar actualizaciones automáticas de los componentes de Kubernetes?
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) apt-mark hold**

**Explicación:**
`apt-mark hold` fija paquetes específicos para evitar actualizaciones automáticas. En los clústeres de Kubernetes, la compatibilidad de versiones de kubelet, kubeadm y kubectl es importante, por lo que se recomienda fijar las versiones con el comando `sudo apt-mark hold kubelet kubeadm kubectl`. En RHEL/CentOS, usa el comando `yum versionlock`.
</details>

## Short Answer Questions

11. ¿Cómo se llama un proceso cuando ha terminado, pero su proceso padre no ha comprobado su estado?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Proceso zombie**

**Explicación:**
Un proceso zombie es un proceso que ha completado su ejecución pero permanece en la tabla de procesos porque el proceso padre no ha comprobado su estado de salida mediante la llamada al sistema `wait()`. Los procesos zombie casi no usan recursos, pero si se acumulan muchos, la tabla de procesos puede llenarse e impedir la creación de nuevos procesos.
</details>

12. ¿Cuál es el nombre del namespace de Linux que aísla el stack de red de un proceso?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Network namespace**

**Explicación:**
El network namespace aísla el stack de red (interfaces de red, tablas de enrutamiento, reglas de firewall, sockets, etc.). Esto permite que cada contenedor tenga su propio entorno de red y opere de forma independiente del sistema host o de las redes de otros contenedores.
</details>

13. ¿Cuál es el nombre de la característica de seguridad de Linux que restringe las llamadas al sistema que puede usar un proceso?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: seccomp (Secure Computing Mode)**

**Explicación:**
seccomp es una característica de seguridad del kernel de Linux que restringe las llamadas al sistema que puede usar un proceso. Los runtimes de contenedores usan filtros seccomp para restringir las llamadas al sistema que los contenedores pueden realizar, lo que mejora la seguridad.
</details>

14. ¿Cómo se llama cuando los privilegios root tradicionales en Linux se dividen en unidades de privilegio más pequeñas?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Capabilities**

**Explicación:**
Linux Capabilities divide los privilegios root tradicionales en unidades de privilegio más pequeñas. Esto permite conceder solo los privilegios mínimos necesarios a un proceso, lo que mejora la seguridad. Por ejemplo, para cambiar la configuración de red, solo se necesita la capability `CAP_NET_ADMIN`, no privilegios root completos.
</details>

15. ¿Cómo se llama el par de interfaces de red entre un host y un contenedor en redes de contenedores?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: veth pair**

**Explicación:**
Un veth pair es un par de interfaces ethernet virtuales donde un extremo está dentro del contenedor y el otro extremo está en el namespace de red del host. Esto habilita la comunicación de red entre el contenedor y el host. Normalmente, la interfaz veth del lado del host se conecta a un bridge (por ejemplo, docker0) para habilitar la comunicación entre múltiples contenedores.
</details>

16. ¿Qué comando se usa para comprobar y limitar el número máximo de descriptores de archivo que un proceso puede abrir?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: ulimit**

**Explicación:**
ulimit es un comando para comprobar y establecer límites de recursos para usuarios y procesos. `ulimit -n` comprueba el número de descriptores de archivo que se pueden abrir y `ulimit -n 65536` cambia el límite. En los nodos de Kubernetes se necesitan muchos handles de archivo, por lo que es común establecer valores altos de forma permanente en `/etc/security/limits.conf`.
</details>

17. ¿Cuál es el nombre de la herramienta del sistema de logging de systemd usada para la gestión unificada de logs de servicios?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: journald (o systemd-journald)**

**Explicación:**
journald es el sistema de logging unificado de systemd que recopila y almacena logs del sistema y de servicios. Los logs pueden consultarse con el comando `journalctl`, usando la opción `-u` para ver logs de un servicio específico y la opción `-f` para ver logs en tiempo real. En los nodos de Kubernetes, los logs de kubelet pueden comprobarse con `journalctl -u kubelet`.
</details>

18. ¿Cuál es el nombre del daemon moderno usado para sincronizar la hora del sistema con servidores NTP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: chronyd (o chrony)**

**Explicación:**
chronyd es un cliente/servidor NTP moderno que sincroniza la hora más rápido que el ntpd tradicional. El comando `chronyc tracking` comprueba el estado de sincronización y `chronyc sources` muestra la lista de servidores NTP. En los clústeres de Kubernetes, todos los nodos deben tener la hora sincronizada con precisión para que la autenticación, el logging, etc. funcionen correctamente.
</details>

19. ¿Cuál es la ruta del archivo donde se almacenan las configuraciones de resolución de nombres DNS en Linux?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: /etc/resolv.conf**

**Explicación:**
`/etc/resolv.conf` es el archivo que almacena la configuración de resolución de nombres DNS y define nameservers, dominios de búsqueda, opciones, etc. En entornos Kubernetes, este archivo desempeña un papel importante junto con CoreDNS y también afecta la configuración DNS de los Pods. En sistemas modernos, systemd-resolved puede gestionar dinámicamente este archivo.
</details>

## Hands-on Questions

20. Escribe los comandos para crear un nuevo network namespace y listar las interfaces de red dentro de ese namespace.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Create a new network namespace
ip netns add mynetns

# List network interfaces within that namespace
ip netns exec mynetns ip link list
```

**Explicación:**
El primer comando crea un nuevo network namespace llamado "mynetns". El segundo comando ejecuta el comando `ip link list` dentro de ese namespace para listar las interfaces de red. Un network namespace recién creado contiene únicamente la interfaz loopback (lo) de forma predeterminada, y esta interfaz está inicialmente en estado down.
</details>

21. Escribe el comando para comprobar la información de cgroup de un proceso específico (PID: 1234).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
cat /proc/1234/cgroup
```

**Explicación:**
En Linux, puedes comprobar la información de cgroup de un proceso específico mediante el archivo `/proc/<PID>/cgroup`. Este archivo muestra todas las jerarquías de cgroup y la información de controladores a los que pertenece el proceso. Como alternativa, puedes usar el comando `systemd-cgls` para ver la jerarquía de cgroup en formato de árbol.
</details>

22. Escribe un comando chmod para dar al archivo "example.sh" permisos de lectura, escritura y ejecución para el propietario, permisos de lectura y ejecución para el grupo, y permiso de solo lectura para otros usuarios.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
chmod 754 example.sh
```

o

```bash
chmod u=rwx,g=rx,o=r example.sh
```

**Explicación:**
El primer método usa notación numérica:
  - 7(rwx): concede permisos de lectura(4), escritura(2) y ejecución(1) al propietario
  - 5(r-x): concede permisos de lectura(4) y ejecución(1) al grupo
  - 4(r--): concede solo permiso de lectura(4) a otros usuarios

El segundo método usa notación simbólica para establecer los mismos permisos.
</details>

23. Escribe el comando para comprobar el uso actual de memoria del sistema.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
free -h
```

**Explicación:**
El comando `free` muestra el uso de memoria del sistema. La opción `-h` muestra la salida en formato legible para humanos (por ejemplo, GB, MB). La salida incluye memoria total, memoria usada, memoria libre, memoria usada para buffers/cache, información de memoria swap, etc.
</details>

24. Escribe el comando para encontrar el proceso que se ejecuta en un puerto específico (por ejemplo, 8080).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
lsof -i :8080
```

o

```bash
netstat -tulpn | grep :8080
```

o

```bash
ss -tulpn | grep :8080
```

**Explicación:**
  - `lsof -i :8080`: muestra los procesos que usan el puerto 8080.
  - `netstat -tulpn | grep :8080`: encuentra entradas que usan el puerto 8080 en la lista de conexiones TCP/UDP. Usa las opciones `-t`(TCP), `-u`(UDP), `-l`(listening), `-p`(información del proceso), `-n`(mostrar numéricamente).
  - `ss -tulpn | grep :8080`: reemplazo moderno de `netstat` que proporciona la misma información.
</details>

25. Escribe los comandos para configurar los módulos del kernel br_netfilter y overlay para que se carguen automáticamente en el arranque, requeridos para nodos de Kubernetes.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
EOF

# Load immediately in current session
sudo modprobe overlay
sudo modprobe br_netfilter
```

**Explicación:**
Crear un archivo `.conf` en el directorio `/etc/modules-load.d/` hace que el servicio systemd-modules-load cargue automáticamente esos módulos en el arranque. El módulo `overlay` soporta el sistema de archivos OverlayFS usado para capas de imagen de contenedores, y el módulo `br_netfilter` permite que el tráfico de bridge pase por iptables, lo cual es esencial para las redes de Kubernetes.
</details>

26. Escribe un comando journalctl para ver logs en tiempo real del servicio kubelet filtrando solo mensajes de nivel error y superior.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
journalctl -u kubelet -f -p err
```

o

```bash
journalctl -u kubelet -f -p warning
```

**Explicación:**
  - `-u kubelet`: muestra solo logs del servicio kubelet
  - `-f`: transmite nuevos logs en tiempo real (similar a tail -f)
  - `-p err`: muestra solo logs de nivel error y superior (err, crit, alert, emerg)
  - `-p warning`: muestra logs de nivel warning y superior (warning, err, crit, alert, emerg)

Los niveles de prioridad de journalctl van de 0(emerg) a 7(debug), y se muestran los mensajes del nivel especificado y de mayor prioridad.
</details>

27. Escribe los comandos para comprobar la zona horaria actual del sistema y cambiarla a Asia/Seoul.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Check current timezone
timedatectl

# Change timezone
sudo timedatectl set-timezone Asia/Seoul
```

**Explicación:**
El comando `timedatectl` es la utilidad de gestión de tiempo de systemd que puede establecer y comprobar la hora, fecha y zona horaria del sistema. El comando `timedatectl list-timezones` muestra las zonas horarias disponibles. En clústeres de Kubernetes, ayuda con el análisis de logs y la resolución de problemas si todos los nodos usan la misma zona horaria o usan UTC.
</details>

28. Escribe la configuración que se debe añadir a /etc/security/limits.conf para establecer permanentemente el límite de descriptores de archivo en 65536.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
*               soft    nofile          65536
*               hard    nofile          65536
```

o para usuarios/servicios específicos:
```bash
root            soft    nofile          65536
root            hard    nofile          65536
```

**Explicación:**
`/etc/security/limits.conf` es un archivo de configuración usado por PAM (Pluggable Authentication Modules) para definir límites de recursos por usuario. `*` significa todos los usuarios, `soft` es el límite predeterminado y `hard` es el límite máximo. `nofile` especifica el número de descriptores de archivo que se pueden abrir. En los nodos de Kubernetes se necesitan muchas conexiones de red y handles de archivo, por lo que este valor debe establecerse alto.
</details>

## Advanced Questions

29. Explica las tres tecnologías principales usadas por el kernel de Linux para el aislamiento de contenedores y describe qué tipo de aislamiento proporciona cada una.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. **Namespaces**:
  - Los namespaces aíslan grupos de procesos para que cada grupo pueda ver los recursos del sistema de forma independiente.
  - Tipos principales de namespace:
  - PID namespace: aislamiento de ID de procesos
  - Network namespace: aislamiento del stack de red (interfaces, tablas de enrutamiento, firewall, etc.)
  - Mount namespace: aislamiento de puntos de montaje del sistema de archivos
  - UTS namespace: aislamiento de hostname y nombre de dominio
  - IPC namespace: aislamiento de recursos de comunicación entre procesos
  - User namespace: aislamiento de ID de usuarios y grupos
  - cgroup namespace: aislamiento del directorio raíz de cgroup

2. **cgroups (Control Groups)**:
  - cgroups es una característica que limita y aísla el uso de recursos de grupos de procesos.
  - Aislamiento proporcionado:
  - Limitación de tiempo de CPU
  - Limitación de uso de memoria
  - Limitación de ancho de banda de E/S de bloques
  - Limitación de ancho de banda de red
  - Control de acceso a dispositivos

3. **Capabilities**:
  - Linux capabilities divide los privilegios root tradicionales en unidades de privilegio más pequeñas.
  - Aislamiento proporcionado:
  - Aislamiento de privilegios: conceder solo los privilegios mínimos necesarios a los contenedores
  - Mejora de seguridad: reducir los riesgos de seguridad eliminando privilegios innecesarios
  - Ejemplos: `CAP_NET_ADMIN` (cambios de configuración de red), `CAP_SYS_ADMIN` (tareas de administración del sistema), etc.

Estas tres tecnologías se combinan para permitir que los contenedores se ejecuten en un entorno aislado del sistema host y de otros contenedores, con uso limitado de recursos y seguridad mejorada.
</details>

30. Explica cómo OverlayFS gestiona las capas de imagen de contenedores y describe la relación entre capas de solo lectura y capas escribibles.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

OverlayFS es un sistema de archivos de montaje union que superpone múltiples directorios para presentarlos como un único directorio. En la gestión de capas de imagen de contenedores, OverlayFS funciona de la siguiente manera:

1. **Estructura de capas**:
  - **Directorio Lower (capas de solo lectura)**: las capas de la imagen base; pueden existir varias. Contiene el sistema de archivos base y el código de la aplicación.
  - **Directorio Upper (capa escribible)**: la capa escribible creada cuando se ejecuta el contenedor. Todos los cambios realizados dentro del contenedor se almacenan en esta capa.
  - **Directorio Work**: un directorio temporal para operaciones internas de OverlayFS.
  - **Directorio Merged**: la vista final donde se integran todas las capas; el sistema de archivos que el contenedor ve realmente.

2. **Relación entre capas de solo lectura y escribibles**:
  - **Lectura de archivos**: al leer un archivo, OverlayFS primero busca el archivo en el directorio Upper (capa escribible). Si no se encuentra, busca secuencialmente en el directorio Lower (capas de solo lectura).
  - **Escritura de archivos**: al modificar un archivo, se usa Copy-on-Write (CoW). Al intentar modificar un archivo en una capa de solo lectura, el archivo primero se copia a la capa escribible y luego se modifica. El archivo original permanece sin cambios.
  - **Eliminación de archivos**: al intentar eliminar un archivo en una capa de solo lectura, el archivo no se elimina realmente; en su lugar, se crea un archivo "whiteout" en la capa escribible para que parezca eliminado.

3. **Beneficios**:
  - **Eficiencia de espacio**: múltiples contenedores comparten las mismas capas de imagen base, lo que ahorra espacio en disco.
  - **Tiempo de inicio rápido**: al iniciar un nuevo contenedor, solo se debe crear la capa escribible, no copiar todo el sistema de archivos.
  - **Gestión de versiones de imágenes**: las imágenes pueden actualizarse añadiendo nuevas capas a la imagen base.

De esta manera, OverlayFS gestiona eficientemente las capas de imagen de contenedores, permitiendo que los contenedores tengan sistemas de archivos independientes mientras comparten imágenes base.
</details>

31. Explica cómo las Linux capabilities afectan la seguridad de contenedores y por qué es importante conceder solo las capabilities mínimas necesarias a los contenedores.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Linux Capabilities y seguridad de contenedores:**

Linux capabilities divide los privilegios root tradicionales en unidades de privilegio más pequeñas, lo que afecta la seguridad de contenedores de las siguientes maneras:

1. **Granularidad de privilegios**:
  - Tradicionalmente, los procesos solo se distinguían como root (UID 0) o no root.
  - Capabilities permite dividir los privilegios root en múltiples privilegios individuales, permitiendo conceder a los procesos solo los privilegios específicos necesarios.
  - Ejemplo: para cambiar la configuración de red, solo se necesita la capability `CAP_NET_ADMIN` en lugar de privilegios root completos.

2. **Mejora de seguridad de contenedores**:
  - Los runtimes de contenedores conceden de forma predeterminada solo un conjunto limitado de capabilities a los contenedores.
  - Esto limita el impacto que los contenedores pueden tener sobre el sistema host.
  - Incluso los procesos que se ejecutan como root dentro de contenedores tienen capabilities limitadas, lo que reduce los riesgos de seguridad.

3. **Capabilities clave relacionadas con contenedores**:
  - `CAP_NET_ADMIN`: cambios de configuración de red
  - `CAP_SYS_ADMIN`: tareas de administración del sistema (muy poderosa)
  - `CAP_CHOWN`: cambios de propiedad de archivos
  - `CAP_DAC_OVERRIDE`: omitir permisos de archivos
  - `CAP_SETUID`: cambios de UID
  - `CAP_SETGID`: cambios de GID

**Importancia del principio de mínimo privilegio:**

Es importante conceder solo las capabilities mínimas necesarias a los contenedores por las siguientes razones:

1. **Superficie de ataque reducida**:
  - Eliminar capabilities innecesarias reduce los vectores que los atacantes pueden explotar.
  - Incluso si un contenedor se ve comprometido, las acciones que un atacante puede realizar quedan limitadas.

2. **Prevención de escape de contenedores**:
  - Capabilities poderosas (especialmente `CAP_SYS_ADMIN`) pueden permitir el escape de contenedores (acceder al host desde un contenedor).
  - Restringir estas capabilities reduce significativamente el riesgo de escape de contenedores.

3. **Estrategia de defensa en profundidad**:
  - El principio de mínimo privilegio forma parte de una estrategia de seguridad de defensa en profundidad.
  - Usado con otros mecanismos de seguridad (seccomp, AppArmor, SELinux, etc.) proporciona mayor seguridad.

4. **Cumplimiento normativo**:
  - Muchos estándares y regulaciones de seguridad requieren el principio de mínimo privilegio.
  - Conceder solo las capabilities mínimas necesarias a los contenedores ayuda a cumplir estos requisitos.

5. **Aislamiento de problemas**:
  - Conceder capabilities limitadas a los contenedores evita que los problemas en un contenedor se propaguen a otros contenedores o al sistema host.

En entornos de producción, es una buena práctica de seguridad identificar con precisión las capabilities que necesita un contenedor y eliminar todas las demás. Para ello se pueden usar las opciones `--cap-drop`, `--cap-add` de Docker o el campo `securityContext.capabilities` de Kubernetes.
</details>

32. Explica la estructura de un archivo de unidad de servicio systemd y el rol de las secciones principales ([Unit], [Service], [Install]), y escribe un ejemplo básico de archivo de unidad para el servicio kubelet de Kubernetes.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Secciones principales de un archivo de unidad systemd:**

1. **Sección [Unit]**: define metadatos y dependencias de la unidad
   - `Description`: descripción del servicio
   - `Documentation`: URL de documentación
   - `After/Before`: define el orden de inicio
   - `Requires/Wants`: define dependencias

2. **Sección [Service]**: define cómo ejecutar el servicio
   - `Type`: tipo de servicio (simple, forking, oneshot, etc.)
   - `ExecStart`: comando a ejecutar
   - `Restart`: política de reinicio
   - `RestartSec`: tiempo de espera antes de reiniciar

3. **Sección [Install]**: define el comportamiento cuando la unidad está habilitada
   - `WantedBy`: target que quiere esta unidad

**Ejemplo de archivo de unidad del servicio kubelet:**

```ini
[Unit]
Description=kubelet: The Kubernetes Node Agent
Documentation=https://kubernetes.io/docs/
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/kubelet
Restart=always
StartLimitInterval=0
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Explicación:**
Este archivo de unidad define el servicio kubelet. Se inicia después de que la red esté lista (`After=network-online.target`), siempre se reinicia ante fallos (`Restart=always`) e intenta reiniciarse cada 10 segundos (`RestartSec=10`). `WantedBy=multi-user.target` significa que este servicio se inicia cuando el sistema arranca en modo multiusuario.
</details>

33. Explica cómo establecer permanentemente los parámetros sysctl del kernel requeridos para la configuración de nodos de Kubernetes y describe el rol de cada parámetro.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Configuraciones sysctl clave requeridas para Kubernetes y sus roles:**

```bash
# Create /etc/sysctl.d/99-kubernetes.conf file
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
# Enable IP forwarding - essential for packet routing between containers
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Bridge traffic passes through iptables - essential for CNI network policies
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Connection tracking table size (for large clusters)
net.netfilter.nf_conntrack_max = 1000000
EOF

# Apply settings
sudo sysctl --system
```

**Rol de cada parámetro:**

1. **net.ipv4.ip_forward = 1**
   - Permite que el kernel de Linux reenvíe paquetes entre interfaces de red
   - Esencial para la comunicación de Pods con otros Pods o redes externas
   - Las redes de contenedores no funcionarán si está deshabilitado

2. **net.bridge.bridge-nf-call-iptables = 1**
   - Configura el tráfico que pasa por bridges para que esté sujeto a reglas de iptables
   - Esencial para que los servicios de Kubernetes (ClusterIP, NodePort) y NetworkPolicy funcionen correctamente
   - Requerido porque kube-proxy usa iptables para el enrutamiento de servicios

3. **net.ipv6.conf.all.forwarding = 1**
   - Habilita el reenvío de paquetes en entornos IPv6
   - Necesario para clústeres dual-stack

**Orden de aplicación de la configuración:**
1. Primero carga el módulo `br_netfilter`: `modprobe br_netfilter`
2. Crea el archivo de configuración sysctl
3. Aplica todas las configuraciones con `sysctl --system`

Sin estas configuraciones, la red del clúster de Kubernetes no funcionará correctamente, especialmente con problemas en la comunicación Pod-a-Pod y el descubrimiento de servicios.
</details>

34. Explica la estrategia de gestión de logs de Linux usando journald y logrotate, y presenta métodos de configuración para una gestión eficiente de logs en nodos de Kubernetes.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Roles de journald y logrotate:**

**journald (logging basado en systemd):**
- Recopila logs stdout/stderr de servicios systemd
- Se almacena en formato binario y se consulta con journalctl
- Soporta compresión y rotación automática de logs

**logrotate (gestión tradicional de archivos de log):**
- Gestiona la rotación, compresión y eliminación de archivos de log de texto
- Se ejecuta periódicamente mediante una tarea cron

**Configuración de gestión de logs de nodos de Kubernetes:**

**1. Configuración de journald (/etc/systemd/journald.conf):**
```ini
[Journal]
# Store persistently on disk
Storage=persistent

# Maximum disk usage (total /var/log/journal)
SystemMaxUse=2G

# Maximum file size
SystemMaxFileSize=100M

# Minimum free space to maintain
SystemKeepFree=1G

# Maximum retention period
MaxRetentionSec=1month
```

**2. Configuración de logrotate para logs de contenedores:**
```bash
# /etc/logrotate.d/containers
/var/log/containers/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
```

**3. Comandos de limpieza de logs:**
```bash
# journald log cleanup
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete old logs when exceeding 1GB

# Check disk usage
journalctl --disk-usage
```

**Mejores prácticas de gestión de logs de Kubernetes:**

1. **logs de kubelet**: gestionados por journald, almacenados en `/var/log/journal/`
2. **logs de contenedores**: almacenados en `/var/log/containers/`, gestionados por logrotate
3. **logging centralizado**: se recomienda reenviar a sistemas externos usando Fluentd/Fluent Bit

Una gestión adecuada de logs mantiene el equilibrio entre evitar fallos de nodo por agotamiento de espacio en disco y conservar logs para la resolución de problemas.
</details>

---

[Volver a los materiales de aprendizaje](../../basics/01-linux-basics.md) | [Siguiente cuestionario: Operaciones de Linux](./02-linux-advanced-quiz.md)
