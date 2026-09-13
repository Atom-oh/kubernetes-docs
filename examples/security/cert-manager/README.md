# cert-manager examples

Validated on September 13, 2026 against cert-manager 1.21.2, trust-manager 0.25.0, istio-csr 0.17.0, aws-privateca-issuer 1.9.2, and ACK ACM 1.8.1. The official cert-manager 1.21 Kubernetes support/test range is 1.33–1.36.

These files demonstrate separate issuance and trust paths. Choose the relevant path; do not apply the entire directory as one installation. Names, account IDs, CA/ACM ARNs, domains, hosted-zone IDs, EAB endpoint IDs, and application images are placeholders. Replace them with approved values. Keep private keys, HMAC credentials, and Vault tokens outside this repository.

| Files | Prerequisites and intended use |
|---|---|
| `cert-manager-values.yaml` | Helm profile; Gateway API and Prometheus Operator CRDs/controllers must already exist. Disable those options if unused. |
| `bootstrap.yaml` | Lab-only SelfSigned root → CA ClusterIssuer → leaf. The manually managed root disables automatic renewal/key rotation; plan explicit root rollover. |
| `public-staging.yaml`, `route53-issuer.yaml`, `route53-policy.json` | Alternative Let’s Encrypt staging paths. HTTP requires an installed Envoy Gateway/controller and namespace labels; DNS requires scoped workload IAM and a real hosted zone. Staging is rate-limited and not browser-trusted. |
| `pca-issuer.yaml` | External Private CA controller, existing CA, workload identity, CA-scoped DescribeCertificateAuthority/GetCertificate/IssueCertificate permissions, approved requests, compatible lifetime/template. |
| `vault-issuer.yaml`, `vault-setup.sh`, `vault-policy.hcl` | Existing Vault PKI and Kubernetes auth mounts; TLS CA Secret, TokenReview configuration, and approved Vault operator identity. The script modifies Vault configuration when executed. It explicitly disables IP SANs and localhost for this DNS-scoped role and reads the role back; POST resets omitted settings to defaults. |
| `ack-acm.yaml` | ACK ACM controller, exportable public issuance, separate DNS validation, IAM/RBAC allowing the chosen export Secret. |
| `acm-acme-issuer.yaml` | ACM ACME endpoint, prevalidated domains, IAM-associated EAB registration, securely supplied base64url HMAC Secret value. The client holds its private key and renews; these certificates cannot attach directly to managed ALB/CloudFront/API Gateway integrations. |
| `alb-acm-ingress.yaml` | AWS Load Balancer Controller, existing ACM certificate ARN and app backend. ALB does not read a Kubernetes TLS Secret directly. |
| `nlb-tcp-service.yaml`, `gateway-tls.yaml` | Separate backend TLS patterns; the NLB target must really listen with TLS on 8443. The Gateway needs Envoy Gateway and uses a lab CA, not public browser trust. |
| `trust-manager-values.yaml`, `trust-bundle.yaml`, `trust-consumer.yaml` | Trust namespace and labelled destinations; directory projection rather than subPath. Supply a real app image and verify trust-store use/reload. |
| `istio-csr-values.yaml` | Ready CA issuer and `application-trust` ConfigMap in cert-manager; actual mounted root file plus matching Istio external-CA configuration. |
| `linkerd-identity.yaml`, `linkerd-values.yaml` | Ready lab CA and trust-manager; externally renewed issuer Secret and trust ConfigMap for the pinned Linkerd control-plane chart 2026.9.1. |
| `certificate-requester-rbac.yaml` | Namespace Certificate management only; separately constrain SANs, issuerRef, secretName and request approval. |
| `alerts.rules.yaml` | Prometheus rule-file format, not a Kubernetes manifest. Verify installed ServiceMonitor selectors/ports and add missing-scrape alerts. |

Local evidence covers Helm rendering, 30 resource schemas, three rejected legacy/unknown-field cases, six renewal-library cases, real local CSR generation/signature verification, three controller-configuration decoder cases, five Prometheus scenarios with 20 assertions, and shell syntax. Kubernetes IntOrString handling is retained when interpreting the official OpenAPI schema. An ephemeral localhost Vault 2.1.0 instance additionally verified sixteen synthetic issuance/CSR-signing cases: approved DNS works, while fixed policy rejects IP SANs/localhost/outside DNS. CRD CEL, admission, external issuance, Kubernetes/Vault authentication integration, AWS permissions, mesh installation, and runtime TLS have not been executed. See `docs/reviews/2026-09-11/cert-manager-validation.json` for evidence and limits.

- [Korean guide](../../../ko/security/10-cert-manager.md)
- [English guide](../../../en/security/10-cert-manager.md)
