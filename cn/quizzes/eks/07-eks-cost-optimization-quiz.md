# Amazon EKS 成本优化测验

> **最后更新**：October 16, 2026

示例是彼此独立的配置选项，并非实际执行的部署或经过测量的节省效果。请将更改合并到现有资源所属方的配置中；不要在同一工作负载上依次应用所有示例。请替换占位应用镜像和由应用负责的钩子，验证账户/上下文/Region 及控制器的兼容性，并在用于实际运维前测试行为。

本测验检验你对 Amazon EKS 集群成本优化策略、工具和最佳实践的理解。

## 测验概览
- 计算资源优化
- 存储成本优化
- 网络成本优化
- 集群管理成本优化
- 成本监控与分析
- 成本优化工具和最佳实践

## 选择题

### 1. 在 Amazon EKS 中，哪种策略最有效地优化计算成本？

- A. 始终使用最大的实例类型
- B. 所有工作负载都只使用按需型实例
- C. 结合使用 Spot Instances、合理调整资源规格和自动扩缩
- D. 将所有工作负载整合到单个节点组
<details>
<summary>显示答案</summary>

**答案：C. 结合使用 Spot Instances、合理调整资源规格和自动扩缩**

**说明：**
在 Amazon EKS 中，优化计算成本最有效的策略是结合使用 Spot Instances、合理调整资源规格和自动扩缩。仅在能够容忍中断且容量允许的情况下使用 Spot，并根据工作负载 SLO 验证节省效果。无论是这种组合还是宣传的最高折扣，都不能保证成本更低或性能保持不变。

**主要计算优化策略：**

1. **使用 Spot Instance**：
   - 与按需型实例相比，最高可节省 90% 成本
   - 适用于容错型工作负载
   - 实施中断处理机制

2. **合理调整资源规格**：
   - 根据实际资源使用量选择实例
   - 消除过度预置的资源
   - 优化资源 requests 和 limits

3. **实施自动扩缩**：
   - 通过 Cluster Autoscaler 或 Karpenter 进行节点级扩缩
   - 通过 Horizontal Pod Autoscaler 进行 Pod 级扩缩
   - 根据需求调整资源

NodePool/EC2NodeClass 需要已安装兼容的 Karpenter controller/CRDs、范围受限的 controller IAM、节点角色、发现资源和中断队列。当前兼容性矩阵要求 EKS 1.36 使用 Karpenter >=1.13。`al2023@latest` 是会动态变化的选择器：请检查解析出的 AMI，并为受控发布固定使用经过测试的别名/AMI。实例列表和容量限制仅为示例，并非支出上限。托管节点组会处理自身的中断流程；避免在 Karpenter 管理的节点上再运行第二个处理程序。

HPA 需要资源指标和 requests；使用 CPU 和 memory 目标时，它会选择所需副本数中的最大值。下面的 VPA 设置为 **Off**，用于提供建议，但不会改变这些分母。`Auto` 已弃用，应改用 `Recreate` 等显式模式；必须协调自动 CPU/memory 更改与 HPA。preStop 钩子会占用终止宽限期，无法保证赶在 Spot 截止时间前完成，也无法保证清理成功。

**实施方法：**

1. **创建使用 Spot Instances 的节点组**：
   ```bash
   # Create Spot Instance node group using eksctl
   eksctl create nodegroup \
     --cluster my-cluster \
     --region us-west-2 \
     --managed \
     --name spot-ng \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --spot
   ```

2. **部署和配置 Karpenter**：
   ```yaml
   # Karpenter NodePool
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m4.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   # Karpenter NodeClass
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **配置 Horizontal Pod Autoscaler**：
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **配置 Vertical Pod Autoscaler**：
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**按工作负载类型划分的优化策略：**

1. **无状态应用**：
   - 优先使用 Spot Instances
   - 实施水平扩缩
   - 跨多个可用区部署

2. **有状态应用**：
   - 混合使用按需型实例和 Spot Instances
   - 选择合适的实例类型
   - 平衡存储性能和成本

3. **批处理作业**：
   - 尽可能多地使用 Spot Instance
   - 实施作业重试机制
   - 在截止时间/容量允许时安排作业；按需型实例没有通用的非高峰时段费率

**最佳实践：**

1. **优化资源 requests 和 limits**：
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         containers:
         - name: web-app
           image: web-app:1.0
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **优化节点亲和性和 Pod 分布**：
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         affinity:
           nodeAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 1
               preference:
                 matchExpressions:
                 - key: node.kubernetes.io/instance-type
                   operator: In
                   values:
                   - m5.large
                   - m5a.large
           podAntiAffinity:
             preferredDuringSchedulingIgnoredDuringExecution:
             - weight: 100
               podAffinityTerm:
                 labelSelector:
                   matchExpressions:
                   - key: app
                     operator: In
                     values:
                     - web-app
                 topologyKey: kubernetes.io/hostname
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

3. **处理 Spot Instance 中断**：
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 3
     template:
       spec:
         terminationGracePeriodSeconds: 60
         containers:
         - name: web-app
           image: web-app:1.0
           lifecycle:
             preStop:
               exec:
                 command:
                 - /bin/sh
                 - -c
                 - sleep 10; /app/cleanup.sh
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

**其他实施注意事项**

- eksctl 配置可以为系统工作负载定义一个按需型组，并为应用定义一个多样化的 Spot 组。仅设置标签不能隔离工作负载。请有意配置 selectors/tolerations；在系统控制器能够运行之前，不要给唯一的引导节点添加污点。
- 在现有 Terraform 模块中，`aws_eks_node_group` 可以设置 `capacity_type = "SPOT"` 和 `scaling_config`。集群、节点 IAM 角色/策略、子网和 provider 必须已经定义。请协调 desired_size 的所有权与 autoscaler。
- EKS 节点组标签不能替代 Cluster Autoscaler 使用的**实际 ASG**发现标签。更改前请检查 ASG，并确认其现有标签的所有者。将 autoscaler 策略绑定到专用控制器身份；附加到节点角色的附加组件权限并非预期的身份。
- 将 AWS 读取/发现操作与两个扩缩写入操作分开。按照[官方 EKS 策略](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)中的做法，将 `autoscaling:SetDesiredCapacity` 和 `autoscaling:TerminateInstanceInAutoScalingGroup` 限制到带有经过审核的启用/集群所有权标签的 ASG。

以下 eksctl 片段会向现有集群添加节点组。请验证资源所有者的私有子网、节点 IAM 策略以及现有组/ASG 标签；这不是独立的集群创建方案。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: system-ng
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 4
  labels:
    workload-type: system
  privateNetworking: true
- name: app-spot-ng
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m4.large
  spot: true
  desiredCapacity: 3
  minSize: 1
  maxSize: 10
  labels:
    workload-type: application
  privateNetworking: true
```

Terraform 片段假定命名的集群/节点角色资源、私有子网变量和 provider 已存在于所属模块中。其 IAM 策略必须附加到专用控制器身份。

```hcl
# Spot managed node group
resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "spot-ng"
  node_role_arn   = aws_iam_role.node_role.arn
  subnet_ids      = var.private_subnet_ids

  capacity_type  = "SPOT"
  instance_types = ["m5.large", "m5a.large", "m5d.large", "m4.large"]

  scaling_config {
    desired_size = 3
    min_size     = 1
    max_size     = 10
  }

  labels = {
    "workload-type" = "application"
  }

  tags = {
    Team        = "platform"
    Environment = "development"
  }
}

# Cluster Autoscaler IAM policy
resource "aws_iam_policy" "cluster_autoscaler" {
  name        = "EKSClusterAutoscalerPolicy"
  description = "Policy for Cluster Autoscaler"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags",
          "autoscaling:DescribeScalingActivities",
          "ec2:DescribeImages",
          "ec2:DescribeInstanceTypes",
          "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup",
          "ec2:DescribeLaunchTemplateVersions"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup"
        ],
        Resource = "*",
        Condition = {
          StringEquals = {
            "aws:ResourceTag/k8s.io/cluster-autoscaler/enabled"                      = "true",
            "aws:ResourceTag/k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
          }
        }
      }
    ]
  })
}
```

其他选项的问题：
- **A. 始终使用最大的实例类型**：这会造成过度预置、产生不必要的成本，而且可能不符合工作负载需求。
- **B. 所有工作负载都只使用按需型实例**：按需型实例比 Spot Instances 更贵，而且许多工作负载都能有效运行在 Spot Instances 上。
- **D. 将所有工作负载整合到单个节点组**：这样难以满足各种工作负载需求，缺乏资源隔离，也会增加成本分摊和优化的难度。
</details>

### 2. 在 Amazon EKS 中，优化存储成本最有效的方法是什么？

- A. 所有工作负载都使用最便宜的存储类型
- B. 将所有数据迁移到 S3
- C. 选择符合工作负载需求的存储类型，并实施生命周期管理
- D. 尽量缩小所有卷的大小
<details>
<summary>显示答案</summary>

**答案：C. 选择符合工作负载需求的存储类型，并实施生命周期管理**

**说明：**
在 Amazon EKS 中，优化存储成本最有效的方法是选择符合工作负载需求的存储类型，并实施生命周期管理。这种方法可在满足性能要求的同时降低成本，并根据数据价值和访问模式使用合适的存储层。

**主要存储优化策略：**

1. **为工作负载选择合适的存储类型**：
   - 高性能需求：io2、gp3 (EBS)
   - 共享访问需求：EFS
   - 大规模数据处理：FSx for Lustre
   - 归档数据：S3、S3 Glacier

2. **存储生命周期管理**：
   - 经常访问的数据：高性能存储
   - 偶尔访问的数据：标准存储
   - 很少访问的数据：低成本归档存储

3. **高效管理卷**：
   - 设置合适的卷大小
   - 识别并删除未使用的卷
   - 管理快照生命周期

StorageClass 示例需要已安装 CSI 驱动程序，并正确配置 IAM/KMS/拓扑。`WaitForFirstConsumer` 会使 EBS 预置与调度相匹配；`Retain` 会使已释放的卷继续产生费用，直到所有者处理它们。已绑定的 PVC 不能就地更改存储类或缩小容量。快照/恢复或受支持的卷类型修改需要由所有者审核迁移方案并测试恢复。Auto Mode 使用不同的 EBS provisioner；不要在标准 CSI 示例中悄然替换它。

`create-file-system` 没有 `--lifecycle-policies` 选项。请对现有文件系统使用 `put-lifecycle-configuration`，并保留如下所示的完整目标策略数组。S3 转换还需要审查最短存储期限/大小、请求成本、版本控制和恢复延迟；替换生命周期配置时必须保留无关规则。

**实施方法：**

1. **优化 EBS 卷**：
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: ebs-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     iops: '3000'
     throughput: '125'
     encrypted: 'true'
   allowVolumeExpansion: true
   volumeBindingMode: WaitForFirstConsumer
   reclaimPolicy: Retain
   ```

2. **EFS 生命周期管理**：
   ```bash
   set -euo pipefail
   : "${AWS_REGION:?Set the reviewed Region}"
   : "${FILE_SYSTEM_ID:?Set the existing reviewed EFS filesystem ID}"
   aws efs describe-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" --query LifecyclePolicies --output json \
     > efs-lifecycle-policies.json
   # Edit the exported array; an IA entry is {"TransitionToIA":"AFTER_30_DAYS"}.
   # Preserve required Archive/return-to-primary entries before submitting the whole policy.
   aws efs put-lifecycle-configuration --region "$AWS_REGION" \
     --file-system-id "$FILE_SYSTEM_ID" \
     --lifecycle-policies file://efs-lifecycle-policies.json
   ```

3. **S3 生命周期策略**：
   ```json
   {
     "Rules": [
       {
         "ID": "Move to IA after 30 days, Glacier after 90 days",
         "Status": "Enabled",
         "Transitions": [
           {
             "Days": 30,
             "StorageClass": "STANDARD_IA"
           },
           {
             "Days": 90,
             "StorageClass": "GLACIER"
           }
         ],
         "Expiration": {
           "Days": 365
         },
         "Filter": {
           "Prefix": "eks-backups/"
         }
       }
     ]
   }
   ```

4. **EBS 快照生命周期管理**：
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

**定期快照和存储审查**

下方快照计划处于暂停状态，直到所有者确认现有的 `team-a/database-data` PVC、标准 EBS CSI 驱动程序、快照控制器/CRDs 和 `ebs-snapshot` 类。挂载的模板使用 `generateName`，以避免固定名称冲突。Role 允许在此命名空间中创建快照；它不会限制来源 PVC 字段。应用一致性/暂停写入和恢复验证属于单独的责任。Job 成功只表示 API 对象已创建，并不表示快照已就绪；请单独监控 `readyToUse` 和错误。Job 历史限制**不会**使 VolumeSnapshots/EBS 快照过期。启用计划前，请明确保留期限和恢复责任；删除 Kubernetes 快照时，`deletionPolicy: Delete` 会删除底层快照。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: snapshot-creator
  namespace: team-a
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: snapshot-creator
  namespace: team-a
rules:
- apiGroups: ["snapshot.storage.k8s.io"]
  resources: ["volumesnapshots"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: snapshot-creator
  namespace: team-a
subjects:
- kind: ServiceAccount
  name: snapshot-creator
  namespace: team-a
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: snapshot-creator
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: snapshot-templates
  namespace: team-a
data:
  snapshot.yaml: |
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      generateName: database-data-
      namespace: team-a
    spec:
      volumeSnapshotClassName: ebs-snapshot
      source:
        persistentVolumeClaimName: database-data
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: volume-snapshot
  namespace: team-a
spec:
  suspend: true
  schedule: "0 1 * * *"
  timeZone: Etc/UTC
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 1800
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      template:
        spec:
          serviceAccountName: snapshot-creator
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 65532
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: snapshot-creator
            image: registry.k8s.io/kubectl:v1.36.2
            command: ["kubectl"]
            args: ["create", "-f", "/snapshots/snapshot.yaml", "--namespace=team-a"]
            env:
            - name: HOME
              value: /tmp
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop: ["ALL"]
            resources:
              requests:
                cpu: 10m
                memory: 32Mi
              limits:
                memory: 128Mi
            volumeMounts:
            - name: snapshots
              mountPath: /snapshots
              readOnly: true
            - name: tmp
              mountPath: /tmp
          volumes:
          - name: snapshots
            configMap:
              name: snapshot-templates
          - name: tmp
            emptyDir: {}
```

根据访问语义和恢复目标匹配存储：数据库可能需要 io2/gp3 IOPS，共享 Web 内容可能适合 EFS，日志/归档通常适合 S3，分析/AI 可能需要 FSx for Lustre 或 EBS 吞吐量。热/温/冷是分类示例，并非自动执行的 EBS→EFS→S3 迁移流水线。请另行准备引用的 `efs-standard`/`ebs-io2` 类。EFS PVC 请求 `100Gi` 不会强制执行文件系统配额，也不会购买相应容量；PVC 标签也不会自动成为 AWS 账单标签。

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: hot-data
  namespace: team-a
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-gp3
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: warm-data
  namespace: team-a
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: efs-standard
  resources:
    requests:
      storage: 100Gi
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-data
  labels:
    app: database
    environment: production
    cost-center: cc-123
  namespace: team-a
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: ebs-io2
  resources:
    requests:
      storage: 100Gi
```

以下 Terraform 片段要求已存在并配置好的 providers/caller identity，以及经过审核的资源所有权。挂载目标、网络/IAM 访问、应用备份和保留策略是单独的前提条件；这不是完整的生产存储部署方案。

```hcl
# Standard EBS CSI gp3 StorageClass
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "ebs-gp3"
  }
  storage_provisioner = "ebs.csi.aws.com"
  parameters = {
    type       = "gp3"
    iops       = "3000"
    throughput = "125"
    encrypted  = "true"
  }
  allow_volume_expansion = true
  volume_binding_mode    = "WaitForFirstConsumer"
  reclaim_policy         = "Retain"
}

# Encrypted EFS filesystem
resource "aws_efs_file_system" "eks_efs" {
  creation_token = "eks-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name = "eks-efs"
  }
}

# S3 bucket and lifecycle policy
resource "aws_s3_bucket" "eks_data" {
  bucket = "eks-data-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "eks-data"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "eks_data_lifecycle" {
  bucket = aws_s3_bucket.eks_data.id

  rule {
    id     = "archive-rule"
    status = "Enabled"

    filter {
      prefix = "eks-backups/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}
```

**只读 PVC 候选项清单**

将下面的 Python 保存为 `unreferenced_pvcs.py`，并使用显式的 context/namespace 命令。它会报告在提供的当前 Pod 快照中未被引用的 Bound PVC，并按 `(namespace, name)` 比较，同时处理非 PVC 卷。Kubernetes 没有提供标准的 `pv_used` annotation。列表快照并非原子快照，也不包括未来/缩容后的控制器消费者、待处理的作业以及备份/恢复要求。不能仅凭此输出作出删除决定。对于 EBS 候选项，请使用 [EKS06 第 6 题](06-eks-monitoring-logging-quiz.md)中按账户/标签限定范围的查询；`available` 表示未附加，并不表示未使用。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Select the reviewed cluster context}"
: "${KUBE_NAMESPACE:?Select the reviewed namespace}"
kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
  get pvc --chunk-size=500 -o json > pvcs.json
kubectl --context "$KUBE_CONTEXT" --namespace "$KUBE_NAMESPACE" \
  get pods --chunk-size=500 -o json > pods.json
python3 unreferenced_pvcs.py
```

```python
import json
from pathlib import Path


def unreferenced_claims(claims, pods):
    referenced = set()
    for pod in pods["items"]:
        namespace = pod["metadata"]["namespace"]
        for volume in pod.get("spec", {}).get("volumes") or []:
            claim = volume.get("persistentVolumeClaim")
            if claim:
                referenced.add((namespace, claim["claimName"]))
    result = []
    for claim in claims["items"]:
        metadata = claim["metadata"]
        identity = (metadata["namespace"], metadata["name"])
        if claim.get("status", {}).get("phase") != "Bound" or identity in referenced:
            continue
        spec = claim.get("spec", {})
        result.append({
            "namespace": identity[0],
            "name": identity[1],
            "storageClass": spec.get("storageClassName"),
            "requested": ((spec.get("resources") or {}).get("requests") or {}).get("storage"),
            "meaning": "not referenced by the supplied current Pod snapshot; review required",
        })
    return result


if __name__ == "__main__":
    claims = json.loads(Path("pvcs.json").read_text())
    pods = json.loads(Path("pods.json").read_text())
    print(json.dumps(unreferenced_claims(claims, pods), indent=2))
```

其他选项的问题：
- **A. 所有工作负载都使用最便宜的存储类型**：最便宜的存储可能无法满足性能要求，进而降低应用性能并影响业务。
- **B. 将所有数据迁移到 S3**：S3 适用于某些数据类型，但不适合延迟敏感型工作负载或需要块存储的应用。
- **D. 尽量缩小所有卷的大小**：卷大小过小可能导致空间不足，而且某些卷类型（例如 gp2）的性能由大小决定。
</details>

### 3. 在 Amazon EKS 中，优化网络成本最有效的策略是什么？

- A. 所有流量都使用最昂贵的网络带宽
- B. 将所有 Service 放在同一个可用区
- C. 优化流量模式，最大限度地降低数据传输成本，并使用 VPC endpoint
- D. 阻止所有网络流量
<details>
<summary>显示答案</summary>

**答案：C. 优化流量模式，最大限度地降低数据传输成本，并使用 VPC endpoint**

**说明：**
在 Amazon EKS 中，优化网络成本最有效的策略是优化流量模式、最大限度地降低数据传输成本，并使用 VPC endpoint。通过考虑 AWS 网络成本模型，这种方法可以提高网络流量效率并减少不必要的成本。

**主要网络成本优化策略：**

1. **优化流量模式**：
   - 尽量减少跨可用区流量
   - 尽量减少跨 Region 流量
   - 实施具备本地性意识的路由

2. **最大限度地降低数据传输成本**：
   - 使用压缩和高效的数据格式
   - 实施缓存策略
   - 消除不必要的数据传输

3. **使用 VPC endpoint**：
   - 与 AWS 服务建立私有连接
   - 绕过 internet gateway
   - 降低数据传输成本

拓扑分布控制 Pod 放置位置；它不会选择 Service 流量使用的 endpoint。`spec.topologyKeys` 已被移除。此示例使用 `trafficDistribution: PreferSameZone`（在 Kubernetes 1.35+ 中稳定），并在无法满足时回退；它并不能保证跨 AZ 流量为零。请验证实际 proxy/CNI 行为和可用性约束。

S3/DynamoDB gateway endpoint 的定价与 interface endpoint 不同。ECR 镜像拉取需要 `ecr.api`、`ecr.dkr` 和 S3 连接、private DNS，以及 endpoint security group 对来自预期节点/Pods 的 TCP 443 入站规则。CLI 示例展示了一个 interface endpoint；请像下方 Terraform 片段一样配置其 DKR 对应端点。请审查 endpoint policy 和实际区域流量/成本模型；“私有”不代表免费。

**实施方法：**

1. **按可用区感知放置 Pod**：
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
   spec:
     replicas: 6
     template:
       spec:
         topologySpreadConstraints:
         - maxSkew: 1
           topologyKey: topology.kubernetes.io/zone
           whenUnsatisfiable: DoNotSchedule
           labelSelector:
             matchLabels:
               app: web-app
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
       metadata:
         labels:
           app: web-app
     selector:
       matchLabels:
         app: web-app
   ```

2. **Service 拓扑路由**：
   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: web-app
   spec:
     selector:
       app: web-app
     ports:
     - port: 80
       targetPort: 8080
     trafficDistribution: PreferSameZone
   ```

3. **配置 VPC endpoint**：
   ```bash
   # Create S3 VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.s3 \
     --route-table-ids rtb-12345678

   # Create DynamoDB VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.dynamodb \
     --route-table-ids rtb-12345678

   # Create ECR API VPC endpoint
   aws ec2 create-vpc-endpoint \
     --vpc-id vpc-12345678 \
     --service-name com.amazonaws.us-west-2.ecr.api \
     --vpc-endpoint-type Interface \
     --subnet-ids subnet-12345678 subnet-87654321 \
     --security-group-ids sg-12345678 \
     --private-dns-enabled
   ```

4. **使用 Istio 进行本地性路由**：
   ```yaml
   apiVersion: networking.istio.io/v1
   kind: DestinationRule
   metadata:
     name: web-app
   spec:
     host: web-app
     trafficPolicy:
       loadBalancer:
         simple: LEAST_REQUEST
         localityLbSetting:
           enabled: true
       outlierDetection:
         consecutive5xxErrors: 5
         interval: 5s
         baseEjectionTime: 30s
   ```

Istio 本地性故障转移需要 endpoint 本地性信息和异常检测。`failover.from/to` 表示的是 **Region**，因此在那里填写 AZ 名称是不正确的。上面的 DestinationRule 使用默认本地性优先级（同一 zone 优先于其他 zone/Region）和异常检测；示例中的驱逐阈值需要在工作负载上进行测试。这是 kube-proxy Service 流量分布的单独选项；仅为降低传输成本并不需要服务网格。



**其他路由、endpoint 和账单示例**

NetworkPolicy 允许同一命名空间内 frontend→API→database 流量，以及标准 CoreDNS Deployment 路径。请添加其他必需依赖并验证 CNI 是否强制执行策略。Auto Mode 节点本地 DNS 或其他 resolver 路径需要单独配置适当的放行规则。请将 selectors 与实际托管标签匹配。

VirtualService 会评估第一个匹配规则，因此 premium 匹配必须排在 catch-all 规则之前，并定义相匹配的 DestinationRule subsets。工作负载必须带有相应的 version 标签。客户端提供的最终用户 header 不能证明其具有相应权限；请在服务器端执行授权。EnvoyFilter 会定位到实际的 ingress gateway 命名空间/标签，并且需要根据已安装的 Istio/Envoy 版本进行验证。它会在 gateway 压缩 HTTP 响应；仅安装 outbound sidecar compressor 并不会自动压缩上传内容。旧版 content_length/content_type 字段已弃用，但尚未移除。此示例使用 response_direction_config/common_config；请测试 CPU、延迟、安全性和协议行为。

Terraform 片段假定 VPC、私有子网、endpoint security group 和路由表已存在于所属模块中。NAT 和路由关联仍由该 VPC 的所有者管理。在多个 AZ 之间共享单个 zonal NAT 是可用性/传输成本权衡，并非默认的高可用节省方案；请单独评估 regional NAT 选项。

将 Python 保存为 network_costs.py。设置 EXPECTED_CALLER_ACCOUNT、LINKED_ACCOUNT_ID、START_DATE 和 END_DATE。reviewed-usage-types.json 必须包含一个 JSON 数组，数组中是从 Cost Explorer/GetDimensionValues 选出的精确 USAGE_TYPE 值。此示例使用位于 us-east-1 的 AWS 商业区账单 endpoint；请验证调用账户和读取权限。API 查询可能会产生费用。GetCostAndUsage 中的维度不支持 CONTAINS，因此辅助函数使用精确的 EQUALS 过滤器。它会完成分页，并保留 Decimal 金额、货币单位和估算状态。结果为空/查询失败不能证明网络总成本为零。账户级行需要额外验证标签/资源映射后才能归属到特定 EKS 集群。结果仅涵盖所选的使用类型；模糊的服务/Regional/Region 子字符串匹配无法可靠地将互联网、AZ 和跨 Region 费用分类。日期使用 UTC，End 为排除端点；请检查可用历史数据和账单最终状态。此前的 100/50/200 USD 阈值只是用于初步排查的示例值，并非通用的优化决策。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - api-server
              topologyKey: topology.kubernetes.io/zone
      containers:
      - name: database
        image: registry.example.com/team/database:REVIEWED_TAG
    metadata:
      labels:
        app: database
  selector:
    matchLabels:
      app: database
```

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
spec:
  hosts:
  - api-service
  http:
  - match:
    - headers:
        end-user:
          exact: premium-user
    route:
    - destination:
        host: api-service
        subset: premium
  - route:
    - destination:
        host: api-service
        subset: v1
      weight: 90
    - destination:
        host: api-service
        subset: v2
      weight: 10
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-subsets
spec:
  host: api-service
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: premium
    labels:
      version: premium
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: compression-filter
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.compressor
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.compressor.v3.Compressor
          response_direction_config:
            common_config:
              min_content_length: 100
              content_type:
              - application/json
              - text/html
          compressor_library:
            name: gzip
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.compression.gzip.compressor.v3.Gzip
              memory_level: 3
              window_bits: 10
              compression_level: BEST_COMPRESSION
              compression_strategy: DEFAULT_STRATEGY
```

```
+-------------------+    +-------------------+    +-------------------+
|                   |    |                   |    |                   |
|  VPC Endpoint     |    |  NAT Gateway      |    |  Internet         |
|  (AWS Services)   |    |  (External APIs)  |    |  Gateway          |
+-------------------+    +-------------------+    +-------------------+
        |                        |                        |
        v                        v                        v
+---------------------------------------------------------------+
|                                                               |
|                  EKS Cluster VPC                              |
|                                                               |
+---------------------------------------------------------------+
        |                        |                        |
        v                        v                        v
+-------------------+    +-------------------+    +-------------------+
|                   |    |                   |    |                   |
|  AZ-a             |    |  AZ-b             |    |  AZ-c             |
|  Workloads        |    |  Workloads        |    |  Workloads        |
|                   |    |                   |    |                   |
+-------------------+    +-------------------+    +-------------------+
        |                        |                        |
        v                        v                        v
+---------------------------------------------------------------+
|                                                               |
|                  Service Mesh                                 |
|                  (Locality-aware routing)                     |
|                                                               |
+---------------------------------------------------------------+
```

```hcl
# Gateway VPC endpoints
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.s3"
  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "s3-endpoint"
  }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  route_table_ids   = [aws_route_table.private.id]
  vpc_endpoint_type = "Gateway"

  tags = {
    Name = "dynamodb-endpoint"
  }
}

# Interface VPC endpoints
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-api-endpoint"
  }
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "ecr-dkr-endpoint"
  }
}
```

```python
import json
import os
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import boto3
from botocore.config import Config


def network_cost_rows(client, start, end, linked_account, usage_types):
    for value in [start, end]:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use YYYY-MM-DD dates")
    if start >= end:
        raise ValueError("Start must precede exclusive End")
    if not re.fullmatch(r"[0-9]{12}", linked_account):
        raise ValueError("A reviewed linked account ID is required")
    if not isinstance(usage_types, list) or not usage_types or any(
        not isinstance(value, str) or not value.strip() for value in usage_types
    ):
        raise ValueError("Provide exact reviewed USAGE_TYPE values")
    request = {
        "TimePeriod": {"Start": start, "End": end},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
        ],
        "Filter": {
            "And": [
                {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account],
                                "MatchOptions": ["EQUALS"]}},
                {"Dimensions": {"Key": "USAGE_TYPE", "Values": usage_types,
                                "MatchOptions": ["EQUALS"]}},
            ]
        },
    }
    rows = []
    seen_tokens = set()
    for _ in range(100):
        response = client.get_cost_and_usage(**request)
        for period in response["ResultsByTime"]:
            for group in period["Groups"]:
                service, usage_type = group["Keys"]
                metric = group["Metrics"]["UnblendedCost"]
                amount = Decimal(metric["Amount"])
                if not amount.is_finite() or not metric["Unit"]:
                    raise ValueError("Invalid monetary amount/unit")
                rows.append({
                    "start": period["TimePeriod"]["Start"],
                    "endExclusive": period["TimePeriod"]["End"],
                    "service": service,
                    "usageType": usage_type,
                    "amount": str(amount),
                    "unit": metric["Unit"],
                    "estimated": period.get("Estimated"),
                })
        token = response.get("NextPageToken")
        if not token:
            return rows
        if token in seen_tokens:
            raise RuntimeError("Repeated pagination token")
        seen_tokens.add(token)
        request["NextPageToken"] = token
    raise RuntimeError("Page limit exceeded; narrow the query")


def main():
    expected_caller = os.environ["EXPECTED_CALLER_ACCOUNT"]
    if not re.fullmatch(r"[0-9]{12}", expected_caller):
        raise ValueError("Set the reviewed calling account")
    session = boto3.Session(region_name="us-east-1")
    config = Config(connect_timeout=5, read_timeout=30,
                    retries={"mode": "standard", "total_max_attempts": 4})
    identity = session.client("sts", config=config).get_caller_identity()
    if identity["Account"] != expected_caller:
        raise RuntimeError("Calling account mismatch")
    usage_types = json.loads(Path("reviewed-usage-types.json").read_text())
    rows = network_cost_rows(
        session.client("ce", config=config),
        os.environ["START_DATE"], os.environ["END_DATE"],
        os.environ["LINKED_ACCOUNT_ID"], usage_types,
    )
    print(json.dumps({"basis": "UnblendedCost", "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
```

其他选项的问题：
- **A. 所有流量都使用最昂贵的网络带宽**：这会造成不必要的成本，而且并非所有工作负载都需要高带宽。
- **B. 将所有 Service 放在同一个可用区**：这可能无法满足关键工作负载的多 AZ 可用性要求。对于非关键环境，选择单 AZ 仍需明确评估容错要求。
- **D. 阻止所有网络流量**：这不切实际，会严重限制应用功能。
</details>

### 4. 优化 Amazon EKS 集群管理成本最有效的方法是什么？

- A. 尽可能多地创建集群
- B. 将所有工作负载整合到单个集群
- C. 根据工作负载需求优化集群数量，并尽量减少管理开销
- D. 手动管理集群
<details>
<summary>显示答案</summary>

**答案：C. 根据工作负载需求优化集群数量，并尽量减少管理开销**

**说明：**
优化 Amazon EKS 集群管理成本最有效的方法是根据工作负载需求优化集群数量，并尽量减少管理开销。这种方法可在满足工作负载隔离和安全要求的同时，平衡集群管理成本和运维复杂性。

**主要集群管理成本优化策略：**

1. **保持适当的集群数量**：
   - 根据业务需求拆分集群
   - 按环境拆分集群（开发、预发布、生产）
   - 考虑安全和合规要求

2. **尽量减少管理开销**：
   - 使用自动化集群管理工具
   - 实施基础设施即代码（IaC）
   - 集中监控和日志记录

3. **优化集群资源**：
   - 选择合适的 control plane 配置
   - 高效管理节点组
   - 使用共享服务

简短的 eksctl 命令展示的是创建操作，并非生产环境网络/IAM 预设。请从 AWS 目录中选择 EKS 版本，按照[创建指南](../../eks/02-eks-cluster-creation.md)检查 VPC 和 API endpoint 暴露情况，并将控制器权限保留在专用身份上。节点组大小界限不会安装 autoscaler，也不会形成支出上限。标准/延长支持费用、可选的 Provisioned Control Plane 容量和共享管理依赖项也会影响比较结果。

Terraform 示例使用经过检查的模块 **21.25.0**，其 AWS provider 最低版本为 **6.59**；示例所示的 provider 固定版本为 6.69.1。输入不会默认填入猜测的环境值。请提供所属方管理的私有网络和 API 可达性、经过审核的 access entries、带 IAM 关联且兼容/固定版本的附加组件，以及托管节点组。标准 EC2 节点需要适当的 CNI/DNS/proxy 路径；这不是 Auto Mode 示例。请协调 desired-size 的所有权与 autoscaler，并在隔离模型要求时使用单独的 state/provider 身份。此处未执行 plan/apply，也未宣称其已可用于生产环境。

**实施方法：**

1. **优化 EKS 集群配置**：
   ```bash
   : "${EKS_VERSION:?Select a version offered by the AWS EKS support catalog}"
   # Create optimized cluster using eksctl
   eksctl create cluster \
     --name optimized-cluster \
     --region us-west-2 \
     --version "$EKS_VERSION" \
     --nodegroup-name standard-workers \
     --node-type m5.large \
     --nodes-min 2 \
     --nodes-max 10 \
     --managed
   ```

2. **使用 Terraform 自动化集群管理**：
   ```hcl
   terraform {
     required_version = ">= 1.5.7"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "= 6.69.1"
       }
     }
   }

   variable "region" { type = string }
   variable "account_id" { type = string }
   variable "cluster_name" { type = string }
   variable "environment" { type = string }
   variable "kubernetes_version" { type = string }
   variable "vpc_id" { type = string }
   variable "private_subnet_ids" { type = list(string) }
   variable "reviewed_addons" { type = any }
   variable "reviewed_access_entries" { type = any }
   variable "managed_groups" { type = any }

   provider "aws" {
     region              = var.region
     allowed_account_ids = [var.account_id]
   }

   module "eks" {
     source  = "terraform-aws-modules/eks/aws"
     version = "21.25.0"

     name                    = var.cluster_name
     kubernetes_version      = var.kubernetes_version
     endpoint_private_access = true
     endpoint_public_access  = false
     vpc_id                  = var.vpc_id
     subnet_ids              = var.private_subnet_ids

     addons                  = var.reviewed_addons
     access_entries          = var.reviewed_access_entries
     eks_managed_node_groups = var.managed_groups
     tags = {
       Environment = var.environment
       Terraform   = "true"
     }
   }
   ```

3. **使用 GitOps 管理集群配置**：
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: cluster-config
     namespace: argocd
   spec:
     project: cluster-config
     source:
       repoURL: https://github.com/myorg/cluster-config.git
       targetRevision: REPLACE_WITH_REVIEWED_COMMIT_SHA
       path: configs
     destination:
       server: https://kubernetes.default.svc
       namespace: default
     syncPolicy:
       automated:
         enabled: false
         prune: false
         selfHeal: false
   ```

4. **多租户集群配置**：
   ```yaml
   # Namespace resource quota
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: team-a-quota
     namespace: team-a
   spec:
     hard:
       requests.cpu: "10"
       requests.memory: 20Gi
       limits.cpu: "20"
       limits.memory: 40Gi
       pods: "50"
       services: "20"
       persistentvolumeclaims: "30"
   ```

**隔离、环境输入和了解上下文的证据**

Argo CD Application 需要已安装的控制器、经过审核的仓库/commit，以及预先创建的 `cluster-config` AppProject，用于限制仓库、目标位置和资源类型。使用前请替换占位 SHA 和仓库地址。初次审查时会禁用自动同步/修剪；只有在所有者确认所需协调行为后才启用。共享管理凭证/控制器可能扩大原本独立的集群之间的故障或安全影响范围。

ResourceQuota 限制的是准入和对象数量，不是账单或租户授权。NetworkPolicy 在多个策略间以叠加方式生效，并且需要 CNI 执行。命名空间示例允许 `team-a` 内部流量、与指定共享命名空间之间的流量，以及到标准 CoreDNS Deployment 的流量；请明确调整 node-local/Auto Mode DNS 和其他依赖项。共享 API 示例仅允许 `team-a` 访问带有 `app: shared-api` 标签、TCP 8080 端口上的 Pods。请协调现有的宽泛策略，不要让旧的 allow-all 策略继续生效。RBAC、准入、IAM 和信任边界仍是独立控制措施。

下面的环境 tfvars 是对上述经过审核的模块的覆盖值，并非调用未提供的 `./modules/eks-cluster`。请将合适的账户/网络/版本/附加组件/访问值合并到各环境的输入中，并使用各自独立的 state/backend 和身份。实例列表和数量仅为示例；请检查中断容忍度和当前区域选项。

该采集脚本每次运行只处理**一个显式指定的 context**。请设置 `KUBE_CONTEXT`、`EXPECTED_API_SERVER`、`EXPECTED_CALLER_ACCOUNT`、`LINKED_ACCOUNT_ID`、`BILLING_TAG_KEY`、`BILLING_TAG_VALUE`、`START_DATE` 和 `END_DATE`；对每个集群有意识地重复执行。API-server URL 必须与经过审核的 EKS 集群匹配。脚本会保存带时间戳/窗口/单位的实际 Metrics API 样本，以及所有按标签限定范围的 Cost Explorer 分页结果，而不是把一个 context 的请求资源重新标记为每个集群的使用率。前提条件包括 Metrics Server 和读取权限。缺少节点样本不代表使用量为零，短时间样本也不是峰值需求历史记录。

此脚本使用 AWS 商业区账单 endpoint 和排除端点形式的结束日期。请选用可用账单历史；之前的 2023 日期只是配置示例，并非测量结果。账单中的标签映射必须存在，而且可能遗漏无标签/共享费用。脚本会保留原始金额单位、成本依据和估算状态；不会根据第一组数据推断总额，也不会根据 request/capacity 阈值建议缩容。

较大的共享集群可以减少重复的 control-plane/共享服务开销，但会增加协调成本和故障影响。较小的集群有助于实现独立维护和工作负载边界，但会增加重复容量和运维工作。请根据信任、工作负载和恢复要求选择混合拆分方案；集群数量本身不能保证隔离或降低总成本。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-isolation
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: shared-services
  egress:
  - to:
    - podSelector: {}
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: shared-services
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shared-services
  labels:
    name: shared-services
    access: global
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-team-a
  namespace: shared-services
spec:
  podSelector:
    matchLabels:
      app: shared-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: team-a
    ports:
    - protocol: TCP
      port: 8080
```

```hcl
# production.tfvars: merge with the production account/network/add-on/access inputs.
cluster_name = "production"
environment  = "production"
managed_groups = {
  critical = {
    instance_types = ["m5.large"]
    capacity_type  = "ON_DEMAND"
    min_size       = 3
    max_size       = 10
    desired_size   = 3
  }
  general = {
    instance_types = ["m5.large", "m5a.large"]
    capacity_type  = "SPOT"
    min_size       = 3
    max_size       = 20
    desired_size   = 3
  }
}
```

```hcl
# development.tfvars: use a separate state/backend and the development identity.
cluster_name = "development"
environment  = "development"
managed_groups = {
  default = {
    instance_types = ["m5.large", "m5a.large"]
    capacity_type  = "SPOT"
    min_size       = 1
    max_size       = 5
    desired_size   = 1
  }
}
```

```python
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path


def read_json(command):
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    return json.loads(completed.stdout)


def collect(context, expected_server, caller_account, linked_account, tag_key, tag_value, start, end,
            run=subprocess.run, query=read_json):
    if not all([context, expected_server, tag_key, tag_value]):
        raise ValueError("Explicit context, API server, and billing tag mapping are required")
    if not all(re.fullmatch(r"[0-9]{12}", account) for account in [caller_account, linked_account]):
        raise ValueError("Use reviewed 12-digit account IDs")
    if any(date.fromisoformat(value).isoformat() != value for value in [start, end]) or start >= end:
        raise ValueError("Use YYYY-MM-DD with Start before exclusive End")
    server = run(
        ["kubectl", "--context", context, "config", "view", "--minify",
         "--output", "jsonpath={.clusters[0].cluster.server}"],
        check=True, capture_output=True, text=True, timeout=30,
    ).stdout.strip()
    if server != expected_server:
        raise RuntimeError("Kubernetes context/API-server mismatch")
    identity = query(["aws", "sts", "get-caller-identity", "--region", "us-east-1",
                      "--output", "json", "--no-cli-pager"])
    if identity["Account"] != caller_account:
        raise RuntimeError("Calling AWS account mismatch")
    usage = query(["kubectl", "--context", context, "get", "--raw",
                   "/apis/metrics.k8s.io/v1beta1/nodes"])
    if usage.get("kind") != "NodeMetricsList" or not isinstance(usage.get("items"), list):
        raise ValueError("Unexpected node metrics response")
    expression = {"And": [
        {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [linked_account], "MatchOptions": ["EQUALS"]}},
        {"Tags": {"Key": tag_key, "Values": [tag_value], "MatchOptions": ["EQUALS"]}},
    ]}
    base = [
        "aws", "ce", "get-cost-and-usage", "--region", "us-east-1",
        "--time-period", json.dumps({"Start": start, "End": end}),
        "--granularity", "MONTHLY", "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=SERVICE",
        "--filter", json.dumps(expression), "--output", "json", "--no-cli-pager",
    ]
    pages = []
    token = None
    seen = set()
    for _ in range(100):
        page = query(base + (["--next-page-token", token] if token else []))
        if not isinstance(page.get("ResultsByTime"), list):
            raise ValueError("Unexpected cost response")
        pages.append(page)
        token = page.get("NextPageToken")
        if not token:
            return {
                "context": context, "apiServer": server, "nodeUsage": usage,
                "billingScope": expression, "basis": "UnblendedCost", "costPages": pages,
            }
        if token in seen:
            raise RuntimeError("Repeated cost pagination token")
        seen.add(token)
    raise RuntimeError("Page limit exceeded; narrow the query")


if __name__ == "__main__":
    result = collect(
        os.environ["KUBE_CONTEXT"], os.environ["EXPECTED_API_SERVER"],
        os.environ["EXPECTED_CALLER_ACCOUNT"], os.environ["LINKED_ACCOUNT_ID"],
        os.environ["BILLING_TAG_KEY"], os.environ["BILLING_TAG_VALUE"],
        os.environ["START_DATE"], os.environ["END_DATE"],
    )
    Path("cluster-cost-and-usage.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Saved raw metrics and tag-scoped billing pages; no resizing recommendation was made.")
```

其他选项的问题：
- **A. 尽可能多地创建集群**：这会增加每个集群的 control plane 成本和管理开销，降低资源利用率。
- **B. 将所有工作负载整合到单个集群**：在某些环境中这样做可能合适，但它没有考虑安全要求、工作负载隔离和故障影响范围。
- **D. 手动管理集群**：手动管理会增加出错概率、降低一致性并增加运维开销。
</details>

### 5. 在 Amazon EKS 中，进行成本监控和分摊最有效的方法是什么？

- A. 只查看 AWS 账单
- B. 实施标签策略、成本分配工具和持续监控
- C. 将相同成本分摊给所有资源
- D. 使用资源时不进行成本监控
<details>
<summary>显示答案</summary>

**答案：B. 实施标签策略、成本分配工具和持续监控**

**说明：**
在 Amazon EKS 中，进行成本监控和分摊最有效的方法是实施标签策略、成本分配工具和持续监控。这种方法有助于准确跟踪成本、按团队或项目分摊成本，并发现成本优化机会。

**主要成本监控和分摊策略：**

1. **全面的标签策略**：
   - 根据业务部门、团队、项目和环境添加标签
   - 实施一致的标签规则
   - 实施自动标记

2. **使用成本分配工具**：
   - AWS Cost Explorer 和 AWS Budgets
   - Kubecost 或 CloudHealth 等专业工具
   - 自定义仪表板和报告

3. **持续监控和优化**：
   - 定期审查和分析成本
   - 异常检测和告警
   - 实施优化建议

Kubernetes labels、AWS 资源标签和已激活的账单标签彼此不同。Namespace 标签不会自动传播到 Pods 或 AWS 资源；请将工作负载标签添加到 Pod 模板。下面所示的 Organizations tag policy 会验证受支持资源（包括 EKS 集群）上配置的标签键/值。它不会添加标签，也不会配置必需标签的强制执行。请审查继承的策略，并单独配置缺失标签控制。账单激活/回填是单独的操作；最多 12 个月的回填要求相关标签在历史时期确实存在。

下面的 CUR 命令创建的是**旧版 CUR**，并非 Cost Explorer 仪表板或 CUR 2.0 导出。AWS 仍支持旧版 CUR。新的设计应参考 [FinOps 指南](../../ops/13-finops-cost-platform.md)，评估 Data Exports/CUR 2.0。此旧版示例需要在指定 Region 中已存在的 bucket、经过审核的 CUR 传送策略和报告权限。它不会创建 bucket、Glue schema、Athena 集成或仪表板。请遵循特定于传送服务的策略；不要用 CUR 2.0 的 `bcm-data-exports` 策略替代旧版服务策略。

**实施方法：**

1. **实施标签策略**：
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: web-app
     namespace: team-a
     labels:
       app: web-app
       team: team-a
       cost-center: cc-123
       environment: production
       project: project-x
   spec:
     selector:
       matchLabels:
         app: web-app
     template:
       metadata:
         labels:
           app: web-app
           team: team-a
           cost-center: cc-123
           environment: production
           project: project-x
       spec:
         containers:
         - name: web-app
           image: registry.example.com/team/web-app:REVIEWED_TAG
   ```

2. **配置 AWS Tag Policy**：
   ```json
   {
     "tags": {
       "team": {
         "tag_key": {
           "@@assign": "team"
         },
         "tag_value": {
           "@@assign": [
             "team-a",
             "team-b",
             "platform"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "cost-center": {
         "tag_key": {
           "@@assign": "cost-center"
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       },
       "environment": {
         "tag_key": {
           "@@assign": "environment"
         },
         "tag_value": {
           "@@assign": [
             "production",
             "staging",
             "development"
           ]
         },
         "enforced_for": {
           "@@assign": [
             "ec2:instance",
             "ec2:volume",
             "eks:cluster"
           ]
         }
       }
     }
   }
   ```

3. **安装和配置 Kubecost**：
使用[源指南](../../eks/07-eks-cost-optimization.md)中经过检查的 Kubecost 3.3.1 安装方案，或使用 [EKS06 第 6 题](06-eks-monitoring-logging-quiz.md)中的 OpenCost 1.121.2/chart 2.5.31。Kubecost 3.x 使用 ClickHouse/直接 finops-agent 收集方式；2.x 的 Prometheus values 和命令行许可证令牌不适用于此配置。请复用由同一所有者管理的部署，并审查其迁移、许可和存储要求。

4. **设置旧版 CUR 传送**：
   ```bash
   # Create cost and usage report
   aws cur put-report-definition \
     --report-definition '{
       "ReportName": "eks-cost-report",
       "TimeUnit": "HOURLY",
       "Format": "Parquet",
       "Compression": "Parquet",
       "AdditionalSchemaElements": ["RESOURCES"],
       "S3Bucket": "my-cost-reports",
       "S3Prefix": "eks-costs",
       "S3Region": "us-east-1",
       "AdditionalArtifacts": ["ATHENA"],
       "RefreshClosedReports": true,
       "ReportVersioning": "OVERWRITE_REPORT"
     }'
   ```

**分摊审查和补充配置**

复用 Q4 中按 context/账户/标签限定范围的采集器，获取实际 Metrics API 样本和账单页面。requests/limits 是声明的配置，不是实际使用量；request/limit 比率低于 0.5 并不意味着可以降低 requests。请比较相同工作负载、时间窗口、单位和覆盖范围，而不是将当前副本数与历史使用量进行比较。请核对团队/成本中心分摊与无标签及共享成本。有关运维报告/告警，请使用 [FinOps 指南](../../ops/13-finops-cost-platform.md)中明确的采集/验证流程；失败/缺失数据不能被当作零。

下面的 1,000 USD/80% 预算仅为示例。请验证实际已激活的 Budgets 标签筛选器格式和覆盖范围；已处理的账单告警不会强制限制支出上限。Terraform 片段假定已有 CUR bucket、caller identity、providers 和 Region 输入。其所有者必须配置 Athena 结果访问、保留/加密、Glue 表和查询权限。Terraform 支持 `aws_quicksight_dashboard`，但账户版本、数据集/模板和权限仍需另行配置。

```bash
aws resourcegroupstaggingapi tag-resources --region us-west-2 \
  --resource-arn-list arn:aws:eks:us-west-2:123456789012:cluster/my-cluster \
  --tags team=platform,cost-center=cc-100,environment=production
```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a-production
  labels:
    team: team-a
    environment: production
    cost-center: cc-123
---
apiVersion: v1
kind: Namespace
metadata:
  name: team-a-development
  labels:
    team: team-a
    environment: development
    cost-center: cc-123
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        image: registry.example.com/team/web-app:REVIEWED_TAG
    metadata:
      labels:
        app: web-app
  selector:
    matchLabels:
      app: web-app
```

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "EKS-Monthly",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "CostFilters": {
      "TagKeyValue": [
        "user:kubernetes.io/cluster/my-cluster$owned"
      ]
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]'
```

```hcl
resource "aws_cur_report_definition" "eks_cost" {
  report_name                = "eks-cost-report"
  time_unit                  = "HOURLY"
  format                     = "Parquet"
  compression                = "Parquet"
  additional_schema_elements = ["RESOURCES"]
  s3_bucket                  = aws_s3_bucket.cost_reports.id
  s3_prefix                  = "eks-costs"
  s3_region                  = "us-east-1"
  additional_artifacts       = ["ATHENA"]
  refresh_closed_reports     = true
  report_versioning          = "OVERWRITE_REPORT"
}

resource "aws_s3_bucket" "athena_results" {
  bucket = "eks-cost-athena-results-${data.aws_caller_identity.current.account_id}-${var.region}"

  tags = {
    Name = "EKS Cost Athena Results"
  }
}

resource "aws_athena_workgroup" "eks_cost" {
  name = "eks-cost-analysis"

  configuration {
    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/output/"
    }
  }
}

```

对于区域性的 TagResources 调用，请验证目标 Region 并检查 `FailedResourcesMap`；CLI 成功退出并不能证明所有请求的资源都已添加标签。在依赖账单分配前，请确认实际资源标签。

**估算分摊费率仪表板**

这是一个针对单个集群的 Prometheus 的即时 **CPU+memory 分摊费率估算值，单位为 USD/hour**。它不是发票，也不是完整的命名空间成本。此示例输入为 OpenCost 分摊/价格指标（`job="opencost"`）和 kube-state-metrics Pod 标签（`job="kube-state-metrics"`）。请确认实际 job 标签和完整的 CPU/memory/价格覆盖范围。按照适当的 ServiceMonitor honor-label 配置，保留导出器提供的工作负载命名空间标签。共享后端需要在每次聚合和联接中使用一致的集群身份。

将第一个 values 片段合并到由所属方管理的 kube-prometheus-stack release 中。Pod team 标签必须受控，并存在于 Pod 模板上；仅有命名空间标签不会自动生成这些标签。缺少 team 标签的项会归入 `unassigned`。查询会对相同的 scrape 副本进行去重；请另外解决互相冲突的价格/所有权来源。GPU、存储、网络、control-plane、空闲/共享分摊、折扣、抵扣额和税费不在这两个组成项内。数据缺失不等于零成本，费率也不是月度金额。

PrometheusRule 命名空间/release 标签必须符合源指南中的 selectors。在配置仪表板之前，请将 `REPLACE_WITH_PROMETHEUS_UID` 替换为经过审核的单集群数据源。ConfigMap 的 `grafana_dashboard: "1"` 标签与源指南的 sidecar 匹配；其 JSON 内容在下方提供。请验证规则运行状况、数据覆盖范围和仪表板查询。这些示例并未连接到实时账单/Grafana 部署。

```yaml
kube-state-metrics:
  metricLabelsAllowlist:
  - pods=[team]
```

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-allocation-rate
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-allocation-rate
    rules:
    - record: eks_review:pod_cpu_memory_cost_per_hour:sum
      expr: "sum by (namespace, pod) (\n  (\n    max by (namespace, pod, container,\
        \ node) (\n      container_cpu_allocation{job=\"opencost\"}\n    )\n    *\
        \ on (node) group_left\n    max by (node) (node_cpu_hourly_cost{job=\"opencost\"\
        })\n  )\n  +\n  (\n    max by (namespace, pod, container, node) (\n      container_memory_allocation_bytes{job=\"\
        opencost\"}\n    ) / 1073741824\n    * on (node) group_left\n    max by (node)\
        \ (node_ram_hourly_cost{job=\"opencost\"})\n  )\n)"
    - record: eks_review:team_cpu_memory_cost_per_hour:sum
      expr: "sum by (team) (\n  label_replace(\n    eks_review:pod_cpu_memory_cost_per_hour:sum\n\
        \    * on (namespace, pod) group_left (label_team)\n    max by (namespace,\
        \ pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\",label_team!=\"\
        \"}),\n    \"team\", \"$1\", \"label_team\", \"(.+)\"\n  )\n  or\n  label_replace(\n\
        \    eks_review:pod_cpu_memory_cost_per_hour:sum\n    unless on (namespace,\
        \ pod) max by (namespace, pod, label_team) (kube_pod_labels{job=\"kube-state-metrics\"\
        ,label_team!=\"\"}),\n    \"team\", \"unassigned\", \"namespace\", \".*\"\n\
        \  )\n)"
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cost-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: '1'
data:
  cost-dashboard.json: "{\n  \"title\": \"Estimated CPU and memory allocation rate\"\
    ,\n  \"uid\": \"eks-allocation-rate\",\n  \"schemaVersion\": 39,\n  \"version\"\
    : 1,\n  \"refresh\": \"1m\",\n  \"time\": {\n    \"from\": \"now-6h\",\n    \"\
    to\": \"now\"\n  },\n  \"panels\": [\n    {\n      \"id\": 1,\n      \"title\"\
    : \"CPU + memory allocation by namespace (USD/hour)\",\n      \"type\": \"timeseries\"\
    ,\n      \"gridPos\": {\n        \"x\": 0,\n        \"y\": 0,\n        \"w\":\
    \ 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n        \"type\":\
    \ \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\n      },\n\
    \      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\": \"currencyUSD\"\
    \n        },\n        \"overrides\": []\n      },\n      \"targets\": [\n    \
    \    {\n          \"refId\": \"A\",\n          \"expr\": \"sum by (namespace)\
    \ (eks_review:pod_cpu_memory_cost_per_hour:sum)\",\n          \"legendFormat\"\
    : \"{{namespace}}\"\n        }\n      ]\n    },\n    {\n      \"id\": 2,\n   \
    \   \"title\": \"CPU + memory allocation by team (USD/hour)\",\n      \"type\"\
    : \"timeseries\",\n      \"gridPos\": {\n        \"x\": 12,\n        \"y\": 0,\n\
    \        \"w\": 12,\n        \"h\": 8\n      },\n      \"datasource\": {\n   \
    \     \"type\": \"prometheus\",\n        \"uid\": \"REPLACE_WITH_PROMETHEUS_UID\"\
    \n      },\n      \"fieldConfig\": {\n        \"defaults\": {\n          \"unit\"\
    : \"currencyUSD\"\n        },\n        \"overrides\": []\n      },\n      \"targets\"\
    : [\n        {\n          \"refId\": \"A\",\n          \"expr\": \"eks_review:team_cpu_memory_cost_per_hour:sum\"\
    ,\n          \"legendFormat\": \"{{team}}\"\n        }\n      ]\n    }\n  ]\n}"
```

其他选项的问题：
- **A. 只查看 AWS 账单**：AWS 账单只提供较高层级的成本信息，因此难以识别详细的成本分摊情况或优化机会。
- **C. 将相同成本分摊给所有资源**：这无法准确反映实际资源使用和成本产生情况，也无法明确团队或项目的成本责任。
- **D. 使用资源时不进行成本监控**：没有成本监控就无法及早发现成本增长或识别优化机会，也会增加预算管理难度。
</details>

### 6. 哪种方法最适合支持可扩展的 EKS 成本优化工作流？

- A. 手动更改资源而不衡量结果
- B. 只考虑账单数据，忽略工作负载遥测数据
- C. 将成本可见性、资源遥测和适当的自动扩缩与明确的所有权结合起来
- D. 让多个互不协调的优化器同时管理同一批资源

<details>
<summary>显示答案</summary>

**答案：C. 将成本可见性、资源遥测和适当的自动扩缩与明确的所有权结合起来**

**说明：**
提到的工具只是互补角色的示例，并不要求全部安装。请选择由明确所有者管理的成本/遥测路径，以及符合工作负载需求的扩缩方式。EKS Auto Mode、自行管理的 Karpenter 或 Cluster Autoscaler 可能已经负责节点容量；请明确区分所有权，避免控制器相互竞争。必须衡量节省效果并验证 SLO 未受影响；仅安装成本工具不会自动将账单数据接入 HPA/Karpenter 策略。

**主要成本优化工具和功能：**

1. **Kubecost**：
   - Kubernetes 资源成本可见性
   - 按 namespace、Deployment、Service 进行成本分摊
   - 成本优化建议
   - 成本预测和预算管理

2. **Karpenter**：
   - 智能节点预置和管理
   - 在工作负载、容量和定价约束内选择实例
   - 必须在实际环境中验证预置/扩缩行为
   - 优化 Spot Instance 使用

3. **AWS Cost Explorer**：
   - 分析 AWS 服务的成本
   - 按标签分配成本
   - 成本趋势和预测
   - Reserved Instance 和 Savings Plans 建议

4. **Kubernetes 自动扩缩工具**：
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**实施方法：**

1. **安装和配置 Kubecost**：
复用 Q5 和[源指南](../../eks/07-eks-cost-optimization.md)中经过检查的安装方案和分摊数据前置条件。Kubecost 3.3.1 使用当前的 `kubecost/kubecost` chart 和 ClickHouse/直接 agent 架构；产品功能取决于版本和配置。OpenCost 是另一种选择。不要在现有、由所属方管理的配置上再部署第二个 collector。

2. **安装和配置 Karpenter**：
将以下内容保存为 `karpenter-values.yaml`，替换为经过审核的现有账户/角色/集群/endpoint/queue 值，并遵循 [Karpenter 指南](../../autoscaling/02-karpenter.md)。经过检查的示例使用 1.14.1；兼容性矩阵要求 EKS 1.36 至少使用 1.13。这些是 `settings.*` 键，不是会被忽略的 `controller.clusterName/clusterEndpoint` 值。IRSA trust 必须与 `system:serviceaccount:karpenter:karpenter` 及其 audience 匹配；不要组合彼此冲突的 IRSA/Pod Identity 分配。请先准备 controller/node IAM、节点访问权限、子网/security group、中断队列/事件连线和可靠的引导容量。全新 Helm 安装与 CRD 升级的所有权/生命周期步骤不同；单独升级控制器不会升级现有 CRDs。

```yaml
serviceAccount:
  create: true
  name: karpenter
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/KarpenterControllerRole-my-cluster
settings:
  clusterName: my-cluster
  clusterEndpoint: https://REPLACE_WITH_REVIEWED_EKS_ENDPOINT
  interruptionQueue: my-cluster
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed context matching the values file}"
KARPENTER_VERSION="1.14.1"
helm template karpenter oci://public.ecr.aws/karpenter/karpenter \
  --version "$KARPENTER_VERSION" --namespace karpenter \
  -f karpenter-values.yaml > karpenter-rendered.yaml
# Fresh installation only after the owned IAM, node access, queue, CRDs, and bootstrap capacity are ready.
helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
  --kube-context "$KUBE_CONTEXT" \
  --version "$KARPENTER_VERSION" --namespace karpenter --create-namespace \
  -f karpenter-values.yaml --wait --timeout 5m
```

   ```yaml
   # Karpenter NodePool and NodeClass configuration
   apiVersion: karpenter.sh/v1
   kind: NodePool
   metadata:
     name: default
   spec:
     template:
       spec:
         requirements:
           - key: "karpenter.sh/capacity-type"
             operator: In
             values: ["spot", "on-demand"]
           - key: "kubernetes.io/arch"
             operator: In
             values: ["amd64"]
           - key: "kubernetes.io/os"
             operator: In
             values: ["linux"]
           - key: "node.kubernetes.io/instance-type"
             operator: In
             values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
         nodeClassRef:
           group: karpenter.k8s.aws
           kind: EC2NodeClass
           name: default
     limits:
       cpu: 1000
       memory: 1000Gi
     disruption:
       consolidationPolicy: WhenEmpty
       consolidateAfter: 30s
   ---
   apiVersion: karpenter.k8s.aws/v1
   kind: EC2NodeClass
   metadata:
     name: default
   spec:
     amiSelectorTerms:
       - alias: al2023@latest
     role: KarpenterNodeRole
     subnetSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     securityGroupSelectorTerms:
       - tags:
           karpenter.sh/discovery: my-cluster
     tags:
       karpenter.sh/discovery: my-cluster
   ```

3. **配置 Horizontal Pod Autoscaler**：
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: web-app
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: web-app
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
   ```

4. **配置 Vertical Pod Autoscaler**：
   ```yaml
   apiVersion: autoscaling.k8s.io/v1
   kind: VerticalPodAutoscaler
   metadata:
     name: web-app-vpa
   spec:
     targetRef:
       apiVersion: "apps/v1"
       kind: Deployment
       name: web-app
     updatePolicy:
       updateMode: "Off"
     resourcePolicy:
       containerPolicies:
       - containerName: '*'
         minAllowed:
           cpu: 50m
           memory: 100Mi
         maxAllowed:
           cpu: 1
           memory: 1Gi
         controlledResources: ["cpu", "memory"]
   ```

**工具集成和工作流：**

1. **成本可见性和分析**：
   - Kubecost：集群内资源成本分析
   - AWS Cost Explorer：跨 AWS 服务的成本分析
   - 集成仪表板：整体成本概览和趋势

2. **自动化资源优化**：
   - Karpenter：优化节点预置和管理
   - HPA/VPA：工作负载级资源优化
   - 使用 Spot Instance：获取经济高效的计算资源

3. **成本分摊和责任归属**：
   - 基于标签的成本分摊
   - 按 namespace 和 label 分析成本
   - 按团队和项目生成成本报告

4. **持续优化和改进**：
   - 实施成本优化建议
   - 定期审查和分析成本
   - 设定并跟踪成本降低目标

**有明确所有权的集成和 API 验证**

VPA 示例使用 Off，而 HPA 使用 CPU/memory 利用率作为分母。只有在协调好控制循环后，才启用自动 request 更改。Cluster Proportional Autoscaler 根据集群大小信号扩缩组件副本；它并不是等价的节点预置器。Karpenter 限制、实例偏好和整合延迟都不是支出或终止时间保证。请检查解析出的 AMI，并为受控更改固定使用经过测试的版本/ID，不要将 `al2023@latest` 视为不可变值。

PriorityClass 控制调度/抢占优先级，不负责成本分摊或保证可用性。请管理谁有权分配优先级；调度器抢占会尽力遵守 PDB。请审查中断影响和工作负载恢复。成本观测和建议需要经过明确审核的策略/更改路径后，控制器才能采取行动；架构图本身不会实现这种集成。

Terraform 替代方案使用 Helm provider 3.3.0 的 values-file 配置和 AWS provider 6.69.1。请提供显式的 Kubernetes context 和经过审核的 chart values，包括兼容的身份、存储和许可证密钥引用；它不会创建这些前置条件。不要将原始许可证/云凭证写入 values 或 state。请与现有 release 的所有者协调，而不要通过第二个管理器再次安装。1,000 USD/80% 预算仅为示例，使用经过验证的账单标签筛选器，并非支出上限。此次审计没有执行集群/Helm 预置，也没有发送通知。

下面的 API 示例明确针对前述设置中的 OpenCost 1.121.2，而不是猜测 Kubecost 3.x 的 URL。其 `/allocation` API 接受 `namespace,controllerKind,controller` 聚合；`deployment` 不是文档中通用的聚合键。响应 data 是 allocation-set maps 数组，而不是直接的 namespace/Deployment 字典。请验证 HTTP/API 错误和数据覆盖范围；结果为空并不代表成本为零，也不能证明存在过度预置。分摊数量、使用量、requests、byte-hours/core-hours 和当前副本数含义不同、时间窗口也不同。提出合理调整规格的建议前，请检查带版本的 schema 和可比较的工作负载指标。原始分摊估算值必须与账单和空闲/共享成本策略核对。





```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  template:
    spec:
      containers:
      - name: web-app
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        image: registry.example.com/team/web-app:REVIEWED_TAG
    metadata:
      labels:
        app: web-app
  selector:
    matchLabels:
      app: web-app
```

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-pool
spec:
  template:
    spec:
      requirements:
        - key: "karpenter.sh/capacity-type"
          operator: In
          values: ["spot"]
        - key: "node.kubernetes.io/instance-type"
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m4.large", "t3.large", "t3a.large"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 1000Gi
```

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: High priority pods
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: Low priority pods
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
spec:
  template:
    spec:
      priorityClassName: high-priority
      containers:
      - name: critical-app
        image: registry.example.com/team/critical-app:REVIEWED_TAG
    metadata:
      labels:
        app: critical-app
  selector:
    matchLabels:
      app: critical-app
```

```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget '{
    "BudgetName": "EKS-Monthly",
    "BudgetLimit": {
      "Amount": "1000",
      "Unit": "USD"
    },
    "CostFilters": {
      "TagKeyValue": [
        "user:kubernetes.io/cluster/my-cluster$owned"
      ]
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {
          "SubscriptionType": "EMAIL",
          "Address": "team@example.com"
        }
      ]
    }
  ]'
```

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "= 3.3.0"
    }
  }
}

variable "region" { type = string }
variable "account_id" { type = string }
variable "kubeconfig_path" { type = string }
variable "kube_context" { type = string }
variable "reviewed_kubecost_values_path" { type = string }
variable "reviewed_karpenter_values_path" { type = string }
variable "budget_name" { type = string }
variable "budget_tag_filter" {
  type        = string
  description = "Actual activated Budgets TagKeyValue, for example user:cluster$production."
}
variable "notification_email" {
  type        = string
  description = "Approved recipient; applying this configures real notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

provider "helm" {
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

resource "helm_release" "kubecost" {
  name             = "kubecost"
  repository       = "https://kubecost.github.io/kubecost/"
  chart            = "kubecost"
  version          = "3.3.1"
  namespace        = "kubecost"
  create_namespace = true
  values           = [file(var.reviewed_kubecost_values_path)]
  wait             = true
  timeout          = 300
}

resource "helm_release" "karpenter" {
  name             = "karpenter"
  repository       = "oci://public.ecr.aws/karpenter"
  chart            = "karpenter"
  version          = "1.14.1"
  namespace        = "karpenter"
  create_namespace = true
  values           = [file(var.reviewed_karpenter_values_path)]
  wait             = true
  timeout          = 300
}

resource "aws_budgets_budget" "eks" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [var.budget_tag_filter]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

```bash
: "${KUBE_CONTEXT:?Select the reviewed OpenCost cluster context}"
# Terminal 1: authorized local access to the OpenCost 1.121.2 service from EKS06.
kubectl --context "$KUBE_CONTEXT" -n opencost port-forward --address 127.0.0.1 svc/opencost 9003:9003
```

```bash
curl --fail --silent --show-error --max-time 30 --get \
  http://127.0.0.1:9003/allocation \
  --data-urlencode 'window=1d' \
  --data-urlencode 'aggregate=namespace,controllerKind,controller' \
  --data-urlencode 'accumulate=true' > allocation.json
```

```python
import json
from pathlib import Path

response = json.loads(Path("allocation.json").read_text())
if response.get("code") != 200 or not isinstance(response.get("data"), list):
    raise ValueError("Unexpected allocation API response; do not replace failure with zero")
if not all(isinstance(allocation_set, dict) for allocation_set in response["data"]):
    raise ValueError("Expected an array of allocation-set maps")
if not response["data"] or not any(response["data"]):
    raise SystemExit("No allocation data for the selected window; investigate coverage")
else:
    print("Allocation response shape accepted; review units, window, and coverage before analysis")
```

其他选项都忽略了衡量、工作负载信号或协调的所有权。相互竞争的控制器会损害稳定性和成本可预测性。
</details>

</source_document>
