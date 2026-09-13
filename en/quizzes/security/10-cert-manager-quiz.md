# cert-manager Quiz

> **Last Updated**: September 13, 2026

Ten questions covering issuance, renewal, trust distribution, and AWS integration boundaries.

## Questions

### 1. What is cert-manager's project status in the CNCF?

- A) Sandbox
- B) Incubating
- C) Graduated
- D) Archived

<details>
<summary>Show Answer</summary>

**Answer: C) Graduated**

cert-manager graduated on September 29, 2024. September 19, 2022 was its Incubating date. Project maturity does not establish the security or availability of an individual installation.

</details>

<span id="_2-which-component-in-cert-manager-watches-certificate-resources-and-triggers-certificate-issuance"></span>

### 2. Which component watches Certificates and reconciles issuance and renewal?

- A) cainjector
- B) webhook
- C) controller
- D) scheduler

<details>
<summary>Show Answer</summary>

**Answer: C) controller**

The controller reconciles certificate lifecycle. The webhook validates, defaults, and converts custom resources; cainjector injects CA bundles into supported API/webhook configurations.

</details>

<span id="_3-what-is-the-key-difference-between-issuer-and-clusterissuer-resources"></span>

### 3. What is the key difference between Issuer and ClusterIssuer?

- A) Only Issuer supports ACME
- B) Issuer is namespaced; ClusterIssuer is cluster-scoped
- C) Only ClusterIssuer renews automatically
- D) Creating a ClusterIssuer automatically enforces SAN policy

<details>
<summary>Show Answer</summary>

**Answer: B) Issuer is namespaced; ClusterIssuer is cluster-scoped**

An Issuer is referenced within its namespace. ClusterIssuer credential/CA Secrets live in the controller cluster-resource namespace, normally cert-manager. Resource scope alone does not authorize SANs or issuerRef; separate approval/admission policy is needed.

</details>

<span id="_4-which-acme-challenge-type-supports-wildcard-certificate-issuance"></span>

### 4. Which validation method supports ordinary Let’s Encrypt ACME wildcard issuance?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) Only checking port 443 connectivity

<details>
<summary>Show Answer</summary>

**Answer: B) DNS-01**

DNS-01 proves domain control through TXT records. HTTP-01 requires port 80 and does not support wildcards. Scope DNS API permissions to the intended zone/TXT names. Reused authorizations or ACM prevalidation can avoid a new Challenge on each request.

</details>

<span id="_5-in-a-certificate-resource-what-does-the-secretname-field-specify"></span>

### 5. What does Certificate.spec.secretName specify?

- A) The ACME account key Secret
- B) The output certificate/private-key Secret in the same namespace
- C) The ConfigMap that always distributes the root CA
- D) The Issuer authentication Secret

<details>
<summary>Show Answer</summary>

**Answer: B) The output certificate/private-key Secret in the same namespace**

The output Secret contains tls.crt and tls.key. ca.crt may be absent and is not a replacement for distributing client trust. The default privateKey.rotationPolicy has been Always since 1.18. Application reload after Secret updates must be verified separately.

</details>

<span id="_6-what-is-the-primary-use-case-for-the-aws-private-ca-issuer"></span>

### 6. Which extension connects AWS Private CA as a cert-manager external issuer?

- A) aws-pca-controller
- B) aws-privateca-issuer
- C) acmesolver
- D) trust-manager

<details>
<summary>Show Answer</summary>

**Answer: B) aws-privateca-issuer**

aws-privateca-issuer handles AWSPCAIssuer/AWSPCAClusterIssuer. It needs CA-scoped IAM permissions, workload identity, request approval, and compatible CA mode/templates/lifetimes. A private CA does not imply public browser trust or free issuance.

</details>

<span id="_7-what-does-trust-manager-do-in-the-cert-manager-ecosystem"></span>

### 7. What is the main role of trust-manager?

- A) Issuing certificates and private keys
- B) Distributing CA bundles to selected namespaces
- C) Copying CA private keys into every Pod
- D) Automatically revoking certificates

<details>
<summary>Show Answer</summary>

**Answer: B) Distributing CA bundles to selected namespaces**

The default 0.25.0 chart uses Bundle v1alpha1. Sources are read from the configured trust namespace and namespaceSelector limits destinations. ConfigMap targets are supported; Secret targets need separate enablement/RBAC. A subPath mount does not receive updates, and directory projection does not guarantee process reload.

</details>

<span id="_8-what-does-the-renewbefore-field-control-in-a-certificate-resource"></span>

### 8. A request asks for 90 days but receives a 45-day certificate. With no explicit renewal settings or ARI, when is default renewal scheduled?

- A) About 30 days into the actual lifetime
- B) Day 60 based on the requested 90 days
- C) Always 30 days before expiry
- D) Always 75 days after issuance

<details>
<summary>Show Answer</summary>

**Answer: A) About 30 days into the actual lifetime**

The default is two-thirds through the actual X.509 lifetime. Day 75 is correct only for an actual 90-day certificate with renewBefore:360h. Do not set renewBefore and renewBeforePercentage together. Version 1.21 renewal policy/windows or supported ARI paths can change scheduling; inspect status.renewalTime.

</details>

<span id="_9-what-is-the-role-of-istio-csr-in-cert-manager-s-istio-integration"></span>

### 9. Which statement correctly describes the Istio sidecar issuance path?

- A) Envoy signs using the CA private key
- B) istio-agent → istio-csr → CertificateRequest/Issuer; SDS delivers material to Envoy
- C) Every connection inside the same Pod is automatically mTLS
- D) A rootCAFile path removes the need to mount a real CA file

<details>
<summary>Show Answer</summary>

**Answer: B) istio-agent → istio-csr → CertificateRequest/Issuer; SDS delivers material to Envoy**

istio-agent creates the CSR and istio-csr connects it to cert-manager issuance. Peer-proxy mTLS is distinct from the local application hop. Configure an actual trust-root mount, ready issuer, and Istio external-CA settings; do not mix in the separate Kubernetes CSR RA mode.

</details>

<span id="_10-what-is-a-key-difference-between-cert-manager-and-aws-certificate-manager-acm"></span>

### 10. Which statement about current ACM and cert-manager behavior is correct?

- A) ACM certificates can never be used by Pods or on premises
- B) ALB reads Kubernetes TLS Secrets directly
- C) ACM exportable certificates support explicit export; ACM ACME has a separate lifecycle and limitations
- D) Changing only the server URL completes ACM ACME enrollment

<details>
<summary>Show Answer</summary>

**Answer: C) ACM exportable certificates support explicit export; ACM ACME has a separate lifecycle and limitations**

ACK ACM export needs options.export:ENABLED, exportTo, an output Secret, and separate domain validation. ACM ACME requires prevalidated domains/EAB and client-managed keys/renewal; its 45-day certificates cannot be directly attached to managed ALB/CloudFront/API Gateway integrations. cert-manager reconciles Kubernetes Secrets and multiple issuers while operators remain responsible for controllers, trust, and CA costs.

</details>

## Score Calculation

- 9–10: Strong understanding.
- 7–8: Revisit the issuance/trust paths you missed.
- 6 or fewer: Review the guide and examples.

## Related Documentation

- [Certificate Management with cert-manager](../../security/10-cert-manager.md)
