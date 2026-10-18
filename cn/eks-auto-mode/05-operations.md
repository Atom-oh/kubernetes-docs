# 运维与管理

> **支持的版本**：EKS Auto Mode GA；示例基线 EKS 1.36
> **最后更新**：2026年9月12日

Day-2 运维必须区分期望容量、节点生命周期、应用可用性以及实际收集到的信号。以下示例是受控实验室配置，并非经过测试的生产运行手册。本次审计未更改任何云资源，也未执行任何实时节点/Pod 操作。

NodePool 清单已使用已发布的 Karpenter 1.14.1 结构化架构进行检查。工作负载示例通过了 Kubernetes 1.36.2 结构化检查和 Restricted Pod Security 策略检查；已验证 nginx 镜像标签/索引摘要及文档所述的非 root 布局。镜像运行时拉取、IAM、网络和应用行为仍需在你的环境中验证。

## 确认运维环境

使用临时凭证和预期的 kubeconfig。此只读保护措施会比较账户和直接 API 端点；如果 kubeconfig 使用了有意配置的代理，应单独审查，而不是绕过不匹配问题。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${AWS_REGION:?Set the cluster region}"
: "${CLUSTER_NAME:?Set the intended cluster name}"
: "${KUBECONFIG:?Set the reviewed kubeconfig path}"
export KUBE_CONTEXT="${KUBE_CONTEXT:-$CLUSTER_NAME}"
check_account() {
  local account
  account=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$account" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch; stop.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/auto-ops.XXXXXXXX")
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,endpoint:endpoint}' --output json > "$WORK_DIR/cluster.json"
endpoint=$(kubectl --context "$KUBE_CONTEXT" config view --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$WORK_DIR/cluster.json" >/dev/null
printf 'Private diagnostic directory: %s\n' "$WORK_DIR"
```

这些清单假定使用经过审查的 `default` NodeClass。仅选择所需示例，有意替换资源名称/网络标识符，并审查最终容量和成本。实验室节点池使用 `ops-lab` 污点，工作负载使用匹配的容忍度/节点池选择器；这些是放置控制措施，并非租户安全边界。

## 预算是叠加的，而非相互覆盖

每个适用的 NodePool 预算都会影响允许中断数量的最小值。添加计划为 `30%` 的预算，不能让始终生效的 `10%` 预算变得更宽松。百分比会向上取整，删除或未就绪的节点会减少剩余允许数量。

此明确的日历使用 30% 上限、10% 工作日上限和一个工作时段内的单节点上限。Karpenter 计划使用 UTC：

| 条目 | UTC 计划 | 预期时段 |
|-------|--------------|-----------------|
| 30% | 始终 | 外层上限 |
| 10% | 周日到周四 15:00，持续 24h | 首尔时间周一到周五的日历日 |
| 1 个节点 | 周一到周五 00:00，持续 9h | 首尔时间 09:00–18:00 工作时段 |
| 0 个节点 | 每月 1 日 00:00，持续 24h | 明确的 **UTC** 月度冻结期 |

对于 20 个其他方面均正常的节点，此示例允许周末发生六次新的自愿中断、工作日非工作时段发生两次、工作时段内发生一次，冻结期内则为零。这些是示例策略选择，并非普遍适用的生产建议。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-calendar
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 30%
    - nodes: 10%
      schedule: 0 15 * * sun-thu
      duration: 24h
    - nodes: '1'
      schedule: 0 0 * * mon-fri
      duration: 9h
    - nodes: '0'
      schedule: 0 0 1 * *
      duration: 24h
  limits:
    cpu: '100'
    memory: 400Gi
```

此前每小时 `9-18`/`9-21` 的 cron 范围和重复的 48 小时周末窗口，彼此重叠，超出了各自声明的时段。计划用于启动一个时间窗口；它不是一个小时列表，不应在长窗口内每到指定小时就重新启动窗口。

## 替换与应用可用性

一个节点的预算会限制适用的正常退出操作速率，但不能保证过期、中断或修复按顺序发生。`expireAfter` 并非最短运行时间承诺，修改它也不会重写现有 NodeClaims。Auto Mode 的默认过期/宽限行为和最长生命周期仍然适用。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-rolling
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 2m
    budgets:
    - nodes: '1'
  limits:
    cpu: '100'
    memory: 400Gi
```

空节点整合策略不会禁用漂移或过期。`do-not-disrupt` 并不保证可以无限期保留：Node 和 Pod 控制措施的作用范围不同，显式/默认终止宽限期也会影响阻塞中的 Pod 对漂移和最终终止的影响。将其用于维护窗口前，请查看[中断指南](https://karpenter.sh/v1.14/concepts/disruption/)。

### PDB 示例

以下命名空间将 Restricted 策略固定到经过审查的 Kubernetes 版本。镜像以 UID/GID 101 运行，监听 8080，并将 `/tmp` 用作 PID/临时路径；即使容器根文件系统为只读，它也需要可写的 emptyDir。该镜像的停止信号为 SIGQUIT。这些细节不能与以 root 运行、监听 80 端口的 nginx 镜像互换。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ops-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: ops-lab
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: web-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: ops-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-calendar
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

期望有五个健康副本时，`minAvailable: 3` 允许最多驱逐两个 Pod，但仍受其他约束影响。`maxUnavailable: 1` 是另一种限制更严格的选择，并非等价写法。

PDB 使用健康/Ready Pod 约束 Eviction API 的决策；它不会自动创建副本，也无法防范所有故障或直接删除操作。百分比值会向上取整：六个副本的 `minAvailable: "80%"` 要求五个健康副本，而一个副本的 `maxUnavailable: "30%"` 预算可能允许驱逐这一个副本。

对于有状态系统，应依据应用实际的仲裁和就绪语义。对于三投票者的多数派系统，两个健康成员可能足够；五投票者系统则需要三个。没有一个通用的 `minAvailable: 2` 建议适用于所有有状态工作负载。单例 PDB 可以有意阻止自愿清空节点，但无法实现高可用性。

## AZ 放置不等于保证容量或故障转移

动态节点池的 `limits.cpu` 是总量上限，并非每个 AZ 的最低容量。示例列出了可能的 AZ，但哪些 AZ 符合条件取决于 NodeClass 子网、容量和调度约束。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ops-multi-az
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
        - ap-northeast-2b
        - ap-northeast-2c
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: high-availability-app
  namespace: ops-lab
spec:
  replicas: 6
  selector:
    matchLabels:
      app: ha-app
  template:
    metadata:
      labels:
        app: ha-app
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: ha-app
        minDomains: 2
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: ha-app
      containers:
      - name: app
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: ops-multi-az
      tolerations:
      - key: ops-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
```

六个副本本身并不能证明已实现 3 个 AZ × 每个 AZ 2 个副本的布局。此示例要求至少两个符合条件的域；只有在评估了实际子网覆盖范围和故障策略后，才应进行调整。AZ 受损时，硬性的 `DoNotSchedule` 约束可能导致 Pod 保持 Pending 状态。

如果要求每个节点恰好运行一个副本，可以将以下 affinity 片段添加到经过审查的 Pod 模板中。使用此约束时，九个副本至少需要九个符合条件的节点；若没有相应的拓扑和容量，这仍不能证明具备跨三个 AZ 的可用性。

```yaml
podAntiAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchLabels:
        app: ha-app
    topologyKey: kubernetes.io/hostname
```

Active-active/standby 设计还需要考虑应用状态、健康检查以及流量/故障转移控制。ARC zonal shift 支持 Auto Mode，可避免在受损 AZ 中新增容量；autoshift 需要单独配置。它无法让绑定到某个 AZ 的卷或硬性放置约束具备跨 AZ 移动能力。

### 现有容量预留

将节点池命名为 `reserved-capacity`、允许 On-Demand 并设置 CPU 上限，并不会创建容量预留。要使用已获批准的现有容量预留，请在自定义 NodeClass 中选择它，并允许 `reserved` 容量。替换示例预留 ID，并验证账户、AZ、类型、状态、权限以及可用的预留容量。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: reserved-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  capacityReservationSelectorTerms:
  - id: cr-0123456789abcdef0
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: reserved-capacity
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: reserved-nodeclass
      taints:
      - key: ops-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        example: ops-lab
  limits:
    cpu: '100'
    memory: 400Gi
```

这些清单不会创建 EC2 容量预留，也不会创建固定数量的节点。即使未使用，容量预留也可能产生费用。如果要让期望节点数不依赖 Pod 需求，Auto Mode 支持使用 `spec.replicas` 的静态节点池，但其限制、权重、整合和扩缩容语义各不相同；请参阅静态容量参考。即使设置了期望数量，仍需成功完成预置并确保容量健康。

## 监控必须与信号发布方匹配

EKS 控制平面指标、已配置的 Container Insights、自行管理的 Prometheus exporter 以及 Auto Mode 组件日志是不同的接口。不要假设 CloudWatch 中会自动填充包含旧版 `karpenter_*` 名称的 `Karpenter` 命名空间。

Auto Mode 托管的计算/存储/负载均衡器/IPAM 日志使用单独配置的 Vended Logs 传送机制。基本控制平面日志记录并不能开启所有托管组件日志。选择范围明确的时间段，并验证 IAM、目标位置和费用。

### 根据实际指标元数据构建仪表板

对于 `AWS/EKS` 控制平面命名空间，首先发现针对经过审查的集群实际返回了哪些指标：

```bash
check_account
aws cloudwatch list-metrics --region "$AWS_REGION" --namespace AWS/EKS \
  --dimensions "Name=ClusterName,Value=$CLUSTER_NAME" --output json \
  > "$WORK_DIR/metric-catalog.json"
jq '.Metrics | to_entries | map({index:.key,metric:.value})' "$WORK_DIR/metric-catalog.json"
```

选择目录中的确切索引和该指标适用的已记录统计量。以下本地生成器会保留真实命名空间/维度并包含 widget 区域。如果目录条目缺失或与集群不符，它会拒绝生成，而不是创建虚构的指标面板。

```bash
: "${METRIC_INDEX:?Choose an exact entry from the captured catalog}"
: "${METRIC_STAT:?Choose the documented statistic for that metric, such as Maximum}"
export METRIC_INDEX METRIC_STAT AWS_REGION CLUSTER_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
folder = Path(os.environ["WORK_DIR"])
metrics = json.loads((folder / "metric-catalog.json").read_text())["Metrics"]
index = int(os.environ["METRIC_INDEX"])
if index < 0 or index >= len(metrics):
    raise SystemExit("Metric is absent; verify collection instead of creating an empty widget")
metric = metrics[index]
if metric["Namespace"] != "AWS/EKS" or not any(
    d["Name"] == "ClusterName" and d["Value"] == os.environ["CLUSTER_NAME"]
    for d in metric["Dimensions"]
):
    raise SystemExit("Metric catalog entry does not match the reviewed cluster")
stat = os.environ["METRIC_STAT"]
if stat not in {"Average", "Sum", "Minimum", "Maximum", "SampleCount"}:
    if not re.fullmatch(r"p[0-9]+(?:\.[0-9]+)?", stat) or not 0 <= float(stat[1:]) <= 100:
        raise SystemExit("Unsupported statistic for this template")
series = [metric["Namespace"], metric["MetricName"]]
for dim in sorted(metric["Dimensions"], key=lambda d: d["Name"]):
    series.extend([dim["Name"], dim["Value"]])
body = {"widgets": [{"type": "metric", "x": 0, "y": 0, "width": 12, "height": 6,
    "properties": {"title": metric["MetricName"], "region": os.environ["AWS_REGION"],
                   "view": "timeSeries", "metrics": [series], "stat": stat, "period": 60}}]}
(folder / "dashboard.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

通过已批准的工作流创建/更新仪表板之前，请先审查 `dashboard.json`。目录中存在某个指标，并不能证明其在所有时间范围内都有数据点。节点池数量、预置延迟和应用 SLO 需要由实际的数据发布方/监测工具提供；不能假设 Container Insights 单独就会生成所有信号。

## Kubernetes 结构化诊断

使用 NodeClaim 条件，而不是不存在的 `.status.phase`；也不要把每个 Pending Pod 都视为容量请求：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodepools -o json |
  jq '[.items[] | {name:.metadata.name,limits:.spec.limits,resources:.status.resources,
      requirements:.spec.template.spec.requirements,disruption:.spec.disruption,
      conditions:[.status.conditions[]? | {type,status,reason,observedGeneration}]}]'
```

```bash
: "${WORKLOAD_NAMESPACE:?Select the workload namespace}"
: "${POD_NAME:?Select the Pod}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pod "$POD_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,phase:.status.phase,
       nodeSelector:.spec.nodeSelector,affinity:.spec.affinity,tolerations:.spec.tolerations,
       conditions:[.status.conditions[]? | {type,status,reason,lastTransitionTime}],
       containers:[.status.containerStatuses[]? |
         {name,ready,restartCount,waitingReason:.state.waiting.reason}]}'
```

要查看节点分布，请解析结构化字段，而不是人类可读表格中的某一列。此命令会统计活动 Pod 对象，包括已分配但尚未就绪的 Pod，并单独列出尚未分配的对象：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
  jq '[.items[] | select(.status.phase != "Succeeded" and .status.phase != "Failed") |
       {node: (.spec.nodeName // "(unscheduled)"), namespace: .metadata.namespace, pod: .metadata.name}] |
      group_by(.node) | map({node: .[0].node, activePodObjects: length})'
```

仅当 metrics API 已配置且运行正常时，才使用 `kubectl top`。查询失败并不能证明 metrics-server 不存在。检查事件原因和托管计算日志，确认是否确实存在实例类型不兼容、NodeClass 未就绪、IAM 或网络问题等故障。缩短 `consolidateAfter` 并不能加快 Spot 中断恢复。

### PDB 允许中断数不是合规性结论

`disruptionsAllowed` 为零可能是有意设计且运行正常的状态。解读前，请检查代次是否为最新，并比较当前健康状态与期望健康状态：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[] | {
    namespace: .metadata.namespace, name: .metadata.name,
    currentHealthy: .status.currentHealthy, desiredHealthy: .status.desiredHealthy,
    disruptionsAllowed: .status.disruptionsAllowed,
    assessment: (if .status.observedGeneration != .metadata.generation
                    or .status.currentHealthy == null or .status.desiredHealthy == null
                    or .status.disruptionsAllowed == null
                  then "UnknownOrStale"
                  elif .status.currentHealthy < .status.desiredHealthy then "BelowDesiredHealthy"
                  elif .status.disruptionsAllowed == 0 then "HealthyNoVoluntaryEvictions"
                  else "EvictionsPermitted" end)
  }]'
```

在了解工作负载可用性要求和恢复计划之前，不要删除或放宽阻止操作的 PDB。

### Node 对象的年龄

Node 对象的创建时间不等于 EC2 启动时间或 AMI 补丁版本的年龄。请根据策略选择诊断阈值；之前固定使用“超过完整七天”的脚本既截断了时间，也假定存在不恰当的通用限制。

```bash
: "${MAX_NODE_OBJECT_AGE_HOURS:?Set a reviewed diagnostic threshold in hours}"
export MAX_NODE_OBJECT_AGE_HOURS
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
  jq '{items:[.items[] | {name:.metadata.name,createdAt:.metadata.creationTimestamp}]}' \
  > "$WORK_DIR/node-times.json"
python3 - <<'PY'
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
limit = float(os.environ["MAX_NODE_OBJECT_AGE_HOURS"])
if not math.isfinite(limit) or limit <= 0:
    raise SystemExit("Set a finite positive threshold")
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-times.json").read_text())["items"]:
    result = {"node": item["name"], "thresholdHours": limit}
    try:
        created = datetime.fromisoformat(item.get("createdAt").replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("timestamp is not usable")
        hours = (now - created).total_seconds() / 3600
        result.update(nodeObjectAgeHours=round(hours, 3), exceedsThreshold=hours > limit)
    except (ValueError, TypeError, AttributeError):
        result["assessment"] = "UnknownTimestamp"
    rows.append(result)
print(json.dumps(rows, indent=2))
PY
```

未知或未来的时间戳不会被报告为健康状态。诊断节点轮换是否逾期之前，请对照实际 NodeClaim 策略、镜像信息以及 AWS 维护/安全背景进行判断。此本地报告不会创建 CloudWatch 告警。

## 安全配置

Auto Mode 会选择其托管的 Bottlerocket 镜像，并使用固定的 IMDSv2/hop-limit 设置。此前的 `amiFamily`、`metadataOptions`、`blockDeviceMappings` 和格式错误的 KMS ARN 示例，并不是有效的 Auto Mode NodeClass 配置。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ops-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
```

请检查配置文件中的节点角色/访问条目、实际私有路由和安全组规则。仅凭标签无法证明网络受到限制。节点根卷/数据 EBS 加密并不意味着应用 PVC 已加密。对于客户管理的密钥或 CA 捆绑包，请按照[NodePool 配置](./02-nodepool-configuration.md)中的有效 `ephemeralStorage.kmsKeyID`/证书流程操作，并审查 IAM 和密钥策略。

Restricted 命名空间示例要求工作负载使用兼容的安全上下文。不要将具有主机访问权限的节点级监控代理强行放入该命名空间，也不要为了让代理运行而禁用集群范围的安全设置；请单独审查收集器的权限和命名空间策略。

## 可选 Prometheus 查询和告警

这些示例假定**只有一个集群**，已安装 kube-state-metrics 收集器，并且有 Linux node-exporter 指标。使用之前：

- 在 kube-state-metrics 中将 Node 标签 `karpenter.sh/nodepool` 和 `eks.amazonaws.com/compute-type` 加入允许列表。
- 确保 CPU 序列具有正确映射的 `node` 标签。并非每种 node-exporter 抓取配置都会自动提供此标签。
- 在联接/计数之前，对 kube-state-metrics 副本进行去重。每个节点必须只有一个当前 NodePool 标签。
- 对于多个集群，应在所有来源中保留真实的集群标签，并将其纳入每个分组和联接中。

节点查询会筛选 Auto Mode 节点；Pod pending/unschedulable 信号适用于整个集群，归因到 Auto Mode 前需要先进行诊断。下面的 CPU 表示每个节点的**非 idle 时间**，而不是资源请求比例或按容量加权的节点池平均值。缺少序列并不意味着使用量自动为零。

```promql
# nodes_by_pool
count by (label_karpenter_sh_nodepool) (max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))

# cpu
100 * (1 - avg by (node) (rate(node_cpu_seconds_total{mode="idle",node!=""}[5m])))
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# pending
sum(max by (namespace, pod, uid) (kube_pod_status_phase{phase="Pending"}))

# unschedulable
sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable))

# age
((time() - max by (node) (kube_node_created)) / 86400)
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})

# not_ready
max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})
* on (node) group_left (label_karpenter_sh_nodepool)
max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"})
```

安装 Prometheus Operator 后，将以下规则放入由 Prometheus 实例选择的命名空间中，并确保其匹配 `ruleSelector`。阈值和持续时间仅供参考。这些规则不能证明每一种预置失败都会体现在终止计数器中。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: auto-ops-example
  namespace: monitoring
spec:
  groups:
  - name: auto-ops-example
    rules:
    - alert: ReportedUnschedulablePods
      expr: sum(max by (namespace, pod, uid) (kube_pod_status_unschedulable)) > 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Reported unschedulable Pods exceed the example threshold
    - alert: AutoNodeNotReady
      expr: '(max by (node) (kube_node_status_condition{condition="Ready",status=~"false|unknown"})

        * on (node) group_left (label_karpenter_sh_nodepool)

        max by (node, label_karpenter_sh_nodepool) (kube_node_labels{label_karpenter_sh_nodepool!="",label_eks_amazonaws_com_compute_type="auto"}))
        == 1'
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A registered Auto Mode node is not Ready
```

## 审查频率

| 频率 | 审查证据 |
|---------|--------------------|
| 每日 | 持续的调度/NodeClaim 错误、Node 条件、工作负载健康状况、当前 PDB 允许中断数和收集器数据新鲜度 |
| 每周 | 中断/漂移事件、观测到的节点/对象年龄、实际容量/Spot 分布、资源请求和账单趋势 |
| 变更前/每月变更审查 | IAM/网络/存储策略、兼容的软件和镜像更新、经过测试的恢复流程、配额和未来工作负载需求 |

此前提出的“Pending 0–5”、“CPU/内存低于 80%”、“启动时间低于 90 秒”、“99.9% 可用性”和响应时间范围都属于未经验证的规划启发式指标，并非 Auto Mode 的正常范围或默认 SLO。应根据应用目标和实测行为定义阈值，不要将每次状态转换或 PDB 允许中断数为零都标记为违规。

## 参考资料

- [Auto Mode NodePool 行为](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [中断预算、漂移和终止](https://karpenter.sh/v1.14/concepts/disruption/)
- [配置 PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [拓扑分布约束](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Auto Mode 静态容量](https://docs.aws.amazon.com/eks/latest/userguide/auto-static-capacity.html)
- [NodeClass 和容量预留选择器](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [EKS ARC zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift-enable.html)
- [托管组件日志传送](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [控制平面指标和 CloudWatch](https://aws.amazon.com/blogs/containers/proactive-amazon-eks-monitoring-with-amazon-cloudwatch-operator-and-aws-control-plane-metrics/)
- [CloudWatch 仪表板结构](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Dashboard-Body-Structure.html)
- [Kube-state-metrics Node 指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Kube-state-metrics Pod 指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [NGINX 非特权镜像](https://github.com/nginx/docker-nginx-unprivileged)

< [上一页：Spot 策略](./04-spot-strategies.md) | [目录](./README.md) | [下一页：成本管理](./06-cost-management.md) >
