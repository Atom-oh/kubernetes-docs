# Part 12: mTLS, Transparent Encryption and Identity

> **Review baseline**: Cilium 1.20.2 (stable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Items marked **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA.
> **Last Updated**: October 15, 2026

Cilium's security model has three layers that are easy to conflate. **Identity and policy** decide who may talk to whom, based on labels rather than IPs. **Transparent encryption** (WireGuard, IPsec) protects bytes on the wire between nodes. **Workload mTLS** (ztunnel) binds an encrypted channel to a workload identity. This chapter explains each from the mechanism up, then covers the removed Mutual Authentication feature, service-mesh options, Hubble/Tetragon, and certificate management.

Related chapters: [eBPF datapath internals](08-ebpf-datapath-internals.md), [overlay and native routing](09-overlay-native-routing.md) (tunnel/MTU interplay), [IPAM](10-ipam-deep-dive.md), [BGP, LB and egress](11-bgp-lb-egress-edge.md), [ClusterMesh, install and upgrade](13-clustermesh-install-upgrade.md). Policy basics are in [IPAM and Network Policies](04-ipam-policy.md); this chapter goes deeper. Introductory visibility material is in [Security and Visibility](06-security-visibility.md).

## Maturity and Timeline at a Glance

| Feature | 1.18 | 1.19 | 1.20 (stable) | 1.21 pre-release |
|---|---|---|---|---|
| Mutual Authentication (SPIFFE/SPIRE, `authentication.mode: required`) | Beta | Beta, `authentication.enabled` defaults to false | **Deprecated** (docs still titled "Beta") | **Removed** |
| ztunnel transparent encryption (`encryption.type=ztunnel`) | - | Beta (introduced) | Beta, `ca.type` added | Beta |
| WireGuard | Stable | Stable | Stable | Stable |
| IPsec | Stable | Stable | Stable | Stable |
| WireGuard `encryption.nodeEncryption` | not checked | not checked | Beta | **Deprecated, removal in 1.22** |
| Double Write identity migration | documented | documented | documented | `cilium-dbg preflight migrate-identity` deprecated in its favour |
| `identityManagementMode` | not checked | not checked | Beta | Beta |
| CiliumEndpointSlice | not checked | not checked | Beta | Beta |
| Kubernetes ClusterNetworkPolicy support | - | - | New, alpha API (v1alpha2) | alpha |

The Mutual Authentication row is the one most often misreported. Exact statement of record:

- It was **Beta** through 1.18, 1.19 and 1.20 (the 1.20 docs page is still titled "Mutual Authentication (Beta)").
- It was **deprecated in 1.20**: the 1.20 upgrade notes say it "is now deprecated and will be removed in a future version" and point to ztunnel.
- It was **removed in 1.21**: the 1.21 upgrade notes say it "has been removed after deprecation" and ask you to remove the configuration before upgrading.
- The `authentication` field in the policy API is **kept for CRD compatibility but is unused** in 1.21.

## Identity Model

### Labels to numeric identity

Cilium does not enforce policy on IP addresses. Every endpoint (Pod) is assigned a **security identity**, a numeric ID derived from its identity-relevant labels. Endpoints with the same label set share one ID, so one policy map entry covers every replica of a Deployment, and the policy decision survives Pod IP churn.

```
Pod labels (k8s:app=web, k8s:io.kubernetes.pod.namespace=shop, ...)
        |  filter by identity-relevant labels
        v
label set  -->  allocator (CRD or kvstore)  -->  numeric identity, e.g. 31337
        |
        +--> CiliumEndpoint.status.identity (published)
        +--> ipcache:  podIP -> identity   (every node learns it)
        +--> source node stamps identity into the packet (tunnel metadata)
                or the destination node resolves srcIP via ipcache
        +--> destination node: policy map lookup (local endpoint, remote identity, port, proto)
```

On the destination side the lookup key is the local endpoint, the remote identity, port and protocol. The identity travels with the packet (in tunnel metadata for overlay) or is recovered from the source IP through the ipcache (native routing), which is why a stale or missing ipcache entry is a policy symptom.

### The 32-bit numeric identity layout

The scope lives in bits 24-31:

| Scope | Value | Used for |
|---|---|---|
| Global | 0 | Identities allocated through the CRD/kvstore allocator; bits 0-23 split between identity and cluster ID |
| Local | `1<<24` | Identities that exist only on one node: CIDR- and FQDN-derived identities |
| Remote-node | `2<<24` | Node identities used for node-based policy selection |

With ClusterMesh, the 24 low bits are shared between identity and cluster ID: `max-connected-clusters` 255 gives 16 bits of identity plus 8 bits of cluster ID; 511 gives 15 plus 9. Identities below 256 are reserved (`MinimalIdentity=256`). See `pkg/identity/numericidentity.go` at v1.21.0-pre.3 for the constants. ClusterMesh sizing is covered in [Part 13](13-clustermesh-install-upgrade.md).

### Reserved and well-known identities

Reserved identities, from the datapath constants (`pkg/datapath/types/types_generated.go`, v1.21.0-pre.3):

| ID | Name | Meaning |
|---|---|---|
| 0 | unknown | Unresolved identity |
| 1 | host | The local node |
| 2 | world | Anything outside the cluster (also the CIDR identity of `0.0.0.0/0`) |
| 3 | unmanaged | Endpoint not managed by Cilium |
| 4 | health | Cilium health endpoints |
| 5 | init | Endpoint whose labels are not yet known (Pod start-up) |
| 6 | remote-node | Other cluster nodes |
| 7 | kube-apiserver | The Kubernetes API server |
| 8 | ingress | Cilium-managed ingress/Envoy |
| 9 / 10 | world-ipv4 / world-ipv6 | Address-family split of world |
| 11-14 | aggregate identities (cluster, clustermesh, world, remote-node) | Used for policy-map aggregation, not applied to traffic |

The upstream terminology page lists only IDs 0-8, so 9 and 10 appear only in the source. Well-known identities that exist without any kvstore or CRD round trip include `kube-dns` (102), `kube-dns` on EKS (103), `coredns` (104), `cilium-operator` (105) and `coredns` on EKS (106), per the terminology page and `numericidentity.go`. These matter on EKS because the default DNS Pods get a fixed ID.

Behaviour to remember: a Pod sits in `reserved:init` until its labels are resolved; north-south Service traffic that reaches a backend arrives as `reserved:world` in tunnel mode, while in native routing it is `world` if the packet hits the node hosting the backend and `remote-node` otherwise (which is why `fromEntities: cluster` matches it). See `Documentation/security/policy/caveats.rst`.

### Identity-relevant labels and identity churn

By default every label is identity-relevant except those on an exclusion list (for example `io.kubernetes`, `kubernetes.io`, StatefulSet pod-name, `pod-template-hash`, `controller-revision-hash`, `annotation.*`, `topology.kubernetes.io`). Patterns are regular expressions anchored at the start of the label.

- Adding any **inclusive** pattern switches the agent to allow-list mode and automatically adds `reserved:`, the Pod namespace, namespace labels, `policy.cluster`, service account and `app.kubernetes.io`.
- Helm `labels:` **appends** to the defaults. To override the list exactly, use `--label-prefix-file` (agent flags `--labels` and `--label-prefix-file`).
- Existing identities do not change until the agent restarts; the operator then garbage-collects the old ones.
- A label that changes per release or per Pod (a build SHA, a timestamp) creates one identity per value. That multiplies identities, ipcache entries and policy-map entries. Exclude such labels from identity.

Source: `Documentation/operations/performance/scalability/identity-relevant-labels.rst`.

### Allocation modes

| Helm `identityAllocationMode` | Backing store | Notes |
|---|---|---|
| `crd` (chart default) | `CiliumIdentity` (cilium.io/v2, cluster-scoped) | No external dependency |
| `kvstore` | etcd | Large clusters that already run etcd |
| `doublewrite-readkvstore` | writes both, reads kvstore | Migration step |
| `doublewrite-readcrd` | writes both, reads CRD | Migration step |

Writer trap: the **agent flag** default is `kvstore`, while the **Helm chart** sets `crd`. Always read the effective value from the ConfigMap, not from `cilium-agent --help`.

**Double Write migration (beta)** moves between backends without an identity gap. For kvstore to CRD: set `doublewrite-readkvstore`, then `doublewrite-readcrd`, then `crd`. Deploy the Operator first, then Agents (when going back to `crd` as the final step, Agents first, then the Operator, per the upgrade guide). The sequence is reversible. Convergence is observable with the operator gauges `doublewrite_{crd,kvstore,crd_only,kvstore_only}_identities`, exposed as `cilium_operator_doublewrite_crd_identities`, `cilium_operator_doublewrite_kvstore_identities`, `cilium_operator_doublewrite_crd_only_identities` and `cilium_operator_doublewrite_kvstore_only_identities` (v1.20.2 `operator/doublewrite/metrics.go:13-33`; `Documentation/observability/metrics.rst` lists the same names). The v1.20.2 upgrade guide (`Documentation/operations/upgrade.rst`) still mentions the old `cilium_operator_identity_*_count` names, which the code no longer registers; do not alert on them. Wait until the two `*_only_identities` values reach zero before the next step. In 1.21 `cilium-dbg preflight migrate-identity` is deprecated in favour of Double Write. Source: `Documentation/operations/upgrade.rst`.

### Operator-managed identities (beta)

Helm `identityManagementMode` takes `agent` (default), `operator` or `both` (`both` only during migration). With `operator`, the operator allocates identities, which avoids duplicate CIDR identities created by many agents at once.

1. Agent to operator: set `both`, restart the operator; then set `operator`, restart the agents.
2. Downgrade: agents to `both`, then the operator to `agent`.
3. After changing identity-relevant label patterns, restart both the operator and the agents.

Related: `operator.identityGCInterval` (15m0s) and `identityHeartbeatTimeout` (30m0s) in the chart; agent flags `identity-allocation-timeout` (2m), `identity-change-grace-period` (5s), `identity-restore-grace-period` (30s).

### CiliumEndpoint, CiliumEndpointSlice and ipcache

- **CiliumEndpoint (CEP)**: one per Cilium-managed Pod, same name and namespace. Status carries labels, the identity ID and the policy in effect. `cilium-health-<node>` CEPs live in `kube-system`.
- **CiliumEndpointSlice (CES, beta; CRD still cilium.io/v2alpha1)**: the operator batches slim CEPs into CES objects and agents watch CES. It cuts API-server load at the price of delay in learning new endpoint identities. Helm `ciliumEndpointSlice.enabled` (default false) and `rateLimits`; namespace annotation `cilium.io/ces-namespace: priority` prioritises a namespace. Not compatible with Egress Gateway. Migrate the operator first, then agents; downgrade agents first. The `--ces-slice-mode` flag was removed in 1.20.
- **ipcache**: the BPF map `cilium_ipcache_v2` maps IP or CIDR to identity. Inspect with `cilium-dbg bpf ipcache list|get|match` and `cilium-dbg identity list|get`.
- Each endpoint has a policy map, sized by `--bpf-policy-map-max` (default 16384).

Many distinct CIDRs in policy create many local-scope identities (one per CIDR selector), the reason to prefer `CiliumCIDRGroup` below.

### Inspect identity state

```bash
kubectl get ciliumidentities
kubectl get cep -A -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ipcache list
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
```

## Policy Model in Depth

### Policy resources

| Resource | Scope | Notes |
|---|---|---|
| Kubernetes `NetworkPolicy` | namespace | L3/L4 |
| `CiliumNetworkPolicy` (CNP, cilium.io/v2) | namespace | L3-L7, entities, FQDN, deny |
| `CiliumClusterwideNetworkPolicy` (CCNP) | cluster | Also host policies via `nodeSelector` |
| `ClusterNetworkPolicy` (policy.networking.k8s.io, v1alpha2) | cluster | **New in 1.20**, alpha API; needs opt-in |
| `CiliumCIDRGroup` | cluster | Named CIDR set referenced from rules |

Semantics: rules are an allow-list and are unioned; enforcement is stateful (reply traffic is allowed); a direction flips to default-deny when at least one rule selecting the endpoint exists for that direction.

### Enforcement mode, default deny and audit mode

| Control | Setting | Effect |
|---|---|---|
| `policyEnforcementMode` (flag `enable-policy`) | `default` / `always` / `never` | `default`: endpoint open until selected; `always`: deny by default everywhere; `never`: policy off |
| `enableDefaultDeny: {ingress, egress}` in a rule | per-rule | A selecting rule does not flip that direction to default-deny |
| Helm `enableNonDefaultDenyPolicies` | true | Chart-level enabling for such rules |
| Audit mode | agent flag `--policy-audit-mode=true` (ConfigMap `policy-audit-mode`), or per endpoint | Would-be drops are logged with verdict `AUDIT` instead of dropped |
| `policyDenyResponse` | `none` / `icmp` | `icmp` is experimental, egress only |

Important: `enableDefaultDeny: false` does **not** apply to L7. An L7 rule without an accompanying allow-all still drops everything else on that port.

Audit mode, cluster-wide and per endpoint:

```bash
kubectl -n kube-system patch cm cilium-config --type merge \
  -p '{"data":{"policy-audit-mode":"true"}}'
kubectl -n kube-system rollout restart ds/cilium
# or for one endpoint (host endpoint included):
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled
hubble observe --verdict AUDIT
```

Use audit mode as the first step of any default-deny rollout; the verdict `AUDIT` in Hubble shows what enforcement would have dropped. Source: `Documentation/security/policy-creation.rst`.

### Entities

`host`, `remote-node`, `kube-apiserver`, `ingress`, `cluster`, `cluster-mesh`, `init`, `health`, `unmanaged`, `world`, `all`. `world` equals `0.0.0.0/0`. `kube-apiserver` ingress may not work on some managed platforms (AKS, GKE per upstream). The agent flag `--allow-localhost=policy` disables the implicit host-to-local-Pod allow.

### Node-based selection and CIDR

- `fromNodes`/`toNodes` require `nodeSelectorLabels: true` (flag `--enable-node-selector-labels`). Nodes then get remote-node-scope identities. Upstream sizing: about 1 MB per 1000 nodes with `policy-cidr-match-mode=nodes`.
- CIDR rules (`fromCIDR`, `toCIDR`, `fromCIDRSet`, `toCIDRSet` with `except`) do **not** match Pods or nodes by default. `policyCIDRMatchMode` (`--policy-cidr-match-mode`, beta) opts in to `pods` and/or `nodes`; `pods` costs additional identities. The inline comment in `values.yaml` mentions only `nodes`; the documentation allows both, so trust the docs. The Kubernetes ClusterNetworkPolicy conformance setup uses `pods,nodes`.
- **CiliumCIDRGroup** keeps many CIDRs under one named object, using roughly one identity per group, and annotates Hubble flows with the group name. The CRD storage version is `cilium.io/v2` in 1.18-1.21 (v2alpha1 is still served); the upstream docs page example still shows `v2alpha1`, so use v2:

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: vpn-example-1
  labels:
    role: vpn
spec:
  externalCIDRs:
  - 10.48.0.0/24
  - 10.16.0.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: from-vpn-example
  namespace: demo
spec:
  endpointSelector: {}
  ingress:
  - fromCIDRSet:
    - cidrGroupRef: vpn-example-1
```

Reference by `cidrGroupRef: <name>` or by `cidrGroupSelector.matchLabels`.

### FQDN policy and the DNS proxy

`toFQDNs` with `matchName` or `matchPattern` (`*` matches one label; `**.` is a multi-label prefix; `*.cilium.io` does not match `cilium.io` itself). Mechanism: the agent's DNS proxy, which runs in each agent, observes DNS answers and installs the resolved IPs as FQDN-derived (local-scope) identities. Therefore:

- An egress DNS rule (`toPorts.rules.dns`) to the cluster DNS is required so the proxy sees answers.
- `toFQDNs` cannot be mixed with other L3 selectors in the same rule.
- If the agent restarts, DNS to the proxy is unavailable for that window.
- FQDN is a name allow-list, not a reputation check. IPsec with the L7 proxy needs `--dnsproxy-enable-transparent-mode=true`.
- The per-endpoint limit on IPs per hostname: the documentation and the code disagree. Read the effective value from the agent flag `tofqdns-endpoint-max-ip-per-hostname` and Helm `dnsProxy.endpointMaxIpPerHostname` in your version rather than trusting a number in prose.
- `dnsProxy.preCache` / `--tofqdns-pre-cache` is deprecated in 1.20 with removal planned in 1.21. The standalone DNS proxy is alpha.

### Deny policies and precedence

`ingressDeny`/`egressDeny` take precedence over all allow rules across CNP, CCNP and Kubernetes NetworkPolicy. There is no L7 deny and no `toFQDNs` deny. Order of evaluation in practice:

| Order | Rule class | Result |
|---|---|---|
| 1 | Deny rule matches | Drop, regardless of any allow |
| 2 | Allow rule matches | Forward |
| 3 | Endpoint selected in this direction, nothing matched | Drop (default deny) |
| 4 | Endpoint not selected in this direction | Forward (unless enforcement mode `always`) |

With Kubernetes ClusterNetworkPolicy the tiers are: Admin tier first, then the NetworkPolicy tier (Kubernetes NetworkPolicy, CNP, CCNP), then the Baseline tier. Enable with `k8sClusterNetworkPolicy.enabled=true` (default false; flag `--enable-k8s-cluster-network-policy`) and install the CRD from the network-policy-api project, `release-0.2`. It is an alpha API in Cilium 1.20.

### Worked policy patterns

**Default deny with DNS and FQDN egress** (namespace `demo`). Selecting the endpoint with an egress rule flips egress to default-deny, so DNS must be allowed explicitly and with a DNS rule so the proxy sees answers:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-fqdn
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: ANY
      rules:
        dns:
        - matchPattern: "*"
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

On EKS the DNS Pods are `coredns` with label `k8s-app: kube-dns`; adjust the selector if your distribution labels them differently.

**Allow traffic only from inside the cluster, never from `world`** (this also closes the plaintext-leak window described under Transparent Encryption):

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cluster-only-ingress
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingress:
  - fromEntities:
    - cluster
```

**Intercept all DNS without default-deny** (verbatim pattern from the upstream intro page): a `CiliumClusterwideNetworkPolicy` with `enableDefaultDeny: {egress: false, ingress: false}` that selects every Pod outside `kube-system` and `kube-dns` and allows DNS to `kube-dns` with `matchPattern: "*"`. It puts the DNS proxy in the path (so Hubble sees DNS names) without turning on default-deny for other traffic.

**Deny an identity regardless of allows**:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: deny-untrusted
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingressDeny:
  - fromEndpoints:
    - matchLabels:
        trust: low
```

**Host policy skeleton** (needs `hostFirewall.enabled=true`; start in audit mode on the host endpoint, and always allow SSH/SSM, kubelet and the API server path first):

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: host-ingress-from-cluster
spec:
  nodeSelector:
    matchLabels:
      node-role: worker
  ingress:
  - fromEntities:
    - cluster
    toPorts:
    - ports:
      - port: "10250"
        protocol: TCP
```

Because default-deny applies to the host endpoint once any ingress rule selects it, a policy like this one drops everything else (including SSH) on matching nodes. Retrieve the host endpoint ID with `cilium-dbg endpoint get -l reserved:host -o jsonpath='{[0].id}'`, set `PolicyAuditMode=Enabled` on it first, and watch `hubble observe --verdict AUDIT` before enforcing.

### Reading a policy decision

```
cilium-dbg endpoint list                       # endpoint ID, identity, ingress/egress enforcement
cilium-dbg endpoint get <ID> -o json           # labels, identity, policy revision
cilium-dbg bpf policy get <ID>                 # the per-endpoint policy map (identity, port, proto, deny flag)
cilium-dbg policy selectors                    # which identities each selector currently matches
hubble observe --pod demo/server --verdict DROPPED -o json   # drop reason and (with correlation) the policy that matched
```

If a selector matches fewer identities than expected, the usual cause is an identity-relevant-label mismatch (for example a label excluded from identity) or a namespace-scoped CNP that implicitly adds the namespace to its selectors.

### CEL rejection of empty policies (1.20)

In 1.20 the CNP and CCNP CRDs carry the CEL rule `has(self.spec) || has(self.specs)` with the message "spec or specs must be provided". Creating or updating a policy with neither field is rejected at admission. Existing empty policies are unaffected until updated. Related earlier changes: `FromRequires`/`ToRequires` have been required to be empty since 1.19, and Kafka/proxylib L7 policy was removed in 1.20.

### Host policies

A `CiliumClusterwideNetworkPolicy` with `nodeSelector` becomes a host policy. Requires `hostFirewall.enabled=true` (optionally `devices`). It applies to the host namespace and host-network Pods and supports L3/L4 plus L7 DNS (beta). `--enable-extended-ip-protocols` is needed for VRRP, IGMP, GRE, IPIP, IPV6, ESP and AH. Known issues from upstream: host policies do **not** work with IPsec, are not applied on host WireGuard interfaces, and unknown L2 protocols are dropped once enabled. L7 DNS host policies can break kubelet image pulls and agent restarts, so start with audit mode.

### 1.21 pre-release additions **[1.21 pre-release]**

CNP egress `toPorts[].listener` redirects a port to a CEC/CCEC Envoy listener (it cannot be combined with L7 rules on the same port; upstream advises Gateway API/GAMMA instead). `--fixed-identity-mapping` is deprecated.

## Authentication Timeline: Mutual Authentication (Removed)

### How it worked (1.18-1.20)

A rule carried `authentication: {mode: required}`. In the datapath, a policy hit with that flag consults the BPF map `cilium_auth_map` (524288 entries; key = local identity, remote identity, remote node, auth type). With no unexpired entry the packet is dropped (`DROP_POLICY_AUTH_REQUIRED`, -189) and a signal reaches the agent. The agent's `pkg/auth` manager opened a TLS 1.3 connection out of band **to the remote node's agent** on port 4250 (`authentication.mutual.port`), presented SPIFFE SVIDs obtained from a SPIRE agent socket (identities `spiffe://spiffe.cilium/identity/<numeric-id>`), verified the peer certificate, and stored the earliest expiry in the auth map. Retransmitted packets then passed. Key point: the handshake was **between agents**, not per connection and not on the data path; application traffic was not encrypted unless WireGuard or IPsec was also enabled. Known limits: no ClusterMesh, only SPIRE tested, no interoperability with external mTLS.

### Timeline and what to do

| Release | State | Action |
|---|---|---|
| 1.18, 1.19 | Beta; in 1.19 `authentication.enabled` defaults to false and policies with `authentication` silently forward without auth (with a validation warning) | Leave as is or migrate |
| 1.20 | Deprecated (docs still labelled Beta) | Plan migration to ztunnel (`encryption.type=ztunnel`) or to network encryption plus identity policy |
| 1.21 | Removed; agent `pkg/auth` and `mesh-auth-*` agent flags gone; `authentication` policy field accepted but unused | Remove `authentication.*` Helm values and SPIRE mutual-auth config **before** upgrading |

Migration guidance:

1. Inventory policies that use `authentication`: `kubectl get cnp,ccnp -A -o yaml | grep -n "authentication"`.
2. Decide what the requirement really was. If it was "encrypted in transit", use WireGuard or IPsec ([below](#transparent-encryption)). If it was "authenticated workload identity", use ztunnel mTLS or a mesh (Istio).
3. Do not assume the field still enforces anything in 1.21: upstream says it is accepted for compatibility but unused, so a policy that relied on `required` no longer requires authentication. How the agent surfaces this at runtime was not verified.
4. In 1.21 the `authentication.mutual.spire.*` chart values survive only because the SPIRE install and the operator's SPIRE client are reused by ztunnel `ca.type=spire`. They no longer configure mutual authentication.
5. Hubble `dropEventEmitter.reasons` no longer lists `auth_required` in 1.21.

## ztunnel Workload mTLS (Beta since 1.19)

### Architecture

`encryption.type=ztunnel` makes Cilium run Istio's per-node L4 proxy (ztunnel concept) with Cilium itself as the control plane.

```
 enrolled Pod A (netns)                         enrolled Pod B (netns)
  app --> iptables (in-pod) --> :15001           :15008 (HBONE in) --> ztunnel --> :15006 --> app
                                   |                  ^
                                   v                  |
                    node A ztunnel (DaemonSet, hostNetwork)  ==HBONE: HTTP/2 CONNECT over mTLS, TCP 15008==> node B ztunnel
                                   ^   xDS (workloads)   ^ CSR to Cilium CA
                                   |                     |
                     Cilium agent: xDS/ADS server, ZDS unix socket (/var/run/cilium/ztunnel.sock),
                                   built-in CA (IstioCertificateService), enrollment reconciler
```

- A `ztunnel-cilium` DaemonSet (hostNetwork, container `istio-proxy`) runs per node; the image in 1.20 and 1.21 is `quay.io/cilium/ztunnel:v1.0.0` (1.19 used `docker.io/istio/ztunnel` 1.28.0-distroless).
- The agent serves workload data (from CEPs) over xDS, passes Pod network namespace file descriptors and metadata over the ZDS unix socket, and signs workload CSRs whose URI SAN is `spiffe://<trust domain>/ns/<ns>/sa/<sa>` for service accounts that have endpoints on that node.
- iptables rules are installed **inside each enrolled Pod's netns**: outbound goes to 15001, plaintext inbound to 15006, HBONE inbound on 15008 is not redirected (mark 0x539). The wire protocol is HBONE (HTTP/2 CONNECT over mTLS) on **TCP 15008**.
- Differences from Istio ambient: no istiod, no waypoint, no L7 features; enrollment is the label `io.cilium/mtls-enabled=true`, not `istio.io/dataplane-mode=ambient`; the CA is Cilium's internal CA or SPIRE. Do not run both on the same Pods.

### Secrets, CA type and enrollment

Generate the bootstrap and CA key material before installing (script in the upstream repo at `examples/kubernetes-ztunnel/generate-secrets.sh`). The secret `cilium-ztunnel-secrets` in `kube-system` holds `bootstrap-private.key`, `bootstrap-root.crt`, `ca-private.key`, `ca-root.crt`. Upstream describes the roles: the bootstrap pair secures ztunnel's connection to Cilium's xDS and certificate server; the CA pair is the root for in-memory, ephemeral workload certificates.

```yaml
# values-ztunnel.yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal   # default; "spire" is new in 1.20
```

| `encryption.ztunnel.ca.type` | Behaviour |
|---|---|
| `internal` (default) | Cilium's built-in CA signs workload certificates; no SPIRE reconciler |
| `spire` (1.20+) | An external SPIRE server issues identities; the operator registers entries (parent `/ztunnel`, path `/ns/<ns>/sa/<sa>`) for service accounts in enrolled namespaces |

The `spire` mode is not described in the upstream encryption guide; this review verified only the operator code path, not an end-to-end deployment. Treat it as an advanced option and test it separately.

Enrol or remove a namespace:

```bash
kubectl label namespace demo io.cilium/mtls-enabled=true
kubectl label namespace demo io.cilium/mtls-enabled-      # disenroll
```

All existing Pods (except ztunnel Pods) and future Pods in the namespace are enrolled. Enrollment is namespace-level only; host-network Pods are skipped.

### Limits

| Limit | Detail |
|---|---|
| Both peers enrolled | Enrolled to non-enrolled traffic is unsupported |
| TCP only | UDP and others are not redirected |
| Policy interaction | Traffic is encrypted before leaving the Pod, so L4 policy cannot see inner ports; only the HBONE port 15008 can be targeted |
| Kernel | Requires iptables support |
| ClusterMesh | Incompatible: enabling both gives a validation error |
| Enrollment | Label on namespace only; no Pod-level enrollment |

On EKS, the peers are in the same VPC, so node security groups must allow TCP 15008 between nodes (self-referencing the node security group, never a public CIDR).

### Verify

```bash
kubectl -n kube-system describe cm cilium-config | grep enable-ztunnel -A2
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system exec ds/cilium -- cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'
# inside a Cilium Pod on the node hosting an enrolled Pod (install tcpdump first)
tcpdump -i eth0 port 15008      # use cilium_vxlan when tunnelling
```

## Transparent Encryption

Common rules: by default only Cilium-managed Pod traffic crossing nodes is encrypted; same-node traffic is never encrypted. Egress to an endpoint the node has not yet learned can leave unencrypted, because the decision uses the same ipcache/policy mechanism. Mitigate with strict mode or egress policy that denies `world`.

### Encryption packet walk

```
Pod A (node 1) -> Pod B (node 2), WireGuard, tunnel mode

 Pod A veth --> bpf_lxc: policy ok, ipcache says dst is remote Cilium endpoint
            --> encryption marks the packet (dst is a managed remote endpoint)
            --> VXLAN/Geneve encapsulation (cilium_vxlan / cilium_geneve)
            --> routed into cilium_wg0 (WireGuard: UDP 51871, peer chosen by CiliumNode pubkey)
            --> NIC (outer IP: node 1 -> node 2)
 NIC (node 2) --> cilium_wg0 decrypt --> tunnel decapsulation --> bpf_lxc ingress policy --> Pod B

Native routing: the VXLAN/Geneve steps are absent; the inner packet is Pod A -> Pod B directly
inside WireGuard. IPsec uses the same decision point but the XFRM state for (src node, dst node)
applies ESP after encapsulation.
```

This is a conceptual summary, not a trace of the exact BPF program order; see [Part 8](08-ebpf-datapath-internals.md) for the program layout. Two consequences follow. First, the "is the destination a managed remote endpoint" decision comes from the ipcache, so an unlearned destination is treated as external (the leak window). Second, because encryption happens after policy and encapsulation, host-level capture on the physical NIC sees only ciphertext, while a capture on `cilium_wg0` sees the inner packet.

### WireGuard (stable)

Mechanism: each agent generates a key pair, publishes its public key in the `CiliumNode` annotation `network.cilium.io/wg-pub-key`, and builds a WireGuard peer for each other node on the device `cilium_wg0`. UDP port **51871** on every node. Requires kernel WireGuard (`CONFIG_WIREGUARD`, Linux 5.6 or newer, or the out-of-tree module). In tunnel mode, Pod traffic is double-encapsulated: VXLAN/Geneve first, then WireGuard, which is why MTU matters ([Part 9](09-overlay-native-routing.md)).

```yaml
encryption:
  enabled: true
  type: wireguard
  wireguard:
    persistentKeepalive: 0s
```

- With CNI chaining (AWS VPC CNI) set `cni.enableRouteMTUForCNIChaining=true`; otherwise encrypted Pod traffic may fragment.
- ClusterMesh needs WireGuard on all clusters and UDP 51871 between clusters.
- Packet drops while the device is being configured are a known issue (gh-33159 upstream).
- **Node-to-node** (`encryption.nodeEncryption`, beta): extends encryption to host traffic. Control-plane nodes opt out via `node-encryption-opt-out-labels`. There are gaps for north-south paths with XDP or non-Geneve DSR. **[1.21 pre-release]** deprecated, removal in 1.22.

### Strict mode

| Helm value | Meaning |
|---|---|
| `encryption.strictMode.egress.enabled` | Drop unencrypted traffic that leaves a node to the strict CIDR |
| `encryption.strictMode.egress.cidr` | The Pod CIDR to enforce (IPv4 only; IPv6 is not protected) |
| `encryption.strictMode.egress.allowRemoteNodeIdentities` | Needed with tunnelling or when node and Pod CIDRs overlap |
| `encryption.strictMode.ingress.enabled` | Drop cluster-internal ingress that did not arrive through WireGuard; **WireGuard only** |

Ingress strict mode (1.19+) is supported in both tunnel and native routing in 1.20.2 docs (1.19 upgrade notes said tunnelling was required). Limits: not with CNI chaining, does not protect node-to-node traffic, and relies on Cilium's BPF being attached to every interface that can carry Pod traffic.

**Flag rename in 1.20**: the old flags `--enable-encryption-strict-mode`, `--encryption-strict-mode-cidr` and `--encryption-strict-mode-allow-remote-node-identities` (deprecated in 1.19) were **removed**. Use `--enable-encryption-strict-mode-egress`, `--encryption-strict-egress-cidr`, `--encryption-strict-egress-allow-remote-node-identities`, and `--enable-encryption-strict-mode-ingress`. Helm moved from `encryption.strictMode.{enabled,cidr,allowRemoteNodeIdentities}` to `encryption.strictMode.egress.*`. The 1.20 upgrade note spells the CIDR value `cidrs` while the 1.20.2 chart `values.yaml` has `cidr`; the chart is authoritative.

### IPsec (stable)

Mechanism: the agent programs Linux XFRM states and policies from a pre-shared key in a Secret. Packets are ESP-encapsulated after any overlay encapsulation (since 1.18 this ordering is fixed; the `encryptedOverlay` option is gone).

```bash
kubectl create -n kube-system secret generic cilium-ipsec-keys \
  --from-literal=keys="3+ rfc4106(gcm(aes)) $(dd if=/dev/urandom count=20 bs=1 2>/dev/null | xxd -p -c 64) 128"
```

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyWatcher: true
    keyRotationDuration: 5m
```

- Secret value format: `key-id algorithm PSK-hex key-size`. The `+` after the key id forces **per-tunnel derived keys**; global keys were deprecated in 1.16 (GHSA-pwqm-x5x6-5586).
- Rotation: key IDs run 1..15 and are meant to increase on every re-key, wrapping from 15 back to 1 (`encryption-ipsec.rst:206-218`; the upstream snippet resets `KEYID` to 0 when it is 15 or more). A plain "patch with a higher ID" therefore fails at the wrap: after ID 15 the next Secret must use ID 1. Patch the Secret with the next ID; agents watch it (`keyWatcher`) and remove the old key after `keyRotationDuration` plus jitter of up to a tenth of it. Do not rotate during an upgrade. With ClusterMesh, rotate in every cluster.
- Direct routing needs `ipv4NativeRoutingCIDR`. Not supported with CNI chaining. Maximum 65535 nodes; decryption for a tunnel is bound to one CPU core.
- Verify with `cilium-dbg encrypt status` (keys in use, XFRM error counters), `tcpdump -l -n -i eth0 esp`. Security groups must allow ESP (IP protocol 50) between nodes by self-reference; the UDP 500/4500 requirement was not verified in this review.
- **Removed in 1.20**: `encryption.ipsec.interface` (`--encrypt-interface`; a no-op since 1.18) and `encryption.ipsec.encryptedOverlay`. The 1.20.2 chart `values.yaml` and the IPsec guide still mention `interface`, so this is an upstream inconsistency; do not set it.
- **Host policies do not work with IPsec** (gh-41854 upstream).

### MTU overhead

Encryption adds header bytes, which reduce the usable Pod MTU, and tunnel mode adds the tunnel header on top. Cilium derives route MTU automatically; with CNI chaining set `cni.enableRouteMTUForCNIChaining`. Part 9 computes the byte counts from `pkg/mtu/mtu.go` (v1.20.2): WireGuard 95, IPsec 77 with the default key size, VXLAN over an IPv4 underlay 50; see its [MTU math section](09-overlay-native-routing.md). They are computed, not measured, so confirm with `ping -M do -s <size>` between Pods and `ip link` on the Cilium devices.

### Choosing

| Need | Pick |
|---|---|
| Simple Pod-to-Pod network encryption, no key handling | WireGuard |
| FIPS/compliance or kernel without WireGuard, accept key rotation duty | IPsec |
| Workload identity bound to the encrypted channel, namespace-scoped opt-in, TCP only | ztunnel |
| Cross-cluster (ClusterMesh) | WireGuard or IPsec (ztunnel is incompatible) |
| L7-aware mTLS, authorization, waypoints | Istio |

## Service Mesh TLS Options

| Option | What it provides | Notes |
|---|---|---|
| Istio sidecar | mTLS between sidecars, L7 policy in Istio | Cilium and Istio L7 policy should not both apply HTTP rules; for Cilium L7 on those Pods, set Istio `PeerAuthentication` mTLS to `DISABLE` |
| Istio ambient | ztunnel/HBONE 15008, optional waypoint | Cilium sees only encrypted L4 on 15008; to apply Cilium L7, remove `istio.io/dataplane-mode` or annotate the Pod `ambient.istio.io/redirection: disabled` |
| Cilium ztunnel | L4 mTLS only | See above |
| Envoy TLS in Cilium (CEC/Gateway API) | TLS termination/origination at the Envoy | For ingress/egress visibility, not for east-west mesh mTLS |

Istio coexistence (upstream `network/servicemesh/istio.rst`): `kubeProxyReplacement=false` is recommended; if replacement is on, set `socketLB.hostNamespaceOnly=true` and `cni.exclusive=false`. With sidecars on overlay, istiod needs `hostNetwork: true`. See also [Part 5](05-l2-l7-networking.md).

**TLS interception** (`terminatingTLS` / `originatingTLS` in CNP `toPorts`): Envoy terminates the client's TLS with a certificate from an internal CA that clients must trust, then re-originates to the destination. Secrets are delivered over SDS (default since 1.17); Helm `tls.secretsNamespace.name` defaults to `cilium-secrets` and `tls.readSecretsOnlyFromSecretsNamespace` is true, so the operator copies referenced Secrets there. This gives visibility for L7 policy on encrypted egress; it is not a mesh mTLS replacement.

**Gateway API TLS**: HTTPS listener termination uses a Secret; `BackendTLSPolicy` (gateway.networking.k8s.io/v1; `targetRefs` Service, `validation.caCertificateRefs` ConfigMap, `hostname`) encrypts traffic from Envoy to the backend. Cilium 1.20 requires Gateway API v1.6.1 CRDs; TLSRoute is v1 and needs the experimental channel if you used it earlier; otherwise, existing objects disappear. cert-manager integrates through the `cert-manager.io/issuer` annotation. **Exposure rule**: upstream Gateway/Ingress examples create `Service` type `LoadBalancer`. On EKS use an internal scheme (`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`) behind a CloudFront VPC origin; never internet-facing. This was not verified against the Cilium chart in this review. See [Part 11](11-bgp-lb-egress-edge.md).

## Hubble and Tetragon

### Hubble components

Hubble's server runs inside each agent (gRPC on `hubble.listenAddress`, default `:4244`, plus the unix socket `/var/run/cilium/hubble.sock`). **Relay** (`hubble.relay.enabled`, default false; listens on 4245) aggregates all nodes behind one API. The **UI** (`hubble.ui.enabled`, default false) sits on Relay. Server and Relay use mTLS by default (`hubble.tls.enabled: true`). Keep Relay and UI as ClusterIP (or an internal LB behind CloudFront VPC origin); do not publish them.

Event path: datapath events, then the per-agent ring buffer (`hubble.eventBufferCapacity`, default 4095; allowed values are 2^n-1 up to 65535), then observers (CLI, Relay, exporters, metrics). `hubble.networkPolicyCorrelation.enabled` (default true) adds the allowing/denying policy to flows.

### Metrics

`hubble.metrics.enabled` takes a list of handlers (for example `dns`, `drop`, `tcp`, `flow`, `port-distribution`, `icmp`, `httpV2`, `flows-to-world`, `policy`; `sctp` is new in 1.20; the handler is absent in v1.19.8). Endpoint port 9965. Dynamic metrics (`hubble.metrics.dynamic.enabled`, ConfigMap `cilium-dynamic-metrics-config`) reconfigure without an agent restart. L7 handlers produce data only for Pods with L7 visibility. The Kafka handler was removed in 1.20. `hubble.metrics.portName` is new **[1.21 pre-release]**.

### Exporters

- Static: `hubble.export.static.enabled`, `filePath` (default `/var/run/cilium/hubble/events.log`; `stdout` allowed), `fileMaxSizeMb`, `fileMaxBackups`, `fileCompress`, `allowList`, `denyList`, `fieldMask`; `fieldAggregate` with `aggregationInterval` since 1.19. Bound to the agent lifecycle.
- Dynamic: `hubble.export.dynamic.enabled` with `config.content[]` entries (`name`, `filePath`, `fieldMask`, `includeFilters`, `excludeFilters`, `end`, rotation fields) stored in the ConfigMap `cilium-flowlog-config`, applied without restart (changes take effect within about a minute).

### Redaction (L7)

`hubble.redact.enabled` (false by default), `http.urlQuery` (false), `http.userInfo` (true), and `http.headers.allow` **or** `deny` (not both). Example: deny `Authorization` and `Proxy-Authorization`. The Kafka `apiKey` redaction was removed in 1.20 with Kafka support.

```yaml
hubble:
  redact:
    enabled: true
    http:
      urlQuery: true
      userInfo: true
      headers:
        deny:
        - Authorization
        - Proxy-Authorization
```

### Drop events

`hubble.dropEventEmitter` (alpha) emits Kubernetes Events for dropped traffic; `interval` 2m; `reasons` default in 1.20.2 is `auth_required` and `policy_denied`; in 1.21 `auth_required` is no longer listed.

### Tetragon (overview only)

Tetragon is a separate project (not part of the Cilium repository): eBPF-based runtime security observability and enforcement for process execution, file and network activity, configured with `TracingPolicy` resources. Cilium's threat-model documentation recommends it for runtime visibility. Details of its CRD versions and enforcement actions were **not verified in this review** and this section is an overview only; use the Tetragon project documentation for specifics.

## Certificate Management

| Component | Cert source | Rotation |
|---|---|---|
| Hubble server, Relay, metrics | `hubble.tls.auto.method`: `helm` (default), `cronJob`, `certmanager` | `helm`: regenerated only on a Helm render (no automatic renewal); `cronJob`: certgen CronJob, schedule `0 0 1 */4 *`; `certmanager`: cert-manager renews, set `certManagerIssuerRef` |
| ClusterMesh API server | same three methods under `clustermesh.apiserver.tls.auto` | see [Part 13](13-clustermesh-install-upgrade.md) |
| ztunnel workloads | internal CA or SPIRE | Short-lived, in memory |
| IPsec / WireGuard | PSK secret / auto key pairs | Manual key rotation (IPsec); WireGuard automatic |

Values to know (1.20.2 `values.yaml`): `hubble.tls.auto.certValidityDuration` defaults to **365** days and the shared auto-generated CA (`tls.ca.certValidityDuration`) to **1095** days. Upstream prose elsewhere cites a three-year default for the leaf certificate; the chart value is the one that applies. Server and Relay certificates and the CA are hot-reloaded.

1.20 changes:

- ClusterMesh auto certificates default to 1 year (`clustermesh.apiserver.tls.auto.certValidityDuration: 365`; was 1095 in 1.19). With the `helm` method, certificates renew only when the chart is rendered, so upgrade at least yearly; `cronJob` and `certmanager` renew automatically (ClusterMesh cronJob regenerates every four months).
- `certgen.enforceCAValidityThroughoutLeavesDuration` defaults to true: certgen fails if the CA would expire before a leaf certificate. Set false to disable.
- Support for certificates supplied manually as Helm values was removed: pre-create the Secrets and set `tls.auto.enabled=false`.
- `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` moved to `...tls.auto.server.*`.

User-provided Hubble certificates need these SANs: `*.<cluster>.hubble-grpc.cilium.io` (server), `*.hubble-relay.cilium.io` (Relay), `*.hubble-ui.cilium.io`, `<cluster>.hubble-metrics.cilium.io`; Secrets carry `tls.crt`, `tls.key`, `ca.crt`. **[1.21 pre-release]** per-Pod certificates: `hubble.tls.disableDefaultVolumes`, `hubble.relay.tls.disableDefaultVolumes`, `hubble.ui.tls.disableDefaultVolumes` and `extraInitContainers` allow Vault, cert-manager CSI or SPIFFE sources; `clustermesh.apiserver.tls.authMode` default becomes `cluster`.

```yaml
hubble:
  tls:
    auto:
      enabled: true
      method: certmanager
      certManagerIssuerRef:
        group: cert-manager.io
        kind: ClusterIssuer
        name: hubble-issuer
```

## Labs

None of these labs were executed against a live cluster in this review (see Validation Limits). Use a disposable cluster. All security-group notes assume node-to-node rules that reference the node security group itself; never open any port to `0.0.0.0/0` or `::/0`.

### Lab 1: Identities, ipcache and label exclusion

Prerequisites: a Cilium 1.20.2 cluster, kubectl, `cilium-dbg` through the agent Pod.

1. Create a namespace and two Deployments `web` (`app=web`) and `db` (`app=db`), each with 2 replicas.
2. `kubectl get ciliumidentities`: expect one identity for the `web` label set and one for `db`, both shared by their replicas.
3. `kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list`, and note IDs of `web` and `db`.
4. Pick one `web` Pod IP and run `cilium-dbg bpf ipcache list | grep <podIP>`: the entry's identity equals the `web` identity.
5. Relabel one `web` Pod with `kubectl label pod <pod> release=r2 --overwrite`. Expected: a new identity appears for that Pod and `kubectl get ciliumidentities` grows by one, demonstrating label churn.
6. Cleanup: delete the namespace. If you changed identity-relevant labels via Helm, roll the change back with `helm upgrade` (`--reuse-values` is valid only if the cluster is already on this chart version, 1.20.2; otherwise pass your saved values explicitly) and restart the agents (identities change only after agent restart).

### Lab 2: WireGuard with strict ingress

Prerequisites: nodes with kernel WireGuard; node security group allows UDP 51871 from the node security group itself.

1. `helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values --set encryption.enabled=true --set encryption.type=wireguard`; restart agents if the rollout does not. `--reuse-values` is only valid when the cluster is already on chart 1.20.2 (the chart version must not change; upstream `upgrade.rst:206-221`). If it is on another version, save `helm get values cilium -n kube-system -o yaml`, review renamed values, and pass them with `-f` instead.
2. `kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep Encryption`. Expected: a `Wireguard [cilium_wg0 (...Port: 51871, Peers: N)]` line with N equal to node count minus one.
3. Generate traffic between Pods on different nodes and run `tcpdump -n -i cilium_wg0` in an agent Pod. Expected: the cleartext Pod-to-Pod flow is visible on `cilium_wg0`; a capture on the physical interface for UDP 51871 shows only encrypted packets.
4. Enable strict mode: `--set encryption.strictMode.egress.enabled=true --set encryption.strictMode.egress.cidr=<podCIDR> --set encryption.strictMode.ingress.enabled=true`. Set `allowRemoteNodeIdentities=true` if tunnelling.
5. Expected: normal Pod traffic continues; unencrypted Pod traffic that bypasses WireGuard is dropped (injecting such traffic needs a host-level tool and is optional).
6. Rollback: set the strict values to false first, then `encryption.enabled=false`, and restart agents. Expect brief drops while the device reconfigures (upstream known issue).

### Lab 3: ztunnel enrollment

Prerequisites: no ClusterMesh, nodes with iptables, node security group allows TCP 15008 between nodes.

1. From the Cilium source tree at the same tag, run `bash examples/kubernetes-ztunnel/generate-secrets.sh` (creates `cilium-ztunnel-secrets` in `kube-system`).
2. Upgrade with `encryption.enabled=true`, `encryption.type=ztunnel`. Check `kubectl -n kube-system get ds ztunnel-cilium` and `describe cm cilium-config | grep enable-ztunnel -A2`.
3. Create namespaces `mtls-on` and `mtls-off` with an HTTP server and a curl client in each. Label only `mtls-on`: `kubectl label ns mtls-on io.cilium/mtls-enabled=true`. Existing Pods are enrolled automatically; no restart is needed.
4. `cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'` should list `mtls-on`.
5. Client in `mtls-on` to server in `mtls-on` on a different node: `tcpdump -i eth0 port 15008` on the node shows HBONE packets.
6. Client in `mtls-on` to server in `mtls-off`: expected to fail, since mixed enrolled/non-enrolled traffic is unsupported.
7. Cleanup: `kubectl label ns mtls-on io.cilium/mtls-enabled-`, delete namespaces, then `encryption.enabled=false` and delete `cilium-ztunnel-secrets`.

### Lab 4: Policy audit, CIDR group and deny

1. Create namespace `pol` with `client` and `server` Pods (HTTP on 8080).
2. Turn on audit mode for the server endpoint: `cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled`.
3. Apply a CNP that allows ingress to `server` only from `app=client` on 8080. From a third Pod, curl the server and run `hubble observe --verdict AUDIT -n pol`: expect `AUDIT` verdict for the third Pod and the request still succeeding.
4. Disable audit mode with `PolicyAuditMode=Disabled`; repeat: the request is now dropped (`hubble observe --verdict DROPPED`).
5. Add a `CiliumCIDRGroup` (the manifest above) and an egress rule `toCIDRSet` with `cidrGroupRef`; verify `cilium-dbg identity list` shows a CIDR-derived identity and flows annotate the group.
6. Add an `ingressDeny` rule for `app=client`; expect the client is dropped even though an allow rule exists (deny precedence).
7. Cleanup: delete the namespace and the CCG.

### Lab 5: Hubble export, redaction and cert-manager

Prerequisites: cert-manager and a ClusterIssuer installed.

1. Enable Relay and dynamic export: `hubble.relay.enabled=true`, `hubble.export.dynamic.enabled=true`, `hubble.redact.enabled=true`, `hubble.redact.http.urlQuery=true`, and `hubble.tls.auto.method=certmanager` with `certManagerIssuerRef`.
2. Edit the ConfigMap `cilium-flowlog-config` to add an exporter with an `includeFilters` entry such as `source_pod: ["kube-system/"]`. Expected: a new file appears under the Hubble export directory in the agent Pod without an agent restart (allow about a minute).
3. Run L7-visible HTTP traffic with a query string and an `Authorization` header (visibility needs an L7 policy on the Pod). Expected: `hubble observe -o json` shows query and header values redacted.
4. `kubectl get certificate -n kube-system`: the Hubble certificates are issued by your ClusterIssuer.
5. Rollback: remove the exporter entry, set `hubble.redact.enabled=false`, and revert the certificate method.

## Version Delta

| Topic | 1.18 | 1.19 | 1.20 | 1.21 pre-release |
|---|---|---|---|---|
| Mutual Authentication | Beta | Beta; disabled by default (`authentication.enabled=false`) | Deprecated | Removed; policy `authentication` field unused |
| ztunnel | - | Introduced (beta); startup validation already rejects ClusterMesh (`pkg/ztunnel/cell.go:46`) | `ca.type` internal/spire; image `quay.io/cilium/ztunnel` | Beta; SPIRE chart reused for `ca.type=spire` |
| Strict mode flags | only `strictMode.{enabled,cidr,allowRemoteNodeIdentities}` | `strictMode.egress.*` and `strictMode.ingress.*` added; old flags deprecated | Old flags removed (`...-egress-*` names) | unchanged |
| IPsec | `encryptedOverlay` no-op | - | `encryptedOverlay` and `ipsec.interface` removed | - |
| WireGuard `nodeEncryption` | not checked | not checked | beta | Deprecated; removal 1.22 |
| Policy | Kafka/proxylib deprecated | `FromRequires`/`ToRequires` must be empty | Kafka/proxylib removed; CEL rejects empty CNP/CCNP; ClusterNetworkPolicy | `toPorts[].listener` redirect |
| Hubble | - | export `fieldAggregate`/`aggregationInterval` | Kafka metrics and redaction removed; certs 1 year default (ClusterMesh); certgen CA-validity check | per-Pod certificates, `portName`, UI `httpRoute` |
| Identity | Double Write documented | documented | documented | `preflight migrate-identity` deprecated |

## Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Policy drops traffic from a new Pod briefly | Pod still `reserved:init` or ipcache not yet propagated | `cilium-dbg endpoint list`, `cilium-dbg bpf ipcache get <ip>` |
| `fromEntities: cluster` unexpectedly matches or misses NodePort traffic | Source identity is `world` or `remote-node` depending on routing mode | See entity caveat above; `hubble observe` for the identity |
| Identity count grows without bound | Volatile labels are identity-relevant | `kubectl get ciliumidentities \| wc -l`; exclude the label |
| `kubectl apply` of a CNP is rejected with "spec or specs must be provided" | 1.20 CEL rule | Provide `spec` or `specs` |
| WireGuard peers count wrong or no `cilium_wg0` | Kernel module missing or UDP 51871 blocked between nodes | `cilium-dbg status \| grep Encryption`, node security group |
| Large packets stall with encryption | MTU too high for encryption plus tunnel | Test with `ping -M do`; check CNI chaining flag |
| IPsec errors counters rising | Key mismatch or stale XFRM state | `cilium-dbg encrypt status`; key rotation clears stale states |
| Host policy has no effect with IPsec | Unsupported combination | Use WireGuard or drop host policies |
| Enrolled namespace but no HBONE packets | Peers not both enrolled, host-network Pod, or UDP traffic | `statedb dump`, Pod type, protocol |
| Agent fails to start after enabling ztunnel | ClusterMesh enabled | Disable one of them |
| Hubble Relay certificate errors after a year | `helm` method does not auto-renew | Switch to `cronJob` or `certmanager`, or upgrade Helm yearly |
| Policy with `authentication` no longer authenticates after 1.21 | Feature removed | Migrate as described above |

## Validation Limits and Sources

The labs were not executed against a live cluster in this review and were checked against upstream source and documentation at the tags below. Facts about Tetragon, the ztunnel `ca.type=spire` end-to-end flow, IPsec ESP/UDP firewall requirements, and runtime behaviour of leftover `authentication` policy fields were not verified and are marked in the text. Items tagged **[1.21 pre-release]** come from v1.21.0-pre.3 and may change before GA. Upstream mismatches deliberately not copied: the FQDN per-hostname IP limit (doc versus code defaults), the Hubble certificate default lifetime in prose versus `values.yaml`, `CiliumCIDRGroup` docs showing `v2alpha1` while storage is `v2`, and the `policyCIDRMatchMode` values comment.

- [1.20 upgrade notes](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc), [Mutual Authentication (1.20)](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst), [Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [policy overview](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/policy.rst)
- [Transparent encryption](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption.rst), [WireGuard](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-wireguard.rst), [IPsec](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-ipsec.rst), [CNP CEL rule](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/v2/cnp_types.go)
- [1.21 upgrade notes (pre-release)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc), [ztunnel guide (pre-release)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/network/encryption-ztunnel.rst), [identity allocation and Double Write](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade.rst), [numeric identity](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/identity/numericidentity.go), [policy layer 3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/policy/layer3.rst), [Hubble TLS](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/tls.rst), [Hubble export](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/export.rst)

## Quiz

[Check your mTLS, encryption and identity understanding](../../quizzes/networking/cilium/12-mtls-encryption-identity-quiz.md).

[Return to Main Page](README.md)
