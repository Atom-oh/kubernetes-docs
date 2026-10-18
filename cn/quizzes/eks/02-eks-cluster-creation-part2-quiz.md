# EKS 集群创建测验 - 第 2 部分

> **最后更新**：2026 年 9 月 11 日

> 各题示例彼此独立。请使用第 1 部分中的前置条件，并明确选择培训账户和集群。每项练习都应在同一个 Bash 会话中按顺序执行。本次审查检查了下方的云端/主机命令，但没有对 AWS 或节点实际执行。

本测验检查你对 Amazon EKS 集群创建相关高级概念、安全设置和网络配置的理解，涵盖集群安全、网络策略和服务账户等主题。

## 基础概念题

1. IRSA 在 EKS 集群中的主要用途是什么？
   * A) 授予 Kubernetes 管理员访问权限
   * B) 分配 EC2 节点 IAM 角色
   * C) 通过 Kubernetes 服务账户向工作负载授予临时 AWS 权限
   * D) 修改 EKS 控制平面角色

<details>
<summary>显示答案</summary>

**答案：C) 通过 Kubernetes 服务账户向工作负载授予临时 AWS 权限**

IRSA 让工作负载使用 Kubernetes 服务账户身份获取临时 AWS 凭证。IAM 角色的权限策略决定它能执行哪些 AWS 操作。这与 Kubernetes RBAC 以及 EKS 控制平面或 EC2 节点所用的 IAM 角色相互独立。

**信任流程：** EKS 会签发投射的服务账户令牌。将集群的实际 OIDC issuer 注册为 IAM OIDC 提供方，再信任预期的受众，以及命名空间/服务账户 subject。受支持的 AWS SDK 默认凭证链会通过 STS `AssumeRoleWithWebIdentity` 交换该令牌。此示例应使用真实的提供方 ARN/issuer 和准确的服务账户身份：

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
        "oidc.eks.us-west-2.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:irsa-lab:my-service-account"
      }
    }
  }]
}
```

给服务账户添加角色 ARN 注解，并让 Pod 引用它。先创建一个未使用的 `irsa-lab` 命名空间。下面两个清单是 eksctl 管理服务账户创建方式的替代方案；不要覆盖其他应用的服务账户：

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: irsa-lab
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/ReviewedIrsaRole
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: irsa-identity-check
  namespace: irsa-lab
spec:
  serviceAccountName: my-service-account
  restartPolicy: Never
  containers:
    - name: aws-cli
      image: public.ecr.aws/aws-cli/aws-cli:2.36.43
      command: ["aws"]
      args: ["sts", "get-caller-identity"]
```

Pod 使用已核实的 AWS CLI v2 镜像标签，只打印调用方身份，不输出秘密访问密钥或 web-identity 令牌。确认返回的角色就是预期工作负载角色。STS 身份检查成功并不能证明它能访问 S3 或其他目标资源；还要像练习 1 那样单独测试所需操作。

**eksctl 替代方式：** 策略应仅允许目标资源和操作；对于单 bucket 任务，不要使用宽泛的 AWS 托管 S3 策略。先检查现有服务账户及角色归属；不要把 `--override-existing-serviceaccounts` 当作通用修复手段。

```bash
# For a new service account and dedicated role, with a reviewed scoped policy.
eksctl utils associate-iam-oidc-provider \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" --approve
KUBECONFIG="${EXAMPLE_KUBECONFIG:?}" eksctl create iamserviceaccount \
  --name "${IRSA_SERVICE_ACCOUNT:?}" --namespace "${IRSA_NAMESPACE:?}" \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --attach-policy-arn "${SCOPED_POLICY_ARN:?}" --approve
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$IRSA_NAMESPACE" \
  get serviceaccount "$IRSA_SERVICE_ACCOUNT" -o yaml
```

**限制与责任：**

- 使用受支持的 SDK 及其凭证链。硬编码凭证或链中优先级更高的其他提供方可能覆盖 IRSA。Webhook 会注入角色/令牌文件配置，SDK 会刷新临时凭证。不要打印或复制令牌/凭证值。
- IRSA 本身不会阻止访问节点 IMDS；共享节点的容器也不是硬隔离边界。应分别限制 IMDS 和节点权限；使用 `hostNetwork` 的 Pod 仍可访问 IMDS。
- IAM 条件能限制角色代入范围，但任何获准创建并使用该服务账户 Pod 的人，都可能获得其 AWS 权限。也要控制 Kubernetes 工作负载和服务账户管理权限。
- EKS Pod Identity 是另一种工作负载身份选项，有自己的支持要求。它通过 EKS Auth/agent 获取凭证，与 IRSA 的 OIDC/STS 流程不同。
- 集群用户通过 EKS access entry/policy 或配置中的旧版 `aws-auth` 映射获得权限。这些机制授权 Kubernetes 访问，不能替代工作负载 IAM 权限策略。

参考：[IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)、[为服务账户分配角色](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html)、[SDK 要求](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html)、[Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)。

</details>

2. AWS 安全组在 EKS 设计中控制什么？
   * A) Kubernetes 资源授权
   * B) 关联网络接口上的允许流量，包括受支持的 Pod 网络接口
   * C) 服务账户令牌受众
   * D) Deployment 的副本数

<details>
<summary>显示答案</summary>

**答案：B) 关联网络接口上的允许流量，包括受支持的 Pod 网络接口**

安全组是关联到网络接口的有状态网络过滤器。在 EKS 中，它们可以控制集群接口、节点之间的流量；在启用受支持的 Security Groups for Pods 功能时，也可控制选定 Pod 的流量。安全组不负责 Kubernetes RBAC，也不负责用户身份验证。

**默认规则与必需规则并不相同。** EKS 会创建 `eks-cluster-sg-<cluster>-<id>`，其中包含自引用入站规则、宽泛出站访问，以及供 EFA 使用的自引用出站规则。这些是需要检查的默认设置，不是最小权限方案。EKS 会把集群安全组关联到集群网络接口，通常也关联到托管节点接口；自定义启动模板安全组会改变此行为。

若要收紧默认出站规则，至少保留文档规定的流量，并考虑实际工作负载的其他依赖：

| 集群安全组所需出站流量 | 目标 |
| --- | --- |
| TCP 443 | 集群安全组 |
| TCP 10250 | 集群安全组 |
| TCP 和 UDP 53 | 集群安全组 |

这张表本身不是完整的网络设计。还应检查节点间/应用端口、API 和镜像仓库访问、S3、DNS 路径以及 IPv4/IPv6 规则。私有端点可在没有普通互联网出口的情况下提供 AWS 连接。EKS 可能在集群更新时重建自引用规则，因此不能把删除它们描述为永久限制。

**附加安全组：** 集群 `resourcesVpcConfig.securityGroupIds` 中指定的安全组会关联到集群网络接口，不会自动关联到节点组。如果节点启动模板提供了自定义安全组，EKS 不会同时添加集群安全组；自定义组必须允许所需的节点/API 流量。

下面的 AWS CLI 示例为新控制平面选择附加安全组。它不会创建节点容量或操作员访问条目。由于已关闭自动授予创建者管理员访问权限，负责预置的身份必须有权创建所需的操作员 access entry：

```bash
# Cluster creation fragment: use reviewed roles/subnets/groups and a new name.
aws eks create-cluster --name "${NEW_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --kubernetes-version 1.36 \
  --role-arn "${CLUSTER_ROLE_ARN:?}" \
  --access-config authenticationMode=API,bootstrapClusterCreatorAdminPermissions=false \
  --resources-vpc-config "subnetIds=${PRIVATE_SUBNET_A:?},${PRIVATE_SUBNET_B:?},securityGroupIds=${ADDITIONAL_CONTROL_PLANE_SG:?},endpointPrivateAccess=true,endpointPublicAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}"
```

等效的 eksctl 网络字段应放入经过完整审查的[第 2 部分](../../eks/02-eks-cluster-creation-part2.md)配置中。替换文档用 CIDR 和所有 ID：

```yaml
# Networking example; merge into a reviewed full ClusterConfig.
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
  version: "1.36"
vpc:
  id: vpc-0123456789abcdef0
  controlPlaneSecurityGroupIDs:
    - sg-0123456789abcdef0
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
```

**公有与私有 API：** 公有 Kubernetes 端点通过 `publicAccessCidrs` 限制，而不是通过集群安全组。集群安全组规则控制私有端点流量。CIDR 白名单或安全组规则都不会授予 IAM/RBAC 授权。

**Pod 安全组：** 在受支持的计算环境中，先配置该功能及必要的 IAM/VPC CNI 设置，再创建 `SecurityGroupPolicy`。检查实例 trunking 兼容性、CNI 版本、强制模式、DNS 和实际安全组规则。Windows 和 EKS Auto Mode 不支持此功能；EC2 `t` 实例系列也不受支持。Fargate 有单独的受支持配置。

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: application-sg
  namespace: sg-lab
spec:
  podSelector:
    matchLabels:
      app: my-app
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

策略会选择单独创建的 `sg-lab` 命名空间中的 Pod；仅存在 CRD 对象并不能证明安全组已附加。标准/严格 Pod 安全组模式及 SNAT 会影响 VPC 外部流量受哪个安全组过滤。请按实际模式核实文档说明。

Kubernetes NetworkPolicy 是另一套由已配置网络插件执行的机制。集群支持 NetworkPolicy，并不意味着 Pod 流量会自动默认拒绝。第 3 题展示了如何明确配置策略。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.resourcesVpcConfig.{clusterSG:clusterSecurityGroupId,additionalSGs:securityGroupIds,publicAccess:endpointPublicAccess,privateAccess:endpointPrivateAccess,cidrs:publicAccessCidrs}'
aws ec2 describe-security-groups --region "$EXAMPLE_REGION" \
  --group-ids "${REVIEWED_SECURITY_GROUP_ID:?}"
```

参考：[集群安全组](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html)、[API 端点访问](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[Pod 安全组](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)。

</details>

3. 在 EKS 中强制执行 Kubernetes NetworkPolicy 需要什么？
   * A) 仅安全组规则
   * B) 已启用且受支持的策略实现，例如 Amazon VPC CNI、Calico 或 Cilium
   * C) 仅 VPC Flow Logs
   * D) 一个没有执行实现的 NetworkPolicy 对象

<details>
<summary>显示答案</summary>

**答案：B) 已启用且受支持的策略实现，例如 Amazon VPC CNI、Calico 或 Cilium**

必须配置网络策略实现；仅创建 `NetworkPolicy` 对象不会强制流量规则。**Amazon VPC CNI 支持 NetworkPolicy**，因此仅为使用该功能，并不强制要求 Calico 或 Cilium。

**Amazon VPC CNI 路径：** 核实集群/平台、Linux 内核和 CNI 版本受支持，再通过拥有该附加组件的配置启用网络策略功能。AWS 当前指南要求 VPC CNI 1.21.0+ 才支持标准策略和管理员策略，并要求 Linux 内核 5.10+。更早版本的历史最低要求不应当作当前集群的升级目标。

```bash
aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni \
  --query 'addon.{version:addonVersion,status:status,configuration:configurationValues}'
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --addon-version "${REVIEWED_CNI_VERSION:?}" \
  --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  get daemonset aws-node -o jsonpath='{.spec.template.spec.containers[*].name}{"\n"}'
```

对于 EKS 托管附加组件，相关配置值如下：

```json
{
  "enableNetworkPolicy": "true"
}
```

将其合并到**完整且经过审查的配置**中，并保留所需现有设置；提供新的 `configurationValues` 文档并不是 JSON patch。不要降级附加组件，也不要用旧的上游清单覆盖 EKS 托管 DaemonSet。若使用 Helm/自管理安装，则按该安装方式的文档配置。

在标准启动模式下，新 Pod 可能会在策略编程完成前短暂允许流量。严格模式启动时默认拒绝，但需要预先准备所有必要连通策略，包括 CoreDNS 依赖。不要在现有集群上盲目切换严格模式。

**其他实现：**

- **与 Amazon VPC 网络配合使用 Calico：** 保留 AWS IPAM/CNI，并将 operator 的 `Installation` 配置为 `AmazonVPC`。按锁定版本的 operator/CRD 说明操作，并满足官方 EKS 指南中的 AWS Pod-IP 注解和 RBAC 前置条件。此 Calico 路径需要关闭 AWS 自己的策略强制执行；仅安装 operator 或随意应用 VXLAN 清单并不等同于此设计。

```yaml
# Installation resource for the Amazon VPC networking path, after operator/CRDs.
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
```

- **与 Amazon VPC CNI 配合使用 Cilium：** 必须采用文档所述 chaining 配置；仅关闭隧道/masquerading 并不会建立 chaining。下列值来自已发布的 1.20.1 指南。检查版本与集群兼容性并满足指南前置条件。需要通过受控滚动更新重建现有 Pod，新的 chaining 路径才会生效。

```yaml
# Relevant Helm values from the Cilium 1.20.1 AWS-CNI chaining guide.
# This is not a complete install or migration command.
cni:
  chainingMode: aws-cni
  exclusive: false
enableIPv4Masquerade: false
routingMode: native
```

选择并验证预期的策略实现，不要叠加未经审查的 CNI/策略安装。更换实现可能遗留节点级规则，需要制定迁移计划。

**策略示例：** 在新建的 `policy-lab` 命名空间中，允许 frontend 到 backend 的 TCP 8080 流量和 DNS，并拒绝其他流量。backend 必须确实监听 8080。AWS 实现中使用相同的 Service 和容器端口。以下 DNS selector 假设 `kube-system` 中运行常规 CoreDNS Pod；NodeLocal DNSCache 或自定义 DNS 需要另行审查规则。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: policy-lab
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: policy-lab
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
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
```

由于两端都处于隔离状态，因此既要允许 frontend 出站，也要允许 backend 入站。多个标准 NetworkPolicy 的允许流量会叠加；默认拒绝对象不会覆盖允许规则。测试命名空间同时允许 DNS，以免把应用连接被拒绝误判为 DNS 故障。

**有效验证：** 使用由 Deployment 管理的 frontend、backend 和无关客户端 Pod。AWS 文档指出，没有 `metadata.ownerReferences` 的独立 Pod 可能无法可靠执行策略，因此不要只用裸 `kubectl run` Pod 证明效果。先确认基线连通性，再应用策略；随后验证 frontend 成功、无关客户端失败，同时 DNS 仍可用。策略收敛后测试新连接。仅看到 CNI Pod 或成功应用 YAML 并不足够。

AWS VPC CNI 策略强制执行仅适用于受支持的 EC2 Linux 节点，不适用于 Windows 或 Fargate。它作用于 Pod 主接口和集群 IP 家族；额外接口和 IPv6 Pod 的 IPv4 出站存在限制。安全组、Network Firewall 和 flow log 用途不同，不能替代此 Kubernetes 策略配置。

参考：[VPC CNI 策略配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)、[AWS 策略限制](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)、[EKS 上的 Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)、[Cilium 1.20.1 chaining 源码](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/installation/cni-chaining-aws-cni.rst)、[Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

4. 哪项陈述正确描述了 EKS 1.28 或更高版本的 Kubernetes API 数据静态加密？
   * A) 默认启用信封加密；可选择客户管理的 KMS 密钥
   * B) 必须重建每个集群才能加密 Secret
   * C) Base64 编码可提供静态加密
   * D) 必须由应用 sidecar 加密 EKS 控制平面数据库

<details>
<summary>显示答案</summary>

**答案：A) 默认启用信封加密；可选择客户管理的 KMS 密钥**

运行 Kubernetes **1.28 或更高版本**的 EKS 集群默认使用 KMS v2 信封加密保护**所有 Kubernetes API 数据**，除非关联客户管理 KMS 密钥，否则使用 AWS owned key。Secret、ConfigMap 及其他存储的 API 资源都包括在内。这是在 etcd 磁盘加密之外增加的保护，不会加密节点或 EBS 卷上的应用数据。

**先检查，再更改。** `encryptionConfig` 中没有客户管理密钥 ARN，并不表示 Secret 未加密。控制台会标明 AWS owned key 模式，但不会显示该密钥 ARN。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" \
  --query 'cluster.{version:version,status:status,encryption:encryptionConfig}'

# Optional CMK inspection, only when a customer-managed key is required.
aws kms describe-key --key-id "${KMS_KEY_ARN:?Reviewed customer-managed key ARN}" \
  --region "$EXAMPLE_REGION" \
  --query 'KeyMetadata.{arn:Arn,state:KeyState,spec:KeySpec,usage:KeyUsage}'
```

**可选客户管理密钥 (CMK)。** 若有客户密钥控制要求，可使用与集群位于同一 Region 的对称加密密钥。核实密钥可用性、调用者 IAM 权限、密钥策略/grant，以及适用时的跨账户权限。只给 `eks.amazonaws.com` 若干 KMS 操作权限的通用策略并不完整：预置/关联身份需要文档规定的 `kms:DescribeKey` 和 `kms:CreateGrant` 权限。在 `CreateCluster` 期间，不能用 `kms:GrantIsForAWSResource` 条件控制 `CreateGrant`。

可以在 `CreateCluster` 中提供 provider，也可以用 `AssociateEncryptionConfig` 为符合条件的现有集群关联 CMK；并非一定要新建集群。不要把它当作通用的密钥替换或关闭加密操作。已关联 CMK 的集群必须使用受支持的密钥管理流程。

```bash
# Optional CMK association for an eligible existing cluster.
# Review current configuration, key policy/grants and recovery procedures first.
KMS_CONFIG_DIR=$(mktemp -d /tmp/eks-kms-config.XXXXXX)
: "${KMS_CONFIG_DIR:?}"
jq -n --arg arn "${KMS_KEY_ARN:?}" \
  '[{resources:["secrets"],provider:{keyArn:$arn}}]' \
  > "$KMS_CONFIG_DIR/encryption.json" || exit 1
if ENCRYPTION_UPDATE_ID=$(aws eks associate-encryption-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --encryption-config "file://$KMS_CONFIG_DIR/encryption.json" \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --update-id "$ENCRYPTION_UPDATE_ID" --query 'update.{status:status,errors:errors}'
fi
```

记录 update ID，并持续检查到状态为 `Successful` 或明确失败；请求被接受不等于完成。为兼容性保留的 `resources: ["secrets"]` 字段仍可接受。在 EKS 1.28+ 中，它**不会**将加密限制为 Secret：该字段已弃用，所有 Kubernetes API 数据都会进行信封加密。当前 API 也接受省略/null/空的 resources 列表，但响应仍保留旧版 `["secrets"]` 值。针对 Kubernetes 1.27 及更早版本的旧 `enable-kms` 操作指南属于历史资料，不是受支持版本的迁移目标。

集群仍在运行时，不要为了实验清理而禁用或删除已关联密钥。密钥不可用会使控制平面退化，永久丢失密钥则可能令集群无法恢复。选择 CMK 前，应审查密钥恢复、访问权限和监控。默认 AWS owned key 加密无需客户密钥设置；CMK 会产生单独的 KMS 费用。

**Secret 的使用方式不变。** 获得授权的 API 客户端和 Pod 仍会收到可用值；静态加密不能替代 RBAC、工作负载身份或日志/备份保护。下面清单故意使用公开的虚构数据，不是生产 Secret：

```yaml
# Public dummy data for a newly created secrets-lab namespace only.
apiVersion: v1
kind: Secret
metadata:
  name: example-credentials
  namespace: secrets-lab
type: Opaque
stringData:
  username: example-user
  password: public-training-placeholder
```

```bash
# Inspect keys and metadata without printing values.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" \
  -n secrets-lab get secret example-credentials -o json |
  jq '{name:.metadata.name,type:.type,keys:(.data|keys)}'
```

真实凭证不要以明文或 base64 值提交清单、写入 shell history，或通过诊断命令打印。Base64 是可逆编码。AWS Secrets Manager 可通过 CSI 挂载文件或同步 Kubernetes Secret 的 controller 集成；应用不一定都需要修改 SDK。同步生成的 Secret 仍受 Kubernetes 访问控制。sidecar 无法配置托管 API server 的静态加密。

参考：[默认信封加密](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[AssociateEncryptionConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_AssociateEncryptionConfig.html)、[旧版 KMS 流程和权限](https://docs.aws.amazon.com/eks/latest/userguide/enable-kms.html)、[在 EKS 上集成 Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html)。

</details>

5. 如何自定义 AL2023 EC2 托管节点的 kubelet 设置？
   * A) 在控制台编辑 EKS 控制平面的 kubelet
   * B) 通过 eksctl 或启动模板用户数据使用受支持的 nodeadm NodeConfig
   * C) 用 kubectl edit node 修改 status.capacity
   * D) 在每次 AL2023 启动时运行 AL2 bootstrap.sh 脚本

<details>
<summary>显示答案</summary>

**答案：B) 通过 eksctl 或启动模板用户数据使用受支持的 nodeadm NodeConfig**

对于 **AL2023 EC2 节点**，应使用 `nodeadm` 的 `NodeConfig` 及受支持的 eksctl/启动模板集成。不要使用 AL2 的 `/etc/eks/bootstrap.sh` 流程，也不要假设 `eksctl create nodegroup --kubelet-extra-args` 是有效参数。此示例中旧的 `kubeletExtraArgs` map 不是受支持的托管节点组字段。

**eksctl：** 对 AL2023 而言，尽管名字如此，`overrideBootstrapCommand` 中放的是 YAML `NodeConfig`。eksctl 会把它加到用户数据前部，供 nodeadm 与生成的节点配置合并。选择 EKS 原生 AMI 时，EKS 会提供集群所需的默认配置。扩大部署前，应先在测试节点检查合并后的有效设置：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-kubelet
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
    overrideBootstrapCommand: |
      apiVersion: node.eks.aws/v1alpha1
      kind: NodeConfig
      spec:
        kubelet:
          config:
            kubeReserved:
              cpu: 100m
              memory: 300Mi
            systemReserved:
              cpu: 200m
              memory: 512Mi
            evictionHard:
              memory.available: 500Mi
            mergeDefaultEvictionSettings: true
```

上面的资源预留和 500 MiB 驱逐阈值只是**示例值**，不是实测建议。它们会减少 Pod 可分配容量，设置不合适时可能导致驱逐。Kubernetes 1.36 支持 `mergeDefaultEvictionSettings: true`；当 kubelet 处理部分驱逐映射时，它能保留未指定信号的默认设置。若不正确合并，只指定一个信号可能意外把其他默认阈值设为零。

**自定义 AMI/启动模板路径：** 如果在 eksctl 生成配置之外提供自己的 AMI ID，必须提供完整集群元数据：名称、API endpoint、base64 CA 和 service CIDR。参照[第 1 部分测验的高级题 5](02-eks-cluster-creation-part1-quiz.md#advanced-topics)生成元数据，并将审查过的 `spec.kubelet.config` 设置加入该 NodeConfig。仅含 kubelet 的部分对象并不是完整的独立引导配置。

AL2023 会在用户数据前运行 `nodeadm-config`，之后运行 `nodeadm-run`。不要再次运行 `nodeadm init`，也不要以会与这些服务冲突的方式手动启动/重新配置 kubelet。Bottlerocket、Windows 等其他 OS 使用不同配置机制；本例不适用于 EKS Auto Mode 节点。

| 设置 | 检查事项 |
| --- | --- |
| `maxPods` / nodeadm `maxPodsExpression` | 实例 ENI/IP 限制、CNI 模式、prefix delegation 和受支持密度；不要强行使用通用值 110 |
| Node label 和 taint | 优先使用托管节点组字段；使用自有 label 前缀，不要覆盖 EKS/AZ label |
| `kubeReserved`、`systemReserved` | 实际主机/系统工作负载需求及 Node Allocatable |
| `evictionHard`、软阈值 | 内存/磁盘/inode 信号和默认值合并行为；不要关闭无关保护 |
| Cgroup driver | 与所选 OS、容器运行时的兼容性；除非变更经过审查，否则保留经测试的 AMI 默认值 |

**验证：** 检查 Node 的 capacity/allocatable 以及有效服务配置/日志。节点 Ready 并不能证明每个自定义值都已应用。本次审计检查了配置语法和官方字段定义，没有用这些设置启动节点。

```bash
# Kubernetes-side checks through the intended cluster context.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" describe node "${EXAMPLE_NODE_NAME:?}"

# Run separately on a specifically authorized AL2023 test node.
sudo systemctl status nodeadm-config nodeadm-run kubelet --no-pager
sudo systemctl cat kubelet
sudo journalctl -u nodeadm-config -u nodeadm-run -u kubelet --since '-15 min' --no-pager
```

应查看已配置服务的实际配置路径，不要假设每种 AMI 都有 `/etc/systemd/system/kubelet.service.d/10-kubelet-args.conf`。按需限制并保护诊断日志。

`kubectl edit node` 可以更改 Node 元数据，但不能设置 kubelet 启动配置。SSM 可以运行主机命令，但临时主机修改并不是托管节点的持久替换配置，而且可能要求造成中断的重启。应把已审查设置放入预置配置，并有计划地替换/测试节点。

参考：[eksctl AL2023 引导](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html)、[AL2023 服务](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[nodeadm API](https://awslabs.github.io/amazon-eks-ami/nodeadm/doc/api/)、[KubeletConfiguration](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/)、[Kubernetes 1.36 字段定义](https://github.com/kubernetes/kubelet/blob/v0.36.0/config/v1beta1/types.go)。

</details>

6. 在 EKS 中，哪些机制可替代已移除的 PodSecurityPolicy 控制？
   * A) 仅 EC2 安全组
   * B) Pod Security Admission；必要时配合兼容的策略引擎
   * C) 仅 CloudWatch 日志保留
   * D) 将 IAM 用户访问密钥存入每个 Pod

<details>
<summary>显示答案</summary>

**答案：B) Pod Security Admission；必要时配合兼容的策略引擎**

PodSecurityPolicy 在 Kubernetes 1.21 弃用、1.25 移除。使用内置的 **Pod Security Admission (PSA)** 执行 **Pod Security Standards (PSS)**；超出这些控制范围的需求，再使用合适的策略引擎。

**PSA：** 三个 PSS 级别是 Privileged、Baseline 和 Restricted；`enforce`、`audit` 和 `warn` 是不同模式。示例会在新建实验命名空间执行 Baseline，并报告 Restricted 违规。策略版本锁定为 EKS 1.36 示例；实际集群须选用受支持的版本。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: policy-engine-lab
  labels:
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
```

不要盲目给现有共享命名空间重新贴标签。先启用 audit/warn，修复工作负载清单，再收紧执行模式。PSA 不会修改 Pod 以使其合规，也不会驱逐正在运行的 Pod。它在 Pod 准入时评估；对工作负载模板执行 warning/audit，可在控制器尝试创建 Pod 前发现违规。

**Kyverno：** 本次审计示例中的 chart 3.9.1 包含 controller 1.19.1。Kyverno 1.19 弃用旧版 `ClusterPolicy`/`Policy` 类型，迁移指南计划在 1.20 移除它们。新示例应使用当前 CEL 策略 API。应在不兼容升级前迁移现有策略，而不是只更改 controller 版本。

```bash
# Optional new installation; review existing controllers and release compatibility.
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update kyverno
helm install kyverno kyverno/kyverno --version 3.9.1 \
  --namespace kyverno --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

下面的 `policies.kyverno.io/v1` **ValidatingPolicy** 会在普通、init 和 ephemeral container 中拒绝 `privileged: true`，且只匹配实验命名空间。该字段不存在或为 false 时允许：

```yaml
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata:
  name: disallow-privileged-lab
spec:
  validationActions:
  - Deny
  evaluation:
    background:
      enabled: true
  matchConstraints:
    resourceRules:
    - apiGroups:
      - ''
      apiVersions:
      - v1
      operations:
      - CREATE
      - UPDATE
      resources:
      - pods
      - pods/ephemeralcontainers
  matchConditions:
  - name: lab-only
    expression: object.metadata.namespace == 'policy-engine-lab'
  validations:
  - expression: object.spec.containers.all(c, !has(c.securityContext) || !has(c.securityContext.privileged) || !c.securityContext.privileged)
    message: Privileged containers are not allowed.
  - expression: '!has(object.spec.initContainers) || object.spec.initContainers.all(c, !has(c.securityContext) ||
      !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged initContainers are not allowed.
  - expression: '!has(object.spec.ephemeralContainers) || object.spec.ephemeralContainers.all(c, !has(c.securityContext)
      || !has(c.securityContext.privileged) || !c.securityContext.privileged)'
    message: Privileged ephemeralContainers are not allowed.
```

这只展示一项控制，并不涵盖 Baseline 或 Restricted 全部标准。应用策略前，策略引擎/CRD 必须就绪；还需在目标集群中验证实时准入和子资源行为。后台评估会报告现有违规，但不会驱逐运行中的工作负载。

**OPA Gatekeeper 替代方案：** 若策略模型符合需求，可安装经过审查的 Gatekeeper 版本。此示例将 chart/controller 固定为 3.23.1：

```bash
# Alternative policy-engine example, not a prerequisite for the Kyverno example.
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update gatekeeper
helm install gatekeeper gatekeeper/gatekeeper --version 3.23.1 \
  --namespace gatekeeper-system --create-namespace \
  --kubeconfig "${EXAMPLE_KUBECONFIG:?}" --wait --timeout 5m
```

Gatekeeper 首先需要 `templates.gatekeeper.sh/v1` ConstraintTemplate。应用对应 Constraint 前，应等待模板和生成的 constraint CRD 建立完成。下面的 Rego 示例检查同样三个容器列表，并将 Constraint 限定在实验命名空间：

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivilegedlab
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivilegedLab
      validation:
        openAPIV3Schema:
          type: object
  targets:
  - target: admission.k8s.gatekeeper.sh
    rego: "package k8snoprivilegedlab\n\ncontainers[c] {\n  c := input.review.object.spec.containers[_]\n\
      }\ncontainers[c] {\n  c := input.review.object.spec.initContainers[_]\n}\ncontainers[c]\
      \ {\n  c := input.review.object.spec.ephemeralContainers[_]\n}\nviolation[{\"\
      msg\": msg}] {\n  c := containers[_]\n  c.securityContext.privileged == true\n\
      \  msg := sprintf(\"Privileged container is not allowed: %v\", [c.name])\n}\n"
---
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoPrivilegedLab
metadata:
  name: no-privileged-lab
spec:
  enforcementAction: deny
  match:
    scope: Namespaced
    namespaces:
    - policy-engine-lab
    kinds:
    - apiGroups:
      - ''
      kinds:
      - Pod
```

Gatekeeper 的 `enforcementAction: deny` 会拒绝匹配的违规；`dryrun` 或 `warn` 可用于分阶段发布。只有模板而没有 Constraint 并不构成已执行策略。应使用已安装版本支持的 API/schema 和 Rego 模式。

**验证与限制：** 本地运行 Kyverno 1.19.1 CLI（将 warning 视为错误）和 Gatekeeper 3.23.1 Gator，各检查六种情况：明确为 false、字段省略、普通/init/ephemeral container 特权开启，以及不在作用范围内的命名空间。两个实现都产生了预期本地结果。没有安装集群组件，也没有执行实时准入测试。

```bash
# Offline policy logic checks using locally reviewed fixture files.
kyverno apply kyverno-policy.yaml --resource test-pod.yaml --warnings-as-errors
gator test --filename gatekeeper-policy.yaml --filename test-pod.yaml --output=json
```

若 PSA 或其他 webhook 也会拒绝请求，不要断言实时拒绝一定来自某个特定引擎。检查策略/controller 状态、目标范围、实际准入响应和报告。针对 host namespace、hostPath、capability、权限提升及其他 PSS 要求，应实施完整控制集。

AWS Security Hub、AWS Config 和 EC2 安全组职责各异；启用它们不能替代 Kubernetes Pod 准入执行。

参考：[PSA](https://kubernetes.io/docs/concepts/security/pod-security-admission/)、[PSS](https://kubernetes.io/docs/concepts/security/pod-security-standards/)、[Kyverno CEL 迁移](https://kyverno.io/docs/guides/migration-to-cel/)、[Kyverno 1.19.1](https://github.com/kyverno/kyverno/releases/tag/v1.19.1)、[Gatekeeper 3.23.1 操作指南](https://github.com/open-policy-agent/gatekeeper/blob/v3.23.1/website/docs/howto.md)。

</details>

7. IRSA 的 web identity 信任需要哪项 IAM 身份提供方前置条件？
   * A) 在每个 Pod 中存放 IAM 用户访问密钥
   * B) cluster-admin RoleBinding
   * C) 与集群 issuer 匹配的 IAM OIDC provider
   * D) 每个工作节点都具有公有 IP

<details>
<summary>显示答案</summary>

**答案：C) 与集群 issuer 匹配的 IAM OIDC provider**

IRSA 需要与目标集群 issuer 匹配的 IAM OIDC provider。先检查是否已存在；不要创建重复 provider，也不要复用其他集群的 issuer。工作负载要代入 IAM 角色之前必须满足此条件，但可以先创建服务账户，之后再创建角色并添加注解。所有资源并没有必须严格按固定顺序创建的普遍要求。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.identity.oidc.issuer --output text
eksctl utils associate-iam-oidc-provider \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" --approve
```

使用 eksctl 或当前的 IAM OIDC provider 流程，不要照抄固定的旧证书 thumbprint。将 `sts.amazonaws.com` 配置为预期的 client ID/audience。在没有互联网出口的 VPC 中，从 VPC 内创建 provider 可能需要独立的 `oidc-eks` interface endpoint/private DNS，或其他可达的管理路径。IRSA 令牌交换还需要区域 STS 连接。

然后创建范围受限的角色策略，以及第 1 题包含 `aud` 和 `sub` 的信任策略；给正确的服务账户添加注解，并创建引用它的新 Pod。仅修改服务账户注解不会为现有 Pod 注入新配置；应通过正常 controller rollout 重新创建 Pod。

身份检查时使用第 1 题明确给出的 Pod 清单。当前不支持 `kubectl run --serviceaccount` 这个参数：

```bash
# After deploying the identity-check Pod from question 1.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n irsa-lab \
  get pod irsa-identity-check -o jsonpath='{.status.phase}{"\n"}'
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n irsa-lab logs irsa-identity-check
```

检查 Pod 退出状态，并把返回的账户/assumed-role 身份与预期角色比较。返回节点角色身份并不能证明 IRSA 正常。接下来只测试范围内的应用操作；不带 bucket 的 `aws s3 ls` 会要求列出所有 bucket，不适合单 bucket 策略。

EKS Pod Identity 使用不同机制，并不要求为每个集群创建 IAM OIDC provider。其服务账户关联、agent 和 IAM 信任要求应与 IRSA 分开处理。

参考：[创建 IAM OIDC provider](https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html)、[IRSA 私有连接](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[Pod 配置](https://docs.aws.amazon.com/eks/latest/userguide/pod-configuration.html)。

</details>

8. 如何启用 EKS 控制平面日志导出？
   * A) 在托管控制平面主机安装 agent
   * B) 通过 EKS API、控制台或 eksctl 配置集群日志
   * C) 只在工作节点安装 Fluentd
   * D) SSH 到托管 API server 并编辑配置

<details>
<summary>显示答案</summary>

**答案：B) 通过 EKS API、控制台或 eksctl 配置集群日志**

通过 EKS API、控制台或 eksctl 启用 EKS 控制平面日志导出。AWS 负责运行控制平面主机；在工作节点安装 CloudWatch/Fluentd agent 并不能启用控制平面日志。操作员无法 SSH 到托管控制平面主机。

**AWS CLI：** 检查当前设置并选择需要的日志类型。这是异步更新：记录其 ID，并重复执行 `describe-update`，直到成功或报告失败。日志更新可能要求集群每个子网最多预留五个空闲 IP。

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

若只启用 API/audit 并明确关闭另外三种类型，请在检查 audit/保留要求后使用下面的**替代**日志 payload。不要连续运行两种配置，也不要仅为省钱而关闭必需日志：

```json
{
  "clusterLogging": [
    {"types": ["api", "audit"], "enabled": true},
    {"types": ["authenticator", "controllerManager", "scheduler"], "enabled": false}
  ]
}
```

**eksctl 替代方式：** 预览和应用是两个独立操作；必须提供 `--approve` 才会应用已审查的变更。若确实需要，`--disable-types` 可明确关闭选定类型。

```bash
# Alternative interface; do not submit a second update while one is running.
# Without --approve this previews the logging change.
eksctl utils update-cluster-logging \
  --cluster "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --enable-types api,audit,authenticator,controllerManager,scheduler

# Apply the reviewed change.
eksctl utils update-cluster-logging \
  --cluster "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --enable-types api,audit,authenticator,controllerManager,scheduler --approve
```

**控制台：** 选择集群，打开 **Observability**，进入 **Control plane logging → Manage logging**。选中所需日志类型并保存经过审查的配置。

| 类型 | 用途 | 日志流前缀 |
| --- | --- | --- |
| `api` | API server 组件诊断；初始 flags 仅在日志轮换前已捕获时可用 | `kube-apiserver-` |
| `audit` | 按托管 audit policy 记录的 Kubernetes API 活动 | `kube-apiserver-audit-` |
| `authenticator` | IAM 身份验证诊断 | `authenticator-` |
| `controllerManager` | 内置 Kubernetes 控制循环诊断 | `kube-controller-manager-` |
| `scheduler` | Pod 调度诊断 | `kube-scheduler-` |

Audit 日志不记录每个应用请求，也不记录节点上的每个进程/网络行为。相关 AWS API 活动由 CloudTrail 单独记录。控制平面日志尽力投递，通常在数分钟内到达；启用日志不能恢复已经轮换掉的日志。

**验证导出：** 日志位于集群账户/Region 中的 `/aws/eks/<cluster-name>/cluster`。日志流后缀会轮换；检查近期事件时间，不要假定流名称永久不变。

```bash
aws eks describe-cluster --name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.logging
aws logs describe-log-streams --region "$EXAMPLE_REGION" \
  --log-group-name "/aws/eks/$EXAMPLE_CLUSTER/cluster" \
  --order-by LastEventTime --descending --max-items 10
```

CloudWatch 接收、存储和查询都会产生费用。按需求设置保留时间/访问控制，并确认所需日志类型确实到达。配置更新成功并不代表所有预期历史事件都存在。工作节点/应用日志收集属于另一个数据平面问题。

参考：[EKS 控制平面日志](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)。

</details>

9. 若实例类型是在 EKS 托管节点组请求中指定，而非自定义模板中指定，如何更改？
   * A) 在控制台原位编辑 instanceTypes 字段
   * B) 创建替代节点组并验证工作负载迁移
   * C) 用 kubectl edit node 更改 EC2 硬件
   * D) 向 update-nodegroup-config 传入新的实例类型

<details>
<summary>显示答案</summary>

**答案：B) 创建替代节点组并验证工作负载迁移**

本题讨论的是在**托管节点组请求**中指定的实例类型，而不是自定义启动模板。不能用 `update-nodegroup-config` 修改这些类型；应创建新节点组并迁移工作负载。

若节点组使用自定义启动模板，且实例类型定义在该模板中，则可审查**同一个**模板的新版本，并通过 `update-nodegroup-version` 应用；实例仍会被替换。不要修改 EKS 生成的模板，不要在两个位置都指定类型，也不要假设不同 CPU 架构能使用相同 AMI/镜像。

**1. 创建替代容量。** 检查实例可用情况、配额、架构、CNI/IP 容量、AZ、存储及节点角色权限。下面两个命令是为现有测试集群提供的替代方案：

```bash
# Alternative 1: eksctl, for an unused managed node-group name.
eksctl create nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --name "${NEW_NODEGROUP_NAME:?}" \
  --managed --node-ami-family AmazonLinux2023 --node-private-networking \
  --node-type m5.large --nodes 3 --nodes-min 1 --nodes-max 5 \
  --node-labels "example.com/migration-target=true"

# Alternative 2: AWS CLI; do not run both for the same node group.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=1,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/migration-target":"true"}'
```

**2. 验证新节点组。** 等待其变为 `ACTIVE`，节点健康且为 `Ready`，并确认 CNI/DNS 正常。仅列出 label 不能证明应用已就绪：

```bash
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --query 'nodegroup.{status:status,health:health,types:instanceTypes,subnets:subnets}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l example.com/migration-target=true -o wide
```

**3. 迁移并测试。** 选择符合应用情况的滚动或蓝绿计划。Service 会将流量发往匹配的 Ready Pod endpoint，而不是直接发往某个节点组名称。了解回滚需求和数据兼容性之前，应保留旧容量。

手动 drain 时，先选一个旧节点，确认节点组 label，并检查 PDB、备用容量和本地存储。示例刻意不会绕过驱逐，也不会丢弃 `emptyDir` 数据。如果 drain 失败，先检查原因再继续；节点可能仍处于 cordon 状态。

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

也可以修改实际应用的 Pod 模板，使其选择替代节点组。下面完整示例是为新建 `migration-lab` 命名空间单独编写的演示，不是现有应用的替换清单：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: migration-demo
  template:
    metadata:
      labels:
        app: migration-demo
    spec:
      nodeSelector:
        example.com/migration-target: "true"
      containers:
        - name: nginx
          image: nginx:1.30.6
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              memory: 256Mi
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: migration-demo
  namespace: migration-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: migration-demo
```

此 PDB 要求自愿驱逐期间至少有两个匹配 Pod 健康。若副本数为三，其他条件允许时通常可一次驱逐一个。它不保证可用性，不保护 Pod 直接删除，也不保留节点本地数据。应使用代表性工作负载测试放置、就绪状态、Service 路由、持久卷 AZ 亲和性和备份。

**4. 仅在验证后退役旧节点组。** 不要同时运行 eksctl 和 AWS 删除命令，也不要绕过 PDB 完成迁移。检查目标集群/节点组，只移除此次迁移拥有的节点组：

```bash
# Separate final step, after application/data validation and ownership review.
if [ "${MIGRATION_VERIFIED:?Set yes only after workload and data checks}" = yes ]; then
  eksctl delete nodegroup --cluster "${EXAMPLE_CLUSTER:?}" \
    --region "${EXAMPLE_REGION:?}" --name "${OLD_NODEGROUP_NAME:?}" --approve --wait
fi
```

若应用验证失败，应保留旧节点组。蓝绿迁移会暂时增加容量和成本；对于有状态变更，它不保证容易回滚。`kubectl edit node` 修改的是 Kubernetes 元数据，不是底层 EC2 实例类型。

参考：[启动模板更新](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[UpdateNodegroupConfig](https://docs.aws.amazon.com/eks/latest/APIReference/API_UpdateNodegroupConfig.html)、[drain](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)。

</details>

10. 关于 EKS 托管节点组 taint，哪项陈述正确？
   * A) 只能使用 kubectl 配置 taint
   * B) 通过控制台/API 或 eksctl 配置节点组，并单独验证现有 Node 状态
   * C) EKS 控制台不能配置 taint
   * D) toleration 保证 Pod 被放到匹配的 tainted 节点组

<details>
<summary>显示答案</summary>

**答案：B) 通过控制台/API 或 eksctl 配置节点组，并单独验证现有 Node 状态**

托管节点组 taint 可通过 EKS 控制台/API 或 eksctl 配置文件设置。控制台是有效方法，因此不能仅因 CLI 也可用就判其错误。直接执行 `kubectl taint` 会修改单个 Node 对象，并不是托管节点组替换节点时持久生效的配置。

**eksctl 配置：** 将以下内容保存为针对现有集群和未使用节点组名称的、经过审查的节点组配置，再执行 `eksctl create nodegroup -f nodegroup.yaml`。使用受支持的 `taints` 字段，不要假设存在某个 CLI flag。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: tainted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    labels:
      example.com/pool: batch
    taints:
      - key: dedicated
        value: batch
        effect: NoSchedule
      - key: special
        value: "true"
        effect: PreferNoSchedule
```

**AWS CLI 替代方式：** Kubernetes/eksctl effect 使用 CamelCase，EKS API 则使用大写名称：

| Kubernetes / eksctl | EKS API | 效果 |
| --- | --- | --- |
| `NoSchedule` | `NO_SCHEDULE` | 没有匹配 toleration 时调度器拒绝新 Pod；现有 Pod 保留 |
| `PreferNoSchedule` | `PREFER_NO_SCHEDULE` | 软性调度偏好，不作保证 |
| `NoExecute` | `NO_EXECUTE` | 也会驱逐没有匹配 toleration 的现有 Pod；`tolerationSeconds` 可延迟驱逐 |

```bash
# Alternative to the eksctl file: create a new group through the EKS API.
aws eks create-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name "${NEW_NODEGROUP_NAME:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --instance-types m5.large --ami-type AL2023_x86_64_STANDARD \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --node-role "${NODE_ROLE_ARN:?}" \
  --labels '{"example.com/pool":"batch"}' \
  --taints '[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"},{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]'
```

```bash
# Separate update example for the intended existing group.
if TAINT_UPDATE_ID=$(aws eks update-nodegroup-config \
  --cluster-name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --nodegroup-name "${EXAMPLE_NODEGROUP:?}" \
  --taints '{"addOrUpdateTaints":[{"key":"dedicated","value":"batch","effect":"NO_SCHEDULE"}],"removeTaints":[{"key":"special","value":"true","effect":"PREFER_NO_SCHEDULE"}]}' \
  --query update.id --output text); then
  aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
    --nodegroup-name "$EXAMPLE_NODEGROUP" --update-id "$TAINT_UPDATE_ID" \
    --query 'update.{status:status,errors:errors}'
fi
```

更新为异步操作；等待其成功完成后检查实际 Node taint。即使节点组配置仍列出某项 taint，EKS **也不会**在有人从现有 Node 手动移除 taint 后自动加回。限制可修改节点的人员，并在变更后验证状态。

**专用工作负载放置：** toleration 允许调度，但不会强制 Pod 放到带 taint 的节点组上。应同时设置合适的 node selector/affinity。完整示例使用新建的 `taint-lab` 命名空间：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: batch-example
  namespace: taint-lab
spec:
  nodeSelector:
    example.com/pool: batch
  tolerations:
    - key: dedicated
      operator: Equal
      value: batch
      effect: NoSchedule
  restartPolicy: Never
  containers:
    - name: task
      image: busybox:1.37
      command: ["sh", "-c", "echo batch-example-complete"]
      resources:
        requests:
          cpu: 100m
          memory: 32Mi
        limits:
          memory: 64Mi
```

GPU 节点组还需选择兼容的 GPU 实例/AMI 并安装受支持的 device plugin；工作负载必须请求 `nvidia.com/gpu` 之类的扩展资源。仅添加 `dedicated=gpu` taint 不会安装驱动或分配 GPU。taint 是调度控制，不是租户安全边界。

**维护：** 临时节点 taint 能阻止普通的新调度，但不会 drain 运行中的 Pod。以下两个命令分别用于经过审查的维护窗口开始和结束：

```bash
# Individual-node maintenance example; does not evict existing Pods.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" taint node \
  "${EXAMPLE_NODE_NAME:?}" maintenance=planned:NoSchedule

# After the maintenance window, remove only this exact example taint.
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" taint node \
  "$EXAMPLE_NODE_NAME" maintenance=planned:NoSchedule-
```

若需驱逐，应另行执行考虑 PDB 的 drain 流程。对已有工作负载的节点组添加 `NoExecute` 前，应先检查即时驱逐影响。节点启动注册 flag 也是一种机制，但在此场景中节点组配置更清晰。

参考：[EKS 托管节点 taint](https://docs.aws.amazon.com/eks/latest/userguide/node-taints-managed-node-groups.html)。

</details>

## 实操练习

### 练习 1：配置 IRSA（IAM Roles for Service Accounts）

**场景：** 现有 EKS 集群中的 Linux 工作负载需要读取一个 S3 bucket 中经批准的 `training/` 前缀。应为它配置专用工作负载角色，不要把宽泛的 S3 策略赋给每个节点。

**前置条件：** 使用商业 AWS partition 中获准的培训集群、AWS CLI v2、eksctl 和 jq。操作员须有本练习所需 IAM/Kubernetes 权限。在经批准的 bucket 中准备一个 `training/` 下已有的非敏感对象，并设置 `S3_BUCKET`/`S3_TEST_KEY`。Bucket policy 及任何客户管理加密密钥都必须允许目标角色；仅当对象加密确实需要时，才额外授予范围受限的 KMS 权限。本示例不会创建 bucket 或对象。

<details>
<summary>显示解决方案</summary>

**1. 准备唯一命名空间、私有 kubeconfig 和集群 OIDC provider。** 清理完成前保留生成目录和所有权记录。在同一 Bash 会话中按顺序运行各步骤；若某步失败，重试前先检查已记录资源。

```bash
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

IRSA 需要 STS 连接，工作负载还需要 S3 访问。仅私有环境需要适当的区域 STS/ECR/S3 路径；从 VPC 内创建 IAM OIDC provider 还可能需要 `oidc-eks` 连接。应分别限制 IMDS 和服务账户使用；IRSA 本身不是 Pod 隔离边界。

**2. 创建专用角色和范围受限的策略。** 信任策略同时要求预期 audience 和精确的命名空间/服务账户 subject。权限策略只允许列出该 bucket 的 `training/` 前缀，并且只读取该前缀下对象；不授予 `ListAllMyBuckets`。

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

角色必须是新建角色。创建失败时脚本会在附加策略前停止，并记录不可变的 IAM `RoleId` 以供清理。这可避免把实验策略附加到恰好同名的现有角色。

**3. 创建服务账户和短时测试 Pod。** 三个容器分别检查调用方身份、最多列出一个允许前缀中的对象，并读取所选对象元数据。示例只输出计数/长度并记录身份元数据，不会打印令牌、秘密密钥或对象内容。

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

三个容器都必须成功，身份检查还必须匹配预期账户和角色。若返回节点角色则视为失败。Pod 失败时，检查各容器状态/日志、IAM 信任、前缀、bucket/key policy 和连通性；不要通过附加 `AmazonS3ReadOnlyAccess` 来解决授权失败。

IAM 变更可能需要时间传播。解决原因后，应在所属命名空间中有意重建测试 Pod，不要假设原始失败运行能证明成功。允许某项操作成功，不代表其他所有操作都已拒绝；应审查所有适用 IAM/资源策略，并在需要时执行获准的负向测试。

**4. 清理所属命名空间和角色。** 命名空间 UID 和 IAM RoleId 可防止名称复用。如果命名空间已不存在，可使用记录的角色继续清理。发现意外的内联策略或查询失败时，应停止后续清理；检查部分失败，不要删除无关资源。

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

保留集群、共享 OIDC provider、bucket 和对象。验证命名空间/角色确已移除；若任何步骤失败，保留所有权记录。停止 Pod 并不表示先前签发的所有 STS 凭证都会立即失效。

本次审计没有预置角色，也没有针对 AWS 运行 Pod。本地检查验证了生成的清单/策略和失败保护；实际 IAM 传播、网络可达性和 S3 访问仍须按环境测试。

参考：[IRSA 角色配置](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html)、[IRSA 私有连接](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)、[S3 策略条件](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html)。

</details>

### 练习 2：强化 EKS 集群安全

**场景：** 在专用 EKS 1.36 培训集群中评估特定安全控制。这是集成练习，不是经过测试、可直接用于生产的配置。

**前置条件：** 获准的集群管理权限、AWS CLI v2、kubectl 和 jq；兼容的 EC2 Linux 节点；启用了网络策略的受支持 EKS 托管 VPC CNI；以及 `kube-system` 中常规 CoreDNS Pod。遵循基础概念第 3 题的当前 CNI/内核要求。示例要求 Pod 基线连通性正常；组织级现有策略可能需要另行获准的测试设计。不要仅为完成本练习而安装第二个 CNI。

<details>
<summary>显示解决方案</summary>

**1. 检查目标并保存当前设置。** 使用实际获准的管理出口 CIDR，而不是其他位置所示的文档示例范围。本例会检查 EKS 1.36 和已启用的托管 CNI 策略配置，再继续操作。

```bash
: "${EXAMPLE_CLUSTER:?Use a dedicated EKS 1.36 training cluster}"
: "${EXAMPLE_REGION:?}"
: "${APPROVED_API_CIDR:?Actual approved administration egress CIDR}"
SECURITY_LAB_DIR=$(mktemp -d /tmp/eks-security-lab.XXXXXX)
: "${SECURITY_LAB_DIR:?}"
SECURITY_NAMESPACE="security-quiz-$(date +%s)-$$"
SECURITY_KUBECONFIG="$SECURITY_LAB_DIR/kubeconfig"

aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster --output json > "$SECURITY_LAB_DIR/before-cluster.json" || exit 1
jq -e '.version == "1.36" and .status == "ACTIVE"' \
  "$SECURITY_LAB_DIR/before-cluster.json" >/dev/null || exit 1
aws eks describe-addon --cluster-name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --query addon --output json > "$SECURITY_LAB_DIR/cni.json" || exit 1
jq -e '(.configurationValues // "{}" | fromjson | .enableNetworkPolicy) as $enabled |
  .status == "ACTIVE" and ($enabled == true or $enabled == "true")' \
  "$SECURITY_LAB_DIR/cni.json" >/dev/null || exit 1
aws eks update-kubeconfig --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --kubeconfig "$SECURITY_KUBECONFIG" --alias "$EXAMPLE_CLUSTER" || exit 1

# Serialize cluster configuration updates. A timeout does not cancel an AWS update.
security_wait_update() {
  local update_id="$1" status attempt
  for ((attempt=1; attempt<=60; attempt++)); do
    status=$(aws eks describe-update --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
      --update-id "$update_id" --query update.status --output text) || return 1
    case "$status" in
      Successful) return 0 ;;
      Failed|Cancelled)
        printf 'EKS update %s ended as %s\n' "$update_id" "$status" >&2
        return 1 ;;
      InProgress) sleep 10 ;;
      *) printf 'Unexpected EKS update status: %s\n' "$status" >&2; return 1 ;;
    esac
  done
  printf '%s\n' 'Update still pending; inspect it before another configuration change.' >&2
  return 1
}
```

**2. 按顺序应用经审查的 endpoint/logging 设置。** 下方配置保留两种 API 路径，并将公有路径限制到获准 CIDR。若要采用仅私有端点方案，应先按第 1 部分所述单独验证私有路由/DNS/API 访问。轮询辅助程序超时不会取消 AWS 更新；再次提交变更前先检查更新状态。

EKS 1.36 已对包括 Secret 在内的 Kubernetes API 数据执行信封加密。客户管理密钥配置为空并不表示数据以明文存储。此步骤不要新建集群或重复创建 KMS key。若需要 CMK，按基础概念第 4 题所述审查流程和密钥生命周期注意事项操作。

```bash
# Keep both API paths; the supplied CIDR must include the intended administration path.
SECURITY_ENDPOINT_UPDATE=$(aws eks update-cluster-config \
  --name "${EXAMPLE_CLUSTER:?}" --region "${EXAMPLE_REGION:?}" \
  --resources-vpc-config "endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs=${APPROVED_API_CIDR:?}" \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_ENDPOINT_UPDATE" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" get nodes || exit 1

# EKS 1.36 already has default envelope encryption; inspect rather than create a new cluster.
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query 'cluster.{version:version,encryption:encryptionConfig}'

SECURITY_LOGGING_UPDATE=$(aws eks update-cluster-config \
  --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query update.id --output text) || exit 1
security_wait_update "$SECURITY_LOGGING_UPDATE" || exit 1
aws eks describe-cluster --name "$EXAMPLE_CLUSTER" --region "$EXAMPLE_REGION" \
  --query cluster.logging
```

控制平面日志会产生 CloudWatch 费用，且采用尽力投递。确认目标日志类型确实到达 `/aws/eks/<cluster-name>/cluster`，并设置保留时间/访问控制。端点限制是 IAM/Kubernetes 授权的补充，不能替代授权。

**3. 创建隔离的 Restricted 命名空间和测试工作负载。** 三个 Deployment 会创建由 controller 管理的 Pod，便于可靠测试 VPC CNI 策略。它们使用非 root 用户、RuntimeDefault seccomp、移除的 capability、只读 root filesystem，以及供 backend 临时文件使用的 `emptyDir`。无需 ServiceAccount API token。

```bash
jq -n --arg ns "${SECURITY_NAMESPACE:?}" '{
  apiVersion:"v1",kind:"Namespace",metadata:{name:$ns,labels:{
    "pod-security.kubernetes.io/enforce":"restricted",
    "pod-security.kubernetes.io/enforce-version":"v1.36",
    "pod-security.kubernetes.io/audit":"restricted",
    "pod-security.kubernetes.io/audit-version":"v1.36",
    "pod-security.kubernetes.io/warn":"restricted",
    "pod-security.kubernetes.io/warn-version":"v1.36"
  }}
}' > "${SECURITY_LAB_DIR:?}/namespace.json" || exit 1
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  create -f "$SECURITY_LAB_DIR/namespace.json" || exit 1
SECURITY_NAMESPACE_UID=$(kubectl --kubeconfig "$SECURITY_KUBECONFIG" \
  get namespace "$SECURITY_NAMESPACE" -o jsonpath='{.metadata.uid}') || exit 1
: "${SECURITY_NAMESPACE_UID:?}"
jq -n --arg ns "$SECURITY_NAMESPACE" --arg uid "$SECURITY_NAMESPACE_UID" \
  '{namespace:$ns,uid:$uid}' > "$SECURITY_LAB_DIR/namespace-owner.json" || exit 1

jq -n --arg ns "$SECURITY_NAMESPACE" '
  def deployment($name;$command):
    {
      apiVersion:"apps/v1",kind:"Deployment",metadata:{name:$name,namespace:$ns},
      spec:{replicas:1,selector:{matchLabels:{app:$name}},template:{
        metadata:{labels:{app:$name}},
        spec:{
          nodeSelector:{"kubernetes.io/os":"linux"},
          automountServiceAccountToken:false,
          securityContext:{
            runAsNonRoot:true,runAsUser:1000,runAsGroup:1000,fsGroup:1000,
            seccompProfile:{type:"RuntimeDefault"}
          },
          volumes:[{name:"tmp",emptyDir:{}}],
          containers:[({
            name:"app",image:"busybox:1.37",command:$command,
            securityContext:{
              allowPrivilegeEscalation:false,readOnlyRootFilesystem:true,
              capabilities:{drop:["ALL"]}
            },
            volumeMounts:[{name:"tmp",mountPath:"/tmp"}],
            resources:{requests:{cpu:"50m",memory:"32Mi"},limits:{memory:"64Mi"}}
          } + if $name == "backend" then {
            ports:[{name:"http",containerPort:8080}],
            readinessProbe:{httpGet:{path:"/",port:8080}}
          } else {} end)]
        }
      }}
    };
  {
    apiVersion:"v1",kind:"List",items:[
      deployment("backend";["sh","-c","mkdir -p /tmp/www && printf \"policy-test-ok\\n\" > /tmp/www/index.html && exec httpd -f -p 8080 -h /tmp/www"]),
      deployment("frontend";["sleep","3600"]),
      deployment("outsider";["sleep","3600"]),
      {
        apiVersion:"v1",kind:"Service",metadata:{name:"backend",namespace:$ns},
        spec:{selector:{app:"backend"},ports:[{name:"http",port:8080,targetPort:8080}]}
      }
    ]
  }' > "$SECURITY_LAB_DIR/workloads.json" || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" create -f "$SECURITY_LAB_DIR/workloads.json" || exit 1
for app in backend frontend outsider; do
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
    rollout status "deployment/$app" --timeout=180s || exit 1
done

# Establish baseline connectivity before applying the policies.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ || exit 1
```

应用策略前，两个客户端都必须能访问 backend。如果基线连通性失败，应先解决问题，不要把失败当作策略已强制执行的证据。

**4. 应用默认拒绝和必要允许规则。** 策略设计与基础概念第 3 题相同，但限定在生成的命名空间内。它允许 frontend 到 backend 的 TCP 8080，以及 UDP/TCP 两种常规 CoreDNS 流量。Service 和容器端口相同。

```bash
cat > "${SECURITY_LAB_DIR:?}/networkpolicies.yaml" << EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-ingress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes: [Egress]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dns-egress
  namespace: ${SECURITY_NAMESPACE:?}
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
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
EOF
kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" apply -f "$SECURITY_LAB_DIR/networkpolicies.yaml" || exit 1
```

**5. 验证新连接及正向控制。** 策略收敛后观察无关客户端请求被拒绝，再确认获准的 frontend 请求和 DNS 仍正常。这些观察仅适用于此测试拓扑；遇到异常时应检查策略/agent 状态和日志。

```bash
# Wait briefly for the expected denied fresh connection; do not treat baseline failures as success.
SECURITY_DENY_OBSERVED=false
for ((attempt=1; attempt<=6; attempt++)); do
  if kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" -n "${SECURITY_NAMESPACE:?}" \
    exec deployment/outsider -- wget -qO- -T 5 http://backend:8080/ >/dev/null 2>&1; then
    sleep 2
  else
    SECURITY_DENY_OBSERVED=true
    break
  fi
done
[ "$SECURITY_DENY_OBSERVED" = true ] || {
  printf '%s\n' 'Expected deny was not observed; inspect policy enforcement.' >&2
  exit 1
}

# Positive controls after the denial: allowed application traffic and DNS must still work.
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/frontend -- wget -qO- -T 5 http://backend:8080/ || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" \
  exec deployment/outsider -- nslookup backend || exit 1
kubectl --kubeconfig "$SECURITY_KUBECONFIG" -n "$SECURITY_NAMESPACE" get networkpolicies
```

PSA 会对该命名空间执行 Restricted 标准。若需求超出 PSA，可选用 Kyverno 或 Gatekeeper；使用基础概念第 6 题中的当前 API，并调整其命名空间匹配条件。即使策略在其他命名空间创建成功，也不会对本实验工作负载执行。

**6. 检查相关控制，不要以不完整配方替代。** 只读 `Describe*` IAM policy 无法运行 AWS Load Balancer Controller；应使用与其版本匹配的官方策略，并审查资源/tag 条件。检查节点 IAM、IMDS、安全组和附加组件身份。`maxUnavailable` 控制已发起托管节点更新造成的中断，不会定期安排替换。维护/升级计划应另行审查。

**7. 清理实验命名空间。** 使用记录的 UID；清理失败时保留私有所有权/设置文件。

```bash
CURRENT_SECURITY_UID=$(kubectl --kubeconfig "${SECURITY_KUBECONFIG:?}" \
  get namespace "${SECURITY_NAMESPACE:?}" --ignore-not-found \
  -o jsonpath='{.metadata.uid}') || exit 1
if [ -z "$CURRENT_SECURITY_UID" ]; then
  printf '%s\n' 'Lab namespace is already absent.'
elif [ "$CURRENT_SECURITY_UID" = "${SECURITY_NAMESPACE_UID:?Recorded UID required}" ]; then
  kubectl --kubeconfig "$SECURITY_KUBECONFIG" delete namespace "$SECURITY_NAMESPACE" --wait=true
else
  printf '%s\n' 'Namespace UID mismatch; no deletion attempted.' >&2
  exit 1
fi
```

若保留集群，应复核最终 endpoint/logging 状态以及日志保留和费用。若删除培训集群，应遵循集群生命周期指南，并检查保留的 CloudWatch 日志及独立管理的资源。不要把已关联 KMS key 当作命名空间清理的一部分删除。

本次审计没有执行 AWS 更新，也没有运行 Pod 网络测试。本地检查覆盖生成清单、策略逻辑以及失败/清理保护。生产 IAM、路由、准入、可用性和恢复仍需按具体环境验证。

参考：[网络策略要求](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)、[默认信封加密](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html)、[API 端点访问](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)、[控制平面日志](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)、[Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)。

</details>

## 高级主题

以下问题涉及 Amazon EKS 集群创建的高级主题，用于检查你对高级概念和最佳实践的理解。

1. 以下哪项**不是** EKS IPv6 集群的要求？
   * A) VPC/子网同时具有 IPv4 和 IPv6 地址
   * B) 受支持的 CNI 配置及 IPv6 IAM 权限
   * C) 受支持的 Nitro EC2 节点或 Fargate
   * D) 独立的纯 IPv6 EC2 实例系列

<details>
<summary>显示答案</summary>

**答案：D) 独立的纯 IPv6 EC2 实例系列**

EKS 不要求专门的“纯 IPv6 实例系列”。但它要求使用**受支持的 Nitro EC2 节点或 Fargate**，因此认为任意普通 EC2 实例类型都可用是错误的。

**前置条件：**

1. 创建**新集群**时选择 IPv6 IP family。该设置不可变；在已有 IPv4 集群上修改 `ENABLE_IPV6` 不会把集群转换为 IPv6。
2. 为 VPC/子网关联 IPv4 和 IPv6 CIDR，并在节点子网上启用 IPv6 自动分配。检查 IPv6 路由、安全组、DNS 和管理连接。子网 ID 必须属于预期 VPC/AZ。
3. 使用已配置 IPv6 和 prefix delegation 的受支持 VPC CNI 版本。1.10.1 是历史最低版本，不是当前建议安装版本。不要把旧 1.10 清单覆盖到当前托管附加组件上。
4. 为 CNI 配置 IPv6 IAM 权限，最好使用独立工作负载角色。IPv4 的 `AmazonEKS_CNI_Policy` 不是 IPv6 policy。检查 eksctl IPv6/附加组件流程生成的角色/策略。

```bash
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,az:AvailabilityZone,ipv4:CidrBlock,ipv6:Ipv6CidrBlockAssociationSet,autoIPv6:AssignIpv6AddressOnCreation}'
aws eks describe-addon-versions --region "$EXAMPLE_REGION" \
  --addon-name vpc-cni --kubernetes-version 1.36
```

**示例：** 使用已准备好的双栈私有子网和基于 Nitro 的 AL2023 节点组。替换示例 ID 和公有访问 CIDR。`kubernetesNetworkConfig.ipFamily: IPv6` 是 eksctl 正确写法；EKS API 使用小写 `ipv6`。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: ipv6-lab
  region: us-west-2
  version: "1.36"
kubernetesNetworkConfig:
  ipFamily: IPv6
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      us-west-2a:
        id: subnet-0123456789abcdef0
      us-west-2b:
        id: subnet-0123456789abcdef1
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  publicAccessCIDRs:
    - 203.0.113.10/32
iam:
  withOIDC: true
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
managedNodeGroups:
  - name: ipv6-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
```

将审查后的配置保存为 `ipv6-cluster.yaml`。为环境选择并记录确切兼容的附加组件版本；上面省略版本号，工具会选择兼容的默认版本。这不表示应安装某个历史 CNI 版本。

```bash
# After reviewing real IDs, routing, IAM, access and compatible addon versions.
eksctl create cluster -f ipv6-cluster.yaml --kubeconfig "${EXAMPLE_KUBECONFIG:?}"
```

此配置不会替你设置现有子网路由/IPv6 属性。除了节点/附加组件就绪情况，还要确认已创建访问条目和 CNI 权限。本次审计没有创建 IPv6 集群。

**寻址与流量：**

- EKS 会为 Pod 提供 IPv6 地址，并分配 IPv6 ClusterIP。VPC 是双栈，并不意味着 EKS Pod/Service 也是双栈。
- Pod IPv6 地址来自子网寻址；Service IPv6 地址使用 EKS 在 `fc00::/7` 中分配的唯一本地地址范围。不要假定 Service CIDR 固定为 `fd00::/108`。
- EC2 节点具有 IPv4 和 IPv6 地址。Pod 也可能收到一个未向外报告的主机本地 IPv4 地址，用于访问外部 IPv4 目标，并经节点源 NAT。私有节点访问 IPv4 互联网仍可能需要 NAT；IPv6 不会消除所有 NAT 依赖。
- 原生 IPv6 互联网流量可按方向和安全设计经 internet gateway 或 egress-only internet gateway 传输。并非每个 IPv6 集群都必须使用 egress-only gateway。
- 要将流量负载均衡到 IPv6 Pod，需要兼容的 controller/load balancer 配置及 IP target。也可通过适当的双栈前端提供 IPv4 客户端访问；不要把 Pod 地址族等同于客户端地址族。
- EKS IPv6 集群不支持 Windows 和 VPC CNI 自定义网络。选择地址族前，应检查存储驱动、附加组件和外部依赖的支持情况。

```bash
aws eks describe-cluster --name "${IPV6_CLUSTER_NAME:?}" \
  --region "${EXAMPLE_REGION:?}" --query cluster.kubernetesNetworkConfig
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get pods -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system get services -o wide
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -o wide
```

检查实际地址，并测试 DNS 以及所需 IPv6/IPv4 目的地。仅列出 IPv6 地址并不能证明连通性或可用性。清理时只删除已记录的实验资源，并遵循集群生命周期流程。

参考：[EKS IPv6 行为](https://docs.aws.amazon.com/eks/latest/userguide/cni-ipv6.html)、[eksctl IPv6 教程](https://docs.aws.amazon.com/eks/latest/userguide/deploy-ipv6-cluster.html)、[CNI IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)、[网络配置响应](https://docs.aws.amazon.com/eks/latest/APIReference/API_KubernetesNetworkConfigResponse.html)。

</details>

2. VPC CNI 自定义网络主要支持什么？
   * A) Pod 使用与节点主接口不同的子网/安全组，但仍位于同一 VPC
   * B) 自动防止所有 CIDR 重叠
   * C) 加密所有节点间连接
   * D) 加快控制平面调和速度

<details>
<summary>显示答案</summary>

**答案：A) Pod 使用与节点主接口不同的子网/安全组，但仍位于同一 VPC**

VPC CNI 自定义网络让 **Linux IPv4 EC2 Pod 使用与节点同一 VPC 内的其他子网/安全组**。Pod 地址范围仍属于 VPC 已关联 CIDR。添加辅助 VPC CIDR 可扩充地址空间，但不会自动避免与其他网络重叠。

默认情况下，VPC CNI 会在节点主子网中创建辅助 ENI，并从这些 ENI 以及主 ENI 上符合条件的地址分配地址。启用自定义网络后，普通 Pod IP 来自通过 `ENIConfig` 配置的辅助 ENI；主 ENI 不再用于分配这些 Pod IP。host-network Pod 仍使用主机网络。

**配置步骤：**

1. 规划可用 IPv4 空间、路由和权限。添加辅助 CIDR 时，检查 VPC 关联限制和与连接网络的重叠。AWS 的 `100.64.0.0/10` 共享地址示例不能保证该范围在你的环境中未被使用。
2. 为 Pod 准备备用子网；每个子网必须与对应节点主子网位于**同一 VPC 和同一 AZ**。检查子网路由和安全组规则，包括 API/DNS/工作负载依赖。
3. 为每个预期 Pod 子网创建 `ENIConfig`。以下示例每个 AZ 使用一个子网；替换全部 ID。不要覆盖由其他部署拥有的现有集群级配置。

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-0123456789abcdef0
  securityGroups:
    - sg-0123456789abcdef0
---
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2b
spec:
  subnet: subnet-0123456789abcdef1
  securityGroups:
    - sg-0123456789abcdef0
```

4. 由 CNI 安装的所有者配置自定义网络及 ENIConfig 选择方式。若使用 EKS 托管附加组件，应先检查安装版本 schema，再把环境设置合并到完整且经过审查的配置中：

```yaml
# Merge with existing managed-addon configuration; do not discard other env values.
env:
  AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG: "true"
  ENI_CONFIG_LABEL_DEF: topology.kubernetes.io/zone
```

自管理 DaemonSet 的等效更新如下。它会影响整个集群的 CNI 行为，应纳入计划中的迁移，不应作为普通应用部署随意执行：

```bash
# Self-managed CNI alternative, after preparing ENIConfig/subnets and a rollout plan.
# For an EKS-managed addon, use its supported configuration-values workflow instead.
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system \
  set env daemonset/aws-node AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG=true \
  ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n kube-system \
  rollout status daemonset/aws-node --timeout=5m
```

5. 使用所需配置预置并验证替代节点，然后通过考虑 PDB 的 drain 和应用测试迁移工作负载。修改环境变量不会重新分配现有 Pod 的地址。AWS 建议自定义网络配置使用新节点。迁移验证完成前保留旧容量。

如果设置了 `ENI_CONFIG_LABEL_DEF=topology.kubernetes.io/zone`，每个 `ENIConfig` 都应按 AZ 命名。同一 AZ 中的多个 Pod 子网若需要不同配置，应使用唯一名称和经过审查的自定义节点 label/annotation 映射。已有 ENIConfig 注解选择可能优先于 label。不要修改节点真实 topology label，强行让它使用其他 AZ 的子网。

**容量和安全限制：**

- 不使用主 ENI 会降低 secondary-IP 模式下的 Pod 容量。prefix delegation 可增加地址容量，但仍受子网前缀可用性、实例支持上限和 kubelet `maxPods` 影响。应计算并测试密度，不要照搬一个通用值。
- 默认 `AWS_VPC_K8S_CNI_EXTERNALSNAT=false` 时，发往 VPC 关联 CIDR 之外的流量会经节点主接口执行源 NAT，并使用其子网/安全组。不要假设 ENIConfig 安全组会过滤所有外部流量。
- 与 Security Groups for Pods 同时使用时，该 Pod 的 `SecurityGroupPolicy` 安全组优先于 ENIConfig 组。检查受支持的强制执行/SNAT 模式。
- 自定义网络本身不是加密或租户隔离边界；没有适当网络设计时，它也不能解决重叠 CIDR 的路由问题。
- EKS IPv6 或 Windows 节点不支持该功能。Fargate 通过其 profile 选择子网，不使用 EC2 节点 ENIConfig 映射。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get eniconfigs
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" get nodes -L topology.kubernetes.io/zone
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "${APPLICATION_NAMESPACE:?}" get pods -o wide
aws ec2 describe-subnets --region "${EXAMPLE_REGION:?}" \
  --subnet-ids "${POD_SUBNET_A:?}" "${POD_SUBNET_B:?}" \
  --query 'Subnets[].{id:SubnetId,vpc:VpcId,az:AvailabilityZone,cidr:CidrBlock,free:AvailableIpAddressCount}'
```

核对 Pod IP 与预期子网、节点 AZ、DNS/API 连通性及必要应用流量。仅列出 `ENIConfig` 不能证明迁移或隔离已完成。本例仅静态审查，没有执行 CNI 变更、节点迁移或网络基准测试。

参考：[自定义网络](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network.html)、[配置和迁移](https://docs.aws.amazon.com/eks/latest/userguide/cni-custom-network-tutorial.html)、[自定义网络注意事项](https://docs.aws.amazon.com/eks/latest/best-practices/custom-networking.html)。

</details>

3. 以下哪项**不是** EKS 上 Windows 工作负载的要求？
   * A) 至少两个 Amazon Linux 托管节点组
   * B) 为仅 Linux 的系统 Pod 提供 Linux 或 Fargate 容量
   * C) 兼容的 Windows AMI 和容器镜像
   * D) Windows IPAM 及正确的 IAM/节点身份验证

<details>
<summary>显示答案</summary>

**答案：A) 至少两个 Amazon Linux 托管节点组**

不要求配置两个 Amazon Linux 托管节点组。EKS 需要为 **CoreDNS 等仅 Linux 系统 Pod 提供 Linux 或 Fargate 容量**；这并不要求指定某个 Linux 发行版或两个独立节点组。应按可用性需求规划副本和故障域，不要把最低要求当成高可用设计。

**Windows 前置条件：**

1. 使用当前受支持的 EKS **IPv4** 集群和兼容的 EKS 优化 Windows AMI。AWS 提供 Windows Server 2019、2022 和 2025 变体；本例有意使用 2022，而不是已过时的 Kubernetes 1.14/1.23 支持基线。
2. 确认集群 IAM 角色具有 `AmazonEKSVPCResourceController` 权限，并在 `kube-system/amazon-vpc-cni` 配置中启用 Windows IPAM。
3. 让托管 VPC resource controller 执行 Windows IPAM。不要从浮动的 `master` URL 安装旧数据平面 resource-controller/admission-webhook 清单。
4. 使用专用 Windows 节点 IAM 角色和正确节点身份验证。API 身份验证使用 `EC2_WINDOWS` access entry；托管节点组会管理自己的节点 access entry。使用旧版 `aws-auth` 时，除了 bootstrap/node 组，还要保留必需的 `eks:kube-proxy-windows` 组。

```bash
aws iam list-attached-role-policies --role-name "${EKS_CLUSTER_ROLE_NAME:?}"

# If missing, attach to the reviewed cluster role, not to every worker role.
aws iam attach-role-policy --role-name "$EKS_CLUSTER_ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSVPCResourceController
```

Windows IPAM 设置应合并到现有 VPC CNI 配置中。如果配置由 EKS 或 Helm 管理，应使用其所有者支持的设置，不要替换整个 ConfigMap：

```yaml
# Relevant ConfigMap data; merge through the owning addon/Helm configuration.
data:
  enable-windows-ipam: "true"
```

**节点组示例：** 检查现有集群、子网、AMI 可用性和 IAM 后，将其保存为 `windows-nodegroup.yaml`。taint 用来避免普通 Linux 工作负载意外落到这些节点；Linux 工作负载模板也应明确选择 Linux 节点。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: windows-ng
    amiFamily: WindowsServer2022FullContainer
    instanceType: m5.large
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    privateNetworking: true
    taints:
      - key: example.com/os
        value: windows
        effect: NoSchedule
```

```bash
# Existing, supported IPv4 cluster with Windows IPAM and IAM prerequisites ready.
eksctl create nodegroup -f windows-nodegroup.yaml
aws eks describe-nodegroup --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --nodegroup-name windows-ng \
  --query 'nodegroup.{status:status,ami:amiType,role:nodeRole,health:health}'
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -l kubernetes.io/os=windows -L node.kubernetes.io/windows-build
```

**工作负载示例：** 创建未使用的 `windows-lab` 命名空间，并部署与节点 Windows build 兼容的镜像。EKS 优化 Windows AMI 包含 kubelet、**Windows kube-proxy**、containerd 及相关主机组件；kube-proxy 并非仅适用于 Linux。

使用带有现成 ServiceMonitor entrypoint 的官方 IIS 镜像。旧的 `dotnetbinaries.blob.core.windows.net` ServiceMonitor 下载地址已退役；此处没必要每次 Pod 启动都安装 IIS 并下载二进制文件。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: windows-iis
  namespace: windows-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: windows-iis
  template:
    metadata:
      labels:
        app: windows-iis
    spec:
      os:
        name: windows
      nodeSelector:
        kubernetes.io/os: windows
        kubernetes.io/arch: amd64
        node.kubernetes.io/windows-build: "10.0.20348"
      tolerations:
        - key: example.com/os
          operator: Equal
          value: windows
          effect: NoSchedule
      containers:
        - name: iis
          image: mcr.microsoft.com/windows/servercore/iis:windowsservercore-ltsc2022
          ports:
            - containerPort: 80
          startupProbe:
            httpGet:
              path: /
              port: 80
            periodSeconds: 10
            failureThreshold: 60
          readinessProbe:
            httpGet:
              path: /
              port: 80
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              memory: 1Gi
```

镜像标签已根据 Microsoft 镜像 README 和 registry 元数据核实。本次审计没有下载镜像层，也没有运行 Windows 工作负载。资源值仅为示例。投入生产前，应检查实际 rollout/readiness、DNS、应用流量以及主机/容器 build 兼容性。

**支持范围：**

- Windows 不能作为 EKS Fargate Pod、EKS Auto Mode 节点或 EKS Hybrid Nodes 运行。它不支持 EKS IPv6、VPC CNI 自定义网络或 Security Groups for Pods。
- 普通 Windows Pod 与特权 Linux 容器不同。Windows **HostProcess** Pod 可使用 host networking，因此笼统地说“Windows 从不支持 hostNetwork”是错误的。HostProcess 需要单独进行高权限安全审查。
- Windows 网络/IP 容量与 Linux 不同。应检查单 ENI 上限和受支持的 prefix delegation，不要假设 Linux Pod 密度计算也适用。
- 选择支持 Windows 的存储驱动并验证卷/路径语义。不要假设 Linux hostPath 权限或所有 CSI 功能都可移植。
- EKS 优化 Windows 节点使用 containerd；Linux 应用镜像应运行在 Linux 节点上。在混合 OS 集群中，核实系统附加组件及应用的放置位置。

参考：[EKS Windows 支持](https://docs.aws.amazon.com/eks/latest/userguide/windows-support.html)、[优化的 Windows AMI](https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-windows-ami.html)、[Microsoft IIS 镜像](https://github.com/microsoft/iis-docker)、[Windows HostProcess](https://kubernetes.io/docs/tasks/configure-pod-container/create-hostprocess-pod/)。

</details>

4. EC2 实例元数据请求中，哪项设置要求使用 session token？
   * A) HttpTokens=required（仅 IMDSv2）
   * B) 为 169.254.169.254 配置安全组规则
   * C) Kubernetes Node label
   * D) 单独设置应用 ServiceAccount 名称

<details>
<summary>显示答案</summary>

**答案：A) HttpTokens=required（仅 IMDSv2）**

要求使用 IMDSv2（`HttpTokens: required`）会禁用不带令牌的 IMDSv1 调用，提供纵深防御。它**不能**消除所有 SSRF，也不能在共享主机的容器之间建立安全边界。

**启动模板设置：** 以下是 EC2 `LaunchTemplateData` 片段，不是 `managedNodeGroups.metadataOptions` 字段。hop limit 为 1 的假设是普通 Pod 使用 IRSA/Pod Identity，而非提取节点凭证：

```json
{
  "MetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 1,
    "HttpEndpoint": "enabled"
  }
}
```

hop limit 限制的是 IMDS token **PUT 响应**，不是每个元数据请求。确实需要 IMDSv2 的容器可能要求 hop limit 为 2。检查兼容性并将应用权限迁移到工作负载角色；不要仅为了掩盖原因不明的故障而调高限制。

通过受支持的 eksctl `launchTemplate.id/version` 字段使用现有且经过审查的模板版本。下面的模板 ID 必须替换；`--launch-template-name` 不是文档规定的 `eksctl create nodegroup` 接口：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-template-ng
    launchTemplate:
      id: lt-0123456789abcdef0
      version: "1"
    privateNetworking: true
```

**eksctl 替代方式：** 新建节点组时可使用受支持的 `disableIMDSv1` 和 `disablePodIMDS` 字段。请先准备所需工作负载身份。`disablePodIMDS` 针对非 host-network Pod，且不能与 `withAddonPolicies` 同时使用。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: imds-restricted-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 4
    disableIMDSv1: true
    disablePodIMDS: true
```

这两种配置是替代方案；应检查实际生成的模板和节点元数据设置。默认值取决于实例启动设置、账户/Region 默认值及 AMI 元数据支持情况，并以启动设置为优先。不要假设所有 AMI/节点组默认 hop limit 都是 1。

**现有节点：** 可以通过托管节点组更新，滚动发布同一自定义启动模板的新版本。也可在符合 IAM/SCP 限制时，修改单个运行中/已停止 EC2 实例的元数据选项；但这不会单独更新未来替换节点的配置：

```bash
# Inspect the explicitly reviewed instance before changing its metadata settings.
aws ec2 describe-instances --region "${EXAMPLE_REGION:?}" \
  --instance-ids "${REVIEWED_INSTANCE_ID:?}" \
  --query 'Reservations[].Instances[].{id:InstanceId,tags:Tags,metadata:MetadataOptions}'

# Separate transition step for a tested instance with compatible host agents.
aws ec2 modify-instance-metadata-options --region "$EXAMPLE_REGION" \
  --instance-id "$REVIEWED_INSTANCE_ID" --http-tokens required \
  --http-put-response-hop-limit 1 --http-endpoint enabled
```

验证选项已达到 `applied` 状态，并确认节点 agent、镜像拉取和工作负载凭证仍可用。不要仅因应用使用 IRSA 就禁用整个元数据端点：主机组件仍可能依赖节点实例配置文件和元数据。

**其他控制：**

- 限定节点角色权限，并给应用分配自己的角色。IRSA/Pod Identity 本身不能阻止通过其他路径访问节点 IMDS。
- `hostNetwork` Pod 可访问 IMDS；权限足够高的主机工作负载也可能绕过 Pod 网络隔离。应分别控制 Pod 特权和主机访问。
- 安全组不会过滤实例的 link-local 元数据服务。若要再加主机/网络限制，应考虑真实 Pod 流量路径以及可选的 IPv6 IMDS endpoint (`fd00:ec2::254`) 和 IPv4。旧的临时 `PREROUTING -i eth0` DNAT 规则不是通用可靠的 Pod IMDS 限制方案。
- 使用受支持的 SDK，并测试元数据访问；不要打印 session token 或 IAM 凭证值。应检查实际实例元数据选项，不要把节点 Kubernetes label 当作已执行限制的证明。

参考：[IMDS 选项和优先级](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)、[IMDSv2 行为](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html)、[eksctl 安全选项](https://docs.aws.amazon.com/eks/latest/eksctl/security.html)、[IRSA 隔离限制](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)。

</details>

5. 哪项任务不属于 EC2 节点引导配置的用途？
   * A) 修改 EKS 管理的控制平面进程
   * B) 配置自定义 AMI 中已安装并经过审查的软件
   * C) 应用经工作负载验证的主机设置
   * D) 设置受支持的节点组 label 和 taint

<details>
<summary>显示答案</summary>

**答案：A) 修改 EKS 管理的控制平面进程**

节点引导配置用于配置**节点主机**，不用于配置 EKS 托管的 API server、scheduler、controller manager 或 etcd。AL2023 应使用 `nodeadm` 和受支持的 eksctl/启动模板路径；旧 AL2 `bootstrap.sh`/`kubeletExtraArgs` 示例不适用。

**有计划地安装和配置软件。** 使用适用于目标 OS/架构的已验证软件包，最好将其烘焙进经过审查的 AMI。每次启动时从网络下载未验证的 `latest` RPM 并不可复现。主机 agent 还需要适当 IAM 权限及私有/公有服务连接。

下面的可选 AL2023 主机示例假设 CloudWatch agent 已安装。它配置主机内存/swap 指标并启动 agent；若 AWS 访问可用，会发送计费遥测。不要在管理工作站、Bottlerocket 或 Auto Mode 上运行：

```bash
#!/bin/bash
# AL2023 host example: the reviewed AMI must already contain the verified agent package.
set -euo pipefail
AGENT_CTL=/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
test -x "$AGENT_CTL" || {
  printf '%s\n' 'CloudWatch agent is not installed in this AMI.' >&2
  exit 1
}
cat > /opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": {"measurement": ["mem_used_percent"]},
      "swap": {"measurement": ["swap_used_percent"]}
    }
  }
}
EOF
"$AGENT_CTL" -a fetch-config -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/cloudwatch-agent.json -s
```

**内核调优：** 根据工作负载证据和实际内核/CNI 要求调整。此处保留原示例值作为尚未验证的调优参考，并非通用性能建议：

| 示例设置 | 原示例值 | 审查要求 |
| --- | --- | --- |
| `net.ipv4.ip_forward` | `1` | 节点/CNI 路由需求 |
| `net.bridge.bridge-nf-call-iptables` | `1` | bridge 模块和 CNI datapath 是否要求 |
| `net.ipv4.tcp_keepalive_time` | `600` | 应用/连接超时行为 |
| `net.ipv4.tcp_max_syn_backlog`、`net.core.somaxconn`、`net.core.netdev_max_backlog` | `40000` | 实际队列压力、内存及工作负载测量 |
| `vm.max_map_count` | `262144` | 特定应用的映射需求 |

不要把此表作为通用节点脚本应用。记录基线，在测试节点组验证更改，并保留回滚路径。

**磁盘：** 绝不要对假定的 `/dev/nvme1n1` 执行 `mkfs`。NVMe 枚举不是稳定的所有权标识，该设备也可能包含必需数据。格式化前，按 volume ID/serial 确认目标 EBS 卷，确认它是新建且可丢弃或已明确准备好的设备，并检查分区、文件系统和挂载。持久挂载配置应使用文件系统 UUID 等稳定标识。

```bash
# Read-only inspection on the specifically authorized test node.
lsblk --output NAME,PATH,TYPE,SIZE,FSTYPE,UUID,MOUNTPOINTS,SERIAL
findmnt
sysctl net.ipv4.ip_forward vm.max_map_count
```

对于持久应用数据，应优先使用合适的 CSI/PV 生命周期，而不是让数据绑定到节点的临时磁盘。上面的检查命令不会格式化或挂载任何内容。

**Label、taint 与安全：** 使用托管节点组 label/taint 字段以及自有域名；不要覆盖 provider 管理的拓扑/节点组 label。主机加固应使用经审查的 AMI 和安全组/CNI 设计。引导时随意通过 SSH 修改防火墙可能与现有规则冲突或切断访问，也不是完整加固流程。

**启动模板用户数据：** 若使用 EKS 选择的 AL2023 AMI，且未指定自定义 `ImageId`，EKS 会提供所需的默认 NodeConfig。最小 MIME 自定义示例如下：

```text
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="EKS_BOOTSTRAP_EXAMPLE"

--EKS_BOOTSTRAP_EXAMPLE
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/company

--EKS_BOOTSTRAP_EXAMPLE--
```

```bash
# Prepare real EC2 UserData JSON from the reviewed MIME file; no placeholder base64.
BOOTSTRAP_DIR=$(mktemp -d /tmp/eks-bootstrap-example.XXXXXX)
: "${BOOTSTRAP_DIR:?}"
jq -n --rawfile data "${REVIEWED_MIME_FILE:?}" \
  '{UserData:($data|@base64)}' > "$BOOTSTRAP_DIR/launch-template-data.json" || exit 1
aws ec2 create-launch-template --region "${EXAMPLE_REGION:?}" \
  --launch-template-name "${NEW_LAUNCH_TEMPLATE_NAME:?}" \
  --version-description "Reviewed AL2023 customization" \
  --launch-template-data "file://$BOOTSTRAP_DIR/launch-template-data.json" \
  --query 'LaunchTemplate.{id:LaunchTemplateId,version:LatestVersionNumber}'
```

如高级题 4 所示，使用返回的模板 ID/版本配置 `managedNodeGroups[].launchTemplate`。若在 eksctl 生成配置之外指定自定义 AMI ID，还必须提供第 5 题所述完整集群 NodeConfig。不要手动启动 kubelet，也不要再次调用 `nodeadm init`。

**eksctl 替代方式：** 下列配置使用受支持节点组字段和无害的预引导目录创建命令。只添加经过审查的主机自定义项。`preBootstrapCommands` 包含 shell 命令；需要自定义 AL2023 NodeConfig 时，`overrideBootstrapCommand` 中应放 NodeConfig YAML。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
  - name: custom-ng
    amiFamily: AmazonLinux2023
    instanceType: m5.large
    privateNetworking: true
    desiredCapacity: 2
    minSize: 2
    maxSize: 5
    labels:
      example.com/environment: test
      example.com/node-type: compute
    taints:
      - key: dedicated
        value: compute
        effect: NoSchedule
    preBootstrapCommands:
      - install -d -m 0755 /opt/company
```

这些示例并未作为生产节点配方实际启动。应在自己的环境验证软件包来源、有效 nodeadm/kubelet 配置、启动故障、网络和工作负载健康。

**CoreDNS 属于数据平面工作负载/附加组件**，通常是运行在 Linux EC2 或受支持 Fargate 容量上的 Deployment，而不是 EKS 托管控制平面进程。应通过附加组件/Kubernetes 流程配置。EKS 控制平面可公开配置的 API 设置（如日志）与节点用户数据彼此独立。

参考：[AL2023 初始化](https://docs.aws.amazon.com/eks/latest/userguide/al2023.html)、[eksctl 引导](https://docs.aws.amazon.com/eks/latest/eksctl/node-bootstrapping.html)、[启动模板限制](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)、[CloudWatch agent 配置](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-Configuration-File-Details.html)。

</details>
