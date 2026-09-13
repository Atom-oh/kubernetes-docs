# EKS Resiliency and High Availability

> **Example API baseline**: Kubernetes 1.36; choose currently supported EKS and compatible controller releases
> **Last Updated**: September 12, 2026

These are configuration patterns, not a tested production platform. Use an owned test scope and replace application images, health paths, IAM and infrastructure references with reviewed inputs. No clusters, failovers or chaos experiments were executed in this audit.

RTO is an acceptable recovery-time target, including detection and restoration; RPO is the acceptable recovery-point/data-loss window. Multi-AZ, replication and a control-plane SLA do not automatically guarantee zero data loss or a particular workload recovery time.

## Resiliency Overview

Resiliency is **the ability to minimize impact during failures while recovering to a normal state or maintaining service**. It goes beyond simple high availability (HA) and represents a design philosophy that anticipates and prepares for failures.

### Resiliency Maturity Model

| Level | Scope | Example controls | Earlier illustrative recovery timing, not measurements |
| --- | --- | --- | --- |
| 1. Basic | Pod/workload | Probes, resources, eviction budget, shutdown | Seconds–minutes |
| 2. Multi-AZ | AZ loss | Placement, surviving capacity, traffic/data recovery | Seconds–minutes |
| 3. Cell | Service partition | Routing and bounded dependencies/capacity | Seconds for partial impact–minutes |
| 4. Multi-Region | Regional loss | Regional traffic/data failover and operations | Near-zero targets through minutes/hours, depending on design |

The earlier language editions used different illustrative timing ranges. This model organizes design choices; it is not a certification or a guarantee that a higher level recovers faster. Define and measure targets for each user journey and its dependencies.

Regional EKS manages its control plane across three AZs. The current endpoint SLA is 99.95% monthly uptime for Standard Control Plane (five-minute measurement intervals), and 99.99% for Provisioned Control Plane (one-minute intervals). These are service-credit commitments with conditions, not application SLO/RTO/RPO guarantees. [AWS EKS SLA](https://aws.amazon.com/eks/sla/)


> Not all services require Level 4. Choose the appropriate level based on SLA requirements, regulations, and budget.

***

## Level 1: Basic Resiliency (Pod Level)

### Liveness/Readiness/Startup Probes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

The image above is an explicit application placeholder, not a published artifact. Replace it with a verified digest and implement the health contract before deployment. Startup gates liveness/readiness; liveness should not fail merely because a downstream service is slow. Resource/probe values are illustrative. Jobs and init containers do not universally need these same probes.

### PodDisruptionBudget (PDB)

PDB constrains supported voluntary evictions for matching Pods. It does not preserve a Pod count through AZ/hardware failure, direct Pod deletion, or a Deployment’s own rolling update/scale-down. Controller strategy, placement and spare capacity are separate controls.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web-app
```

```bash
# Check PDB status
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb web-app-pdb
# Inspect the actual workload health and ongoing disruptions.
# Illustrative only: three Ready replicas and no ongoing/unhealthy deductions permit one eviction.
```

### Graceful Shutdown

```yaml
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    lifecycle:
      preStop:
        sleep:
          seconds: 5
```

This is a Pod-spec fragment for the owned application. Native preStop sleep is GA from Kubernetes 1.34 and is valid in the 1.36 baseline. A five-second sleep is only a delay; it does not guarantee endpoint/load-balancer propagation. The grace period includes the hook, and EndpointSlice termination updates run concurrently with node shutdown. Terminating endpoints can remain listed with ready=false and a serving condition for draining.

The runtime then sends the configured stop signal (normally SIGTERM; image/runtime settings can differ). The application must handle it and finish/reject work before forced termination. Do not manually kill PID 1 in preStop and assume a strict endpoint-removal sequence. Test actual long-lived connections, deregistration and flushing.

***

## Level 2: Multi-AZ Strategy

### Pod Topology Spread Constraints

Topology spread influences placement; it does not create healthy capacity or automatically move existing Pods after a failure.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      topologySpreadConstraints:
      # Hard constraint for the documented N-1 example; review eligible domains and capacity.
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
        minDomains: 2
      # Soft constraint: Even distribution across nodes
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-app
      containers:
      - name: app
        image: web-app:1.0
```

| Parameter           | Description                                              |
| ------------------- | -------------------------------------------------------- |
| `maxSkew` | With DoNotSchedule, difference between the candidate domain count and the global minimum |
| `topologyKey`       | Distribution basis (zone, hostname, etc.)                |
| `whenUnsatisfiable` | `DoNotSchedule` (Hard) or `ScheduleAnyway` (Soft)        |
| `minDomains` | If fewer eligible domains remain, the global minimum becomes zero |

For example, if two eligible zones remain with two matching Pods each, minDomains=3 gives a global minimum of zero and can block replacement Pods at maxSkew=1. minDomains=2 permits the spread calculation for another Pod if other constraints/capacity allow it. It does not require exactly two or three occupied AZs. Gate initial three-AZ placement and surviving-AZ headroom separately. ScheduleAnyway is a preference; other scheduler constraints still apply.

### Karpenter Multi-AZ NodePool

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: topology.kubernetes.io/zone
        operator: In
        values: ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand", "spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ["m6i.xlarge", "m6i.2xlarge", "m7i.xlarge", "m7i.2xlarge"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
    budgets:
    - nodes: "20%"    # Applicable voluntary budget, rounded up and reduced by deleting/NotReady nodes
    - nodes: "0"
      schedule: "0 0 * * MON-FRI"   # UTC 00:00–09:00 = Korea/Japan 09:00–18:00; not all failure types
      duration: 9h
```

Karpenter requirements permit zones; they do not evenly pre-provision nodes or reserve failure headroom. Use an EKS-compatible version; the schema baseline is the maintained 1.14.1 release, not an unconditional historic 1.0+ floor. The referenced EC2NodeClass, AMIs, role, subnets and capacity must already be reviewed.

Percentage budgets use ceil(total × percentage), less deleting and NotReady nodes; the most restrictive applicable budget wins. They do not rate-limit every interruption, expiration, repair or manual deletion. Schedules are UTC; the example is one weekday 09:00–18:00 Korea/Japan block. A zero budget does not prevent all failures.

Separate Spot/On-Demand pools can use weights 100/50, but weights are provisioning preferences, not a guarantee that the lower-weight pool is used only when Spot is unavailable. Existing capacity, constraints and batching also matter. NodePool limits cap provisioning rather than pre-scaling it.

### Same-Zone Service Preference

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

PreferSameZone/PreferSameNode are GA from Kubernetes 1.35 and valid for this 1.36 baseline; PreferClose is the older alias for PreferSameZone. This is a preference, not strict locality or a latency/cost guarantee. Check actual proxy/EndpointSlice behavior and Local traffic policies. The older topology-mode=Auto annotation uses a different hint-allocation heuristic; topology-aware-hints is legacy guidance.

Sources: [PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/), [Pod termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/), [Service traffic distribution](https://kubernetes.io/docs/concepts/services-networking/service/#traffic-distribution), [Karpenter disruption](https://karpenter.sh/docs/concepts/disruption/).

### ARC Zonal Shift

Manual zonal shift and automatic zonal autoshift are separate operations. EKS integration cordons affected-zone nodes and removes their endpoints from EndpointSlices; it does not evict Pods or terminate those nodes. Auto Mode avoids new nodes and suspends relevant voluntary disruption in the affected AZ; managed node groups suspend AZ rebalancing and avoid new launches there. Current Karpenter integration needs its documented version/settings/IAM setup. A load-balancer shift is a separate resource operation.

First verify the account, exact managed resource, enabled integration, existing practice configuration and alarm behavior. Test surviving-zone application, DNS, data and node capacity. Zonal shift is not absolute network isolation: EKS has a fail-safe when all service endpoints are in the impaired zone. It cannot move an existing zonal EBS volume. Pure Auto Mode uses node-system CoreDNS; mixed/non-Auto nodes still need the Deployment and its capacity.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the resource region}"
: "${ARC_RESOURCE_ARN:?Set the exact owned EKS cluster or eligible load-balancer ARN}"
aws sts get-caller-identity
aws arc-zonal-shift get-managed-resource \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN"
```
The next blocks are separate operational steps, not a single setup script. Practice configuration starts recurring traffic changes; inspect an existing configuration instead of recreating it. An outcome alarm identifier is an ARN string, not an alarmName/region object. Enable autoshift separately when ready.

```bash
# MUTATION: authorizes recurring weekly traffic-shifting practice runs.
: "${OUTCOME_ALARM_ARN:?Set the reviewed CloudWatch alarm ARN in the resource region}"
aws arc-zonal-shift create-practice-run-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --outcome-alarms "alarmIdentifier=$OUTCOME_ALARM_ARN,type=CLOUDWATCH"
```
```bash
# MUTATION: enable automatic shifts only after the readiness review.
aws arc-zonal-shift update-zonal-autoshift-configuration \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --zonal-autoshift-status ENABLED
```
```bash
# MUTATION: a separate, manually initiated one-hour shift.
set -euo pipefail
: "${AWAY_FROM_AZ:?Set an AZ of this resource}"
SHIFT_ID=$(aws arc-zonal-shift start-zonal-shift \
  --region "$AWS_REGION" --resource-identifier "$ARC_RESOURCE_ARN" \
  --away-from "$AWAY_FROM_AZ" --expires-in 1h \
  --comment "Owned resilience exercise" --query zonalShiftId --output text)
test -n "$SHIFT_ID" && test "$SHIFT_ID" != None
printf '%s\n' "$SHIFT_ID" > owned-zonal-shift-id.txt
```
```bash
# MUTATION: cancel only the recorded manual shift after checking its ownership.
: "${SHIFT_ID:?Use the exact ID recorded for this exercise}"
aws arc-zonal-shift cancel-zonal-shift \
  --region "$AWS_REGION" --zonal-shift-id "$SHIFT_ID"
```
[EKS ARC behavior and prerequisites](https://docs.aws.amazon.com/eks/latest/userguide/zone-shift.html) · [Auto Mode/Karpenter integration](https://aws.amazon.com/blogs/containers/arc-zonal-shift-support-for-eks-auto-mode-and-karpenter/)

### Storage Considerations

WaitForFirstConsumer delays initial provisioning/binding until scheduler placement can be considered. **EBS remains AZ-bound.** After AZ loss, a replacement Pod in another AZ cannot attach that same volume. Restore/migrate data through a reviewed backup/replication plan and test RPO/RTO.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-ebs
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: 'true'
allowVolumeExpansion: true
reclaimPolicy: Retain
```
This StorageClass uses the standard EBS CSI driver. Auto Mode uses ebs.csi.eks.amazonaws.com and its own compatible node/IAM/migration requirements. Set encrypted: "true" explicitly in either design and inspect the created EBS volume/KMS key. Auto Mode node root/data-disk encryption does not establish that every workload PVC is encrypted; the current Auto Mode StorageClass parameter default is false. Retain preserves a released volume for controlled recovery/cleanup; it is not a backup and can retain billable resources.

For cross-AZ shared filesystem access, use an existing **Regional** EFS filesystem, reachable mount targets, TCP 2049 security rules, reviewed access-point permissions and compatible CSI IAM. EFS One Zone is not the same resilience design. These IDs are placeholders; no filesystem is created here.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: resilience-efs
provisioner: efs.csi.aws.com
parameters:
  provisioningMode: efs-ap
  fileSystemId: fs-0123456789abcdef0
  directoryPerms: '700'
  basePath: /resilience-demo
reclaimPolicy: Retain
mountOptions:
- tls
```
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: efs-claim
  namespace: resilience-demo
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: resilience-efs
  resources:
    requests:
      storage: 5Gi
```
The 5Gi PVC request is not an enforced EFS storage quota. TLS mount encryption and at-rest filesystem encryption are separate settings. Retain also requires a documented access-point/data cleanup process.

[EKS EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html) · [Auto Mode StorageClass parameters](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html) · [EFS CSI](https://github.com/kubernetes-sigs/aws-efs-csi-driver)

### Istio Locality-Aware Routing

For the Istio sidecar-mode example, Istio reads locality from the node running the Pod unless its documented locality override is set; ordinary Pod zone labels do not automatically define this. Verify actual proxy endpoints/localities and reachable healthy capacity. Outlier detection is required for the documented locality failover behavior.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: web-app-locality
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
    loadBalancer:
      simple: ROUND_ROBIN
      localityLbSetting:
        enabled: true
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```
As an **alternative weighted-distribution configuration**, replace the loadBalancer localityLbSetting with the following fragment. It includes all three source zones; 80/10/10 are configured weights, not measured locality or a guarantee of failover capacity. Do not combine a distribute rule with an incompatible failover policy.

```yaml
localityLbSetting:
  enabled: true
  distribute:
  - from: ap-northeast-2/ap-northeast-2a/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 80
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2b/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 80
      ap-northeast-2/ap-northeast-2c/*: 10
  - from: ap-northeast-2/ap-northeast-2c/*
    to:
      ap-northeast-2/ap-northeast-2a/*: 10
      ap-northeast-2/ap-northeast-2b/*: 10
      ap-northeast-2/ap-northeast-2c/*: 80
```
The original 80%+ local traffic, 60–80% cost reduction and <1ms same-AZ latency figures are retained only as unverified illustrations. Their measurement sources are unavailable; health, connection reuse, endpoint mix, request bytes and pricing change the result.

[Locality failover](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/failover/) · [Weighted distribution](https://istio.io/latest/docs/tasks/traffic-management/locality-load-balancing/distribute/)

---

## Level 3: Cell-Based Architecture

### Cell Concept

A Cell is **a self-contained service unit with its own data store, cache, and queue**. It aims to bound failure impact when routing, capacity and dependencies enforce the cell boundary.

### Cell Partitioning Strategies

| Strategy       | Description                       | Suitable For                     |
| -------------- | --------------------------------- | -------------------------------- |
| Customer-based | Assign Cell by customer ID hash   | SaaS multi-tenant                |
| Region-based   | Partition by geographic location  | Global services                  |
| Capacity-based | New Cell when capacity is reached | Even load distribution           |
| Tier-based     | Cell by service tier              | Premium/Standard differentiation |

### Namespace-based Cell Implementation

Namespaces, quotas and NetworkPolicy provide logical boundaries, not independent failure domains. Shared nodes, the control plane, CNI, DNS, routers and data services remain dependencies. Verify that the network plugin enforces policy; allowed traffic is the union of all applicable policies. The router namespace/workload below must exist with the exact labels.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-1
  labels:
    cell: '1'
    customer-range: a-f
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-1-quota
  namespace: cell-1
spec:
  hard:
    requests.cpu: '20'
    requests.memory: 40Gi
    limits.cpu: '40'
    limits.memory: 80Gi
    pods: '100'
    services: '20'
    persistentvolumeclaims: '50'
```
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: cell-1-limits
  namespace: cell-1
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
```
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: cell-1-isolation
  namespace: cell-1
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: cell-router
      podSelector:
        matchLabels:
          app: cell-router
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector: {}
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
DNS permits TCP and UDP to matching CoreDNS Pods in kube-system. Node-local/Auto Mode system DNS follows a different path and needs mode-specific verification. This policy intentionally does not allow arbitrary external traffic: add reviewed endpoint or egress-gateway rules for required services. Excluding only 10.0.0.0/8 from 0.0.0.0/0 does not isolate all private networks or cells.

[NetworkPolicy semantics](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

### Shuffle Sharding

Stable assignment to a subset of cells can reduce overlap between customers, when routing, admission limits and data availability implement the design.

```
With 2 Cell combinations from a pool of 8 Cells:
- Customer A → Cell 1, Cell 5
- Customer B → Cell 2, Cell 7
- Customer C → Cell 1, Cell 3

When Cell 1 fails:
- Customer A → Can use Cell 5 if failover routing/data/capacity are ready
- Customer B → Not affected ✅
- Customer C → Can use Cell 3 if failover routing/data/capacity are ready
```

C(8,2)=28. Independent uniform assignment gives an exact-pair collision probability of 1/28 (about 3.6%). A fixed failed cell touches an expected 2/8=25% of assignments, not a maximum of 25% of customers or load. A ConfigMap or hash alone implements neither failover nor data replication.

***

## Level 4: Multi-Cluster / Multi-Region

Choose a pattern per user journey and its data consistency requirements. A second cluster or region alone does not guarantee a near-zero RTO/RPO. The original timing/cost values below are unverified design illustrations, not measured results or AWS commitments.

| Pattern | Earlier RTO illustration | Earlier RPO illustration | Earlier cost illustration | Design condition |
| --- | --- | --- | --- | --- |
| Active-Active | ~0 target | ~0 target | 2x+ | Routing, consistency, conflict handling and capacity |
| Active-Passive | Minutes–hours | Minutes | 1.5x | Standby readiness, replication lag and promotion |
| Regional Isolation | Not specified | Not specified | 1x per region | Independent regional service; not automatic regional failover |
| Hub-Spoke | Minutes | Minutes | 1.3x | Hub is a shared dependency unless separately protected |

### Argo CD ApplicationSet

These three alternatives require an existing Argo CD/ApplicationSet controller, explicitly registered reachable clusters with the documented labels, repository credentials and a pre-created AppProject restricted to the reviewed repo/destinations/resource kinds. Replace the example repository and revision with owned inputs. Generated Applications have manual sync: review rendered targets/manifests before enabling any automated sync/prune policy. No generator provisions an EKS cluster.

#### Cluster generator

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-clusters
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - clusters:
      selector:
        matchLabels:
          resilience-example: 'true'
  template:
    metadata:
      name: web-app-{{.nameNormalized}}
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/web-app/overlays/{{.metadata.labels.region}}
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
#### Git directories × registered clusters

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-region-directories
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - git:
          repoURL: https://github.com/example/owned-gitops.git
          revision: REPLACE_WITH_REVIEWED_COMMIT
          directories:
          - path: regions/*
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
              region: '{{.path.basename}}'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.path.basename}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: '{{.path.path}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
The second matrix child matches the directory basename to a registered cluster label and uses the real server value. Region names cannot be converted into EKS API URLs. A missing/no-match label can produce no Applications; inspect the generated set, not just schema validity.

#### Cluster × application list

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: resilience-cluster-app-matrix
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions:
  - missingkey=error
  generators:
  - matrix:
      generators:
      - clusters:
          selector:
            matchLabels:
              resilience-example: 'true'
      - list:
          elements:
          - app: frontend
            port: '80'
          - app: backend
            port: '8080'
          - app: worker
            port: '9090'
  template:
    metadata:
      name: '{{.nameNormalized}}-{{.app}}'
    spec:
      project: resilience-reviewed
      source:
        repoURL: https://github.com/example/owned-gitops.git
        targetRevision: REPLACE_WITH_REVIEWED_COMMIT
        path: apps/{{.app}}
        helm:
          parameters:
          - name: cluster.name
            value: '{{.name}}'
          - name: service.port
            value: '{{.port}}'
      destination:
        server: '{{.server}}'
        namespace: resilience-demo
```
[ApplicationSet matrix parameters](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Matrix/)

### Global Accelerator

Use existing eligible ALB/NLB endpoints with tested TLS, health checks and sufficient regional capacity. The following is an optional provisioning example, not executed here. Save returned resource IDs and an owned cleanup plan; failure part-way through does not delete previously created resources. Disabling an accelerator does not eliminate its resource charges.

```bash
# MUTATIONS: creates a disabled, billable accelerator and its configuration.
set -euo pipefail
: "${GA_API_REGION:?Set the documented Global Accelerator API region}"
: "${ACCELERATOR_NAME:?Set a unique owned name}"
: "${REGION_ONE:?Set the first endpoint region}"
: "${REGION_TWO:?Set the second endpoint region}"
: "${REGION_ONE_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
: "${REGION_TWO_LB_ARN:?Set the reviewed eligible ALB/NLB ARN}"
test "$REGION_ONE" != "$REGION_TWO"
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --region "$GA_API_REGION" --name "$ACCELERATOR_NAME" \
  --ip-address-type IPV4 --no-enabled --query Accelerator.AcceleratorArn --output text)
test -n "$ACCELERATOR_ARN" && test "$ACCELERATOR_ARN" != None
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" \
  --protocol TCP --port-ranges FromPort=443,ToPort=443 \
  --query Listener.ListenerArn --output text)
test -n "$LISTENER_ARN" && test "$LISTENER_ARN" != None
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_ONE" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_ONE_LB_ARN,Weight=100"
aws globalaccelerator create-endpoint-group \
  --region "$GA_API_REGION" --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region "$REGION_TWO" --traffic-dial-percentage 100 \
  --endpoint-configurations "EndpointId=$REGION_TWO_LB_ARN,Weight=100"
```
```bash
# MUTATION: run separately after endpoint health, routing, data and rollback checks.
: "${ACCELERATOR_ARN:?Use the accelerator just reviewed}"
aws globalaccelerator update-accelerator \
  --region "$GA_API_REGION" --accelerator-arn "$ACCELERATOR_ARN" --enabled
```
A traffic dial is the percentage of traffic already directed to that regional endpoint group, for new connections; two 50% dials do not establish a global 50/50 split. The example leaves both at 100%. Existing connections are not forcibly moved by a dial change, and failover rules can ignore a zero dial. Endpoint weights and traffic dials are different controls. ALB/NLB endpoint health follows Elastic Load Balancing health checks; setting a Global Accelerator /healthz override does not configure those target-group checks.

[Traffic dial semantics](https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups-traffic-dial.html) · [Endpoint health](https://repost.aws/knowledge-center/global-accelerator-unhealthy-endpoints) · [Failover rules](https://repost.aws/knowledge-center/global-accelerator-failover-different-region)

### Istio Multi-Primary Federation

The sidecar multi-primary/multiple-network design needs a shared trusted identity model, distinct cluster/network names, reachable remote Kubernetes APIs and east-west gateways, compatible services/namespaces and data behavior. A ServiceEntry alone does not establish federation. Keep gateway access limited to the intended networks; a Layer-7 TLS-terminating load balancer is incompatible with AUTO_PASSTHROUGH.

The following IstioOperator is **istioctl installation input**, not an in-cluster operator to kubectl apply. Prepare the corresponding Tokyo configuration and the full official gateway/discovery setup. DNS capture/auto-allocation flags do not substitute for that setup.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    global:
      meshID: resilience-mesh
      multiCluster:
        clusterName: cluster-seoul
      network: network-seoul
```
```bash
# MUTATIONS: source-cluster credentials/RBAC and destination Secret may be created.
set -euo pipefail
umask 077
: "${SEOUL_CONTEXT:?Verify the owned Seoul context}"
: "${TOKYO_CONTEXT:?Verify the owned Tokyo context}"
test "$SEOUL_CONTEXT" != "$TOKYO_CONTEXT"
test ! -e tokyo-remote-secret.yaml && test ! -e seoul-remote-secret.yaml
istioctl create-remote-secret --context "$TOKYO_CONTEXT" --name cluster-tokyo > tokyo-remote-secret.yaml
istioctl create-remote-secret --context "$SEOUL_CONTEXT" --name cluster-seoul > seoul-remote-secret.yaml
# Inspect Secret metadata without printing token data; verify destination contexts first.
kubectl --context "$SEOUL_CONTEXT" -n istio-system apply -f tokyo-remote-secret.yaml
kubectl --context "$TOKYO_CONTEXT" -n istio-system apply -f seoul-remote-secret.yaml
```
The remote-secret files contain credentials: keep them private, exclude them from source control and remove the local copies according to credential-handling policy after installation. Commands above are a mutating step after the trust/network setup, not a read-only diagnostic.

Explicit routing can then use workload-region **Pod-template labels you set in each cluster**. Node topology labels are not automatically copied onto Pods. Treat x-region as routing input, not authorization. These 80/20 weights do not implement a data failover protocol.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cross-cluster-routing
  namespace: resilience-demo
spec:
  hosts:
  - web-app.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-region:
          exact: tokyo
    route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
  - route:
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: seoul
      weight: 80
    - destination:
        host: web-app.resilience-demo.svc.cluster.local
        subset: tokyo
      weight: 20
```
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: cross-cluster-subsets
  namespace: resilience-demo
spec:
  host: web-app.resilience-demo.svc.cluster.local
  subsets:
  - name: seoul
    labels:
      workload-region: ap-northeast-2
  - name: tokyo
    labels:
      workload-region: ap-northeast-1
```
For an unrelated external DNS service, a separate ServiceEntry can describe its registry entry, as below. This is an alternative external-service pattern with its own DNS/TLS/application prerequisites, not discovery of the Kubernetes service in a second cluster.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: reviewed-remote-service
  namespace: resilience-demo
spec:
  hosts:
  - remote-service.example.com
  location: MESH_EXTERNAL
  ports:
  - number: 443
    name: https
    protocol: TLS
  resolution: DNS
```
[Full Istio multi-primary prerequisites and steps](https://istio.io/latest/docs/setup/install/multicluster/multi-primary_multi-network/)

---

## Application Resilience Patterns

The preceding PDB and shutdown examples apply only to their matching owned workloads. For percentages, both minAvailable and maxUnavailable round up: 75% of three means three required Ready Pods, while 25% maxUnavailable permits one. Controller rollouts and direct deletion are separate controls.

### Circuit Breaker via Istio

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: backend-circuit-breaker
  namespace: resilience-demo
spec:
  host: backend-service.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```
These limits apply to the configured proxy/destination pool, not a cluster-wide concurrency cap. http2MaxRequests limits active HTTP requests; maxRetries limits **concurrent outstanding retries**, not per-request attempt count. minHealthPercent controls when outlier detection is active; it does not reserve that percentage of healthy capacity. Error ejection, connection limits and retries need measured tuning.

### Retry/Timeout

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: backend-retry-timeout
  namespace: resilience-demo
spec:
  hosts:
  - backend-service.resilience-demo.svc.cluster.local
  http:
  - match:
    - method:
        exact: GET
    route:
    - destination:
        host: backend-service.resilience-demo.svc.cluster.local
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
      retryRemoteLocalities: true
```
The GET-only route assumes the application really makes these requests safe to retry. Three retries are in addition to the original attempt, but the 10s total budget, 3s per-try limit, backoff and concurrency limit can prevent all attempts from running. Retries can amplify overload or duplicate side effects; writes need an explicit idempotency contract. retryRemoteLocalities permits alternatives, not guaranteed healthy remote capacity. Envoy retriable-4xx currently means **409 only**, not 408; optimistic-lock conflicts may require re-reading state instead of replaying the request.

[Istio DestinationRule](https://istio.io/latest/docs/reference/config/networking/destination-rule/) · [Envoy retry conditions](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter)

---

## Chaos Engineering

Chaos engineering tests a falsifiable steady-state hypothesis with controlled faults. Start in an owned representative test environment; production experiments require separately reviewed blast radius, authority, telemetry, stop conditions and recovery. Applying a CR can trigger a fault. The configurations here were checked offline, not executed, and do not establish production readiness.

```bash
# Read-only: verify the exact cluster/namespace and opt-in test workload.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=web-app,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pdb
```
### AWS Fault Injection Service (FIS)

Prepare the IAM experiment role/trust policy, required EKS access entry (or documented legacy mapping), namespaced Kubernetes ServiceAccount/Role/RoleBinding and action-specific EC2/network permissions from the official guide. The role and alarm ARNs below are placeholders in one example region/account: replace all of them consistently. The alarm must exist, receive meaningful data and be tested; a stop condition is not a data restore or a guarantee of zero impact.

Pod targets use clusterIdentifier/namespace/selectors; **cluster ARNs cannot be supplied as resourceArns for aws:eks:pod**. kubernetesServiceAccount is required on the action. Pod deletion uses the direct deletion path, so a PDB is not a deletion guard. COUNT(1) selects one target from the opt-in set and does not simulate an AZ outage.

#### One Pod deletion

```json
{
  "description": "Delete one selected test Pod; not an AZ outage",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "delete-one": {
      "actionId": "aws:eks:pod-delete",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
#### One Pod network latency

```json
{
  "description": "Add bounded IPv4 latency to one selected test Pod",
  "targets": {
    "test-pod": {
      "resourceType": "aws:eks:pod",
      "selectionMode": "COUNT(1)",
      "parameters": {
        "clusterIdentifier": "REPLACE_WITH_OWNED_TEST_CLUSTER",
        "namespace": "resilience-demo",
        "selectorType": "labelSelector",
        "selectorValue": "app=web-app,experiment-approved=true"
      }
    }
  },
  "actions": {
    "latency": {
      "actionId": "aws:eks:pod-network-latency",
      "parameters": {
        "kubernetesServiceAccount": "fis-test",
        "duration": "PT1M",
        "delayMilliseconds": "200",
        "jitterMilliseconds": "50",
        "sources": "10.20.0.0/24",
        "maxErrorsPercent": "0"
      },
      "targets": {
        "Pods": "test-pod"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
Replace the illustrative destination CIDR with the reviewed test dependency. This network action requires privileged/root fault injection and is not supported on Fargate or bridge networking. It affects IPv4; ALL or an IPv4 CIDR does not impair IPv6. Review current readonly-root-filesystem and container-security restrictions. Do not weaken the production workload’s security profile just to run this example. FIS uses an injector Pod and, for actions other than pod-delete, ephemeral containers; ending a process does not remove the immutable ephemeral-container record from the Pod spec.

#### One subnet network disruption

```json
{
  "description": "One owned test subnet network disruption, not a complete AZ outage",
  "targets": {
    "test-subnet": {
      "resourceType": "aws:ec2:subnet",
      "selectionMode": "COUNT(1)",
      "resourceArns": [
        "arn:aws:ec2:ap-northeast-2:123456789012:subnet/subnet-0123456789abcdef0"
      ]
    }
  },
  "actions": {
    "network": {
      "actionId": "aws:network:disrupt-connectivity",
      "parameters": {
        "duration": "PT1M",
        "scope": "all"
      },
      "targets": {
        "Subnets": "test-subnet"
      }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:ap-northeast-2:123456789012:alarm:owned-resilience-stop"
    }
  ],
  "roleArn": "arn:aws:iam::123456789012:role/owned-fis-test"
}
```
The subnet must be a dedicated owned test subnet with no unrelated workloads. This action clones its NACL, adds denies and restores the original association on completion; intra-subnet traffic still works even with scope=all. It is not full AZ power loss. Verify NACL quotas, IAM, the exact subnet and management/telemetry access before starting. Stop and recovery are asynchronous; confirm final experiment state and actual network/workload recovery.

```bash
# MUTATION: stop only the recorded experiment ID, not all account experiments.
: "${AWS_REGION:?Set the experiment region}"
: "${EXPERIMENT_ID:?Set the exact running FIS experiment ID}"
aws fis stop-experiment --region "$AWS_REGION" --id "$EXPERIMENT_ID"
```
[FIS EKS Pod prerequisites/RBAC](https://docs.aws.amazon.com/fis/latest/userguide/eks-pod-actions.html) · [Action parameters and subnet behavior](https://docs.aws.amazon.com/fis/latest/userguide/fis-actions-reference.html)

### Litmus Chaos (CNCF Incubating)

The reviewed 3.31.0 operator defines ChaosEngine, ChaosExperiment and ChaosResult. It does not define ChaosHub or ChaosSchedule. Install a reviewed release and each required ChaosExperiment with scoped RBAC and verified runner/helper images before using these engine examples. The catalog’s current fault files include CI/latest image defaults; do not apply them blindly. Schema verification is not proof of your cluster/runtime compatibility.

These examples start with engineState: stop. After preparing the named targets, evaluate one experiment at a time using the installed release’s workflow. An active engine can delete Pods repeatedly over its duration; a 30-second duration is not a promise of exactly one deletion. The fixed TARGET_PODS is intentionally unresolved until you select a Pod by current name/UID. It must not be left blank or expanded to an entire production selector.

#### Pod deletion

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
#### Node drain, not instance termination

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: node-drain-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: node-drain-sa
  experiments:
  - name: node-drain
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_NODE
          value: REPLACE_WITH_ONE_OWNED_TEST_NODE
```
Drain affects workloads on the node beyond the application selector. Use a dedicated test node, an explicit nonempty name, PDB-aware eviction behavior and a recovery/uncordon plan. Never substitute a generic kubernetes.io/os=linux selector for ownership. This experiment is not EC2 node termination.

#### DNS error

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-dns-error-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=web-app,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-dns-error-sa
  experiments:
  - name: pod-dns-error
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '60'
        - name: TARGET_HOSTNAMES
          value: '["backend-service.resilience-demo.svc.cluster.local"]'
        - name: MATCH_SCHEME
          value: exact
        - name: CONTAINER_RUNTIME
          value: containerd
        - name: SOCKET_PATH
          value: /run/containerd/containerd.sock
        - name: PODS_AFFECTED_PERC
          value: '100'
```
TARGET_HOSTNAMES is a JSON-array string. Runtime/socket/privilege assumptions must match the selected Linux test nodes; the sample is not portable to every EKS node type. Scope the selected workload so this percentage cannot target unrelated Pods. Observe ChaosResult and application health; a resource existing is not a successful experiment.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine,chaosresult
```
[Litmus operator 3.31.0](https://github.com/litmuschaos/chaos-operator/releases/tag/3.31.0) · [Official fault catalog](https://github.com/litmuschaos/chaos-charts/tree/master/faults/kubernetes) · [CNCF project status](https://www.cncf.io/projects/litmus/)

### Chaos Mesh

The examples use the released 2.8.4 CRD shapes. Review the Helm chart’s runtime/socket, node selection, daemon privileges, dashboard access and cluster compatibility before installation. Privileged host fault injection must use an explicitly approved test node class; do not assume support on Auto Mode/Fargate/Hybrid Nodes from schema validity alone.

NetworkChaos/IOChaos/TimeChaos below are paused using the release’s experiment.chaos-mesh.org/pause annotation. Applying a paused manifest is still a cluster write. Review targets and status before separately removing the pause; wait for recovery status when stopping. Pause does not undo deleted data, and one-shot faults have different pause semantics.

#### Network latency

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: delay
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  delay:
    latency: 100ms
    jitter: 50ms
    correlation: '25'
  duration: 1m
```
#### Network partition

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: review-network-partition
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: partition
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  direction: both
  target:
    mode: fixed
    value: '1'
    selector:
      namespaces:
      - resilience-demo
      labelSelectors:
        app: backend
        experiment-approved: 'true'
  duration: 1m
```
#### I/O latency

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: IOChaos
metadata:
  name: review-io-delay
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  action: latency
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  volumePath: /audit-data
  delay: 100ms
  percent: 50
  duration: 1m
```
Use a disposable mounted test volume at /audit-data. This example leaves the optional path filter unset; confirm the selected files before activation. percent is the injection-operation percentage, not a capacity limit. Do not point this example at the original production PostgreSQL data directory. Verify recovery and data integrity from a known baseline.

#### Time offset

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: TimeChaos
metadata:
  name: review-time-offset
  namespace: resilience-demo
  annotations:
    experiment.chaos-mesh.org/pause: 'true'
spec:
  mode: fixed
  value: '1'
  selector:
    namespaces:
    - resilience-demo
    labelSelectors:
      app: web-app
      experiment-approved: 'true'
  timeOffset: -2h
  clockIds:
  - CLOCK_REALTIME
  duration: 1m
```
The -2h offset applies to the selected injected program’s CLOCK_REALTIME behavior, not a universal two-hour change to the node and every clock. Check the injection mechanism and application’s clock use before inferring token, scheduler or lease behavior. Duration bounds the intended fault window, not guaranteed application recovery time.

```bash
kubectl --context "$KUBE_CONTEXT" -n resilience-demo \
  get networkchaos,iochaos,timechaos -o yaml
```
[Chaos Mesh 2.8.4 chart](https://github.com/chaos-mesh/chaos-mesh/tree/v2.8.4/helm/chaos-mesh) · [Pause controller](https://github.com/chaos-mesh/chaos-mesh/blob/v2.8.4/controllers/common/desiredphase/controller.go)

### Game Day Framework

Define abort thresholds, an independent observer and an exact recovery owner before injection. Record detection and restoration separately, including failed/no-data observations. Stop one experiment before beginning the next, and verify restoration rather than declaring success solely because the fault duration elapsed.

| Phase                  | Activity                            | Deliverable               |
| ---------------------- | ----------------------------------- | ------------------------- |
| 1. Record Steady State | Collect metric baselines            | Dashboard snapshot        |
| 2. Inject Failure      | Run FIS/Litmus experiments          | Experiment logs           |
| 3. Observe Recovery    | Monitor automatic recovery process  | Recovery time measurement |
| 4. Analyze Impact      | Analyze error rate, latency changes | Impact report             |
| 5. Post-mortem Review  | Identify improvements, Action Items | Improvement plan          |

***

## Implementation Checklist

### Level 1 Basic

* [ ] Choose health probes appropriate to each long-running application
* [ ] Set Resource requests/limits
* [ ] Configure PodDisruptionBudget
* [ ] Implement Graceful shutdown (preStop hook)
* [ ] Set appropriate terminationGracePeriodSeconds

### Level 2 Multi-AZ

* [ ] Apply Pod Topology Spread Constraints
* [ ] Verify actual Pod/node distribution and surviving-AZ headroom
* [ ] Plan zonal storage recovery; use WaitForFirstConsumer for new provisioning
* [ ] Review ARC eligibility, N-1 readiness, alarms and separate autoshift authorization
* [ ] Monitor Cross-AZ traffic costs

### Level 3 Cell-Based

* [ ] Define Cell boundaries (Namespace or Cluster)
* [ ] Implement Cell Router
* [ ] Verify cell boundaries and the network plugin’s policy enforcement
* [ ] Implement Shuffle Sharding
* [ ] Set ResourceQuota per Cell

### Level 4 Multi-Region

* [ ] Decide on Multi-Region architecture pattern
* [ ] Configure Global Accelerator
* [ ] Deploy multi-cluster with ArgoCD ApplicationSet
* [ ] Establish data replication strategy
* [ ] Maintain consistency with GitOps

***

## Cost Considerations

The following preserves the original unverified cost illustrations, not current quotes or measured savings. Cross-AZ charges depend on service, traffic path/direction and region; $0.01/GB is not a universal all-inclusive EKS rate. Price actual resources and failure headroom using the current service pricing pages. No cost/chaos benchmark was rerun.

| Item                       | Cost Impact                          | Cost Reduction Strategy                      |
| -------------------------- | ------------------------------------ | -------------------------------------------- |
| Multi-Region Active-Active | 2x+ compared to single region        | Reduce Passive by 50-70% with Active-Passive |
| Cross-AZ Traffic           | $0.01/GB (within same region)        | Reduce 60-80% with Locality-aware routing    |
| Spot Instance              | 60-90% savings compared to On-Demand | Apply to stateless workloads                 |
| Chaos Engineering | Earlier $100–500/month illustration; actual FIS/resource usage applies | Bound experiment resources and duration |
| Cell Architecture | Earlier 10–20% increase illustration | Measure isolation overhead and operational value |

***

## Next Steps

* [EKS Advanced Debugging and Incident Response](11-eks-advanced-debugging.md)
* [EKS High Availability Quiz](../quizzes/eks/10-eks-resiliency-quiz.md)
* [Istio Service Mesh](../service-mesh/02-istio.md) - Circuit Breaker, Retry Deep Dive
