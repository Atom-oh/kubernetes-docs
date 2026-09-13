# Bare Metal Server OS Installation and Migration Guide

< [Previous: Operations and Maintenance](./08-operations.md) | [Table of Contents](./README.md) | [Next: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >

> **Validation baseline**: AWS Hybrid OS/nodeadm documentation and public prices checked September 13, 2026; nodeadm 1.0.20 is the reviewed CLI reference. Choose a currently supported EKS/OS/CNI combination.
> **Last Updated**: September 13, 2026

This guide separates destructive OS installation, image preparation, cluster joining and read-only acceptance checks. Examples contain placeholders and require a host-specific installation plan. No OS installation, Packer build, VM creation or AWS/cluster operation was executed for this review.

## Overview

### Why Choose Bare Metal

Removing a hypervisor can avoid its licensing and execution layer, but does not guarantee lower total cost or better application performance. Inventory virtualization features, availability, backup, storage, networking, support contracts and migration effort before choosing a replacement. VM applications are not automatically converted into containers, and existing license obligations do not disappear when a pilot cluster starts.

### OS Infrastructure Support Matrix

| OS | Bare metal | On-premises virtualization | Configuration and support boundary |
| --- | --- | --- | --- |
| Ubuntu 20.04/22.04/24.04 | Listed Hybrid OS families | Supported host infrastructure subject to OS/kernel/CNI requirements | nodeadm/YAML; verify Ubuntu lifecycle and support separately |
| RHEL 8/9 | Listed Hybrid OS families | Supported host infrastructure subject to OS/kernel/CNI requirements | nodeadm/YAML; Red Hat subscription/OS support remains separate |
| AL2023 | **Not the supported deployment path** | On-premises virtualized guest | nodeadm/YAML; AWS Support Plans do not cover AL2023 outside EC2 |
| Bottlerocket VMware variants >=1.37.0 | **Not supported for Hybrid bare metal** | VMware vSphere, **x86_64** | Bottlerocket settings/bootstrap; govc manages VMware VMs |

AWS supports the Hybrid integration with the listed Ubuntu/RHEL families, not the OS vendor's support obligations. Check specific versions, architecture and CNI/kernel requirements. AL2023 outside EC2 is a VM guest option, not a generic raw-image bare-metal recommendation. Bottlerocket's VMware Kubernetes variants begin at 1.28, which is a variant history, not a recommendation to run that old EKS version. SSM installations/upgrades require nodeadm >=1.0.19 because older releases use an outdated SSM signing key.

## Cost Comparison Analysis

### License/Subscription Cost Comparison

#### VMware vSphere

Obtain a current quote for the actual product bundle, licensed cores, minimums, term and support. The old $4,500–8,500/socket-year figure has no verified source here and cannot be treated as a current vSphere quote.

#### OpenShift

Normalize actual Red Hat entitlements, physical/virtual core or socket metrics and support tiers. The old $2,500–5,000/node-year estimate and “premium support included” statement are unverified; do not use them as a current price or entitlement guarantee.

#### EKS Hybrid Nodes

The [official price page](https://aws.amazon.com/eks/pricing/) charges monthly marginal tiers on **reported node vCPU-hours**: first 576,000 at $0.020; next 576,000 at $0.014; next 4,608,000 at $0.010; next 5,760,000 at $0.008; above 11,520,000 at $0.006. These are not a universal flat $0.01 rate.

Tiers aggregate within one account/Region, or across accounts in the same Region under AWS Organizations consolidated billing. Hyperthreaded bare-metal cores can report two vCPUs each. Charges start when a node joins and stop when it is removed; idle workloads do not eliminate the node charge. AWS asks customers to contact their account team for machines larger than 32 vCPU. Cluster, provisioned-control-plane/capability, network, logging, storage, OS and other support charges are separate.

### Annual Cost Comparison by Scale (32 vCPU Servers)

The following is a deterministic **model**, not a bill or measurement: 32 reported vCPU/node, 730 hours every month, one Region/aggregation scope, no other Hybrid usage, and twelve identical modeled months. The final column adds one base-tier cluster in standard support at $0.10/hour. It excludes other services, discounts/taxes, hardware, power, OS entitlements, labor and migration; actual month lengths/tier resets affect invoices.

| Nodes | Monthly vCPU-hours | Monthly node fee | Annualized node fee | Annualized nodes + one base standard-support cluster |
| --- | --- | --- | --- | --- |
| 10 | 233,600 | $4,672.00 | $56,064.00 | $56,940.00 |
| 50 | 1,168,000 | $19,744.00 | $236,928.00 | $237,804.00 |
| 100 | 2,336,000 | $31,424.00 | $377,088.00 | $377,964.00 |

<details>
<summary>Preserved historical estimates — unverified and not current pricing</summary>

The original table is retained for traceability. Vendor quote sources could not be verified. Its EKS column used the obsolete assumption `32 × $0.01 × 8,760 = $2,803.20/node-year`, with no cluster fee or marginal tiers. These numbers are not valid current comparative TCO evidence.

| Scale | VMware vSphere (prior annual estimate) | OpenShift (prior annual estimate) | EKS Hybrid (obsolete flat-rate estimate) |
| --- | --- | --- | --- |
| 10 nodes | ~$45,000–85,000 | ~$25,000–50,000 | ~$28,032 |
| 50 nodes | ~$225,000–425,000 | ~$125,000–250,000 | ~$140,160 |
| 100 nodes | ~$450,000–850,000 | ~$250,000–500,000 | ~$280,320 |

</details>

### TCO (Total Cost of Ownership) Considerations

Include spare capacity, facilities/power, OS/security patching, PKI/SSM operations, storage/backup/restore, connectivity, monitoring, staffing, licensing obligations and rollback capacity. Compare equivalent availability/support scope; do not claim a savings percentage from the unverified old table.

## OS-Specific Bare Metal Installation

### Prerequisites

#### BIOS/UEFI Settings

Verify the selected installer, firmware, boot mode, NIC/storage drivers and signed boot chain. Keep Secure Boot when the validated bootloader/kernel/module chain supports it; do not disable it as a blanket container prerequisite. Ordinary Linux containerd/runc containers do not require VT-x/AMD-V hardware virtualization. VM-based sandboxes, QEMU/KVM image builders and other virtualization workloads have separate requirements.

#### Network Infrastructure

Legacy PXE commonly uses DHCP/ProxyDHCP and TFTP, while UEFI HTTP/iPXE designs can use different boot transports. `pxelinux.0` is not a universal UEFI loader. Use the bootloader appropriate to the firmware, verify ISO/kernel/initrd integrity, and separate provisioning networks from workloads. Protect host-specific configuration; do not serve activation codes, private keys or passwords from an unauthenticated shared HTTP/TFTP root.

#### AWS Packer Templates

The [AWS example directory](https://github.com/aws/eks-hybrid/tree/main/example/packer) currently contains `hybrid-nodes-template.pkr.hcl`, not the original invented `bare-metal-template.pkr.hcl`. Its input `CREDENTIAL_PROVIDER` accepts `ssm` or `iam`; its HCL maps `iam` to nodeadm's `iam-ra`. QEMU output uses `PACKER_OUTPUT_FORMAT`, not an `output_format` variable. Review the template and provisioner scripts at an approved commit, including required builder inputs and password/user-data handling.

```bash
# From a reviewed checkout of aws/eks-hybrid/example/packer:
export NODEADM_ARCH=amd       # This template uses amd/arm, not amd64/arm64.
export CREDENTIAL_PROVIDER=ssm # The template accepts ssm/iam; maps iam to nodeadm iam-ra.
export PACKER_OUTPUT_FORMAT=raw
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
: "${ISO_URL:?Set the approved Ubuntu or RHEL installer ISO}"
: "${ISO_CHECKSUM:?Set the verified vendor ISO checksum}"
export K8S_VERSION ISO_URL ISO_CHECKSUM
# Also prepare the selected builder's required inputs using the reviewed template.
packer validate -syntax-only hybrid-nodes-template.pkr.hcl
# A separate build action, not a validation step:
# packer build -only=general-build.qemu.ubuntu24 hybrid-nodes-template.pkr.hcl
```

The template also has AMI/vSphere builders: select only the intended builder before a separately authorized build. Syntax-only validation is not a built/tested image. Do not copy stale Kubernetes examples, default builder passwords, world-readable credential files or enrolled machine/SSM identities into a reusable image.

For a manually provisioned host, stage an approved nodeadm release/architecture with a reviewed checksum. This is an **installation step**, not a health check. Obtain the checksum through the approved release-verification process; do not invent it or bypass a mismatch.

```bash
set -euo pipefail
: "${NODEADM_VERSION:?Set the approved release, at least 1.0.19 for SSM}"
: "${NODEADM_SHA256:?Set the approved SHA-256 for this release and architecture}"
: "${NODEADM_ARTIFACT:?Set the local file delivered through the approved artifact channel}"
case "$(uname -m)" in
  x86_64) NODEADM_ARCH=amd64 ;;
  aarch64|arm64) NODEADM_ARCH=arm64 ;;
  *) printf 'Unsupported architecture\n' >&2; exit 2 ;;
esac
[[ "$NODEADM_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
[[ "$NODEADM_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || exit 2
[[ "$(printf '%s\n' 1.0.19 "$NODEADM_VERSION" | sort -V | head -n 1)" == 1.0.19 ]] || exit 2
umask 077
STAGING_DIR=$(mktemp -d)
trap 'rm -f -- "$STAGING_DIR/nodeadm"; rmdir -- "$STAGING_DIR"' EXIT
cp -- "$NODEADM_ARTIFACT" "$STAGING_DIR/nodeadm"
printf '%s  %s\n' "$NODEADM_SHA256" "$STAGING_DIR/nodeadm" | sha256sum --check -
chmod 0700 "$STAGING_DIR/nodeadm"
# Check the verified staged binary before replacing the installed executable.
ACTUAL_VERSION=$("$STAGING_DIR/nodeadm" --version)
VERSION_RE="(^|[^0-9.])v?${NODEADM_VERSION//./\\.}([^0-9A-Za-z.+-]|$)"
[[ "$ACTUAL_VERSION" =~ $VERSION_RE ]] || { printf 'Artifact version mismatch\n' >&2; exit 2; }
printf '%s\n' "$ACTUAL_VERSION"
sudo install -m 0755 "$STAGING_DIR/nodeadm" /usr/local/bin/nodeadm
/usr/local/bin/nodeadm --version
```

### Ubuntu LTS (22.04/24.04)

Ubuntu Server's Subiquity Autoinstall uses YAML; cloud-init can deliver its configuration. The template below deliberately keeps storage interactive and requires an exact approved disk serial and SSH key before use. Selecting/partitioning a disk destroys its existing data. Confirm backups, disk inventory, installer delivery, access/recovery and firmware compatibility on a disposable target first. No wildcard/empty disk match or “largest disk” assumption is appropriate for a host with data disks.

#### Autoinstall Configuration Example

```yaml
#cloud-config
autoinstall:
  version: 1
  interactive-sections: [storage]
  locale: en_US.UTF-8
  keyboard:
    layout: us
  storage:
    layout:
      name: lvm
      match:
        serial: REPLACE_WITH_APPROVED_DISK_SERIAL
  identity:
    hostname: replace-with-unique-hostname
    username: hybrid-admin
    password: "!"
  ssh:
    install-server: true
    allow-pw: false
    authorized-keys:
    - "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
  packages: [curl, jq]
  shutdown: poweroff
```

`password: "!"` locks password authentication in this template; verify the actual approved SSH access and recovery path. Supply network/NIC/VLAN/bond settings appropriate to the host and chosen installer. The local schema check does not test disk selection, boot or login. nodeadm is staged/installed in the separate step above; the installer does not fetch an unverified `latest` binary.

#### Ubuntu 24.04 Specific Notes

[Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423) concerns AppArmor signal denial during container termination and has released package fixes. AWS's OS page still describes the 1.7.19+ fix context. Check the actual distribution package/backport, loaded profile, runtime and denial logs. This is not a universal diagnosis for every stuck Pod or a recommendation to remain on an old containerd release.

```bash
# Read-only investigation on the affected host:
containerd --version
dpkg-query -W 'containerd*' 'runc*' 'apparmor*'
sudo journalctl -k --since '30 minutes ago' --no-pager -n 200
if test -f /run/reboot-required.pkgs; then cat /run/reboot-required.pkgs; fi
```

For the documented affected package/profile transition, the Ubuntu issue requires a restart to load the corrected profiles; schedule draining, reboot and workload checks through the lifecycle procedure. Do not generalize that every AppArmor edit requires reboot. `aa-remove-unknown` removes all loaded profiles absent from `/etc/apparmor.d`; it is not a targeted profile editor and is not the default repair command.

### RHEL 9

RHEL uses Kickstart. The following is an installation template, **not Bash**. Substitute an approved single installation disk identifier, password hash and complete SSH public key. `ignoredisk --only-use` and `clearpart --drives` must name that same verified disk; do not use an unrestricted `clearpart --all`. Match repository/stage2/bootloader/network details to the selected RHEL installer and validate with its ksvalidator before use.

#### Kickstart Configuration Example

```text
# Template: substitute and validate the approved target disk, key and password hash.
lang en_US.UTF-8
keyboard us
timezone UTC --utc
rootpw --lock
user --name=hybrid-admin --groups=wheel --iscrypted --password=REPLACE_WITH_CRYPT_HASH
sshkey --username=hybrid-admin "ssh-ed25519 REPLACE_WITH_APPROVED_PUBLIC_KEY"
network --bootproto=dhcp --device=link --activate
ignoredisk --only-use=REPLACE_WITH_APPROVED_INSTALL_DISK
clearpart --all --initlabel --drives=REPLACE_WITH_APPROVED_INSTALL_DISK
autopart --type=lvm
selinux --enforcing
services --enabled=sshd
%packages
@core
openssh-server
curl
jq
%end
poweroff
```

Keep SELinux enforcing and diagnose the specific policy/context requirements. nodeadm documents containerd SELinux configuration and Pod security contexts; do not blanket-mark `container_t` permissive. OS packages and nodeadm/containerd installation are separate stages.

#### RHEL containerd Installation Notes

`distro` is not a supported nodeadm containerd source on RHEL. Choose `docker` to let nodeadm install the compatible Docker-distributed package, or `none` when you separately install/maintain containerd. “RHEL always requires docker” is too broad.

```bash
set -euo pipefail
: "${K8S_VERSION:?Set a currently supported cluster-compatible major.minor}"
sudo nodeadm install "$K8S_VERSION" --credential-provider ssm \
  --containerd-source docker
# If containerd is separately installed and maintained, choose --containerd-source none.
```

#### Large-Scale Environments: Satellite/Foreman Integration

Satellite/Foreman can manage reviewed Kickstart templates, repositories and provisioning workflows. Validate per-host disks, hardware identities, subscriptions, artifact integrity and failure recovery; a syntactically valid shared template is not permission to wipe an arbitrary fleet.

### Amazon Linux 2023

This is a **virtualized-guest reference**, not a bare-metal installation option. AWS provides KVM, VMware and Hyper-V VM images for AL2023 outside EC2. AWS Support Plans do not cover that AL2023 OS use outside EC2; distinguish it from EKS Hybrid integration support. Use the appropriate image and cloud-init transport. A minimal VM-identity fragment is:

```yaml
#cloud-config
# VM identity fragment only; it does not install or join a Hybrid Node.
hostname: replace-with-unique-hostname
manage_etc_hosts: true
ssh_pwauth: false
```

It intentionally does not create an administrator, embed keys or initialize a node. Prepare approved access and use the separately reviewed bootstrap flow. `--containerd-source docker` is not supported for AL2023; use its supported distribution source or deliberately manage containerd yourself.

### Bottlerocket on VMware (Reference)

For EKS Hybrid Nodes, use supported VMware variants >=1.37.0 on x86_64. Bottlerocket settings and bootstrap containers configure the OS/authentication; govc is a VMware VM-management CLI, not the TOML settings parser. Use the [complete bootstrap guide](./04-node-bootstrap.md) for versioned settings, private user-data and credential setup.

## Credential Provider Configuration Comparison

### nodeadm-Based Configuration (Ubuntu/RHEL/AL2023)

These are separate SSM and IAM Roles Anywhere alternatives. Replace every placeholder with the approved cluster/Region/identity, protect NodeConfig with root ownership and mode 0600, and keep per-host private keys private. Do not put enrolled SSM state or one shared host key into cloned golden images.

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: "REPLACE_WITH_PRIVATE_ACTIVATION_CODE"
      activationId: "REPLACE_WITH_PRIVATE_ACTIVATION_ID"
```

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-cluster
    region: ap-northeast-2
  hybrid:
    iamRolesAnywhere:
      trustAnchorArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:trust-anchor/REPLACE_WITH_ID
      profileArn: arn:aws:rolesanywhere:ap-northeast-2:111122223333:profile/REPLACE_WITH_ID
      roleArn: arn:aws:iam::111122223333:role/HybridNodeRole
      certificatePath: /etc/eks/pki/node.crt
      privateKeyPath: /etc/eks/pki/node.key
```

Nodeadm validates configuration and obtains the required cluster metadata through the configured AWS identity. Verify actual API reachability, EKS access entries, trust/permissions and certificate paths before joining; parsing YAML alone does not prove authorization.

### Bottlerocket-Based Configuration (VMware)

The old `[settings.hybrid.ssm]` and `[settings.hybrid.iam-roles-anywhere]` blocks were not valid Bottlerocket settings. Use the supported Kubernetes settings and documented Hybrid bootstrap-container inputs described in [node bootstrap](./04-node-bootstrap.md). Base64 user-data is encoding, not encryption; protect VMware guestinfo and provisioning logs.

### Credential Provider Selection Guide

| Situation | Selection consideration |
| --- | --- |
| No managed PKI | SSM hybrid activation can reduce certificate-management work; maintain identity/activation lifecycle |
| Existing managed PKI | IAM Roles Anywhere can use per-host X.509 identity; maintain issuance, trust, expiry and revocation |
| No public internet | Either needs its required AWS APIs through an approved private/proxy path; verify endpoint support |
| Fully disconnected/DDIL | EKS Hybrid Nodes is not the supported operating model; IAM Roles Anywhere still calls AWS CreateSession |
| Custom node identity | Review the provider's naming and lifecycle rules; do not assume the Node name is a resolvable host name |

See [private connectivity](./03-airgap-setup.md). “No public internet” and “no AWS connectivity” are different requirements.

## Large-Scale Provisioning Automation

### PXE Boot Infrastructure Setup

```text
Approved host/firmware inventory
  → matching DHCP/HTTP/PXE boot configuration
  → verified signed loader and installer kernel/initrd
  → protected host-specific installation configuration
  → explicit approved disk / OS installation
  → unique host identity / separate Hybrid bootstrap
```

The shown TFTP/PXELINUX combination describes legacy BIOS. UEFI PXE can also use TFTP, but needs a UEFI-compatible loader; choose supported secure transports for the actual environment. ISO checksums and signature trust are separate from DHCP reachability.

### Ansible Automation Playbook

The following playbook is a **read-only preflight for already prepared hosts**. It stops on missing components/services and does not use the existence of `/usr/bin/kubelet` as proof of the desired version. It does not install binaries, deploy secret templates or repeatedly run nodeadm init.

```yaml
# Read-only preflight; does not provision, install, or initialize hosts.
- name: Inspect approved Hybrid hosts
  hosts: hybrid_nodes
  become: true
  gather_facts: false
  serial: 1
  any_errors_fatal: true
  tasks:
  - name: Read OS release
    ansible.builtin.command:
      argv: [cat, /etc/os-release]
    changed_when: false
  - name: Read architecture
    ansible.builtin.command:
      argv: [uname, -m]
    changed_when: false
  - name: Read installed nodeadm version
    ansible.builtin.command:
      argv: [/usr/local/bin/nodeadm, --version]
    changed_when: false
  - name: Check each required service
    ansible.builtin.command:
      argv: [systemctl, is-active, --quiet, "{{ item }}"]
    loop: [containerd, kubelet]
    changed_when: false
```

For provisioning, use distinct approved stages: validate host/disk inventory → stage verified OS/artifacts → supply private per-host configuration → run the [bootstrap state/identity procedure](./04-node-bootstrap.md) → verify the actual Node UID, version, new Lease and workload health. For existing hosts use [lifecycle management](./07-node-lifecycle.md). Coordinate one host at a time, stop on failures and preserve partial-state evidence; do not hide changes behind `creates: /usr/bin/kubelet`.

## Migration Strategies

### VMware → Bare Metal + EKS Hybrid Nodes

#### Phase 1: Build Parallel Infrastructure

Inventory workloads, virtual machines, licenses, network/security functions, storage and dependencies. Prepare a parallel supported target, private connectivity and rollback capacity. Bottlerocket on VMware may remain during a transition, but does not turn into a bare-metal OS.

#### Phase 2: Containerize Workloads

Containerize appropriate workloads explicitly; some VMs may need to remain VMs. Validate state migration, CSI behavior, permissions, backups and restores before moving writers. AWS managed databases are an architectural option, not an automatic conversion.

#### Phase 3: Network Transition

Inventory NSX-T routing, overlay, firewall, load-balancing and policy functions separately. Cilium BGP exchanges routes; it is not a feature-equivalent replacement for all NSX-T functions. Validate addressing, return paths, ingress/TLS, DNS, policies and established connections before switching traffic.

#### Phase 4: Decommission VMware

Decommission only after workload/data acceptance, an agreed rollback window, backup recovery and licensing/retention decisions. Verify the actual infrastructure being removed; do not make license cancellation or disk wiping an automatic pipeline finalizer.

### OpenShift → EKS Hybrid Nodes

#### Concept Mapping

| OpenShift | Candidate target | Migration gap to resolve |
| --- | --- | --- |
| Route | Ingress / Gateway API controller | TLS termination/reencrypt/passthrough, weights, annotations and policy are controller-dependent |
| SCC | PSS/Pod Security Admission plus needed policy/defaulting | PSS does not reproduce SCC UID/SELinux/group strategies or mutation |
| OLM | Supported OLM, Helm or EKS add-on/operator delivery | OLM can run on Kubernetes; CRD conversion, upgrades and dependencies do not migrate automatically |
| MachineSet | Host lifecycle/provisioning automation | nodeadm/Ansible is not a Machine API controller with replacement/scaling semantics |
| ImageStream | Registry plus image-promotion/trigger automation | ECR stores images; it does not replace ImageStream import/tag/change triggers |
| BuildConfig | Reviewed external CI/CD | Recreate source, image, credential and build-policy behavior |
| DeploymentConfig | Deployment plus required rollout automation | Preserve triggers, hooks, strategies and rollback behavior |

#### Workload Migration Checklist

- Inventory every Route, policy/default, CRD/operator, image trigger, build and rollout hook.
- Test target behavior and service-account/RBAC scope with representative workloads.
- Verify data consistency, snapshots/restores, DNS/TLS, network controls and observability.
- Rehearse cutover and rollback before decommissioning the source.

#### Phased Migration

Assess dependencies → pilot a representative non-critical workload → transition in controlled waves → accept data/operations and retain recovery evidence → decommission after the agreed rollback period.

## Post-Installation Verification

Verification must not reinstall packages or initialize a joined host. These reads are only observations; process activity or an old Ready condition alone is not workload acceptance.

```bash
# Read-only, on the host mapped to the intended Kubernetes Node:
set -euo pipefail
cat /etc/os-release
uname -m -r
/usr/local/bin/nodeadm --version
containerd --version
for service in containerd kubelet; do
  systemctl is-active --quiet "$service"
done
```

```bash
# From the approved administrative context; these are reads, not installation:
set -euo pipefail
: "${KUBE_CONTEXT:?Set the approved context}"
: "${NODE:?Set the actual registered Node name from inventory}"
kubectl --context "$KUBE_CONTEXT" get node "$NODE" -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-node-lease get lease "$NODE" -o yaml
```

Use the Node-to-host inventory mapping, inspect a fresh Lease and version, confirm CNI/DNS/storage and execute the approved workload checks from the [bootstrap](./04-node-bootstrap.md) and [lifecycle](./07-node-lifecycle.md) guides. Failed/unknown reads are not a pass.

## Troubleshooting

| Issue | Checks and bounded next step |
| --- | --- |
| Boot failure | Firmware mode, signed loader, DHCP/HTTP/TFTP design, NIC drivers and approved image checksums |
| Autoinstall/Kickstart failure | Installer logs/schema, intended disk, repository/stage2 and host-specific configuration; do not retry destructive partitioning blindly |
| Ubuntu termination issue | Actual AppArmor signal-denial evidence, fixed package/backport and required planned reboot |
| RHEL containerd | Select supported docker/none source, verify actual runtime and SELinux policy |
| nodeadm/authentication | Verify current nodeadm, protected config, AWS private connectivity, identity and trust; avoid blind re-registration |

## Validation Scope and References

Local evidence includes 50 schema/contract/command-double checks, twelve artifact/host/API-read subprocess cases, the pykickstart 3.78 RHEL9 parser and ten Decimal pricing assertions. The canonical Autoinstall schema permits additional root keys and does not replace validation by the selected installer. No real OS installation, disk erasure, boot/login, Packer image build, Ansible SSH operation, nodeadm execution, VM creation or AWS/Kubernetes call was performed. The temporary test targets and executables were synthetic.

- [AWS Hybrid OS requirements](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [AWS Hybrid nodeadm](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [AWS EKS pricing](https://aws.amazon.com/eks/pricing/)
- [AWS Packer example](https://github.com/aws/eks-hybrid/tree/main/example/packer)
- [Canonical Autoinstall reference](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
- [RHEL 9 Kickstart reference](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/automatically_installing_rhel/kickstart-commands-and-options-reference_rhel-installer)
- [Ubuntu bug 2065423](https://bugs.launchpad.net/ubuntu/+source/containerd-app/+bug/2065423)
- [aa-remove-unknown manual](https://manpages.ubuntu.com/manpages/noble/man8/aa-remove-unknown.8.html)
- [AL2023 outside EC2](https://docs.aws.amazon.com/linux/al2023/ug/outside-ec2.html)
- [Operator Lifecycle Manager](https://olm.operatorframework.io/docs/)
- [OpenShift SCC API](https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_apis/securitycontextconstraints-security-openshift-io-v1)


---

< [Previous: Operations and Maintenance](./08-operations.md) | [Table of Contents](./README.md) | [Next: Hybrid Nodes Gateway](./10-hybrid-nodes-gateway.md) >
