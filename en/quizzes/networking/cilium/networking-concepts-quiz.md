# Cilium Networking Concepts Quiz

> **Supported Version**: Cilium 1.17
> **Last Updated**: February 22, 2026

## OSI Model and Basic Concepts

1. **Which layer of the OSI model does Cilium primarily operate at?**
   - A) L2 (Data Link Layer)
   - B) L3/L4 (Network/Transport Layer)
   - C) L7 (Application Layer)
   - D) All layers from L3 to L7

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) All layers from L3 to L7</p>
   <p><strong>Explanation</strong>: Cilium provides networking and security features not only at L3/L4 (IP addresses, ports) but also up to L7 (HTTP, gRPC, Kafka, etc.) layers.</p>
   </details>

2. **Which of the following is an L2 (Data Link Layer) address?**
   - A) IP address
   - B) MAC address
   - C) Port number
   - D) URL

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) MAC address</p>
   <p><strong>Explanation</strong>: A MAC (Media Access Control) address is a unique identifier for a network interface card and is used at the L2 layer.</p>
   </details>

3. **Which of the following is an L3 (Network Layer) protocol?**
   - A) TCP
   - B) UDP
   - C) IP
   - D) HTTP

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) IP</p>
   <p><strong>Explanation</strong>: IP (Internet Protocol) is a protocol responsible for packet routing at the network layer (L3).</p>
   </details>

## Container Networking

4. **What is Cilium's default network model?**
   - A) Bridge mode
   - B) Overlay network
   - C) Underlay network
   - D) Host network

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Overlay network</p>
   <p><strong>Explanation</strong>: Cilium uses an overlay network model using VXLAN or Geneve by default.</p>
   </details>

5. **What is the default overlay protocol used by Cilium?**
   - A) VXLAN
   - B) GRE
   - C) IPsec
   - D) MPLS

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) VXLAN</p>
   <p><strong>Explanation</strong>: Cilium uses the VXLAN (Virtual Extensible LAN) protocol by default to configure overlay networks.</p>
   </details>

6. **What is the main benefit of Cilium's Direct Routing mode?**
   - A) Higher security
   - B) Better compatibility
   - C) Lower latency and higher throughput
   - D) Easier setup

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) Lower latency and higher throughput</p>
   <p><strong>Explanation</strong>: Direct Routing mode provides lower latency and higher throughput because it does not use overlay encapsulation.</p>
   </details>

## IP Address Management (IPAM)

7. **What is Cilium's default IPAM mode?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) CRD-based
   - D) AWS ENI

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Cluster Scope</p>
   <p><strong>Explanation</strong>: Cilium's default IPAM mode is Cluster Scope, which allocates IP addresses centrally across the entire cluster.</p>
   </details>

8. **What is the recommended IPAM mode when using Cilium on AWS EKS?**
   - A) Kubernetes Host Scope
   - B) Cluster Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) AWS ENI</p>
   <p><strong>Explanation</strong>: On AWS EKS, it is recommended to use AWS ENI IPAM mode to directly allocate VPC IP addresses to Pods.</p>
   </details>

9. **What Kubernetes feature does Cilium's IPAM 'PodCIDR' mode utilize?**
   - A) NodeSpec.PodCIDR
   - B) NodeSpec.CIDR
   - C) NodeSpec.Subnet
   - D) NodeSpec.IPRange

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) NodeSpec.PodCIDR</p>
   <p><strong>Explanation</strong>: Cilium's PodCIDR IPAM mode utilizes the NodeSpec.PodCIDR field assigned by Kubernetes to each node.</p>
   </details>

## Services and Load Balancing

10. **Which feature is NOT provided by Cilium's kube-proxy replacement mode?**
    - A) ClusterIP service support
    - B) NodePort service support
    - C) LoadBalancer service support
    - D) Service mesh functionality

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Service mesh functionality</p>
    <p><strong>Explanation</strong>: Cilium's kube-proxy replacement mode supports basic Kubernetes service types, but service mesh functionality is provided through a separate Cilium Service Mesh feature.</p>
    </details>

11. **What algorithms does Cilium use for service load balancing?**
    - A) Round robin
    - B) Least connections
    - C) IP hash
    - D) All of the above

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) All of the above</p>
    <p><strong>Explanation</strong>: Cilium supports various load balancing algorithms including round robin, least connections, and IP hash.</p>
    </details>

12. **What does Cilium's Global Service feature enable?**
    - A) Globally distributed service access
    - B) Service load balancing across multiple clusters
    - C) Global IP address allocation
    - D) Global network policy application

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Service load balancing across multiple clusters</p>
    <p><strong>Explanation</strong>: Cilium's Global Service feature enables load balancing for the same service across multiple clusters through Cluster Mesh.</p>
    </details>

## Network Policies

13. **What does the 'toCIDR' rule in Cilium network policies allow?**
    - A) Traffic to specific IP address ranges
    - B) Traffic to specific domain names
    - C) Traffic to specific services
    - D) Traffic to specific ports

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) Traffic to specific IP address ranges</p>
    <p><strong>Explanation</strong>: The toCIDR rule is used to allow traffic to specific IP address ranges (in CIDR notation).</p>
    </details>

14. **What does the 'world' entity mean in Cilium network policy 'toEntities' rules?**
    - A) All internal cluster endpoints
    - B) All external networks
    - C) All nodes
    - D) All namespaces

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) All external networks</p>
    <p><strong>Explanation</strong>: The 'world' entity means all networks external to the cluster.</p>
    </details>

15. **Which protocol is NOT supported in Cilium's L7 policies?**
    - A) HTTP
    - B) gRPC
    - C) Kafka
    - D) SMTP

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) SMTP</p>
    <p><strong>Explanation</strong>: Cilium supports L7 protocols such as HTTP, gRPC, and Kafka, but does not support SMTP by default.</p>
    </details>

## Advanced Networking Concepts

16. **What protocols can be used in Cilium's Transparent Encryption feature?**
    - A) IPsec
    - B) WireGuard
    - C) Both A and B
    - D) TLS

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) Both A and B</p>
    <p><strong>Explanation</strong>: Cilium can encrypt traffic between nodes using both IPsec and WireGuard.</p>
    </details>

17. **What technology does Cilium's Multi-cluster feature use?**
    - A) Cluster Federation
    - B) Cluster Mesh
    - C) Multi-cluster Networking
    - D) Global Cluster

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Cluster Mesh</p>
    <p><strong>Explanation</strong>: Cilium uses Cluster Mesh technology to provide connectivity between multiple Kubernetes clusters.</p>
    </details>

18. **What is possible through Cilium's BGP support?**
    - A) Route exchange with external routers
    - B) External IP advertisement for LoadBalancer services
    - C) Direct routing between clusters
    - D) All of the above

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) All of the above</p>
    <p><strong>Explanation</strong>: Cilium's BGP support enables route exchange with external routers, external IP advertisement for LoadBalancer services, and direct routing between clusters.</p>
    </details>

19. **What is the main purpose of Cilium's Egress Gateway feature?**
    - A) Preserving the source IP address of external traffic
    - B) Changing the destination IP address of external traffic
    - C) Encrypting external traffic
    - D) Blocking external traffic

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) Preserving the source IP address of external traffic</p>
    <p><strong>Explanation</strong>: Egress Gateway SNATs traffic going from Pods to outside the cluster to a specific IP, providing a consistent source IP.</p>
    </details>

20. **Which statement is correct about Cilium's Host Routing feature?**
    - A) Routing between host network and Pod network
    - B) Direct routing between hosts
    - C) Host network interface protection
    - D) Host-based load balancing

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Direct routing between hosts</p>
    <p><strong>Explanation</strong>: Cilium's Host Routing provides direct routing between hosts without an overlay network.</p>
    </details>
