# Cuestionario sobre tecnología de contenedores

Este cuestionario evalúa los fundamentos de la tecnología de contenedores, su funcionamiento y su relación con Kubernetes.

Responde pensando en contenedores Linux aislados mediante procesos. Los entornos de ejecución respaldados por máquinas virtuales, como Kata o Fargate, y la compatibilidad con Windows presentan diferencias.

## Preguntas de opción múltiple

1. ¿Cuál de las siguientes NO es una característica clave de los contenedores?
   - A) Portabilidad
   - B) Ligereza
   - C) Virtualización completa del hardware
   - D) Entorno de ejecución aislado
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Virtualización completa del hardware**

**Explicación:**
Los contenedores comparten el núcleo del sistema operativo anfitrión y no virtualizan el hardware. La virtualización completa del hardware es una característica de las máquinas virtuales (VM). Los contenedores son portátiles y ligeros, ofrecen entornos de ejecución aislados y dependen del núcleo del sistema operativo anfitrión.
</details>

2. ¿Cuál es la principal diferencia entre los contenedores y las máquinas virtuales?
   - A) Cada contenedor necesita su propio sistema operativo independiente
   - B) Las máquinas virtuales arrancan más rápido que los contenedores
   - C) Los contenedores comparten el núcleo del sistema operativo anfitrión
   - D) Las máquinas virtuales usan menos recursos que los contenedores
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Los contenedores comparten el núcleo del sistema operativo anfitrión**

**Explicación:**
Los contenedores comparten el núcleo del sistema operativo anfitrión, mientras que cada máquina virtual incluye un sistema operativo completo. Como resultado, los contenedores son más ligeros, arrancan más rápido y son más eficientes en el uso de recursos que las máquinas virtuales.
</details>

3. ¿Cuál de los siguientes no es un entorno de ejecución de contenedores de bajo nivel compatible con OCI (Open Container Initiative)?
   - A) runc
   - B) crun
   - C) containerd
   - D) gVisor
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) containerd**

**Explicación:**
containerd es un entorno de ejecución de contenedores de alto nivel que ofrece funciones como transferir y almacenar imágenes y gestionar el ciclo de vida de los contenedores. runc, crun y gVisor son entornos de ejecución de bajo nivel compatibles con OCI, responsables de crear y ejecutar los contenedores.
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

5. ¿Cuál es el propósito principal de usar compilaciones de varias etapas en los Dockerfiles?
   - A) Mejorar la velocidad de compilación
   - B) Reducir el tamaño final de la imagen
   - C) Reducir vulnerabilidades de seguridad
   - D) Compatibilidad con varios sistemas operativos
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Reducir el tamaño final de la imagen**

**Explicación:**
El propósito principal de las compilaciones de varias etapas es reducir el tamaño de la imagen final. La fase de compilación incluye las herramientas necesarias para compilar el código e instalar sus dependencias; la fase de ejecución incorpora solo los artefactos necesarios y un entorno mínimo. Así, la imagen final no contiene las herramientas de compilación ni los archivos intermedios.
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
El controlador `bridge` es la red predeterminada de Docker y permite la comunicación entre contenedores del mismo anfitrión. Crea un puente virtual que los conecta. El controlador `host` usa directamente la red del anfitrión; `overlay` permite la comunicación entre varios anfitriones, y `macvlan` asigna direcciones MAC para que los contenedores aparezcan como dispositivos físicos de red.
</details>

7. Para conservar datos de los contenedores, ¿qué método usa un área del sistema de archivos del anfitrión que administra Docker?
   - A) Almacenamiento efímero
   - B) Volumen
   - C) Montaje enlazado
   - D) Montaje tmpfs
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Volumen**

**Explicación:**
Los volúmenes son áreas del sistema de archivos del anfitrión administradas por Docker y suelen ser la opción más adecuada para conservar datos de contenedores. El almacenamiento efímero es el sistema de archivos interno del contenedor, donde los datos se pierden cuando se elimina el contenedor. Los montajes enlazados conectan una ruta específica del anfitrión al contenedor. Los montajes `tmpfs` usan almacenamiento respaldado por memoria, aunque el sistema puede intercambiar páginas a swap.
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

9. ¿Qué servicio de AWS ofrece un entorno sin servidor para ejecutar contenedores?
   - A) Amazon EC2
   - B) Amazon ECS
   - C) Amazon Fargate
   - D) Amazon ECR
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon Fargate**

**Explicación:**
Amazon Fargate permite ejecutar contenedores en AWS sin administrar servidores. Amazon EC2 ofrece servidores virtuales, Amazon ECS es un servicio de orquestación de contenedores y Amazon ECR es un registro de imágenes de contenedor.
</details>

10. ¿Cuál NO es una función principal de las herramientas de orquestación de contenedores?
    - A) Despliegue y reversión automáticos
    - B) Detección de servicios y balanceo de carga
    - C) Construcción de imágenes de contenedor
    - D) Escalado automático

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Construcción de imágenes de contenedor**

**Explicación:**
La creación de imágenes de contenedor suele corresponder a los procesos de CI/CD o a herramientas como Docker. Las funciones principales de los orquestadores (Kubernetes, Docker Swarm y otros) incluyen despliegue y reversión automáticos, detección de servicios y balanceo de carga, escalado automático, recuperación automática, gestión de configuración y orquestación del almacenamiento.
</details>

11. ¿Cuál de los siguientes no es un estado del ciclo de vida de un contenedor Docker?
    - A) Created
    - B) Exited
    - C) Building
    - D) Paused

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Building**

**Explicación:**
Los estados del ciclo de vida de un contenedor incluyen Created, Running, Paused, Restarting, Exited, Removing y Dead. Building corresponde al proceso de crear una imagen, no a un estado del contenedor; los contenedores se crean a partir de imágenes ya construidas.
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
La política `unless-stopped` vuelve a iniciar el contenedor automáticamente, incluso después de reiniciar el daemon de Docker, salvo que se lo haya detenido manualmente con `docker stop`; esa detención se mantiene después del reinicio del daemon. Con `always`, en cambio, una detención manual suprime los reinicios solo hasta que se reinicia el daemon o se inicia el contenedor explícitamente.
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
El comando `docker diff` muestra los cambios entre el sistema de archivos del contenedor y la imagen original. En la salida, A indica archivos añadidos, C archivos modificados y D archivos eliminados. Este comando es útil para depurar qué archivos se modificaron mientras el contenedor estaba en ejecución.
</details>

## Preguntas de respuesta breve

14. ¿Cuál es el identificador único basado en el contenido de una imagen de contenedor, expresado como un hash SHA256?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Digest**

**Explicación:**
El digest de una referencia de imagen identifica los bytes del manifiesto o del índice para varias plataformas, normalmente mediante SHA256; el manifiesto, a su vez, referencia los digest de las capas y la configuración. A diferencia de una etiqueta, el digest identifica con precisión esos bytes. Ejemplo: `nginx@sha256:2834dc507516af02784808c5f48b7cbe38b8ed5d0f4837f16e78d00deb7e7767`
</details>

15. ¿Cuál es la directiva de Dockerfile que especifica el comando que se ejecutará cuando se inicie un contenedor?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: CMD**

**Explicación:**
La directiva CMD especifica el comando predeterminado que se ejecutará cuando se inicie un contenedor. Por ejemplo, `CMD ["node", "server.js"]` ejecuta el comando `node server.js` cuando se inicia el contenedor. CMD se puede sobrescribir proporcionando argumentos al comando docker run.
</details>

16. ¿Cómo se llama la interfaz de red virtual que Docker crea para que se comuniquen los contenedores?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker0**

**Explicación:**
docker0 es el puente de red virtual que Docker crea de forma predeterminada. Permite la comunicación entre contenedores del mismo anfitrión y media el tráfico entre ellos y las redes externas.
</details>

17. ¿Cuál es la característica de seguridad de Linux que restringe las llamadas al sistema que puede usar un proceso que se ejecuta dentro de un contenedor?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: seccomp (Secure Computing Mode)**

**Explicación:**
seccomp es una característica de seguridad del núcleo de Linux que restringe las llamadas al sistema que puede usar un proceso. Los entornos de ejecución de contenedores, como Docker, utilizan perfiles seccomp para restringir las llamadas al sistema que pueden realizar los procesos del contenedor y reforzar así la seguridad.
</details>

18. ¿Cuál es el nombre del servicio de AWS que almacena y administra imágenes de contenedor?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Amazon ECR (Elastic Container Registry)**

**Explicación:**
Amazon ECR (Elastic Container Registry) es el servicio administrado de AWS para almacenar imágenes de contenedor. Ofrece análisis de vulnerabilidades, integración con IAM y gestión del ciclo de vida de las imágenes, y se integra con otros servicios de AWS.
</details>

19. ¿Qué comando de Docker permite ejecutar comandos adicionales dentro de un contenedor en ejecución?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker exec**

**Explicación:**
El comando `docker exec` permite ejecutar comandos adicionales dentro de un contenedor en ejecución. Por ejemplo, `docker exec -it <container> bash` se conecta a una terminal interactiva dentro del contenedor, o `docker exec <container> ls /app` lista archivos dentro del contenedor. Este comando es muy útil para depurar contenedores.
</details>

20. ¿Qué comando de Docker supervisa los eventos del contenedor en tiempo real (inicio, detención, reinicio, etc.) como un flujo continuo?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: docker events**

**Explicación:**
El comando `docker events` muestra en tiempo real los eventos del daemon de Docker en un flujo continuo. Permite supervisar, por ejemplo, el inicio, la detención y el reinicio de contenedores, la descarga de imágenes y la conexión o desconexión de redes. La opción `--filter` limita la salida a un contenedor o tipo de evento, algo útil para depurar y supervisar el sistema.
</details>

## Preguntas prácticas

21. Escribe un Dockerfile que cumpla los siguientes requisitos:
    - Usar la imagen Node.js 24 Alpine
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
FROM node:24-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY --chown=node:node . .

USER node

EXPOSE 3000

CMD ["node", "server.js"]
```

**Explicación:**
Este Dockerfile muestra una configuración básica para aplicaciones de Node.js. Al copiar primero los archivos de dependencias (`package*.json`) e instalarlas antes de copiar los demás archivos, aprovecha la caché de capas de Docker. Así, si cambia el código fuente pero no las dependencias, se puede reutilizar la capa de `npm ci`.
</details>

22. Analiza el siguiente comando de Docker y explica su propósito:
    ```bash
    docker run -d --name my-app -p 8080:80 -v data:/app/data --restart always nginx:latest
    ```

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
El comando sirve para lo siguiente:
    - `-d`: Ejecuta el contenedor en segundo plano, en modo desacoplado.
    - `--name my-app`: Asigna al contenedor el nombre `my-app`.
    - `-p 8080:80`: Publica el puerto 80 del contenedor como el puerto 8080 del anfitrión.
    - `-v data:/app/data`: Monta el volumen llamado `data` en `/app/data` dentro del contenedor; esto no cambia el directorio raíz de documentos de NGINX.
    - `--restart always`: Reinicia el contenedor tras una salida. Si se detiene manualmente, el reinicio queda suprimido hasta que se reinicie el daemon o se inicie el contenedor explícitamente.
    - `nginx:latest`: Usa la etiqueta mutable `latest`; para obtener una imagen más reciente hay que descargarla de nuevo.

El comando ejecuta el servidor web NGINX en segundo plano y publica el puerto 8080 del host. De forma predeterminada, el puerto publicado escucha en todas las direcciones del anfitrión; para limitar el acceso a la máquina local, usa `127.0.0.1:8080:80`. El volumen conserva datos, pero no hace que NGINX los sirva desde `/app/data` sin configurar su raíz de documentos.
</details>

23. Escribe un Dockerfile optimizado para una aplicación React mediante una compilación de varias etapas.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```dockerfile
# Build stage
FROM node:24 AS build

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

# Run stage
FROM nginx:1.30.6-alpine

# Copy build artifacts to nginx's service directory
COPY --from=build /app/build /usr/share/nginx/html

# Use default nginx configuration

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Explicación:**
Este Dockerfile de varias etapas consta de dos fases:
1. Compilación: usa una imagen de Node.js para construir la aplicación React.
2. Ejecución: usa la imagen ligera de NGINX para servir los archivos estáticos resultantes.

Así, la imagen final no incluye Node.js, los paquetes de npm ni el código fuente, lo que reduce su tamaño. Solo contiene los archivos estáticos generados y NGINX, por lo que también tiene una superficie de software menor.
</details>

24. Escribe un Dockerfile que incluya comprobaciones de estado del contenedor. Configúralo para consultar el endpoint HTTP `/health` cada 30 segundos, considerar fallida la comprobación si no responde en 3 segundos y marcar el contenedor como `unhealthy` tras 3 fallos.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```dockerfile
FROM nginx:1.30.6-alpine

# Copy application (example)
COPY ./html /usr/share/nginx/html
RUN printf 'ok\n' > /usr/share/nginx/html/health

# Health check configuration
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Explicación:**
Significado de cada opción de la instrucción `HEALTHCHECK`:
- `--interval=30s`: Ejecuta la comprobación de estado cada 30 segundos.
- `--timeout=3s`: La comprobación se considera fallida si no termina en 3 segundos.
- `--start-period=10s`: Permite fallos durante la inicialización por hasta 10 segundos; una comprobación correcta temprana termina antes ese período de gracia.
- `--retries=3`: Marca el contenedor como `unhealthy` tras 3 fallos consecutivos.
- `CMD`: Define el comando que se ejecutará; aquí, `wget` consulta el endpoint `/health`.

Docker puede marcar el contenedor como `unhealthy`, pero ese estado por sí solo no reinicia un contenedor independiente. Un orquestador puede reaccionar a las señales de salud que admita; Kubernetes requiere sus propias sondas y no usa `HEALTHCHECK` del Dockerfile. Para que el ejemplo funcione, la aplicación debe responder con HTTP 200 en `/health`.
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
- `docker top` muestra los procesos del contenedor desde el punto de vista del anfitrión
- `docker diff` comprueba archivos modificados en comparación con la imagen
Usar estas herramientas de forma eficaz ayuda a comprender el estado interno del contenedor y resolver problemas.
</details>

El ejercicio del Dockerfile requiere el `package-lock.json` correspondiente, `server.js` o el script de compilación estática y el directorio `html` que espera la aplicación. Excluye `node_modules`, `.git` y `.env` mediante `.dockerignore`. La salida estática de React puede estar en `build` o `dist`; usa la ruta que genere la herramienta real. Una aplicación SSR no se ejecuta copiando archivos estáticos a NGINX. El ejemplo de `/health` comprueba la respuesta de NGINX estático, no la disponibilidad del servicio de backend.

## Preguntas avanzadas

26. Compara las funciones de los espacios de nombres (namespaces) y los cgroups, componentes principales de la tecnología de contenedores, y explica cómo contribuye cada uno al aislamiento.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Espacios de nombres (namespaces)**:
    - **Función**: Aíslan grupos de procesos para que cada grupo vea los recursos del sistema de forma independiente.
    - **Tipo de aislamiento**: Aíslan la visibilidad de los recursos.
    - **Espacios de nombres principales**:
    - Espacio de nombres PID: Aislamiento de identificadores de proceso
    - Espacio de nombres de red: Aislamiento de la pila de red
    - Espacio de nombres de montaje: Aislamiento de los puntos de montaje del sistema de archivos
    - Espacio de nombres UTS: Aislamiento del nombre de host y del nombre de dominio NIS
    - Espacio de nombres IPC: Aislamiento de los recursos de comunicación entre procesos
    - Espacio de nombres de usuario: Aislamiento de los identificadores de usuario y grupo

**cgroups (grupos de control)**:
    - **Función**: Limitan y aíslan el uso de recursos de grupos de procesos.
    - **Tipo de aislamiento**: Limitación del uso de recursos.
    - **Funciones principales**:
    - Limitación del tiempo de CPU
    - Limitación del uso de memoria
    - Limitación del ancho de banda de E/S de bloques
    - Control del tráfico de red mediante la integración con `tc`/eBPF
    - Control del acceso a dispositivos

**Contribución al aislamiento de contenedores**:

Los espacios de nombres y los cgroups cumplen funciones complementarias:

    - Los espacios de nombres dan a cada contenedor su propio entorno y vista del sistema (árbol de procesos, interfaces de red, puntos de montaje, etc.), lo que proporciona aislamiento lógico.

    - Los cgroups limitan los recursos del sistema (CPU, memoria, E/S de disco, entre otros) que puede usar cada contenedor, y evitan que consuma en exceso y afecte a los demás o al sistema anfitrión.

Estas tecnologías permiten ejecutar contenedores con aislamiento y límites de recursos. Ese aislamiento es más ligero que el de las máquinas virtuales, pero la seguridad depende de la exposición al núcleo, los privilegios y la configuración del entorno de ejecución; no ofrece una garantía de aislamiento completo.
</details>

27. Explica cómo funciona el sistema de capas de imágenes de contenedor y cómo la estrategia Copy-on-Write (CoW) contribuye a la eficiencia de los contenedores.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Capas de las imágenes de contenedor**:

Las imágenes de contenedor constan de varias capas apiladas. Cada capa representa cambios en el sistema de archivos: `RUN`, `COPY` y `ADD` pueden generar diferencias en él, mientras que instrucciones que solo modifican metadatos, como `ENV` o `CMD`, no crean una capa del sistema de archivos. Las capas son de solo lectura y se apilan para formar la imagen final.

Características principales del sistema de capas:
1. **Compilaciones incrementales**: Solo las capas modificadas se regeneran durante las construcciones de imágenes
2. **Compartición de capas**: Varias imágenes comparten las mismas capas base
3. **Caché**: Las capas ya descargadas se reutilizan

**Estrategia de copia al escribir (Copy-on-Write, CoW)**:

La copia al escribir es una estrategia de optimización que aplaza la copia hasta que se modifican los datos. En los contenedores:

1. **Inicio del contenedor**: Al iniciar un contenedor, se añade una capa escribible fina sobre las capas existentes de la imagen.
2. **Operaciones de lectura**: Al leer un archivo, el sistema busca en las capas de arriba hacia abajo y usa la primera versión del archivo encontrada.
3. **Escritura**: Al modificar un archivo, primero se copia a la capa escribible y después se modifica mediante copia al escribir; el archivo original permanece intacto.
4. **Eliminación**: Si se elimina un archivo de una capa inferior, se crea un marcador `whiteout` en la capa escribible para ocultarlo. Un archivo que solo existe en la capa superior se puede eliminar de esa capa.

**Cómo contribuye a la eficiencia**:

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

Gracias a estas eficiencias, los contenedores pueden ser más ligeros y arrancar más rápido que las máquinas virtuales, y un mismo host puede ejecutar más contenedores.
</details>

28. Explica todo el ciclo de vida de un contenedor y describe el comportamiento del contenedor y los métodos de transición de estado en cada estado (Created, Running, Paused, Restarting, Exited, Dead).

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Estados del ciclo de vida del contenedor:**

1. **Created**
   - El contenedor se ha creado, pero aún no se ha iniciado
   - Creado con el comando `docker create`
   - El proceso aún no se ejecuta y se asignan pocos recursos.
   - Transición: `docker start` → Running

2. **Running**
   - El proceso principal del contenedor está en ejecución
   - Se inicia mediante `docker run` o `docker start`.
   - Utiliza activamente recursos como CPU y memoria.
   - Transiciones:
     - `docker pause` → Paused
     - `docker stop` → Exited
     - `docker kill` → Exited
     - `docker restart` → secuencia de detención e inicio → Running
     - Al terminar el proceso → Exited

3. **Paused**
   - Los procesos Linux se congelan mediante el cgroup freezer, no enviándoles SIGSTOP
   - Se entra mediante el comando `docker pause`
   - La memoria se mantiene, pero no hay uso de CPU
   - Transición: `docker unpause` → Running

4. **Restarting**
   - Estado temporal mientras el contenedor se reinicia
   - Indica un reinicio automático provocado por una política de reinicio; `docker restart` solicita explícitamente una secuencia de detención e inicio
   - Transición: pasa automáticamente a Running o Exited.

5. **Exited**
   - El proceso principal terminó.
   - Se conserva el código de salida.
   - Se conservan los cambios del sistema de archivos.
   - Transiciones:
     - `docker start` → Running
     - `docker rm` → Deleted

6. **Dead**
   - Estado anómalo en el que falló el intento de eliminación del contenedor
   - La limpieza de recursos no se completó.
   - Por lo general, requiere intervención manual.
   - Se puede intentar eliminarlo por la fuerza con `docker rm -f`.

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
- `always`: Reinicia tras la salida o el reinicio del daemon; una detención manual suprime el reinicio hasta que se reinicie el daemon o se inicie el contenedor explícitamente.
- `unless-stopped`: Reinicia tras la salida o el reinicio del daemon, salvo que el contenedor se haya detenido manualmente; esa detención persiste después de reiniciar el daemon.

Comprender el ciclo de vida de los contenedores ayuda a mantener la disponibilidad de las aplicaciones y a definir estrategias adecuadas de recuperación ante problemas.
</details>

---

[Volver a los materiales de aprendizaje](../../basics/03-container-technology.md) | [Siguiente cuestionario: Introducción a Kubernetes](./04-kubernetes-introduction-quiz.md)

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
