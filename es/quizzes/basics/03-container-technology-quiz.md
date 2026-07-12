# Container Technology Quiz

Este cuestionario evalúa tu comprensión de los fundamentos de la tecnología de contenedores, cómo funcionan y su relación con Kubernetes.

## Multiple Choice Questions

1. ¿Cuál de las siguientes NO es una característica clave de los contenedores?
   - A) Portabilidad
   - B) Ligereza
   - C) Virtualización completa del hardware
   - D) Entorno de ejecución aislado
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Virtualización completa del hardware**

**Explicación:**
Los contenedores comparten el kernel del sistema operativo host y no virtualizan el hardware. La virtualización completa del hardware es una característica de las máquinas virtuales (VM). Los contenedores proporcionan portabilidad, operación ligera y entornos de ejecución aislados, pero dependen del kernel del sistema operativo host para funcionar.
</details>

2. ¿Cuál es la principal diferencia entre los contenedores y las máquinas virtuales?
   - A) Cada contenedor requiere su propio sistema operativo independiente
   - B) Las máquinas virtuales tienen tiempos de inicio más rápidos que los contenedores
   - C) Los contenedores comparten el kernel del sistema operativo host
   - D) Las máquinas virtuales usan menos recursos que los contenedores
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Los contenedores comparten el kernel del sistema operativo host**

**Explicación:**
Los contenedores funcionan compartiendo el kernel del sistema operativo host, mientras que cada máquina virtual incluye un sistema operativo completo. Como resultado, los contenedores son más ligeros, arrancan más rápido y son más eficientes en el uso de recursos que las máquinas virtuales.
</details>

3. ¿Cuál de los siguientes NO es un runtime de contenedores de bajo nivel compatible con OCI (Open Container Initiative)?
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) containerd**

**Explicación:**
containerd es un runtime de contenedores de alto nivel que proporciona funciones como transferencia de imágenes, almacenamiento y administración de la ejecución de contenedores. runc, crun y gVisor son runtimes de contenedores de bajo nivel compatibles con OCI responsables de la creación y ejecución reales de contenedores.
</details>

4. ¿Qué afirmación es correcta sobre las capas de las imágenes de contenedor?
   - A) Cada capa puede modificarse de forma independiente
   - B) Las capas siempre se fusionan y se almacenan como un único archivo
   - C) Las capas representan cambios respecto a la capa anterior
   - D) Cada contenedor tiene su propio conjunto único de capas
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Las capas representan cambios respecto a la capa anterior**

**Explicación:**
Las imágenes de contenedor constan de varias capas, y cada capa representa cambios respecto a la capa anterior. Este enfoque por capas hace que compartir imágenes y usar caché sea eficiente, ahorrando espacio de almacenamiento y mejorando las velocidades de descarga de imágenes. Las capas son de solo lectura y, cuando se ejecuta un contenedor, se añade una capa escribible encima.
</details>

5. ¿Cuál es el propósito principal de usar compilaciones multi-stage en Dockerfiles?
   - A) Mejorar la velocidad de compilación
   - B) Reducir el tamaño final de la imagen
   - C) Reducir vulnerabilidades de seguridad
   - D) Compatibilidad con varios sistemas operativos
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir el tamaño final de la imagen**

**Explicación:**
El propósito principal de las compilaciones multi-stage es reducir el tamaño final de la imagen. La etapa de build incluye todas las herramientas necesarias para la compilación del código fuente, la instalación de dependencias, etc., mientras que la etapa de ejecución lleva solo los artefactos de build para crear una imagen pequeña con un entorno de runtime mínimo. Esto excluye las herramientas de build y los archivos intermedios de la imagen final.
</details>

6. ¿Cuál es el controlador de red predeterminado de Docker?
   - A) host
   - B) bridge
   - C) overlay
   - D) macvlan
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) bridge**

**Explicación:**
bridge es el controlador de red predeterminado de Docker, que permite la comunicación entre contenedores que se ejecutan en el mismo host. Este controlador crea un bridge virtual dentro del host para conectar contenedores. El controlador host usa directamente la red del host, overlay es para comunicación entre varios hosts y macvlan asigna direcciones MAC a los contenedores para que aparezcan como dispositivos de red físicos.
</details>

7. Para el almacenamiento persistente de datos en contenedores, ¿qué método usa un área del sistema de archivos del host administrada por Docker?
   - A) Almacenamiento efímero
   - B) Volume
   - C) Bind mount
   - D) tmpfs mount
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Volume**

**Explicación:**
Los volúmenes son un área del sistema de archivos del host administrada por Docker, que es el método más adecuado para el almacenamiento persistente de datos en contenedores. El almacenamiento efímero es el sistema de archivos interno del contenedor, donde los datos se pierden cuando se elimina el contenedor. Los bind mounts montan una ruta específica del host dentro del contenedor, y los tmpfs mounts almacenan datos solo en memoria.
</details>

8. ¿Cuál NO es un método para mejorar la seguridad de los contenedores?
   - A) Ejecutar contenedores como usuarios no root
   - B) Conceder solo las capacidades de Linux necesarias
   - C) Conceder privilegios de administrador a todos los contenedores
   - D) Usar sistemas de archivos de solo lectura
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Conceder privilegios de administrador a todos los contenedores**

**Explicación:**
Conceder privilegios de administrador a todos los contenedores es una acción que debilita la seguridad. Para mejorar la seguridad de los contenedores, debes seguir el principio de privilegio mínimo. Ejecutar contenedores como usuarios no root, conceder solo las capacidades de Linux necesarias y montar sistemas de archivos como solo lectura cuando sea posible son buenas prácticas de seguridad.
</details>

9. ¿Qué servicio de AWS proporciona un entorno serverless de ejecución de contenedores?
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon Fargate**

**Explicación:**
Amazon Fargate es el entorno serverless de ejecución de contenedores de AWS, que permite ejecutar contenedores sin administrar servidores. Amazon EC2 es un servicio de servidores virtuales, Amazon ECS es un servicio de orquestación de contenedores y Amazon ECR es un servicio de registro de imágenes de contenedor.
</details>

10. ¿Cuál NO es una función principal de las herramientas de orquestación de contenedores?
    - A) Despliegue y rollback automáticos
    - B) Service discovery y balanceo de carga
    - C) Construcción de imágenes de contenedor
    - D) Auto scaling

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Construcción de imágenes de contenedor**

**Explicación:**
La construcción de imágenes de contenedor suele ser responsabilidad de los pipelines de CI/CD o de herramientas de build de contenedores como Docker. Las funciones principales de las herramientas de orquestación de contenedores (Kubernetes, Docker Swarm, etc.) son el despliegue y rollback automáticos, service discovery y balanceo de carga, auto scaling, self-healing, gestión de configuración y orquestación de almacenamiento.
</details>

11. ¿En qué estado NO puede estar un contenedor mientras no se está ejecutando?
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Building**

**Explicación:**
Los estados del ciclo de vida de un contenedor incluyen Created (creado), Running (en ejecución), Paused (pausado), Restarting (reiniciando), Exited (salido) y Dead (muerto). Building es un estado del proceso de construcción de imágenes y no es un estado de contenedor. Los contenedores se crean después de que se construyen las imágenes.
</details>

12. ¿Qué política de reinicio de contenedores reinicia el contenedor cuando se inicia el daemon de Docker, pero no lo reinicia si el contenedor se detuvo manualmente?
    - A) no
    - B) on-failure
    - C) always
    - D) unless-stopped

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) unless-stopped**

**Explicación:**
La política de reinicio `unless-stopped` siempre reinicia el contenedor a menos que se haya detenido explícitamente. El contenedor se inicia automáticamente incluso cuando se reinicia el daemon de Docker, pero si el usuario lo detuvo manualmente con el comando `docker stop`, el contenedor no se iniciará después del reinicio del daemon. `always` reinicia independientemente del estado de detención manual.
</details>

13. ¿Qué comando de Docker verifica los cambios del sistema de archivos entre un contenedor y su imagen original?
    - A) docker inspect
    - B) docker diff
    - C) docker logs
    - D) docker history

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) docker diff**

**Explicación:**
El comando `docker diff` muestra los cambios entre el sistema de archivos del contenedor y la imagen original. En la salida, A representa archivos Added, C representa archivos Changed y D representa archivos Deleted. Este comando es útil para depurar qué archivos se modificaron mientras el contenedor estaba en ejecución.
</details>

## Short Answer Questions

14. ¿Cuál es el identificador único basado en el contenido de una imagen de contenedor, expresado como un hash SHA256?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Digest**

**Explicación:**
Un digest es el hash SHA256 del contenido de la imagen de contenedor y sirve como identificador único de la imagen. A diferencia de las tags, si el contenido de la imagen cambia, el digest también cambia, por lo que se usa para referenciar con precisión una versión específica de la imagen. Ejemplo: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. ¿Cuál es la directiva de Dockerfile que especifica el comando que se ejecutará cuando se inicie un contenedor?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: CMD**

**Explicación:**
La directiva CMD especifica el comando predeterminado que se ejecutará cuando se inicie un contenedor. Por ejemplo, `CMD ["node", "server.js"]` ejecuta el comando `node server.js` cuando se inicia el contenedor. CMD se puede sobrescribir proporcionando argumentos al comando docker run.
</details>

16. ¿Cuál es el nombre de la interfaz de red virtual que Docker crea para la comunicación entre contenedores?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker0**

**Explicación:**
docker0 es la interfaz de red bridge virtual que Docker crea de forma predeterminada. Este bridge permite la comunicación entre contenedores que se ejecutan en el mismo host y media la comunicación entre contenedores y redes externas.
</details>

17. ¿Cuál es la característica de seguridad de Linux que restringe las llamadas al sistema que puede usar un proceso que se ejecuta dentro de un contenedor?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: seccomp (Secure Computing Mode)**

**Explicación:**
seccomp es una característica de seguridad del kernel de Linux que restringe las llamadas al sistema que puede usar un proceso. Los runtimes de contenedores como Docker usan perfiles seccomp para restringir las llamadas al sistema que los contenedores pueden realizar, mejorando así la seguridad.
</details>

18. ¿Cuál es el nombre del servicio de AWS que almacena y administra imágenes de contenedor?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Amazon ECR (Elastic Container Registry)**

**Explicación:**
Amazon ECR (Elastic Container Registry) es el servicio administrado de registro de imágenes de contenedor de AWS. Proporciona características como análisis de vulnerabilidades de imágenes, integración con IAM y administración del ciclo de vida de imágenes, y se integra sin problemas con otros servicios de AWS.
</details>

19. ¿Qué comando de Docker permite ejecutar comandos adicionales dentro de un contenedor en ejecución?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker exec**

**Explicación:**
El comando `docker exec` permite ejecutar comandos adicionales dentro de un contenedor en ejecución. Por ejemplo, `docker exec -it <container> bash` se conecta a una shell interactiva dentro del contenedor, o `docker exec <container> ls /app` lista archivos dentro del contenedor. Este comando es muy útil para depurar contenedores.
</details>

20. ¿Qué comando de Docker monitorea eventos de contenedor en tiempo real (inicio, detención, reinicio, etc.) como un stream?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker events**

**Explicación:**
El comando `docker events` muestra eventos en tiempo real del daemon de Docker como un stream. Puedes monitorear eventos como inicio, detención y reinicio de contenedores, descarga de imágenes, conexión/desconexión de red, etc. La opción `--filter` permite filtrar por contenedor específico o tipo de evento, lo que es útil para depuración y monitoreo.
</details>

## Hands-on Questions

21. Escribe un Dockerfile que cumpla los siguientes requisitos:
    - Usar la imagen Node.js 14 Alpine
    - Establecer el directorio de trabajo en /app
    - Copiar primero los archivos package.json y package-lock.json
    - Instalar dependencias
    - Copiar los archivos restantes
    - Exponer el puerto 3000
    - Ejecutar el comando "node server.js" cuando se inicie el contenedor

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
Este Dockerfile muestra una configuración básica para aplicaciones Node.js. Al copiar primero los archivos de dependencias (package*.json) e instalarlas antes de copiar los archivos restantes, optimiza el almacenamiento en caché de capas de Docker. De esta forma, incluso si cambia el código fuente, el paso npm install puede reutilizarse si las dependencias no han cambiado.
</details>

22. Analiza el siguiente comando de Docker y explica su propósito:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Este comando se usa para los siguientes propósitos:
    - `-d`: Ejecutar el contenedor en segundo plano (modo detached)
    - `--name my-app`: Establecer el nombre del contenedor en "my-app"
    - `-p 8080:80`: Mapear el puerto 8080 del host al puerto 80 del contenedor
    - `-v data:/app/data`: Montar un volumen llamado "data" en la ruta /app/data dentro del contenedor
    - `--restart always`: Reiniciar automáticamente siempre que el contenedor salga
    - `nginx:latest`: Usar la versión más reciente de la imagen nginx

Este comando ejecuta el servidor web nginx en segundo plano, lo hace accesible a través del puerto 8080 del host, configura un volumen para almacenamiento persistente de datos y configura el reinicio automático cuando el contenedor sale.
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
1. Etapa de build: Usa la imagen Node.js para construir la aplicación React.
2. Etapa de ejecución: Usa la imagen ligera nginx para servir los archivos estáticos construidos.

La ventaja de este enfoque es que la imagen final no incluye el runtime de Node.js, paquetes npm, código fuente, etc., lo que reduce significativamente el tamaño de la imagen. La imagen final contiene solo los archivos estáticos construidos y nginx, por lo que es más pequeña y segura.
</details>

24. Escribe un Dockerfile que incluya health checks de contenedor. Configúralo para comprobar el endpoint HTTP /health cada 30 segundos, tratarlo como fallido si no hay respuesta en 3 segundos y marcarlo como unhealthy después de 3 fallos.

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
- `--interval=30s`: Realizar el health check cada 30 segundos
- `--timeout=3s`: El comando de health check debe completarse en 3 segundos
- `--start-period=10s`: Ignorar fallos de health check durante 10 segundos después del inicio del contenedor (tiempo de inicialización)
- `--retries=3`: Marcar el contenedor como unhealthy después de 3 fallos consecutivos
- `CMD`: Comando de health check que se ejecutará. Usa wget para comprobar el endpoint /health

Las health checks son usadas por herramientas de orquestación de contenedores para determinar el estado del contenedor para decisiones de recuperación automática o enrutamiento de tráfico.
</details>

25. Escribe comandos de Docker para comprobar las variables de entorno, la configuración de red y la lista de procesos de un contenedor en ejecución con fines de depuración.

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
Al depurar contenedores, combina estos comandos para diagnosticar problemas:
- `docker exec` ejecuta comandos en un contenedor en ejecución
- `docker inspect` comprueba metadatos detallados del contenedor
- `docker top` muestra los procesos del contenedor desde la perspectiva del host
- `docker diff` comprueba archivos modificados en comparación con la imagen
Usar estas herramientas de forma eficaz ayuda a comprender el estado interno del contenedor y resolver problemas.
</details>

## Advanced Questions

26. Compara los roles de namespaces y cgroups, los componentes principales de la tecnología de contenedores, y explica cómo contribuye cada uno al aislamiento de contenedores.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Namespaces**:
    - **Rol**: Aísla grupos de procesos para que cada grupo pueda ver los recursos del sistema de forma independiente.
    - **Tipo de aislamiento**: Proporciona aislamiento de visibilidad.
    - **Namespaces principales**:
    - PID namespace: Aislamiento de ID de proceso
    - Network namespace: Aislamiento de la pila de red
    - Mount namespace: Aislamiento de puntos de montaje del sistema de archivos
    - UTS namespace: Aislamiento de hostname y nombre de dominio
    - IPC namespace: Aislamiento de recursos de comunicación entre procesos
    - User namespace: Aislamiento de ID de usuario y grupo

**cgroups (Control Groups)**:
    - **Rol**: Limita y aísla el uso de recursos de grupos de procesos.
    - **Tipo de aislamiento**: Proporciona limitación de recursos.
    - **Funciones principales**:
    - Limitación de tiempo de CPU
    - Limitación de uso de memoria
    - Limitación de ancho de banda de Block I/O
    - Limitación de ancho de banda de red
    - Control de acceso a dispositivos

**Contribución al aislamiento de contenedores**:

Namespaces y cgroups desempeñan roles complementarios:

    - Namespaces permite que los contenedores tengan sus propios entornos independientes (árboles de procesos, interfaces de red, puntos de montaje, etc.), proporcionando aislamiento lógico. Esto da a cada contenedor su propia vista única del sistema.

    - cgroups limita los recursos del sistema (CPU, memoria, I/O de disco, etc.) que los contenedores pueden usar, proporcionando aislamiento de recursos físicos. Esto evita que un contenedor use recursos excesivos y afecte a otros contenedores o al sistema host.

Estas dos tecnologías trabajan juntas para permitir que los contenedores se ejecuten en entornos aislados con uso limitado de recursos. Este aislamiento es más ligero que el de las máquinas virtuales, pero proporciona aislamiento suficiente para seguridad y administración de recursos.
</details>

27. Explica cómo funciona el sistema de capas de imágenes de contenedor y cómo la estrategia Copy-on-Write (CoW) contribuye a la eficiencia de los contenedores.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Sistema de capas de imágenes de contenedor**:

Las imágenes de contenedor constan de una pila de varias capas. Cada capa representa cambios del sistema de archivos, y cada comando de Dockerfile (FROM, RUN, COPY, etc.) crea una nueva capa. Estas capas son de solo lectura y se apilan jerárquicamente para formar la imagen final.

Características clave del sistema de capas:
1. **Builds incrementales**: Solo las capas modificadas se regeneran durante las construcciones de imágenes
2. **Compartición de capas**: Varias imágenes comparten las mismas capas base
3. **Caché**: Las capas ya descargadas se reutilizan

**Estrategia Copy-on-Write (CoW)**:

Copy-on-Write es una estrategia de optimización que retrasa las operaciones de copia hasta que los datos se modifican realmente. En el contexto de contenedores:

1. **Inicio del contenedor**: Cuando se inicia un contenedor, se añade una capa escribible delgada encima de las capas de imagen existentes.
2. **Operaciones de lectura**: Al leer un archivo, el sistema busca en las capas de arriba hacia abajo y usa la primera versión del archivo encontrada.
3. **Operaciones de escritura**: Al modificar un archivo, primero se copia el archivo a la capa escribible y luego se modifica (Copy-on-Write). El archivo original permanece sin cambios.
4. **Operaciones de eliminación**: Al eliminar un archivo, el archivo no se elimina realmente; en su lugar, se crea un archivo "whiteout" en la capa escribible para hacer que parezca eliminado.

**Contribución a la eficiencia**:

1. **Eficiencia de almacenamiento**: 
    - Varios contenedores que usan la misma imagen base comparten capas de imagen, ahorrando espacio en disco.
    - Cada contenedor solo necesita almacenar sus propios datos modificados.

2. **Tiempo de inicio más rápido**:
    - Al iniciar un nuevo contenedor, solo se debe crear la capa escribible, no copiar todo el sistema de archivos.
    - Esto reduce significativamente el tiempo de inicio del contenedor.

3. **Eficiencia de memoria**:
    - Cuando varios contenedores usan el mismo archivo, la caché de páginas puede compartirse.

4. **Eficiencia de red**:
    - Las capas ya existentes no necesitan descargarse de nuevo durante la descarga de imágenes.

Gracias a estas eficiencias, los contenedores pueden iniciar de forma más ligera y rápida que las máquinas virtuales, y pueden ejecutarse más contenedores en el mismo host.
</details>

28. Explica todo el ciclo de vida de un contenedor y describe el comportamiento del contenedor y los métodos de transición de estado en cada estado (Created, Running, Paused, Restarting, Exited, Dead).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Estados del ciclo de vida del contenedor:**

1. **Created**
   - El contenedor se ha creado, pero aún no se ha iniciado
   - Creado con el comando `docker create`
   - El proceso no está en ejecución, asignación mínima de recursos
   - Transición: `docker start` → Running

2. **Running**
   - El proceso principal del contenedor está en ejecución
   - Se entra mediante `docker run` o `docker start`
   - Usa activamente recursos como CPU y memoria
   - Transiciones:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → Restarting → Running
     - Al terminar el proceso → Exited

3. **Paused**
   - Todos los procesos están pausados con SIGSTOP
   - Se entra mediante el comando `docker pause`
   - La memoria se mantiene, pero no hay uso de CPU
   - Transición: `docker unpause` → Running

4. **Restarting**
   - Estado temporal mientras el contenedor se reinicia
   - Ocurre mediante `docker restart` o una política de reinicio
   - Transición: Cambia automáticamente a Running o Exited

5. **Exited**
   - El proceso principal ha terminado
   - Se conserva el código de salida
   - Se mantienen los cambios del sistema de archivos
   - Transiciones:
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - Estado anómalo en el que falló el intento de eliminación del contenedor
   - Limpieza de recursos no completada
   - Generalmente requiere intervención manual
   - Intentar eliminación forzada con `docker rm -f`

**Comandos de verificación y administración de estado:**
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

**Políticas de reinicio y ciclo de vida:**
- `no`: Sin reinicio automático
- `on-failure[:max]`: Reiniciar en caso de salida anómala; se puede especificar un número máximo
- `always`: Reiniciar siempre (incluido el reinicio del daemon)
- `unless-stopped`: Reiniciar siempre hasta que se detenga manualmente

Comprender el ciclo de vida de los contenedores ayuda a garantizar la disponibilidad de las aplicaciones y a establecer estrategias de recuperación adecuadas cuando ocurren problemas.
</details>

---

[Volver a los materiales de aprendizaje](../../basics/03-container-technology.md) | [Siguiente cuestionario: Kubernetes Introduction](./04-kubernetes-introduction-quiz.md)
