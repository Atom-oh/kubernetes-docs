# Tecnología de contenedores

> **Versiones compatibles**: Versiones con mantenimiento activo de Linux, Docker y CRI; CRI v1 de Kubernetes; ejemplos de compilación con Node.js 24 **Última actualización**: 16 de octubre de 2026

Los contenedores son una tecnología que empaqueta aplicaciones y sus dependencias, lo que permite ejecutarlas de forma coherente en diversos entornos. Este documento explica los conceptos fundamentales de los contenedores, cómo funcionan y su relación con Kubernetes.

## Tabla de contenido

* [¿Qué es un contenedor?](03-container-technology.md#what-is-a-container)
* [Contenedor frente a máquina virtual](03-container-technology.md#container-vs-virtual-machine)
* [Fundamentos técnicos de los contenedores](03-container-technology.md#technical-foundation-of-containers)
* [Runtime de contenedores](03-container-technology.md#container-runtime)
* [Imágenes de contenedor](03-container-technology.md#container-images)
* [Dockerfile](03-container-technology.md#dockerfile)
* [Redes de contenedores](03-container-technology.md#container-networking)
* [Almacenamiento de contenedores](03-container-technology.md#container-storage)
* [Seguridad de contenedores](03-container-technology.md#container-security)
* [Administración del ciclo de vida de los contenedores](03-container-technology.md#container-lifecycle-management)
* [Orquestación de contenedores](03-container-technology.md#container-orchestration)
* [Contenedores en AWS](03-container-technology.md#containers-on-aws)

> Los comandos de Linux que aparecen a continuación presuponen un host Linux con Docker. Docker Desktop ejecuta su daemon en una VM, por lo que no se pueden inspeccionar directamente desde el sistema operativo de escritorio las rutas de PID o del sistema de archivos del host. Las imágenes requieren una arquitectura de CPU, un sistema operativo y características del kernel compatibles. Los entornos basados en VM, como Kata/Fargate, difieren del modelo básico de aislamiento de procesos descrito aquí.

## ¿Qué es un contenedor? {#what-is-a-container}

Un contenedor es una unidad de software estandarizada que incluye todo lo necesario para ejecutar una aplicación (código, runtime, herramientas del sistema, bibliotecas del sistema y configuración). Los contenedores se ejecutan en entornos aislados mientras comparten el kernel del sistema operativo host.

### Características principales de los contenedores

1. **Portabilidad**: Ofrecen un entorno de ejecución coherente durante el desarrollo, las pruebas y la producción
2. **Ligereza**: Utilizan menos recursos que las máquinas virtuales
3. **Aislamiento**: Entorno de ejecución aislado de otros contenedores y del sistema host
4. **Inicio y detención rápidos**: A menudo se inician rápidamente; la descarga de la imagen y la inicialización de la aplicación determinan cuándo están listos
5. **Escalabilidad**: Es fácil replicarlos para escalar horizontalmente
6. **Control de versiones**: Administración del ciclo de vida de las aplicaciones mediante el control de versiones de imágenes

### Historia de la tecnología de contenedores

* **Principios de la década de 2000**: Surgen las primeras tecnologías de contenedores, como Linux VServer y OpenVZ
* **2008**: Linux 2.6.24 publica la implementación inicial de cgroups
* **2008**: Comienza el proyecto LXC (Linux Containers)
* **2013**: El lanzamiento de Docker populariza la tecnología de contenedores
* **2015**: Se crea la Open Container Initiative (OCI) para estandarizar los contenedores
* **2017**: containerd se dona como proyecto de CNCF

## Contenedor frente a máquina virtual {#container-vs-virtual-machine}

### Arquitectura de máquinas virtuales frente a arquitectura de contenedores

### Diferencias principales

Esta es una comparación de arquitecturas, no una prueba de rendimiento/inicio basada en mediciones. El tamaño de la imagen, la inicialización y los mecanismos de restauración de VM afectan los resultados.

| Característica       | Contenedor                       | Máquina virtual                                           |
| ------------------- | -------------------------------- | --------------------------------------------------------- |
| Tamaño              | Capas de aplicación y espacio de usuario; varía | Sistema operativo invitado más aplicación; varía          |
| Tiempo de inicio    | A menudo es rápido cuando la imagen ya está en el host | Depende de la estrategia de arranque/restauración          |
| Nivel de aislamiento | Aislamiento a nivel de proceso   | Aislamiento a nivel de hardware                            |
| Sistema operativo   | Comparte el kernel del sistema operativo host | Cada VM requiere un sistema operativo completo             |
| Rendimiento         | Casi nativo                      | Cierta sobrecarga                                         |
| Seguridad           | Kernel compartido; requiere medidas de refuerzo | Límite del hipervisor; también requiere medidas de refuerzo |
| Eficiencia de recursos | Alta                          | Media                                                     |
| Casos de uso        | Microservicios, CI/CD, desarrollo/pruebas | Aplicaciones heredadas, requisitos de sistemas operativos diversos, necesidades de alta seguridad |

## Fundamentos técnicos de los contenedores {#technical-foundation-of-containers}

Los contenedores se implementan mediante varias características del kernel de Linux. Estas tecnologías se explicaron en detalle en 01-linux-basics.md; aquí nos centramos en su relación con los contenedores.

### Aislamiento mediante namespaces

Los contenedores utilizan namespaces de Linux para aislar procesos. El uso compartido de namespaces se puede configurar; por ejemplo, los contenedores de un mismo Kubernetes Pod comparten un namespace de red.

```bash
# Check container namespaces
docker inspect <container-id> | grep -A 10 "Pid"
ls -la /proc/<pid>/ns/

# Check processes inside container (isolated PID namespace)
docker exec <container-id> ps aux

# Check same process from host (actual PID)
ps aux | grep <process-name>
```

**Namespaces que utilizan los contenedores**:

* **PID**: El contenedor tiene su propio árbol de procesos (a partir del PID 1)
* **Network**: Pila de red independiente (dirección IP, tabla de enrutamiento y puertos)
* **Mount**: Vista independiente del sistema de archivos
* **UTS**: Nombre de host independiente
* **IPC**: Espacio independiente para la comunicación entre procesos
* **User**: Asignación independiente de ID de usuario (opcional)

### Limitación de recursos mediante cgroups

Los contenedores utilizan cgroups para limitar y supervisar el uso de recursos.

```bash
# Run container with CPU limit
docker run --cpus=0.5 --memory=512m nginx

# Check container resource usage
docker stats <container-id>

# Check container cgroup settings
docker inspect <container-id> | grep -A 20 "Cgroup"

# On a Linux cgroup v2 host, inspect a running container's actual path.
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' <container-id>)
if [ "$CONTAINER_PID" -gt 0 ]; then
  CGROUP_PATH=$(awk -F: '$1 == "0" {print $3}' "/proc/$CONTAINER_PID/cgroup")
  cat "/sys/fs/cgroup$CGROUP_PATH/cpu.max"
  cat "/sys/fs/cgroup$CGROUP_PATH/memory.max"
fi
```

**Controles de recursos cgroup que utilizan los contenedores**:

* **CPU**: Limitación del tiempo de CPU y asignación de núcleos de CPU
* **Memoria**: Limitación del uso de memoria y control del comportamiento OOM
* **E/S de bloques**: Limitación del ancho de banda de E/S del disco
* **Red**: Clasificación del tráfico integrada con tc/eBPF
* **PIDs**: Límite del número de procesos dentro del contenedor

### Administración de capas mediante OverlayFS

Las instalaciones nuevas de Docker Engine 29.0+ utilizan de forma predeterminada el almacén de imágenes y los snapshotters de containerd. Las actualizaciones pueden conservar el overlay2 clásico; consulta docker info. Las rutas de GraphDriver.Data no están disponibles en todas las instalaciones.

Las imágenes OCI describen las capas del sistema de archivos de forma independiente de la implementación de almacenamiento. OverlayFS es un backend común de Linux; los runtimes pueden utilizar otros controladores de almacenamiento o snapshotters.

```bash
# Check image layers
docker history <image-name>

# Check container file system layers
docker info --format '{{.Driver}} {{json .DriverStatus}}'
docker image inspect <image-name> --format '{{json .RootFS.Layers}}'

# Check OverlayFS mount information
mount | grep overlay
```

**Estructura de OverlayFS**:

* **LowerDir**: Capas de imagen de solo lectura (capa inferior → capa superior)
* **UpperDir**: Capa de contenedor de lectura/escritura
* **WorkDir**: Directorio de trabajo de OverlayFS
* **MergedDir**: Vista unificada (sistema de archivos que ve el contenedor)

### Laboratorio: comprender los fundamentos técnicos de los contenedores

```bash
# 1. Run a simple container
docker run -d --name test-container nginx

# 2. Get container PID
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' test-container)
echo "Container PID: $CONTAINER_PID"

# 3. Check container namespaces
ls -la /proc/$CONTAINER_PID/ns/

# 4. Check container cgroup
cat /proc/$CONTAINER_PID/cgroup

# 5. Check container file system layers
docker inspect test-container | jq '.[0].GraphDriver'

# 6. Cleanup
docker stop test-container
docker rm test-container
```

## Runtime de contenedores {#container-runtime}

Un runtime de contenedores es un software que administra el ciclo de vida de los contenedores. Ejecuta imágenes de contenedor, limita el uso de recursos de los contenedores y configura las redes y el almacenamiento.

### Jerarquía de runtime de contenedores

1. **Runtime de bajo nivel (compatible con OCI)**
   * **runc**: Runtime predeterminado de Docker e implementación del estándar OCI
   * **crun**: Runtime OCI ligero escrito en C
   * **kata-containers**: Runtime con seguridad reforzada que utiliza virtualización de hardware
   * **gVisor**: Runtime de seguridad que emula funciones del kernel en el espacio de usuario
2. **Runtime de alto nivel**
   * **containerd**: Runtime de contenedores estándar del sector, separado de Docker
   * **CRI-O**: Runtime ligero diseñado específicamente para Kubernetes
   * **Docker Engine**: Plataforma de contenedores de uso más extendido

### Interfaz de runtime de contenedores de Kubernetes (CRI)

Kubernetes se integra con distintos runtimes de contenedores mediante CRI (Container Runtime Interface). CRI proporciona una interfaz estandarizada entre Kubernetes y los runtimes de contenedores.

Kubernetes 1.26+ requiere CRI v1. Utiliza una versión compatible de containerd/CRI-O y haz coincidir su controlador cgroup con el de kubelet. Docker Engine no implementa CRI por sí mismo; dockershim, integrado en Kubernetes, se eliminó en la versión 1.24. Docker Engine necesita un adaptador CRI independiente, como cri-dockerd. Las imágenes OCI creadas con Docker siguen funcionando. CRI es el contrato de API entre kubelet y el runtime; no necesariamente un servicio intermedio que se implemente por separado.

## Imágenes de contenedor {#container-images}

Las imágenes de contenedor son plantillas inmutables que contienen aplicaciones y sus dependencias. Las imágenes constan de varias capas, cada una de las cuales representa cambios en el sistema de archivos.

### Capas de imagen

Las imágenes de contenedor se componen de una pila de varias capas. Cada capa representa los cambios realizados sobre la capa anterior. Este enfoque por capas hace que el uso compartido y el almacenamiento en caché de imágenes sean eficientes.

![Una pila de capas que muestra cómo se crea una imagen de contenedor desde una capa del sistema operativo, pasando por una capa de runtime y una capa de dependencias, hasta la capa de aplicación; cada capa registra los cambios sobre la capa inferior, lo que permite compartir imágenes y almacenarlas en caché de forma eficiente.](../.gitbook/assets/en-basics-03-container-technology-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-03-container-technology-0.html)

### Registros de imágenes

Las imágenes de contenedor se almacenan y comparten en registros. Entre los principales registros se incluyen:

* **Docker Hub**: El mayor registro público
* **Amazon ECR**: Servicio de registro de contenedores de AWS
* **Google Artifact Registry**: Registro actual de Google Cloud; Container Registry cerró en 2025, mientras que los repositorios gcr.io respaldados por Artifact Registry siguen siendo compatibles.
* **Azure Container Registry**: Registro de Microsoft Azure
* **GitHub Container Registry**: Registro de contenedores de GitHub
* **Harbor**: Registro de código abierto de nivel empresarial

### Etiquetas y digest de imágenes

* **Etiqueta**: Referencia mutable y legible para las personas; se puede reasignar, a menos que el registro aplique la inmutabilidad (por ejemplo, `nginx:1.30.6`)
* **Digest**: Valor hash de un manifiesto de imagen o de un índice multiplataforma (habitualmente SHA-256); identifica el contenido y hace referencia a los digest de la configuración y de las capas (por ejemplo, `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`)

## Dockerfile

Un Dockerfile es un archivo de texto que contiene instrucciones para crear una imagen de contenedor. Las instrucciones que modifican el sistema de archivos pueden crear capas; ENV, CMD y otras instrucciones que solo contienen metadatos no añaden diferencias al sistema de archivos.

### Instrucciones principales de Dockerfile

```dockerfile
FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production
# Requires a committed package-lock.json matching package.json.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY --chown=node:node . .
RUN mkdir -p /app/data && chown node:node /app/data
USER node
EXPOSE 3000
VOLUME /app/data
CMD ["node", "server.js"]
```

Node.js 14 llegó al final de su vida útil; estos ejemplos utilizan la línea Node.js 24 con soporte vigente. Comprueba que los módulos nativos sean compatibles con musl de Alpine. Prepara .dockerignore para evitar que node_modules del host o las credenciales se copien en la imagen. EXPOSE es metadato y no publica un puerto; para publicar un puerto se necesita docker run -p o la configuración del orquestador.

```text
# .dockerignore
node_modules
.git
.env
.env.*
npm-debug.log
```

### Compilaciones en varias etapas

Las compilaciones en varias etapas utilizan varias etapas de compilación para reducir el tamaño de la imagen final.

```dockerfile
FROM node:24 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.30.6-alpine
# This example assumes a static build written to dist/.
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Técnicas de optimización de imágenes

1. **Elegir una imagen base adecuada**: Utiliza imágenes ligeras, como Alpine
2. **Utilizar compilaciones en varias etapas**: Excluye las herramientas de compilación y los archivos intermedios
3. **Optimizar el contenido de las capas y la caché**: Combina la instalación y la limpieza de paquetes en una instrucción RUN; reducir el número de capas no garantiza por sí solo que la imagen sea más pequeña.
4. **Excluir archivos innecesarios**: Utiliza el archivo .dockerignore
5. **Aprovechar la caché**: Coloca las capas que cambian con frecuencia al final

## Redes de contenedores {#container-networking}

Las redes de contenedores permiten la comunicación entre contenedores y con el exterior.

### Controladores de red

Docker proporciona varios controladores de red:

1. **bridge**: Controlador de red predeterminado; permite la comunicación entre contenedores del mismo host
2. **host**: Comparte el namespace de red del host; se mantiene el resto del aislamiento del contenedor
3. **overlay**: Comunicación entre contenedores de varios hosts
4. **macvlan**: Asigna una dirección MAC al contenedor, que aparece como un dispositivo de red físico
5. **none**: Deja solo la red de loopback

### Asignación de puertos

Asigna los puertos internos del contenedor a los puertos del host para permitir el acceso externo.

```bash
# Map host port 8080 to container port 80
docker run -p 8080:80 nginx
```

La publicación de puertos se enlaza de forma predeterminada a todas las direcciones del host. Utiliza `-p 127.0.0.1:8080:80` para un laboratorio accesible solo desde el equipo local.

### Comunicación entre contenedores

1. **Misma red**: Los contenedores de una misma red bridge definida por el usuario pueden resolver los nombres de los demás; el bridge predeterminado no proporciona resolución DNS automática de nombres
2. **Links**: Método heredado para configurar enlaces directos entre contenedores
3. **Red externa**: Comunicación a través de los puertos del host

## Almacenamiento de contenedores {#container-storage}

La capa de escritura de un contenedor Docker se conserva al detenerlo y volverlo a iniciar, pero se elimina junto con el contenedor. Guarda los datos persistentes en volúmenes u otros almacenamientos externos.

### Tipos de almacenamiento

1. **Almacenamiento efímero**: Sistema de archivos interno del contenedor; los datos se pierden al eliminarlo
2. **Volúmenes**: Áreas del sistema de archivos del host administradas por Docker
3. **Montajes bind**: Montan rutas específicas del host en el contenedor
4. **Montajes tmpfs**: Almacenamiento temporal respaldado por memoria; el sistema puede llevar sus páginas a disco mediante swap

### Ejemplos de uso de volúmenes

```bash
# Create volume
docker volume create my-vol

# Run container using volume
docker run -v my-vol:/app/data nginx

# Use bind mount
docker run -v /host/path:/container/path nginx

# Read-only mount
docker run -v /host/path:/container/path:ro nginx
```

### Patrones para compartir datos

1. **Uso compartido de volúmenes**: Varios contenedores utilizan el mismo volumen
2. **Contenedor de volumen de datos**: Crea un contenedor que solo contenga datos y luego compártelo
3. **Integración con almacenamiento externo**: Utiliza sistemas de almacenamiento externos, como AWS EBS o NFS

## Seguridad de contenedores {#container-security}

La seguridad de los contenedores debe tenerse en cuenta en varias capas, incluidas las imágenes, el runtime de contenedores y los sistemas host.

### Seguridad de las imágenes

1. **Análisis de vulnerabilidades**: Analiza las imágenes en busca de vulnerabilidades con herramientas como Trivy o Clair
2. **Imágenes base de confianza**: Utiliza imágenes oficiales o verificadas
3. **Principio de privilegio mínimo**: Incluye solo los paquetes y permisos necesarios
4. **Firma de imágenes**: Utiliza un flujo de trabajo de firma de imágenes mantenido, como Cosign. Docker Content Trust está en proceso de retirada; está previsto que el servicio Notary v1 de Docker cierre el 8 de diciembre de 2026.

### Seguridad en tiempo de ejecución

1. **Restricción de privilegios**: Ejecuta los contenedores con un usuario no root
2. **Restricción de capacidades**: Concede solo las capacidades de Linux necesarias
3. **Perfiles seccomp**: Restringen las llamadas al sistema
4. **AppArmor/SELinux**: Aplica controles de acceso obligatorios
5. **Sistema de archivos de solo lectura**: Monta el sistema de archivos como solo lectura cuando sea posible

### Prácticas recomendadas de seguridad

1. **Actualizaciones periódicas**: Actualiza periódicamente las imágenes de contenedor y los sistemas host
2. **Aislamiento de red**: Restringe la comunicación entre contenedores mediante políticas de red adecuadas
3. **Administración de secretos**: Utiliza el mecanismo de secretos de la plataforma o un administrador de secretos externo. Los secretos de Docker Swarm se aplican a los servicios, no a los contenedores independientes ejecutados con docker run; los secretos de los archivos Compose ofrecen garantías distintas.
4. **Límites de recursos**: Limita el uso de CPU, memoria y otros recursos
5. **Supervisión y registro**: Supervisa la actividad de los contenedores y centraliza los registros

## Administración del ciclo de vida de los contenedores {#container-lifecycle-management}

Comprender todo el ciclo de vida de los contenedores es esencial para administrarlos eficazmente.

### Estados de los contenedores

Los contenedores pueden encontrarse en varios estados:

* **Created**: Contenedor creado, pero aún no iniciado
* **Running**: El contenedor está en ejecución
* **Paused**: Los procesos de Linux están congelados mediante el cgroup freezer
* **Restarting**: El contenedor se está reiniciando
* **Exited**: El contenedor ha terminado
* **Removing**: Se está eliminando el contenedor
* **Dead**: Contenedor parcialmente eliminado o inservible; no se puede reiniciar y es necesario limpiarlo

```bash
# Check container status
docker ps -a

# Detailed status of specific container
docker inspect <container-id> | jq '.[0].State'

# Container state transitions
docker create nginx  # Created state
docker start <container-id>  # Transition to Running state
docker pause <container-id>  # Transition to Paused state
docker unpause <container-id>  # Return to Running state
docker stop <container-id>  # Transition to Exited state
docker rm <container-id>  # Remove container
```

### Crear y ejecutar contenedores

```bash
# Create container only (don't start)
docker create --name my-nginx nginx

# Start container
docker start my-nginx

# Create and start container (all at once)
docker run --name my-nginx2 -d nginx

# Run in interactive mode
docker run -it ubuntu bash

# Run in background
docker run -d nginx

# Auto-remove when container exits
docker run --rm nginx

# Run with environment variables
docker run -e "DB_HOST=localhost" -e "DB_PORT=5432" myapp

# Run with port mapping
docker run -p 8080:80 nginx

# Run with volume mount
docker run -v /host/path:/container/path nginx
```

### Controlar contenedores

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop with configured signal (default SIGTERM), then SIGKILL after timeout
docker stop <container-id>

# Force kill container (SIGKILL)
docker kill <container-id>

# Restart container
docker restart <container-id>

# Pause container
docker pause <container-id>

# Resume container
docker unpause <container-id>

# Execute command in running container
docker exec -it <container-id> bash
docker exec <container-id> ls -la /app

# Copy files from/to container
docker cp <container-id>:/path/to/file /local/path
docker cp /local/path <container-id>:/path/to/file
```

### Registro y supervisión de contenedores

```bash
# View container logs
docker logs <container-id>

# Stream real-time logs
docker logs -f <container-id>

# Last N log lines
docker logs --tail 100 <container-id>

# Output logs with timestamps
docker logs -t <container-id>

# Logs since specific time
docker logs --since "2025-11-24T10:00:00" <container-id>

# Check container resource usage
docker stats <container-id>

# All container resource usage
docker stats

# Check container processes
docker top <container-id>

# Container detailed information
docker inspect <container-id>
```

### Limpieza de contenedores

```bash
# Remove all stopped containers
docker container prune

# Remove stopped containers, unused networks, dangling images and build cache; no volumes
docker system prune

# Additionally prune unused anonymous volumes; running resources are not removed
docker system prune --volumes

# Check disk usage
docker system df

# Remove image
docker rmi <image-id>

# Remove dangling images; -a includes all unused images
docker image prune

# Remove volume
docker volume rm <volume-name>

# Remove unused anonymous volumes; --all includes unused named volumes
docker volume prune

# Remove network
docker network rm <network-name>

# Remove unused networks
docker network prune
```

### Comprobaciones de estado

HEALTHCHECK registra el estado de salud de Docker. En una instalación independiente de Docker, las políticas de reinicio responden a la salida del proceso, no solo al estado de salud. Kubernetes ignora HEALTHCHECK de Dockerfile y utiliza sondas de liveness/readiness/startup.

```dockerfile
FROM nginx:1.30.6-alpine

# Define health check in Dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
```

```bash
# Define health check at runtime
docker run -d \
  --health-cmd="wget -q -O /dev/null http://127.0.0.1/ || exit 1" \
  --health-interval=30s \
  --health-timeout=3s \
  --health-retries=3 \
  nginx:1.30.6-alpine

# Check health check status
docker inspect <container-id> | jq '.[0].State.Health'
```

### Políticas de reinicio

Configura los contenedores para que se reinicien automáticamente al terminar.

```bash
# Restart policy options
# - no: Don't restart (default)
# - on-failure: Restart only on failure
# - always: Restart after exit; manual stop suppresses it until daemon restart or explicit start
# - unless-stopped: Always restart unless explicitly stopped

# Restart on failure (max 3 times)
docker run -d --restart=on-failure:3 nginx

# Always restart
docker run -d --restart=always nginx

# Restart unless explicitly stopped
docker run -d --restart=unless-stopped nginx

# Change restart policy of existing container
docker update --restart=always <container-id>
```

### Depuración de contenedores

bash/ip/netstat/ps deben estar instalados en la imagen. Para imágenes mínimas, utiliza docker inspect/top desde el host o una imagen de depuración aprobada. La salida de env o inspect puede contener secretos; no la pegues en registros compartidos.

```bash
# Explore container internal file system
docker exec -it <container-id> bash

# Check container environment variables
docker exec <container-id> env

# Check container network information
docker exec <container-id> ip addr
docker exec <container-id> netstat -tuln

# Check container processes
docker exec <container-id> ps aux

# Monitor container events
docker events

# Filter specific container events
docker events --filter container=<container-id>

# Check container changes (compared to image)
docker diff <container-id>
```

## Orquestación de contenedores {#container-orchestration}

La orquestación de contenedores es el proceso de administrar y coordinar varios contenedores. Entre sus características principales se incluyen la administración de implementaciones, el escalado, las redes y la detección de servicios.

### Principales herramientas de orquestación

1. **Kubernetes**: La plataforma de orquestación de contenedores de uso más extendido
2. **Docker Swarm**: Herramienta de orquestación integrada en Docker, con una configuración sencilla
3. **Amazon ECS**: Servicio de orquestación de contenedores de AWS
4. **HashiCorp Nomad**: Admite cargas de trabajo tanto con contenedores como sin ellos

### Características principales de la orquestación

1. **Implementación y reversión automatizadas**: Administración de la implementación de aplicaciones mediante configuración declarativa
2. **Detección de servicios y balanceo de carga**: Comunicación entre contenedores y distribución de carga
3. **Escalado automático**: Ajuste del número de contenedores según la carga
4. **Recuperación automática**: Reinicio automático de los contenedores que hayan fallado
5. **Administración de la configuración**: Administración de la configuración de aplicaciones y de secretos
6. **Orquestación del almacenamiento**: Administración del almacenamiento persistente
7. **Ejecución por lotes**: Ejecución de tareas puntuales y programadas

## Contenedores en AWS {#containers-on-aws}

AWS ofrece varios servicios para cargas de trabajo en contenedores.

### Amazon ECS (Elastic Container Service)

Servicio de orquestación de contenedores propio de AWS que puede ejecutar contenedores en instancias EC2 o en AWS Fargate.

**Características principales**:

* Integración estrecha con los servicios de AWS
* Ejecución de contenedores sin servidor (Fargate)
* Configuración y administración sencillas
* Escalado automático y balanceo de carga

### Amazon EKS (Elastic Kubernetes Service)

Servicio Kubernetes administrado por AWS que permite ejecutar Kubernetes en la infraestructura de AWS mediante las API estándar de Kubernetes.

**Características principales**:

* Plano de control de Kubernetes administrado
* Alta disponibilidad en varias zonas de disponibilidad
* Integración con los servicios de AWS
* Compatibilidad con EC2 y Fargate

### AWS Fargate

Entorno de ejecución de contenedores sin servidor que permite ejecutar contenedores sin administrar servidores.

**Características principales**:

* No es necesario administrar servidores
* La facturación se basa en los recursos solicitados para las tareas (ECS) o los recursos del Pod (EKS), no en una tarifa independiente por cada contenedor de aplicación
* Integración con ECS y EKS
* Aislamiento de seguridad

### Amazon ECR (Elastic Container Registry)

Servicio de registro de imágenes de contenedor administrado por AWS.

**Características principales**:

* Análisis de vulnerabilidades de imágenes
* Integración con IAM
* Administración del ciclo de vida de las imágenes
* Alta disponibilidad y escalabilidad

## Glosario

| Término               | Descripción                                                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Contenedor**        | Unidad de software estandarizada que empaqueta una aplicación con sus dependencias y permite ejecutarla de forma coherente en cualquier lugar. |
| **Imagen**            | Plantilla de solo lectura utilizada para crear contenedores, que contiene código de aplicación, bibliotecas, dependencias, herramientas y otros archivos. |
| **Dockerfile**        | Archivo de texto que contiene instrucciones para crear una imagen de contenedor.                                              |
| **Registro**          | Repositorio que almacena y distribuye imágenes de contenedor. (por ejemplo, Docker Hub, Amazon ECR)                            |
| **Runtime de contenedores** | Software que ejecuta contenedores. (por ejemplo, Docker, containerd, CRI-O)                                                |
| **Namespace**         | Característica del kernel de Linux que aísla procesos para que no puedan ver otras partes del sistema.                        |
| **cgroups**           | Característica del kernel de Linux que limita y supervisa el uso de recursos (CPU, memoria, etc.) de grupos de procesos.     |
| **Capa**               | Las imágenes de contenedor constan de varias capas que representan diferencias en el sistema de archivos; las instrucciones que solo contienen metadatos no necesitan una capa del sistema de archivos. |
| **Volumen**            | Mecanismo para almacenar datos de contenedor de forma persistente.                                                            |
| **Orquestación**      | Proceso de automatizar la implementación, la administración, el escalado y la configuración de red de varios contenedores.                     |
| **ECS**               | Amazon Elastic Container Service, servicio de orquestación de contenedores de AWS.                                            |
| **ECR**               | Amazon Elastic Container Registry, servicio de registro de imágenes de contenedor de AWS.                                     |
| **Fargate**           | Entorno de ejecución de contenedores sin servidor de AWS que ejecuta contenedores sin administrar la infraestructura.        |

## Conclusión

La tecnología de contenedores ha revolucionado la forma de desarrollar e implementar aplicaciones. Proporciona portabilidad, coherencia y eficiencia, mejora la productividad de los desarrolladores y reduce la complejidad operativa. Combinada con herramientas de orquestación como Kubernetes, permite administrar eficazmente aplicaciones distribuidas a gran escala.

Comprender los conceptos básicos y el funcionamiento de los contenedores es esencial para desarrollar y operar aplicaciones nativas de la nube modernas. Este conocimiento constituye la base para utilizar Kubernetes de forma eficaz.

## Cuestionario

Para poner a prueba lo que has aprendido en este capítulo, responde al [Cuestionario sobre tecnología de contenedores](../quizzes/basics/03-container-technology-quiz.md).

## Referencias

* [Documentación oficial de Docker](https://docs.docker.com/)
* [OCI (Open Container Initiative)](https://opencontainers.org/)
* [Proyecto containerd](https://containerd.io/)
* [Descripción general del runtime de contenedores de Kubernetes](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)
* [Servicios de contenedores de AWS](https://aws.amazon.com/containers/)

## Referencias de verificación

- https://kubernetes.io/docs/setup/production-environment/container-runtimes/
- https://docs.docker.com/reference/cli/docker/container/pause/
- https://docs.docker.com/reference/cli/docker/container/ls/
- https://docs.docker.com/engine/containers/start-containers-automatically/
- https://docs.docker.com/reference/cli/docker/system/prune/
- https://docs.docker.com/reference/cli/docker/volume/prune/
- https://docs.docker.com/reference/dockerfile/
- https://docs.docker.com/engine/network/drivers/bridge/
- https://docs.docker.com/engine/storage/containerd/
- https://docs.docker.com/engine/storage/tmpfs/
- https://docs.docker.com/engine/security/trust/
- https://docs.docker.com/engine/swarm/secrets/
- https://github.com/opencontainers/image-spec/blob/main/config.md
- https://github.com/opencontainers/image-spec/blob/main/manifest.md
- https://github.com/nodejs/Release/blob/main/schedule.json
- https://github.com/docker-library/official-images/blob/master/library/node
- https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md
- https://github.com/npm/cli/blob/latest/docs/lib/content/commands/npm-ci.md
- https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr
- https://man7.org/linux/man-pages/man7/cgroups.7.html
- https://github.com/torvalds/linux/releases/tag/v2.6.24
- https://docs.aws.amazon.com/eks/latest/userguide/fargate.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- https://aws.amazon.com/fargate/pricing/
