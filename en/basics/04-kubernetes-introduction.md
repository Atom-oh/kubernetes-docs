# Introduction to Kubernetes

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33 **Last Updated**: February 11, 2026

Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. This document explains the basic concepts, architecture, main components, and features of Kubernetes.

## Lab Environment Setup

To follow along with the examples in this document, you will need the following tools and environment:

### Required Tools

* **kubectl**: Command-line tool for interacting with Kubernetes clusters
* **Container Runtime**: Docker, containerd, CRI-O, etc.
* **minikube** or **kind**: Local Kubernetes cluster (for development and learning)

### Installation Methods

**kubectl Installation**:

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

**minikube Installation**:

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

Kubernetes means 'helmsman' or 'pilot' in Greek and is an open-source system that automates the deployment, scaling, and operation of containerized applications. It was inspired by Google's internal Borg system and was released as open source in 2014.

### Key Features of Kubernetes

1. **Service Discovery and Load Balancing**: Expose containers externally and distribute traffic
2. **Storage Orchestration**: Automatically mount local or cloud storage systems
3. **Automated Rollouts and Rollbacks**: Gradually change application state and restore to previous state on issues
4. **Automatic Bin Packing**: Place containers on nodes based on resource requirements
5. **Self-healing**: Restart failed containers and replace unresponsive containers
6. **Secret and Configuration Management**: Store sensitive information and update configuration
7. **Horizontal Scaling**: Scale applications through simple commands or UI
8. **Batch Execution**: Manage batch and CI workloads

### Problems Kubernetes Solves

* **Container Orchestration**: Efficiently manage hundreds or thousands of containers
* **High Availability**: Ensure uninterrupted application operation
* **Scalability**: Auto scaling based on traffic increase
* **Disaster Recovery**: Automatic recovery on failures
* **Resource Efficiency**: Efficiently utilize hardware resources
* **Declarative Configuration**: Manage infrastructure as code
* **Multi-cloud and Hybrid Cloud**: Consistent deployment and management across various environments

## History of Kubernetes

### Background

* **2003-2013**: Google internally used a container orchestration system called Borg
* **June 2014**: Google released Kubernetes as open source
* **July 2015**: Kubernetes 1.0 released and donated to Cloud Native Computing Foundation (CNCF)
* **2016-2017**: Major cloud providers launched managed Kubernetes services
* **2018 and beyond**: Established as the de facto standard for container orchestration

### Origin of the Name

Kubernetes (κυβερνήτης) means 'helmsman' or 'pilot' in Greek. This symbolizes its role in guiding containerized applications. The abbreviation K8s is used because there are 8 characters between 'K' and 's'.

### Meaning of the Logo

The Kubernetes logo depicts a helm (ship's steering wheel) with 7 spokes, symbolizing Kubernetes' role in guiding the course of containerized applications.

## Kubernetes Architecture

Kubernetes follows a master-node architecture. Master nodes (control plane) manage the cluster, and worker nodes run the actual application workloads.

### Control Plane (Master) Components

1. **kube-apiserver**: Frontend of the control plane that exposes the Kubernetes API
2. **etcd**: Consistent and highly available key-value store for all cluster data
3. **kube-scheduler**: Component that assigns pods to nodes
4. **kube-controller-manager**: Component that runs controller processes
   * Node Controller: Notification and response when nodes go down
   * Replication Controller: Maintains correct number of pod replicas
   * Endpoints Controller: Connects services and pods
   * Service Account & Token Controller: Creates default accounts and API access tokens for new namespaces
5. **cloud-controller-manager**: Component containing cloud-specific control logic
   * Node Controller: Checks with cloud provider if node has been deleted
   * Route Controller: Sets up routes in cloud infrastructure
   * Service Controller: Creates, updates, deletes cloud provider load balancers
   * Volume Controller: Creates, attaches, mounts volumes

### Node Components

1. **kubelet**: Agent running on each node that ensures containers in pods are running
2. **kube-proxy**: Network proxy running on each node that implements the Kubernetes Service concept
3. **Container Runtime**: Software responsible for running containers (Docker, containerd, CRI-O, etc.)

### Full Architecture

## Kubernetes Main Components

### API Server (kube-apiserver)

The API server is the frontend of the control plane that exposes the Kubernetes API. All internal and external requests are processed through the API server.

**Key Functions**:

* Provides REST API
* Authentication and authorization
* Request validation
* Communication with etcd
* Horizontally scalable

### etcd

etcd is a consistent and highly available key-value store that stores all cluster data.

**Key Features**:

* Distributed system
* Strong consistency
* High availability
* Secure data storage
* Watch feature for monitoring changes

### Scheduler (kube-scheduler)

The scheduler is a control plane component that selects nodes to run newly created pods.

**Scheduling Process**:

1. **Filtering**: Identify nodes that can run the pod
2. **Scoring**: Assign scores to suitable nodes
3. **Binding**: Assign pod to optimal node

**Considerations**:

* Resource requirements (CPU, memory)
* Hardware/software/policy constraints
* Affinity/anti-affinity specifications
* Data locality
* Workload interference

### Controller Manager (kube-controller-manager)

The controller manager is a control plane component that runs multiple controller processes.

**Main Controllers**:

* **Node Controller**: Monitor and respond to node state
* **Replication Controller**: Maintain pod replica count
* **Endpoints Controller**: Connect services and pods
* **Service Account & Token Controller**: Create default accounts and API tokens for namespaces
* **Job Controller**: Manage one-time tasks
* **CronJob Controller**: Manage scheduled tasks
* **DaemonSet Controller**: Ensure specific pods run on all nodes
* **StatefulSet Controller**: Manage stateful applications
* **PV Controller**: Manage persistent volumes

### Cloud Controller Manager (cloud-controller-manager)

The cloud controller manager is a control plane component containing cloud-specific control logic.

**Main Controllers**:

* **Node Controller**: Check node state through cloud provider API
* **Route Controller**: Set up routes in cloud environment
* **Service Controller**: Create, update, delete cloud load balancers
* **Volume Controller**: Create, attach, mount cloud storage volumes

### kubelet

kubelet is an agent running on each node that ensures containers in pods are running.

**Key Functions**:

* Run containers according to PodSpec
* Report container status
* Perform container health checks
* Manage container lifecycle
* Report node status

### kube-proxy

kube-proxy is a network proxy running on each node that implements the Kubernetes Service concept.

**Key Functions**:

* Maintain network rules for service IPs and ports
* Forward connections
* Implement load balancing

**Operating Modes**:

* **userspace mode**: Run proxy in user space (legacy)
* **iptables mode**: NAT implementation using Linux iptables (default)
* **IPVS mode**: Uses Linux kernel's IP Virtual Server (high performance)

## Kubernetes Basic Objects

Kubernetes objects are persistent entities that represent the state of the cluster. These objects describe running applications, available resources, policies, etc. in the cluster.

### Pod

A Pod is the smallest deployable unit in Kubernetes, representing a group of one or more containers. Containers in a pod share storage and network and are always scheduled together on the same node.

**Key Features**:

* Has unique IP address
* Shared network namespace (same IP and port space)
* Shared IPC namespace
* Shared hostname
* Localhost communication between containers possible

**Pod Example**:

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

Namespaces provide a way to isolate resource groups within a single cluster. This is useful when multiple teams or projects share the same cluster.

**Default Namespaces**:

* **default**: Default namespace
* **kube-system**: Namespace for objects created by the Kubernetes system
* **kube-public**: Namespace for objects readable by all users
* **kube-node-lease**: Namespace for node heartbeats

**Namespace Example**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Labels and Selectors

Labels are key-value pairs attached to objects, used to identify and select objects. Selectors provide a way to filter objects based on labels.

**Labels Example**:

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**Selector Types**:

* **Equality-based**: `=`, `!=`
* **Set-based**: `in`, `notin`, `exists`

**Selector Example**:

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### Annotations

Annotations are key-value pairs that store non-identifying metadata about objects. Annotations are useful for storing information used by tools or libraries.

**Annotations Example**:

```yaml
metadata:
  annotations:
    kubernetes.io/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Node

A node is a worker machine in a Kubernetes cluster that runs pods. A node can be a physical or virtual machine.

**Node Status**:

* **Addresses**: Hostname, Internal IP, External IP
* **Conditions**: Ready, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable
* **Capacity**: CPU, Memory, Maximum pods
* **Info**: Kernel version, Container runtime version, kubelet version

**Node Example**:

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

Workload resources are objects used to manage and run pods. These resources manage the creation, scaling, updates, and termination of pods.

### ReplicaSet

A ReplicaSet ensures that a specified number of pod replicas are always running. If pods fail or are deleted, the ReplicaSet automatically creates replacement pods.

**Key Functions**:

* Maintain specified number of pod replicas
* Define pod template
* Identify pods through selectors

**ReplicaSet Example**:

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

A Deployment abstracts ReplicaSets one level further, providing declarative updates for applications. Deployments provide features like rolling updates, rollbacks, and scaling.

**Key Functions**:

* Declarative application updates
* Rolling updates and rollbacks
* Deployment history management
* Scaling

**Deployment Example**:

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

A StatefulSet is a workload resource for applications that require state maintenance. It assigns unique identifiers to each pod and provides stable network identifiers and persistent storage.

**Key Functions**:

* Stable and unique network identifiers
* Stable and persistent storage
* Sequential deployment and scaling
* Sequential updates

**StatefulSet Example**:

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

A DaemonSet ensures that a copy of a pod runs on all nodes (or specific nodes). When nodes are added to the cluster, pods are automatically added, and when nodes are removed, pods are also removed.

**Key Use Cases**:

* Log collectors (Fluentd, Logstash)
* Monitoring agents (Prometheus Node Exporter)
* Network plugins (Calico, Cilium)
* Storage daemons (Ceph)

**DaemonSet Example**:

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

A Job creates one or more pods and continues execution until a specified number of pods successfully terminate. Suitable for batch processing tasks.

**Key Functions**:

* One-time task execution
* Parallel task execution
* Guarantee task completion
* Retry on failure

**Job Example**:

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

A CronJob runs Jobs periodically according to a specified schedule. Works similarly to Linux cron jobs.

**Key Functions**:

* Task execution according to schedule
* Cron expression support
* Concurrency policy settings
* History limits

**CronJob Example**:

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

The Kubernetes networking model is based on the premise that all pods have unique IP addresses and can communicate with each other without special configuration. Services provide stable endpoints for sets of pods.

### Service

A Service provides a single endpoint and load balancing for a set of pods. Since pods are dynamically created and deleted, services provide stable network addresses despite these changes.

**Service Types**:

* **ClusterIP**: Service accessible only within the cluster (default)
* **NodePort**: Accessible externally through each node's IP and specific port
* **LoadBalancer**: Accessible externally using cloud provider's load balancer
* **ExternalName**: Creates CNAME record for external service

**Service Example**:

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

**NodePort Service Example**:

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

**LoadBalancer Service Example**:

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

An Ingress is an API object that manages HTTP and HTTPS routing from outside the cluster to internal services. Ingress provides load balancing, SSL termination, name-based virtual hosting, etc.

**Ingress Controllers**:

* **NGINX Ingress Controller**: NGINX-based ingress controller
* **AWS ALB Ingress Controller**: AWS Application Load Balancer-based ingress controller
* **Traefik**: Cloud-native edge router
* **Istio Ingress**: Service mesh-based ingress

**Ingress Example**:

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

NetworkPolicy provides a way to control communication between pods. By default, all pods can communicate with each other, but you can restrict this using network policies.&#x20;

**Key Functions**:

* Control communication between pods
* Control communication between namespaces
* Control ingress (incoming) and egress (outgoing) traffic
* Port and protocol-based filtering

**NetworkPolicy Example**:

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

Kubernetes provides a DNS service within the cluster to support service discovery. CoreDNS is used by default.

**DNS Name Format**:

* **Service**: `<service-name>.<namespace>.svc.cluster.local`
* **Pod**: `<pod-IP-address-dots-replaced>.pod.cluster.local`

**DNS Configuration Example**:

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

A service mesh is an infrastructure layer that manages communication between microservices. Service meshes provide traffic management, security, and observability.

**Major Service Meshes**:

* **Istio**: Most widely used service mesh
* **Linkerd**: Lightweight service mesh
* **AWS App Mesh**: AWS managed service mesh

**Istio VirtualService Example**:

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

Kubernetes provides various storage options for containerized applications. It provides ways to persist data even when pods are restarted or rescheduled.

### Volume

A volume is a directory that can be mounted to containers in a pod, persisting data for the pod's lifecycle. Volumes are also used to share data between containers in a pod.

**Main Volume Types**:

* **emptyDir**: Starts as empty directory, deleted when pod is deleted
* **hostPath**: Mount from host node's file system to pod
* **configMap**: Mount ConfigMap as volume
* **secret**: Mount Secret as volume
* **persistentVolumeClaim**: Mount persistent volume to pod

**emptyDir Volume Example**:

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

A PersistentVolume is an API object representing a storage resource in the cluster. It exists independently of pods and is provisioned by cluster administrators.

**Access Modes**:

* **ReadWriteOnce (RWO)**: Can be mounted read/write by a single node
* **ReadOnlyMany (ROX)**: Can be mounted read-only by multiple nodes
* **ReadWriteMany (RWX)**: Can be mounted read/write by multiple nodes

**PersistentVolume Example**:

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

A PersistentVolumeClaim is an API object representing a user's storage request. Pods access PVs through PVCs.

**PersistentVolumeClaim Example**:

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

**Pod using PVC Example**:

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

A StorageClass describes "classes" of storage provided by administrators. Different service quality levels, backup policies, or arbitrary policies determined by cluster administrators can be provided.

**StorageClass Example**:

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

Dynamic provisioning is a feature that automatically creates PVs when PVCs are requested using storage classes.

**Dynamic Provisioning Example**:

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

CSI provides a standard interface between Kubernetes and storage systems. This allows storage providers to develop their own storage drivers without modifying Kubernetes code.

**Major CSI Drivers**:

* **AWS EBS CSI Driver**: Amazon EBS volume management
* **AWS EFS CSI Driver**: Amazon EFS file system management
* **AWS FSx for Lustre CSI Driver**: FSx for Lustre file system management
* **GCE PD CSI Driver**: Google Compute Engine persistent disk management
* **Azure Disk CSI Driver**: Azure disk management

**CSI Driver Deployment Example**:

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

Kubernetes provides various objects and mechanisms for managing application configuration and security.

### ConfigMap

A ConfigMap is an API object that stores configuration data as key-value pairs. Pods can use ConfigMap data as environment variables, command-line arguments, or configuration files.

**ConfigMap Example**:

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

**Pod using ConfigMap Example**:

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

A Secret is an API object that stores sensitive information such as passwords, tokens, and keys. Similar to ConfigMap but designed for sensitive data.

**Secret Types**:

* **Opaque**: Arbitrary user-defined data (default)
* **kubernetes.io/service-account-token**: Service account token
* **kubernetes.io/dockercfg**: Serialized \~/.dockercfg file
* **kubernetes.io/dockerconfigjson**: Serialized \~/.docker/config.json file
* **kubernetes.io/basic-auth**: Credentials for basic authentication
* **kubernetes.io/ssh-auth**: Credentials for SSH authentication
* **kubernetes.io/tls**: Data for TLS client or server

**Secret Example**:

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

**Pod using Secret Example**:

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

RBAC is a mechanism for controlling access to the Kubernetes API. It grants specific permissions to users or service accounts using Roles and RoleBindings.

**Main RBAC Objects**:

* **Role**: Defines a set of permissions within a namespace
* **ClusterRole**: Defines a set of permissions cluster-wide
* **RoleBinding**: Binds a role to users, groups, or service accounts
* **ClusterRoleBinding**: Binds a cluster role to users, groups, or service accounts

**Role Example**:

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

**RoleBinding Example**:

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

A ServiceAccount provides an identity for processes running inside a pod. Pods use service accounts to communicate with the Kubernetes API.

**ServiceAccount Example**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
```

**Pod using ServiceAccount Example**:

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

NetworkPolicy provides a way to control communication between pods. By default, all pods can communicate with each other, but you can restrict this using network policies.

**NetworkPolicy Example**:

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

PodSecurityPolicy defines security-related conditions for pod creation and updates. This has been deprecated since Kubernetes 1.21 and replaced by Pod Security Standards.

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

Pod Security Standards provide three policy levels that define security requirements for pods:

1. **Privileged**: No restrictions, all features allowed
2. **Baseline**: Prevent known privilege escalations
3. **Restricted**: Strong restrictions applying best practices

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

Amazon EKS (Elastic Kubernetes Service) is a managed Kubernetes service provided by AWS. EKS provides all the basic features of Kubernetes while adding AWS service integration and management convenience.

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

1. **AWS IAM Integration**: Integration of Kubernetes RBAC and AWS IAM
2. **AWS Load Balancer Controller**: Integration of ALB and NLB with Kubernetes services and ingress
3. **EKS Managed Node Groups**: Node lifecycle management automation
4. **Fargate Profiles**: Serverless Kubernetes pod execution
5. **VPC CNI Plugin**: Integration with AWS VPC networking
6. **CloudWatch Container Insights**: Container monitoring and logging
7. **AWS App Mesh**: Service mesh integration
8. **AWS Distro for OpenTelemetry**: Distributed tracing and monitoring
9. **EKS Console and CLI**: Management interfaces
10. **EKS Blueprints**: Best practices-based cluster configuration

### EKS-Specific Components

1. **EKS Control Plane**: High availability across multiple availability zones
2. **EKS Node AMI**: Amazon Linux or Ubuntu AMI optimized for Kubernetes
3. **EKS Managed Node Groups**: Auto scaling and update support
4. **EKS Fargate**: Serverless container execution environment
5. **EKS Connector**: Connect external Kubernetes clusters to AWS console
6. **EKS Anywhere**: Run EKS-compatible clusters in on-premises environments
7. **EKS Distro**: AWS-managed Kubernetes distribution

### AWS Service Integration

EKS integrates with the following AWS services:

1. **Amazon VPC**: Networking infrastructure
2. **AWS IAM**: Authentication and authorization
3. **Amazon ECR**: Container image repository
4. **AWS Load Balancer**: Application traffic distribution
5. **Amazon EBS/EFS/FSx**: Persistent storage
6. **AWS CloudWatch**: Monitoring and logging
7. **AWS CloudTrail**: Audit and compliance
8. **AWS KMS**: Encryption key management
9. **AWS WAF**: Web application firewall
10. **AWS Shield**: DDoS protection
11. **AWS X-Ray**: Distributed tracing
12. **AWS App Mesh**: Service mesh
13. **AWS SageMaker**: Machine learning workloads
14. **AWS Bedrock**: Generative AI workloads

## Getting Started with Kubernetes

There are several ways to get started with Kubernetes. Here we briefly introduce how to start Kubernetes in a local development environment and on AWS EKS.

### Local Development Environment

#### Minikube

Minikube is a tool that runs a single-node Kubernetes cluster on your local machine.

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

Kind is a tool that runs Kubernetes clusters locally using Docker containers as nodes.

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

Docker Desktop provides a feature to easily run Kubernetes on Mac and Windows.

**Setup**:

1. Install Docker Desktop
2. Settings > Kubernetes > Check "Enable Kubernetes"
3. Click "Apply & Restart"

### AWS EKS

#### Creating EKS Cluster with eksctl

eksctl is a simple CLI tool for creating and managing EKS clusters.

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

You can also create EKS clusters through the AWS Management Console.

**Steps**:

1. Log in to AWS Management Console
2. Navigate to EKS service
3. Click "Create cluster"
4. Configure cluster name, IAM role, VPC and subnets
5. Configure security groups
6. Configure logging options
7. Create cluster
8. Add node groups

### kubectl Installation and Configuration

kubectl is a command-line tool for interacting with Kubernetes clusters.

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

Kubernetes Dashboard provides a web-based UI for managing clusters.

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

The dashboard can be accessed at http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/.

## Conclusion

Kubernetes is a powerful platform that automates the deployment, scaling, and management of containerized applications. Summary of key content covered in this document:

### Core Architecture

* **Control Plane**: Brain of the cluster (API Server, etcd, Scheduler, Controller Manager)
* **Worker Nodes**: Nodes that run actual applications (kubelet, kube-proxy, Container Runtime)
* **Declarative Configuration**: Define desired state and Kubernetes matches current state to desired state

### Main Objects and Resources

* **Basic Objects**: Pod, Service, Volume, Namespace
* **Workload Resources**: Deployment, StatefulSet, DaemonSet, Job, CronJob
* **Configuration and Security**: ConfigMap, Secret, RBAC, ServiceAccount
* **Networking**: Service, Ingress, NetworkPolicy
* **Storage**: PersistentVolume, PersistentVolumeClaim, StorageClass

### Recommended Learning Path

**Step 1: Build Local Environment**

* Create local cluster with minikube or kind
* Learn kubectl commands
* Practice with basic objects (Pod, Deployment, Service)

**Step 2: Master Core Concepts**

* Understand and practice workload resources
* Configuration management with ConfigMap and Secret
* Configure networking with Service and Ingress
* Manage storage with PV and PVC

**Step 3: Learn Advanced Features**

* RBAC and security policies
* Auto scaling (HPA, VPA, Cluster Autoscaler)
* Monitoring and logging (Prometheus, Grafana)
* Service mesh (Istio, Linkerd)

**Step 4: Production Operations**

* Use Amazon EKS or other managed Kubernetes
* CI/CD pipeline integration
* Disaster recovery and backup strategies
* Cost optimization and resource management

### Next Steps

* **EKS Deep Dive**: EKS-specific features (Fargate, VPC CNI, ALB Controller)
* **Advanced Networking**: CNI plugins (Calico, Cilium)
* **Observability**: Metrics, logs, tracing
* **GitOps**: ArgoCD, Flux
* **Security Hardening**: Pod Security Standards, Network Policies, OPA/Gatekeeper

Kubernetes continues to evolve and has become a core element of cloud-native application development and operations. We hope this document helps you start your Kubernetes journey.

### Additional Learning Resources

* **Official Documentation**: [Kubernetes Official Documentation](https://kubernetes.io/docs/) provides the most accurate and up-to-date information
* **Interactive Tutorials**: Hands-on practice available at [Kubernetes Tutorials](https://kubernetes.io/docs/tutorials/)
* **Community**: [Kubernetes Slack](https://slack.k8s.io/), [Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **Certifications**: CKA (Certified Kubernetes Administrator), CKAD (Certified Kubernetes Application Developer)
* **Korean Community**: Kubernetes Korea User Group, AWS Korea User Group

## Quiz

To test what you learned in this chapter, take the [Introduction to Kubernetes Quiz](../quizzes/basics/04-kubernetes-introduction-quiz.md).

## References

* [Kubernetes Official Documentation](https://kubernetes.io/docs/)
* [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
* [Kubernetes GitHub Repository](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
