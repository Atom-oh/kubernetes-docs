# Amazon EKS Security

> **Supported Versions**: Amazon EKS 1.31, 1.32, 1.33
> **Last Updated**: July 3, 2026

To securely run workloads on Amazon EKS (Elastic Kubernetes Service), you need to understand and implement various security layers and best practices. This document covers key concepts, components, and best practices for strengthening the security of your EKS cluster.

## Table of Contents

1. [EKS Security Overview](#eks-security-overview)
2. [Latest Security Trends (2023)](#latest-security-trends-2023)
3. [IAM and Authentication](#iam-and-authentication)
4. [OIDC Provider Deep Dive](#oidc-provider-deep-dive)
5. [EKS Pod Identity](#eks-pod-identity)
6. [Cluster Endpoint Access Control](#cluster-endpoint-access-control)
7. [Network Security](#network-security)
8. [Pod Security](#pod-security)
9. [Bottlerocket and Read-Only OS](#bottlerocket-and-read-only-os)
10. [IAM Permission Boundaries](#iam-permission-boundaries)
11. [Encryption and Secrets Management](#encryption-and-secrets-management)
12. [Compliance and Auditing](#compliance-and-auditing)
13. [Security Monitoring and Detection](#security-monitoring-and-detection)
14. [EKS Security Best Practices](#eks-security-best-practices)
15. [EKS Security Considerations for Financial Services](#eks-security-considerations-for-financial-services)

## EKS Security Overview

Amazon EKS combines the security features of AWS and Kubernetes to provide a multi-layered security architecture. EKS security consists of the following key areas:

- **Shared Responsibility Model**: AWS manages the security of the EKS control plane, while customers are responsible for the security of worker nodes, containers, and applications.
- **Infrastructure Security**: Network infrastructure security including VPC, subnets, and security groups
- **Cluster Security**: Kubernetes API server access control, RBAC, and service accounts
- **Workload Security**: Container image security, runtime security, and network policies

### EKS Security Architecture

![Architecture diagram showing AWS manages the encrypted control plane, etcd, KMS, and IAM authentication, while the customer secures worker nodes, pods, service accounts, security groups, network policies, and secrets.](../.gitbook/assets/en-eks-05-eks-security-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-0.html)

## Latest Security Trends (2023)

The latest trends and recommendations in the Kubernetes and EKS security domain are as follows:

### 1. Zero Trust Architecture

Moving away from traditional perimeter-based security models, this approach does not trust any access by default and continuously verifies it.

![Architecture diagram mapping five Zero Trust principles to the EKS implementation methods that satisfy each one, from encrypted communication via service mesh mTLS and least privilege via IRSA to traffic inspection via default-deny network policies.](../.gitbook/assets/en-eks-05-eks-security-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-1.html)

Implementing Zero Trust in EKS:
- **Service Mesh**: mTLS communication between services using Istio or AWS App Mesh
- **IAM Roles for Service Accounts (IRSA)**: Fine-grained permission management
- **Network Policies**: Default deny policies that allow only necessary communication
- **OPA/Gatekeeper**: Policy-based access control
- **AWS Security Hub**: Continuous security posture monitoring

### 2. Supply Chain Security

As software supply chain attacks increase, security of the entire pipeline from container images to deployment has become important.

Key implementation methods:
- Adopt **SLSA (Supply-chain Levels for Software Artifacts)** framework
- **Image signing and verification**: Cosign, Notary v2
- **SBOM (Software Bill of Materials)** generation and management: Syft, Grype
- **Image scanning**: Amazon ECR image scanning, Trivy, Clair
- **GitOps security**: Signed commits, secure pipelines

### 3. Runtime Security and Threat Detection

As container runtime security becomes important, the following technologies are gaining attention:

- **eBPF-based security monitoring**: Cilium, Falco
- **AWS GuardDuty EKS Protection**: Runtime threat detection
- **Kubernetes Audit log analysis**: CloudWatch Logs Insights
- **Anomaly behavior detection**: Amazon Detective
- **Container escape prevention**: gVisor, Kata Containers

### 4. Policy as Code

An approach to managing security policies as code to improve consistency and automation:

- **OPA (Open Policy Agent)**: General-purpose policy engine
- **Kyverno**: Kubernetes-native policy management
- **AWS Config**: Compliance monitoring
- **Terraform Sentinel**: IaC policy enforcement
- **AWS CloudFormation Guard**: IaC policy validation

## IAM and Authentication

### EKS Authentication Mechanisms

Amazon EKS provides the following authentication mechanisms:

1. **AWS IAM Authenticator**: Authenticates to the Kubernetes API server using AWS IAM credentials.
2. **OIDC Provider Integration**: Integrates with external OIDC providers (e.g., Active Directory, Okta, Auth0) to manage user authentication.
3. **IAM Roles for Service Accounts**: Links AWS IAM roles to Kubernetes service accounts so pods can securely access AWS services.

![Architecture diagram showing how DevOps, developers, CI/CD, and pods authenticate through IAM Authenticator, OIDC, or IRSA into the Kubernetes API server, RBAC, and service accounts, with IRSA also granting pods direct access to AWS resources.](../.gitbook/assets/en-eks-05-eks-security-2.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-2.html)

### IAM Roles and Policy Configuration

#### EKS Cluster Role

Minimum permissions required when creating an EKS cluster:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:CreateCluster",
        "eks:DescribeCluster",
        "eks:UpdateClusterConfig",
        "eks:DeleteCluster"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "eks.amazonaws.com"
        }
      }
    }
  ]
}
```

#### EKS Access Entry

EKS Access Entry is a new method that replaces the aws-auth ConfigMap for managing IAM user and role access to EKS clusters. Access Entry provides the following benefits:

- Improved stability as an AWS-managed solution
- Management through declarative API
- Version control and audit capabilities
- Separation of node IAM role and user/role access management

```bash
# Enable Access Entry for the cluster
aws eks update-cluster-config \
  --name my-cluster \
  --region us-west-2 \
  --access-config authenticationMode=API_AND_CONFIG_MAP

# Create Access Entry for IAM role
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:role/DevTeamRole \
  --username dev-team \
  --kubernetes-groups dev-team

# Create Access Entry for IAM user
aws eks create-access-entry \
  --cluster-name my-cluster \
  --principal-arn arn:aws:iam::123456789012:user/admin \
  --username admin \
  --kubernetes-groups system:masters

# List Access Entries
aws eks list-access-entries --cluster-name my-cluster
```

> **Note**: EKS Access Entry was introduced in 2023 and provides a more stable and easier to manage method than the aws-auth ConfigMap. Existing clusters can migrate to a hybrid mode that supports both methods.

### IRSA (IAM Roles for Service Accounts)

IRSA allows you to link AWS IAM roles to Kubernetes service accounts so pods can securely access AWS services.

#### IRSA Setup Steps

1. Create an OIDC provider for the EKS cluster:

```bash
eksctl utils associate-iam-oidc-provider --cluster my-cluster --approve
```

2. Create IAM role and policy:

```bash
eksctl create iamserviceaccount \
  --name s3-reader \
  --namespace default \
  --cluster my-cluster \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

3. Associate the service account with a pod:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
spec:
  serviceAccountName: s3-reader
  containers:
  - name: app
    image: amazonlinux:2
    command: ['sh', '-c', 'aws s3 ls']
```

## OIDC Provider Deep Dive

OpenID Connect (OIDC) is the foundation of IAM Roles for Service Accounts (IRSA) in EKS. Understanding how OIDC works helps you troubleshoot authentication issues and implement secure workload identity patterns.

### OIDC Trust Relationship Mechanics

When you create an EKS cluster, AWS automatically creates an OIDC provider endpoint. This endpoint serves as an identity provider that AWS STS trusts to authenticate Kubernetes service accounts.

The trust relationship works as follows:
1. EKS issues OIDC tokens to pods via projected service account tokens
2. The token contains claims about the pod's identity (namespace, service account name)
3. AWS STS validates the token against the OIDC provider's public keys
4. If valid, STS issues temporary AWS credentials

### STS AssumeRoleWithWebIdentity Flow

![Sequence diagram showing a pod exchanging its projected Kubernetes service account JWT with AWS STS via AssumeRoleWithWebIdentity, STS validating the token against the EKS OIDC provider's JWKS and the IAM role trust policy, then returning temporary credentials the pod uses to call an AWS service.](../.gitbook/assets/en-eks-05-eks-security-3.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-3.html)

### Token Exchange Mechanism

The projected service account token is a JWT (JSON Web Token) with the following structure:

```json
{
  "aud": ["sts.amazonaws.com"],
  "exp": 1234567890,
  "iat": 1234567800,
  "iss": "https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE",
  "kubernetes.io": {
    "namespace": "default",
    "pod": {
      "name": "my-pod",
      "uid": "1234-5678-9012-3456"
    },
    "serviceaccount": {
      "name": "my-service-account",
      "uid": "abcd-efgh-ijkl-mnop"
    }
  },
  "sub": "system:serviceaccount:default:my-service-account"
}
```

Key claims:
- **iss**: The OIDC provider URL (must match the IAM trust policy)
- **sub**: The subject (service account identifier)
- **aud**: The audience (must include `sts.amazonaws.com` for AWS)

### OIDC Endpoint Verification

Verify your cluster's OIDC configuration:

```bash
# Get OIDC provider URL
aws eks describe-cluster \
  --name my-cluster \
  --query "cluster.identity.oidc.issuer" \
  --output text

# Example output: https://oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE

# List OIDC providers in your account
aws iam list-open-id-connect-providers

# Get OIDC provider details
aws iam get-open-id-connect-provider \
  --open-id-connect-provider-arn arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE
```

### JWKS URI and Token Validation

The JWKS (JSON Web Key Set) endpoint provides public keys for token validation:

```bash
# Fetch JWKS from OIDC provider
OIDC_URL=$(aws eks describe-cluster --name my-cluster --query "cluster.identity.oidc.issuer" --output text)
curl -s "${OIDC_URL}/.well-known/openid-configuration" | jq .

# Get the JWKS directly
curl -s "${OIDC_URL}/keys" | jq .
```

The JWKS response contains RSA public keys used to verify token signatures:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "key-id-1",
      "use": "sig",
      "alg": "RS256",
      "n": "base64-encoded-modulus",
      "e": "AQAB"
    }
  ]
}
```

## EKS Pod Identity

EKS Pod Identity is a newer authentication mechanism that simplifies how pods access AWS services. It provides advantages over IRSA while maintaining strong security guarantees.

### Advantages over IRSA

| Feature | IRSA | EKS Pod Identity |
|---------|------|------------------|
| Setup Complexity | Requires OIDC provider + IAM role per SA | Simpler Pod Identity Association |
| IAM Role Reuse | One role per service account | Same role across clusters/accounts |
| Session Tags | Limited | Full support for ABAC |
| Cross-Account | Complex trust policies | Simplified with associations |
| Credential Rotation | Token-based, short-lived | Managed by Pod Identity Agent |
| Troubleshooting | Complex token validation | Simpler debugging |

### Pod Identity Agent Mechanics

The EKS Pod Identity Agent runs as a DaemonSet on your nodes and handles credential distribution:

![Architecture diagram of the six-step EKS Pod Identity flow in which a pod's credential request is intercepted by the node's Pod Identity Agent DaemonSet, the agent checks the Pod Identity Association that maps the service account to an IAM role, calls AssumeRoleForPodIdentity to obtain temporary credentials from AWS STS, and delivers them back to the pod.](../.gitbook/assets/en-eks-05-eks-security-4.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-4.html)

### Pod Identity Association Setup

**Using eksctl**:

```bash
# Create Pod Identity Association
eksctl create podidentityassociation \
  --cluster my-cluster \
  --namespace default \
  --service-account-name my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

**Using AWS CLI**:

```bash
# First, create the IAM role with Pod Identity trust policy
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
EOF

aws iam create-role \
  --role-name MyAppRole \
  --assume-role-policy-document file://trust-policy.json

# Attach required policies
aws iam attach-role-policy \
  --role-name MyAppRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create the Pod Identity Association
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace default \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

### IRSA to Pod Identity Migration Procedure

Step-by-step migration from IRSA to Pod Identity:

1. **Install Pod Identity Agent** (if not already installed):

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-pod-identity-agent \
  --addon-version v1.0.0-eksbuild.1
```

2. **Update IAM role trust policy** to support both IRSA and Pod Identity:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:default:my-app-sa"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": [
        "sts:AssumeRole",
        "sts:TagSession"
      ]
    }
  ]
}
```

3. **Create Pod Identity Association**:

```bash
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace default \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

4. **Test the new authentication** by restarting pods:

```bash
kubectl rollout restart deployment my-app -n default
```

5. **Remove IRSA annotations** after verifying Pod Identity works:

```bash
kubectl annotate serviceaccount my-app-sa \
  -n default \
  eks.amazonaws.com/role-arn-
```

6. **Clean up IRSA trust policy** from IAM role (optional, after full migration).

### Pod Identity Architecture Diagram

![Architecture diagram showing two namespaces each associating a service account with its own IAM role, while pods in both namespaces request credentials from a shared Pod Identity Agent and Pod Identity Service before accessing AWS services.](../../assets/diagrams/rendered/en-eks-05-eks-security-5.svg)

## Cluster Endpoint Access Control

EKS cluster endpoint access control determines how users and workloads can reach the Kubernetes API server. Proper configuration is essential for security.

### Public/Private/Public+Private Endpoint Configuration

EKS supports three endpoint access configurations:

| Configuration | Public Endpoint | Private Endpoint | Use Case |
|--------------|-----------------|------------------|----------|
| Public Only | Enabled | Disabled | Development, testing |
| Private Only | Disabled | Enabled | High-security production |
| Public + Private | Enabled | Enabled | Balanced security and convenience |

**Public Only** (default):
- API server accessible from the internet
- Nodes communicate over the internet
- Simplest setup but least secure

**Private Only**:
- API server only accessible from within VPC
- Requires VPN, Direct Connect, or bastion host for kubectl access
- Nodes communicate over private network
- Most secure option

**Public + Private**:
- API server accessible from both internet and VPC
- Nodes communicate over private network (more efficient)
- Good balance of security and usability

### CIDR Restriction Settings

When using public endpoint, restrict access to specific IP ranges:

```bash
# Update cluster to restrict public access
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=true,\
    endpointPrivateAccess=true,\
    publicAccessCidrs="10.0.0.0/8","203.0.113.0/24"
```

Using eksctl:

```yaml
# cluster-config.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2

vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 10.0.0.0/8        # Internal corporate network
    - 203.0.113.0/24    # Office IP range
```

### Private Cluster Operation Patterns

Operating a private-only EKS cluster requires network connectivity solutions:

**Pattern 1: VPN Access**

![Architecture diagram showing an admin workstation reaching the EKS control plane API server over an AWS VPN tunnel into the cluster VPC and through its private endpoint only, without exposing the API server to the internet.](../.gitbook/assets/en-eks-05-eks-security-6.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-6.html)

```bash
# Create Client VPN endpoint
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.100.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-west-2:123456789012:certificate/abc123 \
  --authentication-options Type=certificate-authentication,MutualAuthentication={ClientRootCertificateChainArn=arn:aws:acm:us-west-2:123456789012:certificate/xyz789} \
  --connection-log-options Enabled=false \
  --vpc-id vpc-12345678
```

**Pattern 2: Transit Gateway**

![Architecture diagram showing an on-premises admin workstation reaching the EKS cluster's private API endpoint through Direct Connect or Site-to-Site VPN into a Transit Gateway that routes into the EKS VPC.](../.gitbook/assets/en-eks-05-eks-security-7.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-7.html)

**Pattern 3: Bastion Host with SSM**

```yaml
# Bastion host deployment for kubectl access
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubectl-bastion
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kubectl-bastion
  template:
    metadata:
      labels:
        app: kubectl-bastion
    spec:
      serviceAccountName: kubectl-bastion-sa
      containers:
      - name: bastion
        image: amazon/aws-cli:latest
        command: ["sleep", "infinity"]
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
```

Access via SSM Session Manager:

```bash
# Start SSM session to bastion pod's node
aws ssm start-session --target i-1234567890abcdef0

# Or use kubectl exec through SSM
aws ssm start-session \
  --target i-1234567890abcdef0 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["443"],"localPortNumber":["6443"]}'
```

### Endpoint Access Control Configuration Example

Complete example for a production-ready private cluster:

```bash
# Create cluster with private endpoint only
eksctl create cluster \
  --name production-cluster \
  --region us-west-2 \
  --vpc-private-subnets subnet-private1,subnet-private2,subnet-private3 \
  --without-nodegroup

# Update to private-only endpoint
aws eks update-cluster-config \
  --name production-cluster \
  --resources-vpc-config \
    endpointPublicAccess=false,\
    endpointPrivateAccess=true

# Verify endpoint configuration
aws eks describe-cluster \
  --name production-cluster \
  --query "cluster.resourcesVpcConfig.{PublicAccess:endpointPublicAccess,PrivateAccess:endpointPrivateAccess,PublicCIDRs:publicAccessCidrs}"
```

Required VPC endpoints for private clusters:

```bash
# Create required VPC endpoints
for service in ec2 ecr.api ecr.dkr s3 logs sts elasticloadbalancing autoscaling; do
  aws ec2 create-vpc-endpoint \
    --vpc-id vpc-12345678 \
    --service-name com.amazonaws.us-west-2.${service} \
    --subnet-ids subnet-private1 subnet-private2 \
    --security-group-ids sg-12345678
done
```

### Customer-Routed Control Plane Egress (June 2026)

> **Announced**: June 18, 2026 · [Source](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-customer-routed-control-plane-egress/)

Previously, when the EKS Kubernetes API server needed to reach external endpoints (admission webhooks, private OIDC providers, aggregated API servers), that egress traffic left through an AWS-managed path. With Customer-Routed Control Plane Egress, you can route this control plane egress traffic directly through your own VPC instead.

**Supported traffic**:
- Admission webhook calls (OPA/Gatekeeper, Kyverno)
- Private OIDC provider access
- Aggregated API server access (e.g., Metrics Server, custom APIs)

**Key characteristics**:
- Because control plane egress traverses the customer VPC, you can implement a data perimeter and monitor/inspect traffic within your own network
- Enforceable at the organization level using the `eks:controlPlaneEgressMode` IAM condition key in an SCP
- Can be applied to existing clusters, no additional cost, available in all regions

```bash
# Enable customer-routed control plane egress on a cluster
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config controlPlaneEgressMode=CUSTOMER_ROUTED
```

```json
// SCP example: enforce customer-routed egress mode
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequireCustomerRoutedControlPlaneEgress",
      "Effect": "Deny",
      "Action": [
        "eks:CreateCluster",
        "eks:UpdateClusterConfig"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "eks:controlPlaneEgressMode": "CUSTOMER_ROUTED"
        }
      }
    }
  ]
}
```

## Network Security

### Security Groups

You can use AWS security groups to control network traffic to nodes and pods in your EKS cluster.

![EKS network security architecture showing internet traffic entering through a public-subnet ALB and bastion host to worker nodes in private subnets, each component wrapped in its own security group, the EKS control plane managing the nodes, network policies governing pod traffic, and worker nodes reaching ECR, S3 and STS privately through VPC endpoints.](../.gitbook/assets/en-eks-05-eks-security-8.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-8.html)

#### Cluster Security Group

The EKS cluster security group allows communication between the control plane and worker nodes:

- Port 443 (HTTPS): Cluster API server communication
- Port 10250: kubelet API
- Port range 1025-65535: Inter-node communication

#### Node Security Group

Recommended security group configuration for worker nodes:

- Inbound: Allow traffic from cluster security group
- Outbound: Allow all traffic (can be restricted as needed)

### Network Policies

You can use Kubernetes network policies to control communication between pods. In EKS, you can implement network policies through network plugins such as Amazon VPC CNI, Calico, and Cilium.

#### Default Deny Policy Example

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: default
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

#### Allow Policy Example for Specific Applications

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### VPC Endpoints

Use VPC endpoints for private access to AWS services to securely access AWS services without going through an internet gateway.

Recommended VPC endpoints for EKS clusters:

- com.amazonaws.region.ecr.api
- com.amazonaws.region.ecr.dkr
- com.amazonaws.region.s3
- com.amazonaws.region.logs
- com.amazonaws.region.sts

## Pod Security

### Pod Security Standards (PSS)

Pod Security Standards, introduced in Kubernetes 1.23, provide a built-in mechanism for restricting the security context of pods. You can apply the following levels of PSS in EKS:

- **Privileged**: No restrictions
- **Baseline**: Prevent known privilege escalation
- **Restricted**: Apply strong security restrictions

![Diagram showing how the Privileged, Baseline and Restricted Pod Security Standards selected by namespace labels (enforce, audit, warn), pod securityContext settings, and OPA Gatekeeper or Kyverno policies enforced through an admission webhook apply to privileged, application and system pods.](../.gitbook/assets/en-eks-05-eks-security-9.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-9.html)

Example of applying PSS to a namespace:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Security Context

You can configure security context at the pod and container level to restrict privileges:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: secure-container
    image: nginx
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### OPA Gatekeeper and Kyverno

You can apply security policies across the cluster using policy engines like OPA Gatekeeper or Kyverno.

#### Kyverno Policy Example - Prevent Privileged Containers

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  validationFailureAction: enforce
  rules:
  - name: privileged-containers
    match:
      resources:
        kinds:
        - Pod
    validate:
      message: "Privileged containers are not allowed"
      pattern:
        spec:
          containers:
          - name: "*"
            securityContext:
              privileged: false
```

## Bottlerocket and Read-Only OS

Bottlerocket is a purpose-built, security-focused operating system designed specifically for running containers. It provides enhanced security through its minimal footprint and immutable design.

### Bottlerocket Characteristics

**API-Based Configuration**:
- No SSH access by default
- Configuration changes through API (apiclient)
- Settings persisted across reboots
- Changes validated before application

```bash
# Example: Configure Bottlerocket settings via user data
[settings.kubernetes]
cluster-name = "my-cluster"
api-server = "https://EXAMPLE.gr7.us-west-2.eks.amazonaws.com"
cluster-certificate = "BASE64_ENCODED_CERT"

[settings.kubernetes.node-labels]
"node.kubernetes.io/os" = "bottlerocket"

[settings.kubernetes.node-taints]
"bottlerocket" = "true:NoSchedule"
```

**Automatic Updates**:
- Wave-based update deployment
- Automatic rollback on failure
- Configurable update windows

```bash
# Configure update settings
[settings.updates]
targets-base-url = "https://updates.bottlerocket.aws/"
version-lock = "1.15.%"  # Lock to specific minor version
```

### SELinux Enforcement

Bottlerocket runs SELinux in enforcing mode by default:

- **Process Isolation**: Containers cannot access host resources
- **File System Protection**: Strict access controls on system files
- **Network Isolation**: Controlled network access between processes

SELinux provides mandatory access control that prevents:
- Container escape attacks
- Privilege escalation
- Unauthorized file access

### dm-verity (Root Filesystem Integrity)

dm-verity provides cryptographic verification of the root filesystem:

![Diagram of dm-verity verifying the read-only root filesystem: each block read is hashed, the hash is compared against the value stored in the Merkle Tree, and access is allowed on a match or denied on a mismatch.](../.gitbook/assets/en-eks-05-eks-security-11.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-11.html)

Key benefits:
- **Tamper Detection**: Any modification to system files is detected
- **Boot-Time Verification**: System integrity verified before containers start
- **Read-Only Root**: Root filesystem mounted read-only

### Immutable Infrastructure Strategy

Bottlerocket enables a true immutable infrastructure approach:

1. **No In-Place Updates**: Replace nodes instead of patching
2. **Consistent State**: Every node starts from a known-good image
3. **Audit Trail**: All changes tracked through AMI versions
4. **Fast Recovery**: Roll back by launching previous AMI

Implementation pattern:

```yaml
# Node group with Bottlerocket
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: secure-cluster
  region: us-west-2

managedNodeGroups:
  - name: bottlerocket-ng
    instanceType: m5.large
    desiredCapacity: 3
    amiFamily: Bottlerocket
    bottlerocket:
      settings:
        kubernetes:
          node-labels:
            os: bottlerocket
        host-containers:
          admin:
            enabled: false  # Disable admin container for production
```

### Using Bottlerocket with EKS Managed Node Groups

Complete setup for Bottlerocket managed node groups:

```bash
# Create managed node group with Bottlerocket
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name bottlerocket-nodes \
  --node-role arn:aws:iam::123456789012:role/EKSNodeRole \
  --subnets subnet-1 subnet-2 subnet-3 \
  --ami-type BOTTLEROCKET_x86_64 \
  --instance-types m5.large \
  --scaling-config minSize=2,maxSize=10,desiredSize=3 \
  --update-config maxUnavailable=1
```

Using eksctl with advanced configuration:

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: production-cluster
  region: us-west-2

managedNodeGroups:
  - name: bottlerocket-workers
    instanceType: m5.xlarge
    minSize: 3
    maxSize: 20
    desiredCapacity: 5
    amiFamily: Bottlerocket
    volumeSize: 100
    volumeType: gp3
    volumeEncrypted: true
    iam:
      attachPolicyARNs:
        - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
        - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
        - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
    bottlerocket:
      settings:
        kubernetes:
          node-labels:
            workload-type: general
            os: bottlerocket
          node-taints:
            - key: "CriticalAddonsOnly"
              value: "true"
              effect: "NoSchedule"
        kernel:
          sysctl:
            "net.core.somaxconn": "32768"
            "net.ipv4.tcp_max_syn_backlog": "32768"
        host-containers:
          admin:
            enabled: false
          control:
            enabled: true
```

## IAM Permission Boundaries

IAM Permission Boundaries provide a mechanism to set the maximum permissions that an IAM entity can have, regardless of what policies are attached to it.

### Permission Boundary Concept

The effective permissions are the intersection of identity-based policies and permission boundaries:

```
Effective Permissions = Identity Policy ∩ Permission Boundary
```

![Diagram showing that effective permissions are the intersection of the identity-based policy and the permission boundary, with an example where a policy allowing s3:*, ec2:* and rds:* meets a boundary allowing only s3:* and ec2:Describe*, leaving s3:* and ec2:Describe* as the effective permissions.](../.gitbook/assets/en-eks-05-eks-security-12.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-12.html)

Example scenario:
- Identity policy allows: `s3:*`, `ec2:*`, `rds:*`
- Permission boundary allows: `s3:*`, `ec2:Describe*`
- Effective permissions: `s3:*`, `ec2:Describe*`

### SCP (Service Control Policy) Usage

SCPs provide guardrails at the AWS Organizations level:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyEKSClusterDeletion",
      "Effect": "Deny",
      "Action": "eks:DeleteCluster",
      "Resource": "*",
      "Condition": {
        "StringNotLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:role/EKSAdminRole"
        }
      }
    },
    {
      "Sid": "RequireIMDSv2",
      "Effect": "Deny",
      "Action": "ec2:RunInstances",
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringNotEquals": {
          "ec2:MetadataHttpTokens": "required"
        }
      }
    },
    {
      "Sid": "DenyPublicEKSEndpoint",
      "Effect": "Deny",
      "Action": "eks:UpdateClusterConfig",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "eks:endpointPublicAccess": "true"
        }
      }
    }
  ]
}
```

### Least Privilege IAM Policy Patterns

Best practices for EKS IAM policies:

**Pattern 1: Namespace-Scoped Permissions**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowNamespaceOperations",
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowSpecificClusterAccess",
      "Effect": "Allow",
      "Action": [
        "eks:AccessKubernetesApi"
      ],
      "Resource": "arn:aws:eks:us-west-2:123456789012:cluster/production-cluster",
      "Condition": {
        "StringEquals": {
          "eks:namespaces": ["team-a", "team-a-staging"]
        }
      }
    }
  ]
}
```

**Pattern 2: Resource-Based Restrictions**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowECRPull",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "arn:aws:ecr:us-west-2:123456789012:repository/approved-*"
    },
    {
      "Sid": "AllowECRAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    }
  ]
}
```

**Pattern 3: Condition-Based Access**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3AccessWithTags",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::app-bucket/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Environment": "${aws:PrincipalTag/Environment}"
        }
      }
    }
  ]
}
```

### EKS Node Role Permission Boundary Example

Apply permission boundaries to EKS node roles to limit blast radius:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEKSNodeOperations",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeNetworkInterfaces",
        "ec2:AttachVolume",
        "ec2:DetachVolume",
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyPrivilegedActions",
      "Effect": "Deny",
      "Action": [
        "iam:*",
        "organizations:*",
        "account:*",
        "eks:DeleteCluster",
        "eks:UpdateClusterConfig",
        "ec2:DeleteVpc",
        "ec2:DeleteSubnet",
        "ec2:DeleteSecurityGroup"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowSecretsInNamespace",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:/eks/production/*"
    }
  ]
}
```

Apply the boundary to the node role:

```bash
# Create permission boundary
aws iam create-policy \
  --policy-name EKSNodePermissionBoundary \
  --policy-document file://node-permission-boundary.json

# Apply boundary to node role
aws iam put-role-permissions-boundary \
  --role-name EKSNodeRole \
  --permissions-boundary arn:aws:iam::123456789012:policy/EKSNodePermissionBoundary

# Verify boundary is applied
aws iam get-role --role-name EKSNodeRole --query "Role.PermissionsBoundary"
```

### Proactive Governance with 7 New IAM Condition Keys (April 2026)

> **Announced**: April 20, 2026 · [Source](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-iam-condition-keys/)

Amazon EKS added seven new IAM condition keys that let you enforce policy-based, proactive governance at cluster creation and update time. These conditions can be applied to the `CreateCluster`, `UpdateClusterConfig`, `UpdateClusterVersion`, and `AssociateEncryptionConfig` APIs, and integrated with AWS Organizations SCPs.

| Condition Key | Purpose |
|----------------|---------|
| `eks:endpointPublicAccess` / `eks:endpointPrivateAccess` | Enforce use of the private endpoint |
| `eks:encryptionConfigProviderKeyArns` | Require KMS-based secrets encryption |
| `eks:kubernetesVersion` | Restrict cluster creation/upgrade to approved Kubernetes versions |
| `eks:controlPlaneScalingTier` | Restrict the control plane scaling tier |
| `eks:deletionProtection` | Enforce cluster deletion protection |
| `eks:zonalShiftEnabled` | Control whether zonal shift is enabled |

```json
// SCP example: require private endpoint and KMS encryption
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RequirePrivateEndpointAndKmsEncryption",
      "Effect": "Deny",
      "Action": [
        "eks:CreateCluster",
        "eks:UpdateClusterConfig"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {
          "eks:endpointPublicAccess": "true"
        }
      }
    },
    {
      "Sid": "RequireEncryptionConfig",
      "Effect": "Deny",
      "Action": "eks:CreateCluster",
      "Resource": "*",
      "Condition": {
        "Null": {
          "eks:encryptionConfigProviderKeyArns": "true"
        }
      }
    },
    {
      "Sid": "RestrictKubernetesVersion",
      "Effect": "Deny",
      "Action": [
        "eks:CreateCluster",
        "eks:UpdateClusterVersion"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "eks:kubernetesVersion": ["1.32", "1.33"]
        }
      }
    }
  ]
}
```

## Encryption and Secrets Management

### EKS Encryption Options

#### etcd Encryption

EKS encrypts Kubernetes secrets stored in etcd by default. You can use AWS KMS for an additional layer of encryption:

![Architecture diagram of EKS encryption options showing AWS KMS adding an extra encryption layer over default etcd encryption, and secrets management solutions such as AWS Secrets Manager, Parameter Store, HashiCorp Vault and Mozilla SOPS feeding Kubernetes Secrets through the External Secrets Operator, ASCP and Secrets Store CSI Driver before being consumed by pods via mounts, environment variables and init containers.](../.gitbook/assets/en-eks-05-eks-security-13.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-13.html)

```bash
eksctl create cluster --name my-cluster --region us-west-2 --encryption-provider-config-key arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab
```

### AWS Secrets Manager and Parameter Store Integration

You can use External Secrets Operator or AWS Secrets and Configuration Provider (ASCP) to mount secrets stored in AWS Secrets Manager or Parameter Store to Kubernetes pods.

#### Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

#### Define SecretStore and ExternalSecret

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: db-credentials
  data:
  - secretKey: username
    remoteRef:
      key: db-credentials
      property: username
  - secretKey: password
    remoteRef:
      key: db-credentials
      property: password
```

### SOPS (Secrets OPerationS)

You can use Mozilla SOPS to securely store and manage encrypted secrets in Git repositories.

#### SOPS Installation and Usage

```bash
# Install SOPS
brew install sops

# Encrypt secrets using AWS KMS key
sops --encrypt --aws-profile default --kms arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab secrets.yaml > secrets.enc.yaml

# Decrypt encrypted secrets
sops --decrypt secrets.enc.yaml
```

## Compliance and Auditing

### EKS Audit Logging

You can enable EKS control plane audit logs to record all API calls made in the cluster:

![Architecture diagram of the compliance and auditing flow: control-plane, audit, CloudTrail and Fluent Bit logs are collected in Amazon CloudWatch, stored and analyzed, and passed through AWS Security Hub to alerting and reporting, while AWS Config and Amazon Inspector findings are evaluated against the CIS Kubernetes Benchmark to confirm compliance with standards such as PCI DSS, HIPAA, GDPR, SOC 2 and ISO 27001.](../.gitbook/assets/en-eks-05-eks-security-14.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-14.html)

```bash
aws eks update-cluster-config \
  --region us-west-2 \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

### AWS Config Rules

You can use AWS Config to monitor the compliance status of your EKS cluster:

- eks-cluster-logging-enabled
- eks-cluster-oldest-supported-version
- eks-endpoint-no-public-access
- eks-secrets-encrypted

### AWS Security Hub Integration

You can use AWS Security Hub to centrally manage and monitor the security posture of your EKS cluster. Security Hub checks compliance against industry standards such as the CIS Kubernetes Benchmark.

## Security Monitoring and Detection

### GuardDuty EKS Protection

You can enable Amazon GuardDuty EKS Protection to detect potential security threats in your EKS cluster:

![Architecture diagram showing AWS security services (GuardDuty, Security Hub, CloudWatch) and Kubernetes security tools (Falco, kube-audit) covering runtime, network, identity and configuration detection types, feeding a threat detection workflow of collection, analysis, detection, response and remediation, with findings reported back into Security Hub.](../.gitbook/assets/en-eks-05-eks-security-15.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-15.html)

```bash
aws guardduty update-detector \
  --detector-id 12abc34d567e8fa901bc2d34e56789f0 \
  --features '[{"Name": "EKS_RUNTIME_MONITORING", "Status": "ENABLED"}]'
```

### AWS Security Hub

You can use AWS Security Hub to centrally manage and monitor the security posture of your EKS cluster:

```bash
aws securityhub enable-security-hub
aws securityhub batch-enable-standards --standards-subscription-requests '[{"StandardsArn":"arn:aws:securityhub:us-west-2::standards/aws-foundational-security-best-practices/v/1.0.0"}]'
```

### Falco

You can use Falco to perform runtime security monitoring and anomaly detection:

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco --namespace falco --create-namespace
```

Falco rule example:

```yaml
- rule: Terminal shell in container
  desc: A shell was spawned by a pod in the container
  condition: container and shell_procs and not container_entrypoint
  output: Shell spawned in a container (user=%user.name pod=%k8s.pod.name container=%container.name shell=%proc.name parent=%proc.pname cmdline=%proc.cmdline)
  priority: WARNING
```

## EKS Security Best Practices

### Cluster Security Hardening

1. **Maintain Latest Kubernetes Version**: Regularly upgrade EKS cluster to latest version to apply security patches
2. **Use Private API Endpoint**: Restrict access to API server from public internet
3. **Apply Principle of Least Privilege**: Apply principle of least privilege to IAM roles and RBAC
4. **Restrict Security Groups**: Configure security groups to allow only necessary ports
5. **Implement Network Policies**: Apply network policies to restrict communication between pods

### Node and Container Security

1. **Use Latest AMI**: Use EKS-optimized AMI with latest security patches
2. **Scan Container Images**: Use ECR image scanning or tools like Trivy for vulnerability scanning
3. **Use Immutable Infrastructure**: Create new node groups and delete old node groups when updating nodes
4. **Run Containers as Non-Root User**: Run containers as non-root user to limit privileges
5. **Use Read-Only Filesystem**: Mount container root filesystem as read-only when possible

### Continuous Security Monitoring

1. **Enable Audit Logging**: Enable EKS control plane audit logs
2. **Enable GuardDuty EKS Protection**: Enable GuardDuty EKS Protection for runtime security monitoring
3. **Security Hub Integration**: Use AWS Security Hub for centralized security posture management
4. **Regular Security Assessments**: Perform regular security assessments based on CIS Kubernetes Benchmark
5. **Establish Incident Response Plan**: Establish and test security incident response plan for EKS cluster

## EKS Security Considerations for Financial Services

Additional security requirements to consider when using EKS in the financial services industry:

### Regulatory Compliance

1. **PCI DSS**: PCI DSS requirements compliance for workloads processing card payment data
2. **GDPR/CCPA**: Compliance with data protection regulations for personally identifiable information (PII)
3. **Financial Regulations**: Compliance with domestic financial regulatory requirements (e.g., Financial Supervisory Service guidelines)

### Data Security

1. **Encryption in Transit**: Encrypt all network communications using TLS 1.2 or higher
2. **Data at Rest Encryption**: Encrypt data at rest using AWS KMS
3. **Data Classification**: Classify data by sensitivity and apply appropriate security controls
4. **Data Access Logging**: Detailed logging and monitoring for all sensitive data access

### High Availability and Disaster Recovery

1. **Multi-AZ Deployment**: Deploy EKS cluster across multiple availability zones
2. **Disaster Recovery Plan**: Establish disaster recovery plan including regular backups and recovery testing
3. **Business Continuity**: Define RTO (Recovery Time Objective) and RPO (Recovery Point Objective) appropriate for financial services

### EKS Security Architecture Example for Financial Services

![Architecture diagram of a financial services VPC in which internet traffic passes through AWS WAF and an Application Load Balancer to application pods and security sidecars in private subnets, the pods access RDS, S3, and DynamoDB data services encrypted with AWS KMS keys, and GuardDuty, Security Hub, AWS Config, and CloudTrail monitor the EKS cluster.](../.gitbook/assets/en-eks-05-eks-security-16.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-05-eks-security-16.html)

## Conclusion

Amazon EKS security is implemented through a multi-layered defense strategy. You can securely operate your EKS cluster through strong authentication and authorization via IAM and RBAC, network security through network policies and security groups, workload security through Pod Security Standards and security context, and integration with various AWS security services.

In industries with strict regulations such as financial services, additional security controls and compliance requirements should be considered. It is important to maintain the security posture of your EKS environment through regular security assessments, vulnerability scanning, and continuous monitoring.

## References

- [Amazon EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/overview/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [AWS Security Hub](https://aws.amazon.com/security-hub/)
- [Amazon GuardDuty](https://aws.amazon.com/guardduty/)
- [Amazon EKS Customer-Routed Control Plane Egress (2026-06-18)](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-eks-customer-routed-control-plane-egress/)
- [Amazon EKS New IAM Condition Keys (2026-04-20)](https://aws.amazon.com/about-aws/whats-new/2026/04/amazon-eks-iam-condition-keys/)

## Quiz

To test what you learned in this chapter, try the [topic quiz](../quizzes/eks/05-eks-security-quiz.md).
