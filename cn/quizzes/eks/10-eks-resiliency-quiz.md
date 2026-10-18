# Amazon EKS 高可用性与弹性测验

> **示例 API 基线**：Kubernetes 1.36；官方来源/测验假设与[源章节](../../eks/10-eks-resiliency.md)一致。
> **最后更新**：September 12, 2026

配置和数值示例仅用于说明。本次审计未运行云资源、混沌实验、工作负载或基准测试。请使用自有测试范围，并在部署前替换占位符。

本测验考查你对 Amazon EKS 集群高可用性（HA）、弹性、多可用区部署、单元化架构、混沌工程、PodDisruptionBudget 和拓扑分布约束的理解。

## 测验概览
- 多可用区架构与配置
- 单元化架构模式
- 混沌工程原则与工具
- PodDisruptionBudget（PDB）配置
- 拓扑分布约束
- 灾难恢复与故障转移

## 选择题

### 1. 多可用区 EKS 工作负载的主要弹性收益是什么？

A. 自动降低成本
B. 若已准备好容量、数据和路由，则在一个 AZ 故障后仍能继续提供服务的设计
C. 以更高延迟为目标
D. 消除运维复杂性

<details>
<summary>查看答案</summary>

**答案：B. 若已准备好容量、数据和路由，则在一个 AZ 故障后仍能继续提供服务的设计**

多可用区能改善故障域设计，但不保证工作负载/数据自动故障转移，也不保证 99.99% 可用性；它也不能解决整个区域丢失的问题。六个容量相同且均匀分布在三个 AZ 的节点，在失去一个 AZ 后会剩下四个；仍须检查实际 Pod 放置和容量。下面只是资源配置输入示例，并未执行创建。版本 1.36 是本章基线：创建资源前，请确认当前区域提供的 EKS/AMI 支持情况。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 2. PodDisruptionBudget 会限制什么？

A. Pod 的 CPU 使用量
B. 根据工作负载可用性限制受支持的主动驱逐
C. 所有 Pod 间流量
D. 每一种 Pod 终止原因

<details>
<summary>查看答案</summary>

**答案：B. 根据工作负载可用性限制受支持的主动驱逐**

PDB admission 会约束 Eviction API，例如遵循该 API 的 drain、维护或自动扩缩操作。它不能防止直接删除 Pod、Deployment 滚动更新/缩容或非主动故障。请在 minAvailable 和 maxUnavailable 中选择一个；标签必须匹配预期的控制器工作负载。此示例是下方百分比 PDB 的替代方案，不应与其作为重叠策略一同应用。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
```

</details>

### 3. whenUnsatisfiable: DoNotSchedule 有什么作用？

A. 即使违反此约束，也会在任意位置调度
B. 没有符合分布约束的可用节点时，让新 Pod 保持未调度状态
C. 忽略所有调度约束
D. 删除现有 Pod 以恢复平衡

<details>
<summary>查看答案</summary>

**答案：B. 没有符合分布约束的可用节点时，让新 Pod 保持未调度状态**

这是一个调度过滤规则，不是 API server 对 Pod 对象的拒绝。ScheduleAnyway 只会让这条分布规则成为偏好；资源、亲和性、污点和存储约束仍然适用。下方完整 Deployment 使用占位镜像和特定于应用的健康检查路径，应用前请替换它们。minDomains=2 允许在剩余两个符合条件的 Zone 时计算 N-1 情况，但不会强制最初占用三个 AZ，也不会创建容量。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

</details>

### 4. 以下哪一项不是单元化架构的目标？

A. 独立部署/扩缩
B. 将单元故障传播到整个系统
C. 自包含的功能单元
D. 与其他单元保持有限耦合

<details>
<summary>查看答案</summary>

**答案：B. 将单元故障传播到整个系统**

隔离是一种需要实现和测试的设计属性，不会因使用 Namespace 标签而自动产生。请分别处理路由/admission 限制、容量和数据依赖；还要考虑共享节点、控制平面、DNS 和路由器。以下两个 namespace 只表达分组关系。Quota 和 NetworkPolicy 需要额外的强制执行措施，也不会创建物理故障域。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
```

</details>

### 5. 混沌工程中的稳态假设是什么？

A. 让服务保持停止状态
B. 关于故障前、故障期间和故障后可接受行为的可测量假设
C. 仅指停止实验的命令
D. 最大可能负载

<details>
<summary>查看答案</summary>

**答案：B. 关于故障前、故障期间和故障后可接受行为的可测量假设**

实验前请定义面向用户的指标、时间窗口、缺失数据时的处理方式和中止阈值。原示例中的 p99<200ms、errors<0.1%、throughput>1000req/s 和 Ready Pods>99% 都是说明性阈值，并非观测结果。Ready Pod 百分比不等于请求可用性。经审查的 operator CRD 中没有 Litmus ChaosExperiment.spec.definition.steadyState 字段。下面的 JSON 是人工审查计划，不是 Kubernetes 资源。

```json
{
  "scenario": "one bounded test fault",
  "hypothesis": {
    "p99_latency_seconds": "<0.2",
    "error_percentage": "<0.1",
    "request_rate_per_second": ">1000",
    "ready_pod_percentage": ">99"
  },
  "required_observations": [
    "baseline",
    "during fault",
    "recovery",
    "missing data"
  ],
  "abort": "Set an independent measured threshold and recovery owner before execution"
}
```

</details>

### 6. 在 Kubernetes 1.36 基线中，Service 的哪个字段表达同 Zone 偏好？

A. spec.trafficDistribution: PreferSameZone
B. spec.zoneRouting: enabled
C. spec.localOnly: true
D. spec.crossZone: disabled

<details>
<summary>查看答案</summary>

**答案：A. spec.trafficDistribution: PreferSameZone**

PreferSameZone/PreferSameNode 从 1.35 起为 GA。它们表达的是偏好，不是严格隔离，也不保证节省成本。PreferClose 是较早的别名。旧式 topology-mode=Auto 注解采用另一种提示启发式；topology-aware-hints 属于旧指导方式。请检查 proxy 实现、EndpointSlices 和 Local 流量策略的优先级。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 7. 有八个健康副本、当前没有持续中的中断，且 maxUnavailable: 25% 时，名义上的驱逐额度是多少？

A. 1
B. 2
C. 3
D. 4

<details>
<summary>查看答案</summary>

**答案：B. 2**

ceil(8×0.25)=2。两种 PDB 百分比形式都会向上取整，而不是向下：三个副本配置 maxUnavailable: 25% 时，ceil(0.75)=1；minAvailable: 75% 时，ceil(2.25)=3 个 Pod 必须健康。不健康的 Pod 和持续中的中断都会占用预算；这不保证任何故障期间始终运行六个 Pod。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb-percentage
  namespace: resilience-demo
spec:
  selector:
    matchLabels:
      app: web-app
  maxUnavailable: 25%
```

</details>

### 8. 对于经审查的 Litmus operator/catalog，哪一项说法不正确？

A. pod-delete 是 catalog 中的故障
B. node-drain 与实例终止不同
C. pod-network-loss 是 catalog 中的故障
D. cluster-delete 是会删除整个 EKS 集群的标准故障

<details>
<summary>查看答案</summary>

**答案：D. cluster-delete 是会删除整个 EKS 集群的标准故障**

经审查的 catalog 包含这些确切的 Pod/节点故障名称，不包含所声称的 cluster-delete 故障。不要假设 network-loss 或 ec2-terminate 这类通用名称就是有效 ID。当前 AWS catalog 包括 aws-az-chaos、ebs-loss-by-id/by-tag 和 ec2-stop-by-id/by-tag。请检查实际故障定义、所需 RBAC 和 runner 镜像。仅安装 operator 并不会安装所有实验；3.31.0 operator 不定义 ChaosHub 或 ChaosSchedule。


</details>

### 9. 谁负责区域级 EKS 控制平面的可用性？

A. 用户手动放置 API server
B. AWS 在三个 AZ 间管理区域控制平面
C. 它始终是单 AZ 控制平面
D. 用户必须为托管 EKS 实现 etcd 故障转移

<details>
<summary>查看答案</summary>

**答案：B. AWS 在三个 AZ 间管理区域控制平面**

区域级 EKS 会将其托管控制平面分布在三个 AZ；客户子网至少需要两个 AZ 是另一项要求。Standard Control Plane 的月度 endpoint SLA 为 99.95%，Provisioned Control Plane 为 99.99%，二者的服务抵扣条件和计量周期不同。这些 SLA 不保证应用可用性，也不提供由客户管理的工作负载/PV 备份。客户仍负责工作负载/数据平面的放置、数据恢复和 SLO 计量。


</details>

### 10. 使用 DoNotSchedule 放置 Pod 时，maxSkew 限制什么？

A. Pod 总数上限
B. 候选拓扑域中的 Pod 数与全局最小值之间的差值
C. 节点数量下限
D. 每个节点的 Pod 数上限

<details>
<summary>查看答案</summary>

**答案：B. 候选拓扑域中的 Pod 数与全局最小值之间的差值**

符合条件的拓扑域和 minDomains 决定全局最小值；符合条件的域少于 minDomains 时，最小值为零。若剩余两个符合条件的 Zone 中计数为 2/2，minDomains=3 且 maxSkew=1 会阻止替换 Pod。2/2/2 是一种健康分布示例，并非永久不变的状态；3/2/1 符合 skew=2 的示例，而在 4/1/1 不平衡时继续放置 Pod 可能失败。现有 Pod 不会自动重新平衡或删除。


</details>

## 简答题

### 1. Kubernetes 1.36 Service 应使用哪个字段表达同 Zone 偏好？

<details>
<summary>查看答案</summary>

spec.trafficDistribution: PreferSameZone。这是偏好；请测量路由行为和成本。旧式 topology-aware-hints 注解不是当前答案。请检查 Local 流量策略以及实际为该 Service 提供服务的实现。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 2. 列出三种可以使用 PDB 感知主动驱逐的操作，并说明哪些操作会绕过它。

<details>
<summary>查看答案</summary>

例如：通过 Eviction 执行 kubectl drain、通过 Eviction drain 的升级工作流，以及遵循该机制的节点自动扩缩器缩容。请确认具体实现和 force 选项。Deployment/StatefulSet 滚动更新、直接运行 kubectl delete pod 以及某些云端期望容量变更，不会以相同方式经过 PDB admission。Cordon 只会阻止新调度，不会驱逐现有 Pod。硬件故障、kernel panic 和 OOM 无法由 PDB 阻止。


</details>

### 3. 请列出有效混沌实验的四项控制措施。

<details>
<summary>查看答案</summary>

定义可测量的稳态假设；选择真实且范围受限的故障；使用有代表性的环境，若确有必要在生产环境测试则必须获得明确授权；通过独立观测、中止阈值和恢复负责人将影响范围降至最小。自动化和实验后分析可提高可重复性，但二者都不意味着必须在生产环境测试，也不会自动恢复数据。


</details>

### 4. 此工作负载示例为何使用三个 AZ？这是 EKS 节点组的最低要求吗？

<details>
<summary>查看答案</summary>

若三个 AZ 的容量相同且工作负载及其依赖也已分布，则失去一个 AZ 后会剩下原有容量的三分之二。这是设计选择，不是通用的节点组 API 最低要求。EKS 集群子网至少需要两个 AZ；其区域级托管控制平面跨三个 AZ。客户节点组的 AZ 不决定 EKS 托管 etcd 的放置位置。请根据所在区域、实例类型、存储和工作负载约束选择可用 AZ。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 5. 路由层应如何将流量分配到某个单元？

<details>
<summary>查看答案</summary>

使用可信的租户身份，并采用稳定哈希、显式映射或区域分配。路由器必须验证授权、容量和数据放置；不能把任意客户端提供的 x-cell-id 当作租户授权。网格示例假设目标 Service 已注册且策略兼容。对于未知/不可信的 cell ID，必须明确拒绝或定义默认策略。仅靠两个 namespace 或一个路由 ConfigMap，无法实现隔离或故障转移。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cell-routing-example
  namespace: resilience-demo
spec:
  hosts:
  - cell-router.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-cell-id:
          exact: cell-a
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: cell-b
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## 动手练习

### 1. 为 app=api-server 编写 api-server-pdb，使 PDB 感知的驱逐至少需要三个可用副本。

<details>
<summary>查看答案</summary>

这是你的应用标签，不是 AWS 托管的 Kubernetes API server。namespace 和匹配的控制器工作负载必须已存在。若有五个 Ready 副本且没有持续中的中断，名义驱逐额度为两个；三个副本时则没有健康 Pod 可供驱逐。请检查实际状态，不要假设早先的示例输出就是实测结果。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: resilience-demo
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```
```bash
# Prerequisite: the owned test namespace and matching application already exist.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=api-server
# MUTATION: apply only this reviewed PDB file.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f api-server-pdb.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo describe pdb api-server-pdb
```

</details>

### 2. 编写一个具有六个副本和 Zone 分布规则的 web-frontend，并说明 AZ 丢失时的权衡。

<details>
<summary>查看答案</summary>

完整示例使用 maxSkew=1 和 minDomains=2 应对 N-1 情况。必须分别验证初始的三 Zone 放置和故障后剩余 Zone 的容量。此规则不会自动重新平衡，也不会迁移 zonal PVC。请替换应用占位镜像/健康检查路径；资源值仅为示例。受控 apply 后，应使用下方 Python 报告，而不要假设每个 Pod 都已有节点名/Zone 标签。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
```
```bash
# MUTATION: replace the image/health contract and review this exact file first.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f web-frontend.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/web-frontend --timeout=5m
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=web-frontend -o json > frontend-pods.json
kubectl --context "$KUBE_CONTEXT" get nodes -o json > frontend-nodes.json
```
```python
import collections, json
from pathlib import Path
pods = json.loads(Path("frontend-pods.json").read_text())["items"]
nodes = json.loads(Path("frontend-nodes.json").read_text())["items"]
zones = {n["metadata"]["name"]: n["metadata"].get("labels", {}).get("topology.kubernetes.io/zone", "<unlabeled>") for n in nodes}
counts, ready = collections.Counter(), collections.Counter()
for pod in pods:
    if pod["metadata"].get("deletionTimestamp"):
        continue
    node = pod.get("spec", {}).get("nodeName")
    zone = zones.get(node, "<unknown-node>") if node else "<unscheduled>"
    counts[zone] += 1
    if any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
        ready[zone] += 1
print(json.dumps({"activePodsByZone": dict(counts), "readyPodsByZone": dict(ready)}, indent=2))
```

</details>

### 3. 准备一个已停止的、持续 30 秒、范围限定为一个经审查测试 Pod 的 Litmus 删除实验。

<details>
<summary>查看答案</summary>

请使用 resilience-demo 中由你管理的 payment-service 测试工作负载，不要使用宽泛的生产选择器。检查 UID/owner 后，将 TARGET_PODS 替换为确切的当前名称。operator、pod-delete ChaosExperiment、经验证的 runner/helper 镜像和范围受限的 RBAC 都必须先经过审查。duration/interval 可能导致重复删除尝试；这不能证明 30 秒内只删除一次。如果需求是执行一次选定的删除操作，请使用章节中的 FIS COUNT(1) 示例，并满足其独立的 IAM/RBAC 前提。这里不会执行任何故障。

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=payment-service,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
```bash
# Read-only: resolve an exact current Pod name/UID before filling TARGET_PODS.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=payment-service,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosexperiment pod-delete
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get serviceaccount pod-delete-sa
# MUTATION: this reviewed file must still have engineState: stop.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f payment-pod-delete-review.yaml
```
```bash
# Read-only observation; no experiment is started by these commands.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine payment-pod-delete-review -o yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosresult
```

</details>

## 高级问题

### 1. 为金融服务工作负载设计 99.99% 可用性 SLO，并指出必须证明哪些内容。

<details>
<summary>查看答案</summary>

99.99% 是工作负载 SLO，并不是以下资源配置所能保证的结果。对于 365 天的时间窗口，算术上的预算为每年 52.56 分钟（此前“约 52 分钟”的说法只是近似值）；EKS SLA 是单独按月计算的服务抵扣承诺。基于请求数的可用性采用不同的分母。请定义每个关键用户旅程、部分故障、计量窗口、RTO/RPO 和告警。

准备主/备用区域，并确保数据、身份、DNS、路由、可观测性和容量均可独立使用。测试复制延迟、写入提升/冲突和恢复责任；Multi-AZ 或 Active-Active 本身都不能保证零数据丢失。以下保持原始规模的资源值仅用于设计说明，不是测得的容量，也不是已执行的部署。

#### 多可用区节点输入和单元资源

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-critical
  instanceType: m5.xlarge
  desiredCapacity: 9
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
  labels:
    criticality: high
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finance-cell
  labels:
    cell: finance
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: finance-cell
spec:
  hard:
    requests.cpu: '100'
    requests.memory: 200Gi
    limits.cpu: '200'
    limits.memory: 400Gi
```

Quota 不会预留节点，也不会隔离共享依赖。请加入章节中经过审查的路由器/网络策略/数据边界。以下严格的 hostname 反亲和性要求九个副本都放在符合条件且带有 criticality=high 的九个节点上；扩至 30 个副本也需要相应节点容量。严格放置可能会故意让 Pod 保持 Pending。请替换占位镜像/健康检查契约，并先确认所选区域/版本/实例是否可用。

#### 放置和驱逐预算

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: finance-cell
spec:
  replicas: 9
  selector:
    matchLabels:
      app: payment-api
  template:
    metadata:
      labels:
        app: payment-api
        tier: critical
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: payment-api
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: payment-api
      nodeSelector:
        criticality: high
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: payment-api
            topologyKey: kubernetes.io/hostname
```
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
  namespace: finance-cell
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: payment-api
```

有九个健康副本时，minAvailable: 80% 向上取整为八；扣除其他因素前，名义上只允许驱逐一个健康 Pod。它不会约束每次 rollout、云端缩容或 AZ 故障。minDomains=2 支持所述 N-1 放置计算，但不会自动疏散工作负载或迁移数据。

#### 具有实际目标和指标契约的 HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
  namespace: finance-cell
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-api
  minReplicas: 9
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

CPU 资源指标要求 Metrics Server 正常工作，并且相关容器设置了 CPU requests。增加副本无法修复内存泄漏、数据库耗尽或区域卷限制。请保持副本数由字段/GitOps/HPA 中一致的所有者管理。

定期进行 game day 时，请使用自有调度器或经批准的工作流来调用经过审查的单项实验，记录确切目标/ID，监测中止信号，并在执行下一项故障前确认已恢复。旧的 2024 ChaosSchedule 片段既已过期，也不是 Litmus 3.31.0 中的 CRD；只修改日期并不能修复它。99.99% 的声明需要实际 SLI 证据和演练，而不只是每周运行一个计划。

</details>

### 2. 规划 Black Friday 流量达到 10× 的场景，包括预扩容和有界故障恢复。

<details>
<summary>查看答案</summary>

10× 是测试目标，并非测量结果。请建模请求组合、CPU/内存、预热、连接、队列、数据库和外部服务配额。承载目标流量时，还要为一个 AZ 丢失预留容量。NodePool 限制是资源调配上限，**不是已经创建或预留的容量**。现有 EC2NodeClass、AMI/IAM、子网/IP 和所选实例类型必须支持该设计。零主动中断预算不能阻止中断、修复或所有强制终止。

#### 需要验证的容量设置

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: blackfriday-example
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-test-class
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.2xlarge
        - m5.4xlarge
        - c5.2xlarge
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  limits:
    cpu: 2000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: '0'
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
  namespace: resilience-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleDown:
      selectPolicy: Disabled
```

原例中的常态 10 / 最小 50 / 最大 500 仅用于说明：副本下限扩大五倍，并不能证明吞吐量会达到十倍。此 HPA 假设已有 product-catalog Deployment，并且设置了 CPU requests、指标也正常工作。禁用 scaleDown 会在扩容仍可进行时阻止 HPA 缩容；这并不会暂停整个 HPA。活动开始前，请验证 Ready Pod、健康 endpoint 和现有可用节点/余量；结束后恢复经过审查的常态策略。

活动前，请在有代表性的测试负载下运行章节中另行审查过的实验：一次范围受限的 Pod 故障、一个受控的区域迁移/网络场景，以及依赖延迟测试。不要将 node-drain 当作整个 AZ 故障，不要把标签选择器当作 TARGET_PODS，也不要在一个运行中的生产引擎里组合未经审查的故障。记录包括失败/无数据情况及实际恢复状态在内的结果。

#### 场景响应计划

| 场景 | 证据 | 经审查的响应 |
| --- | --- | --- |
| AZ 受损 | endpoint/客户健康度、节点状态、数据可用性 | 符合条件的 ARC/人工迁移以及已验证的故障后容量；仅靠拓扑分布不会疏散 Pod |
| 数据库延迟 | 查询/连接/复制指标 | 限制重试/并发；需要时遵循 writer 提升/runbook，而不是盲目切换到任意只读副本 |
| OOM/内存增长 | 限制、工作集、重启和应用证据 | 诊断/修复资源或应用行为；CPU HPA 不会自动修复 OOM |
| 流量激增 | 请求组合、积压、饱和度、客户错误 | admission/速率限制和已测试的扩缩；仅缓存具有安全的公共/个性化语义的数据 |

#### 熔断器和指标

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
  namespace: resilience-demo
spec:
  host: product-catalog.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```

代理池限制和异常检测不会预留后端容量。请根据源章节的超时/幂等性规则调优。以下查询要求**你的应用程序埋点**提供指定的 counter/classic-histogram 指标、job/namespace/status 标签，以及 kube-state-metrics。请初始化相关状态序列并验证抓取覆盖；EKS 不会自动提供这些指标。请求分母为零/没有样本属于证据不可用，不代表 100% 成功。Pod 指标会有意排除已完成/正在删除的 Pod，因此不是应用 SLI。

请求速率

```promql
sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
```

5xx 百分比

```promql
100 * sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
and on() (sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m])) > 0)
```

Classic histogram p99 秒数

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="product-catalog",namespace="resilience-demo"}[5m]))
)
```

活动测试 namespace 中 Ready Pod 的百分比，不是请求可用性

```promql
100 *
sum(
  kube_pod_status_ready{namespace="resilience-demo",condition="true"}
  and on (namespace,pod)
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
/
count(
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
```

#### 工作负载回滚和需单独审查的控制

```bash
# MUTATION: workload revision rollback only, after data/schema and GitOps review.
set -euo pipefail
: "${KUBE_CONTEXT:?Set the verified owned context}"
: "${REVIEWED_REVISION:?Set an inspected compatible Deployment revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout history deployment/product-catalog
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout undo deployment/product-catalog \
  --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/product-catalog --timeout=5m
```

回滚前请协调 GitOps 和 HPA 的所有权；rollout undo 不是数据库/PVC 回滚，也不是 EKS 控制平面降级。将 minReplicas 提到 100 不会暂停 HPA。需要时请使用 HPA 行为策略和有记录的恢复计划。Feature flag 需要真实且经过身份验证的管理 API/SDK，以及经过审计的目标 flag；此处不假设存在通用的未认证禁用 URL。

对于 CloudFront，请先将现有完整配置和 ETag 获取到私有文件中：

```bash
# Read-only preparation; output can include sensitive origin configuration.
set -euo pipefail
umask 077
: "${CF_DIST_ID:?Set the exact owned CloudFront distribution ID}"
test ! -e cloudfront-current-private.json
aws cloudfront get-distribution-config --id "$CF_DIST_ID" > cloudfront-current-private.json
```

检查缓存策略、cookie、授权和个性化内容。修改必须包含完整有效的 DistributionConfig 和匹配的 IfMatch ETag；update-distribution 没有 --default-cache-behavior 这类快捷参数。请单独准备并审查完整配置，等待部署完成，并保留恢复计划。不要对事务性/用户特定的响应设置一律 24 小时的 TTL。

原定的 D-14 基础测试、D-7 game day、D-3 最终验证/预扩容和 D-Day 监控日程仍只是计划示例；本次未验证任何运行时结果。

[CloudFront 更新 API](https://docs.aws.amazon.com/cli/latest/reference/cloudfront/update-distribution.html) · [HPA 行为](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [kube-state-metrics Pod 指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)

</details>
