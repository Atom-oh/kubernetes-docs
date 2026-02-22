# Calico Architecture Quiz

> **Related Document**: [Calico Architecture](../../../networking/calico/02-architecture.md)
> **Last Updated**: February 22, 2025

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
Felix is the core agent running on each node in a Calico cluster. Its primary responsibilities include interface management (creating Pod veth pairs), routing table programming, iptables/eBPF rule management, and network policy enforcement. Felix ensures that the dataplane is configured correctly to implement the desired network policies.

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
BIRD (BIRD Internet Routing Daemon) is the BGP agent in Calico responsible for managing BGP peer connections, exchanging and propagating routes between nodes, and optionally functioning as a Route Reflector. BIRD enables Calico's native BGP capabilities for direct routing without encapsulation.

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
confd is responsible for dynamically generating BIRD configuration files based on templates. It monitors the Calico datastore for changes in BGP configuration, node information, and peer settings, then automatically updates BIRD's configuration to reflect these changes without manual intervention.

</details>

4. When should Typha be deployed in a Calico cluster?
   - A) Always, regardless of cluster size
   - B) Only for clusters with more than 50 nodes
   - C) Only when using eBPF mode
   - D) Only for multi-cluster deployments

<details>
<summary>Show Answer</summary>

**Answer: B) Only for clusters with more than 50 nodes**

**Explanation:**
Typha is recommended for clusters with 50 or more nodes. Without Typha, each Felix instance connects directly to the datastore, which can overwhelm the API server in large clusters. Typha aggregates datastore connections and provides cached data to Felix instances, significantly reducing API server load.

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
Calico supports two datastore options: a dedicated etcd cluster or the Kubernetes API (using CRDs). The Kubernetes API datastore is recommended for most deployments as it simplifies operations by using the existing Kubernetes infrastructure. The etcd datastore is used for non-Kubernetes deployments or when specific etcd features are required.

</details>

6. Which controllers are included in kube-controllers?
   - A) Only Policy Controller
   - B) Policy, Namespace, ServiceAccount, WorkloadEndpoint, and Node Controllers
   - C) Only Node and Policy Controllers
   - D) Only WorkloadEndpoint Controller

<details>
<summary>Show Answer</summary>

**Answer: B) Policy, Namespace, ServiceAccount, WorkloadEndpoint, and Node Controllers**

**Explanation:**
kube-controllers includes multiple controllers that synchronize between Kubernetes and the Calico datastore: Policy Controller (NetworkPolicy synchronization), Namespace Controller (namespace profile management), ServiceAccount Controller (service account synchronization), WorkloadEndpoint Controller (endpoint cleanup), and Node Controller (node information synchronization).

</details>

7. What is the recommended formula for calculating Typha replicas in large clusters?
   - A) 1 replica per 50 nodes
   - B) Node count divided by 200, minimum 3
   - C) Fixed at 5 replicas
   - D) 1 replica per 100 nodes, minimum 1

<details>
<summary>Show Answer</summary>

**Answer: B) Node count divided by 200, minimum 3**

**Explanation:**
The recommended formula for Typha replicas is: node count / 200, with a minimum of 3 replicas for high availability. For example, a 500-node cluster would need at least 3 replicas (500/200 = 2.5, rounded up to minimum 3), while a 1000-node cluster would need 5 replicas.

</details>

8. In Calico's packet flow, which component is responsible for programming routing tables on the node?
   - A) BIRD
   - B) confd
   - C) Felix
   - D) Typha

<details>
<summary>Show Answer</summary>

**Answer: C) Felix**

**Explanation:**
Felix is responsible for programming the routing tables on each node. While BIRD handles BGP route exchange between nodes, Felix takes the route information and programs it into the Linux kernel's routing tables. Felix also manages iptables/eBPF rules for policy enforcement.

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
Typha listens on port 5473 (calico-typha) for connections from Felix instances. This is the default port configured in Typha deployments for receiving connections from the calico-node pods running on each node in the cluster.

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
To enable eBPF mode in Calico, you set `bpfEnabled: true` in the FelixConfiguration resource. This switches the dataplane from iptables to eBPF, providing improved performance and enabling features like Direct Server Return (DSR) and kube-proxy replacement.

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
Without Typha, every Felix instance on every node maintains its own connection to the datastore (Kubernetes API server). In large clusters with hundreds of nodes, this can overwhelm the API server with watch connections and data transfers. Typha solves this by aggregating connections and caching data.

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
By default, Felix's health check endpoint listens on port 9099 when `healthEnabled: true` is set in FelixConfiguration. This port is used by Kubernetes liveness and readiness probes to verify that Felix is running correctly on each node.

</details>

---

[Return to Learning Materials](../../../networking/calico/02-architecture.md) | [Previous Quiz: Introduction](./01-introduction-quiz.md) | [Next Quiz: Networking Modes](./03-networking-modes-quiz.md)
