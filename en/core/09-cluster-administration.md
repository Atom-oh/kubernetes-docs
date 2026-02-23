# Kubernetes Cluster Administration

> **Supported Versions**: Kubernetes 1.34 (Released 2025-11-24)
> **Last Updated**: 2025-11-24

Kubernetes cluster administration is an important task that includes cluster setup, maintenance, monitoring, troubleshooting, and upgrades. In this chapter, we will explore various aspects of Kubernetes cluster administration and best practices for cluster management in Amazon EKS.

## Core Concepts

- **Cluster Lifecycle Management**: The entire process from cluster creation to decommissioning
- **Control Plane Management**: Managing core components such as API server, scheduler, and controller manager
- **Node Management**: Adding, removing, and maintaining worker nodes
- **Resource Allocation**: Setting resource allocation and limits for CPU, memory, storage, etc.
- **Upgrade Strategy**: Cluster and application upgrade strategies to minimize downtime

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

The following tools are required for cluster administration:

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

Kubernetes cluster administration is the process of managing the entire lifecycle of a cluster. This includes the following main areas:

1. **Cluster Setup and Configuration**: Cluster creation, node addition, networking setup, storage configuration, etc.
2. **Operations Management**: Resource monitoring, performance optimization, capacity planning, troubleshooting
3. **Security Management**: Authentication, authorization, network policies, security contexts, etc.
4. **Upgrades and Patches**: Cluster version upgrades, security patch application
5. **Backup and Recovery**: Cluster data backup, disaster recovery planning

The following diagram shows the main areas of Kubernetes cluster administration and related tools:

## Cluster Component Management

A Kubernetes cluster consists of control plane components and node components. Managing each component is critical for cluster stability and performance.

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

The API server is a core component of the control plane that exposes the Kubernetes API.

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### etcd Management

etcd is a distributed key-value store that stores all cluster data for Kubernetes.

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

Nodes are worker machines that run containerized applications.

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

Various tools are available for Kubernetes cluster administration:

1. **kubectl**: Command-line tool for interacting with Kubernetes clusters
2. **kubeadm**: Tool for creating and managing Kubernetes clusters
3. **kops**: Tool for creating, upgrading, and managing Kubernetes clusters
4. **eksctl**: Tool for creating and managing Amazon EKS clusters
5. **Helm**: Kubernetes application package manager
6. **Kubernetes Dashboard**: Web-based Kubernetes user interface
7. **Prometheus & Grafana**: Monitoring and alerting tools
8. **Fluentd & Elasticsearch**: Logging tools

## Cluster Component Management

A Kubernetes cluster consists of multiple components, and effectively managing these components is important.

### Control Plane Components

Control plane components manage the overall state of the cluster:

1. **kube-apiserver**: Component that exposes the Kubernetes API
2. **etcd**: Key-value store that stores cluster data
3. **kube-scheduler**: Component that schedules pods to nodes
4. **kube-controller-manager**: Component that runs controllers
5. **cloud-controller-manager**: Component that interacts with cloud providers

The following diagram shows Kubernetes control plane components and their interactions:

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

It is important to monitor the status of control plane components:

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Control Plane Component Configuration

How to manage control plane component configuration:

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

Node components run on each node and manage pods:

1. **kubelet**: Agent running on each node that ensures pods and containers are running
2. **kube-proxy**: Maintains network rules and handles connection forwarding
3. **Container Runtime**: Software that runs containers (Docker, containerd, CRI-O, etc.)

#### Node Management

Key commands for node management:

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

Commands for node troubleshooting:

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

Effectively managing resources in a Kubernetes cluster is important for maintaining cluster stability and performance.

### Resource Quotas

Resource quotas limit resource usage per namespace:

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

In the above example, the `dev` namespace can have a maximum of 10 pods, 1 CPU and 1Gi memory requests, and 2 CPU and 2Gi memory limits.

### Limit Ranges

Limit ranges set defaults and limits for individual resources within a namespace:

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

In the above example, all containers in the `dev` namespace have default limits of 500m CPU and 512Mi memory, default requests of 200m CPU and 256Mi memory, maximum of 1 CPU and 1Gi memory, and minimum of 100m CPU and 128Mi memory.

### Horizontal Pod Autoscaler (HPA)

HPA automatically adjusts the number of pods based on CPU usage or custom metrics:

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

In the above example, the `frontend` deployment automatically scales out when CPU utilization exceeds 80% and scales in when below 80%. It maintains a minimum of 2 and maximum of 10 replicas.

### Vertical Pod Autoscaler (VPA)

VPA automatically adjusts pod CPU and memory requests:

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

In the above example, pods in the `frontend` deployment have their CPU and memory requests automatically adjusted based on actual resource usage.
## Cluster Networking

Kubernetes cluster networking manages communication between pods, services, and nodes.

### Cluster Network Model

Basic requirements of the Kubernetes network model:

1. All pods can communicate with all other pods without NAT
2. Node agents (kubelet) can communicate with all pods on that node
3. Pods running in NAT mode can communicate with the outside

The following diagram shows Kubernetes networking components and communication flows:

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

Kubernetes implements networking through CNI plugins. Common CNI plugins:

1. **Calico**: CNI with enhanced network policy and security features
2. **Flannel**: Provides simple overlay networking
3. **Cilium**: eBPF-based networking and security solution
4. **AWS VPC CNI**: CNI integrated with AWS VPC
5. **Weave Net**: Multi-host container networking solution

#### CNI Plugin Installation and Configuration

CNI plugin installation example (Calico):

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Service Networking

Kubernetes services provide stable endpoints for pod sets:

1. **ClusterIP**: Service accessible only within the cluster
2. **NodePort**: Service accessible through a specific port on all nodes
3. **LoadBalancer**: Service accessible through an external load balancer
4. **ExternalName**: Provides CNAME record for external services

#### Service CIDR Configuration

Service CIDR defines the service IP address range:

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS Management

CoreDNS provides DNS services for Kubernetes:

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

CoreDNS configuration example:

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

Network policies control communication between pods:

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

In the above example, pods with the `role=db` label only allow TCP port 3306 inbound traffic from pods with the `role=frontend` label and TCP port 9090 outbound traffic to pods with the `role=monitoring` label.

## Authentication and Authorization Management

Kubernetes authentication and authorization management are core elements of cluster security.

The following diagram shows the Kubernetes authentication and authorization flow:

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

Kubernetes supports various authentication methods:

1. **X.509 Certificates**: Authentication using client certificates
2. **Service Account Tokens**: JWT tokens associated with service accounts
3. **OpenID Connect (OIDC)**: Authentication through external identity providers
4. **Webhook Token Authentication**: Token verification through external services
5. **Authentication Proxy**: Request processing through authentication proxy

#### X.509 Certificate Management

X.509 certificate creation and management:

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

OIDC authentication configuration example:

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Authorization

Kubernetes supports various authorization modes:

1. **RBAC (Role-Based Access Control)**: Role-based access control
2. **ABAC (Attribute-Based Access Control)**: Attribute-based access control
3. **Node**: Node authorization
4. **Webhook**: Authorization through external services

#### RBAC Configuration

RBAC is the most common authorization mechanism:

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

In the above example, `user` has permission to view pods in the `default` namespace.

#### ClusterRole and ClusterRoleBinding

Manages permissions for cluster-wide resources:

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

In the above example, `user` has permission to view all nodes in the cluster.

### Service Account Management

Service accounts are used by pods to communicate with the API server:

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

Security context defines permissions and access control for pods and containers:

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

In the above example, the pod runs with UID 1000 and GID 3000, and the container cannot escalate privileges, has all Linux capabilities dropped, and has the root filesystem mounted as read-only.

## Cluster Upgrades

Kubernetes cluster upgrades are necessary to apply new features, performance improvements, and security patches.

The following diagram shows the Kubernetes cluster upgrade process:

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

Considerations when planning cluster upgrades:

1. **Version Compatibility**: Check compatibility between Kubernetes versions
2. **Upgrade Path**: Check supported upgrade paths
3. **Downtime**: Plan for expected downtime during upgrade
4. **Rollback Plan**: Develop a rollback plan in case of issues
5. **Application Impact**: Assess the impact of upgrades on applications

### Control Plane Upgrade

Control plane upgrade using kubeadm:

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

Worker node upgrade process:

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

Verify cluster status after upgrade:

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

Kubernetes cluster backup and recovery is an important part of disaster recovery planning.

The following diagram shows the Kubernetes cluster backup and recovery process:

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

etcd stores all state information for the Kubernetes cluster, so regular backups are important:

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

Restore from etcd snapshot:

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

Backup Kubernetes resources as YAML files:

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

Automate backup tasks with CronJob:

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

Effective monitoring and logging is a core element of cluster administration.

The following diagram shows the Kubernetes cluster monitoring and logging architecture:

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

Tools for Kubernetes cluster monitoring:

1. **Prometheus**: Metric collection and storage
2. **Grafana**: Metric visualization
3. **Alertmanager**: Alert management
4. **kube-state-metrics**: Generate Kubernetes object metrics
5. **metrics-server**: Provide resource usage metrics

#### Prometheus and Grafana Installation

Install Prometheus and Grafana using Helm:

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

Key metrics to monitor:

1. **Node Metrics**: CPU, memory, disk, network usage
2. **Pod Metrics**: CPU, memory usage, restart count
3. **Container Metrics**: CPU, memory usage, filesystem usage
4. **API Server Metrics**: Request latency, request count, error rate
5. **etcd Metrics**: Disk I/O, leader changes, commit latency

### Logging Tools

Tools for Kubernetes cluster logging:

1. **Elasticsearch**: Log storage and search
2. **Fluentd/Fluent Bit**: Log collection and forwarding
3. **Kibana**: Log visualization
4. **Loki**: Log aggregation system
5. **Grafana**: Log visualization

#### EFK (Elasticsearch, Fluentd, Kibana) Stack Installation

Install EFK stack using Helm:

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

Fluentd configuration example:

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

Kubernetes cluster troubleshooting is an important part of cluster administration.

### Pod Troubleshooting

Commands for pod troubleshooting:

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

Commands for node troubleshooting:

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

Commands for networking troubleshooting:

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

Commands for control plane troubleshooting:

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

Amazon EKS is a managed Kubernetes service that automates many aspects of cluster administration.

The following diagram shows the Amazon EKS cluster architecture and management components:

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

EKS cluster configuration management:

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

EKS node group management:

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

EKS add-on management:

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

EKS cluster upgrade process:

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

EKS cluster monitoring tools:

1. **Amazon CloudWatch**: Metrics, logs, alerts
2. **AWS CloudTrail**: API call logging
3. **Amazon Managed Grafana**: Metric visualization
4. **Amazon Managed Service for Prometheus**: Metric collection and storage

Enable CloudWatch Container Insights:

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## Cluster Administration Best Practices

Best practices for Kubernetes and EKS cluster administration:

### Cluster Configuration Best Practices

1. **Infrastructure as Code (IaC)**: Manage cluster configuration using Terraform, AWS CDK, eksctl, etc.
2. **Version Control**: Store cluster configuration in version control systems
3. **Multiple Environments**: Separate development, staging, and production environments
4. **Network Separation**: Configure appropriate network separation and security groups
5. **Least Privilege Principle**: Grant only the minimum necessary permissions

### Operations Best Practices

1. **Regular Backups**: Regular backup of etcd and important resources
2. **Monitoring and Alerting**: Build comprehensive monitoring and alerting systems
3. **Centralized Logging**: Centralize and analyze logs
4. **Automation**: Automate repetitive tasks
5. **Disaster Recovery Planning**: Establish and test clear disaster recovery plans

### Security Best Practices

1. **Regular Updates**: Regular updates of cluster and nodes
2. **Network Policies**: Configure appropriate network policies
3. **Encryption**: Encrypt data at rest and in transit
4. **Security Context**: Configure appropriate security contexts
5. **Image Scanning**: Scan container images for vulnerabilities

### Resource Management Best Practices

1. **Resource Requests and Limits**: Set appropriate resource requests and limits for all pods
2. **Namespace Separation**: Separate workloads by namespace
3. **Resource Quotas**: Set resource quotas per namespace
4. **HPA and VPA**: Configure autoscaling
5. **Node Affinity and Taints**: Optimize workload placement

### EKS-Specific Best Practices

1. **Managed Node Groups**: Use managed node groups when possible
2. **Fargate**: Use Fargate for serverless workloads
3. **EKS Add-ons**: Use official EKS add-ons
4. **IAM Roles for Service Accounts (IRSA)**: Manage IAM permissions per pod
5. **VPC CNI Customization**: Configure VPC CNI according to networking requirements

## Conclusion

Kubernetes cluster administration plays an important role in maintaining cluster stability, security, and performance. This chapter covered various aspects of cluster administration including cluster component management, resource management, networking, authentication and authorization management, upgrades, backup and recovery, monitoring and logging, and troubleshooting.

Using Amazon EKS reduces the complexity of Kubernetes control plane management and simplifies cluster administration through integration with AWS services. However, understanding fundamental Kubernetes concepts and best practices is still important for effective cluster management.

Cluster administration is an ongoing process that must be continuously adjusted according to cluster requirements and workload characteristics. It is important to use monitoring tools to track cluster status, minimize repetitive tasks through automation, and follow best practices to maintain cluster stability and security.

## Cluster Networking

Kubernetes cluster networking manages pod-to-pod communication, service discovery, and external access.

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

CNI (Container Network Interface) plugins handle networking for Kubernetes clusters.

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

Kubernetes authentication and authorization management are core elements of cluster security. RBAC (Role-Based Access Control) is used to manage permissions for users and service accounts.

### Authentication Methods

Kubernetes supports various authentication methods:

1. **X.509 Certificates**: Authentication using client certificates
2. **Service Account Tokens**: Used for API server access within pods
3. **OpenID Connect (OIDC)**: Integration with external identity providers
4. **Webhook Token Authentication**: Integration with external authentication services
5. **Authentication Proxy**: Authentication through proxy

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

Kubernetes cluster upgrades are necessary to apply new features, security patches, and bug fixes. Upgrades must be carefully planned and executed.

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

Kubernetes cluster backup and recovery is an important part of disaster recovery planning. Main backup targets are the etcd database, persistent volume data, and Kubernetes resource definitions.

### etcd Backup and Recovery

etcd is a core component that stores all state information for the cluster.

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

Velero is a tool for backing up and recovering Kubernetes cluster resources and persistent volumes.

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

Effective cluster management requires a comprehensive monitoring and logging system. This allows problems to be detected and resolved early.

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

You can configure alerts using Prometheus Alertmanager:

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

Kubernetes cluster troubleshooting is an important skill for system administrators and operators. A systematic approach is required for effective troubleshooting.

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

Amazon EKS (Elastic Kubernetes Service) is a managed Kubernetes service on AWS where AWS manages the control plane. However, management of nodes, networking, security, etc. is the user's responsibility.

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

Best practices for effective Kubernetes cluster management are important for ensuring stability, security, and performance.

### Cluster Setup Best Practices

1. **Multi-Availability Zone Configuration**: Distribute nodes across multiple availability zones for high availability
2. **Appropriate Sizing**: Select node types and counts appropriate for workloads
3. **Autoscaling Configuration**: Enable cluster autoscaler and horizontal pod autoscaler
4. **Apply Network Policies**: Start with a default deny policy and allow only necessary communication
5. **Set Resource Quotas**: Set resource limits per namespace

### Operations Best Practices

1. **Use Declarative Configuration**: Define all resources as YAML files and version control them
2. **Adopt GitOps**: Use Git as the single source of truth and build automated deployment pipelines
3. **Regular Backups**: Regular backup of etcd data and persistent volume data
4. **Monitoring and Alerting**: Build comprehensive monitoring systems and set alerts for key metrics
5. **Centralized Logging**: Collect all logs to a central logging system for easy analysis

### Security Best Practices

1. **Least Privilege Principle**: Grant only the minimum necessary permissions using RBAC
2. **Network Segmentation**: Limit pod-to-pod communication using network policies
3. **Image Scanning**: Implement container image scanning for vulnerability detection
4. **Secret Management**: Use external secret management tools (e.g., AWS Secrets Manager, HashiCorp Vault)
5. **Regular Security Audits**: Conduct regular audits of cluster configuration and permissions

### Upgrade Best Practices

1. **Gradual Upgrades**: Upgrade gradually rather than all at once
2. **Test Environment First**: Verify upgrades in test environments before production
3. **Create Backups**: Perform full backups before upgrades
4. **Rollback Plan**: Develop a plan to rollback to previous versions in case of issues
5. **Set Upgrade Windows**: Perform upgrades during low-usage periods

### Cost Optimization Best Practices

1. **Select Appropriate Node Sizes**: Select optimal node types for workloads
2. **Utilize Spot Instances**: Use spot instances for non-critical workloads
3. **Configure Autoscaling**: Configure automatic scale up and down based on demand
4. **Optimize Resource Requests and Limits**: Set resource requests and limits based on actual usage
5. **Identify Idle Resources**: Regularly identify and remove idle resources

### Documentation Best Practices

1. **Document Architecture**: Document cluster architecture, networking, and security settings
2. **Document Operations Procedures**: Document common operations tasks, troubleshooting procedures, and emergency response plans
3. **Change Management**: Record and track all cluster changes
4. **Create Runbooks**: Provide step-by-step guides for common scenarios
5. **Knowledge Sharing**: Conduct regular knowledge sharing and training sessions within the team
## Conclusion

Kubernetes cluster administration is a complex task that includes various aspects. A systematic approach is required from cluster setup to operation, monitoring, troubleshooting, and upgrades.

For effective cluster administration, focus on the following key areas:

1. **Cluster Component Management**: Stable operation of control plane and node components
2. **Resource Management**: Efficient resource allocation and usage
3. **Networking**: Secure and efficient network configuration
4. **Security**: Appropriate authentication and authorization management
5. **Backup and Recovery**: Data loss prevention and disaster recovery planning
6. **Monitoring and Logging**: Cluster status and performance monitoring
7. **Troubleshooting**: Systematic troubleshooting approach

When using managed Kubernetes services like Amazon EKS, it is important to understand the shared responsibility model between the service provider and the user. While AWS manages the control plane, management of nodes, networking, security, etc. is still the user's responsibility.

By following best practices and utilizing appropriate tools, you can operate a stable, secure, and efficient Kubernetes cluster. Continuous learning and improvement to enhance cluster management capabilities is important.

---

> **References**:
> - [Kubernetes Official Documentation: Cluster Administration](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes Best Practices: Cluster Administration](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd Documentation: Backup and Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

## Quiz

To test what you learned in this chapter, try the [Cluster Administration Quiz](../quizzes/core/09-cluster-administration-quiz.md).
