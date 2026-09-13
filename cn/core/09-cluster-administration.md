# Kubernetes 集群管理

> **支持的版本**: Kubernetes 1.34 (Released 2025-11-24)
> **最后更新**: February 23, 2026

Kubernetes 集群管理是一项重要工作，涵盖集群设置、维护、监控、故障排除和升级。本章将探讨 Kubernetes 集群管理的各个方面，以及在 Amazon EKS 中进行集群管理的最佳实践。

## 核心概念

- **集群生命周期管理**: 从集群创建到退役的整个过程
- **Control Plane 管理**: 管理 API server、scheduler 和 controller manager 等核心组件
- **Node 管理**: 添加、移除和维护 worker node
- **资源分配**: 为 CPU、内存、存储等设置资源分配和限制
- **升级策略**: 尽量减少停机时间的集群和应用程序升级策略

## 目录
1. [集群管理概述](#cluster-administration-overview)
2. [集群组件管理](#cluster-component-management)
3. [资源管理](#resource-management)
4. [集群网络](#cluster-networking)
5. [身份验证和授权管理](#authentication-and-authorization-management)
6. [集群升级](#cluster-upgrades)
7. [备份和恢复](#backup-and-recovery)
8. [监控和日志](#monitoring-and-logging)
9. [故障排除](#troubleshooting)
10. [Amazon EKS 集群管理](#amazon-eks-cluster-administration)
11. [集群管理最佳实践](#cluster-administration-best-practices)
12. [结论](#conclusion)

## 环境设置

集群管理需要以下工具：

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

## 集群管理概述

Kubernetes 集群管理是管理集群整个生命周期的过程，包含以下主要领域：

1. **集群设置和配置**: 集群创建、Node 添加、网络设置、存储配置等
2. **运维管理**: 资源监控、性能优化、容量规划、故障排除
3. **安全管理**: 身份验证、授权、网络策略、安全上下文等
4. **升级和补丁**: 集群版本升级、安全补丁应用
5. **备份和恢复**: 集群数据备份、灾难恢复规划

下图展示了 Kubernetes 集群管理的主要领域和相关工具：

## 集群组件管理

Kubernetes 集群由 Control Plane 组件和 Node 组件组成。管理每个组件对于集群稳定性和性能至关重要。

### Control Plane 组件管理

![展示 Kubernetes Control Plane 分支至五个组件（API server、etcd、scheduler、controller manager 和 cloud controller manager）的树状图；每个组件均对应其负责的运维事项：身份验证和授权、数据备份、调度策略、controller 状态监控以及云资源管理。](../.gitbook/assets/en-core-09-cluster-administration-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-0.html)

#### API Server 管理

API server 是暴露 Kubernetes API 的 Control Plane 核心组件。

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/healthz'
```

#### etcd 管理

etcd 是一个分布式键值存储，用于存储 Kubernetes 的所有集群数据。

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

### Node 管理

Node 是运行容器化应用程序的 worker machine。

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

### 组件状态监控

```bash
# Check control plane component status
kubectl get componentstatuses

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

![展示集群管理员五个职责领域及各领域所用工具的图表。](../.gitbook/assets/en-core-09-cluster-administration-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-1.html)

### 集群管理工具

有多种工具可用于 Kubernetes 集群管理：

1. **kubectl**: 与 Kubernetes 集群交互的命令行工具
2. **kubeadm**: 创建和管理 Kubernetes 集群的工具
3. **kops**: 创建、升级和管理 Kubernetes 集群的工具
4. **eksctl**: 创建和管理 Amazon EKS 集群的工具
5. **Helm**: Kubernetes 应用程序包管理器
6. **Kubernetes Dashboard**: 基于 Web 的 Kubernetes 用户界面
7. **Prometheus & Grafana**: 监控和告警工具
8. **Fluentd & Elasticsearch**: 日志工具

## 集群组件管理

Kubernetes 集群由多个组件构成，有效管理这些组件非常重要。

### Control Plane 组件

Control Plane 组件管理集群的整体状态：

1. **kube-apiserver**: 暴露 Kubernetes API 的组件
2. **etcd**: 存储集群数据的键值存储
3. **kube-scheduler**: 将 Pod 调度到 Node 的组件
4. **kube-controller-manager**: 运行 controller 的组件
5. **cloud-controller-manager**: 与云提供商交互的组件

下图展示了 Kubernetes Control Plane 组件及其交互方式：

![架构图展示 etcd、kube-scheduler、kube-controller-manager 和 cloud-controller-manager 与中央 kube-apiserver 双向通信；worker node 的 kubelet 也与 API server 双向通信，同时管理 kube-proxy 和 container runtime。](../.gitbook/assets/en-core-09-cluster-administration-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-2.html)

#### Control Plane 组件监控

监控 Control Plane 组件的状态十分重要：

```bash
# Check control plane component status
kubectl get componentstatuses

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -it -n kube-system etcd-<node-name> -- etcdctl endpoint health
```

#### Control Plane 组件配置

如何管理 Control Plane 组件配置：

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

### Node 组件

Node 组件运行在每个 Node 上并管理 Pod：

1. **kubelet**: 运行在每个 Node 上、确保 Pod 和容器正常运行的 agent
2. **kube-proxy**: 维护网络规则并处理连接转发
3. **Container Runtime**: 运行容器的软件（Docker、containerd、CRI-O 等）

#### Node 管理

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

#### Node 故障排除

用于 Node 故障排除的命令：

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

## 资源管理

在 Kubernetes 集群中有效管理资源，对于保持集群稳定性和性能十分重要。

### 资源配额

资源配额会限制每个 namespace 的资源使用量：

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

在上例中，`dev` namespace 最多可拥有 10 个 Pod、1 CPU 和 1Gi 内存 requests，以及 2 CPU 和 2Gi 内存 limits。

### Limit Range

Limit Range 为 namespace 内的单个资源设置默认值和限制：

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

在上例中，`dev` namespace 中的所有容器具有 500m CPU 和 512Mi 内存的默认 limits、200m CPU 和 256Mi 内存的默认 requests、1 CPU 和 1Gi 内存的最大值以及 100m CPU 和 128Mi 内存的最小值。

### Horizontal Pod Autoscaler (HPA)

HPA 会根据 CPU 使用率或自定义指标自动调整 Pod 数量：

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

在上例中，`frontend` Deployment 会在 CPU 利用率超过 80% 时自动扩容，低于 80% 时自动缩容。它保持最少 2 个、最多 10 个 replica。

### Vertical Pod Autoscaler (VPA)

VPA 会自动调整 Pod 的 CPU 和内存 requests：

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

在上例中，`frontend` Deployment 中 Pod 的 CPU 和内存 requests 会根据实际资源使用情况自动调整。
## 集群网络

Kubernetes 集群网络管理 Pod、Service 和 Node 之间的通信。

### 集群网络模型

Kubernetes 网络模型的基本要求：

1. 所有 Pod 无需 NAT 即可与其他所有 Pod 通信
2. Node agent（kubelet）可以与该 Node 上的所有 Pod 通信
3. 以 NAT 模式运行的 Pod 可以与外部通信

下图展示了 Kubernetes 网络组件和通信流：

![架构图展示客户端流量经由 Ingress 进入 Service，该 Service 在不同 Node 上的两个 Pod 之间进行负载均衡；这些 Pod 可相互通信并访问外部 Service。](../.gitbook/assets/en-core-09-cluster-administration-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-3.html)

### CNI (Container Network Interface) 插件

Kubernetes 通过 CNI 插件实现网络。常见的 CNI 插件：

1. **Calico**: 具有增强网络策略和安全功能的 CNI
2. **Flannel**: 提供简单的 overlay 网络
3. **Cilium**: 基于 eBPF 的网络和安全解决方案
4. **AWS VPC CNI**: 与 AWS VPC 集成的 CNI
5. **Weave Net**: 多主机容器网络解决方案

#### CNI 插件安装和配置

CNI 插件安装示例（Calico）：

```bash
# Install Calico
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Service 网络

Kubernetes Service 为 Pod 集合提供稳定的 endpoint：

1. **ClusterIP**: 仅可在集群内部访问的 Service
2. **NodePort**: 可通过所有 Node 上特定端口访问的 Service
3. **LoadBalancer**: 可通过外部 load balancer 访问的 Service
4. **ExternalName**: 为外部 Service 提供 CNAME record

#### Service CIDR 配置

Service CIDR 定义 Service IP 地址范围：

```bash
# Set service CIDR in kube-apiserver configuration
--service-cluster-ip-range=10.96.0.0/12
```

### CoreDNS 管理

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

### 网络策略

网络策略控制 Pod 之间的通信：

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

在上例中，带有 `role=db` 标签的 Pod 仅允许来自带有 `role=frontend` 标签的 Pod 的 TCP 端口 3306 入站流量，以及到带有 `role=monitoring` 标签的 Pod 的 TCP 端口 9090 出站流量。

## 身份验证和授权管理

Kubernetes 身份验证和授权管理是集群安全的核心要素。

下图展示了 Kubernetes 身份验证和授权流程：

![架构图展示一个请求在到达 API server 之前依次经过身份验证、授权和准入控制，并列出每个阶段支持的具体身份验证方法和授权模式。](../.gitbook/assets/en-core-09-cluster-administration-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-4.html)

### 身份验证

Kubernetes 支持多种身份验证方法：

1. **X.509 Certificates**: 使用客户端证书进行身份验证
2. **Service Account Tokens**: 与 Service Account 关联的 JWT token
3. **OpenID Connect (OIDC)**: 通过外部身份提供商进行身份验证
4. **Webhook Token Authentication**: 通过外部服务验证 token
5. **Authentication Proxy**: 通过身份验证代理处理请求

#### X.509 证书管理

X.509 证书的创建和管理：

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

#### OIDC 身份验证配置

OIDC 身份验证配置示例：

```bash
# Add OIDC flags to kube-apiserver configuration
--oidc-issuer-url=https://accounts.google.com
--oidc-client-id=kubernetes
--oidc-username-claim=email
--oidc-groups-claim=groups
```

### 授权

Kubernetes 支持多种授权模式：

1. **RBAC (Role-Based Access Control)**: 基于角色的访问控制
2. **ABAC (Attribute-Based Access Control)**: 基于属性的访问控制
3. **Node**: Node 授权
4. **Webhook**: 通过外部服务授权

#### RBAC 配置

RBAC 是最常见的授权机制：

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

在上例中，`user` 有权查看 `default` namespace 中的 Pod。

#### ClusterRole 和 ClusterRoleBinding

管理集群范围资源的权限：

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

在上例中，`user` 有权查看集群中的所有 Node。

### Service Account 管理

Service Account 供 Pod 与 API server 通信时使用：

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

### 安全上下文

安全上下文为 Pod 和容器定义权限及访问控制：

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

在上例中，Pod 以 UID 1000 和 GID 3000 运行，容器无法提升权限、移除了所有 Linux capability，且 root filesystem 以只读方式挂载。

## 集群升级

Kubernetes 集群升级是应用新功能、性能改进和安全补丁所必需的。

下图展示了 Kubernetes 集群升级流程：

![Kubernetes 集群升级的工作流图：规划并检查版本兼容性、备份 etcd、先升级第一个 Control Plane Node 并进行功能测试、升级其余 Control Plane 和 worker node，随后验证集群并完成升级；若验证发现问题，则通过回滚路径从备份恢复。](../.gitbook/assets/en-core-09-cluster-administration-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-5.html)

### 升级规划

规划集群升级时的注意事项：

1. **版本兼容性**: 检查 Kubernetes 版本之间的兼容性
2. **升级路径**: 检查受支持的升级路径
3. **停机时间**: 为升级期间的预期停机时间制定计划
4. **回滚计划**: 制定发生问题时的回滚计划
5. **应用程序影响**: 评估升级对应用程序的影响

### Control Plane 升级

使用 kubeadm 升级 Control Plane：

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

### Worker Node 升级

Worker Node 升级流程：

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

### 升级验证

升级后验证集群状态：

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
## 备份和恢复

Kubernetes 集群备份和恢复是灾难恢复规划的重要组成部分。

下图展示了 Kubernetes 集群备份和恢复流程：

![架构图展示定期的 etcd snapshot 和资源 YAML 备份均存入备份存储，之后在灾难恢复期间分别用于 etcd restore 和资源 restore。](../.gitbook/assets/en-core-09-cluster-administration-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-6.html)

### etcd 备份

etcd 存储 Kubernetes 集群的所有状态信息，因此定期备份十分重要：

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

### etcd 恢复

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

### 资源备份

将 Kubernetes 资源备份为 YAML 文件：

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

### 备份自动化

使用 CronJob 自动化备份任务：

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

## 监控和日志

有效的监控和日志记录是集群管理的核心要素。

下图展示了 Kubernetes 集群监控和日志架构：

![架构图展示 API server 和 Node 指标经由 kube-state-metrics 和 Node Exporter 流入 Prometheus，随后到达 Alertmanager 和 Grafana；Pod 日志则经由 Fluentd/Fluent Bit 流入 Elasticsearch（配合 Kibana）和 Loki，Loki 也向 Grafana 提供数据。](../.gitbook/assets/en-core-09-cluster-administration-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-7.html)

### 监控工具

用于 Kubernetes 集群监控的工具：

1. **Prometheus**: 指标收集和存储
2. **Grafana**: 指标可视化
3. **Alertmanager**: 告警管理
4. **kube-state-metrics**: 生成 Kubernetes 对象指标
5. **metrics-server**: 提供资源使用指标

#### Prometheus 和 Grafana 安装

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

#### 关键监控指标

要监控的关键指标：

1. **Node 指标**: CPU、内存、磁盘、网络使用情况
2. **Pod 指标**: CPU、内存使用情况、重启次数
3. **容器指标**: CPU、内存使用情况、文件系统使用情况
4. **API Server 指标**: 请求延迟、请求数、错误率
5. **etcd 指标**: 磁盘 I/O、leader 变更、提交延迟

### 日志工具

用于 Kubernetes 集群日志的工具：

1. **Elasticsearch**: 日志存储和搜索
2. **Fluentd/Fluent Bit**: 日志收集和转发
3. **Kibana**: 日志可视化
4. **Loki**: 日志聚合系统
5. **Grafana**: 日志可视化

#### EFK (Elasticsearch, Fluentd, Kibana) Stack 安装

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

#### 日志收集配置

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

## 故障排除

Kubernetes 集群故障排除是集群管理的重要组成部分。

### Pod 故障排除

用于 Pod 故障排除的命令：

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

### Node 故障排除

用于 Node 故障排除的命令：

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

### 网络故障排除

用于网络故障排除的命令：

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

### Control Plane 故障排除

用于 Control Plane 故障排除的命令：

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

## Amazon EKS 集群管理

Amazon EKS 是一项托管 Kubernetes 服务，可自动执行集群管理的许多方面。

下图展示了 Amazon EKS 集群架构和管理组件：

![架构图展示用户通过 AWS console、CLI 或 API 管理 Amazon EKS；EKS 运行 Control Plane、managed node group 和 Fargate，Control Plane 使用 AWS IAM、VPC 和 CloudWatch，并包含 VPC CNI、CoreDNS 和 kube-proxy add-on。](../.gitbook/assets/en-core-09-cluster-administration-8.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-8.html)

### EKS 集群配置

EKS 集群配置管理：

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

### EKS Node Group 管理

EKS Node Group 管理：

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

### EKS Add-on 管理

EKS Add-on 管理：

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

### EKS 集群升级

EKS 集群升级流程：

1. **Control Plane 升级**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version 1.22
   ```

2. **Add-on 升级**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version v1.10.2-eksbuild.1
   ```

3. **Node Group 升级**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS 集群监控

EKS 集群监控工具：

1. **Amazon CloudWatch**: 指标、日志、告警
2. **AWS CloudTrail**: API 调用日志
3. **Amazon Managed Grafana**: 指标可视化
4. **Amazon Managed Service for Prometheus**: 指标收集和存储

启用 CloudWatch Container Insights：

```bash
# Enable Container Insights
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## 集群管理最佳实践

Kubernetes 和 EKS 集群管理的最佳实践：

### 集群配置最佳实践

1. **Infrastructure as Code (IaC)**: 使用 Terraform、AWS CDK、eksctl 等管理集群配置
2. **版本控制**: 在版本控制系统中存储集群配置
3. **多环境**: 分离开发、预发布和生产环境
4. **网络隔离**: 配置适当的网络隔离和安全组
5. **最小权限原则**: 仅授予必要的最小权限

### 运维最佳实践

1. **定期备份**: 定期备份 etcd 和重要资源
2. **监控和告警**: 构建全面的监控和告警系统
3. **集中式日志**: 集中收集和分析日志
4. **自动化**: 自动化重复性任务
5. **灾难恢复规划**: 建立并测试清晰的灾难恢复计划

### 安全最佳实践

1. **定期更新**: 定期更新集群和 Node
2. **网络策略**: 配置适当的网络策略
3. **加密**: 对静态和传输中的数据进行加密
4. **安全上下文**: 配置适当的安全上下文
5. **镜像扫描**: 扫描容器镜像中的漏洞

### 资源管理最佳实践

1. **资源 Requests 和 Limits**: 为所有 Pod 设置适当的资源 requests 和 limits
2. **Namespace 隔离**: 按 namespace 隔离工作负载
3. **资源配额**: 为每个 namespace 设置资源配额
4. **HPA 和 VPA**: 配置自动扩缩容
5. **Node Affinity 和 Taints**: 优化工作负载放置

### EKS 专属最佳实践

1. **Managed Node Groups**: 尽可能使用 managed node group
2. **Fargate**: 将 Fargate 用于无服务器工作负载
3. **EKS Add-ons**: 使用官方 EKS add-on
4. **IAM Roles for Service Accounts (IRSA)**: 按 Pod 管理 IAM 权限
5. **VPC CNI Customization**: 根据网络要求配置 VPC CNI

## 结论

Kubernetes 集群管理对于维护集群稳定性、安全性和性能发挥着重要作用。本章涵盖了集群管理的各个方面，包括集群组件管理、资源管理、网络、身份验证和授权管理、升级、备份和恢复、监控和日志以及故障排除。

使用 Amazon EKS 可降低 Kubernetes Control Plane 管理的复杂性，并通过与 AWS 服务集成简化集群管理。不过，了解基础 Kubernetes 概念和最佳实践对于有效进行集群管理仍然很重要。

集群管理是一个持续过程，必须根据集群需求和工作负载特性不断调整。使用监控工具跟踪集群状态、通过自动化减少重复性任务以及遵循最佳实践，对于维护集群稳定性和安全性十分重要。

## 集群网络

Kubernetes 集群网络管理 Pod 间通信、Service 发现和外部访问。

### 网络架构

![架构图展示集群网络分为 Pod 网络、Service 网络、Ingress 和网络策略，分别通过 CNI 插件、Service 类型（ClusterIP、NodePort、LoadBalancer）、Ingress controller 和网络安全实现。](../.gitbook/assets/en-core-09-cluster-administration-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-9.html)

### CNI 插件管理

CNI (Container Network Interface) 插件负责 Kubernetes 集群网络。

```bash
# Install Calico CNI
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# Install Flannel CNI
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml

# Install Cilium CNI (using Helm)
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --version 1.14.0 --namespace kube-system
```

### CNI 插件比较

| CNI 插件 | 网络模型 | 网络策略支持 | 性能 | 功能 |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | 是 | 高 | 网络策略强大，基于路由 |
| **Flannel** | VXLAN/host-gateway | 否 | 中 | 设置简单，功能有限 |
| **Cilium** | eBPF | 是 | 很高 | L3-L7 策略，高性能 |
| **Weave Net** | VXLAN | 是 | 中 | 支持加密，多集群 |
| **AWS VPC CNI** | AWS VPC | 否 | 高 | 针对 AWS EKS 优化 |

### 网络故障排除

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
## 身份验证和授权管理

Kubernetes 身份验证和授权管理是集群安全的核心要素。RBAC (Role-Based Access Control) 用于管理用户和 Service Account 的权限。

### 身份验证方法

Kubernetes 支持多种身份验证方法：

1. **X.509 Certificates**: 使用客户端证书进行身份验证
2. **Service Account Tokens**: 用于 Pod 内访问 API server
3. **OpenID Connect (OIDC)**: 与外部身份提供商集成
4. **Webhook Token Authentication**: 与外部身份验证服务集成
5. **Authentication Proxy**: 通过代理进行身份验证

### RBAC 配置

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

### 用户证书创建

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

### Service Account 管理

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

### 权限验证

```bash
# Check user permissions
kubectl auth can-i get pods --as jane

# Check permissions in a specific namespace
kubectl auth can-i create deployments --as jane --namespace production
```
## 集群升级

Kubernetes 集群升级是应用新功能、安全补丁和 bug 修复所必需的。必须仔细规划和执行升级。

### 升级规划

![树状图展示升级规划分为四项任务：检查版本兼容性、创建备份、选择升级策略和规划停机时间；每项任务分别对应具体操作：审查 API 变更、etcd 备份、就地升级与蓝绿部署的选择以及用户沟通。](../.gitbook/assets/en-core-09-cluster-administration-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-10.html)

### 升级策略比较

| 策略 | 描述 | 优点 | 缺点 | 适用环境 |
|----------|-------------|------------|---------------|---------------------|
| **就地升级** | 直接升级现有集群 | 资源高效，流程简单 | 回滚复杂，可能停机 | 开发、测试环境 |
| **蓝绿部署** | 创建新版本集群并切换 | 回滚安全，可验证 | 资源重复，成本增加 | 生产环境 |
| **金丝雀部署** | 仅将部分工作负载迁移到新集群 | 可逐步验证，风险较低 | 管理复杂，双重运行 | 关键生产环境 |

### 使用 kubeadm 升级

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

### 升级后验证

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
## 备份和恢复

Kubernetes 集群备份和恢复是灾难恢复规划的重要组成部分。主要备份目标为 etcd 数据库、persistent volume 数据和 Kubernetes 资源定义。

### etcd 备份和恢复

etcd 是存储集群所有状态信息的核心组件。

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

### Kubernetes 资源备份

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

### 使用 Velero 进行备份和恢复

Velero 是用于备份和恢复 Kubernetes 集群资源和 persistent volume 的工具。

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

### 备份策略比较

| 备份方法 | 备份目标 | 优点 | 缺点 | 恢复时间 |
|--------------|---------------|------------|---------------|---------------|
| **etcd Snapshot** | 集群状态 | 内置功能，完整状态保留 | 不包含 volume 数据，手动流程 | 中等 |
| **资源 YAML 备份** | Kubernetes 对象 | 实现简单，可选择性恢复 | 不包含 volume 数据，关系复杂 | 慢 |
| **Velero** | 资源和 volume | 自动化、可调度、volume snapshot | 需要安装额外工具 | 快 |
| **Cloud Provider Snapshots** | 整个集群 | 完整恢复，云集成 | 云依赖，成本 | 非常快 |
## 监控和日志

有效的集群管理需要全面的监控和日志系统。这可及早发现和解决问题。

### 监控架构

![架构图展示 Kubernetes 监控分为指标收集、日志收集、告警和可视化，分别由 Prometheus（配合 kube-state-metrics 和 node-exporter）、将日志发送到 Elasticsearch 和 Kibana 的 Fluentd/Fluent Bit、Alertmanager 和 Grafana 处理。](../.gitbook/assets/en-core-09-cluster-administration-11.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-11.html)

### Prometheus 和 Grafana 安装

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

### EFK Stack 安装 (Elasticsearch, Fluentd, Kibana)

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

### 关键监控指标

| 指标类型 | 描述 | 关键指标 | 监控工具 |
|-------------|-------------|-------------|-----------------|
| **Node 指标** | Node 级资源使用情况 | CPU、内存、磁盘、网络 | node-exporter、Prometheus |
| **Pod 指标** | 容器资源使用情况 | CPU、内存使用量、limits | cAdvisor、Prometheus |
| **集群指标** | 集群状态和资源 | Pod 数量、Node 状态、event | kube-state-metrics |
| **应用程序指标** | 自定义应用程序指标 | 请求数、延迟、错误率 | Prometheus client libraries |

### 日志收集和分析

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

### 告警配置

可以使用 Prometheus Alertmanager 配置告警：

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
## 故障排除

Kubernetes 集群故障排除是系统管理员和运维人员的重要技能。有效的故障排除需要系统化的方法。

### 故障排除方法论

![工作流图展示从问题识别到文档记录的六步故障排除流程，其中信息收集步骤分支为日志、event 和资源状态检查。](../.gitbook/assets/en-core-09-cluster-administration-12.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-12.html)

### 常见问题和解决方案

| 问题类型 | 症状 | 诊断命令 | 常见解决方案 |
|-------------|----------|---------------------|-----------------|
| **Pod 未启动** | Pod 处于 Pending 或 ContainerCreating 状态 | `kubectl describe pod <pod-name>` | 检查资源限制、镜像可用性、volume mount |
| **Service 连接问题** | 无法通过 Service 访问 Pod | `kubectl describe svc <service-name>`, `kubectl get endpoints <service-name>` | 检查 label selector、Pod 状态、网络策略 |
| **Node 问题** | Node 处于 NotReady 状态 | `kubectl describe node <node-name>`, `kubectl get events` | 检查 kubelet 状态、系统资源、网络连接 |
| **DNS 问题** | 无法通过 Service 名称连接 | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | 检查 CoreDNS Pod、kube-dns Service、网络策略 |
| **身份验证问题** | API server 拒绝访问 | `kubectl auth can-i <verb> <resource>` | 检查 RBAC 设置、证书有效性、Service Account |

### Pod 故障排除

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

### Node 故障排除

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

### 网络故障排除

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
## Amazon EKS 集群管理

Amazon EKS (Elastic Kubernetes Service) 是 AWS 上的托管 Kubernetes 服务，其中 AWS 管理 Control Plane。但是，Node、网络、安全等的管理由用户负责。

### EKS 集群架构

![架构图展示 Amazon EKS 集群分为 AWS 管理的 Control Plane（API server、etcd、scheduler）和客户责任区域；客户责任区域涵盖 data plane（managed node group 及 EC2 Auto Scaling group、self-managed node、Fargate）、网络（VPC CNI 和 AWS VPC）及安全（使用 IAM role 和 policy 的 IAM 身份验证）。](../.gitbook/assets/en-core-09-cluster-administration-13.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-13.html)

### EKS 集群创建

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

### Node Group 管理

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

### EKS 集群升级

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

### EKS 集群身份验证和授权

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

### EKS 集群监控

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
## 集群管理最佳实践

有效 Kubernetes 集群管理的最佳实践对于确保稳定性、安全性和性能非常重要。

### 集群设置最佳实践

1. **多可用区配置**: 将 Node 分布在多个可用区以实现高可用性
2. **适当的规模**: 选择适合工作负载的 Node 类型和数量
3. **自动扩缩容配置**: 启用 cluster autoscaler 和 horizontal pod autoscaler
4. **应用网络策略**: 从默认拒绝策略开始，仅允许必要通信
5. **设置资源配额**: 按 namespace 设置资源限制

### 运维最佳实践

1. **使用声明式配置**: 将所有资源定义为 YAML 文件并进行版本控制
2. **采用 GitOps**: 将 Git 用作唯一事实来源，并构建自动化部署 pipeline
3. **定期备份**: 定期备份 etcd 数据和 persistent volume 数据
4. **监控和告警**: 构建全面的监控系统并为关键指标设置告警
5. **集中式日志**: 将所有日志收集到集中式日志系统，便于分析

### 安全最佳实践

1. **最小权限原则**: 使用 RBAC 仅授予必要的最小权限
2. **网络分段**: 使用网络策略限制 Pod 间通信
3. **镜像扫描**: 实施容器镜像扫描以检测漏洞
4. **Secret 管理**: 使用外部 Secret 管理工具（例如 AWS Secrets Manager、HashiCorp Vault）
5. **定期安全审计**: 定期审计集群配置和权限

### 升级最佳实践

1. **渐进式升级**: 逐步升级，而非一次性完成
2. **先在测试环境中验证**: 在生产环境之前于测试环境验证升级
3. **创建备份**: 升级前执行完整备份
4. **回滚计划**: 制定发生问题时回滚到先前版本的计划
5. **设置升级窗口**: 在低使用率时段执行升级

### 成本优化最佳实践

1. **选择适当的 Node 大小**: 为工作负载选择最佳 Node 类型
2. **利用 Spot Instance**: 对非关键工作负载使用 spot instance
3. **配置自动扩缩容**: 根据需求配置自动扩容和缩容
4. **优化资源 Requests 和 Limits**: 根据实际使用情况设置资源 requests 和 limits
5. **识别空闲资源**: 定期识别并移除空闲资源

### 文档最佳实践

1. **记录架构**: 记录集群架构、网络和安全设置
2. **记录运维流程**: 记录常见运维任务、故障排除流程和紧急响应计划
3. **变更管理**: 记录和跟踪所有集群变更
4. **创建 Runbook**: 为常见场景提供分步指南
5. **知识共享**: 在团队内定期开展知识共享和培训会议
## 结论

Kubernetes 集群管理是一项复杂任务，涵盖多个方面。从集群设置到运维、监控、故障排除和升级，都需要采用系统化的方法。

为有效进行集群管理，请重点关注以下关键领域：

1. **集群组件管理**: Control Plane 和 Node 组件的稳定运行
2. **资源管理**: 高效的资源分配和使用
3. **网络**: 安全且高效的网络配置
4. **安全**: 适当的身份验证和授权管理
5. **备份和恢复**: 防止数据丢失和规划灾难恢复
6. **监控和日志**: 监控集群状态和性能
7. **故障排除**: 系统化的故障排除方法

使用 Amazon EKS 等托管 Kubernetes 服务时，了解服务提供商与用户之间的共同责任模型非常重要。虽然 AWS 管理 Control Plane，但 Node、网络、安全等的管理仍然是用户的责任。

通过遵循最佳实践并使用适当工具，您可以运行稳定、安全且高效的 Kubernetes 集群。不断学习和改进以提升集群管理能力非常重要。

---

> **参考资料**:
> - [Kubernetes 官方文档：集群管理](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS 用户指南](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes 最佳实践：集群管理](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd 文档：备份和恢复](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus 文档](https://prometheus.io/docs/introduction/overview/)

## 测验

要测试您在本章所学的内容，请尝试[集群管理测验](../quizzes/core/09-cluster-administration-quiz.md)。
