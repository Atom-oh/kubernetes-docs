# Cuestionario de Pods y Workloads

Este cuestionario evalúa tu comprensión de los Pods, la unidad básica de ejecución de Kubernetes, y los diversos recursos de workload que los administran.

## Preguntas de opción múltiple

1. ¿Cuál es la unidad informática implementable más pequeña en Kubernetes?
   - A) Container
   - B) Pod
   - C) Deployment
   - D) Node
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Pod**

**Explicación:**
Un Pod es la unidad informática implementable más pequeña en Kubernetes. Un Pod es un grupo de uno o más containers que comparten almacenamiento y red, y se programan juntos. Aunque los containers son unidades más pequeñas contenidas dentro de Pods, no son la unidad de implementación administrada directamente por Kubernetes.
</details>

2. ¿Cuál de las siguientes NO es una característica de un Pod?
   - A) Todos los containers de un Pod comparten la misma dirección IP
   - B) Todos los containers de un Pod siempre se ejecutan en el mismo node
   - C) Un Pod puede ejecutarse en varios nodes
   - D) Un Pod tiene una dirección IP única
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Un Pod puede ejecutarse en varios nodes**

**Explicación:**
Todos los containers de un Pod siempre se ejecutan en el mismo node. Un Pod no puede ejecutarse en varios nodes. Esta es una de las características fundamentales de los Pods, que permite que los containers dentro del Pod se comuniquen localmente y compartan volumes. Todos los containers de un Pod comparten el mismo namespace de red y, por lo tanto, tienen la misma dirección IP, y cada Pod tiene una dirección IP única dentro del cluster.
</details>

3. ¿Cuál es el patrón de Pod con varios containers que extiende la funcionalidad del container principal con containers auxiliares?
   - A) Patrón Ambassador
   - B) Patrón Sidecar
   - C) Patrón Adapter
   - D) Patrón Init
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Patrón Sidecar**

**Explicación:**
El patrón sidecar agrega containers auxiliares que extienden la funcionalidad del container principal. Por ejemplo, los recopiladores de logs, sincronizadores de archivos y proxies se pueden implementar como containers sidecar. El patrón ambassador agrega containers que actúan como proxies para servicios externos, el patrón adapter agrega containers que estandarizan la salida del container principal y el patrón init agrega containers que se ejecutan antes de que se inicie el container principal.
</details>

4. ¿Qué probe comprueba si un container está listo para gestionar solicitudes y lo elimina del tráfico de servicio cuando falla?
   - A) livenessProbe
   - B) readinessProbe
   - C) startupProbe
   - D) healthProbe
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) readinessProbe**

**Explicación:**
readinessProbe comprueba si un container está listo para gestionar solicitudes y lo elimina del tráfico de servicio cuando falla. livenessProbe comprueba si un container está activo y lo reinicia cuando falla. startupProbe comprueba si la aplicación dentro del container se ha iniciado y deshabilita las demás probes hasta que tiene éxito. healthProbe no existe en Kubernetes.
</details>

5. ¿Cuál de las siguientes NO es una función principal de ReplicaSet?
   - A) Mantener una cantidad especificada de réplicas de pod
   - B) Crear automáticamente pods de reemplazo cuando los pods fallan o se eliminan
   - C) Realizar actualizaciones graduales
   - D) Identificar los pods que se deben administrar mediante selectores de labels
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Realizar actualizaciones graduales**

**Explicación:**
Las actualizaciones graduales son una función principal de los Deployments, no son compatibles directamente con los ReplicaSets. Las funciones principales de ReplicaSets son mantener una cantidad especificada de réplicas de pod, crear automáticamente pods de reemplazo cuando los pods fallan o se eliminan e identificar los pods que se deben administrar mediante selectores de labels. Los Deployments administran ReplicaSets para proporcionar actualizaciones graduales, rollbacks y otras funciones.
</details>

6. ¿Cuáles NO son estrategias de actualización integradas de Deployment? (Selecciona dos.)
   - A) RollingUpdate
   - B) Recreate
   - C) BlueGreen
   - D) Canary
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) BlueGreen y D) Canary**

**Explicación:**
Los Deployments de Kubernetes proporcionan dos estrategias de actualización de forma predeterminada: RollingUpdate y Recreate. BlueGreen y Canary son patrones de implementación, pero no se proporcionan directamente como estrategias de actualización de Deployment. Estos patrones se pueden implementar mediante otros recursos de Kubernetes, como Services e Ingresses, o con herramientas adicionales como Argo Rollouts.
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
StatefulSet es un recurso de workload para aplicaciones que requieren persistencia de estado. Asigna identificadores únicos a cada pod y proporciona identificadores de red estables y almacenamiento persistente. Es adecuado para aplicaciones que necesitan mantener el estado, como bases de datos, sistemas distribuidos y colas de mensajes. Los Deployments y ReplicaSets son para aplicaciones sin estado, y los DaemonSets garantizan que una copia de un pod se ejecute en todos los nodes.
</details>

8. ¿Qué recurso de workload garantiza que una copia de un pod se ejecute en todos los nodes (o en nodes específicos)?
   - A) Deployment
   - B) ReplicaSet
   - C) StatefulSet
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: D) DaemonSet**

**Explicación:**
DaemonSet garantiza que una copia de un pod se ejecute en todos los nodes (o en nodes específicos). Cuando se agrega un node al cluster, el pod se agrega automáticamente, y cuando se elimina un node, el pod también se elimina. Se usa principalmente para ejecutar servicios en segundo plano, como recopiladores de logs, agentes de monitoreo y plugins de red. Los Deployments y ReplicaSets mantienen una cantidad especificada de réplicas de pod, y los StatefulSets son para aplicaciones que requieren persistencia de estado.
</details>

9. ¿Qué recurso de workload es para ejecutar tareas únicas?
   - A) Deployment
   - B) Job
   - C) CronJob
   - D) DaemonSet
   
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Job**

**Explicación:**
Un Job es un recurso de workload que crea uno o más pods y continúa la ejecución hasta que una cantidad especificada de pods finalice correctamente. Se utiliza para ejecutar tareas únicas. Los Deployments son para aplicaciones que se ejecutan de forma continua, los CronJobs ejecutan jobs periódicamente según una programación y los DaemonSets ejecutan copias de pods en todos los nodes.
</details>

10. ¿Qué recurso de workload ejecuta tareas periódicamente según una programación?
    - A) Deployment
    - B) Job
    - C) CronJob
    - D) StatefulSet
    
<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) CronJob**

**Explicación:**
CronJob es un recurso de workload que ejecuta jobs periódicamente según una programación especificada. Funciona de manera similar a los trabajos cron de Linux y se utiliza para tareas regulares, como copias de seguridad, generación de informes y envío de correos electrónicos. Los Deployments son para aplicaciones que se ejecutan de forma continua, los Jobs ejecutan tareas únicas y los StatefulSets son para aplicaciones que requieren persistencia de estado.
</details>

## Preguntas de respuesta corta

11. ¿Cuál es el nombre del container especial que se ejecuta antes de que se inicien los containers de un pod?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Init Container**

**Explicación:**
Los Init Containers son containers especiales que se ejecutan antes de que se inicien los containers de la aplicación en un pod. Los init containers se ejecutan de uno en uno en el orden definido, y cada init container solo se inicia después de que el anterior haya finalizado correctamente. Si un init container falla, se reinicia según la política de reinicio del pod. Se utilizan principalmente para la configuración antes de que se inicien los containers de la aplicación, la comprobación de dependencias y la configuración de permisos.
</details>

12. ¿Cuál es la señal de detención predeterminada cuando un Pod termina, si la imagen/el container no la ha sobrescrito?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: SIGTERM**

**Explicación:**
Cuando un pod termina, kubelet ejecuta cualquier hook preStop y luego solicita al runtime que envíe SIGTERM de forma predeterminada. El hook consume parte del período de gracia; un STOPSIGNAL de imagen o una sobrescritura compatible del container puede seleccionar una señal diferente. Esto proporciona tiempo para que la aplicación se cierre correctamente. Si el container no termina dentro del período de terminación predeterminado (30 segundos), se envía una señal SIGKILL. Cuando la aplicación recibe la señal SIGTERM, puede completar el trabajo en curso, cerrar conexiones, limpiar recursos y realizar otras tareas.
</details>

13. ¿Cuál es el nombre del recurso que administran los Deployments?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: ReplicaSet**

**Explicación:**
Los Deployments administran ReplicaSets. Los Deployments crean ReplicaSets y los ReplicaSets crean y administran pods. Los Deployments proporcionan actualizaciones graduales, rollbacks, escalado y otras funciones mediante ReplicaSets. Al implementar una nueva versión de una aplicación, el Deployment crea un nuevo ReplicaSet y reduce gradualmente el ReplicaSet anterior.
</details>

14. ¿Cuál es el formato del identificador único asignado a los pods en un StatefulSet? (Por ejemplo, si el nombre de StatefulSet es 'web')

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: \<nombre de StatefulSet\>-\<índice ordinal\> (p. ej., web-0, web-1, web-2)**

**Explicación:**
Los StatefulSets asignan identificadores únicos con el formato `<StatefulSet name>-<ordinal index>` a los pods. Por ejemplo, el StatefulSet `web` crea pods como `web-0`, `web-1`, `web-2`. Este identificador se conserva incluso cuando los pods se reprograman y se utiliza para proporcionar identificadores de red estables y almacenamiento persistente.
</details>

15. ¿Cuál es la política de concurrencia en CronJob que omite nuevos jobs cuando los jobs anteriores todavía se están ejecutando?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Forbid**

**Explicación:**
La política de concurrencia `Forbid` en CronJob omite nuevos jobs si los jobs anteriores todavía se están ejecutando. Los CronJobs proporcionan tres políticas de concurrencia: `Allow` (varios jobs pueden ejecutarse simultáneamente, valor predeterminado), `Forbid` (omite nuevos jobs si los jobs anteriores todavía se están ejecutando) y `Replace` (reemplaza los jobs anteriores por jobs nuevos si todavía se están ejecutando). Estas políticas se pueden establecer mediante el campo `concurrencyPolicy`.
</details>

## Preguntas prácticas

16. Escribe un archivo YAML de pod con varios containers que cumpla los siguientes requisitos:
    - Nombre del Pod: web-app
    - Primer container: servidor web nginx (imagen: nginx:1.30.4)
    - Segundo container: recopilador de logs (imagen: fluentd:v1.19-debian-1)
    - Volumen emptyDir para compartir el directorio de logs entre los dos containers
    - El container nginx expone el puerto 80
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
      image: nginx:1.30.4
      ports:
        - containerPort: 80
      volumeMounts:
        - name: log-volume
          mountPath: /var/log/nginx
    - name: log-collector
      image: fluentd:v1.19-debian-1
      volumeMounts:
        - name: log-volume
          mountPath: /fluentd/log
  volumes:
    - name: log-volume
      emptyDir: {}
```

**Explicación:**
Este archivo YAML define un pod con varios containers que contiene un servidor web nginx y un recopilador de logs fluentd. Crea un volumen emptyDir llamado `log-volume` y lo monta en `/var/log/nginx` en el container nginx y en `/fluentd/log` en el container fluentd. Esto comparte los archivos; la recopilación real también requiere una fuente tail de Fluentd para `/fluentd/log/*.log` y una configuración de salida. El container nginx expone el puerto 80. Este es un ejemplo del patrón sidecar.
</details>

17. Escribe un archivo YAML de Deployment que cumpla los siguientes requisitos:
    - Nombre: nginx-deployment
    - Labels: app=nginx, tier=frontend
    - Cantidad de réplicas: 3
    - Estrategia de actualización gradual: aumento máximo 1, no disponibles máximo 0
    - Imagen del container: nginx:1.30.4
    - Puerto del container: 80
    - Solicitudes de recursos: CPU 100m, memoria 128Mi
    - Límites de recursos: CPU 200m, memoria 256Mi
    - Probe de liveness: HTTP GET /, retraso inicial 30 segundos, período 10 segundos
    - Probe de readiness: HTTP GET /, retraso inicial 5 segundos, período 5 segundos

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
          image: nginx:1.30.4
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
Este archivo YAML define un Deployment con 3 réplicas que utiliza la imagen nginx:1.30.4. La estrategia de actualización gradual está configurada con un aumento máximo de 1 (cantidad máxima de pods que se pueden crear por encima de la cantidad deseada) y un máximo de no disponibles de 0 (cantidad máxima de pods que pueden no estar disponibles durante la actualización), lo que permite actualizaciones sin tiempo de inactividad. Cada container expone el puerto 80 y tiene restricciones de recursos de solicitud de CPU 100m, solicitud de memoria 128Mi, límite de CPU 200m y límite de memoria 256Mi. Las probes de liveness y readiness verifican el estado del container mediante solicitudes HTTP GET.
</details>

18. Escribe un archivo YAML de CronJob que cumpla los siguientes requisitos:
    - Nombre: database-backup
    - Programación: se ejecuta diariamente a las 2:00 UTC (usa una expresión cron y timeZone)
    - Política de concurrencia: Forbid
    - Límite del historial de jobs correctos: 3
    - Límite del historial de jobs fallidos: 1
    - Imagen del container: postgres:14
    - Comando: pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
    - Variables de entorno: PGHOST=postgres-service, PGUSER y PGPASSWORD de postgres-secret
    - Volumen: monta backup-pvc en /backup
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
  timeZone: "Etc/UTC"
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
Este archivo YAML define un CronJob de copia de seguridad de base de datos que se ejecuta diariamente a las 2:00. `concurrencyPolicy: Forbid` omite nuevos jobs si los jobs anteriores todavía se están ejecutando. `successfulJobsHistoryLimit: 3` y `failedJobsHistoryLimit: 1` limitan el historial de jobs correctos y fallidos a 3 y 1 respectivamente. El container utiliza la imagen postgres:14 y ejecuta el comando pg_dump para hacer una copia de seguridad de la base de datos. La variable de entorno PGHOST se establece directamente, mientras que PGUSER y PGPASSWORD se recuperan de postgres-secret. El volumen backup-pvc se monta en el directorio /backup para almacenar los archivos de copia de seguridad. La política de reinicio se establece en OnFailure, por lo que el container se reinicia si el job falla.
</details>

## Preguntas avanzadas

19. Explica qué responsabilidades proporciona un StatefulSet para un cluster de MySQL con un primary y dos réplicas, y cuáles requieren un operador de base de datos o un controlador de replicación. ¿Por qué es incorrecto configurar un servidor MySQL local desde un init container normal?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:**

- Un StatefulSet proporciona nombres de Pod estables, un Service sin encabezado rector, PVC por Pod y escalado ordenado de forma predeterminada. Reemplaza los Pods que fallan con el mismo ordinal y almacenamiento, sujeto a la disponibilidad de almacenamiento.
- No copia los datos de la base de datos, configura la replicación, elige/promueve un primary, aísla un primary anterior ni redirige a los clientes de la base de datos. Un operador/runbook de base de datos probado debe implementar estos comportamientos, las credenciales de replicación, las copias de seguridad y las comprobaciones de restauración.
- Los init containers normales finalizan antes de que se inicie el container de la aplicación local. Intentar una conexión SQL local desde un init container no puede configurar un servidor MySQL que no se ha iniciado. La configuración de replicación debe ejecutarse en una etapa adecuada del ciclo de vida de la base de datos.
- Tres Pods de MySQL independientes no constituyen una base de datos de alta disponibilidad replicada. Reutilizar el mismo ID de servidor entre réplicas o insertar contraseñas de replicación en un ConfigMap también es incorrecto.
- Consulta el ejemplo de StatefulSet de instancia única del capítulo para la configuración de identidad/almacenamiento de Kubernetes; no lo escales a tres ni afirmes que proporciona replicación o failover automático.

</details>

20. Compara las características y los casos de uso de diversos recursos de workload (Deployment, StatefulSet, DaemonSet, Job, CronJob), y selecciona el recurso de workload más adecuado para los siguientes escenarios y explica por qué:
    - Frontend de aplicación web
    - Cluster de base de datos distribuida
    - Agente de recopilación de logs
    - Copia de seguridad de datos diaria
    - Migración de datos única

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**

**Comparación de recursos de workload**

| Recurso de workload | Características clave | Casos de uso |
|--------------|---------|---------|
| **Deployment** | - Aplicaciones sin estado<br>- Compatibilidad con actualizaciones graduales<br>- Escalado automático<br>- Administración de ReplicaSet | - Servidores web<br>- Servidores API<br>- Microservicios sin estado<br>- Aplicaciones frontend |
| **StatefulSet** | - Identificadores de red estables<br>- Almacenamiento persistente<br>- Implementación y escalado secuenciales<br>- Creación ordenada de pods garantizada | - Bases de datos<br>- Sistemas distribuidos<br>- Colas de mensajes<br>- Aplicaciones con estado |
| **DaemonSet** | - Se ejecuta en todos los nodes<br>- Implementación automática cuando se agregan nodes<br>- Limpieza automática cuando se eliminan nodes<br>- Posibilidad de seleccionar nodes | - Recopiladores de logs<br>- Agentes de monitoreo<br>- Plugins de red<br>- Daemons de almacenamiento |
| **Job** | - Tareas únicas<br>- Seguimiento de finalización (puede fallar)<br>- Posibilidad de ejecución en paralelo<br>- Reintento ante fallos | - Procesamiento por lotes<br>- Migración de datos<br>- Tareas de cálculo<br>- Tareas de administración únicas |
| **CronJob** | - Ejecución basada en programación<br>- Tareas periódicas<br>- Política de concurrencia<br>- Límites de historial | - Copias de seguridad programadas<br>- Sincronización de datos<br>- Generación de informes<br>- Tareas de limpieza |

**Recursos de workload adecuados por escenario**

1. **Frontend de aplicación web**
  - **Recurso adecuado: Deployment**
  - **Motivo**: Los frontends de aplicaciones web suelen ser aplicaciones sin estado. Los Deployments pueden implementar nuevas versiones sin tiempo de inactividad mediante actualizaciones graduales, son fáciles de escalar horizontalmente y proporcionan recuperación automática. También se pueden usar con HorizontalPodAutoscaler para escalar automáticamente según el tráfico.

2. **Cluster de base de datos distribuida**
  - **Recurso adecuado: StatefulSet**
  - **Motivo**: Las bases de datos distribuidas requieren persistencia de estado y cada instancia necesita un identificador único y almacenamiento persistente. Los StatefulSets proporcionan identificadores de red estables (`<StatefulSet name>-<ordinal index>`) y almacenamiento persistente, y admiten implementación y escalado ordenados; la base de datos debe implementar la replicación y la consistencia. Adecuado para clusters de bases de datos distribuidas como MySQL, PostgreSQL, MongoDB y Cassandra.

3. **Agente de recopilación de logs**
  - **Recurso adecuado: DaemonSet**
  - **Motivo**: Los agentes de recopilación de logs deben ejecutarse en todos los nodes del cluster. Los DaemonSets garantizan que una copia de un pod se ejecute en todos los nodes (o en nodes específicos), e implementan automáticamente agentes de recopilación de logs cuando se agregan nuevos nodes al cluster. Adecuado para implementar agentes de recopilación de logs como Fluentd, Logstash y Filebeat.

4. **Copia de seguridad de datos diaria**
  - **Recurso adecuado: CronJob**
  - **Motivo**: La copia de seguridad de datos diaria es una tarea que debe ejecutarse periódicamente según una programación establecida. Los CronJobs pueden especificar programaciones de ejecución mediante expresiones cron y se pueden configurar para ejecutar tareas de copia de seguridad a una hora específica cada día. También pueden definir el comportamiento cuando las copias de seguridad anteriores aún se están ejecutando mediante `concurrencyPolicy` y pueden limitar el historial de Job; la retención de archivos de copia de seguridad requiere una política independiente.

5. **Migración de datos única**
  - **Recurso adecuado: Job**
  - **Motivo**: La migración de datos es una tarea única que debe finalizar correctamente. Los Jobs continúan la ejecución hasta que una cantidad especificada de pods finalice correctamente y proporcionan mecanismos de reintento ante fallos. Además, las migraciones de datos grandes se pueden procesar más rápido ejecutando varios pods en paralelo mediante la configuración de `parallelism`.

**Conclusión**

Cada recurso de workload está diseñado para casos de uso específicos, y es importante seleccionar el recurso adecuado según los requisitos de la aplicación. Los Deployments son adecuados para aplicaciones sin estado, los StatefulSets para aplicaciones que requieren persistencia de estado, los DaemonSets para servicios que deben ejecutarse en todos los nodes, los Jobs para tareas únicas y los CronJobs para tareas periódicas. Comprender estas características y seleccionar el recurso de workload adecuado permite una administración eficiente de aplicaciones en Kubernetes.
</details>

---

[Volver a los materiales de aprendizaje](../../core/02-pods-and-workloads.md) | [Siguiente cuestionario: Services y Networking](../core/03-services-networking-quiz.md)