# EKS Cluster Creation Quiz - Part 5

> **Last Updated**: September 11, 2026

This quiz covers EKS operations, logging, policy enforcement and tenant isolation. The final questions connect these topics to access validation and retirement in the concept guide. Commands require reviewed cluster/Region/kubeconfig, IAM and controller prerequisites; no cloud deployment or production test was performed in this audit.

## Multiple Choice Questions

1. Which approach can combine a non-Spot baseline with interruptible capacity?
   * A) All nodes On-Demand
   * B) Separate On-Demand and Spot groups with workload placement
   * C) Select Reserved as every group’s capacityType
   * D) All workloads must use Fargate

<details>
<summary>Show Answer</summary>

**Answer: B) Separate On-Demand and Spot groups with workload placement**

A mix can fit an interruption-sensitive baseline plus interruption-tolerant capacity. Use separate managed groups for On-Demand and Spot, and explicit workload placement. This is not a universal “most effective” cost strategy: workload utilization, reliability requirements, region/instance pricing and operational effort determine the result.

AWS advertises Spot savings of up to 90% versus On-Demand, not a guaranteed discount for every capacity pool or measured savings in this guide. On-Demand avoids Spot reclamation but still has maintenance/failure risks. Checkpointing, retries and spare capacity matter for Spot.

Rightsizing, Cluster Autoscaler/Karpenter, compatible Graviton images and appropriate commitment discounts are other options. Reserved Instances/Savings Plans are billing arrangements, not another ordinary managed-group capacity setting. Fargate may fit some demand patterns; compare provisioned capacity and total cost instead of assuming one compute type always wins.

</details>

2. Why distribute suitable workloads across multiple AZs?
   * A) Always lower latency
   * B) Guaranteed higher throughput
   * C) Reduce single-AZ failure exposure
   * D) Automatically replicate across Regions

<details>
<summary>Show Answer</summary>

**Answer: C) Reduce single-AZ failure exposure**

Multiple AZs reduce dependence on a single failure domain. The managed EKS control plane is spread across AZs, but application availability additionally needs appropriately distributed replicas, healthy endpoints, spare capacity and compatible networking/storage.

Kubernetes controllers can create replacement Pods; bare Pods are not automatically recreated, and insufficient capacity, hard affinity or zonal EBS volumes may prevent recovery. Merely listing several subnets does not ensure every application replica is spread across them. Review topology spread/anti-affinity and the actual placement.

PDBs govern voluntary eviction, not AZ outages. Rolling updates and cross-AZ failover need application-level validation and a data recovery design. Multiple AZs do not provide cross-Region replication automatically and can add cross-AZ data-transfer cost.

</details>

3. What is the default CNI for conventional EKS EC2 nodes?
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>Show Answer</summary>

**Answer: C) Amazon VPC CNI**

Conventional EKS EC2 nodes use Amazon VPC CNI by default. It allocates VPC addresses through supported secondary-IP or prefix modes. Auto Mode provides its own managed networking capabilities; Hybrid Nodes use a supported alternative CNI. Do not install an unconfigured replacement over an existing CNI.

Security groups for Pods require their own supported instance/CNI configuration and policy selection; they are not automatically unique for every Pod. Native NetworkPolicy also requires supported compute and explicit enablement.

VPC-native routing avoids a conventional overlay in this design, but it is not a measured performance guarantee. Validate bandwidth, routing, IP capacity, policy behavior and application requirements. Integrations such as Load Balancer Controller also need their own installation and permissions.

</details>

4. Which workload identity mechanism uses the EKS OIDC issuer and a projected ServiceAccount token?
   * A) IAM Roles for Service Accounts (IRSA)
   * B) An EKS access policy
   * C) A Kubernetes RoleBinding alone
   * D) A node label

<details>
<summary>Show Answer</summary>

**Answer: A) IAM Roles for Service Accounts (IRSA)**

**IAM Roles for Service Accounts (IRSA)** uses a projected service-account token, the cluster's OIDC issuer and IAM trust to obtain STS temporary credentials. Scope trust to the intended audience (`sts.amazonaws.com`) and exact namespace/ServiceAccount subject, then grant only the required AWS actions/resources.

Use the intended ServiceAccount in the Pod and a compatible SDK credential chain. Verify the assumed-role identity; successful AWS access alone may come from other credentials. IRSA does not by itself prevent access to node IMDS credentials.

EKS Pod Identity is another role-to-ServiceAccount mechanism with a different agent/association flow. It is supported on eligible EC2/Auto Mode and specifically configured Hybrid Nodes, while Fargate needs another supported mechanism such as IRSA. Neither mechanism is an EKS access entry: workload AWS permissions and access to the Kubernetes API are separate.

</details>

5. Which controller scales existing EKS managed node-group ASGs from Kubernetes scheduling demand?
   * A) Horizontal Pod Autoscaler
   * B) Vertical Pod Autoscaler
   * C) Cluster Autoscaler
   * D) A ResourceQuota

<details>
<summary>Show Answer</summary>

**Answer: C) Cluster Autoscaler**

Cluster Autoscaler adjusts discovered existing node groups/ASGs. It needs a compatible installation, Kubernetes RBAC, dedicated AWS permissions and correct discovery tags; it is not installed merely by setting min/max sizes.

It considers scheduling requests/constraints for scale-out and relocation/disruption conditions for scale-in. Not every Pending Pod can be solved by adding nodes, and its scale-down utilization logic is not the same as a CPU-usage HPA threshold.

HPA adjusts replicas and VPA recommends/changes Pod requests; both can indirectly alter node demand. Karpenter is a separate capacity provisioner using NodePools/NodeClaims, not a universally faster replacement or an ASG controller. Validate the control loops and workload constraints.

</details>

## Short Answer Questions

6. How do you enable and verify EKS control-plane logging to CloudWatch?

<details>
<summary>Answer and Explanation</summary>

Enable the required control-plane log types: `api`, `audit`, `authenticator`, `controllerManager` and `scheduler`. In the EKS console use **Observability → Control plane logging → Manage logging**, not the old Logging-tab instruction.

This example enables all five; choose the reviewed set for your environment:

```bash
set -euo pipefail
LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
```
Poll the returned update ID until `Successful`, handling failures before another change. The eksctl alternative requires `--approve` to apply the logging change:

```bash
# Alternative to the AWS CLI update, not a second concurrent update.
eksctl utils update-cluster-logging --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --enable-types=api,audit,authenticator,controllerManager,scheduler --approve
```
Logs go to `/aws/eks/<cluster-name>/cluster` in the cluster Region. Streams rotate and there can be multiple streams per type; delivery is best effort, typically within minutes. Verify enabled configuration, current stream timestamps and relevant actual events. A log group alone is not proof. Set retention and access controls, account for ingestion/storage cost, and avoid publishing sensitive audit events. Worker and application logs need separate collectors.

</details>

7. How can kubelet logs be collected from conventional EKS Linux nodes into CloudWatch?

<details>
<summary>Answer and Explanation</summary>

Kubelet logs are node logs, separate from EKS control-plane logging. On the EKS-optimized AL2023 Linux path, inspect the systemd journal for `kubelet.service`; do not assume `/var/log/kubelet.log` or `/var/log/kube-proxy.log` exists. Kube-proxy commonly logs as a container. VPC CNI log files/stdout depend on its configuration.

The managed **Amazon CloudWatch Observability EKS add-on** installs the agent/operator and Fluent Bit. A raw quickstart manifest is not that managed add-on. Do not overwrite existing ServiceAccounts or replace an entire Fluent Bit ConfigMap without reviewing its owner.

This example is for a **Linux EC2 lab**, with Pod Identity Agent ready and an existing approved role trusted for this cluster's `amazon-cloudwatch/cloudwatch-agent` ServiceAccount. Review its CloudWatch permissions; `CloudWatchAgentServerPolicy` is AWS's managed baseline, not a claim that every permission is minimal for your log scope. The current chart's Fluent Bit uses that same ServiceAccount; a second `fluent-bit` IAM ServiceAccount is not required by this setup.

First select a compatible add-on build and inspect its schema. The Helm chart version and EKS add-on build string are different:

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?}" "${EXAMPLE_REGION:?}"
CLUSTER_VERSION=$(aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.version --output text)
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --kubernetes-version "$CLUSTER_VERSION"
: "${CLOUDWATCH_ADDON_VERSION:?Choose a reviewed compatible build with the configuration fields below}"
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --query configurationSchema --output text > cloudwatch-addon-schema.json
```
Save the following as `cloudwatch-addon-values.yaml`. It was rendered with official chart 6.6.0. The full Linux `dataplane-log.conf` override collects only kubelet journal records; empty application/host files disable those default log routes. Other global Fluent Bit sections retain their defaults. The add-on also collects Container Insights metrics, so this is not a log-only agent installation. Application Signals auto-monitoring is explicitly disabled to avoid automatically instrumenting services for this exercise.

```yaml
manager:
  applicationSignals:
    autoMonitor:
      monitorAllServices: false
containerLogs:
  fluentBit:
    config:
      extraFiles:
        application-log.conf: ''
        host-log.conf: ''
        dataplane-log.conf: |
          [INPUT]
            Name                systemd
            Tag                 dataplane.kubelet
            Systemd_Filter      _SYSTEMD_UNIT=kubelet.service
            DB                  /var/fluent-bit/state/kubelet.db
            Path                /var/log/journal
            Read_From_Tail      On

          [FILTER]
            Name                modify
            Match               dataplane.kubelet
            Rename              _HOSTNAME hostname
            Rename              MESSAGE message

          [OUTPUT]
            Name                cloudwatch_logs
            Match               dataplane.kubelet
            region              ${AWS_REGION}
            log_group_name      /aws/containerinsights/${CLUSTER_NAME}/dataplane
            log_stream_prefix   ${HOST_NAME}-
            auto_create_group   true
```
Confirm the mounted journal path and writable state directory on the intended nodes. These Linux overrides do not configure Windows collection; mixed, Hybrid and Auto Mode environments need their documented paths. Check the selected add-on schema and retain any unrelated existing configuration before adapting this to an update.

```bash
# New installation only, after the schema/role/configuration review.
: "${CLOUDWATCH_ROLE_ARN:?Existing approved Pod Identity role}"
CW_ASSOCIATIONS=$(jq -cn --arg role "$CLOUDWATCH_ROLE_ARN" \
  '[{serviceAccount:"cloudwatch-agent",roleArn:$role}]')
aws eks create-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --addon-version "$CLOUDWATCH_ADDON_VERSION" \
  --pod-identity-associations "$CW_ASSOCIATIONS" \
  --configuration-values file://cloudwatch-addon-values.yaml --resolve-conflicts NONE
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name amazon-cloudwatch-observability --query 'addon.{status:status,health:health,version:addonVersion}'
```
Wait for the specific add-on operation to finish and inspect health errors, agent/Fluent Bit Pods and fresh events under `/aws/containerinsights/<cluster>/dataplane`. A successful Helm render or log-group existence does not prove collection. Review IAM, network endpoints, log retention and ingestion/metric costs. Existing observability installations need a planned migration; do not run a second collector that duplicates logs or silently enable application restarts. No live agent installation, journal collection or CloudWatch delivery was tested here.

</details>

8. What replaced PSP, and how should equivalent admission controls be evaluated?

<details>
<summary>Answer and Explanation</summary>

PodSecurityPolicy was deprecated in Kubernetes 1.21 and removed in 1.25. Currently supported EKS versions do not provide that API. Pod Security Admission (PSA) enforces the Pod Security Standards (PSS) profiles, but is not a field-for-field replacement for every PSP feature.

For a new EKS 1.36 lab namespace, pin the profile version so a future cluster upgrade does not silently change the selected policy version:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: psa-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```
For existing production namespaces, assess audit/warn results and application compatibility before enforcing Restricted. PSA validates rather than supplying the old PSP mutation/defaulting behavior. Map old controls for host namespaces, capabilities, volumes, IDs and seccomp to appropriate replacements.

**Kyverno alternative:** the following uses the current CEL-based `policies.kyverno.io/v1` ValidatingPolicy available in the reviewed Kyverno 1.19.1/chart 3.9.1 path. Legacy ClusterPolicy is deprecated in 1.19; this is not a claim that it has already been removed. Install the compatible controller/CRDs separately and use a reviewed `policy-engine-lab` namespace. All ordinary, init and ephemeral containers are checked:

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```
**Gatekeeper alternative:** a ConstraintTemplate alone does not enforce a rule. The template and its Constraint below are a reviewed Gatekeeper 3.23.1 example; `templates.gatekeeper.sh/v1` and the generated Constraint API have different versions:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: |
      package k8snoprivilegedlab

      containers[c] {
        c := input.review.object.spec.containers[_]
      }
      containers[c] {
        c := input.review.object.spec.initContainers[_]
      }
      containers[c] {
        c := input.review.object.spec.ephemeralContainers[_]
      }
      violation[{"msg": msg}] {
        c := containers[_]
        c.securityContext.privileged == true
        msg := sprintf("Privileged container is not allowed: %v", [c.name])
      }
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```
These two engine examples are alternatives and demonstrate one control, not complete PSP parity or a production hardening policy. Test allowed/missing-securityContext cases and privileged regular/init/ephemeral containers. Account for admission failure policy, webhook availability and exemptions. GuardDuty, Security Hub and Inspector provide complementary threat/posture/vulnerability capabilities for supported resources; they do not replace admission-time Pod rejection.

</details>

## Hands-on Questions

9. Configure separate On-Demand and Spot groups, with placement controls and autoscaling prerequisites.

<details>
<summary>Answer and Explanation</summary>

Use **separate** managed groups: On-Demand 2–5 nodes for critical work and Spot 2–10 for interruption-tolerant work. These are examples, not measured savings or capacity guarantees. Choose one creation method and unused group names; verify private-subnet egress/endpoints, IAM and AMI/image compatibility first.

The eksctl configuration uses the supported `managedNodeGroups` and `spot` fields. Do not grant every node autoscaler-controller permissions:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: critical-workloads
  amiFamily: AmazonLinux2023
  instanceType: m5.xlarge
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  spot: false
  labels:
    workload-type: critical
    node-lifecycle: on-demand
- name: general-workloads
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large]
  privateNetworking: true
  desiredCapacity: 3
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    workload-type: general
    node-lifecycle: spot
  taints:
  - key: spot
    value: "true"
    effect: PreferNoSchedule
```
Save and review the file, then use `eksctl create nodegroup -f nodegroups.yaml` for the existing cluster. The AWS CLI alternative follows. EKS API taint effects use uppercase names and structured values, unlike Kubernetes/eksctl CamelCase:

```bash
set -euo pipefail
# Alternative to eksctl; use unused group names and approved role/subnet IDs.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${CRITICAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=5,desiredSize=2 \
  --instance-types m5.xlarge --capacity-type ON_DEMAND --ami-type AL2023_x86_64_STANDARD \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" --node-role "${NODE_ROLE_ARN:?}" \
  --labels workload-type=critical,node-lifecycle=on-demand
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$CRITICAL_NODEGROUP_NAME"

aws eks create-nodegroup --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "${GENERAL_NODEGROUP_NAME:?}" --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --instance-types m5.large m5a.large m5d.large m5ad.large --capacity-type SPOT \
  --ami-type AL2023_x86_64_STANDARD --subnets "$PRIVATE_SUBNET_A" "$PRIVATE_SUBNET_B" \
  --node-role "$NODE_ROLE_ARN" --labels workload-type=general,node-lifecycle=spot \
  --taints '[{"key":"spot","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
aws eks wait nodegroup-active --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$GENERAL_NODEGROUP_NAME"
```
In a new reviewed `placement-lab` namespace, these sleeping containers demonstrate scheduling only. Replace them with reviewed real application images before claiming application behavior. The critical selector requires On-Demand labels. The general workload prefers Spot but may fall back elsewhere; a toleration permits placement and does not force it, and `PreferNoSchedule` is a soft control.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: critical-app
  namespace: placement-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: critical-app
  template:
    metadata:
      labels:
        app: critical-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: workload-type
                operator: In
                values:
                - critical
              - key: node-lifecycle
                operator: In
                values:
                - on-demand
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: general-app
  namespace: placement-lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: general-app
  template:
    metadata:
      labels:
        app: general-app
    spec:
      automountServiceAccountToken: false
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 1
            preference:
              matchExpressions:
              - key: node-lifecycle
                operator: In
                values:
                - spot
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: placement-check
        image: public.ecr.aws/docker/library/busybox:1.37.0
        command:
        - sleep
        - '3600'
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      tolerations:
      - key: spot
        operator: Equal
        value: 'true'
        effect: PreferNoSchedule
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-app-pdb
  namespace: placement-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-app
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: general-app-hpa
  namespace: placement-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: general-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
The preserved request/limit values are illustrative. PDB protection applies to voluntary eviction and does not stop Spot reclamation or AZ failure. HPA requires Metrics Server and a meaningful load/metric relationship; the sleeping demonstration is not a scaling benchmark.

Prepare a dedicated Cluster Autoscaler ServiceAccount/role with tag-scoped AWS permissions and actual ASG discovery tags. Node-group tags are not proof of ASG tags. For EKS 1.36, render the reviewed chart/image pair and inspect it before installation:

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
Keep local-storage/system-Pod safeguards unless a separate review justifies changing them. Comparable CPU/memory/GPU shapes matter within mixed CA-managed groups. Managed node groups already have Spot rebalance/drain handling; do not blindly add a second Node Termination Handler. Self-managed capacity needs its own reviewed lifecycle handling. Validate interruption recovery, placement, data persistence and total cost under representative workload conditions.

</details>

## Advanced Questions

10. Compare EKS tenant-isolation approaches and their actual boundaries.

<details>
<summary>Answer and Explanation</summary>

Choose a tenant boundary from the actual trust, data, availability and governance requirements. The following are **alternative designs**, not instructions to combine every example into one shared namespace.

**Separate clusters/accounts:** dedicated API/control-plane resources reduce coupling and allow independent lifecycle choices, at higher operational cost. They do not automatically isolate shared IAM, VPCs, storage, quotas or external services, and do not guarantee that one tenant can never affect another. Use the reviewed cluster-creation guide instead of two unqualified default `eksctl create cluster` commands.

**Namespaces with enforced controls:** namespaces separate names, not all security or capacity. A platform administrator creates new tenant namespaces and owns their policy labels, quota and RBAC boundaries:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
---
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-b
  labels:
    tenant: b
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
```
The following complete tenant-a example includes the Role missing from the old RoleBinding, explicit workload permissions, intra-namespace traffic plus scoped DNS, ResourceQuota and LimitRange. Configure the authenticated `tenant-a-users` group and equivalent reviewed tenant-b resources separately:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
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
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
The policy needs a compatible enforcement engine and assumes ordinary CoreDNS labels; adapt NodeLocal DNSCache paths. Quotas are admission limits, not reserved nodes or guaranteed bandwidth. Workload creation can use namespace-local service accounts and Secrets, so restrict those through admission and keep platform credentials outside tenant namespaces. Shared kernels/control-plane resources still need threat-model review.

**Virtual clusters:** a virtual API/control plane can separate cluster-scoped configuration while shared-node workloads still share the host kernel/CNI/CSI. The reviewed vCluster 0.36.1 configuration uses current `sync.fromHost.nodes` fields and leaves host-node synchronization disabled. It is not required just to create a tenant; enabling it can expose host metadata. Private/dedicated-node architectures have different prerequisites and isolation properties.

Save the following as `vcluster-values.yaml`, replacing the storage class with an approved working class. Use separate, platform-controlled host namespaces so tenants cannot edit the privileged syncer/controller through a host RoleBinding:

```yaml
sync:
  fromHost:
    nodes:
      enabled: false
controlPlane:
  statefulSet:
    persistence:
      volumeClaim:
        enabled: true
        storageClass: REPLACE_WITH_APPROVED_STORAGE_CLASS
        size: 5Gi
        retentionPolicy: Retain
    imagePullPolicy: IfNotPresent
```

```bash
helm repo add vcluster https://charts.loft.sh
helm repo update vcluster
helm template vcluster-tenant-a vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-a-host -f vcluster-values.yaml > tenant-a-reviewed.yaml
helm template vcluster-tenant-b vcluster/vcluster --version 0.36.1 --kube-version 1.36.0 \
  --namespace vcluster-b-host -f vcluster-values.yaml > tenant-b-reviewed.yaml
```
Inspect the rendered RBAC, storage, resource requests, image and sync configuration, then deploy through the reviewed Helm/GitOps owner. The published chart renders `vcluster-pro:0.36.1` by default; review the selected edition, feature availability and licensing before deployment. Rendering does not verify entitlement, persistence, cluster startup or production isolation. Back up tenant state and understand PVC/PV retention before deleting a virtual cluster or its host namespace.

**AWS identity and governance:** use tenant-specific IRSA or supported Pod Identity roles with scoped trust and resource permissions. These AWS identities complement Kubernetes authorization. An SCP sets maximum permissions for covered member-account principals; it does not grant access or distinguish Kubernetes namespaces.

The following S3 denial illustrates an SCP attached only to **tenant A’s member account/OU**, targeting a reviewed tenant B bucket. Do not attach it to a shared account and expect it to distinguish A from B:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "DenyTenantBStoreFromTenantAAccount",
    "Effect": "Deny",
    "Action": ["s3:*"],
    "Resource": [
      "arn:aws:s3:::amzn-s3-demo-tenant-b",
      "arn:aws:s3:::amzn-s3-demo-tenant-b/*"
    ]
  }]
}
```
SCPs do not restrict the management account or service-linked roles and do not directly constrain unrelated external-account principals. Resource policies, IAM permissions and data protections remain necessary. This is one account-level guardrail, not a complete tenant-isolation policy. Test effective access and rollback/retention under the chosen design; no clusters, virtual clusters or SCPs were created here.

</details>


## Access and Lifecycle Checks

11. Does update-kubeconfig grant Kubernetes permissions?
   * A) Yes, cluster-admin automatically
   * B) No; it configures the client, while access entries/policies/RBAC determine permissions
   * C) Yes, through the CA certificate
   * D) Only for a new namespace

<details>
<summary>Show Answer</summary>

**Answer: B) No; it configures the client, while access entries/policies/RBAC determine permissions**

Initial administration depends on bootstrap/tool configuration. Keep a known administrator identity and test the intended role explicitly.

</details>

12. Can a namespace RoleBinding narrow an EKS cluster-admin access policy?
   * A) Yes, RBAC always overrides it
   * B) No, grants are additive
   * C) Yes, if the group name is system:masters
   * D) Only with kubectl --as

<details>
<summary>Show Answer</summary>

**Answer: B) No, grants are additive**

Use the intended access-policy scope or a custom RBAC group. --as/--as-group forces Kubernetes RBAC and does not test EKS access-policy grants.

</details>

13. What is needed beyond a Pod phase of Running?
   * A) Nothing
   * B) Only a log-group name
   * C) Readiness, rollout/health and the intended application path
   * D) Every Job must keep running forever

<details>
<summary>Show Answer</summary>

**Answer: C) Readiness, rollout/health and the intended application path**

Running can include unready containers; completed Jobs can correctly be Succeeded. Validate expected compute and real DNS/Service behavior.

</details>

14. Which is an appropriate EKS upgrade plan?
   * A) Use any newest upstream version
   * B) Skip directly across two minors
   * C) Use EKS release/readiness information and move one minor at a time
   * D) Assume rollback restores all persistent data

<details>
<summary>Show Answer</summary>

**Answer: C) Use EKS release/readiness information and move one minor at a time**

Conditional rollback within seven days does not rewind etcd, workloads or data. Review component compatibility and backups separately.

</details>

15. What should happen before retiring a cluster?
   * A) Delete every PVC immediately
   * B) Delete generic IAM roles by name
   * C) Remove the VPC first
   * D) Review identity/ownership, backups/reclaim policy, dependencies, protection and capabilities

<details>
<summary>Show Answer</summary>

**Answer: D) Review identity/ownership, backups/reclaim policy, dependencies, protection and capabilities**

Use the original IaC owner, explicit reviewed resources and completion checks. Preserve shared resources and recovery evidence.

</details>

## References

- [CloudWatch Observability add-on](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html)
- [EKS access policies](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS managed node groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
- [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
- [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [vCluster 0.36.1 configuration](https://github.com/loft-sh/vcluster/blob/v0.36.1/chart/values.yaml)
- [SCP scope](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)
