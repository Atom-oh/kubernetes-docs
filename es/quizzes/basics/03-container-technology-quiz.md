# Container Technology Quiz

Este cuestionario evalúa tu comprensión de los fundamentos de la tecnología de containers (contenedores), cómo funcionan y su relación con Kubernetes.

## Multiple Choice Questions

1. ¿Cuál de las siguientes NO es una característica clave de los containers?
   - A) Portabilidad
   - B) Ligereza
   - C) Virtualización completa del hardware
   - D) Entorno de ejecución aislado
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Virtualización completa del hardware**

**Explicación:**
Los containers comparten el kernel del OS host y no virtualizan el hardware. La virtualización completa del hardware es una característica de las virtual machines (VMs). Los containers proporcionan portabilidad, operación ligera y entornos de ejecución aislados, pero dependen del kernel del OS host para funcionar.
</details>

2. ¿Cuál es la principal diferencia entre containers y virtual machines?
   - A) Cada container requiere su propio OS independiente
   - B) Las virtual machines tienen tiempos de inicio más rápidos que los containers
   - C) Los containers comparten el kernel del OS host
   - D) Las virtual machines usan menos recursos que los containers
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Los containers comparten el kernel del OS host**

**Explicación:**
Los containers funcionan compartiendo el kernel del OS host, mientras que cada virtual machine incluye un OS completo. Como resultado, los containers son más ligeros, arrancan más rápido y son más eficientes en recursos que las virtual machines.
</details>

3. ¿Cuál de los siguientes NO es un runtime de container de bajo nivel compatible con OCI (Open Container Initiative)?
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) containerd**

**Explicación:**
containerd es un runtime de container de alto nivel que proporciona funciones como transferencia de imágenes, almacenamiento y gestión de ejecución de containers. runc, crun y gVisor son todos runtimes de container de bajo nivel compatibles con OCI, responsables de la creación y ejecución real de containers.
</details>

4. ¿Qué afirmación es correcta sobre las capas de imágenes de container?
   - A) Cada capa se puede modificar de forma independiente
   - B) Las capas siempre se fusionan y se almacenan como un único archivo
   - C) Las capas representan cambios respecto a la capa anterior
   - D) Cada container tiene su propio conjunto único de capas
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Las capas representan cambios respecto a la capa anterior**

**Explicación:**
Las imágenes de container constan de múltiples capas, y cada capa representa cambios respecto a la capa anterior. Este enfoque por capas hace que compartir imágenes y usar caché sea eficiente, ahorrando espacio de almacenamiento y mejorando las velocidades de descarga de imágenes. Las capas son de solo lectura y, cuando se ejecuta un container, se añade una capa escribible encima.
</details>

5. ¿Cuál es el propósito principal de usar compilaciones multi-stage en Dockerfiles?
   - A) Mejorar la velocidad de compilación
   - B) Reducir el tamaño de la imagen final
   - C) Reducir vulnerabilidades de seguridad
   - D) Admitir múltiples sistemas operativos
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir el tamaño de la imagen final**

**Explicación:**
El propósito principal de las compilaciones multi-stage es reducir el tamaño de la imagen final. La etapa de build incluye todas las herramientas necesarias para compilar el código fuente, instalar dependencias, etc., mientras que la etapa de ejecución lleva solo los artefactos de build para crear una imagen pequeña con un entorno de runtime mínimo. Esto excluye herramientas de build y archivos intermedios de la imagen final.
</details>

6. ¿Cuál es el driver de red predeterminado de Docker?
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) bridge**

**Explicación:**
bridge es el driver de red predeterminado de Docker, que permite la comunicación entre containers que se ejecutan en el mismo host. Este driver crea un bridge virtual dentro del host para conectar containers. El driver host usa directamente la red del host, overlay es para comunicación multi-host y macvlan asigna direcciones MAC a los containers para que parezcan dispositivos de red físicos.
</details>

7. Para el almacenamiento persistente de datos en containers, ¿qué método usa un área del sistema de archivos del host gestionada por Docker?
   - A) Almacenamiento efímero
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Volume**

**Explicación:**
Los volumes son un área del sistema de archivos del host gestionada por Docker, que es el método más adecuado para el almacenamiento persistente de datos en containers. El almacenamiento efímero es el sistema de archivos interno del container, donde los datos se pierden cuando se elimina el container. Los bind mounts montan una ruta específica del host en el container, y los tmpfs mounts almacenan datos solo en memoria.
</details>

8. ¿Cuál NO es un método para mejorar la seguridad de containers?
   - A) Ejecutar containers como usuarios non-root
   - B) Conceder solo las Linux capabilities necesarias
   - C) Conceder privilegios de administrador a todos los containers
   - D) Usar sistemas de archivos de solo lectura
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Conceder privilegios de administrador a todos los containers**

**Explicación:**
Conceder privilegios de administrador a todos los containers es una acción que debilita la seguridad. Para mejorar la seguridad de containers, debes seguir el principio de mínimo privilegio. Ejecutar containers como usuarios non-root, conceder solo las Linux capabilities necesarias y montar sistemas de archivos como solo lectura cuando sea posible son buenas prácticas de seguridad.
</details>

9. ¿Qué servicio de AWS proporciona un entorno de ejecución de containers serverless?
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon Fargate**

**Explicación:**
Amazon Fargate es el entorno de ejecución de containers serverless de AWS, que permite ejecutar containers sin gestionar servidores. Amazon EC2 es un servicio de servidores virtuales, Amazon ECS es un servicio de orquestación de containers y Amazon ECR es un servicio de registry de imágenes de container.
</details>

10. ¿Cuál NO es una función principal de las herramientas de orquestación de containers?
    - A) Despliegue y rollback automáticos
    - B) Service discovery y load balancing
    - C) Construcción de imágenes de container
    - D) Auto scaling

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Construcción de imágenes de container**

**Explicación:**
La construcción de imágenes de container suele ser responsabilidad de pipelines de CI/CD o herramientas de build de containers como Docker. Las funciones principales de las herramientas de orquestación de containers (Kubernetes, Docker Swarm, etc.) son despliegue y rollback automáticos, service discovery y load balancing, auto scaling, self-healing, gestión de configuración y orquestación de almacenamiento.
</details>

11. ¿En qué estado NO puede estar un container mientras no está en ejecución?
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Building**

**Explicación:**
Los estados del ciclo de vida de un container incluyen Created (creado), Running (en ejecución), Paused (pausado), Restarting (reiniciando), Exited (salido) y Dead (muerto). Building es un estado del proceso de build de imágenes y no es un estado de container. Los containers se crean después de construir las imágenes.
</details>

12. ¿Qué restart policy de container reinicia el container cuando se inicia el Docker daemon, pero no lo reinicia si el container se detuvo manualmente?
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) unless-stopped**

**Explicación:**
La restart policy `unless-stopped` siempre reinicia el container a menos que se haya detenido explícitamente. El container se inicia automáticamente incluso cuando el Docker daemon se reinicia, pero si el usuario lo detuvo manualmente con el comando `docker stop`, el container no se iniciará después de reiniciar el daemon. `always` reinicia sin importar el estado de parada manual.
</details>

13. ¿Qué comando de Docker comprueba los cambios del sistema de archivos entre un container y su imagen original?
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) docker diff**

**Explicación:**
El comando `docker diff` muestra los cambios entre el sistema de archivos del container y la imagen original. En la salida, A representa archivos añadidos, C representa archivos modificados y D representa archivos eliminados. Este comando es útil para depurar qué archivos se modificaron mientras el container estaba en ejecución.
</details>

## Short Answer Questions

14. ¿Cuál es el identificador único basado en el contenido de una imagen de container, expresado como un hash SHA256?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Digest**

**Explicación:**
Un digest es el hash SHA256 del contenido de la imagen de container, que sirve como identificador único de la imagen. A diferencia de los tags, si el contenido de la imagen cambia, el digest también cambia, por lo que se usa para referenciar con precisión una versión específica de la imagen. Ejemplo: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. ¿Cuál es la directiva de Dockerfile que especifica el comando que se ejecutará cuando se inicia un container?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: CMD**

**Explicación:**
La directiva CMD especifica el comando predeterminado que se ejecutará cuando se inicia un container. Por ejemplo, `CMD ["node", "server.js"]` ejecuta el comando `node server.js` cuando se inicia el container. CMD se puede sobrescribir proporcionando argumentos al comando docker run.
</details>

16. ¿Cuál es el nombre de la interfaz de red virtual que Docker crea para la comunicación entre containers?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker0**

**Explicación:**
docker0 es la interfaz de red bridge virtual que Docker crea de forma predeterminada. Este bridge permite la comunicación entre containers que se ejecutan en el mismo host y media la comunicación entre containers y redes externas.
</details>

17. ¿Cuál es la función de seguridad de Linux que restringe las llamadas al sistema que puede usar un proceso que se ejecuta dentro de un container?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: seccomp (Secure Computing Mode)**

**Explicación:**
seccomp es una función de seguridad del kernel de Linux que restringe las llamadas al sistema que puede usar un proceso. Los runtimes de container como Docker usan perfiles seccomp para restringir las llamadas al sistema que pueden realizar los containers, mejorando así la seguridad.
</details>

18. ¿Cuál es el nombre del servicio de AWS que almacena y gestiona imágenes de container?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Amazon ECR (Elastic Container Registry)**

**Explicación:**
Amazon ECR (Elastic Container Registry) es el servicio gestionado de registry de imágenes de container de AWS. Proporciona funciones como escaneo de vulnerabilidades de imágenes, integración con IAM y gestión del ciclo de vida de imágenes, y se integra sin problemas con otros servicios de AWS.
</details>

19. ¿Qué comando de Docker permite ejecutar comandos adicionales dentro de un container en ejecución?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker exec**

**Explicación:**
El comando `docker exec` permite ejecutar comandos adicionales dentro de un container en ejecución. Por ejemplo, `docker exec -it <container> bash` se conecta a una shell interactiva dentro del container, o `docker exec <container> ls /app` lista archivos dentro del container. Este comando es muy útil para depurar containers.
</details>

20. ¿Qué comando de Docker monitoriza eventos de container en tiempo real (start, stop, restart, etc.) como un stream?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker events**

**Explicación:**
El comando `docker events` muestra eventos en tiempo real del Docker daemon como un stream. Puedes monitorizar eventos como inicio, parada, reinicio de containers, pull de imágenes, conexión/desconexión de redes, etc. La opción `--filter` permite filtrar por container específico o tipo de evento, lo que es útil para depuración y monitorización.
</details>

## Hands-on Questions

21. Escribe un Dockerfile que cumpla los siguientes requisitos:
    - Usar la imagen Node.js 14 Alpine
    - Establecer el directorio de trabajo en /app
    - Copiar primero los archivos package.json y package-lock.json
    - Instalar dependencias
    - Copiar los archivos restantes
    - Exponer el puerto 3000
    - Ejecutar el comando "node server.js" cuando se inicie el container

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```dockerfile
FROM node:14-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
```

**Explicación:**
Este Dockerfile muestra una configuración básica para aplicaciones Node.js. Al copiar primero los archivos de dependencias (package*.json) e instalarlas antes de copiar los archivos restantes, optimiza el caching de capas de Docker. De esta manera, incluso si el código fuente cambia, el paso npm install puede reutilizarse si las dependencias no han cambiado.
</details>

22. Analiza el siguiente comando de Docker y explica su propósito:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Este comando se utiliza para los siguientes propósitos:
    - `-d`: Ejecutar el container en segundo plano (detached mode)
    - `--name my-app`: Establecer el nombre del container en "my-app"
    - `-p 8080:80`: Mapear el puerto 8080 del host al puerto 80 del container
    - `-v data:/app/data`: Montar un volume llamado "data" en la ruta /app/data del container
    - `--restart always`: Reiniciar siempre automáticamente cuando el container salga
    - `nginx:latest`: Usar la versión más reciente de la imagen nginx

Este comando ejecuta el servidor web nginx en segundo plano, lo hace accesible a través del puerto 8080 del host, configura un volume para almacenamiento persistente de datos y configura el reinicio automático cuando el container sale.
</details>

23. Escribe un Dockerfile optimizado para una aplicación React usando compilaciones multi-stage.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```dockerfile
# Build stage
FROM node:14 AS build

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# Run stage
FROM nginx:alpine

# Copy build artifacts to nginx's service directory
COPY --from=build /app/build /usr/share/nginx/html

# Use default nginx configuration

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Explicación:**
Este Dockerfile multi-stage consta de dos etapas:
1. Etapa de build: usa una imagen Node.js para construir la aplicación React.
2. Etapa de ejecución: usa una imagen nginx ligera para servir los archivos estáticos construidos.

La ventaja de este enfoque es que la imagen final no incluye el runtime de Node.js, paquetes npm, código fuente, etc., lo que reduce significativamente el tamaño de la imagen. La imagen final contiene solo los archivos estáticos construidos y nginx, lo que la hace más pequeña y más segura.
</details>

24. Escribe un Dockerfile que incluya health checks de container. Configúralo para comprobar el endpoint HTTP /health cada 30 segundos, tratarlo como fallido si no hay respuesta en 3 segundos y marcarlo como unhealthy después de 3 fallos.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```dockerfile
FROM nginx:alpine

# Copy application (example)
COPY ./html /usr/share/nginx/html

# Health check configuration
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Explicación:**
Significado de cada opción de la directiva HEALTHCHECK:
- `--interval=30s`: Realizar un health check cada 30 segundos
- `--timeout=3s`: El comando de health check debe completarse en 3 segundos
- `--start-period=10s`: Ignorar fallos de health check durante 10 segundos después del inicio del container (tiempo de inicialización)
- `--retries=3`: Marcar el container como unhealthy después de 3 fallos consecutivos
- `CMD`: Comando de health check que se ejecutará. Usa wget para comprobar el endpoint /health

Los health checks son usados por herramientas de orquestación de containers para determinar el estado del container para decisiones de recuperación automática o enrutamiento de tráfico.
</details>

25. Escribe comandos de Docker para comprobar las variables de entorno, la configuración de red y la lista de procesos de un container en ejecución con fines de depuración.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```bash
# 1. Check environment variables
docker exec <container-id> env

# Or use inspect
docker inspect <container-id> --format='{{range .Config.Env}}{{println .}}{{end}}'

# 2. Check network settings
docker exec <container-id> ip addr
docker exec <container-id> netstat -tuln
# or
docker exec <container-id> ss -tuln

# Check IP address only
docker inspect <container-id> --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# 3. Check process list
docker exec <container-id> ps aux
# or
docker top <container-id>

# 4. Additional useful debugging commands
# Container detailed information
docker inspect <container-id>

# Container logs
docker logs <container-id>

# File system changes
docker diff <container-id>

# Real-time resource usage
docker stats <container-id>
```

**Explicación:**
Al depurar containers, combina estos comandos para diagnosticar problemas:
- `docker exec` ejecuta comandos en un container en ejecución
- `docker inspect` comprueba metadatos detallados del container
- `docker top` muestra los procesos del container desde la perspectiva del host
- `docker diff` comprueba archivos modificados en comparación con la imagen
Usar estas herramientas de forma efectiva ayuda a comprender el estado interno del container y resolver problemas.
</details>

## Advanced Questions

26. Compara los roles de namespaces y cgroups, los componentes principales de la tecnología de containers, y explica cómo contribuye cada uno al aislamiento de containers.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Namespaces**:
    - **Role**: Aísla grupos de procesos para que cada grupo pueda ver los recursos del sistema de forma independiente.
    - **Isolation type**: Proporciona aislamiento de visibilidad.
    - **Main namespaces**:
    - PID namespace: Aislamiento de ID de procesos
    - Network namespace: Aislamiento de stack de red
    - Mount namespace: Aislamiento de puntos de montaje del sistema de archivos
    - UTS namespace: Aislamiento de hostname y nombre de dominio
    - IPC namespace: Aislamiento de recursos de comunicación entre procesos
    - User namespace: Aislamiento de ID de usuarios y grupos

**cgroups (Control Groups)**:
    - **Role**: Limita y aísla el uso de recursos de grupos de procesos.
    - **Isolation type**: Proporciona limitación de recursos.
    - **Main functions**:
    - Limitación de tiempo de CPU
    - Limitación de uso de memoria
    - Limitación de ancho de banda de Block I/O
    - Limitación de ancho de banda de red
    - Control de acceso a dispositivos

**Contribución al aislamiento de containers**:

Namespaces y cgroups cumplen roles complementarios:

    - Namespaces permite que los containers tengan sus propios entornos independientes (árboles de procesos, interfaces de red, puntos de montaje, etc.), proporcionando aislamiento lógico. Esto da a cada container su propia vista única del sistema.

    - cgroups limita los recursos del sistema (CPU, memoria, disk I/O, etc.) que pueden usar los containers, proporcionando aislamiento de recursos físicos. Esto evita que un container use recursos excesivos y afecte a otros containers o al sistema host.

Estas dos tecnologías trabajan juntas para permitir que los containers se ejecuten en entornos aislados con uso limitado de recursos. Este aislamiento es más ligero que el de las virtual machines, pero proporciona aislamiento suficiente para seguridad y gestión de recursos.
</details>

27. Explica cómo funciona el sistema de capas de imágenes de container y cómo la estrategia Copy-on-Write (CoW) contribuye a la eficiencia de containers.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Container Image Layering System**:

Las imágenes de container constan de una pila de múltiples capas. Cada capa representa cambios del sistema de archivos, y cada comando de Dockerfile (FROM, RUN, COPY, etc.) crea una nueva capa. Estas capas son de solo lectura y se apilan jerárquicamente para formar la imagen final.

Características clave del sistema de capas:
1. **Incremental builds**: Solo las capas cambiadas se regeneran durante los builds de imágenes
2. **Layer sharing**: Múltiples imágenes comparten las mismas capas base
3. **Caching**: Las capas ya descargadas se reutilizan

**Copy-on-Write (CoW) Strategy**:

Copy-on-Write es una estrategia de optimización que retrasa las operaciones de copia hasta que los datos se modifican realmente. En el contexto de containers:

1. **Container start**: Cuando un container se inicia, se añade una capa escribible delgada encima de las capas de imagen existentes.
2. **Read operations**: Al leer un archivo, el sistema busca en las capas de arriba hacia abajo y usa la primera versión del archivo que encuentra.
3. **Write operations**: Al modificar un archivo, primero se copia el archivo a la capa escribible y luego se modifica (Copy-on-Write). El archivo original permanece sin cambios.
4. **Delete operations**: Al eliminar un archivo, el archivo no se elimina realmente; en su lugar, se crea un archivo "whiteout" en la capa escribible para que parezca eliminado.

**Contribución a la eficiencia**:

1. **Storage efficiency**: 
    - Múltiples containers que usan la misma imagen base comparten capas de imagen, ahorrando espacio en disco.
    - Cada container solo necesita almacenar sus propios datos modificados.

2. **Faster startup time**:
    - Al iniciar un nuevo container, solo es necesario crear la capa escribible, no copiar todo el sistema de archivos.
    - Esto reduce significativamente el tiempo de inicio del container.

3. **Memory efficiency**:
    - Cuando varios containers usan el mismo archivo, se puede compartir el page cache.

4. **Network efficiency**:
    - Las capas que ya existen no necesitan descargarse de nuevo durante la descarga de la imagen.

Gracias a estas eficiencias, los containers pueden iniciarse de forma más ligera y rápida que las virtual machines, y se pueden ejecutar más containers en el mismo host.
</details>

28. Explica todo el ciclo de vida de un container y describe el comportamiento del container y los métodos de transición de estado en cada estado (Created, Running, Paused, Restarting, Exited, Dead).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Container Lifecycle States:**

1. **Created**
   - El container ha sido creado, pero aún no se ha iniciado
   - Creado con el comando `docker create`
   - Proceso no en ejecución, asignación mínima de recursos
   - Transición: `docker start` → Running

2. **Running**
   - El proceso principal del container está en ejecución
   - Se entra mediante `docker run` o `docker start`
   - Usa activamente recursos como CPU y memoria
   - Transiciones:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - Al terminar el proceso → Exited

3. **Paused**
   - Todos los procesos pausados con SIGSTOP
   - Se entra mediante el comando `docker pause`
   - La memoria se mantiene, pero no hay uso de CPU
   - Transición: `docker unpause` → Running

4. **Restarting**
   - Estado temporal mientras el container se reinicia
   - Ocurre mediante `docker restart` o restart policy
   - Transición: pasa automáticamente a Running o Exited

5. **Exited**
   - El proceso principal ha terminado
   - Se conserva el código de salida
   - Se mantienen los cambios del sistema de archivos
   - Transiciones:
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - Estado anómalo en el que falló el intento de eliminación del container
   - Limpieza de recursos no completada
   - Generalmente requiere intervención manual
   - Intentar eliminación forzada con `docker rm -f`

**Comandos de comprobación y gestión de estado:**
```bash
# Check state
docker ps -a                    # List all containers
docker inspect <id> | jq '.[0].State'  # Detailed state

# State transitions
docker create nginx             # → Created
docker start <id>               # → Running
docker pause <id>               # → Paused
docker unpause <id>             # → Running
docker stop <id>                # → Exited
docker restart <id>             # → Running
docker rm <id>                  # Delete
```

**Restart policies y ciclo de vida:**
- `no`: Sin reinicio automático
- `on-failure[:max]`: Reiniciar en una salida anómala; se puede especificar un recuento máximo
- `always`: Reiniciar siempre (incluido el reinicio del daemon)
- `unless-stopped`: Reiniciar siempre hasta que se detenga manualmente

Comprender el ciclo de vida de containers ayuda a garantizar la disponibilidad de la aplicación y a establecer estrategias de recuperación adecuadas cuando ocurren problemas.
</details>

---

[Volver a los materiales de aprendizaje](../../basics/03-container-technology.md) | [Siguiente cuestionario: Kubernetes Introduction](./04-kubernetes-introduction-quiz.md)
