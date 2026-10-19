# Cuestionario de fundamentos de Linux

Este cuestionario evalúa tu comprensión de los conceptos fundamentales de Linux que forman la base de Kubernetes y la tecnología de contenedores.

## Preguntas de opción múltiple

1. ¿Cuál de las siguientes NO es una función principal del kernel de Linux?
   - A) Gestión de procesos
   - B) Gestión de memoria
   - C) Proporcionar interfaz de usuario
   - D) Gestión de dispositivos
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Proporcionar interfaz de usuario**

**Explicación:**
El kernel de Linux es el núcleo del sistema operativo y actúa como intermediario entre el hardware y el software. Las funciones principales del kernel incluyen la gestión de procesos, la gestión de memoria, la gestión de dispositivos y proporcionar interfaces de llamadas al sistema. La interfaz de usuario (GUI, CLI) la proporcionan programas separados que se ejecutan en el espacio de usuario y no es responsabilidad del kernel.

</details>

2. ¿Cuál de los siguientes NO es un tipo de namespace (espacio de nombres) de Linux?
   - A) PID namespace
   - B) Network namespace
   - C) Memory namespace
   - D) User namespace
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Memory namespace**

**Explicación:**
Linux tiene namespaces de PID (identificadores de proceso), red, montaje, UTS (hostname), IPC (comunicación entre procesos), usuario, cgroup y tiempo. No existe un namespace de memoria: los espacios de direcciones virtuales de los procesos aíslan la memoria, mientras que los cgroups contabilizan y limitan su uso.
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
cgroups es una función del kernel de Linux que limita y aísla el uso de recursos de grupos de procesos. Puede limitar y supervisar el tiempo de CPU, la memoria y la E/S de bloques; para controlar el ancho de banda de red se necesita integrar tc/eBPF. Es una tecnología fundamental para implementar límites de recursos en contenedores.
</details>

4. En el permiso de archivo "rwxr-xr--", ¿qué permisos corresponden al grupo?
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
  - 3 caracteres del medio (r-x): permisos del grupo: lectura, ejecución
  - Últimos 3 caracteres (r--): permisos de otros usuarios: solo lectura

Por lo tanto, los usuarios del grupo tienen permisos de lectura y ejecución.

</details>

5. ¿Qué sistema de archivos se usa principalmente para implementar las capas de imágenes de contenedores?
   - A) ext4
   - B) XFS
   - C) OverlayFS
   - D) Btrfs

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) OverlayFS**

**Explicación:**
OverlayFS es un sistema de archivos de montaje de unión que superpone varios directorios para presentarlos como un único directorio. Lo usan principalmente runtimes de contenedores como Docker para implementar capas de imagen. Esto permite que la imagen base permanezca en modo de solo lectura mientras se añade una capa escribible para cada contenedor.
</details>

6. Al gestionar servicios con el comando systemctl, ¿qué comando configura un servicio para que se inicie automáticamente al arrancar?
   - A) systemctl start
   - B) systemctl enable
   - C) systemctl restart
   - D) systemctl reload

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) systemctl enable**

**Explicación:**
`systemctl enable` configura un servicio para que se inicie automáticamente cuando el sistema arranca. `start` inicia el servicio inmediatamente, `restart` reinicia el servicio y `reload` solo vuelve a leer el archivo de configuración. En los nodos de Kubernetes, los servicios principales como kubelet y containerd deben tener configurado el inicio automático con `systemctl enable`.
</details>

7. ¿Qué parámetro del kernel es esencial para configurar un clúster de Kubernetes, ya que habilita el reenvío de paquetes IP para la red de contenedores?
   - A) net.ipv4.tcp_syncookies
   - B) net.ipv4.ip_forward
   - C) net.core.somaxconn
   - D) fs.file-max

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) net.ipv4.ip_forward**

**Explicación:**
`net.ipv4.ip_forward` habilita el reenvío de paquetes IP en el kernel de Linux. Establécelo en 1 cuando el nodo deba reenviar paquetes IPv4 entre interfaces; el tráfico de localhost dentro del mismo network namespace no requiere reenvío. En nodos de Kubernetes, habilítalo cuando la topología de red lo necesite. Puedes establecerlo con `sysctl -w net.ipv4.ip_forward=1`.
</details>

8. En un archivo de unidad de systemd, ¿qué directiva se usa para definir que un servicio debe iniciarse después de un servicio específico?
   - A) Requires
   - B) Wants
   - C) After
   - D) Before

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) After**

**Explicación:**
En una unidad de systemd, `After` establece el orden de inicio respecto de otra unidad, pero solo cuando ambas se inician. Si el servicio necesita conectividad de red al arrancar, combina `Wants=network-online.target` con `After=network-online.target` y con la implementación wait-online de la distribución. Esto no supervisa continuamente la disponibilidad de la red. `Requires` define una dependencia fuerte, `Wants` una dependencia débil y `Before` indica que la unidad actual debe iniciarse antes que otra.
</details>

9. ¿Qué parámetro del kernel hace que el tráfico IPv4 puenteado pase por iptables cuando el CNI seleccionado requiere bridge netfilter?
   - A) net.ipv4.ip_forward
   - B) net.bridge.bridge-nf-call-iptables
   - C) net.core.netdev_max_backlog
   - D) net.ipv4.tcp_max_syn_backlog

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) net.bridge.bridge-nf-call-iptables**

**Explicación:**
`net.bridge.bridge-nf-call-iptables` hace que el tráfico IPv4 puenteado pase por las reglas de iptables. La necesidad de esta opción depende del CNI y del plano de datos; no es un requisito universal para redes enrutadas o basadas en eBPF. Para habilitar esta opción, primero carga el módulo del kernel `br_netfilter`.
</details>

10. En la gestión de paquetes, ¿qué comando se usa en Ubuntu/Debian para impedir actualizaciones automáticas de los componentes de Kubernetes?
    - A) apt lock
    - B) apt-mark hold
    - C) apt freeze
    - D) apt pin

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) apt-mark hold**

**Explicación:**
`apt-mark hold` marca paquetes específicos para impedir que se actualicen automáticamente. En clústeres de Kubernetes importa la compatibilidad entre las versiones de kubelet, kubeadm y kubectl; por eso se recomienda fijarlas con `sudo apt-mark hold kubelet kubeadm kubectl`. En sistemas basados en RPM, usa el complemento versionlock de DNF/YUM que esté instalado o exclusiones de repositorio adecuadas para la distribución.
</details>

## Preguntas de respuesta breve

11. ¿Cómo se llama un proceso cuando ha terminado, pero su proceso padre no ha comprobado su estado?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Proceso zombi**

**Explicación:**
Un proceso zombi es un proceso que ha completado su ejecución, pero permanece en la tabla de procesos porque el proceso padre no ha comprobado su estado de salida mediante la llamada al sistema `wait()`. Los procesos zombis casi no usan recursos, pero si se acumulan muchos, la tabla de procesos puede llenarse e impedir la creación de nuevos procesos.
</details>

12. ¿Cómo se llama el namespace de Linux que aísla la pila de red de un proceso?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Network Namespace**

**Explicación:**
El network namespace aísla la pila de red (interfaces de red, tablas de enrutamiento, reglas de firewall, sockets, etc.). Esto permite que cada contenedor tenga su propio entorno de red y opere de forma independiente del sistema host o de las redes de otros contenedores.
</details>

13. ¿Cómo se llama la característica de seguridad de Linux que restringe las llamadas al sistema que puede usar un proceso?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: seccomp (Secure Computing Mode)**

**Explicación:**
seccomp es una característica de seguridad del kernel de Linux que restringe las llamadas al sistema que puede usar un proceso. Los runtimes de contenedores usan filtros seccomp para restringir las llamadas al sistema que pueden realizar los contenedores, mejorando así la seguridad.
</details>

14. ¿Cómo se llama la división de los privilegios root tradicionales en Linux en unidades de privilegio más pequeñas?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Capabilities**

**Explicación:**
Las Linux Capabilities dividen los privilegios root tradicionales en unidades de privilegio más pequeñas. Esto permite conceder a un proceso solo los privilegios mínimos necesarios, mejorando la seguridad. Por ejemplo, para cambiar la configuración de red, solo se necesita la capability `CAP_NET_ADMIN`, no privilegios root completos.
</details>

15. ¿Cómo se llama el par de interfaces de red entre un host y un contenedor en redes de contenedores?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: veth pair**

**Explicación:**
Un veth pair es un par de interfaces ethernet virtuales donde un extremo está dentro del contenedor y el otro extremo está en el namespace de red del host. Esto permite la comunicación de red entre el contenedor y el host. Normalmente, la interfaz veth del lado del host se conecta a un bridge (por ejemplo, docker0) para habilitar la comunicación entre varios contenedores.
</details>

16. ¿Qué comando se usa para comprobar y limitar el número máximo de descriptores de archivo que puede abrir un proceso?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: ulimit**

**Explicación:**
`ulimit` permite consultar y establecer límites de recursos. `ulimit -n` muestra el límite de descriptores de archivo y `ulimit -n 65536` lo cambia para el shell actual y sus procesos hijos futuros. Los límites de PAM se aplican a las nuevas sesiones de inicio de sesión; para servicios del sistema como kubelet, configura `LimitNOFILE` en systemd.
</details>

17. ¿Cómo se llama la herramienta del sistema de logging de systemd usada para la gestión unificada de logs de servicios?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: journald (o systemd-journald)**

**Explicación:**
journald es el sistema de logging unificado de systemd que recopila y almacena logs del sistema y de servicios. Los logs se pueden consultar con el comando `journalctl`, usando la opción `-u` para ver logs de servicios específicos y la opción `-f` para ver logs en tiempo real. En los nodos de Kubernetes, los logs de kubelet pueden comprobarse con `journalctl -u kubelet`.
</details>

18. ¿Cómo se llama el daemon moderno usado para sincronizar la hora del sistema con servidores NTP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: chronyd (o chrony)**

**Explicación:**
`chronyd` es un cliente/servidor NTP. La convergencia depende de la red, la calidad de las fuentes y la configuración. `chronyc tracking` consulta el estado de sincronización y `chronyc sources` muestra la lista de fuentes NTP. En clústeres de Kubernetes, todos los nodos deben mantener la hora sincronizada con precisión para que funcionen correctamente la autenticación, los registros y otros componentes.
</details>

19. ¿Cuál es la ruta del archivo donde se almacenan las configuraciones de resolución de nombres DNS en Linux?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: /etc/resolv.conf**

**Explicación:**
`/etc/resolv.conf` es el archivo que almacena la configuración de resolución de nombres DNS y define nameservers, dominios de búsqueda, opciones, etc. En entornos de Kubernetes, este archivo cumple un papel importante junto con CoreDNS y también afecta a la configuración DNS de Pod. En sistemas modernos, systemd-resolved puede gestionar dinámicamente este archivo.
</details>

## Ejercicios prácticos

20. Escribe los comandos para crear un nuevo network namespace y listar las interfaces de red dentro de ese namespace.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# Create a new network namespace
sudo ip netns add mynetns

# List network interfaces within that namespace
sudo ip netns exec mynetns ip link list
# After the exercise, when no processes use it:
sudo ip netns delete mynetns
```

**Explicación:**
El primer comando crea un nuevo network namespace llamado "mynetns". El segundo comando ejecuta el comando `ip link list` dentro de ese namespace para listar las interfaces de red. Un network namespace recién creado contiene solo la interfaz loopback (lo) de forma predeterminada, y esta interfaz inicialmente está en estado down.
</details>

21. Escribe el comando para comprobar la información de cgroup de un proceso específico (PID: 1234).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
cat /proc/1234/cgroup
```

**Explicación:**
En Linux, puedes comprobar la información de cgroup de un proceso específico mediante el archivo `/proc/<PID>/cgroup`. Este archivo muestra todas las jerarquías de cgroup y la información de controladores a las que pertenece el proceso. Como alternativa, puedes usar el comando `systemd-cgls` para ver la jerarquía de cgroups en formato de árbol.
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
  - 7(rwx): Concede permisos de lectura(4), escritura(2) y ejecución(1) al propietario
  - 5(r-x): Concede permisos de lectura(4) y ejecución(1) al grupo
  - 4(r--): Concede solo permiso de lectura(4) a otros usuarios

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
El comando `free` muestra el uso de memoria del sistema. La opción `-h` genera la salida en un formato legible para humanos (por ejemplo, GB, MB). La salida incluye memoria total, memoria usada, memoria libre, memoria usada para buffers/cache, información de memoria swap, etc.
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
  - `lsof -i :8080`: Muestra los procesos que usan el puerto 8080.
  - `netstat -tulpn | grep :8080`: Encuentra entradas que usan el puerto 8080 en la lista de conexiones TCP/UDP. Usa las opciones `-t`(TCP), `-u`(UDP), `-l`(listening), `-p`(información de proceso), `-n`(mostrar numéricamente).
  - `ss -tulpn | grep :8080`: Un reemplazo moderno de `netstat` que proporciona la misma información.
</details>

25. Escribe los comandos para configurar los módulos del kernel `br_netfilter` y `overlay` para que se carguen automáticamente al arrancar, cuando los requiera el runtime o el CNI seleccionado.

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
Crear un archivo `.conf` en `/etc/modules-load.d/` hace que `systemd-modules-load` cargue esos módulos al arrancar. `overlay` admite OverlayFS, que se usa para las capas de imágenes de contenedores. `br_netfilter` permite que el tráfico puenteado pase por iptables cuando la configuración del CNI seleccionado lo requiere.
</details>

26. Escribe un comando `journalctl` para seguir en tiempo real los registros del servicio kubelet y filtrar los mensajes de nivel error y más graves.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
journalctl -u kubelet -f -p err
```

`-p warning` también incluye advertencias, por lo que no cumple el requisito de mostrar solo mensajes de nivel error y más graves.

**Explicación:**
  - `-u kubelet`: muestra solo los registros del servicio kubelet
  - `-f`: sigue los mensajes nuevos en tiempo real, como `tail -f`
  - `-p err`: muestra mensajes de nivel error y más graves (`err`, `crit`, `alert`, `emerg`)

Los niveles de prioridad de `journalctl` van de 0 (`emerg`) a 7 (`debug`); se muestran los mensajes del nivel indicado y de mayor prioridad.
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
El comando `timedatectl` es la utilidad de gestión de tiempo de systemd que puede establecer y comprobar la hora, la fecha y la zona horaria del sistema. El comando `timedatectl list-timezones` muestra las zonas horarias disponibles. En clústeres de Kubernetes, ayuda con el análisis de logs y la resolución de problemas si todos los nodos usan la misma zona horaria o usan UTC.
</details>

28. Escribe las líneas que se deben añadir a `/etc/security/limits.conf` para establecer el límite de descriptores de archivo en 65536.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```text
*               soft    nofile          65536
*               hard    nofile          65536
```

o para un usuario que inicia sesión mediante PAM (no para un servicio systemd):
```text
root            soft    nofile          65536
root            hard    nofile          65536
```

**Explicación:**
`/etc/security/limits.conf` es un archivo de PAM (Pluggable Authentication Modules) para definir límites de recursos por usuario. `*` coincide con usuarios ordinarios, pero no incluye a `root`, que necesita una entrada explícita. `soft` es el límite aplicado por defecto y `hard` el máximo; `nofile` indica el número de descriptores que se pueden abrir. Elige límites según las necesidades de la carga. PAM no cambia los procesos en ejecución ni los servicios systemd del sistema; para estos últimos configura `LimitNOFILE` en una unidad complementaria del servicio.
</details>

## Preguntas avanzadas

29. Explica las tres tecnologías principales usadas por el kernel de Linux para el aislamiento de contenedores y describe qué tipo de aislamiento proporciona cada una.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

1. **Namespaces**:
  - Los namespaces aíslan grupos de procesos para que cada grupo pueda ver los recursos del sistema de forma independiente.
  - Tipos principales de namespace:
  - PID namespace: aislamiento de ID de proceso
  - Network namespace: aislamiento de la pila de red (interfaces, tablas de enrutamiento, firewall, etc.)
  - Mount namespace: aislamiento de puntos de montaje del sistema de archivos
  - UTS namespace: aislamiento de hostname y nombre de dominio
  - IPC namespace: aislamiento de recursos de comunicación entre procesos
  - User namespace: aislamiento de ID de usuario y grupo
  - cgroup namespace: aislamiento del directorio raíz de cgroup

2. **cgroups (Control Groups)**:
  - cgroups es una característica que limita y aísla el uso de recursos de grupos de procesos.
  - Aislamiento proporcionado:
  - Limitación de tiempo de CPU
  - Limitación de uso de memoria
  - Limitación de ancho de banda de E/S de bloques
  - Clasificación del tráfico de red integrada con `tc`/eBPF
  - Control de acceso a dispositivos

3. **Capabilities**:
  - Las Linux capabilities dividen los privilegios root tradicionales en unidades de privilegio más pequeñas.
  - Efecto en la seguridad:
  - Mínimo privilegio: concede a los contenedores solo los privilegios necesarios
  - Reducción de riesgos: elimina privilegios innecesarios
  - Ejemplos: `CAP_NET_ADMIN` (cambios de configuración de red), `CAP_SYS_ADMIN` (tareas de administración del sistema), etc.

Estas tres tecnologías se combinan para permitir que los contenedores se ejecuten en un entorno aislado del sistema host y de otros contenedores, con uso de recursos limitado y seguridad mejorada.
</details>

30. Explica cómo OverlayFS gestiona las capas de imágenes de contenedores y describe la relación entre capas de solo lectura y capas escribibles.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

OverlayFS es un sistema de archivos de montaje de unión que superpone varios directorios para presentarlos como un único directorio. En la gestión de capas de imágenes de contenedores, OverlayFS funciona de la siguiente manera:

1. **Estructura de capas**:
  - **Directorio Lower (capas de solo lectura)**: Las capas de la imagen base; pueden existir varias. Contiene el sistema de archivos base y el código de la aplicación.
  - **Directorio Upper (capa escribible)**: La capa escribible creada cuando se ejecuta el contenedor. Todos los cambios realizados dentro del contenedor se almacenan en esta capa.
  - **Directorio Work**: Un directorio temporal para operaciones internas de OverlayFS.
  - **Directorio Merged**: La vista final donde se integran todas las capas; el sistema de archivos que el contenedor ve realmente.

2. **Relación entre capas de solo lectura y escribibles**:
  - **Lectura de archivos**: Al leer un archivo, OverlayFS busca primero el archivo en el directorio Upper (capa escribible). Si no lo encuentra, busca secuencialmente en el directorio Lower (capas de solo lectura).
  - **Escritura de archivos**: Al modificar un archivo, se usa Copy-on-Write (CoW). Cuando se intenta modificar un archivo en una capa de solo lectura, primero se copia el archivo a la capa escribible y luego se modifica. El archivo original permanece sin cambios.
  - **Eliminación de archivos**: Cuando se intenta eliminar un archivo en una capa de solo lectura, el archivo no se elimina realmente; en su lugar, se crea un archivo "whiteout" en la capa escribible para hacer que parezca eliminado.

3. **Beneficios**:
  - **Eficiencia de espacio**: Varios contenedores comparten las mismas capas de imagen base, ahorrando espacio en disco.
  - **Tiempo de inicio rápido**: Al iniciar un nuevo contenedor, solo se necesita crear la capa escribible, no copiar todo el sistema de archivos.
  - **Gestión de versiones de imágenes**: Las imágenes pueden actualizarse añadiendo nuevas capas a la imagen base.

De esta manera, OverlayFS gestiona eficientemente las capas de imágenes de contenedores, permitiendo que los contenedores tengan sistemas de archivos independientes mientras comparten imágenes base.
</details>

31. Explica cómo las Linux capabilities afectan a la seguridad de contenedores y por qué es importante conceder solo las capabilities mínimas necesarias a los contenedores.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Linux Capabilities y seguridad de contenedores:**

Las Linux capabilities dividen los privilegios root tradicionales en unidades de privilegio más pequeñas, afectando a la seguridad de contenedores de las siguientes maneras:

1. **Granularidad de privilegios**:
  - Tradicionalmente, los procesos solo se distinguían como root (UID 0) o no root.
  - Las capabilities permiten dividir los privilegios root en varios privilegios individuales, permitiendo conceder a los procesos solo privilegios específicos necesarios.
  - Ejemplo: Para cambiar la configuración de red, solo se necesita la capability `CAP_NET_ADMIN` en lugar de privilegios root completos.

2. **Mejora de la seguridad de contenedores**:
  - Los runtimes de contenedores conceden de forma predeterminada solo un conjunto limitado de capabilities a los contenedores.
  - Esto limita el impacto que los contenedores pueden tener en el sistema host.
  - Incluso los procesos que se ejecutan como root dentro de los contenedores tienen capabilities limitadas, lo que reduce los riesgos de seguridad.

3. **Capabilities clave relacionadas con contenedores**:
  - `CAP_NET_ADMIN`: Cambios de configuración de red
  - `CAP_SYS_ADMIN`: Tareas de administración del sistema (muy potente)
  - `CAP_CHOWN`: Cambios de propiedad de archivos
  - `CAP_DAC_OVERRIDE`: Omisión de permisos de archivo
  - `CAP_SETUID`: Cambios de UID
  - `CAP_SETGID`: Cambios de GID

**Importancia del principio de mínimo privilegio:**

Es importante conceder solo las capabilities mínimas necesarias a los contenedores por las siguientes razones:

1. **Superficie de ataque reducida**:
  - Eliminar capabilities innecesarias reduce los vectores que los atacantes pueden explotar.
  - Incluso si un contenedor se ve comprometido, las acciones que un atacante puede realizar están limitadas.

2. **Prevención de escape de contenedores**:
  - Las capabilities potentes (especialmente `CAP_SYS_ADMIN`) pueden permitir el escape de contenedores (acceder al host desde un contenedor).
  - Restringir estas capabilities reduce significativamente el riesgo de escape de contenedores.

3. **Estrategia de defensa en profundidad**:
  - El principio de mínimo privilegio forma parte de la estrategia de seguridad de defensa en profundidad.
  - Usado con otros mecanismos de seguridad (seccomp, AppArmor, SELinux, etc.) proporciona una seguridad más fuerte.

4. **Cumplimiento normativo**:
  - Muchos estándares y regulaciones de seguridad exigen el principio de mínimo privilegio.
  - Conceder solo las capabilities mínimas necesarias a los contenedores ayuda a cumplir estos requisitos.

5. **Aislamiento de problemas**:
  - Conceder capabilities limitadas a los contenedores evita que los problemas de un contenedor se propaguen a otros contenedores o al sistema host.

En entornos de producción, es una buena práctica de seguridad identificar con precisión las capabilities que necesita un contenedor y eliminar todas las demás. Para ello se pueden usar las opciones `--cap-drop`, `--cap-add` de Docker o el campo `securityContext.capabilities` de Kubernetes.
</details>

32. Explica la estructura de una unidad de servicio de systemd y la función de sus secciones principales ([Unit], [Service], [Install]). Escribe una unidad básica para un servicio de formación y explica por qué deben conservarse la unidad y las unidades complementarias empaquetadas de kubelet.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Secciones principales de una unidad de systemd:**

1. **Sección [Unit]**: define los metadatos y las dependencias de la unidad.
   - `Description`: descripción del servicio
   - `Documentation`: URL de documentación
   - `After/Before`: orden de inicio
   - `Requires/Wants`: dependencias

2. **Sección [Service]**: define cómo se ejecuta el servicio.
   - `Type`: tipo de servicio (`simple`, `forking`, `oneshot`, etc.)
   - `ExecStart`: comando que se ejecutará
   - `Restart`: política de reinicio
   - `RestartSec`: espera antes del reinicio

3. **Sección [Install]**: define el comportamiento al habilitar la unidad.
   - `WantedBy`: destino que incorpora esta unidad

**Ejemplo de unidad para el servicio de formación `linux-basics-demo.service`:**

```ini
[Unit]
Description=Linux basics training service
Documentation=man:systemd.service(5)
Wants=network-online.target
After=network-online.target

[Service]
ExecStart=/usr/bin/sleep infinity
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Explicación:**
Esta unidad ejecuta un proceso inocuo para la formación. Usa `systemctl cat kubelet` para inspeccionar la unidad de la distribución y las unidades complementarias creadas por kubeadm; no las sustituyas por este ejemplo. El servicio queda ordenado después de `network-online.target` cuando ambas unidades se activan. Se reinicia si falla (`Restart=on-failure`) y vuelve a intentarlo después de 10 segundos (`RestartSec=10`). `WantedBy=multi-user.target` hace que se inicie al arrancar el sistema en modo multiusuario.
</details>

33. Explica cómo establecer de forma persistente parámetros sysctl del kernel para configurar nodos de Kubernetes y la función de cada parámetro.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Configuración de sysctl y función de sus parámetros:**

```bash
# Create /etc/sysctl.d/99-kubernetes.conf file
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
# Enable IP forwarding - essential for packet routing between containers
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Bridge traffic passes through iptables - only if the CNI uses bridge netfilter
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Size conntrack separately from measured workload/memory requirements.
EOF

# Apply settings
sudo sysctl --system
```

**Función de cada parámetro:**

1. **`net.ipv4.ip_forward = 1`**
   - Permite que el kernel de Linux reenvíe paquetes entre interfaces de red.
   - Se necesita cuando el nodo debe reenviar tráfico IPv4 entre Pods u otras redes.

2. **`net.bridge.bridge-nf-call-iptables = 1`**
   - Hace que el tráfico puenteado se procese con reglas de iptables.
   - Solo se necesita para implementaciones que dependen de bridge netfilter. `kube-proxy` puede usar iptables o nftables, y otro plano de datos puede sustituir a `kube-proxy`.

3. **`net.ipv6.conf.all.forwarding = 1`**
   - Habilita el reenvío de paquetes en entornos IPv6.
   - Se necesita para clústeres dual-stack cuando la topología lo requiere.

**Orden para aplicar la configuración:**
1. Carga `br_netfilter` si lo requiere el CNI seleccionado.
2. Crea el archivo de configuración sysctl.
3. Aplica los ajustes con `sysctl --system`.

Aplica solo los ajustes necesarios para las familias IP y el CNI que uses, dentro de un laboratorio aislado o mediante un proceso revisado de configuración de nodos.
</details>

34. Explica la estrategia de gestión de registros de Linux con journald y logrotate, y presenta métodos de configuración para administrar eficazmente los registros en nodos de Kubernetes.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Funciones de journald y logrotate:**

**journald (registro basado en systemd):**
- Recopila la salida estándar y de error (`stdout`/`stderr`) de los servicios de systemd.
- Almacena los registros en formato binario y permite consultarlos con `journalctl`.
- Admite compresión y rotación automáticas.

**logrotate (gestión tradicional de archivos de registro):**
- Rota, comprime y elimina archivos de texto de registro.
- Se ejecuta mediante el temporizador de systemd de la distribución o un trabajo de cron.

**Configuración de los registros de nodos de Kubernetes:**

**1. Configuración de journald (`/etc/systemd/journald.conf`):**
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

**2. Rotación de registros CRI de kubelet:**

Combina estos campos con la configuración existente de kubelet; no los apliques con `kubectl` ni sustituyas el archivo completo.

```yaml
containerLogMaxSize: 10Mi
containerLogMaxFiles: 5
```

Para los registros de texto normales de aplicaciones que no administra kubelet:

```text
# /etc/logrotate.d/myapp
/var/log/myapp/*.log {
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

**3. Comandos para limpiar registros:**
```bash
# journald log cleanup
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete old logs when exceeding 1GB

# Check disk usage
journalctl --disk-usage
```

**Buenas prácticas para gestionar registros en Kubernetes:**

1. **Registros de kubelet**: suelen gestionarse con journald. Los registros persistentes están en `/var/log/journal`; los volátiles, en `/run/log/journal`.
2. **Registros de contenedores**: los archivos CRI suelen estar en `/var/log/pods` y tienen enlaces simbólicos en `/var/log/containers`. Kubelet administra su rotación; no ejecutes logrotate sobre esos enlaces simbólicos.
3. **Registro centralizado**: se recomienda reenviar los registros a sistemas externos mediante Fluentd o Fluent Bit.

`copytruncate` puede perder registros por la carrera entre la copia y el truncado; es preferible que la aplicación admita un mecanismo para volver a abrir sus archivos. Los comandos de `journalctl` con la opción `--vacuum` solo eliminan archivos archivados.

Una gestión adecuada de los registros equilibra la prevención de fallos de nodos por falta de espacio en disco con la conservación de datos para resolver problemas.
</details>

---

[Volver a los materiales de aprendizaje](../../basics/01-linux-basics.md) | [Siguiente cuestionario: Operaciones de Linux](./02-linux-advanced-quiz.md)

## Referencias de verificación

- https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html
- https://kubernetes.io/docs/concepts/architecture/cgroups/
- https://man7.org/linux/man-pages/man7/time_namespaces.7.html
- https://man7.org/linux/man-pages/man2/getrlimit.2.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html
- https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- https://kubernetes.io/docs/concepts/cluster-administration/logging/
- https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
- https://ubuntu.com/about/release-cycle
- https://www.debian.org/releases/
- https://www.centos.org/centos-linux-eol/
- https://documentation.ubuntu.com/server/how-to/networking/timedatectl-and-timesyncd/
- https://aws.amazon.com/amazon-linux-2/faqs/
- https://docs.aws.amazon.com/linux/al2023/ug/ec2.html
- https://github.com/logrotate/logrotate/blob/main/logrotate.8.in
- https://github.com/linux-pam/linux-pam/blob/master/modules/pam_limits/limits.conf.5.xml
