# 节点生命周期管理

> **支持版本**：EKS Auto Mode GA；示例按 EKS 1.36 审阅
> **最后更新**：2026 年 9 月 12 日

过期策略、受管镜像更新和应用恢复是节点生命周期中的不同环节。Kubernetes Node 对象创建时间较近，并不能证明所有 CVE 都已修补，也不能证明工作负载符合要求。这些示例依据官方资料及本地 schema/fixture 审阅；未执行实际节点轮换、云端变更或基准测试。

## 过期策略与 Auto Mode 生命周期上限

`spec.template.spec.expireAfter` 根据年龄决定由该模板创建的 NodeClaim 何时过期。早期 Provisioner 使用的 `ttlSecondsUntilExpired` 字段不适用于这些 `karpenter.sh/v1` NodePool。

请区分以下三个设置：

| 概念 | Auto Mode 行为 |
|---------|--------------------|
| 默认过期时间 | AWS 文档规定为 **336h（14 天）**，不是 7 天或 21 天 |
| 终止宽限期 | 如果 NodePool 未设置，Auto Mode 会在 NodeClaim 上默认为 **24h**；即使池配置中看不到，也要检查 claim |
| 受管实例最长生命周期 | AWS 强制实施 **21 天（504h）**；这不保证节点一定会保留到该时限 |

不得用上游 Karpenter 的 720h 默认值替代 Auto Mode 默认值。较长的时长或上游 `Never` 语法都不能让 Auto Mode 受管实例无限期保留。不要把 504h 再加上较长的驱逐时间，误当成延长 AWS 生命周期上限的方法。

运行下方只读命令前，请先按照 [运维指南](./05-operations.md) 中的说明设置账户/上下文保护和私有 `WORK_DIR`。示例池假定使用经过审查的 `default` NodeClass。这些配置范围受限，并带有 taint；必须匹配工作负载的 selector/toleration，并测试应用恢复。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: with-expiration
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
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

### 过期实际会触发什么

过期是一个**强制性中断触发条件**。NodeClaim 达到策略规定的年龄后，系统便开始终止和驱逐流程，不会等待预先创建的替代节点变为 Ready。NodePool disruption budget 不会限制过期触发。工作负载控制器和资源供应流程可能按需创建替代容量；此处不能保证旧的五步顺序“新节点 Ready 后再驱逐”。

终止控制器会阻止新的普通调度，尝试通过 Eviction API 驱逐，并处理卷分离和实例终止。PDB 和 Pod `do-not-disrupt` 可以影响驱逐，但终止宽限期限以及 AWS 生命周期上限意味着它们不能提供无限期可用性保护。Pod 关停宽限期和节点终止宽限期是不同设置。本地/临时存储上的数据必须有恢复方案。

修改池的 `expireAfter` 不会改写现有 NodeClaim；这可能使其产生 drift，且新策略适用于替代 claim。其他中断方式可能让节点更早结束生命周期。一个节点的 budget 不能让多个同时到期的节点依次终止。

### 选择时长

此前按环境列出的 24h、48h、72h、168h 和 336h 示例是策略选择，不是 AWS 生产默认值，也不是 PCI/HIPAA/SOC2 要求的轮换间隔。此前 504h 的开发环境示例代表服务上限，并不意味着建议设置 `expireAfter` 再加驱逐时间。

应根据补丁紧急程度、工作负载检查点、缓存预热、副本/仲裁行为、可用容量和恢复测试来选择策略。频繁轮换可能增加镜像拉取、重新调度和计费的恢复工作；它本身不会提高某个 Spot 实例被 EC2 中断的概率，也不保证新发布的补丁已可用。

## 受管 AMI 与 NodeClass 配置

Auto Mode 使用 AWS 受管的 **Bottlerocket 变体**。它不提供 AL2023/Bottlerocket `amiFamily` 切换、自定义 `amiSelectorTerms`、任意 `userData`、SSH 或 SSM Session Manager 访问。这些接口不能从自管 Karpenter 的 EC2NodeClass 或普通受管节点组配置中照搬过来。

下面受支持的 NodeClass 用于配置存储/网络身份；它不会选择或固定 AMI：

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: lifecycle-nodeclass
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

请检查其实例配置文件角色/access entry 以及实际选中的子网/安全组，然后只从预期的池引用 `lifecycle-nodeclass`。Auto Mode 管理 IMDSv2/hop-limit 设置，不能用 `metadataOptions` 覆盖。使用 `ephemeralStorage`，而非 `blockDeviceMappings`；节点根卷/数据卷启用 EBS 加密并不代表应用 PVC 已加密。受支持的密钥/证书设置请参阅 [NodePool 配置](./02-nodepool-configuration.md)。

### 历史操作系统对比不是 Auto Mode 的选择菜单

AL2023 是包含部分 Fedora 上游组件的通用 Amazon Linux 发行版，不等同于 RHEL。普通 AL2023 主机或独立管理的 Bottlerocket 主机，与受到限制的 Auto Mode 节点具有不同的管理选项。Auto Mode 也通过其受管镜像支持 GPU 工作负载，因此“GPU 必须使用 AL2023”在此并不成立。

原有 AL2023 40–60s、Bottlerocket 20–30s/20–40s 的启动时长范围，以及测验中的 20–40s 对 15–25s 范围，都没有经过验证的测量来源。它们保留为历史示例，不代表操作系统速度排名或这些清单的预测值。必须分别测量镜像拉取、架构、实例类型和工作负载就绪时间。

## Drift 与受管镜像更新

AWS 文档显示 Auto Mode AMI 大约每周发布，并允许通过 drift 替换符合条件的节点。这个频率不是针对每个 CVE 的补丁 SLA。另一个 EKS 优化 AMI 系列发布新版本，也不会自动构成 Auto Mode 镜像更新。

| 变更或观察结果 | 正确解释 |
|-----------------------|------------------------|
| Auto Mode 受管 AMI 更新 | 可能使现有 claim 出现 drift；检查实际 condition 和 rollout 状态 |
| NodePool requirement 变更 | 并非每次变更都会导致 drift；放宽兼容的允许值后，现有节点仍可能符合要求 |
| `expireAfter` 模板变更 | 现有 claim 保留已存储的值；替代 claim 使用更新后的策略 |
| weight、limits 或 disruption 设置 | 属于行为设置，不会一概触发 drift |
| NodeClass 期望状态变更 | 使用受支持字段并观察受管控制器；外观标签不能保证触发紧急补丁 |
| `amiFamily` / `blockDeviceMappings` 变更 | 这些不是 Auto Mode NodeClass 的有效字段 |

请检查 NodeClaim 的 `Drifted` condition。哈希注解不是布尔型 drift 状态；未报告 condition 也不能证明“没有 drift”。读取 reason/transition/generation 信息，并与当前资源状态对照：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
jq '[.items[] | {
  name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
  createdAt:.metadata.creationTimestamp,deletionTimestamp:.metadata.deletionTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
  imageID:.status.imageID,
  drift:([.status.conditions[]?|select(.type=="Drifted")|
    {status,reason,lastTransitionTime,observedGeneration}] |
    if length == 0 then {status:"NotReported"} else .[0] end),
  conditions:[.status.conditions[]?|{type,status,reason,lastTransitionTime,observedGeneration}]
}]'
```

Drift 是一种平缓中断方式，受适用的 budget、调度可行性和驱逐限制约束。下面的配置允许一次适用的自愿中断，并仅在工作日 UTC 00:00–08:00 暂停 **drift**，对应首尔时间 09:00–17:00。旧的 `0 9-17`/`0 9-18` 每小时计划会重新开始，形成长时间重叠窗口。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: controlled-drift
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
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
    - nodes: '1'
    - nodes: '0'
      schedule: 0 0 * * mon-fri
      duration: 8h
      reasons:
      - Drifted
  limits:
    cpu: '100'
    memory: 400Gi
```

这不会暂停过期、EC2 中断或修复。`consolidateAfter` 影响 consolidation，不是 AMI 补丁期限。Pod 与 Node 上的 `do-not-disrupt` 注解也不同；评估 Pod 注解能否阻止 drift 时，要考虑 Auto Mode 的默认 NodeClaim 宽限期。

## 补丁与特殊手动恢复

AWS 管理节点操作系统/Auto Mode 组件补丁；应用/容器依赖项和工作负载安全仍由你负责。记录实际镜像信息、相关 AWS 发布说明/公告、rollout 进度和应用检查结果。较新的时间戳或 `SecurityPatch` 标签不能证明修复已包含在镜像中。

紧急修复时：

1. 确认所需的受管镜像/修复已可用于此集群，并确定受影响的工作负载。
2. 使用指定上下文，检查**单个 NodeClaim UID**、节点映射、池、当前 condition、PDB、数据持久性以及可用/可获取的备用容量。
3. 若受管 drift rollout 能满足要求，优先采用该方式。若必须手动替换，请使用经过审查的单资源维护流程，并先确认替代节点和应用已就绪，再处理下一个资源。
4. 每次变更后重新检查健康和镜像证据；如果状态未知、容量不足或应用回归，立即停止。

以下命令仅收集证据：

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```

`kubectl delete nodes -l ...` 是批量删除请求，不是顺序滚动更新。手动删除节点/claim 不受 NodePool budget 限制；`drain --delete-emptydir-data` 可能丢弃本地数据，而且单独执行 drain 并不能保证替代节点已存在。因此，旧测验中的无限制删除命令和通过修改标签“触发补丁”都不能作为紧急运行手册。

## Consolidation、Drift 与过期

| 机制 | 触发条件和控制方式 |
|-----------|---------------------|
| Consolidation | 基于请求/约束寻找成本更低且可行的放置；适用平缓中断控制 |
| Drift | 现有 claim 不再符合期望的受管状态；适用平缓中断控制 |
| 过期 | Claim 年龄达到已存储的策略；强制触发，不受 NodePool budget 限制 |

平缓中断控制器会先评估 drift，再评估 consolidation；过期则是独立的强制路径。不存在通用的“drift > 过期 > consolidation”优先级或“首个 condition 生效”契约。五天大的节点可能在七天过期前先 consolidation；八天大的过期节点也不必先满足利用率不足才开始终止。

以下是不同的实验室策略，不保证特定成本/安全结果：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-priority
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
      expireAfter: 336h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: security-priority
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
      expireAfter: 72h
      terminationGracePeriod: 24h
      taints:
      - key: lifecycle-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        lifecycle-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
```

`WhenEmpty` 会缩小 consolidation 的适用范围，但不会禁用 drift/过期。请根据选定的过期时间和宽限期协调应用行为；不能只凭策略名称推断可用性。

## Node 对象年龄与镜像证据

`Node.metadata.creationTimestamp`、NodeClaim 创建时间和 EC2 启动时间是不同的观测值。`Node.status.nodeInfo.osImage` 描述操作系统，不是 AMI ID。此前重复的 CREATED/AGE 时间戳列以及“安全补丁状态”年龄脚本都不能证明补丁状态。

先采集选定的 Node 字段，再计算可移植的小数年龄和明确分桶。无效、缺失、无时区或来自未来的时间戳都应视为未知：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '{items:[.items[] | {
  name:.metadata.name,uid:.metadata.uid,createdAt:.metadata.creationTimestamp,
  pool:.metadata.labels["karpenter.sh/nodepool"],
  osImage:.status.nodeInfo.osImage,kernelVersion:.status.nodeInfo.kernelVersion
}]}' > "$WORK_DIR/node-lifecycle.json"
```

```bash
python3 - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path
now = datetime.now(timezone.utc)
rows = []
for item in json.loads((Path(os.environ["WORK_DIR"]) / "node-lifecycle.json").read_text())["items"]:
    result = {"node": item["name"], "pool": item.get("pool")}
    try:
        created = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
        if created.tzinfo is None or created > now:
            raise ValueError("unusable timestamp")
        hours = (now - created).total_seconds() / 3600
        bucket = "<1d" if hours < 24 else "1d–<3d" if hours < 72 else "3d–<7d" if hours < 168 else ">=7d"
        result.update(nodeObjectAgeHours=round(hours, 3), bucket=bucket)
    except (KeyError, AttributeError, TypeError, ValueError):
        result["bucket"] = "UnknownTimestamp"
    rows.append(result)
summary = [{"bucket": bucket, "count": sum(row["bucket"] == bucket for row in rows)}
           for bucket in ("<1d", "1d–<3d", "3d–<7d", ">=7d", "UnknownTimestamp")]
print(json.dumps({"observedAt": now.isoformat(), "nodes": rows, "distribution": summary}, indent=2))
PY
```

分桶区间为 `[0,1)`、`[1,3)`、`[3,7)` 和 `>=7` 天；正好七天归入最后一档。成功返回但 Node 列表为空，可以与 API 错误区分开。该快照用于诊断，不是实时更新的仪表板，也不是补丁合规检查。

### Prometheus 与 Grafana

安装 kube-state-metrics，并将 `karpenter.sh/nodepool` 和 `eks.amazonaws.com/compute-type` 加入 allowlist。下面的**单集群**规则文件会对重复抓取去重，并将 Auto Mode 标签与 Node 创建时间 gauge 连接起来。多集群查询在每个分组/连接中都必须保留真实的集群标签。指标缺失或时间戳来自未来时，不能将其算作年龄为零的健康节点。

年龄告警保留了旧的十天阈值和三天标准差阈值，作为**示例审查信号**。它们不是 Auto Mode 默认值；混合池策略和正常自动扩缩都可能使年龄分布较宽。请将其作为 Prometheus rule 文件加载，或将 group 放在由 operator 选择的 PrometheusRule 的 `spec` 下：

```yaml
groups:
- name: node-lifecycle
  rules:
  - record: eks_auto:node_object_age_days
    expr: "(\n  ((time() - max by (node) (kube_node_created)) >= 0) / 86400\n) * on\
      \ (node) group_left (label_karpenter_sh_nodepool)\nmax by (node,label_karpenter_sh_nodepool)\
      \ (\n  kube_node_labels{label_karpenter_sh_nodepool!=\"\",label_eks_amazonaws_com_compute_type=\"\
      auto\"}\n)"
  - alert: ReviewNodeObjectAge
    expr: eks_auto:node_object_age_days > 10
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: Review this node against its actual lifecycle policy
  - alert: ReviewNodeAgeSpread
    expr: stddev(eks_auto:node_object_age_days) > 3
    for: 4h
    labels:
      severity: info
    annotations:
      summary: Age spread is a review signal, not proof of failed rotation
```

```promql
# median_object_age_days
quantile(0.5, eks_auto:node_object_age_days)

# mean_by_pool
avg by (label_karpenter_sh_nodepool) (eks_auto:node_object_age_days)

# oldest_five
topk(5, eks_auto:node_object_age_days)

# less_than_1d
sum((eks_auto:node_object_age_days >= bool 0) * (eks_auto:node_object_age_days < bool 1))

# 1d_to_under_3d
sum((eks_auto:node_object_age_days >= bool 1) * (eks_auto:node_object_age_days < bool 3))

# 3d_to_under_7d
sum((eks_auto:node_object_age_days >= bool 3) * (eks_auto:node_object_age_days < bool 7))

# 7d_or_more
sum(eks_auto:node_object_age_days >= bool 7)
```

`kube_node_created` 是时间戳 gauge，不是 histogram/counter。默认不存在 `kube_node_created_bucket`；`rate()` 加 `histogram_quantile()` 无法凭空生成节点年龄直方图。使用 `quantile()` 计算当前年龄中位数，并用显式布尔分桶绘制柱状图。如果有已观测节点但某个桶中没有节点，这些桶的查询和会返回零；没有输入时仍然没有结果。

| Grafana 面板 | 证据 |
|---------------|----------|
| 当前年龄分布 | 四个显式分桶查询 |
| 按池平均年龄/最老节点 | 标签连接以及 `avg` / `topk` |
| 接近过期的 claim | 实际 NodeClaim 创建时间和已存储的 `expireAfter`；仅凭 Node 年龄不足以判断 |
| 替换速率 | 已配置的事件/日志历史或经验证的计数器发布方，不能从当前对象数量推断 |
| 补丁 rollout | 受管镜像/发布信息、claim condition 和应用健康状况 |

## 参考资料

- [Auto Mode NodePool 默认值与终止宽限期](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode 安全与实例生命周期上限](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode 受管操作系统与责任](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [NodeClass 受支持配置](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Karpenter disruption、过期与 drift](https://karpenter.sh/v1.14/concepts/disruption/)
- [Kube-state-metrics Node 指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)
- [Prometheus 聚合运算符](https://prometheus.io/docs/prometheus/latest/querying/operators/)
- [AL2023 与 Fedora 的关系](https://docs.aws.amazon.com/linux/al2023/ug/relationship-to-fedora.html)

< [上一页：成本管理](./06-cost-management.md) | [目录](./README.md) | [下一页：工作负载优化](./08-workload-optimization.md) >
