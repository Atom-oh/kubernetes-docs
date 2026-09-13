# Cost Management and Optimization

> **Supported Versions**: EKS Auto Mode GA; examples reviewed for EKS 1.36
> **Last Updated**: September 12, 2026

Cost optimization needs billing evidence for comparable useful work. A snapshot of node counts, low CPU usage or an advertised discount is not a measured saving. These examples were checked locally against source/schema/CLI contracts; no purchase, cloud deployment or live billing query was performed.

## What the Bill Includes

Account for the EKS cluster fee, EC2 usage, **additional Auto Mode charges**, EBS, load balancers, NAT/data transfer, observability and other workload services. Auto Mode compute charges are per second with a one-minute minimum and are independent of the EC2 purchase option. EC2 Savings Plans/RI discounts do not discount the separate Auto Mode charge.

### July 2026 GPU fee reduction

AWS's July announcement confirms that, effective July 1, G-series **Auto Mode management fees** fell 35%, and P-series/Trainium fees fell 60%, automatically in supported Regions. This is a reduction in that fee component, not the same percentage off the total GPU bill. The announcement also describes parallel image pulling/unpacking on GPU instances with local NVMe and accelerator-aware repair; it does not establish a measured startup or application recovery time for this example.

## Cost-Oriented Placement

First use the account/API-endpoint guard and private `WORK_DIR` from [Operations](./05-operations.md). The examples assume a reviewed `default` NodeClass and available compatible capacity. Review costs before deploying them.

The complete lab workload below fixes the missing selector/image in the old English example. It uses the non-root nginx image verified in the operations chapter, a Restricted namespace and a pool selector/toleration. The illustrative requests are **not measured usage**. Confirm multi-architecture images, libraries and application behavior before permitting ARM.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cost-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: cost-optimized
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
        - r
        - i
        - d
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      taints:
      - key: cost-lab
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        cost-lab: 'true'
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: 10%
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cost-efficient-app
  namespace: cost-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: cost-efficient
  template:
    metadata:
      labels:
        app: cost-efficient
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.4@sha256:cb92301e719d6639028de775fe8b28e15f58343aca5e5372001311958aafb300
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: cost-optimized
      tolerations:
      - key: cost-lab
        operator: Equal
        value: 'true'
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: karpenter.sh/capacity-type
                operator: In
                values:
                - spot
```

Allowing both Spot and On-Demand permits capacity selection; a soft Pod preference does not guarantee a percentage or immediate fallback. Category diversity helps only where the region, NodeClass, workload and actual inventory allow it. A separate tier pool can express interruption, GPU or architecture constraints, but unnecessary fragmentation can reduce packing efficiency.

`WhenEmptyOrUnderutilized` evaluates whether Pods can be rescheduled more cheaply using requests and constraints; it is not a CPU-utilization threshold. `consolidateAfter` is a debounce, not a deletion deadline. PDBs, affinity and budgets can prevent consolidation. Pool CPU/memory limits bound requested infrastructure growth; eventual consistency can temporarily overshoot during rapid provisioning. They are not a currency budget or a hard account-wide spending cap.

## Separate Billing from Operational Metrics

An instantaneous node gauge is not node-hours, and node-hours are not dollars without instance/rate/time data. Auto Mode does not automatically publish the old examples' invented `Karpenter` CloudWatch cost metrics. Use actual billing exports/Cost Explorer for money and configured collectors for capacity and performance.

### CloudWatch billing overview

After enabling billing alerts/metrics, `AWS/Billing` estimated charges are published in **us-east-1** for worldwide account charges. They are cumulative estimated charges for the current month, not daily EC2 spend, an EKS-cluster total or a forecast. A payer account has its own linked-account scope. This local dashboard definition uses the required currency dimension and region:

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "title": "Account estimated charges, month to date (USD)",
        "region": "us-east-1",
        "view": "timeSeries",
        "metrics": [
          [
            "AWS/Billing",
            "EstimatedCharges",
            "Currency",
            "USD"
          ]
        ],
        "period": 21600,
        "stat": "Maximum"
      }
    }
  ]
}
```

Use Cost Explorer/CUR or Data Exports for service/cluster allocation and daily changes. AWS Budgets and Cost Anomaly Detection can notify on reviewed monetary thresholds; they are not hard spending caps. A node-count alarm is a separate capacity guard and needs a real configured publisher, dimensions and notification target. The old alarm referenced both an invented metric and an undefined SNS resource.

### Kubecost

The reviewed stable chart/app is **3.2.4**, chart name `kubecost` in the new repository below; a newer release candidate is not used as a blind upgrade target. Version 3 uses its FinOps agent and ClickHouse-based architecture. Do not reuse the old `cost-analyzer` repository, `kubecostToken` command-line example or assumptions from a version-2 Prometheus deployment.

Prepare a version-specific values file for licensing, cluster identity, billing integration, scoped workload IAM, authentication, retention and storage. An Auto Mode EBS StorageClass uses `ebs.csi.eks.amazonaws.com`; choose it explicitly where needed and review encryption. This chart has persistent-data retention/keep annotations, so uninstalling is not proof all chargeable storage was deleted. Keep access private and review collector/telemetry behavior. Render locally before any installation:

```bash
: "${KUBECOST_VALUES:?Set the reviewed Kubecost 3.2.4 values file}"
test -f "$KUBECOST_VALUES"
helm repo add kubecost https://kubecost.github.io/kubecost/
helm repo update kubecost
helm show chart kubecost/kubecost --version 3.2.4
helm template cost-review kubecost/kubecost --version 3.2.4 \
  --namespace kubecost --values "$KUBECOST_VALUES" \
  > "$WORK_DIR/kubecost-rendered.yaml"
```

The rendering command does not install anything. Pod/namespace/idle-cost allocation requires the agent and matching data sources; actual billing reconciliation needs the AWS integration. Namespace labels alone do not create billing data. Reconcile idle/shared costs, discounts and unallocated costs rather than summing incompatible estimates.

## Measuring Spot Savings

This structured snapshot handles zero nodes, missing labels and mixed instance types. It counts **Auto Mode Node objects**, not billed hours or spend:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[] | {
  capacity: (.metadata.labels["karpenter.sh/capacity-type"] // "unknown"),
  instanceType: (.metadata.labels["node.kubernetes.io/instance-type"] // "unknown")
}] as $nodes |
{
  totalNodeObjects: ($nodes | length),
  byCapacityAndType: ($nodes | group_by([.capacity,.instanceType]) |
    map({capacity: .[0].capacity, instanceType: .[0].instanceType, count:length})),
  spotNodePercent: (if ($nodes|length) == 0 then null
    else 100 * ([$nodes[]|select(.capacity=="spot")]|length) / ($nodes|length) end)
}'
```

For a cost comparison, use the same period, region/AZ, instance/OS/tenancy, currency and useful-work requirement. Historical Spot rates vary with AZ and time. A Pricing API result selected only by instance type can be for the wrong region/OS/tenancy/product; the former script also suppressed API errors. A current price sample cannot reconstruct last month's actual bill.

```text
reference_total = cost of the reviewed On-Demand counterfactual for the same useful work
actual_total = actual compute + Auto Mode fees + other allocated costs
               + recovery costs not already included in those billed components
savings_amount = reference_total - actual_total
savings_percent = 100 * savings_amount / reference_total  (reference_total > 0)
```

Include interrupted/retried work and idle/unutilized commitments once, and avoid counting recovery compute twice. The reference also needs its corresponding Auto Mode/other fees. A 70% assumed Spot discount or current Spot-node percentage cannot be labeled actual monthly savings. Retain separate evidence for interruption events; a guessed termination-counter reason does not measure every interruption.

### Cost Explorer, read-only

Activate the AWS-generated **`aws:eks:cluster-name`** tag first; `eks:cluster-name` is not the documented billing key. It attributes participating EC2 instance costs, **not the control-plane fee or every cluster-related service**. Review the account/payer scope and tag coverage. Cost Explorer API requests can themselves incur charges.

Choose an explicit inclusive start/exclusive end. This request uses monetary `AmortizedCost`; it does not add incompatible `UsageQuantity` units or treat node ratios as dollars.

```bash
: "${COST_START:?Set YYYY-MM-DD inclusive start}"
: "${COST_END:?Set YYYY-MM-DD exclusive end, no later than today UTC}"
export COST_START COST_END CLUSTER_NAME
python3 - <<'PY'
import json, os
from datetime import date, datetime, timezone
from pathlib import Path
start, end = (date.fromisoformat(os.environ[key]) for key in ("COST_START", "COST_END"))
if not start < end <= datetime.now(timezone.utc).date():
    raise SystemExit("Require start < end <= today UTC")
request = {
    "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
    "Granularity": "DAILY",
    "Metrics": ["AmortizedCost"],
    "Filter": {"Tags": {"Key": "aws:eks:cluster-name", "Values": [os.environ["CLUSTER_NAME"]]}},
    "GroupBy": [{"Type": "DIMENSION", "Key": "INSTANCE_TYPE"},
                {"Type": "DIMENSION", "Key": "PURCHASE_TYPE"}]
}
(Path(os.environ["WORK_DIR"]) / "ce-request.json").write_text(json.dumps(request, indent=2) + "\n")
PY
```

```bash
check_account
aws ce get-cost-and-usage --region us-east-1 \
  --cli-input-json "file://$WORK_DIR/ce-request.json" \
  --output json > "$WORK_DIR/ce-result.json"
jq '[.ResultsByTime[] | {period:.TimePeriod,estimated:.Estimated,groups:.Groups}]' \
  "$WORK_DIR/ce-result.json"
```

Preserve the `Estimated` flags and account for refunds, credits, discount allocation and incomplete data. A tag-filtered result may exclude unallocated fees or unused commitments; reconcile it against the complete billing dataset before claiming a total or a saving.

## Resource Right-Sizing

Use the pinned [VPA 1.7.1 installation guide](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/installation.md). Its documented compatibility includes Kubernetes 1.28+, with higher requirements for specific in-place features. The old `releases/latest/download/...` URLs were not a valid VPA installation procedure. Review CRDs, RBAC, metrics-server and component/certificate setup before applying cluster-wide installation scripts; `Off` still needs a working recommender.

This resource targets the actual lab Deployment in the same namespace:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cost-app-vpa
  namespace: cost-lab
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cost-efficient-app
  updatePolicy:
    updateMode: 'Off'
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: '4'
        memory: 8Gi
```

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get vpa cost-app-vpa -o json |
  jq '{conditions:.status.conditions,recommendations:.status.recommendation.containerRecommendations}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n cost-lab \
  get deployment cost-efficient-app -o json |
  jq '[.spec.template.spec.containers[] | {name,resources}]'
```

`Off` provides recommendations without applying them. Check all containers, recommendation conditions/history, workload seasonality, startup peaks, latency, CPU throttling and memory/OOM behavior. A bound in `resourcePolicy` is not evidence that its recommendation fits the existing limits. VPA is not a performance guarantee; this reviewed release also documents limitations with Pod-level resource stanzas.

### Preserve Kubernetes quantity units

`1` CPU means one core, while `1m` means one millicore. `1Gi` is 1024Mi; deleting suffixes does not convert either unit. Snapshot each container's raw requests/limits and usage instead of using the old `sed`/`awk` totals:

```bash
: "${WORKLOAD_NAMESPACE:?Select a namespace}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  get pods -o json |
  jq '[.items[] | {pod:.metadata.name,uid:.metadata.uid,
    podResources:.spec.resources,overhead:.spec.overhead,
    containers:[.spec.containers[]|{name,resources}],
    initContainers:[.spec.initContainers[]?|{name,restartPolicy,resources}]}]' \
  > "$WORK_DIR/pod-requests.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s -n "$WORKLOAD_NAMESPACE" \
  top pods --containers > "$WORK_DIR/container-usage.txt"
```

The metrics query must succeed; missing data is not zero utilization. These two snapshots are not simultaneous, and container usage is not the scheduler's complete Pod request calculation: init/restartable-init containers, Pod-level resources and overhead also matter.

| Observation | Review action |
|-------------|---------------|
| Request appears above 2× representative usage | Investigate peaks and SLO headroom before reducing it; no automatic 20–50% saving |
| Request is within 2× usage | Not proof it is optimal |
| Usage exceeds request | Evaluate scheduling/headroom; memory **limits**, not simply requests, are relevant to OOM enforcement |
| Limit greatly exceeds request | Evaluate burst/throttling/OOM policy; lowering only the limit does not ordinarily improve request-based packing |

### Optional Prometheus review candidates

The following informational rules assume **one cluster**, kube-state-metrics with normalized CPU-core/memory-byte units and container-level cAdvisor usage carrying namespace/Pod/container labels. The CPU query requires the aggregate `cpu="total"` series; verify your collector's labels. They deduplicate collector replicas, exclude infrastructure cgroups and require a positive request denominator. Use real cluster labels in every grouping/join for multiple clusters. Missing series do not become zero. Review stale-series/container-recreation effects and representative history.

The 30% utilization threshold sustained for one hour is an illustrative review trigger, not an automatic recommendation to reduce requests or a measured saving. Install Prometheus Operator and match its namespace/rule selectors before using this resource:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cost-review-candidates
  namespace: monitoring
spec:
  groups:
  - name: cost-review-candidates
    rules:
    - alert: LowCpuRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])) and on (namespace,pod,container)\
        \ max by (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        cpu\",unit=\"core\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\n\
        ) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}))\
        \ > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"cpu\",unit=\"core\"}) unless\
        \ on (namespace,pod,container) max by (namespace,pod,container) (rate(container_cpu_usage_seconds_total{cpu=\"\
        total\",container!=\"\",container!=\"POD\",image!=\"\"}[5m]))\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
    - alert: LowMemoryRequestUtilization
      expr: "((\n  sum by (namespace,pod) (max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"}) and on (namespace,pod,container) max by\
        \ (namespace,pod,container) (kube_pod_container_resource_requests{resource=\"\
        memory\",unit=\"byte\"}))\n  / sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }))\n) and on (namespace,pod) (sum by (namespace,pod) (max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        })) > 0)\nunless on (namespace,pod) count by (namespace,pod) (\n  max by (namespace,pod,container)\
        \ (kube_pod_container_resource_requests{resource=\"memory\",unit=\"byte\"\
        }) unless on (namespace,pod,container) max by (namespace,pod,container) (container_memory_working_set_bytes{container!=\"\
        \",container!=\"POD\",image!=\"\"})\n)) < 0.3"
      for: 1h
      labels:
        severity: info
      annotations:
        summary: Review request sizing; do not automatically reduce it
```

## Savings Plans and Reserved Instances

| Option | Eligible usage / scope | Important limitation |
|--------|------------------------|----------------------|
| Compute Savings Plans | Eligible EC2 usage across families, sizes, regions, OS and tenancy; also Fargate/Lambda | Up to 66% is an advertised maximum, not an expected discount |
| EC2 Instance Savings Plans | Chosen instance family in one region; size/OS/tenancy flexibility within that scope | Up to 72%; not a commitment to one exact instance size |
| EC2 RIs | Matching usage; regional size flexibility/exchange rules depend on offering | Existing matching commitments can still benefit Auto Mode |
| Spot | Separate Spot pricing | No Savings Plans stacking |

Eligible Graviton and GPU EC2 usage does not require a special “ARM Savings Plan” or blanket GPU exclusion. SageMaker AI Savings Plans cover SageMaker usage, not an EC2 GPU node merely because it runs ML. Savings Plans do not reserve physical capacity; evaluate capacity reservations separately. The separate Auto Mode fee remains outside these EC2 discounts.

Size commitments in **USD/hour at the applicable Savings Plans rates** from sustained eligible, uncovered hourly usage. If the baseline already excludes Spot, do not multiply it by `(1 - Spot%)` again. Account for existing RI/SP coverage, future right-sizing/architecture changes, sharing settings, seasonality and unused commitment. A lower EC2 rate or node count does not by itself determine a safe purchase.

```bash
check_account
aws ce get-savings-plans-purchase-recommendation --region us-east-1 \
  --savings-plans-type COMPUTE_SP --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT --lookback-period-in-days THIRTY_DAYS \
  --output json > "$WORK_DIR/savings-plan-recommendation.json"
```

This retrieves a recommendation, not a purchase. The 30-day lookback is a selectable API option; compare it with longer representative history before deciding.

The original 60–70%/70% Compute coverage, 30–40% EC2 Instance coverage, 50% On-Demand coverage and Spot 40–60% / covered 30–40% / uncovered 10–20% diagram are **unverified planning examples**, not additive universal targets. A workload is running on Spot or On-Demand capacity; Savings Plans describe billing coverage of eligible usage, not a third type of node.

## Cost Attribution

Use valid NodeClass identity/network selectors and approved tagging permissions. Custom NodeClasses need their node-role access entry. Tags describe resources; they do not create network isolation or automatically cover every dependent service.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: tagged-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  tags:
    Environment: lab
    Team: platform
    Project: web-services
    CostCenter: CC-12345
    Application: cost-lab
    ManagedBy: eks-auto-mode
```

Reference `tagged-nodeclass` deliberately from the intended pool to use this example. `amiFamily: AL2023` is not an Auto Mode NodeClass field. Verify tags on actual resources and activate the relevant keys in Billing. User-defined keys can take up to 24 hours to appear for activation and a further up to 24 hours to activate; reporting freshness is separate. Do not promise all data exactly 24 hours later.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    cost-center: team-a
    environment: production
```

Namespace labels can support Kubernetes allocation tooling; they do not automatically propagate to AWS cost-allocation tags. Tag-based EC2 attribution also does not replace shared/control-plane/storage/network cost allocation.

## Optimization Checklist and Prior Numerical Examples

Keep compatible instance diversity, workload-aware Spot use, measured request sizing, feasible consolidation, billing integration and commitment review as separate work items. Measure total useful-work cost and availability before/after a change.

The previous estimates below have no verified benchmark/billing provenance. They are preserved for context, are not guaranteed, and must not be added or multiplied into a claimed total saving:

| Prior topic | Original example ranges |
|-------------|-------------------------|
| Spot | 60–70%, 60–90%, 70–90% |
| ARM/Graviton | 20% |
| Request sizing / VPA | 10–30%, 15–30%, 20–40%, 20–50% |
| Consolidation | 10–20%, 10–30% |
| Savings Plans | 20–30%, 20–40% |
| Multi-AZ / scheduling | 5–10% / 10–20% |

Reducing AZ resilience is not a generic cost optimization. Include data transfer, failure recovery, storage retention and workload objectives in any placement/scheduling experiment.

## References

- [EKS pricing and Auto Mode charges](https://aws.amazon.com/eks/pricing/)
- [July 2026 GPU management-fee reduction](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-eks-auto-mode-gpu-price/)
- [Auto Mode cost controls](https://docs.aws.amazon.com/eks/latest/userguide/auto-cost-control.html)
- [NodePool resource limits and disruption](https://karpenter.sh/v1.14/concepts/nodepools/)
- [Savings Plans types](https://docs.aws.amazon.com/savingsplans/latest/userguide/plan-types.html)
- [Savings Plans versus RIs](https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-ris.html)
- [EKS billing tags](https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html)
- [Activating cost allocation tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html)
- [CloudWatch estimated billing charges](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html)
- [Kubecost 3.2.4 chart](https://kubecost.github.io/kubecost/kubecost-3.2.4.tgz)
- [VPA 1.7.1 installation](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/installation.md)
- [VPA known limitations](https://github.com/kubernetes/autoscaler/blob/vertical-pod-autoscaler-1.7.1/vertical-pod-autoscaler/docs/known-limitations.md)
- [Kubernetes resource units and scheduling](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Auto Mode NodeClass and tags](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)

< [Previous: Operations](./05-operations.md) | [Table of Contents](./README.md) | [Next: Node Lifecycle](./07-node-lifecycle.md) >
