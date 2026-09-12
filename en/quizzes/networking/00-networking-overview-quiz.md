# Kubernetes Networking Overview Quiz

Reviewed September 11, 2026. Use the [networking overview](../../networking/README.md) and its official references for version and platform conditions.

## Quiz Questions

### 1. Which statement is NOT guaranteed by the Kubernetes networking model?

- A. Ordinary Pods have direct Pod-network connectivity, subject to intentional segmentation
- B. Node agents can reach Pods on their own node
- C. Containers in an ordinary Pod share its network namespace
- D. A recreated Pod always retains the same IP

<details>
<summary>Show Answer</summary>

**Answer: D. A recreated Pod always retains the same IP**

A replacement Pod can receive a different IP, and a container restart within the same Pod does not necessarily recreate its network sandbox. Services provide stable discovery over changing endpoints. Network policy and routing still determine whether a particular connection succeeds.

</details>

### 2. What is CNI's primary role in current Kubernetes?

- A. Schedule Pods through the API server
- B. Provide the runtime interface for configuring container networking and addresses
- C. Replace every Service load-balancing implementation
- D. Download container images

<details>
<summary>Show Answer</summary>

**Answer: B. Provide the runtime interface for configuring container networking and addresses**

Kubelet requests sandbox operations through CRI; the container runtime manages and invokes CNI plugins. Plugins implement networking operations and may delegate IPAM or use a provider-specific agent. A veth pair is a common implementation, not a requirement of every CNI.

</details>

### 3. What distinguishes overlay from native routing?

- A. Overlay is always faster
- B. Overlay encapsulates traffic over another network; native routing uses the underlying routes without that overlay
- C. Native routing always requires VXLAN
- D. Only AWS can use an overlay

<details>
<summary>Show Answer</summary>

**Answer: B. Overlay encapsulates traffic over another network; native routing uses the underlying routes without that overlay**

VXLAN/IPIP are encapsulation examples. Native routing requires a suitable route design; it can use BGP but does not always require it. Compare MTU, encryption, policy, traffic and hardware before making performance claims.

</details>

### 4. Which default Service type supplies a cluster-internal virtual IP?

- A. NodePort
- B. LoadBalancer
- C. ClusterIP
- D. ExternalName

<details>
<summary>Show Answer</summary>

**Answer: C. ClusterIP**

ClusterIP is the default. Its typical internal exposure is not a security boundary or a guarantee of reachability. NodePort uses configured node addresses/ports; LoadBalancer requires an implementation and can be internal; ExternalName supplies a DNS alias. Headless Services omit the virtual IP.

</details>

### 5. Which project combines an eBPF-based networking dataplane with Hubble?

- A. Flannel
- B. The original Weave Net project
- C. Cilium
- D. AWS VPC CNI

<details>
<summary>Show Answer</summary>

**Answer: C. Cilium**

Cilium uses eBPF and includes Hubble observability; applicable L7 features use Envoy. Other projects also use eBPF, including Calico dataplane options and AWS's policy agent. The technology name alone does not establish a universal performance ranking.

</details>

### 6. Which statement is NOT an accurate description of the documented EKS VPC-CNI/Auto Mode policy capabilities?

- A. VPC CNI uses VPC addresses and EC2 ENIs/prefixes
- B. Per-node Pod capacity depends on instance limits, allocation mode and kubelet limits
- C. Supported EKS deployments provide standard and Admin network policy capabilities
- D. DNS-based ApplicationNetworkPolicy implies current HTTP-method/body inspection

<details>
<summary>Show Answer</summary>

**Answer: D. DNS-based ApplicationNetworkPolicy implies current HTTP-method/body inspection**

AWS documents DNS/FQDN ApplicationNetworkPolicy for Auto Mode, and Admin ClusterNetworkPolicy for Auto Mode and supported EC2/VPC-CNI installations. DNS-based network-layer controls are distinct from HTTP inspection. Linux EC2, Windows and Fargate support conditions differ; a standard EC2 add-on is not the Auto Mode implementation.

</details>

### 7. Which pair provides a BGP control-plane option?

- A. Flannel and original Weave Net
- B. Calico and Cilium
- C. AWS VPC CNI and Flannel
- D. Original Weave Net and AWS VPC CNI

<details>
<summary>Show Answer</summary>

**Answer: B. Calico and Cilium**

Calico and Cilium can advertise routes to suitable peers. BGP peering does not itself provide application service discovery, workload authentication or encryption. Verify route ownership and the selected CNI's current BGP API and topology requirements.

</details>

### 8. Which traffic is outside ordinary inter-Pod Kubernetes NetworkPolicy isolation?

- A. Traffic between different Pods
- B. Pod egress to an external endpoint
- C. Localhost communication between containers sharing one Pod network namespace
- D. External traffic entering a Pod

<details>
<summary>Show Answer</summary>

**Answer: C. Localhost communication between containers sharing one Pod network namespace**

Containers sharing a Pod network namespace can communicate over localhost. NetworkPolicy requires an enforcement implementation and has defined exceptions and implementation-dependent details. Do not infer that every host, translated or tunneled flow is controlled in the same way.

</details>

### 9. Which is a useful scalability criterion when evaluating a large cluster?

- A. Whether the project has a dashboard alone
- B. Controller/API load, state propagation, per-node resources and behavior under realistic churn
- C. Logo appearance
- D. Release frequency alone

<details>
<summary>Show Answer</summary>

**Answer: B. Controller/API load, state propagation, per-node resources and behavior under realistic churn**

Test policy/endpoint cardinality, update propagation, connection churn, failure recovery and actual dataplane load. A node-count threshold or an eBPF label alone does not prove suitability. Product components and scaling mechanisms must match the chosen installation mode.

</details>

### 10. What is the correct relationship between Ingress and Service?

- A. Ingress is an L4-only API and Service is L7-only
- B. Ingress describes HTTP/HTTPS routing; Services describe network endpoints and discovery
- C. Services are always external
- D. Ingress is UDP-only

<details>
<summary>Show Answer</summary>

**Answer: B. Ingress describes HTTP/HTTPS routing; Services describe network endpoints and discovery**

An Ingress needs a controller/data plane and typically references Service backends. The data plane may connect to endpoint Pod IPs or NodePorts, so the Service virtual IP is not necessarily an extra packet hop. Service protocols and load-balancer support must be checked for the actual implementation.

</details>
