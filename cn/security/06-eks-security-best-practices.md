# EKS 安全最佳实践

> **审查基线**：当前 AWS 文档、Kubernetes 1.35 API 架构、Terraform 1.15.7 / AWS provider 6.64.0。未执行实时集群部署。
> **最后更新**：October 15, 2026

本文档涵盖 Amazon EKS 环境的安全最佳实践。了解如何从 IAM 集成到网络安全和运行时保护，安全地运营 EKS 集群。

## 目录

1. [IRSA (IAM Roles for Service Accounts)](#irsa-iam-roles-for-service-accounts)
2. [EKS Pod Identity](#eks-pod-identity)
3. [Pod 的 Security Groups](#security-groups-for-pods)
4. [VPC Endpoints](#vpc-endpoints)
5. [控制平面日志记录](#control-plane-logging)
6. [GuardDuty EKS 保护](#guardduty-eks-protection)
7. [Amazon Inspector](#amazon-inspector)
8. [CIS Kubernetes 基准](#cis-kubernetes-benchmark)
9. [集群加密](#cluster-encryption)
10. [节点安全](#node-security)
11. [私有集群](#private-clusters)
12. [多租户模式](#multi-tenancy-patterns)
13. [边界安全和检查路径](#perimeter-security-and-inspection-paths)

---

## IRSA (IAM Roles for Service Accounts)

### IRSA 概述

IRSA (IAM Roles for Service Accounts) 将 IAM 角色与 Kubernetes ServiceAccount 关联，使 Pod 能够安全地访问 AWS 服务。

Kubernetes API server 签发投影的 ServiceAccount token。SDK 使用 STS AssumeRoleWithWebIdentity 交换该 token；STS 验证与 IAM OIDC provider 和角色信任条件关联的 issuer/JWKS，然后返回临时凭证。IAM OIDC provider 对象并非一个正在运行的 token 签发代理。


### IRSA 设置

以下操作员示例未执行。请匹配实际的 Region、集群、bucket 所有者/路径和 policy ARN，并将应用程序镜像替换为经审查的版本/digest。请勿混用来自其他 Region 的 OIDC issuer 或猜测 eksctl 生成的角色 ARN。



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

## EKS Pod Identity

### Pod Identity 概述

EKS Pod Identity 是一种替代凭证交付机制。请根据实际的平台/SDK 支持、信任边界和运营要求在它与 IRSA 之间做出选择；它并不会淘汰 IRSA，也不会自动让每个工作负载更安全。

受支持的 Pod SDK 使用本地 agent 路径；agent 根据关联和角色通过 EKS Auth 获取临时凭证。对于跨账户角色或角色链，请分别验证当前受支持的机制、信任和 session-tag 条件。


### Pod Identity 设置

EKS Auto Mode 包含该 agent。对于其他受支持的平台，请选择当前兼容的 addon 版本，并通过现有所有者进行管理。替换以下账户/集群/namespace/ServiceAccount 值，并使用预期的 namespace/ServiceAccount session-tag 条件约束角色信任。安装 addon 和关联并不能验证 SDK 兼容性、凭证优先级或网络访问。



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
| **信任策略** | 精确的 OIDC issuer、audience 和 subject | Service principal 加上受约束的条件 |
| **角色复用** | 需要按集群修改 | 跨集群复用 |
| **审计日志记录** | CloudTrail（SA 级别） | CloudTrail（Pod 级别） |
| **Session Tags** | 不要假定具有与 EKS Pod Identity 相同的 session-tag 行为 | 支持已记录的 session tags；审查禁用/链式行为 |
| **选择** | 受支持的平台、OIDC 信任和运营模型 | 受支持的平台、关联和 agent/SDK 模型 |

---

## Pod 的 Security Groups {#security-groups-for-pods}

### 概述

Pod 的 Security Groups 将 VPC Security Groups 直接应用于 Pod，提供网络层隔离。

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

Pod 的 Security Groups 需要受支持的、兼容 trunking 的实例和 CNI 模式。当前文档不包括 Windows 和 EKS Auto Mode；并非所有 Nitro 实例都受支持。VPC Resource Controller policy 属于集群角色。多个附加的 security groups 会合并允许规则；它们不会取交集。启用前请审查 strict/standard 模式、DNS、probes 和 load-balancer 行为。

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

确定实际的源 security groups 以及所需的数据库、复制和监控端口，并牢记所附加的 SG 规则会合并。SecurityGroupPolicy、源/目标 SG、VPC 和 Pod selectors 必须一致。旧声明包含未定义的 module/SG 引用和不受限制的 egress；它不是完整的部署模块。

Security-group 返回流量是有状态的，但应用程序发起的新 DNS/数据库/外部连接具有独立的 egress 要求。限制目标，并使用 CNI enforcing 模式和 NetworkPolicy 测试连通性。本次审查未创建 security groups/Pod ENIs，也未执行网络隔离测试。

---

## VPC Endpoints

### 私有 EKS 的 VPC Endpoints

Kubernetes 私有 API endpoint 和 AWS 服务 PrivateLink endpoints 不同。`eks` VPC endpoint 不会替代 kubectl 使用的 Kubernetes API 连接。仅选择实际节点、工作负载和操作员路径所需的服务，并同时验证 Region 支持、DNS、security groups、routes、endpoint policy 和 IAM。

| 用途 | 路径 |
|---|---|
| Kubernetes API | 集群私有 API endpoint 和已连接网络 |
| EKS 管理 API | `com.amazonaws.<region>.eks` |
| Pod Identity | `com.amazonaws.<region>.eks-auth` |
| IRSA STS 交换 | `com.amazonaws.<region>.sts`；在 SDK 中配置区域性 STS |
| OIDC discovery/JWKS | 当前已记录的 `com.amazonaws.<region>.oidc-eks`，独立于 STS |
| ECR 镜像 | `ecr.api`、`ecr.dkr` interfaces 加上 S3 image-layer 路径 |
| 附加服务 | 为实际使用的 EC2、Logs、ELB、Auto Scaling、SSM 和其他 API 验证的 endpoints |

当前 EKS 私有集群文档还列出了 Route 53 API 服务 `com.amazonaws.route53`。区分 DNS 解析与 Route 53 管理 API 调用，并验证服务/Region 支持。请勿在每个 Region 中无条件创建旧版 `ec2messages` endpoints；检查 SSM Agent 和消息传递要求。

### Terraform VPC Endpoint 设置

[完整 Terraform 示例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security/private-endpoints)采用 `logical name → exact service name` 映射。旧的 `split(...)[4]` 可能越界，也可能根据 service-name 长度产生错误 tag；tags 现在使用 `each.key`。

提供现有 subnets、route tables、经批准的客户端 security groups 以及经过审查的 S3 endpoint policy。仅允许来自指定客户端 groups 的 HTTPS。S3 policy 必须涵盖 ECR layer buckets 和其他所需 buckets；endpoint policy 本身并不授予 IAM 访问权限。Terraform 1.15.7/AWS provider 6.64.0 架构验证已通过；未执行 plan/apply 或创建资源。

---

## 控制平面日志记录 {#control-plane-logging}

### EKS 控制平面日志类型

支持的类型为 `api`、`audit`、`authenticator`、`controllerManager` 和 `scheduler`。Kubelet/container 日志具有独立的收集路径。日志组为 `/aws/eks/<cluster-name>/cluster`；请根据运营策略配置 Region、retention、访问、加密、敏感数据处理和收集成本。

### 启用日志记录

与现有集群的 IaC 所有者协调变更。以下目标为一个自有集群，且未在本次审查中执行。更新是异步的：使用 `describe-update` 检查返回的更新 ID，然后单独验证实际日志到达。启用日志记录不需要声明新的集群资源或改变 API endpoint 暴露范围。

```bash
aws eks update-cluster-config --region ap-northeast-2 \
  --name "$CLUSTER_NAME" --logging file://control-plane-logging.json
```

### CloudWatch Logs Insights 查询

以下是**独立的 Logs Insights QL 查询**。请检查所选日志组中的实际字段/时间范围。第一个查询是探索性文本匹配，并非完整的身份验证失败检测器。本次审查未执行托管查询引擎。

Authenticator 错误（探索性）

```text
fields @timestamp, @message
| filter @logStream like /authenticator/
| filter @message like /error|denied/
| sort @timestamp desc
| limit 100
```

由选定身份发起的调用

```text
fields @timestamp, user.username, verb, requestURI, responseStatus.code
| filter @logStream like /audit/
| filter user.username = "REPLACE_WITH_REVIEWED_USERNAME"
| sort @timestamp desc
| limit 50
```

授权拒绝

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

## GuardDuty EKS 保护 {#guardduty-eks-protection}

### GuardDuty EKS 保护概述

请区分 EKS audit-log 分析、Runtime Monitoring 和基础 GuardDuty 数据源。EKS audit 分析涉及 Kubernetes API 活动，并不依赖于启用用户的 CloudWatch 控制平面日志导出。Runtime Monitoring 需要安全 agent 和实际覆盖范围。

当前 Runtime Monitoring 文档支持 EC2 支持的 EKS 和 EKS Auto Mode，而不包括 EKS Hybrid Nodes 和 EKS Fargate。ECS Fargate 支持并不等于 EKS Fargate 支持。确认组织/delegated-administrator 所有权、区域性 detector、平台、成本和 agent-management 所有者。

### 启用 GuardDuty

以下是一个现有 detector 的**配置 payload 示例**；它未应用于任何账户。`RUNTIME_MONITORING` 包含 EKS，因此与 `EKS_RUNTIME_MONITORING` 一起指定无效。请检查自有 detector，而不是总是创建 detector 并选择返回的第一个 ID。审查自动 agent-management 资源/权限和测量的覆盖范围。

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

真实类型包含 tactic 前缀。请使用 finding 的 `severity`、资源、账户/Region、覆盖范围和官方说明，而不是虚构的固定 severity 表。

| 实际类型示例 | 范围 |
|---|---|
| `CredentialAccess:Kubernetes/MaliciousIPCaller` | Kubernetes API 活动 |
| `Discovery:Kubernetes/AnomalousBehavior.PermissionChecked` | 异常 Kubernetes 权限检查 |
| `Execution:Runtime/ReverseShell` | agent 观察到的运行时行为 |
| `CryptoCurrency:Runtime/BitcoinTool.B` | 与运行时挖矿相关的检测 |

### 自动化 Finding 响应

此 EventBridge pattern 路由 Kubernetes/Runtime 类型。旧的 `prefix: Kubernetes` 和 `prefix: Runtime` 无法匹配真实的带 tactic 前缀名称。已使用官方 AWS Event Ruler 2.2.0 library 检查六个匹配/不匹配案例及旧失败情况。

该 pattern 没有 notification/isolation target。Runtime findings 可能涉及 EKS 以外的资源：在路由到经批准的响应之前，检查实际资源 metadata。单独配置 target roles/permissions、retries、DLQ 和 deduplication。创建 `boto3.client("eks")` 不会隔离 Pod；控制需要设计好的 CNI/host/cloud 控制及经过授权的 Kubernetes 操作。

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

### Inspector Container Image 扫描

ECR enhanced scanning 与 Amazon Inspector 集成，可检查受支持镜像中的 package vulnerabilities。运行中镜像的使用上下文不同于运行时行为检测。同一次镜像扫描不会检查任意 Kubernetes manifests、IAM policies 或实时网络流量。

Registry scanning 变更会影响账户/Region 和 repository filter 范围；请确认所有权和预期范围。选择要部署的 digest，而非 `latest`。继续管理新的 CVEs、受支持镜像、重新扫描资格和失败；通过初始扫描并不保证未来安全。

### Inspector 和 CI/CD 集成

[完整的扫描 gate 和测试](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-security)需要精确的 registry/repository/digest、完成时间戳和明确的 severity-count map。仅连续扫描 `ACTIVE` 并不能证明初始结果已就绪。缺失结果、超时、访问拒绝、失败和未知状态绝不能变为零 findings。

```bash
python ecr_scan_gate.py --region ap-northeast-2 \
  --registry-id 123456789012 --repository my-app \
  --digest "$PUBLISHED_IMAGE_DIGEST" --timeout 600 --interval 10 --max-high 0
```

`PUBLISHED_IMAGE_DIGEST` 必须是 build/push 后由 registry 确认的 `sha256:...` 值。替换示例账户/repository 并安装 boto3。十二个回归测试使用真实的 boto3/botocore Stubber 和 fake time，不发出 AWS 请求也不实际等待。

GitHub Actions 集成需要经批准的 OIDC-trusted 角色 ARN、`permissions: id-token: write`、最小权限读取、来自 ECR login outputs 的 registry 以及构建 digest 的传播。未定义的 `$ECR_REGISTRY`、不含角色的凭证配置以及固定的 60 秒 sleep 并非完整 workflow。对于多架构 indexes，请为已部署的 child digests 定义扫描策略。单独管理 exceptions、expiry/ownership 和结果时效性要求。

Enhanced finding events 使用 `aws.inspector2` / `Inspector2 Finding`，不同于 Basic ECR image-scan events。[已验证的 alerting CloudFormation 示例](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/security/image-security/inspector-alerts.yaml)具有独立的 key、permission 和 receiver 前提条件。

---

## CIS Kubernetes 基准 {#cis-kubernetes-benchmark}

### 运行 kube-bench

经审查的上游版本为 kube-bench **0.16.0**。它包括 `eks-1.5.0`、`eks-1.7.0` 和 `eks-1.8.0`，但不包括旧示例的 `eks-1.4.0` 目录。请选择组织所需且与集群/node OS/tool 支持兼容的 CIS EKS 版本；最高编号并不自动是正确选择。上游示例 Job 本身仍使用 `latest` 和 1.5.0，因此应审查并固定 image digest、profile、host mounts 和 permissions，而不是盲目应用。

某些检查需要 host PID/filesystem 访问，并与 Restricted 应用 namespace 冲突。使用经批准的 scanner 运行路径，并记录检查的节点、遗漏和警告。本次审查未在实际节点上执行 kube-bench。

### CIS Benchmark 关键部分

检查所选 CIS EKS profile 中实际的 controlplane、node、policies 和 managedservices 检查。请勿假定客户可访问托管 control-plane 文件。Node settings、RBAC、network policy 和 audit 检查可能需要自动/手动/不适用分类。工具通过率并非安全认证或穷尽性的入侵评估。

### 自动化合规检查

一个 Job 可能只检查其被调度到的节点。为 node groups、OS、architecture 和 configuration 差异设计覆盖范围，并使用 cluster/node/image/profile/time 标注结果。定时运行需要 host mounts、ServiceAccount、所需读取权限、并发控制、完成/失败处理以及结果保留。

旧 CronJob 缺少 host mounts，并假定 kube-bench 镜像包含 AWS CLI。如果必须上传结果，请使用经审查的 uploader 或具有受约束 workload identity 的日志管道。成功上传不得掩盖扫描失败。

---

## 集群加密 {#cluster-encryption}

### EKS Secrets 加密 (KMS)

EKS **1.28+ 默认使用 AWS 自有 KMS key 对所有 Kubernetes API 数据进行信封加密**。请针对特定要求选择 customer-managed key；没有此类 key 并不意味着当前 EKS Secrets 未加密存储。

对于 customer-managed keys，请一并审查 cluster-role/KMS grants、key policy、账户/Region、key 可用性和变更程序。禁用/删除 key 可能影响可用性和恢复；请勿将七天删除窗口照搬为通用的生产标准。`Resource: "*"` 具有 key-policy 特定含义，但不得将其重新用于不受限制的 IAM 访问。验证实际 key 所有者、管理/使用角色、条件和 IAM delegation。

静态加密无法阻止经授权的 API 读取或已被攻陷的应用程序使用某个值。凭证轮换、Secret 交付和重新加载是独立的 [secrets-management](./05-secrets-management.md) 操作。本章未创建 KMS key/cluster，也未更改现有 key association。

---

## 节点安全 {#node-security}

### Bottlerocket OS

Bottlerocket 是一种 container-host OS 选项，并不保证每个工作负载都是安全的。请验证 cluster Kubernetes version、CPU architecture、managed-node-group/Auto Mode model、CNI、storage 和 agents 的受支持组合。遵循 managed-node-group bootstrap merge 规则，而不是盲目覆盖 cluster/API/CA 设置。

管理 updates/reboots/replacements、control/admin-container 访问、SSM permissions、image provenance 和 recovery。旧示例中的 network-buffer sysctls 并非安全加固的证据。AMI type 和 instance architecture 必须一致；本次审查未执行 node group 或 OS。

### 节点安全加固

将受限的 node role 与 workload-specific IRSA/Pod Identity roles 分开。评估 IMDSv2 和 metadata-access controls，包括 hostNetwork、privileged Pods 和 node compromise。仅启用 IRSA 不会自动阻止访问 node role。

使用合适的 non-root identities、禁止 privilege escalation、drop capabilities、seccomp 和具有显式 writable volumes 的 read-only root filesystem，并测试实际应用程序。Labels/selectors/tolerations 是调度输入，而不是 OS attestation 或 authorization。不要将用户设置的标签（例如 `node.kubernetes.io/os: bottlerocket`）视为信任边界；审查 administrator-controlled labels 和用于安全 placement 的实际保护机制，例如 NodeRestriction。

---

## 私有集群 {#private-clusters}

### 完全私有 EKS 配置

私有 Kubernetes API 需要来自 VPC 或已连接管理网络的 DNS、routes 和 security groups，以及 IAM authentication 和 Kubernetes authorization。无法从 public internet 到达并不代表每个已连接用户都获得授权。

变更 API exposure 前，请从当前 operators、CI 和 recovery paths 测试私有访问。通过现有 IaC owner 管理 `endpoint_private_access`/`endpoint_public_access`，而不是无意中声明新集群。单独设计 worker bootstrap 和所需 AWS API/image/package 访问。无互联网运行和私有 API exposure 是不同要求。

### Bastion 或 VPN 访问

使用 VPN、Direct Connect、适当连接的网络或受限制的管理主机。仅 Client VPN subnet association 不足以实现：请一并配置 server/client authentication、非重叠 client CIDR、authorization rules、routes/return routes、DNS、security groups、connection logging 和 IAM/Kubernetes permissions。

Bastion 会增加自身的访问、patching 和 audit 责任。不要默认采用宽泛 SSH ingress 或不受限制的集群管理。本章未部署 VPN、bastion 或 certificates。

---

## 多租户模式 {#multi-tenancy-patterns}

### 基于 Namespace 的多租户

Namespaces 是共享集群中的管理范围，而不是相互敌对租户之间的完整边界。结合 PSS、RBAC、quota、NetworkPolicy、storage、workload identity 和 node/administrator 边界。该示例使用 Kubernetes1.35 policy baseline；请验证与实际集群的兼容性。

同 namespace peers 被允许，而 DNS 在一个 peer 中使用 kube-system namespace **和** kube-dns Pod selector。UDP 和 TCP53 均被包括在内。请单独验证实际 DNS labels、NodeLocal DNS、CNI enforcement、其他 additive policies 和 hostNetwork/node traffic。未执行实时连通性测试。

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

示例 workload admin 无法直接修改 Namespace labels、RoleBindings、NetworkPolicy 或 Secret API permissions。但是，创建 Pods/Deployments 可间接使用 namespace Secrets、ServiceAccounts 和 volumes。排除 Secret get 并不能证明无法访问 secret。当需要更强隔离时，请考虑独立的 clusters/accounts。

对于 EKS 用户访问，请使用 namespace-scoped access policies 或 Kubernetes groups/RBAC 评估当前 access entries。aws-auth ConfigMap 是旧版兼容路径，而不是唯一的集成机制。Authentication-mode 变更具有不可逆的迁移约束；迁移前请验证 administrator/node mappings 和 recovery paths。EKS access policies 和 Kubernetes RBAC 可独立允许访问，因此其中一个缺少权限并不会拒绝另一个授予的允许。不要将 system:masters 授予普通开发人员作为默认示例。

---

## 边界安全和检查路径 {#perimeter-security-and-inspection-paths}

除 IAM 和 Pod policies 外，还应分别验证 public applications、admission webhooks、administrator access、outbound traffic 和 inter-VPC paths。外部 WAF 不会自动保护内部 webhooks；中心化 TGW inspection 覆盖实际经由它路由的流量。将现有 IAM、CNI 和 runtime controls 与以下指南连接起来。

| 保护区域 | 详细指南 |
|---|---|
| 事件、检测和补丁后恢复 | [Defense in Depth and Incident Response](./13-defense-in-depth-incident-response.md) |
| HTTP(S)、API 和 origin bypass | [WAF, Edge and API Security](./14-waf-edge-api-security.md) |
| 管理、TLS visibility 和 appliance selection | [Palo Alto and Fortinet NGFW](./15-ngfw-paloalto-fortinet.md) |
| Symmetric routing、NAT、AZs 和故障 | [GWLB and GENEVE](./16-gwlb-geneve-inspection.md) |

这些指南包括主要来源、inspection limits 和 approved-environment verification plans，而非实际 appliance deployment 或性能结果。

---

## 总结

EKS 安全关键最佳实践：

1. **IAM 集成**：使用 IRSA 或 Pod Identity 访问 AWS 服务
2. **网络安全**：Pod 的 Security Groups、VPC endpoints
3. **日志记录和监控**：控制平面日志、GuardDuty
4. **镜像安全**：Amazon Inspector、ECR 扫描
5. **合规性**：CIS Benchmark、kube-bench
6. **加密**：使用 KMS 加密 Secrets
7. **节点安全**：Bottlerocket OS、最小权限
8. **多租户**：Namespace 隔离、RBAC、ResourceQuota

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