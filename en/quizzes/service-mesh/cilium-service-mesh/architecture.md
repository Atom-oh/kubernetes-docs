# Cilium Service Mesh Architecture Quiz

Reviewed against Cilium 1.20.1. Read the [architecture guide](../../../service-mesh/cilium-service-mesh/01-architecture.md) for the configuration, qualifications and primary references.

### 1. What is a characteristic of Cilium's architecture?

- **A.** It replaces the Kubernetes API server
- **B.** It combines eBPF L3/L4 processing with Envoy for applicable L7 traffic
- **C.** It sends every packet through a per-Pod Envoy
- **D.** It cannot use Kubernetes resources

<details>
<summary>Show Answer</summary>

**Answer: B. It combines eBPF L3/L4 processing with Envoy for applicable L7 traffic**

Cilium implements networking and L3/L4 policy with eBPF. Applicable L7 functions use Envoy, either agent-managed or in a separate DaemonSet. This describes component placement, not a universal performance result.

</details>

### 2. Which item is not a kernel attachment mechanism used to describe Cilium's datapath?

- **A.** TC/TCX
- **B.** cgroup socket hooks
- **C.** The application's HTTP handler
- **D.** XDP

<details>
<summary>Show Answer</summary>

**Answer: C. The application's HTTP handler**

An HTTP handler is application code, not a kernel hook. Cilium can use TC/TCX and cgroup hooks; XDP acceleration requires an appropriate configuration/device. The presence of eBPF does not mean all these hooks run on every packet.

</details>

### 3. What does sharing an Envoy process at node scope establish?

- **A.** Exactly 100 MB of memory per node
- **B.** A guaranteed 0.1 ms request latency
- **C.** A shared proxy lifecycle/resource/failure boundary that must be sized for the workload
- **D.** That encryption needs no configuration

<details>
<summary>Show Answer</summary>

**Answer: C. A shared proxy lifecycle/resource/failure boundary that must be sized for the workload**

Sharing can reduce the number of proxy instances compared with per-Pod sidecars, but total resource use includes agents, maps, control-plane and optional components. Node count, traffic, policies and features determine the actual cost; the old fixed 5 GB versus 500 MB comparison was not a measured result.

</details>

### 4. What does a CiliumEnvoyConfig define?

- **A.** Pod scheduling only
- **B.** Namespaced low-level Envoy resources and associated Service redirection/backend synchronization
- **C.** A replacement for every CiliumEndpoint
- **D.** A universal configuration accepted solely because kubectl apply succeeds

<details>
<summary>Show Answer</summary>

**Answer: B. Namespaced low-level Envoy resources and associated Service redirection/backend synchronization**

CEC connects Kubernetes Services with Envoy Listeners, Routes and Clusters. Cilium can allocate omitted listener addresses and fill xDS sources. Kubernetes does not validate all embedded Envoy fields, so acceptance and runtime behavior still need checking. CCEC has cluster scope but does not turn '*' into a Service wildcard.

</details>

### 5. Which statement about Maglev is correct?

- **A.** It is an HTTP cookie parser
- **B.** It replaces Kubernetes ClientIP session affinity
- **C.** It provides consistent backend selection for applicable external traffic, separately from session affinity
- **D.** It guarantees that removed backends keep serving old connections

<details>
<summary>Show Answer</summary>

**Answer: C. It provides consistent backend selection for applicable external traffic, separately from session affinity**

Maglev consistently maps flows to backends for applicable north–south load balancing. The documented socket-level east–west path is not subject to Maglev. ClientIP affinity and connection tracking are separate mechanisms; Maglev cannot keep an unavailable backend alive.

</details>

### 6. How is a Cilium workload security identity assigned?

- **A.** It is always identical to the Pod IP
- **B.** Cilium allocates a numeric ID for an identity-relevant label set; several Pods can share it
- **C.** Users calculate a label hash and create a guessed CiliumIdentity
- **D.** Every Pod has a globally permanent numeric identity

<details>
<summary>Show Answer</summary>

**Answer: B. Cilium allocates a numeric ID for an identity-relevant label set; several Pods can share it**

Identity-relevant labels can include namespace, service account and selected workload labels. The allocator resolves the label set to an ID; it is not a user-computed hash or necessarily unique per Pod. Inspect CiliumEndpoint/CiliumIdentity and the agent's cilium-dbg identity list.

</details>

### 7. Which traffic may use Envoy?

- **A.** Every packet in every configuration
- **B.** HTTP L7 policy traffic and traffic redirected by supported Service/Ingress/Gateway configuration
- **C.** Only flows with a CiliumNetworkPolicy HTTP rule, never Gateway traffic
- **D.** No traffic unless every Pod has an Envoy sidecar

<details>
<summary>Show Answer</summary>

**Answer: B. HTTP L7 policy traffic and traffic redirected by supported Service/Ingress/Gateway configuration**

HTTP policy redirects the corresponding ingress or egress traffic to Envoy. CEC Service load balancing and Gateway/Ingress can also require Envoy. The response of a proxied request uses the established proxy connection; this is not an independent optional redirect for each response.

</details>

### 8. What is Cilium's BPF connection tracking used for?

- **A.** Replacing the Kubernetes API
- **B.** Maintaining flow state and recognizing return traffic, alongside policy checks
- **C.** Permanently caching the first allow decision for all future packets
- **D.** Storing HTTP application credentials

<details>
<summary>Show Answer</summary>

**Answer: B. Maintaining flow state and recognizing return traffic, alongside policy checks**

CT maps track flow state, lifetime and translation/proxy metadata. The released endpoint datapath checks policy for both new and established initiating-direction traffic, with explicit exceptions, and handles recognized replies statefully. CT caching is not a blanket exemption from policy enforcement.

</details>

### 9. What distinguishes CiliumClusterwideNetworkPolicy from CiliumNetworkPolicy?

- **A.** They have identical Kubernetes resource scope
- **B.** CCNP is cluster-scoped, while CNP is namespaced; selectors still determine the affected endpoints
- **C.** Only CNP can express any L7 rule
- **D.** Every CCNP necessarily denies every namespace

<details>
<summary>Show Answer</summary>

**Answer: B. CCNP is cluster-scoped, while CNP is namespaced; selectors still determine the affected endpoints**

Both support applicable L7 policy rules. Resource scope and endpoint selection are different concepts: a cluster-scoped resource does not automatically select or deny all workloads. Other applicable policy grants also matter.

</details>

### 10. What is the default SPIFFE ID form for Cilium's beta out-of-band mutual authentication?

- **A.** urn:spiffe:cluster/namespace/pod
- **B.** `spiffe://spiffe.cilium/identity/<numeric-security-identity>`
- **C.** `spiffe://cluster.local/ns/<namespace>/sa/<service-account>` in every Cilium installation
- **D.** `https://spiffe.io/id/<pod-name>`

<details>
<summary>Show Answer</summary>

**Answer: B. `spiffe://spiffe.cilium/identity/<numeric-security-identity>`**

Cilium's released SPIRE provider constructs the `/identity/<numeric-id>` path under its configured trust domain, defaulting to spiffe.cilium. Agents act on behalf of Cilium security identities. The authentication exchange is out of band; application encryption requires separate WireGuard/IPsec configuration. The out-of-band feature remains beta/incomplete. The separate ztunnel encryption beta uses a different workload identity model; this answer does not describe its certificate path.

</details>

### 11. Which is not a Cilium Agent responsibility?

- **A.** Local eBPF program and map management
- **B.** Local policy and Envoy configuration management
- **C.** Serving as the Kubernetes API server
- **D.** Local endpoint and identity-related management

<details>
<summary>Show Answer</summary>

**Answer: C. Serving as the Kubernetes API server**

The Agent runs on nodes; the Kubernetes API server remains a separate control-plane component. Cilium Operator is a separate Deployment for cluster-wide tasks such as identity garbage collection and relevant IPAM operations.

</details>

### 12. Which statement about same-node Pod traffic is accurate?

- **A.** It must always leave the node
- **B.** A suitable BPF host-routing path can bypass upper host networking layers, but the actual path depends on configuration
- **C.** All Linux and Pod networking stacks are always bypassed
- **D.** Its latency is guaranteed to be 0.1 ms

<details>
<summary>Show Answer</summary>

**Answer: B. A suitable BPF host-routing path can bypass upper host networking layers, but the actual path depends on configuration**

BPF host routing can bypass the upper host stack/netfilter when requirements are met. Pod protocol stacks still exist. Legacy routing, endpoint device mode, L7 policy and integrations change the path; latency requires measurement.

</details>
