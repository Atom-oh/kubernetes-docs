# Kubernetes Cluster Administration

> **Supported Versions**: Kubernetes 1.34 (Released 2025-11-24)
> **最后更新**: February 23, 2026

Kubernetes cluster（集群）管理是一项重要任务，涵盖 cluster 设置、维护、监控、故障排除和升级。在本章中，我们将探讨 Kubernetes cluster 管理的各个方面，以及在 Amazon EKS 中进行 cluster 管理的最佳实践。

## Core Concepts

- **Cluster Lifecycle Management**: 从 cluster 创建到退役的整个过程
- **Control Plane Management**: 管理 API server、scheduler 和 controller manager 等核心组件
- **Node Management**: 添加、移除和维护 worker nodes
- **Resource Allocation**: 设置 CPU、内存、存储等资源分配和限制
- **Upgrade Strategy**: 用于最大限度减少停机时间的 cluster 和应用程序升级策略

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

cluster 管理需要以下工具：

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

Kubernetes cluster 管理是管理 cluster 整个生命周期的过程。这包括以下主要领域：

1. **Cluster Setup and Configuration**: cluster 创建、Node 添加、网络设置、存储配置等
2. **Operations Management**: 资源监控、性能优化、容量规划、故障排除
3. **Security Management**: 认证、授权、网络策略、security contexts 等
4. **Upgrades and Patches**: cluster 版本升级、安全补丁应用
5. **Backup and Recovery**: cluster 数据备份、灾难恢复规划

下图展示了 Kubernetes cluster 管理的主要领域和相关工具：

## Cluster Component Management

Kubernetes cluster 由 control plane components 和 node components 组成。管理每个组件对于 cluster 的稳定性和性能至关重要。

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

API server 是 control plane 的核心组件，用于公开 Kubernetes API。

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### etcd Management

etcd 是一个分布式 key-value store，用于存储 Kubernetes 的所有 cluster 数据。

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

Nodes 是运行容器化应用程序的 worker machines。

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

Kubernetes cluster 管理可使用多种工具：

1. **kubectl**: 与 Kubernetes clusters 交互的命令行工具
2. **kubeadm**: 用于创建和管理 Kubernetes clusters 的工具
3. **kops**: 用于创建、升级和管理 Kubernetes clusters 的工具
4. **eksctl**: 用于创建和管理 Amazon EKS clusters 的工具
5. **Helm**: Kubernetes 应用程序包管理器
6. **Kubernetes Dashboard**: 基于 Web 的 Kubernetes 用户界面
7. **Prometheus & Grafana**: 监控和告警工具
8. **Fluentd & Elasticsearch**: 日志工具

## Cluster Component Management

Kubernetes cluster 由多个组件组成，有效管理这些组件非常重要。

### Control Plane Components

Control plane components 管理 cluster 的整体状态：

1. **kube-apiserver**: 公开 Kubernetes API 的组件
2. **etcd**: 存储 cluster 数据的 key-value store
3. **kube-scheduler**: 将 pods 调度到 nodes 的组件
4. **kube-controller-manager**: 运行 controllers 的组件
5. **cloud-controller-manager**: 与 cloud providers 交互的组件

下图展示了 Kubernetes control plane components 及其交互：

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

监控 control plane components 的状态非常重要：

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Control Plane Component Configuration

管理 control plane component 配置的方法：

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

Node components 在每个 node 上运行并管理 pods：

1. **kubelet**: 在每个 node 上运行的 agent，确保 pods 和 containers 正在运行
2. **kube-proxy**: 维护网络规则并处理连接转发
3. **Container Runtime**: 运行 containers 的软件（Docker、containerd、CRI-O 等）

#### Node Management

Node 管理的关键命令：

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

用于 node 故障排除的命令：

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

在 Kubernetes cluster 中有效管理资源对于维持 cluster 稳定性和性能非常重要。

### Resource Quotas

Resource quotas 限制每个 namespace 的资源使用量：

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

在上述示例中，`dev` namespace 最多可以拥有 10 个 pods、1 CPU 和 1Gi 内存请求，以及 2 CPU 和 2Gi 内存限制。

### Limit Ranges

Limit ranges 为 namespace 内的单个资源设置默认值和限制：

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

在上述示例中，`dev` namespace 中的所有 containers 都具有 500m CPU 和 512Mi 内存的默认限制、200m CPU 和 256Mi 内存的默认请求、1 CPU 和 1Gi 内存的最大值，以及 100m CPU 和 128Mi 内存的最小值。

### Horizontal Pod Autoscaler (HPA)

HPA 会根据 CPU 使用率或自定义 metrics 自动调整 pods 数量：

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

在上述示例中，当 CPU 利用率超过 80% 时，`frontend` deployment 会自动扩容；当低于 80% 时会缩容。它维持最少 2 个、最多 10 个 replicas。

### Vertical Pod Autoscaler (VPA)

VPA 会自动调整 pod CPU 和内存请求：

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

在上述示例中，`frontend` deployment 中 pods 的 CPU 和内存请求会根据实际资源使用情况自动调整。
## Cluster Networking

Kubernetes cluster networking 管理 pods、services 和 nodes 之间的通信。

### Cluster Network Model

Kubernetes 网络模型的基本要求：

1. 所有 pods 都可以在没有 NAT 的情况下与所有其他 pods 通信
2. Node agents（kubelet）可以与该 node 上的所有 pods 通信
3. 在 NAT 模式下运行的 pods 可以与外部通信

下图展示了 Kubernetes networking components 和通信流：

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

Kubernetes 通过 CNI plugins 实现网络。常见 CNI plugins：

1. **Calico**: 具有增强网络策略和安全功能的 CNI
2. **Flannel**: 提供简单的 overlay networking
3. **Cilium**: 基于 eBPF 的网络和安全解决方案
4. **AWS VPC CNI**: 与 AWS VPC 集成的 CNI
5. **Weave Net**: 多主机 container networking 解决方案

#### CNI Plugin Installation and Configuration

CNI plugin 安装示例（Calico）：

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Service Networking

Kubernetes services 为 pod sets 提供稳定 endpoints：

1. **ClusterIP**: 只能在 cluster 内访问的 Service
2. **NodePort**: 可通过所有 nodes 上的特定端口访问的 Service
3. **LoadBalancer**: 可通过外部 load balancer 访问的 Service
4. **ExternalName**: 为外部 services 提供 CNAME 记录

#### Service CIDR Configuration

Service CIDR 定义 service IP 地址范围：

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS Management

CoreDNS 为 Kubernetes 提供 DNS 服务：

```bash
# Check CoreDNS status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS configuration
kubectl get configmap -n kube-system coredns -o yaml
```

CoreDNS 配置示例：

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

Network policies 控制 pods 之间的通信：

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

在上述示例中，带有 `role=db` label 的 pods 只允许来自带有 `role=frontend` label 的 pods 的 TCP 端口 3306 入站流量，并允许到带有 `role=monitoring` label 的 pods 的 TCP 端口 9090 出站流量。

## Authentication and Authorization Management

Kubernetes authentication 和 authorization 管理是 cluster 安全的核心要素。

下图展示了 Kubernetes authentication 和 authorization 流程：

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

Kubernetes 支持多种 authentication 方法：

1. **X.509 Certificates**: 使用客户端 certificates 进行 authentication
2. **Service Account Tokens**: 与 service accounts 关联的 JWT tokens
3. **OpenID Connect (OIDC)**: 通过外部 identity providers 进行 authentication
4. **Webhook Token Authentication**: 通过外部 services 进行 token 验证
5. **Authentication Proxy**: 通过 authentication proxy 处理请求

#### X.509 Certificate Management

X.509 certificate 创建和管理：

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

OIDC authentication 配置示例：

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### Authorization

Kubernetes 支持多种 authorization 模式：

1. **RBAC (Role-Based Access Control)**: 基于角色的访问控制
2. **ABAC (Attribute-Based Access Control)**: 基于属性的访问控制
3. **Node**: Node authorization
4. **Webhook**: 通过外部 services 进行 authorization

#### RBAC Configuration

RBAC 是最常见的 authorization 机制：

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

在上述示例中，`user` 有权限查看 `default` namespace 中的 pods。

#### ClusterRole and ClusterRoleBinding

管理 cluster-wide resources 的权限：

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

在上述示例中，`user` 有权限查看 cluster 中的所有 nodes。

### Service Account Management

Service accounts 由 pods 用于与 API server 通信：

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

Security context 为 pods 和 containers 定义权限和访问控制：

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

在上述示例中，该 pod 使用 UID 1000 和 GID 3000 运行，container 不能提升权限，已移除所有 Linux capabilities，并且 root filesystem 以只读方式挂载。

## Cluster Upgrades

Kubernetes cluster 升级对于应用新功能、性能改进和安全补丁是必要的。

下图展示了 Kubernetes cluster 升级过程：

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

规划 cluster 升级时的注意事项：

1. **Version Compatibility**: 检查 Kubernetes 版本之间的兼容性
2. **Upgrade Path**: 检查受支持的升级路径
3. **Downtime**: 规划升级期间预期的停机时间
4. **Rollback Plan**: 制定发生问题时的 rollback plan
5. **Application Impact**: 评估升级对应用程序的影响

### Control Plane Upgrade

使用 kubeadm 升级 control plane：

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

Worker node 升级过程：

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

升级后验证 cluster 状态：

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

Kubernetes cluster backup and recovery 是灾难恢复规划的重要组成部分。

下图展示了 Kubernetes cluster backup and recovery 过程：

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

etcd 存储 Kubernetes cluster 的所有状态信息，因此定期备份非常重要：

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

从 etcd snapshot 恢复：

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

将 Kubernetes resources 备份为 YAML 文件：

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

使用 CronJob 自动执行备份任务：

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

有效的 monitoring and logging 是 cluster 管理的核心要素。

下图展示了 Kubernetes cluster monitoring and logging 架构：

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

用于 Kubernetes cluster monitoring 的工具：

1. **Prometheus**: Metric 收集和存储
2. **Grafana**: Metric 可视化
3. **Alertmanager**: Alert 管理
4. **kube-state-metrics**: 生成 Kubernetes object metrics
5. **metrics-server**: 提供资源使用 metrics

#### Prometheus and Grafana Installation

使用 Helm 安装 Prometheus 和 Grafana：

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

需要监控的关键 metrics：

1. **Node Metrics**: CPU、内存、磁盘、网络使用情况
2. **Pod Metrics**: CPU、内存使用情况、重启次数
3. **Container Metrics**: CPU、内存使用情况、filesystem 使用情况
4. **API Server Metrics**: 请求延迟、请求数量、错误率
5. **etcd Metrics**: 磁盘 I/O、leader 变更、commit 延迟

### Logging Tools

用于 Kubernetes cluster logging 的工具：

1. **Elasticsearch**: 日志存储和搜索
2. **Fluentd/Fluent Bit**: 日志收集和转发
3. **Kibana**: 日志可视化
4. **Loki**: 日志聚合系统
5. **Grafana**: 日志可视化

#### EFK (Elasticsearch, Fluentd, Kibana) Stack Installation

使用 Helm 安装 EFK stack：

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

Fluentd 配置示例：

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

Kubernetes cluster troubleshooting 是 cluster 管理的重要组成部分。

### Pod Troubleshooting

用于 pod 故障排除的命令：

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

用于 node 故障排除的命令：

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

用于 networking 故障排除的命令：

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

用于 control plane 故障排除的命令：

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

Amazon EKS 是一种 managed Kubernetes service，可自动执行 cluster 管理的许多方面。

下图展示了 Amazon EKS cluster 架构和管理组件：

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

EKS cluster 配置管理：

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

EKS node group 管理：

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

EKS add-on 管理：

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

EKS cluster 升级过程：

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

EKS cluster monitoring 工具：

1. **Amazon CloudWatch**: Metrics、logs、alerts
2. **AWS CloudTrail**: API call logging
3. **Amazon Managed Grafana**: Metric 可视化
4. **Amazon Managed Service for Prometheus**: Metric 收集和存储

启用 CloudWatch Container Insights：

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## Cluster Administration Best Practices

Kubernetes 和 EKS cluster 管理的最佳实践：

### Cluster Configuration Best Practices

1. **Infrastructure as Code (IaC)**: 使用 Terraform、AWS CDK、eksctl 等管理 cluster 配置
2. **Version Control**: 将 cluster 配置存储在版本控制系统中
3. **Multiple Environments**: 分离开发、staging 和生产环境
4. **Network Separation**: 配置适当的网络隔离和 security groups
5. **Least Privilege Principle**: 仅授予最低必要权限

### Operations Best Practices

1. **Regular Backups**: 定期备份 etcd 和重要 resources
2. **Monitoring and Alerting**: 构建全面的 monitoring and alerting systems
3. **Centralized Logging**: 集中收集并分析 logs
4. **Automation**: 自动化重复性任务
5. **Disaster Recovery Planning**: 建立并测试清晰的灾难恢复计划

### Security Best Practices

1. **Regular Updates**: 定期更新 cluster 和 nodes
2. **Network Policies**: 配置适当的 network policies
3. **Encryption**: 对静态数据和传输中数据进行加密
4. **Security Context**: 配置适当的 security contexts
5. **Image Scanning**: 扫描 container images 以发现漏洞

### Resource Management Best Practices

1. **Resource Requests and Limits**: 为所有 pods 设置适当的 resource requests 和 limits
2. **Namespace Separation**: 按 namespace 分离 workloads
3. **Resource Quotas**: 为每个 namespace 设置 resource quotas
4. **HPA and VPA**: 配置 autoscaling
5. **Node Affinity and Taints**: 优化 workload 放置

### EKS-Specific Best Practices

1. **Managed Node Groups**: 尽可能使用 managed node groups
2. **Fargate**: 将 Fargate 用于 serverless workloads
3. **EKS Add-ons**: 使用官方 EKS add-ons
4. **IAM Roles for Service Accounts (IRSA)**: 按 pod 管理 IAM permissions
5. **VPC CNI Customization**: 根据 networking requirements 配置 VPC CNI

## Conclusion

Kubernetes cluster 管理在维持 cluster 稳定性、安全性和性能方面发挥重要作用。本章介绍了 cluster 管理的多个方面，包括 cluster component management、resource management、networking、authentication and authorization management、upgrades、backup and recovery、monitoring and logging，以及 troubleshooting。

使用 Amazon EKS 可降低 Kubernetes control plane 管理的复杂性，并通过与 AWS services 集成来简化 cluster 管理。但是，理解基础 Kubernetes 概念和最佳实践对于有效的 cluster 管理仍然很重要。

Cluster 管理是一个持续过程，必须根据 cluster requirements 和 workload characteristics 不断调整。重要的是使用 monitoring tools 跟踪 cluster 状态，通过 automation 最大限度减少重复性任务，并遵循最佳实践来维持 cluster 稳定性和安全性。

## Cluster Networking

Kubernetes cluster networking 管理 pod-to-pod 通信、service discovery 和外部访问。

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

CNI (Container Network Interface) plugins 处理 Kubernetes clusters 的网络。

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
| **Calico** | BGP | Yes | High | 擅长 network policies，基于 routing |
| **Flannel** | VXLAN/host-gateway | No | Medium | 设置简单，功能有限 |
| **Cilium** | eBPF | Yes | Very High | L3-L7 policies，高性能 |
| **Weave Net** | VXLAN | Yes | Medium | 支持加密、multi-cluster |
| **AWS VPC CNI** | AWS VPC | No | High | 针对 AWS EKS 优化 |

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

Kubernetes authentication 和 authorization 管理是 cluster 安全的核心要素。RBAC (Role-Based Access Control) 用于管理 users 和 service accounts 的权限。

### Authentication Methods

Kubernetes 支持多种 authentication 方法：

1. **X.509 Certificates**: 使用 client certificates 进行 authentication
2. **Service Account Tokens**: 用于 pods 内访问 API server
3. **OpenID Connect (OIDC)**: 与外部 identity providers 集成
4. **Webhook Token Authentication**: 与外部 authentication services 集成
5. **Authentication Proxy**: 通过 proxy 进行 authentication

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

Kubernetes cluster 升级对于应用新功能、安全补丁和 bug fixes 是必要的。升级必须经过仔细规划和执行。

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
| **In-place Upgrade** | 直接升级现有 cluster | 资源高效、流程简单 | rollback 复杂、可能停机 | 开发、测试环境 |
| **Blue/Green Deployment** | 创建新版本 cluster 并切换 | rollback 安全、可验证 | 资源重复、成本增加 | 生产环境 |
| **Canary Deployment** | 仅将部分 workloads 移动到新 cluster | 渐进验证、风险降低 | 管理复杂、双环境运行 | 关键生产环境 |

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

Kubernetes cluster backup and recovery 是灾难恢复规划的重要组成部分。主要备份目标是 etcd database、persistent volume data 和 Kubernetes resource definitions。

### etcd Backup and Recovery

etcd 是存储 cluster 所有状态信息的核心组件。

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

Velero 是一个用于备份和恢复 Kubernetes cluster resources 与 persistent volumes 的工具。

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
| **etcd Snapshot** | Cluster state | 内置功能、完整状态保留 | 不包含 volume data、手动流程 | Medium |
| **Resource YAML Backup** | Kubernetes objects | 实现简单、可选择性恢复 | 不包含 volume data、关系复杂 | Slow |
| **Velero** | Resources and volumes | 自动化、调度、volume snapshots | 需要安装额外工具 | Fast |
| **Cloud Provider Snapshots** | Entire cluster | 完整恢复、cloud 集成 | 依赖 cloud、成本 | Very Fast |
## Monitoring and Logging

有效的 cluster 管理需要全面的 monitoring and logging system。这使问题能够被及早发现并解决。

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
| **Node Metrics** | Node 级资源使用情况 | CPU、内存、磁盘、网络 | node-exporter, Prometheus |
| **Pod Metrics** | Container 资源使用情况 | CPU、内存使用情况、limits | cAdvisor, Prometheus |
| **Cluster Metrics** | Cluster 状态和 resources | Pod 数量、node 状态、events | kube-state-metrics |
| **Application Metrics** | 自定义应用程序 metrics | 请求数量、延迟、错误率 | Prometheus client libraries |

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

可以使用 Prometheus Alertmanager 配置 alerts：

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

Kubernetes cluster troubleshooting 是系统管理员和运维人员的一项重要技能。有效的故障排除需要系统化方法。

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
| **Pod Not Starting** | Pod 处于 Pending 或 ContainerCreating 状态 | `kubectl describe pod <pod-name>` | 检查资源约束、image 可用性、volume mounts |
| **Service Connection Issues** | 无法通过 service 访问 pods | `kubectl describe svc <service-name>`, `kubectl get endpoints <service-name>` | 检查 label selectors、pod 状态、network policies |
| **Node Issues** | Node 处于 NotReady 状态 | `kubectl describe node <node-name>`, `kubectl get events` | 检查 kubelet 状态、系统资源、网络连接 |
| **DNS Issues** | 无法通过 service name 连接 | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | 检查 CoreDNS pods、kube-dns service、network policies |
| **Authentication Issues** | API server 访问被拒绝 | `kubectl auth can-i <verb> <resource>` | 检查 RBAC 设置、certificate 有效性、service account |

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

Amazon EKS (Elastic Kubernetes Service) 是 AWS 上的 managed Kubernetes service，其中 AWS 管理 control plane。但是，nodes、networking、security 等的管理仍由用户负责。

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

有效 Kubernetes cluster 管理的最佳实践对于确保稳定性、安全性和性能非常重要。

### Cluster Setup Best Practices

1. **Multi-Availability Zone Configuration**: 将 nodes 分布到多个 availability zones 以实现高可用性
2. **Appropriate Sizing**: 选择适合 workloads 的 node 类型和数量
3. **Autoscaling Configuration**: 启用 cluster autoscaler 和 horizontal pod autoscaler
4. **Apply Network Policies**: 从默认拒绝策略开始，仅允许必要通信
5. **Set Resource Quotas**: 为每个 namespace 设置资源限制

### Operations Best Practices

1. **Use Declarative Configuration**: 将所有 resources 定义为 YAML 文件并进行版本控制
2. **Adopt GitOps**: 使用 Git 作为 single source of truth，并构建自动化部署流水线
3. **Regular Backups**: 定期备份 etcd data 和 persistent volume data
4. **Monitoring and Alerting**: 构建全面的 monitoring systems，并为关键 metrics 设置 alerts
5. **Centralized Logging**: 将所有 logs 收集到中央 logging system 中以便分析

### Security Best Practices

1. **Least Privilege Principle**: 使用 RBAC 仅授予最低必要权限
2. **Network Segmentation**: 使用 network policies 限制 pod-to-pod 通信
3. **Image Scanning**: 实施 container image scanning 以检测漏洞
4. **Secret Management**: 使用外部 secret management tools（例如 AWS Secrets Manager、HashiCorp Vault）
5. **Regular Security Audits**: 定期审计 cluster 配置和权限

### Upgrade Best Practices

1. **Gradual Upgrades**: 逐步升级，而不是一次性全部升级
2. **Test Environment First**: 在生产环境之前先在测试环境中验证升级
3. **Create Backups**: 升级前执行完整备份
4. **Rollback Plan**: 制定发生问题时回滚到先前版本的计划
5. **Set Upgrade Windows**: 在低使用量时段执行升级

### Cost Optimization Best Practices

1. **Select Appropriate Node Sizes**: 为 workloads 选择最佳 node 类型
2. **Utilize Spot Instances**: 对非关键 workloads 使用 spot instances
3. **Configure Autoscaling**: 根据需求配置自动扩缩容
4. **Optimize Resource Requests and Limits**: 根据实际使用情况设置 resource requests 和 limits
5. **Identify Idle Resources**: 定期识别并删除闲置 resources

### Documentation Best Practices

1. **Document Architecture**: 记录 cluster architecture、networking 和 security settings
2. **Document Operations Procedures**: 记录常见运维任务、故障排除流程和应急响应计划
3. **Change Management**: 记录并跟踪所有 cluster 变更
4. **Create Runbooks**: 为常见场景提供分步指南
5. **Knowledge Sharing**: 在团队内定期开展知识分享和培训
## Conclusion

Kubernetes cluster 管理是一项复杂任务，包含多个方面。从 cluster 设置到运行、监控、故障排除和升级，都需要系统化方法。

为了有效进行 cluster 管理，请重点关注以下关键领域：

1. **Cluster Component Management**: Control plane 和 node components 的稳定运行
2. **Resource Management**: 高效资源分配和使用
3. **Networking**: 安全且高效的网络配置
4. **Security**: 适当的 authentication 和 authorization 管理
5. **Backup and Recovery**: 数据丢失预防和灾难恢复规划
6. **Monitoring and Logging**: Cluster 状态和性能监控
7. **Troubleshooting**: 系统化故障排除方法

使用 Amazon EKS 这类 managed Kubernetes services 时，理解 service provider 和 user 之间的 shared responsibility model 非常重要。虽然 AWS 管理 control plane，但 nodes、networking、security 等的管理仍然是用户的责任。

通过遵循最佳实践并使用适当工具，你可以运行稳定、安全且高效的 Kubernetes cluster。持续学习和改进以提升 cluster 管理能力非常重要。

---

> **References**:
> - [Kubernetes Official Documentation: Cluster Administration](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes Best Practices: Cluster Administration](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd Documentation: Backup and Recovery](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

## Quiz

要测试你在本章学到的内容，请尝试 [Cluster Administration Quiz](../quizzes/core/09-cluster-administration-quiz.md)。
