# EKS 工作负载 IAM 迁移实验：从节点角色迁移到 IRSA 和 Pod Identity

> **难度**：高级
> **预计时间**：40–60 分钟（使用 `harden` 时约多 30 分钟）
> **支持的版本**：已在 Amazon EKS 1.36、AWS CLI 2.35.11（在 Pod 内）上验证
> **上次更新**：2026 年 11 月 21 日

## 学习目标

- 从三个使用相同订单应用副本的初始状态开始，这些副本都使用节点 IAM 角色，然后将一个副本迁移到 IRSA，另一个迁移到 EKS Pod Identity。
- 亲自观察这两种方法注入的环境变量、令牌和角色信任策略有何不同。
- 撤销节点角色的 S3 权限，观察只有未迁移的 Pod 被拒绝访问，并了解 IAM 和关联的最终一致性。
- （可选）将 IMDS 跳数限制降低到 1，以关闭普通 Pod 获取节点凭证的途径。
- 使用服务器端试运行，检查当一个 ServiceAccount 同时具有 IRSA 注解和 Pod Identity 关联时，新 Pod 会获得什么。

本实验将逐步带你完成 [将 EKS 节点 IAM 权限迁移到 IRSA 和 Pod Identity](../../security/17-eks-workload-identity-migration.md) 中的[实时演示](../../security/17-eks-workload-identity-migration.md#live-demo)。请先阅读工作手册中的 [IRSA 流程](../../security/17-eks-workload-identity-migration.md#irsa-flow)和 [Pod Identity 流程](../../security/17-eks-workload-identity-migration.md#pod-identity-flow)部分。

## 时间和费用

| 步骤 | 实测时间 | 备注 |
| --- | --- | --- |
| `up` | 174 秒（运行 `t1121`） | 主要耗时在创建节点组；具体为 3–5 分钟，取决于环境 |
| `migrate-irsa` | 6 秒 | |
| `migrate-podid` | 11 秒 | 包括等待关联进入准入流程的 5 秒 |
| `diff` | 8 秒 | 只读 |
| `revoke` | 首次出现 `denied` 需 13 秒 | 命令在 17–18 秒后返回 |
| `harden`（可选） | 878 秒 | 滚动替换节点组 |
| `restore` | 15 秒；在 `harden` 后为 578 秒 | 用于重复练习 |
| `down` | 323 秒（运行 `t1121`） | 主要耗时在删除节点组 |

费用主要来自一台 t3.medium 按需实例（首尔区域每小时 0.052 美元）和一个 20 GiB gp3 卷。实验一小时的费用约为 0.06 美元；S3 请求和 API 调用的费用可以忽略不计。可选的公共演示页面每天会增加约 0.55 美元的 ALB 费用。完成后务必运行 `down` 清理资源。

## 先决条件

- [ ] **现有 EKS 集群**（已在 1.36 上验证）。核心演示不会创建集群、VPC、子网或安全组（只有可选的 `page-up` 会为内部 ALB 创建一个安全组，并为 `PAGE_DOMAIN` 创建 DNS 记录）。演示假设集群采用常见配置，即 vpc-cni 在节点角色上运行。
- [ ] 已安装 **`eks-pod-identity-agent` 插件**。脚本只会检查它，不会安装它。
- [ ] 集群颁发者已注册为 **IAM OIDC 提供商**。脚本也不会创建它。
- [ ] 集群 VPC 中的 **私有子网**及其 Name 标签。只接受 `MapPublicIpOnLaunch=false` 的子网；节点通过 VPC 现有的 NAT 路径拉取 `public.ecr.aws/aws-cli/aws-cli`。
- [ ] 工具：AWS CLI v2、kubectl、jq、bash、git。
- [ ] 权限：具有 EKS、EC2（启动模板）、IAM 和 S3 权限的凭证，以及对集群的 cluster-admin 访问权限。请使用临时凭证，而不要使用长期访问密钥。

### 预检命令

```bash
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER> VPC_NAME=<Name tag of the cluster VPC> \
  SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>

aws sts get-caller-identity --query Arn --output text
aws eks describe-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent \
  --query addon.status --output text                       # ACTIVE
ISSUER=$(aws eks describe-cluster --name "$CLUSTER" \
  --query cluster.identity.oidc.issuer --output text | sed 's#^https://##')
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam get-open-id-connect-provider --open-id-connect-provider-arn \
  "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${ISSUER}" --query ClientIDList   # ["sts.amazonaws.com"]
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text)
aws eks describe-cluster --name "$CLUSTER" --query cluster.resourcesVpcConfig.vpcId --output text  # must equal $VPC_ID
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=$SUBNET_NAMES" \
  --query 'Subnets[].[Tags[?Key==`Name`]|[0].Value,SubnetId,MapPublicIpOnLaunch]' --output table
```

确认插件状态为 `ACTIVE`，OIDC 提供商查询成功，集群 VPC ID 与通过 `VPC_NAME` 查到的 VPC 相符，并且每个子网的 `MapPublicIpOnLaunch` 都显示为 `False`。如果其中任何一项未通过，`up` 会在创建任何资源之前停止。

### 代码和环境文件

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs/examples/security/eks-workload-identity

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/eks-workload-identity-demo"
mkdir -p "$STATE_DIR"
cat > "$STATE_DIR/env" <<'EOF'
export AWS_REGION=ap-northeast-2
export CLUSTER=<CLUSTER>
export VPC_NAME=<Name tag of the cluster VPC>
export SUBNET_NAMES=<private subnet Name tag 1>,<private subnet Name tag 2>
EOF

export RUN_ID=lab01     # 4–12 lowercase letters or digits; goes into resource names wid-<RUN_ID>-*
export NS="wid-$RUN_ID"
export KUBECONFIG="$STATE_DIR/kubeconfig-$RUN_ID"   # the dedicated kubeconfig demo.sh writes
```

`demo.sh` 每次运行时都会加载此环境文件，因此第二个终端中的 `watch` 使用相同的值。该文件会在 shell 变量之后加载，因此如果文件中的值与同名 shell 变量冲突，则以文件中的值为准。接下来直接运行 `kubectl` 时，请使用上面的 `KUBECONFIG`，确保这些命令不会访问其他集群上下文。此文件会在首次运行 `up` 时创建。

脚本打印的命令和结果会将账户 ID、OIDC 颁发者 ID、集群名称和启动模板 ID 分别遮蔽为 `<ACCOUNT_ID>`、`<OIDC_ID>`、`<CLUSTER>` 和 `<LAUNCH_TEMPLATE_ID>`。下面的预期输出也以相同方式遮蔽。这些输出来自 2026 年 11 月 21 日在首尔区域进行的演练，每个区块都会注明运行 ID（`d1124` 或 `t1121`）。屏幕上会显示你自己的 `RUN_ID` 和时间戳。

## 步骤 0：部署实验环境（`up`）

**命令**（终端 A）

```bash
./demo.sh up "$RUN_ID"
```

**预期输出**（实测，运行 `t1121`，174 秒）

```text
==> bucket and test object
==> node role (with the app's S3 permission, the legacy pattern)
==> IRSA and Pod Identity roles
==> creating node group wid-t1121 (3–5 min)
==> namespace, ServiceAccounts and three copies of the orders app
Waiting for deployment "orders-legacy" rollout to finish: 0 of 1 updated replicas are available...
deployment "orders-legacy" successfully rolled out
deployment "orders-irsa" successfully rolled out
deployment "orders-podid" successfully rolled out
==> ready. In a second terminal run: ./demo.sh watch t1121
```

**检查内容**

```bash
./demo.sh status "$RUN_ID"
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `status` 应显示节点组为 `ACTIVE t3.medium lt-version=1`，三个角色（`wid-<RUN_ID>-node`、`-irsa`、`-podid`）上都有内联策略 `OrdersReadInvoices`，存储桶状态为 `present`，`pod-id 0 association(s)`，`irsa SA (not annotated)`，并且三个 Pod 均为 `Running`。
- 启动模板的 `MetadataOptions` 为 `HttpTokens: required`、`HttpPutResponseHopLimit: 2` 和 `HttpEndpoint: enabled`。

**原因。** `up` 会创建一个与生产环境节点组起始状态相同的环境。必须使用 IMDSv2，但跳数限制为 2 时，未使用主机网络的普通 Pod 仍可获取 IMDS 令牌和节点角色凭证，而该节点角色拥有应用所需的 `s3:GetObject` 权限。IRSA 和 Pod Identity 角色会提前创建，但此时尚未关联到任何 ServiceAccount。

## 步骤 1：检查初始状态（`watch`）

**命令**（终端 B，使用相同目录）

```bash
export RUN_ID=lab01
./demo.sh watch "$RUN_ID"     # refreshes every 2 s; Ctrl-C to stop
```

**预期画面**（实测，运行 `d1124`）

```text
04:11:37 EKS workload identity — <CLUSTER>/wid-d1124  (Ctrl-C to stop)

COPY            CREDENTIALS    ROLE                           S3        AT
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36
orders-irsa     node (IMDS)    wid-d1124-node  ← node       allowed   04:11:35
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:11:36

node role: wid-d1124-node   bucket object: invoices/2026-11.txt
```

**检查内容。** 三行都显示 `node (IMDS)`、`wid-<RUN_ID>-node ← node` 和 `allowed`，并且 `AT` 时间每 3 秒更新一次。此画面取自每个副本的最新 Pod 中最新的一行日志。你可以在终端 A 中查看原始 JSON：

```bash
kubectl -n "$NS" logs deploy/orders-legacy --tail=3
# format: {"t":"HH:MM:SS","src":"imds","role":"wid-<RUN_ID>-node","s3":"allowed"}
```

**原因。** 三个 Pod 都没有注入凭证变量，因此 AWS CLI 的默认凭证提供程序链会一路查找，直到最后一步 IMDS，并获取节点角色。`app.sh` 根据是否存在 `AWS_WEB_IDENTITY_TOKEN_FILE` 或 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 设置 `src`，并从 `sts get-caller-identity` ARN 中读取角色名称。它不会输出令牌或密钥。

## 步骤 2：迁移到 IRSA（`migrate-irsa`）

**命令**（终端 A）

```bash
./demo.sh migrate-irsa "$RUN_ID"
```

**预期输出**（实测，运行 `t1121`，6 秒）

```text
==> IRSA: point the ServiceAccount at its own role, then restart the copy
$ kubectl -n wid-t1121 annotate serviceaccount orders-irsa --overwrite eks.amazonaws.com/role-arn=arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-irsa
$ kubectl -n wid-t1121 rollout restart deployment/orders-irsa
$ kubectl -n wid-t1121 rollout status deployment/orders-irsa --timeout=180s
Waiting for deployment "orders-irsa" rollout to finish: 1 old replicas are pending termination...
deployment "orders-irsa" successfully rolled out
```

在终端 B 中，`orders-irsa` 行会变为 `IRSA (STS)`、`wid-<RUN_ID>-irsa`、`allowed`；另外两行保持不变（实测，运行 `d1124`）。

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:11:59
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:01
orders-podid    node (IMDS)    wid-d1124-node  ← node       allowed   04:12:00
```

**亲自检查。** 查看 Kubernetes 对象发生了哪些变化。

```bash
# 1) The ServiceAccount annotation
kubectl -n "$NS" get sa orders-irsa \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}'

# 2) Names of the environment variables the webhook added to the new Pod (no values)
POD=$(kubectl -n "$NS" get pod -l app=orders,track=irsa \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'

# 3) The projected token mount path
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].volumeMounts[*]}{.mountPath}{"\n"}{end}'
```

**检查内容**

- 注解为 `arn:aws:iam::<ACCOUNT_ID>:role/wid-<RUN_ID>-irsa`。
- 除清单中原有的 `BUCKET`、`KEY`、`AWS_REGION` 等变量外，变量列表还会显示 Webhook 添加的 `AWS_STS_REGIONAL_ENDPOINTS`、`AWS_ROLE_ARN` 和 `AWS_WEB_IDENTITY_TOKEN_FILE`。
- 挂载路径现在包括 `/var/run/secrets/eks.amazonaws.com/serviceaccount`。
- `orders-legacy` 和 `orders-podid` Pod 没有这些变量。

**原因。** EKS 变更 Webhook 会在 **创建 Pod 时**读取 ServiceAccount 的 `eks.amazonaws.com/role-arn` 注解，并添加变量和令牌卷。正在运行的 Pod 不会随之改变，因此脚本在添加注解后会立即运行 `rollout restart`。在新 Pod 中，AWS CLI 会找到 Web Identity 令牌提供程序。该提供程序在凭证链中的位置早于 IMDS，因此它会通过 STS `AssumeRoleWithWebIdentity` 获取 IRSA 角色。

## 步骤 3：迁移到 Pod Identity（`migrate-podid`）

**命令**（终端 A）

```bash
./demo.sh migrate-podid "$RUN_ID"
```

**预期输出**（实测，运行 `t1121`，11 秒）

```text
==> Pod Identity: associate the ServiceAccount with its role in the EKS API, then restart
$ aws eks create-pod-identity-association --cluster-name <CLUSTER> --namespace wid-t1121 --service-account orders-podid --role-arn arn:aws:iam::<ACCOUNT_ID>:role/wid-t1121-podid --tags Lab=eks-workload-identity-demo\,LabRun=t1121 --query association.associationId --output text
==> waiting for the association change to reach Pod admission (eventually consistent)
    2s  not yet   injected after 5s
$ kubectl -n wid-t1121 rollout restart deployment/orders-podid
$ kubectl -n wid-t1121 rollout status deployment/orders-podid --timeout=180s
Waiting for deployment "orders-podid" rollout to finish: 1 old replicas are pending termination...
deployment "orders-podid" successfully rolled out
```

在终端 B 中，`orders-podid` 行会变为 `Pod Identity`、`wid-<RUN_ID>-podid`、`allowed`（实测，运行 `d1124`）。

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       allowed   04:12:27
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:29
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:27
```

**亲自检查**

```bash
# The association lives in the EKS API; the ServiceAccount has no annotation
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "$NS" \
  --query 'associations[].[serviceAccount,associationId]' --output text
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'

POD=$(kubectl -n "$NS" get pod -l app=orders,track=podid \
  --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1:].metadata.name}')
kubectl -n "$NS" get pod "$POD" \
  -o jsonpath='{range .spec.containers[0].env[*]}{.name}{"\n"}{end}'
```

**检查内容**

- 有一个关联，属于 `orders-podid`，且 ServiceAccount 注解为空。
- 新 Pod 具有 `AWS_STS_REGIONAL_ENDPOINTS`、`AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`。
- 输出中的 `injected after Ns` 表示从创建关联到准入流程注入变量所经过的时间。两次演练中都为 5 秒。

**为什么要等待注入。** 关联具有最终一致性。第一次演练中，创建关联后立即进行滚动更新，结果生成的 Pod 没有 Pod Identity 变量，并继续使用节点角色。因此，脚本会通过 `kubectl create --dry-run=server` 将 Deployment 的 Pod 模板提交给 API 服务器，并且只有在变更 Webhook 实际注入变量后才执行滚动更新。服务器端试运行不会保存任何内容，但会经过与真实 Pod 相同的准入步骤，恰好能用于此项检查。

## 步骤 4：比较两种方法（`diff`）

**命令**

```bash
./demo.sh diff "$RUN_ID"
```

**预期输出**（实测，运行 `t1121`）

```text
1. What EKS injected into each new Pod (env var names)
  irsa   AWS_STS_REGIONAL_ENDPOINTS, AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
  podid  AWS_STS_REGIONAL_ENDPOINTS, AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE

2. The projected ServiceAccount token (claims only)
  irsa   {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["sts.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-irsa","lifetime_s":86400}
  podid  {"iss":"https://oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>","aud":["pods.eks.amazonaws.com"],"sub":"system:serviceaccount:wid-t1121:orders-podid","lifetime_s":79636}

3. Who each role trusts
  irsa             {"principal":{"Federated":"arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.ap-northeast-2.amazonaws.com/id/<OIDC_ID>"},"action":"sts:AssumeRoleWithWebIdentity","conditions":["<issuer>:aud","<issuer>:sub"]}
  podid            {"principal":{"Service":"pods.eks.amazonaws.com"},"action":["sts:AssumeRole","sts:TagSession"],"conditions":["aws:RequestTag/eks-cluster-arn","aws:RequestTag/kubernetes-namespace","aws:RequestTag/kubernetes-service-account"]}

4. Where the SDK goes for credentials
  irsa   Pod → STS AssumeRoleWithWebIdentity (regional endpoint) → temporary credentials
  podid  Pod → Pod Identity Agent 169.254.170.23 on the node → EKS Auth AssumeRoleForPodIdentity → credentials
  legacy Pod → IMDSv2 169.254.169.254 → node role credentials

5. Wiring lives in
  irsa   ServiceAccount annotation + IAM OIDC provider + per-role trust on issuer/sub
  podid  EKS association (1 found) + one service principal trust, reusable across clusters
```

**如何解读输出**

- **1**：两种方法都会向新 Pod 添加变量，但变量名称不同。IRSA 会传递角色 ARN 和令牌文件，SDK 会自行调用 STS。Pod Identity 不会传递角色 ARN，只传递凭证 URI 和授权令牌文件；Pod 会获得哪个角色由关联决定。
- **2**：两个令牌都是由同一个集群颁发者签名的 ServiceAccount 令牌，`sub` 格式也相同。区别在于 `aud`：`sts.amazonaws.com` 令牌只能被 STS 接受，`pods.eks.amazonaws.com` 令牌只能被 EKS Auth 接受。Pod Identity 令牌的有效期会因运行而异，因为 Webhook 会添加随机抖动（实测为 79,636 秒和 86,171 秒）。
- **3**：IRSA 角色信任具有 `aud` 和 `sub` 条件的集群专属 OIDC 提供商，因此每增加一个集群，信任策略都需要扩展。Pod Identity 角色信任带有会话标签条件的单个服务主体，因此在其他集群中无需更改信任策略。
- **4–5** 是脚本打印的固定摘要文本。只有第 5 项中的 `1 found` 才是实际关联数。

**原因。** 两种方法的区别在于由谁获取令牌并将其转换为角色。使用 IRSA 时，Pod 会直接访问 STS，由 STS 通过 OIDC 提供商验证签名。使用 Pod Identity 时，同一节点上的 Agent 会请求 EKS Auth；后者查找关联，并返回带有会话标签的凭证。

## 步骤 5：撤销节点角色权限（`revoke`）

**命令**

```bash
./demo.sh revoke "$RUN_ID"
```

**预期输出**（实测，运行 `t1121`，首次出现 `denied` 需 13 秒）

```text
==> remove the app's S3 permission from the node role
$ aws iam delete-role-policy --role-name wid-t1121-node --policy-name OrdersReadInvoices
==> waiting for IAM to propagate: legacy copy should flip to denied
    1s  legacy still: allowed     5s  legacy still: allowed     9s  legacy still: allowed   legacy denied after 13s
  orders-irsa   allowed via wid-t1121-irsa
  orders-podid  allowed via wid-t1121-podid
```

终端 B（实测，运行 `d1124`；在 `revoke` 执行后立即和 60 秒后结果相同）：

```text
orders-legacy   node (IMDS)    wid-d1124-node  ← node       denied    04:12:56
orders-irsa     IRSA (STS)     wid-d1124-irsa                 allowed   04:12:58
orders-podid    Pod Identity   wid-d1124-podid                allowed   04:12:58
```

**检查内容**

- 只有 `orders-legacy` 会变成 `denied`，其角色仍然是节点角色：它仍能获取凭证，但该角色已不再拥有这项权限。
- IRSA 和 Pod Identity 副本仍然是 `allowed`，这证明它们不再依赖节点角色的应用权限。
- 接下来几分钟内，检查日志中是否还有稍后出现的 `allowed` 读取记录。

```bash
kubectl -n "$NS" logs deploy/orders-legacy --since=10m | jq -r 'select(.s3=="allowed") | .t' | tail -n 3
```

**原因。** IAM 策略变更具有最终一致性。两次演练中，首次拒绝都在 13 秒后出现，但第一次演练中约 4.5 分钟后又出现了两次 `allowed` 读取。`revoke` 会在首次出现 `denied` 时返回，因此在生产环境中移除节点策略后，应继续观察几分钟再做判断。

## 步骤 6（可选）：关闭 IMDS 路径（`harden`）

此步骤约需 15 分钟（实测 878 秒），因此你可以在 `revoke` 之后立即启动，然后继续步骤 7。

**命令**

```bash
./demo.sh harden "$RUN_ID"
./demo.sh status "$RUN_ID"      # in another terminal: nodegroup UPDATING → ACTIVE
```

**预期输出**（实测，运行 `d1124`，878 秒）。脚本会将节点组更新为新的启动模板版本，并每隔 15 秒打印一个点，直到完成。

```text
==> block Pod access to IMDS on the demo node group (hop limit 1)
$ aws eks update-nodegroup-version --cluster-name <CLUSTER> --nodegroup-name wid-d1124 --launch-template id=<LAUNCH_TEMPLATE_ID>\,version=2 --query update.id --output text
...
deployment "orders-legacy" successfully rolled out
==> legacy copy now has no credentials at all; IRSA and Pod Identity are unaffected
```

节点替换后的每个副本的最后一行日志（实测，运行 `d1124`）：

```text
legacy: {"t":"04:00:27","src":"imds","role":"no-credentials","s3":"no-creds"}
irsa: {"t":"04:00:26","src":"irsa","role":"wid-d1124-irsa","s3":"allowed"}
podid: {"t":"04:00:27","src":"pod-identity","role":"wid-d1124-podid","s3":"allowed"}
```

**检查内容**

```bash
aws ec2 describe-launch-template-versions --launch-template-name "wid-$RUN_ID-node" --versions '$Latest' \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'
```

- `HttpPutResponseHopLimit` 为 `1`，`HttpEndpoint` 仍为 `enabled`。
- `orders-legacy` 完全无法获取凭证（`no-credentials` / `no-creds`）；另外两个副本在新节点上仍保持 `allowed`。

**原因。** 跳数限制为 1 时，IMDSv2 令牌响应无法从节点的网络命名空间穿过到 Pod，因此普通 Pod 无法获取节点角色的凭证。**不要关闭 IMDS（`HttpEndpoint=disabled`）。** Pod Identity Agent 在主机网络上运行，会从 IMDS 获取节点角色的凭证以调用 EKS Auth；关闭 IMDS 后，`orders-podid` 也会失去凭证。使用 `hostNetwork` 的 Pod 无论跳数限制是多少，都能访问 IMDS，因此应单独对其进行控制。

运行 `harden` 后，在执行 `restore` 或 `down` 之前，请等待节点组重新变为 `ACTIVE`。`harden` 后运行 `restore` 会将跳数限制恢复为 2，约需 10 分钟（实测 578 秒）。

## 步骤 7：实验——同时使用 IRSA 注解和关联

工作手册指出，如果一个 ServiceAccount 同时具有 IRSA 注解和关联，EKS Webhook 只会向新 Pod 注入 Pod Identity 变量。请在步骤 3 后亲自检查。不要为 `orders-irsa` 创建关联：脚本的 `restore` 和 `down` 只会删除 `orders-podid` 关联，因此该关联会残留下来。应该改为暂时给已有该关联的 `orders-podid` 添加 IRSA 注解。

**7.1 用于显示注入结果的函数**——它会像 `demo.sh` 中的 `podid_injected()` 一样，通过服务器端试运行提交 Deployment 的 Pod 模板。

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

injected() { # deployment name
  kubectl -n "$NS" get deployment "$1" -o json |
    jq --arg n "probe-$RUN_ID" '{apiVersion:"v1",kind:"Pod",metadata:{name:$n},spec:.spec.template.spec}' |
    kubectl -n "$NS" create --dry-run=server -o json -f - |
    jq -r '[.spec.containers[0].env[]?.name
            | select(test("^AWS_(ROLE_ARN|WEB_IDENTITY_TOKEN_FILE|CONTAINER_)"))] | join(", ")'
}
```

**7.2 基线：一个只有注解的 ServiceAccount，以及一个只有关联的 ServiceAccount**

```bash
injected orders-irsa     # expected (from diff output and coexistence.log): AWS_ROLE_ARN, AWS_WEB_IDENTITY_TOKEN_FILE
injected orders-podid    # expected (from diff output and coexistence.log): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.3 给具有该关联的 `orders-podid` 添加 IRSA 注解，然后再次试运行**

```bash
kubectl -n "$NS" annotate sa orders-podid \
  "eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/wid-${RUN_ID}-irsa"
injected orders-podid    # expected (from diff output and coexistence.log): AWS_CONTAINER_CREDENTIALS_FULL_URI, AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE
```

**7.4 清理：移除注解，不要执行滚动更新**

```bash
kubectl -n "$NS" annotate sa orders-podid eks.amazonaws.com/role-arn-
kubectl -n "$NS" get sa orders-podid -o jsonpath='{.metadata.annotations}{"\n"}'   # should be empty
```

**检查内容。** 如果 7.3 只显示 Pod Identity 变量而没有 `AWS_ROLE_ARN`，则结果与工作手册一致。2026 年 11 月 21 日在运行 `d1124` 时实测：只有注解时，变量为 `AWS_ROLE_ARN` 和 `AWS_WEB_IDENTITY_TOKEN_FILE`；添加关联 5 秒后，只剩 `AWS_CONTAINER_CREDENTIALS_FULL_URI` 和 `AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE`；移除二者 2 秒后，不再有任何变量。试运行不会创建 Pod，因此不会影响正在运行的 `orders-podid`。

**原因。** 如果 ServiceAccount 具有一个关联，即使存在 IRSA 注解，EKS Webhook 也会优先使用 Pod Identity 变量，不会注入 IRSA 变量。反过来，如果之后才添加关联，**已经在运行的** Pod 会继续保留 IRSA 变量，直到它们被重新创建。因此，切换方法时，应通过滚动更新重新创建 Pod，并移除未使用的注解，避免两种配置混用。

## 公共演示页面（可选）

此功能会启动一个只读实时页面，观众可以在自己的浏览器中打开。页面上的三张卡片会显示每个副本的凭证来源、角色、S3 结果、EKS 注入的 `AWS_*` 变量名称以及近期读取记录；页面上的任何操作都不会改变任何内容。**任何拥有 URL 的人都可以查看页面**，因此页面只显示角色名称、Pod 名称、注入的变量名称和读取结果，不会显示凭证、令牌、账户 ID 或 ARN。

访问路径为 CloudFront（HTTPS，仅允许 GET/HEAD，HTTP 重定向到 HTTPS）→ CloudFront VPC 源站 → **内部** ALB（HTTP 80）→ 仪表板 Pod。ALB 安全组只允许 VPC 的 `CloudFront-VPCOrigins-Service-SG` 访问；如果该安全组尚不存在，则允许 CloudFront 托管前缀列表（`com.amazonaws.global.cloudfront.origin-facing`）访问。不会创建面向互联网的负载均衡器、公共 IP 或公共 CIDR 规则。仪表板 Pod 没有 IAM 角色，其 Role 只会列出此命名空间中的 Pod 并读取它们的日志。由于演示节点的跳数限制为 2，因此 NetworkPolicy 会将 Pod 的出站流量限制为 DNS 和 TCP 443（Kubernetes API），使其无法访问 IMDS 或 Pod Identity Agent。

**额外先决条件**：AWS Load Balancer Controller、已启用 VPC CNI 网络策略（`enableNetworkPolicy`）、支持 CloudFront VPC 源站的新版 AWS CLI v2，以及创建和删除 CloudFront VPC 源站与分配、ELB、EC2 安全组和 Route 53 记录的权限，以及读取 ACM 证书的权限。向环境文件添加三个值：

```bash
export PAGE_DOMAIN=<page host name>
export PAGE_CERT_ARN=<ACM certificate ARN in us-east-1 covering PAGE_DOMAIN>
export PAGE_ZONE_ID=<public hosted zone ID for PAGE_DOMAIN>
```

**命令**

```bash
./demo.sh page-up "$RUN_ID"     # measured 446 s (mostly the VPC origin and distribution deployments)
./demo.sh status "$RUN_ID"      # page https://<PAGE_DOMAIN>/ (Deployed)
```

如果 `PAGE_DOMAIN` 已有记录且未指向本次运行的分配，脚本会停止，不会触碰 DNS。运行 `page-down` 后再运行 `page-up` 时，在此期间查询过该域名的解析器可能会缓存“域名不存在”的响应，最长达 15 分钟（托管区的 SOA 负缓存 TTL）。重新创建后，我们观察到只有工作主机的 VPC 解析器返回 NXDOMAIN（权威服务器和公共解析器均返回正确结果）；约 10 分钟后解析恢复正常。不要在演讲开始前立即重新创建页面。

**预期画面**（实测，运行 `d1124`，每个步骤均通过截图检查）：标题行中的步骤会随演示进度变化。开始时显示“0 · 시작: 세 벌 모두 노드 역할”，并有三张标注为 node (IMDS) 的卡片；运行 `migrate-irsa` 后，orders-irsa 卡片切换到 IRSA；运行 `migrate-podid` 后，orders-podid 卡片切换到 Pod Identity 并列出注入的变量名称；运行 `revoke` 后，只有 orders-legacy 卡片变为红色并显示 `denied`。

**检查内容。** 卡片内容应与终端 `watch` 相符，顶部的 UTC 时间每 2 秒更新一次。要确认仪表板 Pod 无法访问 IMDS，请运行：

```bash
P=$(kubectl -n "wid-$RUN_ID" get pod -l app=wid-dashboard -o name | head -1)
kubectl -n "wid-$RUN_ID" exec "$P" -- python3 -c "import urllib.request as u; u.urlopen(u.Request('http://169.254.169.254/latest/api/token', method='PUT', headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'}), timeout=3)"
# measured: urllib.error.URLError (timed out) — blocked
```

**原因。** 仪表板每 2 秒从 Kubernetes API 收集状态并存入内存，响应中带有 `Cache-Control: max-age=1`。CloudFront 根据此标头缓存，因此大量观众不会增加集群 API 调用。

**费用和清理。** 页面运行期间，ALB 每天会增加约 0.55 美元的费用。运行 `./demo.sh page-down "$RUN_ID"` 删除页面（实测 546 秒）；`down` 会先执行此操作。要检查是否已清理干净：

```bash
aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='wid-$RUN_ID-page'].Id" --output text   # empty
aws cloudfront list-vpc-origins --query "VpcOriginList.Items[?Name=='wid-$RUN_ID-page'].Id" --output text         # empty
aws elbv2 describe-load-balancers --names "wid-$RUN_ID-page" 2>&1 | grep -c LoadBalancerNotFound                   # 1
aws route53 list-resource-record-sets --hosted-zone-id "$PAGE_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='$PAGE_DOMAIN.'].Type" --output text                                          # empty
```

## 清理（`down`）

如果运行过 `harden`，请先确保节点组处于 `ACTIVE` 状态。若想使用相同的 RUN_ID 再次练习，可以运行 `./demo.sh restore "$RUN_ID"`，而不是运行 `down`，以恢复到初始状态。

**命令**

```bash
./demo.sh down "$RUN_ID"
```

**预期输出**（实测，运行 `t1121`，323 秒）

```text
==> deleted namespace
==> deleting node group (3–5 min)
==> deleted launch template
==> deleted role wid-t1121-node
==> deleted role wid-t1121-irsa
==> deleted role wid-t1121-podid
==> deleted bucket
==> done
```

**检查是否有残留。** `down` 会删除专用 kubeconfig，因此请使用 AWS CLI。

```bash
aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" 2>&1 | grep -c ResourceNotFound   # 1
aws eks list-pod-identity-associations --cluster-name "$CLUSTER" --namespace "wid-$RUN_ID" \
  --query 'length(associations)'                                                             # 0
for r in node irsa podid; do
  aws iam get-role --role-name "wid-$RUN_ID-$r" >/dev/null 2>&1 && echo "left: wid-$RUN_ID-$r"
done                                                                                          # no output
aws ec2 describe-launch-templates --filters "Name=tag:LabRun,Values=$RUN_ID" \
  --query 'LaunchTemplates[].LaunchTemplateName' --output text                               # empty
aws ec2 describe-instances --filters "Name=tag:LabRun,Values=$RUN_ID" \
  "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text                              # empty
aws s3api head-bucket --bucket "wid-$RUN_ID-$(aws sts get-caller-identity --query Account --output text)-$AWS_REGION" \
  2>&1 | grep -c 404                                                                         # 1
```

还要使用你常用的 kubeconfig 检查 `kubectl get namespace wid-$RUN_ID` 是否返回 `NotFound`。如果启动了公共演示页面，请检查是否还有 CloudFront 分配或内部 ALB 残留。你可以保留环境文件供下一个实验使用；如果不再需要，可删除 `$STATE_DIR`。

## 故障排除

| 症状 | 原因和解决方法 |
| --- | --- |
| 只显示用法文本（`Usage: ./demo.sh <command> RUN_ID`） | RUN_ID 必须是 4–12 个小写字母或数字；不能包含连字符或大写字母。 |
| `set CLUSTER to an existing EKS cluster name` 或类似消息 | `CLUSTER`、`VPC_NAME` 或 `SUBNET_NAMES` 为空。检查环境文件的路径和内容；环境文件中的值优先于 shell 变量。 |
| `cluster VPC is not <VPC_NAME>` | 通过 `VPC_NAME` 找到的 VPC 不是集群 VPC。请重新检查集群 VPC 的 Name 标签。 |
| `private subnet '<name>' not found in <VPC_NAME>` | 子网不在集群 VPC 中，或者它是 `MapPublicIpOnLaunch=true` 的公有子网。请使用私有子网的 Name 标签。 |
| `eks-pod-identity-agent add-on is required` | 使用 `aws eks create-addon --cluster-name "$CLUSTER" --addon-name eks-pod-identity-agent` 安装，并等待状态变为 `ACTIVE`。请与集群管理员协调。 |
| `IAM OIDC provider for the cluster is required` | 将集群颁发者注册为 IAM OIDC 提供商（例如 `eksctl utils associate-iam-oidc-provider --cluster "$CLUSTER" --approve`）。 |
| `role ... is not tagged for run ...; refusing to modify it` | 已存在同名角色，但没有此实验的标签。请使用其他 RUN_ID。 |
| `up` 卡在创建节点组的步骤 | 检查 `aws eks describe-nodegroup --cluster-name "$CLUSTER" --nodegroup-name "wid-$RUN_ID" --query nodegroup.health`。如果私有子网没有 NAT 路径，节点就无法加入集群或拉取镜像。 |
| `watch` 一直显示 `starting` | Pod 尚未进入 `Running` 状态，或没有日志。使用 `kubectl -n "$NS" get pods` 和 `kubectl -n "$NS" describe pod` 检查。 |
| `association change not visible to admission within 120s` | 使用 `aws eks list-pod-identity-associations` 检查关联是否存在，然后再次运行 `migrate-podid`。如果关联已存在，脚本会跳过创建步骤，直接检查变量注入情况。 |
| 运行 `migrate-podid` 后，`orders-podid` 仍使用节点角色 | Pod 是在变量注入之前创建的。使用步骤 3 中的命令检查变量；如果缺少这些变量，再次运行 `kubectl -n "$NS" rollout restart deploy/orders-podid`。 |
| `legacy copy did not flip within 180s` | IAM 传播较慢。继续运行 `watch` 观察。再次运行 `revoke` 会提示策略已删除，并再次等待。 |
| S3 结果为 `error` | 出现了 `AccessDenied` 或缺少凭证以外的错误。检查 Pod 到 STS 和 S3 端点的路径（NAT、VPC 端点、DNS）。 |
| 角色符合预期，但结果为 `denied` | 角色身份和资源访问是两回事。检查存储桶策略、SCP、权限边界和 VPC 端点策略。 |

## 参考资料

- [将 EKS 节点 IAM 权限迁移到 IRSA 和 Pod Identity](../../security/17-eks-workload-identity-migration.md) — 本实验的工作手册
- [演示代码和演示者操作手册](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/security/eks-workload-identity)
- [面向 ServiceAccount 的 IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Pod Identity 的工作原理](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-how-it-works.html)
- [托管节点组启动模板](https://docs.aws.amazon.com/eks/latest/userguide/launch-templates.html)

## 后续步骤

- 通过 [EKS 工作负载 IAM 迁移测验](../../quizzes/security/17-eks-workload-identity-migration-quiz.md)检查你对内容的理解。
- 使用工作手册中的[生产迁移顺序](../../security/17-eks-workload-identity-migration.md)，为实际工作负载规划依赖项发现和金丝雀切换。
