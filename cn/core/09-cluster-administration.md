# Kubernetes 集群管理

> **支持的版本**: Kubernetes 1.34–1.37 的 EKS 标准支持（检查日期：2026 年 10 月 12 日）
> **最后更新**: October 12, 2026

Kubernetes 集群管理是一项重要工作，涵盖集群设置、维护、监控、故障排除和升级。本章将探讨 Kubernetes 集群管理的各个方面，以及在 Amazon EKS 中进行集群管理的最佳实践。

自行管理的 kubeadm 操作与 EKS 服务操作不同。EKS 不会公开控制平面主机、静态 Pod 清单或直接 etcd 访问。请将以下代码块视为独立示例，而不是按顺序执行的单一脚本。请检查实际集群版本的上游支持和附加组件兼容性。

## 核心概念

- **集群生命周期管理**: 从创建集群到退役的完整过程
- **控制平面管理**: 管理 API server、scheduler 和 controller manager 等核心组件
- **节点管理**: 添加、移除和维护工作节点
- **资源分配**: 设置 CPU、内存、存储等资源分配和限制
- **升级策略**: 最大限度减少停机时间的集群和应用程序升级策略

## 目录
1. [集群管理概览](#cluster-administration-overview)
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

请使用 [官方 kubectl 安装指南](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)，并使 kubectl 与 API server 的次要版本差距不超过一个版本。对于自行管理的集群，请从目标次要版本的 `pkgs.k8s.io` 仓库安装 kubeadm/kubelet；旧的 `1.x.y-00` 软件包示例已过时。请在安装前从已配置的仓库中选择准确的软件包版本。

请根据其 [官方 Helm 说明](https://helm.sh/docs/intro/install/)和 [k9s 发布页面](https://github.com/derailed/k9s/releases)安装 Helm 和 k9s，并检查平台架构和校验和。EKS 管理还需要已经过身份验证的 AWS CLI 和兼容的 eksctl。

```bash
kubectl version --client
helm version
k9s version
# Self-managed nodes only, after configuring the target minor repository:
apt-cache madison kubeadm
```


## 集群管理概览

Kubernetes 集群管理是管理集群完整生命周期的过程。这包括以下主要领域：

1. **集群设置和配置**: 创建集群、添加节点、设置网络、配置存储等
2. **运维管理**: 资源监控、性能优化、容量规划、故障排除
3. **安全管理**: 身份验证、授权、网络策略、安全上下文等
4. **升级和补丁**: 集群版本升级、应用安全补丁
5. **备份和恢复**: 集群数据备份、灾难恢复规划

下图显示 Kubernetes 集群管理的主要领域及相关工具：

## 集群组件管理

Kubernetes 集群由控制平面组件和节点组件构成。管理好每个组件对于集群稳定性和性能至关重要。

### 控制平面组件管理

![显示 Kubernetes 控制平面分支到其五个组件（API server、etcd、scheduler、controller manager、cloud controller manager）的树状图；每个组件均配有其负责的运维事项：身份验证和授权、数据备份、调度策略、控制器状态监控和云资源管理。](../.gitbook/assets/en-core-09-cluster-administration-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-0.html)

#### API Server 管理

API server 是公开 Kubernetes API 的控制平面核心组件。

```bash
# Check API server logs
kubectl logs -n kube-system kube-apiserver-<master-node-name>

# Check API server configuration (kubeadm cluster)
sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml

# Check API server status
kubectl get --raw='/readyz?verbose'
```

#### etcd 管理

etcd 是存储 Kubernetes API 状态的分布式键值存储。

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

### 节点管理

节点是运行容器化应用程序的工作机器。

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
kubectl get --raw='/readyz?verbose'

# Check system pod status
kubectl get pods -n kube-system

# Check node resource usage
kubectl top nodes
```

![展示集群管理员五个职责领域及各领域所用工具的图表。](../.gitbook/assets/en-core-09-cluster-administration-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-1.html)

### 集群管理工具

可用于 Kubernetes 集群管理的工具有多种：

1. **kubectl**: 与 Kubernetes 集群交互的命令行工具
2. **kubeadm**: 创建和管理 Kubernetes 集群的工具
3. **kops**: 创建、升级和管理 Kubernetes 集群的工具
4. **eksctl**: 创建和管理 Amazon EKS 集群的工具
5. **Helm**: Kubernetes 应用程序包管理器
6. **Headlamp**: Kubernetes Web UI；旧 Kubernetes Dashboard 项目已归档
7. **Prometheus & Grafana**: 监控和告警工具
8. **Fluentd & Elasticsearch**: 日志工具

## 集群组件管理

Kubernetes 集群由多个组件构成，有效管理这些组件十分重要。

### 控制平面组件

控制平面组件管理集群的整体状态：

1. **kube-apiserver**: 公开 Kubernetes API 的组件
2. **etcd**: 存储集群数据的键值存储
3. **kube-scheduler**: 将 Pod 调度到节点的组件
4. **kube-controller-manager**: 运行控制器的组件
5. **cloud-controller-manager**: 与云提供商交互的组件

下图显示 Kubernetes 控制平面组件及其交互：

![架构图：etcd、kube-scheduler、kube-controller-manager 和 cloud-controller-manager 与位于中央的 kube-apiserver 双向通信；工作节点的 kubelet 与 API server 双向通信，同时使用容器运行时；kube-proxy 独立监视 Service/EndpointSlice 状态。](../.gitbook/assets/en-core-09-cluster-administration-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-2.html)

#### 控制平面组件监控

监控控制平面组件状态非常重要：

```bash
# Check control plane component status
kubectl get --raw='/readyz?verbose'

# Check API server logs
kubectl logs -n kube-system kube-apiserver-<node-name>

# Check etcd status
kubectl exec -n kube-system etcd-<node-name> -- etcdctl \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
  --key=/etc/kubernetes/pki/etcd/healthcheck-client.key endpoint health
```

#### 控制平面组件配置

以下清单只是标志/配置片段。它省略了主机网络、证书挂载和其他 kubeadm 生成的设置；不要使用此片段替换正在运行的控制平面清单。请使镜像与集群升级计划相匹配。

如何管理控制平面组件配置：

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
    - --service-account-signing-key-file=/etc/kubernetes/pki/sa.key
    - --service-account-issuer=https://kubernetes.default.svc.cluster.local
    - --service-cluster-ip-range=10.96.0.0/12
    - --tls-cert-file=/etc/kubernetes/pki/apiserver.crt
    - --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
    image: registry.k8s.io/kube-apiserver:v1.36.4
    name: kube-apiserver
```

### 节点组件

节点组件在每个节点上运行并管理 Pod：

1. **kubelet**: 在每个节点上运行、确保 Pod 和容器处于运行状态的代理
2. **kube-proxy**: 维护网络规则并处理连接转发
3. **Container Runtime**: 运行容器的软件（containerd、CRI-O，或使用外部 CRI 适配器的 Docker Engine）

#### 节点管理

节点管理的关键命令：

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
kubectl drain <node-name> --ignore-daemonsets
```

Drain 可能因独立 Pod、PDB 或本地数据而停止。不要默认添加 `--force` 或 `--delete-emptydir-data`，而应调查原因；后者会明确授权丢失 emptyDir 数据。在维护前，请等待 drain 完成并确认工作负载健康。

#### 节点故障排除

节点故障排除命令：

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

有效管理 Kubernetes 集群中的资源，对于保持集群稳定性和性能非常重要。

### Namespace 管理

使用一次性 Namespace 练习生命周期操作。删除 Namespace 会删除其命名空间作用域资源；请先检查并备份所需数据。`get all` 仅是工作负载的一个子集。

```bash
kubectl create namespace admin-demo
kubectl get all -n admin-demo
# Cleanup only the disposable exercise namespace:
kubectl delete namespace admin-demo
```

### 资源配额

资源配额限制每个 Namespace 的资源使用：

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

在上述示例中，`dev` Namespace 最多可有 10 个 Pod、1 CPU 和 1Gi 内存请求，以及 2 CPU 和 2Gi 内存限制。

### LimitRange

LimitRange 为 Namespace 内的单个资源设置默认值和限制：

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

在上述示例中，`dev` Namespace 中的所有容器默认限制为 500m CPU 和 512Mi 内存，默认请求为 200m CPU 和 256Mi 内存，最大值为 1 CPU 和 1Gi 内存，最小值为 100m CPU 和 128Mi 内存。

### Horizontal Pod Autoscaler (HPA)

HPA 根据 CPU 使用率或自定义指标自动调整 Pod 数量：

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

在上述示例中，`frontend` Deployment 的目标是已请求 CPU 的平均利用率达到 80%，但需受容差、缺失指标、稳定窗口和扩缩容策略约束。它保持最少 2 个、最多 10 个副本。

### Vertical Pod Autoscaler (VPA)

VPA 自动调整 Pod 的 CPU 和内存请求：

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
    updateMode: "Recreate"
```

在上述示例中，`frontend` Deployment 中 Pod 的 CPU 和内存请求会根据实际资源使用情况自动调整。
## 集群网络

Kubernetes 集群网络管理 Pod、Service 和节点之间的通信。

### 集群网络模型

Kubernetes 网络模型的基本要求：

1. 所有 Pod 无需 NAT 即可与其他所有 Pod 通信
2. 节点代理（kubelet）可与该节点上的所有 Pod 通信
3. 外部连接取决于路由和出口策略；不存在通用的 Pod NAT 模式要求

下图显示 Kubernetes 网络组件和通信流：

![架构图：客户端流量通过 Ingress 进入一个 Service，Service 在不同节点上的两个 Pod 之间进行负载均衡；这些 Pod 彼此通信并访问外部服务。](../.gitbook/assets/en-core-09-cluster-administration-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-3.html)

### CNI (Container Network Interface) 插件

Kubernetes 通过 CNI 插件实现网络。常见 CNI 插件：

1. **Calico**: 具备增强网络策略和安全功能的 CNI
2. **Flannel**: 提供简单的覆盖网络
3. **Cilium**: 基于 eBPF 的网络和安全解决方案
4. **AWS VPC CNI**: 与 AWS VPC 集成的 CNI
5. **Weave Net（历史）**: 已归档；新安装应选择受维护的替代方案

#### CNI 插件安装和配置

CNI 插件安装示例（Calico）：

请选择一个 CNI，或使用有文档记录的链式/迁移设置。不得在同一运行中集群中依次安装 Calico、Flannel 和 Cilium 替代方案。请使用受支持的固定版本和提供商特定说明；在 EKS 上，请遵循[网络章节](./03-services-networking.md)中的 VPC CNI 或计划使用的替代 CNI 流程。

```bash
# Inspect the installed networking components before making changes
kubectl get daemonsets -A
kubectl get pods -A -l k8s-app=calico-node
```


### Service 网络

Kubernetes Service 为 Pod 集合提供稳定端点：

1. **ClusterIP**: 只能在集群内访问的 Service
2. **NodePort**: 通过所有节点上的特定端口可访问的 Service
3. **LoadBalancer**: 通过外部负载均衡器可访问的 Service
4. **ExternalName**: 为外部服务提供 CNAME 记录

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

在上述示例中，带有 `role=db` 标签的 Pod 只允许来自带有 `role=frontend` 标签 Pod 的 TCP 端口 3306 入站流量，以及到带有 `role=monitoring` 标签 Pod 的 TCP 端口 9090 出站流量。

## 身份验证和授权管理

Kubernetes 身份验证和授权管理是集群安全的核心要素。

下图显示 Kubernetes 身份验证和授权流程：

![架构图：请求在 API server 内依次经过身份验证、授权和准入控制，并显示每个阶段支持的具体身份验证方法和授权模式。](../.gitbook/assets/en-core-09-cluster-administration-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-4.html)

### 身份验证

Kubernetes 支持多种身份验证方法：

1. **X.509 Certificates**: 使用客户端证书进行身份验证
2. **Service Account Tokens**: 与 Service Account 关联的 JWT 令牌
3. **OpenID Connect (OIDC)**: 通过外部身份提供商进行身份验证
4. **Webhook Token Authentication**: 通过外部服务验证令牌
5. **Authentication Proxy**: 通过身份验证代理处理请求

#### X.509 证书管理

X.509 证书创建和管理：

```bash
# Generate a protected private key and CSR
umask 077
openssl genrsa -out user.key 2048
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
kubectl wait --for=jsonpath='{.status.certificate}' csr/user-csr --timeout=60s

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
3. **Node**: 节点授权
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
---
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

在上述示例中，`user` 有权查看 `default` Namespace 中的 Pod。

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
---
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

在上述示例中，`user` 有权查看集群中的所有节点。

### Service Account 管理

Service Account 供 Pod 与 API server 通信：

```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default

# Grant permissions to service account
---
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
---
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

安全上下文定义 Pod 和容器的权限与访问控制：

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
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: security-context-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

在上述示例中，Pod 使用 UID 1000 和 GID 3000 运行，容器无法提升权限、移除了所有 Linux capabilities，且根文件系统以只读方式挂载。

## 集群升级

必须进行 Kubernetes 集群升级，才能应用新功能、性能改进和安全补丁。

下图显示 Kubernetes 集群升级流程：

![Kubernetes 集群升级的工作流图：规划和版本兼容性检查、etcd 备份、第一个控制平面节点升级和功能测试、其余控制平面和工作节点升级，随后进行集群验证并完成升级；验证发现问题时，会通过回滚路径从备份恢复。](../.gitbook/assets/en-core-09-cluster-administration-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-5.html)

### 升级规划

规划集群升级时的注意事项：

1. **版本兼容性**: 检查 Kubernetes 版本之间的兼容性
2. **升级路径**: 检查受支持的升级路径
3. **停机时间**: 规划升级期间的预期停机时间
4. **回滚计划**: 制定出现问题时的回滚计划
5. **应用程序影响**: 评估升级对应用程序的影响

### 控制平面升级

使用 kubeadm 升级控制平面：

请使用[特定版本的 kubeadm 升级流程](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)。启用目标次要版本的 pkgs.k8s.io 仓库，并选择已发布的准确软件包版本；每次只升级一个次要版本。

1. 备份 etcd 并验证工作负载/附加组件兼容性。在第一个控制平面节点上升级 kubeadm，运行 `kubeadm upgrade plan`，然后运行 `kubeadm upgrade apply <target-version>`。
2. 在其他控制平面节点上，升级 kubeadm 并运行 `kubeadm upgrade node`。
3. 升级 kubelet 前，先 drain 每个节点。如果 drain 失败，停止流程并解决原因。将 kubelet/kubectl 升级到兼容版本，重新加载 systemd，重启 kubelet，验证 Ready 和工作负载，然后从管理客户端 uncordon。
4. 在每个工作节点上，升级 kubeadm 并运行 `kubeadm upgrade node`，然后执行 drain/kubelet/验证/uncordon 序列。不要以通用的全系统升级替代 Kubernetes 特定版本升级流程。

请在明确指定的节点或管理客户端上运行命令；一系列嵌套的 `ssh` 会话不是多节点自动化脚本。

### 工作节点升级

工作节点升级流程：

请使用[特定版本的 kubeadm 升级流程](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)。启用目标次要版本的 pkgs.k8s.io 仓库，并选择已发布的准确软件包版本；每次只升级一个次要版本。

1. 备份 etcd 并验证工作负载/附加组件兼容性。在第一个控制平面节点上升级 kubeadm，运行 `kubeadm upgrade plan`，然后运行 `kubeadm upgrade apply <target-version>`。
2. 在其他控制平面节点上，升级 kubeadm 并运行 `kubeadm upgrade node`。
3. 升级 kubelet 前，先 drain 每个节点。如果 drain 失败，停止流程并解决原因。将 kubelet/kubectl 升级到兼容版本，重新加载 systemd，重启 kubelet，验证 Ready 和工作负载，然后从管理客户端 uncordon。
4. 在每个工作节点上，升级 kubeadm 并运行 `kubeadm upgrade node`，然后执行 drain/kubelet/验证/uncordon 序列。不要以通用的全系统升级替代 Kubernetes 特定版本升级流程。

请在明确指定的节点或管理客户端上运行命令；一系列嵌套的 `ssh` 会话不是多节点自动化脚本。

### 升级验证

升级后验证集群状态：

```bash
# Check node versions
kubectl get nodes

# Check component status
kubectl get --raw='/readyz?verbose'

# Check pod status
kubectl get pods --all-namespaces

# Test cluster functionality
kubectl create deployment nginx --image=nginx
kubectl expose deployment nginx --port=80
kubectl get svc nginx
```
## 备份和恢复

Kubernetes 集群备份和恢复是灾难恢复规划的重要组成部分。

下图显示 Kubernetes 集群备份和恢复流程：

![架构图：定期 etcd 快照和资源 YAML 备份都会存入备份存储，备份存储随后在灾难恢复期间用于 etcd 恢复和资源恢复。](../.gitbook/assets/en-core-09-cluster-administration-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-6.html)

### etcd 备份

etcd 存储 Kubernetes 集群的所有状态信息，因此定期备份非常重要：

```bash
# Create etcd snapshot
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db

# Check snapshot status
etcdutl snapshot status --write-out=table /backup/etcd-snapshot-2023-01-01-12-00-00.db
```

### etcd 恢复

从 etcd 快照恢复：

对于自行管理的灾难恢复，请使用特定发行版的操作手册停止所有 API server 和受影响的 etcd 进程。仅停止 kubelet 不会停止现有的静态 Pod 容器。请使用兼容的 etcdutl 恢复到新目录；在验证恢复之前保留原始数据。此单成员命令只是示例，而不是多成员 HA 恢复：

```bash
etcdutl snapshot status "$SNAPSHOT_FILE" --write-out=table
etcdutl snapshot restore "$SNAPSHOT_FILE" \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

将 SNAPSHOT_FILE 设置为已验证的快照。对于 HA，在每个成员上恢复同一快照，但使用其唯一名称/对等 URL 和相同的完整成员列表。选择超过快照后变更量的修订号增量。使用正确的所有权和证书更新 etcd 清单/服务到恢复路径，验证 quorum/health，然后重启 API server/controller。请参阅[官方恢复指南](https://etcd.io/docs/v3.6/op-guide/recovery/)。EKS 用户无法直接恢复托管控制平面 etcd。

### 资源备份

这些导出内容是受保护的清单，而不是完整的可移植恢复计划。它们包含 Secret，需要受限权限/加密，且不包含 PV 数据。请使用 `umask 077` 并检查每个命令失败情况；按顺序恢复 CRD/依赖项，并酌情删除服务器拥有的元数据。`kubectl get all` 只返回资源种类的一个子集。

将 Kubernetes 资源备份为 YAML 文件：

```bash
# Export listable resources (includes sensitive Secrets)
set -eu
umask 077
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  mkdir -p /backup/resources/$ns
  for resource in $(kubectl api-resources --verbs=list --namespaced=true -o name); do
    kubectl get -n "$ns" "$resource" -o yaml > "/backup/resources/$ns/$resource.yaml"
  done
done

# Backup cluster-scoped resources
mkdir -p /backup/resources/cluster-scoped
for resource in $(kubectl api-resources --verbs=list --namespaced=false -o name); do
  kubectl get "$resource" -o yaml > "/backup/resources/cluster-scoped/$resource.yaml"
done
```

### 备份自动化

仅限自行管理 kubeadm 示例：请将工具镜像替换为包含兼容 etcdctl 的已验证镜像，使控制平面标签/污点和证书路径相匹配，并创建备份 PVC。所选主机必须在所示回环地址公开 etcd 并允许 PVC 挂载。此操作不能在托管 EKS 控制平面上运行。请验证快照并将其复制到受保护的外部存储；仅集群内 PVC 不构成灾难恢复。

使用 CronJob 自动执行备份任务：

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  concurrencyPolicy: Forbid
  schedule: "0 0 * * *"  # Run daily at midnight
  jobTemplate:
    spec:
      template:
        spec:
          hostNetwork: true
          automountServiceAccountToken: false
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""
          tolerations:
          - key: node-role.kubernetes.io/control-plane
            operator: Exists
            effect: NoSchedule
          containers:
          - name: etcd-backup
            image: example.invalid/etcd-backup-tools:replace-me
            command:
            - /bin/sh
            - -c
            - |
              set -eu
              umask 077
              ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt \
                --key=/etc/kubernetes/pki/etcd/healthcheck-client.key \
                snapshot save /backup/etcd-snapshot-$(date +%Y-%m-%d-%H-%M-%S).db
            volumeMounts:
            - name: etcd-ca
              mountPath: /etc/kubernetes/pki/etcd/ca.crt
              readOnly: true
            - name: etcd-client-cert
              mountPath: /etc/kubernetes/pki/etcd/healthcheck-client.crt
              readOnly: true
            - name: etcd-client-key
              mountPath: /etc/kubernetes/pki/etcd/healthcheck-client.key
              readOnly: true
            - name: backup
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: etcd-ca
            hostPath:
              path: /etc/kubernetes/pki/etcd/ca.crt
              type: File
          - name: etcd-client-cert
            hostPath:
              path: /etc/kubernetes/pki/etcd/healthcheck-client.crt
              type: File
          - name: etcd-client-key
            hostPath:
              path: /etc/kubernetes/pki/etcd/healthcheck-client.key
              type: File
          - name: backup
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

## 监控和日志

有效的监控和日志记录是集群管理的核心要素。

下图显示 Kubernetes 集群监控和日志架构：

![架构图：API server 和节点指标通过 kube-state-metrics 和 Node Exporter 流入 Prometheus，再到 Alertmanager 和 Grafana；Pod 日志则通过 Fluentd/Fluent Bit 流入 Elasticsearch（搭配 Kibana）和 Loki，Loki 也向 Grafana 提供数据。](../.gitbook/assets/en-core-09-cluster-administration-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-7.html)

### 监控工具

Kubernetes 集群监控工具：

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

需要监控的关键指标：

1. **节点指标**: CPU、内存、磁盘、网络使用率
2. **Pod 指标**: CPU、内存使用率、重启次数
3. **容器指标**: CPU、内存使用率、文件系统使用率
4. **API Server 指标**: 请求延迟、请求数、错误率
5. **etcd 指标**: 磁盘 I/O、leader 变更、提交延迟

### 日志工具

Kubernetes 集群日志工具：

1. **Elasticsearch**: 日志存储和搜索
2. **Fluentd/Fluent Bit**: 日志收集和转发
3. **Kibana**: 日志可视化
4. **Loki**: 日志聚合系统
5. **Grafana**: 日志可视化

#### EFK (Elasticsearch, Fluentd, Kibana) Stack 安装

独立的 Elastic Stack Helm chart 仓库已归档。若要进行受维护的部署，请使用 Elastic Cloud on Kubernetes (ECK)，然后定义 Elasticsearch/Kibana 资源和兼容的日志收集器。仅安装 operator 不会创建 EFK Stack：

```bash
helm repo add elastic https://helm.elastic.co
helm upgrade --install elastic-operator elastic/eck-operator \
  --namespace elastic-system --create-namespace \
  --version "${ECK_CHART_VERSION:?Select a supported ECK chart version}"
```

将仪表板置于 ClusterIP/已验证访问之后；请按照 [ECK 指南](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/install-using-helm-chart)配置存储、TLS、凭证、收集器解析和 RBAC。

#### 日志收集配置

此示例解析 CRI 日志信封，而不是假定使用 Docker JSON。收集器镜像必须包含元数据/输出插件，挂载节点日志和可写的位置文件存储，并获得范围受限的元数据 RBAC。请为实际 Elasticsearch Service 配置 TLS/身份验证；仅有占位主机不是完整的 ECK 集成。根据所选收集器处理部分/多行记录。

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
        @type regexp
        expression /^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$/
        time_type string
        time_format %Y-%m-%dT%H:%M:%S.%N%:z
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

Pod 故障排除命令：

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

### 节点故障排除

节点故障排除命令：

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

网络故障排除命令：

```bash
# Check service status
kubectl get svc <service-name>

# Check service detailed information
kubectl describe svc <service-name>

# Check endpoints
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# Check DNS
kubectl run -it --rm --restart=Never busybox --image=busybox -- nslookup <service-name>

# Test network connectivity
kubectl run -it --rm --restart=Never busybox --image=busybox -- wget -O- <service-name>:<port>

# Check network policies
kubectl get networkpolicy
kubectl describe networkpolicy <policy-name>
```

### 控制平面故障排除

控制平面故障排除命令：

```bash
# Check component status
kubectl get --raw='/readyz?verbose'

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

Amazon EKS 是一种托管 Kubernetes 服务，可自动化处理集群管理的许多方面。

下图显示 Amazon EKS 集群架构和管理组件：

![架构图：用户通过 AWS 控制台、CLI 或 API 管理 Amazon EKS；EKS 运行控制平面以及托管节点组和 Fargate，控制平面使用 AWS IAM、VPC 和 CloudWatch，并使用 VPC CNI、CoreDNS 和 kube-proxy 附加组件。](../.gitbook/assets/en-core-09-cluster-administration-8.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-8.html)

### EKS 集群配置

更改端点访问之前，请设置实际的管理员 CIDR，并验证私有访问仍可访问。版本升级必须升级到下一个受支持的次要版本，并使用兼容的附加组件/节点；不要将此示例用于降级或跳过次要版本操作。轮询返回的更新 ID，如果失败则停止依赖的变更。

EKS 集群配置管理：

```bash
# Check EKS cluster information
aws eks describe-cluster --name my-cluster

# Update EKS cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${ADMIN_CIDR:?Set an approved administrator public CIDR}"

# Update EKS cluster version
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"
```

### EKS 节点组管理

EKS 节点组管理：

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

### EKS 附加组件管理

使用 `aws eks describe-cluster --name my-cluster --query cluster.version --output text` 读取当前版本；将其用于发现附加组件并选择兼容的固定版本。在创建/更新前检查现有配置/IAM，不要再次创建已受管理的附加组件。删除示例使用 `--preserve`，以便在移除 EKS 管理时保持 CNI 运行；卸载活动网络是另一项有破坏性的操作。

EKS 附加组件管理：

```bash
# Check available add-ons
aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version "${CLUSTER_VERSION:?Set the actual cluster version}"

# Install add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"

# Delete add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni --preserve
```

### EKS 集群升级

EKS 集群升级流程：

1. **控制平面升级**:
   ```bash
   aws eks update-cluster-version \
     --name my-cluster \
     --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"
   ```

2. **附加组件升级**:
   ```bash
   aws eks update-addon \
     --cluster-name my-cluster \
     --addon-name vpc-cni \
     --addon-version "${CNI_ADDON_VERSION:?Select a compatible pinned VPC CNI add-on version}"
   ```

3. **节点组升级**:
   ```bash
   aws eks update-nodegroup-version \
     --cluster-name my-cluster \
     --nodegroup-name my-nodegroup
   ```

### EKS 集群监控

控制平面日志会导出 api/audit/authenticator/controllerManager/scheduler 日志。Container Insights 需要 CloudWatch agent/附加组件和范围受限的遥测 IAM 权限；它不会通过 update-cluster-logging 启用。CloudWatch observability 附加组件安装 CloudWatch/Fluent Bit 组件，而不是 Prometheus/Grafana。请参阅[官方附加组件设置](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)。

EKS 集群监控工具：

1. **Amazon CloudWatch**: 指标、日志、告警
2. **AWS CloudTrail**: API 调用日志
3. **Amazon Managed Grafana**: 指标可视化
4. **Amazon Managed Service for Prometheus**: 指标收集和存储

启用 EKS 控制平面日志：

```bash
# Enable EKS control-plane logs
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --approve
```

## 集群管理最佳实践

Kubernetes 和 EKS 集群管理的最佳实践：

### 集群配置最佳实践

1. **Infrastructure as Code (IaC)**: 使用 Terraform、AWS CDK、eksctl 等管理集群配置
2. **版本控制**: 将集群配置存储在版本控制系统中
3. **多环境**: 分离开发、预发布和生产环境
4. **网络隔离**: 配置适当的网络隔离和安全组
5. **最小权限原则**: 仅授予必要的最低权限

### 运维最佳实践

1. **定期备份**: 定期备份 etcd 和重要资源
2. **监控和告警**: 构建全面的监控和告警系统
3. **集中式日志**: 集中收集和分析日志
4. **自动化**: 自动化重复性任务
5. **灾难恢复规划**: 建立并测试清晰的灾难恢复计划

### 安全最佳实践

1. **定期更新**: 定期更新集群和节点
2. **网络策略**: 配置适当的网络策略
3. **加密**: 加密静态数据和传输中数据
4. **安全上下文**: 配置适当的安全上下文
5. **镜像扫描**: 扫描容器镜像中的漏洞

### 资源管理最佳实践

1. **资源请求和限制**: 为所有 Pod 设置适当的资源请求和限制
2. **Namespace 隔离**: 按 Namespace 隔离工作负载
3. **资源配额**: 为每个 Namespace 设置资源配额
4. **HPA 和 VPA**: 配置自动扩缩容
5. **节点亲和性和污点**: 优化工作负载放置

### EKS 特定最佳实践

1. **托管节点组**: 尽可能使用托管节点组
2. **Fargate**: 将 Fargate 用于无服务器工作负载
3. **EKS 附加组件**: 使用官方 EKS 附加组件
4. **IAM Roles for Service Accounts (IRSA)**: 按 Pod 管理 IAM 权限
5. **VPC CNI 自定义**: 根据网络要求配置 VPC CNI

## 结论

Kubernetes 集群管理对于维持集群稳定性、安全性和性能发挥着重要作用。本章介绍了集群管理的多个方面，包括集群组件管理、资源管理、网络、身份验证和授权管理、升级、备份和恢复、监控和日志以及故障排除。

使用 Amazon EKS 可降低 Kubernetes 控制平面管理的复杂性，并通过与 AWS 服务集成简化集群管理。但是，理解 Kubernetes 基础概念和最佳实践对于有效的集群管理仍然很重要。

集群管理是一个持续过程，必须根据集群要求和工作负载特征不断调整。使用监控工具跟踪集群状态、通过自动化减少重复性任务，并遵循最佳实践以维持集群稳定性和安全性非常重要。

## 集群网络

Kubernetes 集群网络管理 Pod 间通信、服务发现和外部访问。

### 网络架构

![架构图：集群网络分为 Pod 网络、Service 网络、Ingress 和网络策略，分别由 CNI 插件、Service 类型（ClusterIP、NodePort、LoadBalancer）、Ingress controller 和网络安全实现。](../.gitbook/assets/en-core-09-cluster-administration-9.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-9.html)

### CNI 插件管理

CNI (Container Network Interface) 插件负责 Kubernetes 集群的网络。

请选择一个 CNI，或使用有文档记录的链式/迁移设置。不得在同一运行中集群中依次安装 Calico、Flannel 和 Cilium 替代方案。请使用受支持的固定版本和提供商特定说明；在 EKS 上，请遵循[网络章节](./03-services-networking.md)中的 VPC CNI 或计划使用的替代 CNI 流程。

```bash
# Inspect the installed networking components before making changes
kubectl get daemonsets -A
kubectl get pods -A -l k8s-app=calico-node
```


### CNI 插件比较

| CNI 插件 | 网络模型 | 网络策略支持 | 性能 | 功能 |
|-----------|---------------|----------------------|-------------|----------|
| **Calico** | BGP | 是 | 高 | 强大的网络策略，基于路由 |
| **Flannel** | VXLAN/host-gateway | 否 | 中 | 设置简单，功能有限 |
| **Cilium** | eBPF | 是 | 很高 | L3-L7 策略，高性能 |
| **Weave Net** | VXLAN | 是 | 中 | 支持加密，多集群 |
| **AWS VPC CNI** | AWS VPC | 是，使用受支持版本/配置 | 取决于工作负载 | 原生 EKS 集成 |

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
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

# Check network policies
kubectl describe networkpolicy -n <namespace>
```
## 身份验证和授权管理

Kubernetes 身份验证和授权管理是集群安全的核心要素。RBAC (Role-Based Access Control) 用于管理用户和 Service Account 的权限。

### 身份验证方法

Kubernetes 支持多种身份验证方法：

1. **X.509 Certificates**: 使用客户端证书进行身份验证
2. **Service Account Tokens**: 用于 Pod 内 API server 访问
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
  name: namespace-reader
rules:
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "watch", "list"]
```

```yaml
# clusterrolebinding.yaml - binding cluster role to user
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-namespaces-global
subjects:
- kind: Group
  name: namespace-viewers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: namespace-reader
  apiGroup: rbac.authorization.k8s.io
```

### 用户证书创建

对于自行管理的客户端证书身份验证，请提交 CSR，并让有权限的审批者验证所请求的身份/组。不要分发集群 CA 私钥。EKS 用户访问应使用 IAM/access entries。

```bash
umask 077
openssl genrsa -out jane.key 2048
openssl req -new -key jane.key -out jane.csr -subj "/CN=jane/O=dev"
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: jane-csr
spec:
  request: $(base64 < jane.csr | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 86400
  usages:
  - client auth
EOF
# Authorized approver only, after reviewing the CSR identity:
kubectl certificate approve jane-csr
kubectl wait --for=jsonpath='{.status.certificate}' csr/jane-csr --timeout=60s
kubectl get csr jane-csr -o jsonpath='{.status.certificate}' | base64 --decode > jane.crt
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

# Inspect ServiceAccount metadata (projected tokens are not listed here)
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

必须进行 Kubernetes 集群升级，才能应用新功能、安全补丁和错误修复。必须谨慎规划和执行升级。

### 升级规划

![展示升级规划分为四项任务的树状图：检查版本兼容性、创建备份、选择升级策略和规划停机时间；每项任务均通向具体行动：审查 API 变更、etcd 备份、原地升级与蓝绿部署的选择，以及用户沟通。](../.gitbook/assets/en-core-09-cluster-administration-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-10.html)

### 升级策略比较

| 策略 | 描述 | 优点 | 缺点 | 适用环境 |
|----------|-------------|------------|---------------|---------------------|
| **原地升级** | 直接升级现有集群 | 资源高效，流程简单 | 回滚复杂，可能停机 | 开发、测试环境 |
| **蓝绿部署** | 创建新版本集群并切换 | 回滚安全，可验证 | 资源重复，成本增加 | 生产环境 |
| **金丝雀部署** | 仅将部分工作负载迁移到新集群 | 逐步验证，风险降低 | 管理复杂，双重运行 | 关键生产环境 |

### 使用 kubeadm 升级

请使用[特定版本的 kubeadm 升级流程](https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/)。启用目标次要版本的 pkgs.k8s.io 仓库，并选择已发布的准确软件包版本；每次只升级一个次要版本。

1. 备份 etcd 并验证工作负载/附加组件兼容性。在第一个控制平面节点上升级 kubeadm，运行 `kubeadm upgrade plan`，然后运行 `kubeadm upgrade apply <target-version>`。
2. 在其他控制平面节点上，升级 kubeadm 并运行 `kubeadm upgrade node`。
3. 升级 kubelet 前，先 drain 每个节点。如果 drain 失败，停止流程并解决原因。将 kubelet/kubectl 升级到兼容版本，重新加载 systemd，重启 kubelet，验证 Ready 和工作负载，然后从管理客户端 uncordon。
4. 在每个工作节点上，升级 kubeadm 并运行 `kubeadm upgrade node`，然后执行 drain/kubelet/验证/uncordon 序列。不要以通用的全系统升级替代 Kubernetes 特定版本升级流程。

请在明确指定的节点或管理客户端上运行命令；一系列嵌套的 `ssh` 会话不是多节点自动化脚本。

### 升级后验证

```bash
# Check cluster version
kubectl version

# Check node versions
kubectl get nodes

# Check component status
kubectl get --raw='/readyz?verbose'

# Check workload status
kubectl get pods -A
```
## 备份和恢复

Kubernetes 集群备份和恢复是灾难恢复规划的重要组成部分。主要备份目标是 etcd 数据库、持久卷数据和 Kubernetes 资源定义。

### etcd 备份和恢复

etcd 是存储集群所有状态信息的核心组件。

对于自行管理的灾难恢复，请使用特定发行版的操作手册停止所有 API server 和受影响的 etcd 进程。仅停止 kubelet 不会停止现有的静态 Pod 容器。请使用兼容的 etcdutl 恢复到新目录；在验证恢复之前保留原始数据。此单成员命令只是示例，而不是多成员 HA 恢复：

```bash
etcdutl snapshot status "$SNAPSHOT_FILE" --write-out=table
etcdutl snapshot restore "$SNAPSHOT_FILE" \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://127.0.0.1:2380 \
  --initial-cluster-token=restored-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380 \
  --bump-revision=1000000000 --mark-compacted
```

将 SNAPSHOT_FILE 设置为已验证的快照。对于 HA，在每个成员上恢复同一快照，但使用其唯一名称/对等 URL 和相同的完整成员列表。选择超过快照后变更量的修订号增量。使用正确的所有权和证书更新 etcd 清单/服务到恢复路径，验证 quorum/health，然后重启 API server/controller。请参阅[官方恢复指南](https://etcd.io/docs/v3.6/op-guide/recovery/)。EKS 用户无法直接恢复托管控制平面 etcd。

### Kubernetes 资源备份

```bash
# Export selected resources, not a full cluster backup
set -eu
umask 077
mkdir -p /backup/resources/$(date +%Y-%m-%d)
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl -n $ns get all -o yaml > /backup/resources/$(date +%Y-%m-%d)/$ns-all.yaml
done

# Backup specific resource types
for resource in deployments services configmaps secrets; do
  kubectl get $resource -A -o yaml > /backup/resources/$(date +%Y-%m-%d)/$resource.yaml
done
```

### 使用 Velero 备份和恢复

请使用官方矩阵选择兼容的 Velero/AWS 插件版本。IRSA 示例假定已配置集群 OIDC provider，并且存在一个信任 velero ServiceAccount 的范围受限角色。请在安装前配置备份 bucket、卷快照/文件备份支持、加密和恢复权限；并非每个 PVC 都会自动受到保护。

Velero 是用于备份和恢复 Kubernetes 集群资源及持久卷的工具。

```bash
# Install Velero (using AWS S3 backup storage)
velero install \
  --provider aws \
  --plugins "${VELERO_AWS_PLUGIN_IMAGE:?Select a plugin compatible with your Velero release}" \
  --bucket velero-backup \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --no-secret \
  --sa-annotations "eks.amazonaws.com/role-arn=${VELERO_ROLE_ARN:?Set the preconfigured IRSA role ARN}"

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
| **etcd Snapshot** | 集群状态 | 内置功能，完整状态保留 | 不包含卷数据，手动流程 | 中等 |
| **Resource YAML Backup** | Kubernetes 对象 | 实现简单，可选择性恢复 | 不包含卷数据，关系复杂 | 慢 |
| **Velero** | 资源和卷 | 自动化、调度、卷快照 | 需要额外安装工具 | 快 |
| **Cloud Provider Snapshots** | 受支持的磁盘/文件系统 | 后端原生恢复点 | 不会捕获整个 Kubernetes/EKS 集群 | 取决于数据/后端 |
## 监控和日志

有效的集群管理需要全面的监控和日志系统。这可以及早发现并解决问题。

### 监控架构

![架构图：Kubernetes 监控分为指标收集、日志收集、告警和可视化，分别由 Prometheus（搭配 kube-state-metrics 和 node-exporter）、将日志发送到 Elasticsearch 和 Kibana 的 Fluentd/Fluent Bit、Alertmanager 和 Grafana 处理。](../.gitbook/assets/en-core-09-cluster-administration-11.png)

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
  --set prometheus.service.type=ClusterIP

# Check services
kubectl get svc -n monitoring

# Access Grafana (using port forwarding)
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
# Obtain credentials from the configured Grafana Secret; do not assume a published default password
```

### EFK Stack 安装（Elasticsearch、Fluentd、Kibana）

独立的 Elastic Stack Helm chart 仓库已归档。若要进行受维护的部署，请使用 Elastic Cloud on Kubernetes (ECK)，然后定义 Elasticsearch/Kibana 资源和兼容的日志收集器。仅安装 operator 不会创建 EFK Stack：

```bash
helm repo add elastic https://helm.elastic.co
helm upgrade --install elastic-operator elastic/eck-operator \
  --namespace elastic-system --create-namespace \
  --version "${ECK_CHART_VERSION:?Select a supported ECK chart version}"
```

将仪表板置于 ClusterIP/已验证访问之后；请按照 [ECK 指南](https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s/install-using-helm-chart)配置存储、TLS、凭证、收集器解析和 RBAC。

### 关键监控指标

| 指标类型 | 描述 | 关键指标 | 监控工具 |
|-------------|-------------|-------------|-----------------|
| **节点指标** | 节点级资源使用情况 | CPU、内存、磁盘、网络 | node-exporter、Prometheus |
| **Pod 指标** | 容器资源使用情况 | CPU、内存使用率、限制 | cAdvisor、Prometheus |
| **集群指标** | 集群状态和资源 | Pod 数量、节点/对象状态、期望/当前副本数 | kube-state-metrics |
| **应用程序指标** | 自定义应用程序指标 | 请求数、延迟、错误率 | Prometheus 客户端库 |

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

您可以使用 Prometheus Alertmanager 配置告警：

在 monitoring 中创建一个受保护、键为 `url` 的 `slack-webhook` Secret，然后将这些 Helm values 合并到现有 kube-prometheus-stack release 中。不要提交 webhook URL。独立的 ConfigMap 不会被 operator 自动使用。

```yaml
# alertmanager-values.yaml
alertmanager:
  alertmanagerSpec:
    secrets:
    - slack-webhook
  config:
    global:
      resolve_timeout: 5m
      slack_api_url_file: /etc/alertmanager/secrets/slack-webhook/url
    route:
      receiver: slack-notifications
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      group_by: [alertname, cluster, service]
    receivers:
    - name: slack-notifications
      slack_configs:
      - channel: '#alerts'
        send_resolved: true
        title: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

升级时请保留当前 chart 版本和其他 values；在依赖通知前，请验证 Alertmanager reload/status。
## 故障排除

Kubernetes 集群故障排除是系统管理员和运维人员的重要技能。有效的故障排除需要系统化的方法。

### 故障排除方法

![展示从问题识别到文档记录的六步故障排除序列的工作流图，其中信息收集步骤分支到日志、事件和资源状态检查。](../.gitbook/assets/en-core-09-cluster-administration-12.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-12.html)

### 常见问题和解决方案

| 问题类型 | 症状 | 诊断命令 | 常见解决方案 |
|-------------|----------|---------------------|-----------------|
| **Pod 未启动** | Pod 处于 Pending 或 ContainerCreating 状态 | `kubectl describe pod <pod-name>` | 检查资源限制、镜像可用性、卷挂载 |
| **Service 连接问题** | 无法通过 Service 访问 Pod | `kubectl describe svc <service-name>`, `kubectl get endpointslices -l kubernetes.io/service-name=<service-name>` | 检查标签选择器、Pod 状态、网络策略 |
| **节点问题** | 节点处于 NotReady 状态 | `kubectl describe node <node-name>`, `kubectl get events` | 检查 kubelet 状态、系统资源、网络连通性 |
| **DNS 问题** | 无法通过 Service 名称连接 | `kubectl exec -it <pod-name> -- nslookup kubernetes.default` | 检查 CoreDNS Pod、kube-dns Service、网络策略 |
| **身份验证/授权问题** | API server 拒绝访问 | `kubectl auth can-i <verb> <resource>` | 检查 RBAC 设置、证书有效性、Service Account |

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

### 节点故障排除

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
kubectl get endpointslices -l kubernetes.io/service-name=<service-name>

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

Amazon EKS (Elastic Kubernetes Service) 是 AWS 上的托管 Kubernetes 服务，其中 AWS 管理控制平面。客户对节点的责任取决于托管节点组、Auto Mode、Fargate 或自行管理的计算；工作负载安全和配置仍是客户责任。

### EKS 集群架构

![架构图：Amazon EKS 集群分为 AWS 管理的控制平面（API server、etcd、scheduler）和客户责任区域，后者包括数据平面（托管节点组及 EC2 Auto Scaling 组、自行管理节点、Fargate）、网络（VPC CNI 和 AWS VPC）和安全（使用 IAM roles 和 policies 的 IAM 身份验证）。](../.gitbook/assets/en-core-09-cluster-administration-13.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-09-cluster-administration-13.html)

### EKS 集群创建

```bash
# Create cluster using eksctl
eksctl create cluster \
  --name my-cluster \
  --version 1.36 \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 5 \
  --managed

# Alternative: create control plane using AWS CLI (not after the eksctl example)
aws eks create-cluster \
  --name my-cluster \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --kubernetes-version 1.36 \
  --resources-vpc-config "subnetIds=${EKS_SUBNET_IDS:?Set two or more appropriate subnets},securityGroupIds=${EKS_SECURITY_GROUP_ID:?Set the intended security group},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${ADMIN_CIDR:?Set an approved administrator public CIDR}"
```

### 节点组管理

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
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup \
  --region us-west-2
```

### EKS 集群升级

```bash
# Check cluster version
aws eks describe-cluster --name my-cluster --query "cluster.version"

# Upgrade cluster control plane
aws eks update-cluster-version \
  --name my-cluster \
  --kubernetes-version "${TARGET_VERSION:?Select the next EKS-supported minor version}"

# Upgrade managed node group
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name my-nodegroup
```

### EKS 集群身份验证和授权

集群必须使用 `API` 或 `API_AND_CONFIG_MAP` 身份验证模式。在保留现有管理员/节点访问权限的同时，规划从旧版 aws-auth 映射的迁移。此示例仅授予查看者角色访问 default Namespace 的权限：

```bash
aws eks describe-cluster --name my-cluster --query cluster.accessConfig.authenticationMode
aws eks create-access-entry --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/cluster-viewer --type STANDARD
aws eks associate-access-policy --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/cluster-viewer \
  --policy-arn arn:aws:eks::aws:cluster-access-policy/AmazonEKSViewPolicy \
  --access-scope type=namespace,namespaces=default
```

请参阅 [EKS access-entry 指南](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)。管理 EKS access entries 的权限与 Kubernetes 工作负载权限是分开的。

### EKS 集群监控

控制平面日志会导出 api/audit/authenticator/controllerManager/scheduler 日志。Container Insights 需要 CloudWatch agent/附加组件和范围受限的遥测 IAM 权限；它不会通过 update-cluster-logging 启用。CloudWatch observability 附加组件安装 CloudWatch/Fluent Bit 组件，而不是 Prometheus/Grafana。请参阅[官方附加组件设置](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)。

```bash
# Enable EKS control-plane logs
eksctl utils update-cluster-logging \
  --enable-types all \
  --cluster my-cluster \
  --region us-west-2

# Install CloudWatch observability (not Prometheus/Grafana)
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability \
  --addon-version "${CLOUDWATCH_ADDON_VERSION:?Select a compatible add-on version}"
```
## 集群管理最佳实践

有效 Kubernetes 集群管理的最佳实践对于确保稳定性、安全性和性能很重要。

### 集群设置最佳实践

1. **多可用区配置**: 将节点分布在多个可用区以实现高可用性
2. **适当的规模**: 选择适合工作负载的节点类型和数量
3. **自动扩缩容配置**: 启用 cluster autoscaler 和 horizontal pod autoscaler
4. **应用网络策略**: 从默认拒绝策略开始，只允许必要通信
5. **设置资源配额**: 为每个 Namespace 设置资源限制

### 运维最佳实践

1. **使用声明式配置**: 将所有资源定义为 YAML 文件并进行版本控制
2. **采用 GitOps**: 使用 Git 作为唯一事实来源，并构建自动化部署流水线
3. **定期备份**: 定期备份 etcd 数据和持久卷数据
4. **监控和告警**: 构建全面的监控系统，并为关键指标设置告警
5. **集中式日志**: 将所有日志收集到集中式日志系统中以便分析

### 安全最佳实践

1. **最小权限原则**: 使用 RBAC 仅授予最低必要权限
2. **网络分段**: 使用网络策略限制 Pod 间通信
3. **镜像扫描**: 实施容器镜像扫描以检测漏洞
4. **Secret 管理**: 使用外部 Secret 管理工具（例如 AWS Secrets Manager、HashiCorp Vault）
5. **定期安全审计**: 定期审计集群配置和权限

### 升级最佳实践

1. **渐进式升级**: 逐步升级，而非一次性升级
2. **先在测试环境验证**: 在生产环境之前于测试环境中验证升级
3. **创建备份**: 升级前执行完整备份
4. **回滚计划**: 制定出现问题时回滚到先前版本的计划
5. **设置升级窗口**: 在低使用率时段执行升级

### 成本优化最佳实践

1. **选择适当的节点大小**: 为工作负载选择最佳节点类型
2. **利用 Spot Instances**: 将 Spot Instances 用于非关键工作负载
3. **配置自动扩缩容**: 根据需求配置自动扩容和缩容
4. **优化资源请求和限制**: 根据实际使用情况设置资源请求和限制
5. **识别空闲资源**: 定期识别并移除空闲资源

### 文档最佳实践

1. **记录架构**: 记录集群架构、网络和安全设置
2. **记录运维流程**: 记录常见运维任务、故障排除流程和紧急响应计划
3. **变更管理**: 记录并跟踪所有集群变更
4. **创建 Runbook**: 为常见场景提供分步指南
5. **知识共享**: 在团队内定期开展知识共享和培训活动
## 结论

Kubernetes 集群管理是一项包含多个方面的复杂任务。从集群设置到运维、监控、故障排除和升级，都需要系统化的方法。

要实现有效的集群管理，请重点关注以下关键领域：

1. **集群组件管理**: 控制平面和节点组件的稳定运行
2. **资源管理**: 高效的资源分配和使用
3. **网络**: 安全高效的网络配置
4. **安全**: 适当的身份验证和授权管理
5. **备份和恢复**: 防止数据丢失和进行灾难恢复规划
6. **监控和日志**: 集群状态和性能监控
7. **故障排除**: 系统化的故障排除方法

使用 Amazon EKS 等托管 Kubernetes 服务时，理解服务提供商与用户之间的共同责任模型非常重要。AWS 管理控制平面，而计算责任因模式而异；客户仍管理应用程序配置和安全性。

通过遵循最佳实践并利用适当工具，您可以运行稳定、安全且高效的 Kubernetes 集群。持续学习和改进以增强集群管理能力非常重要。

---

> **参考资料**:
> - [Kubernetes 官方文档：集群管理](https://kubernetes.io/docs/tasks/administer-cluster/)
> - [Amazon EKS 用户指南](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
> - [Kubernetes 最佳实践：集群管理](https://kubernetes.io/docs/setup/best-practices/)
> - [etcd 文档：备份和恢复](https://etcd.io/docs/v3.5/op-guide/recovery/)
> - [Prometheus 文档](https://prometheus.io/docs/introduction/overview/)

## 测验

要测试您在本章中所学的内容，请尝试[集群管理测验](../quizzes/core/09-cluster-administration-quiz.md)。
