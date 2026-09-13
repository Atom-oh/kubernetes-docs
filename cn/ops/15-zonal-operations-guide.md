# 分区集群运维：流量迁移、升级回滚与数据层 AZ 亲和性

> **支持的版本**: Amazon EKS 1.33+, AWS Load Balancer Controller 2.9+, Kafka 2.4+ (KIP-392), Valkey GLIDE 1.x
> **最后更新**: July 21, 2026

< [上一节：Tekton Pipelines](14-tekton-pipelines.md) | [目录](./README.md) | [下一节：故障排查手册](16-troubleshooting-playbook.md) >

***

客户问题中最常见的主题就是“运维”。有一种组合不断出现：**按可用区拆分集群以隔离故障，使用负载均衡器 Target Group 权重迁移流量，并且在出现问题时原地回滚，而不是新建集群。** 本指南将这一组合整合为一套运维策略，并补上通常缺失的一环：**将 DB/cache/messaging 层的读取路径固定到某个可用区。**

本仓库其他位置已提供每一部分的详细操作步骤。本文说明它们为何需要结合使用，并补全此前缺失的数据层内容。

## 目录

1. [为什么采用分区运维](#why-zonal-operations)
2. [流量层：Target Group + TargetGroupBinding + 权重迁移](#traffic-layer-target-group--targetgroupbinding--weight-shifting)
3. [升级：为何原地升级 + 原生回滚成为默认选择](#upgrades-why-in-place--native-rollback-became-the-default)
4. [数据层：将读取路径固定到可用区](#data-layer-pinning-the-read-path-to-a-zone)
5. [推荐组合摘要](#recommended-combination-summary)

***

## 为什么采用分区运维

多 AZ 单集群与每个 AZ 一个集群（分区/单可用区）的集群组有不同的权衡。

| 方面 | 多 AZ 单集群 | 分区（单可用区）集群 |
|--------|--------------------------|-------------------------------|
| 故障隔离 | 一个 AZ 故障会影响集群的一部分 | 一个 AZ 故障仅影响该分区集群；其余集群不受影响 |
| 跨 AZ 成本 | Pod 间流量跨越 AZ 边界（$0.01/GB） | 仅有同 AZ 流量，没有跨 AZ 传输成本 |
| 升级 | 滚动更新，整个集群同时升级版本 | 按可用区依次升级，其他可用区保持在先前版本 |
| 运维复杂度 | 管理一个集群 | 管理 N 个集群，外加需保持同步的流量路由层 |

AWS 通过 [Cell-Based Architecture for Amazon EKS Guidance](https://aws.amazon.com/solutions/guidance/cell-based-architecture-for-amazon-eks/) 提供了这一确切模式。在此模式中，一个分区集群是一个“cell”，Region 内的一组 cell 是一个“supercell”。cell 前方的路由层（Route 53 加权路由加上 Application Recovery Controller）负责故障切换，而每个 cell 内的 ALB 则在其内部进行流量分配。其关键特性是：流量绝不会跨越 cell 边界，因此从一开始就没有跨 AZ 数据传输成本。

分区/蓝绿架构本身已在 [`ops/02-infrastructure-advanced.md`](02-infrastructure-advanced.md#1-bluegreen-architecture-overview) 中介绍，而 Multi-AZ/Cell-Based Architecture 的成熟度模型视角位于 [`eks/10-eks-resiliency.md`](../eks/10-eks-resiliency.md)。本指南在此基础上，将流量迁移、升级和数据读取连接为一个运维闭环。

***

## 流量层：Target Group + TargetGroupBinding + 权重迁移

![具有加权流量迁移的分区 cell 架构](../../assets/ops-zonal-traffic-architecture.png)

在多个分区集群之间迁移流量的标准模式：

1. 使用 Terraform 等 IaC 在集群**外部**创建 NLB/ALB 和 Target Groups（以便即使更换集群，负载均衡器仍能保留）。
2. 使用 `TargetGroupBinding` CRD 将每个分区集群的 Service 绑定到其 Target Group。
3. 通过调整负载均衡器上的 **Target Group 权重** 在集群间迁移流量，无需触及集群内部的任何内容。

```yaml
apiVersion: elbv2.k8s.aws/v1beta1
kind: TargetGroupBinding
metadata:
  name: zone-a-tgb
  namespace: production
spec:
  targetGroupARN: arn:aws:elasticloadbalancing:ap-northeast-2:ACCOUNT:targetgroup/zone-a-tg/xxxxxxxxxxxx
  serviceRef:
    name: app-service
    port: 80
  targetType: ip
```

```bash
# Adjust weight between target groups in the ALB listener's forward action
aws elbv2 modify-listener \
  --listener-arn "$LISTENER_ARN" \
  --default-actions '[{
    "Type": "forward",
    "ForwardConfig": {
      "TargetGroups": [
        {"TargetGroupArn": "'"$ZONE_A_TG_ARN"'", "Weight": 20},
        {"TargetGroupArn": "'"$ZONE_C_TG_ARN"'", "Weight": 80}
      ]
    }
  }]'
```

TargetGroupBinding 的基本/高级/多端口配置见 [`networking/03-aws-lb-controller.md`](../networking/03-aws-lb-controller.md#targetgroupbinding)，NLB 加权 Target Groups 与 Route 53 加权路由的完整 Terraform 设置见 [`ops/02-infrastructure-advanced.md`](02-infrastructure-advanced.md#2-nlb-weighted-target-groups)。

**计划内迁移与故障触发的迁移**：权重调整用于升级和部署等**计划内**转换。AZ 中断等非计划情况由 [ARC (Application Recovery Controller) Zonal Shift](../eks/10-eks-resiliency.md#arc-zonal-shift) 处理，其会自动检测并迁移流量——这两种机制并不冲突，而是分别承担计划内与响应式职责。

> **2026 年 7 月更新**：ARC zonal shift/autoshift [现已支持 EKS Auto Mode 集群](https://aws.amazon.com/about-aws/whats-new/2026/07/eks-auto-mode-arc-zonal-shift)。在 Auto Mode 中，无需设置任何标志，也无需管理 Karpenter 版本——只需在集群上启用 ARC zonal shift；当迁移被激活时，受损 AZ 中的新节点预置和自愿中断（consolidation/drift）会自动暂停。

***

## 升级：为何原地升级 + 原生回滚成为默认选择

2026 年 7 月，Amazon EKS [GA 了原生 Kubernetes 版本回滚](https://aws.amazon.com/blogs/containers/announcing-amazon-eks-rollback-for-safe-and-reliable-management-of-cluster-upgrades/)。如果升级后出现问题，您可在 **7 天内每次回退一个次要版本**；在您回滚前，Rollback Readiness Insights 会自动预检查 API 兼容性、kubelet 版本偏差和 add-on 版本。对于 Auto Mode 集群，回滚覆盖数据平面（worker nodes）以及控制平面——但如果您使用 self-managed node groups 原地升级分区集群（如下节所述），则不适用自动数据平面回滚；只有控制平面会回退，因此 node/AMI/add-on 更改需要单独回退。两种情况均不产生额外费用。

在此功能出现之前，“新版本有问题怎么办”的唯一答案是维护一组常驻的蓝绿集群，可在切换前对其进行验证。如今，已运行分区（每个集群对应一个可用区）设置的团队有了更轻量的选择：每次原地升级一个分区集群，并将原生回滚作为安全网。

| 方法 | 适用场景 |
|----------|---------------------------|
| **常驻蓝绿集群组** | 您需要在切换前针对完全独立集群上的真实生产流量验证新版本，或者您需要整体回退 node/AMI/add-on 更改（原生回滚仅回退控制平面） |
| **分区原地升级 + 原生回滚** | 您已因可用性需求（而非仅仅为了升级）运行分区集群，希望避免始终运行两组完整集群的成本，并且可以接受约 7 天的回滚资格窗口而非立即在集群级别故障恢复 |
| **Route 53 加权 DNS 切换** | 集群位于完全不同的 Regions/accounts，或者您需要替换 NLB 层本身 |

执行 runbook（迁移 NLB 权重 -> 原地升级 -> 验证 -> 恢复权重，以及完整蓝绿集群组仍是正确选择的情形）已记录在 [`ops/11-upgrade-operations.md` 的“Alternative: Zonal In-Place Upgrade with Native Rollback”](11-upgrade-operations.md#alternative-zonal-in-place-upgrade-with-native-rollback) 部分，因此本文不再重复。有关回滚具备资格的确切条件（以目标版本创建的集群无法回滚、已再次升级的集群无法回滚等），请参阅 [`eks/08-eks-upgrades.md` 的 Rollback Procedure](../eks/08-eks-upgrades.md#rollback-procedure)。

***

## 数据层：将读取路径固定到可用区

对于采用分区架构的团队，流量迁移和升级通常已经就位。通常被悄然忽视的是 **DB/cache/messaging 的读取路径**——一个应用 Pod 可能完全位于一个 AZ 内，但它所访问的 DB reader、cache replica 或 Kafka broker 却被跨 AZ 轮询分配，从而产生跨 AZ 成本和延迟，往往在账单到来前无人察觉。

其底层原理在各处都相同：**写入必须发送到 leader/primary，因此无论如何都可能跨 AZ；但读取可以路由到同一 AZ 的 replica。** 对于大部分为读取的工作负载（cache、lookup queries、consumers），仅此一项即可消除大部分跨 AZ 成本。

![数据层 AZ 亲和性读取路径](../../assets/ops-zonal-data-az-affinity.png)

实现这一点需要 Pod 知道自己所在的 AZ。Kubernetes Downward API 不会将节点的可用区标签（`topology.kubernetes.io/zone`）直接注入 Pod，因此需要采用以下方法之一：

- **EC2 IMDS 查询**：Pod 或 sidecar 直接调用 `http://169.254.169.254/latest/meta-data/placement/availability-zone`
- **准入时标签注入**：Kyverno 等 mutating policy 将节点的 `topology.k8s.aws/zone-id` 标签复制到 Pod annotation——这是 AWS 在其 [MSK-on-EKS rack awareness guide](https://aws.amazon.com/blogs/big-data/optimize-traffic-costs-of-amazon-msk-consumers-on-amazon-eks-with-rack-awareness/) 中推荐的模式；有关如何编写 Kyverno policy，请参阅本仓库中的 [`security/01-kyverno-policy-management.md`](../security/01-kyverno-policy-management.md)
- **内置 operator 支持**：Strimzi 等 operator 将 rack-awareness 作为一等功能，因此 init-container 可在无需自定义实现的情况下处理它

### Kafka：KIP-392 Follower Fetching

[KIP-392](https://cwiki.apache.org/confluence/display/KAFKA/KIP-392:+Allow+consumers+to+fetch+from+closest+replica)（Kafka 2.4+）允许 consumer 直接从其**自身 rack（AZ）中的 follower replica** 获取数据，而不再始终访问 partition leader。

![序列图展示 AZ-a 中的 Kafka consumer 从 AZ-b 中的 leader broker 获取数据，通过 rack-aware 提示被重定向至同一 AZ 的 follower replica，然后在本地重新获取数据，从而无需支付跨 AZ 传输成本。](../../assets/diagrams/rendered/en-ops-15-zonal-operations-guide-0.svg)

- **Brokers**：设置 `replica.selector.class=org.apache.kafka.common.replica.RackAwareReplicaSelector`，并为每个 broker 提供 `broker.rack`（AZ ID）
- **Consumers**：将 `client.rack` consumer property 设置为 consumer 自身的 AZ ID，通过上述某种 zone-awareness 方法获取
- **使用 Strimzi 时**，operator 原生支持此功能：

  ```yaml
  apiVersion: kafka.strimzi.io/v1beta2
  kind: Kafka
  spec:
    kafka:
      rack:
        topologyKey: topology.kubernetes.io/zone
      config:
        replica.selector.class: org.apache.kafka.common.replica.RackAwareReplicaSelector
  ```

  设置 `rack.topologyKey` 会使 Strimzi 自动配置 `broker.rack`，并通过 init-container 注入 client rack。
- 还值得了解的是：[KIP-881](https://cwiki.apache.org/confluence/display/KAFKA/KIP-881%3A+Rack-aware+Partition+Assignment+for+Kafka+Consumers) 更进一步，使 consumer group 的 partition assignment 本身具备 rack-awareness。

有关在 EKS 上运行 Kafka 的更广泛内容，请参阅 [`data-on-eks/kafka/`](../data-on-eks/kafka/README.md)。

### Redis/Valkey (ElastiCache)：AZ 亲和性读取策略

[Valkey GLIDE](https://valkey.io/blog/az-affinity-strategy/) client 通过其 `ReadFrom` 设置支持四种读取策略。

| 策略 | 行为 |
|----------|----------|
| `PRIMARY` | 始终从 primary 读取（默认，不感知 AZ） |
| `PREFER_REPLICA` | 在 replicas 间轮询，失败时回退 |
| `AZ_AFFINITY` | 优先选择同一 AZ 的 replica，否则回退 |
| `AZ_AFFINITY_REPLICAS_AND_PRIMARY` | 先选择同一 AZ 的 replica，然后是同一 AZ 的 primary，最后才将其他 AZ 作为最后手段 |

对于读取密集型工作负载（>99% 读取），`AZ_AFFINITY_REPLICAS_AND_PRIMARY` 是成本节省和可用性之间的推荐平衡方案。

```python
from glide import GlideClient, GlideClientConfiguration, ReadFrom

config = GlideClientConfiguration(
    addresses=[...],
    read_from=ReadFrom.AZ_AFFINITY_REPLICAS_AND_PRIMARY,
    client_az="ap-northeast-2a",  # the pod's AZ, obtained via one of the methods above
)
client = await GlideClient.create(config)
```

作为实际案例，HotelTrader 在采用 Valkey GLIDE 的 AZ-affinity routing 后，将跨 AZ 数据传输成本降低了 95%，平均延迟改善了 49%（在缺乏 AZ awareness 时，cache 请求会在各 AZ 间随机分配，从而产生不必要的传输成本）。详情请参阅 [AWS database blog post](https://aws.amazon.com/blogs/database/how-hoteltrader-cut-inter-az-cost-95-and-latency-by-49-with-valkey-glide-on-amazon-elasticache/)。

### Aurora/RDS：Reader Endpoint 的局限与解决方法

Aurora 的默认 reader endpoint 是**不具备 AZ awareness 的轮询 DNS**——同一 AZ 中的 replica 不会获得优先级。这并非功能缺失，而是当前实际存在的限制；公开的 [aws-advanced-jdbc-wrapper#1139](https://github.com/aws/aws-advanced-jdbc-wrapper/issues/1139) issue 正在请求实现 AZ affinity 本身。

有两种解决方法：

1. **按 AZ 划分的 custom endpoints**：将给定 AZ 中的 replica instances 分组为一个 custom endpoint，并将该 AZ 的应用流量指向它。

   ```bash
   aws rds create-db-cluster-endpoint \
     --db-cluster-identifier my-aurora-cluster \
     --db-cluster-endpoint-identifier reader-az-a \
     --endpoint-type READER \
     --static-members db-instance-az-a-1 db-instance-az-a-2
   ```

2. **AWS Advanced JDBC Wrapper**：提供读/写拆分和 `fastestResponse` reader-selection 策略。它并非真正的 AZ affinity，但会优先选择响应最快的 reader，通常就是同一 AZ 中的 reader。

如果您需要真正的 AZ affinity，在上述公开 issue 得到解决前，选项 1（custom endpoints）是唯一可靠的方法。

### 补充的 Kubernetes Service 层选项

若要在应用层将 Service 流量本身固定到一个 AZ，请参阅 [Topology Aware Routing (GA)](../eks/12-kubernetes-version-roadmap.md)；如果您运行 service mesh，请参阅 [Istio Zone-Aware Routing](../service-mesh/istio/resilience/03-zone-aware-routing.md)。结合上述数据层策略，应用到 cache/DB/messaging 的整个读取路径都可保持在 AZ 内。

***

## 推荐组合摘要

| 层 | 截至 2026 年的推荐方案 | 替代方案/回退方案 |
|-------|--------------------------|------------------------|
| 架构 | 分区（单可用区）集群 + Cell-Based Architecture | 多 AZ 单集群（较小的运维团队） |
| 流量迁移 | Target Group + TargetGroupBinding + 权重调整 | Route 53 加权 DNS（不同的 Region/account） |
| 故障响应 | ARC Zonal Shift（自动） | 手动权重调整 |
| 升级 | 分区原地升级 + EKS 原生回滚（7 天） | 常驻蓝绿集群组（需要完整预验证时） |
| Kafka 读取 | KIP-392（`client.rack` + `RackAwareReplicaSelector`），或 Strimzi 的 `rack.topologyKey` | 允许 Region 范围的回退（无本地 follower 时自动发生） |
| Cache 读取 | Valkey GLIDE `AZ_AFFINITY_REPLICAS_AND_PRIMARY` | `PREFER_REPLICA`（不需要 AZ awareness 时） |
| DB 读取 | Aurora 按 AZ 划分的 custom endpoints | AWS Advanced JDBC Wrapper `fastestResponse` |

推荐的实施顺序为 **流量迁移层 -> 升级/回滚 -> 数据读取层**，因为若未部署前面的层，就难以衡量后续层带来的收益（尤其是成本节省）。

***

< [上一节：Tekton Pipelines](14-tekton-pipelines.md) | [目录](./README.md) | [下一节：故障排查手册](16-troubleshooting-playbook.md) >
