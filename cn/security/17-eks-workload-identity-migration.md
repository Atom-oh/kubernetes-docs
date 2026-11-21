# 将 EKS 节点 IAM 权限迁移到 IRSA 和 Pod Identity

> **最后更新**：2026年11月21日

如果应用程序的 S3 权限附加在 EC2 节点的实例配置文件（即节点 IAM 角色）上，那么该节点上所有能够访问实例元数据服务（IMDS）的 Pod 都会获得相同的权限。为一个 payments Pod 添加授权，也会同时向该节点上的日志转发器和批处理 Job 开放权限。CloudTrail 会将它们全部记录为同一个节点实例会话，因此你无法判断是哪个工作负载发起了调用。

本手册比较了将权限迁移到每个工作负载独立身份的两种方式：IRSA（ServiceAccount 的 IAM 角色）和 EKS Pod Identity。随后介绍生产集群的迁移顺序，并展示一个实时演示，演示如何并排迁移同一应用的三个副本。

## 凭证的来源

![三个 Pod 通过三种路径获取凭证。使用节点角色的 Pod 从 IMDSv2 获取凭证，IRSA Pod 通过 STS AssumeRoleWithWebIdentity 获取凭证，Pod Identity Pod 则通过其所在节点上的 Pod Identity Agent 和 EKS Auth 获取凭证。每个 Pod 都使用收到的凭证为 S3 请求签名。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-0.svg)

Pod 内的 AWS SDK 和 AWS CLI 会从头开始按顺序遍历[默认凭证提供程序链](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)。环境变量中的静态密钥、Web 身份令牌（IRSA）和容器凭证提供程序（Pod Identity）都排在 IMDS 之前。因此，EKS 注入了 IRSA 或 Pod Identity 变量的新 Pod 无需更改代码，就会使用新的角色。没有任何注入内容的 Pod 会继续执行到最后一步 IMDS，并获取节点角色。

| 路径 | 注入 Pod 的内容 | SDK 调用 | 最终使用的角色 |
| --- | --- | --- | --- |
| 节点实例配置文件 | 无 | IMDSv2 `169.254.169.254` | 节点 IAM 角色（该节点上的所有 Pod 共享） |
| IRSA | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、令牌卷 | 区域 STS（安全令牌服务）`AssumeRoleWithWebIdentity` | ServiceAccount 注解中指定的角色 |
| EKS Pod Identity | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、令牌卷 | 同一节点上的 Pod Identity Agent，`169.254.170.23` | 关联中指定的角色 |

当 IMDS 响应跳数限制为 2 或更高时，未使用主机网络的普通 Pod 可以获取 IMDSv2 令牌和节点角色的凭证。托管节点组启动模板通常会将此值设为 2。这就是为什么迁移的最后一步要将跳数限制降至 1。

<a id="irsa-flow"></a>
## IRSA 的工作方式

![IRSA 流程。Webhook 检测到 ServiceAccount 注解后，会注入环境变量和一个投射令牌（aud sts.amazonaws.com）。SDK 将令牌发送到 STS AssumeRoleWithWebIdentity；STS 通过 IAM OIDC 提供程序验证签名，检查信任策略中的 aud 和 sub，然后返回临时凭证。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-1.svg)

1. **信任设置。** 每个集群都有一个 OIDC（OpenID Connect）颁发者 URL。在账户中将该颁发者注册为 IAM OIDC 提供程序，每个集群只需注册一次。角色的信任策略将该提供程序设为 `Federated` 主体，并针对 `aud`（`sts.amazonaws.com`）和 `sub`（`system:serviceaccount:<namespace>:<serviceaccount>`）设置条件。
2. **创建 Pod 时注入。** 当 ServiceAccount 带有 `eks.amazonaws.com/role-arn` 时，EKS 变更 Webhook 会向每个新 Pod 添加 `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`，以及挂载在 `/var/run/secrets/eks.amazonaws.com/serviceaccount/token` 的投射令牌卷。运行中的 Pod 不会发生变化，因此需要滚动更新。
3. **签发和刷新令牌。** kubelet 会请求面向 `sts.amazonaws.com` 受众的 ServiceAccount 令牌，将其写入文件，并在令牌过期前刷新。
4. **令牌交换。** SDK 将令牌发送到区域 STS 的 `AssumeRoleWithWebIdentity`。STS 使用通过 IAM OIDC 提供程序注册的颁发者密钥验证签名，检查 `aud` 和 `sub` 条件，然后返回临时凭证。Pod 会直接与 STS 通信，因此需要能够连接到 STS 的网络路径。[AWS IRSA 文档](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

<a id="pod-identity-flow"></a>
## EKS Pod Identity 的工作方式

![Pod Identity 流程。EKS API 中的关联将 ServiceAccount 映射到一个角色，EKS 会注入容器凭证变量和一个投射令牌（aud pods.eks.amazonaws.com）。SDK 调用 Pod 所在节点上的 Pod Identity Agent；Agent 使用节点角色的 eks-auth 权限调用 EKS Auth AssumeRoleForPodIdentity，EKS 随后返回带有会话标签的角色凭证。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-2.svg)

1. **Agent 设置。** 每个集群安装一次 `eks-pod-identity-agent` 插件。Agent 是运行在节点主机网络上的 DaemonSet，使用链路本地地址 `169.254.170.23`（IPv6 `[fd00:ec2::23]`）上的 80 和 2703 端口。EKS Auto Mode 已内置该 Agent。
2. **角色和关联。** 角色信任服务主体 `pods.eks.amazonaws.com`，以执行 `sts:AssumeRole` 和 `sts:TagSession`。无需为每个集群单独配置提供程序，因此同一角色可在其他集群中使用，无需更改信任策略。绑定是在 EKS API 中创建的关联（集群、命名空间、ServiceAccount → 角色）；无需注解任何 Kubernetes 对象。
3. **创建 Pod 时注入。** 对于已建立关联的 ServiceAccount，EKS 会向新 Pod 注入 `AWS_CONTAINER_CREDENTIALS_FULL_URI=http://169.254.170.23/v1/credentials`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`，以及面向 `pods.eks.amazonaws.com` 受众的投射令牌。
4. **凭证查询。** SDK 将令牌发送给 Pod 所在节点上的 Agent。Agent 使用节点角色的 `eks-auth:AssumeRoleForPodIdentity` 权限（该权限属于 `AmazonEKSWorkerNodePolicy`）调用 EKS Auth。EKS Auth 验证令牌和关联，代入角色并返回带有 `eks-cluster-arn`、`kubernetes-namespace` 和 `kubernetes-service-account` 等会话标签的凭证。节点角色仅保留 Agent 调用 EKS Auth 所需的权限；应用的业务权限则配置在 Pod Identity 角色上。[Pod Identity 的工作方式](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)

## IRSA 与 Pod Identity 对比

AWS 建议尽可能使用 EKS Pod Identity。某些运行时环境和团队组织方式仍适合使用 IRSA。[AWS 对比文档](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)

| 属性 | IRSA | EKS Pod Identity |
| --- | --- | --- |
| 每个集群的设置 | 为每个集群注册一个 IAM OIDC 提供程序 | 为每个集群安装 Pod Identity Agent 插件（Auto Mode 已内置） |
| 绑定所在位置 | Kubernetes ServiceAccount 注解 | EKS API 关联（无需更改 Kubernetes 对象） |
| 信任策略 | 使用带 `aud`/`sub` 条件的 `Federated` OIDC 提供程序；每个集群需增加一条语句 | 单个主体 `pods.eks.amazonaws.com`；新增集群时无需更改 |
| 扩展限制 | 每个账户默认最多 100 个 OIDC 提供程序；默认 2,048 个字符的信任策略通常可容纳每个角色约四个绑定 | 每个集群 5,000 个关联；角色信任策略不会增长 |
| 凭证路径 | Pod → 区域 STS（Pod 会占用 STS API 配额） | Pod → 节点 Agent → EKS Auth（Pod 不会调用 STS） |
| 会话信息 | 角色会话名称；无会话标签 | 集群、命名空间和 ServiceAccount 会话标签支持 ABAC（基于属性的访问控制） |
| 运行时环境 | EKS on EC2 和 Fargate、EKS Anywhere、ROSA、EC2 上的自管理 Kubernetes | 仅限 EKS 中的 Linux EC2 节点；不支持 Fargate、Windows、Outposts 或 EKS Anywhere |
| 跨账户 | 目标账户角色信任此集群的 OIDC 提供程序 | 关联角色位于集群所在账户；通过委派目标角色或角色链实现跨账户访问 |
| 职责分离 | IAM 管理员创建 OIDC 提供程序；集群运维人员添加注解 | IAM 仅管理角色；绑定位于 EKS API 中 |

简而言之，对于 EC2 上的新 EKS 工作负载，Pod Identity 更简单，也更易扩展。对于 Fargate 或 Windows 节点，或者同一设置还必须运行在 EKS 之外的 Kubernetes 上的情况，请使用 IRSA。两者可以在同一集群中运行。如果一个 ServiceAccount 同时具有 IRSA 注解和关联，EKS Webhook 只会向新 Pod 注入 Pod Identity 变量，而不会注入 IRSA 变量。在演示集群中，`kubectl create --dry-run=server` 检查发现，只有注解时会返回 `AWS_ROLE_ARN` 和 `AWS_WEB_IDENTITY_TOKEN_FILE`，添加关联后则只返回 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`。运行中的 Pod 会一直保留 IRSA 变量，直到重新创建，因此切换时应执行滚动更新并移除未使用的注解。

在私有集群中，确保 IRSA Pod 能连接到区域 STS，Pod Identity Agent 能连接到 EKS Auth（`eks-auth`）。如果没有互联网连接，请检查相应的 VPC 接口端点、DNS 和安全组。如果使用代理，请将 `169.254.170.23` 和 `[fd00:ec2::23]` 加入 `NO_PROXY`。[Pod Identity 注意事项](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html) · [私有集群要求](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)

## 生产集群的迁移顺序

1. **盘点依赖项。** 将节点角色策略与 CloudTrail 实际记录的 IAM 会话进行比较，并列出 Deployments、StatefulSets、DaemonSets、CronJobs 和控制器调用的 AWS API。若要在 CloudTrail 中查看 S3 对象访问，需要为相应存储桶启用数据事件。保留用于节点注册和 Pod Identity Agent 的 `AmazonEKSWorkerNodePolicy`，以及用于拉取 Amazon ECR（弹性容器注册表）镜像的 `AmazonEC2ContainerRegistryPullOnly`（或等效策略）。VPC CNI（容器网络接口）的 `AmazonEKS_CNI_Policy` 可以迁移到专用的 `aws-node` 角色；从节点角色中移除该策略前，请先验证 CNI 凭证和新 Pod 的 IP 分配。[EKS 节点 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html) · [S3 CloudTrail 事件](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging-s3-info.html)
2. **为每个工作负载创建范围明确的 IAM 角色和专用 ServiceAccount。** 使用 IRSA 时，将集群颁发者注册为 IAM OIDC 提供程序，创建一个检查确切受众和主体的角色，并使用 `eks.amazonaws.com/role-arn` 注解 ServiceAccount。使用 Pod Identity 时，先检查 Agent 是否就绪以及节点是否具有 EKS Auth 权限，再创建一个由请求标签限定范围的角色关联。确认计算平台和 SDK 均受支持。[IRSA SDK 版本](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts-minimum-sdk.html) · [Pod Identity SDK 版本](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-minimum-sdk.html)
3. **创建金丝雀 Pod。** 更改 Pod 模板中的 `serviceAccountName`，或滚动部署新 Pod，然后检查注入的变量名称、运行进程的调用方 ARN 以及其所需的 AWS API。切勿记录令牌或密钥。显式凭证或默认凭证链中优先级更高的提供程序可能会优先生效。[默认凭证提供程序链](https://docs.aws.amazon.com/sdkref/latest/guide/standardized-credentials.html)
4. **逐个切换工作负载。** 监控错误率、`AccessDenied`、令牌和凭证刷新情况，以及定时任务的运行情况。某个工作负载不再依赖节点角色的业务权限后，只移除相应的策略语句。在回滚窗口内保留之前的 Pod 模板和节点策略的精确副本。如果移除权限后需要回滚，应先恢复该最小策略，确认更改已传播，然后再部署之前的 Pod。
5. **限制节点凭证访问。** 从已测试兼容性的节点组开始，强制启用 IMDSv2 并限制普通 Pod 对 IMDS 的访问。对于使用自定义启动模板的托管节点组，请在新模板版本中设置 `HttpTokens=required` 和 `HttpPutResponseHopLimit=1`，然后滚动更新节点。Karpenter 使用 `EC2NodeClass.spec.metadataOptions`；EKS Auto Mode 默认强制启用 IMDSv2，并将跳数限制设为 1。无论跳数限制如何设置，使用 `hostNetwork` 的 Pod 都能访问 IMDS，因此应单独管理这类 Pod。不要关闭 IMDS（`HttpEndpoint=disabled`）：Pod Identity Agent 本身运行在主机网络上，需要从 IMDS 获取节点角色凭证才能调用 EKS Auth。[托管节点组启动模板](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html) · [EKS IAM 最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)

<details>
<summary>信任策略和金丝雀命令</summary>

IRSA 角色的信任策略会限定集群颁发者和 ServiceAccount。`<OIDC_ISSUER>` 中应使用不带 `https://` 的颁发者地址。

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

Pod Identity 角色信任 EKS 服务主体。以下条件通过会话标签限定集群、命名空间和 ServiceAccount，因此应在关联中启用会话标签。

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

![演示流程。开始时，orders 应用的三个副本都从 IMDS 获取节点角色并读取 S3。执行 migrate-irsa 后，其中一个副本从 STS 获取 IRSA 角色；执行 migrate-podid 后，另一个副本通过 Agent 获取 Pod Identity 角色。执行 revoke 移除节点角色的 S3 权限后，只有旧版副本会被拒绝。](../.gitbook/assets/en-security-17-eks-workload-identity-migration-anim-3.svg)

此演示会在现有 EKS 1.36 集群中添加一个专用的托管节点组（t3.medium、私有子网、带污点），并在其中运行同一 orders 应用的三个副本。每个副本每 3 秒调用一次 STS `GetCallerIdentity` 和 S3 `GetObject`，并输出一行 JSON，其中包含凭证来源、角色名称和 S3 结果。初始配置与集群的生产节点组一致：要求使用 IMDSv2，跳数限制为 2，且节点角色具有应用的 `s3:GetObject` 权限。旧版 Pod 是未使用主机网络的普通 Pod。[演示代码和演示者操作手册](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity) · [幻灯片（韩语）](https://presentation.atomai.click/eks-workload-identity/)

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

使用 `page-up` 可以与观众分享只读实时页面。访问路径为 CloudFront → VPC 源站 → 内部 ALB → dashboard Pod；ALB 安全组只允许来自 CloudFront VPC 源站的访问。dashboard Pod 没有 IAM 角色，只有一个可读取此命名空间中 Pod 和日志的 Role；由于演示节点使用跳数限制 2，NetworkPolicy 会阻止它访问 IMDS 或 Pod Identity Agent。此隔离要求启用 VPC CNI 网络策略强制执行（`enableNetworkPolicy`），`page-up` 会先检查该设置。

脚本创建的所有资源名称中都包含运行 ID，或带有 `LabRun` 标签；脚本只会更改或删除名称或标签匹配的资源。脚本不会创建 VPC、子网、插件或 OIDC 提供程序，只会检查它们是否存在；唯一的安全组由可选的 `page-up` 创建，用于内部 ALB。[动手实验](../labs/security/17-eks-workload-identity-migration-lab.md)通过命令、预期输出和检查点带你逐步完成每个步骤。

### 首尔区域的实测结果

我们于2026年11月21日在 `ap-northeast-2` 的 EKS 1.36 集群上进行了两次演练，Pod 内使用 AWS CLI 2.35.11。第一次演练中 Pod Identity 注入失败（见下文），因此我们修复了脚本；表格展示的是使用修复后脚本端到端运行的第二次演练。只有 `harden` 的结果来自第一次演练。

| 步骤 | orders-legacy | orders-irsa | orders-podid | 用时 |
| --- | --- | --- | --- | --- |
| 开始 | IMDS · 节点角色 · 允许读取 | IMDS · 节点角色 · 允许读取 | IMDS · 节点角色 · 允许读取 | — |
| `migrate-irsa` | 未变 | STS · IRSA 角色 · 允许读取 | 未变 | 6 秒 |
| `migrate-podid` | 未变 | 未变 | Agent · Pod Identity 角色 · 允许读取 | 11 秒（包括创建关联后等待 5 秒，直到注入内容可见） |
| `revoke` | 节点角色 · **读取被拒绝** | 允许读取 | 允许读取 | 13 秒后被拒绝 |
| `harden`（可选，第一次演练） | **无凭证**（IMDS 响应被阻止） | 允许读取 | 允许读取 | 节点滚动更新 878 秒 |

`diff` 会展示两者的差异。两个令牌都是由同一集群颁发者签名的 ServiceAccount 令牌，但受众和接收方不同。

| 对比项 | IRSA Pod | Pod Identity Pod |
| --- | --- | --- |
| 注入的变量 | `AWS_ROLE_ARN`、`AWS_WEB_IDENTITY_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` | `AWS_CONTAINER_CREDENTIALS_FULL_URI`、`AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`、`AWS_STS_REGIONAL_ENDPOINTS` |
| 令牌 `aud` | `sts.amazonaws.com` | `pods.eks.amazonaws.com` |
| 令牌 `sub` | `system:serviceaccount:wid-d1124:orders-irsa` | `system:serviceaccount:wid-d1124:orders-podid` |
| 令牌有效期 | 86,400 秒（24 小时） | 约 22–24 小时（Webhook 会加入随机抖动；实测为 79,636 秒和 86,171 秒） |
| 角色信任主体 | `Federated`：集群 OIDC 提供程序，条件为 `aud` 和 `sub` | `Service`：`pods.eks.amazonaws.com`，以及三个请求标签条件 |

演练发现了两种最终一致性现象。第一，第一次演练中，在创建关联后立即滚动更新的 Pod 没有 Pod Identity 变量，仍在使用节点角色，因此移除节点策略后也被拒绝。为此，`migrate-podid` 会将 Deployment 的 Pod 模板通过 `kubectl create --dry-run=server` 提交，以检查变更 Webhook 会注入哪些内容，然后才执行滚动更新。第二次演练中，创建关联 5 秒后才看到注入内容。第二，第一次演练中，执行 `revoke` 后，旧版 Pod 在 13 秒内被拒绝，但约 4.5 分钟后又出现了两次获准的读取。随后立即检查的一分钟内，11 次读取全部被拒绝。在生产环境中，移除节点策略后应继续观察几分钟，再得出结论。

## 故障排查

- **出现了节点角色。** 检查 Pod 是否为新建、引用了正确的 ServiceAccount，并且具有 IRSA 注解或完全匹配的关联。检查 SDK 版本、默认提供程序链以及注入的变量名称。
- **IRSA 令牌交换失败。** 检查 IAM 提供程序是否对应令牌颁发者、`aud`/`sub` 信任条件是否正确，以及 STS 是否可达。
- **Pod Identity 凭证查询失败。** 检查该节点上的 Agent、EKS Auth 连接、节点 IAM 权限、关联传播情况，以及角色的请求标签信任条件。关联创建后可能需要几秒才会生效。
- **预期角色访问 S3 时被拒绝。** 身份授权与资源访问授权是两个独立环节。检查对象 ARN、存储桶策略、SCP（服务控制策略）、权限边界和 VPC 端点策略。对于使用 AWS KMS（密钥管理服务）密钥加密（SSE-KMS）的对象，还要检查对该密钥的权限。
