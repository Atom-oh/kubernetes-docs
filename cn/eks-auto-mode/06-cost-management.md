# 成本管理与优化

> **支持的版本**：EKS Auto Mode GA；示例已针对 EKS 1.36 审核
> **最后更新**：2026 年 9 月 12 日

成本优化需要基于账单证据，比较完成的有用工作量。节点数量快照、较低的 CPU 使用率或宣传中的折扣，都不等于经测量确认的节省。本文示例已在本地依据源代码/schema/CLI 契约进行检查；未进行购买、云部署或实时账单查询。

## 账单包含哪些内容

计算 EKS 集群费用、EC2 使用费、**额外的 Auto Mode 费用**、EBS、负载均衡器、NAT/数据传输、可观测性以及其他工作负载服务费用。Auto Mode 计算费用按秒计费，最低计费时长为一分钟，且独立于 EC2 购买选项。EC2 Savings Plans/RI 折扣不会抵扣单独的 Auto Mode 费用。

### 2026 年 7 月 GPU 费用下调

AWS 的 7 月公告确认，自 7 月 1 日起，G 系列的 **Auto Mode 管理费**下调了 35%，P 系列/Trainium 的费用下调了 60%，并在受支持的区域自动生效。这只是该费用组成部分的降幅，并不意味着 GPU 总账单也按相同比例下降。公告还介绍了在配备本地 NVMe 的 GPU 实例上并行拉取/解包镜像，以及感知加速器的修复机制；但并未证明本示例的启动时间或应用恢复时间经过实际测量。

## 面向成本的放置

首先使用[运维](./05-operations.md)中的账户/API 端点防护措施和私有 `WORK_DIR`。这些示例假定已经审核 `default` NodeClass，且有可用的兼容容量。部署前请审核成本。

以下完整实验室工作负载修正了旧英文示例中缺失的选择器/镜像。它使用运维章节中已验证的非 root nginx 镜像、Restricted 命名空间以及池选择器/容忍度。示例请求值**并非实测使用量**。启用 ARM 前，请确认多架构镜像、库和应用行为。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cost-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
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
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
  namespace: cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cost-efficient
  template:
    metadata:
      labels:
        app: cost-efficient
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
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
        karpenter.sh/nodepool: cost-optimized
      tolerations:
      - key: cost-lab
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
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
```

同时允许 Spot 和 On-Demand 可以选择容量；Pod 的软性偏好不能保证特定比例，也不能保证立即回退。只有在区域、NodeClass、工作负载和实际库存允许的情况下，多样化实例类别才有帮助。单独的分层池可以表达中断、GPU 或架构约束，但不必要的碎片化可能降低装箱效率。

`WhenEmptyOrUnderutilized` 会根据请求和约束，评估是否能以更低成本重新调度 Pod；它不是 CPU 使用率阈值。`consolidateAfter` 是防抖时间，不是删除期限。PDB、亲和性和预算都可能阻止整合。池的 CPU/内存限制可以限制请求的基础设施增长；在快速预置期间，最终一致性可能导致暂时超出限制。它们不是货币预算，也不是账户级硬性支出上限。

## 将账单与运维指标分开

瞬时节点仪表值不是节点小时数；没有实例/费率/时间数据，节点小时数也不是美元金额。Auto Mode 不会自动发布旧示例中杜撰的 `Karpenter` CloudWatch 成本指标。应使用实际账单导出/Cost Explorer 了解费用，并使用配置好的采集器了解容量和性能。

### CloudWatch 账单概览

启用账单提醒/指标后，`AWS/Billing` 估算费用会在全球账户费用对应的 **us-east-1** 区域发布。这些是当月累计估算费用，不是每日 EC2 支出、EKS 集群总费用或预测值。付款账户具有其自身的关联账户范围。此本地仪表板定义使用了必需的货币维度和区域：

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "Account estimated charges, month to date (USD)",
        "region": "us-east-1",
        "view": "timeSeries",
        "metrics": [
          [
            "AWS/Billing",
            "EstimatedCharges",
            "Currency",
            "USD"
          ]
        ],
        "period": 21600,
        "stat": "Maximum"
      }
    }
  ]
}
```

使用 Cost Explorer/CUR 或 Data Exports 进行服务/集群费用分摊并查看每日变化。AWS Budgets 和 Cost Anomaly Detection 可以针对经过审核的货币阈值发送通知；它们不是硬性支出上限。节点数量警报是独立的容量防护措施，需要实际配置的发布器、维度和通知目标。旧警报引用了杜撰的指标和未定义的 SNS 资源。

### Kubecost

经审核的稳定版 chart/app 为 **3.2.4**，新仓库中的 chart 名称为 `kubecost`；不会将较新的候选版本作为盲目升级目标。版本 3 使用 FinOps agent 和基于 ClickHouse 的架构。不要复用旧的 `cost-analyzer` 仓库、`kubecostToken` 命令行示例或版本 2 Prometheus 部署的假设。

请准备特定版本的 values 文件，用于配置许可、集群标识、账单集成、限定范围的工作负载 IAM、身份验证、保留期和存储。Auto Mode 的 EBS StorageClass 使用 `ebs.csi.eks.amazonaws.com`；在需要时明确选择它，并审核加密设置。此 chart 包含持久数据保留/keep 注解，因此卸载并不能证明所有计费存储都已删除。保持访问私有，并审核采集器/遥测行为。安装前先在本地渲染：

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```

渲染命令不会安装任何内容。Pod/命名空间/闲置成本分摊需要 agent 和匹配的数据源；实际账单核对则需要 AWS 集成。仅靠命名空间标签不会生成账单数据。请核对闲置/共享成本、折扣和未分配成本，不要将不兼容的估算值相加。

## 衡量 Spot 节省

此结构化快照可处理零个节点、缺失标签和混合实例类型。它统计的是 **Auto Mode Node 对象**，而非计费小时数或支出：

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[] | {
  capacity: (.metadata.labels["karpenter.sh/capacity-type"] // "unknown"),
  instanceType: (.metadata.labels["node.kubernetes.io/instance-type"] // "unknown")
}] as $nodes |
{
  totalNodeObjects: ($nodes | length),
  byCapacityAndType: ($nodes | group_by([.capacity,.instanceType]) |
    map({capacity: .[0].capacity, instanceType: .[0].instanceType, count:length})),
  spotNodePercent: (if ($nodes|length) == 0 then null
    else 100 * ([$nodes[]|select(.capacity=="spot")]|length) / ($nodes|length) end)
}'
```

进行成本比较时，应使用相同的时段、区域/AZ、实例/OS/租赁方式、货币和有用工作量要求。历史 Spot 费率会随 AZ 和时间变化。如果 Pricing API 结果仅按实例类型选择，可能对应错误的区域/OS/租赁方式/产品；旧脚本还会屏蔽 API 错误。当前价格采样无法还原上个月的实际账单。

```text
reference_total = cost of the reviewed On-Demand counterfactual for the same useful work
actual_total = actual compute + Auto Mode fees + other allocated costs
               + recovery costs not already included in those billed components
savings_amount = reference_total - actual_total
savings_percent = 100 * savings_amount / reference_total  (reference_total > 0)
```

应将被中断/重试的工作和闲置/未利用的承诺计入一次，并避免重复计算恢复计算成本。参考值也需要包含对应的 Auto Mode/其他费用。假设 Spot 折扣为 70%，或当前 Spot 节点占比，都不能称为实际月度节省。请单独保留中断事件证据；猜测终止计数器的原因并不能衡量所有中断。

### Cost Explorer，只读

首先启用 AWS 生成的 **`aws:eks:cluster-name`** 标签；`eks:cluster-name` 不是文档中规定的账单键。该标签可归集参与计费的 EC2 实例费用，**但不包括控制平面费用或所有集群相关服务费用**。请审核账户/付款方范围和标签覆盖情况。Cost Explorer API 请求本身也可能产生费用。

选择明确的起始日期（包含）和结束日期（不包含）。此请求使用货币指标 `AmortizedCost`；不会将不兼容的 `UsageQuantity` 单位相加，也不会把节点比例当作美元金额。

```bash
: "${COST_START:?Set YYYY-MM-DD inclusive start}"
: "${COST_END:?Set YYYY-MM-DD exclusive end, no later than today UTC}"
export COST_START COST_END CLUSTER_NAME
python3 - <<'PY'
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
start, end = (date.fromisoformat(os.environ[key]) for key in ("COST_START", "COST_END"))
if not start < end <= datetime.now(timezone.utc).date():
    raise SystemExit("Require start < end <= today UTC")
request = {
    "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
    "Granularity": "DAILY",
    "Metrics": ["AmortizedCost"],
    "Filter": {"Tags": {"Key": "aws:eks:cluster-name", "Values": [os.environ["CLUSTER_NAME"]]}},
    "GroupBy": [{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"},
                {"Type": "DIMENSION", "Key": "PURCHASE_TYPE"}]
}
(Path(os.environ["WORK_DIR"]) / "ce-request.json").write_text(json.dumps(request, indent=2) + "\n")
PY
```

```bash
check_account
aws ce get-cost-and-usage --region us-east-1 \
  --cli-input-json "file://$WORK_DIR/ce-request.json" \
  --output json > "$WORK_DIR/ce-result.json"
jq '[.ResultsByTime[] | {period:.TimePeriod,estimated:.Estimated,groups:.Groups}]' \
  "$WORK_DIR/ce-result.json"
```

保留 `Estimated` 标志，并考虑退款、抵扣、折扣分摊和数据不完整的情况。按标签筛选的结果可能不包含未分配费用或未使用的承诺；在宣称总额或节省金额前，请将其与完整账单数据集核对。

## 资源适当调整

请使用固定版本的 [VPA 1.8.0 安装指南](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md)。该指南说明 VPA 1.8.x 与 Kubernetes 1.36–1.38 兼容，特定的原地功能还需要满足额外要求。旧的 `releases/latest/download/...` URL 并不是有效的 VPA 安装流程。应用集群范围的安装脚本前，请审核 CRD、RBAC、metrics-server 以及组件/证书配置；`Off` 模式仍需要正常工作的 recommender。

此资源针对同一命名空间中的实际实验室 Deployment：

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get vpa cost-app-vpa -o json |
  jq '{conditions:.status.conditions,recommendations:.status.recommendation.containerRecommendations}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get deployment cost-efficient-app -o json |
  jq '[.spec.template.spec.containers[] | {name,resources}]'
```

`Off` 模式会提供建议，但不会应用建议。请检查所有容器、建议条件/历史记录、工作负载季节性、启动峰值、延迟、CPU 节流以及内存/OOM 行为。`resourcePolicy` 中的上限并不能证明其建议适用于现有限制。VPA 不保证性能；此经审核版本还说明了其在 Pod 级资源配置方面的限制。

### 保留 Kubernetes 数量单位

`1` CPU 表示一个核心，而 `1m` 表示一个毫核。`1Gi` 是 1024Mi；删除后缀不会转换任何一种单位。请快照每个容器的原始请求/限制和使用量，而不要使用旧的 `sed`/`awk` 总数：

```bash
: "${WORKLOAD_NAMESPACE:?Select a namespace}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pods -o json |
  jq '[.items[] | {pod:.metadata.name,uid:.metadata.uid,
    podResources:.spec.resources,overhead:.spec.overhead,
    containers:[.spec.containers[]|{name,resources}],
    initContainers:[.spec.initContainers[]?|{name,restartPolicy,resources}]}]' \
  > "$WORK_DIR/pod-requests.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  top pods --containers > "$WORK_DIR/container-usage.txt"
```

指标查询必须成功；缺少数据不等于使用率为零。这两个快照并非同时采集，而且容器使用量不等同于调度器计算 Pod 请求时所考虑的全部因素：init/可重启 init 容器、Pod 级资源和开销也都很重要。

| 观察结果 | 审核操作 |
|-------------|---------------|
| 请求值似乎超过代表性使用量的 2 倍 | 降低之前先调查峰值和 SLO 余量；不能据此认定会自动节省 20–50% |
| 请求值在使用量的 2 倍以内 | 不能证明配置已达到最佳 |
| 使用量超过请求值 | 评估调度/余量；与 OOM 强制执行相关的是内存**限制**，而不只是请求值 |
| 限制值远高于请求值 | 评估突发/节流/OOM 策略；单独降低限制通常不会改善基于请求值的装箱 |

### 可选的 Prometheus 审核候选项

以下信息性规则假定**只有一个集群**，使用 kube-state-metrics 提供规范化的 CPU 核心/内存字节单位，并使用携带 namespace/Pod/container 标签的容器级 cAdvisor 使用量。CPU 查询需要聚合后的 `cpu="total"` 序列；请核实采集器的标签。规则会对采集器副本去重、排除基础设施 cgroup，并要求请求值分母大于零。对于多个集群，请在每个分组/连接中使用实际集群标签。缺失的序列不会被视为零。请审核过期序列/容器重新创建的影响，并查看具有代表性的历史数据。

持续一小时的 30% 利用率阈值仅是示例性审核触发条件，并非自动降低请求的建议，也不是实测节省。使用此资源前，请安装 Prometheus Operator 并匹配其命名空间/规则选择器：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-review-candidates
  namespace: monitoring
spec:
  groups:
  - name: cost-review-candidates
    rules:
    - alert: LowCpuRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])) and on (namespace,pod,container)\
        \ max by (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        cpu\",unit=\"core\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\n\
        ) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\
        \ > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}) unless\
        \ on (namespace,pod,container) max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m]))\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
    - alert: LowMemoryRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"}) and on (namespace,pod,container) max by\
        \ (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        memory\",unit=\"byte\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }))\n) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        })) > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }) unless on (namespace,pod,container) max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"})\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
```

## Savings Plans 和 Reserved Instances

| 选项 | 符合条件的使用量/范围 | 重要限制 |
|--------|------------------------|----------------------|
| Compute Savings Plans | 符合条件的 EC2 使用量，涵盖不同系列、大小、区域、OS 和租赁方式；也包括 Fargate/Lambda | 最高 66% 是宣传的上限，不是预期折扣 |
| EC2 Instance Savings Plans | 指定区域中的所选实例系列；在该范围内可灵活选择大小/OS/租赁方式 | 最高 72%；并非承诺使用某个确切实例大小 |
| EC2 RIs | 匹配的使用量；区域大小灵活性/交换规则取决于具体方案 | 现有匹配承诺仍可使 Auto Mode 受益 |
| Spot | 独立的 Spot 定价 | 不与 Savings Plans 叠加 |

符合条件的 Graviton 和 GPU EC2 使用量不需要特殊的“ARM Savings Plan”，也不受一概排除 GPU 的限制。SageMaker AI Savings Plans 覆盖 SageMaker 使用量，而不是仅仅因为 EC2 GPU 节点运行 ML 就覆盖该节点。Savings Plans 不预留物理容量；请单独评估容量预留。EC2 折扣不涵盖单独的 Auto Mode 费用。

根据持续、符合条件且未覆盖的每小时使用量，按**适用 Savings Plans 费率的美元/小时**确定承诺金额。如果基准值已排除 Spot，就不要再乘以 `(1 - Spot%)`。请考虑现有 RI/SP 覆盖、未来的资源适当调整/架构变更、共享设置、季节性和未使用承诺。较低的 EC2 费率或较少的节点数本身不足以确定安全的购买金额。

```bash
check_account
aws ce get-savings-plans-purchase-recommendation --region us-east-1 \
  --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT --lookback-period-in-days THIRTY_DAYS \
  --output json > "$WORK_DIR/savings-plan-recommendation.json"
```

此命令会获取建议，不会执行购买。30 天回溯期是可选的 API 参数；做决定前，请将其与更长且具有代表性的历史数据进行比较。

原先关于 Compute 覆盖率 60–70%/70%、EC2 Instance 覆盖率 30–40%、On-Demand 覆盖率 50%，以及 Spot 40–60% / 已覆盖 30–40% / 未覆盖 10–20% 的图表，都是**未经验证的规划示例**，不是普遍适用的累加目标。工作负载运行在 Spot 或 On-Demand 容量上；Savings Plans 描述的是符合条件使用量的账单覆盖情况，并不是第三种节点类型。

## 成本归因

使用有效的 NodeClass 身份/网络选择器和经批准的标记权限。自定义 NodeClass 需要其节点角色访问条目。标签用于描述资源；它们不会创建网络隔离，也不会自动覆盖所有依赖服务。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
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
  tags:
    Environment: lab
    Team: platform
    Project: web-services
    CostCenter: CC-12345
    Application: cost-lab
    ManagedBy: eks-auto-mode
```

请在预期的池中明确引用 `tagged-nodeclass`，以使用此示例。`amiFamily: AL2023` 不是 Auto Mode NodeClass 字段。请核实实际资源上的标签，并在 Billing 中启用相关键。用户定义的键可能需要最多 24 小时才会显示为可启用状态，启用本身还可能再花费最多 24 小时；报表数据的新鲜度则是另一回事。不要承诺所有数据都会在恰好 24 小时后出现。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: team-a
    environment: production
```

命名空间标签可用于 Kubernetes 分摊工具；它们不会自动传播为 AWS 成本分配标签。基于标签的 EC2 归因也不能替代对共享/控制平面/存储/网络成本的分摊。

## 优化清单与先前的数值示例

将兼容实例多样性、面向工作负载的 Spot 使用、经过衡量的请求调整、可行的整合、账单集成和承诺审核分别作为独立工作项。在变更前后衡量每单位有用工作量的总成本和可用性。

以下先前的估算没有经验证的基准测试/账单依据。为便于了解背景，现予以保留；这些数值不作保证，也不得相加或相乘后宣称为总节省：

| 先前主题 | 原始示例范围 |
|-------------|-------------------------|
| Spot | 60–70%、60–90%、70–90% |
| ARM/Graviton | 20% |
| 请求调整 / VPA | 10–30%、15–30%、20–40%、20–50% |
| 整合 | 10–20%、10–30% |
| Savings Plans | 20–30%、20–40% |
| 多 AZ / 调度 | 5–10% / 10–20% |

降低 AZ 弹性并不是通用的成本优化措施。在任何放置/调度实验中，都应考虑数据传输、故障恢复、存储保留和工作负载目标。

## 参考资料

- [EKS 定价和 Auto Mode 费用](https://aws.amazon.com/eks/pricing/)
- [2026 年 7 月 GPU 管理费下调](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price/)
- [Auto Mode 成本控制](https://docs.aws.amazon.com/eks/latest/userguide/auto-cost-control.html)
- [NodePool 资源限制和中断](https://karpenter.sh/v1.14/concepts/nodepools/)
- [Savings Plans 类型](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [Savings Plans 与 RI 的比较](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-ris.html)
- [EKS 账单标签](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
- [启用成本分配标签](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)
- [CloudWatch 估算账单费用](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html)
- [Kubecost 3.2.4 chart](https://kubecost.github.io/kubecost/kubecost-3.2.4.tgz)
- [VPA 1.8.0 安装](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/installation.md)
- [VPA 已知限制](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.8.0/vertical-pod-autoscaler/docs/known-limitations.md)
- [Kubernetes 资源单位和调度](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Auto Mode NodeClass 和标签](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)

< [上一页：运维](./05-operations.md) | [目录](./README.md) | [下一页：节点生命周期](./07-node-lifecycle.md) >
