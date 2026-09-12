# Part 1: Introduction

> **Reviewed baseline**: Cilium 1.20.1 / Cilium CLI 0.20.0 / Hubble CLI 1.19.4. **Last Updated**: September 12, 2026

## Lab Environment Setup

Use an isolated, prepared Kubernetes environment. Cilium 1.20 lists Kubernetes **1.33–1.36** as tested. Nodes require AMD64/AArch64 Linux with kernel **5.10+**, or the documented equivalent such as RHEL 8.10's backported 4.18 kernel. A kind/minikube VM or container uses its node/VM kernel; the workstation's OS name alone does not establish compatibility. Feature-specific requirements still apply.

Use kubectl within one minor version of the API server. Install the correct OS/architecture Cilium CLI and Hubble CLI assets with checksum verification as described in [the main guide](README.md). Helm can render/review configuration; the audit used Helm 3.21.3. Do not repeat unchecked `latest` AMD64 downloads or reinstall the release in every chapter.

### Install Once with the Selected Profile

EKS ENI, VPC CNI chaining and ordinary cluster-pool configurations have different prerequisites; see [the main guide](README.md). The following lab values are the **ordinary IPv4 cluster-pool alternative**, with kube-proxy and DNS already working and one prepared CNI owner. They are not an EKS migration recipe. Verify that the Pod CIDR does not overlap Service, node or connected-network ranges.

Save as `cilium-lab-values.yaml`:

```yaml
routingMode: tunnel
tunnelProtocol: vxlan
kubeProxyReplacement: false
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - icmp
    - httpV2
```

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
kubectl --context "$CILIUM_LAB_CONTEXT" get nodes -o wide
cilium version --client

# Fresh installation only, after preparing the cluster/CNI ownership and values.
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.1 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

If Cilium is already installed, inspect its version/configuration and follow its owner’s upgrade process. Installation/status commands and the later connectivity tests are not evidence of production compatibility; no cluster was provisioned for this audit.

## What is Cilium?

Cilium provides networking, security and observability through a Linux eBPF dataplane and Kubernetes integration. It offers endpoint policy, mode-dependent IPAM/routing, Service handling and Hubble flow visibility. The Docker libnetwork integration was removed in 1.20; Kubernetes, Docker and Mesos should not be presented as interchangeable current installation targets.

### Core Components and Capabilities

| Component / feature | Role and qualification |
| --- | --- |
| Cilium Agent | Per-node endpoint and dataplane management; it does not own every host/networking function |
| Cilium Operator | Cluster-level allocation/identity/controller work; multiple replicas are supported, with leader election where applicable. The reviewed chart defaults to two replicas |
| eBPF | Programs/maps at kernel hooks, subject to verification and feature requirements; performance must be measured |
| L3/L4 and L7 policy | L7 needs the supported Envoy/DNS proxy path; Kafka-aware L7 policy was removed in 1.20, while L4 rules can still govern Kafka connections |
| kube-proxy replacement | Optional Service handling; DSR, Maglev and XDP have their own configuration/topology constraints |
| Encryption | Transparent IPsec/WireGuard modes; separate beta ztunnel workload mTLS is not the same setting |
| Hubble | Network/proxy flow observations and service maps, not automatic end-to-end application tracing |
| ClusterMesh / BGP | ClusterMesh needs identity, trust and network reachability; BGP advertises routes but does not program internal cluster routing |

The component relationship is: kubelet requests Pod sandbox operations through **CRI**; the container runtime invokes the configured **CNI plugin**; Cilium coordinates endpoint setup and the agent programs the dataplane. CNI is not a per-packet forwarding hop. Envoy handles configured L7 proxy traffic, and Hubble exposes flow events separately from Prometheus metric scraping.

### Security Identity

A security identity is an allocated numeric identifier for an endpoint's **security-relevant label set**, within the relevant allocation scope. These labels are filtered/configured and can include namespace-derived labels. Same `app` labels alone do not guarantee the same identity across namespaces or clusters. The numeric ID is not a permanent globally meaningful hash or a Pod IP. Other endpoint types also use identities.

## Container Networking Basics

Host networking shares the host network namespace. A bridge connects interfaces on a host; an overlay encapsulates traffic across an underlay. Native routing relies on the underlay reaching Pod addresses. These concepts can coexist and should not be confused with choosing an eBPF versus Netfilter implementation.

Operational questions include address capacity, routing/MTU, Service behavior, tenant policy, observability and failure recovery. A network model alone does not determine performance or security.

## Understanding CNI

CNI is the CNCF specification/library/plugin ecosystem for container network configuration. Plugins exchange configuration/results in JSON, and can delegate address allocation to an IPAM plugin. CNI's setup/removal contract is distinct from CRI, which kubelet uses to communicate with the container runtime. Since Kubernetes 1.24, kubelet no longer owns the removed `--network-plugin`/`--cni-bin-dir` configuration flags.

| Project | Relevant distinction |
| --- | --- |
| Cilium | Linux eBPF dataplane, several routing/IPAM modes, proxy-assisted L7 policy and Hubble |
| Calico | Linux Iptables/Nftables/BPF and supported Windows HNS; OSS WireGuard, staged policy and separately configured L7 integration |
| Flannel | Connectivity backends such as VXLAN/host-gw/WireGuard; policy can be supplied by its optional chart controller or another implementation |
| AWS VPC CNI | VPC address allocation/networking; native policy on supported EC2 Linux nodes and separate SG-for-Pods controls |
| Weave Net | The original `weaveworks/weave` repository is archived; treat it as a historical option and check any proposed maintained distribution separately |

See [the current comparison](README.md) for support boundaries. Do not use unbounded Kubernetes compatibility or “very high/high/medium” performance rankings as deployment evidence. Service meshes are optional integrations, not a prerequisite for ordinary Pod networking.

## Lab: A Scoped L4 Policy

Use the chosen context and a dedicated namespace. This example defines policy; it does **not** deploy an application server or client images. Prepare controller-managed test workloads with approved images/tools:

- A backend Pod labeled `app=backend`, listening on TCP 8080.
- A frontend Pod labeled `app=frontend` and another client with a different label, both with a suitable test client.
- Ordinary managed Pod interfaces, default label handling, known DNS/Service configuration and no other matching allow policies that invalidate the intended isolation.

Save the namespace definition as `cilium-intro-namespace.yaml`, apply it, then prepare the test workloads:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cilium-intro-demo
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-namespace.yaml
```

Save the policy below as `cilium-intro-policy.yaml`:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: cilium-intro-demo
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: cilium-intro-demo
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

```bash
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n cilium-intro-demo --show-labels
kubectl --context "$CILIUM_LAB_CONTEXT" apply -f cilium-intro-policy.yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n cilium-intro-demo
```

With those prerequisites and no additional matching allow, expected **regular Pod-to-Pod ingress** results are:

| Source / destination | Expected result |
| --- | --- |
| Same-namespace frontend → backend TCP 8080 | Allowed |
| Other client label → backend TCP 8080 | Denied |
| Frontend → backend another port/protocol | Not allowed by this policy |
| Same app label from another namespace | Not allowed by this policy |

Verify both positive and negative connections after policy realization. Other allow/deny policies, host traffic and probes can change the effective result. This ingress rule does not restrict frontend egress or provide HTTP method/path filtering. Inspect actual traffic and endpoint state rather than assuming API acceptance equals enforcement.

`cilium connectivity test` is an additional test runner that creates workloads and policies. Run it only in a reviewed test environment with the needed permissions; it is not a read-only status command. Use `cilium connectivity perf` for the separate performance runner and preserve actual version/topology/results when benchmarking.

## References and Next Steps

- [Cilium requirements and setup](README.md)
- [CNI project](https://github.com/containernetworking/cni)
- [Kubernetes network plugins and runtime ownership](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes client version skew](https://kubernetes.io/releases/version-skew-policy/)
- [Cilium identities and terminology](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/gettingstarted/terminology.rst)
- [Original Weave repository metadata](https://api.github.com/repos/weaveworks/weave)

Continue to [eBPF](02-ebpf.md) or test your understanding with the [Introduction Quiz](../../quizzes/networking/cilium/01-introduction-quiz.md).
