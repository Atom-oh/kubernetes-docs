# IPAM and Network Policies

> **Review baseline**: Cilium 1.20.1; tested Kubernetes 1.33–1.36. Resource API versions and platform requirements are checked separately.
> **Last reviewed**: September 12, 2026

## Lab Environment Setup

Use the [installation profiles](README.md) and [networking prerequisites](03-networking.md) to prepare a disposable Linux cluster. Keep kubectl within the supported API-server version skew. IPAM profiles below are alternatives for installation or a documented migration, not ConfigMap toggles to apply sequentially to a running cluster.

The policy lab uses its own namespace and matching workloads below, replacing the old Cilium 1.14 Star Wars manifest whose labels did not match these policies. Inspect existing Kubernetes/Cilium cluster-wide policy and admission settings first; a new namespace does not override them.

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

Use the actual namespace/release name if different. Desired Helm values and ConfigMaps, node overrides, operator settings and realized agent state answer different questions. A grep result containing `ipam` is not a complete effective-configuration check.

## IP Address Management Strategies

Cilium Pod IPAM allocates workload addresses. Kubernetes allocates Service **ClusterIPs**; Cilium **LoadBalancer IPAM** is a separate facility for LoadBalancer addresses. A `CiliumPodIPPool` does not allocate Service ClusterIPs.

### Allocators and Authoritative State

| Configuration | Who allocates node capacity / Pod IPs? | State to inspect |
|---|---|---|
| `cluster-pool` (generic default) | Cilium Operator assigns per-node CIDRs; each agent allocates local addresses | `CiliumNode.spec.ipam.podCIDRs` and operator status |
| `kubernetes` / host scope | Kubernetes supplies node PodCIDRs; each agent allocates within them | Kubernetes `Node.spec.podCIDRs` / `spec.podCIDR` and supported provider annotations |
| `multi-pool` | Operator assigns blocks from named pools in response to agent demand; agent allocates Pod IPs | `CiliumPodIPPool`, `CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | An external allocator supplies available addresses; agent consumes/releases them | `CiliumNode.spec.ipam.pool` / `status.ipam.used` (and applicable IPv6 fields) |
| `eni` | Operator manages AWS ENIs/IPs/prefixes; agent translates interface state into its multi-pool allocator | `CiliumNode.status.eni.enis` and mode-specific pool/demand state |
| `azure` | Upstream operator/agent integration for self-managed Azure VM/VMSS clusters | Azure/CiliumNode allocation state |
| `delegated-plugin` | Cilium CNI invokes another IPAM plugin, such as managed AKS's Azure IPAM | Provider/plugin state; do not substitute upstream Azure IPAM configuration |
| GKE integration | Upstream GKE integration uses host-scope `kubernetes` IPAM; managed Dataplane V2 has its own ownership | Provider configuration and Node CIDRs; not a separate `gke` IPAM value |

Both cluster-pool and Kubernetes host scope allocate individual Pod addresses locally. The difference is who allocates the **node prefixes**. Neither eliminates coordination or guarantees that a user-supplied pool cannot overlap a VPC, node network, Service range or another cluster.

The released CRD/type definitions use `pool` and `used` for generic CRD-backed allocation. Some explanatory documentation still says `available`/`inuse`; use the installed schema and mode-specific fields rather than copying those older names. ENI in 1.20.1 uses the interface/multi-pool path, so generic CRD-backed fields are not its universal source of truth.

### Kubernetes/CNI Integration

The kubelet requests Pod sandbox operations through the container runtime; a CNI-capable runtime invokes the Cilium CNI plugin. Allocation depends on the selected backend, after which the plugin/agent configures the endpoint network. In host-scope mode, Kubernetes must supply the required address-family CIDRs, for example through a correctly configured node-CIDR allocator.

## IPAM Configuration

These are **Helm value fragments** to merge into the matching installation profile. Review Pod/Service/node/external address ranges first.

### Cluster Pool

**`cluster-pool-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
ipv4:
  enabled: true
ipv6:
  enabled: false
```


The Operator coordinates node blocks, not a central request for each Pod address. Multiple CIDRs in `clusterPoolIPv4PodCIDRList` expand the common allocation space; this is different from selecting named pools per workload.

Do not replace existing pool-list entries to grow a live cluster. Add a non-conflicting CIDR through the documented expansion procedure. The node mask size is not a routine mutable setting. Address counts per block are not identical to usable Pod capacity because addresses are reserved or used by node-local facilities.

For a cluster already prepared for Kubernetes/Cilium dual stack:

**`dual-stack-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList:
    - fd00:10:244::/104
    clusterPoolIPv6MaskSize: 120
ipv4:
  enabled: true
ipv6:
  enabled: true
```


Enabling these two Cilium address-family flags does not configure Kubernetes Service CIDRs, underlay IPv6 connectivity or cloud support by itself.

### Multi-Pool and CiliumPodIPPool

The documented mode is `multi-pool`; the resource API remains `cilium.io/v2alpha1`. Do not infer a feature's maturity solely from that API suffix. On a fresh cluster using this mode, provide a default pool for ordinary allocations:

**`multi-pool-values.yaml`**

```yaml
ipam:
  mode: multi-pool
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4:
          cidrs:
          - 10.244.0.0/16
          maskSize: 24
```


This additional named pool uses the current `cidrs` and `maskSize` fields:

**`blue-pool.yaml`**

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumPodIPPool
metadata:
  name: blue-pool
spec:
  ipv4:
    cidrs:
    - 10.245.0.0/16
    maskSize: 24
  namespaceSelector:
    matchLabels:
      ipam-pool: blue
  podSelector:
    matchLabels:
      role: blue
```


The pool resource is cluster-scoped. `podSelector` and `namespaceSelector` are separate fields, and both must match when both are configured. The old `ipv4.cidr`, `blockSize` and generic `selector` example was invalid.

For the selector example:

**`blue-namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ipam-selection-demo
  labels:
    ipam-pool: blue
  annotations:
    ipam.cilium.io/require-pool-match: 'true'
```


**`blue-pod.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: blue-client
  namespace: ipam-selection-demo
  labels:
    role: blue
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


Apply these only on a prepared multi-pool installation. The namespace's `require-pool-match` annotation prevents automatic fallback to the default pool when a non-default selector match is required.

Pool choice follows explicit Pod/namespace `ipam.cilium.io/ip-pool` or address-family pool annotations, then automatic selectors, then the default pool. Automatic selection must match exactly one pool for the address family; overlapping selectors cause allocation failure. Pool annotations affect **new allocations**, not already-running Pod IPs. Node-specific defaults can also be configured through `CiliumNodeConfig`.

Pool selection is not a substitute for network authorization: control who can change workload labels/annotations and enforce traffic policy separately. Pools must not have overlapping CIDRs. In-use ranges/pools must not be removed casually; `maskSize`, `allowFirstIP` and `allowLastIP` are immutable. The first/last address reservation has documented small-prefix exceptions.

A current documented online migration exists from **cluster-pool to multi-pool**. That does not authorize arbitrary live IPAM changes or an unplanned reverse migration. Follow its prerequisites and workload/capacity checks; no migration is executed by this chapter.

### AWS ENI

Use the full EKS/ENI installation profile for routing, operator IAM, subnet/instance capacity and node preparation. The following fragment illustrates the current keys, including optional IPv4 prefix delegation:

**`eni-values-fragment.yaml`**

```yaml
ipam:
  mode: eni
eni:
  enabled: true
  eniTags:
    team: platform
  awsEnablePrefixDelegation: true
routingMode: native
endpointRoutes:
  enabled: true
ipv4:
  enabled: true
ipv6:
  enabled: false
```


`eni.awsEnablePrefixDelegation` requires the instance/subnet setup to support the requested prefixes. An IPv4 `/28` contains 16 addresses, not a guarantee of 16 additional schedulable Pods in every configuration. The default is disabled. Do not add the invented `eni-prefix-delegation-enabled` key.

The Operator makes the EC2 API calls; pre-allocation reduces per-Pod delays but cannot eliminate quota, API or subnet exhaustion. `eni.eniTags` tags managed interfaces. Let the SDK resolve the appropriate EC2 endpoint unless there is a deliberate, validated `eni.ec2APIEndpoint` override.

This example is IPv4. The ENI reference documents IPv6 as beta with different prefix/allocation behavior; platform validation is separate from enabling `ipv6.enabled`. AWS VPC CNI chaining keeps address ownership with AWS VPC CNI. Ordinary EC2, Hybrid Nodes, Fargate and Auto Mode have different installation/support boundaries; Fargate and Auto Mode cannot use this replacement profile.

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## Querying Per-Node Allocation State

### CiliumNode Example

This is an **illustrative read-only object shape**, not a manifest to apply over Operator-owned state:

**`ciliumnode-example.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNode
metadata:
  name: hybrid-node-001
spec:
  addresses:
  - ip: 10.85.0.1
    type: CiliumInternalIP
  - ip: 10.80.1.10
    type: InternalIP
  ipam:
    podCIDRs:
    - 10.85.0.0/25
```


The first address can be `CiliumInternalIP`, not the underlay node's `InternalIP`. Multiple InternalIPs/address families and multiple allocation entries can exist. Even a typed InternalIP is only a candidate for a network design, not an automatically valid next hop from every router.

### Mode-specific Inventory

Save this query as `ciliumnode-inventory.jq`:

**`ciliumnode-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.spec.addresses[]? |
    select(.type == "InternalIP") | .ip] | unique),
  clusterPoolPodCIDRs: (.spec.ipam.podCIDRs // []),
  multiPoolAllocations: (.spec.ipam.pools.allocated // []),
  eniInterfaceIDs: ((.status.eni.enis // {}) | keys),
  operatorStatus: (.status.ipam["operator-status"] // {})
}
```


```bash
kubectl get ciliumnodes -o json | jq -f ciliumnode-inventory.jq
```

An absent/empty field can be normal for a different IPAM mode. For Kubernetes host scope, inspect the Kubernetes Node instead:

**`kubernetes-node-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.status.addresses[]? |
    select(.type == "InternalIP") | .address] | unique),
  podCIDRs: (.spec.podCIDRs // []),
  legacyPodCIDR: (.spec.podCIDR // null)
}
```


```bash
kubectl get nodes -o json | jq -f kubernetes-node-inventory.jq
```

These queries retain all relevant addresses/CIDRs instead of silently selecting `[0]`. They produce inventory, not `ip route add` commands. Select interfaces/next hops and verify forwarding/return paths through the network's routing procedure. Do not assume every CIDR should be installed via the first address on an unrelated router.

The inventory can inform [EKS Hybrid Nodes network planning](../../eks-hybrid-nodes/02-network-configuration.md), but it does not replace that environment's routing and reachability checks.

## Network Policy Design and Implementation

### Resource and Rule Semantics

- A namespaced `CiliumNetworkPolicy` selects endpoints in its namespace; `CiliumClusterwideNetworkPolicy` provides cluster-wide scope. Host-firewall `nodeSelector` is supported only in the latter, with host firewall configured.
- `endpointSelector` identifies subjects; ingress/egress describe traffic relative to them. Cilium rule `spec.labels` stores optional identification/metadata, not references that inherit another policy. Kubernetes `metadata.labels` labels the resource itself.
- Allowed traffic from applicable policies is combined; explicit deny rules have their documented precedence. Another unrestricted L4 allow can bypass an overlapping L7-restricted allow.
- Default deny is direction-specific. Preserve required DNS/application paths deliberately, and inspect realized policy plus actual flows. Merely disabling default deny is not a universal L7 dry-run mode.

### Matched Policy Lab

Run these steps in one shell in the disposable cluster:

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

Stop if the namespace already exists and choose a fresh name consistently. These workloads use the official CLI's test images and labels used by the policies:

**`policy-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-ipam-policy-demo
  labels:
    app: frontend
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
  namespace: cilium-ipam-policy-demo
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
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
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
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-ipam-policy-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


```bash
kubectl apply -f policy-app.yaml
kubectl -n cilium-ipam-policy-demo wait --for=condition=Ready \
  pod/frontend pod/outsider pod/client --timeout=120s
kubectl -n cilium-ipam-policy-demo rollout status deployment/backend --timeout=120s
kubectl -n cilium-ipam-policy-demo get pods -o wide --show-labels
BACKEND_IP=$(kubectl -n cilium-ipam-policy-demo get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
kubectl -n cilium-ipam-policy-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 "http://$BACKEND_IP:8080/"
```

First confirm baseline connectivity from the outsider as well. Backend anti-affinity requires another eligible node. The database rule below illustrates an additional application dependency; this lab does not deploy or validate a database server.

### L3/L4 Policy

**`backend-l4.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


Apply `backend-l4.yaml`, wait for policy realization on the backend's agent and check fresh requests. Frontend should retain access; outsider denial requires flow evidence, not just a nonzero curl exit.

### L7 HTTP Policy

This is an **alternative definition of the same `backend-access` resource**, not a second overlapping allow policy. Applying it replaces this lab's L4 version; still inspect other applicable policies.

**`backend-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/$
          headerMatches:
          - name: content-type
            value: application/json
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


```bash
kubectl apply -f backend-http.yaml
kubectl -n cilium-ipam-policy-demo get cnp backend-access -o yaml
```

After realization, the policy permits GET `/`, and POST `/` only with the exact `content-type: application/json` value. A request to another path/method should be denied by the proxy. The application must itself implement an allowed operation; policy permission does not guarantee application success. The demo server's known readiness path is GET `/`.

HTTP method/path fields are regular expressions. Keep examples anchored and escape metacharacters when adapting them. HTTP/gRPC rules require Envoy and visible application traffic; TLS termination/interception must be configured when needed. gRPC service/method information is carried in the HTTP/2 path and metadata in headers, not a separate `rules.grpc` field or arbitrary protobuf-payload filtering.

### Kafka Policy Boundary

Current Cilium does not provide the removed `rules.kafka` API. Do not apply the old topic/API-key/client-ID YAML. Use appropriate L4 connectivity rules to the broker's **actual listener port**, and configure authentication/authorization such as topic access in the broker. NetworkPolicy neither replaces broker authorization nor enables encryption.

### DNS/FQDN Policy

This example assumes the selected resolver is a CoreDNS/kube-dns Pod in `kube-system` on TCP/UDP 53. Inspect the Pod's actual resolver first; NodeLocal DNS, OpenShift and managed DNS paths need their own matching configuration.

**`dns-egress.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-egress
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```


The DNS L7 rule redirects matching resolver traffic through Cilium's DNS proxy so it can learn name-to-IP responses. Permitting port 53 alone does not provide that observation. `matchPattern: "*"` permits DNS queries to the selected resolver; HTTPS egress is separately limited to IPs learned for the `toFQDNs` names. Replace `api.example.com` with a resolvable, controlled test name before claiming a successful external test.

`*.googleapis.com` matches one label beneath that suffix; it does not match the apex or multiple labels. In this release, `**.googleapis.com` can match one or more subdomain levels, still excluding the apex. DNS TTL/cache state and fresh lookups matter. Name-to-IP allowance is not an HTTP hostname, URL or application-user authorization check.

The default DNS proxy runs in the agent; a separate standalone DNS proxy is documented as alpha. DNS policy does not universally require Envoy. For OpenShift, the official example uses the `openshift-dns` resolver configuration and port 5353 rather than blindly copying this rule.

### CIDRs, Services and Entities

| Rule | Boundary |
|---|---|
| `toCIDR` / `toCIDRSet` | Select IP prefixes, primarily external peers. By default they do not substitute for selectors of Cilium-managed Pods/nodes; documented opt-in CIDR matching for `pods`/`nodes` is beta and consumes identities |
| `toServices` | Resolves Service selectors or selectorless EndpointSlice addresses into policy selectors; it does not create a Service or route. Selectorless cases inherit CIDR-mode limitations |
| `world` | Broad outside-cluster identity category, not “public Internet only” or a named remote-cluster selector |
| `cluster` / `cluster-mesh` | `cluster` covers local cluster endpoints plus documented reserved entities/remote nodes; `cluster-mesh` additionally selects meshed-cluster endpoints |
| `all` | Broad combination including cluster/mesh and external peers; not a least-privilege shortcut |

For API-server access, use the documented `kube-apiserver` entity behavior rather than assuming `toServices: default/kubernetes` has ordinary workload-selector semantics.

## Multi-cluster Scenarios

Cluster Mesh shares state while keeping Kubernetes clusters and network namespaces separate. Remote nodes do not become local Kubernetes Node objects, and policy resources are not automatically distributed.

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

The Cluster Mesh API server synchronizes state; Pod packets do not need to pass through it. Control-plane mTLS does not by itself encrypt Pod-to-Pod traffic.

### Setup Prerequisites and Partial Sequence

Prepare separate clusters with non-overlapping Pod CIDRs, reachable node InternalIPs, allowed network paths, the same datapath mode and Cilium versions within the documented one-minor difference. Native routing additionally needs all remote Pod ranges reachable and covered by the configured native-routing CIDR. Assign unique Cilium names/IDs at installation (for example `cluster-a`/1 and `cluster-b`/2) and configure peer certificate trust.

The following is a partial sequence **after** those prerequisites and the private NodePort control-plane path are prepared. Kubeconfig context names need not equal Cilium cluster names:

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

This does not provision VPC peering/VPNs, routes, firewalls, private endpoints or certificate trust. Follow the full platform-specific setup; do not change a live cluster's name/ID casually.

### Global Services and Cross-cluster Policy

Create matching namespaces and actual backend workloads in each prepared cluster, then use the **same Service name and namespace** with compatible ports:

**`global-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: global-service
  namespace: mesh-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: global-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
```


`service.cilium.io/global` is the current annotation. A global service shares local backends by default; `service.cilium.io/shared: "false"` stops sharing them to peers without necessarily preventing local clients from using remote backends. Local ClusterIPs do not have to be identical.

Do not promise automatic failover solely from this annotation. By default, unreachable-cluster state is retained (`clustermesh.cacheTTL: 0s`); a configured positive TTL can revoke stale remote data after control-plane disconnection. That is not an application health probe or a zero-downtime guarantee.

Apply this ingress policy in the destination cluster's `mesh-demo` namespace when the named source workload exists in `cluster-a`:

**`cross-cluster-policy.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cluster-a-frontend
  namespace: mesh-demo
spec:
  endpointSelector:
    matchLabels:
      app: global-app
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: frontend-ns
        k8s:io.cilium.k8s.policy.cluster: cluster-a
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


The cluster label uses the configured **Cilium cluster name**, not a kubeconfig context. In current Cilium, endpoint selectors default to the local cluster unless peers are explicitly selected. Install the required policies independently in each cluster and test both traffic directions.

## Validation and Cleanup

The examples were checked against release-specific schemas, configuration/source contracts and bounded local fixtures. This audit does not claim live IP allocation, kernel policy enforcement, cloud provisioning, a running database or successful cross-cluster traffic.

Inspect desired and realized state, verify a successful baseline, then correlate expected denials with the relevant flow. Clean up only this run's namespaced policy workloads after verifying ownership. For the separate multi-pool exercise, release workloads and verify pool allocations are no longer in use before considering pool removal; never delete active CiliumNode/pool state as a shortcut.

## Sources

- [IPAM modes/migration](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/index.rst), [cluster pool](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool.rst), [host scope](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/kubernetes.rst), [multi-pool](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/multi-pool.rst), [migration procedure](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [PodIPPool schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml), [CiliumNode schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml), [ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/concepts/ipam/eni.rst), [Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml), [EKS CNI boundaries](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Policy rule API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/rule.go), [L3 rules](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer3.rst), [L7 rules](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst), [DNS policies](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/dns.rst), [wildcard implementation](https://github.com/cilium/cilium/blob/v1.20.1/pkg/fqdn/matchpattern/matchpattern.go)
- [Cluster Mesh setup](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/setup.rst), [architecture](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/intro.rst), [global services](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/global-services.rst), [cross-cluster policy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/clustermesh/policy.rst)


[Return to Main Page](README.md)

## Quiz

[Check your IPAM and policy understanding](../../quizzes/networking/cilium/04-ipam-policy-quiz.md).
