# BGP Deep Dive Quiz

> **Related Document**: [BGP Deep Dive](../../../networking/calico/04-bgp-deep-dive.md)
> **Last Updated**: September 12, 2026

## Quiz

1. What does BGP stand for?
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Bridge Gateway Protocol
   - D) Bandwidth Gateway Protocol

<details>
<summary>Show Answer</summary>

**Answer: B) Border Gateway Protocol**

**Explanation:**
BGP stands for Border Gateway Protocol. It is the routing protocol that powers the internet, enabling autonomous systems to exchange routing information. In Calico, BGP is used to distribute pod network routes between nodes and optionally to external network infrastructure.

</details>

2. What is the difference between iBGP and eBGP?
   - A) iBGP is faster, eBGP is more secure
   - B) iBGP is within the same AS, eBGP is between different ASes
   - C) iBGP uses TCP, eBGP uses UDP
   - D) iBGP is for IPv4, eBGP is for IPv6

<details>
<summary>Show Answer</summary>

**Answer: B) iBGP is within the same AS, eBGP is between different ASes**

**Explanation:**
iBGP (Internal BGP) refers to BGP sessions between routers within the same Autonomous System (AS). eBGP (External BGP) refers to BGP sessions between routers in different Autonomous Systems. In Calico clusters, nodes typically use iBGP within the cluster (same AS) and may use eBGP to peer with external network infrastructure (different AS).

</details>

3. Which range is reserved for private 16-bit ASNs?
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>Show Answer</summary>

**Answer: B) 64512-65534**

**Explanation:**
Private ASN ranges are 64512–65534 (16-bit) and 4200000000–4294967294 (32-bit). They identify autonomous systems; they are not inherently unroutable IP addresses. Remove private ASNs from AS paths before advertising those routes to the global Internet. Calico defaults to ASN 64512.

</details>

4. In a full-mesh BGP topology, how many BGP sessions are established in a cluster with N nodes?
   - A) N sessions
   - B) N * 2 sessions
   - C) N * (N-1) / 2 sessions
   - D) N^2 sessions

<details>
<summary>Show Answer</summary>

**Answer: C) N * (N-1) / 2 sessions**

**Explanation:**
In a full-mesh BGP topology, every node peers with every other node. The number of sessions is calculated as N * (N-1) / 2, where N is the number of nodes. For example, a 10-node cluster would have 10 * 9 / 2 = 45 BGP sessions. This is why Route Reflectors are recommended for larger clusters.

</details>

5. What is the primary role of a BGP Route Reflector?
   - A) To encrypt BGP traffic
   - B) To reduce the number of BGP sessions by reflecting routes to clients
   - C) To filter malicious routes
   - D) To convert iBGP to eBGP

<details>
<summary>Show Answer</summary>

**Answer: B) To reduce the number of BGP sessions by reflecting routes to clients**

**Explanation:**
A Route Reflector reduces the number of required BGP sessions in a cluster by receiving routes from clients and "reflecting" them to other clients. Instead of N*(N-1)/2 sessions in a full mesh, clients only need to peer with the Route Reflector(s). This is essential for scaling BGP in large clusters.

</details>

6. What is the purpose of the Cluster ID in a Route Reflector configuration?
   - A) To identify the Kubernetes cluster
   - B) To prevent routing loops between Route Reflectors
   - C) To assign IP addresses to nodes
   - D) To encrypt BGP sessions

<details>
<summary>Show Answer</summary>

**Answer: B) To prevent routing loops between Route Reflectors**

**Explanation:**
A reflector rejects a reflected route whose CLUSTER_LIST already contains its own cluster ID. Redundant RRs serving the same clients can share an ID; different RR groups or hierarchy levels require deliberate IDs. This is not the Kubernetes cluster identifier.

</details>

7. What does the nodeSelector field in a BGPPeer resource control?
   - A) Which pods can use BGP
   - B) Which nodes should establish the BGP peering
   - C) Which routes are advertised
   - D) Which namespaces can use the peer

<details>
<summary>Show Answer</summary>

**Answer: B) Which nodes should establish the BGP peering**

**Explanation:**
The `nodeSelector` field in a BGPPeer resource specifies which nodes should establish a BGP session with the defined peer. This is useful for rack-aware peering where only nodes in a specific rack should peer with the local ToR (Top of Rack) switch, rather than all nodes in the cluster.

</details>

8. Which BGPConfiguration setting disables the automatic node-to-node mesh?
   - A) meshEnabled: false
   - B) nodeToNodeMeshEnabled: false
   - C) disableMesh: true
   - D) bgpMesh: disabled

<details>
<summary>Show Answer</summary>

**Answer: B) nodeToNodeMeshEnabled: false**

**Explanation:**
The setting disables automatic mesh sessions. Establish and verify replacement RR or fabric sessions, received/exported routes, next hops and representative traffic first. Marking a node as an RR removes that node from the automatic mesh immediately, so prepare suitable nodes before converting them.

</details>

9. Which types of Service IPs can Calico advertise via BGP?
   - A) Only ClusterIPs
   - B) Only LoadBalancer IPs
   - C) ClusterIPs, ExternalIPs, and LoadBalancer IPs
   - D) Only NodePort services

<details>
<summary>Show Answer</summary>

**Answer: C) ClusterIPs, ExternalIPs, and LoadBalancer IPs**

**Explanation:**
The fields are serviceClusterIPs, serviceExternalIPs and serviceLoadBalancerIPs. They advertise existing addresses; allocation, endpoint health and return routing are separate prerequisites. A cloud load-balancer hostname is not a BGP prefix. Kubernetes spec.externalIPs is deprecated since 1.36, not removed.

</details>

10. What is the purpose of BGP communities in Calico?
    - A) To create user groups for access control
    - B) To tag routes with metadata for policy decisions
    - C) To encrypt specific routes
    - D) To compress routing tables

<details>
<summary>Show Answer</summary>

**Answer: B) To tag routes with metadata for policy decisions**

**Explanation:**
Communities tag routes for router policy. A standard community has two 16-bit values; a large community has three 32-bit values. Names such as high-priority or internal-only do not enforce their meaning automatically. prefixAdvertisements tags matching existing routes; it does not originate an aggregate.

</details>

11. What authentication method can be used to secure BGP sessions in Calico?
    - A) TLS certificates
    - B) MD5 authentication
    - C) OAuth tokens
    - D) Kerberos

<details>
<summary>Show Answer</summary>

**Answer: B) MD5 authentication**

**Explanation:**
The TCP MD5 signature option authenticates BGP traffic using a shared secret referenced by BGPPeer. It does not encrypt traffic or prove that routes from an authenticated peer are legitimate. Configure matching credentials and routing filters independently.

</details>

12. What is Graceful Restart in BGP context?
    - A) A method to restart BGP without losing configuration
    - B) A mechanism to preserve forwarding state during BGP daemon restart
    - C) A way to gradually add new BGP peers
    - D) A technique for slow route withdrawal

<details>
<summary>Show Answer</summary>

**Answer: B) A mechanism to preserve forwarding state during BGP daemon restart**

**Explanation:**
Peers negotiate Graceful Restart capability and may retain routes for a bounded interval while a BGP daemon restarts. It helps only if the forwarding path remains usable; retained stale routes can blackhole traffic. It is not a guarantee of uninterrupted updates.

</details>

13. What command is used to check BGP protocol status in the BIRD daemon?
    - A) bird status
    - B) birdcl -s /var/run/calico/bird.ctl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>Show Answer</summary>

**Answer: B) birdcl -s /var/run/calico/bird.ctl show protocols**

**Explanation:**
Run the command inside the intended calico-node container using the explicit IPv4 control socket. It lists protocols including BGP, kernel and device protocols; use show protocols all with an actual protocol name for detail. IPv6 uses birdcl6 and /var/run/calico/bird6.ctl. A BGP-disabled installation may have no BIRD daemon.

</details>

14. In a Spine-Leaf data center topology, how should Calico nodes typically peer?
    - A) All nodes peer with all spine switches
    - B) Nodes peer with their local ToR (Leaf) switches
    - C) Only master nodes peer with network infrastructure
    - D) Nodes peer directly with each other, bypassing switches

<details>
<summary>Show Answer</summary>

**Answer: B) Nodes peer with their local ToR (Leaf) switches**

**Explanation:**
In a Spine-Leaf topology, Calico nodes typically peer with their local Top-of-Rack (ToR/Leaf) switches. The Leaf switches then peer with Spine switches. This follows the hierarchical design of the data center network and uses nodeSelector in BGPPeer resources to ensure nodes only peer with their rack's ToR switch.

</details>

15. What can happen while nodeToNodeMeshEnabled is true and explicit Route Reflector peerings are being introduced?
    - A) Route Reflectors take priority, mesh is disabled
    - B) Non-RR client mesh sessions can coexist with explicit RR sessions during transition
    - C) Configuration error, Calico fails to start
    - D) Route Reflectors are ignored

<details>
<summary>Show Answer</summary>

**Answer: B) Non-RR client mesh sessions can coexist with explicit RR sessions during transition**

**Explanation:**
RR nodes are excluded from the automatic mesh after a routeReflectorClusterID is set. The remaining non-RR clients can keep their mesh while explicit RR sessions are prepared and tested. Only remove that mesh after the replacement sessions, routes, next hops and traffic are verified.

</details>

16. Which import rule matches only the IPv4 default route?
    - A) Accept with In 0.0.0.0/0
    - B) Accept with Equal 0.0.0.0/0
    - C) Reject with NotIn 0.0.0.0/0
    - D) A filter with no rules

<details>
<summary>Show Answer</summary>

**Answer: B) Accept with Equal 0.0.0.0/0**

**Explanation:**
Equal matches the exact /0 prefix. In /0 matches every IPv4 route; NotIn /0 matches none. BGPFilter defaults to Accept for unmatched routes, so a whitelist also needs a final unconditional Reject.

</details>

17. What does prefixAdvertisements for 10.244.0.0/16 do?
    - A) Always originates a new /16 route
    - B) Replaces every /26 route with a /16
    - C) Adds communities to existing routes matching that range
    - D) Allocates Service IPs

<details>
<summary>Show Answer</summary>

**Answer: C) Adds communities to existing routes matching that range**

**Explanation:**
The current Calico renderer adds communities to matching existing routes, including Pod routes. It does not originate the prefix, allocate addresses or aggregate blocks. An earlier explicit BGPFilter export Accept can bypass that built-in tagging, so an accepted-route operation may be needed.

</details>


---

[Return to Learning Materials](../../../networking/calico/04-bgp-deep-dive.md) | [Previous Quiz: Networking Modes](./03-networking-modes-quiz.md) | [Next Quiz: Network Policy](./05-network-policy-quiz.md)
