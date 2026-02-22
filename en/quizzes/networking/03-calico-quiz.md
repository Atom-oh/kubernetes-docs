# Calico Quiz

This quiz tests your understanding of Calico CNI architecture, Network Policy, BGP configuration, and operations.

## Quiz Questions

### 1. Which Calico core component is the agent that enforces Network Policy on each node?

A. BIRD
B. Felix
C. confd
D. Typha

<details>
<summary>Show Answer</summary>

**Answer: B. Felix**

**Explanation:**
Calico component roles:
- **Felix**: Core agent running on each node. Manages interfaces, programs routing tables, manages iptables/eBPF rules, enforces Network Policy
- **BIRD**: BGP routing daemon. Route exchange and propagation
- **confd**: Dynamic generation of BIRD configuration files
- **Typha**: Aggregates datastore connections in large clusters

</details>

### 2. Which component is recommended for Calico clusters with 50 or more nodes?

A. Felix
B. BIRD
C. Typha
D. confd

<details>
<summary>Show Answer</summary>

**Answer: C. Typha**

**Explanation:**
Typha is an essential component for large clusters (50+ nodes):
- Aggregates datastore (etcd/Kubernetes API) connections
- Provides cached data to Felix
- Reduces API server load
- Felix instances receive data through Typha instead of connecting directly to API server

Operating large clusters without Typha can overload the API server.

</details>

### 3. What is the behavior of the CrossSubnet option in Calico's IPIP mode?

A. Always uses IPIP encapsulation
B. Uses IPIP encapsulation only within the same subnet
C. Uses IPIP encapsulation only for traffic to different subnets
D. Completely disables IPIP encapsulation

<details>
<summary>Show Answer</summary>

**Answer: C. Uses IPIP encapsulation only for traffic to different subnets**

**Explanation:**
IPIP mode options:
- **Always**: IPIP encapsulation for all Pod-to-Pod traffic
- **CrossSubnet**: Encapsulation only for traffic to different subnets (direct routing within same subnet)
- **Never**: Disable IPIP, use BGP direct routing

CrossSubnet is useful in hybrid environments - direct communication without overhead within the same L2 domain, encapsulation to other subnets.

</details>

### 4. What is the correct difference between Calico GlobalNetworkPolicy and NetworkPolicy?

A. GlobalNetworkPolicy applies to a specific namespace, while NetworkPolicy applies cluster-wide
B. GlobalNetworkPolicy applies cluster-wide, while NetworkPolicy applies to a specific namespace
C. GlobalNetworkPolicy only supports Ingress rules, while NetworkPolicy only supports Egress rules
D. GlobalNetworkPolicy and NetworkPolicy provide identical functionality

<details>
<summary>Show Answer</summary>

**Answer: B. GlobalNetworkPolicy applies cluster-wide, while NetworkPolicy applies to a specific namespace**

**Explanation:**
Calico Policy types:
- **NetworkPolicy**: Applies to Pods within a specific namespace. Namespace scoped.
- **GlobalNetworkPolicy**: Applies cluster-wide. Cluster scoped. Can also apply to Host Endpoints.

GlobalNetworkPolicy use cases:
- Default Deny policy
- DNS allow policy
- Monitoring system access

</details>

### 5. What is the purpose of Tier-based policies in Calico?

A. To group policies by namespace
B. To layer policies to define evaluation order and separate management permissions
C. To filter policies by Pod labels
D. To improve policy enforcement performance

<details>
<summary>Show Answer</summary>

**Answer: B. To layer policies to define evaluation order and separate management permissions**

**Explanation:**
Purposes of Tier-based policies:
1. **Define evaluation order**: Lower order Tiers are evaluated first
2. **Separate management permissions**: Assign Tiers to Security team, Platform team, Application team
3. **Pass action**: Don't decide in current Tier, pass to next Tier

Typical Tier configuration:
- Security Tier (order: 100) - Block malicious IPs
- Platform Tier (order: 200) - Allow monitoring, logging
- Application Tier (order: 300) - App-specific rules

</details>

### 6. What is the purpose of NetworkSet in Calico?

A. To group multiple namespaces together
B. To define a set of IP addresses for reuse in multiple policies
C. To configure network interfaces
D. To limit Pod network bandwidth

<details>
<summary>Show Answer</summary>

**Answer: B. To define a set of IP addresses for reuse in multiple policies**

**Explanation:**
NetworkSet defines a set of IP addresses or CIDR blocks:

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-databases
  labels:
    service-type: database
spec:
  nets:
    - 10.0.100.10/32
    - 10.0.100.11/32
```

Reference in Policy:
```yaml
destination:
  selector: service-type == 'database'
```

Use cases:
- Managing external service IPs
- Partner/trusted IP lists
- Abstracting repeated IP addresses in policies

</details>

### 7. What is the reason for using BGP Route Reflector in Calico?

A. To reduce CPU usage on each node
B. To reduce the number of full-mesh BGP connections and improve scalability
C. To allocate more IP addresses to Pods
D. To speed up Network Policy evaluation

<details>
<summary>Show Answer</summary>

**Answer: B. To reduce the number of full-mesh BGP connections and improve scalability**

**Explanation:**
Problems with BGP Full-mesh:
- N nodes require N×(N-1)/2 connections
- 100 nodes = 4,950 connections
- Scalability issues in large clusters

With Route Reflector:
- Each node only connects to Route Reflectors
- Route Reflector propagates route information
- Significant reduction in connections (N → 2×RR count)

Typically 2-3 Route Reflectors are configured for availability.

</details>

### 8. Which is NOT an advantage of Calico eBPF mode?

A. Higher throughput compared to iptables
B. Can replace kube-proxy
C. Full Windows container support
D. Reduced CPU usage

<details>
<summary>Show Answer</summary>

**Answer: C. Full Windows container support**

**Explanation:**
Advantages of Calico eBPF mode:
- 20-40% higher throughput compared to iptables
- 20-30% lower latency
- Consistent performance (regardless of rule count)
- Replaces kube-proxy for Service handling
- Direct Server Return (DSR) support

Limitations:
- Requires Linux kernel 5.3+ (recommended 5.8+)
- eBPF is not supported on Windows
- Possible compatibility issues with some older kernel features

</details>

### 9. What is the recommended configuration when using Calico on EKS?

A. Use Calico for both CNI and Network Policy
B. AWS VPC CNI for networking, Calico for Network Policy
C. Calico as CNI, AWS VPC CNI for Network Policy
D. Don't use Calico and AWS VPC CNI together

<details>
<summary>Show Answer</summary>

**Answer: B. AWS VPC CNI for networking, Calico for Network Policy**

**Explanation:**
Recommended configuration on EKS:
1. **AWS VPC CNI**: Handles Pod networking
   - VPC native IP allocation
   - Leverage AWS network features (Security Groups, Flow Logs, etc.)

2. **Calico**: Handles Network Policy
   - Advanced policy features (GlobalNetworkPolicy, NetworkSet, Tiers)
   - DNS-based policies
   - Detailed policy logging

Installation:
```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico-policy-only.yaml
```

</details>

### 10. What is the behavior of the following policy in Calico?

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny
spec:
  selector: all()
  types:
    - Ingress
    - Egress
```

A. Allow all traffic
B. Deny only all Ingress traffic
C. Deny only all Egress traffic
D. Deny all Ingress and Egress traffic

<details>
<summary>Show Answer</summary>

**Answer: D. Deny all Ingress and Egress traffic**

**Explanation:**
Analysis of this policy:
- `selector: all()` - Applies to all Pods
- `types: [Ingress, Egress]` - Controls both directions
- No rules - Denies all traffic without explicit allow (default deny)

This is the foundational policy for Zero Trust networking. After applying this policy, additional policies are needed to explicitly allow required traffic:
- Allow DNS traffic
- Allow communication between specific services
- Allow monitoring system access

</details>

### 11. How do you check BGP status on a node using calicoctl?

A. `calicoctl get bgppeer`
B. `calicoctl node status`
C. `calicoctl show bgp`
D. `calicoctl describe node`

<details>
<summary>Show Answer</summary>

**Answer: B. `calicoctl node status`**

**Explanation:**
Key calicoctl commands:
- `calicoctl node status` - Check node's BGP peering status
- `calicoctl get bgppeer` - List BGPPeer resources
- `calicoctl get node -o wide` - Detailed node information
- `calicoctl ipam show` - IPAM blocks and IP allocation status

Example `calicoctl node status` output:
```
Calico process is running.
IPv4 BGP status
+--------------+-------------------+-------+----------+-------------+
| PEER ADDRESS |     PEER TYPE     | STATE |  SINCE   |    INFO     |
+--------------+-------------------+-------+----------+-------------+
| 192.168.1.2  | node-to-node mesh | up    | 10:15:00 | Established |
| 192.168.1.3  | node-to-node mesh | up    | 10:15:05 | Established |
+--------------+-------------------+-------+----------+-------------+
```

</details>

### 12. What is the correct comparison between Calico VXLAN and IPIP modes?

A. IPIP has larger overhead (50 bytes), VXLAN has smaller overhead (20 bytes)
B. IPIP has smaller overhead (20 bytes), VXLAN has larger overhead (50 bytes)
C. IPIP and VXLAN have identical overhead
D. IPIP is UDP-based, VXLAN is IP protocol 4-based

<details>
<summary>Show Answer</summary>

**Answer: B. IPIP has smaller overhead (20 bytes), VXLAN has larger overhead (50 bytes)**

**Explanation:**
| Characteristic | IPIP | VXLAN |
|----------------|------|-------|
| Overhead | 20 bytes | 50 bytes |
| Base Protocol | IP protocol 4 | UDP |
| Performance | Better | Slightly lower |
| Azure Support | Limited | Supported |
| Hardware Offload | Limited | Widely supported |

IPIP has better performance, but VXLAN has better compatibility in some cloud environments (especially Azure).

</details>

---

## Additional Learning Resources

- [Calico Official Documentation](https://docs.tigera.io/calico/latest/about/)
- [Calico Network Policy Reference](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [BGP Configuration Guide](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
