# EKS 集群创建测验 - 第 3 部分

> **最后更新**：2026 年 9 月 11 日

本测验涵盖 EKS 网络、节点容量、多租户、自动扩缩和节点安全。命令和清单均为学习示例；本次审查期间未执行云端部署和端到端行为验证。使用前请确认目标账户、Region、kubeconfig、兼容的附加组件版本以及资源所有权。

## 基本概念问题

1. 在常规 IPv4 辅助 IP 计算中，什么决定 ENI 和每个 ENI 的地址上限？
   * A) Namespace 名称
   * B) EC2 实例类型
   * C) Service 名称
   * D) Deployment 名称

<details>
<summary>显示答案</summary>

**答案：B) EC2 实例类型**

对于 Linux IPv4 **辅助 IP 模式**，在子网地址充足且未使用自定义网络或 Pod 安全组的情况下，实例类型决定 ENI 和每个 ENI 的地址上限。此公式用于估算常规节点 Pod 上限，而不是“每个 Pod 的 IP 地址数”。

常规公式会预留**每个** ENI 的主地址：

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
```
额外的两个地址是历史上为 `aws-node` 和 `kube-proxy` 保留的 host-network 配额。表格保留了这项辅助 IP 计算；它**并非**适用于每一种 AMI、CNI 模式或托管节点组的实际 `maxPods`。

| 实例类型 | 最大 ENI 数 | 每个 ENI 的 IP 数 | 最大 Pod 数 |
| ------------- | -------- | ----------- | -------- |
| t3.small      | 3        | 4           | 11       |
| t3.medium     | 3        | 6           | 17       |
| m5.large      | 3        | 10          | 29       |
| m5.xlarge     | 4        | 15          | 58       |
| m5.2xlarge    | 4        | 15          | 58       |
| m5.4xlarge    | 8        | 30          | 234      |
| c5.large      | 3        | 10          | 29       |
| c5.xlarge     | 4        | 15          | 58       |
| r5.large      | 3        | 10          | 29       |
| r5.xlarge     | 4        | 15          | 58       |

**检查实际容量和 EC2 限制：**

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.node\\.kubernetes\\.io/instance-type,CAPACITY:.status.capacity.pods,ALLOCATABLE:.status.allocatable.pods
aws ec2 describe-instance-types --region us-west-2 \
  --instance-types m5.large m5.4xlarge \
  --query 'InstanceTypes[].{Type:InstanceType,ENIs:NetworkInfo.MaximumNetworkInterfaces,IPv4PerENI:NetworkInfo.Ipv4AddressesPerInterface}'
```
即使未达到节点上限，子网地址耗尽也可能导致无法创建 Pod。CPU/内存请求、其他 host-network Pod、自定义网络、Pod 安全组以及 kubelet 配置也会产生影响。托管节点组会将 `maxPods` 上限设为：少于 30 个 vCPU 的实例为 110，否则为 250；这与公式算出的更大结果无关。

IPv4 前缀委派会将一个 `/28` 分配给 ENI 上的一个辅助地址**槽位**；多个前缀可以占用同一个 ENI。它不会增加子网地址空间。前提条件和迁移方法请参见问题 5。

对于自定义 AL2023 AMI，请在计算并测试合适的值后，在 NodeConfig 中配置 `spec.kubelet.config.maxPods`。如果使用托管节点组且未指定自定义 AMI ID，EKS 会计算建议值。单独提高 kubelet 上限并不能增加 IP 地址或计算容量。不要传入不存在的 eksctl `--kubelet-extra-args` 选项。

</details>

2. 如果没有 NetworkPolicy 选择某个 Pod，它的 NetworkPolicy 隔离状态是什么？
   * A) 未隔离，但仍受其他网络控制措施约束
   * B) 仅允许同一 namespace 的流量
   * C) 必须显式配置允许规则
   * D) 拒绝所有流量

<details>
<summary>显示答案</summary>

**答案：A) 未隔离，但仍受其他网络控制措施约束**

如果没有策略选择某个 Pod 的某个流量方向，Kubernetes NetworkPolicy 会使该方向处于未隔离状态。这**并不意味着**可以绕过安全组、路由表、NACL、其他策略 API 或应用程序的监听设置。

Amazon VPC CNI 在受支持的 Linux EC2 节点上启用时，具有原生 NetworkPolicy 执行功能。目前标准/管理员策略指南要求 VPC CNI 1.21 或更高版本，以及 5.10 或更高版本的内核；请确认所选附加组件的兼容性。此执行路径不涵盖 Windows 和 Fargate。请使用受控制器管理的 Pod（例如 Deployments），并检查 AWS 对接口和 Service 端口的限制。

使用 AWS VPC 网络的 Calico 策略和 AWS-CNI 链接模式下的 Cilium 是可选方案，但各自有安装要求。不要安装未经配置的第二个 CNI，也不要无意中叠加策略代理。AWS Network Firewall 会过滤经路由传输的 VPC 流量；它不会实现 Kubernetes NetworkPolicy 选择器。

以下示例适用于一个**新建且专用的** `network-policy-lab` namespace。第一条策略仅隔离入口流量。接下来的两条策略允许特定流量；`prod` 对等端要求同时匹配内置 namespace 标签和 backend Pod 标签。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: network-policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: backend}
  policyTypes: [Ingress]
  ingress:
  - from:
    - podSelector:
        matchLabels: {app: frontend}
    ports:
    - {protocol: TCP, port: 8080}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prod-to-database
  namespace: network-policy-lab
spec:
  podSelector:
    matchLabels: {app: database}
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: prod
      podSelector:
        matchLabels: {app: backend}
    ports:
    - {protocol: TCP, port: 5432}
```
对于出口隔离，请单独允许实际的 DNS 路径和应用程序依赖。只有在基线连接、DNS、就绪状态以及允许的正向对照均成功后，被拒绝的连接才有意义。不要为了快速测试而对 `kube-system` 或共享的 `default` namespace 应用全面拒绝策略。

</details>

3. 对于私有 IPv4 子网，哪种方式是常规的互联网出口路径？
   * A) 将 IGW 附加到子网
   * B) 路由到公有 NAT gateway，再路由到 VPC IGW
   * C) 为每个 Pod 分配一个 Elastic IP
   * D) 使用私有 NAT gateway 直接通过 IGW

<details>
<summary>显示答案</summary>

**答案：B) 路由到公有 NAT gateway，再路由到 VPC IGW**

对于需要通过公有 IPv4 访问互联网的私有 IPv4 节点和 Pod，常见设计是将私有子网的默认路由指向**公有子网中的公有 NAT gateway**。该公有子网会路由到附加到**VPC** 的互联网网关，且 NAT gateway 具有 Elastic IP。NAT instance 是另一种方案，但需要额外配置路由、源/目标检查和运维。

采用默认 IPv4 VPC CNI SNAT 行为时，Pod 发往 VPC 外部的流量首先使用节点的主 IPv4 地址。具有公有 IPv4 地址且有 IGW 路由的公有节点可以使用不同路径。原生 IPv6 出口可以使用仅出口互联网网关；通过 VPC endpoints 访问 AWS 服务可能不需要互联网 NAT。不要将 NAT 视为每个 Pod 的通用前提条件。

**单可用区 CloudFormation 路由示例**：此示例展示公有/私有路由关联；它不是完整的 EKS VPC。EKS 集群子网至少需要两个 AZ。对于按可用区部署 NAT 的设计，可以考虑每个 AZ 配置一个 NAT gateway 和一条私有路由，以避免跨 AZ 依赖。NAT gateway 和公有 IPv4 地址会产生费用。有关集群部署，请查看概念指南中的完整 EKS VPC 模板。

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: One-AZ IPv4 NAT routing demonstration; not a complete EKS VPC
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsSupport: true
      EnableDnsHostnames: true
      Tags:
        - Key: Name
          Value: EKS-VPC

  PublicSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.0.0/24
      MapPublicIpOnLaunch: false
      Tags:
        - Key: Name
          Value: Public-Subnet-1

  PrivateSubnet1:
    Type: AWS::EC2::Subnet
    Properties:
      VpcId: !Ref VPC
      AvailabilityZone: !Select [0, !GetAZs ""]
      CidrBlock: 10.0.2.0/24
      Tags:
        - Key: Name
          Value: Private-Subnet-1

  InternetGateway:
    Type: AWS::EC2::InternetGateway
    Properties:
      Tags:
        - Key: Name
          Value: EKS-IGW

  VPCGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC
      InternetGatewayId: !Ref InternetGateway

  NatGatewayEIP:
    Type: AWS::EC2::EIP
    DependsOn: VPCGatewayAttachment
    Properties:
      Domain: vpc

  NatGateway:
    Type: AWS::EC2::NatGateway
    Properties:
      AllocationId: !GetAtt NatGatewayEIP.AllocationId
      SubnetId: !Ref PublicSubnet1
      Tags:
        - Key: Name
          Value: EKS-NAT-GW

  PublicRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Public-RT

  PublicRoute:
    Type: AWS::EC2::Route
    DependsOn: VPCGatewayAttachment
    Properties:
      RouteTableId: !Ref PublicRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      GatewayId: !Ref InternetGateway

  PrivateRouteTable:
    Type: AWS::EC2::RouteTable
    Properties:
      VpcId: !Ref VPC
      Tags:
        - Key: Name
          Value: Private-RT

  PrivateRoute:
    Type: AWS::EC2::Route
    Properties:
      RouteTableId: !Ref PrivateRouteTable
      DestinationCidrBlock: 0.0.0.0/0
      NatGatewayId: !Ref NatGateway

  PublicSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PublicSubnet1
      RouteTableId: !Ref PublicRouteTable

  PrivateSubnetAssociation:
    Type: AWS::EC2::SubnetRouteTableAssociation
    Properties:
      SubnetId: !Ref PrivateSubnet1
      RouteTableId: !Ref PrivateRouteTable
```
`SubnetRouteTableAssociation` 资源至关重要：在未关联的路由表中创建路由不会改变任一子网的路由。

完成经独立审查的部署后，请检查实际 ID 和路由。如果改用 CLI 创建 NAT gateway，请记录返回的 ID，并在创建路由前等待其状态变为 `nat-gateway-available`。如果 NAT 创建失败，必须停止工作流。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the Region}"
: "${VPC_ID:?Set the deployed VPC ID}"
aws ec2 describe-route-tables --region "$AWS_REGION" \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'RouteTables[].{Id:RouteTableId,Associations:Associations,Routes:Routes}'
aws ec2 describe-nat-gateways --region "$AWS_REGION" \
  --filter "Name=vpc-id,Values=$VPC_ID" \
  --query 'NatGateways[].{Id:NatGatewayId,Subnet:SubnetId,State:State}'
```
eksctl 的 `vpc.nat.gateway: Single` 适用于其托管 VPC 创建工作流，但会引入单 AZ 依赖。`HighlyAvailable` 会在每个 AZ 创建一个分区 NAT。这些选项无法修复任意现有子网的路由。对于实验堆栈，请先移除依赖工作负载/ENI，再仅删除由你创建的资源；确认 NAT 及其 EIP 已释放。

</details>

4. 哪种 Pod 设置会共享节点网络，而不是使用 Pod 分支 ENI？
   * A) 匹配的 Pod 标签
   * B) 匹配的 ServiceAccount 标签
   * C) hostNetwork: true
   * D) 选定的 SecurityGroupPolicy

<details>
<summary>显示答案</summary>

**答案：C) hostNetwork: true**

host-network Pod 会共享节点的网络 namespace 和安全组。Pod 安全组会为具有独立网络 namespace 的选定 Pod 使用分支 ENI。

此 Linux EC2 示例的前提条件包括：受支持的 trunking 实例类型、兼容的 VPC CNI、集群角色具有 `AmazonEKSVPCResourceController` 权限，以及 `ENABLE_POD_ENI=true`。EC2 `t` 系列和 EKS Auto Mode 不支持此功能。请核实 DNS、控制平面和应用规则、分支 ENI 容量以及 `POD_SECURITY_GROUP_ENFORCING_MODE`；不同模式下 SNAT 和策略行为有所不同。请使用附加组件所有者提供的配置工作流，而不是应用旧的 CNI 清单。

SecurityGroupPolicy 使用 `podSelector` **或** `serviceAccountSelector` 选择 Pod；选择 Pod 并不强制要求使用专门创建的 service account。`ENIConfig` 是自定义网络资源，仅使用 Pod 安全组时并不需要它。

对于下面的 service-account 选择器方案，请先创建专用的 `pod-sg-lab` namespace，将 SG 占位符替换为 VPC 中现有且经过审查的组，并满足前提条件。此休眠客户端用于演示选择功能；它并不能证明数据库连接正常。匹配的 ServiceAccount 标签和 Pod 的 `serviceAccountName` 都已设置。

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: pod-sg-lab
spec:
  serviceAccountSelector:
    matchLabels:
      role: db-client
  securityGroups:
    groupIds:
    - sg-REPLACE_WITH_REVIEWED_GROUP
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: db-client
  namespace: pod-sg-lab
  labels:
    role: db-client
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: pod-sg-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: db-client}
  template:
    metadata:
      labels: {app: db-client}
    spec:
      serviceAccountName: db-client
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
也可以将 `serviceAccountSelector` 替换为 `podSelector: {matchLabels: {app: db-client}}`。请确保策略和被选择的 Pod 位于同一 namespace。验证**新创建的** Pod 的分支 ENI，以及实际允许/拒绝的连接；创建策略不会追溯修改正在运行的 Pod。测试后只清理此实验 namespace 及其策略，不要删除仍被其他资源使用的 SG。

</details>



5. IPv4 前缀委派的主要容量优势是什么？
   * A) 保证 Pod 到 Pod 流量更快
   * B) 增加每个节点的 Pod IP 容量
   * C) 为每个 Pod 分配公有 IPv4 地址
   * D) 自动隔离网络

<details>
<summary>显示答案</summary>

**答案：B) 增加每个节点的 Pod IP 容量**

在 Linux IPv4 前缀模式下，一个 `/28`（16 个地址）会占用一个 ENI 辅助地址槽位。一个 ENI 上可以附加多个前缀；ENI 数量上限本身不会增加。在 kubelet 和资源限制允许的情况下，这可以提高基于 IP 的 Pod 密度，并减少地址分配 API 调用。

对于 `m5.large`，常规辅助 IP 计算结果为 29 个 Pod。采用前缀模式的兼容托管节点组可以使用建议的 `maxPods` 值 110，而不是不受限制地“超过 110”。理论地址槽位并不代表应用容量保证。

**前提条件和权衡：**

* 使用受支持的 Nitro 实例和兼容的 CNI（历史上的 Linux IPv4 最低版本为 1.9.0；应选择当前受支持的版本）。
* 子网需要连续的 `/28` 地址块。即使有许多空闲的独立 IP，子网碎片化也可能导致 `InsufficientCidrBlocks`。子网 CIDR 预留可以保留前缀空间。
* 前缀以地址块的形式占用真实子网地址。它不会扩大 CIDR，也不保证降低 IP 消耗、提高利用率或降低成本。
* `WARM_PREFIX_TARGET` 指定备用前缀数。`WARM_IP_TARGET` 指定备用 IP 数；`MINIMUM_IP_TARGET` 设置最低总分配量。配置后，后两项会覆盖 `WARM_PREFIX_TARGET`。请根据启动延迟和未使用地址消耗进行调整。
* 规划替换节点组，并以受控方式执行 cordon/drain 迁移。不要只切换变量并重启所有 Pod。检查 PDB、卷、备用容量和回滚方案；移除旧组前先验证新节点。

以下是**新建集群的配置示例**，不是现有集群的更新命令。它使用私有 API 访问，因此管理员需要可路由的管理路径。如果未提供版本，则会选择兼容的 EKS 默认 CNI 版本；部署前请记录并审查实际解析出的版本。`withOIDC` 会参与 eksctl 的 CNI IAM 集成；请审查最终生成的角色。容量上下限本身不会安装 autoscaler。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: prefix-demo
  region: us-west-2
  version: "1.36"
vpc:
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
iam:
  withOIDC: true
addons:
- name: vpc-cni
  configurationValues: |
    {"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
managedNodeGroups:
- name: prefix-linux
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  privateNetworking: true
  disableIMDSv1: true
```

</details>

6. 哪个 Kubernetes 对象包含 CoreDNS 使用的 Corefile？
   * A) 节点安全组
   * B) coredns ConfigMap
   * C) StorageClass
   * D) PodDisruptionBudget

<details>
<summary>显示答案</summary>

**答案：B) coredns ConfigMap**

`coredns` ConfigMap 包含 `data.Corefile`。正确的**配置所有者**取决于 CoreDNS 是 EKS 托管附加组件还是自管理组件。

对于托管附加组件，AWS 控制台和 `aws eks update-addon --configuration-values` 都可以自定义受支持的字段。直接编辑 ConfigMap 可能会在附加组件更新时被覆盖：请将完整的自定义 Corefile 存储在附加组件的 `corefile` 配置键中。保留现有配置键，并根据准确的附加组件版本检查 schema。

编辑前，请在新的本地工作目录中保存当前配置：

```bash
set -euo pipefail
: "${EXAMPLE_CLUSTER:?Set the cluster}"
: "${EXAMPLE_REGION:?Set the Region}"
: "${EXAMPLE_KUBECONFIG:?Set a private kubeconfig path}"
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --addon-name coredns > coredns-addon-before.json
COREDNS_VERSION=$(jq -er '.addon.addonVersion' coredns-addon-before.json)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --query configurationSchema --output text > coredns-schema.json
jq -e '(.addon.configurationValues // "{}") | fromjson | select(type == "object")' \
  coredns-addon-before.json > coredns-values-before.json
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  get configmap coredns -o json | jq -er '.data.Corefile' > Corefile.reviewed
```
编辑 `Corefile.reviewed` 时，请保留此安装所需的 Kubernetes zone、转发、`ready`、health 和 monitoring 插件。以下是彼此独立的自定义示例，并非替代 Corefile：

* 向现有 server block 添加静态记录；使用实际内部地址：

```text
hosts {
    10.0.0.1 example.com
    10.0.0.2 api.example.com
    fallthrough
}
```
* 条件转发器应使用独立的 server block；上游必须可访问，且不能回环到此 CoreDNS Service：

```text
example.org:53 {
    errors
    forward . 10.0.0.53
    cache 30
}
```
* 替换现有的 cache stanza，而不是添加重复项。`prefetch` 时长需要包含单位：

```text
cache {
    success 10000
    denial 5000
    prefetch 10 10m 10%
}
```
* 可选的错误类别查询日志记录（请评估日志量和敏感名称）：

```text
log {
    class error
}
```
`autopath` 是一个用于服务器端搜索路径补全的独立插件，并非 `kubernetes` 指令。将 `autopath off` 放在 Kubernetes block 中是无效的。要禁用现有的 `autopath @kubernetes`，请移除该指令；对于从未启用它的安装，不要添加该指令。

完成 schema 和语法审查后，更新**同一**附加组件版本：

```bash
# After reviewing the complete Corefile and existing configuration:
jq --rawfile corefile Corefile.reviewed '.corefile = $corefile' \
  coredns-values-before.json > coredns-values-reviewed.json
COREDNS_UPDATE_ID=$(aws eks update-addon \
  --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --addon-version "$COREDNS_VERSION" \
  --resolve-conflicts PRESERVE \
  --configuration-values file://coredns-values-reviewed.json \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name coredns --update-id "$COREDNS_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
响应仍可能是 `InProgress`。请持续检查此 update ID，直到状态变为 `Successful`；如果失败，请停止并检查错误后再进行其他更改。然后验证 Deployment 就绪状态、日志、内部 Service 查询和自定义 DNS 场景。如有需要，请通过同一配置所有者恢复保存的配置。

对于自管理的 CoreDNS，请通过其 GitOps/清单所有者编辑经过审查的 ConfigMap。启用 `reload` 时，ConfigMap 投影和 reload 间隔之后会检测到 Corefile 更改；不一定需要重启。请监控重新加载错误和 DNS 行为。Deployment 设置的更改可能仍需要 rollout。

**扩缩和资源**：如果所选版本满足 AWS 前提条件，EKS 托管 CoreDNS 支持 `autoScaling` 配置对象。只能保留一个负责管理副本数的控制器。以下 CPU HPA 是**自管理 CoreDNS 的替代方案**，需要 Metrics Server 和 CPU requests；不要与 EKS CoreDNS autoscaling 同时运行：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coredns-autoscaler
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
2–10 个副本和 60% 目标只是示例，并非测量得出的容量规划值。请检查内存、CPU 限流、缓存增长、拓扑和 DNS 延迟；应通过附加组件 schema 或自管理工作负载所有者更改资源，而不是按容器数组索引替换整个 resources 对象。

</details>

7. 对于共享一个 EKS 集群的可信团队，哪种组合有助于实现逻辑隔离？
   * A) 仅使用 Namespaces
   * B) Namespaces、RBAC、强制执行的策略和配额
   * C) 仅使用节点选择器
   * D) 共享 cluster-admin 角色

<details>
<summary>显示答案</summary>

**答案：B) Namespaces、RBAC、强制执行的策略和配额**

对于共享集群的互信团队，Namespaces 加上 RBAC、强制执行的网络策略和配额可以提供有效的逻辑隔离。但它们并非适用于恶意租户的通用解决方案。

平台管理员创建新的 `tenant-a`/`tenant-b` namespaces，并强制执行适当的 Pod Security Admission 策略（对于此 Linux EKS 1.36 示例，使用版本为 `v1.36` 的 Restricted 策略）。以下是 `tenant-a` 的策略集；请为 `tenant-b` 应用经过审查的等效策略。还需要为 `tenant-a-users` 配置经过身份验证的组映射。

应用程序权限是显式设置的。租户不能通过此 Role 直接更改 ResourceQuota、LimitRange、NetworkPolicy、Roles 或 RoleBindings。集群范围资源由平台负责管理。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-workloads
  namespace: tenant-a
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "deployments/scale", "statefulsets/scale"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["batch"]
  resources: ["jobs", "cronjobs"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "configmaps", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["pods", "pods/log", "events"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: tenant-a-access
  namespace: tenant-a
subjects:
- kind: Group
  name: tenant-a-users
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: tenant-workloads
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-boundary
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
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-a
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "20"
    persistentvolumeclaims: "30"
    secrets: "100"
    configmaps: "100"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: tenant-limits
  namespace: tenant-a
spec:
  limits:
  - default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 256Mi
    type: Container
```
**限制和验证：**

* 创建工作负载仍可能使用可访问的 service accounts，并挂载该 namespace 中的 Secrets。此 Role 并不是租户内部的 Secret 机密性边界。请通过准入策略强制限制允许的身份、挂载和安全设置；平台凭证应保留在租户 namespace 之外。
* DNS 规则假设 `kube-system` 中的常规 CoreDNS Pod 使用 `k8s-app=kube-dns` 标签。若使用 NodeLocal DNSCache 或其他 DNS 路径，请相应调整并测试。此规则允许 DNS 查询，而不是允许访问所有系统 Pod；它不会隐藏跨 namespace 的 DNS 名称。
* 配额会限制获准资源的请求量/数量；它们不会预留物理节点、保证带宽或消除 noisy neighbor。LimitRange 值是示例默认值。
* 在启用租户之前，请使用租户身份验证有效权限和策略执行情况，包括允许的连接、被拒绝的跨租户连接以及触发配额拒绝的场景。
* 专用节点组可以减少某些共享，但节点选择器/污点本身不是安全边界。若要实现更强隔离，请评估沙箱运行时、虚拟控制平面或独立集群/账户/网络，同时考虑其共享依赖和运维成本。

共享 namespace 可以降低控制平面开销，并简化集中运维。设计取决于所需的隔离级别，而不存在普遍“最优”的方案。

</details>

8. 哪一项本身不会改变 EC2 实例类型的技术容量？
   * A) vCPU 和内存大小
   * B) 网络和存储限制
   * C) 仅用于显示的名称标签
   * D) ENI 和地址限制

<details>
<summary>显示答案</summary>

**答案：C) 仅用于显示的名称标签**

选择实例时，必须考虑 CPU、内存、加速器需求、架构兼容的镜像/AMI 和驱动程序、Pod 密度、网络带宽、EBS/实例存储性能、AZ 可用性、中断容忍度和成本。Kubernetes 版本可能会通过受支持的 AMI、驱动程序和功能产生影响；不能忽略它。

以下原始系列示例用于说明工作负载类型，而非当前价格/性能排名。`m5` 是通用型，`r5` 是内存优化型，`c5` 是计算优化型。Graviton 替代方案要求镜像和依赖项兼容 Arm 架构。GPU 工作负载还需要适当的加速 AMI 和 device plugin。实例存储中的数据是临时数据；仅靠标签无法保证数据库持久性或放置位置。

以下是针对现有且经过审查的集群的**可选节点组配置文件**（`eksctl create nodegroup -f ...`），使用未占用的组名称和具有所需出口/端点的私有子网。请检查实际 Region/AZ 是否提供相应实例。容量上下限不会安装 Cluster Autoscaler；批处理组的容量设为零时，需要正确配置 autoscaler 或手动扩缩。

**Web 服务器**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: web-servers
  instanceType: m5.large
  minSize: 2
  maxSize: 10
  labels:
    role: web
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**数据库工作负载**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: database-nodes
  instanceType: r5.xlarge
  minSize: 3
  maxSize: 5
  labels:
    role: database
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**批处理**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: batch-processors
  instanceType: c5.2xlarge
  minSize: 0
  maxSize: 20
  labels:
    role: batch
  amiFamily: AmazonLinux2023
  privateNetworking: true
```

**可中断的 Spot worker**

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: spot-workers
  instanceTypes:
  - m5.large
  - m5a.large
  - m5d.large
  - m5ad.large
  minSize: 2
  maxSize: 10
  spot: true
  labels:
    lifecycle: spot
  amiFamily: AmazonLinux2023
  privateNetworking: true
```
EKS 提供 14 个月的标准版本支持，随后提供 12 个月的扩展支持。请与上游 Kubernetes 发行版本分开检查 EKS 支持日历、升级要求和附加组件兼容性。这些示例不代表经过测量的成本节省或容量。

</details>

9. 哪个 Kubernetes 对象会在 drain 期间限制自愿驱逐 Pod？
   * A) StorageClass
   * B) PodDisruptionBudget
   * C) ConfigMap
   * D) IngressClass

<details>
<summary>显示答案</summary>

**答案：B) PodDisruptionBudget**

PDB 会通过 Eviction API 限制自愿驱逐。它只是更新策略的一部分，并不保证可用性。PDB 无法阻止节点故障、直接删除 Pod 或 Deployment 自身的滚动更新。

对于一个经过审查、包含三个副本且标签为 `app=my-app` 的 `update-lab` Deployment，此示例仅允许在至少保留两个符合条件的健康 Pod 时执行驱逐：

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
  namespace: update-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: my-app
```
另一种写法是 `maxUnavailable: "50%"`；两个预算字段只能指定一个。百分比会**向上取整**，因此这允许 3 个 Pod 中有 2 个不可用，或 1 个 Pod 中有 1 个不可用。这并不保证至少一半的 Pod 保持运行。应根据仲裁要求、就绪状态、工作负载行为和可调度的备用容量来选择预算。

托管节点组采用 `DEFAULT` 更新时，会在对选定旧节点进行 drain 前先启动替代容量。`MINIMAL` 则先终止选定旧节点，以减少临时容量需求。`maxUnavailable` 控制同时不可用的节点数；PDB 会单独限制 Pod 驱逐。不要将 `--force` 作为 drain 被阻止时的常规应对方式，因为它可能绕过 Pod 驱逐保护。

配置节点更新策略，并在启动版本更新**之前**等待此特定更新成功：

```bash
set -euo pipefail
NODEGROUP_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --update-config '{"maxUnavailable":1,"updateStrategy":"DEFAULT"}' \
  --query update.id --output text)
aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$NODEGROUP_UPDATE_ID" \
  --query 'update.{status:status,errors:errors}'
```
持续轮询此 ID 的 `describe-update`，直到状态为 `Successful`，并明确处理 `Failed`/`Cancelled`。原先的 eksctl `update nodegroup --max-unavailable` 命令不能作为受支持的替代方案。检查实际 PDB `disruptionsAllowed`、就绪状态、应用健康状况和卷迁移；三个副本只是示例，并非通用最低要求。

</details>

10. 哪个控制器会建议或更改 Pod 的 CPU 和内存 requests？
   * A) Cluster Autoscaler
   * B) Karpenter
   * C) Horizontal Pod Autoscaler
   * D) Vertical Pod Autoscaler

<details>
<summary>显示答案</summary>

**答案：D) Vertical Pod Autoscaler**

VPA 会建议或更新 Pod 资源 requests。HPA 会更改副本数。**两者**都可能间接改变节点需求；两者都不会直接管理托管节点组的 ASG。

| 组件 | 管理对象 |
| --- | --- |
| Cluster Autoscaler | 根据可调度性和安全移除条件，调整已发现现有节点组/ASG 的期望容量 |
| Karpenter | 通过 NodePools 和 EC2NodeClasses 选择并管理自己的 NodeClaims/EC2 容量；不管理托管节点组 ASG |
| HPA / KEDA | 根据资源/自定义/外部指标或事件调整工作负载副本数 |
| VPA | 根据更新模式提供 Pod 资源建议/requests |

**Cluster Autoscaler**：使用与集群相同的 Kubernetes 次要版本。对于 EKS 1.36 示例，chart 9.59.0 必须显式使用镜像 `v1.36.1`（其默认镜像为 1.35.0）。首先为 `cluster-autoscaler` ServiceAccount 配置专用身份，并配置经过审查、限定标签范围的 IAM 权限和 ASG 发现标签。安装前请渲染并检查 RBAC、镜像和参数：

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update autoscaler
helm template cluster-autoscaler autoscaler/cluster-autoscaler \
  --version 9.59.0 --namespace kube-system \
  --set-string autoDiscovery.clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string awsRegion="${EXAMPLE_REGION:?}" \
  --set-string image.tag=v1.36.1 \
  --set rbac.serviceAccount.create=false \
  --set-string rbac.serviceAccount.name=cluster-autoscaler \
  > cluster-autoscaler-reviewed.yaml
```
不要轻率地禁用本地存储保护措施，也不要让 ASG 的 target-tracking/predictive 策略与 Cluster Autoscaler 同时控制同一预期容量。

**Karpenter 替代方案**：单独安装并授权兼容的控制器。将 AMI ID、节点角色和发现标签值替换为该集群中经过审查的资源；AMI 必须兼容 AL2023、Kubernetes 版本和架构。请固定 AMI ID 或经过测试的版本化别名，而不要静默选择 `al2023@latest`。以下限制和整合时间仅为示例，并非实测容量规划或预置速度保证。

```yaml
# Karpenter NodePool (karpenter.sh/v1)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
# Karpenter EC2NodeClass (karpenter.k8s.aws/v1)
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  amiFamily: AL2023
  amiSelectorTerms:
    - id: ami-REPLACE_WITH_VERIFIED_AL2023_AMI
  role: KarpenterNodeRole-my-cluster
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```
**HPA**：此示例需要在 `autoscaling-lab` 中已有 `my-app` Deployment、Metrics Server 和 CPU requests：

```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app-hpa
  namespace: autoscaling-lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
**VPA**：首先安装 VPA CRD/控制器。先使用仅提供建议的模式，并在选择明确受支持的更新模式前检查建议：

```yaml
# Vertical Pod Autoscaler
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
  namespace: autoscaling-lab
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"
  resourcePolicy:
    containerPolicies:
    - containerName: '*'
      minAllowed:
        cpu: 100m
        memory: 50Mi
      maxAllowed:
        cpu: 1
        memory: 500Mi
      controlledResources: ["cpu", "memory"]
```
`Off` 不会更改 Pod 资源。应用建议可能需要重新创建 Pod，或需要受支持的原地调整，具体取决于 VPA/Kubernetes 版本和配置；不要承诺每种模式都会重启。CPU 利用率 HPA 管理同一工作负载时更新 CPU requests，会通过利用率分母产生反馈。仅提供建议的示例在审查并协调设计之前避免了此冲突。

</details>

## 实践练习

### 练习 1：在 EKS 集群中实施网络策略

**场景**：允许 frontend → backend 和 backend → database，同时拒绝 frontend → database。使用 AWS VPC CNI 分配 IP，以保留原本的 Calico 学习目标。

**范围**：现有的、可丢弃的 Linux IPv4 EKS 集群；没有冲突的全局/层级策略；使用标准 CoreDNS；并且由管理员审查 Calico 安装。这是连通性练习，不是生产微服务/数据库方案。本次审计未执行云端安装和流量测试。


<details>
<summary>显示解决方案</summary>

**1. 准备策略引擎**。按照官方 Calico EKS **Amazon VPC networking** 路径操作。通过其配置所有者禁用原生 AWS VPC CNI NetworkPolicy；它与 Calico 执行功能冲突。保留 `aws-node` 网络配置。启用其 `ANNOTATE_POD_IP=true` 设置，并授予其 ServiceAccount patch Pod 的权限。以下专用 RBAC 示例添加了该权限，不会将格式错误的 YAML 追加到附加组件的 ClusterRole 中：

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-cni-pod-annotation
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-cni-pod-annotation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-cni-pod-annotation
subjects:
- kind: ServiceAccount
  name: aws-node
  namespace: kube-system
```
保存并检查 RBAC，然后仅将它应用于预期的 `aws-node` ServiceAccount；通过托管附加组件或自管理清单所有者配置环境变量。在 rollout 和注释行为正常之前不要继续。如果已安装 Calico，请检查并复用现有安装，而不要运行以下新安装命令。

```bash
# Download pinned manifests for inspection; do not overwrite an existing installation.
curl --fail --location --output calico-crds.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
curl --fail --location --output tigera-operator.yaml \
  https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
# After review, on the intended new lab installation:
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" create -f calico-crds.yaml
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create -f tigera-operator.yaml
```
operator CRD 建立后，创建以下经过审查的 `Installation` 和 `APIServer` 资源。仅安装 operator 不会配置 AWS VPC 网络。`projectcalico.org/v3` 策略示例需要 API server：

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
```

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get tigerastatus
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get apiservice v3.projectcalico.org
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n calico-system get pods
```
要求 Calico 组件和聚合 API 均可用，然后在下方验证实际执行情况。节点 `Ready` 状态本身并不足够。此练习不需要可选的 Goldmane/Whisker UI。

**2. 创建自有 namespace 和临时数据库凭证**。后续代码片段请在同一个 Bash 会话中运行。namespace 名称和 UID 都会被记录，以确保清理时不会有意针对其他 namespace：

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed lab cluster kubeconfig}"
NETWORK_LAB_DIR=$(mktemp -d /tmp/eks-calico-lab.XXXXXX)
NETWORK_NAMESPACE="calico-quiz-$(date +%s)-$$"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$NETWORK_NAMESPACE"
NETWORK_NAMESPACE_UID=$(kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
  get namespace "$NETWORK_NAMESPACE" -o jsonpath='{.metadata.uid}')
: "${NETWORK_NAMESPACE_UID:?}"
jq -n --arg name "$NETWORK_NAMESPACE" --arg uid "$NETWORK_NAMESPACE_UID" \
  '{namespace:$name,namespaceUID:$uid}' > "$NETWORK_LAB_DIR/ownership.json"
openssl rand -hex 32 > "$NETWORK_LAB_DIR/db-password"
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
  create secret generic database-auth \
  --from-file=password="$NETWORK_LAB_DIR/db-password"
```
**3. 部署三个层级**。Python HTTP server 充当 frontend/backend，使两个容器都能使用诊断 TCP 客户端。PostgreSQL 17 镜像使用 `POSTGRES_PASSWORD_FILE` 和 namespace 本地 Secret；它不会执行外部数据库操作。数据库的 `emptyDir` 会在 Pod 替换时**丢失**。不要在这里放置有价值的数据。保留数据库镜像的初始化行为；这不是符合 Restricted 配置文件的生产数据库清单。主要版本镜像标签可变：如需可重复运行，请记录解析后的摘要。

```bash
# The HTTP layers are diagnostic stand-ins, not business applications.
for tier in frontend backend; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $tier
spec:
  replicas: 1
  selector:
    matchLabels: {app: $tier}
  template:
    metadata:
      labels: {app: $tier}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: diagnostic
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: $tier
spec:
  selector: {app: $tier}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
done

kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database
spec:
  replicas: 1
  selector:
    matchLabels: {app: database}
  template:
    metadata:
      labels: {app: database}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      containers:
      - name: database
        image: postgres:17-alpine
        env:
        - name: POSTGRES_PASSWORD_FILE
          value: /run/secrets/postgres/password
        ports:
        - containerPort: 5432
        readinessProbe:
          exec:
            command: [pg_isready, -U, postgres]
          initialDelaySeconds: 5
        resources:
          requests: {cpu: 100m, memory: 128Mi}
          limits: {cpu: 500m, memory: 256Mi}
        volumeMounts:
        - {name: data, mountPath: /var/lib/postgresql/data}
        - {name: auth, mountPath: /run/secrets/postgres, readOnly: true}
      volumes:
      - name: data
        emptyDir: {}
      - name: auth
        secret: {secretName: database-auth}
---
apiVersion: v1
kind: Service
metadata:
  name: database
spec:
  selector: {app: database}
  ports:
  - {port: 5432, targetPort: 5432, protocol: TCP}
EOF

for tier in frontend backend database; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    rollout status "deployment/$tier" --timeout=180s
done
```
**4. 建立基线**。应用策略前，三个 TCP 路径和 DNS 都必须正常。5432 端口连接成功只证明 TCP 连接可用，并不能证明 SQL 身份验证或应用行为正常。

```bash
# Distinguish DNS failure from TCP denial. Status 42 means a TCP failure.
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" \
    exec "deployment/$1" -c diagnostic -- python -c '
import socket, sys
host, port = sys.argv[1], int(sys.argv[2])
try:
    address = socket.gethostbyname(host)
except OSError as error:
    print("DNS failure:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, port), timeout=3)
    connection.close()
except OSError as error:
    print("TCP connection failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP connection succeeded")
' "$2" "$3"
}

# Baseline: all three must succeed BEFORE the policy is applied.
check_tcp frontend backend 8080
check_tcp backend database 5432
check_tcp frontend database 5432
```
**5. 应用并测试策略**。所选 Pod 会在两个方向上被隔离；未匹配的流量会被拒绝。显式规则允许两个应用流量路径以及 UDP/TCP DNS。要访问实验 namespace 之外的 CoreDNS，需要 namespace 选择器。测试前，请根据 NodeLocal DNSCache 或不同标签调整 DNS 规则。

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NETWORK_NAMESPACE" create -f - <<'EOF'
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: tier-boundaries
spec:
  selector: all()
  types: [Ingress, Egress]
  ingress:
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
  egress:
  - action: Allow
    protocol: UDP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    destination:
      namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
      selector: k8s-app == 'kube-dns'
      ports: [53]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'frontend'
    destination:
      selector: app == 'backend'
      ports: [8080]
  - action: Allow
    protocol: TCP
    source:
      selector: app == 'backend'
    destination:
      selector: app == 'database'
      ports: [5432]
EOF

# Allow policy propagation, then verify positive controls and the denied path.
POLICY_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp frontend backend 8080
  check_tcp backend database 5432
  if check_tcp frontend database 5432; then
    sleep 2
  else
    result=$?
    if [ "$result" -ne 42 ]; then
      printf '%s\n' 'DNS/exec failure is not proof of policy denial.' >&2
      exit 1
    fi
    # Database availability must still hold after the negative observation.
    check_tcp backend database 5432
    POLICY_VERIFIED=true
    break
  fi
done
[ "$POLICY_VERIFIED" = true ] || {
  printf '%s\n' 'Expected denial was not observed; inspect policy enforcement.' >&2
  exit 1
}
```
策略传播是异步的。超时、DNS 失败、缺少诊断二进制文件或数据库不可用，本身都不能证明隔离已成功。此流程先使用正常基线和正向对照；如果观察结果不同，请调查其他策略/路由。

**6. 清理**。确认 UID 后，仅删除自有 namespace。这样会移除测试工作负载、策略、Secret 和临时数据，但不会移除集群范围的 Calico 安装。练习结束后，请删除本地密码文件。除非另有经管理员审查的回滚流程负责，否则保留共享 CNI/RBAC 配置。

```bash
CURRENT_NETWORK_UID=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get namespace "${NETWORK_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_NETWORK_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_NETWORK_UID" = "${NETWORK_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" \
    delete namespace "$NETWORK_NAMESPACE" --wait=true || exit 1
else
  printf '%s\n' 'Namespace UID changed; no deletion attempted.' >&2
  exit 1
fi
```

</details>

### 练习 2：在 EKS 集群中配置 IRSA 和 S3 访问

**场景**：使用 IRSA 而不是节点角色，为一个工作负载授予对现有 S3 bucket 中已批准 `training/` 前缀的只读访问权限。验证实际使用的角色身份，并与一个特意不配置凭证的 Pod 进行比较。

**前提条件**：Bash、jq、AWS CLI、eksctl 和 kubectl；现有且已获授权的 EKS 集群；对新 namespace 和 IAM 角色的管理员访问权限；已批准的非敏感现有 S3 对象。此商业分区示例假设对象不需要额外的客户 KMS 要求。Bucket/KMS 策略、SCP、DNS、STS 和 S3 网络路径可能还会带来其他要求。不会创建、更改或删除任何 S3 对象。


<details>
<summary>显示解决方案</summary>

**1. 限定实验范围并验证 OIDC**。设置 `EXAMPLE_CLUSTER`、`EXAMPLE_REGION`、`S3_BUCKET` 和 `S3_TEST_KEY`（位于 `training/` 下）。OIDC provider 是集群共享基础设施；清理时不要删除它。如果创建 namespace 或验证 provider 失败，请停止。

```bash
set -euo pipefail
umask 077
# Commercial AWS partition example; use an existing approved S3 training prefix.
: "${EXAMPLE_CLUSTER:?}"
: "${EXAMPLE_REGION:?}"
: "${S3_BUCKET:?Existing bucket containing the approved training object}"
: "${S3_TEST_KEY:?Existing non-sensitive object key under training/}"
case "$S3_TEST_KEY" in training/*) ;; *) printf '%s\n' 'Use a training/ key.' >&2; exit 1 ;; esac
IRSA_LAB_DIR=$(mktemp -d /tmp/eks-irsa-lab.XXXXXX)
: "${IRSA_LAB_DIR:?}"
IRSA_LAB_ID="irsa-quiz-$(date +%s)-$$"
IRSA_NAMESPACE="$IRSA_LAB_ID"
IRSA_ROLE_NAME="$IRSA_LAB_ID"
IRSA_SERVICE_ACCOUNT=s3-reader
IRSA_KUBECONFIG="$IRSA_LAB_DIR/kubeconfig"

aws sts get-caller-identity --output json > "$IRSA_LAB_DIR/caller.json" || exit 1
IRSA_ACCOUNT_ID=$(jq -er '.Account' "$IRSA_LAB_DIR/caller.json") || exit 1
jq -e '.Arn | startswith("arn:aws:")' "$IRSA_LAB_DIR/caller.json" >/dev/null || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$IRSA_LAB_DIR/cluster.json" || exit 1
IRSA_ISSUER=$(jq -er '.identity.oidc.issuer' "$IRSA_LAB_DIR/cluster.json") || exit 1
case "$IRSA_ISSUER" in https://*) ;; *) printf '%s\n' 'Invalid OIDC issuer.' >&2; exit 1 ;; esac
IRSA_ISSUER_HOST="${IRSA_ISSUER#https://}"
IRSA_PROVIDER_ARN="arn:aws:iam::$IRSA_ACCOUNT_ID:oidc-provider/$IRSA_ISSUER_HOST"

aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$IRSA_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create namespace "$IRSA_NAMESPACE" || exit 1
IRSA_NAMESPACE_UID=$(kubectl --kubeconfig "$IRSA_KUBECONFIG" \
  get namespace "$IRSA_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${IRSA_NAMESPACE_UID:?}"
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "$IRSA_NAMESPACE_UID" \
  '{namespace:$namespace,namespaceUID:$uid}' > "$IRSA_LAB_DIR/ownership.json" || exit 1

# The cluster's provider is shared infrastructure; eksctl checks/associates it.
eksctl utils associate-iam-oidc-provider --cluster "$EXAMPLE_CLUSTER" \
  --region "$EXAMPLE_REGION" --approve || exit 1
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$IRSA_PROVIDER_ARN" \
  --output json > "$IRSA_LAB_DIR/provider.json" || exit 1
jq -e '.ClientIDList | index("sts.amazonaws.com") != null' \
  "$IRSA_LAB_DIR/provider.json" >/dev/null || exit 1
```
**2. 创建唯一且范围受限的角色**。信任关系要求同时满足 `aud=sts.amazonaws.com` 和准确的 namespace/ServiceAccount `sub`。角色创建失败时停止附加策略；记录不可变的 RoleId，以便清理。

```bash
jq -n --arg provider "${IRSA_PROVIDER_ARN:?}" --arg issuer "${IRSA_ISSUER_HOST:?}" \
  --arg subject "system:serviceaccount:${IRSA_NAMESPACE:?}:${IRSA_SERVICE_ACCOUNT:?}" \
  '{
    Version:"2012-10-17",
    Statement:[{
      Effect:"Allow",
      Principal:{Federated:$provider},
      Action:"sts:AssumeRoleWithWebIdentity",
      Condition:{StringEquals:{
        ($issuer+":aud"):"sts.amazonaws.com",
        ($issuer+":sub"):$subject
      }}
    }]
  }' > "${IRSA_LAB_DIR:?}/trust.json" || exit 1

jq -n --arg bucket "${S3_BUCKET:?}" \
  '{
    Version:"2012-10-17",
    Statement:[
      {
        Effect:"Allow",Action:"s3:ListBucket",Resource:("arn:aws:s3:::"+$bucket),
        Condition:{StringLike:{"s3:prefix":["training/","training/*"]}}
      },
      {
        Effect:"Allow",Action:"s3:GetObject",
        Resource:("arn:aws:s3:::"+$bucket+"/training/*")
      }
    ]
  }' > "$IRSA_LAB_DIR/s3-policy.json" || exit 1

# Stop on creation failure; never attach this policy to a pre-existing role.
aws iam create-role --role-name "${IRSA_ROLE_NAME:?}" \
  --assume-role-policy-document "file://$IRSA_LAB_DIR/trust.json" \
  --tags "Key=TrainingLab,Value=${IRSA_LAB_ID:?}" \
  --query Role --output json > "$IRSA_LAB_DIR/created-role.json" || exit 1
IRSA_ROLE_ARN=$(jq -er '.Arn' "$IRSA_LAB_DIR/created-role.json") || exit 1
IRSA_ROLE_ID=$(jq -er '.RoleId' "$IRSA_LAB_DIR/created-role.json") || exit 1
jq -n --arg namespace "$IRSA_NAMESPACE" --arg uid "${IRSA_NAMESPACE_UID:?}" \
  --arg roleName "$IRSA_ROLE_NAME" --arg roleArn "$IRSA_ROLE_ARN" --arg roleId "$IRSA_ROLE_ID" \
  '{namespace:$namespace,namespaceUID:$uid,roleName:$roleName,roleARN:$roleArn,roleID:$roleId}' \
  > "$IRSA_LAB_DIR/ownership.json" || exit 1
aws iam put-role-policy --role-name "$IRSA_ROLE_NAME" \
  --policy-name ScopedTrainingS3Read \
  --policy-document "file://$IRSA_LAB_DIR/s3-policy.json" || exit 1
```
**3. 部署并验证**。如果测试失败，请留出时间等待 IAM 传播后再重试。三个容器分别检查身份、前缀列举计数和对象长度；不会记录对象内容或凭证。身份必须与新建角色匹配；否则，S3 操作成功也可能是因为使用了权限更广泛的节点角色。

```bash
# JSON construction preserves literal object keys and prevents YAML interpolation errors.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg sa "${IRSA_SERVICE_ACCOUNT:?}" \
  --arg role "${IRSA_ROLE_ARN:?}" --arg region "${EXAMPLE_REGION:?}" \
  --arg bucket "${S3_BUCKET:?}" --arg key "${S3_TEST_KEY:?}" '
  {
    apiVersion:"v1",kind:"List",items:[
      {
        apiVersion:"v1",kind:"ServiceAccount",
        metadata:{name:$sa,namespace:$ns,annotations:{
          "eks.amazonaws.com/role-arn":$role,
          "eks.amazonaws.com/sts-regional-endpoints":"true"
        }}
      },
      {
        apiVersion:"v1",kind:"Pod",metadata:{name:"irsa-check",namespace:$ns},
        spec:{
          serviceAccountName:$sa,nodeSelector:{"kubernetes.io/os":"linux"},restartPolicy:"Never",
          containers:[
            {name:"identity",args:["--region",$region,"sts","get-caller-identity"]},
            {name:"list-prefix",args:["--region",$region,"s3api","list-objects-v2","--bucket",$bucket,
              "--prefix","training/","--max-keys","1","--query","KeyCount","--output","json"]},
            {name:"object-metadata",args:["--region",$region,"s3api","head-object","--bucket",$bucket,
              "--key",$key,"--query","ContentLength","--output","json"]}
          ] | map(.+{
            image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",command:["aws"],
            resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
          })
        }
      }
    ]
  }' > "${IRSA_LAB_DIR:?}/workload.json" || exit 1
kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" create -f "$IRSA_LAB_DIR/workload.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Succeeded pod/irsa-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs irsa-check -c identity > "$IRSA_LAB_DIR/pod-identity.json" || exit 1
jq -e --arg account "${IRSA_ACCOUNT_ID:?}" --arg role "${IRSA_ROLE_NAME:?}" \
  '.Account == $account and (.Arn | startswith("arn:aws:sts::"+$account+":assumed-role/"+$role+"/"))' \
  "$IRSA_LAB_DIR/pod-identity.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c list-prefix
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" logs irsa-check -c object-metadata
```
**4. 受控的负向比较**。新 namespace 的默认 ServiceAccount 不得带有 IRSA 注释或 EKS Pod Identity 关联，也不得注入其他凭证。在此测试客户端中禁用 IMDS 回退，并要求出现特定的缺少凭证错误。随机网络错误或授权错误不能作为有效的负向结果。

```bash
# Controlled comparison: no IRSA, no Pod Identity association, no IMDS fallback.
jq -n --arg ns "${IRSA_NAMESPACE:?}" --arg region "${EXAMPLE_REGION:?}" '
{
  apiVersion:"v1",kind:"Pod",
  metadata:{name:"no-role-check",namespace:$ns},
  spec:{
    automountServiceAccountToken:false,
    serviceAccountName:"default",
    nodeSelector:{"kubernetes.io/os":"linux"},
    restartPolicy:"Never",
    containers:[{
      name:"identity",image:"public.ecr.aws/aws-cli/aws-cli:2.36.43",
      command:["aws"],args:["--region",$region,"sts","get-caller-identity"],
      env:[{name:"AWS_EC2_METADATA_DISABLED",value:"true"}],
      resources:{requests:{cpu:"100m",memory:"128Mi"},limits:{memory:"256Mi"}}
    }]
  }
}' > "${IRSA_LAB_DIR:?}/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" create -f "$IRSA_LAB_DIR/negative-pod.json" || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  wait --for=jsonpath='{.status.phase}'=Failed pod/no-role-check --timeout=180s || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get pod no-role-check -o json > "$IRSA_LAB_DIR/negative-status.json" || exit 1
jq -e '.status.containerStatuses[] | select(.name=="identity") |
  .state.terminated.exitCode == 255' "$IRSA_LAB_DIR/negative-status.json" >/dev/null || exit 1
kubectl --kubeconfig "$IRSA_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  logs no-role-check -c identity > "$IRSA_LAB_DIR/negative-log.txt" || exit 1
grep -F 'Unable to locate credentials' "$IRSA_LAB_DIR/negative-log.txt" >/dev/null || {
  printf '%s\n' 'Unexpected failure: inspect the saved log; do not claim isolation.' >&2
  exit 1
}
```
这是凭证提供程序对比测试，并不能证明任意 Pod 都无法访问 IMDS，也不能证明容器构成安全边界。请单独限制节点凭证。IRSA 使用投射的 web-identity token 和 STS 临时凭证；兼容的 SDK 会刷新这些凭证。不要转储所有 `AWS_*` 环境变量或 token 文件。

**5. 仅清理自有资源**。保留记录的 namespace UID 和 IAM RoleId。受保护的清理操作会移除实验 namespace、其内联策略及唯一角色；会保留 S3 bucket/object、共享 OIDC provider 和集群。如果设置只部分成功，请检查 `ownership.json`，仅清理其中实际记录的资源。

```bash
# Recover the recorded values from ownership.json if this is a later shell.
IRSA_CLEANUP_NAMESPACE_OK=false
if CURRENT_IRSA_UID=$(kubectl --kubeconfig "${IRSA_KUBECONFIG:?}" \
  get namespace "${IRSA_NAMESPACE:?}" --ignore-not-found -o jsonpath='{.metadata.uid}'); then
  if [ -z "$CURRENT_IRSA_UID" ]; then
    IRSA_CLEANUP_NAMESPACE_OK=true
  elif [ "$CURRENT_IRSA_UID" = "${IRSA_NAMESPACE_UID:?Recorded UID required}" ]; then
    if kubectl --kubeconfig "$IRSA_KUBECONFIG" delete namespace "$IRSA_NAMESPACE" --wait=true; then
      IRSA_CLEANUP_NAMESPACE_OK=true
    else
      exit 1
    fi
  else
    printf '%s\n' 'Namespace UID mismatch; stop and inspect.' >&2
    exit 1
  fi
else
  printf '%s\n' 'Namespace lookup failed; stop and inspect.' >&2
  exit 1
fi

if [ "$IRSA_CLEANUP_NAMESPACE_OK" = true ]; then
  CURRENT_IRSA_ROLE_JSON=$(aws iam get-role --role-name "${IRSA_ROLE_NAME:?}" \
    --query Role --output json) || exit 1
  CURRENT_IRSA_ROLE_ID=$(printf '%s' "$CURRENT_IRSA_ROLE_JSON" | jq -er '.RoleId') || exit 1
  if [ "$CURRENT_IRSA_ROLE_ID" = "${IRSA_ROLE_ID:?Recorded IAM RoleId required}" ]; then
    IRSA_INLINE_POLICIES=$(aws iam list-role-policies --role-name "$IRSA_ROLE_NAME" \
      --query PolicyNames --output json) || exit 1
    printf '%s' "$IRSA_INLINE_POLICIES" |
      jq -e 'all(.[]; . == "ScopedTrainingS3Read")' >/dev/null || exit 1
    if printf '%s' "$IRSA_INLINE_POLICIES" | jq -e 'index("ScopedTrainingS3Read") != null' >/dev/null; then
      aws iam delete-role-policy --role-name "$IRSA_ROLE_NAME" \
        --policy-name ScopedTrainingS3Read || exit 1
    fi
    aws iam delete-role --role-name "$IRSA_ROLE_NAME"
  else
    printf '%s\n' 'IAM RoleId mismatch; no IAM deletion attempted.' >&2
    exit 1
  fi
fi
```

</details>

## 高级主题

以下问题涉及 Amazon EKS 集群创建的高级主题。本部分考查你对 EKS 集群创建高级概念和最佳实践的理解。

1. 以下哪项**并非** IPv4 前缀委派所能保证？
   * A) 一个前缀占用一个 ENI 地址槽位
   * B) 一个节点上可以容纳更多 IP 容量
   * C) 每个应用程序都会更快就绪
   * D) 需要连续的子网地址块

<details>
<summary>显示答案</summary>

**答案：C) 每个应用程序都会更快就绪**

前缀委派可以降低地址分配延迟：将另一个前缀附加到现有 ENI，可以避免部分 ENI 创建/附加工作。AWS 记录了此项优势，因此原先关于前缀委派无法缩短启动时间且必然增加路由开销的解释不正确。

端到端 Pod 就绪仍取决于调度、节点启动、镜像拉取、卷附加、初始化、探针和应用程序启动。此处未提供前后基准测试，本次审计也未执行相关测试。不要推断固定的延迟改善幅度，也不要臆造减速原因。

每个 IPv4 `/28` 会占用一个辅助地址槽位，并从连续子网地址块中消耗 16 个地址。在 `maxPods`、计算资源和子网空间允许的情况下，它会提高每个节点的 IP 容量。它不会扩大 CIDR，也不保证减少已分配的地址。Warm-pool 设置会在备用地址消耗和地址分配就绪程度之间产生权衡。

请参考基本问题 5 中的前提条件和新节点组迁移方法：检查碎片化情况，配置兼容的 CNI，验证计算出的节点容量，并通过预留备用容量和考虑 PDB 的 drain 进行迁移。对现有 Pod 进行全面重启并不是完整的迁移方案。

</details>

2. 对使用 Cluster Autoscaler 的混合实例托管节点组，哪项做法不正确？
   * A) 使用 CPU/内存/GPU 规格相近的实例
   * B) 验证镜像和 AZ 兼容性
   * C) 分开使用 Spot 和 On-Demand 节点组
   * D) 混用任意规格，因为 autoscaler 会模拟每种类型

<details>
<summary>显示答案</summary>

**答案：D) 混用任意规格，因为 autoscaler 会模拟每种类型**

多样性可以增加容量选择，尤其适用于 Spot，但必须遵循 autoscaler 的调度模型。Cluster Autoscaler 使用混合组中的第一种实例类型进行模拟；候选实例应具有相同的 CPU、内存和 GPU 规格。较小的替代实例可能导致 Pod 保持 Pending，而较大的实例可能浪费容量。名称相似并不能保证规格相同：例如，`c5n.large` 的内存不同于 `c5.large`。

托管节点组只具有一种容量类型。请使用**独立节点组**提供 On-Demand 基础容量和 Spot 扩展容量；在一个托管组中列出多个 `instanceTypes` 并不会混合购买选项。EKS 会选择托管 Spot 的分配策略；`spotAllocationStrategy` 不是 eksctl `managedNodeGroups` 支持的字段。

此示例保留了规格相近的 `m5` 系列实例。它是为现有且经过审查的集群配置节点组的示例，要求使用未占用的组名称；它并不证明价格/性能或容量有保障。请确认各 AZ 是否提供实例，以及镜像/驱动程序/存储兼容性：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: on-demand-base
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  spot: false
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
- name: spot-scaling
  amiFamily: AmazonLinux2023
  instanceTypes: [m5.large, m5a.large, m5d.large, m5ad.large, m5n.large]
  privateNetworking: true
  spot: true
  desiredCapacity: 0
  minSize: 0
  maxSize: 20
```
请将不同工作负载规格分开，不要把内存型、计算型和通用型实例合并到一个自动扩缩组中：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: compute-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [c5.2xlarge, c5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: compute}
  taints:
  - {key: workload-type, value: compute, effect: NoSchedule}
- name: memory-optimized
  amiFamily: AmazonLinux2023
  instanceTypes: [r5.2xlarge, r5a.2xlarge]
  privateNetworking: true
  minSize: 2
  maxSize: 10
  labels: {workload-type: memory}
  taints:
  - {key: workload-type, value: memory, effect: NoSchedule}
```
如果工作负载必须使用专用资源池，则它必须同时具有匹配的 toleration 和选择器/亲和性。标签本身不会安排它，而污点不是租户安全边界。请考虑从零扩缩时的发现、daemon 开销、中断处理、存储持久性，以及对所有候选实例类型的测试。多样性可能增加监控和故障排查工作；管理更简单或成本更低都不是必然结果。

</details>

3. 哪种策略会先创建独立的替代节点组，再退役旧节点组？
   * A) 未跟踪的主机软件包更新
   * B) 蓝绿迁移
   * C) 一次性删除所有节点
   * D) 仅更改集群显示名称

<details>
<summary>显示答案</summary>

**答案：B) 蓝绿迁移**

蓝绿迁移会创建独立的替代节点组，并在验证后迁移工作负载。在旧节点组和兼容的应用程序/数据状态仍保留期间，这种方法可以保留回滚选项。一个集群中的两个节点组仍共享控制平面和其他依赖；这并非完全隔离，也不保证零停机。

| 策略 | 优点 | 重要限制 |
| --- | --- | --- |
| 蓝绿 | 在最终退役前验证替代容量 | 需要额外成本/容量；回滚取决于保留的节点和兼容状态 |
| 托管滚动更新 | EKS 协调逐步替换节点 | `DEFAULT` 会使用临时额外节点；PDB/容量问题可能阻止更新进展 |
| Canary | 先尝试独立的小型工作负载/节点组 | 必须实际限制工作负载/流量范围；会增加验证和路由工作 |
| 手动修改主机软件包 | 更改单个主机 | 会导致与 AMI 不一致；应使用经过审查的替代镜像生命周期，而不是不加限定的 SSH/yum 操作说明 |

**替代组示例**：对于现有集群和未占用的组名称，请审查此文件并运行 `eksctl create nodegroup -f green-nodegroup.yaml`。首先确认 AL2023/架构兼容性、附加组件、出口、IP 空间、配额和存储拓扑。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: green-nodegroup
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 3
  minSize: 3
  maxSize: 5
  labels:
    audit.example.com/pool: green
```
**真正的 canary 会使用单独的 Deployment**：以下是在专用 `update-lab` namespace 中运行的最小 HTTP 探测工作负载，使用独特标签以避免意外加入现有 Service。若要声称应用程序兼容，请先将其替换为实际应用程序中经过审查的 canary。修改主 Deployment 的节点选择器会滚动更新其**所有**副本，并不是范围受限的 canary。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-canary
  namespace: update-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: my-app-canary}
  template:
    metadata:
      labels: {app: my-app-canary}
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        audit.example.com/pool: green
      containers:
      - name: web
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        readinessProbe:
          httpGet: {path: /, port: 80}
        resources:
          requests: {cpu: 100m, memory: 64Mi}
          limits: {cpu: 500m, memory: 128Mi}
```
在经过审查的观察期内，验证就绪状态、API/CNI/DNS、应用程序错误、资源压力、持久卷和有代表性的流量。明确配置流量路由；节点标签不会切换流量。验证替代容量以及工作负载/数据行为后，每次 drain 一个确认无误的旧节点：

```bash
# One reviewed node at a time, after validating replacement capacity.
OLD_NODE_JSON=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  get node "${OLD_NODE_NAME:?}" -o json) || exit 1
OLD_NODE_GROUP=$(printf '%s' "$OLD_NODE_JSON" |
  jq -er '.metadata.labels["eks.amazonaws.com/nodegroup"]') || exit 1
if [ "$OLD_NODE_GROUP" != "${OLD_NODEGROUP_NAME:?}" ]; then
  printf '%s\n' 'Node is not in the intended old managed node group.' >&2
  exit 1
fi
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" cordon "$OLD_NODE_NAME" &&
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" drain "$OLD_NODE_NAME" \
  --ignore-daemonsets --timeout=15m
```
drain 被阻止时应进行诊断，而不是使用 `--force` 或自动删除 emptyDir。在单独执行最终删除步骤前，确认所有工作负载和状态数据均已迁移：

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```
若选择托管滚动更新方案，请先按照基本问题 9 完成 `update-nodegroup-config` 操作，再提交 `update-nodegroup-version`，然后跟踪返回的 update ID。托管节点组可以保留其资源身份，同时替换 EC2 节点。旧容量被删除或数据发生不兼容更改后，“立即回滚”便不再可行。

</details>

4. 哪项操作可能与 Cluster Autoscaler 对托管 ASG 的控制权冲突？
   * A) 检查发现标签
   * B) 根据观察调整扫描频率
   * C) 使用准确的 Pod 资源 requests
   * D) 添加另一个独立更改相同预期容量的策略

<details>
<summary>显示答案</summary>

**答案：D) 添加另一个独立更改相同预期容量的策略**

Cluster Autoscaler 根据调度请求而非仅根据 EC2 平均 CPU 使用率来控制节点组容量。更改同一预期容量的 target-tracking 或 predictive ASG 策略可能与该控制循环冲突，并绕过预期的 Kubernetes drain 流程。不要为了“优化”而直接将预期容量重设为两个。

**实用控制措施：**

* 根据响应时间和 API 负载调整扫描频率。文档记录的默认值为 10 秒；30 秒只是可供测试的示例，并非测量得出的最佳值。同样，预置超时也必须符合实际节点启动行为。
* 使用经过审查的 ASG 发现标签和限定标签范围的 IAM。标签用于识别符合条件的组；它们不会授予权限，也不定义扩缩算法。
* 使 requests、标签和污点与实际容量匹配。使用一种实例类型可能合适；如果可用性/Spot 需求有理由支撑，采用规格相近的多样化实例也有用（高级问题 2）。
* 有意地使用优先级。抢占不保证可用性，也可能影响低优先级工作负载。只有在评估准入和工作负载策略后，才通过 `priorityClassName` 绑定以下类别：

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-high-priority
value: 1000000
globalDefault: false
description: Reviewed priority for critical application Pods
```
**超额预留容量**：使用可抢占的低优先级 Pod 预留 requests。对于此示例，Cluster Autoscaler 配置的 expendable-Pod cutoff 必须低于 `-5`（例如 `-10`），而应用程序 Pod 的优先级必须更高。否则，备用 Pod 可能无法按预期触发容量补充。请使用专用 namespace 和未占用的 PriorityClass 名称：

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: audit-overprovisioning
value: -5
globalDefault: false
description: Temporary spare capacity for an autoscaling lab
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: overprovisioning
  namespace: autoscaling-lab
spec:
  replicas: 1
  selector:
    matchLabels: {app: overprovisioning}
  template:
    metadata:
      labels: {app: overprovisioning}
    spec:
      priorityClassName: audit-overprovisioning
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: reserve
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '86400']
        resources:
          requests: {cpu: 1000m, memory: 1000Mi}
          limits: {cpu: 1000m, memory: 1000Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
此配置会占用 1 个 CPU 和 1000Mi 的请求容量，不会预热应用程序状态，并且会产生节点成本。它不会避免镜像拉取、卷附加或应用程序初始化。请根据观察到的需求确定规模，并在测试后删除自有的预留 Deployment 和 PriorityClass。

请使用基本问题 10 中完整渲染的 Cluster Autoscaler 配置，而不是旧的不完整 v1.23 Deployment。Karpenter 是单独管理容量的替代方案；其 NodePool 必须引用有效且已授权的 EC2NodeClass。KEDA/HPA 会扩缩工作负载副本，进而可能为任一节点 autoscaler 产生需求。启用所有扩缩机制并让它们同时管理相同资源前，请验证这些控制循环之间的相互作用。

</details>

5. 以下哪项**不是** EKS 节点组的通用安全最佳实践？
   * A) 要求使用 IMDSv2 并检查元数据访问
   * B) 遵循最小权限原则
   * C) 为每个节点分配公有 IP
   * D) 检查安全组规则

<details>
<summary>显示答案</summary>

**答案：C) 为每个节点分配公有 IP**

为每个节点分配公有 IP 并不是通用安全最佳实践。私有子网可以减少直接暴露于互联网的风险，但仍需考虑路由、安全组、IAM、软件维护和工作负载控制。

**节点身份和元数据**：使用 eksctl 支持的 `disableIMDSv1` 字段，要求使用 IMDSv2。嵌套的 `metadataOptions` 对象并非 eksctl 托管节点组字段；自定义 EC2 MetadataOptions 应放在经过审查的启动模板中。IMDSv2 可以缓解某些 SSRF 路径，但无法阻止所有 Pod 访问节点凭证，尤其是 host-network Pod。请分别检查元数据访问、工作负载身份和主机依赖项。

**最小权限和加密根卷**：此现有集群节点组示例假设 CNI 已有自己的 IRSA/Pod Identity 权限。EBS CSI、日志收集器和应用程序也需要各自经过审查的角色；将这些资源的广泛权限附加到每个节点上有违最小权限原则。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: secure-nodes
  amiFamily: AmazonLinux2023
  instanceType: m5.large
  privateNetworking: true
  desiredCapacity: 2
  minSize: 2
  maxSize: 5
  disableIMDSv1: true
  volumeEncrypted: true
  iam:
    attachPolicyARNs:
    - arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy
    - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly
```
EBS 加密保护的是与 Kubernetes API 数据不同的层。EKS 1.28 及更高版本默认使用 envelope encryption 对所有 Kubernetes API 静态数据进行加密；客户托管 KMS key 是可选项，但会增加授权/权限和密钥生命周期义务。不要将禁用或删除集群密钥作为例行清理操作。

**网络设计**：私有 API endpoint 要求具备可路由的管理员/节点访问路径。公有 API 限制应使用 `publicAccessCidrs`，而不是在集群 SG 上设置入站规则。请检查 AWS 对完整集群/节点 SG 的要求：TCP 443、TCP 10250、TCP/UDP 53，以及工作负载特定路径，并确保方向和对等安全组正确。仅配置两条入站端口规则并不是完整的节点网络设计。

私有 IPv4 互联网出口可以使用 NAT；VPC endpoints 和原生 IPv6 则具有不同路径。入站流量可以来自负载均衡器或已授权的互联网络。仅使用私有子网既不能证明已完全隔离，也不能证明符合监管要求。

**容器控制**：使用兼容非 root 和只读运行模式的工作负载。此由控制器管理的诊断 Pod 在**新建的专用** `security-lab` namespace 中运行，无需网络或可写根文件系统：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-pod
  namespace: security-lab
spec:
  replicas: 1
  selector:
    matchLabels: &id001
      app: secure-pod
  template:
    metadata:
      labels: *id001
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: secure-container
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command:
        - sh
        - -c
        - echo read-only-lab; sleep 3600
        resources:
          requests:
            cpu: 10m
            memory: 16Mi
          limits:
            cpu: 100m
            memory: 32Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```
可以在该专用 namespace 中演示强制执行的拒绝策略；用于实际工作负载前，请添加显式的 DNS/应用允许规则：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: security-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```
**日志记录和检测**：控制平面 CloudWatch 日志有五种可配置类型：

```bash
# Enable the reviewed set of log types; this example enables all five.
if LOG_UPDATE_ID=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$LOG_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```
等待返回的更新成功，并验证实际日志传输和保留情况。这不会收集所有容器的应用程序日志。GuardDuty EKS audit-log protection 和 Runtime Monitoring 是不同的功能，各自有独立配置/覆盖范围；仅启用控制平面日志并不能实现运行时威胁检测。

</details>


## 参考资料

* [EKS 前缀模式](https://docs.aws.amazon.com/eks/latest/best-practices/prefix-mode-linux.html)
* [EKS maxPods 和前缀配置流程](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)
* [EKS 网络策略](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
* [NAT gateways](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
* [子网路由表关联](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ec2-subnetroutetableassociation.html)
* [Pod 安全组](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
* [CoreDNS 托管附加组件](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)
* [CoreDNS cache](https://coredns.io/plugins/cache/)
* [CoreDNS reload](https://coredns.io/plugins/reload/)
* [Kubernetes 多租户](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
* [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
* [EKS Cluster Autoscaler](https://docs.aws.amazon.com/eks/latest/best-practices/cas.html)
* [EKS 托管节点更新](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)
* [在 EKS 上运行 Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
* [Calico NetworkPolicy](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
* [EKS 节点 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html)
