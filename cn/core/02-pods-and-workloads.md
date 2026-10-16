# Kubernetes Pod 和工作负载

> **支持的版本**: Kubernetes 1.35, 1.36, 1.37
> **最后更新**: October 12, 2026

本文详细说明 Kubernetes 中的基本执行单元 Pod，以及用于管理它们的各种工作负载资源。我们将从 Pod 概念开始，介绍 Deployment、StatefulSet、DaemonSet 等多种工作负载资源的特性和使用场景。

## 实验环境设置

要跟随本文中的示例，您需要以下工具和环境：

### 所需工具
- 与 API server 相差不超过一个次要版本的 kubectl
- 可用的 Kubernetes 集群（EKS、minikube、kind 等）

### 部署示例应用程序

```bash
# Create namespace
kubectl create namespace workloads-demo

# Create a simple deployment
kubectl -n workloads-demo apply -f - <<EOF
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
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
EOF

# Check deployment status
kubectl -n workloads-demo get deployments,pods
```

## 目录
- [Pod 概念](#pod-concepts)
- [Pod 生命周期](#pod-lifecycle)
- [Pod 设计模式](#pod-design-patterns)
- [工作负载资源概述](#workload-resources-overview)
- [ReplicaSet](#replicaset)
- [Deployment](#deployment)
- [StatefulSet](#statefulset)
- [DaemonSet](#daemonset)
- [Job 和 CronJob](#jobs-and-cronjobs)

## Pod 概念

> **核心概念**：Pod 是 Kubernetes 中最小的可部署计算单元，由共享存储和网络的一个或多个容器组构成。

Pod 是 Kubernetes 中最小的可部署计算单元。Pod 是一个或多个容器组成的组，它们共享存储和网络，并被共同调度。

### Pod 特性

1. **共享上下文**：容器共享 Pod 网络，通常也共享 IPC；进程命名空间共享需要 `shareProcessNamespace: true`。容器根文件系统仍然彼此独立。
2. **同一节点**：Pod 中的所有容器始终运行在同一节点上。
3. **唯一 IP 地址**：每个 Pod 在集群内都有唯一的 IP 地址。
4. **临时性**：Pod 本质上是临时的，发生故障时可以被新的 Pod 替换。
5. **原子单元**：Pod 是部署、调度和复制的原子单元。

### Pod 结构

Pod 由以下组件构成：

1. **容器**：在 Pod 中运行的一个或多个容器
2. **卷**：Pod 中容器共享的存储
3. **网络**：分配给 Pod 的 IP 地址和端口
4. **容器规范**：容器镜像、环境变量、资源需求等

![Kubernetes Pod 边界：应用程序容器、sidecar 容器和 init 容器共享一个 Pod IP 地址和网络命名空间，旁边还有四类可挂载存储卷（emptyDir、configMap、secret、persistentVolumeClaim）。](../.gitbook/assets/en-core-02-pods-and-workloads-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-core-02-pods-and-workloads-0.html)

### Pod 示例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: multi-container-pod
  labels:
    app: web
spec:
  containers:
  - name: web
    image: nginx:1.30.4
    ports:
    - containerPort: 80
    volumeMounts:
    - name: shared-data
      mountPath: /usr/share/nginx/html
  - name: content-updater
    image: alpine
    command: ["/bin/sh", "-c"]
    args:
    - |
      while true; do
        echo "Current time: $(date)" > /content/index.html;
        sleep 10;
      done
    volumeMounts:
    - name: shared-data
      mountPath: /content
  volumes:
  - name: shared-data
    emptyDir: {}
```

### 实际示例：Web 应用程序 Pod

以下示例展示一个包含 Web 应用程序和 sidecar 容器的 Pod：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
  labels:
    app: web
    environment: production
spec:
  containers:
  - name: web-application
    image: nginx:1.30.4
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx
    ports:
    - containerPort: 80
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "256Mi"
        cpu: "500m"
  - name: log-collector
    image: fluentd:v1.19-debian-1
    volumeMounts:
    - name: log-volume
      mountPath: /var/log/nginx
    resources:
      requests:
        memory: "64Mi"
        cpu: "50m"
      limits:
        memory: "128Mi"
        cpu: "100m"
  volumes:
  - name: log-volume
    emptyDir: {}
```

此示例演示以下实际场景：
- 将 Nginx Web server 作为主容器运行
- 将 Fluentd 日志收集器作为 sidecar 容器运行
- 在两个容器之间共享日志卷
- 为每个容器设置资源请求和限制

此配置适合在微服务架构中运行紧密关联的容器，同时分离日志记录、监控和代理等功能。

这些日志清单展示了卷的连接方式。Fluentd 还需要显式的 tail 源和输出配置；仅挂载目录不会收集其日志。镜像和应用程序配置仅用于说明，并非生产版本建议。原生 sidecar 使用带有 `restartPolicy: Always` 的 `initContainers`（自 v1.33 起稳定）；普通多容器 Pod 不保证启动或关闭顺序。

### Pod 定义

Pod 使用 YAML 或 JSON 格式的清单文件定义。以下是基本 Pod 定义示例：

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
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### 单容器与多容器 Pod

**单容器 Pod**：
- 最常见的使用场景
- 仅包含一个应用程序容器
- 结构简单直观

**多容器 Pod**：
- 包含多个紧密耦合的容器
- 容器之间可进行本地通信（localhost）
- 通过共享卷共享数据
- 共同扩缩容和放置

### 多容器 Pod 模式

1. **Sidecar 模式**：扩展主容器功能的辅助容器
   - 示例：日志收集器、文件同步、代理

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-sidecar
spec:
  containers:
  - name: web
    image: nginx:1.30.4
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  - name: log-collector
    image: fluentd:v1.19-debian-1
    volumeMounts:
    - name: logs
      mountPath: /var/log/nginx
  volumes:
  - name: logs
    emptyDir: {}
```

2. **Ambassador 模式**：充当外部服务代理的容器
   - 示例：数据库代理、服务网格 sidecar

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-ambassador
spec:
  containers:
  - name: app
    image: myapp:1.0
  - name: ambassador
    image: envoyproxy/envoy:v1.20.0
    ports:
    - containerPort: 9901
```

3. **Adapter 模式**：标准化主容器输出的容器
   - 示例：日志格式转换、指标转换

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-adapter
spec:
  containers:
  - name: app
    image: myapp:1.0
    volumeMounts:
    - name: app-logs
      mountPath: /var/log/app
  - name: adapter
    image: adapter:1.0
    volumeMounts:
    - name: app-logs
      mountPath: /var/log/app
  volumes:
  - name: app-logs
    emptyDir: {}
```

4. **Init 容器模式**：在主容器启动前运行的容器
   - 示例：创建配置文件、数据库迁移、权限设置

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: app-with-init
spec:
  initContainers:
  - name: init-db
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup db; do echo waiting for db; sleep 2; done;']
  containers:
  - name: app
    image: myapp:1.0
```

### Pod 网络

Pod 中的容器具有以下网络特性：

1. **相同 IP 地址**：Pod 中所有容器共享同一 IP 地址。
2. **端口共享**：Pod 中的容器共享端口空间，因此通常不能绑定相同的 IP/协议/端口组合。
3. **Localhost 通信**：Pod 中的容器可通过 localhost 彼此通信。
4. **Pod 间通信**：每个 Pod 都有唯一 IP 地址，可直接与其他 Pod 通信。

### Pod 存储

Pod 可以使用各种类型的卷来存储和共享数据：

1. **emptyDir**：创建 Pod 时创建、删除 Pod 时删除的临时卷
2. **hostPath**：从主机节点文件系统挂载到 Pod 的卷
3. **persistentVolumeClaim**：请求持久存储的卷
4. **configMap**：作为卷挂载的 ConfigMap
5. **secret**：作为卷挂载的 Secret
6. **projected**：映射到同一目录的多个卷源

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-volumes
spec:
  containers:
  - name: app
    image: myapp:1.0
    volumeMounts:
    - name: data
      mountPath: /data
    - name: config
      mountPath: /etc/config
  volumes:
  - name: data
    emptyDir: {}
  - name: config
    configMap:
      name: app-config
```

## Pod 生命周期

Pod 从创建到终止会经历多个生命周期阶段。了解该生命周期对于确保应用程序稳定性和可用性非常重要。

### Pod 阶段

Pod 会经历以下阶段：

1. **Pending**：Pod 已被集群接受，但一个或多个容器尚未设置完成
2. **Running**：Pod 已绑定到节点，所有容器均已创建，并且至少有一个容器正在运行、启动或重启
3. **Succeeded**：Pod 中所有容器均已成功终止，且不会重启
4. **Failed**：Pod 中所有容器均已终止，且至少一个容器因失败而终止
5. **Unknown**：由于某种原因无法获取 Pod 状态

### 容器状态

Pod 中的每个容器可具有以下状态：

1. **Waiting**：容器运行前的状态（下载镜像、等待依赖项等）
2. **Running**：进程正在执行；仅此状态并不能表明应用程序健康或就绪
3. **Terminated**：容器已完成执行或因某种原因失败

### Pod Conditions

Pod 通过以下 Conditions 更具体地表示其状态：

1. **PodScheduled**：Pod 是否已调度到节点
2. **ContainersReady**：Pod 中所有容器是否就绪
3. **Initialized**：常规 init 容器已完成，且可重启 init 容器（原生 sidecar）已启动
4. **Ready**：Pod 是否能够处理请求并加入 Service 的负载均衡池

### 容器探针

Kubernetes 提供以下探针以检查容器状态：

1. **livenessProbe**：检查容器是否存活；失败时重启容器
2. **readinessProbe**：检查容器是否已准备好处理请求；失败时从 Service 流量中排除
3. **startupProbe**：检查容器中的应用程序是否已启动；成功前禁用其他探针

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-probes
spec:
  containers:
  - name: app
    image: myapp:1.0
    ports:
    - containerPort: 8080
    livenessProbe:
      httpGet:
        path: /healthz
        port: 8080
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8080
      initialDelaySeconds: 5
      periodSeconds: 5
    startupProbe:
      httpGet:
        path: /startup
        port: 8080
      failureThreshold: 30
      periodSeconds: 10
```

### Pod 终止过程

终止 Pod 时会发生以下过程：

1. **向 API Server 发出删除请求**：用户或控制器请求删除 Pod
2. **终止期开始**：设置默认终止期（30 秒）
3. **API 更新**：API server 更新 Pod 的删除时间戳
4. **Endpoint 更新**：EndpointSlice 将端点标记为正在终止且未就绪；传播与节点关闭并发进行
5. **停止信号**：kubelet 在宽限期内运行任意 preStop hook，然后请求运行时发送停止信号（通常是 SIGTERM，除非镜像/容器覆盖它）
6. **等待优雅关闭**：为应用程序提供优雅关闭的时间
7. **SIGKILL 信号**：如果容器在终止期后仍未终止，将发送 SIGKILL 信号
8. **资源清理**：kubelet 清理 Pod 资源

### Init 容器

Init 容器是应用程序容器在 Pod 中启动前运行的特殊容器：

1. **顺序执行**：Init 容器按定义顺序逐个运行
2. **前置条件**：每个 init 容器仅在前一个容器成功完成后启动
3. **失败时重启**：若 init 容器失败，将根据 Pod 的重启策略重启
4. **用途**：应用程序容器启动前的设置、依赖验证、权限设置等

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: init-pod
spec:
  initContainers:
  - name: init-myservice
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup myservice; do echo waiting for myservice; sleep 2; done;']
  - name: init-mydb
    image: busybox:1.34
    command: ['sh', '-c', 'until nslookup mydb; do echo waiting for mydb; sleep 2; done;']
  containers:
  - name: app
    image: myapp:1.0
```

### Pod 中断

Pod 中断可分为自愿中断和非自愿中断：

1. **自愿中断**：由集群管理员或自动化工具导致的中断
   - 节点排空
   - Deployment 更新
   - Pod 删除

2. **非自愿中断**：因硬件故障、内核 panic、网络分区等造成的中断。

PodDisruptionBudget 通过 Eviction API（例如 drain）限制自愿驱逐。直接删除 Pod 和 Deployment 滚动更新会绕过它；请另行配置 rollout 可用性。它无法防止非自愿故障。

## Pod 设计模式

设计 Pod 时需要考虑多种模式和最佳实践。理解并应用这些模式可提高应用程序的稳定性、可扩展性和可维护性。

### 单一职责原则

Pod 应遵循单一职责原则：

1. **一个主要功能**：每个 Pod 应负责一个主要功能或进程
2. **独立扩缩容**：设计应使每项功能均可独立扩缩容
3. **独立生命周期**：设计应使每项功能均可拥有自己的生命周期

### Pod 模板

Pod 模板是用于在工作负载资源（Deployment、StatefulSet 等）中创建 Pod 的规范：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:  # Pod template starts
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.30.4
        ports:
        - containerPort: 80
  # Pod template ends
```

### Pod 亲和性和反亲和性

Pod 亲和性和反亲和性是控制 Pod 调度到哪些节点的规则：

1. **Pod 亲和性**：与特定 Pod 调度到同一节点或拓扑域
2. **Pod 反亲和性**：与特定 Pod 调度到不同节点或拓扑域

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-pod
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: "kubernetes.io/hostname"
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - web
          topologyKey: "kubernetes.io/hostname"
  containers:
  - name: web
    image: nginx:1.30.4
```

### 节点亲和性

节点亲和性是将 Pod 限制为调度到特定节点的规则：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: gpu
            operator: In
            values:
            - "true"
  containers:
  - name: gpu-container
    image: gpu-app:1.0
```

### Taint 和 Toleration

Taint 应用于节点以阻止某些 Pod 被调度，而 Toleration 应用于 Pod 以允许调度到带有 Taint 的节点：

```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule
```

```yaml
# Apply toleration to Pod
apiVersion: v1
kind: Pod
metadata:
  name: tolerant-pod
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: app
    image: myapp:1.0
```

### 资源请求和限制

为 Pod 中的容器设置资源请求和限制，对于高效使用集群资源和确保稳定性很重要：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
  - name: app
    image: myapp:1.0
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

### Pod 安全上下文

安全上下文在 Pod 或容器级别定义安全设置：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: security-pod
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

### Pod 优先级和抢占

Pod 优先级和抢占决定在集群资源不足时哪些 Pod 被调度、哪些 Pod 被抢占：

```yaml
# Priority class definition
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical pods only."
---
# Pod using priority class
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: app
    image: myapp:1.0
```

## 工作负载资源概述

Kubernetes 提供多种工作负载资源来管理 Pod。每种工作负载资源均针对特定使用场景和需求而设计。

### 工作负载资源类型

Kubernetes 中的主要工作负载资源有：

1. **ReplicaSet**：维护指定数量的 Pod 副本
2. **Deployment**：管理 ReplicaSet 以提供声明式更新
3. **StatefulSet**：用于需要状态持久化的应用程序的资源
4. **DaemonSet**：在所有节点上运行一份 Pod 副本
5. **Job**：完成后终止的一次性任务
6. **CronJob**：按计划定期运行 Job

### 工作负载资源选择标准

选择合适工作负载资源的标准：

1. **状态持久化**：应用程序是否需要保持状态
2. **执行模式**：持续运行、一次性运行还是定期运行
3. **部署需求**：滚动更新、蓝绿部署等要求
4. **节点覆盖范围**：是否需要在所有节点上运行
5. **可扩展性需求**：是否需要水平扩缩容

## ReplicaSet

ReplicaSet 确保始终运行指定数量的 Pod 副本。如果 Pod 失败或被删除，ReplicaSet 会自动创建替换 Pod。

### ReplicaSet 的主要功能

1. **维护 Pod 副本**：维护指定数量的 Pod 副本
2. **Pod 选择**：通过标签选择器识别要管理的 Pod
3. **Pod 创建**：必要时创建新的 Pod
4. **Pod 删除**：删除多余的 Pod

### ReplicaSet 定义

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata:
  name: frontend
  labels:
    app: guestbook
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      tier: frontend
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      containers:
      - name: php-redis
        image: gcr.io/google_samples/gb-frontend:v3
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
        ports:
        - containerPort: 80
```

### ReplicaSet 操作

1. **标签选择器匹配**：ReplicaSet 识别匹配标签选择器的 Pod
2. **检查当前状态**：验证当前运行的 Pod 数量
3. **与期望状态比较**：将当前 Pod 数量与期望副本数比较
4. **调整操作**：根据需要创建或删除 Pod

### ReplicaSet 与 Replication Controller

ReplicaSet 是 Replication Controller 的后继者，并提供更强大的标签选择器：

1. **Replication Controller**：仅支持基于相等性的选择器（例如 app=nginx）
2. **ReplicaSet**：支持基于集合的选择器（例如 app in (nginx, apache)）

### ReplicaSet 使用场景

ReplicaSet 通常通过 Deployment 间接使用，而非直接使用。但在以下情况可直接使用：

1. **简单复制**：仅需维护 Pod 副本时
2. **自定义更新**：需要自定义更新机制时
3. **遗留支持**：支持遗留应用程序

## Deployment

Deployment 管理 ReplicaSet，以便为 Pod 提供声明式更新。Deployment 为应用程序管理滚动更新、回滚、扩缩容等。

### Deployment 的主要功能

1. **声明式更新**：声明期望状态，Deployment 将当前状态变更为期望状态
2. **滚动更新**：无需停机即可更新应用程序
3. **回滚**：可轻松回滚到先前版本
4. **扩缩容**：调整应用程序副本数量
5. **部署历史**：保留先前部署版本的记录

### Deployment 定义

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
            memory: 100Mi
          limits:
            cpu: 200m
            memory: 200Mi
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

### Deployment 更新策略

Deployment 提供两种更新策略：

1. **RollingUpdate**：逐步更新 Pod，以实现无停机部署（默认）
   - **maxSurge**：可在期望 Pod 数量之上创建的最大 Pod 数量
   - **maxUnavailable**：更新期间不可用 Pod 的最大数量

2. **Recreate**：在创建新 Pod 前删除所有现有 Pod（会造成暂时停机）

### Deployment 回滚

Deployment 支持回滚到先前版本：

```bash
# Check deployment history
kubectl -n workloads-demo rollout history deployment/nginx-deployment

# Check details of specific version
kubectl -n workloads-demo rollout history deployment/nginx-deployment --revision=2

# Rollback to previous version
kubectl -n workloads-demo rollout undo deployment/nginx-deployment

# Rollback to specific version
kubectl -n workloads-demo rollout undo deployment/nginx-deployment --to-revision=2
```

### Deployment 扩缩容

Deployment 可以轻松扩缩容：

```bash
# Imperative scaling
kubectl -n workloads-demo scale deployment/nginx-deployment --replicas=5

# Declarative scaling (after modifying YAML file)
kubectl apply -f deployment.yaml
```

### 暂停和恢复 Deployment

可以暂停和恢复 Deployment rollout：

```bash
# Pause rollout
kubectl -n workloads-demo rollout pause deployment/nginx-deployment

# Apply multiple changes
kubectl -n workloads-demo set image deployment/nginx-deployment nginx=nginx:1.30.4-alpine
kubectl -n workloads-demo set resources deployment/nginx-deployment -c=nginx --limits=cpu=200m,memory=256Mi

# Resume rollout
kubectl -n workloads-demo rollout resume deployment/nginx-deployment
```

### Deployment 状态

Deployment Conditions 包括 `Progressing`、`Available` 和 `ReplicaFailure`。停滞的 rollout 可能报告原因为 `ProgressDeadlineExceeded` 的 `Progressing=False`；Kubernetes 不会自动回滚它。“Complete”描述的是 rollout 完成情况，而非一种 Condition 类型。

## StatefulSet

StatefulSet 是用于需要状态持久化的应用程序的工作负载资源。它为每个 Pod 分配唯一标识符，并提供稳定的网络标识符和持久存储。

### StatefulSet 的主要功能

1. **稳定且唯一的网络标识符**：Pod 名称和主机名即使在重启后也会保持
2. **稳定且持久的存储**：即使 Pod 被重新调度，也可访问相同存储
3. **顺序部署和扩缩容**：Pod 按顺序创建、更新和删除
4. **顺序自动滚动更新**：Pod 按顺序更新

### StatefulSet 定义

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  selector:
    matchLabels:
      app: nginx
  serviceName: "nginx"
  replicas: 3
  updateStrategy:
    type: RollingUpdate
  podManagementPolicy: OrderedReady
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
          name: web
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: www
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: "standard"
      resources:
        requests:
          storage: 1Gi
```

### StatefulSet Pod 标识符

StatefulSet 按以下格式为 Pod 分配唯一标识符：
```
<StatefulSet name>-<ordinal index>
```

例如，`web` StatefulSet 创建 `web-0`、`web-1`、`web-2` 等 Pod。

### StatefulSet Headless Service

StatefulSet 通常与 headless Service（clusterIP: None）配合使用。这会为每个 Pod 创建 DNS 记录：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx
  labels:
    app: nginx
spec:
  ports:
  - port: 80
    name: web
  clusterIP: None
  selector:
    app: nginx
```

这样，每个 Pod 都有以下格式的 DNS 名称：
```
<Pod name>.<service name>.<namespace>.svc.cluster.local
```

示例：`web-0.nginx.default.svc.cluster.local`

### StatefulSet 存储

StatefulSet 使用 `volumeClaimTemplates` 自动为每个 Pod 创建 Persistent Volume Claim（PVC）。即使 Pod 被重新调度，这些 PVC 仍会保留。

### StatefulSet 更新策略

StatefulSet 提供两种更新策略：

1. **RollingUpdate**：按顺序更新 Pod（默认）
2. **OnDelete**：仅在删除 Pod 时更新

### Pod 管理策略

StatefulSet 提供两种 Pod 管理策略：

1. **OrderedReady**：按顺序创建和终止 Pod（默认）
2. **Parallel**：并行创建和终止 Pod

### StatefulSet 使用场景

StatefulSet 适用于以下应用程序：

1. **数据库**：MySQL、PostgreSQL、MongoDB 等
2. **分布式系统**：Kafka、ZooKeeper、Elasticsearch 等
3. **消息队列**：RabbitMQ 等
4. **其他有状态应用程序**：文件服务器、会话存储等

### StatefulSet 示例：持久化 MySQL 实例

此示例展示一个 MySQL 实例的稳定身份和 PVC。它**不会**配置复制或自动数据库故障转移。增加 `replicas` 会创建相互独立的数据库。在相同 namespace 中创建具有 `password` 键的 `mysql-secret`，并提供默认 StorageClass（或显式设置合适的 class）。请使用经过测试的 MySQL 8.4 patch/digest；凭据变更需要数据库级别的轮换，而不只是更新 Secret。

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
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  podManagementPolicy: OrderedReady
  template:
    metadata:
      labels:
        app: mysql
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
        - name: mysql
          containerPort: 3306
        startupProbe:
          tcpSocket:
            port: mysql
          periodSeconds: 10
          failureThreshold: 60
        readinessProbe:
          exec:
            command:
            - sh
            - -c
            - 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -h 127.0.0.1 -u root -e "SELECT 1"'
          periodSeconds: 10
          timeoutSeconds: 5
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            memory: 2Gi
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 10Gi
```

对于复制和 leader 提升，请使用数据库 operator 或单独经过测试的复制 runbook。单独的 StatefulSet 不提供其中任一功能。[上游复制教程](https://kubernetes.io/docs/tasks/run-application/run-replicated-stateful-application/)明确使用了不安全的教学默认值，并非生产配置。

## DaemonSet

DaemonSet 确保一份 Pod 副本在所有节点（或特定节点）上运行。节点添加到集群时会自动添加 Pod，节点移除时也会移除 Pod。

### DaemonSet 的主要功能

1. **在所有节点运行**：在集群中的所有节点上运行 Pod
2. **节点选择**：可通过节点选择器仅在特定节点上运行
3. **自动部署**：添加新节点时自动部署 Pod
4. **自动清理**：移除节点时自动清理 Pod

### DaemonSet 定义

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd-elasticsearch
  namespace: kube-system
  labels:
    k8s-app: fluentd-logging
spec:
  selector:
    matchLabels:
      name: fluentd-elasticsearch
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        name: fluentd-elasticsearch
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
      containers:
      - name: fluentd-elasticsearch
        image: quay.io/fluentd_elasticsearch/fluentd:v2.5.2
        resources:
          limits:
            memory: 200Mi
          requests:
            cpu: 100m
            memory: 200Mi
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
      terminationGracePeriodSeconds: 30
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
```

对于 CRI runtime，请配置收集器解析 `/var/log/pods` 下的 CRI 日志（通常从 `/var/log/containers` 链接），而不是 Docker JSON 日志。收集器需要自己的源/输出配置和 RBAC。

### DaemonSet 更新策略

DaemonSet 提供两种更新策略：

1. **RollingUpdate**：顺序更新 Pod（默认）
   - **maxUnavailable**：更新期间不可用 Pod 的最大数量

2. **OnDelete**：仅在删除 Pod 时更新

### DaemonSet 节点选择

可以配置 DaemonSet 仅在特定节点上运行：

```yaml
spec:
  template:
    spec:
      nodeSelector:
        disk: ssd
```

### DaemonSet Taint Toleration

DaemonSet 可以设置 Toleration，以在带有 Taint 的节点上运行：

```yaml
spec:
  template:
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
```

### DaemonSet 使用场景

DaemonSet 用于以下目的：

1. **日志收集器**：Fluentd、Logstash 等
2. **监控 Agent**：Prometheus Node Exporter、Datadog Agent 等
3. **网络插件**：Calico、Cilium 等
4. **存储 Daemon**：Ceph、GlusterFS 等
5. **安全 Agent**：Falco、Sysdig 等

### DaemonSet 示例：Prometheus Node Exporter

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      hostPID: true
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.3.1
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        - --web.listen-address=:9100
        ports:
        - containerPort: 9100
          protocol: TCP
          name: http
        resources:
          limits:
            cpu: 250m
            memory: 180Mi
          requests:
            cpu: 102m
            memory: 180Mi
        volumeMounts:
        - name: proc
          mountPath: /host/proc
          readOnly: true
        - name: sys
          mountPath: /host/sys
          readOnly: true
        - name: root
          mountPath: /host/root
          readOnly: true
      tolerations:
      - operator: "Exists"
      volumes:
      - name: proc
        hostPath:
          path: /proc
      - name: sys
        hostPath:
          path: /sys
      - name: root
        hostPath:
          path: /
```

## Job 和 CronJob

Job 和 CronJob 是用于运行一次性或定期任务的工作负载资源。

### Job

Job 创建一个或多个 Pod，并持续执行，直到指定数量的 Pod 成功终止。

#### Job 的主要功能

1. **完成情况跟踪**：跟踪成功的 Pod；重试限制或截止期限可使 Job 失败
2. **并行执行**：可并行运行多个 Pod
3. **重试**：自动重试失败的 Pod
4. **完成后清理**：可选地在 Job 完成后清理 Pod

#### Job 定义

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 5      # Number of Pods that must successfully complete
  parallelism: 2      # Number of Pods to run in parallel
  backoffLimit: 4     # Number of retries on failure
  activeDeadlineSeconds: 100  # Job time limit (seconds)
  ttlSecondsAfterFinished: 100  # Deletion time after completion (seconds)
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.34
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
        resources:
          requests:
            cpu: 100m
            memory: 50Mi
          limits:
            cpu: 100m
            memory: 100Mi
      restartPolicy: Never  # or OnFailure
```

#### Job 完成模式

Job 提供两种完成模式：

1. **NonIndexed**：标准 Job 模式，指定数量的 Pod 成功完成时 Job 完成
2. **Indexed**：每个 Pod 被分配从 0 开始的索引，并为特定索引范围执行任务

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-job
spec:
  completions: 5
  parallelism: 3
  completionMode: Indexed  # Enable Indexed mode
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.34
        command: ["sh", "-c", "echo Processing item ${JOB_COMPLETION_INDEX}"]
      restartPolicy: Never
```

#### Job 使用场景

Job 用于以下目的：

1. **批处理**：数据处理、ETL 任务
2. **计算任务**：科学计算、渲染
3. **数据库迁移**：Schema 更新
4. **一次性管理任务**：备份、清理任务

### CronJob

CronJob 根据指定计划定期运行 Job。它们的工作方式与 Linux cron job 类似。

#### CronJob 的主要功能

1. **计划执行**：使用 cron 表达式指定执行计划
2. **Job 管理**：按计划创建 Job
3. **并发策略**：定义先前 Job 仍在运行时的行为
4. **历史限制**：限制已完成 Job 的历史记录

#### CronJob 定义

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello
spec:
  schedule: "*/1 * * * *"  # Run every minute
  timeZone: "America/New_York"  # Timezone (stable since Kubernetes 1.27)
  concurrencyPolicy: Forbid  # Allow, Forbid, Replace
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  startingDeadlineSeconds: 60
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.34
            command:
            - /bin/sh
            - -c
            - date; echo Hello from the Kubernetes cluster
          restartPolicy: OnFailure
```

#### Cron 表达式

Cron 表达式采用以下格式：
```
+------------------- minute (0 - 59)
| +----------------- hour (0 - 23)
| | +--------------- day of month (1 - 31)
| | | +------------- month (1 - 12)
| | | | +----------- day of week (0 - 6) (Sunday to Saturday; use 0 for Sunday)
| | | | |
| | | | |
* * * * *
```

常见 cron 表达式示例：
- `*/5 * * * *`：每 5 分钟
- `0 * * * *`：每小时整点
- `0 0 * * *`：每天午夜
- `0 0 * * 0`：每周日午夜
- `0 0 1 * *`：每月 1 日午夜
- `0 0 1 1 *`：每年 1 月 1 日午夜

#### 并发策略

CronJob 提供三种并发策略：

1. **Allow**：多个 Job 可同时运行（默认）
2. **Forbid**：若先前 Job 仍在运行，跳过新 Job
3. **Replace**：若先前 Job 仍在运行，用新 Job 替换它

#### CronJob 使用场景

CronJob 用于以下目的：

1. **定期备份**：数据库备份、创建快照
2. **数据同步**：定期数据同步
3. **报告生成**：每日/每周/每月报告生成
4. **清理任务**：临时文件清理、日志轮转
5. **通知和监控**：状态检查、发送告警

#### CronJob 示例：数据库备份

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  schedule: "0 2 * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:14
            env:
            - name: PGHOST
              value: postgres-service
            - name: PGUSER
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: username
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            command:
            - /bin/sh
            - -c
            - |
              set -eu
              backup_file="/backup/db-$(date +%Y%m%d-%H%M%S).dump"
              trap 'rm -f "$backup_file.partial"' EXIT
              pg_dump -Fc > "$backup_file.partial"
              pg_restore --list "$backup_file.partial" > /dev/null
              mv "$backup_file.partial" "$backup_file"
              find /backup -maxdepth 1 -type f -name 'db-*.dump' -mtime +7 -delete
            volumeMounts:
            - name: backup-volume
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-volume
            persistentVolumeClaim:
              claimName: backup-pvc
```

CronJob 调度是近似的：Job 必须能够容忍重复执行。`Forbid` 仅适用于来自同一 CronJob 的 Job。历史限制删除的是 Job/Pod 对象，而不是备份文件。备份示例在 02:00 UTC 运行，且需要 `backup-pvc`、`postgres-secret` 和可访问的数据库；`pg_dump` 必须至少与 server 主版本一样新。当 `PGDATABASE` 与 `PGUSER` 不同时，请指定 `PGDATABASE`。请单独测试实际恢复。

## 总结

本文介绍了 Kubernetes 的基本构建块 Pod 和各种工作负载资源。我们从 Pod 概念开始，探讨了 Deployment、StatefulSet、DaemonSet、Job 和 CronJob 等多种工作负载资源的特性和使用场景。这些资源各有独特用途和功能，恰当使用它们可实现高效的应用程序部署和管理。

## 测验

要测试您在本章所学内容，请尝试 [Pod 和工作负载测验](../quizzes/core/02-pods-and-workloads-quiz.md)。
