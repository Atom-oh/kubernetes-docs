# Node Lifecycle Management

< [Previous: Workload Placement Strategies](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations and Maintenance](./08-operations.md) >

> **Supported Versions**: EKS Hybrid Nodes on an AWS-supported Kubernetes version; nodeadm 1.0.20 reference (SSM install/upgrade requires 1.0.19+)
> **Last Updated**: September 13, 2026

This document covers advanced nodeadm configuration, fleet installation automation, upgrade strategies, credential lifecycle management, and health monitoring for EKS Hybrid Nodes.

## 1. Advanced NodeConfig

### kubelet Tuning

In production environments, you need to fine-tune kubelet resource reservations, eviction thresholds, image garbage collection, and shutdown behavior.

#### Resource Reservation (system-reserved / kube-reserved)

These settings subtract reservations when calculating Node Allocatable. They are not a universal hard limit for every host process. The default enforceNodeAllocatable setting covers Pods; enforcing system/kube reservations additionally requires valid dedicated cgroups and a reviewed cgroup hierarchy. Measure OS, kubelet, container runtime and CNI/driver overhead before choosing values.

```yaml
kubelet:
  config:
    systemReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "10Gi"
    kubeReserved:
      cpu: "500m"
      memory: "1Gi"
      ephemeral-storage: "5Gi"
```

| Parameter | Description | Initial planning example; measure before use |
|-----------|-------------|-------------------|
| `systemReserved.cpu` | CPU for OS and system daemons | 500m – 1000m |
| `systemReserved.memory` | Memory for OS and system daemons | 1Gi – 2Gi |
| `kubeReserved.cpu` | CPU for kubelet and containerd | 500m – 1000m |
| `kubeReserved.memory` | Memory for kubelet and containerd | 1Gi – 2Gi |

#### Eviction Thresholds

The kubelet attempts node-level reclaim and, when needed, eviction under resource pressure. This is not a stability guarantee, and node-pressure eviction does not honor PodDisruptionBudgets like an API eviction request does.

```yaml
kubelet:
  config:
    evictionHard:
      memory.available: 200Mi
      nodefs.available: 10%
      imagefs.available: 15%
      nodefs.inodesFree: 5%
      imagefs.inodesFree: 5%
    evictionSoft:
      memory.available: 500Mi
      nodefs.available: 15%
    evictionSoftGracePeriod:
      memory.available: 1m30s
      nodefs.available: 2m
    evictionMaxPodGracePeriod: 60
```

> **Note**: Hard thresholds have no configured soft observation period and use immediate termination. A soft threshold must persist for evictionSoftGracePeriod; evictionMaxPodGracePeriod separately caps Pod termination grace. Soft thresholds do not prevent later hard eviction or OOM. When customizing evictionHard, specify the complete intended threshold map, including inode thresholds: omitted defaults otherwise become zero unless supported default-merge behavior is explicitly enabled.

#### maxPods Calculation

Size maxPods from CPU, memory, daemon overhead and the Cilium per-node pool. Cilium cluster-pool reserves two IPv4 addresses per CIDR, so /25, /24 and /26 provide 126, 254 and 62 usable addresses respectively. The values below are planning examples, not validated fleet recommendations or an ENI-derived limit. Existing clusterPoolIPv4MaskSize cannot simply be changed to grow allocated blocks.

```yaml
kubelet:
  config:
    maxPods: 110  # /25 has 126 usable IPv4 addresses; leave capacity for overhead
```

| Mask Size | Total IPv4 addresses | Example maxPods |
|-----------|----------|-------------------|
| /25 | 128 | 110 |
| /24 | 256 | 240 |
| /26 | 64 | 50 |

#### Image Garbage Collection

Automatically clean up unused images to manage disk space.

```yaml
kubelet:
  config:
    imageGCHighThresholdPercent: 85
    imageGCLowThresholdPercent: 80
    imageMinimumGCAge: "2m"
```

#### Shutdown Grace Period

On supported Linux hosts, graceful node shutdown relies on systemd inhibitor locks and kubelet configuration. It cannot guarantee graceful termination during power loss or forced shutdown.

```yaml
kubelet:
  config:
    shutdownGracePeriod: 60s
    shutdownGracePeriodCriticalPods: 20s
```

> **Note**: In this two-group configuration, the total 60-second budget includes 20 seconds for critical Pods, leaving a 40-second window for other Pods. This is not a promise that each Pod always receives 40 seconds; its terminationGracePeriodSeconds and actual shutdown conditions also apply.

### Advanced containerd Configuration

#### Private Registry Mirror Setup

The following snippet uses containerd 1.x (config version 2). For containerd 2.x, use config version 3 and the registry plugin path io.containerd.cri.v1.images.registry. Check the installed version and effective merged config before restarting a runtime. Registry trust and mirror path support must be verified; do not disable TLS verification.

Use trusted private registries as mirrors. The server entry below retains the upstream endpoint as fallback; it is not an air-gap configuration. Verify authentication, the proxy-project path and CA trust before relying on the mirror.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d"
```

Configure per-registry mirrors using `hosts.toml` files:

```bash
# /etc/containerd/certs.d/docker.io/hosts.toml
sudo mkdir -p /etc/containerd/certs.d/docker.io
cat <<EOF | sudo tee /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."https://harbor.internal.company.io/v2/dockerhub-proxy"]
  capabilities = ["pull", "resolve"]
  ca = "/usr/local/share/ca-certificates/registry-ca.crt"
  override_path = true
EOF
```

#### NVIDIA Runtime Class for GPU Nodes

This containerd 1.x fragment assumes the NVIDIA runtime binary/toolkit and compatible driver are already installed on a dedicated GPU node. It registers a handler; it does not install a GPU stack. Select it through an actual RuntimeClass/workload configuration when needed. For containerd 2.x use config version 3 and io.containerd.cri.v1.runtime plugin paths; do not mix the two formats. See the GPU chapter for the chosen device-plugin/DRA and toolkit prerequisites.

```yaml
containerd:
  config: |
    version = 2

    [plugins."io.containerd.grpc.v1.cri".containerd]

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]
      privileged_without_host_devices = false
      runtime_type = "io.containerd.runc.v2"

    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia.options]
      BinaryName = "/usr/bin/nvidia-container-runtime"
      SystemdCgroup = true
```

### Label and Taint Strategies

#### Automatic nodeadm Labels

nodeadm automatically assigns the following label when initializing hybrid nodes:

```
eks.amazonaws.com/compute-type=hybrid
```

This label does not need to be manually added to `--node-labels`.

#### Custom Label Strategies

Add labels by purpose or environment for fine-grained workload placement control.

```yaml
kubelet:
  flags:
    # Purpose-based labels
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training

    # Environment-based labels (production)
    # - --node-labels=environment=production,tier=compute

    # Datacenter location labels
    # - --node-labels=datacenter=dc-seoul-01,rack=rack-a3
```

#### Taint Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Automatic taints (NodeConfig) | Applied on initial Node registration; reconcile existing Node taints explicitly | Common taints for all hybrid nodes |
| Manual taints (kubectl) | Applied dynamically during operations | GPU node isolation, maintenance mode |

```yaml
# Automatic taints in NodeConfig
kubelet:
  flags:
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
```

```bash
# Manual taint addition during operations
kubectl taint nodes hybrid-gpu-001 gpu=true:NoSchedule
kubectl taint nodes hybrid-node-005 maintenance=true:NoSchedule
```

<a id="full-production-nodeconfig-example"></a>

### Complete NodeConfig Review Template

This is an unexecuted configuration template, not a production-readiness claim. The preceding kubelet/containerd fragments belong under spec. Cluster name and Region must identify the intended cluster; nodeadm obtains cluster metadata through its authorized discovery path. Deliver real activation values only through an approved private NodeConfig file. Select the containerd syntax and all resource values for the actual host.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: prod-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: <activation-code>
      activationId: <activation-id>
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 60s
      shutdownGracePeriodCriticalPods: 20s
      systemReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 10Gi
      kubeReserved:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 5Gi
      evictionHard:
        memory.available: 200Mi
        nodefs.available: 10%
        imagefs.available: 15%
        nodefs.inodesFree: 5%
        imagefs.inodesFree: 5%
      evictionSoft:
        memory.available: 500Mi
        nodefs.available: 15%
      evictionSoftGracePeriod:
        memory.available: 1m30s
        nodefs.available: 2m
      imageGCHighThresholdPercent: 85
      imageGCLowThresholdPercent: 80
      evictionMaxPodGracePeriod: 60
    flags:
    - --node-labels=node.kubernetes.io/instance-type=on-prem-gpu,workload-type=ml-training
    - --register-with-taints=eks.amazonaws.com/compute-type=hybrid:NoSchedule
  containerd:
    config: "version = 2\n[plugins.\"io.containerd.grpc.v1.cri\".registry]\n  config_path\
      \ = \"/etc/containerd/certs.d\"\n"
```

---

## 2. Fleet Installation Automation

### Ansible Playbook

Use a controlled inventory and small waves to orchestrate the [bootstrap workflow](./04-node-bootstrap.md). Pin and verify the Hybrid Nodes nodeadm artifact for each host architecture; do not send an amd64 binary to every host or redownload an unreviewed `latest` binary during a wave. For SSM installations/upgrades, AWS requires nodeadm **1.0.19 or later** because older releases contain an outdated installer signing key. This chapter references 1.0.20; check the approved OS, Kubernetes, CNI, CSI and runtime combination before execution.

#### Inventory Configuration

The addresses below are documentation placeholders. Record the actual host connection target separately from its Kubernetes Node name and UID. In particular, an SSM-backed Node name need not be a resolvable SSH hostname.

```ini
[hybrid_nodes:children]
gpu_nodes
cpu_nodes

[gpu_nodes]
gpu-host-a ansible_host=192.0.2.10 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[cpu_nodes]
cpu-host-a ansible_host=192.0.2.20 kubernetes_node_name=REPLACE_WITH_REGISTERED_NODE_NAME

[hybrid_nodes:vars]
ansible_user=REPLACE_WITH_APPROVED_OPERATOR
```

#### Automation Playbook

This playbook is a **preflight for preinstalled hosts**, not a complete installer. Deliver a root-owned private NodeConfig through the approved secret-file process first; activation codes/private keys must not be ordinary inventory/group variables or logged template output. Replace both digest placeholders with independently verified artifacts for the selected release. It does not run install/init or start a stopped service while claiming to verify health.

```yaml
- name: Review preinstalled Hybrid Nodes before an approved bootstrap
  hosts: hybrid_nodes
  gather_facts: true
  become: true
  serial: 1
  any_errors_fatal: true
  vars:
    architecture_map:
      x86_64: amd64
      aarch64: arm64
    approved_nodeadm_sha256:
      amd64: REPLACE_WITH_REVIEWED_AMD64_SHA256
      arm64: REPLACE_WITH_REVIEWED_ARM64_SHA256
    nodeconfig_path: /etc/eks/nodeconfig.yaml
  tasks:
  - name: Require a reviewed architecture and binary digest
    ansible.builtin.assert:
      that:
      - ansible_facts.architecture in architecture_map
      - approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]] is match('^[a-f0-9]{64}$')
  - name: Inspect the existing nodeadm artifact
    ansible.builtin.stat:
      path: /usr/local/bin/nodeadm
      checksum_algorithm: sha256
      get_checksum: true
    register: nodeadm_artifact
  - name: Match the approved artifact
    ansible.builtin.assert:
      that:
      - nodeadm_artifact.stat.exists
      - nodeadm_artifact.stat.executable
      - nodeadm_artifact.stat.checksum == approved_nodeadm_sha256[architecture_map[ansible_facts.architecture]]
  - name: Validate the privately delivered NodeConfig
    ansible.builtin.command:
      argv:
      - /usr/local/bin/nodeadm
      - config
      - check
      - -c
      - file://{{ nodeconfig_path }}
    changed_when: false
    no_log: true
```

A kubelet file alone is not evidence of a completed install. After preflight, invoke the bootstrap chapter's complete install/init procedure with its per-host operation record and identity checks. Stop the wave on failure; retain an unknown/partial state for recovery instead of blindly rerunning init. `changed_when: false` controls Ansible reporting, not the behavior of the command being executed.

#### Role-Based Variables (GPU Nodes vs CPU Nodes)

| Host group | Explicit per-host configuration to review |
| --- | --- |
| CPU | Selected OS/architecture, runtime format, measured reservations, workload labels and taints |
| GPU | CPU prerequisites plus actual driver/toolkit, selected device-plugin or DRA path, runtime handler/RuntimeClass and GPU validation |

Select the template explicitly for each host; `group_names[0]` is not a reliable role selector. Declaring `nvidia.com/gpu.present=true` does not install a driver or establish an allocatable GPU. See [GPU integration](./05-gpu-integration.md).

### Fleet Verification Script

Save a separately approved `expected-nodes.json` covering **all expected Hybrid Nodes** in the cluster. Do not derive this expected set from the same API response being tested: that would hide missing nodes. Replacement changes the identity record and requires deliberate reconciliation.

```json
[
  {"name": "REPLACE_WITH_REGISTERED_NODE_NAME", "uid": "REPLACE_WITH_APPROVED_NODE_UID"}
]
```

Save the following as `check-fleet.sh`. It requires Bash, kubectl and jq. Set `KUBE_CONTEXT` on an operator workstation; the in-cluster observer below uses its ServiceAccount. A denied/failed API call, an empty cohort, a wrong UID, or a missing/Unknown condition returns nonzero.

```bash
#!/usr/bin/env bash
# Read-only Node inventory/condition snapshot; no workload or host mutations.
set -euo pipefail
EXPECTED_FILE="${1:?Usage: check-fleet.sh expected-nodes.json}"
umask 077
WORK_DIR=$(mktemp -d)
trap 'rm -rf -- "$WORK_DIR"' EXIT
KUBECTL=(kubectl --cache-dir "$WORK_DIR/kube-cache")
if [ -n "${KUBE_CONTEXT:-}" ]; then KUBECTL+=(--context "$KUBE_CONTEXT"); fi
"${KUBECTL[@]}" get nodes -l eks.amazonaws.com/compute-type=hybrid -o json > "$WORK_DIR/nodes.json"
jq -e --slurpfile expected "$EXPECTED_FILE" '
  def required($kind; $status):
    [.status.conditions[]? | select(.type == $kind)] as $c |
    ($c | length) == 1 and $c[0].status == $status;
  $expected[0] as $want |
  ($expected | length) == 1 and ($want | type) == "array" and
  ($want | length) > 0 and
  ($want | length) == ($want | map(.name) | unique | length) and
  all($want[]; (.name | type) == "string" and (.name | length) > 0 and
               (.uid | type) == "string" and (.uid | length) > 0) and
  (.items | type) == "array" and
  (.items | map(.metadata.name) | sort) == ($want | map(.name) | sort) and
  all(.items[];
    . as $node |
    any($want[]; .name == $node.metadata.name and .uid == $node.metadata.uid) and
    .metadata.deletionTimestamp == null and
    .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
    required("Ready"; "True") and
    required("MemoryPressure"; "False") and
    required("DiskPressure"; "False") and
    required("PIDPressure"; "False"))
' "$WORK_DIR/nodes.json" > /dev/null
printf 'Expected Node identities and conditions match this snapshot.\n'
# CNI readiness, DNS, network paths, storage, applications and freshness need
# separate checks; Node Ready is not an end-to-end health guarantee.
```

This is a Node inventory/condition snapshot. `Ready=True` does not prove current CNI, DNS, storage or application health. Check the selected CNI's actual DaemonSet/Pods, connectivity between the relevant sites, DNS resolution, storage operations and workload endpoints separately; do not count `NotReady` as Ready with a substring match.

## 3. Node Upgrade Strategies

### Version Skew Policy

The 1.31 table below illustrates the version-skew arithmetic; it is not a recommendation to deploy those historical node versions today. Select an EKS-supported target and compatible OS, CNI, CSI and runtime from current AWS documentation.

Kubernetes maintains a strict version compatibility policy between kubelet and the API server.

| kubelet Version | API Server Version | Compatible |
|----------------|-------------------|------------|
| 1.31 | 1.31 | Yes (same version) |
| 1.30 | 1.31 | Yes (n-1) |
| 1.29 | 1.31 | Yes (n-2) |
| 1.28 | 1.31 | Yes (n-3) |
| 1.27 | 1.31 | No (n-4, unsupported) |
| 1.32 | 1.31 | No (kubelet > API server, unsupported) |

> **Upgrade order**: First bring lagging nodes up to the current control-plane minor version. Before moving nodes to the next minor version, upgrade the control plane. A kubelet must not be newer than the API server; the supported skew is not a recommendation to keep old nodes indefinitely.

### Pre-Upgrade Checklist

Before each wave, approve the target major.minor and full artifact versions/checksums, check control-plane skew and OS/CNI/CSI/runtime compatibility, and confirm enough spare capacity for the evicted workloads. Inspect Pod requests/placement, PDB allowed disruptions, local PV/emptyDir ownership, backup/recovery and observability. `kubectl top` is optional measured usage, not proof that every Pod can reschedule.

Inventory the Node name/UID, actual host connection, credential provider and original `.spec.unschedulable` state. `nodeadm upgrade` preserves the Node name and cannot change the credential provider. It normally selects the latest artifacts for the requested minor; a fixed minor alone is not an immutable artifact plan. Use the approved manifest/private-artifact procedure when reproducibility is required.

### Rolling Upgrade

Process **one explicitly selected node at a time** and stop on the first failure. The examples below are an unexecuted operator workflow, not a fleet controller with a tested availability guarantee. Run the first and last blocks from the approved cluster-admin workstation, in the same shell or with the recorded directory/inputs restored. The operator needs Node, Lease, Pod/PDB observation and cordon/drain permissions.

Save the private record path; these commands cordon and drain the selected Node. A blocked PDB or local emptyDir requires an explicit workload/data decision. Do not add force, disable-eviction or delete-emptydir-data simply to make a failed drain succeed.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the actual Kubernetes Node name}"
: "${EXPECTED_UID:?Set the approved Node UID}"
UPGRADE_RECORD_DIR=$(mktemp -d "$PWD/hybrid-upgrade.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/node-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null
' "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$UPGRADE_RECORD_DIR/lease-before.private.json"
jq -e --arg uid "$EXPECTED_UID" '
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | type) == "string"
' "$UPGRADE_RECORD_DIR/lease-before.private.json" > /dev/null
printf 'Private upgrade record: %s\n' "$UPGRADE_RECORD_DIR"
kubectl --context "$KUBE_CONTEXT" cordon "$NODE"
kubectl --context "$KUBE_CONTEXT" drain "$NODE" --ignore-daemonsets --timeout=10m
```

Only after drain succeeds, connect to the **mapped physical/virtual host**, verify its recorded identity and the reviewed nodeadm binary, and run the disruptive upgrade there. The NodeConfig must retain the existing credential provider. Do not skip node/pod/init validation as routine operation.

```bash
set -euo pipefail
: "${TARGET_MINOR:?Set the approved EKS-supported major.minor target}"
sudo /usr/local/bin/nodeadm upgrade "$TARGET_MINOR" \
  -c file:///etc/eks/nodeconfig.yaml --timeout 20m
```

An upgrade command error or lost session is an unknown/failed operation, even if Kubernetes still shows an old Ready condition. Keep the Node cordoned and investigate. After a confirmed successful host operation, observe it from the workstation; use the full expected kubelet version from the artifact plan, including any build suffix.

```bash
set -euo pipefail
umask 077
: "${KUBE_CONTEXT:?Set the approved host cluster context}"
: "${NODE:?Set the recorded Node name}"
: "${EXPECTED_UID:?Set the recorded Node UID}"
: "${EXPECTED_KUBELET_VERSION:?Set the full version from the approved artifact plan}"
: "${UPGRADE_RECORD_DIR:?Use the private record directory from the pre-upgrade step}"
jq -e --arg uid "$EXPECTED_UID" --arg node "$NODE" \
  '.metadata.uid == $uid and .metadata.name == $node' \
  "$UPGRADE_RECORD_DIR/node-before.private.json" > /dev/null
POSTCHECK_DIR=$(mktemp -d "$UPGRADE_RECORD_DIR/check.XXXXXX")
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o json \
  > "$POSTCHECK_DIR/node-after.private.json"
jq -e --arg uid "$EXPECTED_UID" --arg version "$EXPECTED_KUBELET_VERSION" '
  [.status.conditions[]? | select(.type == "Ready")] as $ready |
  .metadata.uid == $uid and
  .metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid" and
  .metadata.deletionTimestamp == null and
  .status.nodeInfo.kubeletVersion == $version and
  ($ready | length) == 1 and $ready[0].status == "True"
' "$POSTCHECK_DIR/node-after.private.json" > /dev/null
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o json \
  > "$POSTCHECK_DIR/lease-after.private.json"
jq -e --arg uid "$EXPECTED_UID" \
  --slurpfile before "$UPGRADE_RECORD_DIR/lease-before.private.json" '
  def epoch: sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601;
  any(.metadata.ownerReferences[]?; .kind == "Node" and .uid == $uid) and
  (.spec.renewTime | epoch) > ($before[0].spec.renewTime | epoch)
' "$POSTCHECK_DIR/lease-after.private.json" > /dev/null
printf 'Node identity, target kubelet version, Ready and a newer Lease observed.\n'
# Workload/CNI/DNS/storage checks and the prior scheduling intent remain separate.
# This check never uncordons the node.
```

This requires a Lease renewal later than the saved snapshot, in addition to the target version and Node identity. It is still not an application acceptance test. Verify the CNI, DNS, volumes, driver/runtime and workload recovery. Only then explicitly uncordon a Node that was schedulable before maintenance. Do not automatically uncordon on an EXIT trap or restore scheduling for a Node that was already intentionally cordoned. Keep the evidence and repeat for the next approved Node.

### Canary Upgrade

Choose a representative canary by OS/architecture, runtime, credential provider and workload; do not select the first name returned by the API. Apply the same one-node workflow, then observe application error/latency, storage/network health and actual versions for the service's agreed period. A fixed sleep or Node Ready alone is not a pass. Expand to further small waves only after these checks; retain the old hosts during a cutover until acceptance succeeds.

<a id="rollback-procedure"></a>

### Recovery and Rollback Boundaries

AWS recommends replacement hosts and a controlled cutover when spare capacity is available. Keep the old hosts available until application, storage, networking and target-version checks pass. In-place `nodeadm upgrade` is disruptive and is not a general transactional downgrade mechanism.

On failure, keep the affected node cordoned, stop the remaining wave, retain diagnostics and inspect the installed artifacts/credentials. Recover on an approved image/version compatible with the current control plane. Do not automatically uncordon a node merely because an old `Ready=True` condition remains visible; verify the expected node identity and actual kubelet version as well as workload readiness.

Do not recursively delete `/var/lib/kubelet` or `/etc/kubernetes` as a generic rollback step. Pod volume and subpath mounts can expose mounted host or application data. Since nodeadm 1.0.9, even forced uninstall deliberately preserves `/var/lib/kubelet`; any exceptional cleanup requires an explicit mount/data-retention review. Uninstall does not drain or delete the Kubernetes Node object and does not completely remove the CNI. For SSM, it also deregisters the managed instance. Rebuilding therefore requires the complete install/bootstrap and identity reconciliation process, not a blind uninstall/reinstall loop.

---

## 4. Credential Lifecycle

<a id="ssm-hybrid-activation-renewal"></a>

### SSM Hybrid Activation Expiration

An activation's expiration limits **new registrations**. Nodes already registered remain Systems Manager managed nodes until explicitly deregistered. Do not uninstall or re-register healthy nodes just because their original activation has expired. Registration, the agent's rotating credentials, IAM permissions and connectivity are separate lifecycles.

Create a new activation only when additional hosts need registration or an approved recovery requires re-registration. Use the actual Hybrid Nodes IAM role configured for SSM; do not substitute a generic Run Command role. Review the role trust/permissions, account, Region and exact number of new nodes before this AWS resource-creation command. The activation code is a password-like secret, so store the response in a private file and deliver it through the approved NodeConfig secret-file process.

```bash
set -euo pipefail
umask 077
: "${HYBRID_NODE_ROLE_NAME:?Set the reviewed Hybrid Nodes IAM role name}"
: "${AWS_REGION:?Set the cluster Region}"
: "${NEW_NODE_COUNT:?Set the approved registration count}"
set -C  # Refuse to overwrite an existing private response file.
aws ssm create-activation   --iam-role "$HYBRID_NODE_ROLE_NAME"   --registration-limit "$NEW_NODE_COUNT"   --region "$AWS_REGION"   --output json > activation.private.json
```

An AWS CLI failure leaves an untrusted/possibly partial response file; stop and inspect it privately before retrying. Do not print the activation code or commit this file. Set an explicit approved expiration when the API default registration window is unsuitable; the maximum is 30 days. The count is a registration limit, not an authorization boundary for which hosts may use a leaked activation.

`nodeadm uninstall` deregisters an SSM-backed host and removes installed components. A subsequent `init` alone does not replace `install`. For intentional recovery, first review drain/data retention and identity changes, then use the complete [bootstrap workflow](./04-node-bootstrap.md). Existing node names/UIDs and SSM managed-instance IDs must be reconciled with the inventory; do not silently reuse an old success record.

### IAM Roles Anywhere Certificate Renewal

Renew the node's **host authentication certificate** through its existing PKI before expiration. This is separate from kubelet client/server certificates and the EKS control-plane CA. The certificate subject, configured nodeName, role-session conditions, profile, role and trust anchor must remain compatible; renaming the CN is not a harmless file rotation.

#### Certificate Expiration Monitoring

Run this check against the configured certificatePath, not an assumed path. A missing, unreadable, invalid or expiring-within-30-days certificate fails. The 30-day warning is an example operational threshold.

```bash
#!/usr/bin/env bash
set -euo pipefail
CERT_PATH="${1:?Usage: check-cert-expiry.sh certificate.pem}"
test -r "$CERT_PATH" || { echo 'Certificate missing or unreadable' >&2; exit 1; }
openssl x509 -in "$CERT_PATH" -checkend 2592000 -noout
# This is an expiration check only, not chain/key/CN/trust/IAM validation.
```

<a id="automatic-renewal-script"></a>

#### Certificate Renewal Workflow

Use the organization's approved CA client and authenticated enrollment policy; there is no generic unauthenticated `/sign` endpoint. Keep the existing key protected when reusing it, or follow the approved key-rotation process. Submit a CSR with the intended identity and store the issued candidate separately from the active certificate.

The following **local checks only** test remaining lifetime, chain validation against separately approved roots and public-key correspondence. Supply intermediates with `INTERMEDIATE_CHAIN` when needed. They do not check every PKI/IAM policy, revocation, nodeName/CN or live authentication condition.

```bash
set -euo pipefail
umask 077
: "${CANDIDATE_CERT:?Path to the issued candidate leaf certificate}"
: "${PRIVATE_KEY:?Path to its existing protected private key}"
: "${APPROVED_CA_PEM:?Path to the separately approved trust roots}"
CERT_CHECK_DIR=$(mktemp -d)
trap 'rm -rf -- "$CERT_CHECK_DIR"' EXIT
openssl x509 -in "$CANDIDATE_CERT" -checkend 2592000 -noout
VERIFY=(openssl verify -CAfile "$APPROVED_CA_PEM")
if [ -n "${INTERMEDIATE_CHAIN:-}" ]; then VERIFY+=(-untrusted "$INTERMEDIATE_CHAIN"); fi
"${VERIFY[@]}" "$CANDIDATE_CERT"
openssl x509 -in "$CANDIDATE_CERT" -pubkey -noout > "$CERT_CHECK_DIR/cert.pub"
openssl pkey -in "$PRIVATE_KEY" -pubout > "$CERT_CHECK_DIR/key.pub"
cmp "$CERT_CHECK_DIR/cert.pub" "$CERT_CHECK_DIR/key.pub"
```

Review the subject/SANs, usages, CA policy, revocation and exact nodeName/role conditions before release. Back up the current certificate privately, then have the approved certificate manager replace the validated certificate atomically on the same filesystem while preserving owner/mode. If rotating both key and certificate, coordinate the pair so a consumer cannot see mismatched files.

Inspect the actual credential-helper mode configured by nodeadm (credential process versus credential-file updater) and validate the next credential refresh through the approved private diagnostic path. Restarting kubelet neither renews the X.509 certificate nor proves that the helper accepted it. Schedule automatic renewal only after testing the issuer, candidate rejection, atomic replacement, refresh and rollback behavior for that environment; no such production renewal was executed for this chapter.

#### Trust Anchor Update

A leaf certificate renewed under the same trusted CA does not normally require replacing the trust anchor. A CA rollover affects every dependent host/profile/role. Plan overlap/migration with the PKI and IAM owners, inspect the source type and dependent nodes, and retain a recovery path before changing trust.

For a **CERTIFICATE_BUNDLE** source, use JSON file input so PEM newlines remain intact. The sourceData union contains only x509CertificateData here. An AWS_ACM_PCA anchor uses acmPcaArn and a different review. This example creates a private request file and then performs an AWS update; do not execute it as part of ordinary certificate-expiry monitoring.

```bash
set -euo pipefail
umask 077
: "${APPROVED_CA_PEM:?Path to the reviewed CA certificate bundle}"
: "${TRUST_ANCHOR_ID:?Set the reviewed existing trust anchor ID}"
: "${AWS_REGION:?Set the trust anchor Region}"
set -C
jq -n --rawfile bundle "$APPROVED_CA_PEM" \
  '{sourceType:"CERTIFICATE_BUNDLE", sourceData:{x509CertificateData:$bundle}}' \
  > trust-anchor-source.private.json
# AWS mutation: run only after the CA rollover and dependent-node review.
aws rolesanywhere update-trust-anchor --trust-anchor-id "$TRUST_ANCHOR_ID" \
  --region "$AWS_REGION" --source file://trust-anchor-source.private.json \
  --output json > trust-anchor-update.private.json
```

Read back and verify the intended anchor and test new credential issuance for a canary before completing the rollover. An API error is unknown/failed, not proof that the old trust remains effective. Never log issued credentials or assume replacing one anchor automatically preserves every old certificate's access.

## 5. Health Monitoring Automation

### Automated Health Check CronJob

This observer runs the Node snapshot check from section2. It does **not** execute nodeadm on the hosts or validate their AWS credentials. Use a reviewed image containing Bash, kubectl and jq, compatible with the cluster and able to run as UID10001. The placeholder image must be replaced before deployment; no image or cluster execution was validated here. The monitoring namespace must already exist.

Create the ConfigMap manifest from the saved check-fleet.sh and approved expected-nodes.json. Then review/apply it together with the ServiceAccount/RBAC/CronJob below. The ClusterRole can list all Nodes; the label selector is a query filter, not an authorization boundary. Review namespace owners who can change the ConfigMap or run Pods with this ServiceAccount.

```bash
: "${KUBE_CONTEXT:?Set the approved cluster context}"
kubectl --context "$KUBE_CONTEXT" -n monitoring create configmap hybrid-node-check \
  --from-file=check-fleet.sh --from-file=expected-nodes.json \
  --dry-run=client -o yaml > hybrid-node-check.yaml
# Review this manifest and the observer/RBAC manifest before applying either.
```
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: hybrid-node-observer
rules:
- apiGroups:
  - ''
  resources:
  - nodes
  verbs:
  - get
  - list
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: hybrid-node-observer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: hybrid-node-observer
subjects:
- kind: ServiceAccount
  name: hybrid-node-observer
  namespace: monitoring
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hybrid-node-observer
  namespace: monitoring
spec:
  schedule: '*/30 * * * *'
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 120
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      backoffLimit: 0
      activeDeadlineSeconds: 120
      ttlSecondsAfterFinished: 1800
      template:
        spec:
          serviceAccountName: hybrid-node-observer
          restartPolicy: Never
          securityContext:
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            fsGroup: 10001
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: observer
            image: example.invalid/hybrid-observer:replace-with-reviewed-build
            command:
            - /bin/bash
            - /config/check-fleet.sh
            - /config/expected-nodes.json
            env:
            - name: TMPDIR
              value: /work
            securityContext:
              allowPrivilegeEscalation: false
              readOnlyRootFilesystem: true
              capabilities:
                drop:
                - ALL
            resources:
              requests:
                cpu: 100m
                memory: 64Mi
              limits:
                cpu: 500m
                memory: 128Mi
            volumeMounts:
            - name: config
              mountPath: /config
              readOnly: true
            - name: work
              mountPath: /work
          volumes:
          - name: config
            configMap:
              name: hybrid-node-check
              defaultMode: 292
          - name: work
            emptyDir:
              sizeLimit: 64Mi
```

Alert on a failed Job **and missed executions/no recent success**. A 30-minute polling interval cannot provide immediate failure detection. Send notifications through the monitoring system's protected integration; do not embed Slack webhook bearer URLs in the Pod environment or treat a failed notification as a successful health check.

### kubelet/containerd Status Monitoring (Node Level)

The following root-owned script observes local service state and the root filesystem without restarting services. Separate mounted kubelet/containerd/image filesystems require additional checks; a root-disk percentage alone is insufficient. An unavailable command or malformed measurement must not be reported as healthy.

```bash
#!/usr/bin/env bash
# Observe local services/filesystem; do not restart anything automatically.
set -euo pipefail
failed=0
for service in kubelet containerd; do
  if ! systemctl is-active --quiet "$service"; then
    printf '%s is not active\n' "$service" >&2
    failed=1
  fi
done
usage=$(df --output=pcent / | tail -n 1 | tr -d ' %')
case "$usage" in ''|*[!0-9]*) echo 'Unknown filesystem usage' >&2; exit 1;; esac
if [ "$usage" -ge 90 ]; then
  printf 'Root filesystem usage: %s%%\n' "$usage" >&2
  failed=1
fi
exit "$failed"
```

Install the script through the reviewed host-management process as `/usr/local/bin/node-health-check.sh`, executable and not writable by untrusted users. The timer/unit are configuration examples; journal and failed-unit monitoring must be connected separately. `PrivateTmp` does not make credentials safe to log.

```ini
[Unit]
Description=Periodic Hybrid Node local observation

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
```
```ini
[Unit]
Description=Observe Hybrid Node local services and root filesystem

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/node-health-check.sh
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
```

For a specific network/credential problem, an operator can separately run `nodeadm debug -c file:///etc/eks/nodeconfig.yaml` with root privileges. It contacts AWS and the cluster and may expose diagnostic context; retain output privately. Do not run it silently on every timer tick, discard its errors, or automatically restart kubelet/containerd without an incident-specific decision.

## Verification and Sources

Local validation covers example parsing, mocked Node/API failure cases and synthetic certificate checks. It does not establish a completed fleet install, host upgrade, credential rollover, Kubernetes admission, CNI/DNS/storage test or production SLO.

- [AWS Hybrid Nodes nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS Hybrid Nodes upgrades](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-upgrade.html)
- [SSM registration and activation lifetime](https://docs.aws.amazon.com/systems-manager/latest/userguide/hybrid-activation-managed-nodes.html)
- [IAM Roles Anywhere credential configuration](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [UpdateTrustAnchor input](https://docs.aws.amazon.com/botocore/latest/reference/services/rolesanywhere/client/update_trust_anchor.html)
- [Kubernetes version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Node pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Node Allocatable](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Graceful node shutdown](https://kubernetes.io/docs/concepts/cluster-administration/node-shutdown/)
- [containerd configuration](https://github.com/containerd/containerd/blob/main/docs/cri/config.md)
- [Cilium 1.20.1 cluster-pool allocator](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst)

---

< [Previous: Workload Placement Strategies](./06-workload-placement.md) | [Table of Contents](./README.md) | [Next: Operations and Maintenance](./08-operations.md) >
