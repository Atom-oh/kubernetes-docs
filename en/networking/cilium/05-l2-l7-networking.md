# L2–L7 Networking and Load Balancing

> **Review baseline**: Cilium 1.20.1, CLI 0.20.0; Istio examples use the 1.31 API.
> **Last reviewed**: September 12, 2026

## Lab Environment Setup

Use a disposable cluster prepared through the [installation](README.md) and [networking](03-networking.md) guides. Check platform/kernel support and kubectl version skew. The HTTP lab needs two schedulable Linux nodes. The DSR/Maglev experiment additionally needs a prepared kube-proxy-free cluster, a reachable real API-server endpoint and a supported network path.

Choose complete installation values for the experiment. Repeated `cilium install --config ...` commands are not a live feature-migration procedure, and deleting kube-proxy after an arbitrary install is not a safe shortcut.

## Understanding the OSI Layers

OSI is a conceptual model, not seven Cilium processes or a fixed sequence of policy hooks.

| Layer | Role / examples | Cilium relationship |
|---|---|---|
| L1 physical | Bits, media, transceivers, repeaters | Underlying hardware/network requirements |
| L2 data link | Ethernet frames, MAC addressing, bridges/switches | Packet handling and explicitly configured L2 service announcements |
| L3 network | IP packets, routing, ICMP | Routing, identity/CIDR policy and supported fragment handling |
| L4 transport | TCP segments and reliable streams; UDP datagrams without delivery/order guarantees | Port/protocol policy, connection state, service translation |
| L5 session | Session/dialog organization | Conceptual functionality often implemented inside applications/protocols |
| L6 presentation | Representation, encoding and cryptographic transformations | TLS is often mapped here conceptually, not a universal separate Linux layer |
| L7 application | HTTP, DNS, gRPC and other application protocols | Supported proxy policies; an application protocol's existence does not imply a Cilium policy parser |

### Actual Layer-specific Features

- **L2:** L2 Announcements is a beta, configured ARP/NDP response mechanism for eligible Service IPs. It needs kube-proxy replacement and appropriate devices/local-network reachability. The elected node receives that Service's traffic; this is not arbitrary MAC/VLAN ACL support or a general L2 bridge/promise to capture every packet. `externalTrafficPolicy: Local` has a documented incompatibility.
- **L3:** IP/identity policy and routing have mode-specific requirements. Multicast is a separately enabled beta feature requiring VXLAN; the documented kernel minimum is 5.10 on AMD64 and 6.0 on AArch64. Do not assume it works in every routing mode.
- **L4:** TCP/UDP port policy, connection tracking, socket/packet service load balancing and supported affinity operate at different hooks. A socket decision can occur before packet construction.
- **L7:** Current built-in policy groups are HTTP and DNS. gRPC uses the supported HTTP/2 path. Kafka L7 rules are removed. TLS/SNI features require their documented proxy configuration; encrypted application content is not automatically inspectable.

HTTP/gRPC policy uses Envoy; DNS policy uses Cilium's DNS proxy. Envoy may be an agent-managed process or a dedicated `cilium-envoy` DaemonSet according to values/upgrade compatibility. Fresh 1.20 chart defaults with L7 enabled favor the DaemonSet, and the profile below sets it explicitly. Adding a policy does not override every installation setting.

## HTTP Policy Lab

Create a fresh namespace and matching workloads. The images/digests and known server readiness path come from the official CLI test deployment definitions.

```bash
set -euo pipefail
kubectl create namespace cilium-l2l7-demo
kubectl label namespace cilium-l2l7-demo docs-audit-lab=cilium-l2l7-05
```

Stop if the namespace already exists; choose a new name consistently instead of reusing another run's resources.

**`l7-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-l2l7-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-l2l7-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app1
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app1
  template:
    metadata:
      labels:
        app: app1
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: client
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: app1-service
  namespace: cilium-l2l7-demo
spec:
  selector:
    app: app1
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f l7-app.yaml
kubectl -n cilium-l2l7-demo wait --for=condition=Ready pod/client pod/outsider --timeout=120s
kubectl -n cilium-l2l7-demo rollout status deployment/app1 --timeout=120s
kubectl -n cilium-l2l7-demo get pods,services -o wide
kubectl -n cilium-l2l7-demo exec client -- \
  curl --fail --silent --show-error --max-time 5 http://app1-service/
```

Verify outsider baseline connectivity too. The Service exposes port 80, but its backend listens on **8080**; the Pod ingress policy uses the backend port. This replaces the nonexistent/unmatched older application setup and a client Pod whose default labels/entrypoint did not match the example.

**`app1-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: app1-http
  namespace: cilium-l2l7-demo
spec:
  endpointSelector:
    matchLabels:
      app: app1
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-l2l7-demo
        k8s:app: client
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/api/v1$
          headerMatches:
          - name: x-demo-tenant
            value: team-a
```


```bash
kubectl apply -f app1-http.yaml
kubectl -n cilium-l2l7-demo get cnp app1-http -o yaml
```

After policy realization, the named client can make GET `/` requests. POST `/api/v1` is permitted by this rule only with the exact `x-demo-tenant: team-a` header; the backend must still implement that API operation. Other methods/paths/peers are denied only insofar as no other applicable policy allows them. Verify realized policy and flow evidence as well as application responses.

The header is a **demonstration filter, not authentication**. The old 32-character “token” condition did not validate identity, signature, issuer, expiry or authorization. In the released translator, a `headers` string containing a value matches that value literally: `X-Auth-Token: ^[a-zA-Z0-9]{32}$` is not a regex token validator. Use explicit `headerMatches` for the intended exact/presence requirement, and authenticate users in the application/appropriate authentication layer.

Methods and paths support regular expressions. Built-in Cilium HTTP policy has no arbitrary request-body predicate. Header presence, exact equality, URL filtering and application authorization are different controls.

## Service Mesh Integration

Cilium supplies networking and supported network policy while Istio owns its configured proxies and mesh behavior. Integration does not automatically bypass Istio sidecars, remove their mTLS cost, unify all traces or guarantee faster requests.

```text
Configuration: istiod --> Istio Envoy proxies
Request: app --> source sidecar --> Cilium/network --> destination sidecar --> app
```

### Preserve Istio's Traffic Interception

The current Cilium integration guide offers kube-proxy coexistence and a carefully configured full-replacement option. A coexistence fragment is:

**`istio-cilium-values.yaml`**

```yaml
kubeProxyReplacement: false
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```


For an intentionally prepared full-replacement setup, `kubeProxyReplacement: true` additionally requires a reachable API endpoint and the replacement prerequisites. Keep `socketLB.hostNamespaceOnly: true` to avoid Pod socket translation bypassing Istio interception, and `cni.exclusive: false` when sharing the node CNI configuration.

Istio sidecar redirection can use an init container or the Istio CNI node agent; ambient uses its corresponding node/CNI path. Follow the [maintained Istio installation guide](../../service-mesh/istio/01-installation.md), selecting one mode. The Kubernetes API server must reach Istio's admission webhook. Managed-control-plane/overlay networks may need a documented routing or host-network solution; do not prescribe `istiod hostNetwork: true` for every overlay cluster.

### Retain mTLS and Assign L7 Responsibility

Do not apply plaintext Cilium HTTP inspection to Istio-encrypted workload traffic. This example keeps Istio mTLS and L7 routing in Istio, and uses Cilium **L3/L4-only** policy. Disabling mTLS just to make the old combined L7 example pass would change the security design.

The following is a **sidecar-mode** configuration for an already prepared `istio-cilium-demo` namespace with `productpage` and `reviews` workloads, a reviews Service on port 9080, and reviews Pods labeled `version: v1`/`v2`. It is not a complete Bookinfo deployment.

**`istio-reviews.yaml`**

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: istio-cilium-demo
spec:
  hosts:
  - reviews.istio-cilium-demo.svc.cluster.local
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v2
        port:
          number: 9080
  - route:
    - destination:
        host: reviews.istio-cilium-demo.svc.cluster.local
        subset: v1
        port:
          number: 9080
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: istio-cilium-demo
spec:
  host: reviews.istio-cilium-demo.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-cilium-demo
spec:
  mtls:
    mode: STRICT
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: reviews-l4
  namespace: istio-cilium-demo
spec:
  endpointSelector:
    matchLabels:
      app: reviews
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: istio-cilium-demo
        k8s:app: productpage
    toPorts:
    - ports:
      - port: '9080'
        protocol: TCP
```


The DestinationRule defines the subsets referenced by the VirtualService. The `end-user: jason` header selects a demo route; it is not authenticated identity. Verify successful sidecar injection, actual endpoint labels, subset readiness and mesh telemetry.

Do not reuse the 9080 Cilium rule as an ambient policy recipe: ambient HBONE uses encrypted tunneling on port 15008 and changes the visible traffic/identity boundary. Apply the appropriate Istio policy and platform-specific Cilium network guards for that topology.

## Load Balancing Architecture

Cilium's service maps, backend maps, reverse-NAT state and connection tracking support different forwarding stages. L7 Envoy load balancing is another component; do not merge its algorithm list with the BPF service datapath.

### BPF Forwarding Modes and Algorithms

| Setting / mechanism | Meaning and limits |
|---|---|
| `loadBalancer.mode: snat` | Default forwarding mode; applicable external service paths use source translation/reverse state rather than a direct-return path |
| `dsr` | Remote backend replies can bypass the ingress load-balancing node. The network must permit that return path; it cannot recover a client IP already translated by an upstream proxy |
| `hybrid` | TCP uses DSR and UDP uses SNAT. This is valid load-balancer behavior, distinct from the invalid tunnel/auto-direct-routing combination |
| Annotation-based forwarding | Supported opt-in per-Service behavior; forwarding annotations are creation-time choices and changing them can break connections |
| `loadBalancer.algorithm: random` | Default BPF backend-selection algorithm |
| `maglev` | Consistent selection for supported external N–S paths, including supported XDP acceleration; ordinary socket-LB E–W connections are not subject to Maglev |
| `sessionAffinity: ClientIP` | Separate Kubernetes Service affinity. The key is the external source IP or, for applicable in-cluster socket-LB traffic, the client's network-namespace cookie |

Maglev is not a guarantee that sessions survive backend removal. Nodes need consistent backend state, table size and seed. The default table size is 16381; 65521 used below is an allowed value, not a universal recommendation. Larger tables cost memory. Affinity expiry and connection state are separate from hashing.

DSR dispatch can use native-routing IP options, Geneve under documented native/Geneve-overlay configurations, or the documented native-only IPIP/IP6IP6 path. VXLAN overlay is not interchangeable with Geneve DSR dispatch. IPIP has its own port/translation constraints; verify the release guide before selecting it.

XDP acceleration needs supported devices/drivers. `native` expects the selected devices to support it; `best-effort` enables it where supported. It is not enabled simply by writing the old `enable-xdp-acceleration` key, and early XDP forwarding may not be visible at tcpdump's later capture point.

### Cilium and kube-proxy

| Aspect | Correct comparison |
|---|---|
| Linux service implementation | Cilium uses BPF hooks/maps; kube-proxy has iptables and nftables modes, plus IPVS deprecated since Kubernetes 1.35 |
| Platform | Cilium's stated Linux/kernel requirements apply; Windows kernelspace kube-proxy is a different implementation |
| Connection state | Cilium BPF connection/NAT state is distinct from Linux netfilter conntrack; “optional versus always” is too broad |
| L7 | Cilium integrates supported proxies; kube-proxy's Service forwarding is not an HTTP policy engine |
| Performance | Measure the same workload and configuration; neither product name establishes a fixed rank |

Do not infer kube-proxy DSR configuration merely because the underlying Linux IPVS subsystem has direct-routing capabilities.

## Prepared DSR/Maglev Lab

This profile is for a fresh, prepared kube-proxy-free **IPv4 Geneve-overlay** test cluster. It does not migrate an existing CNI, remove kube-proxy or configure cloud anti-spoofing/routing controls. Use a non-conflicting Pod CIDR and validate the external return path.

**`lb-values.yaml`**

```yaml
kubeProxyReplacement: true
routingMode: tunnel
tunnelProtocol: geneve
ipv4:
  enabled: true
ipv6:
  enabled: false
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
  algorithm: maglev
  acceleration: disabled
maglev:
  tableSize: 65521
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
l7Proxy: true
envoy:
  enabled: true
hubble:
  enabled: true
  relay:
    enabled: true
```


Supply the real API endpoint and one persisted per-cluster Maglev seed. The seed is a base64 encoding of 12 random bytes; generate it once, store it with the cluster values and reuse it, rather than regenerating it on each upgrade.

```bash
: "${API_SERVER_HOST:?Set the reachable real API server host, not its ClusterIP}"
: "${API_SERVER_PORT:?Set the actual API server port}"
: "${MAGLEV_SEED:?Set the persisted base64 encoding of 12 random bytes}"
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
helm install cilium cilium/cilium --version 1.20.1 --namespace kube-system \
  --values lb-values.yaml \
  --set-string k8sServiceHost="$API_SERVER_HOST" \
  --set k8sServicePort="$API_SERVER_PORT" \
  --set-string maglev.hashSeed="$MAGLEV_SEED"
cilium status --wait
```

Use the namespace created by this guide in the selected cluster; if this is a different disposable cluster, repeat the namespace creation/label steps there first. The HTTP-policy application and this external-LB backend use different labels, so the earlier client-only HTTP rule does not accidentally block this experiment.

**`lb-echo.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lb-echo
  template:
    metadata:
      labels:
        app: lb-echo
    spec:
      automountServiceAccountToken: false
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: lb-echo
  namespace: cilium-l2l7-demo
spec:
  type: NodePort
  selector:
    app: lb-echo
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
```


```bash
kubectl apply -f lb-echo.yaml
kubectl -n cilium-l2l7-demo rollout status deployment/lb-echo --timeout=120s
kubectl -n cilium-l2l7-demo get pods -l app=lb-echo -o wide
kubectl -n cilium-l2l7-demo get service lb-echo -o wide
NODEPORT=$(kubectl -n cilium-l2l7-demo get service lb-echo -o jsonpath='{.spec.ports[0].nodePort}')
```

Use a reachable ingress node **different from the backend node**, and an external client not subject to Cilium's in-cluster socket LB. From that client, request `http://ENTRY_NODE_IP:NODEPORT/` using the actual values. A Pod-to-ClusterIP curl proves neither external DSR nor Maglev behavior. Verify request/response paths and backend/connection state; do not infer them from a successful HTTP response alone.

## Masquerading

Pod egress masquerading changes a source address when required for the configured external path. It is not encryption or a firewall, and it is distinct from Service DNAT and DSR forwarding.

The following fragment excludes the example `10.0.0.0/8` destination range from source masquerading **only when the network really supports those Pod source/return routes**:

**`masquerade-values.yaml`**

```yaml
bpf:
  masquerade: true
enableIPv4Masquerade: true
enableIPv6Masquerade: false
ipv4NativeRoutingCIDR: 10.0.0.0/8
```


`ipv4NativeRoutingCIDR` expresses the assumed routable range and corresponding masquerade exclusion. It does not install routes or switch the entire datapath to native routing. A broad exclusion without working return routes can break connectivity.

- BPF masquerading depends on the BPF NodePort feature in this release and only applies on devices carrying the BPF program. Inspect selected devices; use the documented `devices` configuration when needed.
- The iptables implementation uses its documented `egressMasqueradeInterfaces` behavior. Do not treat that field or the removed generic `masquerade-interfaces`/`masquerade-all` examples as universal BPF controls.
- IPv6 BPF masquerading is documented as beta. Neither implementation removes Cilium's platform/kernel requirements, and both ultimately process traffic in the kernel.
- Node-address exceptions, ip-masq-agent exclusions and later cloud/NAT gateways can affect the observed source. Use a controlled observer plus node-side state/captures; reaching an arbitrary public site does not prove a particular NAT implementation.

On the relevant agent:

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-AGENT-ON-TARGET-NODE
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
```

## Fragment Handling and MTU

The released fragment tracker stores datagram identity and L4 source/destination ports in bounded LRU maps. It can recover port context for later fragments that lack an L4 header; it is **not a BPF payload-reassembly engine** or a guarantee against fragment attacks.

The documented feature includes IPv4 and IPv6 tracking, enabled by default through the corresponding flags, and is marked beta. The valid IPv4 flag is still `enable-ipv4-fragment-tracking`. `bpf-fragments-map-max` controls tracked datagram map capacity; the old `fragment-tracking-timeout` and `max-fragments-per-flow` settings are not the released configuration contract.

An explicit example using the chart's extra configuration map:

**`fragment-values.yaml`**

```yaml
extraConfig:
  enable-ipv4-fragment-tracking: 'true'
  bpf-fragments-map-max: '8192'
```


8192 is a capacity example, not a maximum number of fragments per flow. Inspect `cilium_ipv4_frag_datagrams` / `cilium_ipv6_frag_datagrams` and their pressure when diagnosing capacity; pressure is not a reassembly-success or attack-prevention counter.

Prefer correct packet sizing and a working path MTU discovery path. PMTUD depends on the relevant error signaling and network behavior; it does not guarantee automatic optimal sizing everywhere. Cilium's `MTU` is the **underlying-network override**. As explained in the [networking guide](03-networking.md), ordinary VXLAN overhead is 50 bytes for IPv4 underlay and 70 for IPv6; blindly setting the base to 1450 for a 1500-byte path can subtract overhead twice.

## Observability and Troubleshooting

Inspect the correct node, actual Envoy deployment mode, desired policy, realized endpoint state and fresh traffic. Use `cilium-dbg` for agent-local operations and the standalone CLI for cluster operations. Removed `policy trace` commands and forced endpoint regeneration are not the starting point for this diagnosis.

Keep an enabled Hubble Relay port-forward running in a separate terminal, then observe relevant flows:

```bash
cilium hubble port-forward
```

```bash
hubble observe --namespace cilium-l2l7-demo --protocol http --last 20
hubble observe --namespace cilium-l2l7-demo --verdict DROPPED --last 20
```

HTTP policy rejection may appear as HTTP 403 rather than a packet DROPPED verdict. A timeout alone can also mean readiness, DNS, routing, TLS or observation problems. Correlate layers instead of interpreting every error as policy success.

## Validation Limits and Sources

These are release-source/schema-checked examples with bounded local fixtures, not a production-tested platform or live-cluster benchmark. Image execution, webhook reachability, mTLS traffic, DSR return paths, NAT behavior and fragmentation still require validation in the prepared environment. Clean up only this run's labeled application resources; do not remove the cluster CNI as lab cleanup.

- [Cilium kube-proxy replacement/DSR/Maglev](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/kubernetes/kubeproxy-free.rst), [masquerading](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/masquerading.rst), [fragment handling](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/fragmentation.rst), [fragment map implementation](https://github.com/cilium/cilium/blob/v1.20.1/pkg/maps/fragmap/fragmap.go)
- [L2 Announcements](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/l2-announcements.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/multicast.rst), [HTTP rule translator](https://github.com/cilium/cilium/blob/v1.20.1/pkg/envoy/policy/envoy_l7_rules_translator.go), [Envoy chart defaults](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/templates/_helpers.tpl)
- [Cilium/Istio integration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/istio.rst), [Istio CNI/init-container modes](https://istio.io/latest/docs/setup/additional-setup/cni/), [webhook requirements](https://istio.io/latest/docs/ops/configuration/mesh/webhook/), [Istio 1.31 schemas](https://github.com/istio/istio/blob/1.31.0/manifests/charts/base/files/crd-all.gen.yaml)
- [Kubernetes Service proxy modes/affinity](https://kubernetes.io/docs/reference/networking/virtual-ips/), [Cilium 1.20.1 values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)


[Return to Main Page](README.md)

## Quiz

[Review the L2–L7 and load-balancing questions](../../quizzes/networking/cilium/05-l2-l7-networking-quiz.md).
