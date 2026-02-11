# Amazon EKS Security

> **Supported Versions**: Amazon EKS 1.31, 1.32, 1.33
> **Last Updated**: July 25, 2025

To securely run workloads on Amazon EKS (Elastic Kubernetes Service), you need to understand and implement various security layers and best practices. This document covers key concepts, components, and best practices for strengthening the security of your EKS cluster.

## Table of Contents

1. [EKS Security Overview](#eks-security-overview)
2. [Latest Security Trends (2023)](#latest-security-trends-2023)
3. [IAM and Authentication](#iam-and-authentication)
4. [Network Security](#network-security)
5. [Pod Security](#pod-security)
6. [Encryption and Secrets Management](#encryption-and-secrets-management)
7. [Compliance and Auditing](#compliance-and-auditing)
8. [Security Monitoring and Detection](#security-monitoring-and-detection)
9. [EKS Security Best Practices](#eks-security-best-practices)
10. [EKS Security Considerations for Financial Services](#eks-security-considerations-for-financial-services)

## EKS Security Overview

Amazon EKS combines the security features of AWS and Kubernetes to provide a multi-layered security architecture. EKS security consists of the following key areas:

- **Shared Responsibility Model**: AWS manages the security of the EKS control plane, while customers are responsible for the security of worker nodes, containers, and applications.
- **Infrastructure Security**: Network infrastructure security including VPC, subnets, and security groups
- **Cluster Security**: Kubernetes API server access control, RBAC, and service accounts
- **Workload Security**: Container image security, runtime security, and network policies

### EKS Security Architecture

```mermaid
flowchart TD
    subgraph AWS["AWS Responsibility"]
        CP[EKS Control Plane] --> |Encrypted Communication| ETCD[etcd]
        CP --> |Managed| KMS[AWS KMS]
    end

    subgraph Customer["Customer Responsibility"]
        WN[Worker Nodes] --> |Run| Pods[Pods/Containers]
        Pods --> |Use| SA[Service Accounts]
        WN --> |Apply| SG[Security Groups]
        Pods --> |Apply| NP[Network Policies]
        Pods --> |Use| Secrets[Kubernetes Secrets]
    end

    CP <--> |Authentication/Authorization| IAM[AWS IAM]
    CP <--> |Encrypted Communication| WN

    style AWS fill:#FFCC99,stroke:#FF9900,stroke-width:2px
    style Customer fill:#CCFFCC,stroke:#009900,stroke-width:2px
```

## Latest Security Trends (2023)

The latest trends and recommendations in the Kubernetes and EKS security domain are as follows:

### 1. Zero Trust Architecture

Moving away from traditional perimeter-based security models, this approach does not trust any access by default and continuously verifies it.

```mermaid
flowchart LR
    subgraph ZTA["Zero Trust Principles"]
        P1["Encrypt All Communications"]
        P2["Principle of Least Privilege"]
        P3["Continuous Verification"]
        P4["Fine-grained Access Control"]
        P5["Inspect All Traffic"]
    end

    subgraph Implementation["EKS Implementation Methods"]
        I1["Service Mesh (Istio)"]
        I2["IAM Roles for Service Accounts"]
        I3["Network Policies"]
        I4["OPA/Gatekeeper"]
        I5["AWS Security Hub"]
    end

    P1 --> I1
    P2 --> I2
    P3 --> I5
    P4 --> I4
    P5 --> I3

    classDef principle fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef implementation fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    class P1,P2,P3,P4,P5 principle;
    class I1,I2,I3,I4,I5 implementation;
    class ZTA,Implementation default;
```

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

```mermaid
flowchart TD
    subgraph Authentication_Methods ["EKS Authentication Mechanisms"]
        IAM_Auth[AWS IAM Authenticator]
        OIDC[OIDC Provider Integration]
        IRSA["IAM Roles for Service Accounts
                IRSA"]
    end

    subgraph Users_and_Services ["Users and Services"]
        DevOps[DevOps Team]
        Developers[Developers]
        CI_CD[CI/CD Pipeline]
        Pods[Kubernetes Pods]
    end

    subgraph AWS_Resources ["AWS Resources"]
        S3[Amazon S3]
        DynamoDB[Amazon DynamoDB]
        SQS[Amazon SQS]
        SNS[Amazon SNS]
    end

    subgraph K8s_Resources ["Kubernetes Resources"]
        API_Server[API Server]
        ServiceAccounts[Service Accounts]
        RBAC[RBAC Permissions]
    end

    DevOps --> IAM_Auth
    Developers --> IAM_Auth
    Developers --> OIDC
    CI_CD --> OIDC
    Pods --> IRSA

    IAM_Auth --> API_Server
    OIDC --> API_Server
    IRSA --> ServiceAccounts

    ServiceAccounts --> RBAC
    RBAC --> API_Server

    IRSA --> AWS_Resources

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class S3,DynamoDB,SQS,SNS,IAM_Auth awsService;
    class API_Server,ServiceAccounts,RBAC k8sComponent;
    class DevOps,Developers,CI_CD,Pods userApp;
    class OIDC,IRSA default;
```

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

## Network Security

### Security Groups

You can use AWS security groups to control network traffic to nodes and pods in your EKS cluster.

```mermaid
flowchart TD
    subgraph VPC ["Amazon VPC"]
        subgraph Public_Subnets ["Public Subnets"]
            ALB["Application
                Load Balancer"]
            NAT[NAT Gateway]
            Bastion[Bastion Host]
        end

        subgraph Private_Subnets ["Private Subnets"]
            subgraph EKS_Cluster ["EKS Cluster"]
                CP[EKS Control Plane]

                subgraph Worker_Nodes ["Worker Nodes"]
                    Node1[Node 1]
                    Node2[Node 2]
                    Node3[Node 3]
                end

                subgraph Network_Policies ["Network Policies"]
                    Default_Deny[Default Deny Policy]
                    App_Allow[App Allow Policy]
                end
            end
        end

        subgraph Security_Groups ["Security Groups"]
            CP_SG["Control Plane
                Security Group"]
            Node_SG["Node
                Security Group"]
            ALB_SG["ALB
                Security Group"]
            Bastion_SG["Bastion
                Security Group"]
        end

        subgraph VPC_Endpoints ["VPC Endpoints"]
            ECR_API["ECR API
                Endpoint"]
            ECR_DKR["ECR DKR
                Endpoint"]
            S3_EP[S3 Endpoint]
            STS_EP[STS Endpoint]
        end
    end

    Internet((Internet)) --> ALB
    Internet --> Bastion

    ALB --> Node1
    ALB --> Node2
    ALB --> Node3

    Bastion --> Node1
    Bastion --> Node2
    Bastion --> Node3

    CP --> Node1
    CP --> Node2
    CP --> Node3

    Node1 --> ECR_API
    Node1 --> ECR_DKR
    Node1 --> S3_EP
    Node1 --> STS_EP

    CP_SG --> CP
    Node_SG --> Worker_Nodes
    ALB_SG --> ALB
    Bastion_SG --> Bastion

    Network_Policies --> Node1
    Network_Policies --> Node2
    Network_Policies --> Node3

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CP,ALB,NAT,Bastion,CP_SG,Node_SG,ALB_SG,Bastion_SG,ECR_API,ECR_DKR,S3_EP,STS_EP awsService;
    class Node1,Node2,Node3,Default_Deny,App_Allow k8sComponent;
```

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

```mermaid
flowchart TD
    subgraph Pod_Security ["Pod Security Layers"]
        subgraph PSS ["Pod Security Standards"]
            Privileged["Privileged
                No Restrictions"]
            Baseline["Baseline
                Prevent Privilege Escalation"]
            Restricted["Restricted
                Strong Restrictions"]
        end

        subgraph Security_Context ["Security Context"]
            RunAsUser["Non-root User
                runAsUser"]
            ReadOnlyFS["Read-only Filesystem
                readOnlyRootFilesystem"]
            NoPrivEsc["Prevent Privilege Escalation
                allowPrivilegeEscalation"]
            DropCaps["Drop Capabilities
                capabilities.drop"]
        end

        subgraph Policy_Engines ["Policy Engines"]
            OPA[OPA Gatekeeper]
            Kyverno[Kyverno]
            AdmissionControllers[Admission Controllers]
        end
    end

    subgraph Enforcement ["Enforcement Methods"]
        NS_Labels[Namespace Labels]
        Webhook[Webhook]
        Audit[Audit]
    end

    subgraph Pod_Types ["Pod Type Security"]
        App_Pod[Application Pods]
        System_Pod[System Pods]
        Privileged_Pod[Privileged Pods]
    end

    Privileged --> Privileged_Pod
    Baseline --> App_Pod
    Restricted --> App_Pod

    Security_Context --> App_Pod
    Security_Context --> System_Pod

    OPA --> Webhook
    Kyverno --> Webhook
    AdmissionControllers --> Webhook

    NS_Labels --> PSS
    Webhook --> Policy_Engines
    Audit --> PSS

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class Privileged,Baseline,Restricted,RunAsUser,ReadOnlyFS,NoPrivEsc,DropCaps k8sComponent;
    class OPA,Kyverno,AdmissionControllers k8sComponent;
    class NS_Labels,Webhook,Audit default;
    class App_Pod,System_Pod,Privileged_Pod userApp;
```

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

## Encryption and Secrets Management

### EKS Encryption Options

#### etcd Encryption

EKS encrypts Kubernetes secrets stored in etcd by default. You can use AWS KMS for an additional layer of encryption:

```mermaid
flowchart TD
    subgraph Encryption_Options ["EKS Encryption Options"]
        subgraph ETCD_Encryption ["etcd Encryption"]
            Default[Default Encryption]
            KMS_Encryption[AWS KMS Encryption]
        end

        subgraph Secret_Management ["Secrets Management Solutions"]
            K8s_Secrets[Kubernetes Secrets]
            AWS_SM[AWS Secrets Manager]
            AWS_PS[AWS Parameter Store]
            Vault[HashiCorp Vault]
            SOPS[Mozilla SOPS]
        end

        subgraph Integration_Tools ["Integration Tools"]
            ESO["External Secrets
                Operator"]
            ASCP["AWS Secrets and
                Configuration Provider"]
            CSI_Driver["Secrets Store
                CSI Driver"]
        end
    end

    subgraph Usage_Patterns ["Usage Patterns"]
        subgraph Storage ["Storage"]
            Encrypted_Storage[Encrypted Storage]
            Version_Control[Version Control]
            Access_Control[Access Control]
        end

        subgraph Retrieval ["Retrieval"]
            Pod_Mount[Pod Mount]
            Env_Vars[Environment Variables]
            Init_Container[Init Container]
        end
    end

    KMS_Encryption --> Default

    AWS_SM --> ESO
    AWS_PS --> ESO
    AWS_SM --> ASCP
    AWS_PS --> ASCP
    Vault --> CSI_Driver

    ESO --> K8s_Secrets
    ASCP --> K8s_Secrets
    CSI_Driver --> K8s_Secrets

    K8s_Secrets --> Encrypted_Storage
    AWS_SM --> Encrypted_Storage
    AWS_PS --> Encrypted_Storage
    Vault --> Encrypted_Storage
    SOPS --> Encrypted_Storage

    AWS_SM --> Version_Control
    Vault --> Version_Control

    AWS_SM --> Access_Control
    AWS_PS --> Access_Control
    Vault --> Access_Control

    K8s_Secrets --> Pod_Mount
    K8s_Secrets --> Env_Vars
    K8s_Secrets --> Init_Container

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class KMS_Encryption,AWS_SM,AWS_PS,ASCP awsService;
    class K8s_Secrets,ESO,CSI_Driver k8sComponent;
    class Vault,SOPS userApp;
    class Default,Encrypted_Storage,Version_Control,Access_Control,Pod_Mount,Env_Vars,Init_Container default;
```

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

```mermaid
flowchart TD
    subgraph Compliance_Audit ["Compliance and Auditing"]
        subgraph Logging ["Logging and Monitoring"]
            CP_Logs[Control Plane Logs]
            Audit_Logs[Audit Logs]
            CloudTrail[AWS CloudTrail]
            CloudWatch[Amazon CloudWatch]
            FluentBit[Fluent Bit]
        end

        subgraph Compliance_Tools ["Compliance Tools"]
            Config[AWS Config]
            SecurityHub[AWS Security Hub]
            Inspector[Amazon Inspector]
            CIS_Benchmark["CIS Kubernetes
                Benchmark"]
        end

        subgraph Compliance_Standards ["Compliance Standards"]
            PCI_DSS[PCI DSS]
            HIPAA[HIPAA]
            GDPR[GDPR]
            SOC2[SOC 2]
            ISO27001[ISO 27001]
        end
    end

    subgraph Audit_Flow ["Audit Workflow"]
        Log_Collection[Log Collection]
        Log_Storage[Log Storage]
        Log_Analysis[Log Analysis]
        Alerting[Alerting]
        Reporting[Reporting]
    end

    CP_Logs --> Log_Collection
    Audit_Logs --> Log_Collection
    CloudTrail --> Log_Collection
    FluentBit --> Log_Collection

    Log_Collection --> CloudWatch
    CloudWatch --> Log_Storage

    Log_Storage --> Log_Analysis
    Log_Analysis --> SecurityHub

    SecurityHub --> Alerting
    SecurityHub --> Reporting

    Config --> CIS_Benchmark
    Inspector --> CIS_Benchmark

    CIS_Benchmark --> PCI_DSS
    CIS_Benchmark --> HIPAA
    CIS_Benchmark --> GDPR
    CIS_Benchmark --> SOC2
    CIS_Benchmark --> ISO27001

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class CloudTrail,CloudWatch,Config,SecurityHub,Inspector awsService;
    class CP_Logs,Audit_Logs k8sComponent;
    class FluentBit,CIS_Benchmark userApp;
    class PCI_DSS,HIPAA,GDPR,SOC2,ISO27001,Log_Collection,Log_Storage,Log_Analysis,Alerting,Reporting default;
```

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

```mermaid
flowchart TD
    subgraph Security_Monitoring ["Security Monitoring and Detection"]
        subgraph AWS_Services ["AWS Security Services"]
            GuardDuty[Amazon GuardDuty]
            SecurityHub[AWS Security Hub]
            Detective[Amazon Detective]
            CloudWatch[Amazon CloudWatch]
        end

        subgraph K8s_Tools ["Kubernetes Security Tools"]
            Falco[Falco]
            KubeAudit[kube-audit]
            TriageParty[Triage Party]
            Starboard[Starboard]
        end

        subgraph Detection_Types ["Detection Types"]
            Runtime[Runtime Security]
            Network[Network Security]
            Config[Configuration Security]
            Identity[Identity and Access Security]
        end
    end

    subgraph Threat_Detection ["Threat Detection Workflow"]
        Collection[Data Collection]
        Analysis[Data Analysis]
        Detection[Threat Detection]
        Response[Response]
        Remediation[Remediation]
    end

    GuardDuty --> Runtime
    GuardDuty --> Network
    GuardDuty --> Identity

    SecurityHub --> Config
    SecurityHub --> Identity

    Falco --> Runtime
    KubeAudit --> Config

    CloudWatch --> Collection
    GuardDuty --> Collection
    Falco --> Collection

    Collection --> Analysis
    Analysis --> Detection
    Detection --> Response
    Response --> Remediation

    Detection --> SecurityHub

    %% Class definitions
    classDef awsService fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef k8sComponent fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef dataStore fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Class application
    class GuardDuty,SecurityHub,Detective,CloudWatch awsService;
    class Falco,KubeAudit,TriageParty,Starboard k8sComponent;
    class Runtime,Network,Config,Identity,Collection,Analysis,Detection,Response,Remediation default;
```

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

```mermaid
flowchart TD
    subgraph VPC["Financial Services VPC"]
        subgraph PrivateSubnets["Private Subnets"]
            EKS[EKS Cluster]
            EKS --> AppPods[Application Pods]
            AppPods --> SecPods[Security Sidecars]
        end

        subgraph SecurityTools["Security Tools"]
            WAF[AWS WAF]
            GuardDuty[GuardDuty]
            SecurityHub[Security Hub]
            Config[AWS Config]
            CloudTrail[CloudTrail]
        end

        subgraph DataServices["Data Services"]
            RDS["(Amazon RDS
                Encrypted)"]
            S3["(S3 Bucket
                Encrypted)"]
            DynamoDB["(DynamoDB
                Encrypted)"]
        end
    end

    Internet((Internet)) --> WAF
    WAF --> ALB["Application
                Load Balancer"]
    ALB --> AppPods

    AppPods --> RDS
    AppPods --> S3
    AppPods --> DynamoDB

    SecurityTools --> |Monitoring| EKS

    KMS[AWS KMS] --> |Encryption Key Management| DataServices

    style VPC fill:#f9f9f9,stroke:#333,stroke-width:1px
    style PrivateSubnets fill:#e6f7ff,stroke:#0099cc,stroke-width:1px
    style SecurityTools fill:#ffe6e6,stroke:#cc0000,stroke-width:1px
    style DataServices fill:#e6ffe6,stroke:#009900,stroke-width:1px
```

## Conclusion

Amazon EKS security is implemented through a multi-layered defense strategy. You can securely operate your EKS cluster through strong authentication and authorization via IAM and RBAC, network security through network policies and security groups, workload security through Pod Security Standards and security context, and integration with various AWS security services.

In industries with strict regulations such as financial services, additional security controls and compliance requirements should be considered. It is important to maintain the security posture of your EKS environment through regular security assessments, vulnerability scanning, and continuous monitoring.

## References

- [Amazon EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/docs/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/overview/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [AWS Security Hub](https://aws.amazon.com/security-hub/)
- [Amazon GuardDuty](https://aws.amazon.com/guardduty/)

## Quiz

To test what you learned in this chapter, try the [topic quiz](../quizzes/eks/05-eks-security-quiz.md).
