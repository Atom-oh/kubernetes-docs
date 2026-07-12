# Karpenter 测验

本测验测试你对 Karpenter Node 自动扩缩器概念、NodePool/EC2NodeClass 配置、成本优化、Consolidation、Drift、中断处理以及 Amazon EKS 集成的理解。

## 选择题

1. 与现有的 Cluster Autoscaler 相比，Karpenter 最大的区别是什么？
   - A) 更高的 Kubernetes 版本要求
   - B) 不使用 Auto Scaling Groups，直接预置 EC2 instance
   - C) 仅支持 AWS，不支持其他 Cloud
   - D) 仅支持基于 CPU 的扩缩

<details>

<summary>显示答案</summary>

**答案：B) 不使用 Auto Scaling Groups，直接预置 EC2 instance**

**解释：**
Karpenter 最大的差异化点是它绕过 Auto Scaling Groups (ASG)，并直接使用 EC2 Fleet API 来预置 Node。Cluster Autoscaler 通过 node groups/ASGs 进行扩缩，因此 instance types 受 node group 配置限制。Karpenter 会根据 pod 要求，从多种选项中动态选择最佳 instance type，并能在数秒内预置 Node。
</details>

2. 在 Karpenter v1beta1 API 中，哪个 CRD 定义 Node 预置策略？
   - A) Provisioner
   - B) NodePool
   - C) NodeTemplate
   - D) EC2NodeClass

<details>

<summary>显示答案</summary>

**答案：B) NodePool**

**解释：**
在 Karpenter v1beta1 API 中，之前的 Provisioner CRD 已被 NodePool 取代。NodePool 定义 Node 预置策略（instance types、capacity types、architectures、availability zones 等）和 disruption 设置（consolidation、expireAfter 等）。EC2NodeClass 定义 AWS 特定配置（subnets、security groups、AMIs、block devices 等），NodePool 通过 nodeClassRef 引用 EC2NodeClass。
</details>

3. 如何配置 Karpenter 使用 Spot instances 进行成本优化？
   - A) disruption.capacityType: spot
   - B) 在 requirements 中指定 karpenter.sh/capacity-type: spot
   - C) 在 nodeClassRef 中设置 spotEnabled: true
   - D) 在 limits 中设置 spot: true

<details>

<summary>显示答案</summary>

**答案：B) 在 requirements 中指定 karpenter.sh/capacity-type: spot**

**解释：**
使用 NodePool 的 `spec.template.spec.requirements` 中的 `karpenter.sh/capacity-type` key 来指定 capacity type。仅使用 Spot instances 时设置 `values: ["spot"]`，或使用 `values: ["spot", "on-demand"]` 以同时允许两者。Karpenter 会综合价格和可用性选择最佳 instances。与 On-Demand 相比，Spot instances 最高可节省 90% 成本。
</details>

4. Karpenter 的 Consolidation 功能做什么？
   - A) 汇总来自多个 Node 的日志
   - B) 将多个 Node 上的 workloads 整合到更少的 Node 上以节省成本
   - C) 将多个 clusters 整合为一个
   - D) 将多个 NodePools 整合为一个

<details>

<summary>显示答案</summary>

**答案：B) 将多个 Node 上的 workloads 整合到更少的 Node 上以节省成本**

**解释：**
Consolidation 是 Karpenter 的核心成本优化功能。它将 underutilized nodes 上的 workloads 整合（bin-packs）到更少的 Node 上，以提高资源利用率并降低成本。`consolidationPolicy: WhenEmpty` 只移除 empty nodes，而 `consolidationPolicy: WhenUnderutilized` 还会在利用率较低时进行整合。`consolidateAfter` 设置整合前的等待时间。
</details>

5. Karpenter 的 expireAfter 设置有什么用途？
   - A) pod 可以在 Node 上运行的最长时间
   - B) Node 创建后自动替换前的最长时间
   - C) Karpenter controller 的缓存过期时间
   - D) NodePool 策略的有效期

<details>

<summary>显示答案</summary>

**答案：B) Node 创建后自动替换前的最长时间**

**解释：**
`expireAfter` 设置定义 Node 的最长生命周期。例如，设置 `expireAfter: 720h`（30 天）会在 30 天后自动替换 Node。这对于定期刷新 Node 以应用安全补丁、AMI 更新以及使用更新的 instance types 很有用。Karpenter 会遵守 PDBs，在终止现有 Node 前安全地将 workloads 移动到其他 Node。
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
NodePool 的 `spec.limits` 定义该 NodePool 可以预置的最大资源。例如，`limits: { cpu: 1000, memory: 1000Gi }` 将预置限制为总计 1000 个 CPU cores 和 1000Gi memory。这可以实现成本控制和 cluster capacity 管理。当达到 limits 时，Karpenter 不会再预置额外的 Node。
</details>

7. Karpenter 的 Drift 功能会检测并处理什么？
   - A) Network traffic 变化
   - B) 因 NodePool/EC2NodeClass 更改而导致现有 Node 与当前配置不匹配的状态
   - C) Pod 调度漂移
   - D) Kubernetes 版本变更

<details>

<summary>显示答案</summary>

**答案：B) 因 NodePool/EC2NodeClass 更改而导致现有 Node 与当前配置不匹配的状态**

**解释：**
Drift 功能会检测 NodePool 或 EC2NodeClass 配置发生变化，且现有 Node 与新配置不匹配的情况。例如，当你更新 AMI 或更改 security groups 时，现有 Node 会变成 “drifted”。Karpenter 会逐步替换这些 Node，使所有 cluster nodes 都使用最新配置。通过 `featureGates.drift=true` 启用。
</details>

8. EC2NodeClass 中哪个字段设置 Node 的 root volume size 和 type？
   - A) spec.rootVolume
   - B) spec.blockDeviceMappings
   - C) spec.storage
   - D) spec.ebsConfig

<details>

<summary>显示答案</summary>

**答案：B) spec.blockDeviceMappings**

**解释：**
EC2NodeClass 的 `spec.blockDeviceMappings` 定义 EBS volume 配置。使用 `deviceName: /dev/xvda` 指定 root volume，并在 `ebs` 子字段中配置 `volumeSize`、`volumeType`、`iops`、`throughput`、`encrypted`、`kmsKeyID` 等。例如，可以适当配置这些属性以使用加密的 100Gi gp3 volume。
</details>

## 简答题

9. Karpenter 检测到 unschedulable pod 并预置合适 Node 的典型耗时是多少？

<details>

<summary>显示答案</summary>

**答案：数秒内**

**解释：**
Karpenter 在检测到 unschedulable pods 后，会在数秒内预置 Node。相比之下，Cluster Autoscaler 通过 ASGs 扩缩需要数分钟。Karpenter 的快速扩缩来自于直接使用 EC2 Fleet API，并分析 pod 要求以立即选择最佳 instances。对于需要应对突发流量或快速 scale-out 的 workloads，这是一个很大优势。
</details>

10. 当 Karpenter 中存在多个 NodePools 时，优先级如何确定？

<details>

<summary>显示答案</summary>

**答案：使用 weight 字段进行基于权重的优先级排序**

**解释：**
当多个 NodePools 都能满足 pod 的要求时，使用 `spec.weight` 字段指定优先级。weight 值更高的 NodePools 会优先被选择。例如，在 Spot instance NodePool 上设置较高 weight，在 On-Demand NodePool 上设置较低 weight，Karpenter 会先尝试 Spot，如果不可用则使用 On-Demand。
</details>

11. Karpenter 在移除 Node 时会遵守哪个 Kubernetes resource 以确保 workload 可用性？

<details>

<summary>显示答案</summary>

**答案：PDB (PodDisruptionBudget)**

**解释：**
Karpenter 在移除 Node（consolidation、expiration、drift 等）时会遵守 PodDisruptionBudget (PDB)。PDB 定义应用的最低可用性，Karpenter 只会在不违反 PDB 的范围内 drain Node。例如，使用 `minAvailable: 2` 的 PDB 设置时，Karpenter 会确保在移除 Node 的过程中始终至少有 2 个 pods 正在运行。
</details>

12. Karpenter 如何在 EC2NodeClass 中选择要使用的 subnets 和 security groups？

<details>

<summary>显示答案</summary>

**答案：通过 subnetSelectorTerms 和 securityGroupSelectorTerms 进行基于 tag 的选择**

**解释：**
EC2NodeClass 使用 `subnetSelectorTerms` 和 `securityGroupSelectorTerms` 对 subnets 和 security groups 进行基于 tag 的选择。例如，`tags: { karpenter.sh/discovery: "my-cluster" }` 会选择带有该 tag 的资源。AWS resources 必须预先打 tag；当选择了多个 subnets 时，Karpenter 会为了 availability zone 分布而适当地分配它们。
</details>

## 实践题

13. 编写一个 NodePool，它优先使用 Spot instances，允许多种 instance types（m5、c5、r5 families），并在 30 分钟后移除 empty nodes。

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
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
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
        apiVersion: karpenter.k8s.aws/v1
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
  weight: 100
```

**解释：**
这个 NodePool 优先使用 Spot instances 进行成本优化（在 `capacity-type` 中首先列出 spot）。允许多种 instance types 可提高 Spot 可用性和价格优化效果。`consolidationPolicy: WhenEmpty` 与 `consolidateAfter: 30m` 会移除已空置 30 分钟的 Node。`weight: 100` 设置了比其他 NodePools 更高的优先级，因此会优先选择此 NodePool。
</details>

14. 编写一个 EC2NodeClass，包含 100Gi gp3 加密 root volume、基于 tag 的 subnet/security group 选择，以及要求 IMDSv2 的设置。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: secure-nodeclass
spec:
  amiFamily: AL2

  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"
        kubernetes.io/role: "private"

  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: "my-cluster"

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
    httpPutResponseHopLimit: 2
    httpTokens: required  # IMDSv2 required

  tags:
    Environment: production
    ManagedBy: karpenter
```

**解释：**
这个 EC2NodeClass 遵循安全最佳实践。`blockDeviceMappings` 配置一个带加密的 100Gi gp3 volume。`metadataOptions.httpTokens: required` 强制使用 IMDSv2，以防止 SSRF attacks。基于 tag 的 selectors 配置为仅使用 private subnets。`instanceProfile` 引用预先创建的 IAM instance profile。
</details>

15. 编写命令以验证 Karpenter 安装状态并调试预置问题。

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
kubectl get events --field-selector source=karpenter --sort-by='.lastTimestamp'

# 9. Check detailed provisioning logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -c controller | grep -i "provisioning\|creating\|launching"

# 10. Check Karpenter metrics (if Prometheus is configured)
kubectl port-forward -n karpenter svc/karpenter 8080:8080 &
curl localhost:8080/metrics | grep karpenter_
```

**解释：**
排查 Karpenter 问题时，需要检查多个方面。首先确认 controller pods 正常运行且 logs 中没有错误。检查 NodePool 和 EC2NodeClass 的状态与配置。检查 Pending pods 及其原因。常见问题包括 IAM permissions 不足、subnet/security group tag 问题以及 instance limits。Karpenter events 和 metrics 对诊断也很有用。
</details>

---

**评分：**
- 13-15 题正确：优秀（Karpenter 专家级）
- 10-12 题正确：良好（能够实际应用）
- 7-9 题正确：一般（建议进一步学习）
- 0-6 题正确：不足（需要复习基本概念）

[返回学习资料](../../autoscaling/02-karpenter.md)
