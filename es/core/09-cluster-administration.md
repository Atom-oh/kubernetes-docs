# Kubernetes Cluster Administration

> **Versiones compatibles**: Kubernetes 1.34 (Publicado 2025-11-24)
> **Última actualización**: February 23, 2026

La administración de clústeres de Kubernetes es una tarea importante que incluye la configuración, el mantenimiento, la monitorización, la resolución de problemas y las actualizaciones del clúster. En este capítulo, exploraremos diversos aspectos de la administración de clústeres de Kubernetes y las mejores prácticas para la gestión de clústeres en Amazon EKS.

## Core Concepts

- **Gestión del ciclo de vida del clúster**: Todo el proceso desde la creación del clúster hasta su retirada
- **Gestión del control plane**: Gestión de componentes principales como el API server, scheduler y controller manager
- **Gestión de Node**: Adición, eliminación y mantenimiento de worker nodes
- **Asignación de recursos**: Configuración de la asignación de recursos y límites para CPU, memoria, almacenamiento, etc.
- **Estrategia de actualización**: Estrategias de actualización del clúster y las aplicaciones para minimizar el tiempo de inactividad

## Table of Contents
1. [Cluster Administration Overview](#cluster-administration-overview)
2. [Cluster Component Management](#cluster-component-management)
3. [Resource Management](#resource-management)
4. [Cluster Networking](#cluster-networking)
5. [Authentication and Authorization Management](#authentication-and-authorization-management)
6. [Cluster Upgrades](#cluster-upgrades)
7. [Backup and Recovery](#backup-and-recovery)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Troubleshooting](#troubleshooting)
10. [Amazon EKS Cluster Administration](#amazon-eks-cluster-administration)
11. [Cluster Administration Best Practices](#cluster-administration-best-practices)
12. [Conclusion](#conclusion)

## Environment Setup

Las siguientes herramientas son necesarias para la administración del clúster:

```bash
# Install kubectl (Linux)
curl -LO "https://dl.k8s.io/release/v1.33.3/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Install kubeadm (for cluster creation and management)
sudo apt-get update && sudo apt-get install -y kubeadm=1.33.3-00

# Install Helm (for package management)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install k9s (cluster management UI)
curl -sS https://webinstall.dev/k9s | bash
```

## Cluster Administration Overview

La administración de clústeres de Kubernetes es el proceso de gestionar todo el ciclo de vida de un clúster. Esto incluye las siguientes áreas principales:

1. **Configuración y preparación del clúster**: Creación del clúster, adición de Node, configuración de red, configuración de almacenamiento, etc.
2. **Gestión de operaciones**: Monitorización de recursos, optimización del rendimiento, planificación de capacidad, resolución de problemas
3. **Gestión de seguridad**: Autenticación, autorización, network policies, security contexts, etc.
4. **Actualizaciones y parches**: Actualizaciones de versión del clúster, aplicación de parches de seguridad
5. **Backup y recuperación**: Backup de datos del clúster, planificación de recuperación ante desastres

El siguiente diagrama muestra las áreas principales de la administración de clústeres de Kubernetes y las herramientas relacionadas:

## Cluster Component Management

Un clúster de Kubernetes consta de componentes del control plane y componentes de Node. Gestionar cada componente es fundamental para la estabilidad y el rendimiento del clúster.

### Control Plane Component Management

```mermaid
graph TD
    A[Control Plane] --> B[API Server]
    A --> C[etcd]
    A --> D[Scheduler]
    A --> E[Controller Manager]
    A --> F[Cloud Controller Manager]

    B --> G[Authentication and Authorization]
    C --> H[Data Backup]
    D --> I[Scheduling Policies]
    E --> J[Controller State Monitoring]
    F --> K[Cloud Resource Management]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef operation fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E,F k8sComponent;
    class G,H,I,J,K operation;
```

#### API Server Management

El API server es un componente central del control plane que expone la API de Kubernetes.

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### etcd Management

etcd es un almacén clave-valor distribuido que guarda todos los datos del clúster para Kubernetes.

```bash
# etcd backup
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d).db

# Check etcd status
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  endpoint health
```

### Node Management

Los Node son máquinas de trabajo que ejecutan aplicaciones en contenedores.

```bash
# List nodes
kubectl get nodes

# Check node detailed information
kubectl describe node <node-name>

# Add node label
kubectl label node <node-name> environment=production

# Set node to maintenance mode
kubectl drain <node-name> --ignore-daemonsets

# Return node after maintenance
kubectl uncordon <node-name>
```

### Component Status Monitoring

```bash
# Check control plane component status
kubectl get componentstatuses

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

```mermaid
flowchart TD
    Admin[Cluster Administrator] --> Setup[Cluster Setup and Configuration]
    Admin --> Operations[Operations Management]
    Admin --> Security[Security Management]
    Admin --> Upgrade[Upgrades and Patches]
    Admin --> Backup[Backup and Recovery]

    Setup --> |Tools| SetupTools[kubeadm, kops, eksctl]
    Operations --> |Tools| OpsTools[kubectl, Prometheus, Grafana]
    Security --> |Tools| SecTools[RBAC, NetworkPolicy, PodSecurityPolicy]
    Upgrade --> |Tools| UpgradeTools[kubeadm upgrade, EKS update]
    Backup --> |Tools| BackupTools[etcd snapshot, Velero]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Admin userApp;
    class Setup,Operations,Security,Upgrade,Backup k8sComponent;
    class SetupTools,OpsTools,SecTools,UpgradeTools,BackupTools default;
```

### Cluster Administration Tools

Existen diversas herramientas disponibles para la administración de clústeres de Kubernetes:

1. **kubectl**: Herramienta de línea de comandos para interactuar con clústeres de Kubernetes
2. **kubeadm**: Herramienta para crear y gestionar clústeres de Kubernetes
3. **kops**: Herramienta para crear, actualizar y gestionar clústeres de Kubernetes
4. **eksctl**: Herramienta para crear y gestionar clústeres de Amazon EKS
5. **Helm**: Gestor de paquetes de aplicaciones de Kubernetes
6. **Kubernetes Dashboard**: Interfaz de usuario web para Kubernetes
7. **Prometheus & Grafana**: Herramientas de monitorización y alertas
8. **Fluentd & Elasticsearch**: Herramientas de logging

## Cluster Component Management

Un clúster de Kubernetes consta de múltiples componentes, y gestionarlos eficazmente es importante.

### Control Plane Components

Los componentes del control plane gestionan el estado general del clúster:

1. **kube-apiserver**: Componente que expone la API de Kubernetes
2. **etcd**: Almacén clave-valor que guarda los datos del clúster
3. **kube-scheduler**: Componente que programa Pods en Nodes
4. **kube-controller-manager**: Componente que ejecuta controllers
5. **cloud-controller-manager**: Componente que interactúa con proveedores cloud

El siguiente diagrama muestra los componentes del control plane de Kubernetes y sus interacciones:

```mermaid
flowchart TD
    API[kube-apiserver] <--> ETCD[(etcd)]
    API <--> SCH[kube-scheduler]
    API <--> CM[kube-controller-manager]
    API <--> CCM[cloud-controller-manager]
    API <--> Kubelet[kubelet]

    subgraph "Control Plane"
        API
        ETCD
        SCH
        CM
        CCM
    end

    subgraph "Worker Node"
        Kubelet
        Proxy[kube-proxy]
        CRI[Container Runtime]
    end

    Kubelet --> CRI
    Kubelet --> Proxy

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class API,SCH,CM,CCM,Kubelet,Proxy,CRI k8sComponent;
    class ETCD dataStore;
```

#### Control Plane Component Monitoring

Es importante monitorizar el estado de los componentes del control plane:

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Control Plane Component Configuration

Cómo gestionar la configuración de los componentes del control plane:

```yaml
# kube-apiserver configuration example
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - command:
    - kube-apiserver
    - --advertise-address=192.168.1.10
    - --allow-privileged=true
    - --authorization-mode=Node,RBAC
    - --client-ca-file=/etc/kubernetes/pki/ca.crt
    - --enable-admission-plugins=NodeRestriction
    - --enable-bootstrap-token-auth=true
    - --etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
    - --etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client.crt
    - --etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client.key
    - --etcd-servers=https://127.0.0.1:2379
    - --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt
    - --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key
    - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
    - --secure-port=6443
    - --service-account-key-file=/etc/kubernetes/pki/sa.pub
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: k8s.gcr.io/kube-apiserver:v1.21.0
    name: kube-apiserver
```

### Node Components

Los componentes de Node se ejecutan en cada Node y gestionan Pods:

1. **kubelet**: Agente que se ejecuta en cada Node y garantiza que Pods y contenedores estén ejecutándose
2. **kube-proxy**: Mantiene reglas de red y gestiona el reenvío de conexiones
3. **Container Runtime**: Software que ejecuta contenedores (Docker, containerd, CRI-O, etc.)

#### Node Management

Comandos clave para la gestión de Node:

```bash
# List nodes
kubectl get nodes

# Check node detailed information
kubectl describe node <node-name>

# Add node label
kubectl label node <node-name> key=value

# Add node taint
kubectl taint node <node-name> key=value:NoSchedule

# Set node to maintenance mode
kubectl cordon <node-name>

# Drain node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

#### Node Troubleshooting

Comandos para la resolución de problemas de Node:

```bash
# Check node status
kubectl describe node <node-name> | grep Conditions -A 10

# Check node resource usage
kubectl top node <node-name>

# Check kubelet logs
journalctl -u kubelet

# Check container runtime status
systemctl status docker  # When using Docker
systemctl status containerd  # When using containerd
```

## Resource Management

Gestionar eficazmente los recursos en un clúster de Kubernetes es importante para mantener la estabilidad y el rendimiento del clúster.

### Resource Quotas

Las resource quotas limitan el uso de recursos por namespace:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-resources
  namespace: dev
spec:
  hard:
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
    pods: "10"
```

En el ejemplo anterior, el namespace `dev` puede tener un máximo de 10 Pods, requests de 1 CPU y 1Gi de memoria, y limits de 2 CPU y 2Gi de memoria.

### Limit Ranges

Los limit ranges establecen valores predeterminados y límites para recursos individuales dentro de un namespace:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: limit-range
  namespace: dev
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 200m
      memory: 256Mi
    max:
      cpu: 1
      memory: 1Gi
    min:
      cpu: 100m
      memory: 128Mi
    type: Container
```

En el ejemplo anterior, todos los contenedores del namespace `dev` tienen limits predeterminados de 500m de CPU y 512Mi de memoria, requests predeterminados de 200m de CPU y 256Mi de memoria, un máximo de 1 CPU y 1Gi de memoria, y un mínimo de 100m de CPU y 128Mi de memoria.

### Horizontal Pod Autoscaler (HPA)

HPA ajusta automáticamente el número de Pods según el uso de CPU o métricas personalizadas:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

En el ejemplo anterior, el Deployment `frontend` escala hacia fuera automáticamente cuando la utilización de CPU supera el 80% y escala hacia dentro cuando está por debajo del 80%. Mantiene un mínimo de 2 y un máximo de 10 réplicas.

### Vertical Pod Autoscaler (VPA)

VPA ajusta automáticamente las requests de CPU y memoria de los Pods:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Auto"
```

En el ejemplo anterior, los Pods del Deployment `frontend` tienen sus requests de CPU y memoria ajustadas automáticamente según el uso real de recursos.
## Cluster Networking

La red del clúster de Kubernetes gestiona la comunicación entre Pods, Services y Nodes.

### Cluster Network Model

Requisitos básicos del modelo de red de Kubernetes:

1. Todos los Pods pueden comunicarse con todos los demás Pods sin NAT
2. Los agentes de Node (kubelet) pueden comunicarse con todos los Pods en ese Node
3. Los Pods que se ejecutan en modo NAT pueden comunicarse con el exterior

El siguiente diagrama muestra los componentes de red de Kubernetes y los flujos de comunicación:

```mermaid
flowchart LR
    Client[Client] --> Ingress[Ingress]
    Ingress --> SVC[Service]
    SVC --> Pod1[Pod 1]
    SVC --> Pod2[Pod 2]

    subgraph "Cluster Internal"
        Ingress
        SVC
        subgraph "Node 1"
            Pod1
        end
        subgraph "Node 2"
            Pod2
        end
    end

    Pod1 <--> Pod2
    Pod1 --> ExtSvc[External Service]
    Pod2 --> ExtSvc

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Ingress,SVC k8sComponent;
    class Pod1,Pod2 userApp;
    class Client,ExtSvc default;
```

### CNI (Container Network Interface) Plugins

Kubernetes implementa la red mediante plugins CNI. Plugins CNI comunes:

1. **Calico**: CNI con funciones mejoradas de network policy y seguridad
2. **Flannel**: Proporciona una red overlay sencilla
3. **Cilium**: Solución de red y seguridad basada en eBPF
4. **AWS VPC CNI**: CNI integrado con AWS VPC
5. **Weave Net**: Solución de red de contenedores multi-host

#### CNI Plugin Installation and Configuration

Ejemplo de instalación de plugin CNI (Calico):

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Service Networking

Los Services de Kubernetes proporcionan endpoints estables para conjuntos de Pods:

1. **ClusterIP**: Service accesible solo dentro del clúster
2. **NodePort**: Service accesible mediante un puerto específico en todos los Nodes
3. **LoadBalancer**: Service accesible mediante un load balancer externo
4. **ExternalName**: Proporciona un registro CNAME para Services externos

#### Service CIDR Configuration

Service CIDR define el rango de direcciones IP de Service:

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS Management

CoreDNS proporciona servicios DNS para Kubernetes:

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

Ejemplo de configuración de CoreDNS:

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
        health {
           lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf
        cache 30
        loop
        reload
        loadbalance
    }
```

### Network Policies

Las network policies controlan la comunicación entre Pods:

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

En el ejemplo anterior, los Pods con la etiqueta `role=db` solo permiten tráfico entrante TCP en el puerto 3306 desde Pods con la etiqueta `role=frontend` y tráfico saliente TCP en el puerto 9090 hacia Pods con la etiqueta `role=monitoring`.

## Authentication and Authorization Management

La gestión de autenticación y autorización de Kubernetes es un elemento central de la seguridad del clúster.

El siguiente diagrama muestra el flujo de autenticación y autorización de Kubernetes:

```mermaid
flowchart TD
    User[User/Service Account] --> Auth[Authentication]
    Auth --> Authz[Authorization]
    Authz --> Admit[Admission Control]
    Admit --> API[API Server]

    subgraph "Authentication Methods"
        Cert[X.509 Certificates]
        Token[Service Account Tokens]
        OIDC[OpenID Connect]
        Webhook[Webhook Token Auth]
    end

    subgraph "Authorization Modes"
        RBAC[RBAC]
        ABAC[ABAC]
        Node[Node]
        WebhookAuthz[Webhook]
    end

    Auth --> Cert
    Auth --> Token
    Auth --> OIDC
    Auth --> Webhook

    Authz --> RBAC
    Authz --> ABAC
    Authz --> Node
    Authz --> WebhookAuthz

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class Auth,Authz,Admit,API k8sComponent;
    class User userApp;
    class Cert,Token,OIDC,Webhook,RBAC,ABAC,Node,WebhookAuthz default;
```

### Authentication

Kubernetes admite diversos métodos de autenticación:

1. **X.509 Certificates**: Autenticación mediante certificados de cliente
2. **Service Account Tokens**: Tokens JWT asociados a service accounts
3. **OpenID Connect (OIDC)**: Autenticación mediante proveedores de identidad externos
4. **Webhook Token Authentication**: Verificación de tokens mediante servicios externos
5. **Authentication Proxy**: Procesamiento de solicitudes mediante un proxy de autenticación

#### X.509 Certificate Management

Creación y gestión de certificados X.509:

```bash
# Create Certificate Signing Request (CSR)
openssl req -new -key user.key -out user.csr -subj "/CN=user/O=group"

# Submit CSR to Kubernetes
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: user-csr
spec:
  request: $(cat user.csr | base64 | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  usages:
  - client auth
EOF

# Approve CSR
kubectl certificate approve user-csr

# Get certificate
kubectl get csr user-csr -o jsonpath='{.status.certificate}' | base64 --decode > user.crt
```

#### OIDC Authentication Configuration

Ejemplo de configuración de autenticación OIDC:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Authorization

Kubernetes admite diversos modos de autorización:

1. **RBAC (Role-Based Access Control)**: Control de acceso basado en roles
2. **ABAC (Attribute-Based Access Control)**: Control de acceso basado en atributos
3. **Node**: Autorización de Node
4. **Webhook**: Autorización mediante servicios externos

#### RBAC Configuration

RBAC es el mecanismo de autorización más común:

```yaml
# Role example
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]

# RoleBinding example
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

En el ejemplo anterior, `user` tiene permiso para ver Pods en el namespace `default`.

#### ClusterRole and ClusterRoleBinding

Gestiona permisos para recursos de todo el clúster:

```yaml
# ClusterRole example
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: node-reader
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get", "watch", "list"]

# ClusterRoleBinding example
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-nodes
subjects:
- kind: User
  name: user
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: node-reader
  apiGroup: rbac.authorization.k8s.io
```

En el ejemplo anterior, `user` tiene permiso para ver todos los Nodes del clúster.

### Service Account Management

Los service accounts son utilizados por los Pods para comunicarse con el API server:

```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# Grant permissions to service account
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-service-account-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: my-service-account
  namespace: default
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io

# Use service account in pod
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

### Security Context

Security context define permisos y control de acceso para Pods y contenedores:

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
  - name: security-context-container
    image: nginx
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

En el ejemplo anterior, el Pod se ejecuta con UID 1000 y GID 3000, y el contenedor no puede escalar privilegios, tiene todas las capabilities de Linux eliminadas y tiene el filesystem root montado como solo lectura.

## Cluster Upgrades

Las actualizaciones de clústeres de Kubernetes son necesarias para aplicar nuevas funciones, mejoras de rendimiento y parches de seguridad.

El siguiente diagrama muestra el proceso de actualización de un clúster de Kubernetes:

```mermaid
flowchart TD
    Start[Upgrade Planning] --> Plan[Check Version Compatibility]
    Plan --> Backup[etcd Backup]
    Backup --> CP1[Upgrade First Control Plane Node]
    CP1 --> CPTest[Test Control Plane Functions]
    CPTest --> CP2[Upgrade Additional Control Plane Nodes]
    CP2 --> Worker[Upgrade Worker Nodes]
    Worker --> Validate[Cluster Validation]
    Validate --> End[Upgrade Complete]

    Validate -- Problem Occurs --> Rollback[Rollback]
    Rollback --> RestoreBackup[Restore from Backup]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef alerting fill:#EB6E85,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class CP1,CP2,Worker,Validate k8sComponent;
    class Backup,RestoreBackup dataStore;
    class Rollback alerting;
    class Start,Plan,CPTest,End default;
```

### Upgrade Planning

Consideraciones al planificar actualizaciones del clúster:

1. **Compatibilidad de versiones**: Comprobar la compatibilidad entre versiones de Kubernetes
2. **Ruta de actualización**: Comprobar las rutas de actualización compatibles
3. **Tiempo de inactividad**: Planificar el tiempo de inactividad esperado durante la actualización
4. **Plan de rollback**: Desarrollar un plan de rollback en caso de problemas
5. **Impacto en aplicaciones**: Evaluar el impacto de las actualizaciones en las aplicaciones

### Control Plane Upgrade

Actualización del control plane usando kubeadm:

```bash
# Check upgrade plan
kubeadm upgrade plan

# Upgrade first control plane node
ssh control-plane-1
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade apply v1.22.0

# Upgrade additional control plane nodes
ssh control-plane-2
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

### Worker Node Upgrade

Proceso de actualización de worker node:

```bash
# Drain node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# SSH to node
ssh <node-name>

# Upgrade kubeadm
sudo apt-get update
sudo apt-get install -y kubeadm=1.22.0-00
sudo kubeadm upgrade node

# Upgrade kubelet and kubectl
sudo apt-get install -y kubelet=1.22.0-00 kubectl=1.22.0-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Uncordon node
kubectl uncordon <node-name>
```

### Upgrade Verification

Verificar el estado del clúster después de la actualización:

```bash
# Check node versions
kubectl get nodes

# Check component status
kubectl get componentstatuses

# Check pod status
kubectl get pods --all-namespaces

# Test cluster functionality
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## Backup and Recovery

El backup y la recuperación de clústeres de Kubernetes son una parte importante de la planificación de recuperación ante desastres.

El siguiente diagrama muestra el proceso de backup y recuperación de un clúster de Kubernetes:

```mermaid
flowchart TD
    subgraph "Backup Process"
        Schedule[Set Backup Schedule] --> ETCDBackup[Create etcd Snapshot]
        Schedule --> ResourceBackup[Backup Resource YAMLs]
        ETCDBackup --> Store[Backup Storage]
        ResourceBackup --> Store
    end

    subgraph "Recovery Process"
        Disaster[Disaster Occurs] --> RestoreETCD[Restore etcd]
        RestoreETCD --> RestartServices[Restart Kubernetes Services]
        RestartServices --> ValidateCluster[Validate Cluster]
        ValidateCluster --> RestoreResources[Restore Resources]
    end

    Store -.-> RestoreETCD
    Store -.-> RestoreResources

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef alerting fill:#EB6E85,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class ETCDBackup,ResourceBackup,RestoreETCD,RestartServices,ValidateCluster,RestoreResources k8sComponent;
    class Store dataStore;
    class Disaster alerting;
    class Schedule default;
```

### etcd Backup

etcd guarda toda la información de estado del clúster de Kubernetes, por lo que los backups regulares son importantes:

```bash
# Create etcd snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# Check snapshot status
ETCDCTL_API=3 etcdctl --write-out=table snapshot status /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### etcd Recovery

Restaurar desde snapshot de etcd:

```bash
# Stop all Kubernetes services
sudo systemctl stop kubelet kube-apiserver kube-controller-manager kube-scheduler

# Backup etcd data directory
sudo mv /var/lib/etcd /var/lib/etcd.bak

# Restore from snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  --data-dir=/var/lib/etcd \
  --initial-cluster=master-1=https://192.168.1.10:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://192.168.1.10:2380 \
  snapshot restore /backup/etcd-snapshot-2023-01-01-12-00-00.db

# Set permissions
sudo chown -R etcd:etcd /var/lib/etcd

# Restart Kubernetes services
sudo systemctl start etcd
sudo systemctl start kubelet kube-apiserver kube-controller-manager kube-scheduler
```

### Resource Backup

Realizar backup de recursos de Kubernetes como archivos YAML:

```bash
# Backup all resources in all namespaces
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --namespaced=true -o name); do
    kubectl get -n $ns $resource -o yaml > /backup/resources/$ns/$resource.yaml
  done
done

# Backup cluster-scoped resources
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --namespaced=false -o name); do
  kubectl get $resource -o yaml > /backup/resources/cluster-scoped/$resource.yaml
done
```

### Backup Automation

Automatizar tareas de backup con CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 0 * * *"  # Run daily at midnight
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etcd-backup
            image: bitnami/etcd:latest
            command:
            - /bin/sh
            - -c
            - |
              ETCDCTL_API=3 etcdctl --endpoints=https://etcd-client:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-certs
              mountPath: /etc/kubernetes/pki/etcd
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
              type: Directory
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## Monitoring and Logging

La monitorización y el logging eficaces son un elemento central de la administración de clústeres.

El siguiente diagrama muestra la arquitectura de monitorización y logging de un clúster de Kubernetes:

```mermaid
flowchart LR
    subgraph "Monitoring Stack"
        Prom[Prometheus] --> Alert[Alertmanager]
        Prom --> Grafana[Grafana]
        KSM[kube-state-metrics] --> Prom
        NE[Node Exporter] --> Prom
        Alert --> Notify[Notification Channels]
    end

    subgraph "Logging Stack"
        Fluentd[Fluentd/Fluent Bit] --> ES[(Elasticsearch)]
        ES --> Kibana[Kibana]
        Fluentd --> Loki[(Loki)]
        Loki --> Grafana
    end

    subgraph "Kubernetes Cluster"
        API[API Server] --> KSM
        Node[Node] --> NE
        Pod[Pod] --> Fluentd
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef prometheusComponent fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef grafana fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class API,Node,Pod k8sComponent;
    class ES,Loki dataStore;
    class Prom,Alert,KSM,NE prometheusComponent;
    class Grafana,Kibana grafana;
    class Fluentd,Notify default;
```

### Monitoring Tools

Herramientas para la monitorización de clústeres de Kubernetes:

1. **Prometheus**: Recopilación y almacenamiento de métricas
2. **Grafana**: Visualización de métricas
3. **Alertmanager**: Gestión de alertas
4. **kube-state-metrics**: Generación de métricas de objetos de Kubernetes
5. **metrics-server**: Proporciona métricas de uso de recursos

#### Prometheus and Grafana Installation

Instalar Prometheus y Grafana usando Helm:

```bash
# Add Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

#### Key Monitoring Metrics

Métricas clave que monitorizar:

1. **Node Metrics**: CPU, memoria, disco, uso de red
2. **Pod Metrics**: CPU, uso de memoria, recuento de reinicios
3. **Container Metrics**: CPU, uso de memoria, uso de filesystem
4. **API Server Metrics**: Latencia de solicitudes, recuento de solicitudes, tasa de errores
5. **etcd Metrics**: I/O de disco, cambios de leader, latencia de commit

### Logging Tools

Herramientas para el logging de clústeres de Kubernetes:

1. **Elasticsearch**: Almacenamiento y búsqueda de logs
2. **Fluentd/Fluent Bit**: Recopilación y reenvío de logs
3. **Kibana**: Visualización de logs
4. **Loki**: Sistema de agregación de logs
5. **Grafana**: Visualización de logs

#### EFK (Elasticsearch, Fluentd, Kibana) Stack Installation

Instalar el stack EFK usando Helm:

```bash
# Install Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace

# Install Fluentd
helm install fluentd fluent/fluentd \
  --namespace logging

# Install Kibana
helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=LoadBalancer
```

#### Log Collection Configuration

Ejemplo de configuración de Fluentd:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.**>
      @type kubernetes_metadata
      kubernetes_url https://kubernetes.default.svc
      bearer_token_file /var/run/secrets/kubernetes.io/serviceaccount/token
      ca_file /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    </filter>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-master
      port 9200
      logstash_format true
      logstash_prefix k8s
    </match>
```

## Troubleshooting

La resolución de problemas de clústeres de Kubernetes es una parte importante de la administración de clústeres.

### Pod Troubleshooting

Comandos para la resolución de problemas de Pod:

```bash
# Check pod status
kubectl get pod <pod-name> -o wide

# Check pod detailed information
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> -c <container-name>  # For multi-container pods
kubectl logs <pod-name> --previous  # Logs from previous container

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh
```

### Node Troubleshooting

Comandos para la resolución de problemas de Node:

```bash
# Check node status
kubectl get node <node-name> -o wide

# Check node detailed information
kubectl describe node <node-name>

# Check node resource usage
kubectl top node <node-name>

# SSH to node
ssh <node-name>

# Check node system logs
journalctl -u kubelet

# Check node resource usage
top
df -h
free -m
```

### Networking Troubleshooting

Comandos para la resolución de problemas de red:

```bash
# Check service status
kubectl get svc <service-name>

# Check service detailed information
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpoints <service-name>

# Check DNS
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### Control Plane Troubleshooting

Comandos para la resolución de problemas del control plane:

```bash
# Check component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check controller manager logs
kubectl logs -n kube-system kube-controller-manager-<node-name>

# Check scheduler logs
kubectl logs -n kube-system kube-scheduler-<node-name>

# Check etcd logs
kubectl logs -n kube-system etcd-<node-name>
```

## Amazon EKS Cluster Administration

Amazon EKS es un servicio gestionado de Kubernetes que automatiza muchos aspectos de la administración de clústeres.

El siguiente diagrama muestra la arquitectura de clústeres de Amazon EKS y los componentes de gestión:

```mermaid
flowchart TD
    User[User] --> |Manage| AWS[AWS Management Console/CLI/API]
    AWS --> |Manage| EKS[Amazon EKS]

    subgraph "AWS Cloud"
        EKS --> CP[EKS Control Plane]
        EKS --> NG[EKS Node Groups]
        EKS --> Fargate[EKS Fargate]

        CP --> |Uses| AWSIAM[AWS IAM]
        CP --> |Uses| AWSVPC[AWS VPC]
        CP --> |Logging| CW[CloudWatch]

        NG --> |Uses| EC2[EC2 Instances]
        Fargate --> |Uses| FargateProfile[Fargate Profiles]
    end

    subgraph "Add-ons"
        EKS --> CNI[Amazon VPC CNI]
        EKS --> CoreDNS[CoreDNS]
        EKS --> KubeProxy[kube-proxy]
    end

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class CP,NG,Fargate,CNI,CoreDNS,KubeProxy k8sComponent;
    class AWS,EKS,AWSIAM,AWSVPC,CW,EC2,FargateProfile awsService;
    class User userApp;
```

### EKS Cluster Configuration

Gestión de configuración de clústeres EKS:

```bash
# Check EKS cluster information
aws eks describe-cluster --name my-cluster

# Update EKS cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=true,endpointPrivateAccess=true

# Update EKS cluster version
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.22
```

### EKS Node Group Management

Gestión de node groups de EKS:

```bash
# Check node group information
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup

# Scale node group
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --scaling-config minSize=2,maxSize=10,desiredSize=5

# Update node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS Add-on Management

Gestión de add-ons de EKS:

```bash
# Check available add-ons
aws eks describe-addon-versions \
  --kubernetes-version 1.22

# Install add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.1-eksbuild.1

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.10.2-eksbuild.1

# Delete add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni
```

### EKS Cluster Upgrade

Proceso de actualización de clústeres EKS:

1. **Control Plane Upgrade**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.22
   ```

2. **Add-on Upgrade**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.2-eksbuild.1
   ```

3. **Node Group Upgrade**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS Cluster Monitoring

Herramientas de monitorización de clústeres EKS:

1. **Amazon CloudWatch**: Métricas, logs, alertas
2. **AWS CloudTrail**: Logging de llamadas de API
3. **Amazon Managed Grafana**: Visualización de métricas
4. **Amazon Managed Service for Prometheus**: Recopilación y almacenamiento de métricas

Habilitar CloudWatch Container Insights:

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## Cluster Administration Best Practices

Mejores prácticas para la administración de clústeres de Kubernetes y EKS:

### Cluster Configuration Best Practices

1. **Infrastructure as Code (IaC)**: Gestionar la configuración del clúster usando Terraform, AWS CDK, eksctl, etc.
2. **Version Control**: Almacenar la configuración del clúster en sistemas de control de versiones
3. **Multiple Environments**: Separar entornos de desarrollo, staging y producción
4. **Network Separation**: Configurar separación de red y security groups adecuados
5. **Least Privilege Principle**: Conceder solo los permisos mínimos necesarios

### Operations Best Practices

1. **Regular Backups**: Backup regular de etcd y recursos importantes
2. **Monitoring and Alerting**: Construir sistemas integrales de monitorización y alertas
3. **Centralized Logging**: Centralizar y analizar logs
4. **Automation**: Automatizar tareas repetitivas
5. **Disaster Recovery Planning**: Establecer y probar planes claros de recuperación ante desastres

### Security Best Practices

1. **Regular Updates**: Actualizaciones regulares del clúster y los Nodes
2. **Network Policies**: Configurar network policies adecuadas
3. **Encryption**: Cifrar datos en reposo y en tránsito
4. **Security Context**: Configurar security contexts adecuados
5. **Image Scanning**: Escanear imágenes de contenedor en busca de vulnerabilidades

### Resource Management Best Practices

1. **Resource Requests and Limits**: Establecer resource requests y limits adecuados para todos los Pods
2. **Namespace Separation**: Separar workloads por namespace
3. **Resource Quotas**: Establecer resource quotas por namespace
4. **HPA and VPA**: Configurar autoscaling
5. **Node Affinity and Taints**: Optimizar la colocación de workloads

### EKS-Specific Best Practices

1. **Managed Node Groups**: Usar managed node groups cuando sea posible
2. **Fargate**: Usar Fargate para workloads serverless
3. **EKS Add-ons**: Usar add-ons oficiales de EKS
4. **IAM Roles for Service Accounts (IRSA)**: Gestionar permisos de IAM por Pod
5. **VPC CNI Customization**: Configurar VPC CNI según los requisitos de red

## Conclusion

La administración de clústeres de Kubernetes desempeña un papel importante en el mantenimiento de la estabilidad, seguridad y rendimiento del clúster. Este capítulo cubrió diversos aspectos de la administración de clústeres, incluida la gestión de componentes del clúster, gestión de recursos, redes, gestión de autenticación y autorización, actualizaciones, backup y recuperación, monitorización y logging, y resolución de problemas.

Usar Amazon EKS reduce la complejidad de la gestión del control plane de Kubernetes y simplifica la administración de clústeres mediante la integración con servicios de AWS. Sin embargo, comprender los conceptos fundamentales de Kubernetes y las mejores prácticas sigue siendo importante para una gestión eficaz del clúster.

La administración de clústeres es un proceso continuo que debe ajustarse de forma permanente según los requisitos del clúster y las características de los workloads. Es importante usar herramientas de monitorización para hacer seguimiento del estado del clúster, minimizar tareas repetitivas mediante automatización y seguir mejores prácticas para mantener la estabilidad y seguridad del clúster.

## Cluster Networking

La red del clúster de Kubernetes gestiona la comunicación de Pod a Pod, el descubrimiento de Services y el acceso externo.

### Network Architecture

```mermaid
graph TD
    A[Cluster Networking] --> B[Pod Network]
    A --> C[Service Network]
    A --> D[Ingress]
    A --> E[Network Policies]

    B --> F[CNI Plugin]
    C --> G[ClusterIP, NodePort, LoadBalancer]
    D --> H[Ingress Controller]
    E --> I[Network Security]

    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef networkComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E k8sComponent;
    class F,G,H,I networkComponent;
```

### CNI Plugin Management

Los plugins CNI (Container Network Interface) gestionan la red para los clústeres de Kubernetes.

```bash
# Install Calico CNI
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Install Flannel CNI
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

# Install Cilium CNI (using Helm)
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.14.0 --namespace kube-system
```

### CNI Plugin Comparison

| CNI Plugin | Network Model | Network Policy Support | Performance | Features |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | Yes | High | Strong in network policies, routing-based |
| **Flannel** | VXLAN/host-gateway | No | Medium | Simple setup, limited features |
| **Cilium** | eBPF | Yes | Very High | L3-L7 policies, high performance |
| **Weave Net** | VXLAN | Yes | Medium | Encryption support, multi-cluster |
| **AWS VPC CNI** | AWS VPC | No | High | Optimized for AWS EKS |

### Network Troubleshooting

```bash
# Test pod network connectivity
kubectl run -it --rm network-test --image=busybox -- sh
# Inside the container
ping <target-ip>
traceroute <target-ip>
wget -O- <service-name>

# DNS troubleshooting
kubectl run -it --rm dns-test --image=busybox -- sh
# Inside the container
nslookup kubernetes.default.svc.cluster.local
cat /etc/resolv.conf

# Check service endpoints
kubectl get endpoints <service-name>

# Check network policies
kubectl describe networkpolicy -n <namespace>
```
## Authentication and Authorization Management

La gestión de autenticación y autorización de Kubernetes es un elemento central de la seguridad del clúster. RBAC (Role-Based Access Control) se utiliza para gestionar permisos de usuarios y service accounts.

### Authentication Methods

Kubernetes admite diversos métodos de autenticación:

1. **X.509 Certificates**: Autenticación mediante certificados de cliente
2. **Service Account Tokens**: Se usan para el acceso al API server dentro de Pods
3. **OpenID Connect (OIDC)**: Integración con proveedores de identidad externos
4. **Webhook Token Authentication**: Integración con servicios de autenticación externos
5. **Authentication Proxy**: Autenticación mediante proxy

### RBAC Configuration

```yaml
# role.yaml - namespace-scoped role
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

```yaml
# rolebinding.yaml - binding role to user
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

```yaml
# clusterrole.yaml - cluster-scoped role
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

```yaml
# clusterrolebinding.yaml - binding cluster role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: manager
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### User Certificate Creation

```bash
# Generate private key
openssl genrsa -out jane.key 2048

# Create Certificate Signing Request (CSR)
openssl req -new -key jane.key -out jane.csr -subj "/CN=jane/O=dev"

# Sign certificate with Kubernetes CA
sudo openssl x509 -req -in jane.csr \
  -CA /etc/kubernetes/pki/ca.crt \
  -CAkey /etc/kubernetes/pki/ca.key \
  -CAcreateserial \
  -out jane.crt -days 365

# Add user to kubeconfig
kubectl config set-credentials jane --client-certificate=jane.crt --client-key=jane.key
kubectl config set-context jane-context --cluster=kubernetes --user=jane
```

### Service Account Management

```bash
# Create service account
kubectl create serviceaccount app-service-account

# Bind role to service account
kubectl create rolebinding app-service-account-binding \
  --role=pod-reader \
  --serviceaccount=default:app-service-account

# Check service account token
kubectl describe serviceaccount app-service-account
```

### Permission Verification

```bash
# Check user permissions
kubectl auth can-i get pods --as jane

# Check permissions in a specific namespace
kubectl auth can-i create deployments --as jane --namespace production
```
## Cluster Upgrades

Las actualizaciones de clústeres de Kubernetes son necesarias para aplicar nuevas funciones, parches de seguridad y correcciones de errores. Las actualizaciones deben planificarse y ejecutarse cuidadosamente.

### Upgrade Planning

```mermaid
graph TD
    A[Upgrade Planning] --> B[Check Version Compatibility]
    A --> C[Create Backup]
    A --> D[Choose Upgrade Strategy]
    A --> E[Plan Downtime]

    B --> F[Review API Changes]
    C --> G[etcd Backup]
    D --> H[In-place vs Blue/Green]
    E --> I[User Communication]

    classDef planning fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef action fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E planning;
    class F,G,H,I action;
```

### Upgrade Strategy Comparison

| Strategy | Description | Advantages | Disadvantages | Suitable Environment |
|----------|-------------|------------|---------------|---------------------|
| **In-place Upgrade** | Directly upgrade existing cluster | Resource efficient, simple procedure | Complex rollback, potential downtime | Development, test environments |
| **Blue/Green Deployment** | Create new version cluster and switch | Safe rollback, verifiable | Resource duplication, increased cost | Production environments |
| **Canary Deployment** | Move only some workloads to new cluster | Gradual verification, reduced risk | Complex management, dual operation | Critical production environments |

### Upgrade Using kubeadm

```bash
# Check current version
kubeadm version

# Check upgrade plan
sudo kubeadm upgrade plan

# Control plane upgrade
sudo apt-get update
sudo apt-get install -y kubeadm=1.33.3-00
sudo kubeadm upgrade apply v1.33.3

# kubelet upgrade
sudo apt-get install -y kubelet=1.33.3-00 kubectl=1.33.3-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# Worker node upgrade (on each node)
# 1. Drain node
kubectl drain <node-name> --ignore-daemonsets

# 2. kubeadm upgrade
sudo apt-get update
sudo apt-get install -y kubeadm=1.33.3-00
sudo kubeadm upgrade node

# 3. kubelet upgrade
sudo apt-get install -y kubelet=1.33.3-00 kubectl=1.33.3-00
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# 4. Uncordon node
kubectl uncordon <node-name>
```

### Post-Upgrade Verification

```bash
# Check cluster version
kubectl version

# Check node versions
kubectl get nodes

# Check component status
kubectl get componentstatuses

# Check workload status
kubectl get pods -A
```
## Backup and Recovery

El backup y la recuperación de clústeres de Kubernetes son una parte importante de la planificación de recuperación ante desastres. Los principales objetivos de backup son la base de datos etcd, los datos de persistent volumes y las definiciones de recursos de Kubernetes.

### etcd Backup and Recovery

etcd es un componente central que guarda toda la información de estado del clúster.

```bash
# etcd backup
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d).db

# etcd recovery
# 1. Stop cluster
sudo systemctl stop kubelet
sudo docker stop $(docker ps -q)

# 2. Restore etcd data
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  snapshot restore /backup/etcd-snapshot-2025-11-24.db \
  --data-dir=/var/lib/etcd-restore \
  --name=master \
  --initial-cluster=master=https://127.0.0.1:2380 \
  --initial-cluster-token=etcd-cluster-1 \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# 3. Configure to use restored data directory
sudo mv /var/lib/etcd /var/lib/etcd.bak
sudo mv /var/lib/etcd-restore /var/lib/etcd

# 4. Restart cluster
sudo systemctl start kubelet
```

### Kubernetes Resource Backup

```bash
# Backup all resources in all namespaces
mkdir -p /backup/resources/$(date +%Y-%m-%d)
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl -n $ns get all -o yaml > /backup/resources/$(date +%Y-%m-%d)/$ns-all.yaml
done

# Backup specific resource types
for resource in deployments services configmaps secrets; do
  kubectl get $resource -A -o yaml > /backup/resources/$(date +%Y-%m-%d)/$resource.yaml
done
```

### Backup and Recovery Using Velero

Velero es una herramienta para realizar backups y recuperar recursos de clústeres de Kubernetes y persistent volumes.

```bash
# Install Velero (using AWS S3 backup storage)
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.7.0 \
  --bucket velero-backup \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --secret-file ./credentials-velero

# Full cluster backup
velero backup create full-cluster-backup --include-namespaces '*'

# Backup specific namespace
velero backup create production-backup --include-namespaces production

# Check backup status
velero backup describe full-cluster-backup

# Restore from backup
velero restore create --from-backup full-cluster-backup
```

### Backup Strategy Comparison

| Backup Method | Backup Target | Advantages | Disadvantages | Recovery Time |
|--------------|---------------|------------|---------------|---------------|
| **etcd Snapshot** | Cluster state | Built-in feature, complete state preservation | Volume data not included, manual process | Medium |
| **Resource YAML Backup** | Kubernetes objects | Simple implementation, selective restore | Volume data not included, relationship complexity | Slow |
| **Velero** | Resources and volumes | Automation, scheduling, volume snapshots | Additional tool installation required | Fast |
| **Cloud Provider Snapshots** | Entire cluster | Complete recovery, cloud integration | Cloud dependency, cost | Very Fast |
## Monitoring and Logging

La gestión eficaz del clúster requiere un sistema integral de monitorización y logging. Esto permite detectar y resolver problemas de forma temprana.

### Monitoring Architecture

```mermaid
graph TD
    A[Kubernetes Monitoring] --> B[Metric Collection]
    A --> C[Log Collection]
    A --> D[Alerting]
    A --> E[Visualization]

    B --> F[Prometheus]
    C --> G[Fluentd/Fluent Bit]
    D --> H[Alertmanager]
    E --> I[Grafana]

    F --> J[kube-state-metrics]
    F --> K[node-exporter]
    G --> L[Elasticsearch]
    L --> M[Kibana]

    classDef monitoring fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef component fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E monitoring;
    class F,G,H,I,J,K,L,M component;
```

### Prometheus and Grafana Installation

```bash
# Install Prometheus and Grafana using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.service.type=NodePort

# Check services
kubectl get svc -n monitoring

# Access Grafana (using port forwarding)
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Default username: admin, default password: prom-operator
```

### EFK Stack Installation (Elasticsearch, Fluentd, Kibana)

```bash
# Install Elasticsearch and Kibana
helm repo add elastic https://helm.elastic.co
helm repo update

helm install elasticsearch elastic/elasticsearch \
  --namespace logging \
  --create-namespace \
  --set replicas=1 \
  --set minimumMasterNodes=1

helm install kibana elastic/kibana \
  --namespace logging \
  --set service.type=NodePort

# Install Fluentd
kubectl apply -f https://raw.githubusercontent.com/fluent/fluentd-kubernetes-daemonset/master/fluentd-daemonset-elasticsearch.yaml
```

### Key Monitoring Metrics

| Metric Type | Description | Key Metrics | Monitoring Tools |
|-------------|-------------|-------------|-----------------|
| **Node Metrics** | Node-level resource usage | CPU, memory, disk, network | node-exporter, Prometheus |
| **Pod Metrics** | Container resource usage | CPU, memory usage, limits | cAdvisor, Prometheus |
| **Cluster Metrics** | Cluster state and resources | Pod count, node status, events | kube-state-metrics |
| **Application Metrics** | Custom application metrics | Request count, latency, error rate | Prometheus client libraries |

### Log Collection and Analysis

```bash
# Check logs for a specific pod
kubectl logs <pod-name> -n <namespace>

# Check logs from previous instance
kubectl logs <pod-name> -n <namespace> --previous

# Check logs for a specific container (multi-container pod)
kubectl logs <pod-name> -c <container-name> -n <namespace>

# Stream logs
kubectl logs -f <pod-name> -n <namespace>

# Check logs for all pods (using label selector)
kubectl logs -l app=nginx -n <namespace>
```

### Alert Configuration

Puedes configurar alertas usando Prometheus Alertmanager:

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

    route:
      receiver: 'slack-notifications'
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      group_by: ['alertname', 'cluster', 'service']

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ end }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}"
```
## Troubleshooting

La resolución de problemas de clústeres de Kubernetes es una habilidad importante para administradores de sistemas y operadores. Se requiere un enfoque sistemático para una resolución de problemas eficaz.

### Troubleshooting Methodology

```mermaid
graph TD
    A[Problem Identification] --> B[Information Gathering]
    B --> C[Root Cause Analysis]
    C --> D[Apply Solution]
    D --> E[Verification]
    E --> F[Documentation]

    B --> G[Check Logs]
    B --> H[Check Events]
    B --> I[Check Resource Status]

    classDef process fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef action fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,C,D,E,F process;
    class G,H,I action;
```

### Common Problems and Solutions

| Problem Type | Symptoms | Diagnostic Commands | Common Solutions |
|-------------|----------|---------------------|-----------------|
| **Pod Not Starting** | Pod in Pending or ContainerCreating state | `kubectl describe pod <pod-name>` | Check resource constraints, image availability, volume mounts |
| **Service Connection Issues** | Cannot access pods through service | `kubectl describe svc <service-name>`, `kubectl get endpoints <service-name>` | Check label selectors, pod status, network policies |
| **Node Issues** | Node in NotReady state | `kubectl describe node <node-name>`, `kubectl get events` | Check kubelet status, system resources, network connectivity |
| **DNS Issues** | Cannot connect by service name | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | Check CoreDNS pods, kube-dns service, network policies |
| **Authentication Issues** | API server access denied | `kubectl auth can-i <verb> <resource>` | Check RBAC settings, certificate validity, service account |

### Pod Troubleshooting

```bash
# Check pod status
kubectl get pod <pod-name> -o wide

# Check pod details
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Logs from previous container

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh

# Check pod events
kubectl get events --field-selector involvedObject.name=<pod-name>
```

### Node Troubleshooting

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# Check node resource usage
kubectl top node <node-name>

# Check node system logs (SSH required)
ssh <node-ip> 'sudo journalctl -u kubelet'

# Check kubelet status (SSH required)
ssh <node-ip> 'sudo systemctl status kubelet'
```

### Networking Troubleshooting

```bash
# Check service and endpoints
kubectl get svc <service-name>
kubectl get endpoints <service-name>

# DNS troubleshooting
kubectl run -it --rm dns-test --image=busybox -- sh
# Inside the container
nslookup kubernetes.default.svc.cluster.local
cat /etc/resolv.conf

# Network connectivity test
kubectl run -it --rm network-test --image=nicolaka/netshoot -- sh
# Inside the container
ping <target-ip>
traceroute <target-ip>
curl <service-name>:<port>
```
## Amazon EKS Cluster Administration

Amazon EKS (Elastic Kubernetes Service) es un servicio gestionado de Kubernetes en AWS donde AWS gestiona el control plane. Sin embargo, la gestión de Nodes, redes, seguridad, etc. es responsabilidad del usuario.

### EKS Cluster Architecture

```mermaid
graph TD
    A[Amazon EKS Cluster] --> B[Control Plane]
    A --> C[Data Plane]
    A --> D[Networking]
    A --> E[Security]

    B --> F[AWS Managed Components]
    C --> G[Managed Node Groups]
    C --> H[Self-Managed Nodes]
    C --> I[Fargate]
    D --> J[VPC CNI]
    E --> K[IAM Authentication]

    F --> L[API Server, etcd, Scheduler]
    G --> M[EC2 Auto Scaling Groups]
    J --> N[AWS VPC]
    K --> O[IAM Roles and Policies]

    classDef awsManaged fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef userManaged fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef network fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    class A,B,F,L awsManaged;
    class C,G,H,I,E,K,O userManaged;
    class D,J,N network;
```

### EKS Cluster Creation

```bash
# Create cluster using eksctl
eksctl create cluster \
  --name my-cluster \
  --version 1.33 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Create cluster using AWS CLI
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345
```

### Node Group Management

```bash
# Create managed node group
eksctl create nodegroup \
  --cluster my-cluster \
  --region us-west-2 \
  --name my-nodegroup \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5

# Scale node group
eksctl scale nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --nodes 5 \
  --region us-west-2

# Update node group
eksctl update nodegroup \
  --cluster my-cluster \
  --name my-nodegroup \
  --region us-west-2 \
  --max-pods-per-node 110
```

### EKS Cluster Upgrade

```bash
# Check cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"

# Upgrade cluster control plane
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version 1.33

# Upgrade managed node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS Cluster Authentication and Authorization

```bash
# Map IAM user/role to cluster RBAC
eksctl create iamidentitymapping \
  --cluster my-cluster \
  --arn arn:aws:iam::123456789012:role/admin-role \
  --group system:masters \
  --username admin

# Check aws-auth ConfigMap
kubectl describe configmap aws-auth -n kube-system
```

### EKS Cluster Monitoring

```bash
# Enable CloudWatch Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --region us-west-2

# Install Prometheus and Grafana (using Amazon EKS add-on)
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version v1.1.1-eksbuild.1
```
## Cluster Administration Best Practices

Las mejores prácticas para una gestión eficaz de clústeres de Kubernetes son importantes para garantizar estabilidad, seguridad y rendimiento.

### Cluster Setup Best Practices

1. **Multi-Availability Zone Configuration**: Distribuir Nodes entre múltiples availability zones para alta disponibilidad
2. **Appropriate Sizing**: Seleccionar tipos y cantidades de Node apropiados para los workloads
3. **Autoscaling Configuration**: Habilitar cluster autoscaler y horizontal pod autoscaler
4. **Apply Network Policies**: Comenzar con una política deny predeterminada y permitir solo la comunicación necesaria
5. **Set Resource Quotas**: Establecer límites de recursos por namespace

### Operations Best Practices

1. **Use Declarative Configuration**: Definir todos los recursos como archivos YAML y gestionarlos con control de versiones
2. **Adopt GitOps**: Usar Git como única fuente de verdad y construir pipelines de despliegue automatizados
3. **Regular Backups**: Backup regular de datos de etcd y datos de persistent volumes
4. **Monitoring and Alerting**: Construir sistemas de monitorización integrales y establecer alertas para métricas clave
5. **Centralized Logging**: Recopilar todos los logs en un sistema de logging central para facilitar el análisis

### Security Best Practices

1. **Least Privilege Principle**: Conceder solo los permisos mínimos necesarios usando RBAC
2. **Network Segmentation**: Limitar la comunicación de Pod a Pod usando network policies
3. **Image Scanning**: Implementar escaneo de imágenes de contenedor para detectar vulnerabilidades
4. **Secret Management**: Usar herramientas externas de gestión de secrets (por ejemplo, AWS Secrets Manager, HashiCorp Vault)
5. **Regular Security Audits**: Realizar auditorías regulares de configuración y permisos del clúster

### Upgrade Best Practices

1. **Gradual Upgrades**: Actualizar de forma gradual en lugar de todo a la vez
2. **Test Environment First**: Verificar las actualizaciones en entornos de prueba antes de producción
3. **Create Backups**: Realizar backups completos antes de las actualizaciones
4. **Rollback Plan**: Desarrollar un plan para volver a versiones anteriores en caso de problemas
5. **Set Upgrade Windows**: Realizar actualizaciones durante períodos de bajo uso

### Cost Optimization Best Practices

1. **Select Appropriate Node Sizes**: Seleccionar tipos de Node óptimos para los workloads
2. **Utilize Spot Instances**: Usar spot instances para workloads no críticos
3. **Configure Autoscaling**: Configurar escalado automático hacia arriba y hacia abajo según la demanda
4. **Optimize Resource Requests and Limits**: Establecer resource requests y limits según el uso real
5. **Identify Idle Resources**: Identificar y eliminar regularmente recursos inactivos

### Documentation Best Practices

1. **Document Architecture**: Documentar la arquitectura del clúster, redes y configuraciones de seguridad
2. **Document Operations Procedures**: Documentar tareas operativas comunes, procedimientos de resolución de problemas y planes de respuesta ante emergencias
3. **Change Management**: Registrar y hacer seguimiento de todos los cambios del clúster
4. **Create Runbooks**: Proporcionar guías paso a paso para escenarios comunes
5. **Knowledge Sharing**: Realizar sesiones regulares de intercambio de conocimientos y formación dentro del equipo
## Conclusion

La administración de clústeres de Kubernetes es una tarea compleja que incluye diversos aspectos. Se requiere un enfoque sistemático desde la configuración del clúster hasta la operación, monitorización, resolución de problemas y actualizaciones.

Para una administración eficaz del clúster, céntrate en las siguientes áreas clave:

1. **Cluster Component Management**: Operación estable de los componentes del control plane y Node
2. **Resource Management**: Asignación y uso eficientes de recursos
3. **Networking**: Configuración de red segura y eficiente
4. **Security**: Gestión adecuada de autenticación y autorización
5. **Backup and Recovery**: Prevención de pérdida de datos y planificación de recuperación ante desastres
6. **Monitoring and Logging**: Monitorización del estado y rendimiento del clúster
7. **Troubleshooting**: Enfoque sistemático de resolución de problemas

Al usar servicios gestionados de Kubernetes como Amazon EKS, es importante comprender el modelo de responsabilidad compartida entre el proveedor del servicio y el usuario. Aunque AWS gestiona el control plane, la gestión de Nodes, redes, seguridad, etc. sigue siendo responsabilidad del usuario.

Siguiendo mejores prácticas y utilizando herramientas adecuadas, puedes operar un clúster de Kubernetes estable, seguro y eficiente. Es importante el aprendizaje y la mejora continuos para fortalecer las capacidades de gestión del clúster.

---

> **Referencias**:
> - [Kubernetes Official Documentation: Cluster Administration](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes Best Practices: Cluster Administration](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd Documentation: Backup and Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

## Quiz

Para comprobar lo que aprendiste en este capítulo, intenta el [Cluster Administration Quiz](../quizzes/core/09-cluster-administration-quiz.md).
