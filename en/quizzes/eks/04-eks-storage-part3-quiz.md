# EKS Storage Part 3 Quiz

This quiz tests your understanding of storage monitoring, troubleshooting, cost optimization, and security in Amazon EKS.

## Question 1: Storage Monitoring Metrics

<details>
<summary>What are the key metrics for monitoring storage performance in EKS?</summary>

**Answer:**
**EBS Metrics:**
- VolumeReadOps/VolumeWriteOps: IOPS usage
- VolumeReadBytes/VolumeWriteBytes: Throughput
- VolumeTotalReadTime/VolumeTotalWriteTime: Latency
- VolumeQueueLength: Number of pending I/O requests
- BurstBalance: Burst credit balance

**EFS Metrics:**
- DataReadIOBytes/DataWriteIOBytes: Data transfer volume
- MetadataIOBytes: Metadata operation volume
- ClientConnections: Number of client connections
- PercentIOLimit: I/O limit utilization

**Kubernetes Metrics:**
- kubelet_volume_stats_used_bytes: Volume usage
- kubelet_volume_stats_capacity_bytes: Volume capacity
- container_fs_usage_bytes: Container filesystem usage
</details>

## Question 2: Storage Problem Diagnosis

<details>
<summary>What should you check when a pod in EKS is stuck in "Pending" state and cannot mount a PVC?</summary>

**Answer:**
1. **Check PVC Status**:
   ```bash
   kubectl get pvc
   kubectl describe pvc <pvc-name>
   ```

2. **Check Storage Class**:
   ```bash
   kubectl get storageclass
   kubectl describe storageclass <storage-class-name>
   ```

3. **Check CSI Driver Status**:
   ```bash
   kubectl get pods -n kube-system -l app=ebs-csi-controller
   kubectl logs -n kube-system -l app=ebs-csi-controller
   ```

4. **Check Node Permissions**:
   - Verify required IAM permissions in EC2 instance profile
   - Verify EBS CSI driver service account permissions

5. **Availability Zone Compatibility**:
   - Verify pod and EBS volume are in the same AZ

6. **Resource Limits**:
   - EBS volume limits (maximum volumes per instance)
   - Verify volume size limits
</details>

## Question 3: Performance Optimization

<details>
<summary>How can you optimize storage performance for database workloads in EKS?</summary>

**Answer:**
1. **Select Appropriate Volume Type**:
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

2. **Use Multi-Attach Volumes** (for read-only workloads):
   ```yaml
   parameters:
     type: io2
     multiAttach: "true"
   ```

3. **Utilize Instance Store**:
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

4. **Select Appropriate Filesystem**:
   - XFS: Large files and high concurrency
   - ext4: General purpose
   - Set appropriate mount options

5. **I/O Scheduler Optimization**:
   ```bash
   # noop or deadline scheduler for SSD
   echo noop > /sys/block/nvme0n1/queue/scheduler
   ```
</details>

## Question 4: Cost Optimization Strategies

<details>
<summary>What strategies can be used to optimize EKS storage costs?</summary>

**Answer:**
1. **Select Appropriate Volume Type**:
   - gp3: Cost-effective for most workloads
   - Migrate from gp2 to gp3
   - Use provisioned IOPS only when necessary

2. **Optimize Volume Size**:
   ```bash
   # Monitor usage
   kubectl top pods --containers
   df -h # Inside pod
   ```

3. **Lifecycle Management**:
   ```yaml
   # Snapshot automation
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: csi-aws-vsc
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

4. **Utilize EFS Storage Classes**:
   ```yaml
   # Infrequent Access storage class
   parameters:
     performanceMode: generalPurpose
     throughputMode: provisioned
     provisionedThroughputInMibps: "100"
   ```

5. **Clean Up Unused Volumes**:
   ```bash
   # Check unused PVs
   kubectl get pv | grep Available

   # Clean up old snapshots
   aws ec2 describe-snapshots --owner-ids self \
     --query 'Snapshots[?StartTime<=`2023-01-01`]'
   ```
</details>

## Question 5: Security Best Practices

<details>
<summary>How can you enhance EKS storage security?</summary>

**Answer:**
1. **Enable Encryption**:
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

2. **Minimize IAM Permissions**:
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

3. **Network Security**:
   ```yaml
   # EFS mount target security group
   securityGroupSelector:
     matchLabels:
       Name: "efs-mount-target-sg"
   ```

4. **Access Control**:
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

5. **Audit Logging**:
   ```yaml
   # Storage-related audit policy
   - level: Metadata
     resources:
     - group: ""
       resources: ["persistentvolumes", "persistentvolumeclaims"]
   ```
</details>

### 6. What is the most effective tool combination for storage monitoring and management in Amazon EKS?

A. Use only CloudWatch and AWS Console
B. CloudWatch, Prometheus, Grafana, and automated management tools
C. Manual inspection and log analysis
D. Use only third-party monitoring tools

<details>
<summary>Show Answer</summary>

**Answer: B. CloudWatch, Prometheus, Grafana, and automated management tools**

**Explanation:**
The most effective tool combination for storage monitoring and management in Amazon EKS is using CloudWatch, Prometheus, Grafana, and automated management tools together. This integrated approach collects both AWS-native metrics and detailed Kubernetes-level metrics, visualizes them, and improves operational efficiency through automated management.

**Integrated Monitoring and Management Architecture:**

1. **CloudWatch**:
   - Collects AWS infrastructure-level metrics
   - EBS, EFS, FSx storage performance metrics
   - Alarm and event management

2. **Prometheus**:
   - Collects detailed Kubernetes-level metrics
   - Collects custom storage metrics
   - Long-term data retention and querying

3. **Grafana**:
   - Integrated dashboards and visualization
   - Integration of CloudWatch and Prometheus data sources
   - Custom alerting and reports

4. **Automated Management Tools**:
   - Storage provisioning automation
   - Capacity planning and scaling
   - Problem detection and resolution
</details>

---

**Score Calculation:**
- 5-6 correct answers: Excellent (EKS storage expert level)
- 3-4 correct answers: Good (additional learning recommended)
- 1-2 correct answers: Fair (basic concept review needed)
- 0 correct answers: Needs improvement (full content re-study required)

**Implementation Examples:**

1. **CloudWatch Container Insights Setup**:
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

2. **Prometheus and Storage Exporter Setup**:
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

3. **Grafana Dashboard Configuration**:
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

4. **Automated Storage Management CronJob**:
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

**Key Monitoring Metrics:**

1. **EBS Volume Metrics**:
   - VolumeReadOps/VolumeWriteOps
   - VolumeReadBytes/VolumeWriteBytes
   - VolumeQueueLength
   - BurstBalance (gp2 volumes)

2. **EFS Metrics**:
   - TotalIOBytes
   - DataReadIOBytes/DataWriteIOBytes
   - MetadataIOBytes
   - ClientConnections
   - StorageBytes (Standard/IA)

3. **FSx for Lustre Metrics**:
   - DataReadBytes/DataWriteBytes
   - DataReadOperations/DataWriteOperations
   - FreeDataStorageCapacity
   - LogicalDiskUsage

4. **Kubernetes Storage Metrics**:
   - PVC usage and capacity
   - Volume mount status
   - Storage class usage

**Advanced Monitoring and Management Features:**

1. **Predictive Analysis**:
   - Capacity prediction and planning
   - Performance trend analysis
   - Cost forecasting

2. **Anomaly Detection**:
   - Detect abnormal I/O patterns
   - Early warning of performance degradation
   - Capacity shortage prediction

3. **Automated Optimization**:
   - Volume type recommendations based on usage patterns
   - Automatic scaling up and down
   - Cost optimization recommendations

4. **Integrated Reporting**:
   - Storage usage and performance reports
   - Cost allocation and analysis
   - Compliance and audit reports

**Implementation Best Practices:**

1. **Multi-Level Monitoring**:
   - Infrastructure level (CloudWatch)
   - Kubernetes level (Prometheus)
   - Application level (custom metrics)

2. **Alerting Strategy**:
   - Set alerts based on severity
   - Alert grouping and deduplication
   - Define escalation paths

3. **Data Retention Policy**:
   - High-resolution data: short-term retention
   - Aggregated data: long-term retention
   - Balance between cost and usefulness

4. **Gradual Automation Introduction**:
   - Implement monitoring and alerting first
   - Add reporting and analysis capabilities
   - Gradually introduce automated management

Issues with other options:
- **A. Use only CloudWatch and AWS Console**: Provides AWS-native metrics but lacks detailed Kubernetes-level metrics and has limited automation capabilities.
- **C. Manual inspection and log analysis**: Lacks scalability, makes real-time monitoring difficult, and prevents proactive problem detection.
- **D. Use only third-party monitoring tools**: May have limited integration with AWS-native metrics and can incur additional costs.
