# 多账户、多集群 EKS 架构

> **最后更新**：2026 年 10 月 12 日

## 1. 集群整合方式

将多个团队 / 领域的工作负载部署到 EKS 上，大致有以下四种方式。

| 方式 | 配置 |
|---|---|
| 单一核心 EKS | 所有工作负载都运行在一个集群上 |
| 每个环境一个中心 EKS | 生产和非生产环境各使用一个集群 |
| 每个领域一个 EKS | 为每个领域设置专用集群 |
| **共享 + 专用** | 通用工作负载运行在共享集群上；只有对租户隔离、配额或 SLO 有严格要求的工作负载才使用专用集群 |

“共享 + 专用”可以作为候选的起始方案。下表中的阈值是本地运维示例，并非 AWS 强制要求的拆分标准。区分默认配额和已应用的配额，并综合评估 SLO、增长情况和运维能力。

| 信号 | 测量方式 | 拆分阈值 |
|---|---|---|
| 托管节点组数量 | EKS API | 25 / 30 |
| Access Entry 数量 | EKS API | 2,000 / 3,000 |
| 控制平面 API 限流 | CloudWatch、429 日志 | 持续出现 429 |
| etcd 大小 / 对象数量 | 目标 EKS 版本暴露的控制平面指标及对象清单 | 设置告警前，先确认指标是否可用以及相关指导 |
| 每个 VPC 的 NAU（网络地址使用量） | VPC 控制台 / CloudWatch | 50,000 / 64,000（或 200,000 / 256,000） |
| 升级影响范围 | 部署在该集群上的 CUJ 数量 | 达到 2 个或更多 CUJ 时考虑拆分 |
| 插件发布节奏冲突 | 各团队对插件版本要求的差异 | 出现冲突要求时拆分 |

超过阈值后应触发审查。比较提高配额、清理资源和分区的成本；通过经过验证的计划和回滚流程拆分集群。

## 2. A/B EKS Runtime：将故障影响范围拆分到两个集群

将同一个 CUJ（关键用户旅程）部署到两个相互独立的 EKS 集群，使一个集群发生故障时，另一个集群仍能继续提供流量服务，通常称为“A/B EKS Runtime”。这**不是 AWS 官方推荐的模式，而是组织必须自行验证的一种实践假设**。若要真正提高可用性，应先满足以下条件。

### 首先，明确要防范的故障

EKS 托管控制平面跨多个可用区；ARC zonal shift / autoshift 作用于数据平面。A/B 可以隔离以下集群特有的故障。但共享的 VPC、DNS、账户、区域和数据依赖仍属于共享故障域；仅有两个集群并不能保证可用区或区域级韧性。

- 集群升级失败
- 插件（CNI / CoreDNS / CSI）回归问题
- 准入 webhook 错误
- 全集群策略发布错误
- 控制平面 API 限流

请明确记录故障清单，并将 PoC 的成功标准设为“拆分为 A/B 后，这项故障是否确实被限制在其中一侧？”。笼统声称“提高了可用性”无法验证。

<span id="coredns-is-the-most-common-single-point-of-failure"></span>

### 检查共享 DNS 的故障模式与容量

DNS 是一项共享依赖：请检查副本数量、可用区分布和容量。没有事故数据时，不要断言 CoreDNS 是最常见的单点故障。对于 Auto Mode 和混合节点，应先找出实际的 DNS 路径。

- `replicaCount` 和 `topologySpreadConstraints` 是否确实将副本分散到多个可用区
- 是否应用了 CoreDNS 插件的自动扩缩容配置（`{"autoScaling":{"enabled":true}}`），或 HPA / cluster-proportional-autoscaler
- 移除一个可用区后 QPS / 延迟如何变化

**EC2 链路本地服务对包含 DNS、IMDS 和 NTP 在内的流量共享每秒 1,024 个数据包的额度**。检查 VPC DNS ENI 限额和实际 ENA `linklocal_allowance_exceeded` 指标。评估缓存和 DNS 副本的位置；仅凭 Pod 密度无法确定 DNS 故障原因。

### 未预先准备备用容量时，ARC zonal shift 可能导致中断

AWS 文档对此有明确警告。发生 zonal shift 时，以下操作会自动发生：

1. 整个可用区的节点会被 cordon，阻止新任务调度到这些节点。
2. 托管节点组会停止跨可用区再平衡。
3. 该可用区中的 Pod 会从 EndpointSlice 移除。
4. 节点 / Pod 本身不会被终止或驱逐（解除 zonal shift 后，它们会立即恢复）。
5. 已向 ARC 注册的 ALB / NLB 只会向健康的可用区路由流量。

**故障安全行为**：如果某工作负载的端点只存在于受影响的可用区，EKS 仍会继续向该可用区发送流量。也就是说，**只部署在单个可用区的工作负载不会受到 zonal shift 的保护**。

还需检查以下技术限制：

- **不适用于 EKS Fargate。**
- 自行管理的 Karpenter 需要 **1.12 或更高版本**才能获得支持。
- EKS Auto Mode 除了在集群上启用 zonal shift，不需要其他配置。启用后，它会停止在受影响的可用区中预置新节点，停止会影响该可用区的主动干预（例如整合），并避免为调度要求严格指定该可用区的 Pod 启动容量。
- 根据存储后端评估有状态工作负载。EBS PV 属于单个可用区，不能直接连接到另一个可用区。并非所有 PVC 都使用 EBS；EFS 和其他后端具有不同的可用性和恢复行为。

> **设计提案**：在启用 autoshift 前，验证每个服务、DNS 和存储在 N-1 条件下的行为。故障安全机制可能会保留单可用区端点，因此演练不一定会停止这些端点。但该故障安全机制也不保证受影响的可用区仍能提供服务。

### 预置容量倍数计算中的陷阱

“2 个可用区需要大约 2 倍预置容量，3 个可用区按 N-1 计算需要大约 1.5 倍预置容量”在算术上是正确的，但很容易在以下三方面出错：

1. **新增节点所需时间**：占位 Pod 和优先级可以预留现有容量，但无法消除节点预置、镜像拉取或应用启动所需时间。
2. **健康可用区新增容量可能受其他客户需求限制**：这不是猜测；AWS 文档明确指出存在“可用区受损期间，健康可用区可能无法新增节点的计算容量限制风险”。
3. **依赖项与可用区放置**：每个必要的 CUJ 环节都必须能从仍然可用的可用区访问，并获得足够容量。根据需要组合拓扑分布、亲和性和跨可用区回退；测试严格亲和性是否会阻止恢复。

### 优化跨可用区成本

按以下顺序处理：测量 → 优化 → 比较剩余成本。

1. 使用 Flow Logs 和 ENI / 可用区映射找出主要成本路径（仅靠 CUR 无法确定源和目标可用区对）。
2. 评估同可用区路由、Service `spec.trafficDistribution`、拓扑分布、ALB IP 目标、NAT / 端点位置和数据位置。该字段本身没有重命名。请确认目标 Kubernetes / EKS 版本对 `PreferClose`、`PreferSameZone` 和 `PreferSameNode` 的支持情况及功能门控设置。
3. 应用这些优化后，再比较剩余跨可用区成本。

ALB 的跨可用区区域数据传输不会额外收取传输费用，因此关闭它并不一定能省钱。按目标组禁用该功能后，将不再支持目标粘性和 Lambda 目标。空可用区可能返回 503；已填充但不健康的可用区则遵循 DNS / 路由故障转移条件。要区分这两种情况；如果无法确保每个可用区都有足够容量，就应保留默认的启用状态。

### 升级策略与 A/B 的存在理由直接相关

如果采用 A/B EKS Runtime 的实际原因是隔离升级风险，就必须明确规定：

- A、B 集群允许的版本偏差
- 始终先升级其中一侧的规则
- 是否使用延长支持

若没有这些规定，A/B 就只是“两个集群”，冗余也就失去了意义。

### 工作节点可用区数量与控制平面子网是两个独立概念

创建集群时，子网必须分布在至少两个不同的可用区，但工作节点可以只放在一个可用区。这表示 EKS 本身并不禁止“工作节点仅在单个可用区运行”；应将此问题与上文提到的 zonal shift 例外规则分开评估。

## 3. 完整工作负载 Cell：加强隔离的替代方案

若需要比 A/B EKS Runtime 更强的隔离，可以将入口、计算、数据和必需依赖项一起拆分并复制为一个“Cell”单元，将故障影响范围限制在该 Cell 内。分区、一致性、容量和运维成本都会大幅增加，因此这**仅适用于能够支持独立数据分区和复制的工作负载**。

## 后续阅读

EKS 可用性设计不能脱离其底层 VPC 结构来考虑 → [共享 VPC 与连接](./04-shared-vpc-and-connectivity.md)

## 参考资料

- [EKS 配额](https://docs.aws.amazon.com/general/latest/gr/eks.html#limits_eks)
- [EKS 子网与多可用区](https://docs.aws.amazon.com/eks/latest/best-practices/subnets.html)
- [EKS 网络成本优化](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt-networking.html)
- [EKS zonal shift](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html)
- [EKS 租户隔离](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html)
- [使用可用区实现静态稳定性](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/)
- [Well-Architected：多可用区](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_fault_isolation_multiaz_region_system.html)
- [ALB 目标组属性](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/edit-target-group-attributes.html)
- [ALB 目标组健康状态](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html#target-group-health)
- [ALB 跨可用区数据传输](https://aws.amazon.com/elasticloadbalancing/faqs/)
- [Amazon DNS 配额](https://docs.aws.amazon.com/vpc/latest/userguide/AmazonDNS-concepts.html)
- [Kubernetes Service 流量分配](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution)
