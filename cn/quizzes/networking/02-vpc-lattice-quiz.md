# VPC Lattice 测验

本测验用于测试你对 Amazon VPC Lattice 的理解。

## 选择题

1. Amazon VPC Lattice 的主要用途是什么？
   - A) 管理从互联网到 AWS 资源的外部流量
   - B) 不同 VPC 和账户中服务之间的内部通信
   - C) AWS 区域之间的数据复制
   - D) 基于 DNS 的全局负载均衡

<details>

<summary>显示答案</summary>

**答案：B) 不同 VPC 和账户中服务之间的内部通信**

**说明：**
VPC Lattice 是一项 AWS 应用程序网络服务，其主要用途是在多个 VPC 和 AWS 账户之间安全地连接和管理服务。它在名为 Service Network 的逻辑边界内提供服务发现、流量路由、身份验证和授权。外部流量管理由 API Gateway 或 ALB 处理，跨区域复制由 S3 Cross-Region Replication 等服务处理。
</details>

2. 以下关于 VPC Lattice 的 Service Network 的说法哪项正确？
   - A) 连接物理网络设备的一层
   - B) 对服务进行分组并管理其通信的逻辑边界
   - C) 在 VPC 内连接子网的路由表
   - D) Internet Gateway 的替代服务

<details>

<summary>显示答案</summary>

**答案：B) 对服务进行分组并管理其通信的逻辑边界**

**说明：**
Service Network 是 VPC Lattice 的核心组件，用于在逻辑上将多个服务分组。当你将 VPC 与 Service Network 关联时，该 VPC 中的资源可以与网络中的服务通信。多个 VPC（包括来自不同账户的 VPC）可以连接到单个 Service Network，并且可以集中管理每个服务的身份验证策略和访问控制。
</details>

3. VPC Lattice 与 AWS App Mesh 有什么区别？
   - A) VPC Lattice 需要 sidecar proxy，而 App Mesh 不需要
   - B) App Mesh 基于 sidecar proxy，而 VPC Lattice 不需要 sidecar
   - C) VPC Lattice 仅支持 TCP，而 App Mesh 仅支持 HTTP
   - D) 两项服务使用相同的架构

<details>

<summary>显示答案</summary>

**答案：B) App Mesh 基于 sidecar proxy，而 VPC Lattice 不需要 sidecar**

**说明：**
AWS App Mesh 是一种 service mesh，它会向每个 service pod 注入 Envoy sidecar proxy 以控制流量。另一方面，VPC Lattice 是一项完全托管的 AWS 服务，无需 sidecar proxy 即可提供服务间通信、路由和身份验证。这样可使 VPC Lattice 的运维复杂度更低、资源开销更小，但 App Mesh 提供的一些细粒度流量控制功能可能会受限。
</details>

4. 将 EKS 与 VPC Lattice 集成时使用哪个 Kubernetes API？
   - A) Ingress API
   - B) Service API
   - C) Gateway API
   - D) NetworkPolicy API

<details>

<summary>显示答案</summary>

**答案：C) Gateway API**

**说明：**
AWS Gateway API Controller 会将 Kubernetes Gateway API 资源（GatewayClass、Gateway、HTTPRoute 等）转换为 VPC Lattice 资源。Gateway API 是 Kubernetes 的下一代 ingress 规范，提供比 Ingress 更丰富的功能和可扩展性。通过在 GatewayClass 中指定 amazon-vpc-lattice controller 并创建 Gateway 和 HTTPRoute，Controller 会自动创建 VPC Lattice Services 和 Target Groups。
</details>

5. VPC Lattice 服务的正确 DNS 名称格式是什么？
   - A) service-name.region.amazonaws.com
   - B) service-name.vpc-lattice-svcs.region.on.aws
   - C) service-name.internal.aws
   - D) service-name.lattice.region.aws

<details>

<summary>显示答案</summary>

**答案：B) service-name.vpc-lattice-svcs.region.on.aws**

**说明：**
VPC Lattice 服务会被自动分配 DNS 名称。格式为 `<service-name>.<service-network-id>.vpc-lattice-svcs.<region>.on.aws`。此 DNS 名称可从连接到 Service Network 的所有 VPC 进行解析。客户端使用此 DNS 名称访问服务，VPC Lattice 会在内部路由到相应的目标。若要使用自定义域名，可以在 Route 53 等服务中设置 CNAME 或 Alias 记录。
</details>

6. VPC Lattice 支持哪些身份验证方法？
   - A) 仅 API Key
   - B) 仅 OAuth 2.0
   - C) AWS IAM 或无身份验证
   - D) 仅 SAML

<details>

<summary>显示答案</summary>

**答案：C) AWS IAM 或无身份验证**

**说明：**
VPC Lattice 支持两种身份验证模式。在 AWS_IAM 模式下，请求需要 SigV4 (Signature Version 4) 签名，并通过 IAM policies 和 resource policies 控制访问。在 NONE 模式下，允许所有请求，无需身份验证。使用 IAM 身份验证可以对哪些 IAM roles/users 能访问哪些服务的哪些路径进行细粒度控制。
</details>

7. 以下哪项不是 VPC Lattice Target Groups 支持的目标类型？
   - A) EC2 instances
   - B) EKS pods (IP type)
   - C) Lambda functions
   - D) RDS databases

<details>

<summary>显示答案</summary>

**答案：D) RDS databases**

**说明：**
VPC Lattice Target Groups 支持 EC2 instances、IP addresses（包括 EKS pods）、Lambda functions 和 ALB 作为目标。RDS databases 不能作为 VPC Lattice 目标，因为它们使用的是数据库协议而非 HTTP/HTTPS。对于 EKS pods，使用 IP type Target Groups，AWS Gateway API Controller 会自动注册/注销 pod IP。
</details>

8. VPC Lattice 中加权路由的主要使用场景是什么？
   - A) 仅负载均衡
   - B) Canary deployments 和 blue-green deployments
   - C) 基于地理位置的路由
   - D) Sticky sessions

<details>

<summary>显示答案</summary>

**答案：B) Canary deployments 和 blue-green deployments**

**说明：**
加权路由会按比例将流量分配到多个 Target Groups。在 canary deployments 中，先将 10% 的流量发送到新版本进行验证，然后逐渐增加。在 blue-green deployments 中，会一次性将 100% 的流量从 blue 切换到 green。示例：设置 `service-v1: weight 90, service-v2: weight 10` 会仅将 10% 的流量发送到 v2。如果发现问题，可以调整权重以回滚。
</details>

## 简答题

9. 说明如何在账户之间共享 VPC Lattice Service Network。

<details>

<summary>显示答案</summary>

**答案：**
使用 AWS Resource Access Manager (RAM) 将 Service Network 共享给其他 AWS 账户或组织。

**说明：**
跨账户共享流程：
1. **所有者账户**：在 RAM 中为 Service Network 创建 resource share
   ```bash
   aws ram create-resource-share \
     --name my-service-network-share \
     --resource-arns arn:aws:vpc-lattice:region:account:servicenetwork/sn-xxx \
     --principals 123456789012  # Target account ID
   ```
2. **目标账户**：接受 RAM 邀请
3. **目标账户**：将其 VPC 与共享的 Service Network 关联
4. 此后，目标账户中的服务也可以注册到 Service Network

使用 Organizations 时，也可以自动共享给整个组织。
</details>

10. 说明为什么在 VPC Lattice 中配置 Health Check 很重要。

<details>

<summary>显示答案</summary>

**答案：**
Health Checks 会自动从流量路由中排除不健康的目标，以确保服务可用性。

**说明：**
VPC Lattice Health Checks 的工作方式：
1. **定期检查**：按配置的间隔向目标 Health Check endpoints 发送请求（例如每 30 秒）
2. **基于阈值的判定**：由连续成功/失败次数决定状态（healthyThresholdCount/unhealthyThresholdCount）
3. **自动排除/恢复**：不健康的目标会从流量中排除，恢复后会自动重新加入
4. **配置示例**：
   ```yaml
   healthCheck:
     enabled: true
     protocol: HTTP
     path: /health
     healthCheckIntervalSeconds: 30
     healthyThresholdCount: 5
     unhealthyThresholdCount: 2
     matcher:
       httpCode: "200-299"
   ```
正确配置 Health Check 可防止在 rolling updates 期间发生停机，并通过避免向故障目标发送请求来保护用户体验。
</details>

11. 说明 VPC Lattice 与 Transit Gateway 之间的区别。

<details>

<summary>显示答案</summary>

**答案：**
Transit Gateway 在网络层 (L3) 提供 VPC 之间的 IP 路由，而 VPC Lattice 在应用层 (L7) 提供基于服务的通信。

**说明：**
主要区别：

| 方面 | Transit Gateway | VPC Lattice |
|--------|-----------------|-------------|
| 抽象层级 | 网络（基于 IP） | 服务（基于名称） |
| 路由 | IP 路由表 | 基于 HTTP path/header |
| 协议 | 所有 IP 流量 | HTTP/HTTPS/gRPC |
| 身份验证 | Security Groups、NACLs | AWS IAM、resource policies |
| 可观测性 | 网络 flow logs | 应用层 metrics/logs |

当需要 VPC 之间进行所有 IP 通信时，使用 Transit Gateway；而 VPC Lattice 适用于 microservices 之间基于 HTTP 的通信。两项服务可以结合使用。
</details>

12. 说明 Auth Policy 在 VPC Lattice 中的作用以及可应用的层级。

<details>

<summary>显示答案</summary>

**答案：**
Auth Policy 定义基于 IAM 的访问控制，并同时应用于 Service Network 层级和单个 Service 层级。

**说明：**
Auth Policy 应用层级：
1. **Service Network 层级**：应用于整个网络的默认 policy
   - 控制哪些 IAM principals 可以连接到网络
2. **Service 层级**：应用于单个服务的详细 policy
   - 控制哪些 principals 可以访问特定服务的哪些路径

Policy 示例：
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
    },
    "Action": "vpc-lattice-svcs:Invoke",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "vpc-lattice-svcs:RequestPath": "/api/*"
      }
    }
  }]
}
```
此 policy 限制 MyAppRole 仅能访问 /api/* 路径。
</details>

## 实操题

13. 编写用于在 EKS 上安装 AWS Gateway API Controller 的 IAM policy 和 IRSA 配置。

<details>

<summary>显示答案</summary>

**答案：**
```bash
# 1. Create IAM policy for VPC Lattice permissions
cat <<EOF > vpc-lattice-controller-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc-lattice:*",
        "iam:CreateServiceLinkedRole",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeAvailabilityZones"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document file://vpc-lattice-controller-policy.json

# 2. Create service account using IRSA
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=aws-application-networking-system \
  --name=gateway-api-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/VPCLatticeControllerPolicy \
  --override-existing-serviceaccounts \
  --approve

# 3. Install AWS Gateway API Controller
kubectl apply -f https://raw.githubusercontent.com/aws/aws-application-networking-k8s/main/files/controller-installation/deploy-v1.0.yaml
```

**说明：**
AWS Gateway API Controller 会监视 Kubernetes 集群中的 Gateway API 资源，并创建/管理 VPC Lattice 资源。通过 IRSA (IAM Roles for Service Accounts)，Controller pod 获得调用所需 AWS APIs 的权限。该 policy 包括 vpc-lattice 操作、VPC/subnet 查询和 log delivery 权限。
</details>

14. 编写一个使用 VPC Lattice 在两个服务之间配置加权路由 (90:10) 的 HTTPRoute。

<details>

<summary>显示答案</summary>

**答案：**
```yaml
# GatewayClass definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Gateway definition
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
  namespace: default
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
# Weighted routing HTTPRoute
apiVersion: gateway.networking.k8s.io/v1beta1
kind: HTTPRoute
metadata:
  name: weighted-routing
  namespace: default
spec:
  parentRefs:
  - name: my-gateway
    sectionName: http
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 80
      weight: 90
    - name: service-canary
      port: 80
      weight: 10
---
# Stable service
apiVersion: v1
kind: Service
metadata:
  name: service-stable
spec:
  selector:
    app: myapp
    version: stable
  ports:
  - port: 80
    targetPort: 8080
---
# Canary service
apiVersion: v1
kind: Service
metadata:
  name: service-canary
spec:
  selector:
    app: myapp
    version: canary
  ports:
  - port: 80
    targetPort: 8080
```

**说明：**
在此配置中，发送到 `/api` 路径的 90% 流量会路由到 service-stable，10% 会路由到 service-canary。当 AWS Gateway API Controller 检测到此 HTTPRoute 时，它会在 VPC Lattice 中创建两个 Target Groups，并设置 listener rules 以根据指定权重分配流量。验证 canary deployment 后，可以逐渐调整权重。
</details>

15. 为 VPC Lattice 服务编写一个基于 IAM 的 Auth Policy。（仅允许特定 IAM roles 访问 /admin 路径）

<details>

<summary>显示答案</summary>

**答案：**
```bash
# Apply Auth Policy to VPC Lattice service
aws vpc-lattice put-auth-policy \
  --resource-identifier svc-0123456789abcdef0 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowGeneralAccess",
        "Effect": "Allow",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringNotEquals": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "AllowAdminAccess",
        "Effect": "Allow",
        "Principal": {
          "AWS": [
            "arn:aws:iam::123456789012:role/AdminRole",
            "arn:aws:iam::123456789012:role/DevOpsRole"
          ]
        },
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          }
        }
      },
      {
        "Sid": "DenyUnauthorizedAdmin",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*",
        "Condition": {
          "StringLike": {
            "vpc-lattice-svcs:RequestPath": "/admin/*"
          },
          "StringNotEquals": {
            "aws:PrincipalArn": [
              "arn:aws:iam::123456789012:role/AdminRole",
              "arn:aws:iam::123456789012:role/DevOpsRole"
            ]
          }
        }
      }
    ]
  }'
```

**Kubernetes Gateway API 方法：**
```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-type: "AWS_IAM"
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: http
    protocol: HTTP
    port: 80
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: vpc-lattice-auth-policy
  namespace: default
  annotations:
    application-networking.k8s.aws/auth-policy: |
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "AWS": "arn:aws:iam::123456789012:role/AdminRole"
            },
            "Action": "vpc-lattice-svcs:Invoke",
            "Resource": "*"
          }
        ]
      }
data: {}
```

**说明：**
此 Auth Policy 包含三条规则：
1. **AllowGeneralAccess**：允许所有 principals 访问除 /admin/* 之外的所有路径
2. **AllowAdminAccess**：允许 AdminRole 和 DevOpsRole 访问 /admin/* 路径
3. **DenyUnauthorizedAdmin**：明确拒绝上述 roles 以外的 principals 访问 /admin/*

客户端必须使用 SigV4 对请求签名。你可以使用 AWS SDK 或 aws-sigv4 library 进行签名。
</details>

---

**评分：**
- 13-15 题正确：优秀（VPC Lattice 专家级别）
- 10-12 题正确：良好（能够进行实际应用）
- 7-9 题正确：一般（建议进一步学习）
- 4-6 题正确：基础（需要复习基本概念）
- 0-3 题正确：不足（需要重新学习全部内容）
