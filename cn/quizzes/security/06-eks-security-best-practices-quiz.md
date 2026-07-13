# EKS 安全最佳实践测验

通过以下问题测试你对 Amazon EKS 安全最佳实践的理解。

***

## 问题

### 1. 当 Pod 使用 IRSA（IAM Roles for Service Accounts）调用 AWS APIs 时，会使用哪种身份验证方法？

* A) IAM User Access Key
* B) EC2 Instance Profile
* C) 基于 OIDC token 的 AssumeRoleWithWebIdentity
* D) 存储在 Kubernetes Secret 中的凭证

<details>

<summary>显示答案</summary>

**答案：C) 基于 OIDC token 的 AssumeRoleWithWebIdentity**

**解析：** IRSA 的工作方式：

1. EKS cluster 的 OIDC Provider 发放 ServiceAccount token
2. Pod 调用 AWS STS `AssumeRoleWithWebIdentity` API
3. OIDC token 通过验证并签发临时凭证
4. Pod 使用临时凭证调用 AWS APIs

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/S3ReaderRole
```

IRSA 支持在 Pod 级别而不是 node 级别进行细粒度权限管理。

</details>

***

### 2. 与 IRSA 相比，EKS Pod Identity 的主要优势是什么？

* A) 更强的加密
* B) 更快的性能
* C) 无需设置 OIDC Provider，管理更简单
* D) 支持更多 AWS 服务

<details>

<summary>显示答案</summary>

**答案：C) 无需设置 OIDC Provider，管理更简单**

**解析：** EKS Pod Identity 的好处：

* 无需设置 OIDC Provider
* 简化 IAM Role Trust Policy
* 通过 Pod Identity Agent 自动管理凭证
* 简化跨账号访问

```bash
# Pod Identity association (simple CLI setup)
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace production \
  --service-account myapp-sa \
  --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

IRSA 需要为每个 cluster 设置 OIDC Provider 并配置复杂的 Trust Policy。

</details>

***

### 3. 下列哪一项不是使用 Security Groups for Pods 的要求？

* A) 基于 Nitro 的实例类型
* B) Amazon VPC CNI plugin
* C) Fargate profile
* D) ENIConfig 或 SecurityGroupPolicy CRD

<details>

<summary>显示答案</summary>

**答案：C) Fargate profile**

**解析：** Security Groups for Pods 的要求：

* **必需**：基于 Nitro 的 EC2 instances（m5、c5、r5 等）
* **必需**：Amazon VPC CNI plugin v1.7.7+
* **必需**：SecurityGroupPolicy CRD 配置
* **可选**：Fargate（单独的配置方法）

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-access-policy
spec:
  podSelector:
    matchLabels:
      app: backend
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Fargate 会自动为每个 Pod 分配 ENI，因此需要单独配置。

</details>

***

### 4. 将 EKS cluster 的 Kubernetes API server endpoint 设置为仅私有访问会有什么影响？

* A) 完全无法使用 kubectl
* B) 只能从 VPC 内部或已连接的网络访问
* C) 无法从 AWS Console 管理 cluster
* D) Worker nodes 无法连接到 API server

<details>

<summary>显示答案</summary>

**答案：B) 只能从 VPC 内部或已连接的网络访问**

**解析：** 配置 private endpoint 时：

* 可从 VPC 内部访问
* 可从通过 VPN、Direct Connect、VPC Peering 连接的网络访问
* 无法从公共互联网访问

```bash
# Endpoint configuration
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=false,endpointPrivateAccess=true
```

出于安全考虑，建议仅使用 private endpoint。

</details>

***

### 5. AWS GuardDuty EKS Protection 不会检测哪种威胁类型？

* A) 与恶意 IPs 通信
* B) Cryptocurrency mining 活动
* C) Pod resource usage 超过限制
* D) Tor network 连接

<details>

<summary>显示答案</summary>

**答案：C) Pod resource usage 超过限制**

**解析：** GuardDuty EKS Protection 检测的威胁：

* 与恶意 IP addresses 通信
* Cryptocurrency mining（Kubernetes API 滥用）
* Tor network 连接
* DNS Rebinding 攻击
* Privilege escalation 尝试
* 异常 API call patterns

Resource usage monitoring 由以下组件执行：

* Kubernetes Metrics Server
* Prometheus/Grafana
* CloudWatch Container Insights

</details>

***

### 6. 在 EKS cluster 中，哪个 AWS service 不需要 VPC endpoints？

* A) ECR (dkr, api)
* B) S3
* C) STS
* D) Route 53

<details>

<summary>显示答案</summary>

**答案：D) Route 53**

**解析：** EKS 推荐的 VPC endpoints：

* **ECR (dkr, api)**：拉取 container image
* **S3**：存储 image layer
* **STS**：IRSA/Pod Identity 身份验证
* **CloudWatch Logs**：传输日志
* **EC2, ELB, Auto Scaling**：管理 node

Route 53 是使用标准 DNS resolution 的 global DNS service，而不是使用 VPC endpoints。

```bash
# Create required VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.region.ecr.dkr \
  --vpc-endpoint-type Interface
```

</details>

***

### 7. 使用 kube-bench 检查 EKS cluster 安全性时使用的是哪个 benchmark？

* A) PCI-DSS
* B) CIS Kubernetes Benchmark
* C) NIST Cybersecurity Framework
* D) SOC 2

<details>

<summary>显示答案</summary>

**答案：B) CIS Kubernetes Benchmark**

**解析：** kube-bench 会根据 CIS（Center for Internet Security）Kubernetes Benchmark 检查 cluster 安全性：

```bash
# Run kube-bench on EKS node
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job-eks.yaml

# Check results
kubectl logs job/kube-bench
```

检查项：

* Control Plane 配置（部分项目因 EKS 托管而为 N/A）
* Worker Node 配置
* Policies 和 Pod security
* Network policies
* Logging 和 auditing

</details>

***

### 8. Service Account Token Volume Projection 在 EKS 中提供什么安全收益？

* A) 减小 token 大小
* B) Bound tokens 和 expiration time 设置
* C) Token 加密
* D) 自动 token 备份

<details>

<summary>显示答案</summary>

**答案：B) Bound tokens 和 expiration time 设置**

**解析：** Service Account Token Volume Projection 的安全收益：

* **Bound tokens**：仅对特定 Pod 有效
* **Expiration time**：自动 token 过期（默认 1 小时）
* **Audience specification**：仅对特定 audience 有效

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: token
          mountPath: /var/run/secrets/tokens
  volumes:
    - name: token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              expirationSeconds: 3600
              audience: sts.amazonaws.com
```

Legacy tokens 永不过期，因此一旦泄露会带来风险。

</details>

***

### 9. Amazon Inspector 在 EKS 环境中扫描什么？

* A) Kubernetes manifests
* B) Container image 漏洞
* C) IAM policies
* D) Network traffic

<details>

<summary>显示答案</summary>

**答案：B) Container image 漏洞**

**解析：** Amazon Inspector 的 EKS 集成：

* 扫描存储在 ECR 中的 container images
* 扫描运行中 workloads 的 images
* 检测 OS package 漏洞
* 检测 application package 漏洞（npm、pip 等）

```bash
# Enable Inspector
aws inspector2 enable \
  --resource-types ECR

# Check scan results
aws inspector2 list-findings \
  --filter-criteria resourceType=AWS_ECR_CONTAINER_IMAGE
```

Continuous scanning 会在发现新的 CVEs 时提供 alerts。

</details>

***

### 10. 将 EKS cluster Control Plane logs 发送到 CloudWatch 时，无法启用哪种 log type？

* A) api
* B) audit
* C) controllerManager
* D) kubelet

<details>

<summary>显示答案</summary>

**答案：D) kubelet**

**解析：** EKS Control Plane log types：

* **api**：API server 日志
* **audit**：审计日志（谁做了什么）
* **authenticator**：IAM 身份验证日志
* **controllerManager**：Controller manager 日志
* **scheduler**：Scheduler 日志

kubelet logs 在 worker nodes 上生成，不属于 Control Plane logs。

```bash
# Enable Control Plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

</details>

***

### 11. 为什么在 EKS 中应将 Node IAM Role 与 Pod IAM Role（IRSA）分离？

* A) 节省成本
* B) 应用 least privilege principle
* C) 性能提升
* D) 降低网络延迟

<details>

<summary>显示答案</summary>

**答案：B) 应用 least privilege principle**

**解析：** 权限分离的重要性：

**Node IAM Role（范围较广）：**

* 所有 Pods 都可访问（Instance Metadata）
* 仅包含 ECR pull、CloudWatch logs 等基本权限

**IRSA（范围较窄）：**

* 仅连接到特定 ServiceAccount
* 只授予每个 application 所需的权限

```yaml
# Wrong example: S3 full access on Node Role
# -> All Pods can access S3

# Correct example: Grant permissions only to specific Pod via IRSA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-processor
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::xxx:role/S3ProcessorRole
```

</details>

***

### 12. 在 EKS 中，哪个组件负责将 Kubernetes RBAC 与 AWS IAM 集成？

* A) kube-apiserver
* B) aws-auth ConfigMap
* C) aws-iam-authenticator
* D) kube-proxy

<details>

<summary>显示答案</summary>

**答案：C) aws-iam-authenticator**

**解析：** EKS 身份验证流程：

1. kubectl 从 AWS STS 获取 token
2. aws-iam-authenticator 验证 IAM credentials
3. aws-auth ConfigMap 将 IAM 映射到 Kubernetes user/group
4. Kubernetes RBAC 决定权限

```yaml
# aws-auth ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/DevTeamRole
      username: dev-user
      groups:
        - dev-team
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/admin
      username: admin
      groups:
        - system:masters
```

</details>

***

## 分数计算

每题计 1 分。

| 分数  | 评级                                       |
| ----- | ------------------------------------------ |
| 11-12 | 优秀 - EKS 安全专家级别                  |
| 8-10  | 良好 - 已理解基本概念，请复习高级功能      |
| 5-7   | 一般 - 建议继续学习                        |
| 0-4   | 需要基础学习                               |

***

## 相关文档

* [EKS 安全最佳实践](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/06-eks-security-best-practices.md)
* [Pod Security Standards](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/03-pod-security-standards.md)
* [Secrets Management](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/security/05-secrets-management.md)
