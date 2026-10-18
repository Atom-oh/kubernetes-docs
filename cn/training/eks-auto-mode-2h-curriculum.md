# EKS Auto Mode 运维培训课程（2 小时）

> **受众**：负责运行 EKS 的基础设施 / 平台工程师
> **前置要求**：掌握 Kubernetes 基础知识并有 EKS 运维经验
> **最后更新**：2026 年 9 月 12 日

## 学习目标

区分 AWS 托管职责和运维方职责，设计 Auto Mode NodePool / NodeClass 资源，使用工作负载 / 成本 / 可用性证据评估改进，并调查节点中断。课程不承诺固定节省百分比或节点预置时间。

## 日程与准备

| 部分 | 时长 | 内容分配 |
| --- | --- | --- |
| 1：架构与放置 | 40 分钟 | 架构 10 分钟 + NodePool / NodeClass 15 分钟 + 扩缩容 15 分钟 |
| 2：优化与生命周期 | 35 分钟 | Spot 10 分钟 + 成本 10 分钟 + 工作负载 10 分钟 + 生命周期 5 分钟 |
| 休息 | 10 分钟 | |
| 3：可观测性与诊断 | 25 分钟 | 节点 8 分钟 + 信号关联 8 分钟 + 场景分析 9 分钟 |
| 4：IaC / GitOps | 10 分钟 | IaC 5 分钟 + ArgoCD 5 分钟 |

总计：120 分钟。使用 [Auto Mode 指南](../eks-auto-mode/README.md)确认当前 API、已准备好的实验环境、账户 / 区域 / kubeconfig、权限和成本限额。纯讲授时可以使用已捕获的事件、NodeClaim 和指标。本课程不会自动执行实际的 FIS 故障注入或节点删除。

行数和关键词出现次数无法证明文档质量或覆盖范围充分，因此已移除旧的评估表。请使用以下参考资料，并根据正在使用的版本补充组织专属的 Terragrunt / 运维流程。

## 第 1 部分：架构与放置（40 分钟）

### 1-1. 管理边界（10 分钟）

使用[入门指南](../eks-auto-mode/01-getting-started.md)比较 Auto Mode、托管节点组和自行管理的 Karpenter。Auto Mode 提供基于 Karpenter 的托管计算资源；运维方仍负责工作负载请求、PDB，以及受支持的 NodeClass 网络 / 存储 / 身份配置。

Auto Mode 使用托管的 Bottlerocket 变体，不提供用户自行选择 AL2023 / Bottlerocket AMI、任意 userData、SSH 或 SSM 访问的能力。请检查通用 / 系统资源池是否实际启用 / 存在。不要假设其托管控制器会像普通 Pod 一样出现在集群中。

### 1-2. NodePool 和 NodeClass（15 分钟）

使用[配置指南](../eks-auto-mode/02-nodepool-configuration.md)查看 `eks.amazonaws.com` 标签和 NodeClass API。不要与自行管理的 Karpenter 所用的 `karpenter.k8s.aws` 实例标签 / EC2NodeClass 混用。支持自定义 NodeClass；AWS 不会替你决定每项设置。

此 **schema 示例**假设已有默认 NodeClass，且镜像兼容 Arm。CPU / 内存限制不是绝对的计费上限，并发预置期间可能会暂时超出限制。它不是适用于所有 GPU / Spot 工作负载的通用资源池。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: kubernetes.io/arch
        operator: In
        values:
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '16'
    memory: 64Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
```

比较 Pod selector / affinity、requests、taint / toleration 和资源池约束。迁移到 Arm 前，需要验证镜像清单、本地依赖和性能。

### 1-3. 扩缩容（15 分钟）

按照[扩缩容指南](../eks-auto-mode/03-scaling-behavior.md)，了解无法调度的 Pod、资源池约束、节点预置和 Pod 就绪流程。40–90 秒并非保证值；请测量镜像拉取、IP / 配额 / 容量和卷依赖所需的时间。

比较 WhenEmpty、WhenEmptyOrUnderutilized 和 consolidateAfter，包括 requests 与实际使用量不一致的工作负载。整合并不能替代手动优化或负载验证。Drift 不保证每一种变更都立即按一次一个节点的方式替换。

## 第 2 部分：优化与生命周期（35 分钟）

### 2-1. Spot（10 分钟）

使用 [Spot 指南](../eks-auto-mode/04-spot-strategies.md)检查兼容的实例多样性、关键容量以及中断 / 恢复。仅要求 Spot 是硬性约束；它并不表示优先使用 Spot 并自动回退到按需实例。do-not-disrupt / PDB 无法阻止 Spot 回收或节点故障。

### 2-2. 成本（10 分钟）

[成本指南](../eks-auto-mode/06-cost-management.md)将 EC2、Auto Mode 费用、EBS、负载均衡器 / NAT / 传输以及可观测性费用分别列出。不要将 Graviton / Spot / 整合的假设百分比乘在一起，并将结果当作实测数据。

符合条件的 EC2 Instance Savings Plans / RI 可以按照相应条款抵扣 EC2 用量，也可以同时使用 Compute Savings Plans。它们不会自动抵扣独立的 Auto Mode 费用，也不能叠加到 Spot 上。Savings Plans 不是容量预留。应另行根据每小时符合条件的基准用量和现有覆盖情况决定是否购买。

### 2-3. 工作负载设计（10 分钟）

使用[工作负载指南](../eks-auto-mode/08-workload-optimization.md)比较 Web、批处理、GPU 和系统工作负载的 requests、镜像 / 架构、存储和 SLO。HPA 控制副本数，VPA 建议 / 更新 CPU / 内存，而 Auto Mode 提供节点。GPU 工作负载需要兼容的型号 / 驱动；VPA 不会选择 GPU 实例。

VPA Off 只提供建议。资源池拆分应依据团队、可用性、授权和容量需求；taint / label 并不是租户安全边界。

### 2-4. 节点生命周期（5 分钟）

通过[生命周期指南](../eks-auto-mode/07-node-lifecycle.md)区分 AWS 文档记载的**默认过期时间 336h（14 天）、默认 NodeClaim 终止宽限期 24h，以及托管实例的最大生命周期 21 天**。此前示例中的 720h（30 天）不是 Auto Mode 的基线，任何生命周期值都不保证节点可用时长。

Budget 会限制自愿执行的 drift / 空节点清理 / 整合操作速率；它无法让所有过期、中断或修复操作都推迟到工作时间之外。检查已保存的 NodeClaim 值、PDB、终止时间和应用恢复情况。

## 休息（10 分钟）

## 第 3 部分：可观测性与诊断（25 分钟）

### 3-1. 节点观测（8 分钟）

使用[运维指南](../eks-auto-mode/05-operations.md)检查 NodePool / NodeClass / NodeClaim 状态、事件以及节点 / 工作负载指标。不要假设可以像普通 Karpenter 部署那样抓取指标端点，或查看 AWS 托管控制器的 Deployment 日志。请配置受支持的托管组件日志及实际的 CloudWatch / Prometheus 发布方。

以下基础告警使用 kube-state-metrics，覆盖整个集群。仅查看 Auto Mode 时，需要使用获准的 compute-type 标签并正确执行 join。节点已删除或指标时间序列缺失时，需要另行调查无数据情况 / 历史记录。

```yaml
groups:
- name: node-health
  rules:
  - alert: NodeNotReady
    expr: kube_node_status_condition{condition="Ready",status="true"} == 0
    for: 5m
  - alert: NodeMemoryPressure
    expr: kube_node_status_condition{condition="MemoryPressure",status="true"} ==
      1
    for: 2m
```

使用相同的单位比较 NodePool `status.resources` 和 `spec.limits`。已移除虚构的 `karpenter_nodeclaims_state/karpenter_nodepool_usage_limit` 比率。CloudWatch Events 和 EventBridge 不是前后相继的两个服务；应验证实际的事件源、规则、目标和延迟。

### 3-2. 关联信号（8 分钟）

使用[可观测性指南](../observability/09-observability-optimization.md)和 [Grafana 指南](../observability/grafana/README.md)区分 trace-to-logs、derived fields 和 exemplars。TraceID 不需要是已索引的 Loki 标签；可以使用日志字段 / 结构化元数据和查询来避免高基数问题。

验证特定版本的设置，例如 tracesToLogsV2、数据源 UID / URL、标签映射、采样和保留期限。Exemplar 需要兼容的发布方、采集、存储和 UI；单独设置一个标志不会为现有数据创建 trace 链接。请为讲解准备一个真实的关联请求示例。

### 3-3. 基于证据的场景分析（9 分钟）

| 现象 | 证据 | 避免过早下结论 |
| --- | --- | --- |
| Pod Pending，但没有新节点 | Pod 事件、PVC、affinity、taint、class / pool 状态、配额 / IP / 容量和 API 错误 | 一定是容量不足 |
| 节点消失 | 删除 / 中断事件、NodeClaim、托管日志、EC2 / CloudTrail 和恢复情况 | 一定是整合或 OOM |
| 响应延迟 | 错误 / 延迟分布、队列、trace / 日志以及 CPU / 内存 / 网络 / 存储 | 单个 trace / 温度值能证明原因 |

CloudTrail 会显示记录到的 API 操作，但无法确定每种调度失败的原因。如果没有调用 EC2 API，Kubernetes condition / event 仍然重要。不要暗示可以恢复缺失的历史遥测数据。

## 第 4 部分：IaC / GitOps（10 分钟）

### 4-1. IaC 边界（5 分钟）

使用[基础设施指南](../ops/01-infrastructure-setup.md)区分共享后端配置与网络 / 集群 / 平台部署层。文件或 state 分离并不能保证网络变更不会影响集群。请验证 provider / module 的 Auto Mode 设置、状态锁定、输出依赖和 apply 顺序。

### 4-2. GitOps 运维（5 分钟）

在 [ArgoCD Applications](../gitops/argocd/02-applications.md) 和 [ApplicationSets](../gitops/argocd/04-applicationsets.md) 中比较权限、生成器和同步策略。自动同步 / 自愈 / prune 并不意味着发布自然安全。审查 NodePool / NodeClass 的删除影响和漂移归属，并验证 Progressive Sync 是否启用及目标版本是否支持。

## 评估与实验准备

- [入门与边界](../quizzes/eks-auto-mode/01-getting-started-quiz.md)
- [NodePool / NodeClass](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
- [扩缩容](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
- [Spot](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
- [成本](../quizzes/eks-auto-mode/06-cost-management-quiz.md)
- [工作负载](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
- [节点生命周期](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
- [运维](../quizzes/eks-auto-mode/05-operations-quiz.md)

准备好账户 / 集群检查、受支持的 API / 镜像、遥测和清理流程，并准确记录实际执行的内容。请参阅[迁移指南](../eks-auto-mode/09-migration-guide.md)和 [Spot 生产实验](../ops/17-spot-production-experiments.md)；故障注入属于单独的、范围受限的实验，需要专用环境、停止条件和恢复证据。

## 审查证据

检查覆盖 120 分钟的日程安排、链接、NodePool 结构 schema 和节点告警规则。没有创建集群、替换节点、运行 FIS 实验、测量节省金额或部署可观测性后端。

- [Auto Mode NodePool 默认值](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [托管实例的最大生命周期](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode 的责任边界与操作系统](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [托管组件日志](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Grafana Tempo 配置](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)
- [Loki 标签基数](https://grafana.com/docs/loki/latest/get-started/labels/)
