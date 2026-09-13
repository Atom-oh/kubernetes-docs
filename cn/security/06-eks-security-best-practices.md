# EKS 安全最佳实践

> **审查基准**：当前 AWS 文档、Kubernetes 1.35 API schema、Terraform 1.15.7 / AWS provider 6.64.0。未执行实时集群部署。
> **最后更新**：September 13, 2026

本文档涵盖 Amazon EKS 环境的安全最佳实践。了解如何从 IAM 集成到网络安全和运行时保护，安全地运营 EKS 集群。

## 目录

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Pod 的 Security Groups](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [控制平面日志](#control-plane-logging)
6. [GuardDuty EKS Protection](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes Benchmark](#cis-kubernetes-benchmark)
9. [集群加密](#cluster-encryption)
10. [节点安全](#node-security)
11. [私有集群](#private-clusters)
12. [多租户模式](#multi-tenancy-patterns)

---

## IRSA (IAM Roles for Service Accounts) {#irsa-iam-roles-for-service-accounts}

### IRSA 概述

IRSA (IAM Roles for Service Accounts) 将 IAM roles 与 Kubernetes ServiceAccounts 关联，使 Pods 能够安全访问 AWS 服务。

Kubernetes API server 签发投影的 ServiceAccount token。SDK 使用它与 STS 交换 AssumeRoleWithWebIdentity；STS 验证与 IAM OIDC provider 及 role trust 条件关联的 issuer/JWKS，然后返回临时凭证。IAM OIDC provider 对象不是正在运行的 token 签发代理。


### IRSA 设置

以下操作示例未执行。请匹配实际的 Region、集群、bucket 所有者/路径和 policy ARN，并将应用程序 image 替换为经过审查的版本/digest。不要混用其他 Region 的 OIDC issuer 或猜测由 eksctl 生成的 role ARN。



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

### 使用 IRSA

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

### IRSA 信任策略

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

### IRSA 最佳实践

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

## EKS Pod Identity {#eks-pod-identity}

### Pod Identity 概述

EKS Pod Identity 是一种替代凭证交付机制。请根据实际的平台/SDK 支持、信任边界和运维要求，在它与 IRSA 之间进行选择；它不会淘汰 IRSA，也不会自动让每个 workload 更加安全。

受支持的 Pod SDK 使用本地 agent 路径；agent 根据 association 和 role 通过 EKS Auth 获取临时凭证。对于跨账户 roles 或 role chaining，请分别验证当前受支持的机制、信任和 session-tag 条件。


### Pod Identity 设置

EKS Auto Mode 包含该 agent。对于其他受支持的平台，请选择当前兼容的 addon 版本，并通过现有所有者进行管理。替换以下账户/集群/namespace/ServiceAccount 值，并使用预期的 namespace/ServiceAccount session-tag 条件限制 role trust。安装 addon 和 association 并不会验证 SDK 兼容性、凭证优先级或网络访问。



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

### 使用 Pod Identity

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

### IRSA 与 Pod Identity 对比

| 功能 | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **设置复杂度** | 需要 OIDC Provider | 简单（API 调用） |
| **信任策略** | 精确的 OIDC issuer、audience 和 subject | Service principal 加上受限条件 |
| **Role 复用** | 每个集群均需修改 | 可跨集群复用 |
| **审计日志** | CloudTrail（SA 级别） | CloudTrail（Pod 级别） |
| **Session Tags** | 不要假定与 EKS Pod Identity 有相同的 session-tag 行为 | 支持已记录的 session tags；审查禁用/chaining 行为 |
| **选择** | 支持的平台、OIDC trust 和运维模型 | 支持的平台、association 和 agent/SDK 模型 |

---

## Pod 的 Security Groups {#security-groups-for-pods}

### 概述

Pod 的 Security Groups 将 VPC Security Groups 直接应用于 Pods，提供网络层隔离。

### 前提条件

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

Pod 的 Security Groups 需要受支持的兼容 trunking 的 instance 和 CNI mode。当前文档排除了 Windows 和 EKS Auto Mode；并非所有 Nitro instance 都受支持。VPC Resource Controller policy 属于 cluster role。附加的多个 security groups 会合并允许规则；它们不会相交。启用前请审查 strict/standard mode、DNS、probes 和 load-balancer 行为。

### SecurityGroupPolicy 配置

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

### 使用 Terraform 配置 Security Group

识别实际的源 security groups 以及所需的 database、replication 和 monitoring ports，并牢记附加的 SG 规则会合并。SecurityGroupPolicy、源/目标 SG、VPC 和 Pod selectors 必须一致。旧声明包含未定义的 module/SG references 和不受限制的 egress；它不是一个完整的部署 module。

Security-group 返回流量是有状态的，但应用程序发起的新 DNS/database/external connections 有独立的 egress 要求。限制目标，并使用 CNI enforcing mode 和 NetworkPolicy 测试连通性。本次审计未创建 security groups/Pod ENIs，也未执行网络隔离测试。

---

## VPC Endpoints {#vpc-endpoints}

### 用于私有 EKS 的 VPC Endpoints

Kubernetes private API endpoint 和 AWS-service PrivateLink endpoints 不同。`eks` VPC endpoint 不会替代 kubectl 使用的 Kubernetes API 连接。仅选择实际 node、workload 和 operator 路径所需的服务，并一同验证 Region 支持、DNS、security groups、routes、endpoint policy 和 IAM。

| 用途 | 路径 |
|---|---|
| Kubernetes API | Cluster private API endpoint 和已连接的网络 |
| EKS management API | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| IRSA STS exchange | `com.amazonaws.<region>.sts`；在 SDK 中配置 regional STS |
| OIDC discovery/JWKS | 当前记录的 `com.amazonaws.<region>.oidc-eks`，与 STS 分离 |
| ECR images | `ecr.api`、`ecr.dkr` interfaces 加上 S3 image-layer 路径 |
| 其他服务 | 已验证的、实际使用的 EC2、Logs、ELB、Auto Scaling、SSM 和其他 APIs endpoints |

当前 EKS private-cluster 文档还列出了 Route 53 API 服务 `com.amazonaws.route53`。请区分 DNS resolution 与 Route 53 management API 调用，并验证 service/Region 支持。不要在每个 Region 中无条件创建旧版 `ec2messages` endpoints；请检查 SSM Agent 和 messaging 要求。

### Terraform VPC Endpoint 设置

[完整的 Terraform 示例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints)采用 `逻辑名称 → 精确服务名称` 映射。旧的 `split(...)[4]` 可能越界，或根据服务名称长度生成错误的 tag；现在 tags 使用 `each.key`。

提供现有 subnets、route tables、已批准的 client security groups 和经过审查的 S3 endpoint policy。仅允许来自指定 client groups 的 HTTPS。S3 policy 必须覆盖 ECR layer buckets 和其他所需 buckets；endpoint policy 本身不会授予 IAM 访问权限。Terraform 1.15.7/AWS provider 6.64.0 schema validation 已通过；未执行 plan/apply 或资源创建。

---

## 控制平面日志 {#control-plane-logging}

### EKS 控制平面日志类型

受支持的类型为 `api`、`audit`、`authenticator`、`controllerManager` 和 `scheduler`。Kubelet/container logs 有单独的收集路径。log group 是 `/aws/eks/<cluster-name>/cluster`；请根据运维 policy 配置 Region、retention、access、encryption、sensitive-data handling 和收集成本。

### 启用日志

请与现有集群的 IaC 所有者协调变更。以下命令面向自有集群，在本次审计期间未执行。更新是异步的：使用 `describe-update` 检查返回的 update ID，然后单独验证实际日志到达。启用日志无需声明新的 cluster resource 或更改 API endpoint exposure。

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### CloudWatch Logs Insights 查询

这些是**独立的 Logs Insights QL 查询**。请检查选定 log group 中的实际 fields/time range。第一个查询是探索性文本匹配，并非完整的 authentication-failure detector。本次审计未执行 managed query engine。

Authenticator 错误（探索性）

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

由选定 identity 发起的调用

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

Authorization 拒绝

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter responseStatus.code = 403
| sort @timestamp desc
| limit 100
```

Secret API 访问

```text
fields @timestamp, user.username, verb, objectRef.namespace, objectRef.name, responseStatus.code
| filter @logStream like /audit/
| filter objectRef.resource = "secrets"
| sort @timestamp desc
| limit 100
```

---

## GuardDuty EKS Protection {#guardduty-eks-protection}

### GuardDuty EKS Protection 概述

请区分 EKS audit-log analysis、Runtime Monitoring 和基础 GuardDuty data sources。EKS audit analysis 关注 Kubernetes API 活动，并不依赖于启用用户的 CloudWatch control-plane log export。Runtime Monitoring 需要 security agent 和实际 coverage。

当前 Runtime Monitoring 文档支持由 EC2 支持的 EKS 和 EKS Auto Mode，并排除 EKS Hybrid Nodes 和 EKS Fargate。ECS Fargate 支持不等于 EKS Fargate 支持。请确认 organization/delegated-administrator ownership、regional detector、platform、cost 和 agent-management owner。

### 启用 GuardDuty

以下是现有 detector 的**配置 payload 示例**；未将其应用于账户。`RUNTIME_MONITORING` 包括 EKS，因此与 `EKS_RUNTIME_MONITORING` 一起指定无效。请检查自有 detector，而不是总是创建 detector 并选择返回的第一个 ID。审查 automated agent-management resources/permissions 和已测量的 coverage。

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

### GuardDuty EKS Finding 类型

真实类型包括 tactic prefix。请使用 finding 的 `severity`、resource、account/Region、coverage 和官方说明，而非虚构的固定 severity table。

| 实际类型示例 | 范围 |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Kubernetes API 活动 |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | 异常 Kubernetes permission checks |
| `Execution:Runtime/ReverseShell` | agent 观测到的 runtime behavior |
| `CryptoCurrency:Runtime/BitcoinTool.B` | 与 runtime mining 相关的检测 |

### 自动化 Finding 响应

此 EventBridge pattern 路由 Kubernetes/Runtime 类型。旧的 `prefix: Kubernetes` 和 `prefix: Runtime` 不匹配真实的带 tactic prefix 的名称。已使用官方 AWS Event Ruler 2.2.0 library 检查六个匹配/不匹配的案例和旧失败情形。

该 pattern 没有 notification/isolation target。Runtime findings 可能涉及 EKS 之外的 resources：在路由到已批准的响应前，请检查实际 resource metadata。请单独配置 target roles/permissions、retries、DLQ 和 deduplication。创建 `boto3.client("eks")` 不会隔离 Pod；containment 需要经过设计的 CNI/host/cloud control 和授权的 Kubernetes operation。

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

## Amazon Inspector {#amazon-inspector}

### Inspector Container Image Scanning

ECR enhanced scanning 与 Amazon Inspector 集成，以检查受支持 images 中的 package vulnerabilities。运行中 image 的 usage context 与 runtime behavior detection 不同。相同的 image scan 不会检查任意 Kubernetes manifests、IAM policies 或实时网络流量。

Registry scanning 变更会影响账户/Region 和 repository filter scope；请确认所有权和预期范围。选择要部署的 digest，而非 `latest`。继续管理新的 CVEs、受支持 images、rescan eligibility 和 failures；通过初始 scan 不保证未来安全。

### Inspector 与 CI/CD 集成

[完整的 scan gate 和测试](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security)需要精确的 registry/repository/digest、completion timestamp 和显式 severity-count map。仅 continuous-scan `ACTIVE` 并不能证明初始结果已就绪。缺失结果、timeout、access denial、failure 和 unknown status 绝不会变成零 findings。

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` 必须是在 build/push 后由 registry 确认的 `sha256:...` 值。替换示例 account/repository 并安装 boto3。十二项 regression tests 使用真实的 boto3/botocore Stubber 和 fake time，不发出 AWS requests，也不实际等待。

GitHub Actions 集成需要已批准的 OIDC-trusted role ARN、`permissions: id-token: write`、least-privilege reads、来自 ECR login outputs 的 registry，以及已构建 digest 的传递。未定义的 `$ECR_REGISTRY`、没有 role 的 credential configuration，以及固定 60 秒的 sleep 并非完整 workflow。对于 multi-architecture indexes，请定义已部署 child digests 的 scanning policy。单独管理 exceptions、expiry/ownership 和 result-freshness requirements。

Enhanced finding events 使用 `aws.inspector2` / `Inspector2 Finding`，不同于 Basic ECR image-scan events。[经过验证的 alerting CloudFormation 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)具有独立的 key、permission 和 receiver 前提条件。

---

## CIS Kubernetes Benchmark {#cis-kubernetes-benchmark}

### 运行 kube-bench

经审查的上游 release 是 kube-bench **0.16.0**。它包含 `eks-1.5.0`、`eks-1.7.0` 和 `eks-1.8.0`，但不包含旧示例的 `eks-1.4.0` directory。请选择组织要求且兼容 cluster/node OS/tool support 的 CIS EKS edition；最高编号并不自动代表正确选择。上游 sample job 本身仍使用 `latest` 和1.5.0，因此请审查并固定 image digest、profile、host mounts 和 permissions，而非盲目应用它。

某些检查需要 host PID/filesystem access，且与 Restricted application namespaces 冲突。请使用已批准的 scanner operating path，并记录已检查 nodes、遗漏项和 warnings。本次审计未在实际 nodes 上执行 kube-bench。

### CIS Benchmark 关键部分

检查所选 CIS EKS profile 中实际的 controlplane、node、policies 和 managedservices checks。不要假定客户可以访问 managed control-plane files。Node settings、RBAC、network policy 和 audit checks 可能需要 automatic/manual/not-applicable classifications。工具通过率不是安全认证或全面的 compromise assessment。

### 自动化合规检查

一个 Job 可能仅检查调度它的 node。为 node groups、OS、architecture 和 configuration differences 设计 coverage，并使用 cluster/node/image/profile/time 标记结果。Scheduled runs 需要 host mounts、ServiceAccount、所需的 read permissions、concurrency control、completion/failure handling 和 result retention。

旧 CronJob 缺少 host mounts，并假设 kube-bench image 包含 AWS CLI。如果必须上传 results，请使用经过审查的 uploader 或具有受限 workload identity 的 log pipeline。成功上传不得掩盖失败的 scan。

---

## 集群加密 {#cluster-encryption}

### EKS Secrets Encryption (KMS)

EKS **1.28+ 默认使用 AWS-owned KMS key 对所有 Kubernetes API data 进行 envelope encryption**。针对特定要求可选择 customer-managed key；没有此类 key 并不意味着当前 EKS Secrets 未加密存储。

对于 customer-managed keys，请一同审查 cluster-role/KMS grants、key policy、account/Region、key availability 和 change procedures。禁用/删除 key 可能影响 availability 和 recovery；不要将七天 deletion window 复制为通用的生产标准。`Resource: "*"` 具有 key-policy-specific 含义，但不得将其重新用作不受限制的 IAM access。验证实际 key owner、administrative/use roles、conditions 和 IAM delegation。

静态加密不会阻止被授权的 API reads 或遭入侵应用程序对某个 value 的使用。Credential rotation、Secret delivery 和 reload 是独立的 [secrets-management](./05-secrets-management.md) 操作。本章未创建 KMS key/cluster，也未更改现有 key association。

---

## 节点安全 {#node-security}

### Bottlerocket OS

Bottlerocket 是 container-host OS 选项，并不保证每个 workload 都安全。请验证 cluster Kubernetes version、CPU architecture、managed-node-group/Auto Mode model、CNI、storage 和 agents 的受支持组合。遵循 managed-node-group bootstrap merge rules，而非盲目覆盖 cluster/API/CA settings。

运维 updates/reboots/replacements、control/admin-container access、SSM permissions、image provenance 和 recovery。旧示例的 network-buffer sysctls 并非安全加固的证据。AMI type 和 instance architecture 必须一致；本次审计未执行 node group 或 OS。

### 节点安全加固

将有限的 node role 与 workload-specific IRSA/Pod Identity roles 分开。评估 IMDSv2 和 metadata-access controls，包括 hostNetwork、privileged Pods 和 node compromise。仅启用 IRSA 并不会自动阻止访问 node role。

使用适当的 non-root identities、禁止 privilege escalation、移除 capabilities、使用 seccomp 和只读 root filesystem，并显式指定 writable volumes，同时测试实际应用程序。Labels/selectors/tolerations 是调度输入，而非 OS attestation 或 authorization。不要将用户设置的 label（如 `node.kubernetes.io/os: bottlerocket`）视为信任边界；审查 administrator-controlled labels 以及 NodeRestriction 等实际 protections，以实现安全 placement。

---

## 私有集群 {#private-clusters}

### 完全私有的 EKS 配置

私有 Kubernetes API 需要来自 VPC 或已连接 management network 的 DNS、routes 和 security groups，以及 IAM authentication 和 Kubernetes authorization。没有 public-internet reachability 并不会授权每个已连接用户。

在更改 API exposure 前，请从当前 operators、CI 和 recovery paths 测试 private access。通过现有 IaC owner 管理 `endpoint_private_access`/`endpoint_public_access`，而不是无意中声明新 cluster。单独设计 worker bootstrap 以及所需 AWS API/image/package access。无互联网运行和 private API exposure 是不同的要求。

### Bastion 或 VPN 访问

使用 VPN、Direct Connect、适当连接的 network 或受限的 management host。仅有 Client VPN subnet association 并不足够：请一同配置 server/client authentication、non-overlapping client CIDR、authorization rules、routes/return routes、DNS、security groups、connection logging 和 IAM/Kubernetes permissions。

Bastion 会增加自身的 access、patching 和 audit responsibilities。不要默认使用宽泛的 SSH ingress 或不受限制的 cluster administration。本章未部署 VPN、bastion 或 certificates。

---

## 多租户模式 {#multi-tenancy-patterns}

### 基于 Namespace 的多租户

Namespaces 是 shared cluster 中的 administrative scope，而不是相互敌对 tenants 之间的完整边界。结合 PSS、RBAC、quota、NetworkPolicy、storage、workload identity 和 node/administrator boundaries。该示例使用 Kubernetes1.35 policy baseline；请验证与实际 cluster 的兼容性。

同一 namespace 的 peers 被允许，而 DNS 在一个 peer 中使用 kube-system namespace **和** kube-dns Pod selector。UDP 和 TCP53 均被包含。请分别验证实际 DNS labels、NodeLocal DNS、CNI enforcement、其他 additive policies 以及 hostNetwork/node traffic。未执行实时 connectivity test。

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

### RBAC 多租户

示例 workload admin 无法直接修改 Namespace labels、RoleBindings、NetworkPolicy 或 Secret API permissions。但是，创建 Pods/Deployments 可以间接使用 namespace Secrets、ServiceAccounts 和 volumes。排除 Secret get 并不能证明无法访问 secret。当需要更强隔离时，请考虑单独的 clusters/accounts。

对于 EKS user access，请使用 namespace-scoped access policies 或 Kubernetes groups/RBAC 评估当前 access entries。aws-auth ConfigMap 是旧版 compatibility path，并非唯一的 integration mechanism。Authentication-mode changes 有不可逆 transition constraints；迁移前请验证 administrator/node mappings 和 recovery paths。EKS access policies 和 Kubernetes RBAC 可以独立允许访问，因此一者中缺少 permission 并不会拒绝另一者授予的 allowance。不要将 system:masters 授予普通 developers 作为默认示例。

---

## 总结

关键 EKS 安全最佳实践：

1. **IAM 集成**：使用 IRSA 或 Pod Identity 访问 AWS 服务
2. **网络安全**：Pod 的 Security Groups、VPC endpoints
3. **日志记录和监控**：控制平面日志、GuardDuty
4. **Image 安全**：Amazon Inspector、ECR scanning
5. **合规性**：CIS Benchmark、kube-bench
6. **加密**：使用 KMS 进行 Secrets encryption
7. **节点安全**：Bottlerocket OS、最小权限
8. **多租户**：Namespace isolation、RBAC、ResourceQuota

---

## 参考资料

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
