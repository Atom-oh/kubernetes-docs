# Kubernetes 简介

> **支持的版本**：Kubernetes 1.31, 1.32, 1.33 **最后更新**：February 11, 2026

Kubernetes (K8s) 是一个开源的容器编排平台，可自动化容器化应用程序的部署、扩展和管理。本文档说明 Kubernetes 的基本概念、架构、主要组件和功能。

## 实验环境设置

要跟随本文档中的示例进行操作，你需要以下工具和环境：

### 必需工具

* **kubectl**：用于与 Kubernetes 集群交互的命令行工具
* **Container Runtime**：Docker、containerd、CRI-O 等
* **minikube** 或 **kind**：本地 Kubernetes 集群（用于开发和学习）

### 安装方法

**kubectl 安装**：

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

**minikube 安装**：

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

### 启动本地集群

```bash
minikube start
```

## 目录

* [什么是 Kubernetes？](04-kubernetes-introduction.md#what-is-kubernetes)
* [Kubernetes 的历史](04-kubernetes-introduction.md#history-of-kubernetes)
* [Kubernetes 架构](04-kubernetes-introduction.md#kubernetes-architecture)
* [Kubernetes 主组件](04-kubernetes-introduction.md#kubernetes-main-components)
* [Kubernetes 基本对象](04-kubernetes-introduction.md#kubernetes-basic-objects)
* [Kubernetes Workload 资源](04-kubernetes-introduction.md#kubernetes-workload-resources)
* [Kubernetes Service 与网络](04-kubernetes-introduction.md#kubernetes-services-and-networking)
* [Kubernetes 存储](04-kubernetes-introduction.md#kubernetes-storage)
* [Kubernetes 配置与安全](04-kubernetes-introduction.md#kubernetes-configuration-and-security)
* [Kubernetes vs Amazon EKS](04-kubernetes-introduction.md#kubernetes-vs-amazon-eks)
* [Kubernetes 入门](04-kubernetes-introduction.md#getting-started-with-kubernetes)

## 什么是 Kubernetes？

Kubernetes 在希腊语中意为“舵手”或“领航员”，它是一个开源系统，可自动化容器化应用程序的部署、扩展和运行。它受到 Google 内部 Borg 系统的启发，并于 2014 年以开源形式发布。

### Kubernetes 的关键特性

1. **Service Discovery 和 Load Balancing**：向外部暴露容器并分发流量
2. **Storage Orchestration**：自动挂载本地或云存储系统
3. **Automated Rollouts and Rollbacks**：逐步更改应用程序状态，并在出现问题时恢复到以前的状态
4. **Automatic Bin Packing**：根据资源需求将容器放置到 Node 上
5. **Self-healing**：重启失败的容器并替换无响应的容器
6. **Secret 和 Configuration Management**：存储敏感信息并更新配置
7. **Horizontal Scaling**：通过简单命令或 UI 扩展应用程序
8. **Batch Execution**：管理批处理和 CI Workload

### Kubernetes 解决的问题

* **Container Orchestration**：高效管理数百或数千个容器
* **High Availability**：确保应用程序不间断运行
* **Scalability**：基于流量增长进行自动扩展
* **Disaster Recovery**：故障时自动恢复
* **Resource Efficiency**：高效利用硬件资源
* **Declarative Configuration**：以代码形式管理基础设施
* **Multi-cloud and Hybrid Cloud**：在各种环境中实现一致的部署和管理

## Kubernetes 的历史

### 背景

* **2003-2013**：Google 内部使用名为 Borg 的容器编排系统
* **2014 年 6 月**：Google 将 Kubernetes 作为开源项目发布
* **2015 年 7 月**：Kubernetes 1.0 发布并捐赠给 Cloud Native Computing Foundation (CNCF)
* **2016-2017**：主要云提供商推出托管 Kubernetes 服务
* **2018 年及以后**：成为容器编排事实上的标准

### 名称的由来

Kubernetes (κυβερνήτης) 在希腊语中意为“舵手”或“领航员”。这象征着它在引导容器化应用程序方面的角色。缩写 K8s 的使用是因为“K”和“s”之间有 8 个字符。

### Logo 的含义

Kubernetes logo 描绘了一个带有 7 根辐条的舵轮（船舶方向盘），象征 Kubernetes 在引导容器化应用程序航向方面的角色。

## Kubernetes 架构

Kubernetes 遵循 master-node 架构。Master node（Control Plane）管理集群，worker node 运行实际的应用程序 Workload。

### Control Plane (Master) 组件

1. **kube-apiserver**：暴露 Kubernetes API 的 Control Plane 前端
2. **etcd**：用于所有集群数据的一致且高可用的键值存储
3. **kube-scheduler**：将 Pod 分配到 Node 的组件
4. **kube-controller-manager**：运行 controller 进程的组件
   * Node Controller：Node 宕机时进行通知和响应
   * Replication Controller：维持正确数量的 Pod 副本
   * Endpoints Controller：连接 Service 和 Pod
   * Service Account & Token Controller：为新的 Namespace 创建默认账户和 API 访问 token
5. **cloud-controller-manager**：包含云特定控制逻辑的组件
   * Node Controller：与云提供商检查 Node 是否已被删除
   * Route Controller：在云基础设施中设置路由
   * Service Controller：创建、更新、删除云提供商的 load balancer
   * Volume Controller：创建、附加、挂载 volume

### Node 组件

1. **kubelet**：运行在每个 Node 上的 agent，用于确保 Pod 中的容器正在运行
2. **kube-proxy**：运行在每个 Node 上的网络 proxy，用于实现 Kubernetes Service 概念
3. **Container Runtime**：负责运行容器的软件（Docker、containerd、CRI-O 等）

### 完整架构

## Kubernetes 主组件

### API Server (kube-apiserver)

API server 是暴露 Kubernetes API 的 Control Plane 前端。所有内部和外部请求都通过 API server 处理。

**关键功能**：

* 提供 REST API
* Authentication 和 authorization
* 请求验证
* 与 etcd 通信
* 可水平扩展

### etcd

etcd 是一个一致且高可用的键值存储，用于存储所有集群数据。

**关键特性**：

* 分布式系统
* 强一致性
* 高可用性
* 安全的数据存储
* 用于监控变更的 watch 功能

### Scheduler (kube-scheduler)

Scheduler 是一个 Control Plane 组件，用于选择运行新创建 Pod 的 Node。

**Scheduling 流程**：

1. **Filtering**：识别可以运行该 Pod 的 Node
2. **Scoring**：为适合的 Node 分配分数
3. **Binding**：将 Pod 分配到最优 Node

**考虑因素**：

* 资源需求（CPU、memory）
* 硬件/软件/策略约束
* Affinity/anti-affinity 规范
* 数据局部性
* Workload 干扰

### Controller Manager (kube-controller-manager)

Controller manager 是运行多个 controller 进程的 Control Plane 组件。

**主要 Controllers**：

* **Node Controller**：监控并响应 Node 状态
* **Replication Controller**：维持 Pod 副本数量
* **Endpoints Controller**：连接 Service 和 Pod
* **Service Account & Token Controller**：为 Namespace 创建默认账户和 API token
* **Job Controller**：管理一次性任务
* **CronJob Controller**：管理计划任务
* **DaemonSet Controller**：确保特定 Pod 在所有 Node 上运行
* **StatefulSet Controller**：管理有状态应用程序
* **PV Controller**：管理 persistent volume

### Cloud Controller Manager (cloud-controller-manager)

Cloud controller manager 是包含云特定控制逻辑的 Control Plane 组件。

**主要 Controllers**：

* **Node Controller**：通过云提供商 API 检查 Node 状态
* **Route Controller**：在云环境中设置路由
* **Service Controller**：创建、更新、删除云 load balancer
* **Volume Controller**：创建、附加、挂载云存储 volume

### kubelet

kubelet 是运行在每个 Node 上的 agent，用于确保 Pod 中的容器正在运行。

**关键功能**：

* 根据 PodSpec 运行容器
* 报告容器状态
* 执行容器健康检查
* 管理容器生命周期
* 报告 Node 状态

### kube-proxy

kube-proxy 是运行在每个 Node 上的网络 proxy，用于实现 Kubernetes Service 概念。

**关键功能**：

* 维护 Service IP 和端口的网络规则
* 转发连接
* 实现 load balancing

**运行模式**：

* **userspace mode**：在用户空间运行 proxy（旧版）
* **iptables mode**：使用 Linux iptables 的 NAT 实现（默认）
* **IPVS mode**：使用 Linux kernel 的 IP Virtual Server（高性能）

## Kubernetes 基本对象

Kubernetes 对象是表示集群状态的持久实体。这些对象描述集群中运行的应用程序、可用资源、策略等。

### Pod

Pod 是 Kubernetes 中最小的可部署单元，表示一个或多个容器的组合。Pod 中的容器共享存储和网络，并且始终一起调度到同一个 Node 上。

**关键特性**：

* 拥有唯一的 IP 地址
* 共享 network namespace（相同的 IP 和端口空间）
* 共享 IPC namespace
* 共享 hostname
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

Namespace 提供了一种在单个集群中隔离资源组的方法。当多个团队或项目共享同一个集群时，这非常有用。

**默认 Namespace**：

* **default**：默认 Namespace
* **kube-system**：由 Kubernetes 系统创建的对象所在的 Namespace
* **kube-public**：所有用户都可读取的对象所在的 Namespace
* **kube-node-lease**：用于 Node heartbeat 的 Namespace

**Namespace 示例**：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: development
```

### Labels 和 Selectors

Labels 是附加到对象的键值对，用于标识和选择对象。Selectors 提供了一种基于 labels 过滤对象的方法。

**Labels 示例**：

```yaml
metadata:
  labels:
    app: nginx
    environment: production
    tier: frontend
```

**Selector 类型**：

* **Equality-based**：`=`, `!=`
* **Set-based**：`in`, `notin`, `exists`

**Selector 示例**：

```yaml
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - {key: tier, operator: In, values: [frontend, middleware]}
    - {key: environment, operator: NotIn, values: [dev]}
```

### Annotations

Annotations 是用于存储对象非标识性 metadata 的键值对。Annotations 适合存储工具或库使用的信息。

**Annotations 示例**：

```yaml
metadata:
  annotations:
    kubernetes.io/created-by: "admin"
    example.com/last-modified: "2023-07-01T12:00:00Z"
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
```

### Node

Node 是 Kubernetes 集群中运行 Pod 的工作机器。Node 可以是物理机或虚拟机。

**Node 状态**：

* **Addresses**：Hostname、Internal IP、External IP
* **Conditions**：Ready、DiskPressure、MemoryPressure、PIDPressure、NetworkUnavailable
* **Capacity**：CPU、Memory、Maximum pods
* **Info**：Kernel version、Container runtime version、kubelet version

**Node 示例**：

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

## Kubernetes Workload 资源

Workload 资源是用于管理和运行 Pod 的对象。这些资源管理 Pod 的创建、扩展、更新和终止。

### ReplicaSet

ReplicaSet 确保始终运行指定数量的 Pod 副本。如果 Pod 失败或被删除，ReplicaSet 会自动创建替代 Pod。

**关键功能**：

* 维持指定数量的 Pod 副本
* 定义 Pod template
* 通过 selector 识别 Pod

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
        image: nginx:1.21
        ports:
        - containerPort: 80
```

### Deployment

Deployment 在 ReplicaSet 之上进一步抽象，为应用程序提供声明式更新。Deployment 提供 rolling update、rollback 和 scaling 等功能。

**关键功能**：

* 声明式应用程序更新
* Rolling update 和 rollback
* Deployment 历史管理
* Scaling

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

StatefulSet 是用于需要维护状态的应用程序的 Workload 资源。它为每个 Pod 分配唯一标识符，并提供稳定的网络标识符和持久存储。

**关键功能**：

* 稳定且唯一的网络标识符
* 稳定且持久的存储
* 顺序部署和扩展
* 顺序更新

**StatefulSet 示例**：

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

DaemonSet 确保 Pod 的一个副本在所有 Node（或特定 Node）上运行。当 Node 添加到集群时，Pod 会自动添加；当 Node 被移除时，Pod 也会被移除。

**主要用例**：

* 日志收集器（Fluentd、Logstash）
* Monitoring agent（Prometheus Node Exporter）
* 网络插件（Calico、Cilium）
* 存储 daemon（Ceph）

**DaemonSet 示例**：

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

Job 创建一个或多个 Pod，并持续执行，直到指定数量的 Pod 成功终止。适用于批处理任务。

**关键功能**：

* 一次性任务执行
* 并行任务执行
* 保证任务完成
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

### CronJob

CronJob 会根据指定的 schedule 周期性运行 Job。其工作方式类似于 Linux cron job。

**关键功能**：

* 根据 schedule 执行任务
* 支持 cron 表达式
* Concurrency policy 设置
* History limit

**CronJob 示例**：

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

## Kubernetes Service 与网络

Kubernetes 网络模型基于这样一个前提：所有 Pod 都拥有唯一 IP 地址，并且无需特殊配置即可彼此通信。Service 为一组 Pod 提供稳定的 endpoint。

### Service

Service 为一组 Pod 提供单一 endpoint 和 load balancing。由于 Pod 会动态创建和删除，Service 尽管面对这些变化，仍然提供稳定的网络地址。

**Service 类型**：

* **ClusterIP**：只能在集群内部访问的 Service（默认）
* **NodePort**：通过每个 Node 的 IP 和特定端口从外部访问
* **LoadBalancer**：使用云提供商的 load balancer 从外部访问
* **ExternalName**：为外部 Service 创建 CNAME 记录

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

**LoadBalancer Service 示例**：

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

Ingress 是一个 API 对象，用于管理从集群外部到内部 Service 的 HTTP 和 HTTPS 路由。Ingress 提供 load balancing、SSL termination、基于名称的 virtual hosting 等功能。

**Ingress Controllers**：

* **NGINX Ingress Controller**：基于 NGINX 的 ingress controller
* **AWS ALB Ingress Controller**：基于 AWS Application Load Balancer 的 ingress controller
* **Traefik**：Cloud-native edge router
* **Istio Ingress**：基于 service mesh 的 ingress

**Ingress 示例**：

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

NetworkPolicy 提供了一种控制 Pod 之间通信的方法。默认情况下，所有 Pod 都可以彼此通信，但你可以使用 network policy 对其进行限制。&#x20;

**关键功能**：

* 控制 Pod 之间的通信
* 控制 Namespace 之间的通信
* 控制 ingress（传入）和 egress（传出）流量
* 基于端口和协议的过滤

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

Kubernetes 在集群内提供 DNS 服务以支持 service discovery。默认使用 CoreDNS。

**DNS 名称格式**：

* **Service**：`<service-name>.<namespace>.svc.cluster.local`
* **Pod**：`<pod-IP-address-dots-replaced>.pod.cluster.local`

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

Service mesh 是一个基础设施层，用于管理微服务之间的通信。Service mesh 提供流量管理、安全性和可观测性。

**主要 Service Mesh**：

* **Istio**：使用最广泛的 service mesh
* **Linkerd**：轻量级 service mesh
* **AWS App Mesh**：AWS 托管的 service mesh

**Istio VirtualService 示例**：

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

## Kubernetes 存储

Kubernetes 为容器化应用程序提供多种存储选项。它提供了即使 Pod 重启或重新调度也能持久化数据的方法。

### Volume

Volume 是一个可以挂载到 Pod 中容器的目录，可在 Pod 生命周期内持久化数据。Volume 也用于在同一个 Pod 中的容器之间共享数据。

**主要 Volume 类型**：

* **emptyDir**：以空目录开始，在 Pod 被删除时删除
* **hostPath**：从 host Node 的文件系统挂载到 Pod
* **configMap**：将 ConfigMap 作为 volume 挂载
* **secret**：将 Secret 作为 volume 挂载
* **persistentVolumeClaim**：将 persistent volume 挂载到 Pod

**emptyDir Volume 示例**：

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

PersistentVolume 是一个 API 对象，表示集群中的存储资源。它独立于 Pod 存在，并由集群管理员进行预置。

**Access Modes**：

* **ReadWriteOnce (RWO)**：可由单个 Node 以读/写方式挂载
* **ReadOnlyMany (ROX)**：可由多个 Node 以只读方式挂载
* **ReadWriteMany (RWX)**：可由多个 Node 以读/写方式挂载

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
  storageClassName: standard
  awsElasticBlockStore:
    volumeID: vol-0123456789abcdef0
    fsType: ext4
```

### PersistentVolumeClaim (PVC)

PersistentVolumeClaim 是一个 API 对象，表示用户的存储请求。Pod 通过 PVC 访问 PV。

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
  storageClassName: standard
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

StorageClass 描述管理员提供的存储“类别”。可以提供不同的服务质量级别、备份策略，或由集群管理员确定的任意策略。

**StorageClass 示例**：

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

Dynamic provisioning 是一种功能，可在使用 storage class 请求 PVC 时自动创建 PV。

**Dynamic Provisioning 示例**：

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

CSI 在 Kubernetes 与存储系统之间提供标准接口。这使存储提供商可以在不修改 Kubernetes 代码的情况下开发自己的存储 driver。

**主要 CSI Driver**：

* **AWS EBS CSI Driver**：Amazon EBS volume 管理
* **AWS EFS CSI Driver**：Amazon EFS 文件系统管理
* **AWS FSx for Lustre CSI Driver**：FSx for Lustre 文件系统管理
* **GCE PD CSI Driver**：Google Compute Engine persistent disk 管理
* **Azure Disk CSI Driver**：Azure disk 管理

**CSI Driver Deployment 示例**：

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

## Kubernetes 配置与安全

Kubernetes 提供多种对象和机制来管理应用程序配置与安全。

### ConfigMap

ConfigMap 是一个 API 对象，以键值对形式存储配置数据。Pod 可以将 ConfigMap 数据用作环境变量、命令行参数或配置文件。

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

Secret 是一个 API 对象，用于存储密码、token 和 key 等敏感信息。它类似于 ConfigMap，但专为敏感数据设计。

**Secret 类型**：

* **Opaque**：任意用户定义数据（默认）
* **kubernetes.io/service-account-token**：Service account token
* **kubernetes.io/dockercfg**：序列化的 \~/.dockercfg 文件
* **kubernetes.io/dockerconfigjson**：序列化的 \~/.docker/config.json 文件
* **kubernetes.io/basic-auth**：用于 basic authentication 的凭证
* **kubernetes.io/ssh-auth**：用于 SSH authentication 的凭证
* **kubernetes.io/tls**：用于 TLS client 或 server 的数据

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

### RBAC (Role-Based Access Control)

RBAC 是用于控制 Kubernetes API 访问的机制。它使用 Role 和 RoleBinding 向用户或 service account 授予特定权限。

**主要 RBAC 对象**：

* **Role**：定义 Namespace 内的一组权限
* **ClusterRole**：定义集群范围内的一组权限
* **RoleBinding**：将 role 绑定到用户、组或 service account
* **ClusterRoleBinding**：将 cluster role 绑定到用户、组或 service account

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

ServiceAccount 为 Pod 内部运行的进程提供身份。Pod 使用 service account 与 Kubernetes API 通信。

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

NetworkPolicy 提供了一种控制 Pod 之间通信的方法。默认情况下，所有 Pod 都可以彼此通信，但你可以使用 network policy 对其进行限制。

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

PodSecurityPolicy 定义了 Pod 创建和更新的安全相关条件。它自 Kubernetes 1.21 起已被弃用，并由 Pod Security Standards 取代。

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
2. **Baseline**：防止已知的 privilege escalation
3. **Restricted**：应用最佳实践的强限制

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

## Kubernetes vs Amazon EKS

Amazon EKS (Elastic Kubernetes Service) 是 AWS 提供的托管 Kubernetes 服务。EKS 提供 Kubernetes 的所有基本功能，同时增加 AWS 服务集成和管理便利性。

### 关键差异

| 特性                     | Self-managed Kubernetes               | Amazon EKS                              |
| ------------------------ | ------------------------------------- | --------------------------------------- |
| Control Plane Management | 用户直接管理                          | 由 AWS 管理                             |
| High Availability        | 用户必须配置                          | 默认提供（跨多个 availability zone 部署） |
| Upgrades                 | 用户直接执行                          | 由 AWS 管理（用户可以发起）             |
| Security Patches         | 用户直接应用                          | 由 AWS 自动应用                         |
| Authentication           | 需要配置各种选项                      | 与 AWS IAM 集成                         |
| Networking               | 需要选择并配置 CNI plugin             | 默认提供 Amazon VPC CNI                 |
| Load Balancing           | 需要手动配置                          | AWS Load Balancer Controller 集成       |
| Storage                  | 需要配置 storage driver               | EBS、EFS、FSx CSI driver 集成           |
| Monitoring               | 需要手动设置                          | CloudWatch Container Insights 集成      |
| Cost                     | 仅基础设施成本                        | Control Plane 成本 + 基础设施成本       |

### 其他 EKS 功能

1. **AWS IAM Integration**：Kubernetes RBAC 与 AWS IAM 集成
2. **AWS Load Balancer Controller**：ALB 和 NLB 与 Kubernetes Service 和 Ingress 集成
3. **EKS Managed Node Groups**：Node 生命周期管理自动化
4. **Fargate Profiles**：Serverless Kubernetes Pod 执行
5. **VPC CNI Plugin**：与 AWS VPC networking 集成
6. **CloudWatch Container Insights**：容器 monitoring 和 logging
7. **AWS App Mesh**：Service mesh 集成
8. **AWS Distro for OpenTelemetry**：Distributed tracing 和 monitoring
9. **EKS Console and CLI**：管理界面
10. **EKS Blueprints**：基于最佳实践的集群配置

### EKS 特定组件

1. **EKS Control Plane**：跨多个 availability zone 的高可用性
2. **EKS Node AMI**：针对 Kubernetes 优化的 Amazon Linux 或 Ubuntu AMI
3. **EKS Managed Node Groups**：Auto scaling 和更新支持
4. **EKS Fargate**：Serverless 容器执行环境
5. **EKS Connector**：将外部 Kubernetes 集群连接到 AWS console
6. **EKS Anywhere**：在本地环境运行 EKS-compatible 集群
7. **EKS Distro**：AWS-managed Kubernetes 发行版

### AWS 服务集成

EKS 与以下 AWS 服务集成：

1. **Amazon VPC**：Networking infrastructure
2. **AWS IAM**：Authentication 和 authorization
3. **Amazon ECR**：Container image repository
4. **AWS Load Balancer**：Application traffic distribution
5. **Amazon EBS/EFS/FSx**：Persistent storage
6. **AWS CloudWatch**：Monitoring 和 logging
7. **AWS CloudTrail**：Audit 和 compliance
8. **AWS KMS**：Encryption key management
9. **AWS WAF**：Web application firewall
10. **AWS Shield**：DDoS protection
11. **AWS X-Ray**：Distributed tracing
12. **AWS App Mesh**：Service mesh
13. **AWS SageMaker**：Machine learning Workload
14. **AWS Bedrock**：Generative AI Workload

## Kubernetes 入门

有多种方式可以开始使用 Kubernetes。这里简要介绍如何在本地开发环境以及 AWS EKS 上启动 Kubernetes。

### 本地开发环境

#### Minikube

Minikube 是一个在本地机器上运行单 Node Kubernetes 集群的工具。

**安装和启动**：

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

Kind 是一个使用 Docker 容器作为 Node 在本地运行 Kubernetes 集群的工具。

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

Docker Desktop 提供了一个可在 Mac 和 Windows 上轻松运行 Kubernetes 的功能。

**设置**：

1. 安装 Docker Desktop
2. Settings > Kubernetes > Check "Enable Kubernetes"
3. Click "Apply & Restart"

### AWS EKS

#### 使用 eksctl 创建 EKS 集群

eksctl 是一个用于创建和管理 EKS 集群的简单 CLI 工具。

**安装和集群创建**：

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

#### 使用 AWS Management Console 创建 EKS 集群

你也可以通过 AWS Management Console 创建 EKS 集群。

**步骤**：

1. 登录 AWS Management Console
2. 导航到 EKS 服务
3. 点击 "Create cluster"
4. 配置集群名称、IAM role、VPC 和 subnet
5. 配置 security group
6. 配置 logging 选项
7. 创建集群
8. 添加 node group

### kubectl 安装和配置

kubectl 是用于与 Kubernetes 集群交互的命令行工具。

**安装**：

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

**基本命令**：

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

### 安装 Kubernetes Dashboard

Kubernetes Dashboard 提供用于管理集群的基于 Web 的 UI。

**安装和访问**：

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

Dashboard 可通过 http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/ 访问。

## 结论

Kubernetes 是一个强大的平台，可自动化容器化应用程序的部署、扩展和管理。本文档涵盖的关键内容总结如下：

### 核心架构

* **Control Plane**：集群的大脑（API Server、etcd、Scheduler、Controller Manager）
* **Worker Nodes**：运行实际应用程序的 Node（kubelet、kube-proxy、Container Runtime）
* **Declarative Configuration**：定义期望状态，Kubernetes 将当前状态匹配到期望状态

### 主要对象和资源

* **基本对象**：Pod、Service、Volume、Namespace
* **Workload 资源**：Deployment、StatefulSet、DaemonSet、Job、CronJob
* **配置与安全**：ConfigMap、Secret、RBAC、ServiceAccount
* **Networking**：Service、Ingress、NetworkPolicy
* **Storage**：PersistentVolume、PersistentVolumeClaim、StorageClass

### 推荐学习路径

**步骤 1：构建本地环境**

* 使用 minikube 或 kind 创建本地集群
* 学习 kubectl 命令
* 使用基本对象（Pod、Deployment、Service）进行练习

**步骤 2：掌握核心概念**

* 理解并练习 Workload 资源
* 使用 ConfigMap 和 Secret 进行配置管理
* 使用 Service 和 Ingress 配置网络
* 使用 PV 和 PVC 管理存储

**步骤 3：学习高级功能**

* RBAC 和安全策略
* Auto scaling（HPA、VPA、Cluster Autoscaler）
* Monitoring 和 logging（Prometheus、Grafana）
* Service mesh（Istio、Linkerd）

**步骤 4：生产环境运维**

* 使用 Amazon EKS 或其他托管 Kubernetes
* CI/CD pipeline 集成
* Disaster recovery 和 backup 策略
* Cost optimization 和资源管理

### 后续步骤

* **EKS Deep Dive**：EKS 特定功能（Fargate、VPC CNI、ALB Controller）
* **Advanced Networking**：CNI plugin（Calico、Cilium）
* **Observability**：Metrics、logs、tracing
* **GitOps**：ArgoCD、Flux
* **Security Hardening**：Pod Security Standards、Network Policies、OPA/Gatekeeper

Kubernetes 持续演进，并已成为 cloud-native 应用程序开发和运维的核心要素。希望本文档能帮助你开启 Kubernetes 之旅。

### 其他学习资源

* **官方文档**：[Kubernetes Official Documentation](https://kubernetes.io/docs/) 提供最准确且最新的信息
* **交互式教程**：可在 [Kubernetes Tutorials](https://kubernetes.io/docs/tutorials/) 进行动手实践
* **社区**：[Kubernetes Slack](https://slack.k8s.io/)、[Reddit r/kubernetes](https://reddit.com/r/kubernetes)
* **认证**：CKA (Certified Kubernetes Administrator)、CKAD (Certified Kubernetes Application Developer)
* **韩国社区**：Kubernetes Korea User Group、AWS Korea User Group

## 测验

要测试你在本章学到的内容，请完成 [Kubernetes 简介测验](../quizzes/basics/04-kubernetes-introduction-quiz.md)。

## 参考资料

* [Kubernetes Official Documentation](https://kubernetes.io/docs/)
* [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
* [Kubernetes GitHub Repository](https://github.com/kubernetes/kubernetes)
* [CNCF (Cloud Native Computing Foundation)](https://www.cncf.io/)
* [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way)
* [Kubernetes Patterns](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
