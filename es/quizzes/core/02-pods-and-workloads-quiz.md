# Cuestionario sobre Pods y cargas de trabajo

Este cuestionario evalúa tu comprensión de los Pods, la unidad básica de ejecución de Kubernetes, y de los diversos recursos de carga de trabajo que los gestionan.

## Preguntas de opción múltiple

1. ¿Cuál es la unidad de cómputo desplegable más pequeña en Kubernetes?
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod**

**Explicación:**
Un Pod es la unidad de cómputo desplegable más pequeña en Kubernetes. Un Pod es un grupo de uno o más containers que comparten almacenamiento y red, y se programan juntos. Aunque los containers son unidades más pequeñas contenidas dentro de Pods, no son la unidad de despliegue gestionada directamente por Kubernetes.
</details>

2. ¿Cuál de las siguientes NO es una característica de un Pod?
   - A) Todos los containers en un Pod comparten la misma dirección IP
   - B) Todos los containers en un Pod siempre se ejecutan en el mismo node
   - C) Un Pod puede ejecutarse en varios nodes
   - D) Un Pod tiene una dirección IP única
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Un Pod puede ejecutarse en varios nodes**

**Explicación:**
Todos los containers en un Pod siempre se ejecutan en el mismo node. Un Pod no puede ejecutarse en varios nodes. Esta es una de las características fundamentales de los Pods, que permite que los containers dentro del Pod se comuniquen localmente y compartan volúmenes. Todos los containers en un Pod comparten el mismo namespace de red y, por lo tanto, tienen la misma dirección IP, y cada Pod tiene una dirección IP única dentro del cluster.
</details>

3. ¿Cuál es el patrón de Pod con múltiples containers que extiende la funcionalidad del container principal con containers auxiliares?
   - A) Patrón Ambassador
   - B) Patrón Sidecar
   - C) Patrón Adapter
   - D) Patrón Init
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Patrón Sidecar**

**Explicación:**
El patrón sidecar añade containers auxiliares que extienden la funcionalidad del container principal. Por ejemplo, los recolectores de logs, sincronizadores de archivos y proxies pueden implementarse como containers sidecar. El patrón ambassador añade containers que actúan como proxies hacia servicios externos, el patrón adapter añade containers que estandarizan la salida del container principal, y el patrón init añade containers que se ejecutan antes de que se inicie el container principal.
</details>

4. ¿Qué probe verifica si un container está listo para gestionar solicitudes y lo elimina del tráfico del service cuando falla?
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) readinessProbe**

**Explicación:**
readinessProbe verifica si un container está listo para gestionar solicitudes y lo elimina del tráfico del service cuando falla. livenessProbe verifica si un container está vivo y lo reinicia cuando falla. startupProbe verifica si la aplicación dentro del container se ha iniciado y deshabilita otras probes hasta que tenga éxito. healthProbe no existe en Kubernetes.
</details>

5. ¿Cuál de las siguientes NO es una función principal de ReplicaSet?
   - A) Mantener un número especificado de réplicas de pods
   - B) Crear automáticamente pods de reemplazo cuando los pods fallan o se eliminan
   - C) Realizar rolling updates
   - D) Identificar los pods que se gestionarán mediante label selectors
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Realizar rolling updates**

**Explicación:**
Los rolling updates son una función principal de Deployments, no están soportados directamente por ReplicaSets. Las funciones principales de ReplicaSets son mantener un número especificado de réplicas de pods, crear automáticamente pods de reemplazo cuando los pods fallan o se eliminan, e identificar los pods que se gestionarán mediante label selectors. Deployments gestionan ReplicaSets para proporcionar rolling updates, rollbacks y otras características.
</details>

6. ¿Cuál de las siguientes NO es una estrategia de actualización para Deployments?
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) BlueGreen**

**Explicación:**
Kubernetes Deployments proporciona dos estrategias de actualización de forma predeterminada: RollingUpdate y Recreate. BlueGreen y Canary son patrones de despliegue, pero no se proporcionan directamente como estrategias de actualización de Deployment. Estos patrones pueden implementarse usando otros recursos de Kubernetes, como Services e Ingresses, o usando herramientas adicionales como Argo Rollouts.
</details>

7. ¿Qué recurso de carga de trabajo es para aplicaciones que requieren persistencia de estado?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) StatefulSet**

**Explicación:**
StatefulSet es un recurso de carga de trabajo para aplicaciones que requieren persistencia de estado. Asigna identificadores únicos a cada pod y proporciona identificadores de red estables y almacenamiento persistente. Es adecuado para aplicaciones que necesitan mantener estado, como bases de datos, sistemas distribuidos y colas de mensajes. Deployments y ReplicaSets son para aplicaciones sin estado, y DaemonSets garantizan que una copia de un pod se ejecute en todos los nodes.
</details>

8. ¿Qué recurso de carga de trabajo garantiza que una copia de un pod se ejecute en todos los nodes (o en nodes específicos)?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) DaemonSet**

**Explicación:**
DaemonSet garantiza que una copia de un pod se ejecute en todos los nodes (o en nodes específicos). Cuando se añade un node al cluster, el pod se añade automáticamente, y cuando se elimina un node, el pod también se elimina. Se utiliza principalmente para ejecutar servicios en segundo plano, como recolectores de logs, agentes de monitorización y plugins de red. Deployments y ReplicaSets mantienen un número especificado de réplicas de pods, y StatefulSets son para aplicaciones que requieren persistencia de estado.
</details>

9. ¿Qué recurso de carga de trabajo es para ejecutar tareas de una sola vez?
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Job**

**Explicación:**
Un Job es un recurso de carga de trabajo que crea uno o más pods y continúa la ejecución hasta que un número especificado de pods finaliza correctamente. Se usa para ejecutar tareas de una sola vez. Deployments son para aplicaciones en ejecución continua, CronJobs ejecutan jobs periódicamente según una programación y DaemonSets ejecutan copias de pods en todos los nodes.
</details>

10. ¿Qué recurso de carga de trabajo ejecuta tareas periódicamente según una programación?
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) CronJob**

**Explicación:**
CronJob es un recurso de carga de trabajo que ejecuta jobs periódicamente según una programación especificada. Funciona de forma similar a los cron jobs de Linux y se usa para tareas regulares como copias de seguridad, generación de informes y envío de correos electrónicos. Deployments son para aplicaciones en ejecución continua, Jobs ejecutan tareas de una sola vez, y StatefulSets son para aplicaciones que requieren persistencia de estado.
</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del container especial que se ejecuta antes de que se inicien los containers en un pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Init Container**

**Explicación:**
Init Containers son containers especiales que se ejecutan antes de que se inicien los app containers en un pod. Los init containers se ejecutan uno a la vez en el orden definido, y cada init container solo se inicia después de que el anterior se haya completado correctamente. Si un init container falla, se reinicia según la política de reinicio del pod. Se utilizan principalmente para la configuración previa al inicio de los app containers, la comprobación de dependencias y la configuración de permisos.
</details>

12. ¿Qué señal se envía primero a un container cuando se termina un pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: SIGTERM**

**Explicación:**
Cuando se termina un pod, kubelet envía primero una señal SIGTERM a los containers. Esto proporciona tiempo para que la aplicación se cierre correctamente. Si el container no termina dentro del periodo de terminación predeterminado (30 segundos), se envía una señal SIGKILL. Cuando la aplicación recibe la señal SIGTERM, puede completar el trabajo en curso, cerrar conexiones, limpiar recursos y realizar otras tareas.
</details>

13. ¿Cuál es el nombre del recurso que gestionan Deployments?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: ReplicaSet**

**Explicación:**
Deployments gestionan ReplicaSets. Deployments crean ReplicaSets, y ReplicaSets crean y gestionan pods. Deployments proporcionan rolling updates, rollbacks, escalado y otras características a través de ReplicaSets. Al desplegar una nueva versión de una aplicación, el Deployment crea un nuevo ReplicaSet y reduce gradualmente el ReplicaSet anterior.
</details>

14. ¿Cuál es el formato del identificador único asignado a los pods en un StatefulSet? (Por ejemplo, si el nombre del StatefulSet es 'web')

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: \<nombre del StatefulSet\>-\<índice ordinal\> (p. ej., web-0, web-1, web-2)**

**Explicación:**
StatefulSets asignan identificadores únicos en el formato `<StatefulSet name>-<ordinal index>` a los pods. Por ejemplo, el StatefulSet `web` crea pods como `web-0`, `web-1`, `web-2`. Este identificador se mantiene incluso cuando los pods se reprograman y se utiliza para proporcionar identificadores de red estables y almacenamiento persistente.
</details>

15. ¿Cuál es la concurrency policy en CronJob que omite nuevos jobs cuando los jobs anteriores aún se están ejecutando?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Forbid**

**Explicación:**
La concurrency policy `Forbid` en CronJob omite nuevos jobs si los jobs anteriores aún se están ejecutando. CronJobs proporciona tres concurrency policies: `Allow` (varios jobs pueden ejecutarse simultáneamente, valor predeterminado), `Forbid` (omite nuevos jobs si los jobs anteriores aún se están ejecutando) y `Replace` (reemplaza los jobs anteriores con nuevos jobs si aún se están ejecutando). Estas políticas pueden configurarse mediante el campo `concurrencyPolicy`.
</details>

## Preguntas prácticas

16. Escribe un archivo YAML de pod con múltiples containers que cumpla los siguientes requisitos:
    - Nombre del Pod: web-app
    - Primer container: servidor web nginx (image: nginx:1.21)
    - Segundo container: recolector de logs (image: fluentd:v1.14)
    - Volumen emptyDir para compartir el directorio de logs entre los dos containers
    - El container nginx expone el port 80
    - Volumen de logs montado en /var/log/nginx en el container nginx y en /fluentd/log en el container fluentd

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
spec:
  containers:
    - name: nginx
      image: nginx:1.21
      ports:
        - containerPort: 80
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/nginx
    - name: log-collector
      image: fluentd:v1.14
      volumeMounts:
        - name: log-volume
          mountPath: /fluentd/log
  volumes:
    - name: log-volume
      emptyDir: {}
```

**Explicación:**
Este archivo YAML define un pod con múltiples containers que contiene un servidor web nginx y un recolector de logs fluentd. Crea un volumen emptyDir llamado `log-volume` y lo monta en `/var/log/nginx` en el container nginx y en `/fluentd/log` en el container fluentd. Esto permite que fluentd recopile los logs generados por nginx. El container nginx expone el port 80. Este es un ejemplo del patrón sidecar.
</details>

17. Escribe un archivo YAML de Deployment que cumpla los siguientes requisitos:
    - Nombre: nginx-deployment
    - Labels: app=nginx, tier=frontend
    - Número de réplicas: 3
    - Estrategia rolling update: max surge 1, max unavailable 0
    - Imagen del container: nginx:1.21
    - Port del container: 80
    - Resource requests: CPU 100m, memoria 128Mi
    - Resource limits: CPU 200m, memoria 256Mi
    - Liveness probe: HTTP GET /, retraso inicial 30 segundos, periodo 10 segundos
    - Readiness probe: HTTP GET /, retraso inicial 5 segundos, periodo 5 segundos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: nginx
        tier: frontend
    spec:
      containers:
        - name: nginx
          image: nginx:1.21
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
```

**Explicación:**
Este archivo YAML define un Deployment con 3 réplicas usando la imagen nginx:1.21. La estrategia rolling update se configura con max surge 1 (número máximo de pods que pueden crearse por encima del número deseado) y max unavailable 0 (número máximo de pods que pueden no estar disponibles durante la actualización), lo que permite actualizaciones sin tiempo de inactividad. Cada container expone el port 80 y tiene restricciones de recursos de CPU request 100m, memory request 128Mi, CPU limit 200m y memory limit 256Mi. Las liveness y readiness probes verifican el estado del container mediante solicitudes HTTP GET.
</details>

18. Escribe un archivo YAML de CronJob que cumpla los siguientes requisitos:
    - Nombre: database-backup
    - Schedule: se ejecuta diariamente a las 2 AM (usar expresión cron)
    - Concurrency policy: Forbid
    - Límite del historial de jobs exitosos: 3
    - Límite del historial de jobs fallidos: 1
    - Imagen del container: postgres:14
    - Command: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - Variables de entorno: PGHOST=postgres-service, PGUSER y PGPASSWORD desde postgres-secret
    - Volume: montar backup-pvc en /backup
    - Restart policy: OnFailure

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:14
              env:
                - name: PGHOST
                  value: postgres-service
                - name: PGUSER
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: username
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: postgres-secret
                      key: password
              command:
                - /bin/sh
                - -c
                - pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
              volumeMounts:
                - name: backup-volume
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-volume
              persistentVolumeClaim:
                claimName: backup-pvc
```

**Explicación:**
Este archivo YAML define un CronJob de copia de seguridad de base de datos que se ejecuta diariamente a las 2 AM. `concurrencyPolicy: Forbid` omite nuevos jobs si los jobs anteriores aún se están ejecutando. `successfulJobsHistoryLimit: 3` y `failedJobsHistoryLimit: 1` limitan el historial de jobs exitosos y fallidos a 3 y 1 respectivamente. El container usa la imagen postgres:14 y ejecuta el comando pg_dump para respaldar la base de datos. La variable de entorno PGHOST se establece directamente, mientras que PGUSER y PGPASSWORD se obtienen de postgres-secret. El volumen backup-pvc se monta en el directorio /backup para almacenar los archivos de copia de seguridad. La restart policy se establece en OnFailure, por lo que el container se reinicia si el job falla.
</details>

## Preguntas avanzadas

19. Explica el diseño de un StatefulSet para una aplicación con estado de alta disponibilidad y escribe un YAML de StatefulSet para un cluster de replicación MySQL que cumpla los siguientes requisitos:
    - Compuesto por 1 master y 2 slaves
    - Proporciona identificadores de red estables
    - Proporciona almacenamiento persistente para cada instancia
    - Despliegue y escalado secuenciales
    - Mecanismo de recuperación automática en caso de fallo del master node

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Principios de diseño para aplicaciones con estado de alta disponibilidad**

Los siguientes principios se aplican al diseño de alta disponibilidad para aplicaciones con estado:

1. **Identificadores de red estables**: Cada instancia mantiene el mismo identificador de red incluso después de reinicios
2. **Almacenamiento persistente**: Acceso a los mismos datos incluso cuando las instancias se reprograman
3. **Despliegue y escalado secuenciales**: Crear y eliminar instancias en orden para mantener la consistencia de los datos
4. **Mecanismo de recuperación automática**: Mecanismo para recuperarse automáticamente cuando ocurren fallos
5. **Copia de seguridad y restauración**: Copias de seguridad regulares y procedimientos de restauración cuando sea necesario

**YAML de StatefulSet para cluster de replicación MySQL**

```yaml
# Headless service definition
apiVersion: v1
kind: Service
metadata:
  name: mysql
  labels:
    app: mysql
spec:
  ports:
    - port: 3306
      name: mysql
  clusterIP: None
  selector:
    app: mysql
---
# ConfigMap for configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql-config
data:
  master.cnf: |
    [mysqld]
    log-bin=mysql-bin
    binlog-format=ROW
    server-id=1
  slave.cnf: |
    [mysqld]
    server-id=100
    log_bin=mysql-bin
    relay_log=mysql-relay-bin
    read_only=1
  init.sql: |
    CREATE DATABASE IF NOT EXISTS mydb;
    GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%' IDENTIFIED BY 'replpass';
    FLUSH PRIVILEGES;
---
# MySQL StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  updateStrategy:
    type: RollingUpdate
  podManagementPolicy: OrderedReady
  template:
    metadata:
      labels:
        app: mysql
    spec:
      initContainers:
        - name: init-mysql
          image: mysql:8.0
          command:
            - bash
            - "-c"
            - |
              set -ex
              # Configure as master or slave based on pod index
              [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
              ordinal=${BASH_REMATCH[1]}
              if [[ $ordinal -eq 0 ]]; then
                # Master configuration
                cp /mnt/config-map/master.cnf /etc/mysql/conf.d/
                # Copy initialization SQL script
                cp /mnt/config-map/init.sql /docker-entrypoint-initdb.d/
              else
                # Slave configuration
                cp /mnt/config-map/slave.cnf /etc/mysql/conf.d/
              fi
          volumeMounts:
            - name: conf
              mountPath: /etc/mysql/conf.d
            - name: config-map
              mountPath: /mnt/config-map
            - name: initdb
              mountPath: /docker-entrypoint-initdb.d
        - name: clone-mysql
          image: mysql:8.0
          command:
            - bash
            - "-c"
            - |
              set -ex
              # Only slaves set up replication
              [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
              ordinal=${BASH_REMATCH[1]}
              if [[ $ordinal -eq 0 ]]; then
                # Master does nothing
                exit 0
              fi

              # Wait for master to be ready
              until mysql -h mysql-0.mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SELECT 1"; do
                echo "Waiting for mysql-0.mysql to be ready..."
                sleep 2
              done

              # Check master status
              master_status=$(mysql -h mysql-0.mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "SHOW MASTER STATUS\G")
              file=$(echo "$master_status" | grep File | awk '{print $2}')
              position=$(echo "$master_status" | grep Position | awk '{print $2}')

              # Configure slave
              mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "CHANGE MASTER TO MASTER_HOST='mysql-0.mysql', MASTER_USER='repl', MASTER_PASSWORD='replpass', MASTER_LOG_FILE='$file', MASTER_LOG_POS=$position; START SLAVE;"
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
      containers:
        - name: mysql
          image: mysql:8.0
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: password
          ports:
            - name: mysql
              containerPort: 3306
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
            - name: conf
              mountPath: /etc/mysql/conf.d
            - name: initdb
              mountPath: /docker-entrypoint-initdb.d
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 1
              memory: 2Gi
          livenessProbe:
            exec:
              command: ["mysqladmin", "ping", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
          readinessProbe:
            exec:
              command: ["mysql", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}", "-e", "SELECT 1"]
            initialDelaySeconds: 5
            periodSeconds: 2
            timeoutSeconds: 1
      volumes:
        - name: conf
          emptyDir: {}
        - name: config-map
          configMap:
            name: mysql-config
        - name: initdb
          emptyDir: {}
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "standard"
        resources:
          requests:
            storage: 10Gi
```

**Explicación:**

Este archivo YAML define un StatefulSet para un cluster de replicación MySQL compuesto por 1 master y 2 slaves.

1. **Headless service**: El service `mysql` está configurado con `clusterIP: None`, lo que crea registros DNS para cada pod. Esto proporciona identificadores de red estables como `mysql-0.mysql`, `mysql-1.mysql`, `mysql-2.mysql`.

2. **ConfigMap**: Define un ConfigMap para la configuración de MySQL. Incluye configuraciones separadas para nodos master y slave, y un script SQL de inicialización.

3. **StatefulSet**: Define un StatefulSet de MySQL con 3 réplicas.
  - `podManagementPolicy: OrderedReady`: Crea y elimina pods en orden.
  - `updateStrategy: RollingUpdate`: Usa la estrategia rolling update.
  - Init containers: aplican la configuración master o slave según el índice del pod, y los nodos slave configuran la replicación desde el master node.
  - Almacenamiento persistente: crea persistent volume claims para cada pod mediante `volumeClaimTemplates`.
  - Resource requests y limits: establece resource requests y limits para cada instancia de MySQL.
  - Liveness y readiness probes: verifican el estado de las instancias de MySQL.

4. **Mecanismo de recuperación automática**:
  - Cuando un pod falla, el StatefulSet crea automáticamente un nuevo pod.
  - El nuevo pod usa el mismo identificador de red y almacenamiento persistente.
  - Los nodos slave configuran la replicación desde el master node para mantener la consistencia de los datos.

Este diseño proporciona un cluster MySQL de alta disponibilidad, y puede implementarse un mecanismo para promover uno de los nodos slave a un nuevo master cuando falla el master node (este ejemplo no incluye el mecanismo de promoción automática, que normalmente se implementa mediante MySQL Operator o controllers adicionales).
</details>

20. Compara las características y casos de uso de varios recursos de carga de trabajo (Deployment, StatefulSet, DaemonSet, Job, CronJob), y selecciona el recurso de carga de trabajo más apropiado para los siguientes escenarios y explica por qué:
    - Frontend de aplicación web
    - Cluster de base de datos distribuida
    - Agente de recolección de logs
    - Copia de seguridad diaria de datos
    - Migración de datos de una sola vez

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Comparación de recursos de carga de trabajo**

| Recurso de carga de trabajo | Características clave | Casos de uso |
|--------------|---------|---------|
| **Deployment** | - Aplicaciones sin estado<br>- Soporte para rolling updates<br>- Auto scaling<br>- Gestión de ReplicaSet | - Servidores web<br>- Servidores API<br>- Microservices sin estado<br>- Aplicaciones frontend |
| **StatefulSet** | - Identificadores de red estables<br>- Almacenamiento persistente<br>- Despliegue y escalado secuenciales<br>- Creación ordenada de pods garantizada | - Bases de datos<br>- Sistemas distribuidos<br>- Colas de mensajes<br>- Aplicaciones con estado |
| **DaemonSet** | - Se ejecuta en todos los nodes<br>- Despliegue automático cuando se añaden nodes<br>- Limpieza automática cuando se eliminan nodes<br>- Selección de nodes posible | - Recolectores de logs<br>- Agentes de monitorización<br>- Plugins de red<br>- Daemons de almacenamiento |
| **Job** | - Tareas de una sola vez<br>- Garantía de finalización<br>- Ejecución paralela posible<br>- Reintento en caso de fallo | - Procesamiento batch<br>- Migración de datos<br>- Tareas de cómputo<br>- Tareas de gestión de una sola vez |
| **CronJob** | - Ejecución basada en programación<br>- Tareas periódicas<br>- Concurrency policy<br>- Límites de historial | - Copias de seguridad programadas<br>- Sincronización de datos<br>- Generación de informes<br>- Tareas de limpieza |

**Recursos de carga de trabajo apropiados por escenario**

1. **Frontend de aplicación web**
  - **Recurso apropiado: Deployment**
  - **Razón**: Los frontends de aplicaciones web suelen ser aplicaciones sin estado. Deployments pueden desplegar nuevas versiones sin tiempo de inactividad mediante rolling updates, son fáciles de escalar horizontalmente y proporcionan recuperación automática. También pueden usarse con HorizontalPodAutoscaler para escalar automáticamente según el tráfico.

2. **Cluster de base de datos distribuida**
  - **Recurso apropiado: StatefulSet**
  - **Razón**: Las bases de datos distribuidas requieren persistencia de estado, y cada instancia necesita un identificador único y almacenamiento persistente. StatefulSets proporcionan identificadores de red estables (`<pod name>-<ordinal index>`) y almacenamiento persistente, y pueden mantener la consistencia de los datos mediante despliegue y escalado secuenciales. Adecuado para clusters de bases de datos distribuidas como MySQL, PostgreSQL, MongoDB y Cassandra.

3. **Agente de recolección de logs**
  - **Recurso apropiado: DaemonSet**
  - **Razón**: Los agentes de recolección de logs deben ejecutarse en todos los nodes del cluster. DaemonSets garantizan que una copia de un pod se ejecute en todos los nodes (o en nodes específicos), y despliegan automáticamente agentes de recolección de logs cuando se añaden nuevos nodes al cluster. Adecuado para desplegar agentes de recolección de logs como Fluentd, Logstash y Filebeat.

4. **Copia de seguridad diaria de datos**
  - **Recurso apropiado: CronJob**
  - **Razón**: La copia de seguridad diaria de datos es una tarea que debe ejecutarse periódicamente según una programación establecida. CronJobs pueden especificar programaciones de ejecución mediante expresiones cron y pueden configurarse para ejecutar tareas de copia de seguridad a una hora específica cada día. También pueden definir el comportamiento cuando las copias de seguridad anteriores aún se están ejecutando mediante `concurrencyPolicy` y pueden limitar el historial de copias de seguridad.

5. **Migración de datos de una sola vez**
  - **Recurso apropiado: Job**
  - **Razón**: La migración de datos es una tarea de una sola vez que debe completarse correctamente. Jobs continúan la ejecución hasta que un número especificado de pods finaliza correctamente y proporcionan mecanismos de reintento en caso de fallo. Además, las migraciones de datos grandes pueden procesarse más rápido ejecutando varios pods en paralelo mediante la configuración de `parallelism`.

**Conclusión**

Cada recurso de carga de trabajo está diseñado para casos de uso específicos, y es importante seleccionar el recurso adecuado según los requisitos de la aplicación. Deployments son adecuados para aplicaciones sin estado, StatefulSets para aplicaciones que requieren persistencia de estado, DaemonSets para servicios que deben ejecutarse en todos los nodes, Jobs para tareas de una sola vez y CronJobs para tareas periódicas. Comprender estas características y seleccionar el recurso de carga de trabajo apropiado permite una gestión eficiente de aplicaciones en Kubernetes.
</details>

---

[Volver a los materiales de aprendizaje](../../core/02-pods-and-workloads.md) | [Siguiente cuestionario: Services y networking](../core/03-services-networking-quiz.md)
