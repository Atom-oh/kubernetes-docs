# Certificate Management with cert-manager

> **Supported Versions**: cert-manager 1.16+, Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: July 13, 2026

cert-manager is a powerful and extensible X.509 certificate controller for Kubernetes. It automates the management and issuance of TLS certificates from various sources, including Let's Encrypt, HashiCorp Vault, Venafi, and private PKI systems.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Core Concepts](#core-concepts)
5. [Issuer Types](#issuer-types)
6. [EKS Integration Patterns](#eks-integration-patterns)
7. [AWS-Native Alternative: ACM + ACK](#aws-native-alternative-acm--ack)
8. [Service Mesh Integration](#service-mesh-integration)
9. [trust-manager](#trust-manager)
10. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
11. [Best Practices](#best-practices)
12. [Summary and References](#summary-and-references)

---

## Overview

### What cert-manager Solves

Manual certificate management in Kubernetes environments presents significant operational challenges:

| Challenge | Impact | cert-manager Solution |
|-----------|--------|----------------------|
| **Manual renewal** | Service outages from expired certificates | Automatic renewal before expiry |
| **Inconsistent processes** | Security gaps and configuration drift | Declarative Certificate resources |
| **Key management** | Risk of key exposure | Automatic key generation and rotation |
| **Multi-issuer complexity** | Operational overhead | Unified interface for all CA types |
| **GitOps incompatibility** | Cannot version control secrets | Certificate CRs are GitOps-friendly |

### Project Status

cert-manager is a **CNCF Graduated project**, indicating production-ready maturity:

- First released: 2017
- CNCF Sandbox: 2020
- CNCF Incubating: 2022
- CNCF Graduated: 2024
- Active maintainers from Venafi, Red Hat, and the community
- Over 10,000 GitHub stars and widespread production adoption

### Why Certificate Lifecycle Automation Matters

```
┌─────────────────────────────────────────────────────────────────────────┐
│              Certificate Lifecycle Without Automation                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Day 1: Generate CSR → Day 2: Submit to CA → Day 3: Receive cert       │
│  Day 4: Configure application → Day 89: Forget about renewal           │
│  Day 90: Certificate expires → Day 90: Production outage!              │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│              Certificate Lifecycle With cert-manager                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Day 1: Apply Certificate CR → cert-manager handles everything         │
│  Day 60: Automatic renewal triggered → Zero intervention required      │
│  Day 90: New certificate active → No outage, no manual work            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Component Overview

cert-manager consists of three main components that work together to manage certificate lifecycles:

![Architecture diagram showing the cert-manager control plane watching Certificate and Issuer custom resources, requesting signed certificates from an external CA, and writing the result into a TLS Secret that Ingress and Gateway resources reference.](../.gitbook/assets/en-security-10-cert-manager-0.png)

### Component Responsibilities

| Component | Responsibility | Key Functions |
|-----------|---------------|---------------|
| **Controller** | Main reconciliation loop | Watches Certificate CRs, creates CertificateRequests, stores issued certs |
| **Webhook** | Admission control | Validates and mutates cert-manager resources |
| **cainjector** | CA bundle injection | Injects CA certificates into webhooks and API server |

### Certificate Issuance Flow

![Flowchart showing cert-manager creating a CertificateRequest from a Certificate resource, branching into an ACME order-and-challenge sequence for ACME issuers or going straight to storage for non-ACME issuers, and finally writing the TLS Secret.](../.gitbook/assets/en-security-10-cert-manager-1.png)

---

## Installation

### Prerequisites

Before installing cert-manager, ensure:

- Kubernetes cluster version 1.25+
- `kubectl` configured with cluster admin access
- Helm 3.x (for Helm installation method)

### Installation with Helm (Recommended)

```bash
# Add the Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.2 \
  --set crds.enabled=true \
  --set prometheus.enabled=true \
  --set webhook.timeoutSeconds=30
```

### Production Helm Values

```yaml
# cert-manager-values.yaml
crds:
  enabled: true
  keep: true

replicaCount: 2

podDisruptionBudget:
  enabled: true
  minAvailable: 1

resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 256Mi

prometheus:
  enabled: true
  servicemonitor:
    enabled: true
    namespace: monitoring

webhook:
  replicaCount: 2
  timeoutSeconds: 30
  resources:
    requests:
      cpu: 25m
      memory: 32Mi
    limits:
      cpu: 100m
      memory: 128Mi

cainjector:
  replicaCount: 2
  resources:
    requests:
      cpu: 25m
      memory: 64Mi
    limits:
      cpu: 100m
      memory: 256Mi

# For EKS with IRSA
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT_ID:role/cert-manager-role

# Global settings
global:
  leaderElection:
    namespace: cert-manager
  logLevel: 2
```

```bash
# Install with custom values
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.2 \
  -f cert-manager-values.yaml
```

### Installation with kubectl

```bash
# Install cert-manager manifests (includes CRDs)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.2/cert-manager.yaml

# Verify installation
kubectl get pods -n cert-manager
```

### Verify Installation

```bash
# Check all pods are running
kubectl get pods -n cert-manager

# Expected output:
# NAME                                       READY   STATUS    RESTARTS   AGE
# cert-manager-5d7f97b46d-xxxxx              1/1     Running   0          2m
# cert-manager-cainjector-7f694c4c58-xxxxx   1/1     Running   0          2m
# cert-manager-webhook-7cd8c769bb-xxxxx      1/1     Running   0          2m

# Check CRDs are installed
kubectl get crd | grep cert-manager

# Expected output:
# certificaterequests.cert-manager.io
# certificates.cert-manager.io
# challenges.acme.cert-manager.io
# clusterissuers.cert-manager.io
# issuers.cert-manager.io
# orders.acme.cert-manager.io

# Test with cmctl (optional)
# Install cmctl: https://cert-manager.io/docs/reference/cmctl/
cmctl check api
```

---

## Core Concepts

### Custom Resource Definitions (CRDs)

cert-manager introduces several CRDs to manage the certificate lifecycle:

| CRD | Scope | Purpose |
|-----|-------|---------|
| **Certificate** | Namespaced | Declares desired certificate properties |
| **CertificateRequest** | Namespaced | Represents a CSR bound to an issuer |
| **Issuer** | Namespaced | Defines how to obtain certificates (namespace-scoped) |
| **ClusterIssuer** | Cluster | Defines how to obtain certificates (cluster-wide) |
| **Order** | Namespaced | Represents an ACME order |
| **Challenge** | Namespaced | Represents an ACME challenge |

### Certificate Resource

The Certificate resource is the primary interface for requesting certificates:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-tls
  namespace: default
spec:
  # Secret where the certificate will be stored
  secretName: example-com-tls-secret

  # Certificate duration (default: 2160h = 90 days)
  duration: 2160h

  # Renewal window (default: 360h = 15 days before expiry)
  renewBefore: 360h

  # Subject fields
  subject:
    organizations:
      - Example Inc

  # Common name (deprecated, use dnsNames)
  commonName: example.com

  # Private key settings
  privateKey:
    algorithm: RSA
    size: 2048
    rotationPolicy: Always

  # Usages
  usages:
    - digital signature
    - key encipherment
    - server auth

  # DNS names for the certificate
  dnsNames:
    - example.com
    - www.example.com
    - api.example.com

  # IP addresses (optional)
  ipAddresses:
    - 192.168.1.1

  # Reference to the issuer
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
    group: cert-manager.io
```

### Issuer vs ClusterIssuer

```yaml
# Issuer - namespace-scoped
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: ca-issuer
  namespace: my-namespace  # Only usable in this namespace
spec:
  ca:
    secretName: ca-key-pair

---
# ClusterIssuer - cluster-wide
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod  # No namespace, available cluster-wide
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
      - http01:
          ingress:
            class: nginx
```

### CertificateRequest Resource

CertificateRequests are typically created automatically by cert-manager:

```yaml
apiVersion: cert-manager.io/v1
kind: CertificateRequest
metadata:
  name: example-com-tls-xxxxx
  namespace: default
spec:
  # Base64-encoded CSR
  request: LS0tLS1CRUdJTi...

  # Reference to the issuer
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
    group: cert-manager.io

  # Requested duration
  duration: 2160h

  # Usages
  usages:
    - digital signature
    - key encipherment
    - server auth
```

---

## Issuer Types

### SelfSigned Issuer (Development/Testing)

Self-signed certificates are useful for development and testing environments:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}

---
# Create a self-signed CA certificate
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: selfsigned-ca
  namespace: cert-manager
spec:
  isCA: true
  commonName: selfsigned-ca
  secretName: selfsigned-ca-secret
  privateKey:
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: selfsigned-issuer
    kind: ClusterIssuer
    group: cert-manager.io
```

### CA Issuer (Internal PKI)

For organizations with their own internal Certificate Authority:

```yaml
# First, create a Secret with the CA certificate and key
apiVersion: v1
kind: Secret
metadata:
  name: ca-key-pair
  namespace: cert-manager
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTi...  # Base64-encoded CA certificate
  tls.key: LS0tLS1CRUdJTi...  # Base64-encoded CA private key

---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: ca-issuer
spec:
  ca:
    secretName: ca-key-pair

---
# Request a certificate from the CA issuer
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: internal-service-tls
  namespace: default
spec:
  secretName: internal-service-tls-secret
  duration: 8760h  # 1 year
  renewBefore: 720h  # 30 days
  dnsNames:
    - internal-service.default.svc.cluster.local
    - internal-service.default.svc
    - internal-service
  issuerRef:
    name: ca-issuer
    kind: ClusterIssuer
```

### ACME / Let's Encrypt

ACME (Automatic Certificate Management Environment) is used with Let's Encrypt and other ACME-compatible CAs.

#### ACME Challenge Types

![Flowchart showing cert-manager choosing between an HTTP-01 challenge when port 80 is reachable and a DNS-01 challenge for wildcard certificates or blocked ports, with the DNS-01 path also creating a Route 53 TXT record through an IRSA-authenticated pod before both paths verify and complete.](../.gitbook/assets/en-security-10-cert-manager-2.png)

#### HTTP-01 Solver

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    # Let's Encrypt production server
    server: https://acme-v02.api.letsencrypt.org/directory

    # Email for certificate expiry notifications
    email: admin@example.com

    # Secret to store the ACME account private key
    privateKeySecretRef:
      name: letsencrypt-prod-account-key

    # HTTP-01 solver configuration
    solvers:
      - http01:
          ingress:
            class: nginx
            # Or specify a specific ingress name
            # ingressTemplate:
            #   metadata:
            #     annotations:
            #       kubernetes.io/ingress.class: nginx
```

#### DNS-01 Solver with Route53 and IRSA

```yaml
# IAM Policy for cert-manager (create via AWS CLI or Terraform)
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Action": "route53:GetChange",
#       "Resource": "arn:aws:route53:::change/*"
#     },
#     {
#       "Effect": "Allow",
#       "Action": [
#         "route53:ChangeResourceRecordSets",
#         "route53:ListResourceRecordSets"
#       ],
#       "Resource": "arn:aws:route53:::hostedzone/HOSTED_ZONE_ID"
#     },
#     {
#       "Effect": "Allow",
#       "Action": "route53:ListHostedZonesByName",
#       "Resource": "*"
#     }
#   ]
# }

---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-dns01
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-dns01-account-key
    solvers:
      # DNS-01 solver for Route53
      - selector:
          dnsZones:
            - "example.com"
        dns01:
          route53:
            region: us-east-1
            hostedZoneID: Z1234567890ABC
            # Using IRSA - no credentials needed in the spec
            # cert-manager ServiceAccount must have the IAM role annotation

---
# Wildcard certificate (only possible with DNS-01)
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-example-com
  namespace: default
spec:
  secretName: wildcard-example-com-tls
  dnsNames:
    - "example.com"
    - "*.example.com"
  issuerRef:
    name: letsencrypt-dns01
    kind: ClusterIssuer
```

### AWS Private CA Issuer

For enterprise environments requiring AWS Private Certificate Authority:

```bash
# Install AWS PCA Issuer
helm repo add awspca https://cert-manager.github.io/aws-privateca-issuer
helm install aws-pca-issuer awspca/aws-privateca-issuer \
  --namespace cert-manager \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::ACCOUNT_ID:role/aws-pca-issuer-role
```

```yaml
# IAM Policy for AWS PCA Issuer
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Action": [
#         "acm-pca:IssueCertificate",
#         "acm-pca:GetCertificate",
#         "acm-pca:DescribeCertificateAuthority"
#       ],
#       "Resource": "arn:aws:acm-pca:REGION:ACCOUNT_ID:certificate-authority/CA_ID"
#     }
#   ]
# }

---
apiVersion: awspca.cert-manager.io/v1beta1
kind: AWSPCAClusterIssuer
metadata:
  name: aws-pca-issuer
spec:
  arn: arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  region: us-east-1

---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: internal-mtls-cert
  namespace: default
spec:
  secretName: internal-mtls-tls
  duration: 8760h
  renewBefore: 720h
  commonName: service.internal.example.com
  dnsNames:
    - service.internal.example.com
  usages:
    - digital signature
    - key encipherment
    - server auth
    - client auth  # For mTLS
  issuerRef:
    name: aws-pca-issuer
    kind: AWSPCAClusterIssuer
    group: awspca.cert-manager.io
```

### HashiCorp Vault PKI

For organizations using HashiCorp Vault as their PKI backend:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: vault-issuer
spec:
  vault:
    # Vault server address
    server: https://vault.example.com

    # PKI secrets engine path
    path: pki/sign/my-role

    # Vault namespace (Enterprise only)
    # namespace: admin

    # CA bundle for Vault TLS
    caBundle: LS0tLS1CRUdJTi...

    # Authentication method
    auth:
      # Kubernetes auth method
      kubernetes:
        role: cert-manager
        mountPath: /v1/auth/kubernetes
        serviceAccountRef:
          name: cert-manager
          # namespace: cert-manager  # Optional, defaults to issuer namespace

      # Or use AppRole auth
      # appRole:
      #   path: approle
      #   roleId: my-role-id
      #   secretRef:
      #     name: vault-approle-secret
      #     key: secretId

---
# Vault configuration (run in Vault)
# vault secrets enable pki
# vault secrets tune -max-lease-ttl=8760h pki
# vault write pki/root/generate/internal \
#     common_name="Example Root CA" \
#     ttl=87600h
# vault write pki/roles/my-role \
#     allowed_domains="example.com" \
#     allow_subdomains=true \
#     max_ttl=72h
# vault write auth/kubernetes/role/cert-manager \
#     bound_service_account_names=cert-manager \
#     bound_service_account_namespaces=cert-manager \
#     policies=pki-policy \
#     ttl=1h
```

---

## EKS Integration Patterns

### TLS Termination Comparison

| Approach | TLS Termination | Certificate Source | Use Case |
|----------|----------------|-------------------|----------|
| **ALB + ACM** | At ALB | AWS Certificate Manager | Public-facing with AWS-managed certs |
| **ALB + cert-manager** | At ALB | cert-manager | Public-facing with custom CA |
| **NLB + Ingress** | At Ingress Controller | cert-manager | Layer 4 load balancing |
| **NLB + Pod** | At Pod | cert-manager | End-to-end encryption |
| **Gateway API** | At Gateway | cert-manager | Modern API, future-proof |

> ACM certificates can now be defined and reconciled as native Kubernetes resources too. See [AWS-Native Alternative: ACM + ACK](#aws-native-alternative-acm--ack) below.

### ALB Ingress with ACM vs cert-manager

```yaml
# Option 1: ALB with ACM (AWS-managed certificates)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress-acm
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    # ACM certificate ARN
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-service
                port:
                  number: 80

---
# Option 2: Ingress-nginx with cert-manager
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress-certmanager
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - app.example.com
      secretName: app-example-com-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-service
                port:
                  number: 80
```

### NLB with TLS Termination at Ingress Controller

```yaml
# NLB Service for ingress-nginx
apiVersion: v1
kind: Service
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: external
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
spec:
  type: LoadBalancer
  ports:
    - name: https
      port: 443
      targetPort: 443
      protocol: TCP
  selector:
    app.kubernetes.io/name: ingress-nginx

---
# Certificate for ingress controller
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ingress-tls
  namespace: ingress-nginx
spec:
  secretName: ingress-tls-secret
  dnsNames:
    - "*.example.com"
    - example.com
  issuerRef:
    name: letsencrypt-dns01
    kind: ClusterIssuer
```

### Gateway API Integration

```yaml
# Install Gateway API CRDs
# kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: default
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  gatewayClassName: nginx  # or istio, envoy, etc.
  listeners:
    - name: https
      port: 443
      protocol: HTTPS
      hostname: "*.example.com"
      tls:
        mode: Terminate
        certificateRefs:
          - name: wildcard-example-com-tls
            kind: Secret
      allowedRoutes:
        namespaces:
          from: All

---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: default
spec:
  parentRefs:
    - name: main-gateway
      namespace: default
  hostnames:
    - app.example.com
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: app-service
          port: 80
```

---

## AWS-Native Alternative: ACM + ACK

### Overview

On December 15, 2025, AWS announced [automated certificate management for Kubernetes with AWS Certificate Manager (ACM)](https://aws.amazon.com/about-aws/whats-new/2025/12/acm-automated-certificate-management-kubernetes), integrating ACM with AWS Controllers for Kubernetes (ACK). With the ACM ACK controller installed in a cluster, certificates can be defined as native Kubernetes custom resources (YAML), and the ACK controller handles the full lifecycle automatically: requesting issuance, completing domain/ownership validation, and creating and renewing the corresponding Kubernetes Secret.

Where cert-manager is a CNCF open-source solution supporting a wide range of issuers (Let's Encrypt and other ACME issuers, Vault, AWS Private CA, self-signed, and more), the ACM+ACK integration is an **AWS-native alternative**. For organizations already invested in the IAM/ACM ecosystem, it delivers the same kind of automation without operating a separate open-source controller.

### July 2026 Update: ACM Now Supports the ACME Protocol

In July 2026, ACM added support for [issuing public certificates via the ACME protocol](https://aws.amazon.com/about-aws/whats-new/2026/07/aws-certificate-manager-acme/). You can provision a fully managed ACME server endpoint that issues public TLS certificates with a 45-day validity from Amazon Trust Services using any ACMEv2-compatible client — including Certbot, acme.sh, and cert-manager for Kubernetes. In other words, you can now consume ACM public certificates from cert-manager's existing ACME Issuer simply by pointing its `server` field at the ACM ACME endpoint, without installing the ACK controller.

PKI administrators can apply centralized governance at the endpoint level — restricting domain scopes and enforcing wildcard policies — and delegate certificate requests to application teams without distributing DNS credentials, with all activity auditable via CloudTrail logging and CloudWatch metrics. With the CA/Browser Forum mandating 47-day certificate lifetimes by 2029, the cert-manager + ACM ACME endpoint combination is positioned as an AWS-native alternative to Let's Encrypt.

### Supported Certificate Types

| Type | Use Case |
|------|----------|
| **ACM Exportable Public Certificates** | Public-domain certificates exported to a Kubernetes Secret for direct use by Pods/Ingress |
| **AWS Private CA** | Internal services and service-mesh (Istio, Linkerd) mTLS workloads that require a private PKI |

### Applicable Scenarios

- TLS termination directly in an application Pod (NGINX, custom applications)
- Service mesh (Istio, Linkerd) workload certificates
- Third-party Ingress Controllers (NGINX Ingress, Traefik) where ALB/NLB-native certificate integration isn't used
- Multi-cluster/hybrid environments that need consistent certificate management

### Example: Defining a Certificate via ACK

```yaml
apiVersion: acm.services.k8s.aws/v1alpha1
kind: Certificate
metadata:
  name: example-com-tls
  namespace: default
spec:
  domainName: example.com
  subjectAlternativeNames:
    - "*.example.com"
  validationMethod: DNS
  tags:
    - key: managed-by
      value: ack
```

The ACK controller watches this resource, requests the certificate from ACM, and creates/renews the resulting Kubernetes Secret once issuance completes. Exact field names and the Secret-export mechanism can vary by ACM ACK controller version, so check the official documentation before installing.

### Comparison with cert-manager

| Aspect | cert-manager | ACM + ACK |
|--------|--------------|-----------|
| **Issuers** | Let's Encrypt, Vault, AWS PCA, and more | ACM (public), AWS Private CA |
| **Ecosystem** | CNCF open source, vendor-neutral | AWS-native, IAM-based access control |
| **What you install** | cert-manager controller | ACK service controller for ACM |
| **Cost** | Free (infrastructure cost only) | Standard ACM/AWS Private CA pricing; no additional charge for the Kubernetes integration itself |
| **Best fit** | Multi-cloud, or ACME issuers required | AWS-centric organizations already using ACM/IAM |

The two approaches aren't mutually exclusive — for example, public-domain certificates can be managed via ACM+ACK while internal mTLS certificates continue to use cert-manager with the AWS PCA Issuer.

---

## Service Mesh Integration

### Istio with istio-csr

istio-csr is a cert-manager agent that integrates with Istio to provide workload certificates. It replaces the default istiod CA with certificates signed by cert-manager.

![Sequence diagram showing an Envoy sidecar requesting a certificate from istio-csr, which forwards a CertificateRequest through cert-manager to a ClusterIssuer for signing, then returns the signed SPIFFE SVID so Envoy can enable mutual TLS.](../.gitbook/assets/en-security-10-cert-manager-3.png)

#### Installing istio-csr

```bash
# Create issuer for istio-csr
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: istio-ca
spec:
  ca:
    secretName: istio-ca-secret
EOF

# Install istio-csr
helm repo add jetstack https://charts.jetstack.io
helm install istio-csr jetstack/cert-manager-istio-csr \
  --namespace cert-manager \
  --set app.certmanager.issuer.name=istio-ca \
  --set app.certmanager.issuer.kind=ClusterIssuer \
  --set app.certmanager.issuer.group=cert-manager.io \
  --set app.tls.certificateDuration=1h \
  --set app.tls.istiodCertificateDuration=1h \
  --set app.tls.rootCAFile=/var/run/secrets/istio-csr/ca.pem
```

#### Configuring Istio to use istio-csr

```yaml
# IstioOperator configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio
  namespace: istio-system
spec:
  profile: default
  meshConfig:
    # Use istio-csr for workload certificates
    caCertificates:
      - pem: |
          # CA certificate from cert-manager
    defaultConfig:
      proxyMetadata:
        # Point to istio-csr for certificate signing
        ISTIO_META_CERT_SIGNER: istio-csr.cert-manager.svc
  components:
    pilot:
      k8s:
        env:
          # Disable istiod CA
          - name: ENABLE_CA_SERVER
            value: "false"
          # Use external CA
          - name: EXTERNAL_CA
            value: ISTIOD_RA_KUBERNETES_API
        overlays:
          - apiVersion: apps/v1
            kind: Deployment
            name: istiod
            patches:
              - path: spec.template.spec.containers[0].volumeMounts[-]
                value:
                  name: istio-csr-ca-configmap
                  mountPath: /var/run/secrets/istiod/tls
                  readOnly: true
              - path: spec.template.spec.volumes[-]
                value:
                  name: istio-csr-ca-configmap
                  configMap:
                    name: istio-csr-ca-configmap
```

### Linkerd Trust Anchor Management

Linkerd requires a trust anchor certificate for mTLS. cert-manager can manage this:

```yaml
# Create a self-signed issuer for the trust anchor
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: linkerd-trust-anchor
spec:
  selfSigned: {}

---
# Trust anchor certificate (root CA)
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: linkerd-trust-anchor
  namespace: linkerd
spec:
  isCA: true
  commonName: root.linkerd.cluster.local
  secretName: linkerd-trust-anchor
  privateKey:
    algorithm: ECDSA
    size: 256
  duration: 87600h  # 10 years
  renewBefore: 8760h  # 1 year
  issuerRef:
    name: linkerd-trust-anchor
    kind: ClusterIssuer

---
# Issuer using the trust anchor
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
spec:
  ca:
    secretName: linkerd-trust-anchor

---
# Identity issuer certificate
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
spec:
  isCA: true
  commonName: identity.linkerd.cluster.local
  secretName: linkerd-identity-issuer
  privateKey:
    algorithm: ECDSA
    size: 256
  duration: 48h
  renewBefore: 25h
  issuerRef:
    name: linkerd-identity-issuer
    kind: Issuer
```

```bash
# Install Linkerd with cert-manager managed certificates
linkerd install \
  --identity-trust-anchors-file <(kubectl get secret linkerd-trust-anchor -n linkerd -o jsonpath='{.data.ca\.crt}' | base64 -d) \
  --identity-issuer-certificate-file <(kubectl get secret linkerd-identity-issuer -n linkerd -o jsonpath='{.data.tls\.crt}' | base64 -d) \
  --identity-issuer-key-file <(kubectl get secret linkerd-identity-issuer -n linkerd -o jsonpath='{.data.tls\.key}' | base64 -d) \
  | kubectl apply -f -
```

---

## trust-manager

trust-manager is a companion project to cert-manager that distributes CA trust bundles across namespaces.

### Installing trust-manager

```bash
helm repo add jetstack https://charts.jetstack.io
helm install trust-manager jetstack/trust-manager \
  --namespace cert-manager \
  --set app.trust.namespace=cert-manager
```

### Bundle Resource

```yaml
apiVersion: trust.cert-manager.io/v1alpha1
kind: Bundle
metadata:
  name: public-bundle
spec:
  sources:
    # Include default CA certificates
    - useDefaultCAs: true

    # Include specific ConfigMap
    - configMap:
        name: my-ca-bundle
        key: ca-bundle.crt

    # Include from Secret
    - secret:
        name: internal-ca
        key: tls.crt

    # Inline CA certificate
    - inlineString: |
        -----BEGIN CERTIFICATE-----
        MIIBkTCB+wIJAKHBfpEgcMFuMA0GCSqGSIb3DQEBCwUAMBExDzANBgNVBAMMBnJv
        ...
        -----END CERTIFICATE-----

  target:
    # Create ConfigMap in all namespaces
    configMap:
      key: ca-bundle.crt

    # Or specify namespaces
    # namespaceSelector:
    #   matchLabels:
    #     trust-bundle: enabled
```

### Using Trust Bundles in Applications

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-trust-bundle
spec:
  template:
    spec:
      containers:
        - name: app
          image: myapp:latest
          volumeMounts:
            - name: ca-bundle
              mountPath: /etc/ssl/certs/ca-certificates.crt
              subPath: ca-bundle.crt
              readOnly: true
          env:
            - name: SSL_CERT_FILE
              value: /etc/ssl/certs/ca-certificates.crt
      volumes:
        - name: ca-bundle
          configMap:
            name: public-bundle
```

---

## Monitoring and Troubleshooting

### Prometheus Metrics

cert-manager exposes metrics for monitoring certificate health:

```yaml
# ServiceMonitor for Prometheus Operator
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cert-manager
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: cert-manager
  namespaceSelector:
    matchNames:
      - cert-manager
  endpoints:
    - port: tcp-prometheus-servicemonitor
      interval: 30s
```

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `certmanager_certificate_ready_status` | Certificate ready state (1=ready, 0=not ready) | != 1 |
| `certmanager_certificate_expiration_timestamp_seconds` | Certificate expiry timestamp | < 7 days |
| `certmanager_certificate_renewal_timestamp_seconds` | Next renewal timestamp | Past due |
| `certmanager_controller_sync_call_count` | Controller sync operations | Spike detection |
| `certmanager_http_acme_client_request_count` | ACME HTTP requests | Rate limiting detection |

### PrometheusRule for Alerting

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cert-manager-alerts
  namespace: monitoring
spec:
  groups:
    - name: cert-manager
      rules:
        - alert: CertificateNotReady
          expr: certmanager_certificate_ready_status == 0
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Certificate {{ $labels.name }} in {{ $labels.namespace }} is not ready"
            description: "Certificate has been in not-ready state for more than 10 minutes"

        - alert: CertificateExpiringSoon
          expr: (certmanager_certificate_expiration_timestamp_seconds - time()) < 604800
          for: 1h
          labels:
            severity: warning
          annotations:
            summary: "Certificate {{ $labels.name }} expires in less than 7 days"
            description: "Certificate will expire in {{ $value | humanizeDuration }}"

        - alert: CertificateExpiryCritical
          expr: (certmanager_certificate_expiration_timestamp_seconds - time()) < 86400
          for: 10m
          labels:
            severity: critical
          annotations:
            summary: "Certificate {{ $labels.name }} expires in less than 24 hours"
            description: "Certificate will expire in {{ $value | humanizeDuration }}"
```

### Certificate Readiness Check

```bash
# Check certificate status
kubectl get certificates -A

# Detailed certificate status
kubectl describe certificate <name> -n <namespace>

# Check CertificateRequest status
kubectl get certificaterequests -A

# View certificate details
kubectl get secret <secret-name> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Waiting for HTTP-01 challenge propagation` | Challenge endpoint not accessible | Check Ingress, Service, firewall rules |
| `DNS problem: NXDOMAIN` | DNS record not created | Verify Route53 permissions, hosted zone ID |
| `Error presenting challenge: 403 Forbidden` | IRSA/IAM permissions issue | Check ServiceAccount annotations, IAM policy |
| `acme: error code 429` | Rate limit exceeded | Wait 1 hour, use staging server for testing |
| `certificate is not valid for any names` | DNS name mismatch | Verify `dnsNames` in Certificate spec |
| `Error getting keypair for CA issuer` | CA secret missing or malformed | Check CA secret exists with correct keys |

### cmctl CLI Tool

```bash
# Install cmctl
# Linux
curl -fsSL https://github.com/cert-manager/cmctl/releases/download/v2.1.0/cmctl_linux_amd64.tar.gz | tar xz
sudo mv cmctl /usr/local/bin/

# Verify API is ready
cmctl check api

# Check certificate status
cmctl status certificate <name> -n <namespace>

# Manually trigger renewal
cmctl renew <certificate-name> -n <namespace>

# Create CertificateRequest for testing
cmctl create certificaterequest my-cr \
  --from-certificate-file cert.yaml \
  --namespace default

# Approve/Deny CertificateRequest (if approval is required)
cmctl approve <certificaterequest-name> -n <namespace>
cmctl deny <certificaterequest-name> -n <namespace>

# Convert legacy cert-manager resources
cmctl convert -f old-resources.yaml
```

---

## Best Practices

### Renewal Buffer Configuration

Set appropriate renewal windows to prevent certificate expiry:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-cert
spec:
  # Certificate valid for 90 days
  duration: 2160h

  # Renew 30 days before expiry (gives time for issues)
  renewBefore: 720h

  # For short-lived certificates (1 hour)
  # duration: 1h
  # renewBefore: 30m
```

### Backup CA Strategy

Always maintain CA backup for disaster recovery:

```bash
# Backup CA certificate and key
kubectl get secret ca-key-pair -n cert-manager -o yaml > ca-backup.yaml

# Store securely (encrypted, off-cluster)
# Consider using AWS Secrets Manager or HashiCorp Vault for CA storage

# Restore procedure
kubectl apply -f ca-backup.yaml
```

### Multi-Tenant Issuer Strategy

```yaml
# ClusterIssuer for shared infrastructure
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform-team@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx

---
# Namespace-scoped Issuer for team-specific CA
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: team-a-ca
  namespace: team-a
spec:
  ca:
    secretName: team-a-ca-keypair

---
# RBAC for namespace issuers
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: cert-manager-issuer-admin
  namespace: team-a
rules:
  - apiGroups: ["cert-manager.io"]
    resources: ["issuers"]
    verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
  - apiGroups: ["cert-manager.io"]
    resources: ["certificates", "certificaterequests"]
    verbs: ["create", "delete", "get", "list", "patch", "update", "watch"]
```

### RBAC Configuration

```yaml
# Allow developers to create Certificates but not Issuers
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cert-manager-certificate-creator
rules:
  - apiGroups: ["cert-manager.io"]
    resources: ["certificates"]
    verbs: ["create", "delete", "get", "list", "watch"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list", "watch"]
    # Note: Don't grant create/delete on secrets unless needed

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: developers-certificate-creator
subjects:
  - kind: Group
    name: developers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: cert-manager-certificate-creator
  apiGroup: rbac.authorization.k8s.io
```

### Private Key Rotation

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: rotating-cert
spec:
  secretName: rotating-cert-tls
  dnsNames:
    - app.example.com
  privateKey:
    # Rotate key on each renewal
    rotationPolicy: Always
    algorithm: ECDSA
    size: 256
  issuerRef:
    name: ca-issuer
    kind: ClusterIssuer
```

---

## Summary and References

### Key Concepts Summary

| Concept | Description |
|---------|-------------|
| **Certificate** | Declares desired certificate, triggers issuance |
| **Issuer** | Namespace-scoped certificate authority configuration |
| **ClusterIssuer** | Cluster-wide certificate authority configuration |
| **CertificateRequest** | Represents a single certificate signing request |
| **ACME** | Protocol for automated certificate issuance (Let's Encrypt) |
| **HTTP-01** | ACME challenge via HTTP endpoint verification |
| **DNS-01** | ACME challenge via DNS TXT record verification |
| **trust-manager** | Distributes CA bundles across namespaces |
| **istio-csr** | Integrates cert-manager with Istio for workload certs |

### Issuer Selection Guide

| Scenario | Recommended Issuer |
|----------|-------------------|
| Development/Testing | SelfSigned or CA |
| Public websites | ACME (Let's Encrypt) |
| Internal services with existing PKI | CA or Vault |
| AWS-native enterprise | AWS PCA |
| Multi-cloud enterprise | Vault PKI |
| Service mesh workloads | CA with istio-csr/Linkerd integration |

### Official References

| Resource | URL |
|----------|-----|
| cert-manager Documentation | https://cert-manager.io/docs/ |
| cert-manager GitHub | https://github.com/cert-manager/cert-manager |
| ACME Protocol RFC | https://datatracker.ietf.org/doc/html/rfc8555 |
| Let's Encrypt Documentation | https://letsencrypt.org/docs/ |
| AWS PCA Issuer | https://github.com/cert-manager/aws-privateca-issuer |
| ACM Automated Certificate Management for Kubernetes (Dec 15, 2025) | https://aws.amazon.com/about-aws/whats-new/2025/12/acm-automated-certificate-management-kubernetes |
| istio-csr | https://github.com/cert-manager/istio-csr |
| trust-manager | https://github.com/cert-manager/trust-manager |
| cmctl CLI | https://cert-manager.io/docs/reference/cmctl/ |
| Helm Chart | https://artifacthub.io/packages/helm/cert-manager/cert-manager |

### Version Compatibility Matrix

| cert-manager | Kubernetes | Helm |
|--------------|------------|------|
| 1.16.x | 1.28 - 1.33 | 3.x |
| 1.15.x | 1.27 - 1.32 | 3.x |
| 1.14.x | 1.26 - 1.31 | 3.x |
| 1.13.x | 1.25 - 1.30 | 3.x |
