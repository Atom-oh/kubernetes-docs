# Security and Visibility

> **Review baseline**: Cilium 1.20.1; Cilium CLI 0.20.0; Hubble CLI 1.19.4.
> **Last reviewed**: September 12, 2026. Kubernetes 1.33–1.36 is the Cilium 1.20 compatibility range; choose kubectl within the API server's supported version skew.

## Lab Environment Setup

Use an existing Cilium 1.20.1 test cluster with at least two schedulable Linux nodes, working DNS, and policy enforcement enabled. Follow [the installation and platform prerequisites](README.md), including the EKS restrictions and verified CLI downloads. These examples do not install or replace a CNI. They require Helm, kubectl, the Cilium and Hubble CLIs, and jq.

The lab assumes CoreDNS Pods labeled `k8s-app=kube-dns` in `kube-system`. Verify the actual resolver path; NodeLocal DNS or a different distribution needs different destinations/ports. Policies, proxy configuration and platform controls already present in the cluster can affect the results.

### Hubble Installation and Setup

Save `hubble-values.yaml`. This fragment enables the local servers, Relay, UI and selected metric plugins. Apply it to an **existing release at the same chart version**; review the retained installation values first. For a version upgrade, use the upgrade procedure instead of blindly reusing old values.

```yaml
# hubble-values.yaml
hubble:
  enabled: true
  relay:
    enabled: true
  ui:
    enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - tcp
    - flow
    - httpV2
    serviceMonitor:
      enabled: false
```
```bash
helm upgrade cilium cilium/cilium --namespace kube-system \
  --version 1.20.1 --reuse-values --values hubble-values.yaml --wait
cilium status --wait
# Terminal 1: keep this process running; stop it with Ctrl-C.
cilium hubble port-forward
```

In another terminal, verify API connectivity. Port forwarding stays local; it does not publish Relay or UI through a public LoadBalancer.

```bash
# Terminal 2
hubble status
hubble observe --last 20
# Optional UI; keep its local forwarding process running while using it.
cilium hubble ui
```

## Cilium's Security Features

Cilium combines network policy with endpoint identities and optional encryption. Hubble makes the resulting network events observable. Their boundaries matter when evaluating a security requirement.

### Cilium Security Architecture

| Responsibility | Component and scope |
| --- | --- |
| Network microsegmentation | Cilium L3/L4 policy selects identities, addresses, ports and directions. A namespaced CiliumNetworkPolicy selects endpoints in its namespace. |
| HTTP policy | Cilium's Envoy integration filters methods, paths and headers when the proxy can see HTTP. DNS policy uses the DNS proxy. |
| DNS/FQDN control | DNS rules control queries; `toFQDNs` permits destination IPs learned from observed DNS answers. This is not an automatic malicious-domain reputation feed. |
| Node transport encryption | IPsec or WireGuard protects supported traffic between nodes. Coverage depends on mode and configuration. |
| Network investigation | Hubble records flow metadata and policy verdicts; Relay, CLI and UI expose it. |
| Process and syscall security | **Tetragon** is a separate project for runtime events and configured enforcement. Enabling Hubble does not install it. |
| Threat detection and response | External alert rules, SIEM/WAF and response controllers must be configured for the intended detection and action. |

### Network and Application Security

Use least-privilege policy to limit lateral movement and explicit egress to limit dependencies. Security identities derive from security-relevant labels; they are not necessarily unique per Pod and do not authenticate an end user.

Current Cilium policy supports HTTP and DNS L7 rules. gRPC can use HTTP method/path/header rules where its HTTP/2 traffic is visible. Kafka topic policies are no longer supported. HTTP `headers` entries with values are literal matches, not regular-expression authentication. An `Authorization` header's presence or shape does not validate a JWT, its issuer, signature or authorization claims. Use the application's authentication layer or a configured gateway for that.

An HTTP rule on port 8443 does not decrypt HTTPS. TLS termination or a separately supported inspection arrangement is required before HTTP policy can evaluate encrypted application data. Do not bypass a service mesh's encryption merely to make L7 inspection work.

### Identity, Authentication and Encryption

Cilium's SPIRE-based **mutual authentication remains Beta**: it performs an out-of-band handshake for security identities. That handshake alone does not encrypt application traffic. Its documented limitations include no ClusterMesh support and no interoperability with arbitrary external mTLS systems. The separate **ztunnel workload mTLS feature is also Beta**; it has its own enrollment and certificate prerequisites. Neither feature should be presented as the automatic consequence of an identity selector.

### Encryption Configuration

The following are **alternative Helm fragments**, not two settings to enable together. Select one for a planned installation/change and validate the kernel, routing and platform prerequisites.

```yaml
# wireguard-values.yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
```
```yaml
# ipsec-values.yaml
encryption:
  enabled: true
  type: ipsec
  nodeEncryption: false
  ipsec:
    secretName: cilium-ipsec-keys
```

WireGuard requires kernel support and the node-to-node UDP path on port 51871. IPsec requires a correctly formatted, securely managed `cilium-ipsec-keys` Secret in Cilium's namespace before enabling it; follow the official key creation and rotation procedure. Merely naming a key file in a ConfigMap does not provision that key or its volume.

By default, these modes protect supported Cilium-managed Pod traffic crossing nodes; same-node traffic is not encrypted by these node tunnels. Traffic to arbitrary external destinations is not automatically covered. WireGuard node-to-node encryption is a separate Beta option; control-plane nodes are excluded from that extension by default, while their Cilium-managed cross-node Pod traffic can still be encrypted. Verify the actual packet path and use application TLS where required. Host firewall compatibility also depends on the encryption mode.

## Network Visibility with Hubble

Hubble receives datapath, proxy and agent events and enriches them with Kubernetes metadata. It is not simply a reader that periodically polls all eBPF maps.

```text
Kernel/datapath events + proxy/agent events
                  |
                  v
       Hubble server in each Cilium agent
          |             |                |
   bounded flow      metric endpoint   optional file exporter
      buffer          TCP 9965            |
          |             ^             log collector/storage
     Relay query        | scrape
          ^          Prometheus <--- Grafana queries
          |
       CLI / UI
```

The server maintains bounded in-memory history. Relay queries multiple servers; it is not a durable database. UI offers flow exploration and service dependency maps, while the CLI supports explicit filters. No matching records can mean no traffic, the wrong filter, unavailable peers, missing L7 visibility or overwritten/lost events.

### Hubble CLI Usage Examples

```bash
hubble observe --namespace cilium-security-demo --last 100
hubble observe --from-pod cilium-security-demo/frontend \
  --to-service cilium-security-demo/backend --last 100
hubble observe --namespace cilium-security-demo --protocol http \
  --http-status '4+' --http-status '5+' --last 100
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
hubble observe --pod cilium-security-demo/frontend --follow
```

`--pod namespace/name` matches either endpoint; use `--from-pod`/`--to-pod` for direction. Pod names are not label selectors: use `--from-label` or `--to-label` when selecting labels. Do not combine `--namespace` with `--from-pod`/`--to-pod`; the CLI rejects that combination.

`DROPPED` is a verdict. `POLICY_DENIED` is a drop reason, selected with `--drop-reason-desc`. HTTP status prefixes use `4+` and `5+`, not `4..` and `5..`. HTTP filters require proxy-derived L7 events; a dropped TCP connection need not have an HTTP status.

## Network Visibility and Monitoring

### Hubble Metrics

The enabled plugins expose different observations:

| Plugin | Example metric | Meaning and limit |
| --- | --- | --- |
| `flow` | `hubble_flows_processed_total` | Processed flow events by protocol/type/verdict; not unique requests or packets on every path. |
| `drop` | `hubble_drop_total{reason="POLICY_DENIED"}` | Observed drops; the reason label is the enum name. |
| `tcp` | `hubble_tcp_flags_total` | Observed TCP flags; not a general RTT, retransmission or concurrent-connection metric. |
| `dns` | `hubble_dns_queries_total`, `hubble_dns_responses_total` | Observed DNS queries/responses and response codes; not a generic DNS latency histogram. |
| `httpV2` | `hubble_http_requests_total`, `hubble_http_request_duration_seconds` | HTTP response-flow-derived request counts/status and duration in seconds. Requires HTTP visibility. |

Do not enable `http` and `httpV2` together. Choose source/destination labels carefully to control cardinality, and avoid adding request headers or sensitive identities without a reason. Check `hubble_lost_events_total` and peer availability before treating a missing event as proof that traffic did not occur.

### Prometheus Integration

The chart creates the headless `hubble-metrics` Service in the Cilium namespace, exposing port **9965** by default. Its Service label `k8s-app=hubble` is used for discovery; the Service selects agent Pods labeled `k8s-app=cilium`. Prometheus should discover the individual endpoints rather than rely on one static DNS target.

With an existing Prometheus Operator and ServiceMonitor CRD, merge this fragment into the release values. `release: monitoring` is an example: it must match your Prometheus `serviceMonitorSelector`, and its namespace selector must include the ServiceMonitor's namespace. A resource that Prometheus does not select will not be scraped.

```yaml
# hubble-servicemonitor-values.yaml
hubble:
  metrics:
    serviceMonitor:
      enabled: true
      labels:
        release: monitoring
```

The chart's ServiceMonitor uses the named port `hubble-metrics` and the Cilium namespace's endpoints. Without the Operator, configure equivalent Kubernetes service discovery in your actual Prometheus configuration. Creating an unrelated ConfigMap does not configure Prometheus. `*.hubble-metrics.cilium.io` is used in metrics TLS identity configuration; it is not a public scrape target on port 9091.

Grafana dashboards query Prometheus metrics; Hubble UI's service map queries Relay. Import dashboards that match the enabled plugins and labels. HTTP dashboards will be empty for traffic whose HTTP payload is not observable.

### Flow Export and Retention

For node-local rotated files, optionally merge `hubble-export-values.yaml`. The field mask deliberately keeps network metadata; it does not export full HTTP headers.

```yaml
# hubble-export-values.yaml
hubble:
  export:
    static:
      enabled: true
      filePath: /var/run/cilium/hubble/events.log
      fileMaxSizeMb: 10
      fileMaxBackups: 5
      fieldMask:
      - time
      - source.namespace
      - source.pod_name
      - destination.namespace
      - destination.pod_name
      - l4
      - IP
      - node_name
      - is_reply
      - verdict
      - drop_reason_desc
```

The static exporter writes on each node and rotates according to its file settings. Arrange a separate collector, access controls and storage retention if events must survive node loss. Static configuration changes require agent rollout; the dynamic exporter supports different update behavior. Exporter filters and field masks can intentionally omit events/fields, and finite buffers can still lose observations.

## Real-time Threat Detection

Hubble supplies evidence for investigations; it does not include a switch that makes it a complete IDS, WAF or automatic quarantine system. There are no supported Cilium settings named `enable-threat-detection`, `enable-anomaly-detection` or `alert-to-slack`.

Repeated denied destinations may suggest scanning; a traffic spike may justify investigation. These observations are not proof of an attack. Correlate them with application authentication logs, workload changes, API audit events and, where deployed, Tetragon runtime events. SQL injection, XSS and command injection require suitable application/WAF/detection rules; a normal HTTP flow record alone does not classify them.

For alerts, define and test external Prometheus/SIEM rules against normal traffic, missing data and event loss. Rate limits, firewall isolation and response automation are separately configured controls. Bound the response scope and provide a recovery path; do not automatically isolate every Pod that records a dropped packet.

## Lab: Hubble Installation and Usage

This lab uses two **fresh, separate namespaces** so a broad allow rule cannot invalidate the default-deny exercise. It creates no database or external API. Commands are examples for your test cluster; the documentation audit checked schemas and local fixtures, not a live deployment.

### 1. Create and Check the Workloads

Save `visibility-app.yaml`. The client and server images match Cilium CLI's versioned test defaults. Backend anti-affinity requires a second schedulable node, making the frontend-to-backend path cross-node.

```yaml
# visibility-app.yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
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
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
```
```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  kubectl create namespace "$ns"
  kubectl label namespace "$ns" audit-lab=security-visibility
  kubectl --namespace "$ns" apply -f visibility-app.yaml
  kubectl --namespace "$ns" wait --for=condition=Ready pod/frontend pod/outsider --timeout=120s
  kubectl --namespace "$ns" rollout status deployment/backend --timeout=120s
  for client in frontend outsider; do
    kubectl --namespace "$ns" exec "$client" -- \
      curl --fail --silent --show-error --max-time 5 http://backend:8080/
  done
done
```

Both clients in both namespaces must reach the backend before applying policy. If not, resolve readiness, scheduling, DNS and network issues first. Do not infer a policy denial from an arbitrary curl error.

### 2. Apply and Observe HTTP Policy

Save `backend-http.yaml`. It allows the `frontend` identity to issue `GET /` to backend TCP 8080. No broad ingress rule should overlap this example: an L4 allow can bypass the intended L7 restriction.

```yaml
# backend-http.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-http
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /
```
```bash
kubectl apply -f backend-http.yaml
# After the endpoint has realized the policy:
kubectl -n cilium-security-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 http://backend:8080/
# Display the HTTP response code; do not use --fail here.
kubectl -n cilium-security-demo exec frontend -- \
  curl --silent --show-error --max-time 5 --output /dev/null \
    --write-out '%{http_code}\n' --request POST http://backend:8080/
# A separate client is not in the allowed identity selector.
kubectl -n cilium-security-demo exec outsider -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-security-demo --verdict DROPPED --last 100
```

After policy realization, expect frontend `GET /` to succeed and its `POST /` to receive the proxy's HTTP 403. The outsider's new connection should be denied at L3/L4. Correlate the request time, endpoints and Hubble event; DNS errors, missing containers and unrelated HTTP errors are not a successful denial test. Use Hubble UI to inspect the generated dependency edge and drops.

For a real backend that needs a database and an external API, the following **optional dependency policy** illustrates egress. It is not applied by this lab: `database` and `api.example.com` must be replaced with real dependencies. Verify DNS endpoints first.

```yaml
# backend-dependencies.yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-dependencies
  namespace: cilium-security-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-security-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

TCP and UDP DNS are allowed, and DNS proxy rules let Cilium observe answers used by `toFQDNs`. Permitting DNS queries is distinct from permitting subsequent connections to their resolved IPs. This policy's DNS `*` allows all query names; it is not a domain blocklist.

### 3. Verify Default Deny Separately

Save `deny-except-dns.yaml`. The explicit `policyTypes` activate isolation in both directions; `ingress: []` contains **no ingress allow rules**. The single egress exception permits DNS to the matched resolver Pods only.

```yaml
# deny-except-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-except-dns
  namespace: cilium-deny-demo
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```
```bash
kubectl apply -f deny-except-dns.yaml
kubectl -n cilium-deny-demo exec frontend -- \
  curl --silent --show-error --max-time 5 http://backend:8080/
hubble observe --namespace cilium-deny-demo --verdict DROPPED \
  --drop-reason-desc POLICY_DENIED --last 100
```

Do not replace the empty ingress list with `ingress: [{}]`: that is an allow-all ingress rule. Standard NetworkPolicy allows are additive, so another policy can open traffic. Cilium deny rules and cluster policies can impose further restrictions. This namespace exercise does not claim to isolate host-network traffic or every host-originated path.

### 4. Inspect JSON and Export a Local Summary

Save the following as `flow-summary.jq`. `--output jsonpb` gives the protobuf response envelope with `.flow`; this avoids relying on the CLI's legacy `json` compatibility setting.

```text
[.[] | select(.flow != null) | .flow] as $flows
| {
    flow_records: ($flows | length),
    other_records: (length - ($flows | length)),
    policy_denied_records: (
      [$flows[] | select(.verdict == "DROPPED"
                        and .drop_reason_desc == "POLICY_DENIED")] | length
    ),
    dropped_by_reason: (
      [$flows[] | select(.verdict == "DROPPED")]
      | group_by(.drop_reason_desc // "UNKNOWN")
      | map({reason: (.[0].drop_reason_desc // "UNKNOWN"), records: length})
    )
  }
```

```bash
set -eu
hubble observe --namespace cilium-deny-demo --last 100 --output jsonpb > flows.jsonl
jq --slurp --from-file flow-summary.jq flows.jsonl
```

The result counts **flow records in this finite sample**, not unique attacks, connections or all cluster packets. It separately counts non-flow records; inspect them for loss/status information. For a live local filter:

```bash
hubble observe --namespace cilium-deny-demo --follow --output jsonpb |
  jq --unbuffered -c 'select(.flow.verdict == "DROPPED"
    and .flow.drop_reason_desc == "POLICY_DENIED")'
```

This pipeline prints locally. Notifications require a separately configured integration, credentials, retry/deduplication policy and handling of stream failures.

### 5. Clean Up the Test Namespaces

After reviewing the namespace names, remove only this lab's workloads and policies. The ownership check stops on lookup failure or a different label.

```bash
set -eu
for ns in cilium-security-demo cilium-deny-demo; do
  LAB_OWNER=$(kubectl get namespace "$ns" -o jsonpath='{.metadata.labels.audit-lab}')
  test "$LAB_OWNER" = security-visibility
  kubectl delete namespace "$ns"
done
```

## Primary References

- [Cilium policy enforcement](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/policy/intro.rst)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [HTTP policy](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/policy/layer7.rst)
- [DNS policy](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/dns.rst)
- [Hubble setup](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/observability/hubble/setup.rst)
- [Metrics](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/observability/metrics.rst)
- [Flow exporter](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/observability/hubble/configuration/export.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [IPsec](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-ipsec.rst)
- [Mutual authentication](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [ztunnel](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)
- [Tetragon](https://raw.githubusercontent.com/cilium/tetragon/main/README.md)
- [Hubble CLI filters](https://raw.githubusercontent.com/cilium/hubble/v1.19.4/vendor/github.com/cilium/cilium/hubble/cmd/observe/flows.go)

[Return to Main Page](README.md)

## Quiz

Test the policy, encryption and observability boundaries in the [topic quiz](../../quizzes/networking/cilium/06-security-visibility-quiz.md).
