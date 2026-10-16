# Kubernetes 简介

> **支持的版本**：上游 Kubernetes 1.35–1.37；EKS 标准支持 1.34–1.37（截至 2026 年 10 月 12 日）
> **最后更新**：October 12, 2026

Kubernetes 项目维护最近三个次要版本（1.35–1.37）的发布分支。上游 1.34 处于维护模式，且在其于 **October 27, 2026** 结束生命周期之前仍会接收补丁版本；该日期与 AWS 的 EKS 支持终止日期不同。请查看 [AWS EKS 生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)以了解 EKS 覆盖范围和日期。

Kubernetes（K8s）是一个开源容器编排平台，可自动部署、扩缩容和管理容器化应用程序。本文档介绍 Kubernetes 的基本概念、架构、主要组件和功能。

这些独立学习示例已根据架构和官方文档进行静态审查。它们并非经部署验证的生产配置。请在目标环境中验证自定义镜像、名称/标签、TLS、IAM/RBAC、CNI 和存储前提条件，并替换占位符。

## 实验环境设置

要跟随本文档中的示例操作，您需要以下工具和环境：

### 必需工具

* **kubectl**：与 Kubernetes 集群交互的命令行工具
* **本地集群驱动程序**：minikube/kind 支持的容器引擎或 VM 驱动程序；Kubernetes 节点使用 CRI v1 运行时。
* **minikube** 或 **kind**：本地 Kubernetes 集群（用于开发和学习）

### 安装方法

**kubectl 安装**：

```bash
# macOS: use a kubectl version within one minor of the API server.
brew install kubectl
```

```bash
# Linux: select an explicit compatible version and architecture.
set -euo pipefail
: "${KUBECTL_VERSION:?Set a cluster-compatible version, e.g. v1.37.1}"
case "$(uname -m)" in
  x86_64) KUBECTL_ARCH=amd64 ;;
  aarch64|arm64) KUBECTL_ARCH=arm64 ;;
  *) echo "Choose a supported kubectl architecture" >&2; exit 1 ;;
esac
curl --fail --location --output kubectl "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl"
curl --fail --location --output kubectl.sha256 "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```

```powershell
$ErrorActionPreference = "Stop"
$KubectlVersion = Read-Host "Cluster-compatible kubectl version (vX.Y.Z)"
$KubectlArch = Read-Host "Architecture (amd64 or arm64)"
if ($KubectlVersion -notmatch '^v\d+\.\d+\.\d+$' -or $KubectlArch -notin @('amd64','arm64')) { throw "Invalid version/architecture" }
$BaseUrl = "https://dl.k8s.io/release/$KubectlVersion/bin/windows/$KubectlArch"
Invoke-WebRequest "$BaseUrl/kubectl.exe" -OutFile kubectl.exe
Invoke-WebRequest "$BaseUrl/kubectl.exe.sha256" -OutFile kubectl.exe.sha256
if ((Get-FileHash kubectl.exe -Algorithm SHA256).Hash -ne (Get-Content kubectl.exe.sha256).Trim()) { throw "Checksum mismatch" }
# Move the verified binary to a directory included in PATH.
```

**minikube 安装**：

请使用 minikube 官方入门指南为您的操作系统/架构选择二进制文件、校验和及驱动程序。在各自的 shell 中运行 Linux 和 Windows 说明，并将已验证的二进制文件添加到 PATH。对于 macOS：

```bash
brew install minikube
minikube version
```

### 启动本地集群

```bash
minikube start
```

## 目录

* [什么是 Kubernetes？](04-kubernetes-introduction.md#what-is-kubernetes)
* [Kubernetes 的历史](04-kubernetes-introduction.md#history-of-kubernetes)
* [Kubernetes 架构](04-kubernetes-introduction.md#kubernetes-architecture)
* [Kubernetes 主要组件](04-kubernetes-introduction.md#kubernetes-main-components)
* [Kubernetes 基本对象](04-kubernetes-introduction.md#kubernetes-basic-objects)
* [Kubernetes 工作负载资源](04-kubernetes-introduction.md#kubernetes-workload-resources)
* [Kubernetes Service 和网络](04-kubernetes-introduction.md#kubernetes-services-and-networking)
* [Kubernetes 存储](04-kubernetes-introduction.md#kubernetes-storage)
* [Kubernetes 配置和安全](04-kubernetes-introduction.md#kubernetes-configuration-and-security)
* [Kubernetes 与 Amazon EKS](04-kubernetes-introduction.md#kubernetes-vs-amazon-eks)
* [Kubernetes 入门](04-kubernetes-introduction.md#getting-started-with-kubernetes)

## 什么是 Kubernetes？

Kubernetes 在希腊语中意为“舵手”或“领航员”，是一个自动化部署、扩缩容和运行容器化应用程序的开源系统。它受 Google 内部 Borg 系统的启发，并于 2014 年作为开源项目发布。

### Kubernetes 的主要特性

1. **Service 发现和负载均衡**：将容器暴露到外部并分发流量
2. **存储编排**：自动挂载本地或云存储系统
3. **发布和回滚**：逐步更新应用程序，并支持由操作员/工具触发的回滚；失败的 Deployment 不会自动回滚。
4. **自动装箱**：根据资源要求将容器放置到节点上
5. **自愈**：重启失败的容器并替换无响应的容器
6. **Secret 和配置管理**：存储敏感信息并更新配置
7. **水平扩缩容**：通过简单命令或 UI 扩缩应用程序
8. **批处理执行**：管理批处理和 CI 工作负载

### Kubernetes 解决的问题

* **容器编排**：高效管理数百或数千个容器
* **高可用性**：通过副本、放置、探针和容量支持有弹性的应用程序设计
* **可扩展性**：根据流量增长自动扩缩容
* **恢复**：协调失败的工作负载；灾难恢复还需要经过测试的备份和恢复计划
* **资源效率**：高效利用硬件资源
* **声明式配置**：以代码形式管理基础设施
* **多云和混合云**：跨各种环境进行一致的部署和管理

## Kubernetes 的历史

### 背景

* **2003-2013**：Google 在内部使用名为 Borg 的容器编排系统
* **June 2014**：Google 将 Kubernetes 作为开源项目发布
* **July 2015**：Kubernetes 1.0 发布并捐赠给 Cloud Native Computing Foundation (CNCF)
* **2016-2017**：主要云提供商推出托管 Kubernetes 服务
* **2018 年及以后**：确立为容器编排的事实标准

### 名称的由来

Kubernetes（κυβερνήτης）在希腊语中意为“舵手”或“领航员”。这象征着它引导容器化应用程序的作用。使用缩写 K8s 是因为“K”和“s”之间有 8 个字符。

### Logo 的含义

Kubernetes Logo 描绘了一个带有 7 根辐条的船舵，象征 Kubernetes 在引导容器化应用程序航向方面的作用。

## Kubernetes 架构

Kubernetes 遵循主节点-工作节点架构。主节点（控制平面）管理集群，工作节点运行实际的应用程序工作负载。

### 控制平面（主节点）组件

![Kubernetes 控制平面：kubectl 请求通过 kube-apiserver 流向 etcd，而 kube-scheduler、kube-controller-manager 和 cloud-controller-manager 通过 API server 进行监视和协调。](../.gitbook/assets/en-basics-04-kubernetes-introduction-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-0.html)

1. **kube-apiserver**：暴露 Kubernetes API 的控制平面前端
2. **etcd**：用于 Kubernetes API 对象和集群状态（不包括应用程序卷内容）的一致且高可用的键值存储
3. **kube-scheduler**：将 Pod 分配到节点的组件
4. **kube-controller-manager**：运行控制器进程的组件
   * Node Controller：节点宕机时进行通知和响应
   * Replication Controller：维护正确数量的 Pod 副本
   * EndpointSlice Controller：维护 Service 端点记录（旧版 Endpoints 已弃用）
   * ServiceAccount controller 创建默认账户；投影的 Pod 令牌使用 TokenRequest 和 kubelet 轮换
5. **cloud-controller-manager**：包含云特定控制逻辑的组件
   * Node Controller：向云提供商检查节点是否已被删除
   * Route Controller：在云基础设施中设置路由
   * Service Controller：创建、更新、删除云提供商负载均衡器

### 节点组件

![Kubernetes 工作节点：kubelet 从控制平面接收指令并驱动运行 Pod 容器的 CRI 运行时（containerd/CRI-O，或通过外部适配器的 Docker Engine），而 kube-proxy 维护其网络规则。](../.gitbook/assets/en-basics-04-kubernetes-introduction-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-1.html)

1. **kubelet**：在每个节点上运行的代理，确保 Pod 中的容器正在运行
2. **kube-proxy**：在每个节点上运行、实现 Kubernetes Service 概念的网络代理
3. **容器运行时**：实现 CRI v1 的软件，例如 containerd 或 CRI-O；Docker Engine 需要单独的 CRI 适配器

### 完整架构

![完整 Kubernetes 集群：kubectl 客户端连接到 kube-apiserver，后者协调 etcd、kube-scheduler、kube-controller-manager 和 cloud-controller-manager，并驱动两个工作节点上的 kubelet、容器运行时和 kube-proxy。](../.gitbook/assets/en-basics-04-kubernetes-introduction-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-2.html)

## Kubernetes 主要组件

### API Server (kube-apiserver)

API server 是暴露 Kubernetes API 的控制平面前端。Kubernetes API 请求都会经过它；应用程序流量和存储 I/O 不会流经 API server。

**主要功能**：

* 提供 REST API
* 身份验证和授权
* 请求验证
* 与 etcd 通信
* 可水平扩展

### etcd

etcd 是一个存储 Kubernetes API 对象和集群状态（不包括应用程序卷内容）的一致且高可用的键值存储。

**主要特性**：

* 分布式系统
* 强一致性
* 高可用性
* 安全的数据存储
* 用于监视变更的 Watch 功能

### Scheduler (kube-scheduler)

Scheduler 是一个控制平面组件，用于选择运行新创建 Pod 的节点。

**调度过程**：

1. **筛选**：识别可以运行 Pod 的节点
2. **评分**：为合适的节点分配分数
3. **绑定**：将 Pod 分配给最优节点

**考虑因素**：

* 资源要求（CPU、内存）
* 硬件/软件/策略约束
* 亲和性/反亲和性规范
* 数据本地性
* 工作负载干扰

### Controller Manager (kube-controller-manager)

Controller Manager 是一个运行多个控制器进程的控制平面组件。

**主要控制器**：

* **Node Controller**：监视并响应节点状态
* **Replication Controller**：维护 Pod 副本数量
* **EndpointSlice Controller**：维护 Service 端点记录（旧版 Endpoints 已弃用）
* **ServiceAccount controller**：创建默认账户；现代 Pod 令牌通过 TokenRequest 请求并由 kubelet 轮换
* **Job Controller**：管理一次性任务
* **CronJob Controller**：管理计划任务
* **DaemonSet Controller**：在每个符合条件的节点上协调一个 Pod
* **StatefulSet Controller**：管理有状态应用程序
* **PV Controller**：管理持久卷

### Cloud Controller Manager (cloud-controller-manager)

Cloud Controller Manager 包含云特定控制逻辑。CSI 控制器 sidecar/驱动程序和 kubelet/节点插件处理存储预配、附加和挂载；这并非 CCM 卷控制器。

**主要控制器**：

* **Node Controller**：通过云提供商 API 检查节点状态
* **Route Controller**：在云环境中设置路由
* **Service Controller**：创建、更新、删除云负载均衡器

### kubelet

kubelet 是在每个节点上运行的代理，确保 Pod 中的容器正在运行。

**主要功能**：

* 根据 PodSpec 运行容器
* 报告容器状态
* 执行容器健康检查
* 管理容器生命周期
* 报告节点状态

### kube-proxy

kube-proxy 是在每个节点上运行、实现 Kubernetes Service 概念的网络代理。

**主要功能**：

* 维护 Service IP 和端口的网络规则
* 转发连接
* 实现负载均衡

**运行模式**：

* **nftables 模式**：自 1.33 起稳定；请验证内核和网络插件兼容性
* **iptables 模式**：使用 Linux iptables 的 NAT 实现（默认）
* **IPVS 模式**：自 1.35 起弃用；请计划迁移。历史 userspace 模式已移除。

## Kubernetes 基本对象

Kubernetes 对象是表示集群状态的持久实体。这些对象描述集群中正在运行的应用程序、可用资源、策略等。

### Pod

Pod 是 Kubernetes 中最小的可部署单元，表示一组一个或多个容器。Pod 中的容器共享网络，并且可以共享显式挂载的卷；它们在同一节点上运行。它们不会自动共享其根文件系统。

**主要特性**：

* 具有唯一 IP 地址
* 共享网络命名空间（相同的 IP 和端口空间）
* 共享 IPC 命名空间
* 共享主机名
* 容器之间可以通过 localhost 通信

**Pod 示例**：

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
    image: nginx:1.30.4
    ports:
    - containerPort: 80
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  - name: log-sidecar
    image: busybox:1.37.0
    command:
    - /bin/sh
    - -c
    - until [ -f /var/log/nginx/access.log ]; do sleep 1; done; tail -F /var/log/nginx/access.log
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
      readOnly: true
  volumes:
  - name: logs
    emptyDir: {}
```

### Namespace

Namespace 提供了一种在单个集群内隔离资源组的方法。这有助于组织团队/项目；Namespace 本身不强制网络或授权隔离。

**默认 Namespace**：

* **default**：默认 Namespace
* **kube-system**：Kubernetes 系统创建对象的 Namespace
* **kube-public**：按惯例用于公开信息的 Namespace；实际对象访问仍取决于 RBAC
* **kube-node-lease**：用于节点心跳的 Namespace

**Namespace 示例**：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### 标签和选择器

标签是附加到对象的键值对，用于识别和选择对象。选择器提供了一种基于标签筛选对象的方法。

**标签示例**：

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**选择器类型**：

* **基于相等性**：`=`, `!=`
* **基于集合**：`in`, `notin`, `exists`

**选择器示例**：

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### 注解

注解是存储对象非标识性元数据的键值对。注解可用于存储工具或库使用的信息。

**注解示例**：

```yaml
metadata:
  annotations:
    example.com/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Node

节点是在 Kubernetes 集群中运行 Pod 的工作机器。节点可以是物理机或虚拟机。

**节点状态**：

* **地址**：主机名、内部 IP、外部 IP
* **条件**：Ready、DiskPressure、MemoryPressure、PIDPressure、NetworkUnavailable
* **容量**：CPU、内存、最大 Pod 数
* **信息**：内核版本、容器运行时版本、kubelet 版本

**说明性 Node 状态（由节点/控制器报告，而非节点预配清单）**：

```yaml
apiVersion: v1
kind: Node
metadata:
  name: worker-1
  labels:
    kubernetes.io/hostname: worker-1
    node-role.kubernetes.io/worker: ""
    topology.kubernetes.io/zone: us-east-1a
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

## Kubernetes 工作负载资源

工作负载资源是用于管理和运行 Pod 的对象。这些资源管理 Pod 的创建、扩缩容、更新和终止。

### ReplicaSet

ReplicaSet 协调期望数量的 Pod 对象；就绪状态还取决于容量、有效配置和应用程序。如果 Pod 失败或被删除，ReplicaSet 会自动创建替换 Pod。

**主要功能**：

* 维护指定数量的 Pod 副本
* 定义 Pod 模板
* 通过选择器识别 Pod

**ReplicaSet 示例**：

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
        image: nginx:1.30.4
        ports:
        - containerPort: 80
```

### Deployment

Deployment 在 ReplicaSet 之上进一步抽象，为应用程序提供声明式更新。Deployment 提供滚动更新、回滚和扩缩容等功能。

**主要功能**：

* 声明式应用程序更新
* 滚动更新和回滚
* Deployment 历史记录管理
* 扩缩容

**Deployment 示例**：

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

MySQL 示例是单个持久实例。StatefulSet 不配置数据库复制、故障转移或备份。请先提供 mysql-secret/password 并替换 StorageClass 占位符。仅增加副本会创建相互独立的数据库；高可用性需要经过测试的数据库 operator/复制设置。

### StatefulSet

StatefulSet 是用于需要维护状态的应用程序的工作负载资源。它为每个 Pod 分配唯一标识符，并提供稳定的网络标识符和持久存储。

**主要功能**：

* 稳定且唯一的网络标识符
* 稳定且持久的存储
* 顺序部署和扩缩容
* 顺序更新

**StatefulSet 示例**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
  - name: mysql
    port: 3306
    targetPort: 3306
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
  replicas: 1
  template:
    metadata:
      labels:
        app: mysql
        role: db
    spec:
      containers:
      - name: mysql
        image: mysql:8.4
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
        readinessProbe:
          tcpSocket:
            port: 3306
          initialDelaySeconds: 10
          periodSeconds: 5
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: replace-with-storage-class
      resources:
        requests:
          storage: 10Gi
```

Linux Fluent Bit 示例将 CRI 日志发送到 stdout 用于演示。它排除自身日志以防止反馈循环，并将其位置 DB 单独持久化。请勿与另一个将相同日志重新发布到 stdout 的收集器同时部署。生产环境需要外部目标以及经过审查的主机路径、权限和 PSS 例外。

### DaemonSet

DaemonSet 会在每个符合条件的节点上创建一个 Pod；节点选择器、污点、容量和准入策略仍然适用。当节点添加到集群时，Pod 会自动添加；当节点移除时，Pod 也会被移除。

**主要用例**：

* 日志收集器（Fluentd、Logstash）
* 监控代理（Prometheus Node Exporter）
* 网络插件（Calico、Cilium）
* 存储守护进程（Ceph）

**DaemonSet 示例**：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intro-log-agent-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush 5
        Parsers_File /fluent-bit/etc/parsers.conf
    [INPUT]
        Name tail
        Path /var/log/containers/*.log
        Exclude_Path /var/log/containers/intro-log-agent-*_kube-system_fluent-bit-*.log
        Parser cri
        Tag kube.*
        DB /var/lib/fluent-bit/tail.db
        Mem_Buf_Limit 5MB
        Skip_Long_Lines On
    [OUTPUT]
        Name stdout
        Match *
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: intro-log-agent
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: intro-log-agent
  template:
    metadata:
      labels:
        app: intro-log-agent
    spec:
      automountServiceAccountToken: false
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
        effect: NoSchedule
      containers:
      - name: fluent-bit
        image: cr.fluentbit.io/fluent/fluent-bit:5.1.2
        securityContext:
          runAsUser: 0
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
        args:
        - -c
        - /fluent-bit/custom/fluent-bit.conf
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
          limits:
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: config
          mountPath: /fluent-bit/custom
          readOnly: true
        - name: state
          mountPath: /var/lib/fluent-bit
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
          type: Directory
      - name: config
        configMap:
          name: intro-log-agent-config
      - name: state
        hostPath:
          path: /var/lib/intro-log-agent
          type: DirectoryOrCreate
      nodeSelector:
        kubernetes.io/os: linux
```

### Job

Job 创建一个或多个 Pod，并持续执行，直到指定数量的 Pod 成功终止。适用于批处理任务。

**主要功能**：

* 一次性任务执行
* 并行任务执行
* 跟踪成功完成；失败/截止时间限制仍可能导致 Job 失败
* 失败时重试

**Job 示例**：

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

Job 可能因重试/截止时间限制而失败，也可能再次运行相同工作，因此任务应具有幂等性。CronJob 调度并非恰好一次；Forbid 仅控制该 CronJob 的重叠 Job。

### CronJob

CronJob 根据指定计划定期运行 Job。其工作方式类似 Linux cron 作业。

**主要功能**：

* 根据计划执行任务
* 支持 Cron 表达式
* 并发策略设置
* 历史记录限制

**CronJob 示例**：

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  timeZone: Etc/UTC
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

## Kubernetes Service 和网络

Kubernetes 网络模型基于以下前提：Pod 网络由兼容的 CNI 提供；可路由性受 NetworkPolicy、防火墙和拓扑影响。Service 为一组 Pod 提供稳定的端点。

### Service

Service 为一组 Pod 提供单一端点和负载均衡。由于 Pod 会动态创建和删除，Service 可在这些变化发生时提供稳定的网络地址。

**Service 类型**：

* **ClusterIP**：仅可在集群内访问的 Service（默认）
* **NodePort**：通过每个节点的 IP 和特定端口从外部访问
* **LoadBalancer**：使用云提供商的负载均衡器从外部访问
* **ExternalName**：为外部 Service 创建 CNAME 记录

![该图说明通过 NodePort 和 LoadBalancer Service 进行外部访问；Ingress/Gateway 等其他入口点也是可行的，ClusterIP Service 保持内部访问，三种 Service 类型都会将端口 80 请求负载均衡到相同的 Pod（Pod 1、2、3）。](../.gitbook/assets/en-basics-04-kubernetes-introduction-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-3.html)

**Service 示例**：

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

**NodePort Service 示例**：

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

此 AWS 示例需要 AWS Load Balancer Controller 及其 IAM/网络前提条件。EKS Auto Mode 使用不同的 loadBalancerClass；本地集群需要自身的 LoadBalancer 实现。

**LoadBalancer Service 示例**：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-lb
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
```

此示例需要已安装的 Traefik、其 traefik IngressClass、app1/app2 Service 和 TLS Secret。路径 /app1 和 /app2 会保留，且必须由后端提供服务。Ingress 资源不会安装控制器。

### Ingress

Ingress 是一个 API 对象，用于管理从集群外部到内部 Service 的 HTTP 和 HTTPS 路由。Ingress 提供负载均衡、SSL 终止、基于名称的虚拟主机等功能。

**Ingress 控制器**：

* **ingress-nginx（于 2026 年 3 月退役）**：历史社区控制器；对于新安装，请选择受维护的控制器。F5 NGINX Ingress Controller 是一个独立项目。
* **AWS Load Balancer Controller**：基于 AWS Application Load Balancer 的 Ingress 控制器
* **Traefik**：云原生边缘路由器
* **Istio Ingress**：基于 Service Mesh 的 Ingress

**Ingress 示例**：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
spec:
  ingressClassName: traefik
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

NetworkPolicy 提供了一种控制 Pod 之间通信的方法。默认情况下，所有 Pod 都可以相互通信，但您可以使用网络策略进行限制。&#x20;

![外部请求流经 default Namespace 中的 frontend、API 和数据库 Pod；db-network-policy NetworkPolicy 保护 role=db 的 Pod，而 monitoring Namespace 中的 Prometheus 会抓取全部三个层。](../.gitbook/assets/en-basics-04-kubernetes-introduction-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-4.html)

**主要功能**：

* 控制 Pod 之间的通信
* 控制 Namespace 之间的通信
* 控制入口（传入）和出口（传出）流量
* 基于端口和协议的筛选

**NetworkPolicy 示例**：

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
          role: api
    ports:
    - protocol: TCP
      port: 3306
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9104
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

NetworkPolicy 的允许规则具有累加性。该策略允许 role=api 访问 DB 的 port3306，并允许 monitoring 中的 app=prometheus 访问单独安装的 DB exporter 的 port9104。它不会使 DB 连接到 Prometheus9090。请根据实际集群 DNS/NodeLocal DNS 设置调整 DNS 出口选择器。

### DNS

Kubernetes 发行版通常部署 CoreDNS 用于 Service 发现。编辑其 ConfigMap 时请保留由发行版管理的设置。下方 Pod 的 insecure 模式在不验证 Pod 存在性的情况下提供旧版基于 IP 的记录；如果不需要这些记录，请使用 disabled；或者使用 verified，但会增加额外的监视/内存成本。

**DNS 名称格式**：

* **Service**：`<service-name>.<namespace>.svc.cluster.local`
* **Pod**：`<pod-ip-with-dashes>.<namespace>.pod.cluster.local`（IPv4 记录；取决于 CoreDNS Pod 模式）

**DNS 配置示例**：

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
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
          pods insecure
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

Service Mesh 是管理微服务之间通信的基础设施层。Service Mesh 提供流量管理、安全性和可观测性。

**主要 Service Mesh**：

* **Istio**：最广泛使用的 Service Mesh
* **Linkerd**：轻量级 Service Mesh
* **AWS App Mesh**：支持于 2026-09-30 结束；AWS 表示其控制台和资源已无法访问。

**Istio VirtualService 示例**：

```yaml
apiVersion: networking.istio.io/v1
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
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Kubernetes 存储

Kubernetes 为容器化应用程序提供各种存储选项。即使 Pod 重启或重新调度，它也提供持久化数据的方法。

![Kubernetes 存储：Pod 1 和 Pod 2 通过 PersistentVolumeClaim（pvc-1、pvc-2）绑定到 PersistentVolume（pv-1、pv-3），standard StorageClass 动态预配 PV，并且每个 PV 映射到一个 AWS EBS 卷。](../.gitbook/assets/en-basics-04-kubernetes-introduction-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-04-kubernetes-introduction-5.html)

### Volume

Volume 是可挂载到 Pod 中容器的目录，可在 Pod 生命周期内持久化数据。Volume 还用于在 Pod 中的容器之间共享数据。

**主要 Volume 类型**：

* **emptyDir**：以空目录开始，在 Pod 删除时删除
* **hostPath**：从主机节点的文件系统挂载到 Pod
* **configMap**：将 ConfigMap 作为 Volume 挂载
* **secret**：将 Secret 作为 Volume 挂载
* **persistentVolumeClaim**：将持久卷挂载到 Pod

**emptyDir Volume 示例**：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-pd
spec:
  containers:
  - name: test-container
    image: nginx:1.30.4
    volumeMounts:
    - mountPath: /cache
      name: cache-volume
  volumes:
  - name: cache-volume
    emptyDir: {}
```

### PersistentVolume (PV)

PersistentVolume 是表示集群中存储资源的 API 对象。它独立于 Pod 存在，由管理员静态预配或由存储预配程序动态预配。

**访问模式**：

* **ReadWriteOnce (RWO)**：可由单个节点读写挂载
* **ReadOnlyMany (ROX)**：可由多个节点只读挂载
* **ReadWriteMany (RWX)**：可由多个节点读写挂载
* **ReadWriteOncePod (RWOP)**：支持的 CSI 卷的单 Pod 访问；仅 RWO 仍允许同一节点上的多个 Pod

必须已安装 EBS CSI Driver 和 IAM 权限。请使用现有卷 ID 及其实际 Availability Zone；切勿重复使用仍在其他位置使用的卷。这些存储示例特定于 AWS；本地集群需要自身的预配程序。

**PersistentVolume 示例**：

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
  storageClassName: ebs-gp3
  csi:
    driver: ebs.csi.aws.com
    volumeHandle: vol-0123456789abcdef0
    fsType: ext4
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - replace-with-volume-az
```

### PersistentVolumeClaim (PVC)

PersistentVolumeClaim 是表示用户存储请求的 API 对象。Pod 通过 PVC 访问 PV。

**PersistentVolumeClaim 示例**：

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
  storageClassName: ebs-gp3
```

**使用 PVC 的 Pod 示例**：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
    - name: myfrontend
      image: nginx:1.30.4
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: pvc-example
```

### StorageClass

StorageClass 描述由管理员提供的存储“类别”。可提供不同的服务质量级别、备份策略或由集群管理员确定的任意策略。

**StorageClass 示例**：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  csi.storage.k8s.io/fstype: ext4
  encrypted: 'true'
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

### 动态预配

动态预配是一项功能，可在使用存储类别请求 PVC 时自动创建 PV。

**动态预配示例**：

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
  storageClassName: ebs-gp3
```

### CSI (Container Storage Interface)

CSI 在 Kubernetes 和存储系统之间提供标准接口。这使存储提供商能够在不修改 Kubernetes 代码的情况下开发自己的存储驱动程序。

**主要 CSI Driver**：

* **AWS EBS CSI Driver**：Amazon EBS 卷管理
* **AWS EFS CSI Driver**：Amazon EFS 文件系统管理
* **AWS FSx for Lustre CSI Driver**：FSx for Lustre 文件系统管理
* **GCE PD CSI Driver**：Google Compute Engine 持久磁盘管理
* **Azure Disk CSI Driver**：Azure 磁盘管理

**使用已安装 CSI Driver 的 StorageClass**：

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ebs-sc
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: 'true'
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
```

## Kubernetes 配置和安全

Kubernetes 提供用于管理应用程序配置和安全性的各种对象和机制。

### ConfigMap

ConfigMap 是将配置数据存储为键值对的 API 对象。Pod 可将 ConfigMap 数据用作环境变量、命令行参数或配置文件。

**ConfigMap 示例**：

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

环境变量值不会自动刷新；请在变更后重新创建 Pod。Volume 更新是最终一致的，并需要应用程序重新加载；subPath 挂载不会收到更新。

**使用 ConfigMap 的 Pod 示例**：

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

Secret 是一个存储密码、令牌和密钥等敏感信息的 API 对象。它类似于 ConfigMap，但专为敏感数据设计。

**Secret 类型**：

* **Opaque**：任意用户定义的数据（默认）
* **kubernetes.io/service-account-token**：手动请求的长寿命旧版令牌 Secret；首选 TokenRequest/投影令牌
* **kubernetes.io/dockercfg**：序列化的 \~/.dockercfg 文件
* **kubernetes.io/dockerconfigjson**：序列化的 \~/.docker/config.json 文件
* **kubernetes.io/basic-auth**：基本身份验证凭据
* **kubernetes.io/ssh-auth**：SSH 身份验证凭据
* **kubernetes.io/tls**：TLS 客户端或服务器的数据

数据字段使用 base64 编码，而非加密。请使用适合集群的 RBAC 和静态加密来保护 Secret；EKS 默认会加密 1.28+ 的所有 Kubernetes API 数据。以下值仅用于演示，必须替换。

**Secret 示例**：

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

**使用 Secret 的 Pod 示例**：

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

### RBAC (基于角色的访问控制)

RBAC 是控制对 Kubernetes API 访问的机制。它使用 Role 和 RoleBinding 向用户或服务账户授予特定权限。

**主要 RBAC 对象**：

* **Role**：定义 Namespace 中的一组权限
* **ClusterRole**：用于集群/Namespace 资源的可重用规则；绑定决定其有效范围
* **RoleBinding**：将角色绑定到用户、组或服务账户
* **ClusterRoleBinding**：将集群角色绑定到用户、组或服务账户

**Role 示例**：

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

**RoleBinding 示例**：

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

ServiceAccount 为在 Pod 内运行的进程提供身份。Pod 使用服务账户与 Kubernetes API 通信。

**ServiceAccount 示例**：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
```

**使用 ServiceAccount 的 Pod 示例**：

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

NetworkPolicy 提供了一种控制 Pod 之间通信的方法。默认情况下，所有 Pod 都可以相互通信，但您可以使用网络策略进行限制。

**NetworkPolicy 示例**：

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
          role: api
    ports:
    - protocol: TCP
      port: 3306
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9104
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Pod Security Admission 和 SecurityContext

PodSecurityPolicy 已在 1.25 中移除。Pod Security Admission 使用 Namespace 标签强制执行 Pod Security Standards。SecurityContext 配置工作负载本身；它不能替代准入强制执行。

**Pod SecurityContext 示例**：

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
  - name: app
    image: myapp:1.0
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
```

### Pod Security Standards

Pod Security Standards 提供三个策略级别，用于定义 Pod 的安全要求：

1. **Privileged**：无任何限制，允许所有功能
2. **Baseline**：防止已知的权限提升
3. **Restricted**：应用最佳实践的严格限制

**Pod Security Standards 应用示例**：

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

## Kubernetes 与 Amazon EKS

Amazon EKS（Elastic Kubernetes Service）是 AWS 提供的托管 Kubernetes 服务。EKS 通过 AWS 集成公开标准 Kubernetes API。以下比较假设使用常规 EC2 节点组；Auto Mode、Fargate 和 Hybrid Nodes 的职责和支持功能各不相同。

### 主要差异

| 特性           | 自行管理的 Kubernetes                         | Amazon EKS                                                        |
| ------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| 控制平面管理 | 用户直接管理                           | 由 AWS 管理                                                    |
| 高可用性        | 用户必须配置                             | 默认提供（部署在多个可用区） |
| 升级                 | 用户直接执行                          | AWS 管理控制平面升级；协调节点/附加组件升级                                |
| 安全补丁         | 用户直接应用                           | AWS 为控制平面打补丁；托管节点 AMI 推出仍由您负责（Auto Mode 不同）                                      |
| 身份验证           | 各种选项需要配置              | 与 AWS IAM 集成                                           |
| 网络               | 需要选择和配置 CNI 插件 | 默认提供 Amazon VPC CNI                                |
| 负载均衡           | 需要手动配置                   | AWS Load Balancer Controller 集成                          |
| 存储                  | 需要存储驱动程序配置           | EBS、EFS、FSx CSI Driver 集成                              |
| 监控               | 需要手动设置                           | CloudWatch Container Insights 集成                         |
| 成本                     | 基础设施加运维工作                       | 控制平面成本 + 基础设施成本                         |

### 其他 EKS 功能

1. **AWS IAM 集成**：Kubernetes RBAC 和 AWS IAM 集成
2. **AWS Load Balancer Controller**：ALB 和 NLB 与 Kubernetes Service 和 Ingress 的集成
3. **EKS Managed Node Groups**：节点生命周期管理自动化
4. **Fargate Profiles**：无服务器 Kubernetes Pod 执行
5. **VPC CNI Plugin**：与 AWS VPC 网络集成
6. **CloudWatch Container Insights**：容器监控和日志记录
7. **AWS App Mesh**：支持于 2026-09-30 结束；AWS 表示其控制台和资源已无法访问
8. **AWS Distro for OpenTelemetry**：分布式追踪和监控
9. **EKS Console and CLI**：管理界面
10. **EKS Blueprints**：基于最佳实践的集群配置

### EKS 特定组件

1. **EKS Control Plane**：跨多个可用区的高可用性
2. **EKS Node AMI**：AWS 提供的 AL2023/Bottlerocket/Windows 选项，以及单独提供的兼容 AMI，例如 Ubuntu
3. **EKS Managed Node Groups**：节点组更新工作流；工作负载驱动的节点扩缩容需要 autoscaler
4. **EKS Fargate**：无服务器容器执行环境
5. **EKS Connector**：将外部 Kubernetes 集群连接到 AWS 控制台
6. **EKS Anywhere**：在本地环境中运行 EKS 兼容集群
7. **EKS Distro**：AWS 管理的 Kubernetes 发行版

### AWS 服务集成

EKS 与以下 AWS 服务集成：

1. **Amazon VPC**：网络基础设施
2. **AWS IAM**：身份验证和授权
3. **Amazon ECR**：容器镜像仓库
4. **AWS Load Balancer**：应用程序流量分发
5. **Amazon EBS/EFS/FSx**：持久存储
6. **AWS CloudWatch**：监控和日志记录
7. **AWS CloudTrail**：AWS API 审计；Kubernetes API 审计需要 EKS 审计日志
8. **AWS KMS**：加密密钥管理
9. **AWS WAF**：附加到 ALB 等受支持的应用程序前门；不能直接附加到 EKS API 端点
10. **AWS Shield**：DDoS 防护
11. **AWS X-Ray**：分布式追踪
12. **AWS App Mesh**：支持于 2026-09-30 结束；现有工作负载需要迁移
13. **AWS SageMaker**：机器学习工作负载
14. **AWS Bedrock**：生成式 AI 工作负载

## Kubernetes 入门

有多种方式可以开始使用 Kubernetes。这里简要介绍如何在本地开发环境和 AWS EKS 上启动 Kubernetes。

### 本地开发环境

#### Minikube

Minikube 运行本地 Kubernetes 集群，并支持单节点和多节点配置。

**安装和启动**：

```bash
# Install
brew install minikube

# Start
minikube start

# Check status
minikube status

# Inspect workloads; see the maintained Headlamp UI section below.
kubectl get pods -A
```

#### Kind (Kubernetes in Docker)

Kind 使用容器作为节点运行本地集群，并支持 Docker/Podman/nerdctl 提供程序。

**安装和启动**：

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

Docker Desktop 提供了在 Mac 和 Windows 上轻松运行 Kubernetes 的功能。

**设置**：

1. 安装 Docker Desktop
2. Settings > Kubernetes > 勾选 “Enable Kubernetes”
3. 点击 “Apply & Restart”

### AWS EKS

#### 使用 eksctl 创建 EKS 集群

eksctl 是用于创建和管理 EKS 集群的简单 CLI 工具。

**安装和创建集群**：

```bash
# Install a reviewed eksctl release from the official eksctl-io GitHub releases,
# verify eksctl_checksums.txt, and place the binary in PATH.
eksctl version
# Use an existing short-lived AWS login/SSO profile with required permissions.
aws sts get-caller-identity
# This example provisions real AWS resources. Choose the intended account/Region,
# supported EKS version, networking and IAM configuration before running it.
: "${EKS_VERSION:?Set a version supported by EKS, not upstream latest}"
eksctl create cluster \
  --name my-cluster \
  --region ap-northeast-2 \
  --version "$EKS_VERSION" \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --node-ami-family AmazonLinux2023 \
  --node-private-networking \
  --nodes 3 --nodes-min 1 --nodes-max 4 --managed
kubectl get nodes
```

#### 使用 AWS Management Console 创建 EKS 集群

您也可以通过 AWS Management Console 创建 EKS 集群。

**步骤**：

1. 登录 AWS Management Console
2. 导航到 EKS 服务
3. 单击 “Create cluster”
4. 配置集群名称、IAM 角色、VPC 和子网
5. 配置安全组
6. 配置日志记录选项
7. 创建集群
8. 添加节点组

### kubectl 安装和配置

kubectl 是用于与 Kubernetes 集群交互的命令行工具。

**安装**：

```bash
# macOS: use a kubectl version within one minor of the API server.
brew install kubectl
```

```bash
# Linux: select an explicit compatible version and architecture.
set -euo pipefail
: "${KUBECTL_VERSION:?Set a cluster-compatible version, e.g. v1.37.1}"
case "$(uname -m)" in
  x86_64) KUBECTL_ARCH=amd64 ;;
  aarch64|arm64) KUBECTL_ARCH=arm64 ;;
  *) echo "Choose a supported kubectl architecture" >&2; exit 1 ;;
esac
curl --fail --location --output kubectl "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl"
curl --fail --location --output kubectl.sha256 "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/$KUBECTL_ARCH/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -m 0755 kubectl /usr/local/bin/kubectl
```

```powershell
$ErrorActionPreference = "Stop"
$KubectlVersion = Read-Host "Cluster-compatible kubectl version (vX.Y.Z)"
$KubectlArch = Read-Host "Architecture (amd64 or arm64)"
if ($KubectlVersion -notmatch '^v\d+\.\d+\.\d+$' -or $KubectlArch -notin @('amd64','arm64')) { throw "Invalid version/architecture" }
$BaseUrl = "https://dl.k8s.io/release/$KubectlVersion/bin/windows/$KubectlArch"
Invoke-WebRequest "$BaseUrl/kubectl.exe" -OutFile kubectl.exe
Invoke-WebRequest "$BaseUrl/kubectl.exe.sha256" -OutFile kubectl.exe.sha256
if ((Get-FileHash kubectl.exe -Algorithm SHA256).Hash -ne (Get-Content kubectl.exe.sha256).Trim()) { throw "Checksum mismatch" }
# Move the verified binary to a directory included in PATH.
```

**基本命令**：

```bash
# Check cluster info
kubectl cluster-info

# List nodes
kubectl get nodes

# Check pods in all namespaces
kubectl get pods --all-namespaces

# Create deployment
kubectl create deployment nginx --image=nginx:1.30.4

# Expose service
kubectl expose deployment nginx --port=80 --type=ClusterIP
# Run port-forward in a separate terminal; stop it when finished.
kubectl port-forward service/nginx 8080:80

# Check logs
kubectl logs <pod-name>

# Execute command in pod container
kubectl exec -it <pod-name> -- /bin/bash
```

### 使用 Headlamp UI

Kubernetes Dashboard 已归档且不再维护。请使用具有现有 RBAC 所限制身份的 Headlamp。Helm 示例禁用了自动 cluster-admin 绑定，并且不启用不安全的共享 service-account-token 模式。管理员可以单独授予范围较窄的权限。

```bash
helm repo add headlamp https://kubernetes-sigs.github.io/headlamp/
helm repo update headlamp
: "${HEADLAMP_CHART_VERSION:?Set a reviewed chart version}"
helm upgrade --install headlamp headlamp/headlamp \
  --namespace kube-system --version "$HEADLAMP_CHART_VERSION" \
  --set clusterRoleBinding.create=false \
  --set config.unsafeUseServiceAccountToken=false
kubectl -n kube-system port-forward service/headlamp 8080:80
```

在本地打开 `http://localhost:8080`，并按照所安装 Headlamp 版本的登录流程操作。公共 Ingress 需要单独配置 TLS 和身份验证。

## 结论

Kubernetes 是一个强大的平台，可自动部署、扩缩容和管理容器化应用程序。本文档涵盖的主要内容总结如下：

### 核心架构

* **Control Plane**：集群的大脑（API Server、etcd、Scheduler、Controller Manager）
* **工作节点**：运行实际应用程序的节点（kubelet、kube-proxy、Container Runtime）
* **声明式配置**：定义期望状态，Kubernetes 将当前状态匹配到期望状态

### 主要对象和资源

* **基本对象**：Pod、Service、Volume、Namespace
* **工作负载资源**：Deployment、StatefulSet、DaemonSet、Job、CronJob
* **配置和安全**：ConfigMap、Secret、RBAC、ServiceAccount
* **网络**：Service、Ingress、NetworkPolicy
* **存储**：PersistentVolume、PersistentVolumeClaim、StorageClass

### 推荐学习路径

**第 1 步：构建本地环境**

* 使用 minikube 或 kind 创建本地集群
* 学习 kubectl 命令
* 使用基本对象（Pod、Deployment、Service）练习

**第 2 步：掌握核心概念**

* 了解并练习工作负载资源
* 使用 ConfigMap 和 Secret 进行配置管理
* 使用 Service 和 Ingress 配置网络
* 使用 PV 和 PVC 管理存储

**第 3 步：学习高级功能**

* RBAC 和安全策略
* 自动扩缩容（HPA、VPA、Cluster Autoscaler）
* 监控和日志记录（Prometheus、Grafana）
* Service Mesh（Istio、Linkerd）

**第 4 步：生产运维**

* 使用 Amazon EKS 或其他托管 Kubernetes
* CI/CD 管道集成
* 灾难恢复和备份策略
* 成本优化和资源管理

### 后续步骤

* **EKS 深入研究**：EKS 特定功能（Fargate、VPC CNI、ALB Controller）
* **高级网络**：CNI 插件（Calico、Cilium）
* **可观测性**：指标、日志、追踪
* **GitOps**：ArgoCD、Flux
* **安全加固**：Pod Security Standards、Network Policies、OPA/Gatekeeper

Kubernetes 持续演进，已成为云原生应用程序开发和运维的核心要素。我们希望本文档能帮助您开启 Kubernetes 学习之旅。

### 其他学习资源

* **官方文档**：[Kubernetes 官方文档](https://kubernetes.io/docs/)提供最准确和最新的信息
* **交互式教程**：[Kubernetes 教程](https://kubernetes.io/docs/tutorials/)提供动手练习
* **社区**：[Kubernetes Slack](https://slack.k8s.io/)、[Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **认证**：CKA（Certified Kubernetes Administrator）、CKAD（Certified Kubernetes Application Developer）
* **韩国社区**：Kubernetes Korea User Group、AWS Korea User Group

## 测验

要测试您在本章所学的内容，请参加 [Kubernetes 简介测验](../quizzes/basics/04-kubernetes-introduction-quiz.md)。

## 参考资料

* [Kubernetes 官方文档](https://kubernetes.io/docs/)
* [Amazon EKS 文档](https://docs.aws.amazon.com/eks/)
* [Kubernetes GitHub 仓库](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)

## 验证参考资料

- https://kubernetes.io/releases/version-skew-policy/
- https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/
- https://kubernetes.io/docs/setup/production-environment/container-runtimes/
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- https://kubernetes.io/docs/concepts/storage/persistent-volumes/
- https://kubernetes.io/docs/reference/networking/virtual-ips/
- https://kubernetes.io/docs/concepts/services-networking/network-policies/
- https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/
- https://coredns.io/plugins/kubernetes/
- https://github.com/fluent/fluent-bit/releases/tag/v5.1.2
- https://github.com/fluent/fluent-bit/blob/v5.1.2/conf/parsers.conf
- https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html
- https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html
- https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html
- https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html
- https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html
- https://eksctl.io/installation/
- https://minikube.sigs.k8s.io/docs/tutorials/multi_node/
- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://github.com/kubernetes/dashboard/blob/master/README.md
- https://headlamp.dev/docs/latest/installation/in-cluster/
- https://github.com/kubernetes-sigs/headlamp/blob/main/charts/headlamp/values.yaml