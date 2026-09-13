# Amazon VPC CNI

> **Review baseline**: VPC CNI / Helm chart 1.23.0; network policy agent 1.4.1.
> **Last reviewed**: September 11, 2026. Select an EKS add-on build compatible with the actual cluster version and Region. Upstream, Helm and EKS `eksbuild` versions are separate identifiers.

## Table of Contents

- [VPC CNI Overview](#vpc-cni-overview)
- [Networking Model](#networking-model)
- [Installation and Configuration](#installation-and-configuration)
- [IP Address Management](#ip-address-management)
- [Network Policy Support](#network-policy-support)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## VPC CNI Overview

Amazon VPC CNI supplies VPC-native Pod networking on standard EKS EC2 nodes. This guide's `aws-node` DaemonSet commands target that installation. Auto Mode runs managed networking components as node services; Fargate and Windows use different management paths. See the [overview](README.md) before applying EC2/Linux instructions to another compute mode.

Pods use VPC-routable addresses without an overlay encapsulation requirement. Routing, security groups, network policies, ENI/IP limits and application behavior still determine connectivity and performance. EKS supports **IPv4 or IPv6 Pod/Service addressing**, selected when creating the cluster; it does not support dual-stacked Pods or Services. A dual-stack VPC or an IPv6 Pod's IPv4 egress helper is a different concept.

### Architecture

| Component | Responsibility |
|---|---|
| Container runtime / CNI binary | The runtime invokes CNI for the Pod sandbox; the AWS plugin requests an address and configures its network namespace. |
| IPAMD | Maintains address pools and manages the required ordinary ENIs/IPs on Linux EC2 nodes. |
| EKS network policy controller / node agent | The managed controller resolves policy endpoints; `aws-eks-nodeagent` enforces supported policies using eBPF when enabled. |
| VPC resource controller | Manages features such as branch/trunk interfaces and Windows address allocation under their own prerequisites. |

The former diagram labeled the CNI binary as directly called by kubelet. Current Kubernetes delegates CNI management to the container runtime.

### IP Allocation Modes

| Property | Secondary IPv4 addresses | Prefix delegation |
|---|---|---|
| Allocation | Individual secondary addresses on an ENI | IPv4 `/28` prefixes with 16 addresses; IPv6 uses `/80` prefixes |
| Capacity | Constrained by interface/address slots and kubelet settings | More addresses per slot, subject to supported hardware, free prefixes and kubelet/resource limits |
| Allocation tradeoff | Fine-grained address allocation | Allocates a block at once; warm targets can reserve unused addresses |
| Selection | Use according to compatibility and measured demand | Verify Nitro support, subnet fragmentation, workload churn and feature combinations |

Prefix delegation is not a universal requirement for a large cluster, and does not manufacture address space in an exhausted subnet.

## Networking Model

### ENI Architecture

For ordinary secondary-IPv4 mode, each ENI has a primary address and additional addresses available to the CNI. The primary ENI also carries the node's primary address. Additional ENIs can supply more secondary Pod addresses. Custom networking changes which interfaces/subnets supply Pod addresses; prefix and branch-ENI modes have different allocation rules.

```text
Linux EC2 node — ordinary secondary-IPv4 illustration
├── Primary ENI: node primary IP + secondary IPs for Pods
├── Additional ENI: its primary IP + secondary IPs for Pods
└── Additional ENI: its primary IP + secondary IPs for Pods
```

### Instance Type ENI/IP Limits

| Instance type | Max ENIs | IPv4 slots per ENI | Legacy secondary-IP bootstrap maxPods |
|---|---|---|---|
| t3.medium | 3 | 6 | 17 |
| t3.large | 3 | 12 | 35 |
| m5.large | 3 | 10 | 29 |
| m5.xlarge | 4 | 15 | 58 |
| m5.2xlarge | 4 | 15 | 58 |
| c5.4xlarge | 8 | 30 | 234 |
| m5.8xlarge | 8 | 30 | 234 |

The historical calculation is **`ENIs × (IPv4 slots per ENI − 1) + 2`**. The `+2` accounts for the two host-network system Pods in that bootstrap calculation; for m5.large, `3 × 9 + 2 = 29`. It does not mean all current deployments always have exactly two host-network Pods.

These are legacy bootstrap values, not current universal Pod-density recommendations. Prefix delegation, custom networking, branch interfaces, multiple network cards, CPU/memory and kubelet `maxPods` all matter. EKS managed node groups cap `maxPods` at 110 for instances with fewer than 30 vCPUs and 250 otherwise. Inspect the actual node's allocatable capacity.

### Prefix Delegation

An EKS managed add-on configuration fragment for Linux IPv4 prefix mode is:

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```

Merge this with the intended add-on configuration using the management procedure below. For a Helm-owned installation, the equivalent `env` mapping belongs in Helm values. Direct `kubectl set env` edits may be reconciled by the chosen manager.

IPv4 allocation needs suitable contiguous `/28` blocks, not merely a positive `AvailableIpAddressCount`. Verify subnet reservations/fragmentation and supported Nitro instances. Enabling prefixes does not automatically raise every existing kubelet's Pod limit or increase the branch-ENI Pod limit.

## Installation and Configuration

### Establish Ownership and Compatibility

Use configured AWS CLI credentials and a Kubernetes context for the intended cluster. Start with reads:

```bash
EKS_REGION=ap-northeast-2
CLUSTER_NAME=my-cluster
KUBERNETES_MINOR="$(aws eks describe-cluster --region "$EKS_REGION" \
  --name "$CLUSTER_NAME" --query cluster.version --output text)"
aws eks describe-addon-versions --region "$EKS_REGION" \
  --addon-name vpc-cni --kubernetes-version "$KUBERNETES_MINOR"
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system get daemonset aws-node -o yaml
```

An EKS `ResourceNotFoundException` for `describe-addon` does not prove that no CNI is installed: it may be self-managed. Inspect the existing DaemonSet, ServiceAccount, Helm releases, configuration and IAM model before choosing **one** manager. Auto Mode networking is not installed through this workflow.

### Existing EKS Managed Add-on

Export the existing settings and inspect the selected compatible build's schema:

```bash
umask 077
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni > vpc-cni-before.json
jq -r '.addon.configurationValues // "{}"' vpc-cni-before.json > vpc-cni-config.json
: "${VPC_CNI_ADDON_VERSION:?Select a compatible EKS add-on build from the metadata}"
aws eks describe-addon-configuration --region "$EKS_REGION" \
  --addon-name vpc-cni --addon-version "$VPC_CNI_ADDON_VERSION"
```

Review required intermediate upgrade versions and release changes. Edit `vpc-cni-config.json` to retain the intended existing configuration and incorporate only the selected changes. Do not assume a partial payload or a conflict flag preserves every setting automatically. Confirm the CNI's IAM permissions and its configured IRSA/Pod Identity role; IPv6 needs the corresponding permissions.

For an already managed add-on, a reviewed update can use:

```bash
set -eu
VPC_CNI_UPDATE_ID="$(aws eks update-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json --resolve-conflicts PRESERVE \
  --query update.id --output text)"
aws eks describe-update --region "$EKS_REGION" --name "$CLUSTER_NAME" \
  --addon-name vpc-cni --update-id "$VPC_CNI_UPDATE_ID"
```

`PRESERVE` is an explicit conflict-handling choice; verify the resulting environment, images and behavior. Recheck the captured update ID until its status is `Successful`; if it is `Failed` or `Cancelled`, inspect its errors before proceeding. Only then check the resulting add-on and DaemonSet:

```bash
aws eks describe-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni
kubectl -n kube-system rollout status daemonset/aws-node --timeout=10m
```

An accepted API request or an earlier DaemonSet's ready state does not prove this update and network validation have completed.

For an absent managed add-on after installation/ownership preparation, the create operation is separate:

```bash
aws eks create-addon --region "$EKS_REGION" \
  --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni \
  --addon-version "$VPC_CNI_ADDON_VERSION" \
  --configuration-values file://vpc-cni-config.json
```

Do not repeatedly call `create-addon` to turn on individual features, and do not force `OVERWRITE` over an existing customized installation without a migration plan.

### Helm-owned Installation

Pin the whole chart, which also selects the matching init and policy-agent components. Overriding only two image tags does not update the rest of the chart:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm show values eks/aws-vpc-cni --version 1.23.0 > chart-defaults.yaml
helm template aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml > rendered-cni.yaml
```

Prepare `helm-values.yaml` for the actual IP family, CNI ServiceAccount/IAM and selected features. The basic Linux examples in this guide use IPv4. Review the rendered resources before applying:

```bash
helm upgrade --install aws-vpc-cni eks/aws-vpc-cni --namespace kube-system \
  --version 1.23.0 -f helm-values.yaml --wait --timeout 10m
```

These commands assume a clean or Helm-owned installation. Existing EKS-managed or bootstrap-owned resources need a planned ownership migration. EKS partition/registry access and image-pull prerequisites must also match the environment.

### Important Configuration Values

| Setting | Meaning | Baseline/default distinction |
|---|---|---|
| `WARM_IP_TARGET` | Desired free addresses for new ordinary Pod assignments | Unset by default; not a hard maximum |
| `MINIMUM_IP_TARGET` | Floor for total allocated addresses | Unset by default; pair with a positive warm-IP target when used |
| `WARM_ENI_TARGET` | Desired warm ENI capacity | Released default: 1; IP targets override it |
| `WARM_PREFIX_TARGET` | Desired free IPv4 prefixes | Released chart/manifest sets 1; bare daemon documentation says unset |
| `ENABLE_PREFIX_DELEGATION` | Select prefix allocation | Linux chart default: `"false"` |
| `AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG` | Select custom-networking behavior | Default: `"false"` |
| `ENI_CONFIG_LABEL_DEF` | Node label key selecting ENIConfig | Daemon default: `k8s.amazonaws.com/eniConfig`; zone-based examples override it |
| `ENABLE_POD_ENI` | Enable the EC2 Pod-ENI integration | Default: `"false"`; other SGPP prerequisites still apply |
| `POD_SECURITY_GROUP_ENFORCING_MODE` | SGPP routing/SNAT/security-group behavior | Default: `strict` |
| `NETWORK_POLICY_ENFORCING_MODE` | Network-policy behavior while a new Pod's rules are being configured | Default: `standard` |

The two enforcing-mode settings control different systems. Environment values in EKS configuration payloads are strings.

### Custom Networking (ENIConfig)

Create actual Pod subnets and security groups in the intended VPC/AZ, then reference their IDs:

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
  - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: ap-northeast-2b
spec:
  subnet: subnet-0abcdef0123456789
  securityGroups:
  - sg-0123456789abcdef0
```

Enable custom networking and use the node's actual zone label:

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

An explicit ENIConfig node annotation takes precedence over the label. ENIConfig objects alone do not enable custom networking. Plan routing, DNS/security rules, address capacity and workload/node transition; current Pods do not move to a new subnet simply because a new CIDR or ENIConfig exists.

## IP Address Management

### Warm-pool Tuning

Use measured Pod demand and churn, available address space and EC2 API limits. These are alternative example targets, not prescriptions based only on cluster size:

```json
{
  "env": {
    "WARM_IP_TARGET": "2",
    "MINIMUM_IP_TARGET": "4"
  }
}
```

```json
{
  "env": {
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

`MINIMUM_IP_TARGET` is a total allocation floor; `WARM_IP_TARGET` targets free addresses. They take precedence over the ENI/prefix warm-target strategy. With prefix delegation, allocations still happen in prefix-sized units. More warm capacity can reduce allocation waits but consumes addresses, and aggressive changes can increase API calls.

### Adding a Secondary CIDR

First review existing associations, connected-network overlap, VPC CIDR restrictions and subnet/routing requirements:

```bash
VPC_ID=vpc-0123456789abcdef0
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

The following uses illustrative IDs and address space; perform it only as part of the reviewed VPC plan:

```bash
aws ec2 associate-vpc-cidr-block --region "$EKS_REGION" \
  --vpc-id "$VPC_ID" --cidr-block 100.64.0.0/16
aws ec2 describe-vpcs --region "$EKS_REGION" --vpc-ids "$VPC_ID" \
  --query 'Vpcs[0].CidrBlockAssociationSet'
```

Confirm that the new CIDR association is **associated**, rather than still associating, before creating a subnet in it:

```bash
aws ec2 create-subnet --region "$EKS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 100.64.0.0/19 --availability-zone ap-northeast-2a
```

The subnet also needs its intended route table, security rules and CNI selection. Existing Pods keep their current networking until the planned transition. RFC 6598 `100.64.0.0/10` is shared address space, not globally unique private capacity; check overlaps with every connected environment.

### IPv6 Cluster Configuration

IP family is selected at cluster creation and cannot be changed afterward. The official `eksctl` interface uses a **configuration file**, not an `--ip-family` flag. A schema example is:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-example
  region: ap-northeast-2
  version: '1.35'
kubernetesNetworkConfig:
  ipFamily: IPv6
iam:
  withOIDC: true
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
managedNodeGroups:
- name: linux-nitro
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  privateNetworking: true
```

Replace the example version/Region, choose supported node images and review VPC endpoint/access and IAM settings before creation. Add-on versions omitted here resolve through the supported EKS/eksctl path; inspect and pin the required compatible builds for a controlled deployment. `iam.withOIDC` and the managed add-ons/node group reflect the documented eksctl IPv6 prerequisites.

```bash
eksctl create cluster --config-file ipv6-cluster.yaml
```

This audit did not create a cluster. Local CLI help/schema checks used eksctl 0.229.0; they are not a live validation of networking, IAM or the Region's available builds.

IPv6 requires supported Linux Nitro/Fargate paths and prefix allocation; Windows is unsupported. IPv6 Pods may have an egress-only IPv4 helper interface. The policy agent documents that IPv6 policy on the primary interface does not protect that helper's IPv4 traffic. If the design requires removing that path, review `ENABLE_V4_EGRESS`, dependencies and Pod rollout rather than assuming IPv6 policy alone blocks it.

## Network Policy Support

### Native Enforcement

Standard native eBPF policy support was introduced in VPC CNI 1.14. Current EKS documentation lists newer prerequisites for standard/Admin policies; the reviewed 1.23 baseline must still be matched to the cluster and platform.

```json
{
  "enableNetworkPolicy": "true"
}
```

`"enableNetworkPolicy": "true"` is the documented string-valued configuration. Supported EC2 Linux nodes can use this implementation; Fargate and Windows do not use its enforcement. Auto Mode has its own managed implementation. EKS `ClusterNetworkPolicy` Admin/Baseline controls and Auto Mode DNS `ApplicationNetworkPolicy` are extensions, not aliases of standard `NetworkPolicy`.

In standard mode, new Pods initially allow traffic while policy rules are resolved. A stricter startup behavior can be selected deliberately:

```json
{
  "enableNetworkPolicy": "true",
  "env": {
    "NETWORK_POLICY_ENFORCING_MODE": "strict"
  }
}
```

Strict mode requires correct policy coverage for DNS and other required traffic before workloads start. It does not configure SGPP's separate `POD_SECURITY_GROUP_ENFORCING_MODE`.

### NetworkPolicy Example

Prerequisites: the `app` namespace contains controller-managed frontend/backend workloads; backend Pods listen on TCP 8080. AWS currently documents `metadata.ownerReferences` as important for reliable enforcement and requires matching Service/container port numbers (and matching names for named ports).

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

The source Pod selector is limited to the same namespace. This rule isolates selected backend ingress and permits matching frontend traffic to 8080; it does not deny backend egress or authenticate an application user. Consider other matching policies and Admin-tier behavior. Validate both allowed and denied flows with Deployment/Job-managed Pods rather than relying on standalone diagnostic Pods.

### Verification and Diagnostics

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-eks-nodeagent --tail=200
kubectl get networkpolicy -A
kubectl get policyendpoints.networking.k8s.aws -A
```

These are **node-agent** logs; the policy controller runs in the EKS-managed control plane. PolicyEndpoint objects are generated state, not objects to edit/delete casually.

On an authorized Linux node with the installed policy CLI:

```bash
sudo /opt/cni/bin/aws-eks-na-cli ebpf progs
sudo /opt/cni/bin/aws-eks-na-cli ebpf maps
```

The tool is `aws-eks-na-cli`, not `ebpf-sdk list-maps`. Inspect the affected node and distinguish process logs from configured policy-event logs and CloudWatch delivery. Enabling external log delivery also requires the appropriate IAM/configuration.

## Advanced Features

### Security Groups for Pods

The selected security groups must already exist with appropriate DNS, API, application and return-path rules:

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: my-security-group-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
    - sg-0123456789abcdef0
    - sg-0abcdef0123456789
```

An example **EC2** configuration choosing standard SGPP behavior is:

```json
{
  "env": {
    "ENABLE_POD_ENI": "true",
    "POD_SECURITY_GROUP_ENFORCING_MODE": "standard"
  }
}
```

This is not a complete SGPP installation. Verify supported trunking instance types, the cluster role's VPC resource-controller permissions, CNI permissions, subnet capacity and the relevant EKS prerequisites. T-family instances are not supported for trunking merely because they are Nitro-based. Newly created/recreated selected Pods receive the intended setup.

The managed resource controller attaches an **additional trunk ENI** and associates branch ENIs with it. The trunk is not the node's primary `eth0` ENI. A selected Pod uses a branch interface with its security groups; prefix delegation does not increase the branch-Pod limit. Fargate security groups use their separate managed path.

| Mode / feature | Consequence to verify |
|---|---|
| SGPP `strict` | Branch security-group behavior and no Pod source NAT; NodeLocal DNSCache and instance-target LoadBalancer/NodePort with `externalTrafficPolicy: Local` have documented restrictions |
| SGPP `standard` | Supports the documented combined policy/DNS paths; with default external-SNAT behavior, out-of-VPC traffic uses the node primary address/security groups |
| Custom networking plus SGPP | The Pod security groups take precedence over ENIConfig security groups |
| IPv6 | Supported by the EKS service guide under its version/platform conditions, including EC2 CNI 1.16+; the older README feature-table “No” cell must not override that detailed guidance |
| Windows / Auto Mode | This SGPP mechanism is unsupported; Auto Mode has separate node-class networking controls |

Mode changes affect newly launched Pods; plan recreation and verify the traffic path. Do not assume the same security groups govern every packet after SNAT.

### Multiple Interfaces and Multus

VPC CNI 1.20+ has native multi-NIC support for suitable instances with multiple network cards. Its `ENABLE_MULTI_NIC` and Pod NIC configuration are distinct from Multus, and applications must use the additional interfaces to gain their benefits.

Multus is a meta-plugin. AWS's supported Multus arrangement uses VPC CNI as the **primary delegate**; using VPC CNI for higher-order interfaces is unsupported. Additional interfaces need their own compatible plugin, address assignment and lifecycle management.

| Additional-interface requirement | Why it matters |
|---|---|
| Dedicated, identified interface | A hard-coded `eth1` can refer to an interface managed by IPAMD |
| `node.k8s.amazonaws.com/no_manage=true` on the additional ENI | Prevents VPC CNI from managing the Multus interface |
| AWS-assigned/routable addresses and correct subnet/SG/routes | An arbitrary `192.168.1.0/24` allocation is not automatically valid on an EC2 ENI |
| Coordinated IPAM | A shared `host-local` range can allocate duplicates on different nodes |
| Interface-specific policy tests | Extra interfaces and IPv4 helper paths are not automatically covered by every primary-interface policy |

A NetworkAttachmentDefinition's `spec.config` contains the chosen CNI JSON, including its supported version, plugin, actual parent interface and IPAM configuration. The former generic `ipvlan`/`eth1`/`host-local` manifest omitted the prerequisites above and has been replaced by these implementation requirements. This guide does not claim a deployed Multus/IPAM solution.

### Windows

Windows uses the VPC resource-controller IPAM path. Prepare the cluster role permissions, Windows node-role authentication/access entry (`EC2_WINDOWS` where applicable), and Linux/Fargate capacity for CoreDNS. Windows Fargate, Auto Mode, Hybrid Nodes, IPv6, custom networking, SGPP and native VPC-CNI network policy have documented restrictions.

The controller's resulting ConfigMap must include the following Windows IPAM entry. This shows the required data, not an instruction to overwrite a manager-owned ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amazon-vpc-cni
  namespace: kube-system
data:
  enable-windows-ipam: 'true'
```

For a **Helm-owned** installation, Windows prefix targets use different keys from Linux:

```yaml
enableWindowsIpam: 'true'
enableWindowsPrefixDelegation: 'true'
warmWindowsPrefixTarget: 1
warmWindowsIPTarget: 0
minimumWindowsIPTarget: 0
```

Review the matching build's schema, field ownership and resulting ConfigMap. Do not assume a Helm value is accepted unchanged as an EKS add-on configuration property. The Windows chart flags map to `enable-windows-ipam` and `enable-windows-prefix-delegation`; the warm-target fields are also Windows-specific here.

After those prerequisites and AMI/version checks, a node-group command can use:

```bash
eksctl create nodegroup --region "$EKS_REGION" --cluster "$CLUSTER_NAME" \
  --name windows-example --managed --node-type m5.large --nodes 2 \
  --node-ami-family WindowsServer2022FullContainer
```

Windows secondary-IP mode normally uses one ENI and its address-slot limit, not the Linux multi-ENI formula. Prefix delegation and actual kubelet limits need separate sizing.

## Troubleshooting

### IP Allocation and Scheduling

Check Pod events to distinguish scheduling failure from sandbox/CNI allocation failure:

```bash
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=300
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, allocatablePods: .status.allocatable.pods}'
SUBNET_ID=subnet-0123456789abcdef0
aws ec2 describe-subnets --region "$EKS_REGION" --subnet-ids "$SUBNET_ID" \
  --query 'Subnets[].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount}'
```

`allocatablePods` is kubelet scheduling capacity, not current IP utilization. Subnet available-address count does not show whether a contiguous `/28` is available. Check IPAMD logs, allocation mode, warm targets, ENI limits, API errors and the affected node before choosing a remedy.

### ENI Count

```bash
INSTANCE_ID=i-0123456789abcdef0
aws ec2 describe-instances --region "$EKS_REGION" --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,AttachedENIs:length(NetworkInterfaces)}'
aws ec2 describe-instance-types --region "$EKS_REGION" --instance-types m5.large \
  --query 'InstanceTypes[].NetworkInfo.{MaxENI:MaximumNetworkInterfaces,IPv4PerENI:Ipv4AddressesPerInterface}'
```

The original projection counted a nested list of interfaces rather than the interfaces themselves. The corrected query reports a count per instance. Multiple cards, unmanaged/trunk interfaces and instance-specific limits still need interpretation.

### Introspection and Metrics

Select the affected node's actual `aws-node` Pod and keep this forwarding session open:

```bash
kubectl -n kube-system get pods -l k8s-app=aws-node -o wide
AWS_NODE_POD=aws-node-example
kubectl -n kube-system port-forward "pod/$AWS_NODE_POD" 61678:61678 61679:61679
```

From another local terminal:

```bash
curl --fail http://127.0.0.1:61679/v1/enis
curl --fail http://127.0.0.1:61678/metrics
```

IPAMD introspection defaults to loopback **61679**; Prometheus metrics use **61678**. `/v1/enis` is not a metrics endpoint. These commands use local curl through the Kubernetes forwarding path; they do not require a curl binary inside the CNI image.

### Classify Errors Before Changing the Cluster

| Observation | Investigate before acting |
|---|---|
| `InsufficientFreeAddressesInSubnet` | Actual free addresses, warm allocation, selected subnets and planned capacity expansion |
| `InsufficientCidrBlocks` | Contiguous prefix availability/fragmentation and subnet reservations |
| ENI/SG limit error | The specific quota, instance/interface type and objects in use; avoid removing unrelated security groups |
| ENI creation failure | Detailed AWS error, CNI credential role, permissions/conditions, quota and API connectivity |
| Waiting for a Pod IP | IPAMD state, controller/API delays, throttling, sandbox events and address readiness |

Restarting IPAMD, enlarging an instance or granting more node-role permissions is not a universal remedy. Capture evidence first and apply a reviewed change to the component that actually owns the failing operation.

## Best Practices

Plan subnet capacity from expected Pods, warm pools, growth and failure/replacement overlap. A `/19` or RFC 6598 range is an example design choice, not a universal requirement. Associate new CIDRs, create the necessary subnets/routes and plan CNI/workload adoption together.

Choose one warm-pool strategy. An IPv4 prefix example using free-IP and total-IP targets is:

```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_IP_TARGET": "5",
    "MINIMUM_IP_TARGET": "10"
  }
}
```

Do not interpret an additional `WARM_PREFIX_TARGET` as an independent effective target when those IP targets are set. Monitor allocation failures and actual resource constraints rather than inferring safety solely from cluster size.

### Metrics and Alerts

The released IPAMD code exports `awscni_total_ip_addresses`, `awscni_assigned_ip_addresses` and the counter `awscni_no_available_ip_addresses`. Total/assigned gauges describe the **IPAMD allocated pool**, not total VPC subnet space. Small warm targets can legitimately produce a high assigned/total ratio; cooldown, branch interfaces, IP family and kubelet capacity need additional context.

Prometheus Operator CRDs and selectors must already be configured. For a Helm-owned CNI, the chart can create a PodMonitor with this **IPv4-cluster example**:

```yaml
podMonitor:
  create: true
  labels:
    release: prometheus
  interval: 30s
  relabelings:
  - sourceLabels:
    - __meta_kubernetes_pod_node_name
    targetLabel: node
  - targetLabel: cluster
    replacement: example-cluster
  - targetLabel: ip_family
    replacement: ipv4
  - targetLabel: job
    replacement: aws-vpc-cni
```

Replace the example cluster label, adapt the `release` selector and set IP-family labels truthfully; labels do not detect the cluster's family. The chart scrapes the Agent's named `metrics` port and the enabled policy agent's `agentmetrics` port. An EKS-managed add-on needs an independently configured scraper/PodMonitor instead of installing a second CNI Helm release.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vpc-cni-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: vpc-cni
    rules:
    - record: vpc_cni:allocated_ipv4_pool_utilization:ratio
      expr: (awscni_assigned_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} / awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"})
        and (awscni_total_ip_addresses{job="aws-vpc-cni",ip_family="ipv4"} > 0)
    - alert: CniHighAllocatedIPv4PoolUtilization
      expr: vpc_cni:allocated_ipv4_pool_utilization:ratio > 0.9
      for: 5m
      labels:
        severity: info
      annotations:
        summary: Most currently allocated IPAMD IPv4 addresses are assigned
        description: This is allocated-pool utilization, not subnet exhaustion. Check
          warm targets, assignment failures and available subnet space.
    - alert: CniIPAssignmentFailures
      expr: increase(awscni_no_available_ip_addresses{job="aws-vpc-cni"}[5m]) > 0
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: IPAMD could not assign an available IP address
    - alert: CniMetricsScrapeFailed
      expr: up{job="aws-vpc-cni"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: A known CNI metrics endpoint cannot be scraped
```

The pool ratio is limited to IPv4 and a positive observed denominator. It is an informational tuning signal, not proof of subnet exhaustion. The assignment-failure counter signals an actual failed allocation. A failed scrape is different from a disappeared target; compare expected node/component inventory separately. No data is not healthy zero. Tune thresholds, labels and notification routing in the actual monitoring environment.

## References

- [VPC CNI 1.23.0 documentation](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/README.md)
- [VPC CNI Helm values](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/values.yaml)
- [Chart version metadata](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/charts/aws-vpc-cni/Chart.yaml)
- [Released CNI manifest](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/config/master/aws-k8s-cni.yaml)
- [IPAMD implementation](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/ipamd.go)
- [IPAMD introspection server](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/introspect.go)
- [IPAM datastore](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/pkg/ipamd/datastore/data_store.go)
- [IPAMD metric definitions](https://raw.githubusercontent.com/aws/amazon-vpc-cni-k8s/v1.23.0/utils/prometheusmetrics/prometheusmetrics.go)
- [Network policy agent 1.4.1](https://github.com/aws/aws-network-policy-agent/blob/v1.4.1/README.md)
- [AWS Helm chart index](https://aws.github.io/eks-charts/index.yaml)
- [EKS security groups for Pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [SGPP operating considerations](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [EKS Multus support boundaries](https://docs.aws.amazon.com/eks/latest/userguide/pod-multus.html)
- [EKS Windows networking](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)
- [EKS IPv6 support](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)
- [eksctl IPv6 configuration](https://docs.aws.amazon.com/eks/latest/eksctl/vpc-ip-family.html)
- [CNI IAM configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)
- [EKS VPC CNI management](https://docs.aws.amazon.com/eks/latest/userguide/managing-vpc-cni.html)
- [EKS network policy conditions](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [Enable EKS network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Prefix allocation and Pod-capacity limits](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)

## Quiz

Check your understanding with the [VPC CNI Quiz](../quizzes/networking/01-vpc-cni-quiz.md).
