# 活动容量规划手册

> **最后更新**：2026 年 9 月 12 日，基于 KEDA 2.20.2 和自管理的 Karpenter AWS provider 1.14.1。
> 数值是根据所述假设计算得出，并非生产基准测试结果。

PM/规划人员提供需求、时间安排、延迟和故障目标。运维人员验证应用、节点、数据库、网络和队列的吞吐量、配额及准备时间。
仅凭活动类型无法保证流量倍数或固定的预热时长。
必要时使用速率限制、候场室和背压；扩缩容并非唯一的过载控制手段。

## 1. 输入和单位

| 输入 | 验证内容 |
|---|---|
| 峰值 RPM/RPS | 单位、用户行为、缓存命中、重试放大和每个 API 的需求 |
| 每个 Pod 的吞吐量 | 使用有代表性的输入、请求和并发量测得的 SLO 容量 |
| 节点容量 | 实际可分配资源减去 DaemonSet 开销；CPU、内存和 Pod 槽位限制 |
| 故障目标 | 定义 Pod/节点/AZ 故障期间的流量目标 |
| 时间 | IANA 时区、明确的 UTC 偏移量以及节点/预留容量实际生效的时间段 |
| 成本 | 价格日期、区域、操作系统、租用方式、未使用的预留容量以及其他服务/税费 |

计算器会检查取整、单位、预留容量重复计费和 AZ 故障。
它假设所有 Pod 使用统一配置文件；其他工作负载需另行汇总，并单独验证拓扑、卷和端口限制。
增加 30% 容量与保留 30% 的容量未使用并不相同。
AZ 故障测试覆盖基线峰值需求，不包括同时发生的额外需求。

`scenario.json`

```json
{
  "description": "Illustrative inputs; replace throughput and allocatable values with measured evidence.",
  "peak_rpm": 600000,
  "pod_rpm_at_slo": 3000,
  "extra_capacity_fraction": "0.30",
  "pod_cpu_milli": 1500,
  "pod_memory_mib": 2048,
  "allocatable_cpu_milli": 15500,
  "daemon_cpu_milli": 500,
  "allocatable_memory_mib": 29696,
  "daemon_memory_mib": 1024,
  "max_pods": 58,
  "daemon_pods": 7,
  "nodes_by_az": {"az-a": 15, "az-b": 11},
  "reserved_nodes_by_az": {"az-a": 15, "az-b": 11},
  "node_start": "2026-11-27T11:00:00+09:00",
  "node_end": "2026-11-27T15:00:00+09:00",
  "reservation_start": "2026-11-27T11:00:00+09:00",
  "reservation_end": "2026-11-27T15:00:00+09:00",
  "usd_per_instance_hour": "0.768",
  "price_region": "ap-northeast-2",
  "price_instance_type": "c5.4xlarge",
  "price_observed_date": "2026-09-12",
  "hpa_max_replicas": 300,
  "node_budget": 40,
  "require_one_az_loss": true,
  "other_services_budget_usd": null
}
```

```python
# capacity.py
"""Deterministic planning arithmetic, not a benchmark or AWS provisioning tool."""
import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP


def number(value, name, minimum=Decimal(0), positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    result = Decimal(str(value))
    if not result.is_finite() or result < minimum or (positive and result == minimum):
        raise ValueError(f"{name}: invalid finite range")
    return result


def integer(value, name, positive=False):
    result = number(value, name, positive=positive)
    if result != result.to_integral_value():
        raise ValueError(f"{name}: integer required")
    return int(result)


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Use timestamps with an explicit UTC offset")
    return result.astimezone(timezone.utc)


def seconds_between(start, end):
    delta = end-start
    return Decimal(delta.days*86400 + delta.seconds) + Decimal(delta.microseconds)/Decimal(1_000_000)


def hours(start, end):
    seconds = seconds_between(start,end)
    if seconds < 60:
        raise ValueError("Planning intervals must be at least 60 seconds")
    return seconds/Decimal(3600)


def ceiling(value):
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def calculate(config):
    if type(config.get("require_one_az_loss",False)) is not bool:
        raise ValueError("require_one_az_loss must be a boolean")
    demand = number(config["peak_rpm"], "peak_rpm", positive=True)
    pod_rate = number(config["pod_rpm_at_slo"], "pod_rpm_at_slo", positive=True)
    margin = number(config["extra_capacity_fraction"], "extra_capacity_fraction")
    pod_cpu = number(config["pod_cpu_milli"], "pod_cpu_milli", positive=True)
    pod_mem = number(config["pod_memory_mib"], "pod_memory_mib", positive=True)
    cpu = number(config["allocatable_cpu_milli"], "allocatable_cpu_milli", positive=True) - number(config["daemon_cpu_milli"], "daemon_cpu_milli")
    memory = number(config["allocatable_memory_mib"], "allocatable_memory_mib", positive=True) - number(config["daemon_memory_mib"], "daemon_memory_mib")
    slots = integer(config["max_pods"], "max_pods", positive=True) - integer(config["daemon_pods"], "daemon_pods")
    if cpu <= 0 or memory <= 0 or slots <= 0:
        raise ValueError("No allocatable application capacity after DaemonSet overhead")
    per_node = min(int(cpu//pod_cpu), int(memory//pod_mem), slots)
    if per_node < 1:
        raise ValueError("The workload cannot fit this node profile")
    base_pods = ceiling(demand/pod_rate)
    planned_pods = ceiling(demand*(Decimal(1)+margin)/pod_rate)
    needed_nodes = ceiling(Decimal(planned_pods)/Decimal(per_node))
    placements = {zone:integer(count, "nodes_by_az") for zone,count in config["nodes_by_az"].items()}
    reservations = {zone:integer(count, "reserved_nodes_by_az") for zone,count in config["reserved_nodes_by_az"].items()}
    if not placements or sum(placements.values()) < 1:
        raise ValueError("Provide at least one planned node")
    nodes = sum(placements.values())
    survivors = nodes-max(placements.values())
    surviving_rpm = Decimal(survivors*per_node)*pod_rate
    start, end = instant(config["node_start"]), instant(config["node_end"])
    reserve_start, reserve_end = instant(config["reservation_start"]), instant(config["reservation_end"])
    node_hours = hours(start,end)
    reservation_hours = hours(reserve_start,reserve_end)
    overlap_start, overlap_end = max(start,reserve_start), min(end,reserve_end)
    overlap = (seconds_between(overlap_start,overlap_end)/Decimal(3600)
               if overlap_end > overlap_start else Decimal(0))
    price = number(config["usd_per_instance_hour"], "usd_per_instance_hour", positive=True)
    # Pay for running instances and unused reserved slots, without double-counting
    # a matching instance occupying a reservation. Assume one instance profile/type.
    running_cost = Decimal(nodes)*node_hours*price
    unused_cost = Decimal(0)
    for zone,reserved in reservations.items():
        used = min(reserved,placements.get(zone,0))
        unused_slot_hours = Decimal(reserved)*reservation_hours-Decimal(used)*overlap
        unused_cost += unused_slot_hours*price
    compute_cost = running_cost+unused_cost
    other = config.get("other_services_budget_usd")
    total = None if other is None else compute_cost+number(other,"other_services_budget_usd")
    findings = []
    if nodes < needed_nodes:
        findings.append("Planned nodes do not satisfy the capacity target")
    if planned_pods > integer(config["hpa_max_replicas"],"hpa_max_replicas",positive=True):
        findings.append("Planned Pod target exceeds the approved HPA maximum")
    if nodes > integer(config["node_budget"],"node_budget",positive=True):
        findings.append("Planned nodes exceed the approved node budget")
    if config.get("require_one_az_loss") and surviving_rpm < demand:
        findings.append("Losing the largest AZ leaves less than the baseline peak demand capacity")
    money = lambda value: format(value.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP),"f")
    return {
        "base_pods":base_pods, "planned_pods_with_extra_capacity":planned_pods,
        "pods_per_node_from_inputs":per_node, "minimum_nodes_for_capacity":needed_nodes,
        "planned_nodes":nodes, "surviving_nodes_after_largest_az_loss":survivors,
        "surviving_rpm":str(surviving_rpm), "node_hours_per_instance":str(node_hours),
        "reservation_hours_per_slot":str(reservation_hours),
        "running_instances_usd":money(running_cost), "unused_reservations_usd":money(unused_cost),
        "ec2_compute_subtotal_usd":money(compute_cost),
        "total_budget_estimate_usd":None if total is None else money(total),
        "findings":findings,
        "assumptions":[
            "Input throughput/allocatable values require workload-specific measurement.",
            "Extra capacity is added once; it is not the same as leaving that fraction unused.",
            "Constant node counts over the interval; matching reservations consumed first within each AZ.",
            "All instances/reservations have the same type/platform/tenancy and supplied hourly rate.",
            "Current public pricing is an estimate for a future event, not a guaranteed charge.",
            "EC2 subtotal excludes EBS, EKS/Auto Mode, networking, load balancers, databases, telemetry and tax.",
            "Capacity and AZ arithmetic do not prove scheduling, recovery or application SLO."
        ]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    try:
        with open(args.input,encoding="utf-8") as stream:
            result = calculate(json.load(stream))
    except (ValueError, KeyError, ArithmeticError) as error:
        parser.error(str(error))
    print(json.dumps(result,indent=2))
```

```bash
python3 capacity.py scenario.json
```

示例计算得出 200 个基线 Pod，增加容量后为 260 个 Pod，至少需要 26 个节点。
不过，较大的 AZ（15/11 个节点）发生故障后，只剩 11 个节点，容量为 330,000 RPM，低于 600,000 RPM 的基线峰值。
不要忽略检查结果并批准该计划。
针对相同配置文件，另行计算的方案是在三个 AZ 中各部署十个节点，可覆盖基线峰值，但仍需进行放置和恢复测试。

区分实际使用预留容量的实例与未使用的槽位。
仅有匹配的硬件，并不会自动将现有实例关联到指定的预留容量。
验证实际的 CapacityReservationId/可用数量；计算器对预留容量使用情况的假设需要验证。
其他服务成本未知时，总预算将保持为 null。EC2 小计并不等于活动的全部成本。

### 定价依据

2026-09-12，AWS Price List API 返回了以下首尔区域 Linux/共享租用方式的按需小时价格，未预装软件。价格不含合同折扣、Spot 和税费。

| 类型 | vCPU | 内存 | 美元/小时 |
|---|---:|---:|---:|
| c5.2xlarge | 8 | 16 GiB | 0.384 |
| c5.4xlarge | 16 | 32 GiB | 0.768 |
| c6i.4xlarge | 16 | 32 GiB | 0.768 |
| m5.4xlarge | 16 | 64 GiB | 0.944 |

示例中的 26 个 c5.4xlarge 节点运行四小时，小计为 $79.87。
原来的 $70.72 估算使用了错误的首尔价格 $0.68/小时。
如果相同的预留容量比节点提前 30 天生效，示例小计（包含未使用的槽位）为 $14,456.83。这些是计算结果，并非实际账单。
活动开始前请重新核对价格和生效时间。还需计入 EBS、EKS/Auto Mode、LB、NAT/传输、数据库、遥测，并区分基线成本与增量成本。

## 2. 职责和前置条件

EC2NodeClass/NodePool 示例适用于自管理的 Karpenter。
Auto Mode 使用 eks.amazonaws.com NodeClass；不要照搬相同的 YAML。
当前的 Auto Mode NodeClass 也支持 capacityReservationSelectorTerms，因此不要假设它不支持预留容量。请分别检查该服务的选择器、权限和支持范围。

有关基线安装和运维人员 IRSA，请参阅[扩缩容章节](./06-scaling-strategies.md)。
首先准备应用 Deployments、ecommerce 命名空间、Prometheus 和指标约定。
此身份验证使用运维人员身份；它不会创建 IAM 角色。

```yaml
# trigger-auth.yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: event-aws
  namespace: ecommerce
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
```

`operator-read-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:ap-northeast-2:123456789012:order-processing"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:GetMetricData"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    }
  ]
}
```

替换账户/队列 ARN 值，并向运维人员角色附加所需的只读权限。
CloudWatch GetMetricData 使用请求区域条件，而非资源级范围限制。
此策略不会授予工作进程 ReceiveMessage/DeleteMessage 权限。
在共享安装中，还需控制哪些人可以创建 ScaledObjects 和 TriggerAuthentications。

## 3. KEDA：每个工作负载只由一个对象负责

不要将多个 ScaledObjects/HPAs 关联到同一个 Deployment。
这些示例针对三个不同的工作负载：order-api、order-worker 和 frontend。
保留基线指标自动扩缩容，并在活动 Cron 结束后移除/更新它。

不要只根据已完成订单对 API 进行扩缩容：负载饱和时，完成量可能趋于平稳或下降，从而错误地暗示应缩容。应将传入请求、积压和等待时间与实际容量关联起来。
以下示例假设应用提供 http_requests_total 计数器，且抓取标签包含命名空间/服务。
不要假设标准 NGINX exporters 会自动提供路径/页面浏览量指标。
此 Prometheus 为单集群部署；如果使用共享后端，请添加集群范围限制。

```yaml
# prometheus-rule.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: event-demand
  namespace: observability
  labels:
    release: prometheus
spec:
  groups:
  - name: event-demand
    rules:
    - record: event:incoming_requests_per_minute:rate1m
      expr: sum by (namespace, service) (rate(http_requests_total{namespace="ecommerce",service="order-api"}[1m]))
        * 60
    - record: event:order_api_error_ratio:rate5m
      expr: (sum by (namespace, service) (rate(http_requests_total{namespace="ecommerce",service="order-api",status=~"5.."}[5m]))
        or 0 * sum by (namespace, service) (rate(http_requests_total{namespace="ecommerce",service="order-api"}[5m])))
        / (sum by (namespace, service) (rate(http_requests_total{namespace="ecommerce",service="order-api"}[5m]))
        > 0)
```

```yaml
# order-api-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-api
  namespace: ecommerce
  labels:
    event: flash-sale-2026-11
spec:
  scaleTargetRef:
    name: order-api
  minReplicaCount: 5
  maxReplicaCount: 300
  pollingInterval: 15
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 100
            periodSeconds: 15
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
          - type: Percent
            value: 10
            periodSeconds: 120
  triggers:
  - type: cron
    metricType: AverageValue
    metadata:
      timezone: Asia/Seoul
      start: 0 11 27 11 *
      end: 0 15 27 11 *
      desiredReplicas: '260'
  - type: prometheus
    metricType: AverageValue
    metadata:
      serverAddress: http://prometheus-kube-prometheus-prometheus.observability.svc:9090
      query: event:incoming_requests_per_minute:rate1m{namespace="ecommerce",service="order-api"}
      threshold: '3000'
      ignoreNullValues: 'false'
```

阈值 3,000 表示每个 Pod 每分钟处理的请求数，与示例吞吐量单位一致。
请用负载测试证据替换此值。查询必须返回一个值。
ignoreNullValues=false 可避免将缺失观测数据当作零需求。
请在生产环境之外测试 HPA 错误/缺失数据时的行为和人工响应流程。

Cron 使用五个 Linux 字段，且没有年份字段。保留 11 月 27 日的示例配置会导致它明年再次触发。一次性活动结束后，应从 Git 中移除活动配置。
IANA 时区遵循 DST：纽约 5 月采用 EDT，而非 EST。
测试时间边界、重叠窗口和有歧义的 DST 时间。

HPA 会合并各指标给出的建议，取最大值，然后应用 min/max 和行为约束。
Cron 提供需求下限，并不保证 Pod 已 Ready。
上限由 maxReplicaCount 和其他限制决定，而非其他指标。
策略或容量约束可能会延迟达到目标。

![KEDA 提供 Cron 和请求指标；HPA 应用扩缩容建议和界限。](../.gitbook/assets/en-ops-12-event-capacity-planning-1.png)

[打开交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-12-event-capacity-planning-1.html)

当 minReplicaCount 大于零时，cooldownPeriod 并不是返回基线前的通用延迟。
应区分 KEDA 激活/缩容到零与 HPA 的 1→N 循环，以及它们各自的轮询/同步/缓存间隔。
Percent/periodSeconds 表示滚动窗口内的变更限制，并非精确的重复计时器。
稳定窗口并非简单地等待固定时长后执行一次操作。

### SQS 工作进程

queueLength 表示每个 Pod 的目标积压量，并不保证每个 Pod 恰好处理十条消息。
应根据处理时间、并发量和允许的等待时间来选择，并监控最早消息的等待时间、DLQ 和重试。此示例包含可见和处理中消息，但不包含延迟消息；计数为近似值。请另行实现可见性超时、幂等性以及关闭/确认行为。

```yaml
# worker-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-worker
  namespace: ecommerce
  labels:
    event: flash-sale-2026-11
spec:
  scaleTargetRef:
    name: order-worker
  minReplicaCount: 2
  maxReplicaCount: 100
  pollingInterval: 15
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          stabilizationWindowSeconds: 0
          policies:
          - type: Percent
            value: 100
            periodSeconds: 15
        scaleDown:
          stabilizationWindowSeconds: 600
          policies:
          - type: Percent
            value: 10
            periodSeconds: 120
  triggers:
  - type: aws-sqs-queue
    metricType: AverageValue
    metadata:
      queueURL: https://sqs.ap-northeast-2.amazonaws.com/123456789012/order-processing
      awsRegion: ap-northeast-2
      queueLength: '10'
      activationQueueLength: '1'
      scaleOnInFlight: 'true'
      scaleOnDelayed: 'false'
    authenticationRef:
      name: event-aws
```

### CloudWatch frontend

RequestCount 是由应用发布的请求计数/增量；对 60 秒内的值求和可得该时间段的请求数。不要对重复发布的每分钟速率 gauge 或累计计数器求和。
KEDA 2.20.2 使用 metricStat，而不是 metricStatType。
minMetricValue 是 NoData 回退值，并非激活阈值。
ignoreNullValues=false 优先生效。请验证采集时间、结束时间偏移量和发布延迟。

```yaml
# frontend-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: frontend
  namespace: ecommerce
  labels:
    event: flash-sale-2026-11
spec:
  scaleTargetRef:
    name: frontend
  minReplicaCount: 3
  maxReplicaCount: 100
  triggers:
  - type: aws-cloudwatch
    metricType: AverageValue
    metadata:
      namespace: ECommerce/Frontend
      dimensionName: Service
      dimensionValue: frontend
      metricName: RequestCount
      metricStat: Sum
      metricStatPeriod: '60'
      metricCollectionTime: '180'
      metricEndTimeOffset: '60'
      metricUnit: Count
      targetMetricValue: '3000'
      activationTargetMetricValue: '0'
      minMetricValue: '0'
      ignoreNullValues: 'false'
      awsRegion: ap-northeast-2
    authenticationRef:
      name: event-aws
```

## 4. 动态扩容与静态预置

仅设置 NodePool 的 weight 和 limits 并不会创建预热节点。动态池会响应 Pod 调度需求。
预先扩容实际应用并验证初始化，是基线方案。
自管理的 Karpenter 也支持通过 spec.replicas 配置静态 NodePools。
这与 EC2 Auto Scaling 已停止实例的 Warm Pool 不同。

此 NodeClass 适用于自管理的 Karpenter。请设置真实的 IAM 角色、子网/SG 标签和集群版本。
该别名固定到通过首尔 EKS 1.36 AL2023 x86_64 公共 SSM 参数验证的版本。
其他 Kubernetes 版本/架构请重新检查兼容性。
明确决定在预留容量不存在或耗尽时是否允许回退。

```yaml
# nodeclass.yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: event-nodes
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
  - alias: al2023@v20260903
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  capacityReservationSelectorTerms:
  - tags:
      event: flash-sale-2026-11
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      encrypted: true
  tags:
    event: flash-sale-2026-11
```

### 选项 A：动态池并预先扩容实际应用

reserved 指 ODCR/容量块容量，而非 Reserved Instance 折扣。
Karpenter 会优先使用允许的实例类型中的预留容量，然后回退到允许的替代方案。
此示例排除 Spot，但按需容量并不保证服务正常运行或新容量一定可用。
weight 表示在兼容的动态池之间的资源调配优先级，并不会强制将工作负载放置到现有节点上。

```yaml
# dynamic-nodepool.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: event-dynamic
spec:
  template:
    metadata:
      labels:
        event: flash-sale-2026-11
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: event-nodes
      taints:
      - key: event
        value: flash-sale-2026-11
        effect: NoSchedule
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - c5.4xlarge
  limits:
    cpu: '640'
  weight: 100
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
```

匹配节点/Pod 的活动标签、选择器、污点和容忍度。
这是对现有 Deployment 的放置补丁，不是完整的独立清单。
命名空间标签不会自动创建 Pod 标签或 EC2 计费标签。
更改在线工作负载的选择器会改变发布/放置行为；请先验证就绪容量和 PDB。

```yaml
# workload-placement-patch.yaml
spec:
  template:
    metadata:
      labels:
        event: flash-sale-2026-11
    spec:
      nodeSelector:
        event: flash-sale-2026-11
      tolerations:
      - key: event
        operator: Equal
        value: flash-sale-2026-11
        effect: NoSchedule
```

### 选项 B：静态池

这是替代方案，不应意外与选项 A 叠加使用。
replicas=0 定义一个不会创建节点的静态池；在获批时间调高数量。
设置后，无法移除 spec.replicas 来切换为动态模式。
静态池不能使用 weight，且只支持 limits.nodes。
它们不会进行整合；扩缩容操作会绕过 NodePool 中断预算，但仍遵循 PDB。
允许多个 AZ 的单个池无法保证均衡放置，因此此示例按 AZ 分开配置。

```yaml
# static-nodepools.yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: event-static-a
spec:
  replicas: 0
  template:
    metadata:
      labels:
        event: flash-sale-2026-11
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: event-nodes
      taints:
      - key: event
        value: flash-sale-2026-11
        effect: NoSchedule
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
  limits:
    nodes: 12
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: event-static-b
spec:
  replicas: 0
  template:
    metadata:
      labels:
        event: flash-sale-2026-11
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: event-nodes
      taints:
      - key: event
        value: flash-sale-2026-11
        effect: NoSchedule
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2b
  limits:
    nodes: 12
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: event-static-c
spec:
  replicas: 0
  template:
    metadata:
      labels:
        event: flash-sale-2026-11
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: event-nodes
      taints:
      - key: event
        value: flash-sale-2026-11
        effect: NoSchedule
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - reserved
        - on-demand
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2c
  limits:
    nodes: 12
```

```bash
# Example only after approval of matching capacity and cost:
DOCS_CONTEXT="my-event-cluster"
kubectl --context "$DOCS_CONTEXT" scale nodepool event-static-a --replicas=10
kubectl --context "$DOCS_CONTEXT" scale nodepool event-static-b --replicas=10
kubectl --context "$DOCS_CONTEXT" scale nodepool event-static-c --replicas=10
```

如果 GitOps 管理 replicas，也要更新其期望状态。
启用放置和活动扩缩容前，先确认静态 Nodes 已 Ready。
准备工作尚未完成时，不要将在线工作负载迁移到零副本容量，也不要启用 Cron。
将更早的准备时间计入 node_start/reservation_start 成本输入。

### 使用占位 Pod 时

低优先级 Pod 可能成为抢占对象，但不能保证立即完成放置/就绪。
如果 Deployment 的期望数量保持不变，占位 Pod 被抢占后可能会重新创建并调配额外节点。请检查节点保留/到期设置和交接流程，移除占位需求，然后验证应用就绪状态。
检查请求值是否过大、选择器是否缺失，以及是否与基线自动扩缩容器冲突。

![移除占位 Pod 需求并检查节点保留情况后，验证应用就绪状态。](../.gitbook/assets/en-ops-12-event-capacity-planning-0.png)

[打开交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-12-event-capacity-planning-0.html)

## 5. 容量预留：容量和计费

targeted 要求明确指定预留容量；它并不是仅限于某个 NodePool 的安全 ACL。请验证账户/共享权限、AZ、类型、平台、租用方式和成功激活状态。
检查选择器、status.capacityReservations 以及实际实例的 CapacityReservationId。
预留容量并不保证应用就绪、SLO 或无故障运行。

以下 Terraform 会立即创建预留容量。未来的 end_date 并不意味着未来才开始。
在 D-30 时应用配置可能会在活动前产生未使用容量费用。
未来日期的预留容量有单独的资格、承诺和开始时间规则。
请根据获批的容量和预算计划设置 az_counts。

```hcl
# reservations/main.tf
terraform {
  required_version = ">= 1.15.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

variable "event" {
  type    = string
  default = "flash-sale-2026-11"
}

variable "instance_type" {
  type    = string
  default = "c5.4xlarge"
}

variable "az_counts" {
  type        = map(number)
  description = "Approved matching capacity per Availability Zone in this AWS account."
  validation {
    condition = length(var.az_counts) > 0 && alltrue([
      for count in values(var.az_counts) : count > 0 && floor(count) == count
    ])
    error_message = "Provide positive integer reservation counts."
  }
}

variable "reservation_end_utc" {
  type        = string
  description = "RFC3339 expiration. This resource creates an immediate reservation, not a future-dated request."
  validation {
    condition     = can(timecmp(var.reservation_end_utc, plantimestamp())) && try(timecmp(var.reservation_end_utc, plantimestamp()) > 0, false)
    error_message = "The expiration must be a valid future RFC3339 timestamp."
  }
}

resource "aws_ec2_capacity_reservation" "event" {
  for_each                = var.az_counts
  instance_type           = var.instance_type
  instance_platform       = "Linux/UNIX"
  tenancy                 = "default"
  availability_zone       = each.key
  instance_count          = each.value
  instance_match_criteria = "targeted"
  end_date_type           = "limited"
  end_date                = var.reservation_end_utc
  tags = {
    Name  = "${var.event}-${each.key}"
    event = var.event
  }
}

output "reservation_ids" {
  value = { for zone, reservation in aws_ec2_capacity_reservation.event : zone => reservation.id }
}
```

```json
{
  "az_counts": {
    "ap-northeast-2a": 10,
    "ap-northeast-2b": 10,
    "ap-northeast-2c": 10
  },
  "reservation_end_utc": "2026-11-27T06:00:00Z"
}
```

这些是示例输入。在保存 reservations/approved-event.tfvars.json 之前，请确认账户 AZ、容量和到期时间。
15:00 KST 即 06:00 UTC。
不要使用已过期日期或没有偏移量的时间戳。
将计划审核与实际创建时间分开。

```bash
terraform -chdir=reservations init
terraform -chdir=reservations plan -var-file=approved-event.tfvars.json -out=event.tfplan
terraform -chdir=reservations show event.tfplan
```

不要对已占用的预留槽位重复收费，额外再收取其实例的费用。
未使用的槽位可能按等效的按需费率计费。
请检查即时/未来预留容量的计费开始时间、最小计费单位和适用折扣。
取消/到期不会自动终止正在运行的 EC2 实例。
清理期间，请分别验证节点、卷和预留容量。

## 6. 启动时间和镜像

分别测量 KEDA 轮询、HPA 同步、控制器协调、EC2 容量/启动、CNI、卷挂载、镜像拉取和应用预热时间。
在下方流程中区分期望数量和 Ready 数量。
节点数量并非总是 Pod 数量除以十。

![HPA 改变需求；资源调配、kubelet 注册和 Pod 就绪是不同阶段。](../.gitbook/assets/en-ops-12-event-capacity-planning-2.png)

[打开交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ops-12-event-capacity-planning-2.html)

预先扩容真实应用副本可以验证初始化和依赖负载，而不只是拉取镜像。
在任意应用镜像中运行 sh -c echo cached 的通用缓存 DaemonSet 对不带 shell 的镜像（如 distroless）会失效。如果使用缓存工具，请验证其支持无副作用命令、注册表权限、架构、匹配的 digest 和节点选择器。
镜像 GC、节点替换和拉取策略意味着缓存无法保证镜像永久保留或完全不再拉取。不要承诺零冷启动。

## 7. 操作手册

| 阶段 | 完成标准 |
|---|---|
| 规划 | 需求、SLO、故障目标、依赖项、预算、配额和预留容量可行性 |
| 非生产测试 | 有代表性的负载、故障/恢复、启动时间分布和缺失指标 |
| 准备 | 渲染/验证固定版本设置，记录 GitOps 管理归属和基线恢复值 |
| 激活 | 在获批计费时段内准备容量；验证节点、放置、应用就绪状态和 SLO |
| 活动期间 | 观察期望/可用数量、错误、延迟、积压时长、约束和成本 |
| 完成 | 恢复 Cron/下限，排空积压/会话/任务，并核实实际节点/预留容量 |

渲染、Schema 验证和服务器端 dry-run 并不能测试真实 EC2 可用性或应用预热。
实际的预扩容测试可能创建资源并产生费用，应在单独的非生产测试中进行。
进行变更前，设置并验证实际 context 和区域。

```bash
DOCS_CONTEXT="my-event-cluster"
DOCS_REGION="ap-northeast-2"
kubectl --context "$DOCS_CONTEXT" -n ecommerce get scaledobjects
kubectl --context "$DOCS_CONTEXT" get nodes -l event=flash-sale-2026-11 -o wide
kubectl --context "$DOCS_CONTEXT" -n ecommerce get deployment order-api
DOCS_HPA=$(kubectl --context "$DOCS_CONTEXT" -n ecommerce get scaledobject order-api \
  -o jsonpath='{.status.hpaName}')
test -n "$DOCS_HPA" || exit 1
kubectl --context "$DOCS_CONTEXT" -n ecommerce get hpa "$DOCS_HPA"
```

直接扩缩容 Deployment 或修改由 KEDA 管理的 HPA，可能会在协调时被覆盖。
不要假设 HPA 与 Deployment 同名。
如有需要，可在获批的最大值范围内临时提高 ScaledObject minReplicaCount，记录并恢复之前的值；如果由 GitOps 管理，也要更新 Git。
不要默认采用会盲目创建池或提高上限的紧急脚本。

```bash
# Example only after checking the current maximum and change ownership:
kubectl --context "$DOCS_CONTEXT" -n ecommerce patch scaledobject order-api \
  --type merge -p '{"spec":{"minReplicaCount":260}}'
```

活动结束后，恢复 Cron/临时下限，同时保留基线指标触发器。
删除 ScaledObject 不会自动恢复原始副本数量。
删除 NodePool 可能会终止关联节点；不要使用定时删除或 terraform destroy -target 自动执行清理。对于静态池，应安全迁移工作负载，将期望数量降为零，并确认实际终止。分别检查 PDB、长时间运行的任务、会话、预留容量、卷和费用。

## 8. 观测和活动后分析

针对同一工作负载范围，对比需求、Deployment 期望/可用数量、HPA 建议、错误率和延迟。目标指标并不等于目标 Pod 数量；统计处于 Running 阶段的 gauge 序列也不等于统计 Ready Pod。

```promql
max(kube_deployment_spec_replicas{namespace="ecommerce",deployment="order-api"})
```

```promql
max(kube_deployment_status_replicas_available{namespace="ecommerce",deployment="order-api"})
```

```promql
event:incoming_requests_per_minute:rate1m{namespace="ecommerce",service="order-api"} / 60
```

```promql
event:order_api_error_ratio:rate5m{namespace="ecommerce",service="order-api"}
```

采集多个集群时，请包含集群标签。
请验证 SQS、CloudWatch 和成本数据中实际使用的 exporter 指标/标签名称。
不要假设 node_cost_hourly 之类未定义的指标存在。
有关 OpenCost/Kubecost API 和成本范围，请参阅[FinOps 章节](./13-finops-cost-platform.md)。
检查 GET API 是否需要使用带有 --data-urlencode 的 curl -G。
提供完整的 dashboard JSON 请求体，而不是 API 包装器或不完整的面板。

记录预测/实测值、时间窗口/样本数量、请求与已完成订单、期望与可用数量、依赖瓶颈、实际节点/预留容量时间段和成本范围。
不要将假设的收入/成本表述为实测结果。
按需容量可避免 Spot 回收风险，但并不能消除所有故障。
请针对 Spot 测试中断、通知限制、重试和恢复；不要仅依据固定的节省百分比或活动时长做决定。

验证使用了 Decimal 计算、固定的 Schema/元数据、Cron 边界/时区、Terraform mocks 和图表。验证未涵盖真实活动负载、EC2 可用性、SQS 处理或计费。

## 官方参考资料

- [KEDA Cron](https://keda.sh/docs/2.20/scalers/cron/)
- [KEDA ScaledObject](https://keda.sh/docs/2.20/reference/scaledobject-spec/)
- [KEDA CloudWatch](https://keda.sh/docs/2.20/scalers/aws-cloudwatch/)
- [KEDA SQS](https://keda.sh/docs/2.20/scalers/aws-sqs/)
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter NodeClasses](https://karpenter.sh/docs/concepts/nodeclasses/)
- [Auto Mode NodeClass](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [容量预留](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-reservations.html)
- [预留容量计费](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-pricing-billing.html)
- [AWS Price List API](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html)

---

< [上一章：EKS 升级](./11-upgrade-operations.md) | [目录](./README.md) | [下一章：FinOps](./13-finops-cost-platform.md) >
