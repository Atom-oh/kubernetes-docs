# Linkerd Security

> **Last Updated**: September 11, 2026 · Linkerd edge-26.9.1 · cert-manager examples checked against 1.21.1

Linkerd provides workload authentication, transport encryption and inbound authorization for traffic handled by its proxies. Enrollment, policy, certificate lifecycle and application security still need explicit design. Use the supported Kubernetes/Gateway API combination in the [installation guide](01-installation.md); the examples here assume that installation and existing application workloads.

## Security Architecture

![Logical signing chain and control-plane roles. The root signs an issuer; the Identity service uses that issuer to sign workload certificates. The drawing does not imply that the root private key must be stored in the cluster.](../../.gitbook/assets/en-service-mesh-linkerd-04-security-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-04-security-0.html)

## Automatic mTLS

Linkerd automatically uses mTLS for eligible TCP traffic between meshed Pods. Both proxies must participate, trust the certificate chain and receive the traffic. Skip ports bypass the proxy; UDP is outside this TCP mechanism. Traffic to or from unmeshed endpoints does not acquire Linkerd mTLS merely because one endpoint has a proxy.

For an application speaking plain HTTP, the outbound proxy authenticates the destination proxy and encrypts the network hop; the receiving proxy authenticates the caller and forwards HTTP to its local application. Application-originated TLS can remain encrypted through the mesh: Linkerd does not automatically decrypt every external or opaque TLS stream.

| Property | Meaning and boundary |
|---|---|
| Transparent encryption | No application TLS implementation is required for the eligible proxy-to-proxy hop |
| Mutual authentication | The proxies authenticate workload identities, not end users |
| TLS 1.3 | The selected release's mesh TLS protocol |
| Automatic leaf renewal | Proxies normally renew their short-lived workload certificates |
| Root/issuer lifecycle | Separate credentials that still need rotation and monitoring |

By default, Linkerd accepts plaintext from unmeshed sources. Authorization policy can reject it. “mTLS enabled” is therefore different from “all inbound access requires an authenticated mesh identity.” Network policy and admission controls must also cover paths that bypass or omit the proxy.

### Observe encryption and identity

```bash
linkerd check --proxy
linkerd viz edges deploy -n production
linkerd viz tap deploy/api -n production --method GET
linkerd identity -n production -l app=api
kubectl -n production get pods -l app=api \
  -o custom-columns=NAME:.metadata.name,SERVICEACCOUNT:.spec.serviceAccountName
```

`viz edges` reports observed resource edges and their security state; it is not an inventory of every possible or idle connection. `tap` shows supported observed traffic, not a complete packet/security audit. Its display is not the same interface as Prometheus TLS label values. Check both accepted and deliberately denied traffic from the intended client identities.

`linkerd identity` retrieves public certificates from selected Pods through port forwarding. Inspect their SANs, issuer and validity. This avoids assuming that an issued leaf is available at a fixed file path inside the proxy image.

## Workload Identity

For the standard Kubernetes identity path, Linkerd uses this DNS-form identity:

```text
<service-account>.<namespace>.serviceaccount.identity.<control-plane-namespace>.<trust-domain>

web.production.serviceaccount.identity.linkerd.cluster.local
api.production.serviceaccount.identity.linkerd.cluster.local
```

The examples use control-plane namespace `linkerd` and trust domain `cluster.local`. The root certificate's common name is not itself the workload trust-domain setting. This is not the Istio-style `spiffe://.../ns/.../sa/...` URI previously shown here. Multiple Pods with the same ServiceAccount share an authorization identity, although their private keys/certificates are separate.

The proxy generates its key and CSR, and sends the CSR with its projected ServiceAccount token to Identity. Identity validates the token using Kubernetes TokenReview, checks the requested identity and signs with the **issuer's** key. The root signs the issuer; it does not sign every proxy request. The private key is not derived from the ServiceAccount token.

Default workload certificates last about 24 hours and refresh before expiry. A certificate request does not generate a new Kubernetes ServiceAccount, and a renewal is not proof that all keys rotate on every refresh. See the [architecture guide](02-architecture.md) for the lifecycle.

## Authorization Policy

These resources belong to Linkerd's `policy.linkerd.io` API. `AuthorizationPolicy` is not a Gateway API resource; it was introduced in Linkerd 2.12. It can target routes that use Gateway API definitions.

| Resource | Role |
|---|---|
| Server | Selects a declared inbound port on matching Pods in its namespace |
| HTTPRoute/GRPCRoute attached to Server | Selects a subset of inbound requests |
| MeshTLSAuthentication | Describes allowed mesh identities |
| NetworkAuthentication | Describes allowed client IP networks; does not supply mTLS |
| AuthorizationPolicy | Grants access to a target when its authentication requirements match |
| ServerAuthorization | Older Server-only grant; supported as `v1beta1` in the selected CRDs |

`ServerAuthorization` and `AuthorizationPolicy` are alternative grant mechanisms, not a sequential pipeline. Multiple grants can broaden access; multiple `requiredAuthenticationRefs` within one AuthorizationPolicy must **all** match. A namespace-targeted AuthorizationPolicy covers policy targets defined in that namespace, not an automatic policy for every undeclared port.

Servers must not select overlapping Pod/port pairs. Declare the application port in the Pod specification. A Server defaults to denying unmatched traffic even if the namespace's default policy is permissive. `accessPolicy: audit` can help observe unmatched traffic during preparation, but it allows that traffic and is not enforcement.

### Default policy

This annotation configures newly created proxies in an enrolled namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  annotations:
    linkerd.io/inject: enabled
    config.linkerd.io/default-inbound-policy: deny
```

Changing the namespace annotation does not retrofit the initialized default into existing proxies. Coordinate workload-specific rollouts and verify readiness. Dynamic policy CRDs are a separate mechanism and can update policy without replacing every Pod.

The cluster-wide Helm value is `proxy.defaultInboundPolicy`, not `policyController.defaultPolicy`. Merge it into the complete installation values, preserving CA configuration and release ownership:

```yaml
proxy:
  defaultInboundPolicy: deny
```

| Default | Meaning |
|---|---|
| all-unauthenticated | Allows traffic without requiring mesh authentication; installation default |
| all-authenticated | Requires authenticated mesh clients, including appropriately trusted multicluster clients |
| cluster-authenticated | Requires authenticated clients from the same cluster |
| cluster-unauthenticated | Allows clients in the configured cluster network scope without requiring mesh authentication |
| deny | Denies unmatched traffic, subject to explicit policy and documented probe handling |
| audit | Allows unmatched traffic while recording audit evidence |

Cluster scope is not an end-user identity or an application authorization boundary. Verify configured networks and the source addresses visible at the proxy.

### Microservice example

For these separate example resources, prepare meshed frontend/API/PostgreSQL workloads in `production`, with `app: frontend/api/postgres`, the declared ports below, and their corresponding ServiceAccounts. Prepare the meshed ingress workload with ServiceAccount `edge-gateway` in namespace `ingress`; this name alone does not install or authenticate a gateway.

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: frontend-http
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: frontend-from-gateway
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: frontend-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: edge-gateway
    namespace: ingress
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: api-http
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: api-from-frontend
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: api-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: frontend
    namespace: production
---
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: database-tcp
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: postgres
  port: 5432
  proxyProtocol: opaque
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: database-tcp
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: api
    namespace: production
```

The intended call chain is gateway → frontend → API → database. A ServiceAccount name in YAML is not sufficient: the caller must present the authenticated identity of that account. Verify that no broader namespace/Server grant also permits unwanted callers.

Linkerd normally adds authorizations for declared HTTP health/readiness probes when no explicit route is attached to the Server. Once HTTPRoute/GRPCRoute resources attach, those default probe grants are not created; explicitly model required probe routes and their limited access. Do not grant unauthenticated access to an entire business port merely to make one probe succeed.

For reference, this **alternative legacy grant** is equivalent to the API's frontend-client grant. It does not need to be combined with the AuthorizationPolicy above:

```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: ServerAuthorization
metadata:
  name: api-from-frontend-legacy
  namespace: production
spec:
  server:
    name: api-http
  client:
    meshTLS:
      serviceAccounts:
      - name: frontend
        namespace: production
```

The selected release does not serve `ServerAuthorization/v1beta2`; do not infer a resource's API version from Server's version. `client.unauthenticated:true` permits clients without mesh authentication, whereas `meshTLS.identities:["*"]` still requires a meshed identity and grants it very broadly.

### Metrics ports and verification

For an explicitly declared **application metrics port 9091** on the API Pod, an example grant is:

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: api-app-metrics
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  port: 9091
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: metrics-from-prometheus
  namespace: production
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: api-app-metrics
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: prometheus
    namespace: monitoring
```

This is different from the proxy's own admin port, normally **4191**. The proxy-init configuration exempts the admin/control ports from ordinary inbound interception. A Server on 4191 therefore does not make that endpoint an mTLS-protected application port. Use the actual cluster/network controls and restricted access paths for management endpoints.

```bash
kubectl -n production get servers,authorizationpolicies,serverauthorizations
kubectl -n production get server api-http -o yaml
# Set this to an actual selected API Pod.
api_pod=api-example-pod
linkerd diagnostics policy -n production "pod/$api_pod" 8080 -o json
linkerd viz authz deploy/api -n production
```

Known HTTP policy rejection normally produces HTTP 403; opaque/TCP traffic can be rejected at connection level. A changed policy may interrupt existing connections. Kubernetes `Forbidden` events are not an automatic per-request record of proxy authorization denials. Use policy diagnostics and the appropriate HTTP/TCP authorization metrics.


## Certificate Management

| Credential | Purpose | Default/manual ownership considerations |
|---|---|---|
| Trust anchor certificate bundle | Public roots accepted by the mesh | Normally ConfigMap `linkerd-identity-trust-roots`, key `ca-bundle.crt` |
| Identity issuer certificate/key | Intermediate CA used by Identity to sign workload certificates | Secret `linkerd-identity-issuer`; key names depend on the issuer scheme |
| Workload certificate/key | Per-proxy TLS credential | Short-lived leaf, automatically refreshed by the proxy |

The default CLI-generated root and issuer expire after one year; workload leaves normally last 24 hours. A manually chosen ten-year root is possible, not a universal recommendation or the installation default. Choose lifetimes and renewal lead time from the CA policy and recovery process, and track every certificate in the chain.

Linkerd's supplied root/issuer credentials require **ECDSA P-256**. The [installation guide](01-installation.md) includes explicit generation parameters and local private-key handling. Keep the root signing key separate from the public trust bundle; a public ConfigMap must never contain that key.

### Read the effective public credentials

```bash
set -euo pipefail
umask 077
# Public trust bundle: ConfigMap data is not base64-encoded.
kubectl -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > current-trust.pem
# Select only public certificate data from the issuer Secret, never its key.
kubectl -n linkerd get secret linkerd-identity-issuer -o json \
  | jq -er '(.data["tls.crt"] // .data["crt.pem"]) | select(length > 0)' \
  | base64 -d > current-issuer.pem

# Show every certificate in a multi-root bundle, not only its first entry.
openssl crl2pkcs7 -nocrl -certfile current-trust.pem \
  | openssl pkcs7 -print_certs -text -noout
openssl x509 -in current-issuer.pem -noout -subject -issuer -dates
# Nonzero exit means expiration is within this window or parsing failed.
openssl x509 -in current-issuer.pem -noout -checkend 86400
```

Under the default `linkerd.io/tls` scheme the issuer Secret uses `crt.pem`/`key.pem`; `kubernetes.io/tls` uses `tls.crt`/`tls.key`. The command selects public certificate data only. Check the configured scheme and resource owner before changing anything.

Inspect every root in a bundle. `openssl x509` by itself only examines the first certificate; it is not a complete multi-root expiry audit. Verify the issuer chain against the intended trust anchors as well as dates, and provide intermediate certificates when the chain requires them. Parsing or API-read failure must be reported as failure, not “certificate healthy.”

### Issuer renewal with an unchanged trust anchor

Update the issuer through its owner: complete Helm/CLI certificate values for a Linkerd-owned Secret, or the certificate controller for a managed Secret. Identity watches its mounted issuer files, validates the replacement and reloads a valid issuer; a blanket Identity Deployment restart is not a required step for every renewal.

```bash
kubectl -n linkerd get events --field-selector reason=IssuerUpdated
kubectl -n linkerd get events --field-selector reason=IssuerUpdateSkipped
kubectl -n linkerd logs deployment/linkerd-identity -c identity --tail=100
linkerd check --proxy
linkerd identity -n production -l app=api
```

`IssuerUpdated` confirms that Identity accepted an update. Investigate `IssuerUpdateSkipped` or validation errors. Existing proxy leaves can remain signed by the previous issuer until their normal refresh; that is expected while both chains remain valid. Immediate replacement of every leaf is a separate coordinated workload operation.

### Trust anchor rotation

Replacing a root needs a staged transition. The healthy-root procedure is not a guaranteed recovery method for a root that has already expired.

1. Inventory the active root bundle, issuer chain, managed resources and every consumer, including control-plane proxies, workloads, external workloads and linked clusters. Confirm capacity/readiness for the planned rollout.
2. Generate the new root and retain the **public old+new bundle**. Update the bundle through its actual owner.
3. Distribute that overlap bundle to all consumers before switching the issuer. Proxies receive trust through installation/injection configuration; a ConfigMap write alone does not prove that existing processes have reloaded it.
4. Verify distribution with `linkerd check --proxy` and workload/cross-cluster checks. Then issue and load an issuer signed by the new root.
5. Allow or deliberately coordinate leaf renewal, and verify that all relevant clients/servers use the new chain. A fixed sleep or only a successful controller rollout is insufficient.
6. Remove the old root through the bundle owner, propagate the final bundle to all consumers, and verify connections and trust again.

Preserve rollback material and monitor each stage. Restart only reviewed meshed workload controllers with workload-appropriate readiness/disruption handling; an all-namespace Deployment loop misses other workload types and can disrupt unrelated workloads. This document does not claim that an untested rotation is zero downtime.

## External Certificate Management

### cert-manager issuer renewal

This example assumes an existing, validated CA certificate and ECDSA P-256 signing key in the `linkerd-trust-anchor` Secret in namespace `linkerd`. A cert-manager CA Issuer keeps that signing key in the cluster; choose a different CA integration if that does not fit the trust model. The selected cert-manager version must support the cluster's Kubernetes version.

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: linkerd-trust-anchor
  namespace: linkerd
spec:
  ca:
    secretName: linkerd-trust-anchor
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
spec:
  secretName: linkerd-identity-issuer
  duration: 8760h
  renewBefore: 720h
  issuerRef:
    name: linkerd-trust-anchor
    kind: Issuer
    group: cert-manager.io
  commonName: identity.linkerd.cluster.local
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  - server auth
  - client auth
```

The issuer is a CA because it signs workload leaves. `rotationPolicy: Always` makes key rotation explicit. Here 8760h is 365 days and `renewBefore:720h` means renewal **30 days before expiry**, not every 30 days. Ensure that the parent CA remains valid long enough: the CA Issuer does not automatically enforce every chain-lifetime/path-length constraint, and updating its CA Secret does not automatically reissue all dependent certificates.

```bash
kubectl -n linkerd get issuer linkerd-trust-anchor
kubectl -n linkerd get certificate linkerd-identity-issuer
kubectl -n linkerd describe certificate linkerd-identity-issuer
# Inspect public certificate contents and effective issuer loading as above.
```

The Certificate must be Ready, its Secret must have the expected keys/chain, and Identity must accept it before this is a functioning integration.

### Choose trust-bundle ownership explicitly

**Option A: cert-manager owns the issuer; Helm owns the public trust bundle.** Save this as `managed-issuer-values.yaml` and supply the root bundle through the complete reviewed chart values:

```yaml
identity:
  externalCA: false
  issuer:
    scheme: kubernetes.io/tls
```

```bash
# Merge into the complete reviewed values from the installation guide.
# In this option, Helm owns the public trust bundle; cert-manager owns the issuer.
helm template linkerd-control-plane linkerd-edge/linkerd-control-plane \
  --version 2026.9.1 -n linkerd \
  -f reviewed-values.yaml -f managed-issuer-values.yaml \
  --set-file identityTrustAnchorsPEM=ca.crt > reviewed-control-plane.yaml
```

With `kubernetes.io/tls`, the chart expects the issuer Secret to exist instead of creating a Linkerd-format one. With `externalCA:false`, Helm still creates the public trust ConfigMap. Review the rendered objects and existing ownership before a deployment through the installation workflow.

**Option B: an external controller also owns the trust ConfigMap.** In that different ownership model:

```yaml
identity:
  externalCA: true
  issuer:
    scheme: kubernetes.io/tls
```

`identity.externalCA:true` means the chart does **not** create `linkerd-identity-trust-roots`. An external controller such as trust-manager must supply that ConfigMap in the control-plane namespace with `ca-bundle.crt`. Merely passing `identityTrustAnchorsPEM` while omitting the external ConfigMap does not complete this setup.

For managed root rotation, retain the previous **public certificate** in the overlap bundle, coordinate issuer renewal and consumer rollouts, and then retire it. Do not copy an entire CA Secret just to retain its public certificate. cert-manager/trust-manager do not make all workload restarts and trust transitions automatic.

### Vault integration boundary

Vault can participate in the CA design, but an ordinary PKI `sign/<role>` leaf-signing recipe is not a complete Linkerd issuer workflow. Linkerd requires an actual intermediate CA certificate; setting `isCA:true` on a Certificate resource alone does not demonstrate that the Vault endpoint grants that capability.

Verify the selected integration's signing endpoint and request/response mapping. Vault documents privileged `root/sign-intermediate` and issuer-specific intermediate-signing endpoints; permission to use them grants CA issuance capability and needs a deliberately restricted role/policy. Also validate ECDSA P-256, the returned chain, issuer lifetime, Vault server trust and renewal behavior.

For cert-manager authentication, prefer the documented short-lived ServiceAccount token flow where appropriate, with the required TokenRequest RBAC, Vault Kubernetes/JWT auth configuration and audiences. A Secret called `vault-token` is not sufficient by itself. The former YAML omitted these prerequisites and a proven intermediate-CA issuance path, so it is not presented as a tested deployment recipe.

## Application Security and Monitoring

| Responsibility | Linkerd contribution | Additional controls |
|---|---|---|
| Network hop | Eligible proxy-to-proxy mTLS | TLS for other hops, network restrictions and endpoint exposure |
| Workload authentication | ServiceAccount-derived mesh identity | End-user/API-client authentication and token validation |
| Service access | Inbound authorization policy | Application roles, tenant and object authorization |
| Data handling | Does not validate business input | Input validation, output handling and data protection |

A permitted frontend identity does not prove that its caller is an administrator. Applications must validate user credentials and business permissions as well as inputs.

### Meaningful security alerts

The following rules require Prometheus Operator and a Prometheus selecting this PrometheusRule, plus scrapes retaining the shown namespace/deployment and proxy TLS identity labels. Review target and cluster scope for shared backends.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: linkerd-security-alerts
  namespace: monitoring
spec:
  groups:
  - name: linkerd-security
    rules:
    - alert: LinkerdWorkloadCertificateExpiring
      expr: identity_cert_expiration_timestamp_seconds{namespace="production"} - time() < 3600
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Proxy workload certificate has less than one hour remaining
    - alert: LinkerdIssuerCertificateExpiring
      expr: issuer_cert_ttl_seconds{job="linkerd-controller",component="identity"} < 86400
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Identity issuer has less than one day remaining
    - alert: LinkerdInboundHTTPWithoutMeshIdentity
      expr: |-
        ((sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) - (sum(rate(response_total{namespace="production",deployment="api",direction="inbound",tls="true",client_id!=""}[5m])) or vector(0))) / sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) > 0.10)
        and on() (sum(rate(response_total{namespace="production",deployment="api",direction="inbound"}[5m])) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: More than 10% of observed API HTTP responses lack authenticated mesh client identity
    - alert: LinkerdInboundHTTPAuthorizationDenied
      expr: sum(rate(inbound_http_authz_deny_total{namespace="production",deployment="api"}[5m])) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: API inbound HTTP authorization denials observed
```

`identity_cert_expiration_timestamp_seconds` measures a **proxy leaf's absolute expiration time**. A seven-day warning would always match a healthy default 24-hour leaf. The controller's `issuer_cert_ttl_seconds` is already a remaining duration; do not subtract `time()` from it. Its selector uses the default Viz controller job/component labels; that scrape does not add a namespace label. Adapt the selector if a custom collector changes those labels. Tune thresholds to the configured credential lifetimes and expected refresh interval, and separately monitor the public roots and scrape availability.

For the selected proxy, TLS labels include `true`, `no_identity`, `disabled` and `opaque`; the original `tls="false"` query did not match the intended series. `tls="true"` alone can also lack a client identity. The example compares completed inbound API HTTP responses with those carrying both TLS and a nonempty authenticated `client_id`, using rates and a positive-traffic guard.

This ratio is **not a percentage of all network bytes or all plaintext traffic**. It does not cover bypassed paths or opaque TCP, and it depends on retaining identity labels. Expected probes or deliberately unauthenticated routes need their own scope/baseline. For all-authenticated traffic without an unauthenticated series, the underlying ratio is zero and this alert does not fire. No traffic or missing data does not prove safety.

HTTP authorization-denial counters are distinct from application login failures. Use the TCP authorization counters for opaque connections, and do not infer “no denials” from a missing scrape. Audit mode logs/metrics record permissive unmatched traffic rather than enforced rejections.

## Next Steps and References

- [Observability](05-observability.md), [multi-cluster](06-multi-cluster.md), [best practices](07-best-practices.md), [security quiz](../../quizzes/service-mesh/linkerd/security.md)
- [Automatic mTLS](https://linkerd.io/docs/features/automatic-mtls/)
- [Authorization behavior](https://linkerd.io/docs/features/server-policy/) and [API reference](https://linkerd.io/docs/reference/authorization-policy/)
- [Identity CLI](https://linkerd.io/docs/reference/cli/identity/)
- [Manual credential rotation](https://linkerd.io/docs/tasks/manually-rotating-control-plane-tls-credentials/)
- [Managed credential rotation](https://linkerd.io/docs/tasks/automatically-rotating-control-plane-tls-credentials/)
- [Proxy metrics](https://linkerd.io/docs/reference/proxy-metrics/)
- [Released Identity reload/issuer metrics implementation](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/pkg/identity/service.go)
- [Released chart credential ownership](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/charts/linkerd-control-plane/templates/identity.yaml)
- [cert-manager CA Issuer](https://cert-manager.io/docs/configuration/ca/) and [Vault authentication](https://cert-manager.io/docs/configuration/vault/)
- [Vault intermediate signing](https://developer.hashicorp.com/vault/api-docs/secret/pki#sign-intermediate)
