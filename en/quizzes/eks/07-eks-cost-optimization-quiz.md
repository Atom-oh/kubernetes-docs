# Amazon EKS Cost Optimization Quiz

> **Last Updated**: September 12, 2026

Examples are independent configuration alternatives, not executed deployments or measured savings. Merge changes into the existing resource owner; do not apply every example successively over the same workload. Replace placeholder application images and application-owned hooks, verify account/context/Region and compatible controllers, and test behavior before operational use.

This quiz tests your understanding of strategies, tools, and best practices for optimizing costs in Amazon EKS clusters.

## Quiz Overview
- Compute resource optimization
- Storage cost optimization
- Networking cost optimization
- Cluster management cost optimization
- Cost monitoring and analysis
- Cost optimization tools and best practices

## Multiple Choice Questions

### 1. What is the most effective strategy for optimizing compute costs in Amazon EKS?

- A. Always use the largest instance types
- B. Use only on-demand instances for all workloads
- C. Combine Spot Instances, right-sizing, and auto-scaling
- D. Consolidate all workloads into a single node group
<details>
<summary>Show Answer</summary>

**Answer: C. Combine Spot Instances, right-sizing, and auto-scaling**

**Explanation:**
The most effective strategy for optimizing compute costs in Amazon EKS is to combine Spot Instances, right-sizing, and auto-scaling. Use Spot only where interruption tolerance and available capacity permit, and verify savings against workload SLOs. Neither this combination nor an advertised maximum discount guarantees lower cost or unchanged performance.

**Key Compute Optimization Strategies:**

1. **Spot Instance Utilization**:
   - Up to 90% cost savings compared to on-demand
   - Suitable for fault-tolerant workloads
   - Implement interruption handling mechanisms

2. **Right-sizing**:
   - Select instances based on actual resource usage
   - Eliminate over-provisioned resources
   - Optimize resource requests and limits

3. **Auto-scaling Implementation**:
   - Node-level scaling through Cluster Autoscaler or Karpenter
   - Pod-level scaling through Horizontal Pod Autoscaler
   - Resource adjustment based on demand

The NodePool/EC2NodeClass require an installed compatible Karpenter controller/CRDs, scoped controller IAM, node role, discovery resources, and interruption queue. EKS 1.36 requires Karpenter >=1.13 in the current matrix. `al2023@latest` is a moving selector: review resolved AMIs and pin a tested alias/AMI for a controlled rollout. Instance lists and capacity limits are illustrative and are not a spending cap. Managed node groups handle their own interruption path; avoid a second handler over Karpenter-managed nodes.

The HPA requires resource metrics and requests; with CPU and memory targets it selects the largest desired replica count. The VPA below is **Off** to provide recommendations without changing those denominators. `Auto` is deprecated in favor of explicit modes such as `Recreate`; automatic CPU/memory changes must be coordinated with HPA. A preStop hook consumes the termination grace period and cannot guarantee a Spot deadline or successful cleanup.

**Implementation Methods:**

1. **Create Node Group with Spot Instances**:
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

2. **Deploy and Configure Karpenter**:
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

3. **Configure Horizontal Pod Autoscaler**:
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

4. **Configure Vertical Pod Autoscaler**:
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

**Optimization Strategies by Workload Type:**

1. **Stateless Applications**:
   - Prioritize Spot Instances
   - Implement horizontal scaling
   - Deploy across multiple availability zones

2. **Stateful Applications**:
   - Mix on-demand and Spot Instances
   - Select appropriate instance types
   - Balance storage performance and cost

3. **Batch Jobs**:
   - Maximize Spot Instance usage
   - Implement job retry mechanisms
   - Schedule within deadlines/capacity availability; no general off-peak On-Demand tariff

**Best Practices:**

1. **Optimize Resource Requests and Limits**:
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

2. **Optimize Node Affinity and Pod Distribution**:
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

3. **Handle Spot Instance Interruptions**:
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

**Additional implementation considerations**

- An eksctl configuration can define an On-Demand group for system workloads and a diversified Spot group for applications. Labels alone do not isolate workloads. Configure selectors/tolerations deliberately; do not taint the only bootstrap nodes before system controllers can run.
- In an existing Terraform module, `aws_eks_node_group` can set `capacity_type = "SPOT"` and `scaling_config`. The cluster, node IAM role/policies, subnets, and provider must already be defined. Coordinate `desired_size` ownership with the autoscaler.
- EKS node-group tags are not a substitute for the **actual ASG** discovery tags used by Cluster Autoscaler. Inspect the ASGs and their existing tag owner before changing them. Bind the autoscaler policy to a dedicated controller identity; node-role add-on permissions are not the intended identity.
- Keep AWS read/discovery actions separate from the two scaling write actions. Restrict `autoscaling:SetDesiredCapacity` and `autoscaling:TerminateInstanceInAutoScalingGroup` to ASGs carrying the reviewed enabled/cluster ownership tags, as in the [official EKS policy](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html).

The following eksctl fragment adds node groups to an existing cluster. Verify the owner's private subnets, node IAM policies, and existing group/ASG tags; it is not a standalone cluster-creation recipe.

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

The Terraform fragment assumes the named cluster/node-role resources, private-subnet variable, and provider already exist in the owning module. Its IAM policy must be attached to the dedicated controller identity.

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

Issues with other options:
- **A. Always use the largest instance types**: This leads to over-provisioning with unnecessary costs and may not match workload requirements.
- **B. Use only on-demand instances for all workloads**: On-demand instances cost more than Spot Instances, and many workloads can run effectively on Spot Instances.
- **D. Consolidate all workloads into a single node group**: This makes it difficult to meet various workload requirements, lacks resource isolation, and makes cost allocation and optimization challenging.
</details>

### 2. What is the most effective approach for optimizing storage costs in Amazon EKS?

- A. Use the cheapest storage type for all workloads
- B. Migrate all data to S3
- C. Select storage types matching workload requirements and implement lifecycle management
- D. Minimize all volume sizes
<details>
<summary>Show Answer</summary>

**Answer: C. Select storage types matching workload requirements and implement lifecycle management**

**Explanation:**
The most effective approach for optimizing storage costs in Amazon EKS is to select storage types that match workload requirements and implement lifecycle management. This approach minimizes costs while meeting performance requirements and leverages appropriate storage tiers based on data value and access patterns.

**Key Storage Optimization Strategies:**

1. **Select Appropriate Storage Types for Workloads**:
   - High performance needs: io2, gp3 (EBS)
   - Shared access needs: EFS
   - Large-scale data processing: FSx for Lustre
   - Archive data: S3, S3 Glacier

2. **Storage Lifecycle Management**:
   - Frequently accessed data: High-performance storage
   - Occasionally accessed data: Standard storage
   - Rarely accessed data: Low-cost archive storage

3. **Efficient Volume Management**:
   - Set appropriate volume sizes
   - Identify and remove unused volumes
   - Manage snapshot lifecycles

StorageClass examples require installed CSI drivers and correct IAM/KMS/topology settings. `WaitForFirstConsumer` aligns EBS provisioning with scheduling; `Retain` leaves released volumes billable until the owner handles them. Bound PVCs cannot change class or shrink in place. Snapshot/restore or supported volume-type modification requires an owner-reviewed migration and restore test. Auto Mode uses a different EBS provisioner; do not silently substitute it into standard CSI examples.

`create-file-system` has no `--lifecycle-policies` option. Use `put-lifecycle-configuration` on the existing filesystem, preserving the complete desired policy array as shown below. S3 transitions also need minimum-duration/size, request cost, versioning, and recovery-latency review; replacing a lifecycle configuration must preserve unrelated rules.

**Implementation Methods:**

1. **EBS Volume Optimization**:
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

2. **EFS Lifecycle Management**:
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

3. **S3 Lifecycle Policy**:
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

4. **EBS Snapshot Lifecycle Management**:
   ```yaml
   apiVersion: snapshot.storage.k8s.io/v1
   kind: VolumeSnapshotClass
   metadata:
     name: ebs-snapshot
   driver: ebs.csi.aws.com
   deletionPolicy: Delete
   ```

**Scheduled snapshots and storage review**

The snapshot schedule below is suspended until the owner confirms the existing `team-a/database-data` PVC, standard EBS CSI driver, snapshot controller/CRDs, and the `ebs-snapshot` class. The mounted template uses `generateName` to avoid a fixed-name collision. The Role permits snapshot creation in this namespace; it does not constrain the source PVC field. Application consistency/quiescing and restore verification are separate responsibilities. A successful Job confirms API creation, not snapshot readiness; monitor `readyToUse` and errors separately. Job history limits do **not** expire VolumeSnapshots/EBS snapshots. Define retention and recovery ownership before enabling the schedule; `deletionPolicy: Delete` deletes the backing snapshot when its Kubernetes snapshot is deleted.

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

Match storage to access semantics and recovery goals: databases may need io2/gp3 IOPS, shared web content may use EFS, logs/archives often fit S3, and analytics/AI may require FSx for Lustre or EBS throughput. Hot/warm/cold is a classification example, not an automatic EBS→EFS→S3 migration pipeline. Prepare the referenced `efs-standard`/`ebs-io2` classes separately. An EFS PVC request of `100Gi` does not enforce a filesystem quota or purchase that capacity, and PVC labels do not automatically become AWS billing tags.

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

The following Terraform fragment requires existing configured providers/caller identity and reviewed resource ownership. Mount targets, network/IAM access, application backups, and retention are separate prerequisites; it is not a complete production storage deployment.

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

**Read-only PVC candidate inventory**

Save the Python below as `unreferenced_pvcs.py` and use the explicit context/namespace commands. It reports Bound PVCs not referenced by the supplied current Pod snapshot, comparing `(namespace, name)` and handling non-PVC volumes. Kubernetes does not supply a standard `pv_used` annotation. List snapshots are not atomic and omit future/scaled-down controller consumers, pending jobs, and backup/recovery requirements. No deletion decision follows from this output. For EBS candidates use the account/tag-scoped query in [EKS06 question 6](06-eks-monitoring-logging-quiz.md); `available` means unattached, not unused.

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

Issues with other options:
- **A. Use the cheapest storage type for all workloads**: The cheapest storage may not meet performance requirements, potentially causing application performance degradation and business impact.
- **B. Migrate all data to S3**: S3 is suitable for some data types but not appropriate for latency-sensitive workloads or applications requiring block storage.
- **D. Minimize all volume sizes**: Excessively minimizing volume sizes can cause space shortage issues, and some volume types (e.g., gp2) have performance determined by size.
</details>

### 3. What is the most effective strategy for optimizing networking costs in Amazon EKS?

- A. Use the most expensive network bandwidth for all traffic
- B. Place all services in a single availability zone
- C. Optimize traffic patterns, minimize data transfer costs, and utilize VPC endpoints
- D. Block all network traffic
<details>
<summary>Show Answer</summary>

**Answer: C. Optimize traffic patterns, minimize data transfer costs, and utilize VPC endpoints**

**Explanation:**
The most effective strategy for optimizing networking costs in Amazon EKS is to optimize traffic patterns, minimize data transfer costs, and utilize VPC endpoints. This approach improves network traffic efficiency and reduces unnecessary costs by considering AWS network cost models.

**Key Networking Cost Optimization Strategies:**

1. **Traffic Pattern Optimization**:
   - Minimize cross-availability zone traffic
   - Minimize cross-region traffic
   - Implement locality-aware routing

2. **Minimize Data Transfer Costs**:
   - Use compression and efficient data formats
   - Implement caching strategies
   - Eliminate unnecessary data transfers

3. **VPC Endpoint Utilization**:
   - Private connections to AWS services
   - Bypass internet gateways
   - Reduce data transfer costs

Topology spread controls placement; it does not select the endpoints used by Service traffic. `spec.topologyKeys` was removed. The example uses `trafficDistribution: PreferSameZone` (stable in Kubernetes 1.35+) with fallback, not a zero-cross-AZ guarantee. Verify the actual proxy/CNI behavior and availability constraints.

S3/DynamoDB gateway endpoints have different pricing from interface endpoints. ECR image pulls need `ecr.api`, `ecr.dkr`, and S3 connectivity, private DNS, and endpoint security-group ingress on TCP 443 from the intended nodes/Pods. The CLI shows one interface endpoint; provision its DKR counterpart as in the Terraform fragment below. Review endpoint policies and the actual regional traffic/cost model; “private” does not imply free.

**Implementation Methods:**

1. **Availability Zone-Aware Pod Placement**:
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

2. **Service Topology Routing**:
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

3. **VPC Endpoint Configuration**:
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

4. **Locality Routing with Istio**:
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

Istio locality failover needs endpoint locality information and outlier detection. `failover.from/to` identify **Regions**, so putting AZ names there is incorrect. The DestinationRule above uses default locality priorities (same zone before other zones/Regions) with outlier detection; its sample ejection thresholds need workload testing. It is a separate option from kube-proxy Service traffic distribution, and a mesh is not required just to reduce transfer cost.



**Additional routing, endpoint, and billing examples**

The NetworkPolicy permits same-namespace frontend→API→database traffic plus a standard CoreDNS Deployment path. Add other required dependencies and verify CNI enforcement. Auto Mode node-local DNS or another resolver path needs its own appropriate allowance. Match selectors to the actual managed labels.

VirtualService evaluates the first matching rule, so the premium match precedes the catch-all and the matching DestinationRule subsets are defined. Workloads must carry those version labels. An end-user header supplied by a client is not proof of entitlement; enforce authorization server-side. The EnvoyFilter targets the actual ingress gateway namespace/labels and requires validation against the installed Istio/Envoy version. It compresses HTTP responses at the gateway; installing an outbound sidecar compressor does not by itself compress uploads. The legacy content_length/content_type fields are deprecated, not removed. This example uses response_direction_config/common_config; test CPU, latency, security, and protocol behavior.

The Terraform fragment assumes the VPC, private subnets, endpoint security group, and route table already exist in the owning module. NAT and route associations remain with that VPC owner. Sharing one zonal NAT across AZs is an availability/transfer-cost tradeoff, not the default HA saving; evaluate a regional NAT option separately.

Save the Python as network_costs.py. Set EXPECTED_CALLER_ACCOUNT, LINKED_ACCOUNT_ID, START_DATE, and END_DATE. reviewed-usage-types.json must contain a JSON array of exact USAGE_TYPE values selected from Cost Explorer/GetDimensionValues. This example uses the commercial AWS billing endpoint in us-east-1; verify the calling account and read permissions. API queries can incur charges. Dimensions in GetCostAndUsage do not support CONTAINS, so the helper uses exact EQUALS filters. It completes pagination and preserves Decimal amounts, currency units, and estimated state. Empty results/failures do not establish zero total network cost. Account-level rows require additional verified tag/resource mapping before attribution to a specific EKS cluster. Only the selected usage types are covered; ambiguous service/Regional/Region substring matching cannot reliably classify internet, AZ, and inter-Region charges. Dates use UTC with an exclusive End; check available history and billing finality. The former 100/50/200 USD thresholds were illustrative triage settings, not universal optimization decisions.

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

Issues with other options:
- **A. Use the most expensive network bandwidth for all traffic**: This incurs unnecessary costs, and not all workloads require high bandwidth.
- **B. Place all services in a single availability zone**: This may fail the multi-AZ availability requirements of critical workloads. A single-AZ choice for a noncritical environment still needs an explicit failure-tolerance decision.
- **D. Block all network traffic**: This is impractical and severely limits application functionality.
</details>

### 4. What is the most effective approach for optimizing Amazon EKS cluster management costs?

- A. Create as many clusters as possible
- B. Consolidate all workloads into a single cluster
- C. Optimize cluster count based on workload requirements and minimize management overhead
- D. Manage clusters manually
<details>
<summary>Show Answer</summary>

**Answer: C. Optimize cluster count based on workload requirements and minimize management overhead**

**Explanation:**
The most effective approach for optimizing Amazon EKS cluster management costs is to optimize cluster count based on workload requirements and minimize management overhead. This approach balances cluster management costs and operational complexity while meeting workload isolation and security requirements.

**Key Cluster Management Cost Optimization Strategies:**

1. **Maintain Appropriate Cluster Count**:
   - Cluster separation based on business requirements
   - Environment-based cluster separation (development, staging, production)
   - Consider security and compliance requirements

2. **Minimize Management Overhead**:
   - Utilize automated cluster management tools
   - Implement Infrastructure as Code (IaC)
   - Centralized monitoring and logging

3. **Optimize Cluster Resources**:
   - Appropriate control plane configuration
   - Efficient node group management
   - Utilize shared services

The short eksctl command illustrates creation, not a production network/IAM preset. Select the EKS version from the AWS catalog, review the VPC and API endpoint exposure using the [creation guide](../../eks/02-eks-cluster-creation.md), and keep controller permissions on dedicated identities. Node-group size bounds do not install an autoscaler or impose a spending cap. Standard/extended support fees, optional Provisioned Control Plane capacity, and shared management dependencies also affect the comparison.

The Terraform example uses the checked module **21.25.0**, whose minimum AWS provider is **6.59**; the shown provider pin is 6.64.0. Inputs deliberately have no guessed environment defaults. Supply owned private networking and API reachability, reviewed access entries, compatible/pinned add-ons with their IAM associations, and managed node groups. Standard EC2 nodes need the appropriate CNI/DNS/proxy path; this is not an Auto Mode example. Coordinate desired-size ownership with the autoscaler and use separate state/provider identities where the isolation model requires it. No plan/apply or production readiness is claimed.

**Implementation Methods:**

1. **Optimized EKS Cluster Configuration**:
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

2. **Cluster Management Automation with Terraform**:
   ```hcl
   terraform {
     required_version = ">= 1.5.7"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "= 6.64.0"
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

3. **Cluster Configuration Management with GitOps**:
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

4. **Multi-tenant Cluster Configuration**:
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

**Isolation, environment inputs, and context-aware evidence**

The Argo CD Application requires an installed controller, the reviewed repository/commit, and a pre-created `cluster-config` AppProject restricting repositories, destinations, and resource kinds. Replace the placeholder SHA and repository before use. Automatic synchronization/pruning is disabled for initial review; enable only the intended reconciliation behavior through the owner. Shared management credentials/controllers can expand the failure or security impact across otherwise separate clusters.

ResourceQuota constrains admission and object counts, not bills or tenant authorization. NetworkPolicy is additive across policies and requires enforcement by the CNI. The namespace example allows traffic within `team-a`, to/from the named shared namespace, and to a standard CoreDNS Deployment; adapt node-local/Auto Mode DNS and other dependencies explicitly. The shared API example allows only `team-a` to Pods labeled `app: shared-api` on TCP 8080. Reconcile any existing broad policies instead of leaving an older allow-all policy in place. RBAC, admission, IAM, and trust boundaries remain separate controls.

The environment tfvars below are overrides for the reviewed module above, not calls to an unprovided `./modules/eks-cluster`. Merge the appropriate account/network/version/add-on/access values into each environment's inputs and use its own state/backend and identity. Instance lists and counts are illustrative; review interruption tolerance and current regional options.

The collection script operates on **one explicit context** per run. Set `KUBE_CONTEXT`, `EXPECTED_API_SERVER`, `EXPECTED_CALLER_ACCOUNT`, `LINKED_ACCOUNT_ID`, `BILLING_TAG_KEY`, `BILLING_TAG_VALUE`, `START_DATE`, and `END_DATE`; repeat deliberately for each cluster. The API-server URL must match the reviewed EKS cluster. It saves actual Metrics API samples with their timestamps/windows/units and all tag-scoped Cost Explorer pages, instead of relabeling one context's requested resources as every cluster's utilization. Metrics Server and read permissions are prerequisites. Missing node samples are not zero usage, and short samples are not peak-demand history.

This uses commercial AWS billing endpoints and exclusive end dates. Choose available billing history; the former 2023 dates were configuration examples, not measured results. The tag mapping must exist in billing and may omit untagged/shared charges. Raw monetary units, cost basis, and estimated status are preserved; the script does not infer a total from the first group or recommend downsizing from a request/capacity threshold.

A large shared cluster can reduce duplicated control-plane/shared-service overhead but increases coordination and failure impact. Smaller clusters can improve independent maintenance and workload boundaries while increasing duplicated capacity and operations. Choose a hybrid split from trust, workload, and recovery requirements; cluster count alone does not guarantee isolation or lower total cost.

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

Issues with other options:
- **A. Create as many clusters as possible**: This increases control plane costs and management overhead for each cluster, reducing resource utilization.
- **B. Consolidate all workloads into a single cluster**: This may be suitable in some environments but doesn't consider security requirements, workload isolation, and failure blast radius.
- **D. Manage clusters manually**: Manual management increases error potential, degrades consistency, and increases operational overhead.
</details>

### 5. What is the most effective approach for cost monitoring and allocation in Amazon EKS?

- A. Only review AWS bills
- B. Implement tagging strategy, cost allocation tools, and continuous monitoring
- C. Allocate the same cost to all resources
- D. Use resources without cost monitoring
<details>
<summary>Show Answer</summary>

**Answer: B. Implement tagging strategy, cost allocation tools, and continuous monitoring**

**Explanation:**
The most effective approach for cost monitoring and allocation in Amazon EKS is to implement a tagging strategy, cost allocation tools, and continuous monitoring. This approach helps accurately track costs, allocate them by team or project, and identify cost optimization opportunities.

**Key Cost Monitoring and Allocation Strategies:**

1. **Comprehensive Tagging Strategy**:
   - Tags by business unit, team, project, environment
   - Apply consistent tagging rules
   - Implement automated tagging

2. **Cost Allocation Tool Utilization**:
   - AWS Cost Explorer and AWS Budgets
   - Specialized tools like Kubecost or CloudHealth
   - Custom dashboards and reports

3. **Continuous Monitoring and Optimization**:
   - Regular cost review and analysis
   - Anomaly detection and alerts
   - Implement optimization recommendations

Kubernetes labels, AWS resource tags, and activated billing tags are distinct. Namespace labels do not automatically propagate to Pods or AWS resources; put workload labels on the Pod template. The shown Organizations tag policy validates configured tag keys/values on supported resources, including EKS clusters. It does not add tags or configure required-tag enforcement. Review inherited policy and separate missing-tag controls. Billing activation/backfill is a separate operation; up to 12 months of backfill requires tags that actually existed historically.

The CUR command below creates a **legacy CUR**, not a Cost Explorer dashboard or CUR 2.0 export. AWS still supports legacy CUR. New designs should evaluate Data Exports/CUR 2.0 in the [FinOps guide](../../ops/13-finops-cost-platform.md). The legacy example requires an existing bucket in the declared Region, a reviewed CUR delivery policy, and reporting permissions. It does not create the bucket, Glue schema, Athena integration, or dashboard. Follow the delivery service-specific policy; do not substitute the CUR 2.0 `bcm-data-exports` policy for the legacy service.

**Implementation Methods:**

1. **Implement Tagging Strategy**:
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

2. **AWS Tag Policy Configuration**:
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

3. **Kubecost Installation and Configuration**:
Use the checked Kubecost 3.2.4 installation in the [source guide](../../eks/07-eks-cost-optimization.md), or OpenCost 1.121.2/chart 2.5.31 in [EKS06 question 6](06-eks-monitoring-logging-quiz.md). Kubecost 3.x uses ClickHouse/direct finops-agent collection; 2.x Prometheus values and command-line license tokens are not this setup. Reuse one owned deployment and review its migration, licensing, and storage requirements.

4. **Legacy CUR Delivery Setup**:
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

**Allocation review and supplementary configuration**

Reuse Q4’s context/account/tag-scoped collector for actual Metrics API samples and billing pages. Requests/limits are declared configuration, not actual usage; a request/limit ratio below 0.5 does not justify reducing requests. Compare the same workload, time window, units, and coverage instead of current replica counts against historical usage. Reconcile team/cost-center allocations with untagged and shared costs. For operational reporting/alerts, use the explicit collection/validation workflow in the [FinOps guide](../../ops/13-finops-cost-platform.md); failures/missing data must not become zero.

The 1,000 USD/80% budget below is illustrative. Verify the real activated Budgets tag-filter format and coverage; processed billing alerts do not impose a hard spending cap. The Terraform fragment assumes an existing CUR bucket, caller identity, providers, and Region input. Its owner must configure Athena result access, retention/encryption, Glue tables, and query permissions. Terraform supports `aws_quicksight_dashboard`, but account edition, datasets/templates, and permissions still require configuration.

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

For the regional TagResources call, verify the target Region and inspect `FailedResourcesMap`; a successful CLI exit does not prove every requested resource was tagged. Confirm actual resource tags before relying on billing allocation.

**Estimated allocation-rate dashboard**

This is an instantaneous **CPU+memory allocation-rate estimate in USD/hour** for one cluster’s Prometheus. It is not an invoice or complete namespace cost. The inputs are OpenCost allocation/price metrics (`job="opencost"` in this example) and kube-state-metrics Pod labels (`job="kube-state-metrics"`). Confirm the actual job labels and complete CPU/memory/price coverage. Keep the exporter’s workload namespace labels with the appropriate ServiceMonitor honor-label configuration. A shared backend needs consistent cluster identity in every aggregation and join.

Merge the first values fragment into the owned kube-prometheus-stack release. Pod team labels must be bounded and present on the Pod template; a namespace label does not create them. Missing team labels are grouped as `unassigned`. The queries deduplicate identical scrape copies; resolve conflicting price/ownership sources separately. GPU, storage, network, control-plane, idle/shared allocation, discounts, credits, and taxes are outside these two components. Missing data is not zero cost, and a rate is not a monthly dollar amount.

The PrometheusRule namespace/release label must match the source guide’s selectors. Replace `REPLACE_WITH_PROMETHEUS_UID` with the reviewed single-cluster data source before provisioning the dashboard. The ConfigMap’s `grafana_dashboard: "1"` label matches the source guide’s sidecar; its JSON is actually provided below. Verify rule health, data coverage, and dashboard queries. These examples were not connected to a live billing/Grafana deployment.

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

Issues with other options:
- **A. Only review AWS bills**: AWS bills only provide high-level cost information, making it difficult to identify detailed cost allocation or optimization opportunities.
- **C. Allocate the same cost to all resources**: This doesn't accurately reflect actual resource usage and cost generation, failing to clarify cost responsibility by team or project.
- **D. Use resources without cost monitoring**: Without cost monitoring, you cannot detect cost increases early or identify optimization opportunities, making budget management difficult.
</details>

### 6. Which approach best supports a scalable EKS cost-optimization workflow?

- A. Change resources manually without measuring outcomes
- B. Consider only billing data and ignore workload telemetry
- C. Combine cost visibility, resource telemetry, and appropriate autoscaling with clear ownership
- D. Run uncoordinated optimizers over the same resources

<details>
<summary>Show Answer</summary>

**Answer: C. Combine cost visibility, resource telemetry, and appropriate autoscaling with clear ownership**

**Explanation:**
The named tools are examples of complementary roles, not a requirement to install all of them. Choose an owned cost/telemetry path and workload-appropriate scaling. EKS Auto Mode, self-managed Karpenter, or Cluster Autoscaler may already own node capacity; separate ownership and avoid competing controllers. Savings and unchanged SLOs must be measured, and installing cost tools does not automatically wire billing data into HPA/Karpenter policies.

**Key Cost Optimization Tools and Features:**

1. **Kubecost**:
   - Kubernetes resource cost visibility
   - Cost allocation by namespace, deployment, service
   - Cost optimization recommendations
   - Cost forecasting and budget management

2. **Karpenter**:
   - Intelligent node provisioning and management
   - Instance selection within workload, capacity, and pricing constraints
   - Provisioning/scaling behavior that must be verified in the actual environment
   - Spot Instance utilization optimization

3. **AWS Cost Explorer**:
   - Cost analysis across AWS services
   - Tag-based cost allocation
   - Cost trends and forecasting
   - Reserved Instance and Savings Plans recommendations

4. **Kubernetes Auto-scaling Tools**:
   - Horizontal Pod Autoscaler (HPA)
   - Vertical Pod Autoscaler (VPA)
   - Cluster Autoscaler
   - Cluster Proportional Autoscaler

**Implementation Methods:**

1. **Kubecost Installation and Configuration**:
Reuse the checked installation and allocation-data prerequisites from Q5 and the [source guide](../../eks/07-eks-cost-optimization.md). Kubecost 3.2.4 uses the current `kubecost/kubecost` chart and ClickHouse/direct-agent architecture; product features depend on edition/configuration. OpenCost is a separate option. Do not deploy a second collector over an existing owned setup.

2. **Karpenter Installation and Configuration**:
Save the following as `karpenter-values.yaml`, replace the account/role/cluster/endpoint/queue with reviewed existing values, and follow the [Karpenter guide](../../autoscaling/02-karpenter.md). The checked example uses 1.14.1; EKS 1.36 needs at least 1.13 in the compatibility matrix. These are `settings.*` keys, not ignored `controller.clusterName/clusterEndpoint` values. The IRSA trust must match `system:serviceaccount:karpenter:karpenter` and its audience; do not combine conflicting IRSA/Pod Identity assignments. Prepare controller/node IAM, node access, subnets/security groups, the interruption queue/event wiring, and reliable bootstrap capacity first. Fresh Helm installs and CRD upgrades have different ownership/lifecycle steps; the controller upgrade alone does not upgrade existing CRDs.

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

3. **Configure Horizontal Pod Autoscaler**:
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

4. **Configure Vertical Pod Autoscaler**:
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

**Tool Integration and Workflow:**

1. **Cost Visibility and Analysis**:
   - Kubecost: In-cluster resource cost analysis
   - AWS Cost Explorer: Cost analysis across AWS services
   - Integrated dashboards: Overall cost overview and trends

2. **Automated Resource Optimization**:
   - Karpenter: Optimal node provisioning and management
   - HPA/VPA: Workload-level resource optimization
   - Spot Instance utilization: Cost-efficient computing resources

3. **Cost Allocation and Responsibility**:
   - Tag-based cost allocation
   - Cost analysis by namespace and label
   - Cost reporting by team and project

4. **Continuous Optimization and Improvement**:
   - Implement cost optimization recommendations
   - Regular cost review and analysis
   - Set and track cost reduction goals

**Owned integration and API validation**

The VPA examples use Off while HPA uses CPU/memory utilization denominators. Enable automatic request changes only after coordinating that control loop. Cluster Proportional Autoscaler scales component replicas from cluster-size signals; it is not an equivalent node provisioner. Karpenter limits, instance preferences, and consolidation delay are not spending or termination-time guarantees. Inspect resolved AMIs and pin a tested version/ID for controlled changes instead of treating `al2023@latest` as immutable.

PriorityClass controls scheduling/preemption priority, not cost allocation or guaranteed availability. Govern who can assign priorities; scheduler preemption makes a best-effort attempt to respect PDBs. Review disruption and workload recovery. Cost observations and recommendations need an explicit reviewed policy/change path before controllers act; the architecture diagram does not implement that integration.

The Terraform alternative uses Helm provider 3.3.0 values-file configuration and AWS provider 6.64.0. Supply the explicit Kubernetes context and reviewed chart values, including compatible identity, storage, and license-secret references; it does not create those prerequisites. Do not put raw license/cloud credentials into values or state. Reconcile an existing release with its owner instead of installing it again through a second manager. The 1,000 USD/80% budget is illustrative, uses a verified billing tag filter, and is not a hard spending cap. No cluster/Helm provisioning or notification was executed in this audit.

The API example below explicitly targets OpenCost 1.121.2 from the earlier setup, not a guessed Kubecost 3.x URL. Its `/allocation` API accepts `namespace,controllerKind,controller` aggregation; `deployment` is not the documented generic aggregation key. The response data is an array of allocation-set maps, not a direct namespace/Deployment dictionary. Validate HTTP/API errors and data coverage; an empty result is not zero cost or evidence of overprovisioning. Allocation quantities, usage, requests, byte-hours/core-hours, and current replica counts have different meanings and time windows. Inspect the versioned schema and comparable workload metrics before recommending rightsizing. Raw allocation estimates must be reconciled with billing and idle/shared-cost policies.





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
      version = "= 6.64.0"
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
  version          = "3.2.4"
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

The other choices omit measurement, workload signals, or coordinated ownership. Competing controllers can undermine stability and cost predictability.
</details>
