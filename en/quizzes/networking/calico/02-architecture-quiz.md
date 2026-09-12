# Calico Architecture Quiz

> **Related Document**: [Calico Architecture](../../../networking/calico/02-architecture.md)
> **Last Updated**: September 12, 2026

## Quiz

1. What is the primary role of Felix in Calico's architecture?
   - A) BGP route distribution
   - B) Policy enforcement and interface management on each node
   - C) Datastore connection aggregation
   - D) Configuration template processing

<details>
<summary>Show Answer</summary>

**Answer: B) Policy enforcement and interface management on each node**

**Explanation:**
Felix reconciles endpoint interface settings, applicable routes and kernel policy. In full Calico Linux networking, the container runtime invokes the CNI/IPAM chain to allocate addresses and create Pod veth interfaces. Felix is not directly called with CNI ADD and does not own Pod IP allocation.

</details>

2. What does BIRD stand for and what is its role in Calico?
   - A) Basic Internet Routing Daemon - handles DNS resolution
   - B) BIRD Internet Routing Daemon - handles BGP routing
   - C) Binary Internet Relay Daemon - handles packet forwarding
   - D) Bridge Internet Routing Device - handles VXLAN tunneling

<details>
<summary>Show Answer</summary>

**Answer: B) BIRD Internet Routing Daemon - handles BGP routing**

**Explanation:**
BIRD manages BGP sessions and route exchange when that backend is enabled. It can act as a route reflector and synchronize routes with the kernel through its kernel protocol. BGP can coexist with encapsulation; enabling BGP does not itself guarantee unencapsulated forwarding. Workload packets do not flow through the BIRD process.

</details>

3. What is the purpose of confd in Calico's architecture?
   - A) Managing container configurations
   - B) Dynamically generating BIRD configuration files
   - C) Storing network policies
   - D) Load balancing traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Dynamically generating BIRD configuration files**

**Explanation:**
confd watches the relevant datastore state and renders the installed BIRD templates. It checks the result and invokes the configured reload command. The generated file is not the durable configuration source; change BGP API resources instead of editing generated bird.cfg.

</details>

4. Which statement about deploying Typha is accurate?
   - A) Always, regardless of cluster size
   - B) Operator installations can deploy Typha below 50 nodes; use the installed version's scaling logic and actual workload requirements
   - C) Only when using eBPF mode
   - D) Only for multi-cluster deployments

<details>
<summary>Show Answer</summary>

**Answer: B) Operator installations can deploy Typha below 50 nodes; use the installed version's scaling logic and actual workload requirements**

**Explanation:**
Typha reduces direct datastore update fan-out to Felix. It is not universally mandatory only above 50 nodes, nor required in every non-operator installation. Operator 1.42.6 scales it for small clusters too, using counted-node logic and checking Linux placement capacity.

</details>

5. What datastore options does Calico support?
   - A) MySQL and PostgreSQL
   - B) etcd and Kubernetes API
   - C) MongoDB and Redis
   - D) Only dedicated etcd

<details>
<summary>Show Answer</summary>

**Answer: B) etcd and Kubernetes API**

**Explanation:**
Calico has Kubernetes API and direct etcdv3 datastore paths with feature/installation constraints. The Kubernetes API path still uses Kubernetes' backing storage but needs no separate Calico etcd cluster. Direct etcd needs its own TLS, credentials, availability and backup design; node count alone is not a reason to switch.

</details>

6. Which controllers does operator 1.42.6 select for its standard Open Source kube-controllers deployment?
   - A) Only Policy Controller
   - B) node and loadbalancer
   - C) Only Node and Policy Controllers
   - D) Only WorkloadEndpoint Controller

<details>
<summary>Show Answer</summary>

**Answer: B) node and loadbalancer**

**Explanation:**
The pinned operator renderer starts node and loadbalancer for its normal Open Source deployment. Policy, namespace, serviceaccount and workloadendpoint controllers also exist for applicable datastore/configuration paths, but they are not all necessarily enabled. ServiceAccount profiles do not grant Kubernetes RBAC.

</details>

7. For 500 counted nodes, what desired Typha replica count does operator 1.42.6's scale function return?
   - A) 1 replica per 50 nodes
   - B) 4 replicas, from floor(500 / 200) + 2
   - C) Fixed at 5 replicas
   - D) 1 replica per 100 nodes, minimum 1

<details>
<summary>Show Answer</summary>

**Answer: B) 4 replicas, from floor(500 / 200) + 2**

**Explanation:**
For more than four counted nodes, this version computes max(3, floor(N / 200) + 2), so 500 gives 4. One or two nodes give 1; three or four give 2. At 1,000 the result is 7. The autoscaler excludes unschedulable nodes and AKS virtual nodes and checks available Linux nodes; the result is not a throughput guarantee.

</details>

8. Which Calico agent reconciles local workload route and kernel-policy state?
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>Show Answer</summary>

**Answer: C) Felix**

**Explanation:**
Felix handles local workload route/policy reconciliation. This does not mean it is the only component touching routes: the CNI creates initial interface/routes, and BIRD's kernel protocol can install BGP-learned routes. confd generates BIRD configuration; Typha distributes cached state.

</details>

9. What port does Typha use to communicate with Felix instances?
   - A) 443
   - B) 5473
   - C) 8080
   - D) 9090

<details>
<summary>Show Answer</summary>

**Answer: B) 5473**

**Explanation:**
TCP 5473 is Typha's default synchronization listener for clients such as Felix. It is separate from metrics and health ports, and is not an application-traffic proxy. The operator also configures TLS trust and client identity.

</details>

10. Which FelixConfiguration setting enables eBPF mode?
   - A) ebpfEnabled: true
   - B) bpfEnabled: true
   - C) dataplaneMode: ebpf
   - D) useEbpf: true

<details>
<summary>Show Answer</summary>

**Answer: B) bpfEnabled: true**

**Explanation:**
bpfEnabled is a valid low-level FelixConfiguration field. For an operator-managed installation, use the supported Installation linuxDataplane setting and coordinate kube-proxy and API reachability. Changing one boolean is not a complete, validated migration or a guarantee that every eBPF feature is available.

</details>

11. What happens to Felix instances when Typha is not deployed in a large cluster?
   - A) Felix instances fail to start
   - B) Each Felix connects directly to the datastore, potentially overwhelming the API server
   - C) Network policies are not enforced
   - D) BGP peering fails

<details>
<summary>Show Answer</summary>

**Answer: B) Each Felix connects directly to the datastore, potentially overwhelming the API server**

**Explanation:**
Direct watches can increase datastore/API load as node count and update volume grow. This is a capacity concern, not a guarantee that policies or BGP stop working without Typha. Even with Typha, other components still access the Kubernetes API.

</details>

12. What is the health check port for Felix by default?
   - A) 8080
   - B) 9091
   - C) 9099
   - D) 10250

<details>
<summary>Show Answer</summary>

**Answer: C) 9099**

**Explanation:**
Felix's default health port is 9099 when health serving is enabled, with localhost as the default bind address. Probe/network settings must match the actual deployment; a request to localhost on an administrator laptop does not inspect a node. The usual metrics port is 9091.

</details>

---

[Learning material](../../../networking/calico/02-architecture.md) | [Previous quiz](01-introduction-quiz.md) | [Next quiz](03-networking-modes-quiz.md)
