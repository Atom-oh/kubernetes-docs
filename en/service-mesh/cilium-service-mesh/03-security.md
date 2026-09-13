# Cilium Service Mesh Security

> **Last Updated**: September 11, 2026 · Cilium/chart 1.20.1 · bundled SPIRE 1.15.2. See the [overview](./README.md) for tested Kubernetes/EKS versions and platform requirements.

## Overview

Evaluate three separate controls: workload authorization, peer authentication and application-data encryption. Cilium's out-of-band mutual authentication, WireGuard/IPsec transport encryption and the separate ztunnel mTLS beta have different requirements and limitations.

The policy examples below describe the ordinary Cilium policy/out-of-band-authentication path. **Do not assume they retain the same L4 enforcement when ztunnel encryption is enabled**; the beta limitation is explained below.

## Security Architecture

![Logical separation of identity/policy, out-of-band authentication and optional encryption choices.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-0.html)

These boxes group responsibilities rather than certify that every combination preserves all policies. In particular, ztunnel beta uses a distinct identity/data path, and its default CA does not require the SPIRE integration shown for out-of-band authentication.

## Mutual Authentication and Data Encryption

### Established Cilium Mutual Authentication

The out-of-band mechanism is still documented as **beta/incomplete** in Cilium 1.20.1. Cilium agents authenticate Cilium security identities using SPIRE-provided SVIDs; the application connection does not itself become TLS because a network-policy rule requires authentication.

![Illustrative out-of-band authentication exchange between agents before policy-protected traffic proceeds.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-1.html)

Authentication records are cached for identity relationships. The diagram is not a new certificate/handshake for every HTTP request or necessarily every application connection. Apply explicit authorization rules as well as authentication requirements.

### Native mTLS via ztunnel (2026 Update)

Cilium 1.20.1 contains **Ztunnel Transparent Encryption (Beta)**. Select it with this mode fragment, after preparing the required bootstrap/CA material:

```yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal
```

The released default uses Cilium's internal CA option. A `cilium-ztunnel-secrets` Secret supplies `bootstrap-private.key`, `bootstrap-root.crt`, `ca-private.key` and `ca-root.crt`; the official generation script is an example, not a complete production PKI/rotation design. The chart's `bootstrapRootCert` option alone supplies only a public certificate and does not generate the private keys required by the internal CA.

The Cilium agent configures iptables redirection in enrolled Pods' network namespaces, sends workload state to the node's ztunnel, and serves its control/certificate interfaces. The chart creates the `ztunnel-cilium` DaemonSet. Namespace enrollment uses `io.cilium/mtls-enabled=true`; installing the mode alone does not enroll all namespaces.

The released guide specifies these boundaries:

- Both source and destination workloads must be enrolled; enrolled-to-unenrolled communication is not supported.
- Enrollment is namespace-based; per-Pod enrollment is not supported. Host-networked Pods cannot be enrolled.
- Only TCP is redirected for mTLS; UDP and other protocols are outside this encryption path.
- ClusterMesh is not supported, and the kernel must support the required iptables operations.
- Encryption occurs before packets leave the Pod. Ordinary L4 policies therefore do not work on this path except when directly targeting HBONE port 15008.

This integration uses a namespace/service-account workload identity model. It differs from the numeric `/identity/<id>` SPIFFE path used by out-of-band authentication.

Read-only checks for a prepared test installation include:

```bash
kubectl -n kube-system get daemonset ztunnel-cilium
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system get configmap cilium-config -o yaml
```

A namespace label, healthy proxy or packet observed on port 15008 alone does not prove all expected traffic is encrypted and authorized. Check successful enrollment, both ends of the chosen path, certificate identity/trust and unsupported traffic cases.

### When to Choose Cilium vs. Istio for mTLS

Choose against the required identity, authorization and traffic coverage. An existing Cilium deployment may use identity policy plus WireGuard/IPsec, or evaluate the separate ztunnel beta within its limitations. Account for the additional proxies, CA and operational dependencies actually enabled.

Istio provides workload-proxy mTLS in sidecar and ambient modes with their own feature/platform boundaries. `PeerAuthentication` `STRICT` is an inbound mTLS requirement; it does not by itself issue identities, install proxies or authorize every caller. Do not reduce the comparison to a single encryption switch. The [sidecar/ambient chapter](../istio/comparison/03-sidecar-vs-ambient.md) preserves its actual measured versions and scenarios.

### SPIRE-Based Mutual Authentication Configuration

For **out-of-band** authentication, merge this overlay into the installation's reviewed values:

```yaml
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      trustDomain: spiffe.cilium
      agentSocketPath: /run/spire/sockets/agent/agent.sock
      install:
        enabled: true
        server:
          dataStorage:
            enabled: true
            size: 1Gi
```

Prepare a suitable StorageClass/PV for the SPIRE StatefulSet. A class named `gp3` is not automatically present on every EKS cluster. `authentication.enabled` is required; trust domain and agent socket settings belong under `authentication.mutual.spire`, not beneath `install.server` or `install.agent`. The bundled chart does not implement the former `server.replicas`, `server.nodeAttestor`, `agent.workloadAttestor` or `server.ca.ttl` examples.

The SPIRE Server attests agents and signs SVIDs. Agents perform workload attestation; the Cilium integration additionally delegates retrieval and registers entries for Cilium security identities. Enabling SPIRE alone neither enforces authentication on all traffic nor enables WireGuard/IPsec.

### Mutual Authentication Policy Enforcement

`authentication` is an **object inside an ingress/egress allow rule**. It is not an array and not a top-level `spec.authentication` switch. This cluster-scoped policy deliberately selects one application/namespace:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-backend-auth
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

### Per-Namespace Mutual Authentication

This namespaced example selects workloads in `production` and permits authenticated peers from that namespace on TCP 8080:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: namespace-auth
  namespace: production
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

It is an illustrative same-namespace allowance, not least privilege for every application. Other ports, clients, probes and existing policy grants must be assessed separately. It affects ingress; it does not silently configure a complete egress dependency policy.

### Per-Service Mutual Authentication

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: service-auth
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
```

Here the source and destination labels describe workloads, not an end user's login. Kubernetes permissions must control who can create workloads, change those labels or use their service accounts.

## CiliumNetworkPolicy L7 Rules

### HTTP L7 Security Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-security-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: reader
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/.*$
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:role: admin
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^(GET|POST|PUT|PATCH|DELETE)$
          path: ^/api/.*$
          headers:
          - Authorization
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: monitoring
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/health$
        - method: ^GET$
          path: ^/metrics$
```

HTTP rules within a rule are alternatives. `headers: [Authorization]` requires presence only: it does not validate a bearer token, its signature, expiry or permissions. The former `Authorization: Bearer .*` string was not a JWT verifier or a general regular-expression value match. Perform application authentication and authorization independently.

An HTTP path policy requires a supported inspectable L7 path. Application TLS, probes and other dependency traffic need the relevant configuration; a port number alone does not turn on TLS.

### Kafka L7 Security Policy

The old `rules.kafka` object is rejected by the Cilium 1.20.1 L7 schema. The replacement below limits **network reachability only**:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-network-boundary
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: kafka
      k8s:app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: producer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kafka
        k8s:role: consumer
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

Configure the actual Kafka listener's TLS/SASL and broker ACLs for produce/fetch, topics and consumer groups. Removing an obsolete L7 rule leaves L4 access; it does not preserve topic-level authorization.

### DNS L7 Security Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-security
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: web-application
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
        - matchPattern: '*.*.svc.cluster.local'
        - matchName: api.stripe.com
        - matchName: sts.us-east-1.amazonaws.com
  - toFQDNs:
    - matchName: api.stripe.com
    - matchName: sts.us-east-1.amazonaws.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

The example assumes CoreDNS endpoints labeled `k8s-app=kube-dns` in `kube-system`, plus the ordinary `cluster.local` DNS suffix. It allows UDP and TCP DNS. A Service FQDN contains both service and namespace labels, so `*.*.svc.cluster.local` differs from the former `*.svc.cluster.local`.

External HTTPS permission is separate from DNS query permission. `sts.us-east-1.amazonaws.com` is a specific regional AWS endpoint; AWS does not use the former `api.aws.amazon.com` as a universal API endpoint. Select the actual SDK region/service endpoints, including any relevant IPv6/dual-stack or private-endpoint variants. Internal DNS answers are not an automatic grant to connect to every internal Service.

Review resolver search-list behavior and NodeLocal DNS if enabled. Broad S3 wildcards can allow destinations beyond one intended bucket, and a DNS/IP policy is not a guarantee against exfiltration through allowed destinations.

## Mutual Authentication

### Authentication Modes

| Mode | Meaning in the out-of-band policy API |
|---|---|
| `required` | Require successful authentication for the matched allowed traffic |
| `disabled` | Explicit authentication exemption for that matched rule |
| `test-always-fail` | Test mode that deliberately fails authentication |

There is no `optional` mode in the released schema. Absence of an explicit requirement differs from a carefully scoped exemption when other rules overlap; inspect the resulting policy rather than assuming authentication rules behave like ordinary independent allow grants.

### Mutual Authentication Policy Examples

An exemption is explicit, narrow and should be justified:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: authentication-exception
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: secure-service
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: trusted-client
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
    authentication:
      mode: disabled
```

The Prometheus rule is **disabled authentication**, not “authenticate if possible.” It grants only the stated monitoring workload and port. TLS on either application's listening port is a separate application configuration.

### SPIFFE ID-Based Authentication

For the default **out-of-band** SPIRE trust domain, a Cilium security identity has this form:

```text
spiffe://spiffe.cilium/identity/<numeric-security-identity>
```

Select the permitted peers through endpoint/identity policy; the `authentication` object has no arbitrary SPIFFE-ID allow-list field. Changing a comment to an Istio-style `/ns/.../sa/...` URI does not constrain access. The ztunnel beta described above uses a separate workload identity model.

## Encryption

### WireGuard Transparent Encryption

```yaml
encryption:
  enabled: true
  type: wireguard
```

Cilium creates node key pairs and distributes public keys through CiliumNode information. Supported traffic between Cilium-managed Pods on **different nodes** is encrypted; same-node traffic is not. The kernel must provide WireGuard support. The chart has no `encryption.wireguard.userspaceFallback` option.

Allow the required node-to-node UDP 51871 path and account for MTU/encapsulation. AWS VPC CNI chaining has additional MTU requirements, including the documented `cni.enableRouteMTUForCNIChaining` setting; follow the selected installation mode rather than applying it blindly.

#### WireGuard Architecture

![Logical management of inter-node WireGuard by Cilium agents, with encryption performed by the kernel WireGuard interfaces.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-2.html)

The Agent box represents management/key distribution, not a userspace transit hop for every packet. Capturing on the WireGuard interface can show plaintext inner packets; verify the correct outer network path when assessing encryption.

Node-to-node coverage is a separate beta option:

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: true
```

Control-plane nodes are excluded from node encryption by default to avoid key-update bootstrap failures. The released traffic matrix also identifies exclusions involving XDP acceleration, non-Geneve DSR and egress-gateway replies. The client-to-cluster leg of an external request is not encrypted by node WireGuard.

### IPsec Encryption

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyFile: keys
    keyWatcher: true
    keyRotationDuration: 5m
```

The Secret must exist in Cilium's namespace. For the documented AES-GCM example, its `keys` entry has the shape:

```text
3+ rfc4106(gcm(aes)) <fresh-20-byte-random-value-in-hex> 128
```

The `+` selects per-tunnel derived keys. The old global-key form without `+` was deprecated for security reasons; do not copy it as current guidance. Generate and protect fresh key material through the documented CLI/Secret workflow rather than reusing a sample key.

`keyRotationDuration: 5m` is a transition/old-key-cleanup grace period after a key change, **not a scheduler that generates a new key every five minutes**. Update key IDs and material through the supported rotation procedure, coordinate all clusters if using ClusterMesh, and do not rotate while nodes are on mixed versions during an upgrade.

Check ESP/firewall support, the actual encryption interfaces and native-routing CIDR. Current IPsec requires the documented transparent DNS-proxy behavior with L7, does not support CNI chaining or host policies, and does not encrypt same-node traffic.

### Encryption Comparison

| Topic | WireGuard | IPsec | ztunnel beta |
|---|---|---|---|
| Keys/identity | Node-generated key pairs | Distributed key material with per-tunnel derivation | Workload mTLS certificates and bootstrap/CA material |
| Data path | Kernel WireGuard interfaces | Kernel IPsec/XFRM | Per-node TLS proxy and Pod-namespace redirection |
| Same-node/coverage | Same-node traffic not encrypted; use released traffic matrix | Same-node traffic not encrypted; mode limitations apply | Both endpoints enrolled; TCP only; policy limitations apply |
| Cipher configuration | WireGuard protocol's ChaCha20-Poly1305 suite | Kernel-supported configured algorithms, such as AES-GCM | TLS negotiated by the supported proxy |
| Performance | Measure the actual CPU, MTU and traffic mix | Measure algorithm/hardware, tunnel and single-tunnel decryption constraints | Measure proxy, TLS and workload overhead; not part of the older comparison benchmarks |

Transparent encryption can also have an endpoint-discovery window in which a permitted unknown destination is treated as external. Cilium documents restricted egress and encryption strict modes as mitigations, with specific limitations: strict egress is IPv4/CIDR-dependent; strict ingress requires WireGuard and managed interfaces and is not supported with CNI chaining. Do not interpret “encryption enabled” as proof of fail-closed protection for every path.

## Identity-Based Security

### Cilium Identity

Cilium allocates a numeric identity for an identity-relevant label set; several Pods can share it. This is not a user-computed hash or a permanent Pod identifier.

### Identity Components

```bash
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
CILIUM_POD='<agent-on-the-workload-node>'
kubectl -n default get ciliumendpoints
kubectl get ciliumidentities
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg encrypt status
```

Namespace, service-account and selected workload labels can contribute. IDs 1–6 correspond to host, world, unmanaged, health, init and remote-node; allocated workload IDs depend on the installation. Inspect the agent on the relevant node and keep full command failures/status.

### Identity-Based Policy

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: identity-based-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: default
      k8s:app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:app: frontend
        k8s:environment: production
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: monitoring
        k8s:app: prometheus
    toPorts:
    - ports:
      - port: '9090'
        protocol: TCP
```

### IP vs Identity Comparison

![Identity selectors avoid manually rewriting address lists for each Pod change, while Cilium still maintains address-to-identity state.](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-03-security-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-03-security-4.html)

Policy selectors can remain stable across IP churn. Cilium must still update endpoint/IP-cache state, and an identity can be garbage-collected and reallocated; the diagram does not promise an immutable numeric ID after every restart.

## External PKI Integration

### cert-manager Integration

These objects illustrate producing an upstream CA Secret. They **do not connect that Secret to SPIRE by themselves**:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cilium-ca-issuer
spec:
  ca:
    secretName: cilium-ca-secret
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: cilium-spire-ca
  namespace: cilium-spire
spec:
  secretName: spire-ca-secret
  duration: 8760h
  renewBefore: 720h
  isCA: true
  privateKey:
    algorithm: ECDSA
    size: 256
    rotationPolicy: Always
  usages:
  - cert sign
  - crl sign
  subject:
    organizations:
    - Cilium
  commonName: SPIRE upstream CA
  issuerRef:
    name: cilium-ca-issuer
    kind: ClusterIssuer
    group: cert-manager.io
```

Prepare a valid signing CA/key in `cilium-ca-secret` in cert-manager's configured cluster-resource namespace, with sufficient remaining lifetime. Validate CA constraints, signing usages and trust chains. The one-year duration is an example subordinate-CA lifetime, not a universal recommendation.

An externally managed SPIRE server must use a supported UpstreamAuthority and access the required mounted material or issuer API. For a disk authority joining an existing PKI, SPIRE requires `cert_file_path`, `key_file_path` and a trusted-root `bundle_file_path`; plan reload/rotation and trust overlap. A Kubernetes Secret update alone is not proof that every certificate consumer has adopted the new CA.

Do not replace the bundled SPIRE ConfigMap with a partial unrelated file. For externally operated SPIRE, review Cilium's external-server address, trust-domain, delegated-identity registration and authentication prerequisites separately.

### Vault Integration

The following is only a **plugin fragment** for an independently configured SPIRE 1.15.2 server, not a complete server configuration or Kubernetes Deployment:

```hcl
plugins {
  UpstreamAuthority "vault" {
    plugin_data {
      vault_addr = "https://vault.vault.svc:8200"
      pki_mount_point = "pki"
      ca_cert_path = "/vault/ca/ca.crt"
      k8s_auth {
        k8s_auth_mount_point = "kubernetes"
        k8s_auth_role_name = "spire-upstream"
        token_path = "/var/run/secrets/vault/token"
      }
    }
  }
}
```

Plugins belong in top-level `plugins`, not inside `server`. The field is `pki_mount_point`; `token_path` belongs inside `k8s_auth` here. The token is a projected Kubernetes service-account token for the configured Vault auth role, not a generic Vault token file.

Prepare the token projection/audience and Vault Kubernetes auth configuration, bind the role to the intended SPIRE workload, mount the TLS CA used to verify Vault, and grant the required PKI sign-intermediate operation. Coordinate SPIRE `ca_ttl`, Vault PKI TTLs, workload trust and rotation. This guide does not claim those external dependencies have been deployed or tested.

## Zero Trust Networking

### Default Deny Policy

This cluster-scoped resource deliberately targets the isolated `policy-lab` namespace:

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: policy-lab-default-deny
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: policy-lab
  enableDefaultDeny:
    ingress: true
    egress: true
  ingress: []
  egress: []
```

The `enableDefaultDeny` flags are explicit: an empty Cilium ingress/egress array by itself does not supply rules that turn on default-deny. Do not transfer that assumption from Kubernetes NetworkPolicy examples.

Add specific dependencies, such as DNS, as separate allow rules:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: policy-lab-dns
  namespace: policy-lab
spec:
  endpointSelector: {}
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
```

There is no universal requirement to allow every host-network flow. Assess actual kubelet/probe, resolver and host-policy behavior. These examples do not change Cilium's host handling or defend against a compromised privileged node.

### Least Privilege Access

This example assumes a Cilium-managed gateway workload labeled `app=ingress-gateway` in `edge`, frontend/database workloads in `production` and a working SPIRE integration:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: production-security
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      k8s:app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: production
        k8s:app: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
```

Use the labels and identities actually observed in the selected gateway implementation. Cilium's own node Envoy ingress/Gateway path and external load balancers can expose different identities; an arbitrary Pod label is not interchangeable with `reserved:ingress` or an external client address. The former retired ingress-nginx example is not a required dependency.

### Microsegmentation

These application-tier policies retain explicit DNS access for tiers that initiate Service lookups. They assume the same gateway model and the stated listening ports:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: frontend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: edge
        k8s:app: ingress-gateway
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
    authentication:
      mode: required
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
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: database
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: app
      k8s:tier: database
  enableDefaultDeny:
    egress: true
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: app
        k8s:tier: backend
    toPorts:
    - ports:
      - port: '5432'
        protocol: TCP
    authentication:
      mode: required
  egress: []
```

The database explicitly enables egress default-deny with no egress allow rule; stateful replies to allowed connections are still permitted. Add real backup, replication, authentication or other dependencies deliberately. Restricting network paths is not complete prevention of data extraction through an otherwise authorized database/application request.

## Security Auditing and Monitoring

### Policy Audit Mode

`cilium.io/audit-mode: "true"` is not a supported per-policy audit switch. A policy carrying that arbitrary annotation can still enforce normally.

For an **isolated endpoint test**, the actual mutable endpoint option is `PolicyAuditMode`. Inspect the local endpoint, temporarily enable it, and restore enforcement after the controlled observation:

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
ENDPOINT_ID='<local-endpoint-id-in-the-isolated-test>'
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=true
# Observe the controlled test, then restore enforcement.
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint config "$ENDPOINT_ID" PolicyAuditMode=false
```

This changes enforcement on that endpoint rather than attaching audit behavior to one policy object. Do not infer that every L7 denial or every security failure becomes an allowed audit event; verify the specific datapath/proxy behavior. `enableDefaultDeny: false` is also not an equivalent L7 audit mode.

### Policy Violation Monitoring

```bash
# Terminal 1
cilium hubble port-forward --port-forward 4245
# Terminal 2
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --last 100
hubble observe --server localhost:4245 --namespace production --verdict DROPPED --drop-reason-desc POLICY_DENIED --last 100
hubble observe --server localhost:4245 --namespace policy-lab --verdict AUDIT --last 100
```

`DROPPED` includes causes other than policy denial. The reason-filtered query focuses on reported policy-denied drops; L7/application authorization failures need their own observation. `AUDIT` is distinct from `DROPPED`. `--last 100` is bounded history, and Relay can return that count per connected Hubble instance; it is not a complete cluster traffic counter. Add `--follow` only when a streaming observation is intended.

### Prometheus Metrics

```yaml
prometheus:
  enabled: true
hubble:
  enabled: true
  metrics:
    enabled:
    - dns
    - drop
    - flow
    - httpV2
    - icmp
    - port-distribution
    - tcp
```

The agent and Hubble exporter need Prometheus discovery/scraping in addition to these enablement flags. `httpV2` replaces deprecated `http`; do not enable both. HTTP metrics need corresponding L7 visibility.

- `cilium_drop_count_total` counts dropped packets by reason/direction, not exclusively policy violations.
- `cilium_forward_count_total` counts forwarded packets, not successful application requests.
- Hubble's `drop` exporter exposes flow-drop information as `hubble_drop_total`; it is not the same accounting unit as the agent packet counter.
- The former `cilium_policy_verdict` metric name was not a documented metric. Use actual policy-verdict events or the metrics exposed by the selected exporter instead.

## Next Steps

- [Observability](./04-observability.md)
- [Ingress & Gateway](./05-ingress-gateway.md)
- [Best Practices](./06-best-practices.md)
- [Security Quiz](../../quizzes/service-mesh/cilium-service-mesh/security.md)

## References

- [Cilium1.20.1 mutual authentication](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
- [Authentication example/API shape](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication-example.rst)
- [Cilium1.20.1 CNP schema](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)
- [Cilium1.20.1 ztunnel beta](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst)
- [Ztunnel CA implementation](https://github.com/cilium/cilium/blob/v1.20.1/pkg/ztunnel/ca/ca_server.go)
- [Ztunnel bootstrap example](https://github.com/cilium/cilium/blob/v1.20.1/examples/kubernetes-ztunnel/generate-secrets.sh)
- [Encryption scope/strict mode](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption.rst)
- [WireGuard](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [IPsec and key rotation](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ipsec.rst)
- [Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [HTTP/DNS policy](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/layer7.rst)
- [Default-deny behavior](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/intro.rst)
- [Explicit default-deny API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/rule.go)
- [Mutable endpoint audit option](https://github.com/cilium/cilium/blob/v1.20.1/pkg/option/endpoint.go)
- [Endpoint configuration CLI](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/cmdref/cilium-dbg_endpoint_config.md)
- [Metrics](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/observability/metrics.rst)
- [SPIRE1.15.2 server configuration](https://github.com/spiffe/spire/blob/v1.15.2/doc/spire_server.md)
- [SPIRE Vault authority](https://github.com/spiffe/spire/blob/v1.15.2/doc/plugin_server_upstreamauthority_vault.md)
- [SPIRE disk authority](https://github.com/spiffe/spire/blob/v1.15.2/doc/plugin_server_upstreamauthority_disk.md)
- [Kafka ACLs](https://kafka.apache.org/41/security/authorization-and-acls/)
- [AWS STS endpoints](https://docs.aws.amazon.com/general/latest/gr/sts.html)
- [WireGuard protocol](https://www.wireguard.com/protocol/)
- [NIST Zero Trust Architecture — further reading](https://www.nist.gov/publications/zero-trust-architecture)
