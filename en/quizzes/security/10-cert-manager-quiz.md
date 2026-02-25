# cert-manager Quiz

Test your understanding of cert-manager and Kubernetes certificate management with the following questions.

---

## Questions

### 1. What is cert-manager's project status in the CNCF?

- A) Sandbox project
- B) Incubating project
- C) Graduated project
- D) Archived project

<details>
<summary>Show Answer</summary>

**Answer: C) Graduated project**

**Explanation:**
cert-manager achieved CNCF Graduated status in November 2022, making it one of the most mature and widely adopted certificate management solutions for Kubernetes. This status indicates the project has met rigorous requirements for governance, security, and community adoption.

</details>

---

### 2. Which component in cert-manager watches Certificate resources and triggers certificate issuance?

- A) cainjector
- B) webhook
- C) controller
- D) acmesolver

<details>
<summary>Show Answer</summary>

**Answer: C) controller**

**Explanation:**
cert-manager consists of three core components:
- **controller**: Watches Certificate resources, manages the certificate lifecycle, and triggers issuance/renewal
- **webhook**: Validates and mutates cert-manager resources via admission webhooks
- **cainjector**: Injects CA bundles into ValidatingWebhookConfiguration, MutatingWebhookConfiguration, and CRD conversion webhooks

</details>

---

### 3. What is the key difference between Issuer and ClusterIssuer resources?

- A) Issuer supports more certificate types
- B) ClusterIssuer is namespace-scoped while Issuer is cluster-scoped
- C) Issuer is namespace-scoped while ClusterIssuer is cluster-scoped
- D) ClusterIssuer only works with ACME

<details>
<summary>Show Answer</summary>

**Answer: C) Issuer is namespace-scoped while ClusterIssuer is cluster-scoped**

**Explanation:**
```yaml
# Issuer - only issues certificates in its namespace
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-prod
  namespace: my-app  # Only works in this namespace

# ClusterIssuer - issues certificates across all namespaces
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod  # No namespace - cluster-wide
```

Use ClusterIssuer for organization-wide certificate policies, Issuer for namespace-specific configurations.

</details>

---

### 4. Which ACME challenge type supports wildcard certificate issuance?

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) Both HTTP-01 and DNS-01

<details>
<summary>Show Answer</summary>

**Answer: B) DNS-01**

**Explanation:**
ACME challenge types and their capabilities:
- **HTTP-01**: Proves domain control via HTTP endpoint (port 80). Does NOT support wildcards.
- **DNS-01**: Proves domain control via DNS TXT records. Supports wildcard certificates (*.example.com).
- **TLS-ALPN-01**: Proves domain control via TLS (port 443). Does NOT support wildcards.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
spec:
  acme:
    solvers:
    - dns01:
        route53:
          region: us-east-1
      selector:
        dnsNames:
        - "*.example.com"  # Wildcard requires DNS-01
```

</details>

---

### 5. In a Certificate resource, what does the secretName field specify?

- A) The name of the Issuer secret
- B) The Kubernetes Secret where the issued certificate will be stored
- C) The CA certificate secret
- D) The ACME account secret

<details>
<summary>Show Answer</summary>

**Answer: B) The Kubernetes Secret where the issued certificate will be stored**

**Explanation:**
The secretName field specifies where cert-manager stores the issued certificate:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: my-app-tls
  namespace: my-app
spec:
  secretName: my-app-tls-cert  # Certificate stored here
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - my-app.example.com
```

The resulting Secret contains:
- `tls.crt`: The certificate chain
- `tls.key`: The private key
- `ca.crt`: The CA certificate (if available)

</details>

---

### 6. What is the primary use case for the AWS Private CA Issuer?

- A) Free public certificates
- B) Internal PKI for private/enterprise certificates
- C) DNS-01 challenge automation
- D) Certificate revocation

<details>
<summary>Show Answer</summary>

**Answer: B) Internal PKI for private/enterprise certificates**

**Explanation:**
AWS Private CA (PCA) Issuer integrates cert-manager with AWS Certificate Manager Private Certificate Authority:

```yaml
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: aws-pca-issuer
spec:
  arn: arn:aws:acm-pca:us-east-1:123456789:certificate-authority/abc-123
  region: us-east-1
```

Use cases:
- Internal microservice mTLS
- Enterprise PKI compliance requirements
- Private certificates not exposed to public internet
- Integration with existing AWS PCA infrastructure

</details>

---

### 7. What does trust-manager do in the cert-manager ecosystem?

- A) Validates certificate signatures
- B) Distributes CA bundles across namespaces as ConfigMaps or Secrets
- C) Manages ACME account registration
- D) Handles certificate revocation

<details>
<summary>Show Answer</summary>

**Answer: B) Distributes CA bundles across namespaces as ConfigMaps or Secrets**

**Explanation:**
trust-manager is a cert-manager sub-project that distributes trusted CA certificates:

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: my-ca-bundle
spec:
  sources:
  - useDefaultCAs: true           # Include system CAs
  - secret:
      name: "internal-ca"
      key: "ca.crt"
  target:
    configMap:
      key: "ca-certificates.crt"
    namespaceSelector:
      matchLabels:
        trust-bundle: enabled     # Distribute to labeled namespaces
```

This ensures consistent CA trust across all application namespaces.

</details>

---

### 8. What does the renewBefore field control in a Certificate resource?

- A) The minimum validity period
- B) How long before expiry cert-manager begins renewal
- C) The maximum renewal attempts
- D) The renewal check interval

<details>
<summary>Show Answer</summary>

**Answer: B) How long before expiry cert-manager begins renewal**

**Explanation:**
The renewBefore field specifies when cert-manager starts the renewal process:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
spec:
  secretName: my-cert
  duration: 2160h    # 90 days validity
  renewBefore: 360h  # Renew 15 days before expiry
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
```

With these settings:
- Certificate valid for 90 days
- Renewal begins at day 75 (90 - 15 = 75)
- Provides buffer for renewal failures

</details>

---

### 9. What is the role of istio-csr in cert-manager's Istio integration?

- A) Validates Istio configurations
- B) Issues workload certificates for Istio service mesh using cert-manager
- C) Manages Istio gateway certificates only
- D) Synchronizes certificates between clusters

<details>
<summary>Show Answer</summary>

**Answer: B) Issues workload certificates for Istio service mesh using cert-manager**

**Explanation:**
istio-csr replaces Istio's built-in CA (istiod) with cert-manager for workload identity:

```yaml
# istio-csr issues certificates for:
# - Workload mTLS (pod-to-pod)
# - Service mesh identity (SPIFFE)

# Configuration example
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: istiod
  namespace: istio-system
spec:
  secretName: istiod-tls
  issuerRef:
    name: istio-ca
    kind: ClusterIssuer
  isCA: true
```

Benefits:
- Centralized PKI management
- Consistent certificate policies across mesh and ingress
- Integration with external CAs (Vault, AWS PCA)

</details>

---

### 10. What is a key difference between cert-manager and AWS Certificate Manager (ACM)?

- A) ACM supports more issuers
- B) cert-manager can only run on EKS
- C) cert-manager provides certificates as Kubernetes Secrets, ACM stores them in AWS
- D) ACM supports more certificate types

<details>
<summary>Show Answer</summary>

**Answer: C) cert-manager provides certificates as Kubernetes Secrets, ACM stores them in AWS**

**Explanation:**
cert-manager vs AWS ACM comparison:

| Feature | cert-manager | AWS ACM |
|---------|--------------|---------|
| Storage | Kubernetes Secrets | AWS-managed |
| Private Key Access | Yes (in Secret) | No (AWS-only) |
| Use with Pods | Direct mounting | Not possible |
| Ingress Integration | Any ingress controller | ALB/NLB only |
| Multi-cloud | Yes | AWS only |
| Issuers | ACME, Vault, PCA, self-signed | Amazon, PCA |

Use cert-manager when you need:
- Certificates inside pods
- Multi-cloud portability
- Custom issuers
- Fine-grained control over private keys

</details>

---

## Score Calculation

- **9-10 correct**: Excellent - You have a deep understanding of cert-manager.
- **7-8 correct**: Good - You have a solid grasp of the key concepts.
- **5-6 correct**: Fair - There are areas that need additional study.
- **4 or fewer**: Please review the documentation again.

## Related Documentation

- [Certificate Management with cert-manager](../../security/10-cert-manager.md)
