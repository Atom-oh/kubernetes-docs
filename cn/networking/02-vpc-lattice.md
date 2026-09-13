# VPC Lattice

Amazon VPC Lattice 连接跨 VPC 和 AWS 账户的应用。本章介绍资源模型、EKS 集成、路由、IAM 授权、监控和故障排除。

> **最后更新**：2026 年 9 月 11 日，依据 AWS Gateway API Controller **v2.1.3** 和 Gateway API **v1.5.0**。示例介绍配置和验证步骤；本次审查未将其部署到 AWS 账户。

## 目录

- [概述](#overview)
- [架构](#architecture)
- [EKS 与 VPC Lattice 集成](#eks-and-vpc-lattice-integration)
- [安装与配置](#installation-and-configuration)
- [服务管理](#service-management)
- [路由与流量管理](#routing-and-traffic-management)
- [安全与身份验证](#security-and-authentication)
- [监控与日志](#monitoring-and-logging)
- [最佳实践](#best-practices)
- [故障排除](#troubleshooting)
- [参考资料](#references)

## 概述 {#overview}

### 什么是 VPC Lattice？

VPC Lattice 提供应用联网能力，无需在每个应用旁运行代理。**服务网络**将服务和资源配置分组，并连接到获授权的使用方。服务提供监听器、路由规则、目标组和服务 DNS 名称。

当前产品还通过资源网关连接**资源配置**，包括使用 TCP 的 RDS 数据库等资源。此资源访问模型与由目标组支持的 HTTP 服务不同；服务网络/服务 IAM 身份验证策略不授权资源配置流量。由 PrivateLink 提供支持的**服务网络 VPC 端点**可以让经对等连接、Transit Gateway、Direct Connect 或 VPN 到达的客户端进行访问。仅有直接 VPC 关联不会将访问扩展到中转网关或对等连接后的客户端。

典型用途包括跨账户应用 API、EKS 与其他计算服务之间的通信，以及共享数据资源访问。关联、路由、安全组、身份验证和应用授权仍需配置。

### 与其他服务比较

| 服务 | 主要职责 | 重要区别 |
|---|---|---|
| VPC Lattice | 私有应用和资源连接 | HTTP/HTTPS/gRPC 服务路由及独立的 TLS/TCP 资源能力；不是互联网 API 入口 |
| API Gateway | 托管 API 端点和 API 管理 | REST、HTTP 或 WebSocket API 的功能不同；GraphQL 不是独立的 API Gateway API 类型 |
| AWS App Mesh | 基于 Envoy 的服务网格 | AWS 将于 **2026-09-30** 终止支持；截至本次审查，该日期尚未到来。应规划迁移，而非全新安装 |
| Transit Gateway | 使用 IP 路由的网络连接 | 连接网络；不能替代各服务的 HTTP 路由和授权 |
| Istio / Linkerd / Cilium | 使用各自数据平面实现的网格能力 | 功能和运维成本不同。并非所有网格架构都必须使用 Sidecar |

VPC Lattice 免除了运维其托管数据平面的需要，但不承诺总成本更低或网格功能完全相同。应针对实际工作负载比较请求/数据/资源费用、控制器运维、身份要求、重试、路由功能和可观测性。参阅 [Istio–Lattice 比较](../service-mesh/istio/comparison/02-istio-vs-lattice.md)。

## 架构 {#architecture}

### 组件与流量流程

| 组件 | 职责 |
|---|---|
| 服务网络 | 逻辑分组和关联；可选的 IAM 授权边界 |
| 服务 | 具有自身 DNS 名称的应用端点 |
| 监听器和规则 | 属于**服务**；选择操作和目标组 |
| 目标组 | 已注册的实例、IP、Lambda 或 ALB 目标，行为因目标类型而异 |
| VPC 关联 | 允许关联 VPC 中的客户端在安全控制约束下访问网络 |
| 服务网络 VPC 端点 | 基于 PrivateLink 的访问，包括受支持的中转/本地网络路径 |
| 资源配置 / 资源网关 | 独立的资源访问模型，包括 TCP/数据库资源 |

![两个 AWS 账户中的三个 VPC 关联到一个服务网络，其服务使用目标组连接 EC2、EKS 和 Lambda 工作负载。](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

图中展示的是逻辑关联，而非单一路由器进程。访问还取决于网络可达性和适用策略。请求解析**服务的** DNS 名称，到达其监听器，通过适用的授权检查，再根据监听器规则路由到目标。目标组描述目的地，并非额外的应用跳点。

使用 `get-service --query dnsEntry` 或控制器的路由注解发现真实域名。不要根据服务名称和服务网络 ID 拼接域名。分配的名称包含服务专属标识符；重新创建服务可能改变该名称。

### 安全模型

网络访问、IAM 授权和加密是独立控制。`AWS_IAM` 要求受支持的签名请求和适当策略。`NONE` 在该特定层禁用 IAM 身份验证；它不会绕过另一层的 IAM 策略、安全组或应用授权。HTTPS 保护客户端到 Lattice 的流量。除非显式配置后端 TLS，否则后端 HTTP 仍为明文。

## EKS 与 VPC Lattice 集成 {#eks-and-vpc-lattice-integration}

AWS Gateway API Controller 将 Kubernetes 资源协调为 VPC Lattice 资源：

| Kubernetes 资源 | Lattice 中的含义 |
|---|---|
| GatewayClass | 选择 `application-networking.k8s.aws/gateway-api-controller` |
| Gateway | 通过 **Gateway 名称**引用服务网络，不包含命名空间 |
| HTTPRoute / GRPCRoute | 创建具有自身域名和监听器/路由配置的服务 |
| 后端 Service 及其端点 | 定义目标组和注册的 Pod 端点 |
| TargetGroupPolicy | 配置目标组的协议和健康检查 |
| IAMAuthPolicy | 将身份验证策略附加到 Gateway 的网络或 Route 的服务 |
| AccessLogPolicy | 配置目标资源的访问日志目的地 |

两个同名 Gateway 即使位于不同 Kubernetes 命名空间，也可能引用同一服务网络。仅创建 Gateway **不会**创建网络或一个共享入口 IP。网络可以由外部管理，简单场景下可使用控制器的 `defaultServiceNetwork` 选项，也可使用控制器的 ServiceNetwork CRD。为每个云资源选择一个管理方。

以下示例使用外部管理的网络和 VPC 关联。不设置 `defaultServiceNetwork`，也不为该关联附加 VpcAssociationPolicy。若采用基于 CRD 的模型，应将网络、VPC 关联和授权作为独立资源管理；不要再用 CloudFormation 管理同一批资源。

## 安装与配置 {#installation-and-configuration}

### 前提条件

控制器的 v2.1 升级指南要求 **Kubernetes 1.31 或更高版本**以及 Gateway API **1.5 或更高版本**。本示例固定到 v2.1 构建时使用的版本 **1.5.0**。此最低要求不是 EKS 支持矩阵，也不能证明与每个更新的 Gateway API 发布版本兼容。更改 Gateway API CRD 前，请检查 EKS 版本生命周期及所有共享这些 CRD 的控制器。尤其是 Gateway API 1.5 引入 TLSRoute 存储/API 转换后，v2.0 控制器可能失败。

使用受支持的 EKS 集群、匹配的 `kubectl`、Helm、AWS CLI v2，以及有权配置目标资源的操作员角色。示例后端假定使用 Linux Pod，且其 IP 可由 VPC Lattice 访问。请确认集群的 CNI、子网容量、端点就绪状态、DNS 和网络策略配置。

```bash
export AWS_REGION=us-west-2
export CLUSTER_NAME=my-cluster
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export VPC_ID="$(aws eks describe-cluster --name "$CLUSTER_NAME" \
  --query 'cluster.resourcesVpcConfig.vpcId' --output text)"
export NETWORK_NAME=my-network
export ASSOCIATION_SG_ID=sg-0123456789abcdef0
kubectl config current-context
kubectl version
```

替换示例安全组 ID。VPC 关联安全组必须允许**获准的客户端**访问 TCP 443。后端 Pod/节点安全组必须允许适用的 Lattice 托管前缀列表访问实际后端/健康检查端口，此处为 TCP 8080。检查真实 Pod ENI 或节点 ENI 上附加的安全组，不要假定每个节点都使用 EKS 集群安全组。还应允许 EKS 控制平面通过所需端口访问控制器 webhook。不要向整个互联网开放所有端口。

### IAM 角色设置

**控制器角色**管理云资源。**调用方角色**为应用请求签名，并需要 `vpc-lattice-svcs:Invoke`；两者是不同角色。

在受支持的节点上使用 EKS Pod Identity，或使用 IRSA。下方 IRSA 示例假定集群的 IAM OIDC 提供程序已存在，并创建专用服务账户。对于 Pod Identity，应使用当前 EKS 插件，为相同命名空间/服务账户创建关联，并配置适当的信任策略；不要在同一示例中同时依赖 IRSA 注解。

此发布版本推荐的控制器策略包含宽泛的 `vpc-lattice:*` 以及日志/标记权限。应将其视为上游起点，**而非最小权限策略**。审核资源范围和启用的功能，保留受限的服务相关角色条件，并在创建前保存审核后的策略。后续运行应复用现有已审核策略 ARN，避免创建重复策略。

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

现有服务账户需要有计划的所有权/角色迁移；示例不会自动覆盖它。

### 安装已发布的控制器

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

对于现有 Helm 发布，使用经过审核且包含已保存 values 的 `helm upgrade` 计划。Helm 不会自动升级 `crds/` 中的 CRD；请单独审核其更改。不要为了让升级通过而删除共享 Gateway API CRD 或准入策略。

对于基于清单的交付，使用 `helm template --include-crds` 渲染**同一个 chart**，采用相同 values 和服务账户选择，然后审核并应用生成的清单。这样可以保留发布版本的 RBAC、EndpointSlice 监视、领导者选举权限和 webhook 配置。不要使用过时的手写 v1.0 部署。除非显式提供证书或通过 cert-manager 选项管理，否则 chart 会生成 webhook 证书；升级期间应保持 webhook Secret 与 CA 捆绑包一致，不要单独重新生成其中之一。

### 创建服务网络

为同一网络选择 **CLI 或 CloudFormation**，不要同时使用两者。CLI 示例创建 `AWS_IAM` 网络。在适用的 Allow 策略安装并传播完成前，请求会被拒绝。

将以下内容保存为 `api-auth-policy.json`，替换账户和调用方角色。网络策略特意仅允许此演示的 `/api` 端点及子路径。生产网络需要审核过的策略，以覆盖预期服务和调用方。

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

```bash
aws vpc-lattice create-service-network --name "$NETWORK_NAME" \
  --auth-type AWS_IAM > service-network.json
export SERVICE_NETWORK_ID="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["id"])')"
export SERVICE_NETWORK_ARN="$(python3 -c \
  'import json; print(json.load(open("service-network.json"))["arn"])')"

aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ID" \
  --vpc-identifier "$VPC_ID" --security-group-ids "$ASSOCIATION_SG_ID"

# Save the reviewed policy below as api-auth-policy.json, then compact it.
python3 -c 'import json; print(json.dumps(json.load(open("api-auth-policy.json")),separators=(",",":")))' \
  > api-auth-policy.compact.json
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_NETWORK_ID" \
  --policy file://api-auth-policy.compact.json
aws vpc-lattice get-service-network --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
```

暴露路由前，验证关联为 `ACTIVE`、网络仍具有 `authType: AWS_IAM`，且 `get-auth-policy` 返回预期策略。策略传播可能需要几分钟。

等效的**网络和关联** CloudFormation 模板如下：

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: VPC Lattice service network and client VPC association
Parameters:
  NetworkName:
    Type: String
    Default: my-network
    MinLength: 3
    MaxLength: 63
    AllowedPattern: '^[a-z0-9]+(-[a-z0-9]+)*$'
    Description: Must match the Kubernetes Gateway name
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC containing the intended clients
  AssociationSecurityGroupIds:
    Type: List<AWS::EC2::SecurityGroup::Id>
    Description: Existing security groups allowing approved clients on listener ports
Resources:
  ServiceNetwork:
    Type: AWS::VpcLattice::ServiceNetwork
    Properties:
      Name: {Ref: NetworkName}
      AuthType: AWS_IAM
  ClientAssociation:
    Type: AWS::VpcLattice::ServiceNetworkVpcAssociation
    Properties:
      ServiceNetworkIdentifier: {Ref: ServiceNetwork}
      VpcIdentifier: {Ref: VpcId}
      SecurityGroupIds: {Ref: AssociationSecurityGroupIds}
Outputs:
  ServiceNetworkArn:
    Description: ARN used for authorization and sharing
    Value: {Fn::GetAtt: [ServiceNetwork, Arn]}
  ServiceNetworkId:
    Description: ID used with VPC Lattice API operations
    Value: {Fn::GetAtt: [ServiceNetwork, Id]}
```

此模板不附加身份验证策略。请在同一所有权模型中添加身份验证策略资源，或在测试请求前显式应用审核后的网络策略。从堆栈输出获取网络 ID/ARN。部署前验证模板并检查变更集；示例不创建 VPC 或其安全组。

### Gateway 和应用

将其保存为 `gateway.yaml` 并应用。Gateway 名称必须与上面创建的 `my-network` 匹配。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lattice-demo
---
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-network
  namespace: lattice-demo
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: unused
```

`certificateRefs: [{name: unused}]` 遵循此控制器文档中的配置：它满足 Gateway API TLS 配置要求，但此控制器不会在此读取 Kubernetes TLS Secret。没有自定义主机名时，Lattice 为生成的域名提供证书。这是**控制器专属行为**，并非可移植的证书管理方法。

将以下内容保存为 `stable.yaml`。它将 NGINX 配置为实际监听 8080 并提供 `/health`；仅声明 `containerPort` 不能实现其中任何一项。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-stable
  namespace: lattice-demo
data:
  nginx.conf: |
    worker_processes 1;
    pid /tmp/nginx.pid;
    error_log stderr notice;
    events { worker_connections 1024; }
    http {
        access_log /dev/stdout;
        default_type application/json;
        client_body_temp_path /tmp/client_temp;
        proxy_temp_path /tmp/proxy_temp;
        fastcgi_temp_path /tmp/fastcgi_temp;
        uwsgi_temp_path /tmp/uwsgi_temp;
        scgi_temp_path /tmp/scgi_temp;
        server {
            listen 8080;
            location = /health { return 200 '{"status":"ok"}\n'; }
            location = /api { return 200 '{"version":"stable"}\n'; }
            location /api/ { return 200 '{"version":"stable"}\n'; }
            location / { return 404 '{"error":"not found"}\n'; }
        }
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  replicas: 2
  selector:
    matchLabels: &id001
      app: lattice-demo
      version: stable
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: nginx:1.30.4-alpine@sha256:dc5069ad14f19660b141b21236140b91656bf89bbc3e2417c70ae650cd66104c
        command:
        - nginx
        args:
        - -c
        - /etc/lattice/nginx.conf
        - -g
        - daemon off;
        ports:
        - name: http
          containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: http
          periodSeconds: 5
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 250m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /etc/lattice
          readOnly: true
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: config
        configMap:
          name: service-stable
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: service-stable
  namespace: lattice-demo
spec:
  selector:
    app: lattice-demo
    version: stable
  ports:
  - name: http
    port: 8080
    targetPort: http
```

根据相同的三个对象创建 `canary.yaml`，将每个 `service-stable` 名称改为 `service-canary`，将选择器和模板中的两个 `version: stable` 标签改为 `version: canary`，并将 JSON 响应值 `"stable"` 改为 `"canary"`。保持 `app: lattice-demo`、端口和健康端点不变。在 `lattice-demo` 中应用两个文件。固定的镜像具有 Linux AMD64 和 ARM64 变体。资源请求和副本数是演示设置，并非测量得到的生产容量配置。

保存并应用以下 `TargetGroupPolicy`；创建针对 `service-canary` 的等效 `canary-health` 策略。

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

CRD 使用 `intervalSeconds`、`timeoutSeconds` 和 `statusMatch`。AWS CLI 使用不同字段名，后文会展示。更改协议/版本可能替换目标组；删除策略会还原其设置，包括默认 HTTP/HTTP1 行为。

## 服务管理 {#service-management}

### 通过 HTTPRoute 创建服务

将其保存为 `api-route.yaml`。同时将下面的 IAMAuthPolicy 保存为 `api-iam.yaml`。先应用应用程序和健康策略，再应用路由和身份验证策略。在协调过程创建并保护路由服务时，保持网络级 `AWS_IAM` 策略启用。

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

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: api-caller
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/api","/api/*"]}}}]}'
```

`spec.policy` 是 JSON **字符串**。此 CRD 在目标服务上启用 `AWS_IAM`；身份验证类型注解或包含策略的 ConfigMap 不能替代它。以 `Gateway` 为目标的策略会管理网络策略，因此本示例中不能让它与外部管理的网络策略争夺管理权。

检查 `Accepted` / `ResolvedRefs`、策略状态、相关 AWS 资源状态和后端就绪状态。`kubectl apply` 成功不能证明云资源协调或日志交付成功。

```bash
kubectl -n lattice-demo get gateway my-network -o yaml
kubectl -n lattice-demo get httproute api -o yaml
kubectl -n lattice-demo get iamauthpolicy api-caller -o yaml
kubectl -n lattice-demo get endpointslices \
  -l kubernetes.io/service-name=service-stable
kubectl -n lattice-demo rollout status deployment/service-stable --timeout=120s
kubectl -n lattice-demo rollout status deployment/service-canary --timeout=120s

export SERVICE_DNS="$(kubectl -n lattice-demo get httproute api \
  -o jsonpath='{.metadata.annotations.application-networking\.k8s\.aws/lattice-assigned-domain-name}')"
test -n "$SERVICE_DNS"
# A caller inside the associated VPC, with MyAppRole credentials, runs:
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

运行最后一条命令前，设置下一节中的签名客户端。使用**调用方角色**凭证，从获授权的网络位置运行它。工作站不仅需要 AWS 凭证，还需要适当的网络路径。

### 签名 HTTPS 客户端

将其保存为 `lattice_get.py`。它使用默认 AWS 凭证提供程序链，为每次请求冻结凭证，针对 **`vpc-lattice-svcs`** 签名，并按 VPC Lattice 要求设置 **`UNSIGNED-PAYLOAD`**。它验证 TLS，不会携带过期签名跟随重定向，也不会自动重试请求。

```python
import argparse
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import BotoCoreError
from botocore.session import Session


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def signed_request(url: str, region: str, credentials) -> Request:
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.fragment):
        raise ValueError("Use an HTTPS URL without user info or a fragment")
    request = AWSRequest(method="GET", url=url, headers={
        "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
    })
    request.context["payload_signing_enabled"] = False
    SigV4Auth(credentials, "vpc-lattice-svcs", region).add_auth(request)
    return Request(url, method="GET", headers=dict(request.headers.items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("url")
    args = parser.parse_args()
    try:
        provider = Session().get_credentials()
        if provider is None:
            raise ValueError("No AWS credentials available")
        request = signed_request(args.url, args.region, provider.get_frozen_credentials())
        opener = build_opener(NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(request, timeout=10) as response:
            print(response.status)
            print(response.read(1048576).decode("utf-8", errors="replace"))
        return 0
    except HTTPError as exc:
        print(f"HTTP {exc.code}; check the policy and access logs", file=sys.stderr)
    except (URLError, BotoCoreError, ValueError) as exc:
        print(f"Request failed: {type(exc).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

```bash
python3.12 -m venv lattice-client
lattice-client/bin/python -m pip install 'botocore==1.43.93'
lattice-client/bin/python lattice_get.py --region "$AWS_REGION" "https://${SERVICE_DNS}/api"
```

此仅支持 GET 的示例已使用 Python 3.12 和 botocore 1.43.93 检查。工作负载应使用已配置的 Pod Identity 或 IRSA 凭证。不要将静态凭证或签名标头复制到清单、日志或支持工单。VPC Lattice 也支持 SigV4A；本示例使用区域 SigV4。

### 直接 AWS API 管理

以下是独立管理资源的**替代方案**。使用可达且稳定的后端 IP，在 8080 上提供 HTTP 和 `/health`；临时 Pod IP 需要控制器跟踪替换。不要手动更改 HTTPRoute 拥有的服务并指望控制器保留更改。

```bash
# Separate API-managed example; do not use for controller-managed resources.
export TARGET_IP=10.0.1.25
export TARGET_GROUP_ID="$(aws vpc-lattice create-target-group \
  --name api-manual --type IP \
  --config "{\"port\":8080,\"protocol\":\"HTTP\",\"protocolVersion\":\"HTTP1\",\"vpcIdentifier\":\"${VPC_ID}\"}" \
  --query id --output text)"
aws vpc-lattice register-targets --target-group-identifier "$TARGET_GROUP_ID" \
  --targets "id=$TARGET_IP,port=8080"
export SERVICE_ID="$(aws vpc-lattice create-service \
  --name api-manual --auth-type AWS_IAM --query id --output text)"
aws vpc-lattice put-auth-policy --resource-identifier "$SERVICE_ID" \
  --policy file://api-auth-policy.compact.json
export LISTENER_ID="$(aws vpc-lattice create-listener \
  --service-identifier "$SERVICE_ID" --name https --protocol HTTPS --port 443 \
  --default-action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TARGET_GROUP_ID}\",\"weight\":1}]}}" \
  --query id --output text)"
aws vpc-lattice create-service-network-service-association \
  --service-identifier "$SERVICE_ID" --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID" --query dnsEntry
```

等待目标健康且关联激活后，再调用发现的 HTTPS 域名。此示例使用生成域名的 AWS 托管证书，并非自定义域名。

### 更新和删除服务

对于 Kubernetes 管理的资源，更改 Route、后端工作负载或策略清单，并验证协调。对于 API 管理的资源，使用相应更新 API 并检查结果状态。从响应中获取资源 ID，不要选择账户中的第一个服务。

移除前，识别所有使用方、网络关联、监听器/规则、目标组引用和所有权。按依赖顺序移除特定路由/服务关联和服务资源，然后移除不再使用的目标组。共享 Gateway/网络可能影响其他命名空间或账户。保留控制器，直至终结器处理和云资源清理完成；不要使用无差别删除。

**删除 IAMAuthPolicy 会先在目标上禁用 IAM 身份验证（`NONE`），再分离策略。** 这不是拒绝访问或安全回滚授权的方法。移除服务时保留限制性策略，并验证剩余网络/服务控制。

## 路由与流量管理 {#routing-and-traffic-management}

### 路径和标头匹配

上面的路由匹配 `/api` 及其路径子树。要添加显式的基于标头的金丝雀规则，请将**同一个** HTTPRoute 替换为：

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
      headers:
      - name: x-version
        value: canary
    backendRefs:
    - name: service-canary
      port: 8080
      weight: 1
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

控制器文档说明：路径匹配不区分大小写，每条规则允许一个方法匹配，最多五个标头匹配，不支持查询参数匹配。不要假定所有 Gateway API 过滤器或匹配均已实现。单独的 HTTPRoute 会创建另一个 Lattice 服务/域名，而不是自动为第一个服务添加规则。

### 加权路由

`backendRefs.weight: 90` 和 `10` 是原生 Gateway API 配置；无需加权路由注解。它们表示相对分布，不是十次请求的精确结果。提高金丝雀权重前，应在适当样本上验证两个版本的端点、健康状况、错误和延迟。

对于独立管理的 AWS 资源：

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

CLI 前缀匹配是词法前缀匹配；应单独审核其边界行为，不能等同于 Kubernetes `PathPrefix` 语义。路由匹配不是授权边界。不要用路径路由测试证明 IAM 策略覆盖所有规范化或编码后的路径变体。

### 健康检查

Kubernetes 示例使用 `TargetGroupPolicy`。等效的 API 更新如下：

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

健康检查根据阈值评估就绪状态；不保证可用性或零停机。HTTP1 目标组默认启用健康检查，而 HTTP2 需要显式考虑。gRPC 目标使用 HTTP1/HTTP2 健康检查，Lambda/ALB 目标类型有不同的健康检查行为。请检查当前目标类型文档，不要将 Pod 示例应用于所有目标。

## 安全与身份验证 {#security-and-authentication}

### 身份验证策略和调用方权限

`put-auth-policy` / `get-auth-policy` 管理调用授权。`put-resource-policy` 是另一种管理/共享 API。调用方应使用 **`vpc-lattice-svcs:Invoke`** 操作。

当网络和服务都使用 `AWS_IAM` 时，调用方身份策略和**两个**适用的身份验证策略都必须允许访问。显式 Deny 优先。一个资源上的 `NONE` 不会取消另一个资源的 IAM 要求。直接访问 Kubernetes ClusterIP/Pod IP 的流量绕过 Lattice 身份验证；应以适当的网络和应用控制保护这些路径。

`StringEquals` 不会将 `/api/*` 解释为通配符。示例使用 `StringLike`，同时包含 `/api` 和 `/api/*`。IAM 条件匹配及应用路径规范化可能不同于控制器路由。对于管理功能，优先使用仅限管理角色访问的专用服务，并保留应用授权；不要添加宽泛的通用 Allow 并假定路径通配符能保护所有别名。

### 跨账户访问

RAM 共享允许与共享实体建立关联；其本身不授予应用调用权限。网络/服务身份验证策略、调用方权限、关联安全组和网络路径仍须允许请求。

```bash
# Owner account: choose a verified account ID or the actual Organizations ARN.
export CONSUMER_ACCOUNT_ID=111122223333
aws ram create-resource-share --name lattice-network-share \
  --resource-arns "$SERVICE_NETWORK_ARN" --principals "$CONSUMER_ACCOUNT_ID"

# Consumer account: inspect invitations only when the sharing mode requires one.
aws ram get-resource-share-invitations
# After verifying the owner, resources, and intended permissions:
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn "$VERIFIED_INVITATION_ARN"

# Run with consumer credentials and that account's VPC/security group values.
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SERVICE_NETWORK_ARN" \
  --vpc-identifier "$CONSUMER_VPC_ID" \
  --security-group-ids "$CONSUMER_ASSOCIATION_SG_ID"
```

启用 Organizations 共享时，组织内使用方无需邀请即可获得访问权限。其他受支持的共享安排需要接受邀请。要与组织或 OU 共享，应使用 **Organizations 提供的真实 ARN**，其中包含管理账户标识符，不要用成员账户 ID 拼接。

所有者可以共享服务、网络和资源配置，不能将单个 IAM 角色作为 RAM 使用方。停止共享会阻止新关联，但**不会移除现有关联**。撤销访问时请显式审核现有关联。

### TLS 和自定义域名

示例 Gateway 仅暴露 HTTPS。对于自定义主机名，应使用该主机名创建服务，获取匹配的 ACM 证书，并将 DNS 配置为实际分配的域名。每个服务仅支持一个自定义域名，且服务创建后不能更改。

对于控制器，设置 HTTPRoute 的 `spec.hostnames` 和 Gateway 监听器的 `tls.options["application-networking.k8s.aws/certificate-arn"]`，或使用文档中的 ACM 发现功能。不要将私钥放入注解。ExternalDNS 自动化还需要其控制器、权限和 DNSEndpoint CRD；仅设置主机名不能证明 DNS 记录已存在。

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

面向客户端的 HTTPS 与后端 TLS 相互独立。设置 `protocol: HTTPS` 的后端 `TargetGroupPolicy` 还需要后端实际使用 TLS，以及兼容的 HTTPS 健康检查。VPC Lattice **不验证后端证书**；它加密连接，但不验证后端的证书身份。如果这符合预期设计，可使用独立的 TLSRoute/TLS 透传模型，并审核其功能限制。

## 监控与日志 {#monitoring-and-logging}

### CloudWatch 指标、仪表板和警报

服务指标使用 **`AWS/VpcLattice`** 命名空间：

| 指标 | 含义 / 统计量 |
|---|---|
| `TotalRequestCount` | 请求数；`Sum` |
| `HTTPCode_4XX_Count` | 4xx 响应数；`Sum` |
| `HTTPCode_5XX_Count` | 5xx 响应数；`Sum` |
| `RequestTime` | 请求持续时间，单位为**毫秒**；平均值或合适的百分位数 |

服务指标使用 `Service` 维度，可选配 `AvailabilityZone`；目标组指标使用 `TargetGroup`。`ServiceName=my-service` 这样的名称不能标识这些指标。发现实际维度值/维度集：

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

流量产生指标后，选择目标服务的**整个服务范围**维度数组，并保存为 `service-dimensions.json`。不要随意选择第一个结果，也不要混合可用区指标和聚合指标。对照所观察的服务验证标识符。使用以下内容构建 `dashboard.json`：

```python
import json
import os

dimensions = json.load(open("service-dimensions.json"))
if {d["Name"] for d in dimensions} != {"Service"}:
    raise ValueError("Select the service-wide metric, without AvailabilityZone")
pairs = [item for d in dimensions for item in (d["Name"], d["Value"])]
dashboard = {"widgets": [{
    "type": "metric", "width": 12, "height": 6,
    "properties": {
        "title": "VPC Lattice requests and errors",
        "region": os.environ["AWS_REGION"], "period": 60, "stat": "Sum",
        "metrics": [["AWS/VpcLattice", name, *pairs] for name in
                    ("TotalRequestCount", "HTTPCode_4XX_Count", "HTTPCode_5XX_Count")],
    },
}]}
with open("dashboard.json", "w") as output:
    json.dump(dashboard, output)
```

```bash
aws cloudwatch put-dashboard --dashboard-name VPCLattice \
  --dashboard-body file://dashboard.json
aws cloudwatch put-metric-alarm --alarm-name LatticeApi5xx \
  --namespace AWS/VpcLattice --metric-name HTTPCode_5XX_Count \
  --dimensions file://service-dimensions.json \
  --statistic Sum --period 60 --evaluation-periods 3 --datapoints-to-alarm 2 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --treat-missing-data missing
```

该警报表示**三个周期中有两个周期每分钟 5xx 响应超过五次**，并非 5% 错误率。如果需要通知，请单独配置审核过的警报操作。缺失数据的处理方式是显式选择的：指标在流量开始后才发布，不能默默将 NoData 视为健康证明。仪表板和警报设置只是示例，并非工作负载专属 SLO。

### 访问日志

对于 CloudWatch Logs，使用现有目的地，或创建带保留策略的专用日志组：

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

执行设置的主体还需要文档规定的日志交付权限。当其具有必要权限时，AWS 可以创建/更新日志资源策略；否则应预先配置。验证 `delivery.logs.amazonaws.com` 权限及源账户/源 ARN 条件。

对于 Kubernetes 管理的路由，使用以下配置，**替代**与之争夺管理权的 CLI 创建订阅：

```yaml
apiVersion: application-networking.k8s.aws/v1alpha1
kind: AccessLogPolicy
metadata:
  name: api-logs
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api
  destinationArn: arn:aws:logs:us-west-2:123456789012:log-group:/aws/vendedlogs/vpc-lattice/api:*
```

替换 ARN，并确认策略状态和实际交付的事件。策略可将 Gateway 作为目标获取网络日志，或将 Route 作为目标获取服务日志。对于每个目标，每种受支持的目的地类型可有一个目的地。

对于 S3，使用经过审核的目标桶，配置阻止公有访问、加密、保留/生命周期规则和适当的交付权限：

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

S3 交付要求为 `delivery.logs.amazonaws.com` 配置文档规定的 `s3:GetBucketAcl` 和 `s3:PutObject` 权限、交付前缀、`aws:SourceAccount` 和 `aws:SourceArn` 条件。现有策略必须合并，不能覆盖。SSE-KMS 需要受支持的客户托管密钥及其交付密钥策略。`--destination-name` 不是访问日志订阅参数。

### 日志分析和追踪

HTTP 服务访问日志包含 `sourceIpPort`、`requestMethod`、`requestPath`、`responseCode`、`durationMS`、`callerPrincipal` 和 `authDeniedReason` 等字段。资源/TCP 日志具有不同模式。

```bash
END_TIME="$(python3 -c 'import time; print(int(time.time()))')"
START_TIME="$((END_TIME - 3600))"
QUERY_ID="$(aws logs start-query --log-group-name "$LOG_GROUP" \
  --start-time "$START_TIME" --end-time "$END_TIME" \
  --query-string 'fields @timestamp, sourceIpPort, requestMethod, requestPath, responseCode, durationMS, callerPrincipal, authDeniedReason | filter responseCode >= 400 | sort @timestamp desc | limit 100' \
  --query queryId --output text)"
aws logs get-query-results --query-id "$QUERY_ID"
# Repeat get-query-results until Complete; Failed/Cancelled/Timeout are errors.
```

VPC Lattice 没有 `update-service --tracing-config` 选项，也没有能自动为应用添加 X-Ray 插桩的控制器注解。应使用 OpenTelemetry/ADOT 或适当的追踪 SDK 为应用插桩，传播追踪上下文，并配置导出/采样。将应用追踪与访问日志和请求 ID 关联；客户端提供的请求 ID 不是经过验证的身份。

## 最佳实践 {#best-practices}

- **设计和所有权：** 使用明确的网络/服务命名和环境边界。考虑跨命名空间的同名 Gateway、共享网络使用方、配额，以及每个策略和关联的所有权。
- **部署：** 保持稳定版和金丝雀后端可独立选择。调整权重前检查端点、目标健康状况和授权。记录回滚标准并保留最近已知的配置。
- **性能：** 使用有界超时和适当的连接复用。让健康端点轻量且有意义。仅在应用语义允许时缓存或批处理。私有 Lattice 服务不会仅因启用缓存就变成 CDN 源站。
- **安全：** 分离管理和调用方角色；不要将凭证放入清单。测试允许和拒绝的角色、根路径和子路径、直接后端访问及 TLS 行为。不要通过删除 IAM 策略 CRD 来拒绝流量。
- **可观测性：** 分别监控请求数、错误数/率、延迟、目标健康状况和缺失遥测。按要求保留访问日志，并显式为应用追踪插桩。
- **成本：** 审核所选模型在当前区域的服务/资源、请求、数据处理、端点和日志费用。使用标签，仅移除确认未使用的资源，并将后端自动扩缩容容量规划与托管 Lattice 数据平面分开。

## 故障排除 {#troubleshooting}

使用控制器注解/状态和 AWS 清单中的标识符。不要假定直接 API 示例中的 `$SERVICE_ID` 就是 Kubernetes 路由的服务。

```bash
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice list-service-network-service-associations \
  --service-network-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-service --service-identifier "$SERVICE_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_NETWORK_ID"
aws vpc-lattice get-auth-policy --resource-identifier "$SERVICE_ID"
aws vpc-lattice list-listeners --service-identifier "$SERVICE_ID"
aws vpc-lattice list-rules --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID"
aws vpc-lattice get-target-group --target-group-identifier "$TARGET_GROUP_ID"
aws vpc-lattice list-targets --target-group-identifier "$TARGET_GROUP_ID"
```

| 症状 | 检查项 |
|---|---|
| DNS/连接失败 | 实际分配的 DNS、客户端 VPC 关联或端点路径、关联状态、安全组、NACL、Pod 可达性 |
| 403/身份验证失败 | 调用方角色、凭证过期及签名区域/服务、`UNSIGNED-PAYLOAD`、两个身份验证层、传播、拒绝原因日志字段 |
| 路由或版本错误 | Route 条件、监听器/规则优先级和匹配、目标组成员、权重、不同 Route 的域名 |
| 目标不健康 | 实际监听端口、`/health`、HTTP 与 HTTPS、就绪状态、安全组、目标类型和健康检查阈值 |
| 无日志/指标 | 目的地权限和交付状态、正确的指标维度、初始流量、保留策略、查询状态 |
| 控制器协调失败 | `manager` 日志、IAM 角色、EndpointSlice、CRD 版本兼容性、webhook 和领导者选举状态 |

使用有界指标时间区间，不依赖仅 GNU 支持的 `date -d`：

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

发生 AWS 服务事件时，查询 AWS Health 和相关账户事件。账户专属 API 访问和支持操作取决于适用计划和端点。支持案例应包含审核后的资源 ID、时间范围、故障症状和脱敏日志。为账户选择当前服务/类别/严重性选项；不要粘贴硬编码的 `urgent` 案例创建命令。

## 参考资料 {#references}

- [VPC Lattice 概述](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [服务网络关联](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [控制器 v2.1.3 安装](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [控制器 v2.1 升级要求](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [控制器 API 参考](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [控制器 HTTPS 和后端 TLS](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [VPC Lattice 身份验证策略](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [请求签名](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [共享实体](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [CloudWatch 指标](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [访问日志](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [CloudWatch Logs 交付权限](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [S3 交付权限](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## 测验

通过 [VPC Lattice 测验](../quizzes/networking/02-vpc-lattice-quiz.md)检验您的理解。
