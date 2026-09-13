# Node Bootstrap

< [Previous: Restricted-internet Setup](./03-airgap-setup.md) | [Table of Contents](./README.md) | [Next: GPU Integration](./05-gpu-integration.md) >

> **Supported Versions**: EKS Hybrid Nodes; nodeadm v1.0.20 source checked. Select a supported OS, Kubernetes and CNI combination for the target cluster.
> **Last Updated**: September 12, 2026

This chapter connects a prepared on-premises host to EKS. It separates software installation, AWS identity, initialization and verified workload readiness. Examples require an identified cluster/host and operator approval for the changes described. Local validation does not establish that a production network, OS image, PKI or workload has been tested.

## Bootstrap workflow

1. Prepare the supported OS/runtime, unique host identity, time synchronization, routes, DNS and firewall rules in [Prerequisites](./01-prerequisites.md) and [Network Configuration](./02-network-configuration.md).
2. Prepare a **Hybrid Nodes IAM role**, the SSM or IAM Roles Anywhere provider and a cluster access entry of type `HYBRID_LINUX`. A generic SSM management role alone is insufficient.
3. Verify the Hybrid nodeadm release, then install dependencies on the host or in a controlled OS image build.
4. Deliver a protected, per-node NodeConfig using exactly one credential provider. Configure proxy and registry trust if required.
5. Run `nodeadm config check`, then `nodeadm init` on the identified host.
6. Configure the supported Hybrid CNI and required add-ons. A registered Node can still be `NotReady`.
7. Verify the exact Node identity, Ready condition, CNI/DNS, credential refresh and a bounded workload before accepting it into service.

## nodeadm and dependency installation

Hybrid nodeadm comes from **`aws/eks-hybrid`**, not the EC2 `amazon-eks-ami` installer. New SSM installs/upgrades require **nodeadm 1.0.19 or later** because earlier versions contain an outdated SSM signing key. This review used the released **v1.0.20 source**.

Download the approved release with HTTPS verification and compare its digest with an independently approved record before executing it as root. Do not blindly replace `/usr/local/bin/nodeadm` with a mutable `latest` download. The [restricted-internet chapter](./03-airgap-setup.md) covers image preparation and the inspected release's private-manifest flags. The audit did not fetch or execute a nodeadm binary after the official artifact host failed TLS hostname verification in this environment.

```bash
# Target host/image builder: installs software. Choose exactly one provider.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${CREDENTIAL_PROVIDER:?ssm or iam-ra}" "${REGION:?}"
: "${CONTAINERD_SOURCE:?distro, docker or none for this OS}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
case "$CONTAINERD_SOURCE" in distro|docker|none) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" \
  --containerd-source "$CONTAINERD_SOURCE" --region "$REGION" --timeout 20m
```

Prefer the control plane's current minor version for a new node. Supported kubelet skew is a compatibility allowance, not a reason to install an old unsupported EKS version. A kubelet must not be newer than the API server; check EKS and CNI support as well as the upstream skew policy.

`distro` is not supported on RHEL; use the documented Docker package source or a preinstalled compatible runtime with `none`. `docker` is not supported on AL2023. `none` skips containerd installation. Private mode also skips OS packages: it does not supply missing runtime dependencies.

| Component | Documented installed location |
|---|---|
| kubelet | `/usr/bin/kubelet` |
| kubectl | `/usr/local/bin/kubectl` |
| ECR credential provider | `/etc/eks/image-credential-provider/ecr-credential-provider` |
| AWS IAM authenticator / signing helper | `/usr/local/bin/aws-iam-authenticator` / `/usr/local/bin/aws_signing_helper` |
| SSM setup CLI | `/opt/ssm/ssm-setup-cli` |
| SSM Agent | Ubuntu snap: `/snap/amazon-ssm-agent/current/amazon-ssm-agent`; AL2023/RHEL: `/usr/bin/amazon-ssm-agent` |
| containerd | Ubuntu/AL2023: `/usr/bin/containerd`; RHEL documentation uses `/bin/containerd` |
| nodeadm tracker | `/opt/nodeadm/tracker` |

`nodeadm install` installs and configures the SSM agent through its signed setup CLI; **SSM registration occurs during `init`**. It is not a hand-written sequence of `dpkg` plus a separate, incompatible nodeadm installer.

## NodeConfig and credentials

### SSM

Provide the cluster name/Region and a valid activation code/ID for the prepared Hybrid role:

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_ACTIVATION_CODE
      activationId: REPLACE_WITH_ACTIVATION_ID
  kubelet:
    config:
      maxPods: 110
      shutdownGracePeriod: 30s
      shutdownGracePeriodCriticalPods: 10s
    flags:
      - --node-labels=workload.example.com/location=onprem
```

The protected config is an input template, not a secret to commit. Use root ownership and mode `0600`; deliver values without publishing them in logs or shell history. Cluster discovery obtains the API endpoint and CA through the Hybrid role's EKS permissions. A raw PEM block in a base64-encoded CA field is not interchangeable with the API representation.

The `maxPods` and shutdown periods are planning examples, not capacity guarantees. Check CNI allocation, reserved IPs, resources and workload termination requirements. Optional `NoSchedule` taints require matching workload/CNI tolerations; do not add a default taint that silently prevents required agents or applications from scheduling.

Create activations only through the credential owner, using the prepared Hybrid role, the correct Region, an explicit expiry and a bounded registration limit. Capture the response in a private file instead of printing the activation code:

```bash
# AWS write: owner-approved activation for one new host.
set -euo pipefail
umask 077
: "${REGION:?}" "${HYBRID_ROLE_NAME:?Prepared Hybrid Nodes IAM role name}"
: "${ACTIVATION_EXPIRY:?Future UTC timestamp within SSM service limits}"
test ! -e activation.json
aws ssm create-activation --region "$REGION" \
  --iam-role "$HYBRID_ROLE_NAME" --registration-limit 1 \
  --expiration-date "$ACTIVATION_EXPIRY" \
  --default-instance-name eks-hybrid-node > activation.json
```

A failed/unknown request is not a signal to retry creation blindly; reconcile it with the credential owner. SSM uses the resulting `mi-*` managed-instance ID as the Node name. Ordinary reboots reuse SSM registration and refreshed temporary credentials. Re-registration requires a still-valid activation with remaining registration capacity; its expiry matters as well as the limit.

### IAM Roles Anywhere

Use the trust anchor, enabled profile, Hybrid role and per-node certificate/key prepared in [Prerequisites](./01-prerequisites.md). Do not create another trust anchor/profile every time this chapter is run.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      nodeName: hybrid-node-001
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_ID
      roleArn: arn:aws:iam::111122223333:role/EKSHybridNodeRole
      certificatePath: /etc/iam/pki/server.pem
      privateKeyPath: /etc/iam/pki/server.key
```

The paths are examples, not an instruction to reuse one certificate across machines. Bind `nodeName` to the certificate attribute used by the role trust policy; the common CN condition requires them to match. The name must meet node naming rules and be at most 64 characters. Enable **`acceptRoleSessionName: true`** on the profile.

Session duration is not increased merely by setting the role maximum to 12 hours. The effective requested/profile duration must fit within the role's `MaxSessionDuration`; equality is permitted. Choose duration according to security/availability requirements and verify credential renewal. Static IAM user access keys are not a third supported Hybrid nodeadm credential provider.

## Private registry trust

For an internal registry, verify the CA fingerprint and certificate hostname through the registry owner. Prefer registry-scoped trust where appropriate. Do not install an arbitrary presented certificate globally or disable hostname verification.

An example `hosts.toml` for the approved registry is:

```toml
# /etc/containerd/certs.d/registry.internal.example.com/hosts.toml
server = "https://registry.internal.example.com"

[host."https://registry.internal.example.com"]
  capabilities = ["pull", "resolve"]
  ca = "/etc/containerd/certs.d/registry.internal.example.com/ca.crt"
```

The matching reviewed CA file must exist on each node. For containerd 1.x, the registry `config_path` belongs under `plugins."io.containerd.grpc.v1.cri".registry`; for containerd 2.x/config version 3, it belongs under `plugins."io.containerd.cri.v1.images".registry`. Check nodeadm's generated `/etc/containerd/config.toml` and use the section for the installed runtime. Do not combine deprecated inline registry `configs/auth` with a `config_path` recipe or put registry passwords in NodeConfig.

If the organization instead needs system-wide CA trust, Ubuntu uses `/usr/local/share/ca-certificates/` plus `update-ca-certificates`; RHEL/AL2023 use `/etc/pki/ca-trust/source/anchors/` plus `update-ca-trust extract`. Do not reference the Ubuntu path from an RHEL example. Ordinary ECR certificates use public trust; the OS still needs a working CA bundle. Registry trust and registry authentication are separate.

## Initialize and verify

```bash
# Identified target host; init changes local configuration and joins EKS.
set -euo pipefail
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml
```

On a private-manifest installation, pass the approved `--manifest-override` and `--private-mode` to `init` as described in [Restricted-internet Setup](./03-airgap-setup.md). Proxy settings must reach the actual nodeadm/daemon processes. `config check` is a local configuration check, not an end-to-end join test.

From the **cluster administrator's** workstation, verify the intended kubeconfig context and exact expected Node name (SSM `mi-*`, or the approved IAM Roles Anywhere name):

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${EXPECTED_NODE_NAME:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o json > node-registration.json
jq -e '.metadata.labels["eks.amazonaws.com/compute-type"] == "hybrid"
  and (.metadata.uid | type == "string" and length > 0)' node-registration.json
expected_uid=$(jq -er '.metadata.uid' node-registration.json)
# After CNI and required add-ons are ready:
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" wait \
  --for=condition=Ready "node/$EXPECTED_NODE_NAME" --timeout=5m
observed_uid=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get node "$EXPECTED_NODE_NAME" -o jsonpath='{.metadata.uid}')
test "$observed_uid" = "$expected_uid"
```

Record the Node UID and compare the provider/addresses with the identified physical/virtual host. A Ready condition is necessary, but also verify DNS, image pulls, connectivity, credential refresh and the required workload. The earlier `v1.31.0` output was illustrative historical output, not a fresh registration measurement.

## systemd automation for a preinstalled host

Prepare software with `nodeadm install` during the controlled build/install phase. The following automation runs **initialization only** and stores a record bound to the machine ID, approved nodeadm binary, NodeConfig and optional private manifest. It refuses changed or partially initialized state instead of silently repeating registration. Do not clone registration state, machine IDs, keys or this state directory into other nodes.

Example root-owned `/etc/eks/bootstrap.env` (mode `0600`):

```text
NODECONFIG_PATH=/etc/eks/nodeconfig.yaml
APPROVED_NODEADM_SHA256=REPLACE_WITH_APPROVED_64_HEX_DIGEST
# Only for the reviewed private-manifest path:
# LOCAL_MANIFEST=/etc/eks/manifest.json
```

Save the following root-owned script at `/usr/local/bin/eks-hybrid-bootstrap.sh`. The protected parent directories and files must be managed by the host owner; this is not a hostile-root defense.

```bash
#!/usr/bin/env bash
# Initialize one preinstalled, uniquely identified host. Run as root.
set -euo pipefail
umask 077
[[ "$EUID" -eq 0 ]]
: "${NODECONFIG_PATH:?Absolute per-node config path}"
: "${APPROVED_NODEADM_SHA256:?Hash from the approved binary record}"
[[ "$NODECONFIG_PATH" = /* ]]
[[ "$APPROVED_NODEADM_SHA256" =~ ^[0-9a-f]{64}$ ]]
NODEADM=/usr/local/bin/nodeadm
STATE=/var/lib/eks-hybrid-bootstrap

private_file() {
  local path=$1 owner mode
  [[ -f "$path" && ! -L "$path" ]]
  owner=$(stat -c '%u' "$path")
  mode=$(stat -c '%a' "$path")
  [[ "$owner" == 0 && "$mode" == 600 ]]
}

private_file "$NODECONFIG_PATH"
test -s /etc/machine-id
test -s /opt/nodeadm/tracker
test -x "$NODEADM"
actual=$(sha256sum "$NODEADM")
[[ "${actual%% *}" == "$APPROVED_NODEADM_SHA256" ]]
if [[ -e /var/lib/eks/.nodeadm-installed || -e /var/lib/eks/.nodeadm-initialized ]]; then
  echo 'Legacy markers found: review existing installation and migrate state manually.' >&2
  exit 1
fi
[[ ! -L "$STATE" ]]
mkdir -p -m 700 "$STATE"
[[ "$(stat -c '%u:%a' "$STATE")" == 0:700 ]]
exec 9>"$STATE/lock"
flock -n 9

args=(--config-source "file://$NODECONFIG_PATH")
fingerprint_inputs=(/etc/machine-id "$NODEADM" "$NODECONFIG_PATH")
if [[ -n "${LOCAL_MANIFEST:-}" ]]; then
  [[ "$LOCAL_MANIFEST" = /* ]]
  private_file "$LOCAL_MANIFEST"
  fingerprint_inputs+=("$LOCAL_MANIFEST")
  args+=(--manifest-override "file://$LOCAL_MANIFEST" --private-mode)
fi
fingerprint=$(sha256sum "${fingerprint_inputs[@]}" | sha256sum)
fingerprint=${fingerprint%% *}
if [[ -e "$STATE/state" ]]; then
  private_file "$STATE/state"
  if [[ "$(cat "$STATE/state")" == "$fingerprint init-command-completed" ]]; then
    echo 'Matching initialization record; verify current Node readiness separately.'
    exit 0
  fi
  echo 'Changed identity/config or incomplete initialization: manual recovery required.' >&2
  exit 1
fi

"$NODEADM" config check --config-source "file://$NODECONFIG_PATH"
printf '%s started\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
# Failure/interruption retains started state and prevents an automatic retry.
"$NODEADM" init "${args[@]}"
systemctl is-active --quiet containerd
systemctl is-active --quiet kubelet
printf '%s init-command-completed\n' "$fingerprint" > "$STATE/state.new"
mv "$STATE/state.new" "$STATE/state"
echo 'Init command completed; cluster registration/CNI/readiness still require verification.'
```

The state record means the init command completed and the two local services were active at that moment. It **does not mean the Kubernetes Node is Ready**. On failure, a `started` record remains; inspect the actual host/SSM/cluster state before an operator reconciles it. A service timeout or interrupted command does not establish that no registration happened.

```ini
# /etc/systemd/system/eks-hybrid-bootstrap.service
[Unit]
Description=Initialize one prepared EKS Hybrid Node
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/eks/bootstrap.env
ExecStart=/usr/local/bin/eks-hybrid-bootstrap.sh
TimeoutStartSec=10min
RemainAfterExit=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Install/enable it through the host configuration owner. `network-online.target` provides boot ordering according to the network manager's wait service; it does not guarantee DNS, VPN, EKS or credential-service reachability. `RemainAfterExit` records service state, not node health. An `EnvironmentFile` is parsed by systemd; the script does not execute it with shell `source`.

Existing marker-only installations require explicit migration. Merely removing `.nodeadm-installed` / `.nodeadm-initialized` and rebooting is not a reset procedure. For an approved configuration change, such as enabling the credentials file, follow the documented maintenance/init procedure and reconcile the automation record afterward.

On normal reboot, configured kubelet/credential services resume. Deleting a Kubernetes Node object does not deregister SSM or stop kubelet; a running, authorized kubelet can recreate the Node. Do not use `delete node` as host decommissioning or assume every failed host will necessarily rejoin.

## Cilium CNI

AWS currently supports its maintained **Cilium 1.17.x and 1.18.x** builds for Hybrid Nodes. Published examples include `1.17.9-0` and `1.18.3-0` in `oci://public.ecr.aws/eks/cilium/cilium`. This is not a recommendation to select an arbitrary newer upstream chart.

The current AWS CNI page explicitly excludes **Ubuntu 20.04 and RHEL 8 for Cilium v1.18.3** because of the kernel requirement. Do not claim that merely changing their kernel establishes AWS support; select an OS/CNI combination within the documented matrix.

Calico examples moved to `aws-samples/eks-hybrid-examples`. This is not a Calico project deprecation or a guarantee that every existing Calico deployment will continue working. The dedicated current AWS CNI support page identifies the AWS-maintained Cilium builds and supported capabilities.

### Installation values

This IPv4 cluster-pool example assumes the reviewed remote Pod network is `10.85.0.0/16`, disjoint from Node/VPC/Service networks. Replace it with the cluster's approved values **before first install**:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: eks.amazonaws.com/compute-type
              operator: In
              values: [hybrid]
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4MaskSize: 25
    clusterPoolIPv4PodCIDRList: [10.85.0.0/16]
loadBalancer:
  serviceTopology: true
operator:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: eks.amazonaws.com/compute-type
                operator: In
                values: [hybrid]
  unmanagedPodWatcher:
    restart: false
envoy:
  enabled: false
kubeProxyReplacement: "false"
preflight:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
```

The preflight selector is separate from agent affinity. A `/25` contains 128 addresses; Cilium cluster-pool reserves two, so that is not a guarantee of 128 usable Pod addresses. Coordinate kubelet `maxPods`, hostNetwork Pods and other constraints.

Do not modify existing pool entries or `clusterPoolIPv4MaskSize`. Cilium documents expansion by **adding** a new pool entry; coordinate EKS remote networks, routing/BGP, overlap and capacity review first. “The entire list can never be extended” is too strong.

```bash
# Cluster write; requires approved context, values and supported chart.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}" "${CILIUM_VERSION:?Approved AWS chart version}"
helm install cilium oci://public.ecr.aws/eks/cilium/cilium \
  --version "$CILIUM_VERSION" --namespace kube-system \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values cilium-values.yaml --wait --timeout 10m
```

Verify the Cilium agent on every intended hybrid node, its operator, Node readiness and cross-node traffic. Affinity confines this installation to Hybrid nodes; cloud-node networking remains under its existing controller. A kube-proxy replacement design requires its own API reachability and migration plan; do not leave competing kube-proxy behavior on the same nodes.

### Upgrade and removal boundaries

Before a Cilium upgrade, save current values/manifests and an explicit Helm revision, review the version-specific upgrade notes, and render the proposed chart with the approved values. Run a **separate preflight release**, scoped to hybrid nodes, with `preflight.enabled=true`, `agent=false`, `operator.enabled=false`. Wait for its DaemonSet coverage **and** validation Deployment readiness; creating the preflight release is not the check result.

Remove only that preflight release after it passes. Upgrade with reviewed saved values and the appropriate `upgradeCompatibility` setting. Do not blindly carry obsolete settings across minor releases using `--reuse-values`. Rollback requires an explicit verified revision and review of CNI state/CRD compatibility; it is not an automatic guarantee of data-plane recovery.

CNI removal is a disruptive decommission/migration task. Evacuate workloads and verify which nodes, policies and CRs still depend on Cilium. Do not run `kubectl get crds | grep cilium | xargs kubectl delete` in a shared cluster. Helm uninstall does not guarantee that host routes, interfaces or BPF state are removed. Follow the version-specific CNI cleanup procedure on the identified evacuated hosts, checking active mounts and retained data before removing paths.

## Bottlerocket uses a different bootstrap contract

AWS supports VMware Bottlerocket variants from **1.37.0**, with the supported x86_64 Kubernetes variant and prerequisites. It does **not** run nodeadm. The AWS guide configures Kubernetes/AWS settings plus an **`eks-hybrid-setup` bootstrap container**. The former `[settings.hybrid.ssm]` and `[settings.hybrid.iam-roles-anywhere]` examples are not the documented settings contract.

Use the complete settings for the chosen provider from [Connect hybrid nodes with Bottlerocket](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html). Common fields include:

```toml
# Common fragment only: combine with the provider-specific settings from AWS.
[settings.kubernetes]
cluster-name = "my-hybrid-cluster"
api-server = "https://REPLACE_WITH_CLUSTER_ENDPOINT"
cluster-certificate = "REPLACE_WITH_BASE64_CLUSTER_CA"
hostname-override = "hybrid-node-001"
provider-id = "eks-hybrid:///ap-northeast-2/my-hybrid-cluster/hybrid-node-001"
authentication-mode = "aws"
cloud-provider = ""
server-tls-bootstrap = true

[settings.network]
hostname = "hybrid-node-001"

[settings.aws]
region = "ap-northeast-2"

[settings.kubernetes.node-labels]
"eks.amazonaws.com/compute-type" = "hybrid"

[settings.bootstrap-containers.eks-hybrid-setup]
mode = "always"
user-data = "REPLACE_WITH_BASE64_PROVIDER_BOOTSTRAP_INPUT"
```

This fragment is not a complete bootable configuration. The SSM provider supplies the `eks-hybrid-ssm-setup` activation/Region input; after registration its Node name changes to `mi-*`. IAM Roles Anywhere supplies `eks-hybrid-iam-ra-setup` certificate/key input and the AWS credential-process configuration, with role-session-name bound to the certificate policy. Include the documented ECR provider and provider-specific node labels/settings.

Base64 is encoding, not encryption. Provider bootstrap data can contain activation secrets or private keys: protect the VM configuration, guestinfo, management permissions and diagnostic exports; never put it in a public repo or log. Admin-container SSH access is optional and must be separately authorized. Do not clone an already registered VM as a clean template.

Configure the approved **powered-off, newly provisioned VM** before first power-on. The AWS guide uses base64-encoded `settings.toml` with `guestinfo.userdata.encoding=base64`; do not label plain base64 as `gzip+base64`. Confirm the deployed govc/VMware version, datastore, network, template ownership and secret-delivery method before provisioning. No VMware deployment was run in this audit.

## Add-on placement and Pod Identity

Route API-server traffic to the actual webhook/aggregated API listener. If hybrid Pod CIDRs are not reachable, place the **webhook server/operator** on reachable cloud nodes or validate an appropriate hostNetwork design where supported. This does not mean every CloudWatch/ADOT agent or application Pod must run in the cloud.

For cloud-node placement, use an explicit reviewed node label/affinity and check capacity/taints. `NotIn [hybrid]` can also match unlabeled nodes; it is not proof of an approved EC2 destination.

In a mixed cloud/hybrid cluster, AWS recommends at least one CoreDNS replica on each side. Four replicas plus soft spread does not guarantee exactly two on each side. Apply and verify the placement and Service Traffic Distribution procedure in [Network Configuration](./02-network-configuration.md).

| Node OS | Pod Identity preparation |
|---|---|
| Ubuntu/RHEL/AL2023 | `spec.hybrid.enableCredentialsFile: true`, then documented `nodeadm init`; agent configuration enables `daemonsets.hybrid.create` |
| Bottlerocket | OS **1.39.0+**; provider bootstrap command uses `--enable-credentials-file=true`; enable `daemonsets.hybrid-bottlerocket.create` |

Compatibility floors are agent **v1.3.3-eksbuild.1** for non-Bottlerocket and **v1.3.7-eksbuild.2** for Bottlerocket, not current install targets. Select a currently compatible add-on version/configuration schema for the cluster. The mounted temporary-credential locations differ: `/eks-hybrid/.aws/credentials` versus Bottlerocket `/var/eks-hybrid/.aws/credentials`.

Private deployments need the `eks-auth` service path, the node role's `eks-auth:AssumeRoleForPodIdentity` permission and each workload's Pod Identity association/trust/permissions. Merely installing the agent is insufficient. Merge the required DaemonSet configuration through the add-on owner; do not overwrite an existing add-on with a blind `create-addon`.

## Upgrade, recovery and removal

Prefer adding and **fully initializing/verifying replacement capacity** before evacuating old nodes. Installing binaries on new hosts alone does not add cluster capacity. Preserve required DNS availability; do not blindly scale an existing four-replica CoreDNS deployment down to two as a “resilience” step.

For one identified old node, verify context, Node UID, host mapping and workload/data ownership. Cordon, drain with a timeout and stop on any PDB/eviction error. `--delete-emptydir-data` explicitly permits loss of local emptyDir data; it is not a default safety option. Unmanaged Pods, local persistent data and DaemonSets need their own handling. Do not use `--force` or disable eviction to make a blocked drain appear successful.

For an in-place update, run the documented `nodeadm upgrade` on the evacuated host, then verify identity, software versions, Ready/CNI/DNS and workload behavior before uncordoning. It is disruptive; “no spare capacity” does not make it safe.

For decommissioning, stop any automatic bootstrap/rejoin path, complete the documented nodeadm removal and provider deregistration, then remove the exact Node object and reconcile remaining CNI resources through their owner. Preserve necessary recovery evidence privately.

`nodeadm uninstall` is not `kubectl drain` or `kubectl delete node`. It normally refuses remaining workload Pods. It does not remove every CNI/add-on artifact. **Since v1.0.9, even the documented force/skip uninstall path does not delete `/var/lib/kubelet`**, because mounted paths can expose the host filesystem. `--force` removes additional default CNI/Kubernetes paths; it is not a generic “skip confirmation and delete everything” flag. Inspect mounts and data before any manual removal.

If a genuine reinstall is approved after removal, run **install → config check → init** again with valid credentials and reconcile the automation record. Never treat an authentication error, existing profile or partially completed init as sufficient reason to uninstall a live node.

## Troubleshooting

| Observation | Investigate before changing state |
|---|---|
| SSM installer signature failure on older nodeadm | Verify the approved nodeadm is at least 1.0.19; do not bypass signature checks |
| Package manager/download failure | Actual repository access, proxy, CA trust, package locks, supported OS/runtime and errors; `dnf update` is a system upgrade, not a diagnostic |
| Timeout | Determine the failed phase and reachability; raising the timeout alone does not repair it |
| Node IP outside remote networks | Actual typed node IP and EKS remote-node CIDRs |
| API unreachable / Unauthorized | DNS/routes/443 and return path, intended Hybrid role, trust/credential validity, `HYBRID_LINUX` access entry |
| NotReady | CNI/agent logs and selected datapath ports, runtime, disk/resource conditions; not every case is missing CNI |
| Image pull or x509 error | Exact image/auth path, ECR API/DKR/S3, private-registry CA and hostname; keep TLS verification enabled |
| Expired activation / token | Activation expiry/capacity/Region versus running agent credential renewal, time sync and AWS reachability; a restart is not a guaranteed fix |
| Existing Hybrid profile / partial init | Inspect current nodeadm/provider state and intended cluster; preserve evidence, do not automatically uninstall |

```bash
# Private diagnostic output on the identified node; no nonexistent nodeadm status.
sudo systemctl status kubelet containerd --no-pager
sudo journalctl -u kubelet --since '-15 min' --lines 200 --no-pager
sudo nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml
```

`nodeadm debug` performs AWS/cluster reads and credential checks. Keep its output private and redact before sharing. `sudo aws sts get-caller-identity` may use a different root/admin credential chain and does not establish what kubelet uses. Do not use `curl -k` as TLS validation. CA trust of the server and approval/issuance of kubelet client certificates are separate mechanisms.

## Primary references

- [Hybrid nodeadm commands, file locations and removal behavior](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [Hybrid credentials](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [IAM Roles Anywhere CreateSession duration](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [SSM CreateActivation](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html)
- [AWS Hybrid CNI support and lifecycle](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Cilium cluster-pool expansion](https://github.com/cilium/cilium/blob/v1.18.3/Documentation/network/concepts/ipam/cluster-pool.rst)
- [Bottlerocket Hybrid bootstrap](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-bottlerocket.html)
- [Hybrid add-ons and Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [containerd registry host configuration](https://github.com/containerd/containerd/blob/v2.2.0/docs/hosts.md)
- [systemd network-online semantics](https://systemd.io/NETWORK_ONLINE/)
- [Kubernetes version skew](https://kubernetes.io/releases/version-skew-policy/)

< [Previous: Restricted-internet Setup](./03-airgap-setup.md) | [Table of Contents](./README.md) | [Next: GPU Integration](./05-gpu-integration.md) >
