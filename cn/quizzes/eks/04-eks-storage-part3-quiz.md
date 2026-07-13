# EKS 存储第 3 部分测验

本测验用于检验你对 Amazon EKS 中存储监控、故障排查、成本优化和安全性的理解。

## 问题 1：存储监控指标

<details>
<summary>在 EKS 中监控存储性能的关键指标有哪些？</summary>

**答案：**
**EBS 指标：**
- VolumeReadOps/VolumeWriteOps：IOPS 使用量
- VolumeReadBytes/VolumeWriteBytes：吞吐量
- VolumeTotalReadTime/VolumeTotalWriteTime：延迟
- VolumeQueueLength：待处理 I/O 请求数
- BurstBalance：突发积分余额

**EFS 指标：**
- DataReadIOBytes/DataWriteIOBytes：数据传输量
- MetadataIOBytes：元数据操作量
- ClientConnections：客户端连接数
- PercentIOLimit：I/O 限制利用率

**Kubernetes 指标：**
- kubelet_volume_stats_used_bytes：Volume 使用量
- kubelet_volume_stats_capacity_bytes：Volume 容量
- container_fs_usage_bytes：Container 文件系统使用量
</details>

## 问题 2：存储问题诊断

<details>
<summary>当 EKS 中的 Pod 处于“Pending”状态并且无法挂载 PVC 时，你应该检查什么？</summary>

**答案：**
1. **检查 PVC 状态**：
   ```bash
   kubectl get pvc
   kubectl describe pvc <pvc-name>
   ```

2. **检查 Storage Class**：
   ```bash
   kubectl get storageclass
   kubectl describe storageclass <storage-class-name>
   ```

3. **检查 CSI Driver 状态**：
   ```bash
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   kubectl logs -n kube-system -l app=ebs-csi-controller
   ```

4. **检查 Node 权限**：
   - 验证 EC2 instance profile 中所需的 IAM 权限
   - 验证 EBS CSI driver service account 权限

5. **Availability Zone 兼容性**：
   - 验证 Pod 和 EBS Volume 位于同一 AZ

6. **资源限制**：
   - EBS Volume 限制（每个 instance 的最大 Volume 数）
   - 验证 Volume 大小限制
</details>

## 问题 3：性能优化

<details>
<summary>如何为 EKS 中的数据库工作负载优化存储性能？</summary>

**答案：**
1. **选择合适的 Volume 类型**：
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: fast-ssd
   provisioner: ebs.csi.aws.com
   parameters:
     type: io2
     iops: "10000"
     encrypted: "true"
   volumeBindingMode: WaitForFirstConsumer
   ```

2. **使用 Multi-Attach Volume**（适用于只读工作负载）：
   ```yaml
   parameters:
     type: io2
     multiAttach: "true"
   ```

3. **利用 Instance Store**：
   ```yaml
   # Instance store for temporary data
   volumeMounts:
   - name: instance-store
     mountPath: /tmp
   volumes:
   - name: instance-store
     hostPath:
       path: /mnt/instance-store
   ```

4. **选择合适的 Filesystem**：
   - XFS：大文件和高并发
   - ext4：通用用途
   - 设置合适的 mount options

5. **I/O Scheduler 优化**：
   ```bash
   # noop or deadline scheduler for SSD
   echo noop > /sys/block/nvme0n1/queue/scheduler
   ```
</details>

## 问题 4：成本优化策略

<details>
<summary>可以使用哪些策略来优化 EKS 存储成本？</summary>

**答案：**
1. **选择合适的 Volume 类型**：
   - gp3：适用于大多数工作负载且具有成本效益
   - 从 gp2 迁移到 gp3
   - 仅在必要时使用预置 IOPS

2. **优化 Volume 大小**：
   ```bash
   # Monitor usage
   kubectl top pods --containers
   df -h # Inside pod
   ```

3. **Lifecycle Management**：
   ```yaml
   # Snapshot automation
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: csi-aws-vsc
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

4. **利用 EFS Storage Classes**：
   ```yaml
   # Infrequent Access storage class
   parameters:
     performanceMode: generalPurpose
     throughputMode: provisioned
     provisionedThroughputInMibps: "100"
   ```

5. **清理未使用的 Volume**：
   ```bash
   # Check unused PVs
   kubectl get pv | grep Available

   # Clean up old snapshots
   aws ec2 describe-snapshots --owner-ids self \
     --query 'Snapshots[?StartTime<=`2023-01-01`]'
   ```
</details>

## 问题 5：安全最佳实践

<details>
<summary>如何增强 EKS 存储安全性？</summary>

**答案：**
1. **启用加密**：
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: encrypted-gp3
   provisioner: ebs.csi.aws.com
   parameters:
     type: gp3
     encrypted: "true"
     kmsKeyId: "arn:aws:kms:region:account:key/key-id"
   ```

2. **最小化 IAM 权限**：
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:CreateVolume",
           "ec2:AttachVolume",
           "ec2:DetachVolume",
           "ec2:DeleteVolume",
           "ec2:DescribeVolumes",
           "ec2:CreateSnapshot",
           "ec2:DeleteSnapshot",
           "ec2:DescribeSnapshots"
         ],
         "Resource": "*",
         "Condition": {
           "StringEquals": {
             "aws:RequestedRegion": "us-west-2"
           }
         }
       }
     ]
   }
   ```

3. **网络安全**：
   ```yaml
   # EFS mount target security group
   securityGroupSelector:
     matchLabels:
       Name: "efs-mount-target-sg"
   ```

4. **访问控制**：
   ```yaml
   # RBAC configuration
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: storage-admin
   rules:
   - apiGroups: [""]
     resources: ["persistentvolumes", "persistentvolumeclaims"]
     verbs: ["get", "list", "create", "delete"]
   ```

5. **审计日志记录**：
   ```yaml
   # Storage-related audit policy
   - level: Metadata
     resources:
     - group: ""
       resources: ["persistentvolumes", "persistentvolumeclaims"]
   ```
</details>

### 6. 在 Amazon EKS 中用于存储监控和管理的最有效工具组合是什么？

A. 仅使用 CloudWatch 和 AWS Console
B. CloudWatch、Prometheus、Grafana 以及自动化管理工具
C. 手动检查和日志分析
D. 仅使用第三方监控工具

<details>
<summary>显示答案</summary>

**答案：B. CloudWatch、Prometheus、Grafana 以及自动化管理工具**

**解析：**
在 Amazon EKS 中，用于存储监控和管理的最有效工具组合是结合使用 CloudWatch、Prometheus、Grafana 以及自动化管理工具。这种集成方法既收集 AWS 原生指标，也收集详细的 Kubernetes 级别指标，对其进行可视化，并通过自动化管理提升运营效率。

**集成监控和管理架构：**

1. **CloudWatch**：
   - 收集 AWS 基础设施级别指标
   - EBS、EFS、FSx 存储性能指标
   - 警报和事件管理

2. **Prometheus**：
   - 收集详细的 Kubernetes 级别指标
   - 收集自定义存储指标
   - 长期数据保留和查询

3. **Grafana**：
   - 集成仪表板和可视化
   - 集成 CloudWatch 和 Prometheus 数据源
   - 自定义告警和报告

4. **自动化管理工具**：
   - 存储预置自动化
   - 容量规划和扩缩容
   - 问题检测和解决
</details>

---

**分数计算：**
- 5-6 个正确答案：优秀（EKS 存储专家级别）
- 3-4 个正确答案：良好（建议进一步学习）
- 1-2 个正确答案：一般（需要复习基础概念）
- 0 个正确答案：需要改进（需要重新学习全部内容）

**实现示例：**

1. **CloudWatch Container Insights 设置**：
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cwagent-config
     namespace: amazon-cloudwatch
   data:
     cwagentconfig.json: |
       {
         "logs": {
           "metrics_collected": {
             "kubernetes": {
               "cluster_name": "my-cluster",
               "metrics_collection_interval": 60
             }
           },
           "force_flush_interval": 5
         },
         "metrics": {
           "namespace": "EKS/Storage",
           "metrics_collected": {
             "statsd": {
               "service_address": ":8125"
             }
           }
         }
       }
   ```

2. **Prometheus 和 Storage Exporter 设置**：
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: storage-monitor
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         app: storage-exporter
     endpoints:
     - port: metrics
       interval: 30s
       path: /metrics
   ```

3. **Grafana Dashboard 配置**：
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: storage-dashboard
     namespace: monitoring
   data:
     storage-dashboard.json: |
       {
         "title": "EKS Storage Dashboard",
         "panels": [
           {
             "title": "EBS Volume IOPS",
             "datasource": "Prometheus",
             "targets": [
               {
                 "expr": "aws_ebs_volume_read_ops + aws_ebs_volume_write_ops",
                 "legendFormat": "{{volume_id}}"
               }
             ]
           },
           {
             "title": "EFS Throughput",
             "datasource": "CloudWatch",
             "targets": [
               {
                 "namespace": "AWS/EFS",
                 "metricName": "TotalIOBytes",
                 "dimensions": {
                   "FileSystemId": "*"
                 },
                 "statistic": "Sum"
               }
             ]
           }
         ]
       }
   ```

4. **自动化存储管理 CronJob**：
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: storage-manager
   spec:
     schedule: "0 1 * * *"
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: storage-manager
               image: storage-tools:latest
               command:
               - /bin/bash
               - -c
               - |
                 # Identify unused PVCs
                 UNUSED_PVCS=$(kubectl get pvc -A -o json | jq -r '.items[] | select(.status.phase == "Bound") | select(.metadata.annotations.lastUsed < "'$(date -d "30 days ago" +%Y-%m-%d)'") | .metadata.name')

                 # Create snapshots
                 for PVC in $UNUSED_PVCS; do
                   kubectl create snapshot ...
                 done

                 # Analyze volume usage and generate reports
                 ...
             restartPolicy: OnFailure
   ```

**关键监控指标：**

1. **EBS Volume 指标**：
   - VolumeReadOps/VolumeWriteOps
   - VolumeReadBytes/VolumeWriteBytes
   - VolumeQueueLength
   - BurstBalance（gp2 Volume）

2. **EFS 指标**：
   - TotalIOBytes
   - DataReadIOBytes/DataWriteIOBytes
   - MetadataIOBytes
   - ClientConnections
   - StorageBytes（Standard/IA）

3. **FSx for Lustre 指标**：
   - DataReadBytes/DataWriteBytes
   - DataReadOperations/DataWriteOperations
   - FreeDataStorageCapacity
   - LogicalDiskUsage

4. **Kubernetes 存储指标**：
   - PVC 使用量和容量
   - Volume 挂载状态
   - Storage Class 使用情况

**高级监控和管理功能：**

1. **预测分析**：
   - 容量预测和规划
   - 性能趋势分析
   - 成本预测

2. **异常检测**：
   - 检测异常 I/O 模式
   - 性能下降的早期预警
   - 容量不足预测

3. **自动化优化**：
   - 根据使用模式推荐 Volume 类型
   - 自动扩容和缩容
   - 成本优化建议

4. **集成报告**：
   - 存储使用量和性能报告
   - 成本分摊和分析
   - 合规性和审计报告

**实现最佳实践：**

1. **多层级监控**：
   - 基础设施级别（CloudWatch）
   - Kubernetes 级别（Prometheus）
   - 应用程序级别（自定义指标）

2. **告警策略**：
   - 根据严重程度设置告警
   - 告警分组和去重
   - 定义升级路径

3. **数据保留策略**：
   - 高分辨率数据：短期保留
   - 聚合数据：长期保留
   - 在成本和实用性之间取得平衡

4. **逐步引入自动化**：
   - 首先实施监控和告警
   - 添加报告和分析功能
   - 逐步引入自动化管理

其他选项的问题：
- **A. 仅使用 CloudWatch 和 AWS Console**：提供 AWS 原生指标，但缺少详细的 Kubernetes 级别指标，并且自动化能力有限。
- **C. 手动检查和日志分析**：缺乏可扩展性，难以进行实时监控，并且无法主动检测问题。
- **D. 仅使用第三方监控工具**：与 AWS 原生指标的集成可能有限，并且可能产生额外成本。
