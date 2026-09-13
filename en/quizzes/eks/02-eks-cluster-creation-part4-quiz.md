# EKS Cluster Creation Quiz - Part 4

> **Last Updated**: September 11, 2026

This quiz connects the Terraform cluster guide to scaling, identities and lifecycle operations. The final section checks Terraform-specific concepts. Examples require reviewed account/Region/kubeconfig, IAM and network prerequisites; they were not deployed during this audit.

## Basic Concept Questions

1. What is the main provisioning difference between Cluster Autoscaler and Karpenter?
   * A) CA is an AWS managed service
   * B) CA scales existing groups; Karpenter provisions selected individual capacity
   * C) CA measures only CPU and Karpenter only Pod count
   * D) Karpenter replaces the Kubernetes scheduler

<details>
<summary>Show Answer</summary>

**Answer: B) CA scales existing groups; Karpenter provisions selected individual capacity**

Cluster Autoscaler adjusts the size of discovered, predefined node groups/ASGs. Karpenter creates NodeClaims and EC2 capacity selected through NodePools and EC2NodeClasses. Kubernetes schedules Pods; Karpenter does not replace the Kubernetes scheduler.

Both consider unschedulable workload requests and placement constraints. Neither is simply “CPU percentage versus Pod count,” and neither resizes a running EC2 instance in place. Karpenter can replace capacity with differently sized instances; VPA separately manages Pod resource requests.

**Cluster Autoscaler example:** for EKS 1.36, use a matching minor and a dedicated ServiceAccount with reviewed IAM and discovery tags. Chart 9.59.0 needs the explicit v1.36.1 image override. Render RBAC, image and arguments before installation:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
Keep local-storage and system-Pod safeguards unless a reviewed workload/data policy requires otherwise. Mixed instance types in one CA-managed group should have comparable CPU/memory/GPU shapes.

**Karpenter example:** install a compatible controller/CRDs and configure its IAM, node authorization, discovery tags, interruption handling and capacity limits separately. Replace both AMI placeholders with reviewed AL2023 images matching the cluster version and each architecture. Workload images must support both architectures if both are allowed:

```yaml
# Karpenter NodePool (karpenter.sh/v1) + EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5a.large", "m5d.large", "m5ad.large", "m6g.large"]
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
  role: KarpenterNodeRole-my-cluster
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_REVIEWED_AMD64_IMAGE
    - id: ami-REPLACE_WITH_REVIEWED_ARM64_IMAGE
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
| Comparison | Cluster Autoscaler | Karpenter |
| --- | --- | --- |
| Scaling unit | Existing node-group/ASG capacity | NodeClaims and selected EC2 capacity |
| Configuration | Groups, discovery, IAM and controller | NodePools, EC2NodeClasses, IAM and controller |
| Removal | Requires scheduling and disruption checks | Subject to consolidation, budgets and disruption controls |
| Historical timing claim in the original guide | 2–10 minutes, unverified | Under 1 minute, unverified |

The original timing numbers are retained as **unverified historical claims**, not benchmarks reproduced in this audit or guaranteed current performance. Node startup, images, quotas and workload constraints affect both tools. Do not infer a universal cost, simplicity or latency ranking from that table.

</details>

2. Which capacity types are in the current EKS CreateNodegroup API?
   * A) Reserved, On-Demand, Spot
   * B) On-Demand, Spot, Dedicated
   * C) ON_DEMAND, SPOT, CAPACITY_BLOCK
   * D) Standard, Burstable, Compute-Optimized

<details>
<summary>Show Answer</summary>

**Answer: C) ON_DEMAND, SPOT, CAPACITY_BLOCK**

The current EKS CreateNodegroup API includes **ON_DEMAND, SPOT and CAPACITY_BLOCK**. A managed node group uses one capacity type; use separate groups for separate capacity pools.

On-Demand avoids Spot reclamation but is not an interruption or availability guarantee. Spot uses spare capacity and requires interruption-tolerant workloads; advertised discounts are not guaranteed savings. Reserved Instances/Savings Plans are billing arrangements, not additional CreateNodegroup enum values.

Capacity Blocks are a separate time-bound reservation workflow for supported instances/Regions. They require a custom launch template targeting the reservation, a matching AZ/subnet and reservation-aware scaling. EKS creates a scheduled scale-down 40 minutes before reservation end; do not modify/delete that action. The examples below are conventional On-Demand/Spot alternatives, not Capacity Block provisioning.

**AWS CLI:** use an unused node-group name, existing private subnets and an approved EC2 node role (including the required CNI identity path). Wait for group activation and then verify actual Node/workload readiness:

```bash
set -euo pipefail
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types t3.medium t3a.medium --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}"
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$NEW_NODEGROUP_NAME"
```
**eksctl alternative:** save a configuration for the existing cluster and unused group names, then use `eksctl create nodegroup -f nodegroups.yaml`. Use `managedNodeGroups` and `spot`, not the unsupported `capacityType` fields from the original example:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: ng-on-demand
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 5
  spot: false
- name: ng-spot
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large]
  privateNetworking: true
  desiredCapacity: 2
  minSize: 0
  maxSize: 5
  spot: true
```
Use affinity/selectors and tolerations to place appropriate workloads. Managed node groups have built-in Spot rebalance/drain handling; Node Termination Handler is not a universal extra requirement. PDBs cannot prevent EC2 reclaiming a Spot instance, and not every Pod receives the full interruption window. Plan checkpointing, spare capacity and interruption recovery.

</details>

3. Which field is mandatory in each Fargate profile selector?
   * A) Instance type
   * B) Namespace; labels are optional
   * C) Security group ID
   * D) Maximum Pod count

<details>
<summary>Show Answer</summary>

**Answer: B) Namespace; labels are optional**

Each profile selector requires a **namespace**; labels are optional. A profile also needs a name and Pod execution role, and uses eligible private subnets. It has no security-group parameter. Pod security groups are a separate supported policy mechanism, not a Fargate-profile field.

Use an unused profile name and reviewed private subnet IDs. This selector intentionally targets only application Pods, leaving existing CoreDNS placement unchanged:

```bash
set -euo pipefail
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"fargate-lab","labels":{"app":"nginx"}}]'
aws eks describe-fargate-profile --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --fargate-profile-name "$NEW_FARGATE_PROFILE" \
  --query 'fargateProfile.{status:status,subnets:subnets,selectors:selectors}'
```
Wait for `ACTIVE` before launching matching Pods. An alternative eksctl profile definition follows; validate the cluster's private subnet discovery and execution-role setup before creating it:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
fargateProfiles:
- name: fp-application
  selectors:
  - namespace: fargate-lab
    labels:
      app: nginx
```
The namespace and labeled workload still need to be created separately. If multiple profiles match, EKS uses alphanumeric profile-name ordering unless the Pod selects a matching profile with `eks.amazonaws.com/fargate-profile`. Profiles are immutable; replacing/deleting them affects their Pods.

The Pod execution role serves the Fargate infrastructure, not application AWS access. Use a compatible workload identity such as IRSA; EKS Pod Identity is not supported on Fargate. Moving CoreDNS to Fargate requires its compute configuration and a matching profile, not merely adding `kube-system` to a selector.

Fargate charges for **provisioned capacity**, determined by requested resources plus overhead/rounding; it does not bill only sampled CPU/memory usage. Inspect `CapacityProvisioned`. EKS Fargate does not support Spot, DaemonSets, privileged containers, host networking or EBS-mounted workload volumes. Persistent EFS uses static provisioning; profile matching alone does not create a file system/PV/PVC. Account for DNS, image pull, STS and other required network paths.

</details>

4. Which is not a NodegroupUpdateConfig field?
   * A) maxUnavailable
   * B) maxUnavailablePercentage
   * C) updateStrategy
   * D) Node-group operation timeout

<details>
<summary>Show Answer</summary>

**Answer: D) Node-group operation timeout**

`NodegroupUpdateConfig` supports integer `maxUnavailable`, integer `maxUnavailablePercentage`, and `updateStrategy` (`DEFAULT` or `MINIMAL`). Set the count or percentage, not both. A percentage is not a valid value for `maxUnavailable` itself.

An operation timeout is not a NodegroupUpdateConfig field. `--force` belongs to a version-update request and can bypass Pod eviction protection; it is not a stored update-config setting. A CLI/IaC wait timeout is also distinct from the service operation.

```bash
set -euo pipefail
UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":2,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
For the alternative percentage setting, use `{"maxUnavailablePercentage":20,"updateStrategy":"DEFAULT"}`. Track the returned update ID to `Successful` before starting a version update. `DEFAULT` launches replacement capacity first; `MINIMAL` terminates selected old nodes first to reduce temporary extra capacity.

For a reviewed three-replica Deployment in `update-lab`, this PDB constrains voluntary eviction:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
A PDB is not a general availability guarantee. Direct deletions, failures and the workload controller's own rollout differ from eviction. Check spare capacity, readiness and volumes. Do not promise that an already running EKS update can simply be paused or rolled back; stop subsequent planned changes and follow the applicable recovery procedure.

</details>

5. Which control-plane upgrade step is supported by the normal EKS version workflow?
   * A) Skip directly across two minors
   * B) Jump to any upstream release
   * C) Move to the next EKS-supported minor after readiness checks
   * D) Upgrade nodes above the control-plane version first

<details>
<summary>Show Answer</summary>

**Answer: C) Move to the next EKS-supported minor after readiness checks**

EKS control-plane upgrades proceed **one minor version at a time**, such as 1.34 → 1.35 → 1.36. Confirm that each target is offered by EKS; an upstream Kubernetes release is not proof of EKS availability. Do not infer a future major-version upgrade policy from today's Kubernetes 1.x workflow.

Before upgrading the control plane, bring managed and Fargate nodes to its current minor as required by the EKS procedure; update self-managed/hybrid nodes as recommended. Kubelets must never be newer than the API server. The general skew ceiling for Kubernetes 1.28+ permits kubelets up to three minors older, but that is not a recommendation to ignore EKS upgrade prerequisites.

Review insights, removed APIs, add-on compatibility, capacity and application/data backups first. EKS does not provide ordinary administrator shell access to its managed etcd for a DIY snapshot command; use supported cluster/resource and persistent-data backup/restore procedures. This command only enforces the one-minor step; it does not replace those checks:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${NEXT_KUBERNETES_VERSION:?Confirm the next supported EKS minor}"
CURRENT_KUBERNETES_VERSION=$(aws eks describe-cluster \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --query cluster.version --output text)
if [[ "$CURRENT_KUBERNETES_VERSION" =~ ^1\.([0-9]+)$ ]]; then
  CURRENT_MINOR="${BASH_REMATCH[1]}"
else
  printf '%s\n' 'Unexpected cluster version; stop and inspect.' >&2
  exit 1
fi
EXPECTED_NEXT_VERSION="1.$((CURRENT_MINOR + 1))"
[ "$NEXT_KUBERNETES_VERSION" = "$EXPECTED_NEXT_VERSION" ] || {
  printf '%s\n' 'Only the next minor version is allowed in this upgrade example.' >&2
  exit 1
}
CLUSTER_UPDATE_ID=$(aws eks update-cluster-version --name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --kubernetes-version "$NEXT_KUBERNETES_VERSION" \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$CLUSTER_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
Wait for that update ID to succeed, then update nodes and compatible cluster components in their documented order. Match Cluster Autoscaler's minor to the cluster and kubectl within its supported skew.

Current EKS offers conditional rollback to the previous minor within seven days of a completed in-place upgrade. It is not available for a cluster created at that version or an end-of-extended-support automatic upgrade. Prepare compatible nodes/add-ons first; Auto Mode manages its node rollback. Rollback does not rewind etcd, workloads or persistent data. See the official rollback readiness requirements instead of treating it as an unconditional undo.

</details>

## Short Answer Questions

6. How can the instance type of an EKS managed node group be changed?

<details>
<summary>Answer and Explanation</summary>

It depends on where the instance type is configured:

* A type set in the managed node group's `instanceTypes` is not an `UpdateNodegroupConfig` field. Create a replacement group, validate capacity and migrate workloads before retiring the old one.
* If the group was originally created with **your custom launch template**, with the instance type in that template rather than the EKS group field, you can update to a new version of the **same template**. EKS recycles the nodes. Do not modify the EKS-generated template or assume you can switch arbitrary template IDs.
* For self-managed ASGs, a launch-template update/instance refresh also needs a Kubernetes-aware drain and lifecycle design; EC2 replacement alone is not a PDB-aware migration.

Review AMI architecture, drivers, Pod IP limits, labels/taints, storage topology, quotas and PDBs. For Terraform-owned resources, make the change through the owning state and inspect replacement actions; do not make an out-of-band CLI change and assume the state remains correct.

</details>

7. How do you allow only private access to the Kubernetes API endpoint?

<details>
<summary>Answer and Explanation</summary>

Set private access to true and public access to false. In module v21 these are `endpoint_private_access` and `endpoint_public_access`; change them through the owning Terraform state when applicable.

Before disabling public access, verify DNS, routes and security rules from the administrator's connected network to the private endpoint. A system can reach it from the VPC **or another properly connected network**; it need not physically reside in the VPC. This changes the Kubernetes API endpoint, not access to the separate AWS EKS service API.

For an API-owned cluster, the equivalent CLI operation is:

```bash
set -euo pipefail
ENDPOINT_UPDATE_ID=$(aws eks update-cluster-config \
  --region "${EXAMPLE_REGION:?}" --name "${EXAMPLE_CLUSTER:?}" \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true \
  --query update.id --output text)
aws eks describe-update --region "$EXAMPLE_REGION" --name "$EXAMPLE_CLUSTER" \
  --update-id "$ENDPOINT_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
Track that update ID to `Successful` and test authenticated kubectl access from the intended management path. A single `InProgress` response is not completion.

</details>

8. What is the EKS Kubernetes version support lifecycle?

<details>
<summary>Answer and Explanation</summary>

An EKS minor version receives **14 months of standard support**, followed by **12 months of extended support** at an additional cluster-hour cost. The clock starts at its EKS release date, not the upstream release date.

On September 11, 2026, EKS lists 1.34–1.36 in standard support and 1.31–1.33 in extended support. Check the current EKS release calendar before selecting a deployment/upgrade target; upstream 1.37 alone does not make it an EKS target.

Extended support is enabled by default. The cluster upgrade policy determines behavior at the end of standard support. After extended support ends, EKS automatically upgrades the control plane to the oldest supported extended version; the old version does not run indefinitely without updates. Managed/self-managed/hybrid nodes and add-ons require their own lifecycle actions, while Auto Mode manages its capabilities and nodes.

Do not rely on a fixed “four versions,” “60-day notice,” or “2–3 month release lag” rule from the old quiz. Use the published dates and policy for the actual cluster. Upstream Kubernetes has its own support schedule; the old nine-month comparison is not current guidance.

</details>

## Hands-on Questions

9. Design Pod autoscaling with CPU 75% / memory 80% utilization targets and a node group bounded at 2–10 nodes, initially 3.

<details>
<summary>Answer and Explanation</summary>

Separate **Pod demand scaling** from **node capacity scaling**. Use HPA resource-utilization targets of CPU 75% and memory 80%, with Metrics Server and valid container requests. HPA chooses the largest replica recommendation from the metrics, subject to tolerance, limits and stabilization; it is not an immediate “threshold exceeded” alarm.

Then use Cluster Autoscaler for a managed node group with min=2, max=10 and initial desired=3. The equivalent Terraform module node-group fields are `min_size`, `max_size` and `desired_size`; review the owning configuration. This complete eksctl alternative is for a new group on the reviewed existing cluster:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: autoscaling-workers
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  minSize: 2
  maxSize: 10
  desiredCapacity: 3
```
Use the dedicated, authorized Cluster Autoscaler setup in question 1. Bounds alone do not run an autoscaler. CA reacts to unschedulable Pod requests and removal constraints; it does not implement the requested CPU/memory percentages itself.

In a new `autoscaling-lab` namespace, the following Deployment/HPA demonstrates requests and both metrics. The Pod replica range 2–20 is separate from the node range 2–10:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: autoscaling-lab
spec:
  replicas: 2
  selector:
    matchLabels: {app: my-app}
  template:
    metadata:
      labels: {app: my-app}
    spec:
      automountServiceAccountToken: false
      containers:
      - name: web
        image: nginx:1.30.4
        ports:
        - containerPort: 80
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```
Inspect HPA conditions, metric availability, Pending reasons and autoscaler decisions under an approved load test. Memory use may not fall proportionally when replicas increase, so validate that metric for the application. These request/limit values are examples, not measured sizing.

Do not add independent ASG CPU/memory target-tracking policies to the same desired-capacity loop. They can compete with CA and have different draining behavior. EC2 does not supply ordinary memory utilization by default; any separate non-CA design needs a correctly published custom metric and a custom namespace, not an assumed `AWS/EC2` memory metric. No such ASG policy is required for this HPA+CA solution.

</details>

## Advanced Questions

10. Explain a blue/green node-group upgrade, its risks and a guarded migration workflow.

<details>
<summary>Answer and Explanation</summary>

Create replacement capacity, test it, migrate gradually and retire the old group only after application/data validation. Keep old capacity and compatible state while rollback remains necessary; sharing one cluster is not complete isolation or a zero-downtime guarantee.

Review quotas, subnet IPs, images/architecture, labels, taints, daemon overhead, PDBs, local data and volume AZ/attachment constraints. StatefulSet membership does not itself make a volume portable. Investigate DNS failures before changing TTLs or adding a service mesh. Confirm monitoring/log collectors actually cover new nodes.

The following CLI example is for **API-owned groups**, with unused green-group names. For Terraform- or eksctl/CloudFormation-owned groups, perform equivalent changes through that owner to avoid drift and orphaned stacks.

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}" "${OLD_NODEGROUP_NAME:?}" "${GREEN_NODEGROUP_NAME:?}"
[ "$OLD_NODEGROUP_NAME" != "$GREEN_NODEGROUP_NAME" ]
OLD_NODEGROUP_ARN=$(aws eks describe-nodegroup --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --nodegroup-name "$OLD_NODEGROUP_NAME" \
  --query nodegroup.nodegroupArn --output text)
aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME" --scaling-config minSize=3,maxSize=10,desiredSize=5 \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --instance-types t3.large \
  --ami-type AL2023_x86_64_STANDARD --node-role "${NODE_ROLE_ARN:?}" \
  --labels audit.example.com/pool=green
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GREEN_NODEGROUP_NAME"
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l "eks.amazonaws.com/nodegroup=$GREEN_NODEGROUP_NAME" -o wide
```
A node-group tag is not proof that the underlying ASG has Cluster Autoscaler discovery tags. Verify the actual ASG tags/IAM if CA will manage it. Check new Node readiness and a separately scoped canary workload before migrating the main workload.

Drain one confirmed old node at a time. This deliberately omits automatic emptyDir deletion and forced eviction:

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
After each step verify readiness, application health and persistent data. Stop when drain fails and resolve the cause. After all workloads are validated and the retained old group is no longer needed, compare its original ARN before this separate final deletion:

```bash
# A separate final step for API-owned groups only.
: "${OLD_NODEGROUP_ARN:?Use the ARN captured before migration}"
if [ "${MIGRATION_VERIFIED:?Set yes only after application/data checks}" = yes ]; then
  CURRENT_OLD_GROUP_ARN=$(aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --nodegroup-name "${OLD_NODEGROUP_NAME:?}" \
    --query nodegroup.nodegroupArn --output text) || exit 1
  [ "$CURRENT_OLD_GROUP_ARN" = "$OLD_NODEGROUP_ARN" ] || {
    printf '%s\n' 'Node-group identity changed; no deletion attempted.' >&2
    exit 1
  }
  aws eks delete-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME" || exit 1
  aws eks wait nodegroup-deleted --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$OLD_NODEGROUP_NAME"
fi
```

</details>


## Terraform Checks

11. What can a terraform_remote_state reader access?
   * A) Only declared outputs at the storage layer
   * B) The full state snapshot, even though HCL exposes outputs
   * C) No sensitive values under any conditions
   * D) Only resources in its own module

<details>
<summary>Show Answer</summary>

**Answer: B) The full state snapshot, even though HCL exposes outputs**

State access is an authorization boundary. Publish selected values separately when consumers must not read the full snapshot.

</details>

12. Which input names match the EKS module v21 example?
   * A) cluster_name and cluster_version
   * B) name and kubernetes_version
   * C) clusterId and versionNumber
   * D) cluster_addons and cluster_compute_config

<details>
<summary>Show Answer</summary>

**Answer: B) name and kubernetes_version**

Module v21 renamed these inputs. AWS resource fields such as aws_eks_addon.cluster_name and module outputs such as cluster_name still use their own documented names; do not globally replace every occurrence.

</details>

13. Which statement about the S3 backend example is correct?
   * A) encrypt=true also enables state locking
   * B) DynamoDB is the only locking option
   * C) use_lockfile=true enables S3 locking; clients and lock-file IAM permissions must be prepared
   * D) One lock coordinates all state keys

<details>
<summary>Show Answer</summary>

**Answer: C) use_lockfile=true enables S3 locking; clients and lock-file IAM permissions must be prepared**

Use Terraform 1.10+ for S3 lock files. DynamoDB locking is deprecated; migrate coordinated clients instead of deleting the table while old clients still depend on it.

</details>

14. Does an aws_eks_pod_identity_association create the Kubernetes ServiceAccount?
   * A) Yes, with cluster-admin
   * B) No; the namespace/ServiceAccount and supported agent/SDK path are separate prerequisites
   * C) Yes, and it installs Metrics Server
   * D) Only on Fargate

<details>
<summary>Show Answer</summary>

**Answer: B) No; the namespace/ServiceAccount and supported agent/SDK path are separate prerequisites**

The association binds AWS identity to an existing Kubernetes identity. Scope trust and permissions, keep required session tags enabled, handle propagation, and verify the actual assumed role.

</details>

15. What does the module constraint ~> 21.0 allow?
   * A) Only 21.0.0
   * B) Only patches in 21.0.x
   * C) Compatible-range 21.x minor and patch versions below 22.0, without guaranteeing behavior
   * D) Every future major version

<details>
<summary>Show Answer</summary>

**Answer: C) Compatible-range 21.x minor and patch versions below 22.0, without guaranteeing behavior**

~> 21.0.0 restricts the range to 21.0.x. The guide pins module versions explicitly; .terraform.lock.hcl records provider selections rather than remote module versions. Review saved plans before applying.

</details>

## References

- [API_CreateNodegroup.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_CreateNodegroup.html)
- [ml-node-groups.html](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-groups.html)
- [fargate-profile.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html)
- [fargate-pod-configuration.html](https://docs.aws.amazon.com/eks/latest/userguide/fargate-pod-configuration.html)
- [API_NodegroupUpdateConfig.html](https://docs.aws.amazon.com/eks/latest/APIReference/API_NodegroupUpdateConfig.html)
- [launch-templates.html](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)
- [kubernetes-versions.html](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [update-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)
- [rollback-cluster.html](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
- [cas.html](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [horizontal-pod-autoscale](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [s3](https://developer.hashicorp.com/terraform/language/backend/s3)
- [remote-state-data](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
