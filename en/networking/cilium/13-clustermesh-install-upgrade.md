# Part 13: Versions, Install/Upgrade and Cluster Mesh

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

This chapter answers three operational questions that the earlier parts only touch on: which Cilium version has which feature and at what maturity, how to install and upgrade it safely (with EKS-specific details), and how Cluster Mesh works from the control plane up. The repository previously had only a short Cluster Mesh section inside [IPAM and Network Policies](04-ipam-policy.md); this chapter is the in-depth guide.

Related parts: [Introduction](01-introduction.md), [Networking](03-networking.md), [IPAM](10-ipam-deep-dive.md), [BGP, LB and Egress](11-bgp-lb-egress-edge.md), [mTLS, encryption and identity](12-mtls-encryption-identity.md).

## Table of Contents

1. Release train and tooling versions
2. Feature-by-version matrix (1.17 to 1.21 pre-release)
3. What changed from 1.20.1 to 1.20.2
4. Compatibility and requirements
5. Installing with Helm (OCI chart, verification)
6. EKS installation specifics
7. Upgrade and rollback procedure
8. Day-2 configuration: drift detection, CiliumNodeConfig, identity migration
9. Cluster Mesh architecture
10. Cluster Mesh configuration
11. Global services, affinity and EndpointSlice sync
12. MCS-API (Multi-Cluster Services)
13. Cross-cluster policy
14. Cluster Mesh on EKS
15. Labs
16. Version Delta, Troubleshooting, Validation Limits and Sources

---

## 1. Release Train and Tooling Versions

Cilium ships three independently versioned artifacts that are easy to confuse.

| Artifact | Current at this review | Notes |
|---|---|---|
| Cilium (agent, operator, Helm chart) | 1.20.2 (2026-09-16) | Chart `version` and `appVersion` are both 1.20.2 in the v1.20.2 tree (`install/kubernetes/cilium/Chart.yaml`) |
| Cilium CLI (`cilium`) | 0.20.1 (2026-09-24) | 0.20.1 changes are dependency/CI only and bump the Cilium dependency to v1.20.2 |
| Hubble CLI (`hubble`) | 1.20.2 (2026-10-07) | Previous tag was 1.19.4; no 1.20.0/1.20.1 Hubble CLI tags exist. 1.20.2 fixes `compact` output for policy-verdict events with the default field mask |
| Backport branches | 1.19.8 and 1.18.14 (both 2026-09-16) | Also released the same day as 1.20.2 |
| Pre-release | 1.21.0-pre.3 (2026-10-02) | `v1.21.0-pre.1` was never published; the pre.2 changelog covers pre.0 to pre.2 |

The Cilium CLI is a separate release train from the agent; pass `--version` explicitly when you want a specific agent version.

Release history around this review:

| Release | Date | Remark |
|---|---|---|
| v1.20.0 | 2026-07-29 | 2660 commits (release body) |
| v1.20.1 | 2026-08-18 | Cluster Mesh documentation overhaul, endpoint fix for CIDR policy handling after agent restart |
| v1.20.2 | 2026-09-16 | Latest stable; see section 3 |
| v1.21.0-pre.0 | 2026-08-03 | |
| v1.21.0-pre.2 | 2026-09-09 | |
| v1.21.0-pre.3 | 2026-10-02 | Latest pre-release |

Treat 1.21.0-pre.x as a preview: option names, defaults and upgrade notes can still move.

## 2. Feature-by-version Matrix (1.17 to 1.21 Pre-release)

Maturity words are quoted from the release notes or in-tree documentation (`.. include:: /beta.rst` banners) of the cited version. A dash means the feature does not exist yet.

### 2.1 Headline features

| Feature | 1.17 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|---|
| Min kernel | 5.4 | 5.10 (4.18 on RHEL 8.10) | 5.10 | 5.10 | 5.10 (LLVM >= 21.1 for native build) |
| Tested Kubernetes | see 1.17 docs | up to 1.33 (go libs 1.33) | 1.35 libs | 1.33 to 1.36 | 1.34 to 1.37 |
| Gateway API CRDs | v1.2.1 | v1.3.0 | v1.4 | v1.6.1 | v1.6.1 |
| Helm OCI chart `quay.io/cilium/charts/cilium` | no | no | yes | yes (recommended) | yes |
| MCS-API | beta (introduced) | beta, EndpointSlice mirroring | beta, CRDs `v1alpha1`, auto CRD install | stable, `v1beta1` (`v1alpha1` still supported) | `v1beta1`; mirrored EndpointSlice name fixes |
| Cluster Mesh policy default scope | all clusters | all clusters; `policy-default-local-cluster` flag introduced (default false) | local cluster only (default true) | local cluster only; `cluster-mesh` entity | local cluster only |
| `clustermesh.apiserver.tls.authMode` | `legacy` (default) | `legacy` (default) | `migration` (default) | `migration` (default) | `cluster` (new `cluster-strict`) |
| KVStoreMesh | default on since 1.16 | `kvstoremesh.enabled` deprecated | on by default | on by default, value deprecated | always on, value removed |
| Double Write identity allocation | introduced (beta) | beta | beta | beta | beta; `cilium-dbg preflight migrate-identity` deprecated |
| Multi-pool IPAM | beta | beta (+KVStore, IPsec, tunnel) | stable | stable; cluster-pool to multi-pool in-place migration | Azure IPAM moves to multi-pool; `CiliumPodIPPool` API `cilium.io/v2` + `reservedRanges` |
| ENI IPv6 IPAM | - | - | - | beta | IPv6 masquerade off by default in ENI mode |
| Mutual authentication (SPIFFE/SPIRE) | exists | exists | disabled by default | deprecated | removed (port 4250 dropped from the firewall table) |
| ztunnel | - | - | beta | beta (internal CA or SPIRE) | beta (`encryption-ztunnel.rst` in the 1.21 tree still carries the `beta.rst` banner) |
| Kafka-aware L7 policy | supported | deprecated | deprecated | removed | removed |
| Envoy Go extensions (proxylib) | supported | deprecated | deprecated | removed | removed |
| BGPv1 `CiliumBGPPeeringPolicy` | supported | deprecated | removed | - | - |
| ConfigMap drift detection (`configDriftDetection`) | - | backported to 1.18.x patch releases | backported to 1.19.x patch releases | native in 1.20.0 | same |
| Datapath mode | `veth` (default), `netkit` (beta), `netkit-l2`, `lb-only` | veth, netkit | BIG TCP in tunnels, PLPMTUD | `bpf.datapathMode=auto` (netkit if supported, else veth; default still veth) | unchanged |

### 2.2 Version highlights by release

**1.17** (2025-02, 2761 commits): QoS Pod annotations (Guaranteed/Burstable/BestEffort egress priority); MCS-API introduced; per-protocol (TCP/UDP) service load balancing; per-Service LB algorithm (maglev/random); `loadBalancerSourceRanges` deny-list mode; AWS static IP via tags and single-IP multi-pool pools; dynamic MTU; `CiliumCIDRGroup` label selection; HTTP policy on port ranges; Gateway API 1.2.1 with static Gateway addresses; dynamic Hubble metrics ConfigMap; Double Write identity allocation mode (migration between KVStore and CRD).

**1.18** (3298 commits): LB control-plane redesign; IPsec VXLAN-in-IPsec; multiple egress gateways (also IPv6 ranges); bandwidth ingress rate limit; IPv6 underlay for tunnels; Hubble policy names and `policy log` field; `cluster` entity can be restricted to the local cluster; apiserver failover via `k8s.apiServerURLs`; BGP CRDs, `CiliumCIDRGroup` and `CiliumLoadBalancerIPPool` promoted to stable `cilium.io/v2`; AWS prefix delegation in ENI mode; Gateway API 1.3.0 and `CiliumGatewayClassConfig`; kernel minimum raised to 5.10. Behavior changes: in ENI mode the default of `enableIPv4Masquerade` flipped from true to false (use `upgradeCompatibility` below 1.18 or set it explicitly); the operator needs `ec2:DescribeRouteTables` in ENI mode; `io.cilium.k8s.policy.serviceaccount` joined the default identity labels, which causes temporary identity churn on upgrade.

**1.19** (2934 commits): policy default local cluster enabled; mutual authentication disabled by default; multi-pool IPAM stable; OCI Helm charts; ztunnel beta; strict encryption modes for IPsec and WireGuard; Kafka policy fields deprecated and `FromRequires/ToRequires` removed; BGPv1 removed; MCS-API CRDs installed automatically (`clustermesh.mcsapi.installCRDs`); certificate generation reworked so the CronJob is no longer a Helm hook (Argo CD and `--wait` friendly); Gateway API 1.4; GAMMA GRPCRoute.

**1.20** (2026-07-29): Gateway API 1.6.1 (ListenerSet, BackendTLSPolicy, TCPRoute/UDPRoute, ExternalAuth, CORS); datapath plugins; `bpf.datapathMode=auto`; egress gateway IPv6 egress IP; BGP via `cilium-dbg shell -- bgp/*` and GoBGP 4.6.1; ENI IPv6 (beta); cluster-pool to multi-pool in-place migration; `PreferSameZone`/`PreferSameNode` traffic distribution; Maglev weights via `service.cilium.io/weight` (0 drains); MCS-API stable; `cluster-mesh` policy entity; Kubernetes ClusterNetworkPolicy admin/baseline tiers; ConfigMap drift detection; `cilium-cni` binary reduced from 77 MB to 16 MB; K8s 1.36, Envoy 1.37.x. **Removed in 1.20**: Envoy Go extensions (proxylib), Kafka-aware L7 policy, `CiliumNodeConfig` `v2alpha1`, `clustermesh.enableMCSAPISupport` (use `clustermesh.mcsapi.enabled`), certificate-as-values for Cluster Mesh, `cilium-docker-plugin`, the old `encryption.strictMode.*` flags (now `encryption.strictMode.egress.*`), `--node-port-algorithm`/`--node-port-mode`, `--ces-slice-mode`, `encryption.ipsec.interface`. **Behavior changes**: `bpf.tproxy=true` is incompatible with netkit; in-cluster NodePort access from Pods without SocketLB (or with `socketLB.hostNamespaceOnly=true`) is now load-balanced at the client Pod, so both client egress and backend ingress policy must allow it; empty `CiliumNetworkPolicy`/`CiliumClusterwideNetworkPolicy` (no `spec`/`specs`) are rejected at admission; Cluster Mesh auto-generated certificates default to one year of validity with a CronJob regenerating every four months; certgen enforces CA validity >= leaf validity (`certgen.enforceCAValidityThroughoutLeavesDuration=false` disables the check).

**1.21 pre-release** (v1.21.0-pre.3): delta xDS (`envoy.xdsMode=delta-split`); Cilium Network Driver (DRA, SR-IOV); Gateway API session persistence; AWS managed prefix lists in policy; KVStoreMesh unconditionally enabled; Cluster Mesh `authMode` default `cluster`; mutual authentication removed; `encryption.nodeEncryption` (WireGuard) deprecated with removal planned for 1.22; `--aws-use-primary-address` operator flag removed (use `eni.nodeSpec.usePrimaryAddress`); `cec.cilium.io/*` annotations from Gateway/GAMMA infrastructure metadata are no longer propagated to generated `CiliumEnvoyConfig`; the operator performs automatic storage-version migration of obsolete objects; Kubernetes libraries 1.37. The pre.2 release note "Enable BPF masquerading by default" is not reflected in the pre.3 tree (see Validation Limits).

## 3. What Changed from 1.20.1 to 1.20.2

`gh api repos/cilium/cilium/compare/v1.20.1...v1.20.2` reports 204 commits (the API truncates the file list at 300, so the changed-file count is not reliable). The commit list was not audited for feature-like entries, so read the release notes before assuming the upgrade is low risk; several fixes matter for specific setups.

| Area | Fix |
|---|---|
| AWS ENI IPAM | Operator released prefix-delegated IPs as individual IPs even when in use; allocation failed when a subnet ran out of prefixes; agent crash at startup in ENI mode when `ipv4NativeRoutingCIDR` is a secondary VPC CIDR; IPv6 ENI routing fixes (health endpoint, ingress, IPsec); restored ENI endpoint routing rules after a masquerade config change; reduced EC2 IMDS load |
| Cluster Mesh | Rare race that left a removed remote cluster connected; stronger validation of service backends ingested from Cluster Mesh; clustermesh-apiserver etcd user management did not revoke stale roles on config change (Helm chart users are unaffected) |
| Upgrade | Clusters created with Cilium 1.15 or earlier failed to upgrade because the `CiliumNodeConfig` `v2alpha1` CRD version was dropped. Use 1.20.2 or later when upgrading such clusters to 1.20 |
| Ignored options | Five options that were accepted but silently ignored now work: `vtep-sync-interval`, `enable-xt-socket-fallback`, `eni-delete-on-termination` with a custom CNI config, Helm `enableIdentityMark` outside chaining mode, `lb-retry-backoff-max`; four Hubble settings that never reached their sink were also fixed |
| Datapath | Fixes for fragmented UDP misclassified as WireGuard, ICMP error checksum on SNAT LB traffic, DSR recovery and PMTU ICMP source, L2 announcements with `externalTrafficPolicy: Local`, LocalRedirectPolicy regressions, `policy-deny-response: icmp` egress deny metrics |
| Policy | A Pod created right after a NetworkPolicy change could show a stale revision for up to two minutes; concurrent policy-map crash with named ports; identities lingering twice as long as expected |
| Gateway API | `HTTPRoute` ExternalAuth now fails closed on an invalid `backendRef`; docs state that Gateway API needs iptables plus netfilter TPROXY modules when `bpf.tproxy` is false (the default) |
| BGP | `defaultGateway` peer auto-discovery picked the wrong routing table |

Image and chart bumps in 1.20.2: certgen v0.4.9 to v0.4.11; Envoy v1.37.5 to v1.37.6; hubble-ui v0.13.5 to v0.13.6; SPIRE 1.15.2 to 1.15.3. The `values.yaml` diff contains only image tags and one schema annotation, and the `enable-identity-mark` ConfigMap key is now rendered only when `enableIdentityMark` is set.

Documentation changes in 1.20.2: two entries were removed from the required kernel configuration list in `system_requirements.rst` (`CONFIG_CRYPTO_USER_API_HASH` and `CONFIG_INET_XFRM_MODE_TUNNEL`), and the Cluster Mesh introduction gained a "Security" section: all clusters in a mesh form a single trust domain, so connect only mutually trusted clusters with equivalent security postures.

Recommendation: use `--version 1.20.2` for ENI users, for Cluster Mesh deployments, and for any cluster created with Cilium 1.15 or earlier.

## 4. Compatibility and Requirements

### 4.1 Version compatibility

| Item | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|
| Kubernetes (tested) | 1.33, 1.34, 1.35, 1.36 | 1.34, 1.35, 1.36, 1.37 |
| Linux kernel | >= 5.10 (RHEL 8.10: 4.18) | >= 5.10 |
| clang/LLVM (native agent build only) | >= 18.1 | >= 21.1 |
| Gateway API CRDs | v1.6.1 required | v1.6.1 |
| Helm chart `kubeVersion` | `>= 1.21.0-0` (the chart constraint, not the tested range) | same |
| Cilium CLI | 0.20.1 | n/a |
| Hubble CLI | 1.20.2 | n/a |

Feature-specific kernel minimums from the 1.20.2 system requirements: multicast on AMD64 >= 5.10 and on AArch64 >= 6.0; IPv6 BIG TCP >= 5.19; IPv4 BIG TCP >= 6.3; netkit >= 6.8 with `CONFIG_NETKIT=y`. A 1.19 note: IPsec plus kube-proxy replacement plus BPF masquerade automatically enables BPF host routing, which requires the kernel fix for CVE-2025-37959.

Cluster Mesh adds another constraint: the Cilium versions of all connected clusters must differ by no more than one minor release (for example 1.19.x can join 1.18.x and 1.20.x, but not 1.17.x).

### 4.2 Ports

Open these between nodes by security-group reference or private CIDR only (never `0.0.0.0/0`):

| Port | Purpose |
|---|---|
| UDP 8472 | VXLAN tunnel |
| UDP 6081 | Geneve tunnel |
| TCP 4240 plus ICMP type 8/0 | Health checks |
| TCP 4244 | Hubble server |
| TCP 4245 | Hubble Relay |
| UDP 51871 | WireGuard |
| ESP (IP protocol 50) | IPsec (AWS security groups block ESP unless a rule allows it) |
| TCP 4250 | Mutual authentication (present in 1.20 docs; removed from the 1.21 docs) |
| TCP 2379 | clustermesh-apiserver between clusters |

### 4.3 Gateway API CRDs

Cilium 1.20 requires Gateway API CRDs v1.6.1 (`gateway_api_version = 'v1.6.1'` in `Documentation/conf.py`, `sigs.k8s.io/gateway-api v1.6.1` in `go.mod`). The Helm chart does not install them. Required CRDs: GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, BackendTLSPolicy, TLSRoute. Optional (the feature stays disabled if absent): TCPRoute, UDPRoute, ListenerSet. Prerequisites: `kubeProxyReplacement=true`, `l7Proxy=true`, and iptables plus TPROXY modules unless `bpf.tproxy=true` (beta). Apply with `kubectl apply --server-side`.

TLSRoute trap: if you already use TLSRoute, install the experimental-channel TLSRoute v1.6.1, which still carries `v1alpha2`. Installing the standard-channel v1.6 TLSRoute makes existing TLSRoute objects unreadable (they effectively disappear). Back up the objects first (`kubectl get tlsroutes -A -o yaml`).

## 5. Installing with Helm

The Helm chart is available from two locations:

| Location | Status |
|---|---|
| `oci://quay.io/cilium/charts/cilium` | Documented as recommended since 1.19; charts are cosign-signed and can be pinned by digest |
| `https://helm.cilium.io/` (`helm repo add cilium`) | Classic repository, fully supported |

Chart versions have no `v` prefix (`--version 1.20.2`); image tags do. OCI registries do not support `helm search`; list versions with `crane ls quay.io/cilium/charts/cilium`. Verify a chart signature:

```bash
cosign verify \
  --certificate-identity-regexp='https://github.com/cilium/cilium/.*' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  quay.io/cilium/charts/cilium:1.20.2
```

Keep values in a file under version control and install with `-f values.yaml`; do not rely on a pile of `--set` flags, because section 7 requires you to re-supply values on every minor upgrade.

## 6. EKS Installation Specifics

### 6.1 Which mode

| Mode | Helm | Datapath / IPAM | Notes |
|---|---|---|---|
| ENI (upstream default for EKS) | `eni.enabled=true` | Native routing (the chart defaults `routingMode` to native when `eni.enabled`), AWS ENI IPAM, Kubernetes CRD datastore | Pods get VPC-routable IPs; needs EC2 API privileges for the operator; `aws-node` must not run on Cilium nodes |
| Overlay | omit `eni.enabled` (chart default is tunnel/VXLAN) | VXLAN, cluster-pool IPAM | More Pods per node than the ENI limit; Pod-to-VPC traffic is SNAT'd to the node IP; the EKS API server cannot route to overlay Pod IPs, so webhooks must be host-networked or reached via a Service/ingress; flush the `AWS-SNAT-CHAIN-0/1` and `AWS-CONNMARK-CHAIN-0/1` iptables chains left by VPC CNI |
| Chaining on VPC CNI | `cni.chainingMode=aws-cni`, `cni.exclusive=false`, `enableIPv4Masquerade=false`, `routingMode=native` | VPC CNI does networking, Cilium adds policy/visibility | Requires VPC CNI >= 1.11.2; restart existing Pods after enabling. Chaining limitations are listed upstream (`cni-chaining-limitations.rst`); read them before choosing this mode |
| EKS Hybrid Nodes | AWS-built chart `oci://public.ecr.aws/eks/cilium/cilium` | VXLAN overlay, cluster-pool | See 6.4 |
| EKS Auto Mode | not supported | n/a | See 6.5 |

### 6.2 ENI mode install

Cilium manages ENIs, so keep VPC CNI from running on nodes that Cilium manages. Patch the `aws-node` DaemonSet with a node selector no node carries (upstream command, verbatim):

```bash
kubectl -n kube-system patch daemonset aws-node --type='strategic' \
  -p='{"spec":{"template":{"spec":{"nodeSelector":{"io.cilium/aws-node-enabled":"true"}}}}}'
```

Taint managed node groups so application Pods wait for Cilium (upstream recommendation):

```yaml
# eksctl ClusterConfig fragment
managedNodeGroups:
- name: ng-1
  taints:
  - key: "node.cilium.io/agent-not-ready"
    value: "true"
    effect: "NoExecute"
```

Values file (all keys exist in the 1.20.2 chart; `eni.enabled=true` sets the operator image, endpoint routes, CiliumNode management and IPv4 masquerade defaults, and the chart validation fails if `ipam.mode=eni` is set without `eni.enabled=true`):

```yaml
# values-eks-eni.yaml  (Cilium 1.20.2)
eni:
  enabled: true
kubeProxyReplacement: true
k8sServiceHost: <EKS-API-ENDPOINT-FQDN-without-scheme>
k8sServicePort: 443
cluster:
  name: eks-a
  id: 1   # keep below 128 in ENI mode (see the cluster.id note in the Helm reference)
```

```bash
helm install cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f values-eks-eni.yaml
```

Notes:

- With kube-proxy replacement you must set `k8sServiceHost` and `k8sServicePort` before kube-proxy is removed; otherwise the agent cannot reach the API server.
- The operator needs EC2 privileges (see the upstream `ec2privileges` section) and, since 1.18, `ec2:DescribeRouteTables`.
- 1.18 flipped the ENI-mode default of `enableIPv4Masquerade` to false. If you upgrade a pre-1.18 ENI cluster and rely on masquerade, set it explicitly or use `upgradeCompatibility`.
- ENI IPv6 is beta in 1.20 (`eni.rst`). One upstream page (`requirements-eks.rst`) still says ENI is IPv4 only; follow the release notes and `eni.rst`.
- Use 1.20.2 for ENI: it fixes prefix-delegation release, subnet-out-of-prefixes allocation and the secondary-VPC-CIDR native-routing crash.
- Pod IPs come from the `default` pool; in ENI mode `CiliumPodIPPool` and the `ipam.cilium.io/ip-pool` annotation are not used (`eni.rst`). See [IPAM](10-ipam-deep-dive.md).

### 6.3 AMIs

The 1.20.2 system requirements list Amazon Linux 2 and Bottlerocket as supported ("all" versions), Ubuntu >= 20.04, RHEL >= 8.6, Talos >= 1.5.0 and Flatcar (with a DHCP caveat for ENI). Amazon Linux 2023 is not listed by name; its kernel is newer than the 5.10 minimum, but that is an inference, not an upstream statement. AWS's Hybrid Nodes documentation notes that Ubuntu 20.04 and RHEL 8 do not meet the kernel requirement for Cilium 1.18.3.

### 6.4 EKS Hybrid Nodes

AWS supports Cilium on hybrid nodes only through the AWS-maintained build in the public ECR repository `oci://public.ecr.aws/eks/cilium/cilium` (versions such as `1.17.9-0` and `1.18.3-0` appear in the AWS documentation; the list of newer AWS builds was not verified in this review). VPC CNI is incompatible with hybrid nodes. The AWS default configuration is a VXLAN overlay with cluster-pool IPAM; the pool CIDR must equal the EKS remote Pod network, must not overlap node, VPC or Service CIDRs, and must not be changed after deployment. Pin the agent and operator to hybrid nodes with the `eks.amazonaws.com/compute-type In hybrid` affinity, and use BGP Control Plane to make Pod CIDRs routable. The AWS support table lists Cilium Ingress and Cilium Gateway as supported for hybrid nodes (default configurations; see the AWS [CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html) and [Ingress](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-ingress.html) pages). `envoy.enabled: false` appears only in the AWS baseline example values; because Cilium Ingress/Gateway and L7 network policy need Envoy, enable it if you use them, following the AWS ingress page. Cilium is not supported on AWS-cloud nodes in that setup.

### 6.5 EKS Auto Mode

EKS Auto Mode does not work with Cilium. AWS documents that Auto Mode does not support alternate CNI plugins or network policy plugins (EKS user guide, "alternate CNI plugins" and "auto networking" pages), and the upstream Cilium documentation has no Auto Mode page. Use a standard managed node group or self-managed nodes for Cilium.

### 6.6 Exposure rule for this repository

Nothing in this chapter requires a public listener. If clients outside the VPC must reach an application, use CloudFront with a VPC origin to an internal ALB/NLB. The clustermesh-apiserver Service must also be internal (section 14).

## 7. Upgrade and Rollback Procedure

### 7.1 Rules

1. Only consecutive minor upgrades and rollbacks are tested (1.19 to 1.20 and back). Do not skip a minor.
2. First move to the latest patch of your current minor, so that a rollback target exists with all fixes.
3. Upgrade all components (agent, operator, Hubble Relay, clustermesh-apiserver) to the same version; do not upgrade only the agent.
4. L3/L4 traffic sees little or no impact; connections through user-space proxies (L7 policy, Ingress, Gateway API, Envoy) are disrupted and clients must reconnect. New policy rules are postponed on a node until its agent is back.
5. Never use `helm upgrade --reuse-values` across minor versions: it ignores the new chart defaults and can render broken manifests. `--reuse-values` is acceptable only when the chart version is unchanged (for example the Cluster Mesh setup upgrade later in this chapter).
6. Set `upgradeCompatibility` to the minor you originally installed (not the one you are upgrading from). It pins old defaults in the rendered ConfigMap; for example it restores the pre-1.18 ENI masquerade default.
7. For clusters created with 1.15 or earlier, upgrade to 1.20.2 or later, not 1.20.0/1.20.1.

### 7.2 Procedure

```bash
# 0. Save and review current values for renamed/removed keys
helm get values cilium -n kube-system -o yaml > old-values.yaml

# 1. Pre-flight: pre-pulls the new image on every node and validates existing CNPs
helm install cilium-preflight oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system \
  --set preflight.enabled=true --set agent=false --set operator.enabled=false
#   (add k8sServiceHost/k8sServicePort when kube-proxy replacement is on)
kubectl -n kube-system get ds cilium-pre-flight-check   # READY must equal the node count
kubectl -n kube-system get deploy cilium-pre-flight-check   # must be 1/1
kubectl -n kube-system logs deployment/cilium-pre-flight-check -c cnp-validator --previous
helm delete cilium-preflight -n kube-system

# 2. Upgrade (NO --reuse-values); 1.19 is the minor you installed originally in this example
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f old-values.yaml --set upgradeCompatibility=1.19

# 3. Watch
kubectl -n kube-system rollout status ds/cilium
kubectl -n kube-system rollout status deploy/cilium-operator
cilium status --wait
```

A pre-flight Deployment that stays at `READY 0/1` means at least one existing CiliumNetworkPolicy fails validation under the new version; fix the policy before upgrading.

### 7.3 Rollback

```bash
helm history cilium -n kube-system
helm rollback cilium <REVISION> -n kube-system
# or, for the DaemonSet only:
kubectl -n kube-system rollout undo daemonset/cilium
```

If you already used new-minor features (new CRs, ConfigMap opt-ins), read the version's upgrade notes before rolling back; a rollback restores the old manifests but not objects the new version created.

### 7.4 CRD handling

| CRD family | Who installs/updates it | Action |
|---|---|---|
| Cilium CRDs (`cilium.io`) | The operator/agent register and update them at start | None, but verify with `kubectl get crd \| grep cilium.io` after upgrade. 1.20 removed `CiliumNodeConfig` `v2alpha1`; use `cilium.io/v2` |
| Gateway API | You (manual, `kubectl apply --server-side`) | Match the version in section 4.3; back up TLSRoute first |
| MCS-API (`multicluster.x-k8s.io`) | Chart, when `clustermesh.mcsapi.enabled=true`, unless `clustermesh.mcsapi.installCRDs=false` (since 1.19) | Set `installCRDs=false` if another controller owns them |
| Obsolete stored versions | **[1.21 pre-release]** the operator migrates storage versions automatically | `CiliumPodIPPool` `v2` becomes the storage version |

### 7.5 Per-minor upgrade actions to check

Always read the "Upgrade Notes" for the target minor. Items called out above that commonly bite: ENI masquerade default and `ec2:DescribeRouteTables` (1.18); identity label churn from the added service-account label (1.18); `policy-default-local-cluster` flips to true (1.19, see section 13); mutual authentication disabled by default (1.19); removed options and Kafka/proxylib removal (1.20); `bpf.tproxy` with netkit and NodePort client-side load balancing (1.20); `authMode=cluster` default and the removal of the `kvstoremesh.enabled` value (1.21 pre-release).

## 8. Day-2 Configuration

### 8.1 ConfigMap drift detection

Many options only take effect after an agent restart. After editing the `cilium-config` ConfigMap (through `helm upgrade` or `cilium config set`), the running agent can differ from the ConfigMap. Drift detection makes that observable. It is native in 1.20.0 and was backported to the 1.18.x and 1.19.x patch releases (it is present in the v1.18.14 and v1.19.8 charts but not in v1.18.0 or v1.19.0).

```yaml
configDriftDetection:
  enabled: true        # enable-dynamic-config: watch the ConfigMap
  driftChecker: true   # enable-drift-checker: compare desired vs active
  ignoredKeys: []      # for example ["devices"] for keys that are intentionally different
```

The agent logs a warning per mismatched key and exposes the gauge `cilium_drift_checker_config_delta`. `0` means in sync; greater than 0 means the agent has not applied the current ConfigMap and needs a restart. Alert on `cilium_drift_checker_config_delta > 0` for longer than your rollout window.

`cilium config set <key> <value>` edits the ConfigMap and restarts agents by default; pass `--restart=false` to defer the restart and let the drift gauge show the pending change.

### 8.2 CiliumNodeConfig (per-node overrides)

`CiliumNodeConfig` (`apiVersion: cilium.io/v2`, namespace `kube-system`) overrides ConfigMap/agent keys on nodes matched by `spec.nodeSelector` (an empty selector `{}` matches all). Changes apply only after the agent Pod is recreated or the node restarts. `v2alpha1` was removed in 1.20.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  namespace: kube-system
  name: enable-xdp
spec:
  nodeSelector:
    matchLabels:
      io.cilium.xdp-offload: "true"
  defaults:
    bpf-lb-acceleration: native
```

Typical uses: enabling XDP or IPv6 BIG TCP only on nodes with suitable hardware, and gradual kube-proxy replacement rollout (label migrated nodes `io.cilium.migration/kube-proxy-replacement=true`, patch the kube-proxy DaemonSet with a `NotIn` affinity on that label, set `kube-proxy-replacement: "true"` in the CiliumNodeConfig, delete the agent Pod per node). `k8sServiceHost` and `k8sServicePort` must already be set before kube-proxy goes away.

### 8.3 KVStore to CRD identity migration ("Double Write", beta)

Introduced in 1.17 and still marked beta in 1.20.2 and in 1.21 pre.3. The allocation mode is the agent option `--identity-allocation-mode`, set through the Helm value `identityAllocationMode` (which renders the `identity-allocation-mode` ConfigMap key in the chart).

| Step | Mode | Rollout order | Source of truth |
|---|---|---|---|
| 0 | `kvstore` | | KVStore |
| 1 | `doublewrite-readkvstore` | operator, then agents | KVStore (identities also written as CRDs, unused) |
| 2 | `doublewrite-readcrd` | operator, then agents | CRDs (still written to KVStore for fast rollback) |
| 3 | `crd` | agents, then operator | CRDs only; KVStore can be decommissioned |

Wait for convergence between steps. The operator exposes gauges in the `cilium_operator` namespace. The upstream upgrade page still lists the older names `cilium_operator_identity_*_count`, but the code in `operator/doublewrite/metrics.go` (v1.20.2) registers `doublewrite_crd_identities`, `doublewrite_kvstore_identities`, `doublewrite_crd_only_identities` and `doublewrite_kvstore_only_identities`, which appear as `cilium_operator_doublewrite_*`. Check `curl` on the operator metrics port for the exact names in your version. Transient differences are normal because KVStore and CRD garbage collection run at different times (`--identity-gc-interval`, `--identity-heartbeat-timeout`). The reverse migration (CRD to KVStore) works by repeating the steps in reverse. Clean-slate recovery: with no agent running in `crd` mode, `kubectl delete ciliumid --all`.

The one-shot `cilium-dbg preflight migrate-identity` tool is documented in 1.20.2 with limitations (no identity churn allowed, no easy rollback) and is deprecated in 1.21 pre-release; use Double Write.

## 9. Cluster Mesh Architecture

Cluster Mesh connects the control planes of several Kubernetes clusters so that identities, endpoints, nodes and services are shared, while Pod traffic flows directly node to node with no gateway or proxy.

```
 Cluster 1                                         Cluster 2
 ┌──────────────────────────────┐                  ┌──────────────────────────────┐
 │ clustermesh-apiserver (Deploy)│                 │ clustermesh-apiserver (Deploy)│
 │  ┌────────┐ ┌──────────────┐ │  mTLS etcd 2379  │  ┌────────┐ ┌──────────────┐ │
 │  │ etcd   │◄┤ apiserver    │ │◄────────────────►│  │ etcd   │◄┤ apiserver    │ │
 │  │(local  │ │ (sync local  │ │  (via internal LB│  │        │ │              │ │
 │  │ state) │ │  state -> etcd)│ │   / NodePort)   │  │        │ │              │ │
 │  └───▲────┘ └──────────────┘ │                  │  └───▲────┘ └──────────────┘ │
 │      │      ┌──────────────┐ │                  │      │      ┌──────────────┐ │
 │      └──────┤ kvstoremesh  │─┼─ pulls remote ──►│      └──────┤ kvstoremesh  │ │
 │             └──────▲───────┘ │   cluster state  │             └──────▲───────┘ │
 │   agents read ONLY │ local   │                  │   agents read ONLY │ local   │
 │   ┌────────────────┴─┐       │                  │   ┌────────────────┴─┐       │
 │   │ cilium-agent (DS)│       │                  │   │ cilium-agent (DS)│       │
 │   └─────────┬────────┘       │                  │   └─────────┬────────┘       │
 └─────────────┼────────────────┘                  └─────────────┼────────────────┘
               └──────── Pod -> Pod, node to node (VXLAN/Geneve or native) ───────┘
```

Components (v1.20.2 `intro.rst`, `values.yaml`):

- **clustermesh-apiserver** is a Deployment with three containers. `etcd` is a single embedded instance without persistent storage; its state is rebuilt from the Kubernetes API server on start, and it is exposed over mTLS. `apiserver` syncs local Cilium and Kubernetes state (nodes, endpoints, identities, services) into that etcd (`etcdQPS: 50`). `kvstoremesh` pulls the state of each remote cluster into the local etcd cache (`etcdQPS: 100`).
- **KVStoreMesh**: agents read remote state only from the local cache, so agents do not each open connections to every remote etcd. It has been the default since 1.16, the `clustermesh.apiserver.kvstoremesh.enabled` value was deprecated in 1.18, and in **[1.21 pre-release]** it is unconditionally enabled and the value is removed.
- **Replicas**: `clustermesh.apiserver.replicas` defaults to 1. Each replica runs its own etcd cluster; remote clients pick one through the Service. `service.enableSessionAffinity` (`HAOnly` default, `Always`, `Never`) reduces full resyncs after reconnects. `podDisruptionBudget` is disabled by default.
- **KVStore mode**: if Cilium already uses an external etcd as its identity/state store, Cluster Mesh can reuse it (`clustermesh.apiserver.kvstoremesh.kvstoreMode: external`); `external` cannot be combined with `crd` identity allocation mode.
- **Single trust domain** (1.20.2 `intro.rst`): a compromised cluster can poison the others, so connect only clusters that are mutually trusted and have equivalent security postures.

### 9.1 Data path

Remote Pods appear in the local ipcache with the remote node as the tunnel endpoint (overlay) or are routed by the underlay (native routing). Because identities include the cluster ID, a policy decision in cluster 1 for traffic from a Pod in cluster 2 uses the remote Pod's numeric identity and works without any gateway. This is why non-overlapping Pod CIDRs and node-IP connectivity are mandatory.

## 10. Cluster Mesh Configuration

### 10.1 Prerequisites

| Requirement | Detail |
|---|---|
| Same datapath mode | All clusters overlay, or all native routing |
| Cilium minor skew | At most one minor apart |
| Unique, non-overlapping Pod CIDRs | Across all nodes of all clusters |
| Node-to-node reachability | Using each node's InternalIP (peering, TGW or VPN) |
| Firewall | TCP 2379 (clustermesh-apiserver), TCP 4240 and ICMP (health), UDP 8472/6081 (tunnel), UDP 51871 (WireGuard) |
| Native routing only | `ipv4NativeRoutingCIDR` must cover every cluster's Pod CIDR (for example `10.0.0.0/8`), and Pods must be routable across clusters on all ports |

### 10.2 Cluster name and ID

| Setting | Rule |
|---|---|
| `cluster.name` | At most 32 characters, regex `^([a-z0-9][-a-z0-9]*)?[a-z0-9]$` (`pkg/clustermesh/types/types.go`); unique per cluster. `default` cannot be used when the ID is non-zero |
| `cluster.id` | 1 to 255 by default; 0 means unset and is reserved. With `maxConnectedClusters: 511` the range extends to 511. **ENI mode and aws-cni chaining**: the chart rejects IDs 128-255 (and 384-511 with `maxConnectedClusters: 511`) unless `extraConfig.allow-unsafe-policy-skb-usage=true` (`templates/validate.yaml:160-168`, cilium/cilium#21330); use IDs below 128 on ENI-mode EKS |
| `clustermesh.maxConnectedClusters` | `255` (default) or `511`; identical in all clusters; set only at install time |

Trade-off: the cluster ID occupies bits of the numeric identity. At 255 clusters the maximum number of cluster-local identities is 65535; at 511 it drops to 32767. Changing `maxConnectedClusters` on a live cluster can disrupt connections and mis-enforce policy. The comment on `cluster.id` in `values.yaml` still says 1 to 255; that is stale for the 511 case. Changing the cluster name or ID on a running cluster requires restarting all workloads, because identities embed the cluster ID.

### 10.3 TLS and authMode

| Value | Meaning |
|---|---|
| `clustermesh.apiserver.tls.auto.method` | `helm` (certificates renew only on `helm upgrade`, so upgrade at least yearly), `cronJob` (default schedule `0 0 1 */4 *`, every four months), `certmanager` |
| `tls.auto.certValidityDuration` | `365` days |
| Shared CA | All clusters must share one CA: copy the `cilium-ca` Secret to the other cluster before enabling, or set `tls.caBundle` |
| User-provided certs | Secrets `clustermesh-apiserver-{server,admin,remote,local}-cert`; CNs: server `clustermesh-apiserver.<ns>.svc` (SANs `*.mesh.cilium.io`, `127.0.0.1`, `::1`, extra DNS names), admin `admin-<cluster>`, local `local-<cluster>`, remote `remote` (1.20) or `remote-<cluster-name>` (`cluster` mode) |

`authMode` controls which etcd user each cluster uses when connecting to a remote clustermesh-apiserver:

| authMode | Behavior | Default in |
|---|---|---|
| `legacy` | All clusters use the user `remote` | 1.17, 1.18 (`values.yaml`: v1.17.18 line 3416, v1.18.14 line 3634) |
| `migration` | Per-cluster users are created but authentication still uses `remote`; required to move between legacy and cluster without disruption | 1.19, 1.20 |
| `cluster` | Each cluster authenticates as `remote-<cluster-name>`; meaningful only when the same CA is shared | **[1.21 pre-release]** |
| `cluster-strict` | **[1.21 pre-release]** Like `cluster` without the shared `remote` user; enable only after all clusters use `cluster` | - |

1.21 action: with `clustermesh.useAPIServer=true` and `tls.auto.enabled=false`, re-issue the remote certificate with CN `remote-<cluster-name>`, or set `authMode` back to `migration` or `legacy`. With automatic certificates the transition is expected to be transparent. When `clustermesh.config.enabled=false` you must create the `clustermesh-remote-users` ConfigMap yourself (1.19 note). Certificate lifetime changes: 1.19 reworked generation (CronJob no longer a Helm hook); 1.20 defaults to one-year validity regenerated every four months and enforces CA validity >= leaf validity; the 1.20 key `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` moved to `clustermesh.apiserver.tls.auto.server.*`.

### 10.4 Helm setup

Per-cluster values (shape from the upstream setup guide; the internal-LB annotation is the standard AWS Load Balancer Controller scheme annotation; whether the chart comments give it was not verified):

```yaml
# cluster1.yaml
cluster:
  name: cluster1
  id: 1
clustermesh:
  useAPIServer: true
  config:
    enabled: true
  apiserver:
    service:
      type: LoadBalancer
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    tls:
      auto:
        enabled: true
        method: cronJob
        server:
          extraDnsNames:
            - cluster1.example.com
```

```yaml
# clusters.yaml  (shared; the local cluster entry is ignored by each cluster)
clustermesh:
  config:
    clusters:
      cluster1:
        address: cluster1.example.com
        port: 2379
      cluster2:
        address: cluster2.example.com
        port: 2379
```

Apply with the same chart version already installed (this is the one case where `--reuse-values` is acceptable, as the upstream guide does), copying the CA first:

```bash
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER1 --reuse-values -f clusters.yaml -f cluster1.yaml

kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | \
  kubectl --context $CLUSTER2 create -f -

helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER2 --reuse-values -f clusters.yaml -f cluster2.yaml
```

Service exposure: `clustermesh.apiserver.service.type` is `NodePort` by default (`nodePort: 32379`). Upstream recommends `LoadBalancer` for a stable address; `NodePort` needs stable node IPs; `ClusterIP` needs ClusterIPs routable between clusters. On AWS, always use `service.beta.kubernetes.io/aws-load-balancer-scheme: internal` (and `loadBalancerSourceRanges` limited to the peer VPC CIDRs) or NodePort/ClusterIP over peering/TGW; an internet-facing LB for this control plane violates this repository's policy and exposes the mesh trust domain. Pair this with a security group that admits TCP 2379 only from the peer cluster's node security group or private CIDR.

Partial mesh: give each cluster a `clusters` map containing only the clusters it should connect to. Static `ips` per cluster are also supported; **[1.21 pre-release]** changing static IPs no longer restarts Pods, and `clustermesh.apiserver.service.port` is configurable.

CLI alternative (a wrapper around Helm, convenient for labs):

```bash
cilium install --set cluster.name=$CLUSTER1 --set cluster.id=1 --context $CLUSTER1
cilium install --set cluster.name=$CLUSTER2 --set cluster.id=2 --context $CLUSTER2
cilium clustermesh enable --context $CLUSTER1
cilium clustermesh enable --context $CLUSTER2
cilium clustermesh connect --context $CLUSTER1 --destination-context $CLUSTER2   # one direction is enough
cilium clustermesh status --context $CLUSTER1 --wait
cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2
```

### 10.5 Namespaces: `defaultGlobalNamespace`

`clustermesh.defaultGlobalNamespace` (default `true`; present in the 1.20.2 chart, not in the 1.19.8 chart) controls whether a namespace's CiliumEndpoints, CiliumIdentities and Services are exported. Annotate a namespace with `clustermesh.cilium.io/global: "true"` or `"false"` to override. Both the source and destination namespaces must be global for cross-cluster connectivity and policy, and a Global Service must be in a global namespace and carry the service annotation. Setting the default to `false` limits the state synchronized between clusters, which helps scalability.

### 10.6 Staleness: `cacheTTL`

`clustermesh.cacheTTL` defaults to `"0s"`: cached data of a disconnected remote cluster is never revoked. Set a duration (for example `"15m"`) to drop stale remote data if connectivity is not re-established in that time.

## 11. Global Services, Affinity and EndpointSlice Sync

A Global Service uses the same Service name and namespace in each cluster and has the annotation `service.cilium.io/global: "true"`. Backends from all clusters are merged.

| Annotation | Effect |
|---|---|
| `service.cilium.io/global: "true"` | Make the Service global. If any cluster omits it or sets it to false, that cluster's Service stays local |
| `service.cilium.io/shared: "false"` | Do not export this cluster's backends, but still consume remote ones. If both are global with shared on both sides, each cluster sees local plus remote; a cluster with `shared: "false"` exports nothing |
| `service.cilium.io/affinity: none\|local\|remote` | `local`: use healthy local backends, fall back to remote only if all local are unavailable; `remote` is the mirror image; `none` (default) no preference |
| `service.cilium.io/global-sync-endpoint-slices: "true"` | **Beta.** Also create EndpointSlices for remote backends so third-party controllers can see them; requires Helm `clustermesh.enableEndpointSliceSynchronization=true` and an operator restart. Headless global Services get it by default |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rebel-base
  annotations:
    service.cilium.io/global: "true"
    service.cilium.io/affinity: "local"
spec:
  type: ClusterIP
  ports:
  - port: 80
  selector:
    name: rebel-base
```

Inspect affinity with `cilium-dbg service list --clustermesh-affinity` (the preferred backends show `(preferred)`). Limits: Global NodePort and host-network clients load-balance to remote backends only with kube-proxy replacement (or `socketLB.enabled=true` with `socketLB.hostNamespaceOnly=true`). The Cilium ingress controller works in a mesh without EndpointSlice sync; other ingress controllers may need it. Metric added in 1.19: `cilium_agent_clustermesh_remote_cluster_endpoints`.

## 12. MCS-API (Multi-Cluster Services)

MCS-API is the Kubernetes SIG-Multicluster API: a `ServiceExport` publishes a Service, and every cluster gets a `ServiceImport` whose DNS name is `<svc>.<ns>.svc.clusterset.local`. Cilium implements the import as a derived Service named `derived-<hash>` that reuses the Global Services machinery, so the two mechanisms are compatible.

| Item | Value |
|---|---|
| Maturity | beta in 1.19 (CRDs `multicluster.x-k8s.io/v1alpha1`); stable in 1.20 (`v1beta1`, `v1alpha1` still supported) |
| Enable | `clustermesh.mcsapi.enabled=true` (replaces the removed `clustermesh.enableMCSAPISupport`) |
| CRDs | Installed by the chart (`clustermesh.mcsapi.installCRDs`, default true) |
| CoreDNS | `clustermesh.mcsapi.corednsAutoConfigure.enabled` (needs CoreDNS >= 1.12.2, the default in Kubernetes >= 1.35). Manual path: ClusterRole `coredns-mcsapi` (list/watch `serviceimports`) and the `multicluster clusterset.local` CoreDNS plugin |
| Namespace | The Service's namespace must exist in every cluster |

```yaml
apiVersion: multicluster.x-k8s.io/v1beta1
kind: ServiceExport
metadata:
  name: rebel-base
spec:
  exportedLabels:
    app.kubernetes.io/name: rebel-base
  exportedAnnotations:
    service.cilium.io/affinity: local
```

Reconciled properties across exports: SessionAffinity, Ports (union), Type (ClusterSetIP or Headless), InternalTrafficPolicy, TrafficDistribution, and labels/annotations. On conflict Cilium sets a conflict condition on the `ServiceExport` status and resolves by creation time, oldest first, so fix conflicts rather than relying on the resolution. A per-cluster DNS name is not supported; export `mysvc-eu` and `mysvc-us` separately. Hostnames of StatefulSet Pods resolve as `<hostname>.<cluster>.<svc>.<ns>.svc.clusterset.local`. Gateway API can use a `ServiceImport` as a `backendRef`. **[1.21 pre-release]** mirrored EndpointSlices with names longer than 40 characters after prefix removal may be recreated during upgrade, causing a brief interruption.

## 13. Cross-cluster Policy

- **Default scope (1.19+)**: selectors match endpoints of the local cluster only (`policy-default-local-cluster`, Helm `clustermesh.policyDefaultLocalCluster: true`). Up to 1.18 the default was all clusters. Before upgrading from 1.18, audit with `cilium clustermesh inspect-policy-default-local-cluster --all-namespaces` (or `-p <namespace>`); an earlier note here claimed a CLI bug in this command is fixed in the 1.21 pre.3 tree; that was not verified, so confirm the command output on your CLI version.
- **Select a remote cluster** with the label `io.cilium.k8s.policy.cluster`:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cross-cluster
spec:
  endpointSelector:
    matchLabels:
      name: x-wing
  egress:
  - toEndpoints:
    - matchLabels:
        name: rebel-base
        io.cilium.k8s.policy.cluster: cluster2
```

Any cluster: use `matchExpressions: [{key: io.cilium.k8s.policy.cluster, operator: Exists}]` instead.

- **Entities**: `cluster` includes remote nodes in a mesh unless restricted to the local cluster (1.18 option); 1.20 adds `cluster-mesh`, which covers all endpoints in meshed clusters plus everything in `cluster`.
- Policies are not replicated: apply them in each cluster.
- Mutual authentication (SPIRE) is not supported with Cluster Mesh, and it is removed entirely in the 1.21 pre-release; ztunnel is not supported together with Cluster Mesh per this repository's service-mesh notes. See [mTLS, encryption and identity](12-mtls-encryption-identity.md).
- The host firewall has restrictions in combination with Cluster Mesh (`host.rst`). Data-plane encryption is separate from the mTLS used by the control plane; WireGuard or IPsec must be configured the same way in all clusters, and UDP 51871 must be open between them. Exact Cluster Mesh plus encryption caveats were not re-verified here.

## 14. Cluster Mesh on EKS

Upstream's `eks-clustermesh-prep.rst` uses `eksctl`, two VPCs with non-overlapping CIDRs (for example `10.0.0.0/16` and `10.1.0.0/16`, avoiding `172.17.0.0/16`), VPC peering, and a security group that allows traffic from itself and from the peer. That guide also builds public subnets with an internet gateway. For this repository, adapt it as follows.

- Private subnets only for nodes; no public IPs or EIPs on nodes.
- Peer the VPCs (or use a Transit Gateway) and add routes in the private route tables to the peer CIDR.
- Security group rules reference the node security groups of both clusters (or private CIDRs); never `0.0.0.0/0` or `::/0`.
- Expose clustermesh-apiserver through an internal NLB (`aws-load-balancer-scheme: internal`) or NodePort over the peering link, with `loadBalancerSourceRanges` set to the peer VPC CIDR.
- ENI mode gives VPC-routable Pod IPs, so native routing requires only that `ipv4NativeRoutingCIDR` cover both VPCs' Pod ranges. In overlay mode, only node-to-node reachability (UDP 8472) is needed.
- Use distinct `cluster.name`/`cluster.id` per EKS cluster and the same `maxConnectedClusters`. In ENI mode keep `cluster.id` below 128, because the chart rejects 128-255 (and 384-511 with `maxConnectedClusters: 511`) unless `extraConfig.allow-unsafe-policy-skb-usage=true` is set (`validate.yaml:160-168`).

## 15. Labs

> These labs were not executed against a live cluster in this review; they were checked against upstream source and documentation. Run them only in disposable clusters.

### Lab 1: Two-cluster Cluster Mesh

Prerequisites: two disposable clusters whose nodes can reach each other (two kind clusters on one Docker host with different `networking.podSubnet`/`serviceSubnet` and `disableDefaultCNI: true`, or two EKS clusters in peered VPCs), Helm 3, Cilium CLI 0.20.1, `$CLUSTER1`/`$CLUSTER2` contexts.

1. Install Cilium 1.20.2 in each cluster with distinct `cluster.name`, `cluster.id` and non-overlapping Pod CIDRs (cluster-pool lists must differ).
2. Copy the CA: `kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | kubectl --context $CLUSTER2 create -f -`.
3. Apply the values files from section 10.4. On kind (no load balancer), use `service.type: NodePort` and list the node IPs in `clustermesh.config.clusters.<name>.ips` with the port `32379`.
4. Run `cilium clustermesh status --context $CLUSTER1 --wait`, then `cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2`.

Verify: `cilium clustermesh status` reports the clustermesh-apiserver ready and the remote cluster connected; `kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg status --all-clusters` lists the remote cluster as ready with its cluster ID and `synchronization status` all true; `cilium-dbg node list` includes remote nodes.

Cleanup: `helm uninstall cilium -n kube-system` in both clusters, or delete the disposable clusters. Rollback of a failed connect: remove `-f clusters.yaml` entries and `helm upgrade` again with the same chart version.

### Lab 2: Global service, `shared` and affinity

Prerequisites: Lab 1.

1. In both clusters create the same namespace and a Deployment plus Service `rebel-base` with `service.cilium.io/global: "true"`; make the Pods answer with their cluster name.
2. From a client Pod in cluster 1, run a curl loop and observe replies from both clusters.
3. Annotate the cluster-1 Service with `service.cilium.io/affinity=local` and repeat; replies come from cluster 1 only. Scale the local backends to zero and observe the failover to cluster 2.
4. Set `service.cilium.io/shared: "false"` in cluster 2 and observe that cluster 1 sees no cluster-2 backends while cluster 2 still reaches cluster 1.

Verify: `cilium-dbg service list --clustermesh-affinity` in the agent shows the preferred backends; `cilium-dbg bpf lb list` shows remote backend addresses.

Cleanup: delete the namespace in both clusters.

### Lab 3: MCS-API

Prerequisites: Lab 1 with `clustermesh.mcsapi.enabled=true` and `corednsAutoConfigure.enabled=true` (restart CoreDNS if you configure it manually).

1. Create the namespace and Service in both clusters, then a `ServiceExport` of the same name in each.
2. From a Pod, resolve `rebel-base.<namespace>.svc.clusterset.local` and curl it.
3. Make the exported ports differ between the clusters and inspect `kubectl get serviceexport -o yaml` for the conflict condition.

Verify: a `ServiceImport` exists in both clusters and a derived Service named `derived-<hash>` appears; the DNS name resolves.

Cleanup: delete the ServiceExports, Services and namespaces.

### Lab 4: Upgrade drill with drift detection

Prerequisites: a disposable cluster on 1.19.8 installed from a values file, with the Prometheus metrics endpoint reachable (or use `cilium-dbg metrics list`).

1. Save values: `helm get values cilium -n kube-system -o yaml > old-values.yaml`.
2. Run the pre-flight chart for 1.20.2 and confirm the checks pass, then delete it.
3. Upgrade with `--version 1.20.2 -f old-values.yaml --set upgradeCompatibility=1.19`.
4. Change one agent-restart-only ConfigMap key with `cilium config set --restart=false <key> <value>` and read the drift metric: `kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg metrics list | grep drift_checker_config_delta`.
5. Roll back: `helm history cilium -n kube-system`, then `helm rollback cilium <REVISION> -n kube-system`.

Verify: `cilium_drift_checker_config_delta` is non-zero after step 4 and returns to 0 after the agents restart; `cilium status` is healthy after the upgrade and after the rollback.

Cleanup: delete the disposable cluster. Rollback note: this lab exercises the rollback path; do not run it on a cluster that used 1.20-only features.

### Lab 5: CiliumNodeConfig per-node override

Prerequisites: any Cilium 1.20.2 cluster with at least two nodes.

1. Label one node: `kubectl label node <node> io.cilium.test-override=true`.
2. Apply a `CiliumNodeConfig` in `kube-system` selecting that label with a harmless `defaults` key such as `debug: "true"`.
3. Delete the agent Pod on the labelled node and on one unlabelled node.

Verify: the recreated agent on the labelled node reports the override in its effective configuration (`cilium-dbg config`); the unlabelled one does not.

Cleanup: delete the CiliumNodeConfig, remove the label and recreate the agent Pod again.

## Version Delta

| Area | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|
| Min kernel | 5.10 | 5.10 | 5.10 | 5.10 (LLVM 21.1) |
| Gateway API CRDs | 1.3.0 | 1.4 | 1.6.1 | 1.6.1 |
| Helm OCI chart | no | yes | yes (recommended) | yes |
| MCS-API | beta | beta (`v1alpha1`, auto CRDs) | stable (`v1beta1`) | `v1beta1` |
| Cluster Mesh policy default | all clusters | local only | local only; `cluster-mesh` entity | local only |
| authMode default | `legacy` | `migration` | `migration` | `cluster` (+ `cluster-strict`) |
| KVStoreMesh | `enabled` deprecated | default on | default on | always on |
| Mutual auth | exists | disabled by default | deprecated | removed |
| Kafka L7 / proxylib | deprecated | Kafka deprecated | removed | removed |
| BGPv1 | deprecated | removed | - | - |
| Multi-pool IPAM | beta | stable | + cluster-pool migration | Azure IPAM to multi-pool |
| Double Write | beta | beta | beta | beta; `migrate-identity` deprecated |
| configDriftDetection | backported | backported | native | same |
| ENI masquerade default | IPv4 flipped to false | false | false | IPv6 masquerade off |

## Troubleshooting

| Symptom | Check |
|---|---|
| Remote cluster not connecting | `cilium clustermesh status --wait`; `kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg troubleshoot clustermesh [cluster...]` (DNS, connectivity, TLS, etcd authorization); with KVStoreMesh also `kubectl exec -n kube-system deploy/clustermesh-apiserver -c kvstoremesh -- clustermesh-apiserver kvstoremesh-dbg troubleshoot` |
| Per-remote state | `cilium-dbg status --all-clusters` (nodes, endpoints, identities, services, MCS-API exports, reconnections, `has-quorum`, `cluster-id`, `kvstoremesh`, synchronization status); `... kvstoremesh-dbg status --verbose` |
| Logs | agent: `New remote cluster configuration`, `Connection to remote cluster established`, `Unable to establish etcd connection to remote cluster`; `kubectl logs -n kube-system deployment/clustermesh-apiserver -c apiserver` |
| TLS errors | Different CAs (copy `cilium-ca`), expired certificates (`helm` method after one year), wrong CN for the `authMode`; secrets `cilium-clustermesh` and `cilium-kvstoremesh` |
| Name resolution of `*.mesh.cilium.io` | hostAliases map `cluster1.mesh.cilium.io` to the LB IP, on the DaemonSet (no KVStoreMesh) or the clustermesh-apiserver Deployment (KVStoreMesh) |
| Port | TCP 2379 must be allowed in the security group by reference/private CIDR |
| Cross-cluster traffic denied | `cilium-dbg identity list` (label `io.cilium.k8s.policy.cluster`), `cilium-dbg bpf ipcache list`, `cilium-dbg service list`, `cilium-health status`; remember the local-cluster default policy scope since 1.19 and that both namespaces must be global |
| Overlapping CIDRs or duplicate IDs | `cilium-dbg node list` shows conflicting node ranges; fix requires re-IPing and restarting workloads |
| Upgrade stuck in 1.20 from an old cluster | Use 1.20.2 or later (the `CiliumNodeConfig v2alpha1` CRD bug) |
| Config change not effective | `cilium_drift_checker_config_delta > 0`: restart agents |

## Validation Limits and Sources

The labs were not executed against a live cluster in this review and were checked against upstream source and documentation at the tags below. Facts that could not be verified are listed here instead of being asserted:

- Whether Cilium 1.21 enables BPF masquerading by default. The pre.2 release note says it does, but the pre.3 tree shows daemon default `false`, chart `bpf.masquerade` default false, and an empty "Changed Options" section in `upgrade-next.inc`.
- Cluster Mesh with WireGuard/IPsec: exact caveats were not re-checked.
- Chaining-mode limitations on EKS; the exact command to remove the EKS-managed kube-proxy add-on; whether Amazon Linux 2023 is listed by name.
- AWS-maintained Cilium build versions beyond 1.17.9-0 and 1.18.3-0.
- The `bpf.tproxy` and ENI IPv6 maturity beyond the quoted "beta".
- The 1.19.0 release date and the exact 1.17 Kubernetes test matrix.
- The MCS-API "stable" label comes from the v1.20.0 release body; the source confirms the removal of the beta banner and the `v1beta1` CRDs.
- Double Write metric names: the upstream upgrade page and the code disagree (section 8.3); the code at v1.20.2 was followed.
- Chart default `kubeVersion` is a chart constraint, not the tested Kubernetes range.

Sources:

- [Cilium v1.20.2 Documentation: operations/upgrade.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade.rst)
- [v1.20.2 upgrade notes](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)
- [v1.20.2 Cluster Mesh docs](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/clustermesh)
- [v1.20.2 Cluster Mesh troubleshooting](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/troubleshooting_clustermesh.rst)
- [v1.20.2 Helm install and EKS](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/k8s-install-helm.rst), [requirements-eks.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [v1.20.2 ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [v1.20.2 system requirements](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [v1.20.2 per-node config](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/per-node-config.rst), [ConfigMap drift detection](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/configmap-drift-detection.rst)
- [v1.20.2 Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- [v1.20.2 Double Write metrics code](https://github.com/cilium/cilium/blob/v1.20.2/operator/doublewrite/metrics.go)
- [v1.21.0-pre.3 upgrade notes](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc), [values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- Release notes: [v1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2), [v1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0), [v1.19.0](https://github.com/cilium/cilium/releases/tag/v1.19.0), [v1.18.0](https://github.com/cilium/cilium/releases/tag/v1.18.0), [v1.17.0](https://github.com/cilium/cilium/releases/tag/v1.17.0), [v1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3)
- AWS: EKS user guide pages on alternate CNI plugins, Auto Mode networking, and hybrid nodes CNI.

## Quiz

Test yourself with the [Part 13 quiz](../../quizzes/networking/cilium/13-clustermesh-install-upgrade-quiz.md).
