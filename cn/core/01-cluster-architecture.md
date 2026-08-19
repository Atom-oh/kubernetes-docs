# 集群架构

> **支持的版本**：Kubernetes 1.32、1.33、1.34
> **最后更新**：August 10, 2026

## 实验环境设置

要练习本文档中的概念，你需要以下工具和环境：

### 必需工具
- kubectl v1.34 或更高版本
- 一个可用的 Kubernetes 集群（EKS、minikube、kind 等）

### 本地开发环境设置

```bash
# Install minikube (for local development)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start cluster
minikube start

# Check cluster status
kubectl cluster-info

# Check control plane components
kubectl get pods -n kube-system
```

## 集群架构概览

> **核心概念**：Kubernetes 集群由控制平面和工作节点组成，每个部分均由执行特定职责的多个组件构成。

Kubernetes 集群由一组用于运行容器化应用程序的节点（虚拟机或物理机）组成。集群大致分为控制平面和工作节点。

### 集群架构图

```mermaid
graph TD
    subgraph "Kubernetes Cluster"
        subgraph "Control Plane"
            API[kube-apiserver]
            ETCD[etcd]
            SCHED[kube-scheduler]
            CM[kube-controller-manager]
            CCM[cloud-controller-manager]

            API <--> ETCD
            API <--> SCHED
            API <--> CM
            API <--> CCM
        end

        subgraph "Worker Node 1"
            KUBELET1[kubelet]
            PROXY1[kube-proxy]
            CRI1[Container Runtime]

            POD1A[Pod A]
            POD1B[Pod B]

            KUBELET1 --> CRI1
            CRI1 --> POD1A
            CRI1 --> POD1B
            PROXY1 --> POD1A
            PROXY1 --> POD1B
        end

        subgraph "Worker Node 2"
            KUBELET2[kubelet]
            PROXY2[kube-proxy]
            CRI2[Container Runtime]

            POD2A[Pod C]
            POD2B[Pod D]

            KUBELET2 --> CRI2
            CRI2 --> POD2A
            CRI2 --> POD2B
            PROXY2 --> POD2A
            PROXY2 --> POD2B
        end

        API <--> KUBELET1
        API <--> KUBELET2
        API <--> PROXY1
        API <--> PROXY2
    end

    %% Style definitions
    classDef controlPlane fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef nodeComponent fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef pod fill:#E83E8C,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class API,SCHED,CM,CCM controlPlane;
    class ETCD dataStore;
    class KUBELET1,KUBELET2,PROXY1,PROXY2,CRI1,CRI2 nodeComponent;
    class POD1A,POD1B,POD2A,POD2B pod;
```

**控制平面组件**：
- **kube-apiserver**：暴露 Kubernetes API 的前端
- **etcd**：存储所有集群数据的键值存储
- **kube-scheduler**：选择用于运行新创建 Pod 的节点
- **kube-controller-manager**：运行用于管理集群状态的控制器
- **cloud-controller-manager**：与云提供商 API 交互

**工作节点组件**：
- **kubelet**：运行在每个节点上的代理，管理容器执行
- **kube-proxy**：维护网络规则并执行连接转发
- **Container Runtime**：运行容器（containerd、CRI-O 等）

## 控制平面组件

控制平面充当 Kubernetes 集群的“中枢”，管理和控制集群的整体状态。控制平面组件通常运行在专用机器上，并可复制为多个实例以实现高可用性。

### 控制平面组件详情

| 组件 | 主要功能 | 通信目标 | 高可用性配置 |
|-----------|---------------|----------------------|--------------------------------|
| **kube-apiserver** | - 提供 Kubernetes API<br>- 身份验证和授权<br>- API 请求处理 | - 所有组件<br>- etcd | 通过多个实例进行水平扩展 |
| **etcd** | - 存储集群数据<br>- 分布式键值存储<br>- 确保一致性 | - kube-apiserver | 多节点集群 |
| **kube-scheduler** | - Pod 放置决策<br>- 评估节点资源<br>- 应用亲和性/反亲和性 | - kube-apiserver | 主备配置 |
| **kube-controller-manager** | - 节点控制器<br>- 副本控制器<br>- Endpoint 控制器<br>- Service Account 控制器 | - kube-apiserver | 主备配置 |
| **cloud-controller-manager** | - 云提供商集成<br>- 节点生命周期<br>- 路由和负载均衡 | - kube-apiserver<br>- 云 API | 主备配置 |

### 控制平面通信流程

1. 用户或控制器向 kube-apiserver 发送请求
2. kube-apiserver 执行身份验证、授权和准入
3. kube-apiserver 从 etcd 读取数据或向其写入数据
4. 控制器和调度器通过 kube-apiserver 监视集群状态
5. kubelet 向 kube-apiserver 报告节点状态

### kube-apiserver

kube-apiserver 是暴露 Kubernetes API 的控制平面前端。所有内部和外部请求均通过此 API 服务器处理。

**主要功能**：
- 提供 REST API
- 身份验证和授权
- 请求验证和处理
- 与 etcd 通信
- 可水平扩展（可扩展到多个实例）

**主要标志和配置选项**：
```bash
# Basic configuration example
kube-apiserver \
  --advertise-address=192.168.1.10 \
  --allow-privileged=true \
  --authorization-mode=Node,RBAC \
  --enable-admission-plugins=NodeRestriction \
  --enable-bootstrap-token-auth=true \
  --etcd-servers=https://127.0.0.1:2379 \
  --kubelet-client-certificate=/etc/kubernetes/pki/apiserver-kubelet-client.crt \
  --kubelet-client-key=/etc/kubernetes/pki/apiserver-kubelet-client.key \
  --service-account-key-file=/etc/kubernetes/pki/sa.pub \
  --service-cluster-ip-range=10.96.0.0/12 \
  --tls-cert-file=/etc/kubernetes/pki/apiserver.crt \
  --tls-private-key-file=/etc/kubernetes/pki/apiserver.key
```

**API Server 安全性**：
- 通过 TLS 证书进行安全通信
- 支持多种身份验证方法（X.509 证书、Service Account token、OIDC、webhook 等）
- 通过 RBAC（基于角色的访问控制）进行权限管理
- 通过准入控制器进行请求验证和修改

### etcd

etcd 是一个一致且高可用的键值存储，用于保存所有集群数据。它是 Kubernetes 的“事实来源”。

**主要特性**：
- 分布式系统
- 强一致性（使用 Raft 共识算法）
- 高可用性（可配置多个节点）
- 安全的数据存储
- 用于监控变更的 Watch 功能

**etcd 集群配置**：
```bash
# etcd cluster configuration example (3 nodes)
etcd \
  --name etcd-1 \
  --initial-advertise-peer-urls https://192.168.1.11:2380 \
  --listen-peer-urls https://192.168.1.11:2380 \
  --listen-client-urls https://192.168.1.11:2379,https://127.0.0.1:2379 \
  --advertise-client-urls https://192.168.1.11:2379 \
  --initial-cluster-token etcd-cluster \
  --initial-cluster etcd-1=https://192.168.1.11:2380,etcd-2=https://192.168.1.12:2380,etcd-3=https://192.168.1.13:2380 \
  --initial-cluster-state new \
  --data-dir=/var/lib/etcd
```

**etcd 备份和恢复**：
```bash
# etcd backup
ETCDCTL_API=3 etcdctl snapshot save snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# etcd recovery
ETCDCTL_API=3 etcdctl snapshot restore snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-1 \
  --initial-cluster=etcd-1=https://192.168.1.11:2380 \
  --initial-cluster-token=etcd-cluster \
  --initial-advertise-peer-urls=https://192.168.1.11:2380
```

**etcd 性能优化**：
- 磁盘 I/O 优化（推荐 SSD）
- 合理分配内存
- 定期压缩和碎片整理
- 根据集群规模配置适当数量的 etcd 节点（通常为 3 或 5 个）

#### 2026 年 7 月更新：etcd v3.7.0 发布

2026 年 7 月 8 日，SIG etcd 发布了 etcd v3.7.0。亮点包括：

- **RangeStream**：以分块方式流式传输大型范围查询结果，而非在内存中缓冲整个响应（这是一项长期期待的功能）
- **性能改进**：优化了仅键范围请求，租约更快、更可靠
- 移除了旧版 v2store 的最后残余部分，并完成了重大的 protobuf 改造
- 包含更新后的核心依赖项 bbolt v1.5.0 和 raft v3.7.0

有关详细信息，请参阅[官方公告](https://kubernetes.io/blog/2026/07/08/announcing-etcd-3.7/)和 [etcd v3.7 变更日志](https://github.com/etcd-io/etcd/blob/main/CHANGELOG/CHANGELOG-3.7.md)。

### kube-scheduler

kube-scheduler 是选择节点来运行新创建 Pod 的控制平面组件。

**调度过程**：
1. **过滤**：识别可以运行 Pod 的节点
   - 资源要求（CPU、内存）
   - 节点选择器、节点亲和性
   - 污点和容忍度
   - Volume 约束

2. **评分**：为合适的节点分配分数
   - 资源利用率
   - Pod 间亲和性/反亲和性
   - 数据本地性
   - 节点间负载均衡

3. **绑定**：将 Pod 分配给最优节点

**调度器配置**：
```bash
# Basic configuration example
kube-scheduler \
  --kubeconfig=/etc/kubernetes/scheduler.conf \
  --leader-elect=true \
  --v=2
```

**调度器配置文件和插件**：
- 默认调度器配置文件
- 自定义调度器配置文件
- 调度器扩展点（过滤、评分、绑定等）
- 多调度器支持

**调度策略**：
```yaml
# Scheduling policy example
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: default-scheduler
  plugins:
    score:
      disabled:
      - name: NodeResourcesLeastAllocated
      enabled:
      - name: NodeResourcesMostAllocated
        weight: 1
```

### kube-controller-manager

kube-controller-manager 是运行多个控制器进程的控制平面组件。每个控制器管理集群的特定方面。

**主要控制器**：
- **Node Controller**：监控和响应节点状态
- **Replication Controller**：维护 Pod 副本数量
- **Endpoint Controller**：连接 Service 和 Pod
- **Service Account & Token Controller**：为 namespace 创建默认账户和 API token
- **Job Controller**：管理一次性任务
- **CronJob Controller**：管理定时任务
- **DaemonSet Controller**：确保特定 Pod 在所有节点上运行
- **StatefulSet Controller**：管理有状态应用程序
- **PV Controller**：管理持久卷
- **Namespace Controller**：管理 namespace 生命周期
- **Garbage Collector**：清理孤立对象

**Controller Manager 配置**：
```bash
# Basic configuration example
kube-controller-manager \
  --kubeconfig=/etc/kubernetes/controller-manager.conf \
  --leader-elect=true \
  --use-service-account-credentials=true \
  --root-ca-file=/etc/kubernetes/pki/ca.crt \
  --service-account-private-key-file=/etc/kubernetes/pki/sa.key \
  --cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt \
  --cluster-signing-key-file=/etc/kubernetes/pki/ca.key \
  --controllers=*,bootstrapsigner,tokencleaner
```

**控制器运行方式**：
1. 控制器通过 API server 持续监视集群状态
2. 检测当前状态与期望状态之间的差异
3. 执行操作以协调该差异
4. 向 API server 报告状态变更

### cloud-controller-manager

cloud-controller-manager 是包含云特定控制逻辑的控制平面组件。这使得 Kubernetes 核心与云提供商 API 能够分离。

**主要控制器**：
- **Node Controller**：通过云提供商 API 检查节点状态
- **Route Controller**：在云环境中配置路由
- **Service Controller**：创建、更新和删除云负载均衡器
- **Volume Controller**：创建、附加和挂载云存储卷

**云提供商实现**：
- AWS Cloud Controller Manager
- Azure Cloud Controller Manager
- GCP Cloud Controller Manager
- OpenStack Cloud Controller Manager
- vSphere Cloud Controller Manager

**Cloud Controller Manager 配置**：
```bash
# AWS Cloud Controller Manager example
cloud-controller-manager \
  --cloud-provider=aws \
  --cloud-config=/etc/kubernetes/cloud-config \
  --kubeconfig=/etc/kubernetes/cloud-controller-manager.conf \
  --leader-elect=true
```

**Cloud Controller Manager 的优势**：
- 将云提供商特定代码与 Kubernetes 核心分离
- 云提供商可独立开发自己的功能
- 无需修改 Kubernetes 核心即可添加云功能

## 节点组件

节点是在 Kubernetes 集群中运行容器化应用程序的工作机器。每个节点均由控制平面管理，并由多个组件构成。

### kubelet

kubelet 是运行在每个节点上的代理，用于管理 Pod 内的容器。kubelet 通过多种机制接收 PodSpec，并确保容器按照这些规格健康运行。

**主要功能**：
- 根据 PodSpec 运行容器
- 监控和报告容器状态
- 管理容器生命周期
- 管理 Volume 挂载
- 报告节点状态
- 执行容器健康检查

**kubelet 配置**：
```bash
# Basic configuration example
kubelet \
  --kubeconfig=/etc/kubernetes/kubelet.conf \
  --config=/var/lib/kubelet/config.yaml \
  --container-runtime=remote \
  --container-runtime-endpoint=unix:///var/run/containerd/containerd.sock \
  --pod-infra-container-image=k8s.gcr.io/pause:3.6
```

**kubelet 配置文件示例**：
```yaml
# /var/lib/kubelet/config.yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
address: 0.0.0.0
authentication:
  anonymous:
    enabled: false
  webhook:
    cacheTTL: 2m0s
    enabled: true
  x509:
    clientCAFile: /etc/kubernetes/pki/ca.crt
authorization:
  mode: Webhook
  webhook:
    cacheAuthorizedTTL: 5m0s
    cacheUnauthorizedTTL: 30s
cgroupDriver: systemd
clusterDomain: cluster.local
cpuManagerPolicy: none
evictionHard:
  memory.available: 100Mi
  nodefs.available: 10%
  nodefs.inodesFree: 5%
failSwapOn: true
healthzBindAddress: 127.0.0.1
healthzPort: 10248
```

**静态 Pod**：
kubelet 可以运行由其直接管理、无需经过 API server 的静态 Pod。这主要用于运行控制平面组件。

```yaml
# /etc/kubernetes/manifests/kube-apiserver.yaml
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
  namespace: kube-system
spec:
  containers:
  - name: kube-apiserver
    image: k8s.gcr.io/kube-apiserver:v1.24.0
    command:
    - kube-apiserver
    - --advertise-address=192.168.1.10
    # ... additional flags
```

### kube-proxy

kube-proxy 是运行在每个节点上的网络代理，用于实现 Kubernetes Service 概念。它维护节点上的网络规则并执行连接转发。

**主要功能**：
- 维护 Service IP 和端口的网络规则
- 连接转发
- 实现负载均衡
- 支持服务发现

**运行模式**：
1. **userspace mode**：在用户空间运行代理（旧版）
2. **iptables mode**：使用 Linux iptables 实现 NAT（默认）
3. **IPVS mode**：使用 Linux 内核的 IP Virtual Server（高性能）

**kube-proxy 配置**：
```bash
# Basic configuration example
kube-proxy \
  --config=/var/lib/kube-proxy/config.conf \
  --hostname-override=node1
```

**kube-proxy 配置文件示例**：
```yaml
# /var/lib/kube-proxy/config.conf
apiVersion: kubeproxy.config.k8s.io/v1alpha1
kind: KubeProxyConfiguration
bindAddress: 0.0.0.0
clientConnection:
  acceptContentTypes: ""
  burst: 10
  contentType: application/vnd.kubernetes.protobuf
  kubeconfig: /var/lib/kube-proxy/kubeconfig.conf
  qps: 5
clusterCIDR: 10.244.0.0/16
configSyncPeriod: 15m0s
conntrack:
  maxPerCore: 32768
  min: 131072
  tcpCloseWaitTimeout: 1h0m0s
  tcpEstablishedTimeout: 24h0m0s
enableProfiling: false
healthzBindAddress: 0.0.0.0:10256
hostnameOverride: node1
iptables:
  masqueradeAll: false
  masqueradeBit: 14
  minSyncPeriod: 0s
  syncPeriod: 30s
ipvs:
  excludeCIDRs: null
  minSyncPeriod: 0s
  scheduler: ""
  syncPeriod: 30s
mode: "iptables"
```

**IPVS 与 iptables 模式比较**：

| 特征 | iptables 模式 | IPVS 模式 |
|----------------|---------------|-----------|
| 性能 | Service 较多时性能下降 | 大型集群中性能更佳 |
| 负载均衡算法 | 仅支持轮询 | 支持多种算法（rr、lc、dh、sh、sed、nq） |
| 实现方式 | 网络数据包过滤链 | 基于哈希表 |
| 内核要求 | 默认内核模块 | 需要 IPVS 内核模块 |

### Container Runtime

Container Runtime 是运行容器的软件。Kubernetes 通过 Container Runtime Interface（CRI）支持多种 Container Runtime。

**主要 Container Runtime**：
1. **containerd**：轻量级 Container Runtime（目前使用最广泛）
2. **CRI-O**：专为 Kubernetes 设计的轻量级 Runtime
3. **Docker Engine**：通过 Docker shim 支持（自 Kubernetes 1.24 起已弃用）

**Container Runtime 分层结构**：

```mermaid
graph TD
    classDef k8s fill:#e3f2fd,stroke:#1976d2,stroke-width:1px;
    classDef cri fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;
    classDef runtime fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;
    classDef lowlevel fill:#ffcdd2,stroke:#d32f2f,stroke-width:1px;

    K8S[Kubernetes] --> CRI[Container Runtime Interface]
    CRI --> CD[containerd]
    CRI --> CRIO[CRI-O]
    CD --> RUNC[runc]
    CRIO --> CRUN[crun]

    class K8S k8s;
    class CRI cri;
    class CD,CRIO runtime;
    class RUNC,CRUN lowlevel;
```

**containerd 配置示例**：
```toml
# /etc/containerd/config.toml
version = 2

[plugins]
  [plugins."io.containerd.grpc.v1.cri"]
    sandbox_image = "k8s.gcr.io/pause:3.6"
    [plugins."io.containerd.grpc.v1.cri".containerd]
      default_runtime_name = "runc"
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
          runtime_type = "io.containerd.runc.v2"
          [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
            SystemdCgroup = true
```

**CRI-O 配置示例**：
```toml
# /etc/crio/crio.conf
[crio]
root = "/var/lib/containers/storage"
runroot = "/var/run/containers/storage"
storage_driver = "overlay"
storage_option = ["overlay.mountopt=nodev"]

[crio.runtime]
default_runtime = "runc"
conmon = "/usr/bin/conmon"
conmon_cgroup = "pod"
cgroup_manager = "systemd"

[crio.image]
pause_image = "k8s.gcr.io/pause:3.6"
```

### 附加组件

附加组件是扩展 Kubernetes 集群功能的额外组件。一些重要的附加组件包括：

1. **CNI 网络插件**：实现 Pod 网络
   - Calico、Cilium、Flannel、Weave Net 等

2. **DNS**：在集群内提供 DNS 服务
   - CoreDNS（默认）

3. **Dashboard**：提供基于 Web 的 UI
   - Kubernetes Dashboard

4. **Ingress Controller**：管理 HTTP/HTTPS 路由
   - NGINX Ingress Controller、Traefik、HAProxy 等

5. **Metrics Server**：收集资源使用指标
   - Metrics Server

6. **日志和监控**：日志收集和监控
   - Prometheus、Grafana、Elasticsearch、Fluentd、Kibana 等

**CoreDNS 配置示例**：
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
        forward . /etc/resolv.conf {
            max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
```

**Calico CNI 配置示例**：
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-config
  namespace: kube-system
data:
  calico_backend: "bird"
  cni_network_config: |-
    {
      "name": "k8s-pod-network",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "calico",
          "log_level": "info",
          "datastore_type": "kubernetes",
          "nodename": "__KUBERNETES_NODE_NAME__",
          "mtu": __CNI_MTU__,
          "ipam": {
            "type": "calico-ipam"
          },
          "policy": {
            "type": "k8s"
          },
          "kubernetes": {
            "kubeconfig": "__KUBECONFIG_FILEPATH__"
          }
        },
        {
          "type": "portmap",
          "snat": true,
          "capabilities": {"portMappings": true}
        }
      ]
    }
```

## 集群通信路径

Kubernetes 集群内的各类组件之间会发生通信。了解这些通信路径对于集群设计、安全性和故障排除至关重要。

### 控制平面内部通信

```mermaid
graph LR
    classDef apiserver fill:#bbdefb,stroke:#1976d2,stroke-width:2px;
    classDef etcd fill:#e8eaf6,stroke:#3f51b5,stroke-width:1px;
    classDef controller fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;
    classDef scheduler fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;

    API[kube-apiserver] <--> ETCD[etcd]
    SCHED[kube-scheduler] --> API
    CTRL[kube-controller-manager] --> API
    CCM[cloud-controller-manager] --> API

    class API apiserver;
    class ETCD etcd;
    class CTRL,CCM controller;
    class SCHED scheduler;
```

控制平面组件之间的通信如下：

1. **kube-apiserver 和 etcd**：kube-apiserver 与 etcd 通信以存储和检索集群状态。
   - 协议：gRPC
   - 端口：2379/TCP
   - 安全性：基于 TLS 证书的身份验证

2. **kube-scheduler 和 kube-apiserver**：kube-scheduler 与 kube-apiserver 通信以进行 Pod 调度。
   - 协议：HTTPS
   - 端口：6443/TCP（kube-apiserver）
   - 安全性：基于 TLS 证书的身份验证

3. **kube-controller-manager 和 kube-apiserver**：控制器与 kube-apiserver 通信以监视和修改集群状态。
   - 协议：HTTPS
   - 端口：6443/TCP（kube-apiserver）
   - 安全性：基于 TLS 证书的身份验证

4. **cloud-controller-manager 和 kube-apiserver**：Cloud Controller 与 kube-apiserver 通信以监视集群状态和管理云资源。
   - 协议：HTTPS
   - 端口：6443/TCP（kube-apiserver）
   - 安全性：基于 TLS 证书的身份验证

### 控制平面和节点通信

```mermaid
graph TD
    classDef apiserver fill:#bbdefb,stroke:#1976d2,stroke-width:2px;
    classDef kubelet fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;
    classDef proxy fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;

    API[kube-apiserver] <--> KB[kubelet]
    API <--> KP[kube-proxy]

    class API apiserver;
    class KB kubelet;
    class KP proxy;
```

控制平面和节点之间的通信如下：

1. **kube-apiserver 和 kubelet**：kube-apiserver 与 kubelet 通信以传递 Pod 规格并收集节点状态。
   - 协议：HTTPS
   - 端口：10250/TCP（kubelet）
   - 安全性：基于 TLS 证书的身份验证

2. **kubelet 和 kube-apiserver**：kubelet 与 kube-apiserver 通信以进行节点注册、Pod 状态报告和事件传输。
   - 协议：HTTPS
   - 端口：6443/TCP（kube-apiserver）
   - 安全性：基于 TLS 证书的身份验证

3. **kube-proxy 和 kube-apiserver**：kube-proxy 与 kube-apiserver 通信以检索 Service 信息。
   - 协议：HTTPS
   - 端口：6443/TCP（kube-apiserver）
   - 安全性：基于 TLS 证书的身份验证

### 节点间通信

```mermaid
graph LR
    classDef pod fill:#ffecb3,stroke:#f9a825,stroke-width:1px;
    classDef cni fill:#e3f2fd,stroke:#1976d2,stroke-width:1px;

    P1[Pod 1] <--> CNI[CNI Network]
    P2[Pod 2] <--> CNI
    P3[Pod 3] <--> CNI
    P4[Pod 4] <--> CNI

    class P1,P2,P3,P4 pod;
    class CNI cni;
```

节点间通信如下：

1. **Pod 到 Pod 的通信**：Pod 通过 CNI 插件提供的网络相互通信。
   - 协议：取决于应用程序（TCP、UDP 等）
   - 端口：取决于应用程序
   - 安全性：可通过网络策略控制

2. **跨节点 Pod 通信**：不同节点上的 Pod 之间的通信由 CNI 插件处理。
   - 协议：取决于应用程序（TCP、UDP 等）
   - 端口：取决于应用程序
   - 安全性：可通过网络策略控制

### 外部通信

```mermaid
graph LR
    classDef external fill:#ffcdd2,stroke:#d32f2f,stroke-width:1px;
    classDef apiserver fill:#bbdefb,stroke:#1976d2,stroke-width:2px;
    classDef service fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;
    classDef pod fill:#ffecb3,stroke:#f9a825,stroke-width:1px;

    C[External Client] --> API[kube-apiserver]
    C --> SVC[Service/Ingress]
    SVC --> P[Pod]

    class C external;
    class API apiserver;
    class SVC service;
    class P pod;
```

与外部实体的通信如下：

1. **客户端和 kube-apiserver**：用户和外部系统通过 kube-apiserver 与集群交互。
   - 协议：HTTPS
   - 端口：6443/TCP（kube-apiserver）
   - 安全性：TLS 证书、token、用户身份验证等

2. **外部流量和 Service**：外部流量通过 NodePort、LoadBalancer Service 或 Ingress 访问集群内的应用程序。
   - 协议：HTTP、HTTPS、TCP、UDP 等
   - 端口：取决于 Service 配置
   - 安全性：取决于 Ingress Controller 和 Service 配置

### 通信安全

Kubernetes 集群内的通信安全性通过以下方式实现：

1. **TLS 证书**：控制平面组件之间的所有通信均使用 TLS 证书加密。
2. **身份验证和授权**：对 API server 的所有请求均经过身份验证和授权过程。
3. **网络策略**：可通过网络策略限制 Pod 到 Pod 的通信。
4. **加密的 Secret**：存储在 etcd 中的 Secret 可以加密。

**API Server 通信安全配置示例**：
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-key>
    - identity: {}
```

### 高可用集群配置

高可用性（HA）Kubernetes 集群旨在消除单点故障，并在不中断服务的情况下持续运行。

### 控制平面高可用性

控制平面的高可用性通过以下方式实现：

1. **多个控制平面节点**：通常部署 3 个或 5 个控制平面节点以实现冗余
2. **etcd 集群**：部署由多个 etcd 实例组成的集群（通常为 3 个或 5 个）
3. **负载均衡器**：在 API server 前放置负载均衡器以分配流量

**高可用控制平面架构**：

```mermaid
graph TD
    classDef loadbalancer fill:#ffecb3,stroke:#f9a825,stroke-width:2px;
    classDef controlplane fill:#bbdefb,stroke:#1976d2,stroke-width:2px;
    classDef component fill:#e3f2fd,stroke:#1976d2,stroke-width:1px;

    LB[Load Balancer] --> CP1[Control Plane 1]
    LB --> CP2[Control Plane 2]
    LB --> CP3[Control Plane 3]

    CP1 --> API1[kube-apiserver]
    CP1 --> ETCD1[etcd]
    CP1 --> SCHED1[kube-scheduler]
    CP1 --> CTRL1[kube-controller-manager]

    CP2 --> API2[kube-apiserver]
    CP2 --> ETCD2[etcd]
    CP2 --> SCHED2[kube-scheduler]
    CP2 --> CTRL2[kube-controller-manager]

    CP3 --> API3[kube-apiserver]
    CP3 --> ETCD3[etcd]
    CP3 --> SCHED3[kube-scheduler]
    CP3 --> CTRL3[kube-controller-manager]

    class LB loadbalancer;
    class CP1,CP2,CP3 controlplane;
    class API1,API2,API3,ETCD1,ETCD2,ETCD3,SCHED1,SCHED2,SCHED3,CTRL1,CTRL2,CTRL3 component;
```

**etcd 集群配置**：

```mermaid
graph LR
    classDef etcd fill:#e8eaf6,stroke:#3f51b5,stroke-width:1px;

    E1[etcd Node 1] <==> E2[etcd Node 2]
    E2 <==> E3[etcd Node 3]
    E3 <==> E1

    class E1,E2,E3 etcd;
```

### 工作节点高可用性

工作节点的高可用性通过以下方式实现：

1. **多个工作节点**：将工作负载分布到多个工作节点上
2. **自动节点恢复**：利用云提供商的自动恢复功能
3. **自动扩缩容**：通过 Cluster Autoscaler 实现节点自动扩缩容
4. **多个可用区**：跨多个可用区部署节点

**工作节点分布式部署**：

```mermaid
graph TD
    classDef az fill:#e3f2fd,stroke:#1976d2,stroke-width:1px,stroke-dasharray:5 5;
    classDef node fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;

    AZ1[Availability Zone A] --> WN1[Worker Node]
    AZ1 --> WN2[Worker Node]

    AZ2[Availability Zone B] --> WN3[Worker Node]
    AZ2 --> WN4[Worker Node]

    AZ3[Availability Zone C] --> WN5[Worker Node]
    AZ3 --> WN6[Worker Node]

    class AZ1,AZ2,AZ3 az;
    class WN1,WN2,WN3,WN4,WN5,WN6 node;
```

### 应用程序高可用性

应用程序的高可用性通过以下方式实现：

1. **ReplicaSet/Deployment**：运行多个 Pod 副本
2. **Pod 分布规则**：通过 Pod 反亲和性将 Pod 分布到多个节点上
3. **PodDisruptionBudget**：确保计划内中断期间的最低可用性
4. **Service 和负载均衡**：将流量分布到多个 Pod

**Pod 反亲和性示例**：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: web-server
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - web-server
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: web-server
        image: nginx:1.21
```

**PodDisruptionBudget 示例**：
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-server-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-server
```

### 灾难恢复策略

Kubernetes 集群的灾难恢复策略通过以下方式实现：

1. **etcd 备份和恢复**：建立定期 etcd 数据备份和恢复程序
2. **多区域部署**：跨多个区域部署集群
3. **集群联邦**：以联邦方式管理多个集群
4. **持续备份**：持续备份应用程序数据

**etcd 备份脚本示例**：
```bash
#!/bin/bash
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d-%H%M%S).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

**etcd 恢复脚本示例**：
```bash
#!/bin/bash
# Stop cluster
systemctl stop kubelet
docker stop $(docker ps -q)

# Recover etcd data
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot.db \
  --data-dir=/var/lib/etcd-restore \
  --name=master \
  --initial-cluster=master=https://127.0.0.1:2380 \
  --initial-cluster-token=etcd-cluster \
  --initial-advertise-peer-urls=https://127.0.0.1:2380

# Replace etcd directory with recovered data
mv /var/lib/etcd /var/lib/etcd.old
mv /var/lib/etcd-restore /var/lib/etcd

# Restart cluster
systemctl start kubelet
```

## 集群网络

Kubernetes 网络支持 Pod、Service 与外部世界之间的通信。Kubernetes 网络模型假定每个 Pod 都具有唯一的 IP 地址，并且可在无需 NAT 的情况下相互通信。

### 网络模型

Kubernetes 网络模型具有以下要求：

1. **Pod 到 Pod 的通信**：所有 Pod 必须能够在无需 NAT 的情况下与所有其他 Pod 通信
2. **节点到 Pod 的通信**：节点必须能够在无需 NAT 的情况下与所有 Pod 通信
3. **Pod 到外部的通信**：Pod 必须能够与外部世界通信（通常使用 NAT）

### CNI（Container Network Interface）

CNI 是在 Kubernetes 中实现网络的标准接口。存在多种 CNI 插件，每种插件都有不同的特性和性能特征。

**主要 CNI 插件**：

1. **Calico**：基于 BGP 的网络，支持网络策略
   - 特性：高性能、网络策略、加密、eBPF 支持
   - 使用场景：大型集群、注重安全的环境

2. **Cilium**：基于 eBPF 的网络和安全
   - 特性：L3-L7 安全策略、高性能、可观测性
   - 使用场景：微服务、注重安全的环境

3. **Flannel**：简单的 Overlay 网络
   - 特性：设置简单、轻量级
   - 使用场景：小型集群、开发环境

4. **Weave Net**：多主机容器网络
   - 特性：加密、网络策略、多云
   - 使用场景：混合云、多云

**CNI 配置示例（Calico）**：
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: calico-config
  namespace: kube-system
data:
  calico_backend: "bird"
  cni_network_config: |-
    {
      "name": "k8s-pod-network",
      "cniVersion": "0.3.1",
      "plugins": [
        {
          "type": "calico",
          "log_level": "info",
          "datastore_type": "kubernetes",
          "nodename": "__KUBERNETES_NODE_NAME__",
          "mtu": __CNI_MTU__,
          "ipam": {
            "type": "calico-ipam"
          },
          "policy": {
            "type": "k8s"
          },
          "kubernetes": {
            "kubeconfig": "__KUBECONFIG_FILEPATH__"
          }
        },
        {
          "type": "portmap",
          "snat": true,
          "capabilities": {"portMappings": true}
        }
      ]
    }
```

### Service 网络

Kubernetes Service 为一组 Pod 提供稳定的端点。Service 有多种类型，包括 ClusterIP、NodePort、LoadBalancer 和 ExternalName。

**Service 网络组件**：

1. **ClusterIP**：仅能在集群内访问的虚拟 IP
2. **kube-proxy**：将发送到 Service IP 的流量路由至 Pod
3. **CoreDNS**：用于服务发现的 DNS 服务

**Service 网络流程**：
```
Client -> Service (ClusterIP) -> kube-proxy -> Pod
```

**Service 示例**：
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### Ingress 网络

Ingress 管理从集群外部到集群内部 Service 的 HTTP 和 HTTPS 路由。Ingress Controller 实现 Ingress 资源。

**主要 Ingress Controller**：
1. **NGINX Ingress Controller**：基于 NGINX 的 Ingress Controller
2. **AWS ALB Ingress Controller**：基于 AWS Application Load Balancer
3. **Traefik**：云原生边缘路由器
4. **HAProxy Ingress**：基于 HAProxy 的 Ingress Controller

**Ingress 网络流程**：
```
Client -> Ingress Controller -> Service -> Pod
```

**Ingress 示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: example.com
    http:
      paths:
      - path: /app
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
```

### 网络策略

网络策略提供了一种控制 Pod 之间通信的方法。默认情况下，所有 Pod 都可以相互通信，但网络策略可以限制这种通信。

**网络策略示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-network-policy
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

### 网络故障排除

用于排查 Kubernetes 网络问题的常见工具和命令：

1. **ping、traceroute**：基本网络连通性测试
2. **tcpdump**：网络数据包捕获和分析
3. **netstat、ss**：检查网络连接状态
4. **nslookup、dig**：DNS 查询测试
5. **kubectl exec**：在 Pod 内执行网络命令

**网络调试示例**：
```bash
# Test network connectivity within a pod
kubectl exec -it <pod-name> -- ping <target-ip>

# Test DNS lookup within a pod
kubectl exec -it <pod-name> -- nslookup <service-name>

# Capture network packets within a pod
kubectl exec -it <pod-name> -- tcpdump -i eth0 -n

# Check service endpoints
kubectl get endpoints <service-name>
```

## 集群存储

Kubernetes 存储为容器化应用程序提供数据持久化能力。Kubernetes 提供了多种存储选项和抽象，以帮助应用程序高效使用存储。

### 存储架构

Kubernetes 存储架构由以下组件构成：

1. **Volume**：可挂载到 Pod 内容器的目录
2. **Persistent Volumes（PV）**：集群中的存储资源
3. **Persistent Volume Claims（PVC）**：用户存储请求
4. **Storage Classes**：定义存储的“类别”或类型
5. **CSI（Container Storage Interface）**：与存储系统的标准接口

**存储架构流程**：

```mermaid
graph LR
    classDef pod fill:#ffecb3,stroke:#f9a825,stroke-width:1px;
    classDef volume fill:#e0f7fa,stroke:#0097a7,stroke-width:1px;
    classDef pvc fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;
    classDef pv fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;
    classDef storage fill:#e8eaf6,stroke:#3f51b5,stroke-width:1px;

    POD[Pod] --> VOL[Volume Mount]
    VOL --> PVC[PVC]
    PVC --> PV[PV]
    PV --> STORAGE[Actual Storage<br>CSI Driver]

    class POD pod;
    class VOL volume;
    class PVC pvc;
    class PV pv;
    class STORAGE storage;
```

### Volume 类型

Kubernetes 支持多种类型的 Volume：

1. **临时 Volume**：
   - **emptyDir**：以空目录开始，并在 Pod 被删除时删除
   - **configMap**：将 ConfigMap 挂载为 Volume
   - **secret**：将 Secret 挂载为 Volume
   - **downwardAPI**：将 Pod 和容器信息作为文件公开

2. **持久 Volume**：
   - **awsElasticBlockStore**：AWS EBS Volume
   - **azureDisk**：Azure Disk
   - **gcePersistentDisk**：GCE Persistent Disk
   - **nfs**：NFS Volume
   - **csi**：通过 CSI Driver 提供的 Volume

**Volume 示例**：
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
    - mountPath: /test-pd
      name: test-volume
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: test-pvc
```

### Persistent Volume 和 Claim

Persistent Volume（PV）是由管理员预置或通过 Storage Class 动态预置的集群存储资源。Persistent Volume Claim（PVC）是用户的存储请求。

**Persistent Volume 示例**：
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

**Persistent Volume Claim 示例**：
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

### Storage Class

Storage Class 描述管理员提供的存储“类别”。当请求 PVC 时，Storage Class 允许动态预置 PV。

**Storage Class 示例**：
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

### CSI（Container Storage Interface）

CSI 在 Kubernetes 和存储系统之间提供标准接口。借助 CSI，存储提供商可以开发自己的存储 Driver，而无需修改 Kubernetes 代码。

**CSI 架构**：

```mermaid
graph TD
    classDef k8s fill:#e3f2fd,stroke:#1976d2,stroke-width:1px;
    classDef csi fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;
    classDef driver fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;
    classDef storage fill:#e0f7fa,stroke:#0097a7,stroke-width:1px;

    K8S[Kubernetes] --> CSI[Container Storage Interface]
    CSI --> DRIVER[CSI Driver<br>e.g., AWS EBS CSI Driver]
    DRIVER --> STORAGE[Storage System<br>e.g., AWS EBS]

    class K8S k8s;
    class CSI csi;
    class DRIVER driver;
    class STORAGE storage;
```

**CSI Driver 部署示例**：
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

### 存储最佳实践

使用 Kubernetes 存储的最佳实践：

1. **选择合适的存储类型**：选择与工作负载特性匹配的存储类型
2. **使用动态预置**：通过 Storage Class 利用动态预置
3. **选择合适的访问模式**：选择与工作负载要求匹配的访问模式
4. **设置资源请求和限制**：请求适当的存储容量
5. **建立备份和恢复策略**：为关键数据准备备份和恢复策略
6. **监控存储**：监控存储使用情况和性能

## 集群可扩展性

Kubernetes 集群可扩展性是指集群处理不断增加的负载和需求的能力。可扩展性可通过水平扩展（scale out）和垂直扩展（scale up）实现。

### 集群规模限制

Kubernetes 集群具有以下规模限制：

1. **节点数量**：每个集群最多 5,000 个节点
2. **Pod 数量**：每个集群最多 150,000 个 Pod
3. **每个节点的 Pod 数量**：每个节点最多 110 个 Pod（默认）
4. **Service 数量**：每个集群最多 10,000 个 Service
5. **每个 Pod 的容器数量**：每个 Pod 最多 20 个容器

这些限制可能因 Kubernetes 版本和集群配置而异。

### 水平扩展

水平扩展通过添加更多节点来增加集群容量。

**节点自动扩缩容**：
Kubernetes Cluster Autoscaler 根据工作负载要求自动调整节点数量。

```yaml
# AWS Auto Scaling Group tags example
tags:
  k8s.io/cluster-autoscaler/enabled: "true"
  k8s.io/cluster-autoscaler/my-cluster: "owned"
```

**Cluster Autoscaler 部署示例**：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      containers:
      - name: cluster-autoscaler
        image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.24.0
        command:
        - ./cluster-autoscaler
        - --cloud-provider=aws
        - --nodes=2:10:my-asg-group
        - --scale-down-unneeded-time=10m
```

**Karpenter**：
Karpenter 是 AWS 开发的新型节点自动扩缩容工具，可提供更快、更高效的节点预置。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  subnetSelector:
    karpenter.sh/discovery: my-cluster
  securityGroupSelector:
    karpenter.sh/discovery: my-cluster
```

### 垂直扩展

垂直扩展可增加现有节点的资源（CPU、内存）。

**Vertical Pod Autoscaler（VPA）**：
VPA 自动调整 Pod 的 CPU 和内存请求。

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
```

### 应用程序扩展

应用程序级别的扩展通过调整 Pod 副本数量实现。

**Horizontal Pod Autoscaler（HPA）**：
HPA 根据 CPU 利用率或自定义指标自动调整 Pod 副本数量。

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
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

**KEDA（Kubernetes Event-driven Autoscaling）**：
KEDA 提供事件驱动的自动扩缩容，可根据各种事件源进行扩展。

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: my-app-scaledobject
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.svc:9092
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: "10"
```

### 可扩展性最佳实践

Kubernetes 集群可扩展性的最佳实践：

1. **设置资源请求和限制**：为所有 Pod 设置适当的资源请求和限制
2. **节点池策略**：针对不同工作负载特性配置多个节点池
3. **配置自动扩缩容**：正确配置 Cluster Autoscaler、HPA、VPA
4. **高效 Pod 放置**：利用节点亲和性、Pod 亲和性/反亲和性
5. **集群监控**：持续监控资源使用情况和性能
6. **负载测试**：定期进行负载测试以验证扩展策略

## 集群安全

Kubernetes 集群安全必须在多个层面实施，包括身份验证、授权、网络策略、Pod 安全等。

### 身份验证

用于验证对 Kubernetes API server 访问的方法：

1. **X.509 证书**：使用 TLS 客户端证书进行身份验证
2. **Service Account Token**：用于 Pod 内 API server 访问的 Token
3. **OpenID Connect（OIDC）**：通过外部身份提供商进行身份验证
4. **Webhook Token Authentication**：通过外部身份验证服务进行身份验证
5. **Authentication Proxy**：通过身份验证代理进行身份验证

**kubeconfig 示例**：
```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority-data: <CA-DATA>
    server: https://api.my-cluster.example.com
users:
- name: admin
  user:
    client-certificate-data: <CERT-DATA>
    client-key-data: <KEY-DATA>
contexts:
- name: my-context
  context:
    cluster: my-cluster
    user: admin
current-context: my-context
```

### 授权

用于控制已验证用户操作的方法：

1. **RBAC（Role-Based Access Control）**：基于角色的访问控制
2. **ABAC（Attribute-Based Access Control）**：基于属性的访问控制
3. **Node Authorization**：节点的特殊授权
4. **Webhook Authorization**：通过外部服务进行授权

**RBAC 示例**：
```yaml
# Role definition
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]

# Role binding
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

### 网络安全

保护集群内网络流量的方法：

1. **网络策略**：控制 Pod 到 Pod 的通信
2. **加密通信**：通过 TLS 加密通信
3. **Service Mesh**：通过 Istio、Linkerd 等实现高级网络安全

**网络策略示例**：
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### Pod 安全

Pod 级别的安全实施：

1. **Pod Security Context**：Pod 和容器级别的安全设置
2. **Pod Security Standards**：定义 Pod 安全要求
3. **seccomp Profiles**：系统调用限制
4. **AppArmor/SELinux**：强制访问控制

**Pod Security Context 示例**：
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

### Secret 管理

安全管理敏感信息的方法：

1. **Kubernetes Secrets**：使用基本 Secret 资源
2. **加密的 etcd**：加密存储在 etcd 中的 Secret
3. **外部 Secret 管理**：利用 HashiCorp Vault、AWS Secrets Manager 等

**加密的 etcd 配置示例**：
```yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
    - secrets
    providers:
    - aescbc:
        keys:
        - name: key1
          secret: <base64-encoded-key>
    - identity: {}
```

### 安全最佳实践

Kubernetes 集群安全的最佳实践：

1. **最小权限原则**：仅授予必要的最小权限
2. **定期更新**：定期更新集群和组件
3. **网络隔离**：通过网络策略限制 Pod 到 Pod 的通信
4. **镜像安全**：仅使用受信任的镜像，并实施漏洞扫描
5. **审计日志**：为集群活动启用审计日志
6. **安全基准**：遵守 CIS 基准等安全标准

## 集群升级

Kubernetes 集群升级是应用新功能、安全补丁和错误修复所必需的。升级必须经过谨慎规划和执行。

### 2026 年 7 月更新：Kubernetes v1.37 进入 Beta 阶段

v1.37.0-beta.0 于 2026 年 7 月 20 日发布，使下一个次要版本 v1.37 进入发布周期的后期阶段。Code Freeze 按计划于 2026 年 7 月 22 日至 23 日生效，最终 v1.37.0 版本计划于 2026 年 8 月 26 日发布。完整时间表请参阅 [v1.37 发布信息](https://www.kubernetes.dev/resources/release/)。

同一周（2026 年 7 月 22 日至 23 日），所有受维护版本线均发布了补丁版本：[v1.36.3](https://github.com/kubernetes/kubernetes/releases/tag/v1.36.3)、[v1.35.7](https://github.com/kubernetes/kubernetes/releases/tag/v1.35.7) 和 [v1.34.10](https://github.com/kubernetes/kubernetes/releases/tag/v1.34.10)。与往常一样，建议为你的次要版本应用最新补丁。

### 2026 年 8 月更新：v1.37 抢先看

2026 年 7 月 31 日，发布团队发布了 [Kubernetes v1.37 抢先看](https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/)，概述了在最终 v1.37.0 版本（仍计划于 2026 年 8 月 26 日发布）之前计划进行的弃用、移除和功能变更。Docs Freeze 于 2026 年 8 月 5 日至 6 日生效。同时，下一个周期的首个 tag v1.38.0-alpha.0 于 2026 年 8 月 6 日创建。

### 升级策略

Kubernetes 集群升级的策略：

1. **Blue/Green 升级**：单独创建新版本集群并迁移工作负载
2. **原地升级**：直接升级现有集群
3. **Canary 升级**：先仅升级部分节点以进行验证

### 升级顺序

Kubernetes 集群升级的典型顺序：

1. **控制平面升级**：kube-apiserver、kube-controller-manager、kube-scheduler、etcd
2. **DNS 和 CNI 升级**：CoreDNS、CNI 插件和其他主要附加组件
3. **工作节点升级**：依次升级工作节点

**kubeadm 升级示例**：
```bash
# Control plane upgrade
kubeadm upgrade plan
kubeadm upgrade apply v1.24.0

# Worker node upgrade
kubectl drain <node-name> --ignore-daemonsets
# Upgrade kubelet and kubeadm on the node
apt-get update && apt-get install -y kubelet=1.24.0-00 kubeadm=1.24.0-00
kubeadm upgrade node
systemctl restart kubelet
kubectl uncordon <node-name>
```

### 升级注意事项

升级 Kubernetes 集群时的注意事项：

1. **API 变更**：检查新版本中的 API 变更
2. **Feature Gates**：检查新的 Feature Gate 和默认值变更
3. **依赖项**：检查 CNI、CSI 等依赖组件的兼容性
4. **停机时间**：规划升级期间的预期停机时间
5. **回滚计划**：制定在发生问题时的回滚计划

### 升级最佳实践

Kubernetes 集群升级的最佳实践：

1. **先在测试环境中测试**：在生产升级前于测试环境中验证
2. **渐进式升级**：每次升级一个次要版本
3. **备份**：在升级前备份 etcd 数据
4. **文档化**：记录升级过程和结果
5. **监控**：在升级期间和之后监控集群状态
6. **升级窗口**：在低流量时段执行升级

## Amazon EKS 集群架构

Amazon EKS（Elastic Kubernetes Service）是 AWS 提供的托管 Kubernetes 服务。EKS 在提供所有基本 Kubernetes 功能的同时，还增加了与 AWS 服务的集成和管理便利性。

### EKS 架构概览

EKS 集群由以下组件构成：

1. **EKS Control Plane**：由 AWS 管理的 Kubernetes 控制平面
2. **EKS Nodes**：由用户管理的工作节点（EC2 实例）
3. **EKS Managed Node Groups**：由 AWS 管理的节点组
4. **EKS Fargate Profiles**：无服务器容器执行环境
5. **VPC 和 Subnets**：用于集群网络的 VPC 和子网

**EKS 架构图**：

```mermaid
graph TD
    classDef aws fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px;
    classDef eks fill:#fce4ec,stroke:#c2185b,stroke-width:1px;
    classDef controlplane fill:#bbdefb,stroke:#1976d2,stroke-width:2px;
    classDef nodes fill:#c8e6c9,stroke:#388e3c,stroke-width:1px;
    classDef services fill:#d1c4e9,stroke:#673ab7,stroke-width:1px;
    classDef network fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px;

    AWS[AWS Cloud] --> CP[EKS Control Plane<br>AWS Managed]
    AWS --> WN[Worker Nodes]
    AWS --> AWSS[AWS Services]
    AWS --> VPC[VPC & Networking]

    CP --> API[kube-apiserver]
    CP --> ETCD[etcd]
    CP --> SCHED[kube-scheduler]
    CP --> CTRL[kube-controller-manager]

    WN --> NG1[Node Group 1<br>EC2 instances]
    WN --> NG2[Node Group 2<br>EC2 instances]
    WN --> FG[Fargate Profile<br>Serverless]

    AWSS --> IAM[IAM]
    AWSS --> ECR[ECR]
    AWSS --> ELB[ELB/ALB/NLB]
    AWSS --> EBS[EBS/EFS/FSx]
    AWSS --> CW[CloudWatch]

    VPC --> VPCM[VPC]
    VPC --> SN[Subnets]
    VPC --> SG[Security Groups]
    VPC --> RT[Route Tables]
    VPC --> CNI[VPC CNI]

    class AWS aws;
    class CP controlplane;
    class WN nodes;
    class AWSS,IAM,ECR,ELB,EBS,CW services;
    class VPC,VPCM,SN,SG,RT,CNI network;
    class API,ETCD,SCHED,CTRL,NG1,NG2,FG eks;
```

### EKS Control Plane

EKS 控制平面由 AWS 管理，并在多个可用区中提供高可用性。

**主要特性**：
1. **托管服务**：AWS 管理控制平面维护和升级
2. **高可用性**：跨多个可用区部署
3. **自动扩缩容**：根据负载自动扩缩容
4. **安全性**：与 AWS 安全服务集成

### EKS 节点类型

EKS 支持多种类型的节点：

1. **自管节点**：用户直接管理 EC2 实例
2. **托管节点组**：AWS 管理节点生命周期
3. **Fargate**：无服务器容器执行环境
4. **Bottlerocket 节点**：针对容器工作负载优化的 OS

**托管节点组示例**：
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: ap-northeast-2
managedNodeGroups:
  - name: ng-1
    instanceType: m5.large
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    volumeSize: 80
    privateNetworking: true
    labels:
      role: worker
    tags:
      nodegroup-role: worker
    iam:
      withAddonPolicies:
        autoScaler: true
        albIngress: true
```

### EKS 网络

EKS 网络基于 Amazon VPC，包含以下组件：

1. **VPC CNI Plugin**：与 AWS VPC 网络集成
2. **Security Groups**：节点和 Pod 级别的网络安全
3. **Load Balancer 集成**：与 ELB、ALB、NLB 集成
4. **VPC Endpoints**：与 AWS 服务进行私有通信

**VPC CNI 配置示例**：
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-network-policy: "true"
  enable-pod-eni: "true"
  warm-ip-target: "5"
  minimum-ip-target: "10"
```

### EKS 存储

EKS 与各种 AWS 存储服务集成：

1. **EBS CSI Driver**：Amazon EBS Volume 管理
2. **EFS CSI Driver**：Amazon EFS 文件系统管理
3. **FSx for Lustre CSI Driver**：FSx for Lustre 文件系统管理
4. **S3**：对象存储

**EBS CSI Driver 示例**：
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
```

### EKS 安全

EKS 与 AWS 安全服务集成以提供强大的安全性：

1. **IAM 集成**：AWS IAM 和 Kubernetes RBAC 集成
2. **VPC 安全**：VPC Security Group 和网络 ACL
3. **AWS KMS**：用于 Secret 加密的 KMS 集成
4. **AWS WAF**：Web 应用程序防火墙集成
5. **AWS Shield**：DDoS 防护

**IAM Role Service Account 示例**：
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/s3-reader-role
```

### EKS 监控和日志记录

EKS 与 AWS 监控和日志记录服务集成：

1. **CloudWatch Container Insights**：容器监控
2. **CloudWatch Logs**：日志收集和分析
3. **X-Ray**：分布式追踪
4. **Prometheus 和 Grafana**：开源监控工具集成

**CloudWatch Container Insights 示例**：
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: amazon-cloudwatch
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: cloudwatch-agent
  namespace: amazon-cloudwatch
spec:
  selector:
    matchLabels:
      name: cloudwatch-agent
  template:
    metadata:
      labels:
        name: cloudwatch-agent
    spec:
      containers:
      - name: cloudwatch-agent
        image: amazon/cloudwatch-agent:1.247347.6b250880
        # ... additional configuration
```

### EKS 成本优化

优化 EKS 集群成本的方法：

1. **Spot Instances**：利用成本效益高的 Spot 实例
2. **Fargate**：通过无服务器容器执行降低空闲资源成本
3. **自动扩缩容**：通过 Cluster Autoscaler 优化资源
4. **Graviton Processors**：利用基于 ARM 的 Graviton 实例
5. **资源请求优化**：设置适当的资源请求和限制

**Spot Instance 节点组示例**：
```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: ap-northeast-2
managedNodeGroups:
  - name: spot-ng
    instanceTypes: ["m5.large", "m5a.large", "m5d.large", "m5ad.large"]
    spot: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 10
```

## 了解更多

要深入了解本文档中介绍的集群架构，请参阅以下主题：

- [Kubernetes 简介](../basics/04-kubernetes-introduction.md) - Kubernetes 的基本概念和历史
- [Pod 和工作负载](./02-pods-and-workloads.md) - 管理在集群中运行的工作负载
- [Service 和网络](./03-services-networking.md) - 集群内的网络配置
- [调度、抢占和驱逐](./08-scheduling-preemption-eviction.md) - Pod 如何被放置在节点上
- [集群管理](./09-cluster-administration.md) - 集群运行和管理
- [EKS 简介](../eks/01-eks-introduction.md) - Amazon EKS 服务概览
- [EKS 集群创建](../eks/02-eks-cluster-creation-part1.md) - 如何创建 EKS 集群

### 实践和进阶学习

- [Kubernetes 官方教程](https://kubernetes.io/docs/tutorials/) - 通过动手实践学习
- [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) - 手动构建 Kubernetes 集群
- [Cilium 网络](../networking/cilium/01-introduction.md) - 高级网络和安全功能

## 结论

在本文档中，我们研究了 Kubernetes 集群的架构、主要组件及其协同工作方式。我们还介绍了集群网络、存储、可扩展性、安全性和升级等重要方面，以及 Amazon EKS 集群的架构。

理解 Kubernetes 集群架构是有效进行集群设计、部署和运行的基础。有了这些知识，你可以构建稳定、可扩展且安全性增强的 Kubernetes 环境。

## 测验

要测试你在本章中学到的知识，请尝试[集群架构测验](../quizzes/core/01-cluster-architecture-quiz.md)。

## 参考资料

- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Amazon EKS 文档](https://docs.aws.amazon.com/eks/)
- [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
- [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
- [Kubernetes Up & Running](https://www.oreilly.com/library/view/kubernetes-up-and/9781492046523/)
- [Kubernetes 最佳实践](https://www.oreilly.com/library/view/kubernetes-best-practices/9781492056461/)
