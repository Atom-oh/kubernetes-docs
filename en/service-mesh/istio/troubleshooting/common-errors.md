# Istio Common Errors and Solutions

> **Reviewed**: September 11, 2026 · CLI/configuration checks: Istio 1.31.0

Start with the observed failure, effective configuration and workload mode. The commands below are diagnostic examples, not instructions to reset the mesh. Check the [installation compatibility guidance](../01-installation.md) for your Kubernetes/EKS version.

Examples use an existing application namespace app, Deployment/Service myapp on port 8080, an ingress namespace istio-ingress and the default cluster DNS suffix. Replace these with actual resources and domains. Deployment YAML blocks are **strategic-merge fragments for an existing Deployment**, not complete new applications. No cluster deployment or production workload test was performed in this review.

```bash
NS=app
GW_NS=istio-ingress
ISTIO_NS=istio-system
: "${POD:?Set the exact application Pod name}"
kubectl config current-context
istioctl version
kubectl -n "$NS" get pod "$POD" -o wide
```

## Table of Contents

1. [Connection Errors During Pod Termination](#connection-errors-during-pod-termination)
2. [Sidecar Injection Issues](#sidecar-injection-issues)
3. [mTLS Connection Failure](#mtls-connection-failure)
4. [VirtualService Routing Failure](#virtualservice-routing-failure)
5. [Gateway Configuration Issues](#gateway-configuration-issues)
6. [Memory and Performance Issues](#memory-and-performance-issues)
7. [Certificate Expiration](#certificate-expiration)
8. [DNS Resolution Failure](#dns-resolution-failure)
9. [Envoy Initialization Timeout](#envoy-initialization-timeout)
10. [Debugging Tools](#debugging-tools)

## Connection Errors During Pod Termination

### Problem Description

Connection reset, broken pipe, EOF and HTTP 503 can occur during shutdown. They do not, by themselves, prove that Envoy exited first. Correlate application/proxy logs, response flags, Pod deletion time and EndpointSlice changes.

### Root Cause

Traditional application containers and a sidecar listed under containers have no guaranteed shutdown order. A proxy can exit while the application still needs it; the application can also stop accepting work before existing requests finish. Kubernetes native sidecars instead use initContainers with restartPolicy:Always and are terminated after the main containers.

The Pod grace period includes preStop execution. It is not always 30 seconds, and processes that already exited are not later killed again. Endpoint updates, load balancer propagation and long-lived connections can create additional failure windows.

### Solutions

#### Method 1: Budget application and proxy shutdown

This annotation configures proxy drain; it does **not** install a preStop hook or wait unconditionally for every active request:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      terminationGracePeriodSeconds: 60
```

The 30/60-second values are examples, not universal minimums. Budget application shutdown, hooks and proxy drain together. holdApplicationUntilProxyStarts concerns **startup**, not shutdown ordering. ProxyConfig changes require new Pods to take effect.

In 1.31, the ordinary terminationDrainDuration path is time-based. When EXIT_ON_ZERO_ACTIVE_CONNECTIONS is enabled, the agent instead waits its minimum drain period and polls downstream listener connection counts; that path does not use the ordinary drain timer as a fixed upper bound. Kubernetes grace limits and missing/error statistics still apply. Validate the selected behavior under representative connections.

#### Method 2: Consider native sidecar ordering

For a supported Kubernetes/Istio combination, this annotation selects native injection for newly created, injection-eligible Pods:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
      labels: {}
    spec: {}
```

The Kubernetes feature is stable from 1.33; Istio's native-sidecar annotation is documented Alpha. Verify actual injected initContainers and application shutdown behavior. Ordering alone does not guarantee zero failed requests or wait forever beyond the Pod's grace period. Ambient workloads have no per-Pod Envoy to configure this way.

There is no documented sidecar.istio.io/terminationGracePeriodSeconds annotation. Set the real spec.terminationGracePeriodSeconds field.

#### Method 3: Installation-wide defaults

The following is an **istioctl installation input**, not a resource to reconcile with the removed in-cluster Istio operator:

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    defaultConfig:
      terminationDrainDuration: 30s
      holdApplicationUntilProxyStarts: true
```

Review the rendered change through the installation's owner and roll out affected workloads deliberately. The former shell/netstat preStop loop was unbounded, counted listening sockets and assumed utilities exist in the proxy image. It did not reliably wait for application work to finish.

### Verification Method

```bash
kubectl -n "$NS" get pod "$POD" -o json
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
kubectl -n "$NS" get events --field-selector "involvedObject.name=$POD"
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Capture logs while the Pod still exists. --previous retrieves a previous container instance in the same Pod; it does not mean “current container while terminating,” nor recover arbitrary deleted-Pod logs.

### Best Practices

Implement application SIGTERM handling and a real readiness contract. Creating /tmp/not-ready changes nothing unless the application or probe reads it. A bounded preStop delay may provide propagation time, but it neither proves endpoint convergence nor replaces graceful application shutdown. There is no universal prohibition on application sleep and no universal 60-second minimum. Measure raw HTTP/non-HTTP failures with write retries disabled; see the [rollout comparison](../comparison/03-sidecar-vs-ambient.md).

## Sidecar Injection Issues

### Issue 1: Sidecar Not Injected

Check both regular and native sidecar locations before concluding that a proxy is absent:

```bash
kubectl -n "$NS" get pod "$POD" -o jsonpath='{.spec.containers[*].name}{"\n"}{.spec.initContainers[*].name}{"\n"}'
kubectl get namespace "$NS" --show-labels
kubectl -n "$NS" get deployment myapp -o yaml
istioctl x check-inject "$POD" -n "$NS"
kubectl get mutatingwebhookconfigurations
kubectl -n "$ISTIO_NS" get pods -l app=istiod --show-labels
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

Ambient enrollment intentionally has no istio-proxy application sidecar. For sidecar mode, inspect the namespace revision/tag, Pod-template labels, hostNetwork, webhook selectors and admission events. Automatic injection excludes host-network Pods and designated system namespaces.

Use the intended installation's revision/tag or legacy injection label, following the [injection guide](../advanced/07-sidecar-injection.md). Do not combine conflicting istio-injection and istio.io/rev selection. Labels affect newly created Pods; they do not retrofit an existing Pod. Recreate only the intended workload through its rollout owner after reviewing the effect.

The preferred per-Pod override is a **label** under the workload's Pod template:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations: {}
      labels:
        sidecar.istio.io/inject: 'true'
    spec: {}
```

The corresponding annotation is deprecated. A false label can be an intentional exclusion, not an error to overwrite blindly. A true label still does not bypass every webhook-selection or platform restriction. Injection is served by Istiod; the old app=sidecar-injector log selector does not identify the current integrated injector.

### Issue 2: Sidecar Resource Shortage

Inspect container termination reasons, events, usage and throttling. OOMKilled can indicate a memory limit problem; CrashLoopBackOff is a restart/backoff state with many possible causes. A runAsNonRoot/non-numeric-user validation error is a security-context/image problem and is not fixed by more RAM.

If measurements justify a resource change, set requests and limits together on the Pod template. These example quantities need workload-specific sizing:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        sidecar.istio.io/proxyCPU: 200m
        sidecar.istio.io/proxyCPULimit: 1000m
        sidecar.istio.io/proxyMemory: 256Mi
        sidecar.istio.io/proxyMemoryLimit: 512Mi
      labels: {}
    spec: {}
```

Validate the newly injected resource settings and namespace LimitRange/ResourceQuota. Avoid overwriting image security settings merely to get past admission.

## mTLS Connection Failure

### Problem Description

Upstream connect errors,503s and WRONG_VERSION_NUMBER can have TLS, protocol, endpoint or network causes. PeerAuthentication controls **accepted inbound mTLS**. DestinationRule TLS settings control outbound TLS from the client-side Envoy. Setting the client's PeerAuthentication to STRICT does not itself force that client to originate mTLS.

### PeerAuthentication and DestinationRule

With auto mTLS enabled and no explicit DestinationRule TLS override, Istio selects workload mTLS for known mesh endpoints. An explicit DISABLE override can conflict with a destination requiring STRICT. Remove an unintended override through its owner or use ISTIO_MUTUAL for a deliberately configured Istio-mTLS destination; do not force it on arbitrary external TLS/plaintext services.

The following selector-free policy applies to the **app namespace** after its callers are ready for strict enforcement:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

A selector-free policy in the configured root namespace (usually istio-system) has mesh-wide scope, not merely that namespace's services. Review migration impact before enforcing it. Ambient does not support disabling its transport mTLS with PeerAuthentication DISABLE. Authentication and AuthorizationPolicy are separate; a 403 is not automatically a TLS failure.

### Debugging Commands

```bash
istioctl x describe pod "$POD" -n "$NS"
kubectl get peerauthentication -A -o yaml
kubectl get destinationrule -A -o yaml
istioctl proxy-config clusters "$POD" -n "$NS" \
  --fqdn myapp.app.svc.cluster.local -o json
istioctl proxy-config secret "$POD" -n "$NS"
```

Use the relevant caller proxy for outbound cluster configuration and the receiving proxy for inbound policy. The experimental describe command is a diagnostic aid, not proof that all paths are encrypted. Inspect certificate validity, identity, trust domain, actual transport socket and response flags. Waypoint and ztunnel diagnostics differ; see the [mTLS guide](../security/01-mtls.md).

## VirtualService Routing Failure

### Issue 1: Traffic Not Being Routed

A404 can come from Envoy or the application. Identify its source and response details before changing routes. A VirtualService with hosts:myapp.example.com routing to the internal Service myapp is **valid** when attached to the appropriate gateway and matched by the request's Host/authority. Frontend host and backend service name need not be identical.

For mesh traffic, match the requested service host; for ingress traffic, match the gateway's admitted domain and attach the VirtualService to that gateway. Short destination names are resolved relative to the configuration resource's namespace, so explicit FQDNs reduce cross-namespace ambiguity.

### Issue 2: Subset Not Found or No Healthy Upstream

This complete pair shows mesh routing to a named subset:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: myapp
  namespace: app
spec:
  host: myapp.app.svc.cluster.local
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

The Service must actually select ready endpoints labeled version:v 1. A matching DestinationRule subset name alone does not create Pods, fix a Service selector or make endpoints healthy. Check the destination Service port, protocol selection, policy visibility and competing routes. The namespace/host examples above assume the default cluster.local suffix.

### Debugging

```bash
istioctl analyze -n "$NS"
istioctl proxy-config routes "$POD" -n "$NS"
istioctl proxy-config endpoints "$POD" -n "$NS"
kubectl -n "$NS" get svc myapp -o yaml
kubectl -n "$NS" get pods -l app=myapp --show-labels
kubectl -n "$NS" get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=myapp -o yaml
```

Analyze is static configuration assistance; inspect the effective route/cluster/endpoints on the proxy actually carrying the request. Configuration propagation is not instantaneous. An ingress request routed to a Service does not automatically inherit another mesh-only VirtualService's subset selection.


## Gateway Configuration Issues

### Issue 1: Traffic Not Reaching Gateway

Connection refused or timeout before an HTTP response can indicate DNS, listener/Service-port mismatch, missing load balancer targets or network filtering. First locate the actual gateway Deployment/Service; its namespace and name depend on the installation method.

```bash
kubectl -n "$GW_NS" get svc,pods --show-labels
kubectl -n "$GW_NS" get gateways.networking.istio.io -o yaml
kubectl -n "$NS" get virtualservice -o yaml
# For installations using Kubernetes Gateway API instead:
kubectl get gatewayclasses.gateway.networking.k8s.io
kubectl -n "$GW_NS" get gateways.gateway.networking.k8s.io -o yaml
kubectl -n "$NS" get httproutes.gateway.networking.k8s.io -o yaml
```

Inspect the Service's loadBalancer ingress fields: providers can publish an IP, hostname or both. On EKS also check the load balancer target health, target type, security groups and network path using the controller's actual configuration; restarting Istiod does not repair an unhealthy AWS target.

Istio Gateway (networking.istio.io) and Kubernetes Gateway API (gateway.networking.k 8s.io) are different resources. For Gateway API inspect Accepted, Programmed and HTTPRoute parent conditions such as ResolvedRefs, along with controller events. A gateway name typo, listener mismatch or denied route attachment needs a different fix from an external connectivity failure.

### Issue 2: HTTPS and Route Attachment

This example uses the **Istio Gateway API**. Replace the selector with the actual gateway Pod labels, use your owned domain and a valid certificate, and ensure the Deployment's Service exposes 443. It uses the same backend subset defined in the preceding section:

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: myapp-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls-secret
    hosts:
    - myapp.example.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-ingress
  namespace: app
spec:
  hosts:
  - myapp.example.com
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
  gateways:
  - istio-ingress/myapp-gateway
```

Here SIMPLE terminates downstream TLS, so the route uses http. A TLS PASSTHROUGH listener instead needs appropriate TLS/SNI routing. Do not mix a terminating listener with only a tls route or expect HTTP path matching inside opaque passthrough traffic.

credentialName refers to a credential accessible to the gateway workload. For this example the gateway Pod and TLS Secret are in istio-ingress:

```bash
kubectl -n "$GW_NS" create secret tls myapp-tls-secret   --cert=path/to/fullchain.pem   --key=path/to/key.pem
```

Use the existing certificate owner's renewal process if that Secret is already managed. This command does not obtain a certificate or make a self-signed issuer trusted. Check domain/SAN matching, the served chain, expiry, client trust and gateway SDS status. The namespace of a separate Gateway configuration object is not a universal substitute for the gateway workload's credential namespace.

## Memory and Performance Issues

### Issue 1: Envoy Memory Usage Increase

Compare actual container memory/CPU, limits, connections, routes/clusters/listeners and telemetry cardinality. A large unrelated ConfigMap or Secret is not automatically loaded into every proxy; only configuration and data consumed by that proxy can explain its footprint. A memory leak needs version-specific evidence.

Where unused configuration dominates, a scoped Sidecar resource can limit configuration imported by a selected **sidecar** workload:

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: myapp-scope
  namespace: app
spec:
  workloadSelector:
    labels:
      app: myapp
  egress:
  - hosts:
    - ./*
    - istio-system/*
```

This example includes only services in app and istio-system. Inventory actual cross-namespace/external dependencies before narrowing imports and avoid overlapping Sidecar selectors. This is configuration scoping, not an egress firewall or an ambient waypoint policy. Size memory requests/limits from observed behavior, using the Pod-template annotations shown earlier.

### Issue 2: High Latency

A P99 above one second is a symptom only relative to a defined workload budget. Check application time, upstream latency, saturation, CPU throttling, connection pools, payloads and retry amplification before changing timeouts.

The following is an **alternative** to the earlier myapp VirtualService, adding a five-second route deadline with retries explicitly disabled:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: app
spec:
  hosts:
  - myapp.app.svc.cluster.local
  http:
  - route:
    - destination:
        host: myapp.app.svc.cluster.local
        subset: v1
        port:
          number: 8080
    retries:
      attempts: 0
    timeout: 5s
```

A deadline bounds waiting; it does not make the backend faster. Blind retries can amplify overload and repeat ambiguous writes. If retries are appropriate for a particular idempotent operation, budget them explicitly against the end-to-end deadline and measure actual attempts. See [Retry and Timeout](../traffic-management/05-retry-timeout.md).

## Certificate Expiration

### Problem Description

x 509 expiry and handshake failures can concern the workload leaf certificate, a signing intermediate/root, an ingress certificate or clock skew. Validity periods depend on the CA/provider and configuration; “ten years” or “24 hours” is not a universal diagnosis.

### Diagnosis and Recovery

Inspect the actual public trust bundle and loaded workload certificates:

```bash
# Public trust bundle, not a private CA key.
kubectl -n "$NS" get configmap istio-ca-root-cert \
  -o jsonpath='{.data.root-cert\.pem}' > root-cert.pem
openssl crl2pkcs7 -nocrl -certfile root-cert.pem |
  openssl pkcs7 -print_certs -text -noout
istioctl proxy-config secret "$POD" -n "$NS"
kubectl -n "$ISTIO_NS" logs -l app=istiod --all-containers=true --tail=200
```

The standard trust ConfigMap may differ with a custom integration; inspect the configured CA provider. The PKCS7 inspection displays all certificates in the PEM bundle, not just its first certificate. Correlate validity with current UTC time, CA/CSR errors, identity tokens, Istiod/SDS reachability and the certificate renewal process.

istioctl 1.31 has no x ca root command. Do not delete or regenerate a CA merely because a leaf expired: an unplanned trust-root replacement can break every dependent workload. Repair the actual renewal/connectivity/provider problem and use the supported CA rotation procedure with required trust overlap. Restart only specifically affected workloads when the recovery process requires it.

## DNS Resolution Failure

### Problem Description

For no-such-host or lookup timeout, distinguish application DNS, CoreDNS/upstream DNS, Service existence/search suffixes and Istio DNS capture.

```bash
kubectl -n kube-system get svc kube-dns
kubectl -n kube-system get pods -l k8s-app=kube-dns
kubectl -n kube-system get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=kube-dns
# Run from the affected app container only if it includes these tools.
kubectl -n "$NS" exec "$POD" -c myapp -- cat /etc/resolv.conf
kubectl -n "$NS" exec "$POD" -c myapp -- nslookup myapp.app.svc.cluster.local
```

Do not assume the minimal application or proxy image includes diagnostic utilities. Use an approved diagnostic container when necessary. Check NetworkPolicy for both UDP/TCP 53, node/resolver reachability and the affected Pod's dnsPolicy/search configuration.

A ServiceEntry registers an external service in Istio; it does not repair CoreDNS, create a public DNS record or make an unresolved upstream hostname resolvable:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: app
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

Replace api.example.com with the actual external hostname. DNS resolution determines upstream endpoints. Depending on mode, version and configuration, Istio DNS capture/IP allocation can answer service names with synthetic addresses; this still does not prove that the real upstream endpoint resolves or is reachable. Check [DNS capture guidance](../advanced/04-dns-cache.md). For an application already sending HTTPS, declaring HTTPS here does not require adding a second TLS-origination layer.

## Envoy Initialization Timeout

### Problem Description

“Waiting for Envoy proxy to be ready” can result from xDS/CA connectivity, rejected configuration, resources, certificate/token problems or bootstrap settings. Check Pod/init-container states, proxy/Istiod logs, events and proxy-status before increasing probe delays.

holdApplicationUntilProxyStarts delays application startup until the proxy is ready; it does not repair an Envoy that cannot become ready. A readinessProbe with only initialDelaySeconds is invalid because it has no probe action.

If the application actually implements /ready on 8080, this fragment provides a concrete startup/readiness contract:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: app
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          holdApplicationUntilProxyStarts: true
      labels: {}
    spec:
      containers:
      - name: myapp
        startupProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          periodSeconds: 5
          failureThreshold: 3
```

Adapt the action and thresholds to the application. StartupProbe controls startup tolerance; readiness controls endpoint eligibility. Neither corrects broken Istiod reachability. Inspect the injected probe rewrites and effective proxy readiness settings before attributing an application probe failure to Envoy initialization.

## Debugging Tools

### istioctl Commands

```bash
istioctl analyze -A
istioctl proxy-status
istioctl proxy-config all "$POD" -n "$NS"
istioctl proxy-config log "$POD" -n "$NS"
# Temporarily change levels only on the selected Envoy.
istioctl proxy-config log "$POD" -n "$NS" --level http:debug
# Restore the previously recorded levels afterwards; --reset restores defaults.
istioctl bug-report --include "$NS" --duration 10m

# Ambient has ztunnel diagnostics; Envoy commands apply to waypoints.
istioctl ztunnel-config workloads -n "$ISTIO_NS"
istioctl ztunnel-config certificates -n "$ISTIO_NS"
```

Experimental commands may change and do not replace traffic verification. Keep a record of log levels before temporary debugging, then restore them; reset means the defaults, which may differ from previous custom settings. Limit diagnostic duration and review collected configuration/log data before sharing a bug-report archive.

### Envoy Admin API

Forward only to loopback:

```bash
# Keep this command running; use a second terminal for the HTTP requests.
kubectl -n "$NS" port-forward --address 127.0.0.1 "$POD" 15000:15000

```

In another terminal:

```bash
curl --fail --silent --show-error http://127.0.0.1:15000/clusters
curl --fail --silent --show-error http://127.0.0.1:15000/stats/prometheus
curl --fail --silent --show-error http://127.0.0.1:15000/config_dump
```

These commands apply to Envoy, including sidecars and waypoints, not ztunnel's different admin interface. Close the port-forward when finished. For logging changes prefer the selected-proxy istioctl command above and restore the recorded levels afterwards.

### Common Log Checking

```bash
kubectl -n "$NS" logs "$POD" -c myapp
kubectl -n "$NS" logs "$POD" -c istio-proxy
# Only when that container has a prior instance in this same Pod:
kubectl -n "$NS" logs "$POD" -c istio-proxy --previous
kubectl -n "$NS" logs -f "$POD" -c istio-proxy
```

Log collection from a running/current Pod is not retention for deleted Pods. Preserve the request time, trace/request ID, response flags and relevant endpoint/configuration changes with incident evidence.

## References

- [Injection troubleshooting](https://istio.io/latest/docs/ops/common-problems/injection/) and [injection configuration](https://istio.io/latest/docs/setup/additional-setup/sidecar-injection/)
- [Network issues](https://istio.io/latest/docs/ops/common-problems/network-issues/) and [TLS direction/auto mTLS](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio annotations](https://istio.io/latest/docs/reference/config/annotations/) and [released 1.31 proxy shutdown code](https://github.com/istio/istio/blob/1.31.0/pkg/envoy/agent.go)
- [Kubernetes Pod termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) and [native sidecars](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Proxy diagnostics](https://istio.io/latest/docs/ops/diagnostic-tools/proxy-cmd/), [CA integration](https://istio.io/latest/docs/tasks/security/cert-management/plugin-ca-cert/) and [secure ingress](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [Kubernetes DNS diagnosis](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) and [Istio DNS proxying](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Observability](../observability/README.md), [Security](../security/README.md), [Traffic Management](../traffic-management/README.md)
