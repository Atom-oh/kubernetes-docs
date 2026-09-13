# EKS Security Best Practices

> **Review baseline**: Current AWS documentation, Kubernetes 1.35 API schemas, Terraform 1.15.7 / AWS provider 6.64.0. No live cluster deployment was performed.
> **Last Updated**: September 13, 2026

This document covers security best practices for Amazon EKS environments. Learn how to securely operate EKS clusters from IAM integration to network security and runtime protection.

## Table of Contents

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Security Groups for Pods](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [Control Plane Logging](#control-plane-logging)
6. [GuardDuty EKS Protection](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [Cluster Encryption](#cluster-encryption)
10. [Node Security](#node-security)
11. [Private Clusters](#private-clusters)
12. [Multi-tenancy Patterns](#multi-tenancy-patterns)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA Overview

IRSA (IAM Roles for Service Accounts) associates IAM roles with Kubernetes ServiceAccounts, enabling Pods to securely access AWS services.

The Kubernetes API server issues the projected ServiceAccount token. The SDK exchanges it with STS AssumeRoleWithWebIdentity; STS validates the issuer/JWKS associated with the IAM OIDC provider and role trust conditions, then returns temporary credentials. The IAM OIDC provider object is not a running token-issuing proxy.


### IRSA Setup

The following operator example was not executed. Match the actual Region, cluster, bucket owner/path and policy ARN, and replace the application image with a reviewed version/digest. Do not mix an OIDC issuer from another Region or a guessed eksctl-generated role ARN.



```bash
# 1. Create OIDC Provider (once per cluster)
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# 2. Create IAM policy
cat <<'EOF' > s3-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        },
        "StringLike": {
          "s3:prefix": [
            "app-data",
            "app-data/*"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::replace-with-owned-bucket/app-data/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceAccount": "123456789012"
        }
      }
    }
  ]
}
EOF

aws iam create-policy \
    --policy-name S3ReadPolicy \
    --policy-document file://s3-policy.json

# 3. Create IAM ServiceAccount
eksctl create iamserviceaccount \
    --name s3-reader-sa \
    --namespace production \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy \
    --approve
```

### Using IRSA

```yaml
# Reuse the ServiceAccount created by eksctl; do not guess its generated role ARN.
# Use ServiceAccount in Pod
apiVersion: v1
kind: Pod
metadata:
  name: s3-reader
  namespace: production
spec:
  serviceAccountName: s3-reader-sa
  containers:
  - name: app
    image: public.ecr.aws/aws-cli/aws-cli:replace-with-reviewed-version
    command: ["aws", "s3", "ls", "s3://replace-with-owned-bucket/app-data/"]
    # AWS SDK automatically uses IRSA token
```

### IRSA Trust Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:sub": "system:serviceaccount:production:s3-reader-sa",
                    "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539D4633E53DE1B71EXAMPLE:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

### IRSA Best Practices

```yaml
# 1. Principle of least privilege
# Grant only minimum required permissions to each ServiceAccount

# 2. Separate ServiceAccounts per namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dynamodb-reader
  namespace: orders-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/orders-dynamodb-role
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-uploader
  namespace: media-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/media-s3-role
```

---

## EKS Pod Identity

### Pod Identity Overview

EKS Pod Identity is an alternative credential-delivery mechanism. Choose between it and IRSA using actual platform/SDK support, trust boundaries and operating requirements; it does not retire IRSA or automatically make every workload more secure.

A supported Pod SDK uses the local agent path; the agent obtains temporary credentials through EKS Auth according to the association and role. For cross-account roles or role chaining, verify the current supported mechanism, trust and session-tag conditions separately.


### Pod Identity Setup

EKS Auto Mode includes the agent. For other supported platforms, select a currently compatible addon version and manage it through the existing owner. Replace the account/cluster/namespace/ServiceAccount values below and constrain role trust with the intended namespace/ServiceAccount session-tag conditions. Installing the addon and association does not validate SDK compatibility, credential precedence or network access.



```bash
# 1. Install Pod Identity Agent addon
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent

# 2. Create IAM role (with Pod Identity trust policy)
cat <<'EOF' > trust-policy.json
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
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/kubernetes-namespace": "production",
          "aws:RequestTag/kubernetes-service-account": "my-app-sa"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
    --role-name my-pod-role \
    --assume-role-policy-document file://trust-policy.json

# 3. Attach policy
aws iam attach-role-policy \
    --role-name my-pod-role \
    --policy-arn arn:aws:iam::123456789012:policy/S3ReadPolicy

# 4. Create Pod Identity Association
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/my-pod-role
```

### Using Pod Identity

```yaml
# ServiceAccount (no annotation needed)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
---
# Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
    # AWS SDK automatically uses Pod Identity
```

### IRSA vs Pod Identity Comparison

| Feature | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **Setup Complexity** | OIDC Provider required | Simple (API call) |
| **Trust Policy** | Exact OIDC issuer, audience and subject | Service principal plus constrained conditions |
| **Role Reuse** | Per-cluster modification needed | Reuse across clusters |
| **Audit Logging** | CloudTrail (SA level) | CloudTrail (Pod level) |
| **Session Tags** | Do not assume the same EKS Pod Identity session-tag behavior | Supports documented session tags; review disabling/chaining behavior |
| **Selection** | Supported platform, OIDC trust and operating model | Supported platform, association and agent/SDK model |

---

## Security Groups for Pods

### Overview

Security Groups for Pods applies VPC Security Groups directly to Pods, providing network-level isolation.

### Prerequisites

```bash
# Inspect the installed CNI and verify current platform/version requirements
kubectl describe daemonset aws-node -n kube-system | grep Image

# Enable Security Groups for Pods
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true

# Attach to the EKS CLUSTER role, after resolving its actual name
aws iam attach-role-policy \
    --role-name "$EKS_CLUSTER_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Security Groups for Pods requires a supported trunking-compatible instance and CNI mode. Current documentation excludes Windows and EKS Auto Mode; not every Nitro instance is supported. The VPC Resource Controller policy belongs to the cluster role. Multiple attached security groups combine allowed rules; they do not intersect them. Review strict/standard mode, DNS, probes and load-balancer behavior before enabling.

### SecurityGroupPolicy Configuration

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  # Target Pod selection
  podSelector:
    matchLabels:
      app: database
  # Security Groups to apply
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0  # Database SG
      - sg-0987654321fedcba0  # Common monitoring SG
```

### Security Group Configuration with Terraform

Identify actual source security groups and required database, replication and monitoring ports, remembering that attached SG rules combine. SecurityGroupPolicy, source/target SGs, VPC and Pod selectors must agree. The old declaration contained undefined module/SG references and unrestricted egress; it was not a complete deployment module.

Security-group return traffic is stateful, but new DNS/database/external connections initiated by an application have separate egress requirements. Limit destinations and test connectivity with the CNI enforcing mode and NetworkPolicy. This audit did not create security groups/Pod ENIs or execute network isolation tests.

---

## VPC Endpoints

### VPC Endpoints for Private EKS

The Kubernetes private API endpoint and AWS-service PrivateLink endpoints are different. An `eks` VPC endpoint does not replace the Kubernetes API connection used by kubectl. Select only services required by actual node, workload and operator paths, and verify Region support, DNS, security groups, routes, endpoint policy and IAM together.

| Purpose | Path |
|---|---|
| Kubernetes API | Cluster private API endpoint and connected network |
| EKS management API | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| IRSA STS exchange | `com.amazonaws.<region>.sts`; configure regional STS in the SDK |
| OIDC discovery/JWKS | Current documented `com.amazonaws.<region>.oidc-eks`, separate from STS |
| ECR images | `ecr.api`, `ecr.dkr` interfaces plus the S3 image-layer path |
| Additional services | Verified endpoints for actually used EC2, Logs, ELB, Auto Scaling, SSM and other APIs |

Current EKS private-cluster documentation also lists the Route 53 API service `com.amazonaws.route53`. Distinguish DNS resolution from Route 53 management API calls and verify service/Region support. Do not unconditionally create legacy `ec2messages` endpoints in every Region; check the SSM Agent and messaging requirements.

### Terraform VPC Endpoint Setup

The [complete Terraform example](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints) takes a `logical name → exact service name` map. The old `split(...)[4]` could be out of range or produce the wrong tag depending on service-name length; tags now use `each.key`.

Supply existing subnets, route tables, approved client security groups and a reviewed S3 endpoint policy. HTTPS is allowed only from the named client groups. The S3 policy must cover ECR layer buckets and other needed buckets; an endpoint policy does not itself grant IAM access. Terraform 1.15.7/AWS provider 6.64.0 schema validation passed; no plan/apply or resource creation was performed.

---

## Control Plane Logging

### EKS Control Plane Log Types

Supported types are `api`, `audit`, `authenticator`, `controllerManager` and `scheduler`. Kubelet/container logs have separate collection paths. The log group is `/aws/eks/<cluster-name>/cluster`; configure Region, retention, access, encryption, sensitive-data handling and collection cost according to operating policy.

### Enabling Logging

Coordinate changes with the existing cluster's IaC owner. The following targets an owned cluster and was not executed during this audit. Updates are asynchronous: inspect the returned update ID with `describe-update`, then verify actual log arrival separately. Enabling logging does not require declaring a new cluster resource or changing API endpoint exposure.

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### CloudWatch Logs Insights Queries

These are **separate Logs Insights QL queries**. Inspect the actual fields/time range in the selected log group. The first query is exploratory text matching, not a complete authentication-failure detector. No managed query engine was executed during this audit.

Authenticator errors (exploratory)

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

Calls by a chosen identity

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

Authorization denials

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

Secret API access

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS Protection

### GuardDuty EKS Protection Overview

Separate EKS audit-log analysis, Runtime Monitoring and foundational GuardDuty data sources. EKS audit analysis concerns Kubernetes API activity and does not depend on enabling the user's CloudWatch control-plane log export. Runtime Monitoring requires the security agent and actual coverage.

Current Runtime Monitoring documentation supports EC2-backed EKS and EKS Auto Mode, and excludes EKS Hybrid Nodes and EKS Fargate. ECS Fargate support is not EKS Fargate support. Confirm organization/delegated-administrator ownership, the regional detector, platform, cost and agent-management owner.

### Enabling GuardDuty

The following is a **configuration payload example** for an existing detector; it was not applied to an account. `RUNTIME_MONITORING` includes EKS, so specifying it together with `EKS_RUNTIME_MONITORING` is invalid. Inspect the owned detector instead of always creating a detector and selecting the first returned ID. Review automated agent-management resources/permissions and measured coverage.

```json
[
  {"Name": "EKS_AUDIT_LOGS", "Status": "ENABLED"},
  {
    "Name": "RUNTIME_MONITORING",
    "Status": "ENABLED",
    "AdditionalConfiguration": [
      {"Name": "EKS_ADDON_MANAGEMENT", "Status": "ENABLED"}
    ]
  }
]
```

### GuardDuty EKS Finding Types

Real types include a tactic prefix. Use the finding's `severity`, resource, account/Region, coverage and official explanation instead of an invented fixed severity table.

| Actual type example | Scope |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Kubernetes API activity |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | Anomalous Kubernetes permission checks |
| `Execution:Runtime/ReverseShell` | Agent-observed runtime behavior |
| `CryptoCurrency:Runtime/BitcoinTool.B` | Runtime mining-related detection |

### Automated Finding Response

This EventBridge pattern routes Kubernetes/Runtime types. The old `prefix: Kubernetes` and `prefix: Runtime` did not match real tactic-prefixed names. Six matching/nonmatching cases and the old failure were checked with the official AWS Event Ruler 2.2.0 library.

The pattern has no notification/isolation target. Runtime findings can concern resources beyond EKS: inspect actual resource metadata before routing to an approved response. Configure target roles/permissions, retries, DLQ and deduplication separately. Creating `boto3.client("eks")` does not isolate a Pod; containment requires a designed CNI/host/cloud control and authorized Kubernetes operation.

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": [
      {"wildcard": "*:Kubernetes/*"},
      {"wildcard": "*:Runtime/*"}
    ]
  }
}
```

---

## Amazon Inspector

### Inspector Container Image Scanning

ECR enhanced scanning integrates with Amazon Inspector to inspect package vulnerabilities in supported images. Running-image usage context differs from runtime behavior detection. The same image scan does not inspect arbitrary Kubernetes manifests, IAM policies or live network traffic.

Registry scanning changes affect the account/Region and repository filter scope; confirm ownership and intended scope. Select the digest to be deployed instead of `latest`. Continue managing new CVEs, supported images, rescan eligibility and failures; passing an initial scan does not guarantee future safety.

### Inspector and CI/CD Integration

The [complete scan gate and tests](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security) require the exact registry/repository/digest, a completion timestamp and an explicit severity-count map. Continuous-scan `ACTIVE` alone does not prove the initial result is ready. Missing results, timeout, access denial, failure and unknown status never become zero findings.

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` must be the registry-confirmed `sha256:...` value after build/push. Replace the example account/repository and install boto3. Twelve regression tests use real boto3/botocore Stubber and fake time, without AWS requests or actual waiting.

A GitHub Actions integration needs an approved OIDC-trusted role ARN, `permissions: id-token: write`, least-privilege reads, the registry from ECR login outputs, and propagation of the built digest. An undefined `$ECR_REGISTRY`, credential configuration without a role, and a fixed60-second sleep are not a complete workflow. For multi-architecture indexes, define scanning policy for the deployed child digests. Manage exceptions, expiry/ownership and result-freshness requirements separately.

Enhanced finding events use `aws.inspector2` / `Inspector2 Finding`, distinct from Basic ECR image-scan events. The [validated alerting CloudFormation example](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml) has separate key, permission and receiver prerequisites.

---

## CIS Kubernetes Benchmark

### Running kube-bench

The reviewed upstream release is kube-bench **0.16.0**. It includes `eks-1.5.0`, `eks-1.7.0` and `eks-1.8.0`, but not the old example's `eks-1.4.0` directory. Select the CIS EKS edition required by your organization and compatible cluster/node OS/tool support; the highest number is not automatically the right choice. The upstream sample job itself still uses `latest` and1.5.0, so review and pin image digest, profile, host mounts and permissions instead of applying it blindly.

Some checks require host PID/filesystem access and conflict with Restricted application namespaces. Use an approved scanner operating path and record inspected nodes, omissions and warnings. This audit did not execute kube-bench on actual nodes.

### CIS Benchmark Key Sections

Inspect the actual controlplane, node, policies and managedservices checks in the chosen CIS EKS profile. Do not assume customer access to managed control-plane files. Node settings, RBAC, network policy and audit checks can require automatic/manual/not-applicable classifications. A tool pass rate is not a security certification or exhaustive compromise assessment.

### Automated Compliance Checks

One Job may inspect only the node on which it is scheduled. Design coverage for node groups, OS, architecture and configuration differences, and label results with cluster/node/image/profile/time. Scheduled runs need host mounts, a ServiceAccount, required read permissions, concurrency control, completion/failure handling and result retention.

The old CronJob lacked host mounts and assumed the kube-bench image contained AWS CLI. If results must be uploaded, use a reviewed uploader or log pipeline with constrained workload identity. A successful upload must not hide a failed scan.

---

## Cluster Encryption

### EKS Secrets Encryption (KMS)

EKS **1.28+ defaults to envelope encryption of all Kubernetes API data using an AWS-owned KMS key**. Choose a customer-managed key for specific requirements; absence of such a key does not mean current EKS Secrets are stored unencrypted.

For customer-managed keys, review cluster-role/KMS grants, key policy, account/Region, key availability and change procedures together. Disabling/deleting a key can affect availability and recovery; do not copy a seven-day deletion window as a universal production standard. `Resource: "*"` has a key-policy-specific meaning, but must not be repurposed as unrestricted IAM access. Verify the actual key owner, administrative/use roles, conditions and IAM delegation.

Encryption at rest does not stop authorized API reads or a compromised application's use of a value. Credential rotation, Secret delivery and reload are separate [secrets-management](./05-secrets-management.md) operations. This chapter did not create a KMS key/cluster or change an existing key association.

---

## Node Security

### Bottlerocket OS

Bottlerocket is a container-host OS option, not a guarantee that every workload is secure. Verify the supported combination of cluster Kubernetes version, CPU architecture, managed-node-group/Auto Mode model, CNI, storage and agents. Follow managed-node-group bootstrap merge rules instead of blindly overwriting cluster/API/CA settings.

Operate updates/reboots/replacements, control/admin-container access, SSM permissions, image provenance and recovery. The old example's network-buffer sysctls were not evidence of security hardening. AMI type and instance architecture must agree; no node group or OS was executed by this audit.

### Node Security Hardening

Separate a limited node role from workload-specific IRSA/Pod Identity roles. Evaluate IMDSv2 and metadata-access controls, including hostNetwork, privileged Pods and node compromise. Merely enabling IRSA does not automatically block access to the node role.

Use suitable non-root identities, no privilege escalation, dropped capabilities, seccomp and a read-only root filesystem with explicit writable volumes, and test the actual application. Labels/selectors/tolerations are scheduling inputs, not OS attestation or authorization. Do not treat a user-set label such as `node.kubernetes.io/os: bottlerocket` as a trust boundary; review administrator-controlled labels and actual protections such as NodeRestriction for security placement.

---

## Private Clusters

### Fully Private EKS Configuration

A private Kubernetes API requires DNS, routes and security groups from the VPC or connected management network, plus IAM authentication and Kubernetes authorization. Absence of public-internet reachability does not authorize every connected user.

Before changing API exposure, test private access from current operators, CI and recovery paths. Manage `endpoint_private_access`/`endpoint_public_access` through the existing IaC owner rather than inadvertently declaring a new cluster. Design worker bootstrap and required AWS API/image/package access separately. No-internet operation and private API exposure are different requirements.

### Bastion or VPN Access

Use VPN, Direct Connect, an appropriately connected network or a restricted management host. A Client VPN subnet association alone is insufficient: configure server/client authentication, non-overlapping client CIDR, authorization rules, routes/return routes, DNS, security groups, connection logging and IAM/Kubernetes permissions together.

A bastion adds its own access, patching and audit responsibilities. Do not default to broad SSH ingress or unrestricted cluster administration. This chapter did not deploy a VPN, bastion or certificates.

---

## Multi-tenancy Patterns

### Namespace-based Multi-tenancy

Namespaces are an administrative scope in a shared cluster, not a complete boundary between mutually hostile tenants. Combine PSS, RBAC, quota, NetworkPolicy, storage, workload identity and node/administrator boundaries. The example uses a Kubernetes1.35 policy baseline; verify compatibility with the actual cluster.

Same-namespace peers are permitted, while DNS uses the kube-system namespace **and** kube-dns Pod selector in one peer. Both UDP and TCP53 are included. Verify actual DNS labels, NodeLocal DNS, CNI enforcement, other additive policies and hostNetwork/node traffic separately. No live connectivity test was performed.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-a-limits
  namespace: tenant-a
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 512Mi
      defaultRequest:
        cpu: 100m
        memory: 128Mi
      min:
        cpu: 50m
        memory: 64Mi
      max:
        cpu: "2"
        memory: 4Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-a-isolation
  namespace: tenant-a
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector: {}
  egress:
    - to:
        - podSelector: {}
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
---
# Workload administration is sensitive, even when namespace-scoped.
# The group cannot change Namespace labels, RoleBindings or this NetworkPolicy.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workload-admin
  namespace: tenant-a
rules:
  - apiGroups: [""]
    resources: [pods, services, configmaps]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [apps]
    resources: [deployments, statefulsets]
    verbs: [get, list, watch, create, update, patch, delete]
  - apiGroups: [""]
    resources: [pods/log]
    verbs: [get]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-workload-admins
  namespace: tenant-a
subjects:
  - kind: Group
    name: tenant-a-workload-admins
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workload-admin
  apiGroup: rbac.authorization.k8s.io
```

### RBAC Multi-tenancy

The example workload admin cannot directly modify Namespace labels, RoleBindings, NetworkPolicy or Secret API permissions. However, creating Pods/Deployments can indirectly use namespace Secrets, ServiceAccounts and volumes. Excluding Secret get does not prove inability to access a secret. Consider separate clusters/accounts when stronger isolation is required.

For EKS user access, evaluate current access entries with namespace-scoped access policies or Kubernetes groups/RBAC. The aws-auth ConfigMap is a legacy compatibility path, not the only integration mechanism. Authentication-mode changes have irreversible transition constraints; validate administrator/node mappings and recovery paths before migration. EKS access policies and Kubernetes RBAC can independently allow access, so absence of permission in one does not deny an allowance from the other. Do not grant ordinary developers system:masters as a default example.

---

## Summary

Key EKS security best practices:

1. **IAM Integration**: Access AWS services with IRSA or Pod Identity
2. **Network Security**: Security Groups for Pods, VPC endpoints
3. **Logging and Monitoring**: Control plane logs, GuardDuty
4. **Image Security**: Amazon Inspector, ECR scanning
5. **Compliance**: CIS Benchmark, kube-bench
6. **Encryption**: Secrets encryption with KMS
7. **Node Security**: Bottlerocket OS, least privilege
8. **Multi-tenancy**: Namespace isolation, RBAC, ResourceQuota

---

## References

- [EKS Security Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/security.html)
- [Amazon EKS User Guide - Security](https://docs.aws.amazon.com/eks/latest/userguide/security.html)
- [AWS Security Blog - EKS](https://aws.amazon.com/blogs/security/tag/amazon-eks/)
- [CIS Amazon EKS Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

- [security-groups-for-pods](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [sgpp](https://docs.aws.amazon.com/eks/latest/best-practices/sgpp.html)
- [private-clusters](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)
- [configure-sts-endpoint](https://docs.aws.amazon.com/eks/latest/userguide/configure-sts-endpoint.html)
- [how-runtime-monitoring-works-eks](https://docs.aws.amazon.com/guardduty/latest/ug/how-runtime-monitoring-works-eks.html)
- [kubernetes-protection](https://docs.aws.amazon.com/guardduty/latest/ug/kubernetes-protection.html)
- [API_DescribeImageScanFindings](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_DescribeImageScanFindings.html)
- [image-scanning-enhanced](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning-enhanced.html)
- [eventbridge-integration](https://docs.aws.amazon.com/inspector/latest/user/eventbridge-integration.html)
- [access-entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [guardduty_finding-types-kubernetes](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-kubernetes.html)
- [findings-runtime-monitoring](https://docs.aws.amazon.com/guardduty/latest/ug/findings-runtime-monitoring.html)
- [API_UpdateDetector](https://docs.aws.amazon.com/guardduty/latest/APIReference/API_UpdateDetector.html)
- [guardduty_findings_eventbridge](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_eventbridge.html)
