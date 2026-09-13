# Service Mesh Solution Comparison

> **Last reviewed**: September 11, 2026
> **API/artifact checks**: Istio 1.31.0; Linkerd edge-26.9.1; Kong Mesh/Kuma 2.14.4; Consul/chart 2.0.4

The artifact versions identify the sources used to check examples. They are **not a shared Kubernetes compatibility matrix** or evidence of a deployed production system. The original Istio 1.24/Linkerd 2.15/Kong Mesh 2.8/Consul 1.19 performance figures are retained below with their historical, unverified status.

## Contents

1. [Architecture](#architecture)
2. [Performance Evidence](#performance-evidence)
3. [Traffic Management](#traffic-management)
4. [Security](#security)
5. [Observability](#observability)
6. [Multicluster](#multicluster)
7. [Installation and Operations](#installation-and-operations)
8. [Cost and Licensing](#cost-and-licensing)
9. [Selection and Validation](#selection-and-validation)

## Architecture

A service mesh moves selected communication functions into infrastructure components. Traffic interception can be transparent to application code, but protocol selection, traffic ownership, workload identity and policy still require configuration. Distributed tracing also needs context propagation/instrumentation. A mesh does not make arbitrary application retries safe.

![Conceptual sidecar pattern: a control plane configures proxies between services. The surrounding text defines the required policy and telemetry configuration.](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-0.html)

The diagram illustrates a configured sidecar deployment; it is not a claim that every feature is enabled by default or that ambient/Cilium use the same per-Pod topology.

### Istio

![Istiod reads configuration and supplies xDS configuration to Envoy sidecars, which carry traffic between enrolled workloads.](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-2.html)

Istiod combines configuration/discovery and identity-management functions historically associated with Pilot, Citadel and Galley; those names do not represent three additional current deployments. Sidecar data planes use Envoy. Ambient uses per-node ztunnel for L4 and separate Envoy waypoints for supported L7 processing. Ingress/egress gateways implement explicitly selected boundary paths.

Kubernetes and documented VM integration are supported, with network/trust prerequisites. Ambient core GA does not imply feature parity with sidecars: waypoint policy attachment, EnvoyFilter support and multicluster maturity differ. Select the mode and required API behavior before estimating resources or complexity.

### Linkerd

![Linkerd Destination, Identity and Proxy Injector components supply discovery, workload certificates and injection for Rust linkerd2-proxy sidecars.](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-3.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-3.html)

Linkerd uses its purpose-built Rust proxy and Kubernetes resources, annotations and CRDs. Current features include Gateway API request routing, timeouts/retries, per-route authorization and local rate limiting. Calling it an annotation-only or “basic features only” mesh is inaccurate.

Non-Kubernetes mesh expansion is documented using ExternalWorkload, a proxy on the external machine, compatible SPIFFE/SPIRE identity, DNS and network access. It is not “no VM support,” nor does registering an external IP automatically install or authenticate a proxy.

### Kong Mesh and Kuma

![Kong Mesh control plane configures Envoy data-plane proxies on Kubernetes and VM workloads. A global control plane is used for the multi-zone model.](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-4.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-4.html)

Kong Mesh builds on Kuma. Kubernetes mode uses Kubernetes resources/storage; Universal mode supports VM/bare-metal environments and uses its configured database. Kong offers self-hosted and managed-global-control-plane options; edition features and support terms must be checked separately from upstream Kuma.

In a multi-zone deployment, the global and zone control planes exchange resources through KDS, while each zone supplies xDS to its local proxies. Cross-zone data traffic uses the destination zone ingress and, when configured, the local zone egress. The global control plane is not an automatic Prometheus/tracing aggregation backend.

A service's discovery does not by itself specify an 80% local/20% remote split. Legacy endpoint weighting and current MeshLoadBalancingStrategy locality settings have different defaults. Inspect the selected policy, eligible endpoints and cross-zone/failover settings instead of treating a diagram's weights as inherent behavior.

Use current policies such as MeshHTTPRoute, MeshTrafficPermission, MeshRetry, MeshTimeout, MeshMetric, MeshTrace and MeshAccessLog where appropriate. TrafficRoute and TrafficPermission are legacy/deprecated interfaces, not necessarily removed APIs in the checked release. Migrate dependent policies together; do not combine old TrafficPermission with MeshTrafficPermission. A policy type alone does not establish “global” versus “zone-only” ownership or propagation.

Global-control-plane failure can leave existing data traffic operating while policy and remote-service changes stop propagating. Zone-control-plane failure can prevent new proxies, configuration updates and certificate refresh. Retained configuration is not an indefinite availability guarantee. Validate registration, updates, draining and expiry under actual failure conditions.

### Consul Service Mesh

Consul supplies service discovery, configuration and identity functions with first-class Envoy support. Current Kubernetes integrations normally use consul-dataplane to manage the sidecar; the old client-agent-per-node picture is not the only or default Kubernetes architecture.

The official proxy overview also describes a built-in L4 proxy for development/testing and advises against production use. It should not be presented as equivalent to Envoy's production L7 feature set, or incorrectly described as removed without release evidence. Consul supports documented VM and other runtime integrations as well as Kubernetes.

### Cilium in the Same Decision

Cilium combines an eBPF network datapath with proxies such as Envoy for L7 parsing/policy. It is not entirely proxy-free L7 networking. Cilium 1.20.1 out-of-band mutual authentication is Beta and uses an out-of-band handshake; WireGuard/IPsec encryption is a separate requirement. See the [Cilium mesh guide](../../cilium-service-mesh/README.md) for its actual feature and Cluster Mesh constraints.

Cilium 1.20.1 also provides a separate [ztunnel transparent-encryption beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), selected with `encryption.type: ztunnel`. It provides TCP workload mTLS with namespace enrollment; both endpoints must be enrolled. It excludes ClusterMesh and host-networked Pods, and the released guide warns that ordinary L4 policies do not work on this path except when targeting HBONE port 15008. This is a distinct deployment choice with its own CA/bootstrap requirements.

## Performance Evidence

### Original Figures: Historical and Unverified

The former text described a **three-node EKS 1.28, m5.xlarge, 100-service, 1,000-RPS** test and named Istio 1.24, Linkerd 2.15, Kong Mesh 2.8 and Consul 1.19. It supplied no raw samples, reproducible harness, exact patch/proxy versions or source benchmark. These numbers cannot establish a current product ranking:

| Original entry | p50 | p95 | p99 | CPU claim | Memory claim |
|---|---:|---:|---:|---:|---:|
| Baseline |0.1 ms|0.2 ms|0.3 ms|—|—|
| Linkerd |+0.5 ms|+0.8 ms|+1.2 ms|+3–8%|+20–50 MB|
| Istio |+1.0 ms|+2.5 ms|+3.5 ms|+5–15%|+50–150 MB|
| Kong Mesh |+0.8 ms|+2.0 ms|+3.0 ms|+5–12%|+40–120 MB|
| Consul |+1.0 ms|+2.5 ms|+3.5 ms|+6–14%|+50–140 MB|

The original control-plane estimates were Istio 0.5–1 CPU/1–2 GB, Linkerd 0.1–0.3 CPU/200–500 MB, Kong 0.2–0.5 CPU/500 MB–1 GB and Consul 0.5–1 CPU/1–2 GB. Per-proxy CPU estimates ranged from Linkerd 20–100m to Istio/Consul 100–500m. These are unverified inputs, not defaults, measurements or capacity recommendations. Counting Linkerd's different components is also not equivalent to counting replicas of one component.

The removed throughput graphic claimed Linkerd retained 95–98%, Kong 90–95%, and Istio/Consul 85–92% of baseline throughput, without supporting data. It cannot justify “Linkerd fastest,” a fixed resource percentage or a minimum fleet size.

### A Reproducible Comparison

Keep the actual product/proxy/Kubernetes versions, hardware and full configuration attached to results. Match traffic protocol/payload/concurrency, TLS/authentication, policy, telemetry and resource limits. Report absolute baseline and meshed latency distributions, throughput at a defined error/SLO limit, per-component CPU/memory, and repeated-run variability.

Compare equivalent HA and failure behavior, including rollout, draining, connection reuse, missing telemetry and control-plane loss. Measure raw errors separately from client-visible outcomes after retries. Do not move the historical version labels forward without rerunning and retaining the experiment.

## Traffic Management

| Capability | What to compare concretely |
|---|---|
| Weighted/header routing | Istio VirtualService, Linkerd HTTPRoute, Kong MeshHTTPRoute, Consul router/splitter/resolver behavior |
| Blue/Green or canary | A route is only one part; a rollout controller or deployment workflow must manage revisions, analysis and reversal |
| Retries/timeouts | Supported request/protocol scope, default policy, budgets and application idempotency |
| Rate limiting | Local versus shared counters, identity, failure policy and actual replica scope |
| Faults/mirroring | Supported API/filter and observed generated configuration; mirrored writes can have side effects |

Linkerd does support local rate limiting through HTTPLocalRateLimitPolicy, including per-identity limits, and dynamic routing by request properties. Local per-proxy limits are not a global service quota. Consul and Kong features can depend on the selected edition/API; a coarse “basic/enterprise/no” table is insufficient.

### Independent Read-only Routing Examples

Use these as **alternatives in the appropriate mesh**, not overlapping controllers on one workload. They assume existing `reviews` Pods in `mesh-demo`, actual version labels, an HTTP listener on 9080 and matching mesh enrollment. This Service shape supplies explicit ports; it does not create the applications:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: mesh-demo
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: mesh-demo
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
    appProtocol: http
```

The following comparisons concern read-only review requests. Before routing writes, audit inherited mesh/client retries and idempotency separately. A routing header is client-controlled input, not authentication.

#### Istio

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  hosts:
  - reviews
  http:
  - name: canary-header
    match:
    - headers:
        x-release:
          exact: canary
    route:
    - destination:
        host: reviews
        subset: v2
        port:
          number: 9080
      weight: 100
    retries:
      attempts: 0
  - name: weighted
    route:
    - destination:
        host: reviews
        subset: v1
        port:
          number: 9080
      weight: 90
    - destination:
        host: reviews
        subset: v2
        port:
          number: 9080
      weight: 10
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

Both routes explicitly disable mesh retries. Subset labels must match real endpoints; traffic weights do not create or scale the versions. Gateway exposure, if required, needs its own host/TLS binding.

#### Linkerd

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews-outbound
  namespace: mesh-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: reviews
    port: 9080
  rules:
  - matches:
    - headers:
      - name: x-release
        type: Exact
        value: canary
    backendRefs:
    - group: ''
      kind: Service
      name: reviews-v2
      port: 9080
      weight: 100
  - backendRefs:
    - group: ''
      kind: Service
      name: reviews-v1
      port: 9080
      weight: 90
    - group: ''
      kind: Service
      name: reviews-v2
      port: 9080
      weight: 10
```

This Gateway API producer route attaches to the Service and configures meshed **clients**. The core Service group is the empty string. It does not require the deprecated SMI TrafficSplit extension. Existing ServiceProfiles take precedence over outbound HTTPRoutes for the same Service; resolve that ownership deliberately. Inspect Accepted/ResolvedRefs and actual routing before relying on it.

#### Kong Mesh

```yaml
apiVersion: kuma.io/v1alpha1
kind: MeshHTTPRoute
metadata:
  name: reviews-weighted
  namespace: mesh-demo
  labels:
    kuma.io/mesh: default
spec:
  targetRef:
    kind: Dataplane
    labels:
      app: productpage
  to:
  - targetRef:
      kind: MeshService
      name: reviews
      sectionName: http
    rules:
    - matches:
      - path:
          type: PathPrefix
          value: /
      default:
        backendRefs:
        - kind: MeshService
          name: reviews-v1
          port: 9080
          weight: 90
        - kind: MeshService
          name: reviews-v2
          port: 9080
          weight: 10
```

`reviews`, `reviews-v1` and `reviews-v2` here denote **actual MeshService resource names**, not an assumption that every generated name equals the Kubernetes Service name. Resolve their names, namespace/port sections and backend readiness in the installed environment. The selected caller Dataplane must carry the app label, and HTTP Service ports must declare the supported protocol. The example changes weights, not locality priority or capacity.

#### Consul

```yaml
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceDefaults
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  protocol: http
---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceResolver
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  subsets:
    v1:
      filter: Service.Meta.version == v1
      onlyPassing: true
    v2:
      filter: Service.Meta.version == v2
      onlyPassing: true
---
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceSplitter
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  splits:
  - weight: 90
    service: reviews
    serviceSubset: v1
  - weight: 10
    service: reviews
    serviceSubset: v2
```

These are the Kubernetes CRD forms of Consul config entries and require the configured Consul controller/RBAC. Service metadata in the Consul catalog must actually contain `version=v1/v2`; a Kubernetes Pod label alone is not proof of catalog metadata. HTTP protocol and resolver subsets complete the split definition. Review Kubernetes-to-Consul namespace/service mapping and healthy endpoints rather than applying several owners to the same config entry.


## Security

Encryption, peer identity, caller authorization and application authentication are separate controls. Automatic mTLS between enrolled proxies does not mean all unmeshed traffic is denied or every caller is authorized.

### Istio: Inbound mTLS and Request Authorization

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: reviews-strict
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: reviews
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: reviews
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/mesh-demo/sa/productpage
    to:
    - operation:
        methods:
        - GET
        paths:
        - /reviews/*
```

This sidecar example requires the actual productpage ServiceAccount identity and reviews workload. Auto mTLS can select the appropriate outbound transport; a blanket `*.local` ISTIO_MUTUAL DestinationRule is not required and can break unrelated/plaintext destinations. STRICT is inbound enforcement, while the ALLOW policy controls the shown identity/method/path.

AuthorizationPolicy string matching is exact, prefix, suffix or presence matching; `*Mobile*` is not a general substring-regex match. User-Agent also is not a workload identity. Ambient L7 attachment requires the supported waypoint policy model rather than copying a sidecar selector unchanged.

### Linkerd: Explicit Inbound Policy

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: reviews-http
  namespace: mesh-demo
spec:
  podSelector:
    matchLabels:
      app: reviews
  port: 9080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  parentRefs:
  - group: policy.linkerd.io
    kind: Server
    name: reviews-http
  rules:
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /reviews/
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: reviews-read
  namespace: mesh-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: reviews-read
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: productpage
```

The Server selects an actual declared Pod port and defaults here to deny. The inbound HTTPRoute selects GET requests under `/reviews/`; the AuthorizationPolicy requires the productpage ServiceAccount. Target API groups are explicit: omitting a group means the core group, not an inferred Linkerd Server. A missing/wrong reference does not create an authorization grant.

The checked edge CRDs serve Server v1beta3 and older versions, including v1beta1; the older API is not claimed removed. Use the API versions supported by the selected artifact. The namespace/pod default `all-unauthenticated` policy is distinct from automatic encryption between meshed peers, and from this explicit Server policy.

### Kong Mesh: Enable mTLS with Deliberate Permissions

The basic installation does not automatically encrypt all service traffic. Plan permissions before enabling mTLS on existing workloads, because communication without matching permissions can be blocked. The minimal Mesh configuration is:

```yaml
apiVersion: kuma.io/v1alpha1
kind: Mesh
metadata:
  name: default
spec:
  mtls:
    enabledBackend: ca-1
    backends:
    - name: ca-1
      type: builtin
```

A restricted service-level example is:

```yaml
apiVersion: kuma.io/v1alpha1
kind: MeshTrafficPermission
metadata:
  name: productpage-to-reviews
  namespace: mesh-demo
  labels:
    kuma.io/mesh: default
spec:
  targetRef:
    kind: Dataplane
    labels:
      app: reviews
  from:
  - targetRef:
      kind: MeshSubset
      tags:
        kuma.io/service: productpage
    default:
      action: Allow
```

Replace `productpage` with the actual source `kuma.io/service` identity tag and verify target Dataplane labels/namespace. It is not guaranteed to equal a bare Kubernetes Service name. This permission is service-level authorization, not equivalent to the Istio/Linkerd GET/path rules above. Do not mix it with legacy TrafficPermission. Required transport, identity and policy resources must be ready before changing production enforcement.

### Consul: L7 Intentions

```yaml
apiVersion: consul.hashicorp.com/v1alpha1
kind: ServiceIntentions
metadata:
  name: reviews
  namespace: mesh-demo
spec:
  destination:
    name: reviews
  sources:
  - name: productpage
    permissions:
    - action: allow
      http:
        methods:
        - GET
        pathPrefix: /reviews/
```

Consul service identities and the HTTP protocol configuration must match the catalog and actual proxies. L7 permissions show why “Consul only has basic service-level authorization” is inaccurate. Do not combine a source's L4 action with its L7 permissions as though both independently apply. Review other intentions/default policy, namespaces/partitions and the controller's mapping.

A mesh config entry's TLS minimum version changes a TLS setting; it does not enroll an application, install a proxy or create a complete CA/ACL configuration. Envoy extensions and escape-hatch APIs also require the permissions of the actual Consul release; the 2.0.4 release tightens mesh:write requirements for code-executing extensions.

## Observability

Metric count is not a meaningful fixed ranking: enabled stats, dimensions, policy, scraping and application instrumentation affect both signal and overhead. EnvoyFilter is not an unlimited telemetry extension API, and all tracing backends are not interchangeable without compatible protocols/exporters.

| Mesh | Configure and verify |
|---|---|
| Istio | Telemetry APIs, actual proxy/control-plane metrics, access-log format, tracing provider and backends; optional Kiali/Grafana integration |
| Linkerd | Proxy golden/per-route metrics, selected viz or external monitoring setup, and configured proxy/application tracing |
| Kong Mesh | MeshMetric, MeshTrace and MeshAccessLog with supported backends; GUI/control-plane availability and access configured separately |
| Consul | Proxy/agent metrics, configured tracing and UI metrics provider with real endpoint/authentication settings |

For end-to-end traces, propagate context across application calls, initiate/sample traces as required and configure collector/backend delivery. Linkerd explicitly documents those requirements; a proxy span alone is not the complete application trace. An OpenTelemetry collector can bridge supported protocols, but its presence is not proof of every product/backend combination.

With the relevant components already installed and authorized, useful inspection commands include:

```bash
istioctl dashboard kiali -n istio-system
linkerd viz check
linkerd viz stat deploy -n mesh-demo
linkerd viz dashboard
```

These do not install dashboards or backends. Kiali's current configuration and compatibility must be checked separately; the old accessible_namespaces example and legacy Istio bundled-addon values are not a current installation recipe. See the [observability guide](../observability/README.md) for maintained configurations and validation limits. Kong GUI is not enabled by an otherwise empty Mesh metrics backend, and a Consul UI metrics URL must resolve from the actual server environment.

## Multicluster

| System | Discovery/data path | Important boundary |
|---|---|---|
| Istio | Each primary reads authorized Kubernetes APIs; cross-network traffic uses configured east-west gateways | Remote secrets do not copy CRDs or establish network/trust. Sidecar and ambient support different topologies. |
| Linkerd | Local mirrored Services describe remote services; hierarchical mode uses the **target** gateway; flat mode supports direct Pod paths | The mirror is in the source cluster. A source gateway is not inherently required. Federated Services use the flat model and do not support headless members. |
| Kong Mesh | KDS exchanges zone/service resources; destination zone ingress and optional source zone egress carry cross-zone traffic | Locality/failover behavior comes from the applicable policy and eligible endpoints; no inherent 80/20 split or unconditional failover. |
| Consul | Supported cluster peering or WAN-federation model with discovery and mesh-gateway paths | Pick the actual topology and configure trust, exported services, authorization and routing; names alone do not join clusters. |

![A schematic Consul WAN-federated datacenter pattern with Consul servers and mesh gateways. Cluster peering is a separate configuration model.](../../../.gitbook/assets/en-service-mesh-istio-comparison-01-service-mesh-comparison-16.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-comparison-01-service-mesh-comparison-16.html)

The original “Linkerd maximum about ten clusters” and generic “dozens” limits had no quota/load-test source. Capacity depends on the actual control/data-plane topology, service/endpoint count, update rate and resources. Automatic service discovery is not automatic policy replication or application/data disaster recovery.

Check remote API/gateway reachability, certificate trust, DNS, namespace/service identity, exported services and failure behavior in both directions. Prefer the [maintained Istio multicluster guide](../advanced/02-multi-cluster.md) to the former two install commands with meshID labels and one secret: those commands were not a complete mesh setup.

## Installation and Operations

### Versions Are Independent Inputs

| Checked source/artifact | Compatibility evidence and limitation |
|---|---|
| Istio 1.31.0 | Supported Kubernetes 1.32–1.36; follow its actual upgrade/skew rules and platform requirements |
| Linkerd edge-26.9.1 CLI/CRDs | Edge guidance belongs to that artifact. The separate published **2.20** table lists Kubernetes 1.31–1.35 and Gateway API 1.2.1–1.5.1; do not treat these as automatic bounds for every later edge/vendor build. |
| Kong Mesh/chart 2.14.4 | Released September 3 with Kuma 2.14.4. The published Kubernetes validation table currently stops at 2.13; no 2.14 compatibility certification is inferred from a chart render. The support table separately lists 2.13 LTS. |
| Consul/chart 2.0.4 | Released application and Helm artifact checked separately. The chart's Kubernetes minimum is metadata, not a complete supported-version matrix or upgrade assessment. |

Gateway API CRDs are cluster-wide dependencies shared by controllers. Do not blindly install the catalog's latest version or downgrade an existing bundle without checking every consumer.

### Istio Revision Handoff

Use the matching CLI and a supported upgrade path from the installed version. The historical 1.24 label in this article is not authorization to jump directly to 1.31. Preserve the reviewed installation values, gateway/CNI settings and revision ownership.

An illustrative default-profile input can set control-plane resources/HPA bounds:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: default
  components:
    pilot:
      k8s:
        hpaSpec:
          minReplicas: 3
          maxReplicas: 10
        resources:
          requests:
            cpu: 2000m
            memory: 4Gi
```

There is no built-in `production` profile. These CPU/memory/replica numbers are sizing inputs, not a production capacity guarantee. Installing another revision alone does not upgrade existing proxies:

```bash
istioctl install -f reviewed-istio.yaml --revision 1-31-0
kubectl label namespace mesh-demo istio-injection-
kubectl label namespace mesh-demo istio.io/rev=1-31-0 --overwrite
: "${DEPLOYMENT:?Set the actual staged Deployment name}"
kubectl rollout restart deployment/"$DEPLOYMENT" -n mesh-demo
kubectl rollout status deployment/"$DEPLOYMENT" -n mesh-demo
```

Review existing namespace and Pod overrides before the handoff. A legacy injection label can take precedence over revision selection. Restart only the intended workload cohort; gateway and ambient components have their own upgrade procedures. Canary revisions do not guarantee zero errors during every application rollout.

### Linkerd Installation and Upgrade

Select an explicit edge or vendor artifact and its compatible Gateway API first. For the current upstream CLI workflow:

```bash
linkerd check --pre
linkerd install --crds > linkerd-crds.yaml
kubectl apply -f linkerd-crds.yaml
linkerd install > linkerd-control-plane.yaml
kubectl apply -f linkerd-control-plane.yaml
linkerd check
```

This is a lab-oriented CLI flow; production installation guidance recommends Helm for repeatability and reviewed identity settings. Annotating a namespace enables injection for newly created Pods, not immediate proxy insertion into running Pods. Upgrade CRDs/control plane using the selected release's procedure and then roll workloads deliberately to update data-plane proxies; no automatic workload rollout is implied.

### Kong and Consul Chart Inspection

These commands obtain and render the exact checked charts for review; they do not deploy a production system:

```bash
helm repo add kong-mesh https://kong.github.io/kong-mesh-charts
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update kong-mesh hashicorp
helm show values kong-mesh/kong-mesh --version 2.14.4 > kong-values.reference.yaml
helm show values hashicorp/consul --version 2.0.4 > consul-values.reference.yaml
helm template kong-mesh kong-mesh/kong-mesh --version 2.14.4   --namespace kong-mesh-system --include-crds --values reviewed-kong-values.yaml
helm template consul hashicorp/consul --version 2.0.4   --namespace consul --include-crds --values reviewed-consul-values.yaml
```

The reviewed values files are environment-specific inputs, not files supplied by this comparison. Confirm Kubernetes support, edition/license, CA/ACL/bootstrap identity, storage, HA, injector/controller settings and upgrade notes before following each product's installation guide. A successful Helm render proves neither runtime readiness nor a safe in-place upgrade.

### Troubleshooting

```bash
istioctl proxy-status
istioctl analyze -n mesh-demo
istioctl proxy-config clusters "$POD" -n mesh-demo
linkerd check
linkerd viz stat deploy -n mesh-demo
kubectl get meshhttproutes,meshtrafficpermissions -n mesh-demo
kubectl get servicedefaults,serviceresolvers,servicesplitters -n mesh-demo
```

Run product-specific commands only in the intended installed environment. Inspect actual component names and logs rather than assuming every Consul sidecar has a fixed historical container name. Tap/debug logs can expose request information; scope and restore temporary diagnostic settings. Measure the team's work on the real workflow rather than claiming an eight-hour or five-minute installation for every organization.


## Cost and Licensing

### Original Cost Inputs Are Not a Quote

The original 100-Pod/m5.xlarge table assigned a $300 baseline and these additional monthly amounts:

| Original product input | Control-plane CPU/memory | Aggregate proxy CPU/memory | Former extra monthly amount |
|---|---|---|---:|
| Linkerd |300m / 500 MB|2 vCPU / 5 GB|$50|
| Istio |1 vCPU / 2 GB|10 vCPU / 15 GB|$150|
| Kong Mesh |500m / 1 GB|8 vCPU / 12 GB|$120|
| Consul |1 vCPU / 2 GB|10 vCPU / 14 GB|$145|

No Region, node count, operating hours, purchase model, allocation formula or billing data supported those prices. Resource requests do not automatically buy fractional EC2 nodes, and released headroom does not necessarily reduce a bill. Retain these only as former hypothetical inputs; do not use them to choose the cheapest product.

The former staffing assumptions were initial setup 40/8/20/24 hours, monthly operations 20/5/10/12 hours, monthly troubleshooting 15/3/8/10 hours and quarterly upgrades 8/2/4/5 hours for Istio/Linkerd/Kong/Consul respectively. They are not measured team productivity, and initial setup is not a recurring monthly expense.

A meaningful cost model uses actual retained capacity, HA and autoscaling constraints, load balancers/transfer, storage/telemetry, platform charges, support subscriptions and observed engineering effort. Compare the same workload, security and availability requirement and state every unit/rate/date. Calculate ROI only from a substantiated difference and migration cost.

### Artifact and Product Licenses

| Component | Distinction to retain |
|---|---|
| Istio | Apache-licensed upstream project; hosted/commercial distributions have their own terms and costs |
| Linkerd | Apache-licensed upstream project; upstream edge artifacts and vendor stable distributions are different release/support choices |
| Kuma / Kong Mesh | Upstream Kuma and the commercial Kong Mesh product are distinct; verify the chosen edition and support contract |
| Consul | The checked **Consul 2.0.4 application** license is Business Source License 1.1 with its stated use grant and later MPL change conditions, not simply current MPL-2.0 |

Consul's Helm chart advertises an MPL license for that artifact; it does not override the application binary's license. Review the exact artifact/version terms. Linkerd HA control-plane configuration is not inherently an enterprise-only feature; paid support/SLA and product features must be distinguished from upstream capabilities. Do not infer support from one vendor name or a dollar-sign ranking.

## Selection and Validation

| Situation | Questions that determine the choice |
|---|---|
| Large deployment | Which exact routing/security APIs, endpoint/update scale and HA behavior are required? |
| Small team or quick start | Which lifecycle and troubleshooting workflow can the team operate, including identity and upgrades? |
| Resource constraints | What does an equivalent-policy workload actually consume, including all proxies, waypoints, gateways and telemetry? |
| VM or legacy workload | Does the documented identity/network/runtime integration fit? Istio and Linkerd also have VM integration paths. |
| Multicloud or multicluster | Which trust, API, data-plane, policy distribution and disaster-recovery boundaries are needed? |
| Strong observability | Which application/proxy signals, collector/exporter paths, retention and access controls are required? |

A Service ExternalName alone does not mesh a VM or create a proxy identity. A data-plane binary additionally needs supported registration, credentials, network redirection and actual control-plane connectivity. Similarly, setting meshID/network strings on two Istio installations is not a complete multicluster design.

Use a bounded proof of concept with the actual workloads and required policies, retain reproducible measurements and test failure/recovery. The [comparison index](README.md) and [Istio versus VPC Lattice guide](02-istio-vs-lattice.md) provide related decision criteria. Product choice is not determined by service count, a generic “most features” label or an unsupported quick-ROI claim.

## Official References

- [Istio architecture](https://istio.io/latest/docs/ops/deployment/architecture/) and [supported releases](https://istio.io/latest/docs/releases/supported-releases/)
- [Istio VM integration](https://istio.io/latest/docs/setup/install/virtual-machine/) and [multicluster](https://istio.io/latest/docs/setup/install/multicluster/)
- [Linkerd releases](https://linkerd.io/releases/), [Kubernetes compatibility](https://linkerd.io/docs/reference/k8s-versions/) and [Gateway API compatibility](https://linkerd.io/docs/features/gateway-api/)
- [Linkerd request routing](https://linkerd.io/docs/features/request-routing/), [HTTPRoute](https://linkerd.io/docs/reference/httproute/), [authorization](https://linkerd.io/docs/reference/authorization-policy/) and [rate limiting](https://linkerd.io/docs/features/rate-limiting/)
- [Linkerd multicluster](https://linkerd.io/docs/features/multicluster/), [VM expansion](https://linkerd.io/docs/tasks/adding-non-kubernetes-workloads/) and [tracing](https://linkerd.io/docs/features/distributed-tracing/)
- [Kong Mesh changelog](https://developer.konghq.com/mesh/changelog/), [support](https://developer.konghq.com/mesh/support-policy/) and [validated versions](https://developer.konghq.com/mesh/version-compatibility/)
- [Kong MeshHTTPRoute](https://developer.konghq.com/mesh/policies/meshhttproute/), [MeshTrafficPermission](https://developer.konghq.com/mesh/policies/meshtrafficpermission/) and [load-balancing policy](https://developer.konghq.com/mesh/policies/meshloadbalancingstrategy/)
- [Kong multi-zone deployment](https://developer.konghq.com/mesh/mesh-multizone-service-deployment/) and [installation](https://developer.konghq.com/mesh/deploy-mesh-self-managed/)
- [Consul proxies](https://developer.hashicorp.com/consul/docs/connect/proxy), [service defaults](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-defaults), [resolver](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-resolver), [splitter](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-splitter) and [intentions](https://developer.hashicorp.com/consul/docs/reference/config-entry/service-intentions)
- [Consul 2.0.4 application license](https://raw.githubusercontent.com/hashicorp/consul/v2.0.4/LICENSE)
- [Istio architecture in this guide](../03-architecture.md)
