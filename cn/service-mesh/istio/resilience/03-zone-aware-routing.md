# 可用区感知路由

> **最后更新**：2026 年 9 月 11 日 · Istio1.31。本章使用 `localityLbSetting` 进行局部性加权/优先级故障转移。独立 `zoneAwareLbSetting` API 的前提条件和语义不同；不要混合字段。示例假定 Sidecar 网格，同主机策略彼此为独立备选。未部署或进行负载测试。

可用区感知路由通过识别 Kubernetes 可用区优化流量。它优先同可用区通信，降低延迟和跨可用区数据传输成本。

## 目录

1. [概述](#overview)
2. [工作原理](#how-it-works)
3. [基本配置](#basic-configuration)
4. [高级配置](#advanced-configuration)
5. [AWS EKS 配置](#configuration-on-aws-eks)
6. [实际示例](#practical-examples)
7. [监控](#monitoring)
8. [故障排除](#troubleshooting)

## 概述 {#overview}

可用区感知路由提供以下收益：


### 收益

1. **降低延迟**：通过同可用区通信尽量降低网络延迟
2. **节省成本**：减少跨可用区数据传输成本
   - 估算实际计费字节、方向、区域和 AWS 服务路径；不存在适用于每个 EKS 请求的通用每 GB 价格。
3. **支持可用性**：要求其他可用区有健康可达端点和备用容量。
4. **性能优化**：优化网络带宽

## 工作原理 {#how-it-works}

### 局部性负载均衡算法

80/10/10 `distribute` 策略将正常流量发送到全部三个健康可用区；10% 部分不是备用故障转移。基于优先级的局部性故障转移是独立模式。健康/容量加权可能在所有本地主机失败前就溢出流量。可用区字母不表示物理邻近或延迟。



### 局部性层级

Istio 使用以下局部性层次：

```
Region/Zone/SubZone

Example:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-west-2/us-west-2a/*
```

**默认局部性优先级**（优先级故障转移激活时）：

1. 相同区域、可用区和子区。
2. 相同区域/可用区，不同子区。
3. 相同区域，不同可用区。
4. 其他区域；配置区域故障转移策略时，按该策略排序。

### 没有 Pod 可用区标签时如何工作

**重要**：Pod 本身不需要可用区标签。Istio 读取**节点拓扑标签**，自动确定 Pod 局部性。

#### 工作原理

![Istiod 服务发现读取各 Node 的 topology.kubernetes.io/zone 标签来确定 Pod 局部性，无需 Pod 自身有可用区标签，再生成 EDS 并向 Envoy 代理推送局部性信息。](../../../.gitbook/assets/en-service-mesh-istio-resilience-03-zone-aware-routing-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-resilience-03-zone-aware-routing-2.html)

#### 分步流程

**步骤 1：Istiod 收集 Pod 信息**

```bash
# Istiod queries Pod information via Kubernetes API
kubectl get pod <pod-name> -o json | jq '.spec.nodeName'
# Output: "ip-10-0-1-10.ec2.internal"
```

**步骤 2：查询运行 Pod 的节点拓扑标签**

```bash
# Query Node info using Pod's nodeName
kubectl get node ip-10-0-1-10.ec2.internal -o json | \
  jq '.metadata.labels."topology.kubernetes.io/zone"'
# Output: "us-east-1a"
```

**步骤 3：生成 EDS（端点发现服务）**

以下是 ClusterLoadAssignment 示意，不是捕获的 CLI 输出。真实 EDS 还携带生成权重/优先级和健康状态：

```json
{
  "cluster_name": "outbound|8080||myapp.default.svc.cluster.local",
  "endpoints": [
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1a"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.1.10",
                "port_value": 8080
              }
            }
          }
        }
      ]
    },
    {
      "locality": {
        "region": "us-east-1",
        "zone": "us-east-1b"
      },
      "lb_endpoints": [
        {
          "endpoint": {
            "address": {
              "socket_address": {
                "address": "10.0.2.20",
                "port_value": 8080
              }
            }
          }
        }
      ]
    }
  ]
}
```

**步骤 4：Envoy 执行基于局部性的路由**

Envoy 比较自身局部性和接收的 EDS 信息进行路由：

```bash
# Check Envoy's Locality (based on node it's running on)
istioctl proxy-config bootstrap <pod-name> -n default -o json | \
  jq '.bootstrap.node.locality'

# Output:
# {
#   "region": "us-east-1",
#   "zone": "us-east-1a"
# }
```

#### 验证方法

```bash
# 1. Check which Node the Pod is running on
kubectl get pod <pod-name> -o wide
# NAME        READY   STATUS    NODE
# myapp-abc   2/2     Running   ip-10-0-1-10.ec2.internal

# 2. Check the Node's Zone label
kubectl get node ip-10-0-1-10.ec2.internal \
  -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}'
# Output: us-east-1a

# 3. Check Endpoint Locality recognized by Envoy
istioctl proxy-config all <pod-name> -n default -o json | \
  jq '.configs[] | select(.["@type"] | endswith("EndpointsConfigDump")) |
      ((.dynamic_endpoint_configs // .dynamicEndpointConfigs // [])[] |
       (.endpoint_config // .endpointConfig)) |
      select((.cluster_name // .clusterName) == "outbound|8080||myapp.default.svc.cluster.local") |
      .endpoints[] | {locality, priority}'
```

#### 为什么不需要 Pod 标签

已调度 Pod 在该 Pod UID 生命周期内留在其节点；控制器可用另一节点上的新 Pod 替换。Istiod 通过 Kubernetes 发现将端点关联到节点拓扑。此正常局部性路由路径不需要额外 Pod 可用区标签。API 监视/缓存和代理配置异步收敛；应检查生效配置，不要假定立即更新。自定义遥测数据补充是独立问题。

```yaml
# Relevant existing Node metadata; do not overwrite actual cloud topology
metadata:
  labels:
    topology.kubernetes.io/zone: us-east-1a
    topology.kubernetes.io/region: us-east-1
```

#### AWS EKS 自动设置

AWS EKS 创建节点时自动添加拓扑标签：

```bash
# Check EKS nodes
kubectl get nodes -L topology.kubernetes.io/zone,topology.kubernetes.io/region

# Example output:
# NAME                           ZONE         REGION
# ip-10-0-1-10.ec2.internal      us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal      us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal      us-east-1c   us-east-1
```

EC2 节点的云/引导集成使用 AWS 实例放置信息。`spec.providerID` 标识提供商实例；本身不是 EC2 实例 ID。工作负载访问 IMDS 可能受限，IMDSv2 要求令牌；适当时使用下方只读 EC2 诊断。Fargate 节点需要自身平台诊断。

## 基本配置 {#basic-configuration}

### 1. 设置 Kubernetes 节点拓扑标签

AWS EKS 自动添加以下标签：

```yaml
topology.kubernetes.io/region: us-east-1
topology.kubernetes.io/zone: us-east-1a
```

**验证**：
```bash
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# Example output:
# NAME                          ZONE         REGION
# ip-10-0-1-10.ec2.internal     us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal     us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal     us-east-1c   us-east-1
```

### 2. 在 DestinationRule 启用可用区感知路由

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

基本示例使用局部性优先级加异常检测。100% 剔除上限允许排除所有不健康端点，若无存活容量可产生“没有健康上游”。这是示意故障转移设置，不是通用安全上限。

### 3. 配置分配比例

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1b/*
          to:
            us-east-1/us-east-1b/*: 80
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1c/*: 10
        - from: us-east-1/us-east-1c/*
          to:
            us-east-1/us-east-1c/*: 80
            us-east-1/us-east-1a/*: 10
            us-east-1/us-east-1b/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## 高级配置 {#advanced-configuration}

### 故障转移配置

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-failover
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

对于 `localityLbSetting`，`failoverPriority` 可如上比较区域/可用区元数据。`failover` 字段则接受**区域名称**，不是 `region/zone` 路径；不表达 A→B→C 可用区顺序。此处使用 `distribute`、`failover` 或 `failoverPriority` 之一。这些规则不同于独立 `zoneAwareLbSetting` API。

### 配合异常检测

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-resilient
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 20
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 0
```

`minHealthPercent` 是池恐慌/故障放行阈值，不是每可用区最小健康容量。零禁用阈值。80/20 加权分配继续使用两个健康可用区；不是备用故障转移。

### 多区域配置

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-multi-region
  namespace: default
spec:
  host: myapp.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/*
          to:
            us-east-1/*: 90
            us-west-2/*: 10
        - from: us-west-2/*
          to:
            us-west-2/*: 90
            us-east-1/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

90/10 示例仅作分配。需要真实多集群/网络设置在两个区域暴露该服务；`myapp.global` 不是自动创建的服务。若改用优先级故障转移，使用此独立策略并验证实际端点/连接：

```yaml
# Alternative to distribute: region-name priority failover
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-regional-failover
  namespace: default
spec:
  host: myapp.default.svc.cluster.local
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        failover:
        - from: us-east-1
          to: us-west-2
        - from: us-west-2
          to: us-east-1
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## AWS EKS 配置 {#configuration-on-aws-eks}

### 1. 创建多可用区节点组

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-east-1
  version: '1.36'
nodeGroups:
- name: ng-zone-a
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1a
  amiFamily: AmazonLinux2023
- name: ng-zone-b
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1b
  amiFamily: AmazonLinux2023
- name: ng-zone-c
  instanceType: t3.medium
  desiredCapacity: 2
  availabilityZones:
  - us-east-1c
  amiFamily: AmazonLinux2023
```

eksctl 文件是会产生费用的集群/节点组设计示例，不是本审计运行的命令。它在文档所述 Istio/EKS 兼容范围内固定 Kubernetes1.36，并使用 AL2023。选择真实子网/可用区、实例容量和访问设置；现有集群需要适当节点组变更计划。

### 2. 跨可用区分布 Pod

将有意不可解析的镜像引用替换为经测试、提供 HTTP8080 的应用镜像，并配置就绪行为。下方 Service 提供策略使用的 `myapp` 目的地。`maxSkew: 1` 作用于合格域，不无条件保证三个可用区；节点亲和性、污点、资源容量和 `minDomains` 影响调度。


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: default
spec:
  replicas: 9
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: myapp
      containers:
      - name: myapp
        image: example.invalid/myapp:replace-with-tested-tag
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: 64Mi
            cpu: 100m
          limits:
            memory: 128Mi
            cpu: 200m
---
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: default
spec:
  selector:
    app: myapp
  ports:
  - name: http
    port: 8080
    targetPort: 8080
```

### 3. 在 Istio 启用可用区感知路由

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 80
            us-east-1/us-east-1b/*: 10
            us-east-1/us-east-1c/*: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## 实际示例 {#practical-examples}

### 示例 1：微服务调用链

前三个文档是现有 frontend/backend Deployment 和数据库工作负载的 **Pod 模板补丁**，不是完整 Kubernetes 资源。将其合并到具有真实容器、选择器、Service 和存储的工作负载。数据库亲和性演示已绑定特定可用区的单个卷/实例；将全部数据库副本放在一个可用区不是高可用建议。最后的 DestinationRule 假定真实 `backend` Service。


```yaml
spec:
  template:
    metadata:
      labels:
        app: frontend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: frontend
---
spec:
  template:
    metadata:
      labels:
        app: backend
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: backend
---
spec:
  template:
    metadata:
      labels:
        app: database
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
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
  namespace: default
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 90
            us-east-1/us-east-1b/*: 5
            us-east-1/us-east-1c/*: 5
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

### 示例 2：成本优化

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cost-optimized
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 95
            us-east-1/us-east-1b/*: 3
            us-east-1/us-east-1c/*: 2
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

95/3/2 策略仅覆盖 zoneA 中调用方；需要时定义其他来源局部性。集中流量可能使本地端点过载。将实测计费字节和服务专属价格与 [EKS 网络成本指南](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)比较；仅请求数/权重不是成本计算。

### 示例 3：高可用

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-availability
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            us-east-1/us-east-1a/*: 34
            us-east-1/us-east-1b/*: 33
            us-east-1/us-east-1c/*: 33
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 100
      minHealthPercent: 0
```

## 监控 {#monitoring}

### Prometheus 指标

`source_zone` 和 `destination_zone` **不是标准 Istio 指标标签**。以下可选查询要求单独实现并验证的数据补充管道，将两端映射到实际可用区，同时保留正常服务标签。本章不部署该管道。仅标记 Node、启用局部性路由或添加 Grafana 面板不会创建这些指标。必要时保留集群/账户上下文；AWS 可用区名称在不同账户可能映射不同，AZ ID 才标识相同物理可用区。

示例显式覆盖一个集群/账户中 us-east-1a/b/c 之间流量。未知可用区、其他区域和其他目的地从分子分母同时排除。PromQL 不能在 `{source_zone=destination_zone}` 这样的选择器内比较两个标签值；按下方使用显式匹配对。速率为每秒，同可用区结果为 0–100 百分比。

```promql
sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

100 * sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1a",destination_zone="us-east-1a"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1b",destination_zone="us-east-1b"}[5m]) or rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone="us-east-1c",destination_zone="us-east-1c"}[5m])) / sum(rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))

sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]",response_code=~"5.."}[5m])) / sum by (destination_zone) (rate(istio_requests_total{reporter="source",source_workload_namespace="default",destination_service="myapp.default.svc.cluster.local",source_zone=~"us-east-1[abc]",destination_zone=~"us-east-1[abc]"}[5m]))
```

单独处理无流量、缺失补充数据和抓取失败。源报告统计请求，不是计费字节；目标报告遗漏未到达服务的失败。活动集群连接不揭示目标可用区，不能证明局部性有效。

### Grafana 仪表板

此仪表板要求上方数据补充及数据源 UID `prometheus`。按[仪表板章节](../observability/04-dashboards.md)预置完整对象。没有补充数据，这些面板不能有效测量可用区流量。

```json
{
  "uid": "istio-enriched-zone-traffic",
  "title": "Istio Enriched Zone Traffic",
  "panels": [
    {
      "id": 1,
      "title": "Enriched Request Rate by Zone",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "sum by (source_zone, destination_zone) (rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=~\"us-east-1[abc]\",destination_zone=~\"us-east-1[abc]\"}[5m]))",
          "legendFormat": "{{source_zone}} → {{destination_zone}}",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        }
      }
    },
    {
      "id": 2,
      "title": "Same-Zone Percentage (Known a/b/c Traffic)",
      "type": "timeseries",
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "targets": [
        {
          "expr": "100 * sum(rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1a\",destination_zone=\"us-east-1a\"}[5m]) or rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1b\",destination_zone=\"us-east-1b\"}[5m]) or rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=\"us-east-1c\",destination_zone=\"us-east-1c\"}[5m])) / sum(rate(istio_requests_total{reporter=\"source\",source_workload_namespace=\"default\",destination_service=\"myapp.default.svc.cluster.local\",source_zone=~\"us-east-1[abc]\",destination_zone=~\"us-east-1[abc]\"}[5m]))",
          "legendFormat": "Same-zone %",
          "refId": "A"
        }
      ],
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 24,
        "h": 8
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        }
      }
    }
  ],
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s"
}
```

### 实时验证

`proxy-config endpoints` 对主机健康有用，但展示不同于 EDS 局部性分配。`proxy-config all -o json` 包含 EDS；检查匹配 ClusterLoadAssignment。查询接受原始 snake_case 和规范化 camelCase JSON 字段名。这是配置证据，不是观测流量分布。

```bash
istioctl proxy-config endpoints <pod-name> -n <namespace>

istioctl proxy-config all <pod-name> -n <namespace> -o json | \
  jq '.configs[] | select(.["@type"] | endswith("EndpointsConfigDump")) |
      ((.dynamic_endpoint_configs // .dynamicEndpointConfigs // [])[] |
       (.endpoint_config // .endpointConfig)) |
      select((.cluster_name // .clusterName) == "outbound|8080||myapp.default.svc.cluster.local") |
      .endpoints[] | {locality, priority}'
```

## 故障排除 {#troubleshooting}

### 可用区感知路由不工作

修复标签前检查实际云拓扑。随意给每个节点应用同一可用区标签，会改变调度/存储/路由决策，并可能使元数据失真。路由示例要求目标策略到达调用方代理，并能发现目标端点。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>
istioctl analyze -n <namespace>
istioctl proxy-config clusters <pod-name> -n <namespace> --fqdn myapp.default.svc.cluster.local -o json
kubectl get pods -n <namespace> -l app=myapp -o wide
```

用上方命令读取 EDS。对于 Kubernetes EDS 集群，集群配置中的 `.loadAssignment` 不是端点来源。Pod 可用区标签不会自动从 Node 复制；通过 `.spec.nodeName` 连接。

### 发往其他可用区的流量比例高

使用结构化字段检查 Pod 到节点的放置和就绪。Running Pod 可能未就绪，节点数量摘要也不是可用区数量摘要。滚动发布期间两份快照时间可能不同。

```bash
kubectl get nodes -o json > /tmp/zone-nodes.json
kubectl get pods -n default -l app=myapp -o json > /tmp/zone-pods.json
jq -r --slurpfile nodes /tmp/zone-nodes.json '
  ($nodes[0].items | map({key: .metadata.name,
    value: .metadata.labels["topology.kubernetes.io/zone"]}) | from_entries) as $zones |
  .items[] | [.metadata.name, (.spec.nodeName // "unscheduled"),
    ($zones[(.spec.nodeName // "")] // "unknown"),
    ([.status.conditions[]? | select(.type == "Ready") | .status][0] // "Unknown")] | @tsv
' /tmp/zone-pods.json

istioctl x envoy-stats <pod-name> -n <namespace> --output prom | grep outlier_detection
```

还应检查端点/剔除状态、来源局部性 `from` 匹配、连接复用、流量和可用区备用容量。加权分配有意将部分健康流量发往其他可用区；副本数不均本身不会重新定义配置的可用区权重。

### EKS 缺少拓扑标签

AWS Node Termination Handler 响应中断/终止事件；安装它不修复拓扑标签。检查 EKS 节点引导/云集成和实际实例放置。以下诊断**只读且仅适用于 EC2 节点**；它从 providerID 提取实例 ID 并提供集群区域。不重新标记节点。Fargate 或非 EC2 提供商使用适当平台诊断。

```bash
CLUSTER_REGION=us-east-1
NODE_NAME=<node-name>
PROVIDER_ID=$(kubectl get node "$NODE_NAME" -o jsonpath='{.spec.providerID}')
INSTANCE_ID=${PROVIDER_ID##*/}
if [[ ! "$INSTANCE_ID" =~ ^i-([0-9a-f]{8}|[0-9a-f]{17})$ ]]; then
  echo "Expected an EC2 instance ID in providerID; inspect the node platform." >&2
  exit 1
fi
aws ec2 describe-instances --region "$CLUSTER_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AZ:Placement.AvailabilityZone,State:State.Name}' \
  --output table
```

应用已审核引导或标签修复前，确认账户/区域及实际节点身份。不要将整个 `aws:///zone/i-...` URI 传给 `--instance-ids`，也不要假定未经身份验证的 IMDSv1 访问可用。

## 最佳实践

### 1. 跨可用区均匀分布 Pod

将此片段放在 Pod 模板 `spec` 下，确保选择器匹配 Pod 标签。约束统计合格域；考虑可用区不可用时，严格调度是否应使 Pod 保持 Pending。


```yaml
# Use topologySpreadConstraints
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: myapp
```

### 2. 成本优化

```yaml
# Prioritize same zone (80% or more)
distribute:
- from: us-east-1/us-east-1a/*
  to:
    "us-east-1/us-east-1a/*": 80
    "us-east-1/us-east-1b/*": 10
    "us-east-1/us-east-1c/*": 10
```

### 3. 确保高可用

结合局部性优先级、异常检测和经测试备用容量。此片段位于 `trafficPolicy.loadBalancer.localityLbSetting` 下；`failover` 排序区域，不是可用区，并且是 `distribute` 的替代方案。

```yaml
failover:
- from: us-east-1
  to: us-west-2
```

### 4. 有状态工作负载的存储和可用性

EBS 卷及附加的 EC2 实例必须位于相同可用区。这约束单个卷/副本，不是 StatefulSet 的每个副本。用兼容存储和调度设计跨故障域数据库复制/故障转移；拓扑感知路由不能选举安全可写主节点。下方亲和性仅用于有意绑定现有 zoneA 卷的工作负载。不是建议将所有有状态副本放在同一可用区。


```yaml
# Pod-spec fragment for one existing zonal volume/replica
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

Kubernetes Service 拓扑提示/流量分布与 Istio Envoy 负载均衡是不同机制。不要假定启用 Service 注解会配置调用方 Sidecar 局部性策略。

## 参考资料

- [Istio 局部性负载均衡](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
- [Kubernetes 拓扑感知路由](https://kubernetes.io/docs/concepts/services-networking/topology-aware-routing/)
- [AWS EKS 韧性](https://docs.aws.amazon.com/eks/latest/userguide/disaster-recovery-resiliency.html)
- [EKS 网络成本优化](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [EBS 卷可用区](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volumes.html)
- [AWS 可用区 ID](https://docs.aws.amazon.com/global-infrastructure/latest/regions/az-ids.html)
