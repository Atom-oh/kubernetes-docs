# Part 2: Architecture

> **Review baseline**: Calico Open Source 3.32.2 / operator 1.42.6; Calico 3.32 is tested against Kubernetes 1.34–1.36.
> **Last Updated**: September 12, 2026. Examples are configuration references, not a live-cluster validation.

## Overview

This section provides an in-depth exploration of Calico's architecture. Understanding how each component works and interacts is essential for effective deployment, troubleshooting, and optimization of Calico in production environments.

## Full Architecture Diagram

![Simplified Kubernetes API and Typha state fan-out toward Felix and the BGP configuration path, with intermediate components omitted.](../../.gitbook/assets/en-networking-calico-02-architecture-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-0.html)

This is a simplified control-state diagram. The BIRD edge omits confd, which renders its configuration; Typha is not a direct BIRD configuration API. BIRD/confd and Typha depend on the installation mode, and control-plane components are not all shown.

## Felix: The Calico Agent

Felix runs in the Calico node agent on selected workload nodes and programs applicable routes, interface settings and policy in the kernel. In the Linux full-networking path, the container runtime invokes the CNI chain, and the CNI/IPAM plugins create interfaces and allocate addresses. Felix observes endpoint changes asynchronously; it is not the handler of a direct CNI ADD call. Operator, platform and networking mode determine the exact components.

### Felix Responsibilities

Linux CNI/IPAM creates Pod interfaces and addresses. Felix reconciles endpoint state and kernel policy. HTTP health serving and datastore status reporting are separate functions.

### Core Functions

1. **Route Programming**: Reconciles applicable workload and tunnel routes; BIRD's kernel protocol also installs learned routes in BGP mode
2. **ACL Enforcement**: Programs iptables/nftables/eBPF rules for network policies
3. **Interface Management**: Reconciles endpoint interface state and relevant kernel settings; Linux veth creation belongs to the CNI path
4. **Health Reporting**: Reports node and endpoint health to the datastore
5. **Endpoint reconciliation**: Watches workload endpoint state and programs applicable policy/routes; the CNI/IPAM plugins allocate addresses and create Linux Pod interfaces

### Felix Data Plane Options

Felix supports multiple data plane backends:

| Data Plane   | Description                | Best For                                    |
| ------------ | -------------------------- | ------------------------------------------- |
| **iptables** | Traditional Linux firewall | Compatibility, mature deployments           |
| **nftables** | Native nftables implementation | Check supported kernel, platform and feature set |
| **eBPF** | In-kernel programmable | Optional Service handling; requires a coordinated migration and supported features |

### FelixConfiguration Resource

```yaml
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  healthEnabled: true
  healthPort: 9099
  prometheusMetricsEnabled: true
  prometheusMetricsPort: 9091
  reportingInterval: 30s
  reportingTTL: 90s
```

This minimal example uses fields accepted by Calico 3.32.2. Apply changes through the configuration owner; it is not a data-plane migration or performance-tuning recipe. Felix's health host defaults to localhost. Enabling metrics does not configure a Prometheus scrape or make public exposure appropriate.

| Configuration concern | Correct owner / interpretation |
|---|---|
| Linux data plane | Operator `Installation.spec.calicoNetwork.linuxDataplane` selects `Iptables`, `Nftables` or `BPF` for the supported configuration |
| `bpfEnabled` | Low-level Felix setting; coordinate an operator-managed transition and kube-proxy/API reachability rather than patching this alone |
| `iptablesBackend: NFT` | Selects the iptables-nft tool backend, not the native Calico nftables data plane |
| Connect-time load balancing | Current field is `bpfConnectTimeLoadBalancing: TCP`, `Enabled` or `Disabled`; the older boolean `bpfConnectTimeLoadBalancingEnabled` is still accepted but deprecated |
| Node address detection | Operator `calicoNetwork.nodeAddressAutodetectionV4` / `V6`, or the node startup environment in a manifest-managed install; not Felix fields named `ipAutoDetectionMethod` or `ipv6AutoDetectionMethod` |
| Flow visibility | Use the supported Goldmane/Whisker configuration; Open Source does not accept the Enterprise file-log fields shown in the previous example |
| MTU and tunnel modes | Derive from the underlay, encapsulation and encryption; coordinate Installation/IPPool settings rather than arbitrarily setting 1440/1410/1420 or enabling every tunnel |
| Host failsafe ports | Review actual API/BGP/etcd/administrative reachability before replacing the default lists; the old shortened lists could remove needed exceptions |
| Durations | Use current names such as `reportingInterval`, `reportingTTL`, `iptablesPostWriteCheckInterval` and `iptablesLockProbeInterval`; do not mechanically append `Secs`/`Millis` |

The released schema rejects the old `iptablesLockFilePath`, `iptablesLockTimeoutSecs`, `iptablesLockProbeIntervalMillis`, `iptablesPostWriteCheckIntervalSecs`, `reportingIntervalSecs` and `reportingTTLSecs` names. Consult the [Felix resource reference](https://docs.tigera.io/calico/latest/reference/resources/felixconfig) and [operator API](https://docs.tigera.io/calico/latest/reference/installation/api). Address or data-plane changes require their own rollout checks.

### Felix iptables Rule Structure

The following are selected prefixes from the [released rule definitions](https://github.com/projectcalico/calico/blob/v3.32.2/felix/rules/rule_defs.go), not the complete chain graph. They describe the iptables data plane; inspect actual rules for the installed mode and configuration.

| Chain/prefix | Role |
|---|---|
| `cali-FORWARD` | Calico forwarding hook |
| `cali-from-wl-dispatch` | Dispatch from workload interfaces |
| `cali-to-wl-dispatch` | Dispatch to workload interfaces |
| `cali-fw-…` / `cali-tw-…` | Per-workload directional chains |
| `cali-pi-…` / `cali-po-…` | Inbound/outbound policy chains |

### Felix Data Flow

On Pod creation, the runtime invokes the CNI/IPAM chain, which configures the network and records endpoint state. Felix observes relevant changes and programs policy/routes; BGP configuration follows its own confd/BIRD path when enabled. Pod Running does not prove routing or policy convergence.

## BIRD: BGP Routing Daemon

BIRD (BIRD Internet Routing Daemon) exchanges BGP routes when Calico's BGP backend is enabled. BIRD/confd are not mandatory in a policy-only or BGP-disabled VXLAN installation. The following topology examples require an appropriately designed BGP-enabled cluster; they are not additions to the BGP-disabled introductory kind lab.

### BIRD in Calico Architecture

![Diagram showing BIRD on each of three nodes forming a full iBGP mesh to exchange pod routes, then peering over eBGP with the top-of-rack switch, which passes those routes on to the core router.](../../.gitbook/assets/en-networking-calico-02-architecture-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-3.html)

The lines represent BGP sessions, not application-packet transit through BIRD. The size labels are illustrative guidance, not a protocol requirement or a fixed threshold for route reflectors.

### BGP Session Types

| Session Type          | Use Case                    | Configuration          |
| --------------------- | --------------------------- | ---------------------- |
| **Node-to-Node Mesh** | Default for small clusters  | Automatic, full mesh   |
| **Route Reflector** | Reduce mesh session count as topology requires | Configure and verify replacement peers first |
| **External Peering**  | On-premises integration     | Manual BGP peer config |

### BGP Configuration Examples

#### Node-to-Node Mesh (Default)

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
```

#### Route Reflector Configuration

Use the [official BGP transition procedure](https://docs.tigera.io/calico/latest/networking/configuring/bgp). Assigning a route-reflector cluster ID immediately removes that node from the existing node mesh and can disrupt workloads. Prepare dedicated nodes without application workloads, or plan an explicit maintenance migration. Do not replace an existing Calico Node with a partial object that omits its other settings.

For the Kubernetes API datastore, the documented node annotation preserves the existing Node fields. Replace these example names with the prepared nodes:

```bash
# Existing, prepared RR nodes with no application workloads.
kubectl get nodes rr-1 rr-2 -o yaml > rr-nodes-before.yaml
kubectl get bgpconfiguration.projectcalico.org default -o yaml > bgp-before.yaml
kubectl annotate node rr-1 projectcalico.org/RouteReflectorClusterID=244.0.0.1 --overwrite
kubectl annotate node rr-2 projectcalico.org/RouteReflectorClusterID=244.0.0.2 --overwrite
kubectl label nodes rr-1 rr-2 route-reflector=true --overwrite
kubectl apply -f - <<'YAML'
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: nodes-to-route-reflectors
spec:
  nodeSelector: all()
  peerSelector: route-reflector == 'true'
YAML
```

`all()` to the RR selector covers clients and RR-to-RR peering; verify both reflectors and the client routes. Wait for established sessions and confirm actual reachability before disabling the old node mesh. An Established session alone does not prove that the required routes were accepted.

```bash
# Only after replacement sessions, routes and test traffic have been verified.
kubectl patch bgpconfiguration.projectcalico.org default --type merge \
  -p '{"spec":{"nodeToNodeMeshEnabled":false}}'
```

This is an ordered transition, not an instruction to apply every block at once or a guarantee of no disruption. Keep the saved configuration and a tested recovery path. Addresses, ASNs and any reused AS numbers in external-fabric examples require deliberate route-policy and AS-loop handling.

#### External BGP Peering

Replace the example peer address, ASNs and rack selector with the planned topology. The password reference requires a matching Secret/key in the Calico node component's namespace and matching router configuration. It authenticates the BGP session, not the workload payload.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tor-switch-peer
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  nodeSelector: rack == 'rack-1'
  password:
    secretKeyRef:
      name: bgp-passwords
      key: tor-password
  sourceAddress: UseNodeIP
  keepOriginalNextHop: false
```

### Route Propagation Process

![Diagram showing Felix adding a route to the kernel routing table, BIRD picking up that route info through its BGP session management, and its route exchange function advertising the Pod CIDR to other nodes and external routers via a BGP UPDATE, with Route Reflector support for large clusters and export-filter-based route filtering shown as further BIRD functions.](../../.gitbook/assets/en-networking-calico-02-architecture-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-4.html)

This shows one route-information path. BIRD's kernel protocol can also install learned routes, while confd/IPAM data contributes to generated routing configuration. BGP route filters are routing policy, not Kubernetes NetworkPolicy enforcement.

### BIRD Status Commands

Select a node where BIRD is running. The released [startup script](https://github.com/projectcalico/calico/blob/v3.32.2/node/filesystem/etc/service/available/bird/run) sets the IPv4 control socket below. A manifest-managed installation may use another namespace.

```bash
CALICO_NODE=worker-node-name
CALICO_POD=$(kubectl -n calico-system get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')
: "${CALICO_POD:?No Calico Pod on the selected node}"
kubectl -n calico-system exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols
kubectl -n calico-system exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
```

Use the actual protocol names and prefixes from the output for more detailed queries. Commands and sample console output are different things; the former `birdcl>` prompts were not Bash commands. These read-only checks do not configure routing.

## confd: Configuration Management

confd is a lightweight configuration management tool that watches the Calico datastore and generates BIRD configuration files.

### confd Workflow

confd watches the relevant BGP configuration, renders its template, checks the candidate and signals BIRD to reload.

### confd Template Processing

Use the [released template](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/templates/bird.cfg.template), not an invented `.NodeIP` / `.BGPPeers` data structure. This excerpt illustrates kernel synchronization; its filter and surrounding configuration are defined elsewhere, so it is not a complete `bird.cfg`.

```text
protocol kernel {
  learn;
  persist;
  scan time 2;
  import all;
  export filter calico_kernel_programming;
  graceful restart;
  merge paths on;
}
```

The [confd template definition](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/conf.d/bird.toml) writes `/etc/calico/confd/config/bird.cfg`, validates the candidate with `bird -p -c {{.src}}`, and uses `sv hup bird || true` as its configured reload action. This establishes that BIRD can export selected learned routes to the kernel; it is not merely receiving every route from Felix. Reload and graceful-restart behavior still need status and traffic checks. Manage BGP settings through their API owner rather than editing the generated file.

## Typha: Scaling Component

Typha is a fan-out proxy that sits between the Kubernetes API server and Felix agents. It reduces load on the API server by caching and distributing datastore updates.

### Why Typha?

Typha reduces repeated datastore update processing by caching state and streaming changes to multiple clients. Installation ownership, TLS and actual scaling logic matter as well as node count.

### Typha scaling in operator 1.42.6

The operator deploys and scales Typha; there is no universal “only above 50 nodes” rule. The pinned [autoscaler implementation](https://github.com/tigera/operator/blob/v1.42.6/pkg/controller/installation/typha_autoscaler.go) counts nodes that are not marked unschedulable, excludes AKS virtual nodes, and separately checks for enough Linux nodes to place the desired replicas. Taints and other placement constraints still matter.

The actual [scale function](https://github.com/tigera/operator/blob/v1.42.6/pkg/common/autoscale.go), rather than its abbreviated comment, returns:

- 1 replica for 1–2 counted nodes.
- 2 replicas for 3–4 counted nodes.
- `max(3, floor(N / 200) + 2)` for 5 or more counted nodes.

| Counted nodes | Desired replicas in this version |
|---|---|
| 50 | 3 |
| 200 | 3 |
| 500 | 4 |
| 1,000 | 7 |
| 2,000 | 12 |

This is a version-specific desired count, not a per-replica capacity guarantee or a recommendation for every installation. Non-cluster-host mode uses a separate eligible HostEndpoint count. The former `max(3, ceil(N / 200))` table did not describe this operator.

### Operator-managed Typha configuration

Keep the operator's Deployment, ServiceAccount/RBAC, Service, disruption budget and TLS configuration together. The hand-written Deployment formerly shown here omitted essential dependencies and could overwrite operator-managed settings. Felix-to-Typha TLS uses a trusted CA, Typha server certificate/key and the expected Felix client identity. Port 5473 is the default sync port, not a user-traffic proxy.

```bash
# Change the operator's supported setting through its API.
kubectl patch installation.operator.tigera.io default --type merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl -n calico-system get deployment calico-typha -o yaml
kubectl -n calico-system get service calico-typha -o yaml
kubectl -n calico-system get pdb
```

Typha's health endpoint defaults to localhost:9098. This operator derives the health port as the configured Felix health port minus one and configures probes accordingly. A Pod-network Deployment whose probe targets the Pod IP will not reach a listener bound only to localhost; copying probes without their network/bind settings is unsafe. The operator source supplies TLS mounts and client-identity settings that are absent from the old standalone example.

### Typha Fan-out Architecture

Each Typha maintains cached state for its client streams. Client grouping in a diagram is not a fixed per-instance capacity specification.

## kube-controllers: Kubernetes Integration

calico-kube-controllers runs selected reconciliation functions. Which controllers run depends on the datastore, edition and installation configuration. Policy/namespace/service-account projection into an etcd datastore is different from Kubernetes API datastore handling.

### Available controller roles

| Controller                      | Purpose                                           |
| ------------------------------- | ------------------------------------------------- |
| **Node Controller**             | Syncs Kubernetes nodes with Calico node resources |
| **Policy Controller**           | Syncs Kubernetes NetworkPolicy with Calico policy |
| **Namespace Controller**        | Syncs namespace labels for profile management     |
| **ServiceAccount Controller**   | Projects service-account labels into Calico profiles; does not grant Kubernetes RBAC             |
| **WorkloadEndpoint Controller** | Updates workload endpoint metadata such as Pod labels on the applicable datastore path                |

### Controller Reconciliation Loop

![Sequence diagram showing kube-controllers repeatedly listing Kubernetes and Calico resources, diffing them, and either writing changes to the Calico datastore or taking no action when the two are already in sync.](../../.gitbook/assets/en-networking-calico-02-architecture-8.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-8.html)

This is a logical desired-versus-observed reconciliation sketch, not a trace proving two remote LIST calls every interval. Real controllers use watches/caches, and their enabled roles depend on the datastore and installation.

### kube-controllers Configuration

For the operator installation, configure the real [KubeControllersConfiguration API](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig). An arbitrary ConfigMap named `calico-kube-controllers-config` is not consumed by the Deployment shown in this guide.

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type merge \
  -p '{"spec":{"logSeverityScreen":"Info","healthChecks":"Enabled","prometheusMetricsPort":9094}}'
```

This merge patch preserves the existing `controllers` configuration. If GitOps manages the resource, make the equivalent change in its desired state instead. A replacement manifest with empty controller objects can alter existing reconciliation or allocation settings.

Operator 1.42.6 selects `ENABLED_CONTROLLERS=node,loadbalancer` for its standard Open Source deployment. The broader list above describes available controller roles, not five controllers necessarily running with every datastore. Its [renderer](https://github.com/tigera/operator/blob/v1.42.6/pkg/render/kubecontrollers/kube-controllers.go) specifies one replica and a `Recreate` strategy; the previous leader-election claim was not supported by that configuration. Keep this workload under the installation owner rather than replacing or manually scaling it.

## Datastore Options

The operator examples here use the Kubernetes API datastore. Calico state can involve Calico CRDs and native Kubernetes objects; not every logical Calico resource is a separate CRD. The usual aggregated API server exposes `projectcalico.org/v3` over the internal representation. Native v3 CRDs are a separate Calico 3.32 tech preview and have their own migration procedure.

Typha distributes read/watch updates; it is not a general write proxy for Felix. Components that update status or resources use their own datastore access. Kubernetes persists its API state in its backing store, but Calico users do not need a separate Calico etcd cluster for this mode.

Direct etcdv3 access is a different installation choice with explicit support and feature constraints. Do not infer that it is faster, unlimited, or required above 5,000 nodes. The eBPF data plane requires the Kubernetes datastore. A direct-etcd deployment also needs its own TLS trust, credentials, availability and consistent backup/restore design.

| Concern | Kubernetes API datastore | Direct etcdv3 |
|---|---|---|
| Access control | Kubernetes authentication/RBAC plus the appropriate Calico API path | etcd authentication/TLS and access controls |
| Operations | Reuse the cluster API; follow provider-specific backup procedures | Operate and back up the selected etcd deployment |
| Host/VM support | Check the specific installation and edition | Check the specific installation and edition |
| Selection | Used by this operator guide | A separately validated design, not a node-count shortcut |

On managed Kubernetes, “Kubernetes backup” does not mean users can take direct control-plane etcd snapshots. Back up supported resources using the platform's procedure.

## Component Interaction Sequence

Kubelet requests sandbox creation through the container runtime, which invokes CNI/IPAM. Endpoint and policy data reaches Felix through the selected datastore/watch path. In BGP mode, confd and BIRD handle routing configuration separately. These components converge asynchronously; verify actual connectivity and enforcement.

## Packet Flow Analysis

### Ingress Packet Flow (Pod-to-Pod, Same Node)

![Diagram showing a packet crossing from one pod to another on the same node through their veth interfaces and the host's iptables/eBPF policy check.](../../.gitbook/assets/en-networking-calico-02-architecture-12.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-12.html)

The policy box summarizes the applicable source-egress and destination-ingress kernel checks. The veth interfaces belong to the two Pods' network paths; packets are not sent through the Felix process.

### Egress Packet Flow (Pod-to-Pod, Different Nodes with IPIP)

![Sequence diagram showing a packet from Pod A passing the Felix/iptables egress policy check on Node 1, reaching Node 2 either IPIP/VXLAN-encapsulated or forwarded directly via a BGP route, then passing the ingress policy check and reaching Pod B.](../../.gitbook/assets/en-networking-calico-02-architecture-13.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-02-architecture-13.html)

Read the two paths as alternatives. “Felix/iptables” means kernel rules programmed by Felix, not daemon packet forwarding. BIRD supplies routing control information in BGP mode; it does not carry application packets.

### Packet Structure Comparison

```
Original Pod-to-Pod Packet:
┌─────────────────────────────────────────────────────────────┐
│ Ethernet │   IP Header    │   TCP/UDP   │     Payload      │
│  Header  │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 192.168.2.10 │             │                  │
└─────────────────────────────────────────────────────────────┘

IPIP Encapsulated Packet:
┌───────────────────────────────────────────────────────────────────────────────┐
│ Ethernet │   Outer IP     │   Inner IP     │   TCP/UDP   │     Payload      │
│  Header  │ Src: 10.0.1.10 │ Src: 192.168.1.10 │   Header    │                  │
│          │ Dst: 10.0.1.11 │ Dst: 192.168.2.10 │             │                  │
│          │ Proto: 4 (IPIP)│                │             │                  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Summary

Calico's architecture is designed for scalability, performance, and operational simplicity:

1. **Felix**: The workhorse agent on every node, programming routes and ACLs
2. **BIRD**: Distributes routes via BGP, enabling native routing integration
3. **confd**: Bridges the datastore to BIRD configuration
4. **Typha**: Scales the system by reducing API server load
5. **kube-controllers**: Keeps Kubernetes and Calico in sync
6. **Datastore**: Kubernetes API (recommended) or etcd for configuration storage

Understanding these components and their interactions is essential for:

* Troubleshooting connectivity issues
* Optimizing performance at scale
* Planning capacity and architecture
* Integrating with existing network infrastructure

[Previous: Part 1 - Introduction to Calico](01-introduction.md)

[Next: Part 3 - Networking Modes](03-networking-modes.md)

[Return to Calico Overview](./README.md)

## Quiz

To test what you've learned in this chapter, try the [Architecture Quiz](../../quizzes/networking/calico/02-architecture-quiz.md).
