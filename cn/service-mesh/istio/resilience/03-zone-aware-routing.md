# Zone Aware Routing（区域感知路由）

Zone Aware Routing 是一项通过识别 Kubernetes Availability Zone（可用区）来优化流量的功能。它优先在同一 AZ 内通信，从而降低延迟和跨 AZ 数据传输成本。

## 目录

1. [概述](#overview)
2. [工作原理](#how-it-works)
3. [基本配置](#basic-configuration)
4. [高级配置](#advanced-configuration)
5. [AWS EKS 上的配置](#configuration-on-aws-eks)
6. [实践示例](#practical-examples)
7. [监控](#monitoring)
8. [故障排除](#troubleshooting)

## 概述

Zone Aware Routing 提供以下优势：

```mermaid
flowchart TB
    subgraph AZ1["Availability Zone A"]
        Client1[Client Pod<br/>Zone A]
        Service1[Service Pod 1<br/>Zone A]
        Service2[Service Pod 2<br/>Zone A]
    end

    subgraph AZ2["Availability Zone B"]
        Service3[Service Pod 3<br/>Zone B]
        Service4[Service Pod 4<br/>Zone B]
    end

    subgraph AZ3["Availability Zone C"]
        Service5[Service Pod 5<br/>Zone C]
    end

    Client1 -->|80%<br/>Same AZ Priority<br/>Free| Service1
    Client1 -->|80%<br/>Same AZ Priority<br/>Free| Service2
    Client1 -.->|10%<br/>Failover<br/>Cross-AZ Cost| Service3
    Client1 -.->|10%<br/>Failover<br/>Cross-AZ Cost| Service5

    %% Style definitions
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef sameZone fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;
    classDef otherZone fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Client1 client;
    class Service1,Service2 sameZone;
    class Service3,Service4,Service5 otherZone;
```

### 优势

1. **降低延迟**：通过同一 AZ 内通信将网络延迟降至最低
2. **节约成本**：减少跨 AZ 数据传输成本
   - AWS：跨 AZ 传输每 GB $0.01-0.02
3. **提高可用性**：发生故障时自动故障转移到其他 AZ
4. **性能优化**：优化网络带宽

## 工作原理

### Locality 负载均衡算法

```mermaid
flowchart TB
    Request[Request Arrives]
    CheckLocal{Healthy Pods<br/>in Same Zone?}
    LocalRoute[Route to<br/>Same Zone<br/>80-100%]
    CheckNearby{Healthy Pods<br/>in Adjacent Zone?}
    NearbyRoute[Route to<br/>Adjacent Zone<br/>10-20%]
    RemoteRoute[Route to<br/>Other Region]

    Request --> CheckLocal
    CheckLocal -->|Yes| LocalRoute
    CheckLocal -->|No| CheckNearby
    CheckNearby -->|Yes| NearbyRoute
    CheckNearby -->|No| RemoteRoute

    %% Style definitions
    classDef request fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef decision fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef route fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Request request;
    class CheckLocal,CheckNearby decision;
    class LocalRoute,NearbyRoute,RemoteRoute route;
```

### Locality 层级

Istio 使用以下分层的 Locality：

```
Region/Zone/SubZone

Example:
us-east-1/us-east-1a/*
us-east-1/us-east-1b/*
us-west-2/us-west-2a/*
```

**优先级**：
1. **同一 Zone**：相同 Region、相同 Zone
2. **同一 Region**：相同 Region、不同 Zone
3. **不同 Region**：不同 Region

### 没有 Pod AZ 标签时的工作原理

**重要提示**：Pod 本身不需要 AZ 标签。Istio 会读取 **Node Topology 标签**，自动确定 Pod Locality。

#### 工作原理

```mermaid
flowchart TB
    subgraph Node1["Node 1<br/>topology.kubernetes.io/zone=us-east-1a"]
        Pod1[Pod A<br/>No Zone Label]
        Pod2[Pod B<br/>No Zone Label]
    end

    subgraph Node2["Node 2<br/>topology.kubernetes.io/zone=us-east-1b"]
        Pod3[Pod C<br/>No Zone Label]
    end

    subgraph Istiod["Istiod (Control Plane)"]
        Discovery[Service Discovery]
        EDS[EDS Generation]
    end

    Discovery -->|"1. Query Node Labels<br/>Pod → Node Mapping"| Node1
    Discovery -->|"1. Query Node Labels<br/>Pod → Node Mapping"| Node2
    Discovery -->|"2. Determine Pod Locality<br/>Pod A → us-east-1a<br/>Pod C → us-east-1b"| EDS
    EDS -->|"3. xDS Push<br/>(Including Locality Info)"| Envoy[Envoy Proxy]

    %% Style definitions
    classDef node fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef control fill:#FF9900,stroke:#333,stroke-width:2px,color:black;

    class Node1,Node2 node;
    class Pod1,Pod2,Pod3 pod;
    class Discovery,EDS,Envoy control;
```

#### 分步流程

**第 1 步：Istiod 收集 Pod 信息**

```bash
# Istiod queries Pod information via Kubernetes API
kubectl get pod <pod-name> -o json | jq '.spec.nodeName'
# Output: "ip-10-0-1-10.ec2.internal"
```

**第 2 步：查询运行 Pod 的 Node 的 Topology 标签**

```bash
# Query Node info using Pod's nodeName
kubectl get node ip-10-0-1-10.ec2.internal -o json | \
  jq '.metadata.labels."topology.kubernetes.io/zone"'
# Output: "us-east-1a"
```

**第 3 步：生成 EDS（Endpoint Discovery Service）**

Istiod 使用 Pod IP 和 Locality 信息生成 EDS：

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

**第 4 步：Envoy 执行基于 Locality 的路由**

Envoy 将自身的 Locality 与收到的 EDS 信息进行比较以执行路由：

```bash
# Check Envoy's Locality (based on node it's running on)
kubectl exec <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/config_dump | \
  jq '.configs[] | select(.["@type"] | contains("BootstrapConfigDump")) | .bootstrap.node.locality'

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
istioctl proxy-config endpoints <pod-name> | grep myapp
# ENDPOINT          STATUS    OUTLIER CHECK     CLUSTER                    LOCALITY
# 10.0.1.10:8080    HEALTHY   OK                myapp.default              us-east-1/us-east-1a
# 10.0.2.20:8080    HEALTHY   OK                myapp.default              us-east-1/us-east-1b
```

#### 为什么不需要 Pod 标签

**传统方法（不需要）**：
```yaml
# Not needed
apiVersion: v1
kind: Pod
metadata:
  labels:
    topology.kubernetes.io/zone: us-east-1a  # Unnecessary!
```

**Istio 方法（自动）**：
```yaml
# Only Node labels needed
apiVersion: v1
kind: Node
metadata:
  name: ip-10-0-1-10.ec2.internal
  labels:
    topology.kubernetes.io/zone: us-east-1a  # This is all you need!
    topology.kubernetes.io/region: us-east-1
```

**原因**：
1. **Pod 不会移动**：Pod 创建后不会迁移到其他 Node
2. **Node 是唯一事实来源**：Pod 的物理位置始终由 Node 决定
3. **消除冗余**：无需为每个 Pod 添加标签，只需管理 Node 标签
4. **自动同步**：Istiod 始终从 Kubernetes API 查询最新的 Node 信息

#### AWS EKS 自动设置

AWS EKS 会在创建 Node 时自动添加 Topology 标签：

```bash
# Check EKS nodes
kubectl get nodes -L topology.kubernetes.io/zone,topology.kubernetes.io/region

# Example output:
# NAME                           ZONE         REGION
# ip-10-0-1-10.ec2.internal      us-east-1a   us-east-1
# ip-10-0-2-20.ec2.internal      us-east-1b   us-east-1
# ip-10-0-3-30.ec2.internal      us-east-1c   us-east-1
```

这些标签会自动从以下来源获取：
- **EC2 Instance Metadata**：`http://169.254.169.254/latest/meta-data/placement/availability-zone`
- **AWS API**：通过 Node 的 `spec.providerID` 查询 EC2 信息

## 基本配置

### 1. 在 Kubernetes Node 上设置 Topology 标签

AWS EKS 会自动添加以下标签：

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

### 2. 在 DestinationRule 中启用 Zone Aware Routing

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
        enabled: true  # Enable Zone Aware Routing
```

### 3. 配置流量分配比例

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
        # Traffic originating from us-east-1a
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80   # 80% to same AZ
            "us-east-1/us-east-1b/*": 10   # 10% to adjacent AZ
            "us-east-1/us-east-1c/*": 10   # 10% to adjacent AZ

        # Traffic originating from us-east-1b
        - from: us-east-1/us-east-1b/*
          to:
            "us-east-1/us-east-1b/*": 80
            "us-east-1/us-east-1a/*": 10
            "us-east-1/us-east-1c/*": 10

        # Traffic originating from us-east-1c
        - from: us-east-1/us-east-1c/*
          to:
            "us-east-1/us-east-1c/*": 80
            "us-east-1/us-east-1a/*": 10
            "us-east-1/us-east-1b/*": 10
```

## 高级配置

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
        failover:
        # When us-east-1a fails, go to us-east-1b
        - from: us-east-1/us-east-1a
          to: us-east-1/us-east-1b

        # When us-east-1b fails, go to us-east-1c
        - from: us-east-1/us-east-1b
          to: us-east-1/us-east-1c

        # When us-east-1c fails, go to us-east-1a
        - from: us-east-1/us-east-1c
          to: us-east-1/us-east-1a
```

### 与 Outlier Detection 一起使用

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-resilient
  namespace: default
spec:
  host: myapp
  trafficPolicy:
    # Zone Aware Routing
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 20

    # Outlier Detection
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50

      # Maintain minimum healthy instances per zone
      minHealthPercent: 50
```

### 多 Region 配置

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp-multi-region
  namespace: default
spec:
  host: myapp.global
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true

        # Cross-region distribution
        distribute:
        # Traffic originating from us-east-1
        - from: us-east-1/*/*
          to:
            "us-east-1/*/*": 90      # 90% to same region
            "us-west-2/*/*": 10      # 10% to other region

        # Traffic originating from us-west-2
        - from: us-west-2/*/*
          to:
            "us-west-2/*/*": 90
            "us-east-1/*/*": 10

        # Region failover
        failover:
        - from: us-east-1
          to: us-west-2
        - from: us-west-2
          to: us-east-1
```

## AWS EKS 上的配置

### 1. 创建多 AZ Node Group

```yaml
# eksctl configuration
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: my-cluster
  region: us-east-1

nodeGroups:
  - name: ng-zone-a
    instanceType: t3.medium
    desiredCapacity: 2
    availabilityZones:
      - us-east-1a
    labels:
      zone: us-east-1a

  - name: ng-zone-b
    instanceType: t3.medium
    desiredCapacity: 2
    availabilityZones:
      - us-east-1b
    labels:
      zone: us-east-1b

  - name: ng-zone-c
    instanceType: t3.medium
    desiredCapacity: 2
    availabilityZones:
      - us-east-1c
    labels:
      zone: us-east-1c
```

### 2. 在 Zone 之间分布 Pod

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
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
      # Even distribution across zones
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: myapp

      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
```

### 3. 在 Istio 中启用 Zone Aware Routing

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 80
            "us-east-1/us-east-1b/*": 10
            "us-east-1/us-east-1c/*": 10
```

## 实践示例

### 示例 1：微服务链路

```yaml
# Frontend → Backend → Database

# Frontend (All AZs)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 6
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: frontend
---
# Backend (All AZs)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 9
  template:
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: backend
---
# Database (Single AZ - StatefulSet)
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: database
spec:
  replicas: 1
  template:
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
# Zone Aware Routing configuration
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend
spec:
  host: backend
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 90
            "us-east-1/us-east-1b/*": 5
            "us-east-1/us-east-1c/*": 5
```

### 示例 2：成本优化

```yaml
# Minimize cross-AZ costs
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cost-optimized
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Concentrate 95% in same AZ
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 95
            "us-east-1/us-east-1b/*": 3
            "us-east-1/us-east-1c/*": 2
```

### 示例 3：高可用性

```yaml
# Availability first (allow cross-AZ)
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: high-availability
spec:
  host: myapp
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        # Even distribution across all AZs
        - from: us-east-1/us-east-1a/*
          to:
            "us-east-1/us-east-1a/*": 34
            "us-east-1/us-east-1b/*": 33
            "us-east-1/us-east-1c/*": 33

        # Failover configuration
        failover:
        - from: us-east-1/us-east-1a
          to: us-east-1/us-east-1b
```

## 监控

### Prometheus 指标

```promql
# Traffic distribution across zones
sum(rate(istio_requests_total[5m])) by (source_zone, destination_zone)

# Same zone traffic ratio
(
  sum(rate(istio_requests_total{source_zone=destination_zone}[5m]))
  /
  sum(rate(istio_requests_total[5m]))
) * 100

# Error rate by zone
sum(rate(istio_requests_total{response_code=~"5.."}[5m])) by (destination_zone)
/
sum(rate(istio_requests_total[5m])) by (destination_zone)

# Locality information check
envoy_cluster_upstream_cx_active{envoy_cluster_name=~".*myapp.*"}
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Istio Zone Aware Routing",
    "panels": [
      {
        "title": "Traffic Distribution by Zone",
        "targets": [
          {
            "expr": "sum(rate(istio_requests_total[5m])) by (source_zone, destination_zone)",
            "legendFormat": "{{source_zone}} → {{destination_zone}}"
          }
        ]
      },
      {
        "title": "Same Zone Traffic Percentage",
        "targets": [
          {
            "expr": "(sum(rate(istio_requests_total{source_zone=destination_zone}[5m])) / sum(rate(istio_requests_total[5m]))) * 100",
            "legendFormat": "Same Zone %"
          }
        ]
      }
    ]
  }
}
```

### 实时验证

```bash
# Check Envoy endpoints
istioctl proxy-config endpoints <pod-name> -n <namespace>

# Check locality information
kubectl exec -n <namespace> <pod-name> -c istio-proxy -- \
  curl localhost:15000/clusters | grep myapp

# Example output:
# myapp.default.svc.cluster.local::10.0.1.10:8080::region::us-east-1::zone::us-east-1a::
# myapp.default.svc.cluster.local::10.0.2.20:8080::region::us-east-1::zone::us-east-1b::
```

## 故障排除

### Zone Aware Routing 未生效

```bash
# 1. Check node Topology labels
kubectl get nodes -L topology.kubernetes.io/zone -L topology.kubernetes.io/region

# If labels are missing, add manually:
kubectl label nodes <node-name> topology.kubernetes.io/zone=us-east-1a
kubectl label nodes <node-name> topology.kubernetes.io/region=us-east-1

# 2. Check DestinationRule
kubectl get destinationrule -n <namespace>
kubectl describe destinationrule <name> -n <namespace>

# 3. Check Envoy configuration
istioctl proxy-config clusters <pod-name> -n <namespace> -o json | \
  jq '.[] | select(.name | contains("myapp")) | .loadAssignment.endpoints[].locality'

# 4. Check pod zone distribution
kubectl get pods -n <namespace> -o wide \
  -L topology.kubernetes.io/zone
```

### 流量流向其他 Zone 的比例过高

```bash
# Root cause analysis:
# 1. Unbalanced pod count per zone
kubectl get pods -n <namespace> -o wide | \
  awk '{print $7}' | sort | uniq -c

# 2. Some pods are unhealthy
kubectl get pods -n <namespace> -o wide | \
  grep -v "Running"

# 3. Pods excluded by Outlier Detection
kubectl exec -n <namespace> <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep outlier_detection
```

### EKS 上缺少 Topology 标签

```bash
# Resolve by installing AWS Node Termination Handler
kubectl apply -f https://github.com/aws/aws-node-termination-handler/releases/download/v1.19.0/all-resources.yaml

# Or add labels manually
for node in $(kubectl get nodes -o name); do
  ZONE=$(kubectl get $node -o jsonpath='{.metadata.labels.topology\.kubernetes\.io/zone}')
  if [ -z "$ZONE" ]; then
    # Get AZ from AWS EC2 metadata
    ZONE=$(kubectl get $node -o jsonpath='{.spec.providerID}' | \
      xargs -I {} aws ec2 describe-instances --instance-ids {} --query 'Reservations[0].Instances[0].Placement.AvailabilityZone' --output text)
    kubectl label $node topology.kubernetes.io/zone=$ZONE
  fi
done
```

## 最佳实践

### 1. 在 Zone 之间均匀分布 Pod

```yaml
# Use topologySpreadConstraints
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
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

### 3. 确保高可用性

```yaml
# Failover configuration is essential
failover:
- from: us-east-1/us-east-1a
  to: us-east-1/us-east-1b
```

### 4. 推荐为 StatefulSet 使用单个 AZ

```yaml
# Deploy StatefulSet (Database, etc.) in single AZ
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

## 参考资料

- [Istio Locality Load Balancing](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/)
- [Kubernetes Topology Aware Hints](https://kubernetes.io/docs/concepts/services-networking/topology-aware-hints/)
- [AWS EKS Multi-AZ](https://docs.aws.amazon.com/eks/latest/userguide/disaster-recovery-resiliency.html)
