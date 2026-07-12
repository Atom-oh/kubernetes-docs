# Introduction to Kubernetes

> **Versiones compatibles**: Kubernetes 1.31, 1.32, 1.33 **Última actualización**: February 11, 2026

Kubernetes (K8s) es una plataforma open-source de orquestación de contenedores que automatiza el despliegue, el escalado y la gestión de aplicaciones en contenedores. Este documento explica los conceptos básicos, la arquitectura, los componentes principales y las características de Kubernetes.

## Lab Environment Setup

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y entorno:

### Required Tools

* **kubectl**: Herramienta de línea de comandos para interactuar con clusters de Kubernetes
* **Container Runtime**: Docker, containerd, CRI-O, etc.
* **minikube** o **kind**: Cluster local de Kubernetes (para desarrollo y aprendizaje)

### Installation Methods

**Instalación de kubectl**:

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Windows (PowerShell)
curl -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"
```

**Instalación de minikube**:

```bash
# macOS
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
chmod +x minikube-linux-amd64
sudo mv minikube-linux-amd64 /usr/local/bin/minikube

# Windows (PowerShell)
New-Item -Path 'c:\' -Name 'minikube' -ItemType Directory
Invoke-WebRequest -OutFile 'c:\minikube\minikube.exe' -Uri 'https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe'
```

### Starting a Local Cluster

```bash
minikube start
```

## Table of Contents

* [What is Kubernetes?](04-kubernetes-introduction.md#what-is-kubernetes)
* [History of Kubernetes](04-kubernetes-introduction.md#history-of-kubernetes)
* [Kubernetes Architecture](04-kubernetes-introduction.md#kubernetes-architecture)
* [Kubernetes Main Components](04-kubernetes-introduction.md#kubernetes-main-components)
* [Kubernetes Basic Objects](04-kubernetes-introduction.md#kubernetes-basic-objects)
* [Kubernetes Workload Resources](04-kubernetes-introduction.md#kubernetes-workload-resources)
* [Kubernetes Services and Networking](04-kubernetes-introduction.md#kubernetes-services-and-networking)
* [Kubernetes Storage](04-kubernetes-introduction.md#kubernetes-storage)
* [Kubernetes Configuration and Security](04-kubernetes-introduction.md#kubernetes-configuration-and-security)
* [Kubernetes vs Amazon EKS](04-kubernetes-introduction.md#kubernetes-vs-amazon-eks)
* [Getting Started with Kubernetes](04-kubernetes-introduction.md#getting-started-with-kubernetes)

## What is Kubernetes?

Kubernetes significa 'timonel' o 'piloto' en griego y es un sistema open-source que automatiza el despliegue, el escalado y la operación de aplicaciones en contenedores. Se inspiró en el sistema interno Borg de Google y se publicó como open source en 2014.

### Key Features of Kubernetes

1. **Service Discovery and Load Balancing**: Expone contenedores externamente y distribuye el tráfico
2. **Storage Orchestration**: Monta automáticamente sistemas de almacenamiento locales o en la nube
3. **Automated Rollouts and Rollbacks**: Cambia gradualmente el estado de la aplicación y restaura el estado anterior ante problemas
4. **Automatic Bin Packing**: Ubica contenedores en nodos según los requisitos de recursos
5. **Self-healing**: Reinicia contenedores fallidos y reemplaza contenedores que no responden
6. **Secret and Configuration Management**: Almacena información sensible y actualiza la configuración
7. **Horizontal Scaling**: Escala aplicaciones mediante comandos simples o una UI
8. **Batch Execution**: Gestiona workloads batch y de CI

### Problems Kubernetes Solves

* **Container Orchestration**: Gestiona de manera eficiente cientos o miles de contenedores
* **High Availability**: Garantiza una operación ininterrumpida de la aplicación
* **Scalability**: Auto scaling basado en el aumento del tráfico
* **Disaster Recovery**: Recuperación automática ante fallos
* **Resource Efficiency**: Utiliza eficientemente los recursos de hardware
* **Declarative Configuration**: Gestiona la infraestructura como código
* **Multi-cloud and Hybrid Cloud**: Despliegue y gestión consistentes en varios entornos

## History of Kubernetes

### Background

* **2003-2013**: Google usó internamente un sistema de orquestación de contenedores llamado Borg
* **June 2014**: Google lanzó Kubernetes como open source
* **July 2015**: Kubernetes 1.0 se lanzó y fue donado a Cloud Native Computing Foundation (CNCF)
* **2016-2017**: Los principales proveedores de nube lanzaron servicios gestionados de Kubernetes
* **2018 and beyond**: Se estableció como el estándar de facto para la orquestación de contenedores

### Origin of the Name

Kubernetes (κυβερνήτης) significa 'timonel' o 'piloto' en griego. Esto simboliza su rol de guiar aplicaciones en contenedores. La abreviatura K8s se usa porque hay 8 caracteres entre 'K' y 's'.

### Meaning of the Logo

El logotipo de Kubernetes representa un timón (rueda de dirección de un barco) con 7 radios, lo que simboliza el rol de Kubernetes al guiar el rumbo de las aplicaciones en contenedores.

## Kubernetes Architecture

Kubernetes sigue una arquitectura master-node. Los master nodes (control plane) gestionan el cluster y los worker nodes ejecutan los workloads reales de la aplicación.

### Control Plane (Master) Components

1. **kube-apiserver**: Frontend del control plane que expone la Kubernetes API
2. **etcd**: Almacén key-value consistente y altamente disponible para todos los datos del cluster
3. **kube-scheduler**: Componente que asigna pods a nodos
4. **kube-controller-manager**: Componente que ejecuta procesos de controller
   * Node Controller: Notificación y respuesta cuando los nodos dejan de funcionar
   * Replication Controller: Mantiene el número correcto de réplicas de pod
   * Endpoints Controller: Conecta services y pods
   * Service Account & Token Controller: Crea cuentas predeterminadas y tokens de acceso a la API para nuevos namespaces
5. **cloud-controller-manager**: Componente que contiene lógica de control específica de la nube
   * Node Controller: Verifica con el proveedor de nube si el nodo ha sido eliminado
   * Route Controller: Configura rutas en la infraestructura de nube
   * Service Controller: Crea, actualiza y elimina load balancers del proveedor de nube
   * Volume Controller: Crea, adjunta y monta volumes

### Node Components

1. **kubelet**: Agent que se ejecuta en cada nodo y garantiza que los contenedores en pods estén en ejecución
2. **kube-proxy**: Network proxy que se ejecuta en cada nodo e implementa el concepto de Kubernetes Service
3. **Container Runtime**: Software responsable de ejecutar contenedores (Docker, containerd, CRI-O, etc.)

### Full Architecture

## Kubernetes Main Components

### API Server (kube-apiserver)

El API server es el frontend del control plane que expone la Kubernetes API. Todas las solicitudes internas y externas se procesan a través del API server.

**Funciones clave**:

* Proporciona REST API
* Autenticación y autorización
* Validación de solicitudes
* Comunicación con etcd
* Escalable horizontalmente

### etcd

etcd es un almacén key-value consistente y altamente disponible que almacena todos los datos del cluster.

**Características clave**:

* Sistema distribuido
* Consistencia fuerte
* Alta disponibilidad
* Almacenamiento seguro de datos
* Función watch para monitorear cambios

### Scheduler (kube-scheduler)

El scheduler es un componente del control plane que selecciona nodos para ejecutar pods recién creados.

**Proceso de scheduling**:

1. **Filtering**: Identificar nodos que pueden ejecutar el pod
2. **Scoring**: Asignar puntuaciones a los nodos adecuados
3. **Binding**: Asignar el pod al nodo óptimo

**Consideraciones**:

* Requisitos de recursos (CPU, memoria)
* Restricciones de hardware/software/política
* Especificaciones de affinity/anti-affinity
* Localidad de datos
* Interferencia de workload

### Controller Manager (kube-controller-manager)

El controller manager es un componente del control plane que ejecuta múltiples procesos de controller.

**Controllers principales**:

* **Node Controller**: Monitorea y responde al estado del nodo
* **Replication Controller**: Mantiene el conteo de réplicas de pod
* **Endpoints Controller**: Conecta services y pods
* **Service Account & Token Controller**: Crea cuentas predeterminadas y tokens de API para namespaces
* **Job Controller**: Gestiona tareas de una sola ejecución
* **CronJob Controller**: Gestiona tareas programadas
* **DaemonSet Controller**: Garantiza que pods específicos se ejecuten en todos los nodos
* **StatefulSet Controller**: Gestiona aplicaciones con estado
* **PV Controller**: Gestiona persistent volumes

### Cloud Controller Manager (cloud-controller-manager)

El cloud controller manager es un componente del control plane que contiene lógica de control específica de la nube.

**Controllers principales**:

* **Node Controller**: Verifica el estado del nodo mediante la API del proveedor de nube
* **Route Controller**: Configura rutas en el entorno de nube
* **Service Controller**: Crea, actualiza y elimina load balancers en la nube
* **Volume Controller**: Crea, adjunta y monta volumes de almacenamiento en la nube

### kubelet

kubelet es un agent que se ejecuta en cada nodo y garantiza que los contenedores en pods estén en ejecución.

**Funciones clave**:

* Ejecutar contenedores según PodSpec
* Reportar el estado de los contenedores
* Realizar comprobaciones de salud de contenedores
* Gestionar el ciclo de vida de los contenedores
* Reportar el estado del nodo

### kube-proxy

kube-proxy es un network proxy que se ejecuta en cada nodo e implementa el concepto de Kubernetes Service.

**Funciones clave**:

* Mantener reglas de red para IPs y puertos de service
* Reenviar conexiones
* Implementar load balancing

**Modos de operación**:

* **userspace mode**: Ejecuta el proxy en el espacio de usuario (legacy)
* **iptables mode**: Implementación de NAT usando Linux iptables (predeterminado)
* **IPVS mode**: Usa IP Virtual Server del kernel de Linux (alto rendimiento)

## Kubernetes Basic Objects

Los objetos de Kubernetes son entidades persistentes que representan el estado del cluster. Estos objetos describen aplicaciones en ejecución, recursos disponibles, políticas, etc. dentro del cluster.

### Pod

Un Pod es la unidad desplegable más pequeña en Kubernetes y representa un grupo de uno o más contenedores. Los contenedores en un pod comparten almacenamiento y red, y siempre se programan juntos en el mismo nodo.

**Características clave**:

* Tiene una dirección IP única
* Namespace de red compartido (mismo espacio de IP y puertos)
* Namespace IPC compartido
* Hostname compartido
* Comunicación localhost posible entre contenedores

**Ejemplo de Pod**:

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
  - name: log-sidecar
    image: busybox
    command: ["/bin/sh", "-c", "tail -f /var/log/nginx/access.log"]
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
```

### Namespace

Los Namespaces proporcionan una forma de aislar grupos de recursos dentro de un único cluster. Esto es útil cuando varios equipos o proyectos comparten el mismo cluster.

**Namespaces predeterminados**:

* **default**: Namespace predeterminado
* **kube-system**: Namespace para objetos creados por el sistema Kubernetes
* **kube-public**: Namespace para objetos legibles por todos los usuarios
* **kube-node-lease**: Namespace para heartbeats de nodos

**Ejemplo de Namespace**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Labels and Selectors

Los Labels son pares key-value adjuntos a objetos, usados para identificar y seleccionar objetos. Los Selectors proporcionan una forma de filtrar objetos según labels.

**Ejemplo de Labels**:

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**Tipos de Selector**:

* **Equality-based**: `=`, `!=`
* **Set-based**: `in`, `notin`, `exists`

**Ejemplo de Selector**:

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### Annotations

Las Annotations son pares key-value que almacenan metadata no identificatoria sobre objetos. Las Annotations son útiles para almacenar información usada por herramientas o bibliotecas.

**Ejemplo de Annotations**:

```yaml
metadata:
  annotations:
    kubernetes.io/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Node

Un node es una máquina worker en un cluster de Kubernetes que ejecuta pods. Un node puede ser una máquina física o virtual.

**Estado de Node**:

* **Addresses**: Hostname, Internal IP, External IP
* **Conditions**: Ready, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable
* **Capacity**: CPU, Memory, Maximum pods
* **Info**: Versión del kernel, versión del container runtime, versión de kubelet

**Ejemplo de Node**:

```yaml
apiVersion: v1
kind: Node
metadata:
  name: worker-1
  labels:
    kubernetes.io/hostname: worker-1
    node-role.kubernetes.io/worker: ""
    topology.kubernetes.io/zone: us-east-1a
spec:
  # ...
status:
  capacity:
    cpu: "4"
    memory: 8Gi
    pods: "110"
  conditions:
    - type: Ready
      status: "True"
  # ...
```

## Kubernetes Workload Resources

Los recursos de workload son objetos usados para gestionar y ejecutar pods. Estos recursos gestionan la creación, el escalado, las actualizaciones y la terminación de pods.

### ReplicaSet

Un ReplicaSet garantiza que siempre se ejecute un número especificado de réplicas de pod. Si los pods fallan o se eliminan, el ReplicaSet crea automáticamente pods de reemplazo.

**Funciones clave**:

* Mantener el número especificado de réplicas de pod
* Definir la plantilla de pod
* Identificar pods mediante selectors

**Ejemplo de ReplicaSet**:

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: nginx-replicaset
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
```

### Deployment

Un Deployment abstrae ReplicaSets un nivel más, proporcionando actualizaciones declarativas para aplicaciones. Los Deployments proporcionan funciones como rolling updates, rollbacks y scaling.

**Funciones clave**:

* Actualizaciones declarativas de aplicaciones
* Rolling updates y rollbacks
* Gestión del historial de Deployment
* Scaling

**Ejemplo de Deployment**:

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
```

### StatefulSet

Un StatefulSet es un recurso de workload para aplicaciones que requieren mantener estado. Asigna identificadores únicos a cada pod y proporciona identificadores de red estables y almacenamiento persistente.

**Funciones clave**:

* Identificadores de red estables y únicos
* Almacenamiento estable y persistente
* Despliegue y scaling secuenciales
* Actualizaciones secuenciales

**Ejemplo de StatefulSet**:

```yaml
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
        - containerPort: 3306
          name: mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
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

### DaemonSet

Un DaemonSet garantiza que una copia de un pod se ejecute en todos los nodos (o nodos específicos). Cuando se agregan nodos al cluster, los pods se agregan automáticamente, y cuando se eliminan nodos, los pods también se eliminan.

**Casos de uso clave**:

* Recolectores de logs (Fluentd, Logstash)
* Agents de monitoreo (Prometheus Node Exporter)
* Plugins de red (Calico, Cilium)
* Daemons de almacenamiento (Ceph)

**Ejemplo de DaemonSet**:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: fluentd
  template:
    metadata:
      labels:
        name: fluentd
    spec:
      tolerations:
      - key: node-role.kubernetes.io/master
        effect: NoSchedule
      containers:
      - name: fluentd
        image: fluentd:v1.14
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 100Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

### Job

Un Job crea uno o más pods y continúa la ejecución hasta que un número especificado de pods termina correctamente. Es adecuado para tareas de procesamiento batch.

**Funciones clave**:

* Ejecución de tareas de una sola vez
* Ejecución de tareas en paralelo
* Garantizar la finalización de tareas
* Reintento ante fallos

**Ejemplo de Job**:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi-calculator
spec:
  completions: 5
  parallelism: 2
  backoffLimit: 3
  template:
    spec:
      containers:
      - name: pi
        image: perl
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```

### CronJob

Un CronJob ejecuta Jobs periódicamente de acuerdo con un schedule especificado. Funciona de manera similar a los cron jobs de Linux.

**Funciones clave**:

* Ejecución de tareas según un schedule
* Soporte para expresiones cron
* Configuración de políticas de concurrencia
* Límites de historial

**Ejemplo de CronJob**:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"  # Run at 02:00 daily
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: database-backup:v1
            env:
            - name: DB_HOST
              value: "db.example.com"
          restartPolicy: OnFailure
```

## Kubernetes Services and Networking

El modelo de red de Kubernetes se basa en la premisa de que todos los pods tienen direcciones IP únicas y pueden comunicarse entre sí sin configuración especial. Los Services proporcionan endpoints estables para conjuntos de pods.

### Service

Un Service proporciona un único endpoint y load balancing para un conjunto de pods. Dado que los pods se crean y eliminan dinámicamente, los services proporcionan direcciones de red estables a pesar de estos cambios.

**Tipos de Service**:

* **ClusterIP**: Service accesible solo dentro del cluster (predeterminado)
* **NodePort**: Accesible externamente a través de la IP de cada nodo y un puerto específico
* **LoadBalancer**: Accesible externamente usando el load balancer del proveedor de nube
* **ExternalName**: Crea un registro CNAME para un service externo

**Ejemplo de Service**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

**Ejemplo de Service NodePort**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-nodeport
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
  type: NodePort
```

**Ejemplo de Service LoadBalancer**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-lb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Ingress

Un Ingress es un objeto de API que gestiona el enrutamiento HTTP y HTTPS desde fuera del cluster hacia services internos. Ingress proporciona load balancing, terminación SSL, hosting virtual basado en nombres, etc.

**Ingress Controllers**:

* **NGINX Ingress Controller**: Ingress controller basado en NGINX
* **AWS ALB Ingress Controller**: Ingress controller basado en AWS Application Load Balancer
* **Traefik**: Edge router cloud-native
* **Istio Ingress**: Ingress basado en service mesh

**Ejemplo de Ingress**:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /app1
        pathType: Prefix
        backend:
          service:
            name: app1-service
            port:
              number: 80
      - path: /app2
        pathType: Prefix
        backend:
          service:
            name: app2-service
            port:
              number: 80
  tls:
  - hosts:
    - example.com
    secretName: example-tls
```

### NetworkPolicy

NetworkPolicy proporciona una forma de controlar la comunicación entre pods. De forma predeterminada, todos los pods pueden comunicarse entre sí, pero puedes restringir esto usando network policies.&#x20;

**Funciones clave**:

* Controlar la comunicación entre pods
* Controlar la comunicación entre namespaces
* Controlar tráfico ingress (entrante) y egress (saliente)
* Filtrado basado en puerto y protocolo

**Ejemplo de NetworkPolicy**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### DNS

Kubernetes proporciona un service DNS dentro del cluster para admitir service discovery. CoreDNS se usa de forma predeterminada.

**Formato de nombre DNS**:

* **Service**: `<service-name>.<namespace>.svc.cluster.local`
* **Pod**: `<pod-IP-address-dots-replaced>.pod.cluster.local`

**Ejemplo de configuración DNS**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health
        kubernetes cluster.local in-addr.arpa ip6.arpa {
          pods insecure
          upstream
          fallthrough in-addr.arpa ip6.arpa
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### Service Mesh

Un service mesh es una capa de infraestructura que gestiona la comunicación entre microservices. Los service meshes proporcionan gestión de tráfico, seguridad y observabilidad.

**Major Service Meshes**:

* **Istio**: Service mesh más utilizado
* **Linkerd**: Service mesh ligero
* **AWS App Mesh**: Service mesh gestionado por AWS

**Ejemplo de Istio VirtualService**:

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

## Kubernetes Storage

Kubernetes proporciona varias opciones de almacenamiento para aplicaciones en contenedores. Proporciona formas de persistir datos incluso cuando los pods se reinician o se reprograman.

### Volume

Un volume es un directorio que se puede montar en contenedores dentro de un pod, persistiendo datos durante el ciclo de vida del pod. Los volumes también se usan para compartir datos entre contenedores en un pod.

**Main Volume Types**:

* **emptyDir**: Comienza como un directorio vacío, se elimina cuando se elimina el pod
* **hostPath**: Monta desde el sistema de archivos del nodo host al pod
* **configMap**: Monta ConfigMap como volume
* **secret**: Monta Secret como volume
* **persistentVolumeClaim**: Monta persistent volume en un pod

**Ejemplo de Volume emptyDir**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - name: test-container
    image: nginx
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### PersistentVolume (PV)

Un PersistentVolume es un objeto de API que representa un recurso de almacenamiento en el cluster. Existe independientemente de los pods y es provisionado por administradores del cluster.

**Access Modes**:

* **ReadWriteOnce (RWO)**: Puede montarse con lectura/escritura por un único nodo
* **ReadOnlyMany (ROX)**: Puede montarse como solo lectura por varios nodos
* **ReadWriteMany (RWX)**: Puede montarse con lectura/escritura por varios nodos

**Ejemplo de PersistentVolume**:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pv-example
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  awsElasticBlockStore:
    volumeID: vol-0123456789abcdef0
    fsType: ext4
```

### PersistentVolumeClaim (PVC)

Un PersistentVolumeClaim es un objeto de API que representa una solicitud de almacenamiento de un usuario. Los pods acceden a PVs mediante PVCs.

**Ejemplo de PersistentVolumeClaim**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pvc-example
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: standard
```

**Ejemplo de Pod usando PVC**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: pvc-example
```

### StorageClass

Una StorageClass describe "clases" de almacenamiento proporcionadas por administradores. Se pueden proporcionar distintos niveles de calidad de servicio, políticas de backup o políticas arbitrarias determinadas por administradores del cluster.

**Ejemplo de StorageClass**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  fsType: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
```

### Dynamic Provisioning

Dynamic provisioning es una característica que crea PVs automáticamente cuando se solicitan PVCs usando storage classes.

**Ejemplo de Dynamic Provisioning**:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dynamic-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard  # Storage class for dynamic provisioning
```

### CSI (Container Storage Interface)

CSI proporciona una interfaz estándar entre Kubernetes y los sistemas de almacenamiento. Esto permite que los proveedores de almacenamiento desarrollen sus propios storage drivers sin modificar el código de Kubernetes.

**Major CSI Drivers**:

* **AWS EBS CSI Driver**: Gestión de volumes de Amazon EBS
* **AWS EFS CSI Driver**: Gestión de file systems de Amazon EFS
* **AWS FSx for Lustre CSI Driver**: Gestión de file systems FSx for Lustre
* **GCE PD CSI Driver**: Gestión de persistent disks de Google Compute Engine
* **Azure Disk CSI Driver**: Gestión de disks de Azure

**Ejemplo de Deployment de CSI Driver**:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  fsType: ext4
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

## Kubernetes Configuration and Security

Kubernetes proporciona varios objetos y mecanismos para gestionar la configuración y la seguridad de las aplicaciones.

### ConfigMap

Un ConfigMap es un objeto de API que almacena datos de configuración como pares key-value. Los pods pueden usar datos de ConfigMap como variables de entorno, argumentos de línea de comandos o archivos de configuración.

**Ejemplo de ConfigMap**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  app.properties: |
    app.name=MyApp
    app.version=1.0.0
    app.environment=production
  log-level: INFO
  max-connections: "100"
```

**Ejemplo de Pod usando ConfigMap**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    env:
    - name: LOG_LEVEL
      valueFrom:
        configMapKeyRef:
          name: app-config
          key: log-level
    volumeMounts:
    - name: config-volume
      mountPath: /etc/config
  volumes:
  - name: config-volume
    configMap:
      name: app-config
```

### Secret

Un Secret es un objeto de API que almacena información sensible como contraseñas, tokens y keys. Es similar a ConfigMap, pero está diseñado para datos sensibles.

**Secret Types**:

* **Opaque**: Datos arbitrarios definidos por el usuario (predeterminado)
* **kubernetes.io/service-account-token**: Token de service account
* **kubernetes.io/dockercfg**: Archivo \~/.dockercfg serializado
* **kubernetes.io/dockerconfigjson**: Archivo \~/.docker/config.json serializado
* **kubernetes.io/basic-auth**: Credenciales para autenticación básica
* **kubernetes.io/ssh-auth**: Credenciales para autenticación SSH
* **kubernetes.io/tls**: Datos para cliente o servidor TLS

**Ejemplo de Secret**:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=  # base64 encoded "admin"
  password: cGFzc3dvcmQxMjM=  # base64 encoded "password123"
```

**Ejemplo de Pod usando Secret**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secret-pod
spec:
  containers:
  - name: db-client
    image: db-client:1.0
    env:
    - name: DB_USERNAME
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: username
    - name: DB_PASSWORD
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
```

### RBAC (Role-Based Access Control)

RBAC es un mecanismo para controlar el acceso a la Kubernetes API. Otorga permisos específicos a usuarios o service accounts usando Roles y RoleBindings.

**Main RBAC Objects**:

* **Role**: Define un conjunto de permisos dentro de un namespace
* **ClusterRole**: Define un conjunto de permisos en todo el cluster
* **RoleBinding**: Vincula un role a usuarios, grupos o service accounts
* **ClusterRoleBinding**: Vincula un cluster role a usuarios, grupos o service accounts

**Ejemplo de Role**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**Ejemplo de RoleBinding**:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: jane
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### ServiceAccount

Un ServiceAccount proporciona una identidad para procesos que se ejecutan dentro de un pod. Los pods usan service accounts para comunicarse con la Kubernetes API.

**Ejemplo de ServiceAccount**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
```

**Ejemplo de Pod usando ServiceAccount**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sa-pod
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: myapp:1.0
```

### NetworkPolicy

NetworkPolicy proporciona una forma de controlar la comunicación entre pods. De forma predeterminada, todos los pods pueden comunicarse entre sí, pero puedes restringir esto usando network policies.

**Ejemplo de NetworkPolicy**:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      role: db
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 3306
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: monitoring
    ports:
    - protocol: TCP
      port: 9090
```

### PodSecurityPolicy

PodSecurityPolicy define condiciones relacionadas con seguridad para la creación y actualización de pods. Ha estado deprecado desde Kubernetes 1.21 y fue reemplazado por Pod Security Standards.

**Pod SecurityContext Example**:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-context-pod
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

### Pod Security Standards

Pod Security Standards proporciona tres niveles de política que definen requisitos de seguridad para pods:

1. **Privileged**: Sin restricciones, todas las funciones permitidas
2. **Baseline**: Previene escaladas de privilegios conocidas
3. **Restricted**: Restricciones fuertes que aplican best practices

**Pod Security Standards Application Example**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## Kubernetes vs Amazon EKS

Amazon EKS (Elastic Kubernetes Service) es un servicio gestionado de Kubernetes proporcionado por AWS. EKS proporciona todas las características básicas de Kubernetes y agrega integración con servicios de AWS y comodidad de gestión.

### Key Differences

| Characteristic           | Self-managed Kubernetes                         | Amazon EKS                                                        |
| ------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| Control Plane Management | User manages directly                           | Managed by AWS                                                    |
| High Availability        | User must configure                             | Provided by default (deployed across multiple availability zones) |
| Upgrades                 | User performs directly                          | Managed by AWS (user can initiate)                                |
| Security Patches         | User applies directly                           | Automatically applied by AWS                                      |
| Authentication           | Various options need configuration              | Integrated with AWS IAM                                           |
| Networking               | CNI plugin selection and configuration required | Amazon VPC CNI provided by default                                |
| Load Balancing           | Manual configuration required                   | AWS Load Balancer Controller integration                          |
| Storage                  | Storage driver configuration required           | EBS, EFS, FSx CSI driver integration                              |
| Monitoring               | Manual setup required                           | CloudWatch Container Insights integration                         |
| Cost                     | Infrastructure costs only                       | Control plane cost + infrastructure costs                         |

### Additional EKS Features

1. **AWS IAM Integration**: Integración de Kubernetes RBAC y AWS IAM
2. **AWS Load Balancer Controller**: Integración de ALB y NLB con services e ingress de Kubernetes
3. **EKS Managed Node Groups**: Automatización de gestión del ciclo de vida de nodos
4. **Fargate Profiles**: Ejecución serverless de pods de Kubernetes
5. **VPC CNI Plugin**: Integración con redes de AWS VPC
6. **CloudWatch Container Insights**: Monitoreo y logging de contenedores
7. **AWS App Mesh**: Integración de service mesh
8. **AWS Distro for OpenTelemetry**: Tracing distribuido y monitoreo
9. **EKS Console and CLI**: Interfaces de gestión
10. **EKS Blueprints**: Configuración de cluster basada en best practices

### EKS-Specific Components

1. **EKS Control Plane**: Alta disponibilidad en varias zonas de disponibilidad
2. **EKS Node AMI**: AMI de Amazon Linux o Ubuntu optimizada para Kubernetes
3. **EKS Managed Node Groups**: Soporte de auto scaling y actualizaciones
4. **EKS Fargate**: Entorno serverless de ejecución de contenedores
5. **EKS Connector**: Conecta clusters externos de Kubernetes a la consola de AWS
6. **EKS Anywhere**: Ejecuta clusters compatibles con EKS en entornos on-premises
7. **EKS Distro**: Distribución de Kubernetes gestionada por AWS

### AWS Service Integration

EKS se integra con los siguientes servicios de AWS:

1. **Amazon VPC**: Infraestructura de redes
2. **AWS IAM**: Autenticación y autorización
3. **Amazon ECR**: Repositorio de imágenes de contenedores
4. **AWS Load Balancer**: Distribución de tráfico de aplicaciones
5. **Amazon EBS/EFS/FSx**: Almacenamiento persistente
6. **AWS CloudWatch**: Monitoreo y logging
7. **AWS CloudTrail**: Auditoría y cumplimiento
8. **AWS KMS**: Gestión de keys de cifrado
9. **AWS WAF**: Firewall de aplicaciones web
10. **AWS Shield**: Protección DDoS
11. **AWS X-Ray**: Tracing distribuido
12. **AWS App Mesh**: Service mesh
13. **AWS SageMaker**: Workloads de machine learning
14. **AWS Bedrock**: Workloads de IA generativa

## Getting Started with Kubernetes

Hay varias formas de comenzar con Kubernetes. Aquí presentamos brevemente cómo iniciar Kubernetes en un entorno de desarrollo local y en AWS EKS.

### Local Development Environment

#### Minikube

Minikube es una herramienta que ejecuta un cluster de Kubernetes de un solo nodo en tu máquina local.

**Installation and Start**:

```bash
# Install
brew install minikube

# Start
minikube start

# Check status
minikube status

# Open dashboard
minikube dashboard
```

#### Kind (Kubernetes in Docker)

Kind es una herramienta que ejecuta clusters de Kubernetes localmente usando contenedores Docker como nodos.

**Installation and Start**:

```bash
# Install
brew install kind

# Create cluster
kind create cluster --name my-cluster

# Check cluster
kind get clusters
kubectl cluster-info --context kind-my-cluster
```

#### Docker Desktop

Docker Desktop proporciona una característica para ejecutar Kubernetes fácilmente en Mac y Windows.

**Configuración**:

1. Instala Docker Desktop
2. Settings > Kubernetes > Check "Enable Kubernetes"
3. Haz clic en "Apply & Restart"

### AWS EKS

#### Creating EKS Cluster with eksctl

eksctl es una herramienta CLI simple para crear y gestionar clusters de EKS.

**Installation and Cluster Creation**:

```bash
# Install eksctl
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Configure AWS CLI
aws configure

# Create EKS cluster
eksctl create cluster \
  --name my-cluster \
  --region ap-northeast-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed

# Check cluster
kubectl get nodes
```

#### Creating EKS Cluster with AWS Management Console

También puedes crear clusters EKS mediante AWS Management Console.

**Steps**:

1. Inicia sesión en AWS Management Console
2. Navega al servicio EKS
3. Haz clic en "Create cluster"
4. Configura el nombre del cluster, IAM role, VPC y subnets
5. Configura security groups
6. Configura opciones de logging
7. Crea el cluster
8. Agrega node groups

### kubectl Installation and Configuration

kubectl es una herramienta de línea de comandos para interactuar con clusters de Kubernetes.

**Installation**:

```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Windows (PowerShell)
curl -LO "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"
```

**Basic Commands**:

```bash
# Check cluster info
kubectl cluster-info

# List nodes
kubectl get nodes

# Check pods in all namespaces
kubectl get pods --all-namespaces

# Create deployment
kubectl create deployment nginx --image=nginx

# Expose service
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# Check logs
kubectl logs <pod-name>

# Execute command in pod container
kubectl exec -it <pod-name> -- /bin/bash
```

### Installing Kubernetes Dashboard

Kubernetes Dashboard proporciona una UI basada en web para gestionar clusters.

**Installation and Access**:

```bash
# Install dashboard
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml

# Create admin user
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF

# Get token
kubectl -n kubernetes-dashboard create token admin-user

# Access dashboard
kubectl proxy
```

Se puede acceder al dashboard en http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/.

## Conclusion

Kubernetes es una plataforma potente que automatiza el despliegue, el escalado y la gestión de aplicaciones en contenedores. Resumen del contenido clave cubierto en este documento:

### Core Architecture

* **Control Plane**: Cerebro del cluster (API Server, etcd, Scheduler, Controller Manager)
* **Worker Nodes**: Nodos que ejecutan aplicaciones reales (kubelet, kube-proxy, Container Runtime)
* **Declarative Configuration**: Define el estado deseado y Kubernetes ajusta el estado actual al estado deseado

### Main Objects and Resources

* **Basic Objects**: Pod, Service, Volume, Namespace
* **Workload Resources**: Deployment, StatefulSet, DaemonSet, Job, CronJob
* **Configuration and Security**: ConfigMap, Secret, RBAC, ServiceAccount
* **Networking**: Service, Ingress, NetworkPolicy
* **Storage**: PersistentVolume, PersistentVolumeClaim, StorageClass

### Recommended Learning Path

**Step 1: Build Local Environment**

* Crear un cluster local con minikube o kind
* Aprender comandos de kubectl
* Practicar con objetos básicos (Pod, Deployment, Service)

**Step 2: Master Core Concepts**

* Entender y practicar recursos de workload
* Gestión de configuración con ConfigMap y Secret
* Configurar networking con Service e Ingress
* Gestionar storage con PV y PVC

**Step 3: Learn Advanced Features**

* RBAC y políticas de seguridad
* Auto scaling (HPA, VPA, Cluster Autoscaler)
* Monitoreo y logging (Prometheus, Grafana)
* Service mesh (Istio, Linkerd)

**Step 4: Production Operations**

* Usar Amazon EKS u otro Kubernetes gestionado
* Integración de pipelines CI/CD
* Estrategias de disaster recovery y backup
* Optimización de costos y gestión de recursos

### Next Steps

* **EKS Deep Dive**: Características específicas de EKS (Fargate, VPC CNI, ALB Controller)
* **Advanced Networking**: Plugins CNI (Calico, Cilium)
* **Observability**: Metrics, logs, tracing
* **GitOps**: ArgoCD, Flux
* **Security Hardening**: Pod Security Standards, Network Policies, OPA/Gatekeeper

Kubernetes continúa evolucionando y se ha convertido en un elemento central del desarrollo y las operaciones de aplicaciones cloud-native. Esperamos que este documento te ayude a iniciar tu recorrido con Kubernetes.

### Additional Learning Resources

* **Official Documentation**: [Kubernetes Official Documentation](https://kubernetes.io/docs/) proporciona la información más precisa y actualizada
* **Interactive Tutorials**: Práctica hands-on disponible en [Kubernetes Tutorials](https://kubernetes.io/docs/tutorials/)
* **Community**: [Kubernetes Slack](https://slack.k8s.io/), [Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **Certifications**: CKA (Certified Kubernetes Administrator), CKAD (Certified Kubernetes Application Developer)
* **Korean Community**: Kubernetes Korea User Group, AWS Korea User Group

## Quiz

Para probar lo que aprendiste en este capítulo, realiza el [Introduction to Kubernetes Quiz](../quizzes/basics/04-kubernetes-introduction-quiz.md).

## References

* [Kubernetes Official Documentation](https://kubernetes.io/docs/)
* [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
* [Kubernetes GitHub Repository](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
