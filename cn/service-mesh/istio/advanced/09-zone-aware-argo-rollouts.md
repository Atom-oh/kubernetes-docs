# 区域感知的 Argo Rollouts

> **验证基线**：Istio 1.31.0、Argo Rollouts 1.10.1、Kubernetes 1.32–1.37
> **最后审核**：2026年10月16日
> **难度**：高级

本指南将独立的分区 canary 与跨 AZ 故障转移区分开来。主要示例是一个**分区路由/隔离蓝图**：客户端群组选择某个区域的 stable/canary Services。当这些端点消失时，它不会自动故障转移到其他区域。

## 目录

1. [问题定义](#problem-definition)
2. [架构概述](#architecture-overview)
3. [关键设计决策](#key-design-decisions)
4. [实施指南](#implementation-guide)
5. [流量路径](#traffic-flow)
6. [故障排查](#troubleshooting)
7. [最佳实践](#best-practices)

## 问题定义 {#problem-definition}

### Spot 中断与 PDB

Spot 容量可能会被回收，因此必须为相关的容量损失做好规划。中断通知尽力而为；停止/终止通知通常会提前两分钟发出，而休眠会立即开始。EKS 托管节点组会尝试进行替换/重新均衡，但无法保证在驱逐发生中断的节点之前，替换节点已达到 Ready 状态。

PodDisruptionBudget 会限制自愿的 Eviction API 操作。它不会阻止 EC2 中断、节点故障、直接删除 Pod 或所有由控制器驱动的更新。Rollouts 不会创建/管理下方的 PDB；应用团队负责定义它们，Kubernetes 负责计算其状态。

对于九个健康且匹配的 Pod，若设置**整数值 `minAvailable: 6`**，示例中的自愿中断允许数量为三个。如果只剩六个健康 Pod，该允许数量就是零。这并不是“至少需要六个 Pod 的 33%”：如果预期有九个 Pod，`minAvailable: "33%"` 会向上取整为三个。百分比形式的 `maxUnavailable` 语义不同，并且对控制器规模有要求。

将全局预算拆分为每个区域 `minAvailable: 1` 会改变保护方式。一个区域失效后，剩余两个预算可能允许自愿驱逐，直到每个区域只剩一个健康 Pod，而不是在全局范围内保留六个。这对于独立操作可能有用，但代表不同的可用性/容量策略。选择 stable 和 canary Pod 的预算也不能保证每个按权重分配的目标各自都有容量。

### 目标与限制

| 设计 | 独立的分区版本 | 跨 AZ 故障转移 | 主要限制 |
|---|---|---|---|
| 跨 AZ 共享一个 revision/subset，且端点分布在多个 AZ | 无法独立控制每个区域的 revision | 在选定的端点池内可能实现 | 其他 AZ 中必须有健康容量，且发布/数据状态兼容 |
| 此处展示的按区域划分 Rollouts 和区域过滤 Services | 是 | locality 设置不提供此能力 | 选定区域的端点池为空时，仍为空 |
| 在区域网关/流水线之前设置独立的、基于健康状态的入口路由 | 可以设计实现 | 需要自己的策略/控制器和测试 | 需要额外协调路由、容量、身份验证和恢复 |

不要仅靠添加 DestinationRule 就声称同时具备三项特性（严格的区域过滤、每个区域独立的哈希值和透明故障转移）。独立的入口路由设计不属于此部署蓝图，也未在此处经过生产环境测试。

## 架构概述 {#architecture-overview}

一个通用的 `test` Service 提供 DNS 名称。对于注入了 sidecar 的客户端，VirtualService 会根据**明确设置的客户端 Pod 标签**选择区域路由。每条路由都指向该区域的 stable/canary Services。独立的 Rollout 控制这对 Services 的哈希值以及其专属命名路由的权重。

Istiod 会将配置编译为 Envoy 配置。VirtualService/DestinationRule 对象不是网络跳点。未加入网格的客户端可以使用通用 Service 的普通 Kubernetes 端点选择机制，从而绕过这些路由规则；路由标签不是安全边界。

每个区域的 Pod 只会调度到其配置的 AZ。因此，区域 A 的 Services 不包含区域 B/C 的备用端点。独立的部署状态也无法消除共享控制平面、API server、网络或数据库依赖。

## 关键设计决策 {#key-design-decisions}

### 1. 路由所有权

Rollouts 1.10 会协调已配置的路由权重和受支持的托管目标；它不会盲目替换所有目标数组。使用不同的路由名称可以避免期望权重相互冲突。不过，三个控制器更新同一个 VirtualService 时，仍可能遇到 Kubernetes `resourceVersion` 冲突和协调延迟。如果需要更强的控制平面隔离，可以选择独立对象/入口路由。

此蓝图使用不同的路由（`zone-a-route`、`zone-b-route`、`zone-c-route`）和**主机级拆分**。它不会混用 Service-hash 和 DestinationRule-subset 所有权。[集成指南](08-argo-rollouts.md)会介绍这两种替代方案。

### 2. 客户端标签与实际 AZ

Istiod 构建网格配置时，`sourceLabels` 用于选择源工作负载；它不是运行时的请求头匹配条件。节点标签（例如 `topology.kubernetes.io/zone`）不会自动复制到 Pod。自定义的 `routing.example.com/zone: a` Pod 标签必须与经过验证、确实位于目标 AZ 的 Pod 部署位置相配套。

这些选择器适用于网格客户端，不适用于到达 ingress gateway 的普通外部请求。保留 `mesh` 网关作用范围。在此示例中，未知客户端群组会收到明确的 503 响应，而不会被静默地路由到其他区域。

### 3. Locality 无法跳出选定的端点池

通过 `zone: a` 和 Rollout A 哈希值选中的 subset 无法故障转移到相邻区域 B 的 subset。按区域过滤的 Service 也一样。Outlier detection 只会改变所选上游端点池内端点的可用性；它不会跳转到其他 VirtualService 路由。

此外，`localityLbSetting.distribute`、`failover` 和 `failoverPriority` 是互斥的选项，不应随意组合字段。`failover.from/to` 的值是**区域（region）**，不是 `region/zone` 字符串。仅靠这些条目无法建立 A→B→C→A 的 AZ 循环。

## 实施指南 {#implementation-guide}

### 先决条件

请采用 [Argo Rollouts 集成](08-argo-rollouts.md)中介绍的控制器、CLI、注入、Prometheus 和工作负载先决条件。这是一个使用默认/旧版注入方式的隔离 sidecar HTTP 演示；如果使用带 revision 的网格，请改用已安装的 revision/tag。此实验需要兼容的 EC2 Linux 工作节点、配额、网络、镜像访问和可观测性配置。Fargate 不在此蓝图范围内；请选择目前受支持且处于 Istio 兼容范围内的 EKS 版本。

示例中的 AZ 名称 `us-east-1a/b/c` 必须替换为实际的节点标签。不同账户中的 AZ 名称映射可能不同；在跨账户协调物理区域时，请核实 AZ ID。固定的演示镜像仅适用于 Linux amd64，因此每个选定 AZ 都需要兼容节点，或经过单独验证的替代镜像。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone,kubernetes.io/arch
```

### 1. Namespace 与通用/区域 Services

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: zone-rollouts-demo
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Service
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-a
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: a
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-b
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: b
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-stable-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
---
apiVersion: v1
kind: Service
metadata:
  name: test-canary-c
  namespace: zone-rollouts-demo
spec:
  selector:
    app: test
    zone: c
  ports:
  - name: http
    port: 8080
    targetPort: http
```

通用 Service 为网格内调用方提供 DNS 入口，不是授权机制。六个区域 Services 都使用实际的 Pod `zone` 选择器；Rollouts 会为每个 stable/canary Service 添加哈希值。

### 2. 客户端模板约定

将以下片段合并到**现有的、名为 `zone-client-a` 的 Deployment** 中，并保留其选择器、容器、已验证的镜像、资源配置和其他放置约束。必须将 `a` 路由标签添加到实际的 Pod 模板中，而不仅是 Deployment 元数据：

```yaml
metadata:
  name: zone-client-a
  namespace: zone-rollouts-demo
spec:
  template:
    metadata:
      labels:
        routing.example.com/zone: a
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
```

测试 B/C 客户端时，准备带有相应标签并受实际 AZ 约束的等效客户端。将亲和性与现有规则组合时，要保留预期的 AND/OR 限制；不要意外扩大节点的可选范围。请根据所选 Node 的区域核实 `.spec.nodeName`。此片段不会部署客户端，也不会自动复制节点元数据。

### 3. 使用独立路由的共享 VirtualService

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: test
  namespace: zone-rollouts-demo
spec:
  hosts:
  - test
  - test.zone-rollouts-demo.svc.cluster.local
  gateways:
  - mesh
  http:
  - name: zone-a-route
    match:
    - sourceLabels:
        routing.example.com/zone: a
    route:
    - destination:
        host: test-stable-a
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-a
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-b-route
    match:
    - sourceLabels:
        routing.example.com/zone: b
    route:
    - destination:
        host: test-stable-b
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-b
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: zone-c-route
    match:
    - sourceLabels:
        routing.example.com/zone: c
    route:
    - destination:
        host: test-stable-c
        port:
          number: 8080
      weight: 100
    - destination:
        host: test-canary-c
        port:
          number: 8080
      weight: 0
    retries:
      attempts: 0
  - name: unclassified-client
    directResponse:
      status: 503
      body:
        string: No reviewed client-zone route
```

发送测试流量之前，请确认每个控制器都已选中预期的哈希值和健康端点。初始权重为 100/0，而不是没有说明的、正在生效的 90/10 拆分。每条命名路由都明确禁用了网格重试；应用程序重试行为是另一回事。

### 4. 按区域划分的 Rollouts

工作负载、副本数、requests/limits 和暂停时间都是演示输入。三个副本不会自动分布到三个节点。对于真实部署，请检查节点级拓扑分布/反亲和性、容量、PDB 和 stable/canary 余量。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-a
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: a
  template:
    metadata:
      labels:
        app: test
        zone: a
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1a
  strategy:
    canary:
      stableService: test-stable-a
      canaryService: test-canary-a
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-a-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-a
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-b
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: b
  template:
    metadata:
      labels:
        app: test
        zone: b
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1b
  strategy:
    canary:
      stableService: test-stable-b
      canaryService: test-canary-b
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-b-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-b
          - name: namespace
            value: zone-rollouts-demo
---
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: test-c
  namespace: zone-rollouts-demo
spec:
  replicas: 3
  revisionHistoryLimit: 2
  selector:
    matchLabels:
      app: test
      zone: c
  template:
    metadata:
      labels:
        app: test
        zone: c
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: amd64
      terminationGracePeriodSeconds: 45
      containers:
      - name: app
        image: argoproj/rollouts-demo@sha256:3225193a6415b14b3fcdd160c40248b2bfd62f8c77326480559b91a41ced6e20
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: http
          initialDelaySeconds: 3
          periodSeconds: 5
          timeoutSeconds: 1
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: topology.kubernetes.io/zone
                operator: In
                values:
                - us-east-1c
  strategy:
    canary:
      stableService: test-stable-c
      canaryService: test-canary-c
      maxSurge: 1
      maxUnavailable: 0
      trafficRouting:
        istio:
          virtualService:
            name: test
            routes:
            - zone-c-route
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - pause: {}
      - setWeight: 25
      - pause:
          duration: 5m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 50
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
      - setWeight: 75
      - pause:
          duration: 10m
      - analysis:
          templates:
          - templateName: zone-canary-check
          args:
          - name: service-name
            value: test-canary-c
          - name: namespace
            value: zone-rollouts-demo
```

每个 Rollout 都有自己的选择器、镜像/revision 状态、Services 和分析参数。经过第一个 5% 阶段后，无期限暂停需要有意执行 promote。严格的区域亲和性会在该 AZ 没有容量时使受影响的 Pod 保持 Pending；它不会将 Pod 迁移到健康的 AZ。

### 5. 明确配置 PDB

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-a-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: a
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-b-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: b
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: test-c-pdb
  namespace: zone-rollouts-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: test
      zone: c
```

这些配置会保留原示例中每个区域至少一个 Pod 的要求。它们不等同于前文的全局最少六个 Pod，也无法独立保护每个按流量权重分配的 revision。自愿维护之前，请检查 `currentHealthy`、`desiredHealthy` 和 `disruptionsAllowed`。

### 6. 按区域进行分析

请在 Rollouts 之前创建此模板。它使用实际的区域 canary Service 名称和标准 source-reporter 指标，而不是臆造的 Pod 区域标签：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-check
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

分子明确表示 **HTTP 2xx**，与本指南的成功定义一致。全部为 5xx 的时间窗口会产生 0，而不是空分子；没有流量或缺少数据都无法通过有限值/流量门槛。源代理必须能够访问配置的 Prometheus，且其实际标签必须与这些选择器匹配。

通过 `http://test.zone-rollouts-demo.svc.cluster.local:8080/color` 持续发送有代表性的网格流量。调用方标签决定其所属区域，控制器则决定该区域 stable/canary 的权重。五分钟预热时间长于两分钟的指标回看窗口；二十个请求的估算值和测量次数只是示例，并不代表统计置信度。

## 流量路径 {#traffic-flow}

### 正常的区域流量路径

标签正确且位于经过审核的 AZ 中的 A 客户端会使用 `zone-a-route`，该路由指向 A 的 stable/canary Services。观测到的比例取决于样本量、会话和就绪状态，并不保证每十个请求中有精确数量的请求。

### 区域失效

如果所有符合条件的 A 端点都消失，A 路由就没有健康的上游。降低 outlier 阈值或更改 PDB，都无法在 A 的 Service 中凭空生成 B 端点。在容量恢复或明确设计的更高层路由策略生效之前，此示例会持续返回失败。

若要实现跨 AZ 连续性，请选择在同一个已选发布池中拥有健康远程端点的架构，或实施并测试独立的入口层故障转移策略。还需考虑远程容量、数据一致性、身份验证、正在处理的请求和故障恢复。上面的区域代码不声称支持透明/循环故障转移。

### 独立的共享端点 Locality 替代方案

以下配置属于**另一种设置**：现有的 `shared-app` Service 或已选 subset，其符合条件的端点横跨多个 AZ，且发布状态兼容。它不会为上面的区域 Services 启用故障转移。如果已有 DestinationRule 管理该共享主机/subsets，请将此 trafficPolicy 合并到现有规则中，而不要创建相互冲突的规则：

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: shared-endpoint-locality
  namespace: zone-rollouts-demo
spec:
  host: shared-app.zone-rollouts-demo.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 3
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
```

Locality 优先级会优先选择区域/可用区匹配的端点，并可将后续流量转移到符合条件的健康端点。它们不会指定固定的循环 AZ 顺序。`consecutive5xxErrors` 是当前字段；连续错误检测由流量驱动，而 `interval` 用于定期检测任务。驱逐所有端点可能导致错误，并且已失败的请求不会自动重放。请参阅[区域感知路由](../resilience/03-zone-aware-routing.md)。

## 故障排查 {#troubleshooting}

```bash
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo
kubectl get virtualservice test -n zone-rollouts-demo -o yaml
kubectl get services test-stable-a test-canary-a -n zone-rollouts-demo -o yaml
kubectl get pods -n zone-rollouts-demo -l app=test -o wide --show-labels
kubectl get endpointslices -n zone-rollouts-demo -l kubernetes.io/service-name=test-canary-a
kubectl get pdb -n zone-rollouts-demo -o wide

istioctl proxy-config routes <client-a-pod> -n zone-rollouts-demo
istioctl proxy-config endpoints <client-a-pod> -n zone-rollouts-demo --cluster 'outbound|8080||test-canary-a.zone-rollouts-demo.svc.cluster.local'
kubectl get analysisruns -n zone-rollouts-demo
kubectl logs -n argo-rollouts deployment/argo-rollouts
```

- **更新冲突**：区分同一路由的所有权冲突和共享 VirtualService 上暂时的对象版本冲突。仅使用不同的 subset 名称无法解决其中任何一种问题。
- **选错区域**：比较实际调用方 Pod 标签、Node 位置和编译后的路由。不要假设节点区域标签已复制到 Pod。
- **没有备用路由**：首先检查所选 Service/subset 中符合条件的端点。如果 A 以外没有端点，更快的 outlier detection 也无法提供跨 AZ 故障转移。
- **没有 canary 流量**：确认请求经过网格、有就绪的 EndpointSlices、哈希选择器和实际权重，并且样本数量足够。
- **分析卡住/失败**：检查原始结果和 provider 错误，而不只是 Rollout 的汇总阶段。缺少自定义区域标签不会自动生成遥测数据。

## 最佳实践 {#best-practices}

### 1. 明确协调版本变更

Promote 会恢复现有的暂停；它不会部署新镜像，也不能证明其他 AZ 健康。通过 Git（或在隔离实验环境中直接操作）更新某个区域期望使用的镜像，观察其分析和工作负载状态，然后再决定是否推进其他区域。仅等待固定的五分钟并不足以作为证据。

```bash
# Isolated lab alternative to changing Git; affects zone A only.
kubectl argo rollouts set image test-a app=argoproj/rollouts-demo@sha256:e32df3d15f759d36c323b3dccb7003d38df1a4274d37217715151f085c24c58f -n zone-rollouts-demo
kubectl argo rollouts get rollout test-a -n zone-rollouts-demo --watch
# After the intended manual pause and review:
kubectl argo rollouts promote test-a -n zone-rollouts-demo
```

Abort 不会还原 Git 中的期望镜像。请协调 GitOps，避免它覆盖各区域托管的权重或 Service 哈希选择器；请参阅前面的集成指南。

### 2. 持续分析替代方案

如果需要持续监控，请有意识地替换内联步骤计划。后台模板中省略了 `count`，`startingStep: 2` 表示第三个步骤：

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: zone-canary-continuous
  namespace: zone-rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
  - name: http-2xx-rate
    interval: 1m
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"2.."}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
---
spec:
  strategy:
    canary:
      analysis:
        templates:
        - templateName: zone-canary-continuous
        startingStep: 2
        args:
        - name: service-name
          value: test-canary-a
        - name: namespace
          value: zone-rollouts-demo
      steps:
      - setWeight: 5
      - pause:
          duration: 5m
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause: {}
```

将此 A 片段改用于 B/C 时，请保留正确区域的路由、Services 和参数。独立分析仍可能依赖共享的 Prometheus/网络/控制平面可用性。

### 3. 监控规则

此 PrometheusRule 需要 Prometheus Operator，并且规则 namespace/标签选择器必须匹配。独立的 Istio 附加组件 Prometheus 不会自动加载此 CRD。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: zone-rollout-alerts
  namespace: zone-rollouts-demo
spec:
  groups:
  - name: zone-rollout
    rules:
    - alert: HighErrorRateZoneACanary
      expr: |-
        ((sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a",response_code=~"5..|0"}[2m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) > 0.05
        and
        (sum(increase(istio_requests_total{reporter="source",destination_service_namespace="zone-rollouts-demo",destination_service_name="test-canary-a"}[2m]))) >= 20
      for: 2m
      annotations:
        summary: Zone A canary has elevated 5xx/zero-status rate with observed traffic
    - alert: UnexpectedDemoZoneRoute
      expr: |-
        sum(rate(istio_requests_total{
          reporter="source",source_workload="zone-client-a",source_workload_namespace="zone-rollouts-demo",
          destination_service_namespace="zone-rollouts-demo",destination_service_name=~"test-(stable|canary)-(b|c)"
        }[5m])) > 0
      for: 5m
      annotations:
        summary: Demo client A is using a B/C destination Service; inspect route/placement assumptions
```

第一条规则检查 5xx/零状态码错误；4xx 也会降低 Analysis 的 2xx 比率，但不会触发这条特定错误规则。低流量/缺失流量需要单独设计预期流量/遥测健康信号；缺少流量并不能证明 canary 健康。

第二条规则是**演示路由不变量告警**，不是通用的物理跨 AZ 检测器。它假设实际源 Deployment 是 `zone-client-a`、其部署位置在 A，且 B/C Services 保留各自的区域选择器。若要测量物理区域，请使用经过验证的节点/端点 locality，或按照路由/可观测性指南所述明确增强遥测数据。

### 4. 恢复与容量

请根据实际的 EKS/节点预置模型，分散使用 Spot 容量并保留足够的容错容量。区域亲和性、中断处理和 PDB 策略都无法保证有替换容量。请检查节点组生命周期行为以及应用的终止/恢复流程。

此蓝图没有经过测量的资源或延迟结果。请根据实际工作负载的实测协调压力、端点数量、资源使用情况以及正常/故障路径延迟，为 Istiod、代理和 Rollouts 控制器确定容量。

## 参考资料与后续步骤

- [Argo Rollouts 集成](08-argo-rollouts.md)
- [区域感知路由](../resilience/03-zone-aware-routing.md)
- [Outlier Detection](../resilience/01-outlier-detection.md)
- [DestinationRule](../traffic-management/03-destination-rule.md)
- [Istio VirtualService 源选择器](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Istio locality 故障转移](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/)
- [Istio DestinationRule API](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Argo Rollouts Istio 集成](https://argoproj.github.io/argo-rollouts/features/traffic-management/istio/)
- [Kubernetes 中断](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [PDB 配置与取整规则](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [节点亲和性](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [EC2 中断通知](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- [EKS 托管节点组的 Spot 行为](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [AWS AZ ID 与账户映射](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
- [AWS 区域与可用区](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html)

请将上述维护中的集成/路由指南作为实验验证的起点。[多集群](02-multi-cluster.md)会引入额外的信任、连接性和故障域设计；它不是对此蓝图通过单一设置进行扩展。
