# Introduction to Kubernetes

> **支持的版本**: Kubernetes 1.31, 1.32, 1.33 **最后更新**: February 11, 2026

Kubernetes (K8s) 是一个开源的容器编排平台，可自动化容器化应用程序的部署、扩缩容和管理。本文档说明 Kubernetes 的基本概念、架构、主要组件和功能。

## Lab Environment Setup

要跟随本文档中的示例进行练习，你需要以下工具和环境：

### Required Tools

* **kubectl**: 用于与 Kubernetes clusters 交互的命令行工具
* **Container Runtime**: Docker、containerd、CRI-O 等
* **minikube** 或 **kind**: 本地 Kubernetes cluster（用于开发和学习）

### Installation Methods

**kubectl 安装**:

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

**minikube 安装**:

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

Kubernetes 在希腊语中意为“舵手”或“领航员”，它是一个开源系统，用于自动化容器化应用程序的部署、扩缩容和运行。它的灵感来自 Google 内部的 Borg 系统，并于 2014 年以开源形式发布。

### Key Features of Kubernetes

1. **服务发现和负载均衡**: 将容器暴露到外部并分发流量
2. **存储编排**: 自动挂载本地或云存储系统
3. **自动发布和回滚**: 逐步更改应用程序状态，并在出现问题时恢复到先前状态
4. **自动装箱**: 根据资源需求将容器放置到 nodes 上
5. **自我修复**: 重启失败的容器并替换无响应的容器
6. **Secret 和配置管理**: 存储敏感信息并更新配置
7. **水平扩缩容**: 通过简单命令或 UI 扩缩容应用程序
8. **批处理执行**: 管理批处理和 CI workloads

### Problems Kubernetes Solves

* **容器编排**: 高效管理数百或数千个容器
* **高可用性**: 确保应用程序不间断运行
* **可扩展性**: 根据流量增长自动扩缩容
* **灾难恢复**: 发生故障时自动恢复
* **资源效率**: 高效利用硬件资源
* **声明式配置**: 以代码形式管理基础设施
* **多云和混合云**: 在各种环境中实现一致的部署和管理

## History of Kubernetes

### Background

* **2003-2013**: Google 在内部使用名为 Borg 的容器编排系统
* **June 2014**: Google 将 Kubernetes 作为开源项目发布
* **July 2015**: Kubernetes 1.0 发布并捐赠给 Cloud Native Computing Foundation (CNCF)
* **2016-2017**: 主要云服务提供商推出托管 Kubernetes 服务
* **2018 and beyond**: 成为容器编排事实上的标准

### Origin of the Name

Kubernetes (κυβερνήτης) 在希腊语中意为“舵手”或“领航员”。这象征着它在引导容器化应用程序方面的角色。缩写 K8s 的使用，是因为 “K” 和 “s” 之间有 8 个字符。

### Meaning of the Logo

Kubernetes 标志描绘了一个带有 7 根辐条的船舵，象征 Kubernetes 在引导容器化应用程序航向方面的作用。

## Kubernetes Architecture

Kubernetes 遵循 master-node 架构。Master nodes (control plane) 管理 cluster，worker nodes 运行实际的应用程序 workloads。

### Control Plane (Master) Components

1. **kube-apiserver**: 暴露 Kubernetes API 的 control plane 前端
2. **etcd**: 用于所有 cluster 数据的一致且高可用的键值存储
3. **kube-scheduler**: 将 pods 分配给 nodes 的组件
4. **kube-controller-manager**: 运行 controller 进程的组件
   * Node Controller: 当 nodes 宕机时进行通知和响应
   * Replication Controller: 维护正确数量的 pod 副本
   * Endpoints Controller: 连接 services 和 pods
   * Service Account & Token Controller: 为新的 namespaces 创建默认 accounts 和 API 访问 tokens
5. **cloud-controller-manager**: 包含云特定控制逻辑的组件
   * Node Controller: 向云提供商检查 node 是否已被删除
   * Route Controller: 在云基础设施中设置 routes
   * Service Controller: 创建、更新、删除云提供商 load balancers
   * Volume Controller: 创建、附加、挂载 volumes

### Node Components

1. **kubelet**: 运行在每个 node 上的 agent，确保 pods 中的容器正在运行
2. **kube-proxy**: 运行在每个 node 上的网络代理，实现 Kubernetes Service 概念
3. **Container Runtime**: 负责运行容器的软件（Docker、containerd、CRI-O 等）

### Full Architecture

## Kubernetes Main Components

### API Server (kube-apiserver)

API server 是 control plane 的前端，用于暴露 Kubernetes API。所有内部和外部请求都通过 API server 处理。

**关键功能**:

* 提供 REST API
* 身份验证和授权
* 请求验证
* 与 etcd 通信
* 可水平扩展

### etcd

etcd 是一个一致且高可用的键值存储，用于存储所有 cluster 数据。

**关键特性**:

* 分布式系统
* 强一致性
* 高可用性
* 安全数据存储
* 用于监控变更的 Watch 功能

### Scheduler (kube-scheduler)

Scheduler 是一个 control plane 组件，用于选择 nodes 来运行新创建的 pods。

**调度过程**:

1. **过滤**: 识别可以运行 pod 的 nodes
2. **评分**: 为合适的 nodes 分配分数
3. **绑定**: 将 pod 分配到最优 node

**考虑因素**:

* 资源需求（CPU、内存）
* 硬件/软件/策略约束
* Affinity/anti-affinity 规范
* 数据本地性
* Workload 干扰

### Controller Manager (kube-controller-manager)

Controller manager 是一个 control plane 组件，用于运行多个 controller 进程。

**主要 Controllers**:

* **Node Controller**: 监控并响应 node 状态
* **Replication Controller**: 维护 pod 副本数量
* **Endpoints Controller**: 连接 services 和 pods
* **Service Account & Token Controller**: 为 namespaces 创建默认 accounts 和 API tokens
* **Job Controller**: 管理一次性任务
* **CronJob Controller**: 管理计划任务
* **DaemonSet Controller**: 确保特定 pods 在所有 nodes 上运行
* **StatefulSet Controller**: 管理有状态应用程序
* **PV Controller**: 管理 persistent volumes

### Cloud Controller Manager (cloud-controller-manager)

Cloud controller manager 是一个 control plane 组件，包含云特定的控制逻辑。

**主要 Controllers**:

* **Node Controller**: 通过云提供商 API 检查 node 状态
* **Route Controller**: 在云环境中设置 routes
* **Service Controller**: 创建、更新、删除云 load balancers
* **Volume Controller**: 创建、附加、挂载云存储 volumes

### kubelet

kubelet 是运行在每个 node 上的 agent，用于确保 pods 中的容器正在运行。

**关键功能**:

* 按照 PodSpec 运行容器
* 报告容器状态
* 执行容器健康检查
* 管理容器生命周期
* 报告 node 状态

### kube-proxy

kube-proxy 是运行在每个 node 上的网络代理，用于实现 Kubernetes Service 概念。

**关键功能**:

* 维护 service IP 和端口的网络规则
* 转发连接
* 实现负载均衡

**运行模式**:

* **userspace mode**: 在用户空间运行代理（旧模式）
* **iptables mode**: 使用 Linux iptables 实现 NAT（默认）
* **IPVS mode**: 使用 Linux kernel 的 IP Virtual Server（高性能）

## Kubernetes Basic Objects

Kubernetes objects 是表示 cluster 状态的持久化实体。这些 objects 描述 cluster 中正在运行的应用程序、可用资源、策略等。

### Pod

Pod 是 Kubernetes 中最小的可部署单元，表示一个或多个容器的组合。Pod 中的容器共享存储和网络，并且始终一起调度到同一个 node 上。

**关键特性**:

* 拥有唯一的 IP 地址
* 共享 network namespace（相同 IP 和端口空间）
* 共享 IPC namespace
* 共享 hostname
* 容器之间可以通过 localhost 通信

**Pod 示例**:

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

Namespaces 提供了一种在单个 cluster 中隔离资源组的方式。当多个团队或项目共享同一个 cluster 时，这非常有用。

**默认 Namespaces**:

* **default**: 默认 namespace
* **kube-system**: Kubernetes system 创建的 objects 所在 namespace
* **kube-public**: 所有用户都可读取的 objects 所在 namespace
* **kube-node-lease**: 用于 node heartbeats 的 namespace

**Namespace 示例**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Labels and Selectors

Labels 是附加到 objects 的键值对，用于识别和选择 objects。Selectors 提供了一种基于 labels 过滤 objects 的方式。

**Labels 示例**:

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**Selector 类型**:

* **基于相等性**: `=`, `!=`
* **基于集合**: `in`, `notin`, `exists`

**Selector 示例**:

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### Annotations

Annotations 是存储有关 objects 的非标识性元数据的键值对。Annotations 适合存储工具或库使用的信息。

**Annotations 示例**:

```yaml
metadata:
  annotations:
    kubernetes.io/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Node

Node 是 Kubernetes cluster 中运行 pods 的 worker 机器。Node 可以是物理机或虚拟机。

**Node 状态**:

* **Addresses**: Hostname, Internal IP, External IP
* **Conditions**: Ready, DiskPressure, MemoryPressure, PIDPressure, NetworkUnavailable
* **Capacity**: CPU, Memory, Maximum pods
* **Info**: Kernel version, Container runtime version, kubelet version

**Node 示例**:

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

Workload resources 是用于管理和运行 pods 的 objects。这些 resources 管理 pods 的创建、扩缩容、更新和终止。

### ReplicaSet

ReplicaSet 确保始终运行指定数量的 pod 副本。如果 pods 失败或被删除，ReplicaSet 会自动创建替代 pods。

**关键功能**:

* 维护指定数量的 pod 副本
* 定义 pod 模板
* 通过 selectors 识别 pods

**ReplicaSet 示例**:

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

Deployment 在 ReplicaSets 的基础上进一步抽象，为应用程序提供声明式更新。Deployments 提供 rolling updates、rollbacks 和 scaling 等功能。

**关键功能**:

* 声明式应用程序更新
* Rolling updates 和 rollbacks
* Deployment 历史管理
* Scaling

**Deployment 示例**:

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

StatefulSet 是用于需要保持状态的应用程序的 workload resource。它为每个 pod 分配唯一标识符，并提供稳定的网络标识符和持久存储。

**关键功能**:

* 稳定且唯一的网络标识符
* 稳定且持久的存储
* 顺序部署和扩缩容
* 顺序更新

**StatefulSet 示例**:

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

DaemonSet 确保在所有 nodes（或特定 nodes）上运行一个 pod 副本。当 nodes 添加到 cluster 时，pods 会自动添加；当 nodes 被移除时，pods 也会被移除。

**主要使用场景**:

* 日志收集器（Fluentd、Logstash）
* 监控 agents（Prometheus Node Exporter）
* 网络 plugins（Calico、Cilium）
* 存储 daemons（Ceph）

**DaemonSet 示例**:

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

Job 创建一个或多个 pods，并持续执行直到指定数量的 pods 成功终止。适用于批处理任务。

**关键功能**:

* 一次性任务执行
* 并行任务执行
* 保证任务完成
* 失败时重试

**Job 示例**:

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

CronJob 根据指定 schedule 定期运行 Jobs。工作方式类似 Linux cron jobs。

**关键功能**:

* 按 schedule 执行任务
* 支持 Cron 表达式
* 并发策略设置
* 历史记录限制

**CronJob 示例**:

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

Kubernetes 网络模型基于这样一个前提：所有 pods 都有唯一的 IP 地址，并且无需特殊配置即可相互通信。Services 为一组 pods 提供稳定的 endpoints。

### Service

Service 为一组 pods 提供单一 endpoint 和负载均衡。由于 pods 会动态创建和删除，services 可以在这些变化发生时仍提供稳定的网络地址。

**Service 类型**:

* **ClusterIP**: 只能在 cluster 内访问的 Service（默认）
* **NodePort**: 通过每个 node 的 IP 和特定端口从外部访问
* **LoadBalancer**: 使用云提供商的 load balancer 从外部访问
* **ExternalName**: 为外部 service 创建 CNAME 记录

**Service 示例**:

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

**NodePort Service 示例**:

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

**LoadBalancer Service 示例**:

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

Ingress 是一个 API object，用于管理从 cluster 外部到内部 services 的 HTTP 和 HTTPS 路由。Ingress 提供负载均衡、SSL termination、基于名称的 virtual hosting 等。

**Ingress Controllers**:

* **NGINX Ingress Controller**: 基于 NGINX 的 ingress controller
* **AWS ALB Ingress Controller**: 基于 AWS Application Load Balancer 的 ingress controller
* **Traefik**: 云原生 edge router
* **Istio Ingress**: 基于 service mesh 的 ingress

**Ingress 示例**:

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

NetworkPolicy 提供了一种控制 pods 之间通信的方式。默认情况下，所有 pods 都可以相互通信，但你可以使用 network policies 来限制。&#x20;

**关键功能**:

* 控制 pods 之间的通信
* 控制 namespaces 之间的通信
* 控制 ingress（入站）和 egress（出站）流量
* 基于端口和协议的过滤

**NetworkPolicy 示例**:

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

Kubernetes 在 cluster 内提供 DNS service 以支持 service discovery。默认使用 CoreDNS。

**DNS 名称格式**:

* **Service**: `<service-name>.<namespace>.svc.cluster.local`
* **Pod**: `<pod-IP-address-dots-replaced>.pod.cluster.local`

**DNS 配置示例**:

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

Service mesh 是一个基础设施层，用于管理 microservices 之间的通信。Service meshes 提供流量管理、安全性和可观测性。

**主要 Service Meshes**:

* **Istio**: 使用最广泛的 service mesh
* **Linkerd**: 轻量级 service mesh
* **AWS App Mesh**: AWS 托管的 service mesh

**Istio VirtualService 示例**:

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

Kubernetes 为容器化应用程序提供各种存储选项。它提供了即使 pods 重启或重新调度后也能持久化数据的方式。

### Volume

Volume 是可以挂载到 pod 中容器的目录，用于在 pod 生命周期内持久保存数据。Volumes 也用于在 pod 中的容器之间共享数据。

**主要 Volume 类型**:

* **emptyDir**: 以空目录开始，在 pod 被删除时删除
* **hostPath**: 从 host node 的文件系统挂载到 pod
* **configMap**: 将 ConfigMap 挂载为 volume
* **secret**: 将 Secret 挂载为 volume
* **persistentVolumeClaim**: 将 persistent volume 挂载到 pod

**emptyDir Volume 示例**:

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

PersistentVolume 是一个 API object，表示 cluster 中的存储资源。它独立于 pods 存在，并由 cluster administrators 预置。

**访问模式**:

* **ReadWriteOnce (RWO)**: 可由单个 node 以读写方式挂载
* **ReadOnlyMany (ROX)**: 可由多个 nodes 以只读方式挂载
* **ReadWriteMany (RWX)**: 可由多个 nodes 以读写方式挂载

**PersistentVolume 示例**:

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

PersistentVolumeClaim 是一个 API object，表示用户的存储请求。Pods 通过 PVCs 访问 PVs。

**PersistentVolumeClaim 示例**:

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

**使用 PVC 的 Pod 示例**:

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

StorageClass 描述由 administrators 提供的存储“classes”。可以提供不同的服务质量等级、备份策略，或由 cluster administrators 确定的任意策略。

**StorageClass 示例**:

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

Dynamic provisioning 是一种功能，可在使用 storage classes 请求 PVCs 时自动创建 PVs。

**Dynamic Provisioning 示例**:

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

CSI 在 Kubernetes 和存储系统之间提供标准接口。这使存储提供商无需修改 Kubernetes 代码即可开发自己的 storage drivers。

**主要 CSI Drivers**:

* **AWS EBS CSI Driver**: Amazon EBS volume 管理
* **AWS EFS CSI Driver**: Amazon EFS file system 管理
* **AWS FSx for Lustre CSI Driver**: FSx for Lustre file system 管理
* **GCE PD CSI Driver**: Google Compute Engine persistent disk 管理
* **Azure Disk CSI Driver**: Azure disk 管理

**CSI Driver Deployment 示例**:

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

Kubernetes 提供各种 objects 和机制，用于管理应用程序配置和安全性。

### ConfigMap

ConfigMap 是一个 API object，用于以键值对形式存储配置数据。Pods 可以将 ConfigMap 数据用作环境变量、命令行参数或配置文件。

**ConfigMap 示例**:

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

**使用 ConfigMap 的 Pod 示例**:

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

Secret 是一个 API object，用于存储密码、tokens 和 keys 等敏感信息。它类似于 ConfigMap，但专为敏感数据设计。

**Secret 类型**:

* **Opaque**: 任意用户定义数据（默认）
* **kubernetes.io/service-account-token**: Service account token
* **kubernetes.io/dockercfg**: 序列化的 \~/.dockercfg 文件
* **kubernetes.io/dockerconfigjson**: 序列化的 \~/.docker/config.json 文件
* **kubernetes.io/basic-auth**: 用于 basic authentication 的 credentials
* **kubernetes.io/ssh-auth**: 用于 SSH authentication 的 credentials
* **kubernetes.io/tls**: 用于 TLS client 或 server 的数据

**Secret 示例**:

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

**使用 Secret 的 Pod 示例**:

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

RBAC 是一种控制 Kubernetes API 访问的机制。它使用 Roles 和 RoleBindings 向用户或 service accounts 授予特定权限。

**主要 RBAC Objects**:

* **Role**: 在 namespace 内定义一组权限
* **ClusterRole**: 在整个 cluster 范围内定义一组权限
* **RoleBinding**: 将 role 绑定到 users、groups 或 service accounts
* **ClusterRoleBinding**: 将 cluster role 绑定到 users、groups 或 service accounts

**Role 示例**:

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

**RoleBinding 示例**:

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

ServiceAccount 为 pod 内部运行的进程提供身份。Pods 使用 service accounts 与 Kubernetes API 通信。

**ServiceAccount 示例**:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
```

**使用 ServiceAccount 的 Pod 示例**:

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

NetworkPolicy 提供了一种控制 pods 之间通信的方式。默认情况下，所有 pods 都可以相互通信，但你可以使用 network policies 来限制。

**NetworkPolicy 示例**:

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

PodSecurityPolicy 定义 pod 创建和更新的安全相关条件。它从 Kubernetes 1.21 起已被弃用，并由 Pod Security Standards 取代。

**Pod SecurityContext 示例**:

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

Pod Security Standards 提供三个策略级别，用于定义 pods 的安全要求：

1. **Privileged**: 无限制，允许所有功能
2. **Baseline**: 防止已知的 privilege escalations
3. **Restricted**: 应用最佳实践的强限制

**Pod Security Standards 应用示例**:

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

Amazon EKS (Elastic Kubernetes Service) 是 AWS 提供的托管 Kubernetes 服务。EKS 在提供 Kubernetes 所有基本功能的同时，还增加了 AWS 服务集成和管理便利性。

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

1. **AWS IAM Integration**: Kubernetes RBAC 与 AWS IAM 集成
2. **AWS Load Balancer Controller**: ALB 和 NLB 与 Kubernetes services 和 ingress 集成
3. **EKS Managed Node Groups**: Node 生命周期管理自动化
4. **Fargate Profiles**: Serverless Kubernetes pod 执行
5. **VPC CNI Plugin**: 与 AWS VPC networking 集成
6. **CloudWatch Container Insights**: 容器监控和日志记录
7. **AWS App Mesh**: Service mesh 集成
8. **AWS Distro for OpenTelemetry**: 分布式 tracing 和监控
9. **EKS Console and CLI**: 管理接口
10. **EKS Blueprints**: 基于最佳实践的 cluster 配置

### EKS-Specific Components

1. **EKS Control Plane**: 跨多个 availability zones 的高可用性
2. **EKS Node AMI**: 为 Kubernetes 优化的 Amazon Linux 或 Ubuntu AMI
3. **EKS Managed Node Groups**: Auto scaling 和更新支持
4. **EKS Fargate**: Serverless 容器执行环境
5. **EKS Connector**: 将外部 Kubernetes clusters 连接到 AWS console
6. **EKS Anywhere**: 在 on-premises 环境中运行 EKS-compatible clusters
7. **EKS Distro**: AWS-managed Kubernetes 发行版

### AWS Service Integration

EKS 与以下 AWS 服务集成：

1. **Amazon VPC**: Networking 基础设施
2. **AWS IAM**: 身份验证和授权
3. **Amazon ECR**: 容器镜像 repository
4. **AWS Load Balancer**: 应用程序流量分发
5. **Amazon EBS/EFS/FSx**: Persistent storage
6. **AWS CloudWatch**: 监控和日志记录
7. **AWS CloudTrail**: 审计和合规
8. **AWS KMS**: 加密 key 管理
9. **AWS WAF**: Web application firewall
10. **AWS Shield**: DDoS protection
11. **AWS X-Ray**: Distributed tracing
12. **AWS App Mesh**: Service mesh
13. **AWS SageMaker**: Machine learning workloads
14. **AWS Bedrock**: Generative AI workloads

## Getting Started with Kubernetes

开始使用 Kubernetes 有几种方式。这里我们简要介绍如何在本地开发环境和 AWS EKS 上启动 Kubernetes。

### Local Development Environment

#### Minikube

Minikube 是一个在本地机器上运行单节点 Kubernetes cluster 的工具。

**安装和启动**:

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

Kind 是一个使用 Docker 容器作为 nodes 在本地运行 Kubernetes clusters 的工具。

**安装和启动**:

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

**设置**:

1. 安装 Docker Desktop
2. Settings > Kubernetes > Check "Enable Kubernetes"
3. Click "Apply & Restart"

### AWS EKS

#### Creating EKS Cluster with eksctl

eksctl 是一个用于创建和管理 EKS clusters 的简单 CLI 工具。

**安装和创建 Cluster**:

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

你也可以通过 AWS Management Console 创建 EKS clusters。

**步骤**:

1. 登录 AWS Management Console
2. 导航到 EKS service
3. Click "Create cluster"
4. 配置 cluster name、IAM role、VPC 和 subnets
5. 配置 security groups
6. 配置 logging options
7. 创建 cluster
8. 添加 node groups

### kubectl Installation and Configuration

kubectl 是用于与 Kubernetes clusters 交互的命令行工具。

**安装**:

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

**基本命令**:

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

Kubernetes Dashboard 提供用于管理 clusters 的基于 Web 的 UI。

**安装和访问**:

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

可以通过 http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/ 访问 dashboard。

## Conclusion

Kubernetes 是一个强大的平台，可自动化容器化应用程序的部署、扩缩容和管理。本文档涵盖的关键内容总结如下：

### Core Architecture

* **Control Plane**: Cluster 的大脑（API Server、etcd、Scheduler、Controller Manager）
* **Worker Nodes**: 运行实际应用程序的 nodes（kubelet、kube-proxy、Container Runtime）
* **Declarative Configuration**: 定义期望状态，Kubernetes 将当前状态匹配到期望状态

### Main Objects and Resources

* **Basic Objects**: Pod, Service, Volume, Namespace
* **Workload Resources**: Deployment, StatefulSet, DaemonSet, Job, CronJob
* **Configuration and Security**: ConfigMap, Secret, RBAC, ServiceAccount
* **Networking**: Service, Ingress, NetworkPolicy
* **Storage**: PersistentVolume, PersistentVolumeClaim, StorageClass

### Recommended Learning Path

**Step 1: Build Local Environment**

* 使用 minikube 或 kind 创建本地 cluster
* 学习 kubectl 命令
* 使用基本 objects（Pod、Deployment、Service）进行练习

**Step 2: Master Core Concepts**

* 理解并练习 workload resources
* 使用 ConfigMap 和 Secret 进行配置管理
* 使用 Service 和 Ingress 配置 networking
* 使用 PV 和 PVC 管理 storage

**Step 3: Learn Advanced Features**

* RBAC 和安全策略
* Auto scaling（HPA、VPA、Cluster Autoscaler）
* 监控和日志记录（Prometheus、Grafana）
* Service mesh（Istio、Linkerd）

**Step 4: Production Operations**

* 使用 Amazon EKS 或其他托管 Kubernetes
* CI/CD pipeline 集成
* 灾难恢复和备份策略
* 成本优化和资源管理

### Next Steps

* **EKS Deep Dive**: EKS-specific features（Fargate、VPC CNI、ALB Controller）
* **Advanced Networking**: CNI plugins（Calico、Cilium）
* **Observability**: Metrics、logs、tracing
* **GitOps**: ArgoCD、Flux
* **Security Hardening**: Pod Security Standards、Network Policies、OPA/Gatekeeper

Kubernetes 持续演进，并已成为云原生应用程序开发和运营的核心要素。希望本文档能帮助你开启 Kubernetes 之旅。

### Additional Learning Resources

* **Official Documentation**: [Kubernetes Official Documentation](https://kubernetes.io/docs/) 提供最准确且最新的信息
* **Interactive Tutorials**: 可在 [Kubernetes Tutorials](https://kubernetes.io/docs/tutorials/) 进行动手实践
* **Community**: [Kubernetes Slack](https://slack.k8s.io/), [Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **Certifications**: CKA (Certified Kubernetes Administrator), CKAD (Certified Kubernetes Application Developer)
* **Korean Community**: Kubernetes Korea User Group, AWS Korea User Group

## Quiz

要测试你在本章中学到的内容，请参加 [Introduction to Kubernetes Quiz](../quizzes/basics/04-kubernetes-introduction-quiz.md)。

## References

* [Kubernetes Official Documentation](https://kubernetes.io/docs/)
* [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
* [Kubernetes GitHub Repository](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
