# Amazon EKS Upgrades Quiz

> **Last Updated**: September 12, 2026

This quiz tests your understanding of Amazon EKS cluster upgrade processes, best practices, troubleshooting, and related considerations.

## Quiz Overview

- EKS cluster upgrade planning
- Control plane upgrades
- Node group upgrades
- Add-on and component upgrades
- Upgrade testing and validation
- Upgrade troubleshooting

## Multiple Choice Questions

### 1. What is the most important first step when planning an Amazon EKS cluster upgrade?

- A. Immediately upgrade the control plane
- B. Upgrade all workloads at once
- C. Review compatibility and establish a test and recovery plan
- D. Upgrade all node groups simultaneously

<details>
<summary>Show Answer</summary>

**Answer: C. Review compatibility and establish a test and recovery plan**

Review the target EKS version, API changes and workload dependencies before selecting a change sequence. A compatibility inventory informs a decision; it does not certify availability.

**Compatibility review**

- Inspect manifests, Helm releases, API clients, CRDs, conversion/admission webhooks and operators. Include CNI/DNS, load balancers, service mesh, storage, monitoring, logging and backup components.
- Use the EKS cluster-version catalog for supported cluster versions. `describe-addon-versions` instead lists add-on compatibility with a Kubernetes version.
- Review EKS Upgrade Insights and available audit/metric evidence over a representative window. `apiserver_requested_deprecated_apis` is the relevant API-server metric where exposed. A missing series, denied request or empty scan does not prove absence of deprecated clients. Insights can retain historical usage within their observation window.
- An object's current `.apiVersion` is its returned representation, not necessarily the API version a client originally requested. Review deployed configuration, source and runtime callers.

Save `eks-upgrade-preflight.py` from the [source guide](../../eks/08-eks-upgrades.md), review its prerequisites, and run its read-only account/context/target inventory:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"
export CLUSTER_NAME AWS_REGION EXPECTED_ACCOUNT_ID KUBE_CONTEXT TARGET_VERSION
umask 077
python3 eks-upgrade-preflight.py > preflight.json
# Review this evidence and the workload/backup/capacity plan before a separate change step.
```

The helper fails on query errors. Review every finding in `preflight.json`; it neither executes an upgrade nor certifies compatibility. Select one supported minor above the current version using the current AWS catalog.

With a reviewed Pluto release, scan rendered manifests, Helm metadata and last-applied configuration:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TARGET_VERSION:?}"; : "${MANIFEST_DIR:?}"
pluto detect-files --directory "$MANIFEST_DIR" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-helm --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
pluto detect-api-resources --kube-context "$KUBE_CONTEXT" --target-versions "k8s=v${TARGET_VERSION}.0" --output wide
```

An earlier nonzero exit stops this shell block for investigation; complete the remaining checks after handling that result. API-resource detection depends on stored annotations and cannot observe all runtime requests. The kube-no-trouble project provides the `kubent` binary, not `kubectl-no-trouble`.

**Historical API-removal examples** — migration history, not current EKS upgrade targets:

| Kubernetes release | Removed serving API / migration |
| --- | --- |
| 1.22 | Several beta APIs, including `networking.k8s.io/v1beta1` Ingress; migrate to stable APIs and their field schemas |
| 1.25 | `policy/v1beta1` PodSecurityPolicy: migrate policy enforcement. `batch/v1beta1` CronJob → `batch/v1` |
| 1.26 | `autoscaling/v2beta2` HPA → `autoscaling/v2`; flow-control `v1beta1` removed |
| 1.27 | `storage.k8s.io/v1beta1` CSIStorageCapacity → `storage.k8s.io/v1` |
| 1.29 / 1.32 | FlowSchema / PriorityLevelConfiguration `v1beta2` / `v1beta3` removed respectively; use `flowcontrol.apiserver.k8s.io/v1` with field/default migrations |

For kubelet 1.25 and newer, upstream policy permits up to three older minors than the API server, never a newer kubelet; older kubelets have a two-minor limit. Mixed API-server versions during an HA upgrade narrow that range. This is a support boundary, not proof that every add-on or application works. Conservative EKS preparation brings nodes to the **current** control-plane version before the next control-plane upgrade.

**Rehearsal and plan template**

Use reviewed infrastructure definitions to prepare a separate environment with representative networking, IAM, compute types, data and controllers. Record production differences, cost and cleanup ownership. Start in development/staging and exercise business functions, scaling, recovery and alerting; do not incidentally run fault injection in production. The old 1.27→1.28 example is historical, not a current provisioning recommendation.

```markdown
# EKS upgrade plan — fill from evidence, not assumed results

- Account / Region / cluster ARN / kube context: TBD
- Current / target minor and EKS support status: TBD
- Node groups, Fargate, Auto Mode, hybrid nodes: inventory required
- Add-on / controller / CRD / webhook versions and owner: TBD
- Compatibility evidence, observation window and unresolved findings: TBD
- Backup coverage, application consistency, restore test and RPO/RTO: TBD
- Subnet IPs, EC2 quotas, placement, surge capacity and cost: TBD
- Rehearsal environment and differences from production: TBD

## Ordered change gates

- [ ] Align nodes to the current control-plane version; verify supported skew
- [ ] Complete API migrations and any required bridge add-on versions
- [ ] Complete a representative non-production rehearsal
- [ ] Upgrade the control plane by one minor; verify the exact update ID
- [ ] Upgrade nodes/add-ons in their reviewed dependency order
- [ ] Verify workloads and monitor agreed SLOs before retiring old capacity

## Test coverage and evidence

- [ ] Deployments: create, readiness, rollout and scaling
- [ ] StatefulSets / PVCs: write, reschedule, read and restore
- [ ] Services, DNS, Ingress / Gateway and external dependencies
- [ ] Jobs / CronJobs, operators, CRDs and admission webhooks
- [ ] API latency, Pod startup, network and resource baselines
- [ ] Controlled node/network/resource-pressure recovery in a test environment
- [ ] Alert delivery and incident ownership
- Result / timestamp / environment / evidence location: NOT RUN

## Recovery decision

- Stop criteria and incident owner: TBD
- Previous minor, upgrade completion time and 7-day rollback deadline: TBD
- Rollback eligibility, compute-type order and add-on compatibility: TBD
- Data restore or forward-fix procedure when version rollback is unsuitable: TBD
```

Record observations instead of pre-filling “all compatible” or “no CRD changes.” Version rollback does not restore application data; Question 5 covers eligibility and compute order. A, B and D skip evidence or combine changes so broadly that diagnosis and recovery become harder.

Sources: [API migration guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/), [version skew policy](https://kubernetes.io/releases/version-skew-policy/), [EKS upgrades](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [Pluto](https://pluto.docs.fairwinds.com/), [kube-no-trouble](https://github.com/doitintl/kube-no-trouble).

</details>

### 2. After prerequisite node alignment, what is the correct order for an in-place upgrade to the next minor?

- A. Move kubelets to the target minor while the API server is still on the older minor
- B. Upgrade the control plane to the target minor, then upgrade target-version node groups in reviewed stages
- C. Start all control-plane and target-version node changes concurrently
- D. A new cluster is mandatory for every minor-version upgrade

<details>
<summary>Show Answer</summary>

**Answer: B. Upgrade the control plane to the target minor, then upgrade target-version node groups in reviewed stages**

Bringing nodes to the **current** control-plane minor is preparation. Moving them to the **target** minor comes after the control plane supports it. EKS upgrades one minor at a time. Supported skew does not guarantee application compatibility. Follow each component's dependency requirements, including bridge add-on versions that may be needed before the control-plane change.

**Preparation and execution**

1. Confirm account, context, current/target support, cluster/node health, insights, subnet IP capacity and access. Plan replacement capacity and workload disruption controls.
2. Validate backups and restoration. EKS users cannot run `etcdctl` against the managed control plane. `kubectl get all` omits many resources and persistent data. Use appropriately configured AWS Backup EKS or Velero/application backups and test their coverage and restoration.
3. Review the preflight from Question 1. Save `eks-wait-update.py` from the [source guide](../../eks/08-eks-upgrades.md) before this separate mutation step, for the reviewed target with no conflicting update.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster}"
: "${AWS_REGION:?Set the reviewed Region}"
: "${TARGET_VERSION:?Set the next supported EKS minor version}"
umask 077
aws eks update-cluster-version \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --output json --no-cli-pager \
  > control-plane-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' control-plane-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

The poller follows this exact request. Only `Successful` succeeds; failure, cancellation, unknown status and API errors stop the procedure. Client timeout does not cancel the AWS operation. `ACTIVE` alone does not prove this update succeeded, and `aws eks wait update-successful` is not an EKS CLI waiter.

Alternatively, `eksctl upgrade cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --version "$TARGET_VERSION"` previews the change; `--approve` initiates it. Choose one owner and execution path rather than submitting both CLI and Terraform changes.

**After the request succeeds**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,platformVersion:platformVersion}'
aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl --context "$KUBE_CONTEXT" get --raw='/readyz'
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
kubectl --context "$KUBE_CONTEXT" get pods -n kube-system
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp'
```

The API readiness endpoint requires permission and is only one signal. Inspect actual workloads, DNS and controllers rather than obsolete `ComponentStatus` objects or an assumed managed-etcd Pod. Pure Auto Mode uses node-level CoreDNS; mixed clusters retain DNS for non-Auto nodes. Missing standard `aws-node`, kube-proxy or CoreDNS Deployments are not inherently Auto Mode faults. `kubectl top` requires Metrics Server; metric availability is separate from request success.

Proceed with a reviewed node group/canary and the required add-on sequence, validating each stage. Auto Mode manages nodes after the control-plane upgrade. Existing Fargate Pods retain their kubelet version; coordinate owner-driven replacement and availability.

**Availability and timing**

The old “20–30 minutes” estimate has no supplied measurement provenance and is retained only as a historical planning illustration, not a duration guarantee. Reserve a window based on rehearsals. API clients must reconnect as API servers are replaced. Existing containers may continue running, while API-dependent controllers and applications can still be affected. A started normal control-plane upgrade cannot be paused or cancelled. Preserve update IDs/errors and involve AWS Support as needed; later version rollback has separate eligibility.

**Terraform ownership example**

Modify the existing resource/module, preserving its other settings and dependencies. This excerpt is not a complete definition or a second resource to create for an existing cluster:

```hcl
# Fragment of the existing, state-managed cluster resource.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.target_version

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.cluster_security_group_id]
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

Supply existing IAM, subnet and security-group values and a reviewed target. Inspect the provider plan for unintended replacement or unrelated changes. `prevent_destroy` guards Terraform destruction, not service disruption. Empty `ignore_changes = []` neither waits nor validates an upgrade; the provider has its own waiter/timeouts. An IaC timeout is not service cancellation, and Git revert is not EKS version rollback. Use Question 6's bounded validation after the change. No live cluster execution was performed in this review.

A makes kubelet newer than the API server. C removes validation gates. D is false: new-cluster migration is optional and has distinct traffic/data migration costs.

Sources: [EKS update procedure](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html), [EKS backups](https://docs.aws.amazon.com/eks/latest/userguide/integration-backup.html), [Terraform EKS resource](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster).

</details>

### 3. Which approach supports a controlled EKS node-group upgrade?

- A. Terminate all nodes simultaneously
- B. Use a staged managed-node-group update or a validated blue/green migration
- C. Leave node versions unchanged indefinitely
- D. Individually replace kubelet binaries on managed nodes

<details>
<summary>Show Answer</summary>

**Answer: B. Use a staged managed-node-group update or a validated blue/green migration**

Select the strategy based on workload disruption tolerance, capacity, stateful storage and the compute owner. Neither a managed update nor blue/green migration guarantees uninterrupted service.

**Managed node groups**

The `DEFAULT` update strategy creates replacement capacity before retiring old nodes; `MINIMAL` removes old capacity first. `maxUnavailable` bounds concurrent unavailability. The normal rolling eviction path honors PDBs, but force update can bypass them. These strategies differ from the console's rolling-versus-force choice. A failed update does **not** imply automatic fleet rollback.

Save the source guide's `eks-wait-update.py` and complete Question 1's account/context/capacity review. For an existing group using an EKS-optimized AMI, select both the Kubernetes version and compatible AMI release explicitly:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
: "${TARGET_VERSION:?Set the reviewed target, no newer than the control plane}"
: "${TARGET_AMI_RELEASE:?Set the reviewed EKS-optimized AMI release}"
umask 077
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" --output json > nodegroup-before.json
if jq -e '.nodegroup.amiType == "CUSTOM"' nodegroup-before.json >/dev/null; then
  echo "Use the custom launch-template path for this node group" >&2
  exit 1
fi
aws eks update-nodegroup-version \
  --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$TARGET_VERSION" --release-version "$TARGET_AMI_RELEASE" \
  --output json > nodegroup-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' nodegroup-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID NODEGROUP_NAME
unset ADDON_NAME
python3 eks-wait-update.py
```

This stops on request or polling failure. Check actual node versions/readiness, Pod placement, events and application SLOs before the next group. For a custom AMI, use a reviewed new version of the **same original launch template** and omit `--kubernetes-version` and `--release-version`; follow the source guide's separate custom-AMI path. Do not edit kubelet packages in place and assume the AMI/runtime/bootstrap were upgraded.

`eksctl upgrade nodegroup` uses `--kubernetes-version`; `eksctl create nodegroup` uses `--version`. For creation, keep reviewed subnet, IAM, AMI, labels and taints in the existing cluster configuration rather than using an unsupported `--taints` flag or an incomplete one-line recipe.

**Blue/green sequence**

1. Retain blue capacity. Create green using the infrastructure owner with a version no newer than the control plane, matching AMI/architecture, private networking and sufficient quota/IP/AZ capacity.
2. Verify green nodes are Ready and test DNS, networking, storage and workload dependencies. Taint green for canaries until suitable workloads tolerate it.
3. Migrate workload Pod templates in stages. Preferred affinity is only a preference and does not move existing Pods. Use an explicit selection when placement is mandatory and initiate a controlled rollout through the workload owner.
4. Inspect each old node's workloads and drain one at a time. Stop on eviction failure; do not continue to termination after a failed drain.
5. Retire blue only after workload/data/traffic evidence and the recovery window have been reviewed. A “yes” prompt or a Ready node listing is not evidence that migration completed.

The following is a complete **independent canary fixture**, not a replacement manifest for an existing application. Prepare its namespace deliberately. It needs at least three eligible Linux green nodes because of required hostname anti-affinity. The toleration permits the taint; the node selector chooses green. Adapt application image/configuration, disruption policy and rollout parameters separately.

```yaml
# Independent fixture in an explicitly prepared test namespace.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: upgrade-canary
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 0
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: upgrade-canary
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
        example.com/upgrade: green
      tolerations:
        - key: example.com/upgrade
          operator: Equal
          value: green
          effect: NoSchedule
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: upgrade-canary
              topologyKey: kubernetes.io/hostname
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: http
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - mkdir -p /tmp/www; printf 'ok\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www
          ports:
            - name: http
              containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: http
            periodSeconds: 5
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: upgrade-canary
  namespace: upgrade-canary
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: upgrade-canary
```

The Deployment's own rolling update is controlled by its strategy, not the PDB. A PDB governs voluntary eviction, not ordinary Deployment/ReplicaSet scale-down or every infrastructure termination. Required anti-affinity can block scheduling if suitable capacity disappears. No image or cluster execution is claimed for this fixture.

For one reviewed old node, the source guide's bounded drain keeps the protections for unmanaged Pods and `emptyDir` data:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
: "${NODE_NAME:?Set one reviewed old node}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o wide
kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" \
  -o jsonpath='{.spec.providerID}{"\n"}'
kubectl --context "$KUBE_CONTEXT" get pods --all-namespaces \
  --field-selector "spec.nodeName=$NODE_NAME" -o wide
# Stop on failure. Do not terminate the instance or delete the node group here.
kubectl --context "$KUBE_CONTEXT" drain "$NODE_NAME" --ignore-daemonsets --timeout=10m
```

A failed drain can leave a node cordoned or partly drained; investigate and recover deliberately. Do not add `--force`, `--delete-emptydir-data` or `--disable-eviction` just to make a migration finish.

**Terraform blue/green example**

Preserve existing resource addresses/settings. These EKS-optimized-AMI fragments keep **both** groups at positive capacity; the green taint is intentionally matched by the canary above.

```hcl
# Existing blue resource address is retained; green is separate capacity.
# Inputs describe reviewed EKS-optimized AMIs, not a custom launch template.
variable "capacity" {
  type    = object({ desired = number, min = number, max = number })
  default = { desired = 3, min = 3, max = 6 }
  validation {
    condition = (
      var.capacity.min >= 1 &&
      var.capacity.desired >= var.capacity.min &&
      var.capacity.max >= var.capacity.desired &&
      alltrue([for n in values(var.capacity) : floor(n) == n])
    )
    error_message = "Retain positive integer capacity: 1 <= min <= desired <= max."
  }
}

resource "aws_eks_node_group" "blue" {
  cluster_name    = var.cluster_name
  node_group_name = "blue-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.blue_version
  release_version = var.blue_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "blue" }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_node_group" "green" {
  cluster_name    = var.cluster_name
  node_group_name = "green-nodegroup"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.green_version
  release_version = var.green_ami_release
  ami_type        = var.ami_type
  instance_types  = var.instance_types
  scaling_config {
    desired_size = var.capacity.desired
    min_size     = var.capacity.min
    max_size     = var.capacity.max
  }
  labels = { "example.com/upgrade" = "green" }
  taint {
    key    = "example.com/upgrade"
    value  = "green"
    effect = "NO_SCHEDULE"
  }
  update_config {
    max_unavailable = 1
  }
  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}
```

Supply the existing cluster/role/subnets, compatible instance types/AMI family and separately reviewed blue/green versions and releases. Green's version must already be supported by the control plane. The `desired_size` ignore rule assumes an autoscaler owns that field; remove it if Terraform is the intended owner. Minimum/maximum changes still apply, and changing a managed node group's scaling configuration does **not** honor PDBs. Do not use a Boolean switch to reduce blue to zero while creating green, or set `max_size = 0` (invalid). Node creation, workload migration and retirement are separate changes; a Terraform dependency alone cannot prove workload readiness.

Define recovery criteria beforehand. While blue is retained, workload placement may be reversible subject to API/data compatibility. Control-plane rollback and MNG version rollback have the additional conditions in Question 5. A, C and D either widen disruption, accumulate unsupported skew, or bypass the managed replacement lifecycle.

Sources: [managed-node updates](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html), [update behavior](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html), [PDBs](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/), [Terraform node groups](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group).

</details>

### 4. What is the correct approach to add-on management during an EKS upgrade?

- A. Ignore add-on upgrades
- B. Upgrade every add-on before the control plane regardless of compatibility
- C. Select compatible versions and follow each component’s dependency and bridge-version sequence
- D. Remove every add-on and reinstall

<details>
<summary>Show Answer</summary>

**Answer: C. Select compatible versions and follow each component’s dependency and bridge-version sequence**

There is no universal “all add-ons after the control plane” rule. Some components need an intermediate version compatible with both control-plane versions before the change; others follow it. Review each release's supported Kubernetes, architecture, compute types, APIs and upgrade path. EKS-managed add-on versions are not automatically upgraded with the control-plane version, and “managed” does not promise automatic installation of every security release.

**Inspect, select and preserve configuration**

For one installed, owned managed add-on, inspect the current state, compatible candidates and the schema for a reviewed candidate. An array's first element is not a “latest compatible version” contract.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"
: "${TARGET_VERSION:?Set the Kubernetes version for this stage}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json > addon-before.json
aws eks describe-addon-versions --addon-name "$ADDON_NAME" \
  --kubernetes-version "$TARGET_VERSION" --region "$AWS_REGION" \
  --output json > addon-candidates.json
# Select ADDON_VERSION after reviewing compatibility, architecture, compute type, and upgrade path.
: "${ADDON_VERSION:?Set the reviewed add-on version}"
aws eks describe-addon-configuration --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --output json > addon-schema.json
jq -r '.addon.configurationValues // "{}"' addon-before.json > addon-config-candidate.json
```

`addon-before.json` includes version/configuration/identity information. A single `aws-node` ConfigMap is not a complete CNI backup; DaemonSet settings, custom resources and IAM/Pod Identity may also matter. Protect evidence files. `addon-config-candidate.json` is input for review, not automatically valid target configuration. Merge intended settings against the new schema and review removed/defaulted fields and release notes.

After completing that review, use the source guide's exact-request poller and a complete target configuration file:

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ADDON_NAME:?}"; : "${ADDON_VERSION:?}"
: "${REVIEWED_ADDON_CONFIG_FILE:?Provide the complete reviewed target configuration JSON}"
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --addon-version "$ADDON_VERSION" --region "$AWS_REGION" \
  --configuration-values "file://$REVIEWED_ADDON_CONFIG_FILE" \
  --resolve-conflicts PRESERVE --output json > addon-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' addon-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID ADDON_NAME
unset NODEGROUP_NAME
python3 eks-wait-update.py
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name "$ADDON_NAME" \
  --region "$AWS_REGION" --output json
```

`PRESERVE` addresses existing field conflicts; it is not a guarantee that an explicit configuration payload is fully merged, accepted or functionally correct. `NONE` fails on conflicts; `OVERWRITE` can replace customizations with EKS defaults. Do not use overwrite as an automatic recovery shortcut. Check update success **and** add-on health/workload behavior before the next dependency; sleeping 30 seconds is not a completion check.

**Component-specific checks**

| Component | Check before progressing |
| --- | --- |
| VPC CNI | Supported upgrade path, IP allocation, node/Pod networking, custom networking and IAM |
| CoreDNS | DNS resolution, Corefile/schema changes, scheduling/readiness and PDB settings |
| kube-proxy | Kubernetes skew, Service reachability and the cluster's actual data plane |
| Cluster Autoscaler | Supported Kubernetes minor, discovery/IAM and scaling ownership |
| Metrics Server | Supported versions, APIService availability and kubelet TLS/access |
| Load Balancer Controller / ExternalDNS / mesh | Controller/chart/CRD/API compatibility, IAM, webhook and traffic behavior |

Pure Auto Mode provides node-level DNS/networking and does not require these standard-node add-ons in the same way. Mixed clusters must retain the components needed by non-Auto nodes, including CoreDNS Deployment coverage. Identify ownership before upgrading or removing anything.

**Terraform-managed add-ons**

Use reviewed version/configuration maps in the existing state-owned resources; retain their IAM/Pod Identity settings. These fragments apply to standard-node add-ons, not a universal Auto Mode installation:

```hcl
# Fragments of existing, imported/state-managed standard-node add-ons.
# Preserve each resource's existing IAM/Pod Identity settings as applicable.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = var.cluster_name
  addon_name                  = "vpc-cni"
  addon_version               = var.addon_versions["vpc-cni"]
  configuration_values        = file(var.addon_config_files["vpc-cni"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.addon_versions["coredns"]
  configuration_values        = file(var.addon_config_files["coredns"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = var.cluster_name
  addon_name                  = "kube-proxy"
  addon_version               = var.addon_versions["kube-proxy"]
  configuration_values        = file(var.addon_config_files["kube-proxy"])
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

The current provider separates `resolve_conflicts_on_create` and `resolve_conflicts_on_update`. Creation does not accept `PRESERVE`; `NONE` deliberately exposes migration conflicts. Do not add a duplicate cluster resource to perform an add-on update. Change only the component scheduled for the current stage; listing three independent resources does not establish a safe upgrade order. Resource destruction or setting changes require their own review.

**Self-managed Helm releases**

Use the existing release owner, a reviewed chart reference/version and migrated values. Install, ownership migration and upgrade are different operations. Preserve CRDs, identity, ServiceAccount, resource/scheduling settings and current behavior:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${RELEASE:?}"; : "${ADDON_NAMESPACE:?}"
: "${CHART_REF:?Set the verified repository/chart or OCI reference}"
: "${CHART_VERSION:?Set a reviewed compatible chart version}"
: "${REVIEWED_VALUES_FILE:?Set the complete reviewed target values file}"
umask 077
helm get values "$RELEASE" --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > addon-values-before.yaml
helm show values "$CHART_REF" --version "$CHART_VERSION" > addon-values-defaults.yaml
# Merge/migrate values and handle CRDs/IAM through the owner before this step.
helm upgrade "$RELEASE" "$CHART_REF" --version "$CHART_VERSION" \
  --namespace "$ADDON_NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  -f "$REVIEWED_VALUES_FILE" --wait --timeout 15m
```

Prepare the reviewed values before the final command. `--wait` does not prove application SLOs or handle all CRD migrations. Do not bulk-install a second controller or change unrelated autoscaler flags during an upgrade. Validate each release's Pods, events and representative functions; record failures instead of printing unconditional completion.

A ignores security and compatibility maintenance. B can install versions incompatible with the still-old control plane. D unnecessarily discards ownership/configuration and can interrupt networking or DNS.

Sources: [updating EKS add-ons](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html), [Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html), [Terraform add-ons](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon), [Helm upgrade](https://helm.sh/docs/helm/helm_upgrade/).

</details>

### 5. What is the most effective approach to problems during an EKS upgrade?

- A. Immediately create a new cluster
- B. Rely only on AWS Support without collecting evidence
- C. Use systematic troubleshooting, logs and hypothesis testing
- D. Ignore upgrade problems

<details>
<summary>Show Answer</summary>

**Answer: C. Use systematic troubleshooting, logs and hypothesis testing**

Define the symptom, start time, affected workloads and business impact; correlate them with specific changes. Collect evidence before testing hypotheses. Apply a targeted correction only after reviewing its expected impact, then verify recovery and record prevention measures. Possible causes are not established root causes.

**Read-only diagnosis**

Confirm the account/context and exact operation ID. The following collector validates its operation type before querying and uses a new private evidence directory. A query failure stops it; files already written are partial evidence, not a successful diagnosis.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${UPDATE_ID:?Set the exact affected update ID}"
: "${ISSUE_KIND:?Set control-plane, nodegroup, or addon}"
: "${EVIDENCE_PARENT:?Set an existing private evidence directory}"
args=(--name "$CLUSTER_NAME" --region "$AWS_REGION" --update-id "$UPDATE_ID")
case "$ISSUE_KIND" in
  control-plane) ;;
  nodegroup) : "${NODEGROUP_NAME:?}"; args+=(--nodegroup-name "$NODEGROUP_NAME") ;;
  addon) : "${ADDON_NAME:?}"; args+=(--addon-name "$ADDON_NAME") ;;
  *) echo "Unknown ISSUE_KIND" >&2; exit 2 ;;
esac
umask 077
EVIDENCE_DIR=$(mktemp -d "$EVIDENCE_PARENT/eks-upgrade-diagnosis.XXXXXXXX")
printf 'Evidence directory: %s\n' "$EVIDENCE_DIR"
aws eks describe-update "${args[@]}" --output json --no-cli-pager \
  > "$EVIDENCE_DIR/update.json" 2> "$EVIDENCE_DIR/update.stderr"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{version:version,status:status,health:health,logging:logging}' \
  --output json --no-cli-pager > "$EVIDENCE_DIR/cluster.json"
kubectl --context "$KUBE_CONTEXT" get nodes -o wide > "$EVIDENCE_DIR/nodes.txt"
kubectl --context "$KUBE_CONTEXT" get pods -A -o wide > "$EVIDENCE_DIR/pods.txt"
kubectl --context "$KUBE_CONTEXT" get events -A --sort-by='.metadata.creationTimestamp' \
  > "$EVIDENCE_DIR/events.txt"
printf 'Snapshots collected; review errors and workload evidence before changing anything.\n'
```

For a node-group or add-on operation, also inspect that resource's `health.issues` and its version/configuration through `describe-nodegroup` or `describe-addon`. Check node ProviderIDs, EC2 status, IAM/bootstrap/AMI/networking and scheduling constraints as appropriate. Do not infer a cause solely from an update's `Failed` status.

Read existing control-plane logs over a bounded window:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
: "${START_TIME_MS:?Set the reviewed start timestamp in epoch milliseconds}"
: "${END_TIME_MS:?Set the reviewed analysis-window end timestamp}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.logging' --output json --no-cli-pager
# Read existing logs; enabling logging is a separate change and does not backfill history.
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name "/aws/eks/$CLUSTER_NAME/cluster" \
  --start-time "$START_TIME_MS" --end-time "$END_TIME_MS" \
  --max-items 200 --output json --no-cli-pager
```

Enabling logging is a separate cluster change and does not backfill earlier events. An absent log group, permission error or empty query is a visibility limitation. Where a relevant Pod exists, inspect it explicitly:

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${AFFECTED_NAMESPACE:?}"; : "${AFFECTED_POD:?}"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" describe pod "$AFFECTED_POD"
kubectl --context "$KUBE_CONTEXT" -n "$AFFECTED_NAMESPACE" logs "$AFFECTED_POD" \
  --all-containers=true --prefix=true --since=15m --tail=100
```

Pod-agent logs are not all host kubelet/runtime journals. Auto Mode, Fargate and standard EC2 have different diagnostic access. Protect snapshots and redact sensitive configuration before sharing with AWS Support; avoid indiscriminate cluster dumps.

| Symptom | Hypotheses to test with evidence |
| --- | --- |
| Control-plane request failed | Exact update errors, prerequisites, subnet IPs/security groups and AWS service-side failure |
| Node not Ready / Pod Pending | AMI/bootstrap, EC2 capacity, IAM/networking/CNI, taints, affinity, PVC topology or resources |
| Add-on CrashLoopBackOff | Configuration/schema, identity, image/startup, resources or version compatibility |
| Application API errors | Removed API callers, admission/conversion webhooks, permissions or application regression |

Retrying, deleting a node group or overwriting add-on configuration is not a diagnosis. Add-on recovery requires a compatible version **and** reviewed configuration/identity, with exact-update monitoring as in Question 4.

**Current EKS rollback conditions**

In-place control-plane rollback is supported under the current EKS guide. It is distinct from application data restore and from replacing a failed node.

- Initiate within seven days of a completed in-place upgrade, to the immediately previous minor. A cluster created at the current version is not eligible; repeated rollbacks to successively older minors are not supported.
- The target must remain supported. An extended-support target needs the `EXTENDED` policy and incurs its charges. An automatic upgrade at end of extended support cannot be rolled back; end-of-standard-support cases have the documented policy conditions.
- Check `ACTIVE`, conflicting updates, backward-incompatible features and other prerequisites. `ROLLBACK_READINESS` `ERROR`/`UNKNOWN` insights block; `WARNING` is advisory. `--force` bypasses insight checks, not eligibility/prerequisites or Auto Mode disruption controls. This differs from the temporary rollback of normal upgrade-insight `--force` enforcement.

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${KUBE_CONTEXT:?}"
aws eks list-insights --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --filter '{"categories":["ROLLBACK_READINESS"]}' --output json --no-cli-pager
kubectl --context "$KUBE_CONTEXT" get nodes -o wide
```

Inspect individual findings with `describe-insight --id "$INSIGHT_ID"`. Do not treat an empty insight list as proof that every prerequisite is met.

| Compute type | Order and limits |
| --- | --- |
| Managed node groups | Roll back applicable groups with `UpdateNodegroupVersion` before the control plane, following the source guide and custom-AMI requirements; verify actual nodes |
| Self-managed / hybrid | Owner coordinates compatible nodes and workload migration before the control plane |
| Auto Mode | Service rolls nodes back first, then the control plane; track the update ID even while cluster status is `ACTIVE` during the node phase |
| Fargate | No in-place kubelet rollback; coordinate Pod/controller/HPA/GitOps/Job behavior and availability so replacement Pods do not immediately recreate the newer kubelet before control-plane rollback |

After validating the applicable node sequence and all prerequisites, the control-plane request uses `update-cluster-version`, not a `rollback-cluster` command. Save the source guide's poller first:

```bash
umask 077
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${ROLLBACK_VERSION:?}"
: "${WAIT_TIMEOUT_SECONDS:?Set an explicit client wait for the approved rollback}"
aws eks update-cluster-version --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --kubernetes-version "$ROLLBACK_VERSION" --output json --no-cli-pager > rollback-update.json
UPDATE_ID=$(jq -er '.update.id | select(type == "string" and length > 0)' rollback-update.json)
export CLUSTER_NAME AWS_REGION UPDATE_ID WAIT_TIMEOUT_SECONDS
unset NODEGROUP_NAME ADDON_NAME
python3 eks-wait-update.py
```

For Auto Mode, use the source guide's alternative `--rollback-config timeoutMinutes=...` request, not a second concurrent request. The default is 720 minutes, supported range 120–10080; this is not an exact finish deadline. Zero drift budgets or node disruption exclusions can block progress. PDBs/Pod disruption exclusions interact with termination grace periods and do not imply indefinite protection. `--force` does not bypass those controls.

Only the Auto Mode node phase before control-plane rollback supports best-effort `CancelUpdate`; in-flight disruption may complete. Timeout/cancellation leaves the control plane unchanged and nodes reconcile back toward its version. A client timeout alone does not cancel the operation. Retry remains subject to the original eligibility window.

Rollback preserves etcd/workload/PV data rather than restoring a backup; add-ons are not automatically reverted. The previous minor receives its latest platform version, not necessarily the exact former platform. CloudFormation rollback or Git revert is not this service operation. Use the source guide's full decision procedure; none of these commands was run against AWS in this review.

**Incident record**

The original timestamp below is preserved. The scenario and purported cause lack supplied incident evidence, so they remain an illustration with hypotheses:

```markdown
# Upgrade troubleshooting report — illustrative, not a verified incident

## Problem description

- Example symptom: CoreDNS Pods in CrashLoopBackOff after a node-group update
- Example impact: service discovery and application connections affected
- Original illustrative timestamp: 2023-07-15 14:30 UTC
- Provenance: no incident logs or measurement evidence supplied

## Investigation

1. Record the exact update ID, versions, changes and affected workloads.
2. Inspect CoreDNS logs/events, node conditions and resource availability.
3. Compare the owned Corefile/configuration with the reviewed baseline.
4. Check connectivity, network policies, scheduling and dependency changes.

## Hypotheses, not established findings

- A configuration parsing error is one possible explanation.
- A ConfigMap modification requires a diff/audit record and relevant log evidence.
- Record evidence that supports or rejects each hypothesis.

## Conditional remediation

1. If a configuration regression is demonstrated, restore compatible reviewed settings.
2. Coordinate any restart with replicas, readiness, PDB and DNS availability.
3. Verify service discovery and application SLOs, not just Pod phase.

## Prevention and record

- Version and back up owned configuration; rehearse restoration.
- Add regression checks and staged rollout gates.
- Actual actions, results and evidence: NOT RUN / TO BE RECORDED.
```

Share the exact update ID, bounded logs/errors, impact and attempted actions with AWS Support. A can add an unplanned migration without resolving the cause; B omits useful evidence; D leaves reliability/security issues untreated.

Sources: [EKS rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html), [Auto Mode rollback](https://docs.aws.amazon.com/eks/latest/userguide/rollback-automode.html), [EKS troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html).

</details>

### 6. What is the most comprehensive post-upgrade validation approach?

- A. Only count nodes
- B. Only verify the cluster version
- C. Validate request status, components, workload functions and representative performance in stages
- D. Send all production traffic immediately without validation

<details>
<summary>Show Answer</summary>

**Answer: C. Validate request status, components, workload functions and representative performance in stages**

First verify the exact update request, version and node/add-on state. Then exercise functionality and compare application metrics with a recorded baseline. Passing a smoke test is narrower than proving production readiness or an SLO.

| Area | Evidence |
| --- | --- |
| Control plane | Update result, API readiness/responsiveness and supported metrics/logs; managed etcd is not directly accessible |
| Nodes | Ready conditions, expected kubelet/AMI/runtime, scheduling and compute-type-specific health |
| Network | Pod/Service/DNS, Ingress/Gateway, egress and dependency connectivity |
| Storage | Provisioning, write/read across consumers, topology, rescheduling and application-consistent restoration |
| Security | Intended authentication/authorization, Pod security, NetworkPolicy and encryption behavior |
| Workloads | Deployment rollout/scaling, StatefulSets, Jobs/CronJobs, CRDs/operators and webhooks |
| Performance | Comparable request rate, latency/error distribution, startup time and resource usage over a representative window |

Use the source guide's `eks-upgrade-smoke.py` for a bounded Linux EC2 test after reviewing context, compatible StorageClass, CSI driver/IAM, scheduling, admission/network policy and cost. Save the supplied implementation locally; this is not a reference to an undefined validation image or script.

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test cluster context}"
: "${TEST_STORAGE_CLASS:?Set an existing compatible test StorageClass}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
python3 eks-upgrade-smoke.py
```

The helper creates a unique namespace, records its UID, runs Deployment rollout/scaling and 20 HTTP requests, and writes then reads a PVC marker using separate Jobs. The writer is created before waiting for binding, so `WaitForFirstConsumer` can schedule a consumer; the writer is removed before the reader. Failures retain evidence/resources. Optional success cleanup requires the same namespace UID; a `Retain` PV may remain billable. It does not test every workload, restore procedure, Fargate/Auto configuration, performance limit or security control.

Choose additional owner-reviewed functional and load tests from the table. `kubectl top` depends on Metrics Server and is a current usage view, not throughput or latency proof. Do not use an unbounded wget loop against production. Record target traffic, duration, success/error criteria, baseline, environment differences and actual results; never infer a benchmark from synthetic fixtures.

**Optional Terraform fixture**

This separately managed fixture preserves the namespace/Deployment/Service/PVC learning example. Configure the provider for the reviewed context, supply a new namespace and compatible StorageClass, and inspect the plan. Do not adopt or destroy a pre-existing namespace. It is a fixture, not an automated validation verdict.

```hcl
# Separate disposable fixture; configure the Kubernetes provider/context externally.
variable "validation_namespace" {
  type = string
  validation {
    condition     = can(regex("^eks-upgrade-validation-[a-z0-9]{8,16}$", var.validation_namespace))
    error_message = "Supply a new, unique namespace with the required validation prefix."
  }
}
variable "test_storage_class" {
  type = string
  validation {
    condition     = length(trimspace(var.test_storage_class)) > 0
    error_message = "Select an existing compatible test StorageClass."
  }
}

resource "kubernetes_namespace_v1" "validation" {
  metadata {
    name = var.validation_namespace
  }
}

resource "kubernetes_persistent_volume_claim_v1" "validation_pvc" {
  metadata {
    name      = "validation-pvc"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_until_bound = false
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = var.test_storage_class
    resources {
      requests = { storage = "1Gi" }
    }
  }
}

resource "kubernetes_deployment_v1" "validation_app" {
  metadata {
    name      = "validation-app"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  wait_for_rollout = true
  spec {
    replicas = 1
    strategy {
      type = "Recreate"
    }
    selector {
      match_labels = { app = "validation-app" }
    }
    template {
      metadata {
        labels = { app = "validation-app" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "http"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args = [
            "test -f /data/index.html || printf 'fixture\\n' > /data/index.html; exec httpd -f -p 8080 -h /data"
          ]
          port {
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "8080"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "data"
            mount_path = "/data"
          }
        }
        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.validation_pvc.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "validation_service" {
  metadata {
    name      = "validation-service"
    namespace = kubernetes_namespace_v1.validation.metadata[0].name
  }
  spec {
    selector = { app = "validation-app" }
    type     = "ClusterIP"
    port {
      port        = 80
      target_port = "8080"
    }
  }
}
```

`wait_until_bound = false` lets Terraform create the consumer before a `WaitForFirstConsumer` PVC binds. The Deployment waits for rollout/readiness. One replica and `Recreate` avoid a rolling multi-node attachment assumption for an RWO volume; this deliberately has downtime. The PVC is actually mounted, but serving a file is not proof of persistence across replacement or a successful backup restore. Use independent write/recreate/read and restoration evidence. Inspect the PV reclaim policy before cleanup. `_v1` resource fields were checked against provider documentation; no Kubernetes-provider apply or live fixture run was performed.

**Validation dashboard**

The following ConfigMap assumes an existing Grafana dashboard sidecar watching `monitoring` with label `grafana_dashboard=1`, datasource UID `prometheus`, and a single-cluster kube-prometheus-stack scrape layout. Adjust those settings and job labels to the actual installation. Do not install a second monitoring stack for this fixture.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-validation-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  cluster-validation.json: |
    {
      "uid": "eks-upgrade-validation",
      "title": "EKS Upgrade Validation",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Ready nodes",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum(max by (node) (kube_node_status_condition{job=\"kube-state-metrics\",condition=\"Ready\",status=\"true\"}))"
            }
          ]
        },
        {
          "id": 2,
          "title": "Ready active Pods (%)",
          "type": "stat",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * sum(max by (namespace, pod, uid) (kube_pod_status_ready{job=\"kube-state-metrics\",condition=\"true\"}) and on (namespace, pod, uid) (max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}) == 1)) / sum(max by (namespace, pod, uid) (kube_pod_status_phase{job=\"kube-state-metrics\",phase=~\"Pending|Running|Unknown\"}))"
            }
          ]
        },
        {
          "id": 3,
          "title": "API requests / second",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "reqps"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (code) (rate(apiserver_request_total{job=\"apiserver\"}[5m]))"
            }
          ]
        },
        {
          "id": 4,
          "title": "Node CPU busy (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - avg by (instance) (max by (instance, cpu) (rate(node_cpu_seconds_total{job=\"node-exporter\",mode=\"idle\"}[5m]))))"
            }
          ]
        },
        {
          "id": 5,
          "title": "Node memory used (%)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 16
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "percent"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "100 * (1 - max by (instance) (node_memory_MemAvailable_bytes{job=\"node-exporter\"}) / max by (instance) (node_memory_MemTotal_bytes{job=\"node-exporter\"}))"
            }
          ]
        }
      ]
    }
```

“Ready active Pods” uses readiness and excludes completed/failed lifecycle phases; `Running` alone is not readiness. The CPU panel uses a rate of the idle counter, and memory has its own percentage panel. Duplicate exporter samples are reduced within the stated single-cluster scope. For multi-cluster sources, filter/group by the cluster label before combining series. Missing metrics or a zero active-Pod denominator must remain unknown/no data, not be replaced with a healthy zero. The dashboard does not itself verify an upgrade or enforce a release gate.

Save update IDs, smoke evidence, test environment/time, metric queries/windows, failures and unresolved coverage in a private results directory. Observe canary traffic and recovery criteria before increasing production traffic. A and B are useful partial checks; neither covers functionality. D exposes users before those checks.

Sources: [persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/), [Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [Terraform PVC](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs/resources/persistent_volume_claim_v1), [Prometheus functions](https://prometheus.io/docs/prometheus/latest/querying/functions/).

</details>
