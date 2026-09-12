# Part 1: Introduction to Calico

> **Review baseline**: Calico Open Source 3.32.2, kind 0.33.0, Kubernetes 1.36.4
> **Reviewed**: September 12, 2026. Calico 3.32 is tested against Kubernetes 1.34–1.36.

## Lab environment

This disposable local lab selects iptables, VXLAN and Calico IPAM explicitly. It does not replace an existing CNI or configure EKS. The audit checked published artifacts and configuration without creating the cluster or testing live traffic.

| Tool/environment | Requirement |
|---|---|
| kind | 0.33.0; pin the 1.36.4 image below instead of accepting an unpinned default |
| Docker | A supported working runtime with capacity for three kind nodes |
| Node OS | Linux kernel/modules meeting [Calico requirements](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements); on macOS this is the container VM's kernel |
| kubectl | Within one minor of API server 1.36; a matching 1.36 client is convenient |
| calicoctl | Optional matching 3.32.2 client for the actual CLI host OS/architecture |
| curl / Python 3 | Optional client download and SHA-256 verification below |
| Helm | Optional alternative in the [overview](README.md), not needed for this lab |

The [Kubernetes skew policy](https://kubernetes.io/releases/version-skew-policy/) does not support an arbitrary `kubectl 1.28+` with every later server. Check Pod/Service CIDRs against your container network, host LAN and VPN before creating the lab.

### Optional: a matching calicoctl

Choose one platform, verify the exact release asset's published digest and keep the binary in the lab directory. These commands do not require global installation or home-directory configuration.

```bash
set -euo pipefail
CALICO_VERSION=v3.32.2
case "$(uname -s)" in
  Linux) CALICO_OS=linux ;;
  Darwin) CALICO_OS=darwin ;;
  *) echo "Select a supported calicoctl OS" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64|amd64) CALICO_ARCH=amd64 ;;
  aarch64|arm64) CALICO_ARCH=arm64 ;;
  *) echo "Select a supported calicoctl architecture" >&2; exit 1 ;;
esac
CALICO_ASSET="calicoctl-$CALICO_OS-$CALICO_ARCH"
curl --fail --location --retry 3 \
  "https://api.github.com/repos/projectcalico/calico/releases/tags/$CALICO_VERSION" \
  --output calico-release.json
curl --fail --location --retry 3 \
  "https://github.com/projectcalico/calico/releases/download/$CALICO_VERSION/$CALICO_ASSET" \
  --output calicoctl
python3 - "$CALICO_ASSET" <<'PY'
import hashlib
import json
import pathlib
import sys

release = json.loads(pathlib.Path("calico-release.json").read_text())
if release["tag_name"] != "v3.32.2":
    raise SystemExit("Unexpected release")
asset = next(a for a in release["assets"] if a["name"] == sys.argv[1])
expected = asset.get("digest") or ""
actual = "sha256:" + hashlib.sha256(pathlib.Path("calicoctl").read_bytes()).hexdigest()
if not expected.startswith("sha256:") or actual != expected:
    raise SystemExit("Digest mismatch or missing published digest")
print("Verified", asset["name"], actual)
PY
chmod +x calicoctl
./calicoctl --help
```

Run `./calicoctl version` after configuring the lab datastore to see client and cluster information. The documented `version` command has no `--client` flag. Once the aggregated API server is ready, `kubectl` can also manage Calico resources; calicoctl is not mandatory for every operation.

### Create a separate kind cluster

Use an unused cluster name and a new local kubeconfig. The [kind 0.33.0 release](https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0) publishes this 1.36.4 image within Calico's tested minor range. The registry digest and amd64/arm64 manifest were checked; node-image layers were not downloaded during the audit.

```bash
set -euo pipefail
CALICO_LAB_KUBECONFIG="$PWD/calico-lab.kubeconfig"
test ! -e "$CALICO_LAB_KUBECONFIG"
cat > kind-calico.yaml <<'YAML'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  disableDefaultCNI: true
  kubeProxyMode: iptables
  podSubnet: 10.244.0.0/16
nodes:
  - role: control-plane
  - role: worker
  - role: worker
YAML
kind create cluster --name calico-lab --config kind-calico.yaml \
  --kubeconfig "$CALICO_LAB_KUBECONFIG" \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed
export KUBECONFIG="$CALICO_LAB_KUBECONFIG"
export DATASTORE_TYPE=kubernetes
kubectl config current-context
kubectl cluster-info
```

Nodes and ordinary Pods may remain unready until the CNI is installed. Do not install a second CNI to clear that condition. If the Pod CIDR conflicts, change it in both kind and the Installation before creating the cluster.

```bash
CALICO_VERSION=v3.32.2
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/v1_crd_projectcalico_org.yaml"
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/tigera-operator.yaml"
kubectl -n tigera-operator rollout status deployment/tigera-operator --timeout=300s
kubectl apply -f - <<'YAML'
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: Kind
  cni:
    type: Calico
  calicoNetwork:
    linuxDataplane: Iptables
    bgp: Disabled
    ipPools:
      - cidr: 10.244.0.0/16
        blockSize: 26
        encapsulation: VXLAN
        natOutgoing: Enabled
        nodeSelector: all()
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
YAML
kubectl get tigerastatus
kubectl -n calico-system get pods -o wide
```

Wait for the operator-created workloads to appear, then check their rollouts and conditions. An empty label selection or one controller's availability does not establish that all node networking works.

```bash
kubectl -n calico-system rollout status daemonset/calico-node --timeout=300s
kubectl -n calico-system rollout status deployment/calico-kube-controllers --timeout=300s
kubectl wait --for=condition=Available apiservice/v3.projectcalico.org --timeout=300s
kubectl wait --for=condition=Ready nodes --all --timeout=300s
kubectl get ippools.projectcalico.org -o wide
kubectl get installations.operator.tigera.io default -o yaml
# Optional, if the matching local client was downloaded:
./calicoctl version
./calicoctl get nodes
```

BGP is disabled here, so BIRD sessions and `calicoctl node status` are not readiness criteria. That command also needs the appropriate node environment rather than only a laptop kubeconfig. Observe actual component counts; CSI/Typha replicas are not fixed. Use disposable workloads to check Pod, Service and DNS connectivity and both permitted and denied policy flows.

## What Calico provides

Calico combines Kubernetes networking, IPAM and policy enforcement. In policy-only integrations, another CNI retains networking and IPAM. Features vary by operating system, data plane and product edition; a platform listing does not promise identical behavior.

## Project history and governance

Project Calico began at Metaswitch in 2014; Tigera was established in 2016 and is its primary maintainer. The release records below correct the earlier 3.0/3.29 dates and distinguish the original eBPF preview from later feature availability.

| Date | Primary release record |
|---|---|
| December 21, 2017 | [Calico 3.0.0](https://github.com/projectcalico/calico/releases/tag/v3.0.0), a historical release, not an installation recommendation |
| February 25, 2020 | [eBPF introduction](https://www.tigera.io/blog/introducing-the-calico-ebpf-dataplane/): announced as a **3.13 tech preview**, not GA |
| October 29, 2024 | [Calico 3.29.0](https://github.com/projectcalico/calico/releases/tag/v3.29.0) |
| August 30, 2026 | [Calico 3.32.2](https://github.com/projectcalico/calico/releases/tag/v3.32.2), this review's baseline |

The old timeline's “full eBPF parity” and “Windows eBPF” claims were incorrect. Current [Windows limitations](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations) still exclude Linux eBPF, IPIP, IPv6/dual stack and WireGuard.

Calico uses Apache-2.0 licensing with Tigera and community maintenance. A CNCF Landscape listing is not CNCF ownership, incubation or graduation. Enterprise is a commercial self-managed product; Cloud is a SaaS offering. Open Source is not restricted to small or non-production clusters.

![Calico ecosystem and commercial product relationships.](../../.gitbook/assets/en-networking-calico-01-introduction-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-01-introduction-4.html)

The CNCF box represents Landscape/ecosystem participation only. Tigera maintains the open-source project as well as its products; the figure's grouping does not confer governance authority on CNCF.

## Core capabilities

### 1. Networking and data planes

Encapsulation and implementation are separate choices. Calico can use IPIP, VXLAN or a routed underlay. CrossSubnet is a conditional IPIP/VXLAN setting, not a WAN connection service. Linux data planes include iptables, nftables and eBPF. eBPF runs **inside the kernel** and can bypass parts of its conventional packet-processing path; it does not bypass the kernel. Unencapsulated routing avoids tunnel headers only when the underlay has the required Pod routes, without guaranteeing the lowest latency for every workload.

### 2. Kubernetes and Calico policy

Kubernetes NetworkPolicy is namespaced and additive. Calico adds explicit actions, ordered policies and tiers, including tiers in Open Source. GlobalNetworkPolicy has cluster resource scope but can select one namespace. HostEndpoint describes a host endpoint to protect; it is not a third policy type below NetworkPolicy in a fixed hierarchy.

These are **independent examples** in a dedicated namespace. Consider existing tiers and higher-priority policies; neither is a complete security baseline.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: calico-demo
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress: []
```

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: calico-demo-trusted-ingress
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'backend'
  order: 100
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
        selector: trusted == 'true'
      destination:
        ports: [8080]
    - action: Deny
```

The Calico example allows TCP 8080 to selected backends from matching demo-namespace endpoints, then denies other ingress. Protect label-writing permissions: `trusted` is not cryptographic identity. These examples do not configure egress or DNS. CIDR/port rules are supported, but a large private CIDR is not an identity boundary. DNS/FQDN and application-layer policy require the appropriate Enterprise/Cloud features; see the [edition matrix](https://docs.tigera.io/calico/latest/about/calico-product-editions).

### 3. IP address management

When Calico owns IPAM, pools and blocks control allocation. An IPv4 /26 block contains 64 addresses, not 64 guaranteed usable Pod addresses on every platform; Windows reserves addresses and IPv6 has different defaults. In VPC CNI policy-only mode, AWS owns IPAM.

This illustrates the [IPPool API](https://docs.tigera.io/calico/latest/reference/resources/ippool). **Do not create it beside an overlapping operator-managed pool.** The kind lab already has its pool; encapsulation/IPAM changes are separate planned exercises.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: example-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

Multiple non-overlapping pools and node selectors can separate allocations. `natOutgoing` normally applies to traffic leaving Calico pools; it is not a firewall or encryption setting. Neither direct routing nor CrossSubnet connects separate sites without an underlay design.

### 4. BGP routing

BGP distributes routes; application packets do not flow through the BIRD process, and BGP does not encrypt them. BGP can support direct routing or coexist with IPIP. Full mesh, route reflectors and external peers are topology choices.

The following belongs to a **separate routed lab**, not the BGP-disabled kind example. Replace the documentation address, ASNs and node labels with a designed topology and matching router configuration. Do not disable the node mesh before replacement route distribution works.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  logSeverityScreen: Info
  nodeToNodeMeshEnabled: true
  asNumber: 64512
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: example-rack-tor
spec:
  peerIP: 192.0.2.1
  asNumber: 64513
  nodeSelector: rack == 'rack-1'
```

BGPPeer supports `password.secretKeyRef` for session authentication. The Secret belongs in the Calico node component's namespace and the router must use matching credentials; this does not encrypt workload traffic. Service-CIDR advertisement and mesh removal require additional testing; see [BGP deep dive](04-bgp-deep-dive.md).

### 5. Platform and scale boundaries

| Environment | Boundary |
|---|---|
| EKS | VPC CNI + Calico policy is one integration; full Calico CNI is a separate new-cluster design |
| AKS | Check the provider's supported CNI/policy combination and current installation procedure |
| GKE | Dataplane V2 uses **Cilium**; Calico applies to the relevant legacy configuration, not an installation over V2 |
| Self-managed Kubernetes | Check distribution, kernel, CNI ownership, routes and privileges |
| Windows | Specified IPv4 configurations; no Linux eBPF, IPIP, IPv6/dual-stack or WireGuard parity |
| Hosts / VMs | Separate installation and feature requirements; KubeVirt/Enterprise status differs from basic host protection |

[GKE's documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/dataplane-v2) explicitly distinguishes Cilium in V2 from the legacy Calico path.

Typha caches and distributes updates through a separate set of Pods, reducing direct Felix datastore watches. Three replicas are an example, not a universal minimum. Capacity depends on policies, endpoints, Service churn, hardware, datastore and data plane. This introduction has no reproducible evidence for a fixed “5,000 nodes / 100,000 Pods / millions of rules” limit.

## Calico, kube-proxy and performance

kube-proxy implements Service forwarding, not CNI networking or NetworkPolicy. Calico's standard data planes can work alongside it, as in this lab; the eBPF data plane can replace Service handling when configured.

| Concern | Compare |
|---|---|
| Pod networking/IPAM | CNI/IPAM implementations with the same topology |
| Service forwarding | Selected kube-proxy backend or an eBPF replacement |
| Policy | Equivalent rules and enforcement coverage |
| Scale | Services/endpoints, selectors, churn and connection reuse |
| CPU/memory/latency | Hardware, kernel, versions, workload, warm-up, repeats and errors |

kube-proxy is not iptables-only: current Kubernetes also offers nftables and version-dependent legacy backends. An IP-set lookup does not make the entire Calico packet path O(1). Initial iptables Service NAT selection also differs from later packets' conntrack fast path. The earlier unsourced 1,000-node/50,000-Pod rule-count, latency and memory example was not a reproducible benchmark and should not be used for sizing.

Traditional VM networks can also be automated and distributed. Calico's declarative policy does not imply unlimited IP capacity or guaranteed second-level convergence.

## Deployment scenarios

- **On-premises**: coordinate Pod routes, BGP peers/filters, return paths and host protection. Disabling encapsulation alone does not create underlay routes.
- **EKS**: to retain AWS networking, select `cni.type: AmazonVPC` and follow the [reviewed overview](README.md), including policy-engine ownership and Pod-IP annotations. Do not apply an EKS Installation to this Kind lab or run two policy engines.
- **Hybrid/multi-cluster**: connectivity, discovery and policy administration are separate functions. A CrossSubnet IPPool does not establish VPNs, shared identity or cross-cluster discovery. Evaluate the appropriate cluster-mesh/multi-cluster product features and underlay separately; “Calico Federation” is not a universal built-in link.
- **Regulated workloads**: Enterprise/Cloud can add reports, logs and security features; installing them does not establish compliance. API audit logs record API changes and flow logs record network observations, not automatically every enforcement decision. WireGuard is also available in supported Open Source Linux configurations.

## Community and source development

Use the [community page](https://www.tigera.io/project-calico/community/) for current Slack/meeting links, the [issue tracker](https://github.com/projectcalico/calico/issues) for reproducible reports, and the [contributor guide](https://github.com/projectcalico/calico/blob/v3.32.2/CONTRIBUTING.md). Do not assume an undated biweekly schedule or old forum URL is current.

For source study, the [developer guide](https://github.com/projectcalico/calico/blob/v3.32.2/DEVELOPER_GUIDE.md) describes a Linux/Docker/git/make environment and component-specific tests. There is no root `make dev-environment` target. This optional source workflow is separate from the networking lab and was not executed during the audit:

```bash
git clone --depth 1 --branch v3.32.2 https://github.com/projectcalico/calico.git calico-source-study
cd calico-source-study
# Read prerequisites and the selected component's Makefile before running tests.
cat DEVELOPER_GUIDE.md
make -C calicoctl test
```

Open Source provides community-supported networking and policy for production as well as labs. Enterprise adds commercial capabilities/support; Cloud delivers SaaS management. Select by the [feature matrix](https://docs.tigera.io/calico/latest/about/calico-product-editions), not a blanket “small versus large cluster” rule.

## Clean up the disposable lab

After saving results, remove only the `calico-lab` cluster created for this exercise with `kind delete cluster --name calico-lab`. Keep any unrelated clusters and kubeconfigs. This local cleanup is not an EKS deletion procedure.

[Next: Calico architecture](02-architecture.md) · [Calico overview](README.md) · [Introduction quiz](../../quizzes/networking/calico/01-introduction-quiz.md)
