# Workload Identity with SPIFFE/SPIRE

> **Last Updated**: September 13, 2026
> **Validation baseline**: SPIRE 1.15.3, hardened chart 0.30.2 / CRD chart 0.6.1, Controller Manager 0.7.0, chart CSI image 0.2.7 (also checked against current CSI 0.2.13 documentation), go-spiffe 2.8.1. Inspect chart-rendered image versions separately.

SPIFFE defines workload identity, credential, delivery, and trust formats; SPIRE implements them. **Issuing an identity does not automatically encrypt traffic or authorize service access.** This guide validates local configuration, schemas, libraries, charts, and diagrams. No live cluster, AWS CA, SPIRE attestation, or mesh installation was performed.

## Overview

SPIFFE and SPIRE are CNCF Graduated projects. Their CNCF project pages record August 23 and August 22, 2022 respectively. Project maturity is separate from validation of an individual deployment.

Stable identities are useful across changing IPs/Pods, but applications still need a Workload API client, SDK, proxy, or explicit file adapter. “Zero application changes for every workload” is not a universal guarantee. This chapter focuses on SPIRE X.509/JWT paths; the separately published **Incubating WIT-SVID specification** is not assumed to be supported in every deployment.

<span id="svid-spiffe-verifiable-identity-document"></span>
<span id="x-509-svid-vs-jwt-svid-comparison"></span>
<span id="trust-bundle"></span>
<span id="trust-domain"></span>

## Core Concepts

### SPIFFE ID

```text
spiffe://example.org/ns/payments/sa/payment-processor
```

An ID contains a scheme, trust domain, and optional path. Query, fragment, port, dot-segment, and percent-encoded path components are disallowed. DNS-like stable trust-domain names are useful but need not be DNS-resolvable. IPv4-shaped or numeric names are not categorically invalid; distinguish syntax from naming guidance.

### SVIDs and Validation

| Concern | X.509-SVID | JWT-SVID |
|---|---|---|
| Identity | SPIFFE URI SAN in the leaf | sub |
| Validation | Chain, lifetime, SVID rules, trust domain | Signature, subject, audience, expiry |
| Use | TLS client/server authentication | APIs accepting bearer tokens |
| Key | Workload/agent private-key path | Issuer retains signing private key |
| Lifetime | Policy and actual issuance | Policy and actual token exp |

CN is not the SPIFFE identity. Local go-spiffe tests rejected CN-only, multiple SPIFFE URIs, expiry, and wrong trust domains. Audience validation limits recipients but is not replay detection: the same valid bearer token passed verification again. Apply appropriate TLS/token-use policy and replay defenses where required.

Trust bundles include X.509 authorities, JWT verification keys, and metadata. PEM, SPIFFE bundle JSON, and arbitrary YAML are not interchangeable. Public bundles must not contain workload or CA private keys.

<span id="spire-server"></span>
<span id="spire-agent"></span>
<span id="svid-issuance-flow"></span>

## SPIRE Architecture

![SPIRE Server, Agent, signing keys and registration responsibilities](../.gitbook/assets/en-security-12-spiffe-spire-0.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-0.html)


The server manages agent attestation, registration, and X.509/JWT signing. DataStore and KeyManager have different persistence responsibilities. An UpstreamAuthority such as AWS Private CA signs SPIRE intermediate CAs; it does not replace every workload leaf-signing operation.

The agent attests the process calling its API and uses synchronized entries/SVID cache. A valid cache does not require new server issuance on every API request. Consumers must adopt updated credentials through streams, SDKs, or proxies.

![Local X.509-SVID cache and conditional renewal path](../.gitbook/assets/en-security-12-spiffe-spire-1.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-1.html)


<span id="prerequisites"></span>
<span id="helm-installation-recommended"></span>
<span id="namespace-layout"></span>
<span id="high-availability-configuration"></span>
<span id="verify-installation"></span>

## Installation

Download the [example directory](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/spiffe) and work from `examples/security/spiffe`. Verify hostPath/CSI/kernel/kubelet requirements. The same DaemonSets cannot be assumed to run on hosts such as Fargate where required access is unavailable.

```bash
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened
helm repo update spiffe
helm upgrade --install spire-crds spiffe/spire-crds \
  --version 0.6.1 --namespace spire-system --create-namespace
helm upgrade --install spire spiffe/spire \
  --version 0.30.2 --namespace spire-system --values lab-values.yaml
```

### Single-Server Lab

```yaml
global:
  spire:
    trustDomain: example.org
    clusterName: documentation
    caSubject:
      organization: Documentation Lab
      country: KR
    namespaces:
      server:
        name: spire-system
      system:
        name: spire-system
  installAndUpgradeHooks:
    enabled: false
  deleteHooks:
    enabled: false
spire-server:
  replicaCount: 1
  controllerManager:
    enabled: true
    identities:
      clusterSPIFFEIDs:
        default:
          enabled: false
        oidc-discovery-provider:
          enabled: false
        test-keys:
          enabled: false
  externalControllerManagers:
    enabled: false
  persistence:
    enabled: true
    size: 1Gi
spire-agent:
  workloadAttestors:
    k8s:
      verification:
        type: apiServerCA
    unix:
      enabled: true
spiffe-oidc-discovery-provider:
  enabled: false
spiffe-csi-driver:
  enabled: true
```


This is a single-server SQLite lab. Broad default, test, and unused OIDC identities are disabled; a separate ClusterSPIFFEID selects workloads. The chart defaults kubelet verification to skip, so apiServerCA is set explicitly. This assumes that the actual kubelet serving certificate validates under that CA; use the appropriate CA/host-certificate method for other PKI rather than disabling verification.

Install/delete hooks are disabled in this profile; perform any required migration/cleanup separately. The render includes a Server StatefulSet with Controller Manager sidecar plus Agent and CSI DaemonSets. Confirm release-specific resource names, labels, and socket paths.

### High Availability

[ha-values.yaml](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/spiffe/ha-values.yaml) uses three replicas, shared PostgreSQL, an existing password Secret, verify-full TLS with a mounted CA, and anti-affinity matching actual Pod labels. Three independent SQLite replicas are not a shared HA datastore.

Prepare PostgreSQL/DNS, the CA ConfigMap, spire-database Secret/password key, StorageClass, and connectivity first. The chart's Secret environment reference and -expandEnv argument were verified, but database connectivity/failover was not. HA also requires key persistence, backups, bundle rollover, and recovery testing.

<span id="attestation-flow"></span>
<span id="kubernetes-psat-projected-service-account-token"></span>
<span id="aws-instance-identity-document-iid"></span>
<span id="join-token-bootstrap"></span>
<span id="node-attestor-comparison"></span>

## Node Attestation

![Separate agent and workload attestation](../.gitbook/assets/en-security-12-spiffe-spire-2.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-2.html)


k8s_psat validates the agent's projected ServiceAccount token through **Kubernetes TokenReview**, then checks namespace/SA/Pod/node data. This is not the IAM OIDC-provider flow used by IRSA. Match logical cluster names, token audience, SA allowlist, and TokenReview permissions.

Default agent IDs follow `spiffe://TRUST_DOMAIN/spire/agent/k8s_psat/CLUSTER/NODE_UID`; the current version also offers a Pod UID mode. Discover registered agent/alias IDs instead of inventing parentIDs. token generate, entry create, and bundle set mutate real state.

aws_iid is an alternative using EC2 instance identity. It is not universally stronger than PSAT or restricted to non-EKS environments. Review skip_block_device, local-validation assumptions, allowed accounts, and additional selectors. Do not place static AWS credentials in ConfigMaps.

<span id="kubernetes-workload-attestor"></span>
<span id="registration-entry-examples"></span>
<span id="unix-workload-attestor"></span>

## Workload Attestation

The agent uses caller PID/cgroups and kubelet information. Do not default to insecure kubelet port 10255 or skip_kubelet_verification=true. Secure authentication, the correct serving CA, and network access are prerequisites.

Common selectors include k8s:ns, k8s:sa, k8s:pod-label, k8s:pod-uid, and k8s:container-name/image. container-image reflects Kubernetes-reported tags/digests; nginx:* is not a glob selector. A tag string is not supply-chain verification. Use appropriate digest/signature attestation separately where needed.

Principals able to change namespace/Pod labels or create Pods under a ServiceAccount can affect identity eligibility. Control namespace/SA/Pod creation and ownership of identity policy together. Unix UID/GID/path/hash selectors also depend on plugin configuration and the threat model.

<span id="spiffe-csi-driver"></span>
<span id="spire-controller-manager"></span>
<span id="envoy-sds-integration"></span>

## Kubernetes Integration

### CSI Mounts the API Socket

The chart’s SPIFFE CSI 0.2.7 and current 0.2.13 implementations mount a **directory containing the Workload API Unix socket**. It does not automatically create svid.pem, svid.key, or bundle.pem files. File-based applications need a separate adapter plus renewal/reload handling.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    spiffe-enabled: 'true'
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: payment-processor
  namespace: payments
---
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: payments-workload
spec:
  spiffeIDTemplate: spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{
    .PodSpec.ServiceAccountName }}
  namespaceSelector:
    matchLabels:
      spiffe-enabled: 'true'
  podSelector:
    matchLabels:
      spiffe-managed: 'true'
  workloadSelectorTemplates:
  - k8s:ns:{{ .PodMeta.Namespace }}
  - k8s:sa:{{ .PodSpec.ServiceAccountName }}
  - k8s:container-name:app
  ttl: 1h
  jwtTtl: 5m
---
apiVersion: v1
kind: Pod
metadata:
  name: payment-processor
  namespace: payments
  labels:
    spiffe-managed: 'true'
spec:
  serviceAccountName: payment-processor
  containers:
  - name: app
    image: registry.example.com/team/payment-app:REPLACE_WITH_APPROVED_VERSION
    env:
    - name: SPIFFE_ENDPOINT_SOCKET
      value: unix:///spiffe-workload-api/spire-agent.sock
    volumeMounts:
    - name: spiffe-workload-api
      mountPath: /spiffe-workload-api
      readOnly: true
  volumes:
  - name: spiffe-workload-api
    csi:
      driver: csi.spiffe.io
      readOnly: true
```


Replace the application image with an actual Workload API consumer. Distinguish chart identity jwtTTL from CRD jwtTtl. The explicit selector targets the app container; a separate Envoy container needs matching proxy registration policy.

### Envoy SDS

The [complete bootstrap example](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/spiffe/envoy.yaml) includes HTTP filters, the SDS cluster, require_client_certificate:true, and an exact allowed peer-URI matcher. The Envoy process must be attestable and both named server/client identities must be registered.

SDS shares the public agent socket with the Workload API. Certificate resource names use a workload SPIFFE ID or default; validation contexts use a trust-domain ID or ROOTCA/ALL. Check SPIFFE certificate-validator support, especially for ALL. Protocol schemas and URI-matcher implementation were verified; no real Envoy/SDS/mTLS handshake was run.

<span id="istio-spire-integration"></span>
<span id="cilium-spire-mutual-authentication"></span>
<span id="linkerd-identity-trust-anchors"></span>

## Service Mesh Integration

### Istio

Do not point Istio's CA address at SPIRE Server port 8081 or use invented ENABLE_SPIFFE_IDENTITY/PILOT_ENABLE_SPIRE_INTEGRATION variables. The current [official integration](https://istio.io/latest/docs/ops/integrations/spire/) configures CSI socket mounts, SPIRE registration, and sidecar/gateway templates.

With native sidecars, istio-proxy is an initContainer and must be patched there. Explicitly disabled native-sidecar mode uses containers instead. Validate installed versions, templates, sockets, and readiness; do not replace a complete injector ConfigMap with a partial snippet.

### Cilium

Cilium 1.20.1 mutual authentication is **beta and out-of-band from ordinary connections**. Traffic encryption requires separate WireGuard/IPsec configuration. An arbitrary label containing a SPIFFE ID is not an authenticated identity policy.

The official setup uses authentication.mutual.spire.enabled and, for its bundled installation, authentication.mutual.spire.install.enabled. Keep bundled and external SPIRE configurations distinct and consult the [pinned installation source](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/installation.rst). Endpoint selectors/authentication modes, identity issuance, and encryption have separate responsibilities.

### Linkerd

Do not pass SPIRE bundle JSON where Linkerd expects PEM roots or copy SPIRE CA private keys as issuer keys. Linkerd needs an appropriate issuer certificate/key and trusted roots, with renewal and root rollover. See the [reviewed cert-manager/Linkerd path](./10-cert-manager.md#linkerd-and-trust-manager). Sharing root trust alone does not integrate the SPIFFE Workload API or SDS.

<span id="federation-trust-establishment"></span>
<span id="configuring-federation"></span>
<span id="federated-registration-entries"></span>
<span id="multi-cloud-federation-example"></span>

## Federation

![Federation with explicit bundle trust and workload authorization](../.gitbook/assets/en-security-12-spiffe-spire-3.png)

[View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-security-12-spiffe-spire-3.html)


Configure each trust direction explicitly; federation does not automatically establish mutual trust or authorization. Operate bundle endpoint connectivity, TLS verification, refresh failures, expiry, and rollover.

```yaml
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterFederatedTrustDomain
metadata:
  name: partner-domain
spec:
  trustDomain: partner.example.org
  bundleEndpointURL: https://bundle.partner.example.org
  bundleEndpointProfile:
    type: https_web
```


This https_web example assumes a real endpoint with a valid Web PKI certificate. https_spiffe additionally needs endpointSPIFFEID and an **initial trusted bundle acquired through an authenticated bootstrap path**; setting a URL alone is insufficient. Use bare trust-domain names such as partner.example.org in applicable workload federatesWith lists. Fetching a trust bundle and authorizing a peer workload are distinct.

<span id="irsa-vs-spiffe-comparison"></span>
<span id="pod-identity-vs-spire"></span>
<span id="hybrid-use-cases"></span>
<span id="eks-specific-node-attestation"></span>

## EKS Integration

IRSA/Pod Identity provide AWS API credential paths; SPIFFE/SPIRE provide workload identity paths. Neither replaces the other, and not every environment needs both. IRSA supports cross-account designs and refreshes credentials through compatible SDK/projected-token behavior; Pod restart is not inherently required. Do not assume a fixed twelve-hour lifetime.

Configure IRSA on the ServiceAccount and validate aud/sub trust and AWS permissions. A Pod annotation or AWS_ROLE_ARN environment variable alone is insufficient. For workload mTLS, applications/proxies must consume SVIDs and authorize peer identities separately.

### AWS Private CA

Use the [pinned plugin fields](https://github.com/spiffe/spire/blob/v1.15.3/doc/plugin_server_upstreamauthority_aws_pca.md) inside a complete server plugins section. This is a plugin fragment, not an independently runnable server configuration.

```hcl
# Merge this plugin into an otherwise complete server configuration.
UpstreamAuthority "aws_pca" {
  plugin_data {
    region = "ap-northeast-2"
    certificate_authority_arn = "arn:aws:acm-pca:ap-northeast-2:111122223333:certificate-authority/REPLACE_CA_ID"
    ca_signing_template_arn = "arn:aws:acm-pca:::template/SubordinateCACertificate_PathLen0/V1"
  }
}
```


SPIRE owns the intermediate CA and signs leaves. Scope DescribeCertificateAuthority/IssueCertificate/GetCertificate to the intended CA ARN using the [policy example](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/spiffe/aws-pca-policy.json). Select signing algorithms/templates for the real CA. supplemental_bundle_path contains additional PEM authorities, not a backup region. Distinguish aws_kms KeyManager from UpstreamAuthority plugins.

## Best Practices and Troubleshooting

Tune lifetimes against renewal failures, clock skew, issuance load, and offline periods. Short TTLs do not solve every revocation or JWT replay concern. bundle set changes trusted bundles; it does not rotate a CA private key.

Network policy must account for DNS, Kubernetes TokenReview/API, datastore, upstream CA/KMS, federation, and telemetry as well as Server↔Agent traffic. A Pod selector in one namespace does not select agents in another. Validate real connectivity before claiming the policy permits all required flows.

Running api fetch inside the agent Pod attests that calling process, not the application's context. Diagnose from the intended workload context under an approved procedure. Limit sensitive selectors, tokens, and keys in logs.

<span id="table-of-contents"></span>
<span id="the-zero-trust-identity-problem"></span>
<span id="spiffe-specification-overview"></span>
<span id="cncf-graduation-status"></span>
<span id="best-practices"></span>
<span id="trust-domain-naming"></span>
<span id="svid-ttl-tuning"></span>
<span id="high-availability-deployment"></span>
<span id="key-rotation"></span>
<span id="security-hardening"></span>
<span id="troubleshooting"></span>
<span id="common-issues"></span>
<span id="health-checks"></span>
<span id="key-takeaways"></span>
<span id="architecture-decision-guide"></span>
<span id="references"></span>

## Summary and References

Local validation covered server/agent configuration, nine ID cases, five X.509 cases, six JWT cases, lab/HA Helm, CRD/Pod schemas, Envoy protobuf schemas, and twenty-four browser cases for eight diagrams. No real attestation, cluster installation, DB connection, AWS issuance, federation exchange, or mTLS traffic was executed.

- [SPIFFE ID specification](https://spiffe.io/docs/latest/spiffe-specs/spiffe-id/)
- [X.509-SVID](https://spiffe.io/docs/latest/spiffe-specs/x509-svid/)
- [JWT-SVID](https://spiffe.io/docs/latest/spiffe-specs/jwt-svid/)
- [Incubating WIT-SVID](https://spiffe.io/docs/latest/spiffe-specs/wit-svid/)
- [Trust domain and bundle](https://spiffe.io/docs/latest/spiffe-specs/spiffe_trust_domain_and_bundle/)
- [Federation specification](https://spiffe.io/docs/latest/spiffe-specs/spiffe_federation/)
- [SPIFFE CNCF history](https://www.cncf.io/projects/spiffe/)
- [SPIRE CNCF history](https://www.cncf.io/projects/spire/)
- [SPIRE 1.15.3](https://github.com/spiffe/spire/releases/tag/v1.15.3)
- [SPIFFE CSI 0.2.13](https://github.com/spiffe/spiffe-csi/blob/v0.2.13/README.md)
- [Hardened Helm charts](https://github.com/spiffe/helm-charts-hardened)
- [Cilium 1.20.1 mutual authentication](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
