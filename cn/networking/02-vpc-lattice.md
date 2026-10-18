# VPC Lattice

Amazon VPC Lattice 可连接跨 VPC 和 AWS 账户的应用程序。本章介绍其资源模型、EKS 集成、路由、IAM 授权、监控和故障排除。

> **最后更新**：2026 年 9 月 11 日，依据 AWS Gateway API Controller **v2.1.3** 和 Gateway API **v1.5.0**。示例介绍配置和验证步骤；本次审查未在 AWS 账户中部署这些示例。

## 目录

- [概述](#overview)
- [架构](#architecture)
- [EKS 和 VPC Lattice 集成](#eks-and-vpc-lattice-integration)
- [安装和配置](#installation-and-configuration)
- [Service 管理](#service-management)
- [路由和流量管理](#routing-and-traffic-management)
- [安全和身份验证](#security-and-authentication)
- [监控和日志记录](#monitoring-and-logging)
- [最佳实践](#best-practices)
- [故障排除](#troubleshooting)
- [参考资料](#references)

## 概述 {#overview}

### 什么是 VPC Lattice？

VPC Lattice 提供应用程序网络连接，无需在每个应用程序旁边运行代理。**服务网络**将服务和资源配置归组，并将其连接到已授权的使用方。Service 提供监听器、路由规则、目标组和 Service DNS 名称。

当前产品还通过资源网关连接**资源配置**，包括使用 TCP 的 RDS 数据库等资源。这种资源访问模型不同于由目标组支持的 HTTP Service；Service Network/Service IAM auth policy 不会授权资源配置流量。由 PrivateLink 提供支持的**服务网络 VPC endpoint**可为通过对等连接、Transit Gateway、Direct Connect 或 VPN 访问的客户端提供访问能力。仅关联 VPC 并不能将访问范围扩展到 Transit Gateway 或对等连接后面的客户端。

典型用途包括跨账户应用程序 API、EKS 与其他计算服务之间的通信，以及共享数据资源访问。关联、路由、安全组、身份验证和应用程序授权仍需要配置。

### 与其他服务的比较

| 服务 | 主要职责 | 重要区别 |
|---|---|---|
| VPC Lattice | 私有应用程序和资源连接 | HTTP/HTTPS/gRPC Service 路由，以及独立的 TLS/TCP 资源功能；不是面向 Internet 的 API 入口 |
| API Gateway | 托管 API 端点和 API 管理 | REST、HTTP 或 WebSocket API 的功能各不相同；GraphQL 不是独立的 API Gateway API 类型 |
| AWS App Mesh | 基于 Envoy 的服务网格 | AWS 支持已于 **2026-09-30** 结束；控制台和资源已不再可访问。迁移现有部署；不要用于新安装 |
| Transit Gateway | 使用 IP 路由实现网络连接 | 连接网络；不能替代按 Service 进行的 HTTP 路由和授权 |
| Istio / Linkerd / Cilium | 通过各自的数据平面实现的网格功能 | 功能和运维成本各不相同。并非所有网格架构都必须使用 sidecar |

VPC Lattice 无需你运维其托管数据平面，但不保证总成本更低，也不保证提供相同的网格功能。请根据实际工作负载比较请求/数据/资源费用、Controller 运维、身份要求、重试、路由功能和可观测性。请参阅 [Istio–Lattice 比较](../service-mesh/istio/comparison/02-istio-vs-lattice.md)。

## 架构 {#architecture}

### 组件和流量流向

| 组件 | 职责 |
|---|---|
| Service network | 逻辑分组和关联；可选的 IAM 授权边界 |
| Service | 具有自身 DNS 名称的应用程序端点 |
| Listener 和规则 | 属于一个 **Service**；选择操作和目标组 |
| Target group | 已注册的实例、IP、Lambda 或 ALB 目标，并具有特定于目标类型的行为 |
| VPC association | 允许关联 VPC 中的客户端访问网络，但仍受安全控制约束 |
| Service network VPC endpoint | 基于 PrivateLink 的访问，包括受支持的传输网络/本地路径 |
| Resource configuration / resource gateway | 独立的资源访问模型，包括 TCP/数据库资源 |

![两个 AWS 账户中的三个 VPC 与一个服务网络关联，该网络中的服务使用目标组连接 EC2、EKS 和 Lambda 工作负载。](../.gitbook/assets/en-networking-02-vpc-lattice-1.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-02-vpc-lattice-1.html)

图中展示的是逻辑关联，而不是单个路由器进程。访问还取决于网络可达性和适用的策略。请求会解析 **Service 的** DNS 名称，到达其 Listener，通过适用的授权检查，然后根据 Listener 规则路由到目标。Target group 描述的是目的地；它不是另一个应用程序跳点。

使用 `get-service --query dnsEntry` 或 Controller 的路由注解来发现真实域名。不要根据 Service 名称和 Service Network ID 拼接域名。分配的名称包含特定于 Service 的标识符；重新创建 Service 后，域名可能会改变。

### 安全模型

网络访问、IAM 授权和加密是不同的控制措施。`AWS_IAM` 要求使用受支持的签名请求和相应策略。`NONE` 会在特定层禁用 IAM 身份验证；它不会绕过其他层的 IAM policy、安全组或应用程序授权。HTTPS 保护客户端到 Lattice 的流量。除非明确配置后端 TLS，否则后端 HTTP 流量仍为明文。

## EKS 和 VPC Lattice 集成 {#eks-and-vpc-lattice-integration}

AWS Gateway API Controller 会将 Kubernetes 资源协调为 VPC Lattice 资源：

| Kubernetes 资源 | Lattice 中的含义 |
|---|---|
| GatewayClass | 选择 `application-networking.k8s.aws/gateway-api-controller` |
| Gateway | 通过 **Gateway 名称**引用 Service Network，不包含其 namespace |
| HTTPRoute / GRPCRoute | 创建一个具有独立域名和 Listener/路由配置的 Service |
| Backend Service 及其端点 | 定义目标组和已注册的 Pod 端点 |
| TargetGroupPolicy | 配置目标组的协议和运行状况检查 |
| IAMAuthPolicy | 将 auth policy 附加到 Gateway 的网络或 Route 的 Service |
| AccessLogPolicy | 配置目标资源的访问日志目的地 |

即使 Kubernetes namespace 不同，具有相同名称的两个 Gateway 也可以引用同一个 Service Network。单独的 Gateway **不会**创建网络，也不会创建一个共享的入口 IP。网络可以在外部管理；简单场景可以使用 Controller 的 `defaultServiceNetwork` 选项，也可以使用 Controller 的 ServiceNetwork CRD。每个云资源应指定一个管理方。

以下示例使用外部管理的网络和 VPC association。示例未设置 `defaultServiceNetwork`，也未将 VpcAssociationPolicy 附加到该 association。如果采用基于 CRD 的模型，请将网络、VPC association 和授权作为单独资源管理；不要同时使用 CloudFormation 管理相同资源。

## 安装和配置 {#installation-and-configuration}

### 先决条件

Controller 的 v2.1 升级指南要求使用 **Kubernetes 1.31 或更高版本**以及 Gateway API **1.5 或更高版本**。此示例固定使用 v2.1 构建时所依据的版本 **1.5.0**。此最低版本要求不代表 EKS 支持矩阵，也不能证明与所有较新版本的 Gateway API 兼容。更改前，请检查 EKS 版本生命周期以及共享 Gateway API CRD 的所有 Controller。特别是，引入 Gateway API 1.5 后发生 TLSRoute 存储/API 过渡，可能导致 v2.0 Controller 无法正常运行。

请使用受支持的 EKS 集群、匹配的 `kubectl`、Helm、AWS CLI v2，以及有权配置目标资源的操作员角色。示例后端假定 Linux Pod 具有可由 VPC Lattice 访问的 IP。请确认集群的 CNI、子网容量、端点就绪状态、DNS 和网络策略配置。

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

请替换示例安全组 ID。VPC association 安全组必须允许**已批准的客户端**通过 TCP 443 访问。后端 Pod/节点安全组必须允许适用的 Lattice 托管前缀列表通过实际后端/运行状况检查端口访问；此处为 TCP 8080。请检查附加到实际 Pod ENI 或节点 ENI 的安全组，不要假设每个节点都使用 EKS 集群安全组。此外，还要允许 EKS 控制平面通过所需端口访问 Controller webhook。不要向整个 Internet 开放所有端口。

### IAM 角色设置

**Controller 角色**负责管理云资源。**调用方角色**负责对应用程序请求签名，并需要 `vpc-lattice-svcs:Invoke` 权限；这是两个不同的角色。

在受支持的节点上使用 EKS Pod Identity，或使用 IRSA。以下 IRSA 示例假定集群的 IAM OIDC provider 已存在，并创建专用 ServiceAccount。对于 Pod Identity，请使用当前 EKS add-on，并为同一个 namespace/ServiceAccount 创建 association，同时配置相应的信任策略；不要在此示例中同时依赖 IRSA 注解。

此版本推荐的 Controller policy 包含范围较广的 `vpc-lattice:*` 和日志/标记权限。应将其视为上游起点，**而非最小权限策略**。请审查其资源范围和已启用功能，保留受限的 service-linked-role 条件，并在创建前保存审查后的策略。后续运行时，请重复使用现有且经过审查的 policy ARN，而不是创建重复策略。

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

现有 ServiceAccount 需要有计划地迁移所有权/角色；此示例不会自动覆盖它。

### 安装已发布的 Controller

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

对于现有 Helm release，请使用经过审查且包含已保存 values 的 `helm upgrade` 计划。Helm 不会自动升级 `crds/` 中的 CRD；请单独审查其更改。不要为了让升级通过而移除共享 Gateway API CRD 或准入策略。

如果采用基于 manifest 的交付方式，请使用相同的 values 和 ServiceAccount 选择，通过 `helm template --include-crds` 渲染**同一个 chart**，然后审查并应用生成的 manifest。这样可以保留已发布版本中的 RBAC、EndpointSlice 监视、Leader 选举权限和 webhook 配置。不要使用过时的手写 v1.0 Deployment。除非显式提供证书或通过其 cert-manager 选项管理证书，否则 chart 会生成 webhook 证书；升级期间请保持 webhook Secret 和 CA bundle 一致，不要单独重新生成其中一项。

### 创建 Service Network

请选择 **CLI 或 CloudFormation**，不要同时使用两者管理同一个网络。CLI 示例会创建一个 `AWS_IAM` 网络。在适用的 Allow policy 安装并传播之前，请求会被拒绝。

将以下内容保存为 `api-auth-policy.json`，并替换账户和调用方角色。网络 policy 有意只允许此演示的 `/api` 端点及其子路径。生产网络需要经过审查的策略，以覆盖预期的 Service 和调用方。

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

在公开路由前，请确认 association 状态为 `ACTIVE`、网络仍具有 `authType: AWS_IAM`，并且 `get-auth-policy` 返回预期策略。策略传播可能需要几分钟。

等效的**网络和 association** CloudFormation 模板如下：

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

此模板不会附加 auth policy。请在相同的所有权模型中添加 auth-policy 资源，或者在测试请求前显式应用经过审查的网络 policy。请从 stack outputs 获取网络 ID/ARN。验证模板并在部署前检查 change set；此示例不会创建 VPC 或其安全组。

### Gateway 和应用程序

将以下内容保存并应用为 `gateway.yaml`。Gateway 名称必须与上面创建的 `my-network` 匹配。

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

`certificateRefs: [{name: unused}]` 符合此 Controller 记录的配置方式：它满足 Gateway API TLS 配置要求，但此 Controller 不会在此处读取 Kubernetes TLS Secret。未配置自定义主机名时，Lattice 会为其生成的域名提供证书。这是**特定于 Controller 的配置**，不是可移植的证书管理方案。

将以下内容保存并应用为 `stable.yaml`。它会配置 NGINX 实际监听 8080 并提供 `/health`；单独声明 `containerPort` 并不能实现这两点。

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
        image: nginx:1.30.6-alpine@sha256:970364228b1e4f932abc22d321932816782cca8a20b85a77552a7cfe9acfb3b5
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

根据相同的三个对象创建 `canary.yaml`，将所有 `service-stable` 名称改为 `service-canary`，将 selector/template 中的 `version: stable` 标签改为 `version: canary`，并将 JSON 响应值 `"stable"` 改为 `"canary"`。保留 `app: lattice-demo`、端口和运行状况检查端点不变。在 `lattice-demo` 中应用这两个文件。固定的镜像包含 Linux AMD64 和 ARM64 变体。资源请求和副本数只是演示设置，并非经生产环境测量得出的容量配置。

保存并应用以下 `TargetGroupPolicy`；再创建一个目标为 `service-canary` 的等效 `canary-health` policy。

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

CRD 使用 `intervalSeconds`、`timeoutSeconds` 和 `statusMatch`。AWS CLI 使用不同的字段名称，稍后会展示。更改协议/版本可能会替换目标组；删除 policy 会恢复其设置，包括默认的 HTTP/HTTP1 行为。

## Service 管理 {#service-management}

### 通过 HTTPRoute 创建 Service

将以下内容保存为 `api-route.yaml`。同时将下面的 IAMAuthPolicy 保存为 `api-iam.yaml`。先应用应用程序和运行状况策略，然后应用路由和 auth policy。在协调过程创建并保护该路由的 Service 期间，请保持网络级 `AWS_IAM` policy 处于启用状态。

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

`spec.policy` 是一个 JSON **字符串**。此 CRD 会在目标 Service 上启用 `AWS_IAM`；auth-type 注解或包含 policy 的 ConfigMap 不能替代它。若 policy 的目标是 `Gateway`，则管理的是网络的 policy，因此不能让它与此示例中外部管理的网络 policy 相冲突。

请检查 `Accepted` / `ResolvedRefs` 和 policy 状态、相关 AWS 资源状态以及后端就绪情况。`kubectl apply` 成功并不能证明云资源协调或日志交付成功。

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

运行最后一条命令前，请先在下一节设置签名客户端。请使用**调用方角色**凭证，从已授权的网络位置运行。你的工作站除了需要 AWS 凭证之外，还需要适当的网络路径。

### 已签名的 HTTPS 客户端

将以下内容保存为 `lattice_get.py`。它使用默认 AWS 凭证提供程序链，为每个请求固定凭证，针对 **`vpc-lattice-svcs`** 签名，并按 VPC Lattice 要求设置 **`UNSIGNED-PAYLOAD`**。它会验证 TLS，不会使用过期签名跟随重定向，也不会自动重试请求。

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

此示例仅发送 GET 请求，并已使用 Python 3.12 和 botocore 1.43.93 检查。工作负载应使用其配置的 Pod Identity 或 IRSA 凭证。不要将静态凭证或签名标头复制到 manifest、日志或支持工单中。VPC Lattice 也支持 SigV4A；此示例使用区域性 SigV4。

### 直接 AWS API 管理

以下是用于独立管理资源的**替代方案**。请使用可访问且稳定的后端 IP，该地址通过 HTTP 8080 提供服务并支持 `/health`；临时 Pod IP 需要 Controller 跟踪其替换情况。不要手动更改由 HTTPRoute 管理的 Service，并期望 Controller 保留此更改。

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

调用已发现的 HTTPS 域名前，请等待目标运行状况正常且 association 处于活动状态。此示例对生成的域名使用 AWS 托管证书，而非自定义域名。

### 更新和删除 Service

对于由 Kubernetes 管理的资源，请更改 Route、后端工作负载或 policy manifest，并验证协调结果。对于由 API 管理的资源，请使用相应的更新 API 并检查其最终状态。从响应中记录资源 ID，不要选择账户中的第一个 Service。

删除之前，请确认所有使用方、网络关联、Listener/规则、目标组引用和资源所有权。按依赖顺序删除特定 Route/Service association 和 Service 资源，然后删除不再使用的目标组。共享的 Gateway/network 可能会影响其他 namespace 或账户。请保留 Controller，直到 finalizer 和云端清理完成；不要执行不加区分的批量删除。

**删除 IAMAuthPolicy 会在解除 policy 附加前禁用其目标上的 IAM 身份验证 (`NONE`)。这不是拒绝访问或安全回滚授权的方式**。删除 Service 时请保留限制性 policy，并验证剩余的网络/Service 控制措施。

## 路由和流量管理 {#routing-and-traffic-management}

### 路径和标头匹配

上面的路由会匹配 `/api` 及其路径子树。若要添加明确的基于标头的 canary 规则，请将**同一个** HTTPRoute 替换为：

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

Controller 文档说明路径匹配不区分大小写、每条规则最多有一个方法匹配、最多有五个标头匹配，并且不支持查询参数匹配。不要假定每个 Gateway API filter 或匹配方式都已实现。单独的 HTTPRoute 会创建另一个 Lattice Service/域名，而不会自动向第一个 Service 添加规则。

### 加权路由

`backendRefs.weight: 90` 和 `10` 是原生 Gateway API 配置；不需要加权路由注解。它们表示相对流量分布，并不意味着十个请求会得到精确结果。增加 canary 权重前，请在适当的样本规模下验证两个版本的端点、运行状况、错误和延迟。

对于独立管理的 AWS 资源：

```bash
# TG_STABLE and TG_CANARY are existing target groups managed by this API workflow.
aws vpc-lattice create-rule --service-identifier "$SERVICE_ID" \
  --listener-identifier "$LISTENER_ID" --name api-canary --priority 10 \
  --match '{"httpMatch":{"pathMatch":{"match":{"prefix":"/api"},"caseSensitive":false}}}' \
  --action "{\"forward\":{\"targetGroups\":[{\"targetGroupIdentifier\":\"${TG_STABLE}\",\"weight\":90},{\"targetGroupIdentifier\":\"${TG_CANARY}\",\"weight\":10}]}}"
```

CLI 前缀匹配是词法前缀；请单独检查其边界行为与 Kubernetes `PathPrefix` 语义的差异。路由匹配不是授权边界。不要将路径路由测试当作 IAM policy 覆盖所有规范化或编码路径变体的证明。

### 运行状况检查

Kubernetes 示例使用 `TargetGroupPolicy`。等效的 API 更新如下：

```bash
aws vpc-lattice update-target-group --target-group-identifier "$TARGET_GROUP_ID" \
  --health-check '{"enabled":true,"protocol":"HTTP","protocolVersion":"HTTP1","port":8080,"path":"/health","healthCheckIntervalSeconds":30,"healthCheckTimeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}'
```

运行状况检查会根据阈值评估就绪状态；它不能保证可用性或零停机。HTTP1 目标组默认启用运行状况检查，而 HTTP2 需要显式考虑。gRPC 目标使用 HTTP1/HTTP2 运行状况检查，Lambda/ALB 目标类型则具有不同的运行状况检查行为。请查看当前的目标类型文档，不要将 Pod 示例套用到所有目标。

## 安全和身份验证 {#security-and-authentication}

### Auth policy 和调用方权限

`put-auth-policy` / `get-auth-policy` 用于管理调用授权。`put-resource-policy` 是用于管理/共享的不同 API。调用方应使用 **`vpc-lattice-svcs:Invoke`** 操作。

如果网络和 Service 都使用 `AWS_IAM`，则调用方的身份 policy 和**两个**适用的 auth policy 都必须允许访问。显式 Deny 优先。一个资源上的 `NONE` 不会取消另一个资源的 IAM 要求。直接访问 Kubernetes ClusterIP/Pod IP 的流量会绕过 Lattice auth；请使用适当的网络和应用程序控制措施保护这些路径。

`StringEquals` 不会将 `/api/*` 解释为通配符。示例使用 `StringLike`，并同时包含 `/api` 和 `/api/*`。IAM 条件匹配与应用程序路径规范化可能不同于 Controller 路由。对于管理功能，建议使用仅限管理角色访问的专用 Service，并保留应用程序授权；不要添加宽泛的通用 Allow，然后假定路径通配符能保护所有别名。

### 跨账户访问

RAM 共享允许与共享实体建立 association；其本身不会授予应用程序调用权限。网络/Service auth policy、调用方权限、association 安全组和网络路径仍必须允许请求。

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

启用 Organizations 共享后，组织内部的使用方无需邀请即可获得访问权限。其他受支持的共享安排则需要接受邀请。若要与组织或 OU 共享，请使用 Organizations 中的**实际 ARN**，其中应包含管理账户标识符；不要根据成员账户 ID 拼接 ARN。

所有者可以共享 Service、网络和资源配置，但不能将单个 IAM 角色作为 RAM 使用方共享。停止共享会阻止建立新的 association，**但不会移除现有 association**。撤销访问权限时，请明确检查并处理现有 association。

### TLS 和自定义域名

示例 Gateway 只公开 HTTPS。若要使用自定义主机名，请创建带有该主机名的 Service，获取匹配的 ACM 证书，并将 DNS 配置为指向实际分配的域名。每个 Service 只支持一个自定义域名，并且创建 Service 后无法更改。

对于 Controller，请设置 HTTPRoute 的 `spec.hostnames` 和 Gateway Listener 的 `tls.options["application-networking.k8s.aws/certificate-arn"]`，或使用其记录的 ACM 发现功能。不要将私钥放入注解中。ExternalDNS 自动化还需要其 Controller、权限和 DNSEndpoint CRD；仅设置主机名并不能证明 DNS 记录已创建。

```bash
# For an API-managed service created with the required custom domain name:
aws vpc-lattice update-service --service-identifier "$SERVICE_ID" \
  --certificate-arn "$ACM_CERTIFICATE_ARN"
# Create an HTTPS listener separately if the service does not already have one.
# create-listener uses --protocol HTTPS; there is no --tls mode=STRICT option.
```

面向客户端的 HTTPS 和后端 TLS 是两项独立配置。使用 `protocol: HTTPS` 的后端 `TargetGroupPolicy` 还要求后端实际使用 TLS，并且配置兼容的 HTTPS 运行状况检查。VPC Lattice **不会验证后端证书**；此配置可以加密连接，但不会验证后端证书的身份。若这是预期设计，请使用独立的 TLSRoute/TLS passthrough 模型，并审查其功能限制。

## 监控和日志记录 {#monitoring-and-logging}

### CloudWatch 指标、控制面板和警报

Service 指标使用 **`AWS/VpcLattice`** namespace：

| 指标 | 含义/统计数据 |
|---|---|
| `TotalRequestCount` | 请求数；`Sum` |
| `HTTPCode_4XX_Count` | 4xx 响应数；`Sum` |
| `HTTPCode_5XX_Count` | 5xx 响应数；`Sum` |
| `RequestTime` | 请求持续时间，单位为**毫秒**；平均值或适当的百分位数 |

Service 指标使用 `Service` dimension，也可以包含 `AvailabilityZone`；目标组指标使用 `TargetGroup`。`ServiceName=my-service` 这样的名称不能标识这些指标。请发现实际的 dimension 值/集合：

```bash
aws cloudwatch list-metrics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions Name=Service > metrics.json
python3 - <<'PY'
import json
for metric in json.load(open("metrics.json"))["Metrics"]:
    print(json.dumps(metric["Dimensions"]))
PY
```

产生流量并生成指标后，请选择目标 Service 的**Service 全局** dimension 数组并保存为 `service-dimensions.json`。不要随意选择第一个结果，也不要将 AZ 指标与汇总指标混用。请对照被观测的 Service 验证标识符。通过以下内容构建 `dashboard.json`：

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

此警报表示**每分钟 5xx 响应数超过五次，且在三个周期中的两个周期内达到此条件**，并不表示错误率为 5%。如果需要通知，请单独配置经过审查的警报操作。缺失数据选项是显式指定的：流量开始后才会发布指标，不能将 NoData 默默视为运行正常的证明。控制面板和警报设置仅为示例，并非针对特定工作负载的 SLO。

### 访问日志

对于 CloudWatch Logs，请使用现有目的地，或创建具有保留策略的专用日志组：

```bash
export LOG_GROUP=/aws/vendedlogs/vpc-lattice/api
aws logs create-log-group --log-group-name "$LOG_GROUP"
aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
export LOG_DESTINATION_ARN="arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:${LOG_GROUP}:*"

# API-managed service only; for an HTTPRoute use AccessLogPolicy below instead.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_DESTINATION_ARN"
```

设置主体还需要文档中列出的日志交付权限。如果设置主体拥有必要权限，AWS 可以创建/更新日志资源策略；否则请预先配置。请验证 `delivery.logs.amazonaws.com` 权限以及 source-account/source-ARN 条件。

对于 Kubernetes 管理的 Route，请使用以下配置，**而不要**另外创建可能发生冲突的 CLI 订阅：

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

替换 ARN，并确认 policy 状态和实际交付的事件。policy 可以将 Gateway 作为目标以记录网络日志，也可以将 Route 作为目标以记录 Service 日志。每种受支持的目标类型只能有一个对应目的地。

对于 S3，请使用经过审查的目标存储桶，并配置 Block Public Access、加密、保留/生命周期规则和适当的交付权限：

```bash
# Existing reviewed destination bucket; no policy is overwritten by this snippet.
aws vpc-lattice create-access-log-subscription \
  --resource-identifier "$SERVICE_ID" --destination-arn "$LOG_BUCKET_ARN"
```

S3 交付需要为 `delivery.logs.amazonaws.com` 配置文档中所述的 `s3:GetBucketAcl` 和 `s3:PutObject` 权限、交付前缀、`aws:SourceAccount` 和 `aws:SourceArn` 条件。必须合并现有策略，不得覆盖。SSE-KMS 需要使用受支持的客户管理密钥及其交付密钥策略。`--destination-name` 不是 access-log-subscription 参数。

### 日志分析和跟踪

HTTP Service 访问日志包含 `sourceIpPort`、`requestMethod`、`requestPath`、`responseCode`、`durationMS`、`callerPrincipal` 和 `authDeniedReason` 等字段。资源/TCP 日志使用不同的架构。

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

VPC Lattice 没有 `update-service --tracing-config` 选项，也没有能自动为应用程序配置 X-Ray 的 Controller 注解。请使用 OpenTelemetry/ADOT 或适用的跟踪 SDK 为应用程序配置插桩，传播跟踪上下文，并配置导出/采样。将应用程序跟踪与访问日志及请求 ID 关联起来；客户端提供的请求 ID 不是经过身份验证的身份。

## 最佳实践 {#best-practices}

- **设计和所有权：** 使用清晰的网络/Service 命名和环境边界。考虑不同 namespace 中同名的 Gateway、共享网络使用方、配额，以及每个 policy 和 association 的所有权。
- **部署：** 确保可以分别选择稳定版和 canary 后端。调整权重前检查端点、目标运行状况和授权。记录回滚标准并保留最近一次已知配置。
- **性能：** 使用有界超时和适当的连接复用。确保运行状况端点轻量且有意义。仅在应用程序语义允许的情况下进行缓存或批处理。私有 Lattice Service 不会仅因启用缓存就成为 CDN 源站。
- **安全：** 分离管理角色和调用方角色；不要将凭证放入 manifest。测试允许和拒绝访问的角色、根路径和子路径、直接访问后端的情况以及 TLS 行为。不要删除 IAM policy CRD 来拒绝流量。
- **可观测性：** 分别监控请求数、错误数/错误率、延迟、目标运行状况和遥测缺失情况。按要求的期限保留访问日志，并明确为应用程序配置跟踪插桩。
- **成本：** 针对所选模型查看当前区域内的 Service/资源、请求、数据处理、端点和日志费用。使用标签，仅移除确认未使用的资源，并将后端自动扩缩容与托管 Lattice 数据平面分开规划。

## 故障排除 {#troubleshooting}

请使用 Controller 注解/状态以及 AWS 资源清单中的标识符。不要假设直接 API 示例中的 `$SERVICE_ID` 就是 Kubernetes Route 的 Service。

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
| DNS/连接失败 | 实际分配的 DNS、客户端 VPC association 或 endpoint 路径、association 状态、安全组、NACL、Pod 可达性 |
| 403/身份验证失败 | 调用方角色、凭证过期和签名区域/Service、`UNSIGNED-PAYLOAD`、两层 auth、传播情况、拒绝原因日志字段 |
| 路由或版本错误 | Route 条件、Listener/规则优先级和匹配条件、目标组成员、权重、不同 Route 的域名 |
| 目标运行状况异常 | 实际监听端口、`/health`、HTTP 与 HTTPS、就绪状态、安全组、目标类型和运行状况检查阈值 |
| 没有日志/指标 | 目的地权限和交付状态、正确的指标 dimensions、初始流量、保留期限、查询状态 |
| Controller 协调失败 | `manager` 日志、IAM 角色、EndpointSlice、CRD 版本兼容性、webhook 和 Leader 选举状态 |

使用有界的指标时间范围，不依赖 GNU 专用的 `date -d`：

```bash
export METRIC_END="$(python3 -c 'from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat())')"
export METRIC_START="$(python3 -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat())')"
aws cloudwatch get-metric-statistics --namespace AWS/VpcLattice \
  --metric-name HTTPCode_5XX_Count --dimensions file://service-dimensions.json \
  --start-time "$METRIC_START" --end-time "$METRIC_END" \
  --period 60 --statistics Sum
```

如果 AWS Service 发生事件，请查看 AWS Health 和相关账户事件。账户专属的 API 访问和支持操作取决于适用的支持计划和端点。支持工单应包含经过审查的资源 ID、时间范围、故障症状和已清理敏感信息的日志。请为账户选择当前适用的 Service/类别/严重性选项；不要粘贴写死 `urgent` 的工单创建命令。

## 参考资料 {#references}

- [VPC Lattice 概述](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html)
- [Service network associations](https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-network-associations.html)
- [Controller v2.1.3 安装](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/deploy.md)
- [Controller v2.1 升级要求](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/upgrading-v2-0-x-to-v2-1-y.md)
- [Controller API 参考](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs/api-types)
- [Controller HTTPS 和后端 TLS](https://github.com/aws/aws-application-networking-k8s/blob/v2.1.3/docs/guides/https.md)
- [VPC Lattice auth policy](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html)
- [签名请求](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sigv4-authenticated-requests.html)
- [共享实体](https://docs.aws.amazon.com/vpc-lattice/latest/ug/sharing.html)
- [CloudWatch 指标](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-cloudwatch.html)
- [访问日志](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html)
- [CloudWatch Logs 交付权限](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-CWL.html)
- [S3 交付权限](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-infrastructure-S3.html)

## 测验

通过 [VPC Lattice 测验](../quizzes/networking/02-vpc-lattice-quiz.md)检验你对本章内容的理解。
