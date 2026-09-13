# EKS Auto Mode Operator Training Curriculum (2 Hours)

> **Audience**: Infrastructure/platform engineers operating EKS
> **Prerequisites**: Kubernetes fundamentals and EKS operations experience
> **Reviewed**: September12,2026

## Learning Objectives

Distinguish AWS-managed responsibilities from operator ownership, design Auto Mode NodePool/NodeClass resources, evaluate improvements through workload/cost/availability evidence, and investigate node interruption. Fixed savings percentages and provisioning times are not promised outcomes.

## Schedule and Preparation

| Part | Duration | Breakdown |
| --- | --- | --- |
|1: Architecture and placement |40min | Architecture10 + NodePool/NodeClass15 + scaling15 |
|2: Optimization and lifecycle |35min | Spot10 + cost10 + workload10 + lifecycle5 |
|Break |10min | |
|3: Observability and diagnosis |25min | Nodes8 + signal correlation8 + scenarios9 |
|4: IaC/GitOps |10min | IaC5 + ArgoCD5 |

Total120minutes. Verify current APIs, prepared lab environment, account/region/kubeconfig, permissions and cost limits using the [Auto Mode guide](../eks-auto-mode/README.md). Lecture-only delivery can use captured events, NodeClaims and metrics. Actual FIS fault injection or node deletion is not automatically executed by this curriculum.

Line counts and keyword occurrence counts do not establish documentation quality or adequate coverage, so the old assessment table was removed. Use the references below and supplement organization-specific Terragrunt/operating procedures for the versions in use.

## Part1: Architecture and Placement (40min)

### 1-1. Management Boundaries (10min)

Use the [getting-started guide](../eks-auto-mode/01-getting-started.md) to compare Auto Mode, managed node groups and self-managed Karpenter. Auto Mode provides Karpenter-based managed compute; operators still own workload requests, PDBs and supported NodeClass networking/storage/identity configuration.

Auto Mode uses managed Bottlerocket variants, not user-selectable AL2023/Bottlerocket AMIs, arbitrary userData, SSH or SSM access. Check actual enablement/existence of the general-purpose/system pools. Do not assume its managed controller appears as an ordinary in-cluster Pod.

### 1-2. NodePool and NodeClass (15min)

Use the [configuration guide](../eks-auto-mode/02-nodepool-configuration.md) for `eks.amazonaws.com` labels and NodeClass APIs. Do not mix them with self-managed Karpenter's `karpenter.k8s.aws` instance labels/EC2NodeClass. Custom NodeClasses are supported; AWS does not choose every setting for you.

This **schema example** assumes an existing default NodeClass and Arm-compatible images. CPU/memory limits are not absolute billing caps and concurrent provisioning may temporarily exceed them. It is not a universal pool for every GPU/Spot workload.

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

Compare Pod selectors/affinity, requests, taints/tolerations and pool constraints. Arm migration requires image-manifest, native-dependency and performance validation.

### 1-3. Scaling (15min)

Follow the [scaling guide](../eks-auto-mode/03-scaling-behavior.md): unschedulable Pods, pool constraints, node provisioning and Pod readiness.40–90seconds is not guaranteed; measure image pulls, IP/quota/capacity and volume dependencies.

Compare WhenEmpty, WhenEmptyOrUnderutilized and consolidateAfter, including workloads whose requests differ from utilization. Consolidation does not replace manual optimization or load validation. Drift does not guarantee immediate one-at-a-time replacement for every change.

## Part2: Optimization and Lifecycle (35min)

### 2-1. Spot (10min)

Use the [Spot guide](../eks-auto-mode/04-spot-strategies.md) to review compatible instance diversity, critical capacity and interruption/recovery. Spot-only is mandatory, not a preference with automatic on-demand fallback. do-not-disrupt/PDBs do not prevent Spot reclamation or node failure.

### 2-2. Cost (10min)

The [cost guide](../eks-auto-mode/06-cost-management.md) separates EC2, Auto Mode fees, EBS, load balancers/NAT/transfers and observability. Do not present multiplied hypothetical Graviton/Spot/consolidation percentages as measured results.

Eligible EC2 Instance Savings Plans/RIs can apply to EC2 usage alongside Compute Savings Plans, subject to their terms. They do not automatically discount separate Auto Mode fees or stack onto Spot. Savings Plans are not capacity reservations. Make purchase decisions separately using hourly eligible baselines and existing coverage.

### 2-3. Workload Design (10min)

Use the [workload guide](../eks-auto-mode/08-workload-optimization.md) to compare web, batch, GPU and system workloads' requests, images/architecture, storage and SLOs. HPA controls replicas, VPA recommends/updates CPU/memory, and Auto Mode supplies nodes. GPU workloads need compatible models/drivers; VPA does not choose GPU instances.

VPA Off is recommendation-only. Pool separation follows team, availability, authorization and capacity needs; taints/labels are not tenant-security boundaries.

### 2-4. Node Lifecycle (5min)

Distinguish AWS-documented **default expiry336h(14days), default NodeClaim termination grace24h and maximum managed-instance lifetime21days** using the [lifecycle guide](../eks-auto-mode/07-node-lifecycle.md). The former720h(30day) example is not Auto Mode's baseline, nor is any lifetime a guaranteed uptime.

Budgets rate-limit voluntary drift/emptiness/consolidation; they cannot defer all expiration/interruption/repair outside business hours. Inspect stored NodeClaim values, PDBs, termination time and application recovery.

## Break (10min)

## Part3: Observability and Diagnosis (25min)

### 3-1. Node Observations (8min)

Use [operations guidance](../eks-auto-mode/05-operations.md) for NodePool/NodeClass/NodeClaim conditions, events and node/workload metrics. Do not assume a normal Karpenter scrape endpoint or Deployment logs for the AWS-managed controller. Configure supported managed-component logs and actual CloudWatch/Prometheus publishers.

These basic alerts use kube-state-metrics and cover the whole cluster. Auto-Mode-only views require allowed compute-type labels and a correct join. Deleted nodes or missing series require separate no-data/history investigation.

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

Compare NodePool status.resources with spec.limits in matching units. The invented karpenter_nodeclaims_state/karpenter_nodepool_usage_limit ratio was removed. CloudWatch Events and EventBridge are not two sequential services; verify actual event sources, rules, targets and delays.

### 3-2. Correlating Signals (8min)

Use the [observability guide](../observability/09-observability-optimization.md) and [Grafana guide](../observability/grafana/README.md) to distinguish trace-to-logs, derived fields and exemplars. TraceID need not be an indexed Loki label; avoid high cardinality with log fields/structured metadata and queries.

Verify version-specific settings such as tracesToLogsV2, datasource UIDs/URLs, label mapping, sampling and retention. Exemplars require compatible publishers, collection, storage and UI; one flag does not create trace links for existing data. Prepare a real correlated-request example for the lecture.

### 3-3. Evidence-Based Scenarios (9min)

| Symptom | Evidence | Avoid premature conclusions |
| --- | --- | --- |
| Pending without a new node | Pod events, PVCs, affinity, taints, class/pool conditions, quotas/IP/capacity and API errors | Always capacity shortage |
| A node disappeared | Deletion/interruption events, NodeClaims, managed logs, EC2/CloudTrail and recovery | Always consolidation or OOM |
| Response latency | Error/latency distributions, queues, traces/logs and CPU/RAM/network/storage | One trace/temperature proves cause |

CloudTrail shows recorded API actions, not every scheduling failure's definitive cause. Kubernetes conditions/events matter when no EC2 call was made. Do not imply missing historical telemetry has been recovered.

## Part4: IaC/GitOps (10min)

### 4-1. IaC Boundaries (5min)

Use the [infrastructure guide](../ops/01-infrastructure-setup.md) to distinguish shared backend configuration from network/cluster/platform deployment layers. Separate files/states do not guarantee network changes cannot affect clusters. Verify provider/module Auto Mode settings, locking, output dependencies and apply order.

### 4-2. GitOps Operations (5min)

Compare permissions, generators and sync policies in [ArgoCD Applications](../gitops/argocd/02-applications.md) and [ApplicationSets](../gitops/argocd/04-applicationsets.md). Auto-sync/self-heal/prune are not automatically safe rollouts. Review NodePool/NodeClass deletion impact and drift ownership, and verify Progressive Sync enablement/version support.

## Assessment and Lab Preparation

- [Getting started and boundaries](../quizzes/eks-auto-mode/01-getting-started-quiz.md)
- [NodePool/NodeClass](../quizzes/eks-auto-mode/02-nodepool-configuration-quiz.md)
- [Scaling](../quizzes/eks-auto-mode/03-scaling-behavior-quiz.md)
- [Spot](../quizzes/eks-auto-mode/04-spot-strategies-quiz.md)
- [Cost](../quizzes/eks-auto-mode/06-cost-management-quiz.md)
- [Workloads](../quizzes/eks-auto-mode/08-workload-optimization-quiz.md)
- [Node lifecycle](../quizzes/eks-auto-mode/07-node-lifecycle-quiz.md)
- [Operations](../quizzes/eks-auto-mode/05-operations-quiz.md)

Prepare account/cluster checks, supported APIs/images, telemetry and cleanup procedures, and state exactly what was executed. Refer to [migration](../eks-auto-mode/09-migration-guide.md) and [Spot production experiments](../ops/17-spot-production-experiments.md); fault injection is a separate bounded lab requiring a dedicated environment, stop conditions and recovery evidence.

## Review Evidence

Checks cover the120minute schedule, links, NodePool structural schema and node-alert rules. No cluster creation, node replacement, FIS experiment, savings measurement or observability-backend deployment was performed.

- [Auto Mode NodePool defaults](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Managed instance maximum lifetime](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Auto Mode responsibilities and OS](https://docs.aws.amazon.com/eks/latest/userguide/automode.html)
- [Managed component logs](https://docs.aws.amazon.com/eks/latest/userguide/auto-managed-component-logs.html)
- [Grafana Tempo configuration](https://grafana.com/docs/grafana/latest/datasources/tempo/configure-tempo-data-source/)
- [Loki label cardinality](https://grafana.com/docs/loki/latest/get-started/labels/)
