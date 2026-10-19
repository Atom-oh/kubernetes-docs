# VPC Lattice 测验

阅读指南并说明前提条件，而不只是 YAML。

## 1. Amazon VPC Lattice 的主要用途是什么？

- A) 基于 Internet DNS 的全球负载均衡
- B) 跨 VPC 和账户的私有应用程序及资源连接
- C) 跨区域数据库复制
- D) 替代所有 IP 路由

<details>
<summary>显示答案</summary>

B. Lattice 连接服务和资源配置。HTTP 服务路由与资源访问模型彼此不同；关联、网络控制和授权仍然适用。

</details>

## 2. 服务网络代表什么？

- A) 物理网络设备
- B) 包含服务/资源与客户端网络关联的逻辑分组
- C) 子网路由表
- D) 每个服务共用的一个 HTTP 监听器

<details>
<summary>显示答案</summary>

B. 监听器和规则属于各个服务。关联会在满足安全组和适用策略的前提下启用路径；它不会无条件地授权每个请求。

</details>

## 3. 关于 App Mesh 和 Lattice 的哪项说法正确？

- A) Lattice 要求每个 Pod 都有一个 Envoy sidecar
- B) App Mesh 使用 Envoy 代理，而 Lattice 提供托管数据平面，无需应用程序 sidecar
- C) 所有其他 mesh 都需要 sidecar
- D) App Mesh 仍可用于新的 Deployment

<details>
<summary>显示答案</summary>

B. App Mesh 使用 Envoy sidecar 代理，而 Lattice 提供无需应用程序 sidecar 的托管数据平面。D 是错误的：AWS App Mesh 支持已于 2026-09-30 结束，其控制台和资源不再可访问，因此应迁移现有 Deployment，而不是新建 Deployment。其他 mesh 模式的 sidecar 要求有所不同。

</details>

## 4. AWS Gateway API Controller 如何映射资源？

- A) 每个 Kubernetes Service 都会创建一个服务网络
- B) Gateway 按名称选择网络；每个 HTTPRoute 都会创建自己的 Lattice 服务/域名
- C) Gateway 总是创建一个由所有 Route 共用的 ingress IP
- D) Controller 仅使用 Ingress API

<details>
<summary>显示答案</summary>

B. GatewayClass 选择 Controller。Gateway 通过不含 namespace 的名称引用现有服务网络；后端 Service/endpoints 提供 target group。单独的 Gateway 不会创建该网络。

</details>

## 5. 客户端应如何获取分配的 Lattice 服务 DNS 名称？

- A) 将 region 附加到 Kubernetes Service 名称
- B) 将服务网络 ID 放入猜测的 hostname
- C) 读取 get-service dnsEntry 或 Route 的 lattice-assigned-domain-name annotation
- D) 将 Gateway.status.addresses 复用为每个 Route 的地址

<details>
<summary>显示答案</summary>

C. 每个 Route 都有自己的服务/域名。请使用实际返回的值；重新创建服务可能会改变其分配的名称。自定义域名需要各自的 DNS 和证书设置。

</details>

## 6. 关于身份验证的哪项说法正确？

- A) 服务上的 NONE 会禁用所有网络策略
- B) 如果客户端具有 IAM role，AWS_IAM 接受未签名的 curl 请求
- C) AWS_IAM 使用受支持的签名请求；每一层适用的 IAM 授权层都必须允许访问
- D) RAM 共享会自动授予 Invoke

<details>
<summary>显示答案</summary>

C. VPC Lattice 支持 SigV4 和 SigV4A。签名时使用 vpc-lattice-svcs 和 UNSIGNED-PAYLOAD。调用方身份权限和适用的网络/服务授权策略必须允许访问；显式 Deny 优先。NONE 只影响它自己的层。

</details>

## 7. 以下哪项不是命名的 Lattice 服务 target-group 类型？

- A) INSTANCE
- B) IP
- C) LAMBDA
- D) RDS

<details>
<summary>显示答案</summary>

D. 服务 target-group 类型包括 INSTANCE、IP、LAMBDA 和 ALB。这并不意味着 Lattice 无法连接 RDS 数据库：资源配置和资源网关提供了单独的 TCP 资源访问模型。服务授权策略不管理该资源流量。

</details>

## 8. backendRefs 的 90:10 weight 比例表示什么？

- A) 连续每十个请求中恰好有一个到达 canary
- B) 两个后端之间的相对流量分配
- C) Pod 副本数要求
- D) Gateway API 不支持的 annotation

<details>
<summary>显示答案</summary>

B. 原生 backendRefs.weight 配置相对分配；小规模请求样本不一定精确匹配。两个后端都必须存在且健康。在增加 canary 份额之前，请观察错误和延迟。

</details>

## 9. 说明服务网络的跨账户共享。

<details>
<summary>显示答案</summary>

所有者为网络 ARN 以及目标账户、组织或 OU 创建 RAM 共享。已启用共享的组织内使用者无需邀请；其他适用安排需要接受。使用者关联自己的 VPC 或创建适当的服务网络 endpoint。共享不会授予 Invoke：调用方策略、授权策略、网络路径和安全组也必须允许访问。停止共享会保留现有的关联。

</details>

## 10. 为演示后端编写 Kubernetes health-check 策略。

<details>
<summary>显示答案</summary>

在与其目标 Service 相同的 namespace 中使用 TargetGroupPolicy。Controller CRD 使用 intervalSeconds/timeoutSeconds/statusMatch，而 AWS API 使用 healthCheckIntervalSeconds/healthCheckTimeoutSeconds/matcher。

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: TargetGroupPolicy
metadata:
  name: stable-health
  namespace: lattice-demo
spec:
  targetRef:
    group: ''
    kind: Service
    name: service-stable
  protocol: HTTP
  protocolVersion: HTTP1
  healthCheck:
    enabled: true
    protocol: HTTP
    protocolVersion: HTTP1
    port: 8080
    path: /health
    intervalSeconds: 30
    timeoutSeconds: 5
    healthyThresholdCount: 2
    unhealthyThresholdCount: 2
    statusMatch: '200'
```

后端必须确实在 8080 上监听，并在 /health 返回 200。阈值有助于确定就绪状态；它们并不保证可用性或零停机时间。请检查 target-type 和特定协议的行为。

</details>

## 11. Transit Gateway 和 VPC Lattice 有何区别？

<details>
<summary>显示答案</summary>

Transit Gateway 在网络之间路由 IP 流量。Lattice 公开服务和资源配置：HTTP 服务路径可以使用 L7 路由，而 TLS/TCP/资源功能具有不同特性。它们可以一起使用。服务网络 VPC endpoint 支持通过 transit/peering 到达的适用客户端；仅直接 VPC 关联不会授予该 transit 访问权限。

</details>

## 12. 授权策略可应用于哪些层级，以及如何限制演示 API 路径？

<details>
<summary>显示答案</summary>

授权策略应用于配置了 AWS_IAM 的服务网络和单个服务。两个适用层以及调用方的身份策略都必须允许该请求。使用 StringLike 进行通配符匹配，并显式包含根路径：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "vpc-lattice-svcs:RequestPath": [
            "/api",
            "/api/*"
          ]
        }
      }
    }
  ]
}
```

StringEquals 会按字面匹配 /api/*。此策略涉及规范路径；应用程序规范化和 Controller 路径路由是独立行为。PutAuthPolicy 而非 PutResourcePolicy 管理调用授权。

</details>

## 13. 描述 AWS Gateway API Controller v2.1.3 的 IRSA 安装。

<details>
<summary>显示答案</summary>

验证集群支持的 Kubernetes 版本、Gateway API 兼容性、IAM OIDC provider 以及网络/webhook 可达性。针对预期账户/功能检查该 release 推荐的策略；其宽泛的上游权限并不能保证最小权限。使用专用的 Controller service account 和已发布的 OCI chart：

```bash
curl --fail --location --output controller-policy-upstream.json \
  https://raw.githubusercontent.com/aws/aws-application-networking-k8s/v2.1.3/files/controller-installation/recommended-inline-policy.json

# Use the policy reviewed for this account and the enabled controller features.
export REVIEWED_POLICY_FILE=controller-policy-reviewed.json
test -s "$REVIEWED_POLICY_FILE"
export CONTROLLER_POLICY_ARN="$(aws iam create-policy \
  --policy-name VPCLatticeControllerPolicy \
  --policy-document "file://$REVIEWED_POLICY_FILE" \
  --query Policy.Arn --output text)"

# Prerequisite: this cluster's IAM OIDC provider already exists.
eksctl create iamserviceaccount \
  --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --namespace aws-application-networking-system \
  --name gateway-api-controller \
  --attach-policy-arn "$CONTROLLER_POLICY_ARN" \
  --approve
```

```bash
curl --fail --location --output gateway-api-v1.5.0.yaml \
  https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.0/standard-install.yaml
# Inspect changes first if any Gateway API controller is already installed.
kubectl apply --server-side -f gateway-api-v1.5.0.yaml

helm pull oci://public.ecr.aws/aws-application-networking-k8s/aws-gateway-controller-chart \
  --version v2.1.3
helm show crds ./aws-gateway-controller-chart-v2.1.3.tgz > lattice-crds.yaml
kubectl apply --server-side -f lattice-crds.yaml

helm install gateway-api-controller ./aws-gateway-controller-chart-v2.1.3.tgz \
  --namespace aws-application-networking-system --create-namespace \
  --set serviceAccount.create=false \
  --set serviceAccount.name=gateway-api-controller \
  --set-string awsRegion="$AWS_REGION" \
  --set-string awsAccountId="$AWS_ACCOUNT_ID" \
  --set-string clusterVpcId="$VPC_ID" \
  --set-string clusterName="$CLUSTER_NAME" \
  --wait --timeout 5m

kubectl -n aws-application-networking-system get pods
kubectl -n aws-application-networking-system logs \
  -l control-plane=gateway-api-controller -c manager --tail=100
```

Controller role 管理资源；它不是应用程序调用方 role。现有 service account/release 需要考虑所有权的升级。Helm 不会自动升级其 CRD。有关单独的服务网络/授权策略设置，请参阅指南。

</details>

## 14. 为 90:10 stable/canary 分流编写 HTTPRoute。

<details>
<summary>显示答案</summary>

前提条件：指南中位于 lattice-demo 的 my-network HTTPS Gateway、其现有服务网络和活动授权策略、两个位于 8080 的后端 Deployment/Service，以及 target-group health 策略。然后应用：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
      weight: 90
    - name: service-canary
      port: 8080
      weight: 10
```

也将指南的 IAMAuthPolicy 应用于此 Route，并检查协调结果。不需要 weight annotation。使用 Route 分配的域名和已签名的 HTTPS 请求；成功应用并不能证明后端健康。

</details>

## 15. 仅允许 AdminRole 和 DevOpsRole 在 /admin 及其子路径调用专用管理服务。

<details>
<summary>显示答案</summary>

将以下内容作为完整的服务授权策略，并使用真实的账户/role ARN。将该专用服务设置为 AWS_IAM，并确保调用方身份策略和网络授权策略也允许这些 role 和路径。指南仅适用于 API 的网络策略需要经过审查后才能为此单独的管理服务进行更改。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
          "vpc-lattice-svcs:RequestPath": [
            "/admin",
            "/admin/*"
          ]
        }
      }
    }
  ]
}
```

对于位于 lattice-demo 且名为 admin 的 Controller 管理的 HTTPRoute，请使用真实的 CRD 附加它：

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: admin-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: admin
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":["arn:aws:iam::123456789012:role/AdminRole","arn:aws:iam::123456789012:role/DevOpsRole"]},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/admin","/admin/*"]}}}]}'
```

不存在宽泛的 AllowGeneralAccess 语句。在此策略中，其他 role 和路径没有 Allow，并且明确包含 /admin，而非仅包含 /admin/*。将路径规范化/编码视为应用程序安全要求；专用的 role 限制服务和应用程序授权可减少对路径别名的依赖。还必须保护直接后端访问。删除 IAMAuthPolicy 会将目标授权类型更改为 NONE，并不是拒绝或安全回滚机制。

</details>

得分 13–15 表示对本章有较强理解，10–12 表示应复习遗漏的主题，0–9 表示应重新阅读指南。测验分数并不能证明具备生产环境运维经验。

[返回指南](../../networking/02-vpc-lattice.md)
