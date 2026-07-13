# Cuestionario sobre Pods y Workloads

Este cuestionario evalúa tu comprensión de Pods, la unidad básica de ejecución de Kubernetes, y de los diversos recursos de workload que los administran.

## Preguntas de opción múltiple

1. ¿Cuál es la unidad de computación desplegable más pequeña en Kubernetes?
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod**

**Explicación:**
Un Pod es la unidad de computación desplegable más pequeña en Kubernetes. Un Pod es un grupo de uno o más Containers que comparten almacenamiento y red, y se programan juntos. Aunque los Containers son unidades más pequeñas contenidas dentro de Pods, no son la unidad de despliegue administrada directamente por Kubernetes.
</details>

2. ¿Cuál de las siguientes NO es una característica de un Pod?
   - A) Todos los Containers en un Pod comparten la misma dirección IP
   - B) Todos los Containers en un Pod siempre se ejecutan en el mismo Node
   - C) Un Pod puede ejecutarse en varios Nodes
   - D) Un Pod tiene una dirección IP única
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Un Pod puede ejecutarse en varios Nodes**

**Explicación:**
Todos los Containers en un Pod siempre se ejecutan en el mismo Node. Un Pod no puede ejecutarse en varios Nodes. Esta es una de las características fundamentales de Pods, ya que permite que los Containers dentro del Pod se comuniquen localmente y compartan volumes. Todos los Containers en un Pod comparten el mismo namespace de red y, por lo tanto, tienen la misma dirección IP, y cada Pod tiene una dirección IP única dentro del cluster.
</details>

3. ¿Cuál es el patrón de Pod multi-container que extiende la funcionalidad del Container principal con Containers auxiliares?
   - A) Patrón ambassador
   - B) Patrón sidecar
   - C) Patrón adapter
   - D) Patrón init
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Patrón sidecar**

**Explicación:**
El patrón sidecar agrega Containers auxiliares que extienden la funcionalidad del Container principal. Por ejemplo, recolectores de logs, sincronizadores de archivos y proxies se pueden implementar como sidecar containers. El patrón ambassador agrega Containers que actúan como proxies hacia servicios externos, el patrón adapter agrega Containers que estandarizan la salida del Container principal y el patrón init agrega Containers que se ejecutan antes de que inicie el Container principal.
</details>

4. ¿Qué probe verifica si un Container está listo para manejar solicitudes y lo elimina del tráfico de Service cuando falla?
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) readinessProbe**

**Explicación:**
readinessProbe verifica si un Container está listo para manejar solicitudes y lo elimina del tráfico de Service cuando falla. livenessProbe verifica si un Container está vivo y lo reinicia cuando falla. startupProbe verifica si la aplicación dentro del Container ha iniciado y deshabilita otras probes hasta que tenga éxito. healthProbe no existe en Kubernetes.
</details>

5. ¿Cuál de las siguientes NO es una función principal de ReplicaSet?
   - A) Mantener un número especificado de réplicas de Pods
   - B) Crear automáticamente Pods de reemplazo cuando los Pods fallan o se eliminan
   - C) Realizar rolling updates
   - D) Identificar los Pods que administrará mediante label selectors
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Realizar rolling updates**

**Explicación:**
Los rolling updates son una función principal de Deployments, no están soportados directamente por ReplicaSets. Las funciones principales de ReplicaSets son mantener un número especificado de réplicas de Pods, crear automáticamente Pods de reemplazo cuando los Pods fallan o se eliminan, e identificar los Pods que administrará mediante label selectors. Deployments administran ReplicaSets para proporcionar rolling updates, rollbacks y otras características.
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
Kubernetes Deployments proporciona dos estrategias de actualización de forma predeterminada: RollingUpdate y Recreate. BlueGreen y Canary son patrones de despliegue, pero no se proporcionan directamente como estrategias de actualización de Deployment. Estos patrones se pueden implementar usando otros recursos de Kubernetes, como Services e Ingresses, o usando herramientas adicionales como Argo Rollouts.
</details>

7. ¿Qué recurso de workload es para aplicaciones que requieren persistencia de estado?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) StatefulSet**

**Explicación:**
StatefulSet es un recurso de workload para aplicaciones que requieren persistencia de estado. Asigna identificadores únicos a cada Pod y proporciona identificadores de red estables y almacenamiento persistente. Es adecuado para aplicaciones que necesitan mantener estado, como bases de datos, sistemas distribuidos y colas de mensajes. Deployments y ReplicaSets son para aplicaciones stateless, y DaemonSets garantizan que una copia de un Pod se ejecute en todos los Nodes.
</details>

8. ¿Qué recurso de workload garantiza que una copia de un Pod se ejecute en todos los Nodes (o en Nodes específicos)?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) DaemonSet**

**Explicación:**
DaemonSet garantiza que una copia de un Pod se ejecute en todos los Nodes (o en Nodes específicos). Cuando se agrega un Node al cluster, el Pod se agrega automáticamente, y cuando se elimina un Node, el Pod también se elimina. Se utiliza principalmente para ejecutar servicios en segundo plano, como recolectores de logs, agentes de monitoreo y plugins de red. Deployments y ReplicaSets mantienen un número especificado de réplicas de Pods, y StatefulSets son para aplicaciones que requieren persistencia de estado.
</details>

9. ¿Qué recurso de workload es para ejecutar tareas de una sola vez?
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Job**

**Explicación:**
Un Job es un recurso de workload que crea uno o más Pods y continúa la ejecución hasta que un número especificado de Pods termina correctamente. Se utiliza para ejecutar tareas de una sola vez. Deployments son para aplicaciones que se ejecutan de forma continua, CronJobs ejecutan Jobs periódicamente según un calendario, y DaemonSets ejecutan copias de Pods en todos los Nodes.
</details>

10. ¿Qué recurso de workload ejecuta tareas periódicamente según un calendario?
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) CronJob**

**Explicación:**
CronJob es un recurso de workload que ejecuta Jobs periódicamente según un calendario especificado. Funciona de manera similar a los cron jobs de Linux y se utiliza para tareas regulares como backups, generación de informes y envío de correos electrónicos. Deployments son para aplicaciones que se ejecutan de forma continua, Jobs ejecutan tareas de una sola vez y StatefulSets son para aplicaciones que requieren persistencia de estado.
</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del Container especial que se ejecuta antes de que inicien los Containers en un Pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Init Container**

**Explicación:**
Init Containers son Containers especiales que se ejecutan antes de que inicien los app containers en un Pod. Los init containers se ejecutan de uno en uno en el orden definido, y cada init container solo inicia después de que el anterior se haya completado correctamente. Si un init container falla, se reinicia según la política de reinicio del Pod. Se utilizan principalmente para configuración previa al inicio de app containers, verificación de dependencias y configuración de permisos.
</details>

12. ¿Qué señal se envía primero a un Container cuando se termina un Pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: SIGTERM**

**Explicación:**
Cuando se termina un Pod, kubelet primero envía una señal SIGTERM a los Containers. Esto proporciona tiempo para que la aplicación se cierre de forma ordenada. Si el Container no termina dentro del período de terminación predeterminado (30 segundos), se envía una señal SIGKILL. Cuando la aplicación recibe la señal SIGTERM, puede completar el trabajo en curso, cerrar conexiones, limpiar recursos y realizar otras tareas.
</details>

13. ¿Cuál es el nombre del recurso que administran Deployments?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: ReplicaSet**

**Explicación:**
Deployments administran ReplicaSets. Deployments crean ReplicaSets, y ReplicaSets crean y administran Pods. Deployments proporcionan rolling updates, rollbacks, escalado y otras características a través de ReplicaSets. Al desplegar una nueva versión de una aplicación, el Deployment crea un nuevo ReplicaSet y reduce gradualmente la escala del ReplicaSet anterior.
</details>

14. ¿Cuál es el formato del identificador único asignado a Pods en un StatefulSet? (Por ejemplo, si el nombre del StatefulSet es 'web')

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: \<StatefulSet name\>-\<ordinal index\> (p. ej., web-0, web-1, web-2)**

**Explicación:**
StatefulSets asignan identificadores únicos en el formato `<StatefulSet name>-<ordinal index>` a los Pods. Por ejemplo, el StatefulSet `web` crea Pods como `web-0`, `web-1`, `web-2`. Este identificador se mantiene incluso cuando los Pods se reprograman y se utiliza para proporcionar identificadores de red estables y almacenamiento persistente.
</details>

15. ¿Cuál es la política de concurrencia en CronJob que omite nuevos Jobs cuando los Jobs anteriores todavía se están ejecutando?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Forbid**

**Explicación:**
La política de concurrencia `Forbid` en CronJob omite nuevos Jobs si los Jobs anteriores todavía se están ejecutando. CronJobs proporciona tres políticas de concurrencia: `Allow` (varios Jobs pueden ejecutarse simultáneamente, predeterminado), `Forbid` (omite nuevos Jobs si los Jobs anteriores todavía se están ejecutando) y `Replace` (reemplaza los Jobs anteriores con nuevos Jobs si todavía se están ejecutando). Estas políticas se pueden establecer mediante el campo `concurrencyPolicy`.
</details>

## Preguntas prácticas

16. Escribe un archivo YAML de Pod multi-container que cumpla los siguientes requisitos:
    - Nombre del Pod: web-app
    - Primer Container: servidor web nginx (image: nginx:1.21)
    - Segundo Container: recolector de logs (image: fluentd:v1.14)
    - Volumen emptyDir para compartir el directorio de logs entre los dos Containers
    - El Container nginx expone el puerto 80
    - Volumen de logs montado en /var/log/nginx en el Container nginx y en /fluentd/log en el Container fluentd

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
Este archivo YAML define un Pod multi-container que contiene un servidor web nginx y un recolector de logs fluentd. Crea un volumen emptyDir llamado `log-volume` y lo monta en `/var/log/nginx` en el Container nginx y en `/fluentd/log` en el Container fluentd. Esto permite que fluentd recopile los logs generados por nginx. El Container nginx expone el puerto 80. Este es un ejemplo del patrón sidecar.
</details>

17. Escribe un archivo YAML de Deployment que cumpla los siguientes requisitos:
    - Nombre: nginx-deployment
    - Labels: app=nginx, tier=frontend
    - Número de réplicas: 3
    - Estrategia rolling update: max surge 1, max unavailable 0
    - Imagen del Container: nginx:1.21
    - Puerto del Container: 80
    - Resource requests: CPU 100m, memory 128Mi
    - Resource limits: CPU 200m, memory 256Mi
    - Liveness probe: HTTP GET /, initial delay 30 seconds, period 10 seconds
    - Readiness probe: HTTP GET /, initial delay 5 seconds, period 5 seconds

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
Este archivo YAML define un Deployment con 3 réplicas usando la imagen nginx:1.21. La estrategia rolling update está configurada con max surge 1 (número máximo de Pods que se pueden crear por encima del número deseado) y max unavailable 0 (número máximo de Pods que pueden no estar disponibles durante la actualización), lo que permite actualizaciones sin tiempo de inactividad. Cada Container expone el puerto 80 y tiene restricciones de recursos de CPU request 100m, memory request 128Mi, CPU limit 200m y memory limit 256Mi. Las probes liveness y readiness verifican el estado del Container mediante solicitudes HTTP GET.
</details>

18. Escribe un archivo YAML de CronJob que cumpla los siguientes requisitos:
    - Nombre: database-backup
    - Schedule: se ejecuta diariamente a las 2 AM (usa una expresión cron)
    - Política de concurrencia: Forbid
    - Límite de historial de Jobs exitosos: 3
    - Límite de historial de Jobs fallidos: 1
    - Imagen del Container: postgres:14
    - Command: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - Variables de entorno: PGHOST=postgres-service, PGUSER y PGPASSWORD desde postgres-secret
    - Volumen: montar backup-pvc en /backup
    - Política de reinicio: OnFailure

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
Este archivo YAML define un CronJob de backup de base de datos que se ejecuta diariamente a las 2 AM. `concurrencyPolicy: Forbid` omite nuevos Jobs si los Jobs anteriores todavía se están ejecutando. `successfulJobsHistoryLimit: 3` y `failedJobsHistoryLimit: 1` limitan el historial de Jobs exitosos y fallidos a 3 y 1 respectivamente. El Container usa la imagen postgres:14 y ejecuta el comando pg_dump para hacer backup de la base de datos. La variable de entorno PGHOST se establece directamente, mientras que PGUSER y PGPASSWORD se recuperan de postgres-secret. El volumen backup-pvc se monta en el directorio /backup para almacenar archivos de backup. La política de reinicio se establece en OnFailure, por lo que el Container se reinicia si el Job falla.
</details>

## Preguntas avanzadas

19. Explica el diseño de un StatefulSet para una aplicación stateful de alta disponibilidad y escribe un YAML de StatefulSet para un cluster de replicación MySQL que cumpla los siguientes requisitos:
    - Compuesto por 1 master y 2 slaves
    - Proporciona identificadores de red estables
    - Proporciona almacenamiento persistente para cada instancia
    - Despliegue y escalado secuenciales
    - Mecanismo de recuperación automática en caso de falla del Node master

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Principios de diseño para aplicaciones stateful de alta disponibilidad**

Los siguientes principios se aplican al diseño de alta disponibilidad para aplicaciones stateful:

1. **Identificadores de red estables**: Cada instancia mantiene el mismo identificador de red incluso después de reinicios
2. **Almacenamiento persistente**: Acceso a los mismos datos incluso cuando las instancias se reprograman
3. **Despliegue y escalado secuenciales**: Crear y eliminar instancias en orden para mantener la consistencia de los datos
4. **Mecanismo de recuperación automática**: Mecanismo para recuperarse automáticamente cuando ocurren fallas
5. **Backup y restore**: Backups regulares y procedimientos de restore cuando sea necesario

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

1. **Headless service**: El Service `mysql` está configurado con `clusterIP: None`, lo que crea registros DNS para cada Pod. Esto proporciona identificadores de red estables como `mysql-0.mysql`, `mysql-1.mysql`, `mysql-2.mysql`.

2. **ConfigMap**: Define un ConfigMap para la configuración de MySQL. Incluye configuraciones separadas para Nodes master y slave, y un script SQL de inicialización.

3. **StatefulSet**: Define un StatefulSet de MySQL con 3 réplicas.
  - `podManagementPolicy: OrderedReady`: Crea y elimina Pods en orden.
  - `updateStrategy: RollingUpdate`: Usa la estrategia rolling update.
  - Init containers: aplican la configuración master o slave según el índice del Pod, y los Nodes slave configuran la replicación desde el Node master.
  - Almacenamiento persistente: crea persistent volume claims para cada Pod mediante `volumeClaimTemplates`.
  - Resource requests and limits: establece resource requests y limits para cada instancia de MySQL.
  - Liveness and readiness probes: verifican el estado de las instancias de MySQL.

4. **Mecanismo de recuperación automática**:
  - Cuando un Pod falla, StatefulSet crea automáticamente un nuevo Pod.
  - El nuevo Pod usa el mismo identificador de red y almacenamiento persistente.
  - Los Nodes slave configuran la replicación desde el Node master para mantener la consistencia de los datos.

Este diseño proporciona un cluster MySQL de alta disponibilidad, y se puede implementar un mecanismo para promover uno de los Nodes slave a un nuevo master cuando falla el Node master (este ejemplo no incluye el mecanismo de promoción automática, que normalmente se implementa mediante MySQL Operator o controladores adicionales).
</details>

20. Compara las características y casos de uso de varios recursos de workload (Deployment, StatefulSet, DaemonSet, Job, CronJob), y selecciona el recurso de workload más apropiado para los siguientes escenarios y explica por qué:
    - Frontend de aplicación web
    - Cluster de base de datos distribuida
    - Agente de recolección de logs
    - Backup diario de datos
    - Migración de datos de una sola vez

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Comparación de recursos de workload**

| Recurso de workload | Características clave | Casos de uso |
|--------------|---------|---------|
| **Deployment** | - Aplicaciones stateless<br>- Soporte para rolling updates<br>- Auto scaling<br>- Administración de ReplicaSet | - Servidores web<br>- Servidores API<br>- Microservices stateless<br>- Aplicaciones frontend |
| **StatefulSet** | - Identificadores de red estables<br>- Almacenamiento persistente<br>- Despliegue y escalado secuenciales<br>- Creación ordenada de Pods garantizada | - Bases de datos<br>- Sistemas distribuidos<br>- Colas de mensajes<br>- Aplicaciones stateful |
| **DaemonSet** | - Se ejecuta en todos los Nodes<br>- Despliegue automático cuando se agregan Nodes<br>- Limpieza automática cuando se eliminan Nodes<br>- Posible selección de Node | - Recolectores de logs<br>- Agentes de monitoreo<br>- Plugins de red<br>- Storage daemons |
| **Job** | - Tareas de una sola vez<br>- Garantía de finalización<br>- Posible ejecución en paralelo<br>- Reintento ante fallas | - Procesamiento por lotes<br>- Migración de datos<br>- Tareas de cómputo<br>- Tareas de administración de una sola vez |
| **CronJob** | - Ejecución basada en calendario<br>- Tareas periódicas<br>- Política de concurrencia<br>- Límites de historial | - Backups programados<br>- Sincronización de datos<br>- Generación de informes<br>- Tareas de limpieza |

**Recursos de workload apropiados por escenario**

1. **Frontend de aplicación web**
  - **Recurso apropiado: Deployment**
  - **Razón**: Los frontends de aplicaciones web suelen ser aplicaciones stateless. Deployments pueden desplegar nuevas versiones sin tiempo de inactividad mediante rolling updates, son fáciles de escalar horizontalmente y proporcionan recuperación automática. También se pueden usar con HorizontalPodAutoscaler para escalar automáticamente según el tráfico.

2. **Cluster de base de datos distribuida**
  - **Recurso apropiado: StatefulSet**
  - **Razón**: Las bases de datos distribuidas requieren persistencia de estado, y cada instancia necesita un identificador único y almacenamiento persistente. StatefulSets proporcionan identificadores de red estables (`<pod name>-<ordinal index>`) y almacenamiento persistente, y pueden mantener la consistencia de los datos mediante despliegue y escalado secuenciales. Adecuado para clusters de bases de datos distribuidas como MySQL, PostgreSQL, MongoDB y Cassandra.

3. **Agente de recolección de logs**
  - **Recurso apropiado: DaemonSet**
  - **Razón**: Los agentes de recolección de logs necesitan ejecutarse en todos los Nodes del cluster. DaemonSets garantizan que una copia de un Pod se ejecute en todos los Nodes (o en Nodes específicos), y despliegan automáticamente agentes de recolección de logs cuando se agregan nuevos Nodes al cluster. Adecuado para desplegar agentes de recolección de logs como Fluentd, Logstash y Filebeat.

4. **Backup diario de datos**
  - **Recurso apropiado: CronJob**
  - **Razón**: El backup diario de datos es una tarea que necesita ejecutarse periódicamente según un calendario establecido. CronJobs pueden especificar calendarios de ejecución usando expresiones cron y pueden configurarse para ejecutar tareas de backup a una hora específica cada día. También pueden definir el comportamiento cuando los backups anteriores todavía se están ejecutando mediante `concurrencyPolicy` y pueden limitar el historial de backups.

5. **Migración de datos de una sola vez**
  - **Recurso apropiado: Job**
  - **Razón**: La migración de datos es una tarea de una sola vez que debe completarse correctamente. Jobs continúan la ejecución hasta que un número especificado de Pods termina correctamente y proporcionan mecanismos de reintento ante fallas. Además, las migraciones de datos grandes se pueden procesar más rápido ejecutando varios Pods en paralelo mediante configuraciones de `parallelism`.

**Conclusión**

Cada recurso de workload está diseñado para casos de uso específicos, y es importante seleccionar el recurso apropiado según los requisitos de la aplicación. Deployments son adecuados para aplicaciones stateless, StatefulSets para aplicaciones que requieren persistencia de estado, DaemonSets para servicios que deben ejecutarse en todos los Nodes, Jobs para tareas de una sola vez y CronJobs para tareas periódicas. Comprender estas características y seleccionar el recurso de workload apropiado permite una gestión eficiente de aplicaciones en Kubernetes.
</details>

---

[Volver a los materiales de aprendizaje](../../core/02-pods-and-workloads.md) | [Siguiente cuestionario: Services and Networking](../core/03-services-networking-quiz.md)
