# Part 7: Advanced Calico Topics

> **Supported Versions**: Calico v3.29+ / Kubernetes 1.28+
> **Last Updated**: February 23, 2026

## Overview

This chapter covers advanced Calico topics for production environments, including IPAM deep dive, WireGuard encryption, Egress Gateway, multi-cluster federation, Windows container support, and large-scale cluster design patterns.

![A sequential overview flow of six advanced Calico topics covered in this chapter: IPAM internals, WireGuard encryption, Egress Gateway, multi-cluster federation, Windows support, and large-scale cluster design.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-11.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-11.html)

## IPAM Deep Dive

Calico's IP Address Management (IPAM) system is designed for high performance and scalability. Understanding its architecture is crucial for optimizing large deployments.

### Block-Based IPAM Architecture

Calico uses a block-based IPAM system where IP addresses are allocated in blocks (default /26 = 64 IPs) to nodes. This approach minimizes datastore interactions and improves allocation speed.

![The datastore hands out fixed-size /26 blocks from the IPPool 10.244.0.0/16 to each node, and each node allocates individual pod IPs out of its own affine blocks, receiving another block when one is exhausted.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-0.html)

### IP Block Affinity

Block affinity ensures that IP blocks are preferentially allocated to specific nodes, improving routing efficiency and reducing route table size.

```yaml
# View block affinities
# calicoctl get blockaffinity -o yaml

apiVersion: projectcalico.org/v3
kind: BlockAffinity
metadata:
  name: node1-10-244-0-0-26
spec:
  cidr: 10.244.0.0/26
  node: node1
  state: confirmed
  # States: pending, confirmed, pendingDeletion
---
apiVersion: projectcalico.org/v3
kind: BlockAffinity
metadata:
  name: node1-10-244-0-64-26
spec:
  cidr: 10.244.0.64/26
  node: node1
  state: confirmed
```

### Allocation Algorithm

The IPAM allocation follows this process:

![On pod creation, Calico tries the node's own affine block first, then claims an unclaimed block from the pool, then borrows from another node's block, and only fails when no free IP exists anywhere.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-1.html)

### Block Size Configuration

The default block size is /26 (64 IPs). Adjust based on your cluster characteristics:

```yaml
# IPPool with custom block size
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv4-ippool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26  # Default: /26 (64 IPs per block)
  # Options:
  # /24 = 256 IPs (large pods per node)
  # /26 = 64 IPs (default, balanced)
  # /28 = 16 IPs (many nodes, few pods each)
  # /29 = 8 IPs (minimum recommended)
  # /30 = 4 IPs (not recommended)
  ipipMode: CrossSubnet
  vxlanMode: Never
  natOutgoing: true
  nodeSelector: all()
```

**Block Size Selection Guidelines:**

| Block Size | IPs per Block | Recommended Scenario |
|------------|---------------|---------------------|
| /24 | 256 | High pod density (50+ pods/node) |
| /25 | 128 | Medium-high density |
| /26 | 64 | Default, balanced |
| /27 | 32 | Many nodes, moderate pods |
| /28 | 16 | Large cluster, low density |
| /29 | 8 | Very large cluster, minimal pods |

### Host-Local IPAM

For simpler deployments or specific use cases, Calico supports host-local IPAM mode:

```yaml
# Installation with host-local IPAM
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: VXLANCrossSubnet
        natOutgoing: Enabled
    # Use host-local IPAM instead of Calico IPAM
    hostLocalIPAMEnabled: true
```

**Calico IPAM vs Host-Local IPAM:**

| Feature | Calico IPAM | Host-Local IPAM |
|---------|-------------|-----------------|
| IP Reuse | Cluster-wide | Node-local |
| Block Management | Dynamic | Static |
| Route Aggregation | Yes | Limited |
| IP Release | Immediate | Delayed |
| Complexity | Higher | Lower |
| Scalability | Better | Limited |

### Multi-Pool Strategy

Configure multiple IP pools for different workload types:

```yaml
# Production workloads pool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: production-pool
spec:
  cidr: 10.244.0.0/18
  blockSize: 26
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: "node-type == 'production'"
---
# Development workloads pool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: development-pool
spec:
  cidr: 10.244.64.0/18
  blockSize: 28  # Smaller blocks for dev
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: "node-type == 'development'"
---
# High-performance pool (no encapsulation)
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: highperf-pool
spec:
  cidr: 10.244.128.0/18
  blockSize: 26
  ipipMode: Never
  vxlanMode: Never
  natOutgoing: false
  nodeSelector: "network == 'direct'"
```

**Assigning Pods to Specific Pools:**

```yaml
# Pod annotation to select IP pool
apiVersion: v1
kind: Pod
metadata:
  name: production-app
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
spec:
  containers:
    - name: app
      image: nginx
---
# Namespace-level pool assignment
apiVersion: v1
kind: Namespace
metadata:
  name: production
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
```

### IPv6 and Dual-Stack Configuration

Calico supports IPv6-only and dual-stack deployments:

```yaml
# Dual-stack IPPool configuration
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: all()
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv6-pool
spec:
  cidr: fd00:10:244::/48
  blockSize: 122  # /122 = 64 IPv6 addresses
  ipipMode: Never  # IPIP not supported for IPv6
  vxlanMode: CrossSubnet
  natOutgoing: true
  nodeSelector: all()
```

```yaml
# FelixConfiguration for dual-stack
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  ipv6Support: true
  # IPv6 auto-detection
  ipAutoDetectionMethod: "kubernetes-internal-ip"
  ip6AutoDetectionMethod: "kubernetes-internal-ip"
```

### IP Exhaustion Strategies

When IP addresses become scarce, implement these strategies:

```yaml
# 1. Enable strict block affinity release
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Release unused blocks faster
  ipamAutoGC: true
  # Garbage collection interval
  # ipamAutoGCInterval: "5m"
---
# 2. Configure node-specific IP limits
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: limited-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  # Limit blocks per node
  allowedUses:
    - Workload
  # Disable tunnel addresses from this pool
  disableBGPExport: false
```

```bash
# Monitor IP usage
calicoctl ipam show

# Show detailed block allocation
calicoctl ipam show --show-blocks

# Check for leaked IPs
calicoctl ipam check

# Release orphaned IPs
calicoctl ipam release --ip=10.244.1.5

# Show IP usage per node
calicoctl ipam show --show-blocks | grep -E "Node|Block"
```

## Querying Per-Node PodCIDRs via BlockAffinity

In Calico's block-based IPAM, the CIDR block allocated to each node is tracked via **BlockAffinity CRs**. These CRs are used to identify per-node pod CIDRs for static route configuration or IPAM debugging.

> **⚠ EKS Hybrid Nodes Note**: Calico is **no longer officially supported** on EKS Hybrid Nodes. Use [Cilium](../cilium/04-ipam-policy.md) for new deployments. The information below is provided for reference in existing Calico environments.

### Querying BlockAffinity CRs

```bash
# Query IPAM blocks using calicoctl
calicoctl ipam show --show-blocks

# Check per-node CIDRs via BlockAffinity CRs
kubectl get blockaffinities

# Table format query
kubectl get blockaffinities -o custom-columns='\
NAME:.metadata.name,\
CIDR:.spec.cidr,\
NODE:.spec.node'
```

Example output:

```
NAME                                    CIDR               NODE
hybrid-node-001-10-85-0-0-25            10.85.0.0/25       hybrid-node-001
hybrid-node-002-10-85-0-128-25          10.85.0.128/25     hybrid-node-002
hybrid-node-003-10-85-1-0-25            10.85.1.0/25       hybrid-node-003
```

### Checking the Overall IPPool

```bash
kubectl get ippools -o custom-columns='\
NAME:.metadata.name,\
CIDR:.spec.cidr,\
BLOCK_SIZE:.spec.blockSize'
```

### Auto-Generating Static Routes

Example of generating static route commands from BlockAffinity:

```bash
# Generate ip route commands from BlockAffinity
kubectl get blockaffinities -o json | jq -r \
  '.items[] | "ip route add \(.spec.cidr) via <NODE_IP_FOR_\(.spec.node)>"'
```

> **Use Case**: This information is used to configure static routes without BGP in EKS Hybrid Nodes environments. For details, see [EKS Hybrid Nodes - Network Configuration](../../eks-hybrid-nodes/02-network-configuration.md).

## WireGuard Encryption

WireGuard provides efficient encryption for pod-to-pod traffic across nodes.

### WireGuard Architecture

![Traffic leaves Pod A in plaintext, is encrypted by Node 1's WireGuard interface (wireguard.cali), crosses the underlay from eth0 to eth0 as an encrypted UDP 51820 WireGuard tunnel, and is decrypted by Node 2's WireGuard interface back to plaintext before reaching Pod B.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-2.html)

### Configuration

```yaml
# Enable WireGuard encryption
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Enable WireGuard for IPv4
  wireguardEnabled: true

  # Enable WireGuard for IPv6 (if using dual-stack)
  wireguardEnabledV6: true

  # WireGuard interface MTU (default: auto)
  wireguardMTU: 1440

  # WireGuard listen port
  wireguardListeningPort: 51820

  # Keep-alive interval for NAT traversal
  wireguardPersistentKeepAlive: "25s"

  # Host encryption (encrypt host-networked pod traffic)
  wireguardHostEncryptionEnabled: true
```

```yaml
# Operator-based installation with WireGuard
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: WireguardCrossSubnet
        natOutgoing: Enabled
```

### Verify WireGuard Status

```bash
# Check WireGuard status on nodes
kubectl exec -n calico-system -it $(kubectl get pods -n calico-system -l k8s-app=calico-node -o name | head -1) -- wg show

# Sample output:
# interface: wireguard.cali
#   public key: ABC123...
#   private key: (hidden)
#   listening port: 51820
#
# peer: DEF456...
#   endpoint: 192.168.1.11:51820
#   allowed ips: 10.244.1.0/26
#   latest handshake: 5 seconds ago
#   transfer: 1.5 MiB received, 2.3 MiB sent

# Check Felix WireGuard statistics
calicoctl node status

# View WireGuard public keys
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}: {.metadata.annotations.projectcalico\.org/WireguardPublicKey}{"\n"}{end}'
```

### Performance Impact

| Metric | Without Encryption | WireGuard | IPsec (AES-GCM) |
|--------|-------------------|-----------|-----------------|
| Throughput | Baseline | -5 to -10% | -15 to -25% |
| Latency | Baseline | +0.1-0.3ms | +0.5-1.0ms |
| CPU Usage | Baseline | +10-15% | +30-50% |
| Setup Complexity | N/A | Low | Medium |
| Key Management | N/A | Automatic | Manual/IKE |

### WireGuard vs IPsec Comparison

![Side-by-side comparison of WireGuard and IPsec encryption on four traits: cryptography, code complexity, key exchange, and per-packet overhead.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-10.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-10.html)

| Feature | WireGuard | IPsec |
|---------|-----------|-------|
| Cryptography | ChaCha20-Poly1305, Curve25519 | AES-GCM, SHA-256, DH |
| Code Complexity | ~4,000 lines | 100,000+ lines |
| Attack Surface | Minimal | Large |
| Key Rotation | Automatic | Manual or IKE |
| NAT Traversal | Built-in | Requires NAT-T |
| Roaming | Seamless | Session re-establishment |
| Kernel Support | 5.6+ (mainline) | All versions |
| Hardware Offload | Limited | Widely supported |

## Egress Gateway

Egress Gateway provides controlled, predictable egress for pods requiring specific source IPs.

### Architecture

![Pods in the secure namespace send outbound traffic through designated Egress Gateway nodes that present fixed source IPs 203.0.113.10-11 to an external service whose firewall allows only those IPs, while a Pod in the default namespace exits directly.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-3.html)

### Configuration

```yaml
# 1. Label egress gateway nodes
# kubectl label node egress-node-1 egress-gateway=true
# kubectl label node egress-node-2 egress-gateway=true

# 2. Create Egress Gateway IP Pool
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: egress-gateway-pool
spec:
  cidr: 203.0.113.0/28
  blockSize: 32
  nodeSelector: "!all()"  # Don't auto-assign
  allowedUses:
    - Workload
  natOutgoing: false
---
# 3. Create Egress Gateway deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: egress-gateway
  namespace: calico-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: egress-gateway
  template:
    metadata:
      labels:
        app: egress-gateway
      annotations:
        cni.projectcalico.org/ipv4pools: '["egress-gateway-pool"]'
    spec:
      nodeSelector:
        egress-gateway: "true"
      tolerations:
        - key: "egress-gateway"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"
      containers:
        - name: egress-gateway
          image: calico/egress-gateway:v3.29.0
          env:
            - name: EGRESS_POD_IP
              valueFrom:
                fieldRef:
                  fieldPath: status.podIP
          securityContext:
            privileged: true
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
# 4. Configure egress gateway selector
apiVersion: projectcalico.org/v3
kind: EgressGateway
metadata:
  name: production-egress
  namespace: production
spec:
  # Select egress gateway pods
  selector: app == 'egress-gateway'
  # Maximum gateways per client (for HA)
  maxGatewaysPerClient: 2
```

### SNAT Policy Configuration

```yaml
# Egress IP policy for specific namespaces
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceExternalIPs:
    - cidr: 203.0.113.0/28
---
# Network policy to route through egress gateway
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: use-egress-gateway
  namespace: production
spec:
  selector: requires-egress == 'true'
  egress:
    - action: Allow
      destination:
        notNets:
          - 10.0.0.0/8
          - 172.16.0.0/12
          - 192.168.0.0/16
      # Route through egress gateway
```

### Compliance Use Case

Organizations with compliance requirements (PCI-DSS, HIPAA) often need predictable egress IPs:

```yaml
# Compliance-focused egress configuration
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: compliance-egress
spec:
  selector: "compliance-level in {'pci', 'hipaa'}"
  order: 100
  egress:
    # Allow only through egress gateway
    - action: Allow
      destination:
        selector: app == 'egress-gateway'
    # Block direct external access
    - action: Deny
      destination:
        notNets:
          - 10.0.0.0/8
```

## Multi-Cluster Federation

Calico supports multi-cluster deployments for cross-cluster communication and policy.

### Federation Architecture

![Typha-based multi-cluster federation in which each cluster's Felix agents connect to their own Typha instances and one lead Typha per cluster reports state up to a single shared Federation Controller.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-4.html)

### Cross-Cluster Connectivity Setup

```yaml
# Cluster A configuration
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: cluster-a-pool
spec:
  cidr: 10.244.0.0/16
  ipipMode: CrossSubnet
  natOutgoing: true
---
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false
---
# BGP peer to Cluster B
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: cluster-b-peer
spec:
  peerIP: 192.168.2.1  # Cluster B border router
  asNumber: 64513
  password:
    secretKeyRef:
      name: bgp-secrets
      key: cluster-b-password
```

```yaml
# Cluster B configuration
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: cluster-b-pool
spec:
  cidr: 10.245.0.0/16
  ipipMode: CrossSubnet
  natOutgoing: true
---
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64513
  nodeToNodeMeshEnabled: false
---
# BGP peer to Cluster A
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: cluster-a-peer
spec:
  peerIP: 192.168.1.1  # Cluster A border router
  asNumber: 64512
  password:
    secretKeyRef:
      name: bgp-secrets
      key: cluster-a-password
```

### Cross-Cluster Network Policy

```yaml
# Global policy that applies across clusters
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: cross-cluster-allow
spec:
  selector: all()
  order: 500
  ingress:
    # Allow from other clusters' pod CIDRs
    - action: Allow
      source:
        nets:
          - 10.244.0.0/16  # Cluster A
          - 10.245.0.0/16  # Cluster B
          - 10.246.0.0/16  # Cluster C
      protocol: TCP
      destination:
        ports:
          - 80
          - 443
          - 8080
  egress:
    - action: Allow
      destination:
        nets:
          - 10.244.0.0/16
          - 10.245.0.0/16
          - 10.246.0.0/16
```

## Windows Container Support

Calico provides networking and policy for Windows containers in Kubernetes.

### Features and Limitations

| Feature | Linux | Windows |
|---------|-------|---------|
| Overlay (VXLAN) | Yes | Yes |
| Direct Routing | Yes | Limited |
| BGP | Yes | Yes |
| Network Policy L3-L4 | Yes | Yes |
| Network Policy L7 | Yes | No |
| eBPF Dataplane | Yes | No |
| WireGuard | Yes | No |
| IPsec | Yes | Yes |
| Host Endpoint Policy | Yes | Limited |
| IPAM | Full | Full |

### Windows Installation

```yaml
# Installation resource for Windows support
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  # Kubernetes provider
  kubernetesProvider: AKS  # or EKS, GKE, etc.

  # Windows dataplane
  windowsDataplane: HNS

  calicoNetwork:
    bgp: Enabled
    ipPools:
      - cidr: 10.244.0.0/16
        encapsulation: VXLAN
        natOutgoing: Enabled

    # Windows-specific settings
    windowsIPAM: Calico
```

### HNS (Host Networking Service) Integration

![On a Windows node, traffic from the Windows containers converges on the Host Networking Service (HNS), which the Calico Node Windows Service programs with networking and policy, then passes through the Virtual Filtering Platform (VFP) for packet filtering before leaving via the physical NIC.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-7.html)

### Windows Network Policy

```yaml
# Network policy for Windows workloads
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: windows-web-policy
  namespace: windows-apps
spec:
  selector: app == 'iis-web'
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'load-balancer'
      destination:
        ports:
          - 80
          - 443
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'sql-server'
        ports:
          - 1433
```

### Hybrid Linux/Windows Cluster

```yaml
# Separate IP pools for Linux and Windows
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: linux-pool
spec:
  cidr: 10.244.0.0/17
  ipipMode: CrossSubnet
  natOutgoing: true
  nodeSelector: "kubernetes.io/os == 'linux'"
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: windows-pool
spec:
  cidr: 10.244.128.0/17
  vxlanMode: Always  # Windows requires VXLAN
  natOutgoing: true
  nodeSelector: "kubernetes.io/os == 'windows'"
```

## Calico Enterprise / Tigera

Tigera offers Calico Enterprise with additional features for enterprise deployments.

### OSS vs Enterprise Comparison

| Feature | Calico OSS | Calico Enterprise |
|---------|-----------|-------------------|
| **Networking** | | |
| CNI Plugin | Yes | Yes |
| BGP Routing | Yes | Yes |
| VXLAN/IPIP Overlay | Yes | Yes |
| eBPF Dataplane | Yes | Yes |
| WireGuard Encryption | Yes | Yes |
| Egress Gateway | Basic | Advanced |
| **Network Policy** | | |
| Kubernetes NetworkPolicy | Yes | Yes |
| Calico NetworkPolicy | Yes | Yes |
| GlobalNetworkPolicy | Yes | Yes |
| Policy Tiers | Yes | Yes |
| DNS Policy | Yes | Yes |
| L7 Policy (HTTP) | Basic | Full |
| Policy Preview | No | Yes |
| Policy Recommendations | No | Yes |
| **Security** | | |
| Threat Detection | No | Yes |
| Anomaly Detection | No | Yes |
| Compliance Reports | No | Yes |
| Security Alerts | No | Yes |
| Workload Identity | Basic | SPIFFE/SPIRE |
| **Observability** | | |
| Flow Logs | Basic | Full |
| Service Graph | No | Yes |
| Kibana Dashboards | No | Yes |
| DNS Logs | Basic | Full |
| L7 Logs | No | Yes |
| **Operations** | | |
| Web UI | No | Yes |
| Multi-Cluster Management | Manual | Unified |
| RBAC | Kubernetes | Extended |
| Audit Logs | Basic | Full |
| **Support** | | |
| Community Support | Yes | Yes |
| Enterprise Support | No | 24/7 SLA |
| Professional Services | No | Yes |

### Calico Cloud

Calico Cloud is a SaaS offering that provides:

![Each customer cluster's Calico agent reports to a shared Management UI, which feeds an Analytics Engine that in turn drives threat intelligence and compliance reporting.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-8.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-8.html)

## Large-Scale Cluster Design (1000+ Nodes)

Designing Calico for large clusters requires careful planning of components and resources.

### Typha Sizing Formula

Typha reduces API server load by aggregating datastore connections:

```
Typha Replicas = max(3, ceil(Node Count / 200))

Examples:
- 100 nodes: 3 Typha replicas (minimum)
- 500 nodes: 3 Typha replicas
- 1000 nodes: 5 Typha replicas
- 2000 nodes: 10 Typha replicas
- 5000 nodes: 25 Typha replicas
```

```yaml
# Large cluster Typha configuration
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  typhaDeployment:
    spec:
      replicas: 10  # For ~2000 nodes
      template:
        spec:
          containers:
            - name: calico-typha
              resources:
                requests:
                  cpu: 500m
                  memory: 512Mi
                limits:
                  cpu: 2000m
                  memory: 1Gi
          affinity:
            podAntiAffinity:
              requiredDuringSchedulingIgnoredDuringExecution:
                - labelSelector:
                    matchLabels:
                      k8s-app: calico-typha
                  topologyKey: kubernetes.io/hostname
          topologySpreadConstraints:
            - maxSkew: 1
              topologyKey: topology.kubernetes.io/zone
              whenUnsatisfiable: DoNotSchedule
              labelSelector:
                matchLabels:
                  k8s-app: calico-typha
```

### Route Reflector Topology

For large BGP deployments, use Route Reflectors instead of full mesh:

![Route Reflector hierarchy for 1000+ nodes: three Tier 1 Route Reflectors peer with each other in an iBGP full mesh, and each reflects routes down to its own rack RR and worker node group instead of a full node-to-node mesh.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-6.html)

```yaml
# Route Reflector node configuration
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-1
  labels:
    route-reflector: "true"
    topology.kubernetes.io/zone: "zone-a"
spec:
  bgp:
    routeReflectorClusterID: 244.0.0.1
    ipv4Address: 192.168.1.10/24
---
# Regular nodes peer with zone-local RR
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: node-to-rr-zone-a
spec:
  nodeSelector: "topology.kubernetes.io/zone == 'zone-a' && !has(route-reflector)"
  peerSelector: "route-reflector == 'true' && topology.kubernetes.io/zone == 'zone-a'"
---
# RR mesh between zones
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rr-full-mesh
spec:
  nodeSelector: "has(route-reflector)"
  peerSelector: "has(route-reflector)"
```

### Felix Tuning for Large Clusters

```yaml
# Optimized Felix configuration for large clusters
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # Reduce datastore polling
  datastoreType: kubernetes

  # Increase refresh intervals (reduce API load)
  routeRefreshInterval: "90s"
  iptablesRefreshInterval: "180s"
  ipSetsRefreshInterval: "90s"

  # Optimize iptables
  iptablesBackend: NFT  # Use nftables if available
  iptablesMarkMask: 0xffff0000

  # Reduce logging overhead
  logSeverityScreen: Warning
  logSeverityFile: Warning

  # Flow logs (if enabled, optimize)
  flowLogsFlushInterval: "60s"
  flowLogsFileAggregationKindForAllowed: 2
  flowLogsFileAggregationKindForDenied: 1

  # Health check optimization
  healthEnabled: true
  healthPort: 9099
  healthTimeoutOverrides:
    - name: "InternalDataplaneMainLoop"
      timeout: "120s"

  # BPF mode optimization (if using eBPF)
  bpfEnabled: true
  bpfConnectTimeLoadBalancingEnabled: true
  bpfExternalServiceMode: "DSR"
  bpfMapSizeConntrack: 512000
  bpfMapSizeNATFrontend: 65536
  bpfMapSizeNATBackend: 262144
  bpfMapSizeNATAffinity: 65536
```

### Datastore at Scale

```yaml
# etcd optimization for large Calico deployments
# (if using etcd datastore instead of Kubernetes)
apiVersion: v1
kind: ConfigMap
metadata:
  name: etcd-config
  namespace: kube-system
data:
  etcd.conf.yaml: |
    name: etcd-0
    data-dir: /var/lib/etcd

    # Increase quota for large deployments
    quota-backend-bytes: 8589934592  # 8GB

    # Snapshot tuning
    snapshot-count: 50000
    auto-compaction-mode: periodic
    auto-compaction-retention: "1h"

    # Performance tuning
    heartbeat-interval: 250
    election-timeout: 2500

    # Enable gRPC gateway
    enable-grpc-gateway: true
```

## Performance Tuning

### Felix Parameters

```yaml
# Comprehensive Felix performance tuning
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  # === CPU Optimization ===
  # Use eBPF for better CPU efficiency
  bpfEnabled: true
  bpfDisableUnprivileged: true

  # Batch iptables updates
  iptablesPostWriteCheckIntervalSecs: 5
  iptablesLockFilePath: "/run/xtables.lock"
  iptablesLockTimeoutSecs: 30
  iptablesLockProbeIntervalMillis: 50

  # === Memory Optimization ===
  # Limit in-memory caches
  routeTableRanges:
    - min: 1
      max: 250

  # === Network Optimization ===
  # MTU configuration
  mtuIfacePattern: "^(en.*|eth.*|bond.*)"

  # Failsafe inbound/outbound ports
  failsafeInboundHostPorts:
    - protocol: tcp
      port: 22
    - protocol: udp
      port: 68
  failsafeOutboundHostPorts:
    - protocol: tcp
      port: 443
    - protocol: udp
      port: 53

  # === Logging Optimization ===
  logFilePath: "/var/log/calico/felix.log"
  logSeverityFile: Warning
  logSeverityScreen: Warning
  logSeveritySys: Warning

  # === Health Check Optimization ===
  healthEnabled: true
  healthPort: 9099
  healthHost: "0.0.0.0"
```

### Typha Ratio and Configuration

```yaml
# Typha deployment for optimal performance
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calico-typha
  namespace: calico-system
spec:
  replicas: 5  # Adjust based on cluster size
  selector:
    matchLabels:
      k8s-app: calico-typha
  template:
    metadata:
      labels:
        k8s-app: calico-typha
    spec:
      priorityClassName: system-cluster-critical
      tolerations:
        - key: CriticalAddonsOnly
          operator: Exists
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  k8s-app: calico-typha
              topologyKey: kubernetes.io/hostname
      containers:
        - name: calico-typha
          image: calico/typha:v3.29.0
          ports:
            - containerPort: 5473
              name: calico-typha
            - containerPort: 9093
              name: metrics
          env:
            - name: TYPHA_LOGSEVERITYSCREEN
              value: "warning"
            - name: TYPHA_DATASTORETYPE
              value: "kubernetes"
            # Max connections per Typha
            - name: TYPHA_MAXCONNECTIONSLOWERLIMIT
              value: "200"
            - name: TYPHA_MAXCONNECTIONSUPPERLIMIT
              value: "400"
            # Connection rebalancing
            - name: TYPHA_CONNECTIONREBALANCINGMODE
              value: "kubernetes"
            # Reduce sync interval
            - name: TYPHA_SNAPSHOTSYNCSINTERVAL
              value: "300s"
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 1000m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /liveness
              port: 9098
            periodSeconds: 30
            initialDelaySeconds: 30
            failureThreshold: 5
          readinessProbe:
            httpGet:
              path: /readiness
              port: 9098
            periodSeconds: 10
            failureThreshold: 3
```

### Resource Allocation Guidelines

| Cluster Size | Felix CPU | Felix Memory | Typha CPU | Typha Memory | Typha Replicas |
|--------------|-----------|--------------|-----------|--------------|----------------|
| < 50 nodes | 100m-250m | 128Mi-256Mi | N/A | N/A | 0 |
| 50-200 | 250m-500m | 256Mi-512Mi | 100m-250m | 128Mi-256Mi | 3 |
| 200-500 | 500m-1000m | 512Mi-1Gi | 250m-500m | 256Mi-512Mi | 3 |
| 500-1000 | 500m-1000m | 512Mi-1Gi | 500m-1000m | 512Mi-1Gi | 5 |
| 1000-2000 | 1000m-2000m | 1Gi-2Gi | 500m-1000m | 512Mi-1Gi | 10 |
| 2000+ | 1000m-2000m | 1Gi-2Gi | 1000m-2000m | 1Gi-2Gi | Node/200 |

---

## References

- [Calico IPAM Documentation](https://docs.tigera.io/calico/latest/networking/ipam/)
- [WireGuard Encryption](https://docs.tigera.io/calico/latest/network-policy/encrypt-cluster-pod-traffic)
- [Egress Gateway](https://docs.tigera.io/calico/latest/networking/egress/egress-gateway/)
- [Windows Containers](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/)
- [Calico Enterprise](https://docs.tigera.io/calico-enterprise/)
- [Performance Tuning](https://docs.tigera.io/calico/latest/operations/monitor/component-performance)

## Quiz

To test what you learned in this chapter, try the [Advanced Topics Quiz](../../quizzes/networking/calico/07-advanced-topics-quiz.md).
