# Pods y cargas de trabajo de Kubernetes

> **Versiones compatibles**: Kubernetes 1.32, 1.33, 1.34
> **Última actualización**: February 23, 2026

Este documento proporciona una explicación detallada de los Pods, la unidad básica de ejecución en Kubernetes, y de los diversos recursos de carga de trabajo que los administran. Partiendo del concepto de Pods, cubriremos las características y los casos de uso de distintos recursos de carga de trabajo, incluidos Deployments, StatefulSets, DaemonSets y más.

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitará las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias
- kubectl v1.34 o posterior
- Un clúster de Kubernetes operativo (EKS, minikube, kind, etc.)

### Implementar la aplicación de ejemplo

```bash
# Create namespace
kubectl create namespace workloads-demo

# Create a simple deployment
kubectl -n workloads-demo apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
EOF

# Check deployment status
kubectl -n workloads-demo get deployments,pods
```

## Tabla de contenido
- [Conceptos de Pod](#pod-concepts)
- [Ciclo de vida del Pod](#pod-lifecycle)
- [Patrones de diseño de Pod](#pod-design-patterns)
- [Descripción general de los recursos de carga de trabajo](#workload-resources-overview)
- [ReplicaSet](#replicaset)
- [Deployment](#deployment)
- [StatefulSet](#statefulset)
- [DaemonSet](#daemonset)
- [Jobs y CronJobs](#jobs-and-cronjobs)
- [Gestión de recursos](#resource-management)
- [Presupuesto de interrupción de Pod](#pod-disruption-budget)
- [Escalado automático horizontal de Pod](#horizontal-pod-autoscaling)
- [Escalado automático vertical de Pod](#vertical-pod-autoscaling)
- [Prácticas recomendadas para cargas de trabajo](#workload-best-practices)
- [Consideraciones sobre cargas de trabajo de Amazon EKS](#amazon-eks-workload-considerations)

## Conceptos de Pod

> **Concepto clave**: Un Pod es la unidad de computación implementable más pequeña de Kubernetes y consta de uno o más grupos de contenedores que comparten almacenamiento y red.

Un Pod es la unidad de computación implementable más pequeña de Kubernetes. Un Pod es un grupo de uno o más contenedores que comparten almacenamiento y red, y se programan juntos.

### Características de Pod

1. **Contexto compartido**: Todos los contenedores dentro de un Pod comparten el mismo espacio de nombres de red, espacio de nombres IPC y espacio de nombres UTS.
2. **Mismo nodo**: Todos los contenedores de un Pod siempre se ejecutan en el mismo nodo.
3. **Dirección IP única**: Cada Pod tiene una dirección IP única dentro del clúster.
4. **Efímero**: Los Pods son fundamentalmente efímeros y pueden sustituirse por Pods nuevos en caso de error.
5. **Unidad atómica**: Los Pods son la unidad atómica de implementación, programación y replicación.

### Estructura de Pod

Un Pod consta de los siguientes componentes:

1. **Contenedores**: Uno o más contenedores que se ejecutan dentro del Pod
2. **Volúmenes**: Almacenamiento compartido por los contenedores dentro del Pod
3. **Red**: Dirección IP y puertos asignados al Pod
4. **Especificación de contenedor**: Imagen de contenedor, variables de entorno, requisitos de recursos, etc.

![Un límite de Pod de Kubernetes que muestra un contenedor de aplicación, un contenedor sidecar y un contenedor init que comparten una dirección IP de Pod y un espacio de nombres de red, junto con cuatro tipos de volúmenes de almacenamiento montables (emptyDir, configMap, secret, persistentVolumeClaim).](../.gitbook/assets/en-core-02-pods-and-workloads-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-core-02-pods-and-workloads-0.html)

### Ejemplo de Pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-container-pod
  labels:
    app: web
spec:
  containers:
  - name: web
    image: nginx:1.21
    ports:
    - containerPort: 80
    volumeMounts:
    - name: shared-data
      mountPath: /usr/share/nginx/html
  - name: content-updater
    image: alpine
    command: ["/bin/sh", "-c"]
    args:
    - while true; do
        echo "Current time: $(date)" > /content/index.html;
        sleep 10;
      done
    volumeMounts:
    - name: shared-data
      mountPath: /content
  volumes:
  - name: shared-data
    emptyDir: {}
```

### Ejemplo práctico: Pod de aplicación web

A continuación se muestra un ejemplo de un Pod que contiene una aplicación web y un contenedor sidecar:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
  labels:
    app: web
    environment: production
spec:
  containers:
  - name: web-application
    image: nginx:1.21
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
  - name: log-collector
    image: fluentd:v1.14
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx
    resources:
      requests:
        memory: "64Mi"
        cpu: "50m"
      limits:
        memory: "128Mi"
        cpu: "100m"
  volumes:
  - name: log-volume
    emptyDir: {}
```

Este ejemplo demuestra el siguiente escenario real:
- Ejecutar el servidor web Nginx como contenedor principal
- Ejecutar el recolector de registros Fluentd como contenedor sidecar
- Compartir un volumen de registros entre dos contenedores
- Establecer solicitudes y límites de recursos para cada contenedor

Esta configuración es adecuada para ejecutar contenedores estrechamente conectados y, a la vez, separar funciones como el registro, la supervisión y el proxy en arquitecturas de microservicios.
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Pod default;
    class Container1,Container2 userApp;
    class Volume dataStore;
    class IP default;
```

### Definición de Pod

Los Pods se definen mediante archivos de manifiesto en formato YAML o JSON. A continuación se muestra un ejemplo básico de definición de Pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels:
    app: nginx
spec:
  containers:
  - name: nginx
    image: nginx:1.21
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### Pods de contenedor único frente a Pods de varios contenedores

**Pods de contenedor único**:
- Caso de uso más común
- Contiene un solo contenedor de aplicación
- Estructura simple e intuitiva

**Pods de varios contenedores**:
- Contiene varios contenedores estrechamente acoplados
- Es posible la comunicación local entre contenedores (localhost)
- Uso compartido de datos mediante volúmenes compartidos
- Se escalan y se colocan juntos

### Patrones de Pod de varios contenedores

1. **Patrón Sidecar**: Contenedor auxiliar que amplía la funcionalidad del contenedor principal
   - Ejemplos: recolector de registros, sincronización de archivos, proxy

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-sidecar
spec:
  containers:
  - name: web
    image: nginx:1.21
  - name: log-collector
    image: fluentd:v1.14
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
```

2. **Patrón Ambassador**: Contenedor que actúa como proxy para servicios externos
   - Ejemplos: proxy de base de datos, sidecar de service mesh

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ambassador
spec:
  containers:
  - name: app
    image: myapp:1.0
  - name: ambassador
    image: envoy:v1.20
    ports:
    - containerPort: 9901
```

3. **Patrón Adapter**: Contenedor que estandariza la salida del contenedor principal
   - Ejemplos: conversión de formato de registros, conversión de métricas

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-adapter
spec:
  containers:
  - name: app
    image: myapp:1.0
  - name: adapter
    image: adapter:1.0
    volumeMounts:
    - name: app-logs
      mountPath: /var/log/app
  volumes:
  - name: app-logs
    emptyDir: {}
```

4. **Patrón de contenedor Init**: Contenedor que se ejecuta antes de que se inicie el contenedor principal
   - Ejemplos: creación de archivos de configuración, migración de bases de datos, configuración de permisos

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: init-db
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup db; do echo waiting for db; sleep 2; done;']
  containers:
  - name: app
    image: myapp:1.0
```

### Redes de Pod

Los contenedores de un Pod tienen las siguientes características de red:

1. **Misma dirección IP**: Todos los contenedores de un Pod comparten la misma dirección IP.
2. **Uso compartido de puertos**: Los contenedores de un Pod comparten el espacio de puertos, por lo que no pueden usar el mismo puerto.
3. **Comunicación mediante localhost**: Los contenedores de un Pod pueden comunicarse entre sí mediante localhost.
4. **Comunicación entre Pods**: Cada Pod tiene una dirección IP única y puede comunicarse directamente con otros Pods.

### Almacenamiento de Pod

Los Pods pueden usar varios tipos de volúmenes para almacenar y compartir datos:

1. **emptyDir**: Volumen temporal creado cuando se crea el Pod y eliminado cuando se elimina el Pod
2. **hostPath**: Volumen montado desde el sistema de archivos del nodo host al Pod
3. **persistentVolumeClaim**: Volumen que solicita almacenamiento persistente
4. **configMap**: ConfigMap montado como volumen
5. **secret**: Secret montado como volumen
6. **projected**: Varias fuentes de volumen asignadas al mismo directorio

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-volumes
spec:
  containers:
  - name: app
    image: myapp:1.0
    volumeMounts:
    - name: data
      mountPath: /data
    - name: config
      mountPath: /etc/config
  volumes:
  - name: data
    emptyDir: {}
  - name: config
    configMap:
      name: app-config
```

## Ciclo de vida del Pod

Los Pods pasan por varias etapas de ciclo de vida, desde su creación hasta su terminación. Comprender este ciclo de vida es importante para garantizar la estabilidad y disponibilidad de la aplicación.

### Fases de Pod

Los Pods pasan por las siguientes fases:

1. **Pending**: El Pod ha sido aceptado por el clúster, pero uno o más contenedores aún no se han configurado
2. **Running**: El Pod se ha vinculado a un nodo, se han creado todos los contenedores y al menos uno está en ejecución, iniciándose o reiniciándose
3. **Succeeded**: Todos los contenedores del Pod han terminado correctamente y no se reiniciarán
4. **Failed**: Todos los contenedores del Pod han terminado y al menos uno ha terminado con error
5. **Unknown**: No se pudo obtener el estado del Pod por algún motivo

### Estados de contenedor

Cada contenedor dentro de un Pod puede tener los siguientes estados:

1. **Waiting**: Estado anterior a que el contenedor se ejecute (descargando la imagen, esperando dependencias, etc.)
2. **Running**: El contenedor se ejecuta sin problemas
3. **Terminated**: El contenedor ha completado su ejecución o falló por algún motivo

### Condiciones de Pod

Los Pods indican su estado de forma más específica mediante las siguientes condiciones:

1. **PodScheduled**: Si el Pod se ha programado en un nodo
2. **ContainersReady**: Si todos los contenedores del Pod están listos
3. **Initialized**: Si todos los contenedores init se han completado correctamente
4. **Ready**: Si el Pod puede atender solicitudes y añadirse al grupo de balanceo de carga de los servicios

### Probes de contenedor

Kubernetes proporciona los siguientes probes para comprobar el estado de los contenedores:

1. **livenessProbe**: Comprueba si el contenedor está activo; reinicia el contenedor si falla
2. **readinessProbe**: Comprueba si el contenedor está listo para atender solicitudes; lo excluye del tráfico del servicio si falla
3. **startupProbe**: Comprueba si la aplicación del contenedor se ha iniciado; deshabilita los otros probes hasta que tenga éxito

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-probes
spec:
  containers:
  - name: app
    image: myapp:1.0
    ports:
    - containerPort: 8080
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
    startupProbe:
      httpGet:
        path: /startup
        port: 8080
      failureThreshold: 30
      periodSeconds: 10
```

### Proceso de terminación de Pod

Cuando se termina un Pod, se produce el siguiente proceso:

1. **Solicitud de eliminación al servidor de API**: El usuario o controlador solicita la eliminación del Pod
2. **Inicio del período de terminación**: Se establece el período de terminación predeterminado (30 segundos)
3. **Actualización de API**: El servidor de API actualiza la marca de tiempo de eliminación del Pod
4. **Eliminación del servicio**: El controlador de endpoints elimina el Pod de los endpoints de servicio
5. **Señal SIGTERM**: kubelet envía la señal SIGTERM a los contenedores
6. **Espera de apagado ordenado**: Se proporciona tiempo para que las aplicaciones se apaguen ordenadamente
7. **Señal SIGKILL**: Si los contenedores no terminan después del período de terminación, se envía la señal SIGKILL
8. **Limpieza de recursos**: kubelet limpia los recursos del Pod

### Contenedores Init

Los contenedores init son contenedores especiales que se ejecutan antes de que se inicien los contenedores de aplicación en un Pod:

1. **Ejecución secuencial**: Los contenedores init se ejecutan de uno en uno en el orden en que se definen
2. **Requisito previo**: Cada contenedor init se inicia solo después de que el contenedor anterior se haya completado correctamente
3. **Reinicio ante errores**: Si un contenedor init falla, se reinicia según la política de reinicio del Pod
4. **Propósito**: Configuración previa al inicio del contenedor de aplicación, verificación de dependencias, configuración de permisos, etc.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: init-pod
spec:
  initContainers:
  - name: init-myservice
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup myservice; do echo waiting for myservice; sleep 2; done;']
  - name: init-mydb
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup mydb; do echo waiting for mydb; sleep 2; done;']
  containers:
  - name: app
    image: myapp:1.0
```

### Interrupción de Pod

Las interrupciones de Pod se pueden dividir en interrupciones voluntarias o involuntarias:

1. **Interrupciones voluntarias**: Interrupciones realizadas por administradores del clúster o herramientas de automatización
   - Drenaje de nodos
   - Actualizaciones de Deployment
   - Eliminación de Pod

2. **Interrupciones involuntarias**: Interrupciones debidas a fallos de hardware, kernel panics, particiones de red, etc.

PodDisruptionBudget puede garantizar una disponibilidad mínima durante las interrupciones voluntarias.

## Patrones de diseño de Pod

Hay varios patrones y prácticas recomendadas que se deben considerar al diseñar Pods. Comprender y aplicar estos patrones puede mejorar la estabilidad, escalabilidad y mantenibilidad de las aplicaciones.

### Principio de responsabilidad única

Los Pods deben seguir el principio de responsabilidad única:

1. **Una función principal**: Cada Pod debe ser responsable de una función o proceso principal
2. **Escalado independiente**: Diseñe de modo que cada función pueda escalarse de forma independiente
3. **Ciclo de vida independiente**: Diseñe de modo que cada función pueda tener su propio ciclo de vida

### Plantillas de Pod

Las plantillas de Pod son especificaciones que se usan para crear Pods en recursos de carga de trabajo (Deployments, StatefulSets, etc.):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:  # Pod template starts
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
  # Pod template ends
```

### Afinidad y antiafinidad de Pod

La afinidad y antiafinidad de Pod son reglas que controlan en qué nodos se programan los Pods:

1. **Afinidad de Pod**: Programar en el mismo nodo o dominio de topología que Pods específicos
2. **Antiafinidad de Pod**: Programar en un nodo o dominio de topología diferente de Pods específicos

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: "kubernetes.io/hostname"
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - web
          topologyKey: "kubernetes.io/hostname"
  containers:
  - name: web
    image: nginx:1.21
```

### Afinidad de nodo

La afinidad de nodo es una regla que restringe que los Pods se programen en nodos específicos:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values:
            - "true"
  containers:
  - name: gpu-container
    image: gpu-app:1.0
```

### Taints y tolerations

Los taints se aplican a los nodos para impedir que se programen ciertos Pods, y las tolerations se aplican a los Pods para permitir su programación en nodos con taints:

```yaml
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Apply toleration to Pod
apiVersion: v1
kind: Pod
metadata:
  name: tolerant-pod
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: app
    image: myapp:1.0
```

### Solicitudes y límites de recursos

Establecer solicitudes y límites de recursos para los contenedores en Pods es importante para el uso eficiente de los recursos del clúster y para garantizar la estabilidad:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### Contexto de seguridad de Pod

El contexto de seguridad define la configuración de seguridad en el nivel de Pod o de contenedor:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

### Prioridad y preempción de Pod

La prioridad y preempción de Pod determinan qué Pods se programan y cuáles se desalojan cuando los recursos del clúster son insuficientes:

```yaml
# Priority class definition
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical pods only."

# Pod using priority class
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: app
    image: myapp:1.0
```

## Descripción general de los recursos de carga de trabajo

Kubernetes proporciona diversos recursos de carga de trabajo para administrar Pods. Cada recurso de carga de trabajo está diseñado para casos de uso y requisitos específicos.

### Tipos de recursos de carga de trabajo

Los principales recursos de carga de trabajo en Kubernetes son:

1. **ReplicaSet**: Mantiene un número especificado de réplicas de Pod
2. **Deployment**: Administra ReplicaSets para proporcionar actualizaciones declarativas
3. **StatefulSet**: Recurso para aplicaciones que requieren persistencia de estado
4. **DaemonSet**: Ejecuta una copia de un Pod en todos los nodos
5. **Job**: Tareas de una sola vez que terminan tras completarse
6. **CronJob**: Ejecuta Jobs periódicamente según una programación

### Criterios de selección de recursos de carga de trabajo

Criterios para seleccionar el recurso de carga de trabajo apropiado:

1. **Persistencia de estado**: Si la aplicación necesita mantener el estado
2. **Patrón de ejecución**: Si se ejecuta de forma continua, una sola vez o periódicamente
3. **Requisitos de implementación**: Requisitos para actualizaciones graduales, implementaciones blue/green, etc.
4. **Cobertura de nodos**: Si necesita ejecutarse en todos los nodos
5. **Requisitos de escalabilidad**: Si se necesita escalado horizontal

## ReplicaSet

Un ReplicaSet garantiza que un número especificado de réplicas de Pod siempre esté en ejecución. Si los Pods fallan o se eliminan, ReplicaSet crea automáticamente Pods de reemplazo.

### Características principales de ReplicaSet

1. **Mantener réplicas de Pod**: Mantiene el número especificado de réplicas de Pod
2. **Selección de Pod**: Identifica los Pods que se administrarán mediante selectores de etiquetas
3. **Creación de Pod**: Crea Pods nuevos cuando es necesario
4. **Eliminación de Pod**: Elimina Pods excedentes

### Definición de ReplicaSet

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: frontend
  labels:
    app: guestbook
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      tier: frontend
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      containers:
      - name: php-redis
        image: gcr.io/google_samples/gb-frontend:v3
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
        ports:
        - containerPort: 80
```

### Funcionamiento de ReplicaSet

1. **Coincidencia de selector de etiquetas**: ReplicaSet identifica los Pods que coinciden con el selector de etiquetas
2. **Comprobar el estado actual**: Verifica el número de Pods que se ejecutan actualmente
3. **Comparar con el estado deseado**: Compara el recuento actual de Pods con el número deseado de réplicas
4. **Acciones de ajuste**: Crea o elimina Pods según sea necesario

### ReplicaSet frente a Replication Controller

ReplicaSet es el sucesor de Replication Controller y proporciona selectores de etiquetas más eficaces:

1. **Replication Controller**: Solo admite selectores basados en igualdad (p. ej., app=nginx)
2. **ReplicaSet**: Admite selectores basados en conjuntos (p. ej., app in (nginx, apache))

### Casos de uso de ReplicaSet

Los ReplicaSets generalmente se usan de forma indirecta mediante Deployments, en lugar de directamente. Sin embargo, pueden usarse directamente en los siguientes casos:

1. **Replicación simple**: Cuando simplemente se mantienen réplicas de Pod
2. **Actualizaciones personalizadas**: Cuando se necesitan mecanismos de actualización personalizados
3. **Compatibilidad heredada**: Compatibilidad con aplicaciones heredadas

## Deployment

Un Deployment administra ReplicaSets para proporcionar actualizaciones declarativas de Pods. Los Deployments administran actualizaciones graduales, rollbacks, escalado y más para las aplicaciones.

### Características principales de Deployment

1. **Actualizaciones declarativas**: Se declara el estado deseado y Deployment cambia el estado actual al estado deseado
2. **Actualizaciones graduales**: Actualizan aplicaciones sin tiempo de inactividad
3. **Rollback**: Reversión sencilla a versiones anteriores
4. **Escalado**: Ajusta el número de réplicas de aplicación
5. **Historial de implementación**: Mantiene registros de versiones de implementación anteriores

### Definición de Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
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
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
          limits:
            cpu: 200m
            memory: 200Mi
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

### Estrategias de actualización de Deployment

Los Deployments proporcionan dos estrategias de actualización:

1. **RollingUpdate**: Actualiza gradualmente los Pods para implementar sin tiempo de inactividad (predeterminado)
   - **maxSurge**: Número máximo de Pods que se pueden crear por encima del recuento deseado de Pods
   - **maxUnavailable**: Número máximo de Pods no disponibles durante la actualización

2. **Recreate**: Elimina todos los Pods existentes antes de crear Pods nuevos (provoca un tiempo de inactividad temporal)

### Rollback de Deployment

Los Deployments admiten rollback a versiones anteriores:

```bash
# Check deployment history
kubectl rollout history deployment/nginx-deployment

# Check details of specific version
kubectl rollout history deployment/nginx-deployment --revision=2

# Rollback to previous version
kubectl rollout undo deployment/nginx-deployment

# Rollback to specific version
kubectl rollout undo deployment/nginx-deployment --to-revision=2
```

### Escalado de Deployment

Los Deployments pueden escalarse fácilmente:

```bash
# Imperative scaling
kubectl scale deployment/nginx-deployment --replicas=5

# Declarative scaling (after modifying YAML file)
kubectl apply -f deployment.yaml
```

### Pausa y reanudación de Deployment

Los rollouts de Deployment pueden pausarse y reanudarse:

```bash
# Pause rollout
kubectl rollout pause deployment/nginx-deployment

# Apply multiple changes
kubectl set image deployment/nginx-deployment nginx=nginx:1.22
kubectl set resources deployment/nginx-deployment -c=nginx --limits=cpu=200m,memory=256Mi

# Resume rollout
kubectl rollout resume deployment/nginx-deployment
```

### Estado de Deployment

Los Deployments pueden tener los siguientes estados:

1. **Progressing**: Se está creando o escalando hacia arriba o abajo un ReplicaSet nuevo
2. **Complete**: Todas las réplicas se han actualizado y están disponibles
3. **Failed**: Se produjo un error durante la implementación (p. ej., error al extraer una imagen, recursos insuficientes)

## StatefulSet

StatefulSet es un recurso de carga de trabajo para aplicaciones que requieren persistencia de estado. Asigna identificadores únicos a cada Pod y proporciona identificadores de red estables y almacenamiento persistente.

### Características principales de StatefulSet

1. **Identificadores de red estables y únicos**: Los nombres y hostnames de los Pods se mantienen incluso después de reinicios
2. **Almacenamiento estable y persistente**: Acceso al mismo almacenamiento incluso cuando los Pods se reprograman
3. **Implementación y escalado secuenciales**: Los Pods se crean, actualizan y eliminan en orden
4. **Actualizaciones graduales automáticas secuenciales**: Los Pods se actualizan en orden

### Definición de StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  selector:
    matchLabels:
      app: nginx
  serviceName: "nginx"
  replicas: 3
  updateStrategy:
    type: RollingUpdate
  podManagementPolicy: OrderedReady
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
          name: web
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: www
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "standard"
      resources:
        requests:
          storage: 1Gi
```

### Identificadores de Pod de StatefulSet

StatefulSet asigna identificadores únicos a los Pods en el siguiente formato:
```
<StatefulSet name>-<ordinal index>
```

Por ejemplo, un StatefulSet `web` crea Pods como `web-0`, `web-1`, `web-2`.

### Service headless de StatefulSet

Los StatefulSets normalmente se utilizan con un Service headless (clusterIP: None). Esto crea registros DNS para cada Pod:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  ports:
  - port: 80
    name: web
  clusterIP: None
  selector:
    app: nginx
```

Con esto, cada Pod tiene un nombre DNS en el siguiente formato:
```
<Pod name>.<service name>.<namespace>.svc.cluster.local
```

Ejemplo: `web-0.nginx.default.svc.cluster.local`

### Almacenamiento de StatefulSet

Los StatefulSets usan `volumeClaimTemplates` para crear automáticamente Persistent Volume Claims (PVCs) para cada Pod. Estos PVCs se mantienen incluso cuando los Pods se reprograman.

### Estrategias de actualización de StatefulSet

Los StatefulSets proporcionan dos estrategias de actualización:

1. **RollingUpdate**: Actualiza Pods en orden (predeterminado)
2. **OnDelete**: Actualiza solo cuando se eliminan los Pods

### Política de administración de Pods

Los StatefulSets proporcionan dos políticas de administración de Pods:

1. **OrderedReady**: Crea y termina Pods en orden (predeterminado)
2. **Parallel**: Crea y termina Pods en paralelo

### Casos de uso de StatefulSet

Los StatefulSets son adecuados para las siguientes aplicaciones:

1. **Bases de datos**: MySQL, PostgreSQL, MongoDB, etc.
2. **Sistemas distribuidos**: Kafka, ZooKeeper, Elasticsearch, etc.
3. **Colas de mensajes**: RabbitMQ, etc.
4. **Otras aplicaciones con estado**: Servidores de archivos, almacenes de sesión, etc.

### Ejemplo de StatefulSet: replicación de MySQL

```yaml
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
  template:
    metadata:
      labels:
        app: mysql
    spec:
      initContainers:
      - name: init-mysql
        image: mysql:5.7
        command:
        - bash
        - "-c"
        - |
          set -ex
          # Generate server ID based on Pod index
          [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
          ordinal=${BASH_REMATCH[1]}
          echo [mysqld] > /mnt/conf.d/server-id.cnf
          echo server-id=$((100 + $ordinal)) >> /mnt/conf.d/server-id.cnf
          # Master or slave configuration
          if [[ $ordinal -eq 0 ]]; then
            echo [mysqld] > /mnt/conf.d/master.cnf
            echo log-bin=mysql-bin >> /mnt/conf.d/master.cnf
          else
            echo [mysqld] > /mnt/conf.d/slave.cnf
            echo super-read-only >> /mnt/conf.d/slave.cnf
          fi
        volumeMounts:
        - name: conf
          mountPath: /mnt/conf.d
      - name: clone-mysql
        image: gcr.io/google-samples/xtrabackup:1.0
        command:
        - bash
        - "-c"
        - |
          set -ex
          # Only perform replication if not the first Pod
          [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
          ordinal=${BASH_REMATCH[1]}
          if [[ $ordinal -eq 0 ]]; then
            exit 0
          fi
          # Replicate data from previous Pod
          ncat --recv-only mysql-$(($ordinal-1)).mysql 3307 | xbstream -x -C /var/lib/mysql
          # Prepare backup
          xtrabackup --prepare --target-dir=/var/lib/mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
      containers:
      - name: mysql
        image: mysql:5.7
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
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          exec:
            command: ["mysqladmin", "ping"]
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          exec:
            command: ["mysql", "-h", "127.0.0.1", "-e", "SELECT 1"]
          initialDelaySeconds: 5
          periodSeconds: 2
          timeoutSeconds: 1
      - name: xtrabackup
        image: gcr.io/google-samples/xtrabackup:1.0
        ports:
        - name: xtrabackup
          containerPort: 3307
        command:
        - bash
        - "-c"
        - |
          set -ex
          cd /var/lib/mysql
          # Start slave
          if [[ -f xtrabackup_slave_info ]]; then
            cat xtrabackup_slave_info | sed -E 's/;$//g' > change_master_to.sql
            mysql -h 127.0.0.1 -e "$(cat change_master_to.sql); RESET SLAVE; START SLAVE;"
          # If replicated from master
          elif [[ -f xtrabackup_binlog_info ]]; then
            [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
            ordinal=${BASH_REMATCH[1]}
            [[ $ordinal -eq 0 ]] && exit 0
            master_host=mysql-0.mysql
            master_log_file=$(cat xtrabackup_binlog_info | awk '{print $1}')
            master_log_pos=$(cat xtrabackup_binlog_info | awk '{print $2}')
            mysql -h 127.0.0.1 -e "CHANGE MASTER TO MASTER_HOST='$master_host', MASTER_USER='root', MASTER_PASSWORD='$MYSQL_ROOT_PASSWORD', MASTER_LOG_FILE='$master_log_file', MASTER_LOG_POS=$master_log_pos; RESET SLAVE; START SLAVE;"
          fi
          # Start backup server
          exec ncat --listen --keep-open --send-only --max-conns=1 3307 -c "xtrabackup --backup --slave-info --stream=xbstream --host=127.0.0.1"
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
      volumes:
      - name: conf
        emptyDir: {}
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 10Gi
```

## DaemonSet

Un DaemonSet garantiza que una copia de un Pod se ejecute en todos los nodos (o en nodos específicos). Cuando se añade un nodo al clúster, los Pods se añaden automáticamente y, cuando se elimina un nodo, también se eliminan los Pods.

### Características principales de DaemonSet

1. **Ejecutar en todos los nodos**: Ejecuta Pods en todos los nodos del clúster
2. **Selección de nodos**: Puede ejecutarse solo en nodos específicos mediante selectores de nodos
3. **Implementación automática**: Implementa Pods automáticamente cuando se añaden nodos nuevos
4. **Limpieza automática**: Limpia los Pods automáticamente cuando se eliminan nodos

### Definición de DaemonSet

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd-elasticsearch
  namespace: kube-system
  labels:
    k8s-app: fluentd-logging
spec:
  selector:
    matchLabels:
      name: fluentd-elasticsearch
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        name: fluentd-elasticsearch
    spec:
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      containers:
      - name: fluentd-elasticsearch
        image: quay.io/fluentd_elasticsearch/fluentd:v2.5.2
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdockercontainers
          mountPath: /var/lib/docker/containers
          readOnly: true
      terminationGracePeriodSeconds: 30
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdockercontainers
        hostPath:
          path: /var/lib/docker/containers
```

### Estrategias de actualización de DaemonSet

Los DaemonSets proporcionan dos estrategias de actualización:

1. **RollingUpdate**: Actualiza Pods secuencialmente (predeterminado)
   - **maxUnavailable**: Número máximo de Pods no disponibles durante la actualización

2. **OnDelete**: Actualiza solo cuando se eliminan los Pods

### Selección de nodos de DaemonSet

Los DaemonSets se pueden configurar para ejecutarse solo en nodos específicos:

```yaml
spec:
  template:
    spec:
      nodeSelector:
        disk: ssd
```

### Tolerations de taints de DaemonSet

Los DaemonSets pueden establecer tolerations para ejecutarse en nodos con taints:

```yaml
spec:
  template:
    spec:
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
```

### Casos de uso de DaemonSet

Los DaemonSets se utilizan para los siguientes propósitos:

1. **Recolectores de registros**: Fluentd, Logstash, etc.
2. **Agentes de supervisión**: Prometheus Node Exporter, Datadog Agent, etc.
3. **Plugins de red**: Calico, Cilium, Weave Net, etc.
4. **Daemons de almacenamiento**: Ceph, GlusterFS, etc.
5. **Agentes de seguridad**: Falco, Sysdig, etc.

### Ejemplo de DaemonSet: Prometheus Node Exporter

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.3.1
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        - --web.listen-address=:9100
        ports:
        - containerPort: 9100
          protocol: TCP
          name: http
        resources:
          limits:
            cpu: 250m
            memory: 180Mi
          requests:
            cpu: 102m
            memory: 180Mi
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
      tolerations:
      - operator: "Exists"
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
```

## Jobs y CronJobs

Los Jobs y CronJobs son recursos de carga de trabajo para ejecutar tareas únicas o periódicas.

### Job

Un Job crea uno o más Pods y continúa ejecutándose hasta que un número especificado de Pods termine correctamente.

#### Características principales de Job

1. **Garantía de finalización**: Se ejecuta hasta que el número especificado de Pods se complete correctamente
2. **Ejecución paralela**: Puede ejecutar varios Pods en paralelo
3. **Reintento**: Reintento automático de Pods fallidos
4. **Limpieza tras la finalización**: Limpieza opcional de Pods tras completar el Job

#### Definición de Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 5      # Number of Pods that must successfully complete
  parallelism: 2      # Number of Pods to run in parallel
  backoffLimit: 4     # Number of retries on failure
  activeDeadlineSeconds: 100  # Job time limit (seconds)
  ttlSecondsAfterFinished: 100  # Deletion time after completion (seconds)
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.34
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
        resources:
          requests:
            cpu: 100m
            memory: 50Mi
          limits:
            cpu: 100m
            memory: 100Mi
      restartPolicy: Never  # or OnFailure
```

#### Modos de finalización de Job

Los Jobs proporcionan dos modos de finalización:

1. **NonIndexed**: Modo de Job estándar en el que el Job se completa cuando el número especificado de Pods se completa correctamente
2. **Indexed**: A cada Pod se le asigna un índice a partir de 0 y ejecuta tareas para rangos de índices específicos

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-job
spec:
  completions: 5
  parallelism: 3
  completionMode: Indexed  # Enable Indexed mode
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.34
        command: ["sh", "-c", "echo Processing item ${JOB_COMPLETION_INDEX}"]
      restartPolicy: Never
```

#### Casos de uso de Job

Los Jobs se utilizan para los siguientes propósitos:

1. **Procesamiento por lotes**: Procesamiento de datos, tareas ETL
2. **Tareas de cómputo**: Cálculos científicos, renderizado
3. **Migraciones de bases de datos**: Actualizaciones de esquema
4. **Tareas administrativas únicas**: Copias de seguridad, tareas de limpieza

### CronJob

Los CronJobs ejecutan Jobs periódicamente según una programación especificada. Funcionan de forma similar a los trabajos cron de Linux.

#### Características principales de CronJob

1. **Ejecución programada**: Especifique la programación de ejecución mediante expresiones cron
2. **Administración de Jobs**: Crea Jobs según la programación
3. **Política de concurrencia**: Define el comportamiento cuando el Job anterior aún se está ejecutando
4. **Límite de historial**: Limita el historial de Jobs completados

#### Definición de CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"  # Run every minute
  timeZone: "America/New_York"  # Timezone (Kubernetes 1.24+)
  concurrencyPolicy: Forbid  # Allow, Forbid, Replace
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  startingDeadlineSeconds: 60
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.34
            command:
            - /bin/sh
            - -c
            - date; echo Hello from the Kubernetes cluster
          restartPolicy: OnFailure
```

#### Expresión cron

Las expresiones cron tienen el siguiente formato:
```
+------------------- minute (0 - 59)
| +----------------- hour (0 - 23)
| | +--------------- day of month (1 - 31)
| | | +------------- month (1 - 12)
| | | | +----------- day of week (0 - 6) (Sunday to Saturday; 7 is also Sunday)
| | | | |
| | | | |
* * * * *
```

Ejemplos comunes de expresiones cron:
- `*/5 * * * *`: Cada 5 minutos
- `0 * * * *`: Cada hora en punto
- `0 0 * * *`: Todos los días a medianoche
- `0 0 * * 0`: Todos los domingos a medianoche
- `0 0 1 * *`: El día 1 de cada mes a medianoche
- `0 0 1 1 *`: El 1 de enero a medianoche cada año

#### Política de concurrencia

Los CronJobs proporcionan tres políticas de concurrencia:

1. **Allow**: Varios Jobs pueden ejecutarse simultáneamente (predeterminado)
2. **Forbid**: Omite el Job nuevo si el Job anterior todavía está en ejecución
3. **Replace**: Reemplaza el Job anterior por el Job nuevo si aún se está ejecutando

#### Casos de uso de CronJob

Los CronJobs se utilizan para los siguientes propósitos:

1. **Copias de seguridad periódicas**: Copias de seguridad de bases de datos, creación de snapshots
2. **Sincronización de datos**: Sincronización periódica de datos
3. **Generación de informes**: Generación de informes diarios, semanales o mensuales
4. **Tareas de limpieza**: Limpieza de archivos temporales, rotación de registros
5. **Notificaciones y supervisión**: Comprobaciones de estado, envío de alertas

#### Ejemplo de CronJob: copia de seguridad de base de datos

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"  # Run daily at 02:00
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
            - |
              pg_dump -Fc > /backup/db-$(date +%Y%m%d-%H%M%S).dump
              find /backup -type f -mtime +7 -delete  # Delete backups older than 7 days
            volumeMounts:
            - name: backup-volume
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-volume
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Conclusión

Este documento cubrió los Pods, el componente básico de Kubernetes, y diversos recursos de carga de trabajo. Partiendo del concepto de Pods, exploramos las características y los casos de uso de diversos recursos de carga de trabajo, incluidos Deployments, StatefulSets, DaemonSets, Jobs y CronJobs. Cada uno de estos recursos tiene propósitos y características únicos, y usarlos adecuadamente permite una implementación y administración eficientes de aplicaciones.

## Cuestionario

Para evaluar lo que aprendió en este capítulo, pruebe el [Cuestionario sobre Pods y cargas de trabajo](../quizzes/core/02-pods-and-workloads-quiz.md).
