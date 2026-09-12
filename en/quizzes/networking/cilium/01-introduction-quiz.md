# Cilium Introduction and Basic Concepts Quiz

> **Baseline**: Cilium 1.20.1 / CLI 0.20.0. **Last Updated**: September 12, 2026

## Multiple Choice Questions

1. Which technology provides Cilium’s programmable kernel datapath?
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>
<summary>Show Answer</summary>

**Answer: B) eBPF**

**Explanation:**
Cilium loads verified eBPF programs at supported kernel hooks. This enables networking and observability features, but does not guarantee higher performance than every alternative; measure the selected workload and configuration.

</details>

2. What policy layers can Cilium support with the required integrations?
   - A) Only L3
   - B) Only L3–L4
   - C) L3/L4 and supported L7 protocols
   - D) Only L2–L3

<details>
<summary>Show Answer</summary>

**Answer: C) L3/L4 and supported L7 protocols**

**Explanation:**
HTTP and DNS policy use supported proxy paths; encrypted HTTP needs the appropriate termination/integration. Kafka-aware L7 rules were removed in 1.20. L4 policy can still control Kafka connections.

</details>

3. Which Cilium component provides network flow visibility?
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>
<summary>Show Answer</summary>

**Answer: B) Hubble**

**Explanation:**
Hubble observes network/proxy flows and can display service relationships. HTTP visibility depends on the proxy path. It does not automatically create complete application traces; Prometheus metrics and distributed tracing serve different purposes.

</details>

4. Which Kubernetes Service component can Cilium replace in a supported configuration?
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>
<summary>Show Answer</summary>

**Answer: B) kube-proxy**

**Explanation:**
kubeProxyReplacement requests Cilium’s Service handling. API/bootstrap access and migration prerequisites still matter, and DSR/Maglev/XDP are separate choices rather than automatic guarantees of better performance.

</details>

5. Which pair names Cilium’s transparent network encryption modes?
   - A) IPsec and WireGuard
   - B) TLS and SSH
   - C) GRE and HTTP
   - D) DNS and VXLAN

<details>
<summary>Show Answer</summary>

**Answer: A) IPsec and WireGuard**

**Explanation:**
The encryption.type choices are IPsec and WireGuard with mode/platform prerequisites. Separate beta ztunnel workload mTLS is not the same setting; saying that Cilium never uses TLS would be incorrect.

</details>

6. What is Cilium’s multi-cluster connectivity feature called?
   - A) Cluster Federation
   - B) ClusterMesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>
<summary>Show Answer</summary>

**Answer: B) ClusterMesh**

**Explanation:**
ClusterMesh connects compatible clusters with configured identities, trust and network reachability. It does not create the entire underlay or automatically make all services globally reachable.

</details>

7. Which technology can Cilium use for optional early packet/load-balancing acceleration?
   - A) DPDK
   - B) XDP
   - C) RDMA
   - D) SR-IOV

<details>
<summary>Show Answer</summary>

**Answer: B) XDP**

**Explanation:**
XDP can process selected traffic early at a supported hook/driver. It is not used by every Cilium packet path, and neither a packets-per-second guarantee nor complete DDoS protection follows from enabling it.

</details>

8. What is the standard upstream Linux kernel baseline for Cilium 1.20, excluding documented vendor-backport equivalents?
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>
<summary>Show Answer</summary>

**Answer: D) 5.10**

**Explanation:**
The current requirements state Linux 5.10+, with named equivalents such as RHEL 8.10’s backported 4.18. Individual features can need newer kernels. Check the node/VM kernel, not only the workstation OS.

</details>

9. Which option provides VXLAN/host-gw connectivity without requiring Cilium’s eBPF dataplane?
   - A) Cilium native routing
   - B) Calico BPF mode
   - C) Flannel VXLAN/host-gw
   - D) Cilium netkit mode

<details>
<summary>Show Answer</summary>

**Answer: C) Flannel VXLAN/host-gw**

**Explanation:**
Flannel connectivity backends are a different implementation. Its optional policy controller or another policy integration must be evaluated separately; avoid universal resource/performance rankings.

</details>

10. What is the API version of CiliumNetworkPolicy?
   - A) networking.k8s.io/v1
   - B) cilium.io/v1
   - C) cilium.io/v2
   - D) policy.cilium.io/v1

<details>
<summary>Show Answer</summary>

**Answer: C) cilium.io/v2**

**Explanation:**
CiliumNetworkPolicy is a separate CRD/API from standard Kubernetes NetworkPolicy. Feature availability still depends on the Cilium version and dataplane/proxy configuration.

</details>

## Short Answer Questions

11. Which component runs per node and programs endpoints and eBPF policy?

<details>
<summary>Show Answer</summary>

**Answer: Cilium Agent**

**Explanation:**
The agent performs node-local work. The container runtime/CNI plugin, operator, proxy and host OS have other responsibilities; the agent does not own every networking operation.

</details>

12. Which component coordinates cluster-level allocation/controller work?

<details>
<summary>Show Answer</summary>

**Answer: Cilium Operator**

**Explanation:**
The operator can run multiple replicas; the reviewed chart defaults to two, with leader election for applicable work. Responsibilities depend on IPAM/identity mode. It is not inherently a single instance or the sole owner of every ClusterMesh connection.

</details>

13. Which CLI command runs Cilium’s connectivity test workloads?

<details>
<summary>Show Answer</summary>

**Answer: cilium connectivity test**

**Explanation:**
It creates workloads/policies and needs an approved test environment and permissions. For read-only inspection start with cilium status, endpoint diagnostics and Hubble. The management command cilium monitor is not the current agent diagnostic interface.

</details>

14. What is the numeric identifier associated with an endpoint’s security-relevant labels?

<details>
<summary>Show Answer</summary>

**Answer: Security identity (Cilium identity)**

**Explanation:**
Only the relevant/selected label set determines the identity in its allocation scope. Namespace-derived labels can differ; same app labels alone do not establish identity equality. The numeric ID is allocated rather than a permanent globally meaningful hash.

</details>

15. What specification defines the container network plugin interface?

<details>
<summary>Show Answer</summary>

**Answer: CNI (Container Network Interface)**

**Explanation:**
Kubelet communicates with the runtime through CRI, and the runtime invokes CNI. CNI exchanges network configuration/results and handles setup/removal; kubelet’s former CNI configuration flags were removed in Kubernetes 1.24.

</details>

## Hands-on Questions

16. Using the installed CLI, show a fresh Cilium 1.20.1 installation with the prepared lab values and explicit context.

<details>
<summary>Show Answer</summary>

**Answer:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium version --client
cilium install --context "$CILIUM_LAB_CONTEXT" --version 1.20.1 \
  --values cilium-lab-values.yaml
cilium status --context "$CILIUM_LAB_CONTEXT" --wait
```

**Explanation:**
Use the guide’s prevalidated environment/CNI ownership, CIDR and values prerequisites. Skip installation for an existing release and use its owner’s upgrade process. Status is not a substitute for positive/negative traffic tests.

</details>

17. Write the lab policy permitting frontend Pod ingress to backend TCP 8080 within cilium-intro-demo.

<details>
<summary>Show Answer</summary>

**Answer:**

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

**Explanation:**
The namespace and workloads must already exist. The explicit peer namespace avoids granting other namespaces the same label-based access. Other allow/deny policies and host traffic affect the result; this rule is not HTTP filtering or an egress restriction.

</details>

18. Show a partial values example requesting kube-proxy replacement and native-routing DSR with Geneve dispatch. What remains to be prepared?

<details>
<summary>Show Answer</summary>

**Answer:**

```yaml
kubeProxyReplacement: true
k8sServiceHost: api.lab.example.internal
k8sServicePort: 443
routingMode: native
tunnelProtocol: geneve
ipv4NativeRoutingCIDR: 10.244.0.0/16
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

**Explanation:**
This is a separate native profile, not an instruction to turn DSR on in the VXLAN lab. Replace the API host/port and native-routing CIDR with the actual prepared values. Ensure API/bootstrap DNS access, underlay Pod routes, Geneve/MTU and return/source-address paths, then follow the supported kube-proxy migration procedure. Static values do not guarantee cloud-load-balancer compatibility or eliminate every bottleneck.

</details>

19. Show cluster status, the selected backend endpoint’s local status, and desired policy resources.

<details>
<summary>Show Answer</summary>

**Answer:**

```bash
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
CILIUM_LAB_NS=cilium-intro-demo
BACKEND_POD=replace-with-actual-backend-pod
cilium status --context "$CILIUM_LAB_CONTEXT" --verbose
kubectl --context "$CILIUM_LAB_CONTEXT" get pod "$BACKEND_POD" -n "$CILIUM_LAB_NS" -o wide
kubectl --context "$CILIUM_LAB_CONTEXT" get pods -n kube-system -l k8s-app=cilium -o wide

# Choose the agent on the backend Pod's node.
CILIUM_AGENT_POD=replace-with-agent-pod-on-that-node
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint list
kubectl --context "$CILIUM_LAB_CONTEXT" exec -n kube-system "$CILIUM_AGENT_POD" \
  -c cilium-agent -- cilium-dbg endpoint get "pod-name:$CILIUM_LAB_NS:$BACKEND_POD"
kubectl --context "$CILIUM_LAB_CONTEXT" get networkpolicy -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get cnp -n "$CILIUM_LAB_NS" -o yaml
kubectl --context "$CILIUM_LAB_CONTEXT" get ccnp -o yaml
```

**Explanation:**
Endpoint identifiers and realized state belong to the selected agent/node; use the Pod identifier supported by cilium-dbg. kubectl reads desired policy resources, not proof of enforcement. cilium-dbg policy get is deprecated, and management cilium endpoint/policy/monitor commands are not equivalent.

</details>

20. Enable Hubble for the existing lab release and observe flows with the client tools already installed.

<details>
<summary>Show Answer</summary>

**Answer:**

```bash
# Terminal 1; the lab Cilium release and client tools must already exist.
CILIUM_LAB_CONTEXT=replace-with-nonproduction-context
cilium hubble enable --context "$CILIUM_LAB_CONTEXT" --ui
cilium hubble port-forward --context "$CILIUM_LAB_CONTEXT" --port-forward 4245
```

```bash
# Terminal 2, with the port-forward still running.
BACKEND_POD=replace-with-actual-backend-pod
hubble observe --server 127.0.0.1:4245 --namespace cilium-intro-demo
hubble observe --server 127.0.0.1:4245 --pod "cilium-intro-demo/$BACKEND_POD"
hubble observe --server 127.0.0.1:4245 --protocol http
hubble observe --server 127.0.0.1:4245 --verdict DROPPED
```

**Explanation:**
If the release is GitOps-managed, change the owner’s Helm values instead of an imperative CLI update; skip enable when already enabled. Keep the foreground port-forward active, and configure client TLS if Relay uses it. HTTP events need a supported L7 proxy path, and DROPPED is not every application failure. Use cilium hubble ui in a separate terminal with the same explicit context for UI access.

</details>

[Return to Learning Materials](../../../networking/cilium/01-introduction.md) | [Next Quiz: eBPF Basics](02-ebpf-quiz.md)
