# Cilium Service Mesh Architecture

> **Supported Versions**: Cilium 1.16+, Kubernetes 1.28+
> **Last Updated**: February 22, 2026

## Overview

The architecture of Cilium Service Mesh is fundamentally different from traditional sidecar-based service meshes. It leverages eBPF to process L3/L4 traffic at the kernel level and provides L7 functionality through a single shared Envoy proxy per node. This chapter explains the core architectural components and operations of Cilium Service Mesh in detail.

## Overall Architecture

![Architecture diagram showing how the Kubernetes control plane drives the per-node Cilium Agent and Operator, which program eBPF kernel datapath maps that intercept pod traffic and redirect L7 flows to a shared node-local Envoy proxy.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-0.html)

## eBPF Datapath

### What is eBPF?

eBPF (extended Berkeley Packet Filter) is a technology that enables running sandboxed programs within the Linux kernel. It allows implementing networking, security, and observability features without modifying the kernel.

![Diagram contrasting a traditional application-to-NIC path that always traverses the kernel network stack with an eBPF-based path where kernel-attached programs process packets directly and can bypass the stack.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-1.html)

### eBPF Hook Points

Cilium utilizes multiple eBPF hook points:

| Hook Point | Location | Purpose |
|------------|----------|---------|
| **XDP (eXpress Data Path)** | NIC Driver | Ultra-fast packet processing, DDoS protection |
| **TC (Traffic Control)** | Network Stack Entry | Packet filtering, redirection |
| **Socket Operations** | Socket Level | Socket connection acceleration |
| **cgroup** | Process Group | Resource control, policy enforcement |

![Diagram showing a packet's ingress path from the NIC through the XDP and TC Ingress eBPF hooks, the network stack and socket layer up to the application, and the egress path back down through the TC Egress hook to the NIC.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-2.html)

### L3/L4 Processing

L3/L4 processing in eBPF works as follows:

![Sequence diagram showing a packet from the source pod entering the TC eBPF hook, which looks up the CT map, evaluates policy only for a new connection or reuses the cached decision, then delivers the packet to the destination pod.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-3.html)

#### eBPF Map Structure

```c
// Connection Tracking Map
struct ct_entry {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8  protocol;
    __u64 lifetime;
    __u32 rx_packets;
    __u32 tx_packets;
};

// Service Map
struct lb_service {
    __u32 service_ip;
    __u16 service_port;
    __u32 backend_count;
    __u32 backend_slot;
};

// Policy Map
struct policy_entry {
    __u32 identity;
    __u16 port;
    __u8  protocol;
    __u8  action;  // ALLOW, DENY, AUDIT
};
```

### kube-proxy Replacement

Cilium's eBPF-based load balancer can completely replace kube-proxy:

```yaml
# Enable kube-proxy replacement during Cilium installation
kubeProxyReplacement: true

# Load balancer algorithm configuration
loadBalancer:
  algorithm: maglev  # or random
  mode: dsr          # Direct Server Return
```

**kube-proxy vs Cilium eBPF Comparison:**

| Feature | kube-proxy (iptables) | Cilium eBPF |
|---------|----------------------|-------------|
| Rule Complexity | O(n) - proportional to services | O(1) - hash map lookup |
| Connection Tracking | conntrack module | eBPF CT Map |
| DSR Support | Limited | Full support |
| Session Affinity | iptables-based | Maglev hashing |
| Performance | Medium | High |

## Per-Node Envoy Proxy

### Sidecar vs Node Proxy

![Side-by-side diagram contrasting the sidecar model, where each pod runs its own 50MB Envoy proxy, with the node proxy model, where three pods on a node share a single 100MB Envoy instance.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-4.html)

### Envoy Deployment Method

Cilium deploys one Envoy proxy per node as a DaemonSet:

```bash
# Check Envoy DaemonSet
kubectl get daemonset -n kube-system cilium-envoy

# Expected output
NAME           DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE
cilium-envoy   3         3         3       3            3
```

### L7 Processing Flow

![Sequence diagram showing a client HTTP request passing through the eBPF datapath, which conditionally redirects traffic to the node Envoy for L7 policy enforcement on both the request and response legs before the response reaches the client.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-5.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-5.html)

### Envoy Resource Configuration

```yaml
# values.yaml
envoy:
  enabled: true
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 100m
      memory: 256Mi

  # Envoy concurrent connection settings
  maxConnectionsPerHost: 1000
  connectTimeout: 5s

  # Proxy protocol settings
  proxy:
    protocol:
      http2:
        enabled: true
      tls:
        enabled: true
```

## CRD Model

### Cilium CRD Structure

![Architecture diagram grouping Cilium CRDs into network policy, Envoy configuration, service mesh, and identity groups, with the policy and Envoy configuration CRDs all resolving to the per-pod CiliumEndpoint beside CiliumIdentity.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-6.html)

### CiliumEnvoyConfig

CiliumEnvoyConfig defines namespace-scoped Envoy configuration:

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: http-filter
  namespace: default
spec:
  # Services this configuration applies to
  services:
  - name: my-service
    namespace: default

  # Envoy resource definitions
  resources:
  - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    name: my-service-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: my-service
          route_config:
            name: local_route
            virtual_hosts:
            - name: my-service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: default/my-service
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

### CiliumClusterwideEnvoyConfig

Cluster-wide Envoy configuration:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideEnvoyConfig
metadata:
  name: global-ratelimit
spec:
  # Apply to all services cluster-wide
  services:
  - name: "*"
    namespace: "*"

  resources:
  - "@type": type.googleapis.com/envoy.config.listener.v3.Listener
    name: global-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: global
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

### CiliumNetworkPolicy (L7)

Network policy with L7 rules:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend

  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
      rules:
        http:
        - method: GET
          path: "/api/v1/.*"
          headers:
          - name: "X-Request-ID"
            value: ".*"
        - method: POST
          path: "/api/v1/users"
        - method: DELETE
          path: "/api/v1/users/[0-9]+"

  egress:
  - toEndpoints:
    - matchLabels:
        app: database
    toPorts:
    - ports:
      - port: "5432"
        protocol: TCP
```

## Cilium Agent and Service Mesh

### Cilium Agent Role

![Architecture diagram showing the Kubernetes API server syncing into the Cilium Agent's network management, policy management, and proxy management groups, with network management feeding metrics and policy management feeding flow logs into the agent's observability output.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-7.html)

### Agent Configuration

```yaml
# ConfigMap: cilium-config
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  # Agent basic settings
  debug: "false"
  enable-ipv4: "true"
  enable-ipv6: "false"

  # Service mesh settings
  enable-l7-proxy: "true"
  enable-envoy-config: "true"

  # kube-proxy replacement
  kube-proxy-replacement: "true"

  # Observability
  enable-hubble: "true"
  hubble-listen-address: ":4244"
  hubble-metrics-server: ":9965"

  # Encryption
  enable-wireguard: "true"
  enable-ipsec: "false"
```

## Service Identity and SPIFFE

### Cilium Identity

Cilium assigns a unique identity to each workload:

![Diagram showing a pod's labels combining with its namespace and service account to derive a numeric Cilium Identity, which in turn sets the workload's security context.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-8.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-8.html)

### Identity-based Policy

```yaml
# Check Pod's Identity
apiVersion: cilium.io/v2
kind: CiliumIdentity
metadata:
  name: "12345"
  labels:
    app: frontend
    k8s:io.kubernetes.pod.namespace: default
spec:
  security-labels:
    k8s:app: frontend
    k8s:io.kubernetes.pod.namespace: default
```

```bash
# List identities
cilium identity list

# Expected output
ID      LABELS
1       reserved:host
2       reserved:world
3       reserved:health
12345   k8s:app=frontend,k8s:io.kubernetes.pod.namespace=default
12346   k8s:app=backend,k8s:io.kubernetes.pod.namespace=default
```

### SPIFFE Integration

Workload identity through SPIFFE (Secure Production Identity Framework for Everyone):

![Diagram showing a workload requesting identity through the SPIRE agent and server, which uses a certificate authority to issue an X.509 SVID that is delivered back to the workload.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-9.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-9.html)

```yaml
# SPIRE integration configuration
authentication:
  mutual:
    spire:
      enabled: true
      install:
        enabled: true
        server:
          dataStorage:
            size: 1Gi
        agent:
          socketPath: /run/spire/sockets/agent.sock
```

SPIFFE ID format:
```
spiffe://cluster.local/ns/<namespace>/sa/<service-account>
```

## Packet Flow Analysis

### Pod-to-Pod Communication (Same Node)

![Sequence diagram showing a packet moving entirely inside the kernel from a source pod's veth eBPF ingress TC hook, through the connection-tracking and policy maps, to the eBPF egress TC hook on the destination pod's veth on the same node, bypassing the network stack.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-10.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-10.html)

### Pod-to-Pod Communication (Different Nodes)

![A packet leaves a pod on one node, is policy-evaluated and encapsulated by that node's eBPF, crosses a VXLAN, Geneve, or native route, then is decapsulated and policy-evaluated by eBPF on the destination node before reaching the target pod.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-11.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-11.html)

### When L7 Processing is Required

![Sequence diagram of an L7-policy request redirected by the client-side eBPF hook to the node Envoy for HTTP parsing, policy enforcement and metrics, forwarded via the server-side eBPF hook, with the response taking the same detour back.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-12.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-12.html)

## Comparison with Istio Sidecar Architecture

### Architecture Comparison Table

| Aspect | Cilium Service Mesh | Istio Sidecar |
|--------|---------------------|---------------|
| **Proxy Location** | 1 per node | 1 per Pod |
| **Proxy Type** | eBPF + Envoy | Envoy only |
| **L4 Processing** | Kernel (eBPF) | User space (Envoy) |
| **L7 Processing** | User space (Envoy) | User space (Envoy) |
| **Memory Usage** | ~100MB/node | ~50MB/Pod |
| **CPU Usage** | Low | Medium-High |
| **Latency** | 0.1-0.5ms | 1-3ms |
| **Configuration Model** | CiliumEnvoyConfig | VirtualService/DestinationRule |
| **mTLS Implementation** | eBPF/WireGuard | Envoy |
| **Injection** | Not required | Sidecar injection required |

### Latency Analysis

![Per-hop latency breakdown showing Istio's sidecar path accumulating about 1.5 ms across two user-space Envoy hops, while Cilium's eBPF path completes the same round trip in about 0.24 ms with the network hop costing the same in both.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-13.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-13.html)

### Resource Efficiency Analysis

For a 100 Pod cluster:

![Diagram comparing resource use on a 100-pod cluster: Istio's per-pod sidecars total about 5GB of memory with high CPU overhead, while Cilium's five node-level Envoy proxies total about 500MB with low CPU overhead.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-01-architecture-14.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-01-architecture-14.html)

## Scalability Considerations

### eBPF Map Sizes

```yaml
# Cilium ConfigMap settings
bpf-map-dynamic-size-ratio: "0.0025"
bpf-ct-global-tcp-max: "524288"
bpf-ct-global-any-max: "262144"
bpf-nat-global-max: "524288"
bpf-policy-map-max: "16384"
```

### Large Cluster Configuration

```yaml
# Large cluster (1000+ nodes) configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  # Identity-related settings
  cluster-id: "1"
  cluster-name: "production"

  # Connection tracking optimization
  bpf-ct-global-tcp-max: "1048576"
  bpf-ct-global-any-max: "524288"

  # NAT table size
  bpf-nat-global-max: "1048576"

  # Policy map size
  bpf-policy-map-max: "65536"

  # Performance optimization
  sockops-enable: "true"
  bpf-lb-sock: "true"

  # Hubble settings
  hubble-disable: "false"
  hubble-socket-path: "/var/run/cilium/hubble.sock"
```

### Node Envoy Scaling

```yaml
# Envoy resource scaling
envoy:
  resources:
    limits:
      cpu: 4000m
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 512Mi

  # Envoy worker threads
  concurrency: 4

  # Connection limits
  perConnectionBufferLimitBytes: 32768

  # Cluster settings
  cluster:
    connectTimeout: 5s
    circuitBreakers:
      maxConnections: 10000
      maxPendingRequests: 10000
      maxRequests: 10000
```

## Next Steps

- [Traffic Management](./02-traffic-management.md): Configure L7 routing and traffic control
- [Security](./03-security.md): Set up mTLS and L7 network policies
- [Observability](./04-observability.md): Monitor service mesh with Hubble

## References

- [Cilium Architecture Documentation](https://docs.cilium.io/en/stable/concepts/overview/)
- [eBPF Documentation](https://ebpf.io/what-is-ebpf/)
- [Envoy Proxy Architecture](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview)
- [SPIFFE Specification](https://spiffe.io/docs/latest/spiffe-about/overview/)
