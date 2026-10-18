# Karpenter 测验

> **最后更新**：2026年9月11日

本测验考查你对 Karpenter 节点自动扩缩器的理解，包括 NodePool/EC2NodeClass 配置、成本优化、Consolidation、Drift、中断处理以及 Amazon EKS 集成。

## 选择题

1. 在本 AWS 示例中，Karpenter 与 Cluster Autoscaler 的架构差异是什么？
   - A) 对 Kubernetes 版本的要求更高
   - B) 不依赖 Auto Scaling Groups，直接预置 EC2 实例
   - C) 只支持 AWS，不支持其他云
   - D) 只支持基于 CPU 的扩缩

<details>

<summary>显示答案</summary>

**答案：B) 不依赖 Auto Scaling Groups，直接预置 EC2 实例**

**解释：**
在 AWS provider 中，Karpenter 通过 NodeClaims 请求 EC2 capacity（包括 EC2 Fleet），而不是扩缩 Auto Scaling Group。Cluster Autoscaler 通常调整已配置的 node groups。实例选择仍取决于 Pod、NodePool 和 NodeClass 的约束、配额及可用性。EC2 API 启动耗时、Node 变为 Ready 的耗时和应用就绪耗时属于不同阶段；并不保证能在数秒内完成。
</details>

2. 在 Karpenter v1 API 中，哪个 CRD 定义节点预置策略（实例类型、capacity 类型和 disruption 设置）？
   - A) NodeClaim
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>显示答案</summary>

**答案：B) NodePool**

**解释：**
NodePool（karpenter.sh/v1）定义模板要求和生命周期策略。expireAfter 位于 spec.template.spec；consolidation 和预算位于 spec.disruption。EC2NodeClass（karpenter.k8s.aws/v1）通过 nodeClassRef 提供 AWS 设置。NodeClaim 则跟踪单个节点所请求的 capacity 及其生命周期。
</details>

3. 如何配置 Karpenter 使用 Spot 实例以优化成本？
   - A) 设置 disruption.capacityType: spot
   - B) 在 requirements 中指定 karpenter.sh/capacity-type: spot
   - C) 在 nodeClassRef 中设置 spotEnabled: true
   - D) 在 limits 中设置 spot: true

<details>

<summary>显示答案</summary>

**答案：B) 在 requirements 中指定 karpenter.sh/capacity-type: spot**

**解释：**
NodePool requirements 可以允许 Spot、On-Demand 以及已配置的 Reserved capacity。In 条件中的值是一个集合，排列顺序不表示优先级。在允许的 capacity 类型中，Karpenter 按 Reserved、Spot、On-Demand 的顺序优先选择，但仍受可用实例和其他约束影响。Spot 价格和中断风险会变化，节省成本并无保证。
</details>

4. Karpenter 的 Consolidation 功能做什么？
   - A) 汇总多个节点上的日志
   - B) 在符合工作负载约束时评估删除节点或以成本更低的节点替换
   - C) 将多个集群合并为一个
   - D) 将多个 NodePool 合并为一个

<details>

<summary>显示答案</summary>

**答案：B) 在符合工作负载约束时评估删除节点或以成本更低的节点替换**

**解释：**
Consolidation 会在遵守工作负载约束和适用的 disruption 控制的前提下，寻找可行的删除或更低成本替换方案。它可能删除一个节点、用更便宜的节点替换一个节点，或合并多个节点；节点总数不一定减少。WhenEmpty 只允许对符合条件的空节点进行 consolidation。consolidateAfter 是相关 Pod 变更后的资格等待时间，并非保证终止的期限，也不是 CPU 利用率阈值。
</details>

5. Karpenter 的 expireAfter 设置有什么用途？
   - A) Pod 可以在节点上运行的最长时间
   - B) 节点达到该年龄时开始由过期策略触发 drain
   - C) Karpenter controller 的缓存过期时间
   - D) NodePool 策略的有效期

<details>

<summary>显示答案</summary>

**答案：B) 节点达到该年龄时开始由过期策略触发 drain**

**解释：**
节点达到配置的年龄后，expireAfter 会启动过期处理和 drain。阻止驱逐的 PDB 或带有 do-not-disrupt 的 Pod 可能延迟完成；若配置了 terminationGracePeriod，最终可以强制删除仍未退出的 Pod。外部中断期限也可能导致 capacity 被移除。替换节点使用当时符合条件的 AMI 和实例类型，不一定更新；过期策略也不保证替换节点先变为 Ready。
</details>

6. Karpenter 中哪个字段为 NodePool 设置资源限制？
   - A) spec.template.limits
   - B) spec.limits
   - C) spec.maxResources
   - D) spec.resourceQuota

<details>

<summary>显示答案</summary>

**答案：B) spec.limits**

**解释：**
spec.limits 限制动态 NodePool 的总资源。使用 cpu: "1000" 这样的字符串数量值，可以避免 API 或 GitOps 工具间的类型差异。并行预置期间限额检查是最终一致的，因此快速扩容可能暂时超出限额。这不是严格的成本或账单上限。
</details>

7. Karpenter 的 Drift 功能会检测并处理什么？
   - A) 网络流量变化
   - B) 现有节点与当前 NodePool/EC2NodeClass 配置不匹配的状态
   - C) Pod 调度漂移
   - D) Kubernetes 版本变化

<details>

<summary>显示答案</summary>

**答案：B) 现有节点与当前 NodePool/EC2NodeClass 配置不匹配的状态**

**解释：**
Drift 会将现有 NodeClaim 与相关的期望配置和已解析配置进行比较。有些变更不会触发 Drift，例如 weight 或预算变化；可变的 AMI selector 即使清单未修改，也可能解析为不同结果。Drift 处理受 disruption 控制约束，无法保证所有节点立即收敛到新配置。Drift 在 v1 中已稳定，旧的 Drift feature gate 已移除。
</details>

8. EC2NodeClass 中哪个字段设置节点根卷的大小和类型？
   - A) spec.rootVolume
   - B) spec.blockDeviceMappings
   - C) spec.storage
   - D) spec.ebsConfig

<details>

<summary>显示答案</summary>

**答案：B) spec.blockDeviceMappings**

**解释：**
spec.blockDeviceMappings 配置 EBS 设备。在 AL2023 示例中，根卷映射为 /dev/xvda；其他镜像应按其实际 AMI/系列布局配置，包括 Bottlerocket 的独立数据设备。卷大小、类型、加密和 KMS 权限都必须符合预期。添加 EBS 映射不会自动格式化或挂载文件系统。
</details>

## 简答题

9. 评估 Karpenter 扩容延迟时，必须分别测量哪些阶段？

<details>

<summary>显示答案</summary>

**答案：测量预置和就绪的各个阶段；不存在适用于所有环境的固定时长。**

**解释：**
测量需求检测/批处理、EC2 请求和 capacity 满足、启动/引导配置、Node 注册并变为 Ready，之后还包括镜像拉取和应用就绪。IAM/API 重试、IP capacity、存储和应用初始化会影响不同阶段。本文没有历史实测数据可用于建立 Karpenter 与 Cluster Autoscaler 的通用耗时对比。
</details>

10. Karpenter 存在多个 NodePool 时，如何确定优先级？

<details>

<summary>显示答案</summary>

**答案：使用 weight 字段表示基于权重的优先倾向。**

**解释：**
对于符合条件的动态 NodePool，数值较大的 spec.weight 表示该池在预置时具有更高的优先倾向。调度批次、工作负载要求、现有 capacity、NodePool 限额以及不可用的实例方案，都可能使其他 NodePool 被选中。它不是针对每个 Pod 的绝对保证，也不代表固定的 Spot/On-Demand 比例；静态 NodePool 另有约束。同一 NodePool 中的 capacity 类型优先级与数组排列顺序无关。
</details>

11. 移除节点时，哪个 Kubernetes 资源会限制自愿驱逐 Pod？

<details>

<summary>显示答案</summary>

**答案：PDB（PodDisruptionBudget）**

**解释：**
PDB 根据匹配副本的健康状态限制自愿驱逐。它既不会创建副本，也不能阻止实例意外丢失、强制修复或配置的 terminationGracePeriod 到期。minAvailable: 2 是驱逐约束，并不保证始终有两个 Pod 正在运行或提供流量。
</details>

12. Karpenter 如何在 EC2NodeClass 中选择要使用的子网和安全组？

<details>

<summary>显示答案</summary>

**答案：使用 subnetSelectorTerms 和 securityGroupSelectorTerms，并结合受支持的标签、资源 ID 及文档支持的其他筛选条件。**

**解释：**
这些 selector 可使用受支持的标签或显式资源 ID；在支持的情况下，安全组也可按名称选择。同一个 term 内的条件按 AND 组合，不同 term 之间按 OR 组合。在选定的可用区内，Karpenter 通常会选择可用 IP 地址最多的匹配子网。这本身不能保证各可用区均匀分布或使用私有路由；还需核验拓扑约束、路由和实际安全组。
</details>

## 实践题

13. 编写一个动态 NodePool，允许 Spot 并在需要时回退到 On-Demand，允许 m5/c5/r5 类型，并使空节点在 30 分钟后符合 consolidation 条件。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    metadata:
      labels:
        nodepool: cost-optimized
    spec:
      requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.large
        - m5.xlarge
        - m5.2xlarge
        - c5.large
        - c5.xlarge
        - c5.2xlarge
        - r5.large
        - r5.xlarge
        - r5.2xlarge
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**解释：**
Spot 的优先级来自 Karpenter 对 capacity 类型的策略，而不是因为在列表中把 spot 写在前面。允许更多合适类型可以增加选择空间，但不保证实例可用。WhenEmpty 与 consolidateAfter: 30m 会使符合条件的空节点在等待该时长后成为候选；预算、PDB 和协调过程仍可能推迟移除。weight: 100 只是相对优先倾向。所引用的默认 EC2NodeClass 和节点身份配置必须已有效。
</details>

14. 编写一个 EC2NodeClass，配置 100Gi gp3 加密根卷、基于标签的子网/安全组选择，并要求使用 IMDSv2。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiSelectorTerms:
  - alias: al2023@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
      example.com/network-role: private
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  instanceProfile: KarpenterNodeInstanceProfile-my-cluster
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      iops: 3000
      throughput: 125
      encrypted: true
      deleteOnTermination: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 1
    httpTokens: required
  tags:
    Environment: production
    ManagedBy: karpenter
```

**解释：**
这是一个 AL2023 学习示例。@latest 解析结果可能变化并触发 Drift；用于生产前，应固定并测试获批的版本或 AMI。私有网络标记是必须真实存在于子网上的自定义标签，并且需验证相应路由。IMDSv2 可减少若干元数据攻击路径，但不能一概防止 SSRF；hop limit 1 可限制许多非 host-network 容器路径，仍需结合 CNI 和 workload identity 设计进行测试。命名的 instance profile、节点访问权限、KMS/卷配置和网络路径都是前置条件。
</details>

15. 编写命令以验证 Karpenter 安装状态并排查预置问题。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# 1. Check Karpenter pod status
kubectl get pods -n karpenter

# 2. Check Karpenter controller logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller

# 3. Check NodePool status
kubectl get nodepool
kubectl describe nodepool default

# 4. Check EC2NodeClass status
kubectl get ec2nodeclass
kubectl describe ec2nodeclass default

# 5. Check pods waiting to be scheduled
kubectl get pods --all-namespaces --field-selector status.phase=Pending

# 6. Check nodes created by Karpenter
kubectl get nodes -l karpenter.sh/nodepool

# 7. Check node details and labels/taints
kubectl describe node <node-name>

# 8. Check Karpenter events
kubectl get events --all-namespaces --sort-by='.metadata.creationTimestamp'
kubectl get nodeclaims -o wide

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Forward the metrics endpoint; keep this terminal open until done.
kubectl port-forward -n karpenter svc/karpenter 8080:8080
```

在另一个终端中，等转发终端显示 ready 后执行：

```bash
curl --fail --show-error http://127.0.0.1:8080/metrics | grep karpenter_
```

**解释：**
应结合检查 controller 就绪状态、NodePool/EC2NodeClass/NodeClaim 条件、Pod 调度事件和 AWS 侧前置条件。Pod 处于 Pending 并不等同于 compute 不足；未找到筛选后的日志行也不能证明操作成功。应在单独终端运行 port-forward 并等待 ready 提示，再从另一个终端获取指标，完成后用 Ctrl+C 停止转发。直接读取该指标不需要 Prometheus server；本文中的命令均未在集群上执行。
</details>

---

**评分：**
- 13-15 题正确：优秀（Karpenter 专家水平）
- 10-12 题正确：良好（能够实际应用）
- 7-9 题正确：一般（建议继续学习）
- 0-6 题正确：不足（需要复习基础概念）

[返回学习资料](../../autoscaling/02-karpenter.md)
