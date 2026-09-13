# Cilium Networking Concepts Quiz

> **Review baseline**: Cilium 1.20.1.
> **Last reviewed**: September 12, 2026.

[Return to the guide](../../../networking/cilium/networking-concepts.md)

## OSI and Basic Concepts

1. **Which description of Cilium policy capabilities is correct?**

   - A) Only a general MAC-address firewall
   - B) Only L3/L4 with no proxy integration
   - C) Only HTTP policy
   - D) L3/L4 controls and configured supported L7 rules

   <details>
   <summary>Show Answer</summary>

   **Answer: D) L3/L4 controls and configured supported L7 rules**

   Cilium combines L3/L4 enforcement with supported HTTP/gRPC and DNS proxy functions. This does not mean implementing every OSI layer or the removed Kafka L7 API.

   </details>

2. **Which is a link-layer address?**

   - A) IP address
   - B) MAC address
   - C) Port number
   - D) URL

   <details>
   <summary>Show Answer</summary>

   **Answer: B) MAC address**

   A MAC address identifies a link-layer interface. It can be locally assigned or changed, so global uniqueness and authenticity are not guaranteed.

   </details>

3. **Which protocol provides network-layer IP addressing?**

   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>Show Answer</summary>

   **Answer: C) IP**

   IP provides logical addressing and network-layer packet delivery; TCP and UDP have different transport semantics.

   </details>

## Container Networking

4. **Without platform overrides, what is the generic Cilium Helm routing default?**

   - A) Docker bridge
   - B) Tunnel/overlay mode
   - C) Mandatory BGP native mode
   - D) Host networking for every workload

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Tunnel/overlay mode**

   The generic default is tunnel mode. Platform-specific installation profiles can choose another mode; it is not an EKS-wide or cloud-wide invariant.

   </details>

5. **Which protocol is the default for the generic Cilium tunnel profile?**

   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>Show Answer</summary>

   **Answer: A) VXLAN**

   VXLAN is the default tunnel protocol, using UDP 8472 in Cilium by default. Standard VXLAN's assigned UDP port is 4789.

   </details>

6. **What is a concrete property of native routing?**

   - A) Automatic encryption
   - B) No need for return routes
   - C) No overlay encapsulation on that path
   - D) Guaranteed best throughput

   <details>
   <summary>Show Answer</summary>

   **Answer: C) No overlay encapsulation on that path**

   Native routing avoids overlay headers but needs valid Pod reachability and return routes. Performance is workload- and implementation-dependent.

   </details>

## IPAM

7. **What is the generic Helm IPAM default without platform overrides?**

   - A) kubernetes
   - B) cluster-pool
   - C) A mode named PodCIDR
   - D) eni

   <details>
   <summary>Show Answer</summary>

   **Answer: B) cluster-pool**

   In cluster-pool mode the operator allocates node CIDRs and each agent allocates Pod IPs locally. Use the actual mode name rather than the ambiguous phrase Cluster Scope.

   </details>

8. **Which Cilium IPAM mode uses EC2 ENIs and VPC addresses?**

   - A) Kubernetes host-scope
   - B) Cluster-pool
   - C) ENI
   - D) Generic CRD-backed

   <details>
   <summary>Show Answer</summary>

   **Answer: C) ENI**

   ENI mode has AWS-specific prerequisites. It is not a universal recommendation for every EKS compute mode or CNI-chaining arrangement.

   </details>

9. **Which Node fields are used by ipam.mode: kubernetes?**

   - A) spec.podCIDR / spec.podCIDRs
   - B) spec.CIDR
   - C) spec.Subnet
   - D) spec.IPRange

   <details>
   <summary>Show Answer</summary>

   **Answer: A) spec.podCIDR / spec.podCIDRs**

   Kubernetes allocates node Pod CIDRs. Cilium uses these in Kubernetes host-scope IPAM; PodCIDR is not the literal IPAM mode name.

   </details>

## Services and Load Balancing

10. **Which feature is not enabled solely by kube-proxy replacement?**

   - A) ClusterIP forwarding
   - B) NodePort forwarding
   - C) Supported LoadBalancer Service forwarding
   - D) Workload mTLS

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Workload mTLS**

   Service forwarding is separate from workload authentication/encryption. External load-balancer provisioning also needs its controller/provider.

   </details>

11. **Which are Cilium's BPF Service load-balancing algorithms?**

   - A) Random and Maglev
   - B) Round robin only
   - C) Least connections by default
   - D) Periodic Maglev timeout rotation

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Random and Maglev**

   Random is the default and Maglev is an alternative on supported paths. Envoy algorithms, ClientIP affinity and affinity timeouts are separate concepts.

   </details>

12. **What does a configured Global Service enable?**

   - A) Automatic worldwide public IP allocation
   - B) Service load balancing across connected clusters
   - C) Automatic replication of every policy
   - D) Shared persistent storage

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Service load balancing across connected clusters**

   ClusterMesh and matching Service names/namespaces are required. Endpoint/cache behavior and failure handling still need validation.

   </details>

## Network Policies

13. **What does toCIDR select?**

   - A) Destination address ranges
   - B) Authenticated DNS hostnames
   - C) Only named Services
   - D) Only TCP ports

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Destination address ranges**

   CIDR selectors have endpoint-classification rules; managed in-cluster Pods/nodes are excluded by default, with an explicit Beta opt-in in this version. It is not an authentication mechanism.

   </details>

14. **What does the world entity represent?**

   - A) All known cluster identities
   - B) External endpoints, rather than known cluster/ClusterMesh identities
   - C) All Kubernetes nodes
   - D) All namespaces

   <details>
   <summary>Show Answer</summary>

   **Answer: B) External endpoints, rather than known cluster/ClusterMesh identities**

   world is not a synonym for every endpoint in every cluster. Select the appropriate entity/identity scope and required ports.

   </details>

15. **Which former Cilium L7 capability was removed?**

   - A) HTTP path matching
   - B) DNS query rules
   - C) Kafka topic rules
   - D) HTTP method matching

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Kafka topic rules**

   Current policy supports HTTP/gRPC-related proxy functions and DNS rules; old Kafka policy examples must not be copied into the current API.

   </details>

## Advanced Concepts

16. **Which pair names alternative Cilium node transport encryption modes?**

   - A) HTTP and DNS
   - B) TCP and UDP
   - C) IPsec and WireGuard
   - D) Relay and Prometheus

   <details>
   <summary>Show Answer</summary>

   **Answer: C) IPsec and WireGuard**

   Choose the appropriate node encryption mode and validate coverage. SPIRE mutual authentication and Beta ztunnel workload mTLS have different roles and prerequisites.

   </details>

17. **What is Cilium's multi-cluster networking feature called?**

   - A) Cluster Federation
   - B) ClusterMesh
   - C) Global Cluster
   - D) NodePort Mesh

   <details>
   <summary>Show Answer</summary>

   **Answer: B) ClusterMesh**

   ClusterMesh shares network metadata and supports configured cross-cluster connectivity; addressing, trust and underlay prerequisites remain.

   </details>

18. **What does Cilium BGP Control Plane do?**

   - A) Programs all learned routes into the local datapath
   - B) Advertises selected Pod/Service prefixes to peers
   - C) Creates DNS records automatically
   - D) Guarantees all cross-cluster traffic

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Advertises selected Pod/Service prefixes to peers**

   Advertisement is distinct from address allocation and actual packet forwarding. Inspect the peer's routes and test both traffic directions.

   </details>

19. **What does Egress Gateway do to matching outbound traffic?**

   - A) SNAT to a selected gateway IP
   - B) Preserve every original Pod source IP
   - C) Automatically encrypt external traffic
   - D) Create gateway interfaces without prerequisites

   <details>
   <summary>Show Answer</summary>

   **Answer: A) SNAT to a selected gateway IP**

   It provides a configured source address by translation. Prepared interfaces/routing and new-Pod policy convergence must be considered.

   </details>

20. **What does BPF host routing optimize?**

   - A) Automatic native/overlay fallback
   - B) Host-internal packet forwarding and use of the host stack
   - C) Host firewall authorization
   - D) Storage encryption

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Host-internal packet forwarding and use of the host stack**

   BPF host routing can bypass parts of the host stack/netfilter with its prerequisites and integration limits. It is distinct from selecting native versus tunnel routing between nodes.

   </details>
