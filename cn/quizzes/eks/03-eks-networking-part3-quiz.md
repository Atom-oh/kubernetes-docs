# EKS 网络测验 - 第 3 部分

> **最后更新**: 2026年10月16日

本测验涵盖[第 3 部分故障排除概念](../../eks/03-eks-networking-part3.md)、私有连接、多集群设计和网格运维。当前示例使用 EKS Kubernetes 1.36 和 VPC CNI 1.23.2；历史 App Mesh 配置会被明确标识。资源创建示例需要经过审查的 IAM、网络和所有权前提条件。本审计执行本地检查，并不部署 EKS。

### 1. 当应用程序加入基于 sidecar 的服务网格时，会发生什么变化？

- A. 所有 Pod 流量离开 VPC
- B. 代理处理已加入服务的流量
- C. 移除服务发现
- D. 所有流量都需要 Transit Gateway

<details>
<summary>显示答案</summary>

**答案：B. 注入的代理处理已加入服务的流量。**

在 sidecar 模式中，应用程序与代理共享一个 Pod 网络命名空间和 IP。代理是数据平面的一部分；控制平面分发路由、安全和身份配置。NetworkPolicy、VPC 路由和 Service 发现仍然重要。逻辑路径如下：
```text
Application → client proxy → Pod network → destination proxy → application
```
拦截取决于加入状态、排除的端口、协议和模式；并非每个数据包都必须经过 Service VIP。Ambient 网格使用不同的节点代理/waypoint 设计，因此此问题明确针对 sidecar 模式。网格可提供重试、路由、mTLS 和遥测，而无需重写主要服务实现，但应用程序仍可能需要追踪上下文传播、兼容的协议和超时处理。

请使用所选网格支持的注入器/revision，而非手动添加旧 Envoy 镜像或同时使用多个注入器。AWS App Mesh 是一个历史示例：支持和访问于 2026 年 9 月 30 日结束。现有部署必须迁移；它不是默认的新安装示例。请参阅 [Istio 安装](../../service-mesh/istio/01-installation.md)，了解维护中的实现路径。

</details>

### 2. VPC endpoints 为私有 EKS 工作负载提供什么？

- A. 无限带宽
- B. 到受支持服务的私有连接
- C. 自动享受 50% 折扣
- D. 自动 AWS 身份验证

<details>
<summary>显示答案</summary>

**答案：B. 对于这些请求，无需互联网/NAT 即可通过私有路径访问受支持的 AWS 服务 endpoint。**

Interface endpoint 会在选定的子网/AZ 中创建 ENI，通常会产生按小时/数据处理费用。用于 S3/DynamoDB 的 Gateway endpoint 会添加路由表条目，且不收取 endpoint 费用；服务/存储/请求费用仍然适用。Endpoint 不会授予 IAM 权限、不保证更低成本/延迟，也不会自动满足合规要求。

对于私有 ECR 镜像拉取，请规划 `ecr.api`、`ecr.dkr` 和 S3 层下载路径、endpoint SG HTTPS 规则、DNS 支持/私有 DNS、路由表和 endpoint/IAM policy。其他必需服务取决于工作负载：用于 IRSA 的区域性 STS、用于 Pod Identity 的 `eks-auth`、用于 CNI 的 EC2 API、Logs/监控以及其他实际使用的服务。EKS 服务 endpoint 不会取代私有 Kubernetes API endpoint。ECR Public、首次 pull-through-cache 请求/Windows foreign layer 可能需要额外外部连接或准备好的镜像镜像仓库。

此参数化 CloudFormation 示例仅向**现有** VPC 添加三个 endpoint。创建前请审查现有 endpoint/私有 DNS 所有权。它特意将特定服务的 endpoint policy 留给安全负责人定义；endpoint 默认访问不会覆盖 IAM。请准备 change set，而非假定这是一套完整的隔离集群部署：
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: ECR API/DKR and S3 endpoints in an existing VPC; not a complete private EKS stack
Parameters:
  VpcId:
    Type: AWS::EC2::VPC::Id
  PrivateSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Existing subnets in distinct Availability Zones
  PrivateRouteTableIds:
    Type: CommaDelimitedList
    Description: Route tables used by the image-pulling workloads
  EndpointSecurityGroupId:
    Type: AWS::EC2::SecurityGroup::Id
    Description: Existing same-VPC SG permitting HTTPS from the intended nodes/Pods
Resources:
  S3GatewayEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
      VpcId: !Ref VpcId
      RouteTableIds: !Ref PrivateRouteTableIds
      VpcEndpointType: Gateway
  ECRApiEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.api
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
  ECRDkrEndpoint:
    Type: AWS::EC2::VPCEndpoint
    Properties:
      ServiceName: !Sub com.amazonaws.${AWS::Region}.ecr.dkr
      VpcId: !Ref VpcId
      SubnetIds: !Ref PrivateSubnetIds
      SecurityGroupIds: [!Ref EndpointSecurityGroupId]
      PrivateDnsEnabled: true
      VpcEndpointType: Interface
```
当需要新的 node group 时，`eksctl create nodegroup` 使用 **`--subnet-ids`**；之前的 `--vpc-private-subnets` 标志不适用于此命令。该示例会在私有 API/服务路径就绪后创建会产生费用的托管节点；仅当 eksctl 是预期所有者且不存在 `private-ng` 时使用。实例大小仅用于说明，并非容量规划建议。
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster name}"
: "${AWS_REGION:?Set its Region}"
: "${PRIVATE_SUBNET_A:?Set an existing private subnet}"
: "${PRIVATE_SUBNET_B:?Set another private subnet}"
eksctl create nodegroup --cluster "$CLUSTER_NAME" --region "$AWS_REGION" \
  --name private-ng --managed --version auto --node-type m5.large \
  --nodes 2 --nodes-min 2 --nodes-max 3 --node-private-networking \
  --subnet-ids "$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B"
```

</details>

### 3. 哪个选项可在多个不重叠的 VPC 之间提供中心路由？

- A. 必须使用公网负载均衡器
- B. Transit Gateway 和完整路由
- C. 每个集群必须共享一个 VPC
- D. NAT gateway 提供 Kubernetes 发现

<details>
<summary>显示答案</summary>

**答案：B. AWS Transit Gateway**

Transit Gateway 是适用于众多 VPC 的一种设计；它并非在所有情况下都是最有效的多集群架构。请针对信任边界、规模、DNS、地址重叠和成本，比较 VPC peering、shared VPC、PrivateLink 服务暴露、VPC Lattice 和 mesh gateway。NAT 也有私有连接用途；它不提供服务发现。

对于 TGW 设计，请规划不重叠且可路由的 Pod/VPC CIDR、每个参与 AZ 中的 attachment、TGW 路由表关联/传播、工作负载子网路由和返回路由。仅有 TGW 路由并不足够。Kubernetes ClusterIP 是虚拟服务地址，并非自动可路由的远程 endpoint。通过明确的发现设计导出可达的 Pod endpoint 或 gateway/load-balancer 服务地址。更改前请读取实际路由状态：
```bash
set -euo pipefail
: "${AWS_REGION:?Set the transit gateway Region}"
: "${TGW_ROUTE_TABLE_ID:?Set the intended TGW route table}"
: "${VPC_ROUTE_TABLE_ID:?Set a workload-subnet route table}"
aws ec2 search-transit-gateway-routes --region "$AWS_REGION" \
  --transit-gateway-route-table-id "$TGW_ROUTE_TABLE_ID" \
  --filters Name=state,Values=active
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --route-table-ids "$VPC_ROUTE_TABLE_ID"
```
TGW 没有附加到其上的防火墙 SG。请酌情使用 endpoint/node/Pod SG、NACL、NetworkPolicy 和经检查的路由。跨 VPC 的 SG 引用是 TGW 在已记录 attachment/Region 限制下支持的功能；它不同于将 SG 附加到 TGW，且不能取代路由。

Cloud Map 需要完成 namespace、Service、注册以及健康检查/取消注册管理。TGW 不会自动共享私有 hosted-zone DNS。请使用经批准的私有 zone 关联或 Route 53 Resolver endpoint/rule。不要将请求转发到另一个 VPC 的 `base+2` resolver，并把它当作该集群的 CoreDNS。此 **Corefile 片段**假设有两个真实、可达的 inbound resolver，且它们已能解析导出的 `cluster2.example.internal` 记录。请通过 DNS 配置所有者合并它，并保留集群本地区域：
```text
cluster2.example.internal:53 {
    errors
    cache 30
    forward . 10.1.20.10 10.1.21.10
}
```
以下 ingress policy 基于 NAT/proxy 后实际可见的源地址，允许远程源 CIDR 访问一个 API 端口。其他匹配 policy 可能会扩大允许范围。必须分别设计 Egress/DNS 要求；跨集群的 namespace/Pod label 不会自动共享。
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: remote-api-ingress
  namespace: multicluster-demo
spec:
  podSelector:
    matchLabels:
      app: api-service
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 10.1.0.0/16
    ports:
    - protocol: TCP
      port: 8080
```
Istio multi-primary 和 primary-remote 是不同的控制平面布局；请选择受支持的模型，并验证 east-west gateway、身份信任和 endpoint 健康状况。现有 App Mesh 多集群使用必须考虑其在 2026 年 9 月的退役。请根据实际路径比较按小时、处理和跨 AZ 费用；same-VPC 或公网负载均衡器设计并非本身无效，但需要各自的安全/成本分析。

</details>

### 4. VPC CNI 的哪项功能以 /28 块分配 IPv4 地址来提高地址槽密度？

- A. 对所有 Pod 使用 hostNetwork
- B. Prefix delegation
- C. 对每个 Service 使用 NodePort
- D. 对 Pod 到 Pod 流量使用 Global Accelerator

<details>
<summary>显示答案</summary>

**答案：B. Prefix delegation**

一个委派的 IPv4 /28 提供 16 个 Pod 地址，同时占用一个 ENI 地址槽。它可以减少分配 API 工作并提高 Pod 启动速度/密度；它不是通用的数据包吞吐优化，也不能解决子网总耗尽问题。IPv6 使用不同的 prefix 大小。受支持的 Nitro 硬件、连续空闲 prefix、kubelet maxPods 和资源容量仍会限制密度。

请在审查 schema/所有权后，将此 JSON 片段合并到精确的 EKS add-on 配置中，或使用相应的 Helm `env` 值。旧的小写 `amazon-vpc-cni` ConfigMap key 不会配置 Linux CNI：
```json
{
  "env": {
    "ENABLE_PREFIX_DELEGATION": "true",
    "WARM_PREFIX_TARGET": "1"
  }
}
```
`WARM_PREFIX_TARGET=1` 表示一个备用 prefix，而非 prefix 大小。正数 `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` 优先于 warm-prefix target。较大的 warm pool 会预留更多子网空间。请规划 node-group 迁移和 maxPods 设置；仅切换 DaemonSet 并不能使现有节点支持任意密度。

| 实例 | 传统的 secondary-IPv4 maxPods 公式 | 这些小型实例的示例 prefix-mode 上限 |
|---|---:|---:|
| t3.medium | 17 | 110 |
| m5.large | 29 | 110 |
| c5.xlarge | 58 | 110 |
| r5.2xlarge | 58 | 110 |

这些是配置限制，并非基准测试结果，也不保证每个 Pod 都能容纳。之前 c5.xlarge/r5.2xlarge 的 250 条目不正确：EKS 的建议上限是在少于 30 个 vCPU 时为 110，在 30 个或更多 vCPU 时为 250。Pod SG branch interface 有单独的限制。Prefix 分配需要连续的 /28 块，而非通用的最小 /24 子网，并且不会自动简化 SG policy。
```bash
set -euo pipefail
: "${AWS_REGION:?Set the node Region}"
kubectl get nodes -o 'custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\.kubernetes\.io/instance-type,PODS:.status.allocatable.pods'
kubectl -n kube-system get daemonset aws-node -o yaml
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
aws ec2 describe-instance-types --region "$AWS_REGION" \
  --instance-types t3.medium m5.large c5.xlarge r5.2xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,vCPUs:VCpuInfo.DefaultVCpus,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4Slots:NetworkInfo.Ipv4AddressesPerInterface}'
```

</details>

### 5. Istio sidecar 模式使用哪个代理，以及如何诊断？

<details>
<summary>显示答案</summary>

**答案：Envoy**

Istio sidecar 模式使用 Envoy，其中 istiod 提供发现、路由和证书配置。旧的 Pilot/Citadel 功能已合并至 istiod，Mixer 不是当前必需的组件。其他网格可以使用不同代理；Envoy 并非 Kubernetes 或每个网格的要求。

配置后，Envoy 支持连接池、HTTP/TCP 路由、重试、outlier detection、TLS 和遥测。仅添加 Envoy 容器并不能配置透明流量拦截、工作负载身份、xDS 或 mTLS。对于真实网格，请使用其受支持的注入器和代理构建。旧的独立 Envoy 1.20 镜像和不完整的 Deployment 不是有效的当前安装。

以下**独立 reverse-proxy bootstrap**展示了原始 listener/route/cluster 概念。它已使用上游 Envoy 1.39.1 在本地验证。独立 HTTP 应用程序必须在同一网络命名空间的 `127.0.0.1:8080` 上监听。代理和 admin listener 仅绑定 loopback；这不是生产环境或 Kubernetes 网格部署：
```yaml
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
static_resources:
  listeners:
  - name: local-proxy
    address:
      socket_address:
        address: 127.0.0.1
        port_value: 15001
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: demo_http
          route_config:
            name: local-route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: /
                route:
                  cluster: local-app
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: local-app
    connect_timeout: 0.25s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local-app
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080
```
将其保存为 `envoy-config.yaml`，并使用匹配的上游二进制文件验证。验证会解析配置；它不证明 backend 或工作负载身份正常工作。
```bash
envoy --mode validate --concurrency 1 --config-path envoy-config.yaml
```
对于现有 Kubernetes 网格代理，请发现已配置的 admin port 和容器名称，而非假设为 19000。App Mesh 的默认 admin port 是 9901；Istio 通常使用 15000，部署设置可能不同。请在一个终端中运行此 port-forward：
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the existing mesh workload namespace}"
: "${MESH_POD:?Set the existing proxy Pod}"
: "${ENVOY_ADMIN_PORT:?Use the admin port actually configured by that mesh}"
kubectl -n "$MESH_NAMESPACE" port-forward --address 127.0.0.1 \
  "pod/$MESH_POD" "19000:$ENVOY_ADMIN_PORT"
```
然后从另一个终端发出有界的只读查询。配置转储可能包含内部拓扑或敏感配置；请勿发布它们或将 admin listener 暴露到外部。
```bash
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/config_dump
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/stats
curl --fail --show-error --max-time 10 http://127.0.0.1:19000/clusters
```
请一并检查上游健康状态、连接池限制、重试、filter 成本、内存和请求延迟。请根据测量到的工作负载行为调优；仅为了降低开销而删除安全 filter 会改变安全模型。

</details>

### 6. 常规 EKS 节点上的 DNS 由什么提供，以及应如何配置？

<details>
<summary>显示答案</summary>

**答案：CoreDNS（首先识别实际的 DNS/add-on 所有者）。**

CoreDNS 是常规 EKS 计算环境中通常使用的 DNS add-on。创建方法/add-on 所有权可能不同；EKS Auto Mode 包含托管的集群 DNS，并非固有地需要传统 CoreDNS Deployment。在应用以下常规 add-on 检查前，请识别计算/DNS 所有者。ResourceNotFound 响应需要调查所有权，而不是自动重新安装：
```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the existing cluster}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-addon --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" \
  --addon-name coredns
kubectl -n kube-system get deployment coredns -o yaml
kubectl -n kube-system get configmap coredns -o yaml
kubectl -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
```
Service DNS 通常遵循 `<service>.<namespace>.svc.<cluster-domain>`；`cluster.local` 是常见 domain，而非不可变的 domain。Headless/ExternalName 记录不同于普通 ClusterIP 记录。不要假定每个任意 Pod IP 都有有用的 reverse-DNS 记录。

这是示例 **Corefile**，而不是可以盲目覆盖的 ConfigMap。请保留托管配置、实际 cluster domain、probe 和 DNS Service。`pods insecure` 允许语法上有效的 Pod-IP DNS 响应而不验证 Pod；请选择预期的 Kubernetes plugin 模式。
```text
.:53 {
    errors
    health {
        lameduck 5s
    }
    ready
    kubernetes cluster.local in-addr.arpa ip6.arpa {
        pods insecure
        fallthrough in-addr.arpa ip6.arpa
        ttl 30
    }
    prometheus :9153
    forward . /etc/resolv.conf
    cache 30
    loop
    reload
    loadbalance
}
```
`errors` 记录失败；`health` 和 `ready` 提供不同的 probe 角色；`kubernetes` 回答集群记录；`forward` 解析其他 domain；`prometheus` 暴露指标；`cache`、`reload` 和 `loadbalance` 会影响缓存/配置重新加载/记录顺序。`loop` plugin 在启动期间检测某些简单的转发循环，并不会永久检测所有动态 DNS 循环。`loadbalance` 改变 DNS 答案排序，而不是 Service 数据包转发。

对于条件转发，请使用已批准且可达的 DNS server，并允许 UDP/TCP53。VPC 子网的第一个地址，例如 10.0.0.1，并不是示例公司 DNS server。`file` plugin 提供权威 zone file，必须创建/挂载并使用有效的 SOA/记录维护；它不能替代 stub-domain forward。公网 resolver 需要有意设计 Egress 和披露 policy；它们不能凭空解析私有 hosted zone。

此 cache 片段修复了原始参数顺序：`prefetch AMOUNT DURATION PERCENTAGE`。请替换现有的 cache directive，而不是添加第二个：
```text
cache 30 {
    success 10000
    denial 1024
    prefetch 10 2m 10%
}
```
在上游 CoreDNS 1.14.7 中，`denial1000` 可被接受，但会规范化为 1024；`success10000` 会规范化为 9984。显式使用 1024 可保留原始的有效 denial 容量。这些容量是实现行为，并非经测量的 DNS 容量规划建议。

请选择**单一扩缩容所有者**。在精确的 add-on 版本/schema 支持时使用 EKS 托管的 CoreDNS autoscaling，或使用单独拥有的 HPA/cluster-proportional autoscaler。以下 HPA 仅适用于有 metrics-server 和 CPU request 的、特意自我管理的 Deployment；请勿将其与另一个 replica manager 结合使用：
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns
  namespace: kube-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coredns
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```
原始资源示例（100m CPU request、70Mi memory request、170Mi memory limit）仅用于说明，并未经过工作负载验证。请监控查询速率、错误、cache 命中/未命中行为、内存/OOM 和响应延迟，再确定大小。诊断时，请使用包含 DNS 工具的现有、已批准的诊断工作负载；检查 dnsPolicy/dnsConfig/resolv.conf、kube-dns EndpointSlice 以及 policy/SG/upstream 路径。请分别测试集群 Service 和已批准的外部/私有名称。之前过时的 dnsutils 镜像和无所有者的裸 Pod 并非 DNS 诊断的前提条件。

</details>

### 7. 应如何保护、观察并迁移现有 App Mesh 部署？

<details>
<summary>显示答案</summary>

**答案：审查现有图、身份和遥测，然后验证受支持的替代方案。**

**历史运维和迁移练习：** AWS App Mesh 支持和资源访问于 **2026 年 9 月 30 日**结束。不要按照原始配方预置新网格、Private CA 和公网 Grafana。对于以前的 App Mesh 部署，请盘点其图并将其迁移到受支持的 mesh/gateway。ECS Service Connect 不是 EKS 安装目标；请针对实际使用的功能评估受支持的 Kubernetes mesh/gateway 架构。
```bash
set -euo pipefail
: "${MESH_NAMESPACE:?Set the namespace of the existing mesh workloads}"
kubectl get meshes.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get virtualnodes.appmesh.k8s.aws,virtualservices.appmesh.k8s.aws,virtualrouters.appmesh.k8s.aws
kubectl -n "$MESH_NAMESPACE" get deployments,services
```
**1. 绘制现有图。** Mesh namespace selector 选择参与的 namespace；VirtualNode Pod selector 选择工作负载、listener 和服务发现。VirtualService 名称路由到 VirtualNode 或 VirtualRouter；router route 选择加权 VirtualNode。请盘点 backend 引用、endpoint DNS、健康检查、IAM/IRSA、注入器设置和应用程序监听端口。原始 `service-a:latest` 占位符和缺少的 service-b 工作负载不是可工作的应用程序。不要覆盖现有 ServiceAccount，也不要将 full-access policy 作为故障排除步骤附加。

**2. 区分 TLS 和双向身份验证。** STRICT 模式下仅有 server certificate 的 listener 要求加密连接，但自身不验证 client。App Mesh mTLS 需要 client certificate 和服务端 client trust，以及客户端 server trust/SAN 检查。Client certificate 和 listener validation trust 使用文件或 SDS，而非 ACM client-certificate 引用。工作负载内 App-to-Envoy 流量不会因 proxy-to-proxy mTLS 自动加密。

以下是**旧配置审查示例**，而非新安装。其文件必须已安全地挂载到 proxy，certificate 必须具有所需身份/用途，service-b 必须存在，且匹配的 namespace 必须属于预期 Mesh。请按照信任设计的要求添加已批准的 client SAN 限制；仅信任 CA 会接受其符合条件的 client certificate：
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualNode
metadata:
  name: service-a
  namespace: app-namespace
spec:
  podSelector:
    matchLabels:
      app: service-a
  listeners:
  - portMapping:
      port: 8080
      protocol: http
    tls:
      mode: STRICT
      certificate:
        file:
          certificateChain: /certs/server.crt
          privateKey: /certs/server.key
      validation:
        trust:
          file:
            certificateChain: /certs/trusted-client-ca.pem
    outlierDetection:
      baseEjectionDuration:
        unit: s
        value: 30
      interval:
        unit: s
        value: 10
      maxEjectionPercent: 50
      maxServerErrors: 5
  backends:
  - virtualService:
      virtualServiceRef:
        name: service-b
      clientPolicy:
        tls:
          enforce: true
          ports: [8080]
          certificate:
            file:
              certificateChain: /certs/client.crt
              privateKey: /certs/client.key
          validation:
            trust:
              file:
                certificateChain: /certs/trusted-server-ca.pem
            subjectAlternativeNames:
              match:
                exact: [service-b.app-namespace.svc.cluster.local]
  serviceDiscovery:
    dns:
      hostname: service-a.app-namespace.svc.cluster.local
  logging:
    accessLog:
      file:
        path: /dev/stdout
```
不要将账户中的所有 ACTIVE CA 选择到一个变量中。创建 root CA 需要显式配置以及激活/certificate 步骤，并会产生费用；它不会立即生成可用 certificate。请保留精确的预期 ARN。App Mesh Kubernetes CRD 字段区分大小写（`certificateARN`、`certificateAuthorityARNs`）；纯 YAML 文件中的 `${CA_ARN}` 不是 shell 插值。所示基于文件的示例避免假装缺失的 CA 工作流程已运行。

对于现有 plaintext peer，请分阶段进行有文档记录的 PERMISSIVE 迁移，预置 client/server identity 和 trust，测试接受和拒绝的 peer，然后要求 STRICT。检查 `ssl.handshake`、`ssl.no_certificate`、`ssl.fail_verify_no_cert` 和 `ssl.fail_verify_san` 以及真实请求结果。仅成功的 server-TLS handshake 并不足以证明 mTLS。

**3. 在迁移期间保留可观测性。** 原始配方中的 `Mesh.spec.tracing`、`Mesh.spec.logging` 和 `Mesh.spec.serviceDiscovery` 并非已审查 controller 1.13.1 CRD 中的字段。access logging 属于 VirtualNode（如上）。App Mesh Envoy image tracing 设置是独立的，例如此**容器环境片段**需要在 2000 上运行的本地 X-Ray daemon/collector、权限、endpoint 访问和 trace-context 传播：
```yaml
env:
- name: ENABLE_ENVOY_XRAY_TRACING
  value: "1"
- name: XRAY_DAEMON_PORT
  value: "2000"
```
请使用已批准的 collector 收集 proxy 实际的 `/stats` 或 Prometheus endpoint。CloudWatch 需要配置 scraping/export/EMF；不要假定 `AWS/AppMesh` RequestCount/Latency metric 会自动出现。构建 dashboard 前，请盘点实际 namespace、metric 名称、dimension 和单位。保留现有的 CloudWatch/Prometheus/Grafana 所有者、credential 和受支持的 StorageClass。避免浮动 manifest、硬编码的 Grafana admin 密码和未经审查的公网 LoadBalancer。此可选 Grafana provisioning 片段仅标识现有 Prometheus datasource；它不会安装或保护任一系统：
```yaml
apiVersion: 1
datasources:
- name: Prometheus
  type: prometheus
  url: http://prometheus-server.prometheus.svc.cluster.local
  access: proxy
  isDefault: true
```
**4. 明确映射流量行为。** 此旧 router 示例假设两个带版本的 VirtualNode 均已存在且具有健康 endpoint。权重不是精确请求计数的保证。Outlier detection 是 endpoint 驱逐，不同于 connection-pool circuit-breaking 限制。原始的四个 HTTP retry event 字符串均有效：`client-error` 表示 409，`stream-error` 表示拒绝的流。请为总体 timeout 预算内的幂等操作选择 retry；retry 可能放大失败负载。
```yaml
apiVersion: appmesh.k8s.aws/v1beta2
kind: VirtualRouter
metadata:
  name: service-a-router
  namespace: app-namespace
spec:
  listeners:
  - portMapping:
      port: 8080
      protocol: http
  routes:
  - name: service-a-route
    httpRoute:
      match:
        prefix: /
      action:
        weightedTargets:
        - virtualNodeRef:
            name: service-a-v1
          weight: 90
        - virtualNodeRef:
            name: service-a-v2
          weight: 10
      retryPolicy:
        maxRetries: 3
        perRetryTimeout:
          unit: ms
          value: 2000
        httpRetryEvents:
        - gateway-error
```
**5. 逐步验证和切换。** 在迁移流量前，比较路由、已授权/未授权 peer、DNS、TLS 轮换、重试、故障恢复、trace 和 metric 连续性。在剩余产品支持窗口内保留 rollback 路径。原始的 100–200m CPU 和 128–256Mi proxy memory 值是**未经验证的示例估计**，不是测量值或有保证的容量。请测量真实饱和度、内存、延迟和错误率。本审计未预置任何 mesh、CA、collector 或云 dashboard。

</details>

### 8. VPC CNI 1.23.2 中哪个变量配置附加的 ENI MTU？

- A. `ENI_MTU`
- B. `AWS_VPC_ENI_MTU`
- C. `VPC_MTU_SIZE`
- D. `MAX_ENI`

<details>
<summary>显示答案</summary>

**答案：B. `AWS_VPC_ENI_MTU`**

`POD_MTU` 配置 Pod 虚拟接口，并在未设置时从 ENI MTU 派生。`ENI_MTU` 是错误的名称。请匹配实际路径 MTU 和规划的 node/Pod rollout；可接受的数值不保证 gateway/tunnel/远程 endpoint 接受该数据包大小。SG 不是 MTU 设置设备。

</details>

### 9. 严格 Pod-SG TCP early-demux workaround 应放在哪里？

- A. 应用程序 Deployment
- B. CoreDNS ConfigMap
- C. CNI init container
- D. LoadBalancer annotation

<details>
<summary>显示答案</summary>

**答案：C. `aws-vpc-cni-init`**

文档记录的 `DISABLE_TCP_EARLY_DEMUX=true` 设置属于 init container，由 Helm `init.env` 表示。在主 `aws-node` container 上设置它不会应用此初始化时更改。请确认 strict-mode kubelet-probe 问题；标准 Pod-SG 模式不需要此 workaround。

</details>

### 10. Kubernetes NetworkPolicy 保证哪种规则顺序优化？

- A. 将最常用的规则放在最前面
- B. 按名称字母顺序排序
- C. 最后创建限制性 policy
- D. 不保证顺序

<details>
<summary>显示答案</summary>

**答案：D. 无；匹配的允许规则是累加的。**

没有可移植的“第一个匹配即生效”或最新 policy 优先级。selector/direction 和允许规则的并集决定隔离。供应商的 tier/order API 是独立的。请保留所需限制，并测量 policy 编程/运行时成本，而不是仅根据数量删除规则。

</details>

### 11. 子网已耗尽。增加 WARM_IP_TARGET 会增加地址容量吗？

- A. 会，它会扩展子网
- B. 不会，它会增加备用地址需求
- C. 会，它会绕过 ENI 限制
- D. 会，它会修复每个 ContainerCreating Pod

<details>
<summary>显示答案</summary>

**答案：B. 不会；它会请求更多备用地址。**

在容量存在时，较大的 warm target 可以减少分配延迟，但也会预留地址并可能加剧耗尽。请独立识别子网空间、ENI 槽、maxPods、API 节流和 prefix 碎片化。Prefix delegation 不会创建更多 IPv4 地址总量。

</details>

### 12. 应检查哪个 API 以获取当前 Service backend 地址和条件？

- A. 仅 Node event
- B. Ingress annotation
- C. EndpointSlice
- D. 仅 Service ClusterIP

<details>
<summary>显示答案</summary>

**答案：C. EndpointSlice**

使用 `kubernetes.io/service-name=<service>` 在 Service namespace 中查询 EndpointSlice。请结合 Service selector 和 targetPort 检查地址、端口以及 ready/serving/terminating 条件。旧版 Endpoints 对象可能会截断大型 endpoint 集；空结果可能表明 selector/readiness 问题，而不是 load-balancer 故障。

</details>

### 13. trafficDistribution: PreferSameZone 表示什么？

- A. 永不跨越 AZ 边界
- B. 优先同一 zone，并允许回退
- C. 将现有 Pod 移至一个 AZ
- D. 覆盖所有 Local 流量 policy

<details>
<summary>显示答案</summary>

**答案：B. 优先使用可用的同一区域 endpoint，并允许回退。**

它是兼容 Service proxy 的路由偏好，而非 AZ 隔离 policy。请确保有足够的本地容量。现有 topology-mode Auto annotation 具有优先级。Local internal/external 流量 policy 对各自流量施加更严格的 node-local 要求，并且在没有本地 endpoint 时可能会丢弃流量。

</details>

### 14. 计算假设的 10 Gbps 流量、20 ms RTT 的带宽延迟积。

<details>
<summary>显示答案</summary>

**答案：25,000,000 字节，约 23.84 MiB。**

```text
10,000,000,000 bits/s × 0.020 s / 8 = 25,000,000 bytes
```
这是算术示例，并非 EKS benchmark，也不是建议将每个 socket buffer 设置为该值。请考虑实际 EC2 单流/burst 限制、TCP auto-tuning、window scaling、并发连接和内存压力。若无测量，先前的 16 MiB 最大值不能称为最优。Keepalive 在已启用的空闲 socket 上运行；它不同于 HTTP pooling 和 buffer sizing。

</details>

### 15. 如何区分 DNS、Service 选择和应用程序连接故障？

<details>
<summary>显示答案</summary>

**答案：收集证据，然后使用正向对照测试实际协议。**

在将 ContainerCreating 分类为网络问题之前，请检查受影响 Pod 的 event。解析已知的集群 Service 和预期 hostname，检查 Service/EndpointSlice selector-port-readiness 一致性，然后从同一源比较 Pod-IP 和 Service-URL 访问。测试已知允许的路径，以免将缺少工具、DNS 失败或 backend 停止误判为 policy 拒绝。请使用源章节中有界的诊断：
```bash
set -euo pipefail
: "${APP_NAMESPACE:?Set the affected namespace}"
: "${APP_POD:?Set the affected Pod}"
: "${APP_SERVICE:?Set the affected Service}"
kubectl -n "$APP_NAMESPACE" describe pod "$APP_POD"
kubectl -n "$APP_NAMESPACE" get events --field-selector "involvedObject.name=$APP_POD" --sort-by=.metadata.creationTimestamp
kubectl -n "$APP_NAMESPACE" get service "$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$APP_SERVICE" -o yaml
kubectl -n "$APP_NAMESPACE" get networkpolicy
kubectl -n kube-system logs -l k8s-app=aws-node -c aws-node --tail=200 --prefix=true
```
对于 load balancer，请识别 controller/class、scheme、target type 和 target-health 原因。验证实际应用程序/health port、SG 和路由路径、TLS/SNI 以及 Host 路由。仅 ICMP 行为不能证明 TCP/UDP NetworkPolicy 强制执行。更改一个已确认的原因，保留所有者的 rollback 路径，并重复相同检查。这些示例不声称执行生产网络测试。

</details>

官方参考：[Private EKS](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[VPC CNI 1.23.2](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.2/README.md)、[CoreDNS cache](https://coredns.io/plugins/cache/)、[App Mesh mTLS](https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html)、[App Mesh metrics](https://docs.aws.amazon.com/app-mesh/latest/userguide/metrics.html)、[Envoy 1.39.1](https://github.com/envoyproxy/envoy/releases/tag/v1.39.1)。
