# 将 EKS 节点 IAM 权限迁移到 IRSA 和 Pod Identity

> **最后更新**：2026年11月21日

当应用的 S3 权限附加到 EC2 节点的实例配置文件（即节点 IAM 角色）时，该节点上所有能够访问实例元数据服务（IMDS）的 Pod 都会获得相同的权限。为一个 payments Pod 添加授权，也会让该节点上的日志采集器和批处理 Jobs 获得该权限。CloudTrail 会将它们全部记录为同一个节点实例会话，因此你无法判断是哪个工作负载发起了调用。

本手册对比了将该权限迁移到每个工作负载各自的身份的两种方式：IRSA（ServiceAccount 的 IAM 角色）和 EKS Pod Identity。随后，手册会说明生产集群的迁移顺序，并展示一个实时演示，其中并排迁移同一应用的三个副本。

## 凭证从何而来

![三个 Pod 通过三种路径获取凭证。节点角色 Pod 从 IMDSv2 获取凭证，IRSA Pod 从 STS AssumeRoleWithWebIdentity 获取凭证，Pod Identity Pod 则通过其所在节点上的 Pod Identity Agent 和 EKS Auth 获取凭证。每个 Pod 都使用收到的凭证为其 S3 请求签名。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

Pod 内的 AWS SDK 和 AWS CLI 会从上到下遍历[默认凭证提供程序链](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)。环境变量中的静态密钥、Web 身份令牌（IRSA）和容器凭证提供程序（Pod Identity）都排在 IMDS 之前。因此，对于 EKS 注入了 IRSA 或 Pod Identity 变量的新 Pod，无需更改代码即可使用新的角色。没有注入任何内容的 Pod 会继续执行到最后一步 IMDS，并获得节点角色。

| 路径 | 注入 Pod 的内容 | SDK 调用 | 最终角色 |
| --- | --- | --- | --- |
| 节点实例配置文件 | 无 | IMDSv2 `169.254.169.254` | 节点 IAM 角色（该节点上的所有 Pod 共享） |
| IRSA | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、令牌卷 | 区域 STS（安全令牌服务）`AssumeRoleWithWebIdentity` | ServiceAccount 注解中指定的角色 |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、令牌卷 | 同一节点上的 Pod Identity Agent，`169.254.170.23` | 关联中指定的角色 |

**谁会注入变量，以及何时注入。** 创建 Pod 时，API 服务器会对请求进行身份验证和授权，然后在变更准入阶段调用 Webhook `iam-for-pods.amazonaws.com`（amazon-eks-pod-identity-webhook）。EKS 在控制平面内运行此 Webhook，因此你的节点上没有 Webhook Pod。Webhook 会检查 Pod 的 ServiceAccount：如果存在关联，它会添加 Pod Identity 变量和令牌卷；如果只有 IRSA 注解，它会添加 IRSA 变量和令牌卷；如果两者都有，它只会添加 Pod Identity。随后，kubelet 会为相应受众请求投射令牌并将其挂载。演示集群的 `MutatingWebhookConfiguration` 只有一条规则 `CREATE pods`，且 `failurePolicy: Ignore`。因此，运行中的 Pod 不会发生变化，直到执行滚动更新；如果 Webhook 无法响应，Pod 仍会创建，但不会带有这些变量，并会悄然使用节点角色。可以通过调用方 ARN 检查结果；在创建 Pod 之前，可以使用 `kubectl create --dry-run=server` 查看经过 Webhook 处理后的 Pod 规格。

当 IMDS 响应跳数限制为 2 或更大时，未使用主机网络的普通 Pod 可以获取 IMDSv2 令牌和节点角色的凭证。托管节点组的启动模板通常会将此值设为 2。因此，迁移的最后一步会将跳数限制降为 1。

<a id="irsa-flow"></a>
## IRSA 的工作方式

![IRSA 流程。Webhook 检查 ServiceAccount 注解，并注入环境变量和投射令牌（aud sts.amazonaws.com）。SDK 将令牌发送给 STS AssumeRoleWithWebIdentity；STS 通过 IAM OIDC 提供程序验证签名，检查信任策略中的 aud 和 sub，并返回临时凭证。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-1.svg)

1. **设置信任关系。** 每个集群都有一个 OIDC（OpenID Connect）颁发者 URL。在账户中将该颁发者注册为 IAM OIDC 提供程序，一次即可。角色的信任策略会将该提供程序指定为其 `Federated` 主体，并根据 `aud`（`sts.amazonaws.com`）和 `sub`（`system:serviceaccount:<namespace>:<serviceaccount>`）设置条件。
2. **创建 Pod 时注入。** 当 ServiceAccount 带有 `eks.amazonaws.com/role-arn` 时，EKS 变更 Webhook 会向每个新 Pod 添加 `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`，以及位于 `/var/run/secrets/eks.amazonaws.com/serviceaccount/token` 的投射令牌卷。运行中的 Pod 不会发生变化，因此需要滚动更新。
3. **签发和刷新令牌。** kubelet 会为受众 `sts.amazonaws.com` 请求 ServiceAccount 令牌，将其写入文件，并在令牌过期前刷新。
4. **交换令牌。** SDK 将令牌发送给区域 STS `AssumeRoleWithWebIdentity`。STS 使用通过 IAM OIDC 提供程序注册的颁发者密钥验证令牌签名，检查 `aud` 和 `sub` 条件，然后返回临时凭证。Pod 会直接与 STS 通信，因此需要能够访问 STS 的网络路径。[AWS IRSA 文档](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## EKS Pod Identity 的工作方式

![Pod Identity 流程。EKS API 中的关联将 ServiceAccount 映射到角色，EKS 会注入容器凭证变量和投射令牌（aud pods.eks.amazonaws.com）。SDK 调用所在节点上的 Pod Identity Agent；Agent 使用节点角色的 eks-auth 权限调用 EKS Auth AssumeRoleForPodIdentity，EKS 随后返回带有会话标签的角色凭证。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-2.svg)

1. **安装 Agent。** 每个集群安装一次 `eks-pod-identity-agent` add-on。Agent 是运行在节点主机网络上的 DaemonSet，使用链路本地地址 `169.254.170.23`（IPv6 `[fd00:ec2::23]`）上的端口 80 和 2703。EKS Auto Mode 已内置该 Agent。
2. **角色和关联。** 角色信任服务主体 `pods.eks.amazonaws.com`，以执行 `sts:AssumeRole` 和 `sts:TagSession`。无需按集群配置提供程序，因此同一个角色可以在另一个集群中使用，无需更改信任策略。绑定是 EKS API 中的一个关联（集群、命名空间、ServiceAccount → 角色）；无需注解 Kubernetes 对象。
3. **创建 Pod 时注入。** 对于带有关联的 ServiceAccount，EKS 会向新 Pod 注入 `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`，以及受众为 `pods.eks.amazonaws.com` 的投射令牌。
4. **查找凭证。** SDK 会将令牌发送给所在节点上的 Agent。Agent 使用节点角色的 `eks-auth:AssumeRoleForPodIdentity` 权限调用 EKS Auth（该权限属于 `AmazonEKSWorkerNodePolicy`）。EKS Auth 会验证令牌和关联，代入该角色，并返回带有会话标签的凭证，例如 `eks-cluster-arn`、`kubernetes-namespace` 和 `kubernetes-service-account`。节点角色只保留 Agent 调用 EKS Auth 所需的权限；应用的业务权限则属于 Pod Identity 角色。[Pod Identity 的工作方式](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## IRSA 与 Pod Identity 对比

AWS 建议尽可能使用 EKS Pod Identity。对于某些运行时和团队组织方式，IRSA 仍然适用。[AWS 对比说明](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| 属性 | IRSA | EKS Pod Identity |
| --- | --- | --- |
| 每个集群的设置 | 为每个集群注册一个 IAM OIDC 提供程序 | 为每个集群安装 Pod Identity Agent add-on（Auto Mode 已内置） |
| 绑定所在位置 | Kubernetes ServiceAccount 注解 | EKS API 关联（不更改 Kubernetes 对象） |
| 信任策略 | `Federated` OIDC 提供程序，并带有 `aud`/`sub` 条件；每个集群需增加一条语句 | 一个主体 `pods.eks.amazonaws.com`；新集群无需更改 |
| 扩展限制 | 每个账户默认最多 100 个 OIDC 提供程序；默认 2,048 个字符的信任策略通常可容纳每个角色约四个绑定 | 每个集群 5,000 个关联；角色信任策略不会增长 |
| 凭证路径 | Pod → 区域 STS（Pod 使用 STS API 配额） | Pod → 节点 Agent → EKS Auth（Pod 不调用 STS） |
| 会话信息 | 角色会话名称；没有会话标签 | 集群、命名空间和 ServiceAccount 会话标签可启用 ABAC（基于属性的访问控制） |
| 运行时 | EKS on EC2 和 Fargate、EKS Anywhere、ROSA、在 EC2 上自我管理的 Kubernetes | EKS 中的 Linux EC2 节点以及 EKS Hybrid Nodes（需要 Agent 的 hybrid DaemonSet 和节点凭证文件）；不支持 Fargate、Windows、Outposts 或 EKS Anywhere |
| 跨账户 | 目标账户中的角色信任此集群的 OIDC 提供程序 | 关联角色位于集群所在账户；通过目标角色或角色链进行委派 |
| 职责分离 | IAM 管理员创建 OIDC 提供程序；集群操作员添加注解 | IAM 只管理角色；绑定位于 EKS API 中 |

简而言之，对于在 EC2 上运行的新 EKS 工作负载，Pod Identity 更简单，也更易于扩展。对于 Fargate 或 Windows 节点，或者同一套配置还必须在 EKS 之外的 Kubernetes 上运行时，请使用 IRSA。两者可以在同一集群中运行。如果一个 ServiceAccount 同时带有 IRSA 注解和关联，EKS Webhook 在新 Pod 中只会注入 Pod Identity 变量，不会注入 IRSA 变量。在演示集群中，使用 `kubectl create --dry-run=server` 检查时发现，只有注解时会返回 `AWS_ROLE_ARN` 和 `AWS_WEB_IDENTITY_TOKEN_FILE`；添加关联后则只返回 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`。运行中的 Pod 会一直保留 IRSA 变量，直到重新创建，因此应通过滚动更新切换，并移除未使用的注解。

两者都可以在 EKS Hybrid Nodes 上运行。IRSA 只需要 Pod 能够访问 STS。Pod Identity Agent 通常从节点的 IMDS 获取凭证，而混合节点没有 IMDS，因此需要在节点的 `nodeadm` 配置中设置 `spec.hybrid.enableCredentialsFile: true`，以创建 `/eks-hybrid/.aws/credentials`，并在 Agent add-on（v1.3.3-eksbuild.1 或更高版本）配置中启用 `daemonsets.hybrid.create`。Bottlerocket 需要 add-on v1.3.7-eksbuild.2 或更高版本、OS 1.39.0 或更高版本，以及 `daemonsets.hybrid-bottlerocket.create`。[为混合节点配置 add-on](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html) · [节点引导](../eks-hybrid-nodes/04-node-bootstrap.md)

在私有集群中，为 IRSA Pod 确保通往区域 STS 的路径，并为 Pod Identity Agent 确保通往 EKS Auth（`eks-auth`）的路径。如果没有互联网访问路径，请检查对应的 VPC 接口端点、DNS 和安全组。如果位于代理之后，请将 `169.254.170.23` 和 `[fd00:ec2::23]` 添加到 `NO_PROXY`。[Pod Identity 注意事项](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [私有集群要求](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## 生产集群的迁移顺序

1. **盘点依赖项。** 将节点角色策略与 CloudTrail 实际记录的 IAM 会话进行比较，并列出 Deployments、StatefulSets、DaemonSets、CronJobs 和控制器调用的 AWS API。要在 CloudTrail 中查看 S3 对象访问，需要为相应存储桶启用数据事件。保留用于节点注册和 Pod Identity Agent 的 `AmazonEKSWorkerNodePolicy`，以及用于从 Amazon ECR（Elastic Container Registry）拉取镜像的 `AmazonEC2ContainerRegistryPullOnly`（或等效策略）。VPC CNI（容器网络接口）的 `AmazonEKS_CNI_Policy` 可以迁移到专用的 `aws-node` 角色；从节点角色中移除该策略之前，请验证 CNI 凭证和新 Pod 的 IP 分配。[EKS 节点 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 CloudTrail 事件](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **为每个工作负载创建范围受限的 IAM 角色和专用 ServiceAccount。** 对于 IRSA，将集群颁发者注册为 IAM OIDC 提供程序，创建检查确切受众和主体的角色，并使用 `eks.amazonaws.com/role-arn` 注解 ServiceAccount。对于 Pod Identity，检查 Agent 是否就绪以及节点是否拥有 EKS Auth 权限，然后创建一个由请求标签限定范围的角色关联。确认计算环境和 SDK 均受支持。[IRSA SDK 版本](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity SDK 版本](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **创建金丝雀 Pod。** 更改 Pod 模板中的 `serviceAccountName`，或滚动创建新 Pod，然后检查注入的变量名称、运行进程的调用方 ARN，以及它需要使用的 AWS API。切勿记录令牌或密钥。显式凭证或默认凭证链中优先级更高的提供程序可能会优先使用。[默认凭证提供程序链](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **逐个切换工作负载。** 监控错误率、`AccessDenied`、令牌和凭证刷新情况，以及计划任务运行情况。工作负载不再依赖节点角色的业务权限后，只移除相应的策略语句。在回滚窗口内保留之前的 Pod 模板，以及节点策略的精确副本。如果移除权限后需要回滚，应先恢复最小限度的策略，确认其已生效，然后再部署之前的 Pod。
5. **限制节点凭证访问。** 从已测试兼容性的节点组开始，强制使用 IMDSv2 并限制普通 Pod 对 IMDS 的访问。对于使用自定义启动模板的托管节点组，请在新模板版本中将 `HttpTokens=required` 和 `HttpPutResponseHopLimit=1`，然后滚动更新节点。Karpenter 使用 `EC2NodeClass.spec.metadataOptions`；EKS Auto Mode 默认会强制使用 IMDSv2，并将跳数限制设为 1。无论跳数限制如何，使用 `hostNetwork` 的 Pod 都能访问 IMDS，因此需要单独进行控制。不要关闭 IMDS（`HttpEndpoint=disabled`）：Pod Identity Agent 本身运行在主机网络上，需要从 IMDS 获取节点角色凭证以调用 EKS Auth。[托管节点组启动模板](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [EKS IAM 最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>信任策略和金丝雀命令</summary>

IRSA 角色信任策略会限定集群颁发者和 ServiceAccount。对于 `<OIDC_ISSUER>`，请使用不带 `https://` 的颁发者地址。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<OIDC_ISSUER>"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {"StringEquals": {
      "<OIDC_ISSUER>:aud": "sts.amazonaws.com",
      "<OIDC_ISSUER>:sub": "system:serviceaccount:<NAMESPACE>:<IRSA_SA>"
    }}
  }]
}
```

Pod Identity 角色信任 EKS 服务主体。这些条件通过会话标签限定集群、命名空间和 ServiceAccount，因此请在关联中启用会话标签。

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "pods.eks.amazonaws.com"},
    "Action": ["sts:AssumeRole", "sts:TagSession"],
    "Condition": {"StringEquals": {
      "aws:RequestTag/eks-cluster-arn": "<CLUSTER_ARN>",
      "aws:RequestTag/kubernetes-namespace": "<NAMESPACE>",
      "aws:RequestTag/kubernetes-service-account": "<POD_IDENTITY_SA>"
    }}
  }]
}
```

```bash
# If you chose IRSA
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" annotate sa "$IRSA_SA" \
  "eks.amazonaws.com/role-arn=$IRSA_ROLE_ARN"

# If you chose Pod Identity and the Agent is ready
aws eks create-pod-identity-association --region "$AWS_REGION" --cluster-name "$CLUSTER" \
  --namespace "$NAMESPACE" --service-account "$POD_IDENTITY_SA" --role-arn "$POD_IDENTITY_ROLE_ARN"

# Roll out the canary with the ServiceAccount chosen above
SA="$IRSA_SA"   # or "$POD_IDENTITY_SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set serviceaccount \
  deployment "$CANARY_DEPLOYMENT" "$SA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
  "deployment/$CANARY_DEPLOYMENT" --timeout=5m
```

</details>

<a id="live-demo"></a>
## 实时演示：迁移同一应用的三个副本

![演示流程。最初，orders 应用的三个副本都从 IMDS 获取节点角色并读取 S3。执行 migrate-irsa 后，一个副本从 STS 获取 IRSA 角色；执行 migrate-podid 后，另一个副本通过 Agent 获取 Pod Identity 角色。执行 revoke 移除节点角色的 S3 权限后，只有旧版副本被拒绝访问。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-3.svg)

此演示会在现有 EKS 1.36 集群中添加一个专用托管节点组（t3.medium、私有子网、带污点），并在其上运行同一 orders 应用的三个副本。每个副本每 3 秒调用一次 STS `GetCallerIdentity` 和 S3 `GetObject`，并输出一行 JSON，包含凭证来源、角色名称和 S3 结果。初始状态与集群的生产节点组一致：要求使用 IMDSv2，跳数限制为 2，且节点角色拥有应用的 `s3:GetObject` 权限。旧版 Pod 是未使用主机网络的普通 Pod。[演示代码和演讲者操作手册](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [幻灯片（韩语）](https://presentation.atomai.click/eks-workload-identity/)

```bash
cd examples/security/eks-workload-identity
export AWS_REGION=ap-northeast-2
export CLUSTER=<cluster name> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
./demo.sh up d1124            # before the talk: node group, roles, bucket, three copies
./demo.sh watch d1124         # second terminal: live table
./demo.sh migrate-irsa d1124  # ServiceAccount annotation + rollout
./demo.sh migrate-podid d1124 # association + injection check + rollout
./demo.sh diff d1124          # compare injected variables, tokens, trust policies
./demo.sh revoke d1124        # remove the S3 permission from the node role
./demo.sh harden d1124        # (optional, ~15 min) roll the nodes to hop limit 1
./demo.sh restore d1124       # back to the start (rehearse again)
./demo.sh down d1124          # clean up
```

使用 `page-up` 可以与观众分享只读实时页面。请求路径为 CloudFront → VPC 源站 → 内部 ALB → dashboard Pod，ALB 安全组只允许 CloudFront VPC 源站访问。dashboard Pod 没有 IAM 角色，只有一个可读取此命名空间中 Pod 和日志的 Role；由于演示节点的跳数限制为 2，NetworkPolicy 会阻止它访问 IMDS 或 Pod Identity Agent。此隔离需要启用 VPC CNI 网络策略强制执行（`enableNetworkPolicy`），`page-up` 会先检查这一点。

脚本创建的所有资源都会在名称中带有运行 ID，或带有 `LabRun` 标签；脚本只会更改或删除名称或标签匹配的资源。脚本不会创建 VPC、子网、add-on 或 OIDC 提供程序，只会检查它们是否存在；唯一的安全组来自可选的 `page-up`，供内部 ALB 使用。[动手实验](../labs/security/17-eks-workload-identity-migration-lab.md)会通过命令、预期输出和检查点逐步讲解每个步骤。

### 首尔区域的测量结果

我们于2026年11月21日在 `ap-northeast-2` 的 EKS 1.36 集群上进行了两次演练，Pod 内运行 AWS CLI 2.35.11。第一次演练中 Pod Identity 注入失败（见下文），因此我们修正了脚本；表格显示的是使用修正后的脚本端到端完成的第二次演练。只有 `harden` 的结果来自第一次演练。

| 步骤 | orders-legacy | orders-irsa | orders-podid | 耗时 |
| --- | --- | --- | --- | --- |
| 开始 | IMDS · 节点角色 · 允许读取 | IMDS · 节点角色 · 允许读取 | IMDS · 节点角色 · 允许读取 | — |
| `migrate-irsa` | 不变 | STS · IRSA 角色 · 允许读取 | 不变 | 6 秒 |
| `migrate-podid` | 不变 | 不变 | Agent · Pod Identity 角色 · 允许读取 | 11 秒（包括创建关联后等待注入可见的 5 秒） |
| `revoke` | 节点角色 · **拒绝读取** | 允许读取 | 允许读取 | 13 秒后拒绝 |
| `harden`（可选，第一次演练） | **无凭证**（IMDS 响应被阻止） | 允许读取 | 允许读取 | 节点滚动更新 878 秒 |

`diff` 会显示两者的差异。两个令牌都是由同一集群颁发者签名的 ServiceAccount 令牌，但受众和接收方不同。

| 对比项 | IRSA Pod | Pod Identity Pod |
| --- | --- | --- |
| 注入的变量 | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` |
| 令牌 `aud` | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| 令牌 `sub` | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| 令牌有效期 | 86,400 秒（24 小时） | 约 22–24 小时（Webhook 会加入抖动；测得 79,636 秒和 86,171 秒） |
| 角色信任主体 | `Federated`：集群 OIDC 提供程序，条件为 `aud` 和 `sub` | `Service`：`pods.eks.amazonaws.com`，以及三个请求标签条件 |

演练暴露了两种最终一致性现象。第一，在第一次演练中，关联创建后立即滚动更新的 Pod 没有 Pod Identity 变量，仍在使用节点角色，因此移除节点策略后也被拒绝访问。于是，`migrate-podid` 会通过 `kubectl create --dry-run=server` 提交 Deployment 的 Pod 模板，以查看变更 Webhook 注入的内容，并且只有在注入检查通过后才执行滚动更新。在第二次演练中，关联创建 5 秒后注入才变得可见。第二，在第一次演练中，`revoke` 执行后，旧版 Pod 在 13 秒内被拒绝访问，但约 4.5 分钟后又出现了两次允许的读取；紧接着检查的那一分钟内，11 次读取全部被拒绝。在生产环境中，移除节点策略后应继续观察几分钟，再得出结论。

## 故障排查

- **出现了节点角色。** 检查 Pod 是否为新建、引用了正确的 ServiceAccount，以及是否具有 IRSA 注解或精确匹配的关联。检查 SDK 版本、默认凭证提供程序链和注入的变量名称。
- **IRSA 令牌交换失败。** 检查 IAM 提供程序中的令牌颁发者、`aud`/`sub` 信任条件，以及 STS 的网络可达性。
- **Pod Identity 凭证查找失败。** 检查该节点上的 Agent、EKS Auth 连通性、节点 IAM 权限、关联传播情况，以及角色的请求标签信任条件。关联创建后可能需要几秒钟才能生效。
- **预期角色被 S3 拒绝访问。** 身份权限和资源访问权限是分开的。检查对象 ARN、存储桶策略、SCP（服务控制策略）、权限边界和 VPC 端点策略。对于使用 AWS KMS（Key Management Service）密钥加密的对象（SSE-KMS），还要检查该密钥的权限。
