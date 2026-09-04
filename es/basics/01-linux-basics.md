# Conceptos básicos de Linux

> **Versiones compatibles**: Todas las principales distribuciones de Linux (Ubuntu 20.04+, CentOS/RHEL 8+, Debian 11+) **Última actualización**: February 11, 2026

Comprender los fundamentos de Linux es esencial para entender Kubernetes y la tecnología de contenedores. Este documento aborda los conceptos centrales de Linux que son especialmente importantes en los entornos de Kubernetes.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás el siguiente entorno:

### Entorno necesario

* Sistema operativo Linux (se recomienda Ubuntu 20.04+, CentOS/RHEL 8+, Debian 11+)
* Acceso a terminal
* Privilegios de sudo

### Configuración del entorno en la nube (opcional)

Si utilizas una instancia AWS EC2:

```bash
# Start an Amazon Linux 2 instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.micro \
  --key-name your-key-pair \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678

# SSH connection
ssh -i your-key.pem ec2-user@your-instance-public-ip
```

### Configuración del entorno local (opcional)

Para practicar localmente, puedes usar una de las siguientes opciones:

* **VirtualBox + Vagrant**: Configura un entorno de máquina virtual
* **WSL2**: Usa un entorno Linux en Windows
* **Docker**: Practica en un entorno de contenedor

## Índice

* [Kernel de Linux y espacio de usuario](01-linux-basics.md#linux-kernel-and-user-space)
* [Gestión de procesos](01-linux-basics.md#process-management)
* [Namespaces](01-linux-basics.md#namespaces)
* [cgroups (Control Groups)](01-linux-basics.md#cgroups-control-groups)
* [Sistema de archivos](01-linux-basics.md#file-system)
* [Conceptos básicos de redes](01-linux-basics.md#networking-basics)
* [Contexto de seguridad](01-linux-basics.md#security-context)
* [systemd y gestión de servicios](01-linux-basics.md#systemd-and-service-management)
* [Parámetros y módulos del kernel](01-linux-basics.md#kernel-parameters-and-modules)
* [Límites de recursos del sistema](01-linux-basics.md#system-resource-limits)
* [Gestión de logs](01-linux-basics.md#log-management)
* [Configuración de DNS y red](01-linux-basics.md#dns-and-network-configuration)
* [Sincronización de hora](01-linux-basics.md#time-synchronization)
* [Gestión de paquetes](01-linux-basics.md#package-management)
* [Comandos esenciales de Linux](01-linux-basics.md#essential-linux-commands)
* [Características de Linux relacionadas con contenedores](01-linux-basics.md#container-related-linux-features)

## Kernel de Linux y espacio de usuario

### Función del kernel

> **Concepto clave**: El kernel de Linux es el núcleo del sistema operativo y actúa como intermediario entre el hardware y el software.

El kernel de Linux es el núcleo del sistema operativo y actúa como intermediario entre el hardware y el software. Sus funciones principales incluyen:

* **Gestión de procesos**: Creación, planificación y finalización de procesos
* **Gestión de memoria**: Memoria virtual y asignación de memoria física
* **Gestión de dispositivos**: Comunicación con dispositivos de hardware
* **Interfaz de llamadas al sistema**: Proporciona una forma para que los programas del espacio de usuario accedan a los servicios del kernel

### Espacio de usuario

El espacio de usuario es la región de memoria donde se ejecutan las aplicaciones normales. Los programas del espacio de usuario acceden a los servicios del kernel mediante llamadas al sistema.

![Espacio de usuario de Linux, espacio del kernel y capas de hardware: las aplicaciones y la shell llegan a los subsistemas del kernel a través de las bibliotecas del sistema y la interfaz de llamadas al sistema, y los controladores de dispositivos llegan a la CPU, la memoria, el almacenamiento y la tarjeta de red.](../.gitbook/assets/en-basics-01-linux-basics-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-0.html)

### Ejemplos de llamadas al sistema

| Llamada al sistema | Descripción           | Comandos relacionados    |
| ----------- | --------------------- | ------------------- |
| `fork()`    | Crear un proceso nuevo    | `ps`, `top`         |
| `exec()`    | Ejecutar un programa       | `bash`, `sh`        |
| `open()`    | Abrir un archivo             | `cat`, `less`       |
| `read()`    | Leer datos de un archivo   | `cat`, `grep`       |
| `write()`   | Escribir datos en un archivo    | `echo`, `tee`       |
| `socket()`  | Crear un socket de red | `netstat`, `ss`     |
| `clone()`   | Crear un namespace      | `unshare`, `docker` |

### Arquitectura del kernel de Linux

![Arquitectura del kernel de Linux en capas: las aplicaciones y la shell entran al kernel mediante las bibliotecas del sistema y la interfaz de llamadas al sistema, y los subsistemas del kernel controlan el hardware mediante controladores de dispositivos.](../.gitbook/assets/en-basics-01-linux-basics-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-1.html)

## Gestión de procesos

### Procesos e hilos

* **Proceso**: Una instancia de un programa en ejecución con su propio espacio de memoria independiente
* **Hilo**: Una unidad de trabajo que se ejecuta dentro de un proceso; los hilos del mismo proceso comparten el espacio de memoria

### Estados de proceso

* **En ejecución**: Se está ejecutando actualmente en la CPU
* **En espera**: Esperando a que finalice una operación de I/O o que ocurra un evento
* **Listo**: Listo para ejecutarse, pero esperando asignación de CPU
* **Zombie**: Finalizado, pero el proceso padre no ha comprobado su estado
* **Detenido**: Estado suspendido

### Comandos clave de gestión de procesos

```bash
# View process list
ps aux

# Real-time process monitoring
top

# Enhanced real-time process monitoring
htop

# Terminate process
kill <PID>
killall <process-name>

# Background execution
command &

# Job management
jobs
fg %<job-number>
bg %<job-number>
```

## Namespaces

Los namespaces son una característica del kernel de Linux que aísla grupos de procesos para que cada grupo pueda ver los recursos del sistema de forma independiente. Son un elemento central de la tecnología de contenedores.

### Tipos principales de namespace

* **PID Namespace**: Aislamiento de ID de proceso; permite que los contenedores tengan su propio PID 1 (init)
* **Network Namespace**: Aislamiento de la pila de red (interfaces, direcciones IP, tablas de enrutamiento, firewalls, etc.); base de las redes de contenedores
* **Mount Namespace**: Aislamiento de puntos de montaje del sistema de archivos; proporciona un sistema de archivos independiente por contenedor
* **UTS Namespace**: Aislamiento de nombre de host y nombre de dominio; proporciona a cada contenedor un identificador de host único
* **IPC Namespace**: Aislamiento de recursos de comunicación entre procesos (memoria compartida, semáforos, colas de mensajes, etc.); importante para el aislamiento de servicios en la arquitectura de microservicios
* **User Namespace**: Aislamiento de ID de usuario y grupo; admite la ejecución de contenedores rootless para mejorar la seguridad
* **cgroup Namespace**: Aislamiento del directorio raíz de cgroup; proporciona visibilidad de los límites de recursos dentro de los contenedores
* **Time Namespace**: Aislamiento del reloj del sistema; permite configuraciones de hora independientes por contenedor (Linux 5.6+)

### Comandos relacionados con namespaces

```bash
# Check process namespaces
ls -la /proc/<PID>/ns/

# Execute command in new namespace
unshare --net --pid --fork --mount-proc bash

# Enter existing process's namespace
nsenter --target <PID> --net --pid bash

# Create and manage network namespaces
ip netns add <name>
ip netns exec <name> <command>

# Using user namespace for rootless container execution
unshare --user --map-root-user --mount --net bash

# Using time namespace (Linux 5.6+)
unshare --time bash
```

## cgroups (Control Groups)

cgroups es una característica del kernel de Linux que limita y aísla el uso de recursos de los grupos de procesos. Se utiliza para implementar límites de recursos de contenedores. Es una tecnología central para la gestión de recursos en entornos cloud-native y Kubernetes.

### Características principales de cgroups

* **Limitación de tiempo de CPU**: Limita el tiempo de CPU disponible para los grupos de procesos y asigna núcleos de CPU
* **Limitación de memoria**: Limita la memoria disponible para los grupos de procesos y controla el comportamiento de OOM (Out of Memory)
* **Limitación de I/O de bloques**: Limitación de ancho de banda de I/O de disco y configuración de prioridad
* **Limitación de ancho de banda de red**: Limitación de tráfico de red (combinada con tc)
* **Control de acceso a dispositivos**: Control de acceso y gestión de permisos para dispositivos específicos
* **Control de PIDs**: Limita el número de creación de procesos para evitar fork bombs
* **Freezer**: Pausa y reanuda grupos de procesos (utilizado para pausar contenedores)
* **cpuset**: Vincula procesos a núcleos de CPU y nodos NUMA específicos

### cgroups v1 y v2

* **cgroups v1**: Jerarquía independiente para cada tipo de recurso; todavía se utiliza en sistemas heredados
* **cgroups v2**: Jerarquía única unificada para una gestión más coherente; predeterminada en distribuciones modernas
* **Modo híbrido**: Usa v1 y v2 conjuntamente para mantener la compatibilidad mientras aprovecha nuevas características

### Comandos relacionados con cgroups

```bash
# Check cgroups
ls -la /sys/fs/cgroup/                     # cgroups v2
ls -la /sys/fs/cgroup/cpu /sys/fs/cgroup/memory  # cgroups v1

# cgroups management through systemd (modern approach)
systemctl set-property <service-name> CPUQuota=20%
systemctl set-property <service-name> MemoryLimit=1G
systemctl set-property <service-name> IOWeight=500

# Check process cgroup
cat /proc/<PID>/cgroup

# Direct cgroups v2 manipulation (advanced)
echo $$ > /sys/fs/cgroup/user.slice/cgroup.procs
echo "max 100000" > /sys/fs/cgroup/user.slice/memory.max
echo "100000 500000" > /sys/fs/cgroup/user.slice/memory.high

# Container runtime and cgroups
podman stats  # Monitor container resource usage
docker run --cpus=0.5 --memory=512m nginx  # Set resource limits
```

## Sistema de archivos

### Jerarquía del sistema de archivos

Linux tiene una estructura jerárquica de sistema de archivos que comienza desde un único directorio raíz (`/`).

Directorios clave:

* `/bin`: Comandos básicos
* `/sbin`: Comandos de administración del sistema
* `/etc`: Archivos de configuración del sistema
* `/home`: Directorios personales de usuarios
* `/var`: Datos variables (logs, caché, etc.)
* `/tmp`: Archivos temporales
* `/usr`: Programas y datos de usuario
* `/proc`: Información de procesos y del kernel (sistema de archivos virtual)
* `/sys`: Información del sistema y hardware (sistema de archivos virtual)

### Tipos de sistemas de archivos

* **ext4**: Sistema de archivos predeterminado de Linux
* **XFS**: Adecuado para sistemas de archivos grandes
* **Btrfs**: Ofrece características avanzadas como snapshots y compresión
* **OverlayFS**: Representa varios directorios como un único directorio (utilizado habitualmente en contenedores)
* **tmpfs**: Sistema de archivos temporal basado en memoria

### Montaje y volúmenes

```bash
# Mount file system
mount -t <filesystem-type> <source> <mount-point>

# Check mounted file systems
mount
df -h

# Unmount file system
umount <mount-point>
```

## Conceptos básicos de redes

### Interfaces de red

* **lo**: Interfaz loopback (127.0.0.1)
* **eth0, ens3, etc.**: Interfaces de red físicas
* **docker0, cni0, etc.**: Interfaces de bridge virtuales (redes de contenedores)

### Comandos de configuración de red

```bash
# Check network interfaces
ip addr show
ifconfig

# Check routing table
ip route
route -n

# Check network connections
netstat -tuln
ss -tuln

# Network packet analysis
tcpdump -i <interface>
```

### Namespaces de red e interfaces virtuales

```bash
# Create network namespace
ip netns add <namespace-name>

# Create virtual ethernet pair
ip link add <veth1> type veth peer name <veth2>

# Connect virtual interface to namespace
ip link set <veth2> netns <namespace-name>
```

## Contexto de seguridad

### Usuarios y grupos

* **UID (User ID)**: Identificador de usuario
* **GID (Group ID)**: Identificador de grupo
* **root (UID 0)**: Usuario especial con privilegios administrativos

### Permisos de archivos

Los permisos de archivos de Linux constan de permisos de lectura (r), escritura (w) y ejecución (x) para el propietario, el grupo y otros usuarios.

![Cómo la cadena de permisos de 10 caracteres de ls -l se divide en un carácter de tipo de archivo más tríos r w x para el propietario, el grupo y otros, interpretando drwxr-xr-- como un directorio con acceso completo del propietario, lectura/ejecución para el grupo y acceso de solo lectura para otros.](../.gitbook/assets/en-basics-01-linux-basics-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-01-linux-basics-2.html)

### Comandos relacionados con permisos

```bash
# Change file permissions
chmod 755 <filename>  # rwxr-xr-x
chmod u+x <filename>  # Add execute permission for owner

# Change file owner
chown <user>:<group> <filename>

# Special permissions
chmod 4755 <filename>  # Set setuid
chmod 2755 <filename>  # Set setgid
chmod 1755 <filename>  # Set sticky bit
```

### SELinux y AppArmor

* **SELinux (Security-Enhanced Linux)**: Sistema de control de acceso obligatorio desarrollado por NSA
* **AppArmor**: Sistema de control de acceso que utiliza perfiles de seguridad por programa

```bash
# Check SELinux status
getenforce

# Change SELinux mode
setenforce 0  # Permissive mode
setenforce 1  # Enforcing mode

# Check AppArmor status
aa-status

# AppArmor profile management
aa-enforce /etc/apparmor.d/<profile>
aa-complain /etc/apparmor.d/<profile>
```

## systemd y gestión de servicios

systemd es el sistema init y gestor de servicios de los sistemas Linux modernos. Se utiliza para gestionar servicios centrales como kubelet y containerd en los nodos de Kubernetes.

### Características principales de systemd

* **Gestión de servicios**: Inicia, detiene, reinicia, habilita o deshabilita servicios del sistema
* **Gestión de dependencias**: Gestión automática de dependencias de servicios e inicio en paralelo
* **Logging**: Gestión de logs integrada mediante journald
* **Timers**: Unidades de temporizador que pueden sustituir a cron
* **Gestión de recursos**: Límites de recursos por servicio mediante cgroups

### Tipos de unidades systemd

* **service**: Servicios del sistema (p. ej., kubelet.service, containerd.service)
* **socket**: Activación basada en socket
* **target**: Grupos de unidades (similares a runlevels)
* **timer**: Tareas programadas
* **mount**: Montajes de sistemas de archivos
* **device**: Unidades de dispositivos

### Comandos systemd

```bash
# Check service status
systemctl status kubelet
systemctl status containerd

# Service control
systemctl start <service>
systemctl stop <service>
systemctl restart <service>
systemctl reload <service>  # Reload configuration

# Set auto-start at boot
systemctl enable <service>
systemctl disable <service>

# Check service logs
journalctl -u kubelet -f  # Real-time logs
journalctl -u kubelet --since "1 hour ago"
journalctl -u kubelet --no-pager

# List all services
systemctl list-units --type=service
systemctl list-unit-files --type=service

# Check failed services
systemctl --failed

# Reload systemd configuration
systemctl daemon-reload
```

### Escritura de archivos de unidad systemd

Ejemplo de archivo de unidad systemd para servicios relacionados con Kubernetes:

```ini
# /etc/systemd/system/kubelet.service
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

### Límites de recursos de systemd

```bash
# CPU limit (20%)
systemctl set-property kubelet CPUQuota=20%

# Memory limit (1GB)
systemctl set-property kubelet MemoryLimit=1G

# I/O weight setting (100-1000, default 100)
systemctl set-property kubelet IOWeight=500

# Check settings
systemctl show kubelet | grep -E 'CPUQuota|MemoryLimit|IOWeight'
```

## Parámetros y módulos del kernel

### Configuración de parámetros del kernel mediante sysctl

sysctl es una herramienta para consultar y modificar los parámetros del kernel en ejecución. Es esencial para ajustar parámetros de red y del sistema al configurar clústeres de Kubernetes.

#### Configuraciones sysctl clave necesarias para Kubernetes

```bash
# Enable IP forwarding (required for container networking)
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Enable bridge traffic to pass through iptables (required for CNI plugins)
sysctl -w net.bridge.bridge-nf-call-iptables=1
sysctl -w net.bridge.bridge-nf-call-ip6tables=1

# Increase maximum file descriptor count
sysctl -w fs.file-max=2097152

# Network performance tuning
sysctl -w net.core.somaxconn=32768
sysctl -w net.ipv4.tcp_max_syn_backlog=8192
sysctl -w net.core.netdev_max_backlog=16384

# ARP cache settings (for large clusters)
sysctl -w net.ipv4.neigh.default.gc_thresh1=80000
sysctl -w net.ipv4.neigh.default.gc_thresh2=90000
sysctl -w net.ipv4.neigh.default.gc_thresh3=100000

# Check current settings
sysctl net.ipv4.ip_forward
sysctl -a | grep bridge-nf-call

# Persistent settings (/etc/sysctl.conf or /etc/sysctl.d/*.conf)
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes.conf
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

# Apply settings
sysctl --system
```

### Gestión de módulos del kernel

Muchos plugins CNI y controladores de almacenamiento requieren módulos específicos del kernel.

```bash
# Load modules
modprobe overlay  # OverlayFS (container storage)
modprobe br_netfilter  # Bridge networking
modprobe ip_vs  # IPVS load balancing (kube-proxy IPVS mode)
modprobe ip_vs_rr  # Round Robin algorithm
modprobe ip_vs_wrr  # Weighted Round Robin
modprobe ip_vs_sh  # Source Hashing

# Check loaded modules
lsmod | grep overlay
lsmod | grep br_netfilter

# Check module information
modinfo overlay

# Set auto-load at boot
cat <<EOF | sudo tee /etc/modules-load.d/kubernetes.conf
overlay
br_netfilter
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
EOF

# Unload module
modprobe -r <module-name>
```

### Comprobación de la versión y características del kernel

```bash
# Check kernel version
uname -r

# Check kernel compile options
cat /boot/config-$(uname -r) | grep OVERLAY
cat /boot/config-$(uname -r) | grep NETFILTER

# Check available kernel features
cat /proc/filesystems  # Supported file systems
cat /proc/sys/net/ipv4/ip_forward  # IP forwarding status
```

## Límites de recursos del sistema

### ulimit: límites de recursos por usuario

ulimit limita los recursos del sistema que pueden utilizar los procesos. Puede ser necesario realizar ajustes en los nodos de Kubernetes para garantizar recursos suficientes.

```bash
# Check current limits
ulimit -a

# Key limit items
ulimit -n      # Number of open file descriptors
ulimit -u      # Maximum number of processes
ulimit -m      # Maximum memory size
ulimit -v      # Virtual memory size

# Change limits (current session)
ulimit -n 65536  # Increase file descriptors to 65536

# Persistent settings (/etc/security/limits.conf)
sudo tee -a /etc/security/limits.conf <<EOF
*               soft    nofile          65536
*               hard    nofile          65536
*               soft    nproc           32768
*               hard    nproc           32768
EOF

# Settings for specific users/groups
sudo tee -a /etc/security/limits.conf <<EOF
root            soft    nofile          65536
root            hard    nofile          65536
@docker         soft    nofile          65536
@docker         hard    nofile          65536
EOF
```

### Configuración de límites PAM

```bash
# Check PAM settings
cat /etc/pam.d/common-session
cat /etc/pam.d/common-session-noninteractive

# Add to PAM settings to apply limits.conf
echo "session required pam_limits.so" | sudo tee -a /etc/pam.d/common-session
```

### Comprobación de recursos por proceso

```bash
# Check current resource limits for a process
cat /proc/<PID>/limits

# Check file descriptors for a specific process
ls -l /proc/<PID>/fd | wc -l
```

## Gestión de logs

### journald: logging integrado de systemd

journald es el sistema de logging de systemd que gestiona los logs de servicios del sistema en los nodos de Kubernetes.

```bash
# Full system logs
journalctl

# Specific service logs
journalctl -u kubelet
journalctl -u containerd
journalctl -u docker

# Real-time logs (similar to tail -f)
journalctl -u kubelet -f

# Time range specification
journalctl --since "2025-11-24 10:00:00"
journalctl --since "1 hour ago"
journalctl --since yesterday
journalctl --until "2025-11-24 12:00:00"

# Filter by priority
journalctl -p err        # Errors only
journalctl -p warning    # Warnings and above
journalctl -p debug      # All including debug

# Change output format
journalctl -u kubelet -o json        # JSON format
journalctl -u kubelet -o json-pretty # Pretty JSON
journalctl -u kubelet -o cat         # Messages only

# Boot logs
journalctl -b           # Current boot logs
journalctl -b -1        # Previous boot logs
journalctl --list-boots # Boot list

# Check disk usage
journalctl --disk-usage

# Clean logs
journalctl --vacuum-time=7d   # Delete logs older than 7 days
journalctl --vacuum-size=1G   # Delete logs over 1GB
```

### Configuración de journald

```bash
# journald configuration file
sudo vi /etc/systemd/journald.conf

# Key configuration options
# Storage=persistent        # Persistent storage to disk
# SystemMaxUse=1G          # Maximum disk usage
# SystemKeepFree=500M      # Minimum free space
# MaxRetentionSec=1month   # Maximum retention period

# Apply configuration
sudo systemctl restart systemd-journald
```

### syslog tradicional

Algunos sistemas todavía utilizan syslog.

```bash
# syslog file locations
/var/log/syslog         # Debian/Ubuntu
/var/log/messages       # RHEL/CentOS

# Real-time log viewing
tail -f /var/log/syslog

# Log search
grep "kubelet" /var/log/syslog
grep -i "error" /var/log/syslog
```

### Rotación de logs

Configura la rotación de logs para evitar que los archivos de log crezcan indefinidamente.

```bash
# logrotate configuration
sudo vi /etc/logrotate.d/kubernetes

# Example configuration
/var/log/kubernetes/*.log {
    daily
    rotate 7
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
}

# Run rotation manually
sudo logrotate -f /etc/logrotate.d/kubernetes
```

## Configuración de DNS y red

### Configuración de DNS

DNS es fundamental para el descubrimiento de servicios dentro de los clústeres de Kubernetes.

```bash
# DNS configuration file
cat /etc/resolv.conf

# Example configuration
nameserver 8.8.8.8
nameserver 8.8.4.4
search cluster.local svc.cluster.local
options ndots:5

# DNS lookup test
nslookup kubernetes.default.svc.cluster.local
dig kubernetes.default.svc.cluster.local

# hosts file
cat /etc/hosts
```

### systemd-resolved

Las distribuciones modernas de Linux utilizan systemd-resolved.

```bash
# Check systemd-resolved status
systemctl status systemd-resolved

# Check DNS servers
resolvectl status

# DNS cache statistics
resolvectl statistics

# Clear DNS cache
resolvectl flush-caches
```

### Archivos de configuración de red

```bash
# NetworkManager (RHEL/CentOS 8+, Ubuntu 18.04+)
nmcli connection show
nmcli device status

# netplan (Ubuntu 18.04+)
cat /etc/netplan/*.yaml

# Example netplan configuration
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]

# Apply configuration
sudo netplan apply
```

## Sincronización de hora

La sincronización de hora es muy importante en los sistemas distribuidos. Todos los nodos de un clúster de Kubernetes deben mantener una hora precisa.

### chronyd (recomendado)

chronyd es un cliente NTP moderno que sincroniza la hora más rápido que ntpd.

```bash
# Install chronyd (RHEL/CentOS)
sudo yum install chrony

# Install chronyd (Ubuntu/Debian)
sudo apt install chrony

# Check service status
systemctl status chronyd

# Check time synchronization status
chronyc tracking

# NTP server list
chronyc sources

# Detailed information
chronyc sourcestats

# Manual time synchronization
sudo chronyc makestep
```

### Configuración de chronyd

```bash
# Configuration file
sudo vi /etc/chrony.conf

# Key settings
# NTP server configuration
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst
server 2.pool.ntp.org iburst
server 3.pool.ntp.org iburst

# Fast synchronization
makestep 1.0 3

# Apply configuration
sudo systemctl restart chronyd
```

### timesyncd (predeterminado de Ubuntu)

Ubuntu utiliza systemd-timesyncd de forma predeterminada.

```bash
# Check status
timedatectl status

# NTP synchronization status
timedatectl show-timesync --all

# Configuration file
sudo vi /etc/systemd/timesyncd.conf

# Example configuration
[Time]
NTP=0.pool.ntp.org 1.pool.ntp.org
FallbackNTP=time.google.com

# Restart service
sudo systemctl restart systemd-timesyncd
```

### Configuración de zona horaria

```bash
# Check current time and timezone
timedatectl

# List timezones
timedatectl list-timezones

# Change timezone
sudo timedatectl set-timezone Asia/Seoul

# Manually set time (when NTP is disabled)
sudo timedatectl set-time "2025-11-24 12:00:00"

# Enable/disable NTP
sudo timedatectl set-ntp true
```

## Gestión de paquetes

Uso de gestores de paquetes para instalar y gestionar Kubernetes y herramientas relacionadas.

### apt (Debian/Ubuntu)

```bash
# Update package list
sudo apt update

# Upgrade packages
sudo apt upgrade

# Install package
sudo apt install <package-name>

# Remove package
sudo apt remove <package-name>
sudo apt purge <package-name>  # Remove configuration files as well

# Search packages
apt search <keyword>

# Package information
apt show <package-name>

# List installed packages
apt list --installed

# Add repository (Kubernetes example)
sudo apt install -y apt-transport-https ca-certificates curl
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
  https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

# Clean unnecessary packages
sudo apt autoremove
sudo apt autoclean
```

### yum/dnf (RHEL/CentOS/Fedora)

```bash
# Install package
sudo yum install <package-name>
sudo dnf install <package-name>  # Fedora/RHEL 8+

# Update packages
sudo yum update
sudo dnf update

# Remove package
sudo yum remove <package-name>
sudo dnf remove <package-name>

# Search packages
yum search <keyword>
dnf search <keyword>

# Package information
yum info <package-name>
dnf info <package-name>

# List installed packages
yum list installed
dnf list installed

# Add repository (Kubernetes example)
cat <<EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.28/rpm/repodata/repomd.xml.key
EOF

# Clean cache
sudo yum clean all
sudo dnf clean all
```

### Bloqueo de versiones de paquetes

Los componentes de Kubernetes tienen requisitos de compatibilidad de versiones, por lo que se deben evitar las actualizaciones automáticas.

```bash
# apt (Ubuntu/Debian)
sudo apt-mark hold kubelet kubeadm kubectl

# Remove apt hold
sudo apt-mark unhold kubelet kubeadm kubectl

# yum (RHEL/CentOS)
sudo yum install yum-plugin-versionlock
sudo yum versionlock add kubelet kubeadm kubectl

# Remove yum versionlock
sudo yum versionlock delete kubelet kubeadm kubectl
```

## Comandos esenciales de Linux

### Gestión de archivos y directorios

```bash
ls -la           # List files (including hidden)
cd <directory>   # Change directory
pwd              # Print current directory
mkdir -p <path>  # Create directory (create parent directories if needed)
rm -rf <path>    # Remove files/directories
cp -r <source> <destination> # Copy files/directories
mv <source> <destination>    # Move or rename files/directories
find <path> -name "<pattern>" # Search files
```

### Procesamiento de texto

```bash
cat <file>        # Output file contents
less <file>       # View file contents page by page
grep "<pattern>" <file> # Search pattern in file
sed 's/<pattern>/<replacement>/' <file> # Text substitution
awk '{print $1}' <file> # Text processing
```

### Información del sistema

```bash
uname -a         # Kernel information
lsb_release -a   # Distribution information
free -h          # Memory usage
df -h            # Disk usage
du -sh <path>    # Directory size
```

### Gestión de procesos y servicios

```bash
systemctl status <service> # Check service status
systemctl start/stop/restart <service> # Service control
journalctl -u <service> # View service logs
```

## Características de Linux relacionadas con contenedores

### OverlayFS

OverlayFS es un sistema de archivos de montaje union que representa varios directorios como uno solo. Lo utilizan runtimes de contenedores como Docker para implementar capas de imágenes.

### Bridge de red y NAT

Las redes de contenedores se implementan principalmente mediante interfaces bridge y NAT (Network Address Translation).

![Docker bridge networking on a single host](../../assets/diagrams/rendered/docker-bridge-networking.svg)

### Filtrado de llamadas al sistema (seccomp)

seccomp (Secure Computing Mode) es una característica del kernel de Linux que restringe las llamadas al sistema disponibles para los procesos. Se utiliza para mejorar la seguridad de los contenedores.

### Restricción de capabilities

Las capabilities de Linux dividen los privilegios tradicionales de root en unidades de permisos más pequeñas. Los contenedores reciben solo las capabilities necesarias para mejorar la seguridad.

Capabilities clave:

* `CAP_NET_ADMIN`: Cambios de configuración de red
* `CAP_SYS_ADMIN`: Tareas de administración del sistema
* `CAP_CHOWN`: Cambiar la propiedad de archivos
* `CAP_DAC_OVERRIDE`: Omitir permisos de archivos

## Conclusión

Los fundamentos y las características de Linux son esenciales para comprender Kubernetes y la tecnología de contenedores. Este es un resumen de los temas clave tratados en este documento:

### Tecnologías centrales

* **Namespaces y cgroups**: Base para el aislamiento de contenedores y la gestión de recursos
* **OverlayFS**: Base de las capas de imágenes de contenedores
* **systemd**: Gestión de servicios de nodos de Kubernetes

### Conocimientos esenciales de operaciones

* **Ajuste de parámetros del kernel**: Optimización de red y del sistema mediante sysctl
* **Gestión de módulos**: Compatibilidad con plugins CNI y controladores de almacenamiento
* **Gestión de logs**: Análisis de logs de sistema y servicios mediante journald
* **Sincronización de hora**: Mantenimiento de la coherencia en sistemas distribuidos

### Resolución de problemas

* **Límites de recursos**: Gestión de recursos mediante ulimit y cgroups
* **Redes**: Configuración de DNS, bridge e iptables
* **Gestión de paquetes**: Gestión de versiones de los componentes de Kubernetes

Con esta base de Linux, puedes resolver eficazmente problemas en entornos de Kubernetes, optimizar clústeres y operarlos de forma fiable.

## Cuestionario

Para poner a prueba lo que has aprendido en este capítulo, realiza el [Cuestionario de conceptos básicos de Linux](../quizzes/basics/01-linux-basics-quiz.md).

## Referencias

* [The Linux Documentation Project](https://tldp.org/)
* [Documentación del kernel de Linux](https://www.kernel.org/doc/)
* [Namespaces de Linux](https://man7.org/linux/man-pages/man7/namespaces.7.html)
* [Control Groups v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
