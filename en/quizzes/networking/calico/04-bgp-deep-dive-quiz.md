# BGP Deep Dive Quiz

> **Related Document**: [BGP Deep Dive](../../../networking/calico/04-bgp-deep-dive.md)
> **Last Updated**: February 22, 2026

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

3. What is the private AS number range that can be used for Calico clusters?
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>Show Answer</summary>

**Answer: B) 64512-65534**

**Explanation:**
The private AS number range is 64512-65534 (for 16-bit ASNs) and 4200000000-4294967294 (for 32-bit ASNs). These ranges are designated for private use and are not globally routable, similar to private IP address ranges. Calico clusters commonly use AS numbers in the 64512-65534 range.

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
The Cluster ID is used to prevent routing loops when multiple Route Reflectors are deployed. When a Route Reflector receives a route with its own Cluster ID, it knows the route has already been through this RR cluster and discards it. All Route Reflectors in the same cluster should share the same Cluster ID.

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
Setting `nodeToNodeMeshEnabled: false` in the BGPConfiguration resource disables the automatic full-mesh BGP peering between all nodes. This should be done when using Route Reflectors or external BGP peering, as the full mesh becomes unnecessary and creates overhead in larger deployments.

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
Calico can advertise multiple types of Service IPs via BGP: ClusterIPs (internal service IPs), ExternalIPs (external IPs assigned to services), and LoadBalancer IPs. This is configured in the BGPConfiguration resource using `serviceClusterIPs`, `serviceExternalIPs`, and `serviceLoadBalancerIPs` fields respectively.

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
BGP communities are tags attached to routes that can be used by routers to make policy decisions. In Calico, you can configure community tags for advertised prefixes, allowing downstream routers to apply specific policies (like traffic engineering or filtering) based on these tags. Communities are expressed as AS:value pairs (e.g., 64512:100).

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
Calico supports MD5 authentication for securing BGP sessions. This is a TCP MD5 signature option that authenticates BGP messages between peers. While not providing encryption, it prevents unauthorized devices from establishing BGP sessions with your nodes. The password is configured in the BGPPeer resource.

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
Graceful Restart is a BGP capability that allows the forwarding plane to continue operating during a BGP daemon restart. The restarting router informs its peers that it is restarting, and peers preserve routes from that router for a grace period. This prevents traffic disruption during software updates or brief failures.

</details>

13. What command is used to check BGP protocol status in the BIRD daemon?
    - A) bird status
    - B) birdcl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>Show Answer</summary>

**Answer: B) birdcl show protocols**

**Explanation:**
The `birdcl show protocols` command displays the status of all BGP protocols in the BIRD daemon. This shows whether BGP sessions are established, the peer state, and route exchange statistics. Other useful commands include `birdcl show route` to display the routing table and `birdcl show protocols all <name>` for detailed session information.

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

15. What happens when nodeToNodeMeshEnabled is true and you also configure Route Reflectors?
    - A) Route Reflectors take priority, mesh is disabled
    - B) Both the mesh and Route Reflector sessions are established (suboptimal)
    - C) Configuration error, Calico fails to start
    - D) Route Reflectors are ignored

<details>
<summary>Show Answer</summary>

**Answer: B) Both the mesh and Route Reflector sessions are established (suboptimal)**

**Explanation:**
If nodeToNodeMeshEnabled remains true while Route Reflectors are configured, both the full mesh sessions AND the Route Reflector sessions will be established. This is suboptimal and wasteful. When using Route Reflectors, you should set `nodeToNodeMeshEnabled: false` to disable the automatic mesh and rely solely on the Route Reflectors for route distribution.

</details>

---

[Return to Learning Materials](../../../networking/calico/04-bgp-deep-dive.md) | [Previous Quiz: Networking Modes](./03-networking-modes-quiz.md) | [Next Quiz: Network Policy](./05-network-policy-quiz.md)
