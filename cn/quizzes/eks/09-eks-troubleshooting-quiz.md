# Amazon EKS 故障排查测验

> **最后更新**：2026 年 9 月 12 日

本测验检验你诊断并解决 Amazon EKS 集群各类问题的能力。

## 测验概览

- 集群创建与配置问题
- 网络问题
- 节点与 Pod 问题
- 存储问题
- 安全与访问问题
- 性能与扩展性问题

## 选择题

### 1. EKS 控制平面创建失败时，最有用的第一步是什么？

- A. 只检查集群名称是否唯一
- B. 检查准确的错误/请求，并核实调用方与服务角色 IAM、VPC/子网及相关配额
- C. 立即在其他 Region 再创建一个集群
- D. 选择更大的工作节点实例类型

<details>
<summary>显示答案</summary>

**答案：B. 检查准确的错误/请求，并核实调用方与服务角色 IAM、VPC/子网及相关配额**

从失败的请求或 CloudFormation 事件入手。IAM、网络、配额和名称冲突都是可检查的假设；在读取错误之前，不能把它们当作统计结论。

**核实内容**

| 区域 | 证据 |
| --- | --- |
| 调用方 | 账号/Region/配置文件是否正确；所需 EKS 操作、`iam:PassRole`、权限边界/会话/SCP 控制，以及必要时创建服务关联角色的权限 |
| 集群服务角色 | 准确的角色 ARN、EKS 信任关系和必需的服务角色策略；它与调用方角色及工作节点角色不同 |
| 集群子网 | 支持的 AZ、至少两个不同 AZ 以及可用地址；节点/Pod/负载均衡器容量是另一项预算 |
| 端点/依赖项 | 预期的私有/公有模式、DNS、路由、安全组/NACL 和所需 AWS 服务访问 |
| 配额 | 实际服务配额及当前已应用的 Region/账号上限；涉及节点创建时也检查 EC2 vCPU 限制 |
| 基础设施所有者 | 原始 Terraform/CloudFormation/eksctl 配置、状态及失败操作 |

当前 EKS 要求所选每个集群子网至少有 **6 个 IP 地址**，并建议至少 **16 个**；子网还必须覆盖至少两个 AZ。CIDR 大小本身不能证明这些地址仍然可用。过去通用的“最小 /28、建议 /24”说法混淆了控制平面与工作负载的容量。私有环境可以使用所需端点；NAT/普通互联网访问并非一概必需。

`AmazonEKSClusterPolicy` 用于集群服务角色。把它附加给人工用户，并不会授予所有创建/PassRole 权限或 Kubernetes RBAC。添加集群所有权子网标签也不是通用的创建故障修复办法。

**只读调查**

```bash
set -euo pipefail
: "${AWS_REGION:?}"; : "${EXPECTED_ACCOUNT_ID:?}"; : "${CLUSTER_NAME:?}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT_ID" != "$EXPECTED_ACCOUNT_ID" ]; then
  echo "Account mismatch" >&2; exit 1
fi
aws cloudtrail lookup-events --region "$AWS_REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateCluster \
  --max-items 20 --output json
aws service-quotas list-service-quotas --service-code eks --region "$AWS_REGION"
: "${VPC_ID:?Set the VPC from the original request}"
aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[].{Id:SubnetId,AZ:AvailabilityZone,AZId:AvailabilityZoneId,AvailableIPs:AvailableIpAddressCount}'
# For an eksctl-owned creation attempt, inspect its existing stacks:
eksctl utils describe-stacks --cluster "$CLUSTER_NAME" --region "$AWS_REGION"
```

如果集群已经可用，用 `describe-cluster` 检查；如果集群尚未创建，应保留创建错误，不要把 ResourceNotFound 当作第二个根因。对于其他 CloudFormation 所有者，检查准确堆栈的事件。`eksctl create cluster --verbose ...` 和 CLI 调试模式仍会创建资源，并非只读诊断。

**示例错误消息**

- `eks:CreateCluster` 调用被拒绝时，应检查调用方权限；服务角色问题属于另一条权限路径。
- 旧示例中 `us-west-2a` 容量不足，说明的是 AZ/容量类响应，不代表该 Region 当前的可用性。
- 旧的 “Current limit is 5” 消息仅作为历史示例保留；确定请求提高到多少之前，应查询当前已应用配额。
- `UnsupportedAvailabilityZoneException` 表示该账号的 EKS 集群不支持相应 AZ，并不只是缺少 EC2 实例类型供给。

**检查基础设施配置**

检查并修正原有所有者的配置。下面的 Terraform 片段展示了显式版本/网络意图及状态输出；它不是完整的新集群模块，也不是诊断期间应执行的命令：

```hcl
# Excerpt of the original state-owned configuration, not a diagnostic apply.
# Preserve its other settings and role/policy dependencies.
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = var.cluster_role_arn
  version  = var.cluster_version
  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = var.cluster_security_group_ids
    endpoint_private_access = true
    endpoint_public_access  = false
  }
}

output "cluster_status" {
  value = aws_eks_cluster.main.status
}
```

提供已核实且现有的角色/子网/安全组输入，保留必需的角色策略依赖关系及其他设置，并检查私有端点的访问路径。输出值来自 Terraform 状态；创建失败时，不保证它会出现或包含最新失败详情。应使用 provider 诊断以及 AWS 请求/堆栈证据。本次检查未执行 Terraform apply 或创建集群。

确定原因后，经审查针对性地修正权限/网络/配额，再由所有者重试。A 是有用但单独不足的检查。C 会改变放置/数据/网络，并可能增加成本，却不一定解决原因。D 会改变工作节点，不能解决控制平面创建问题。

来源：[EKS 网络要求](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)、[EKS 故障排查](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)、[Terraform EKS 集群](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster)。

</details>

### 2. EKS 节点处于 NotReady 状态时，最有效的首项调查是什么？

- A. 立即终止节点
- B. 检查节点状况/事件、日志、资源以及实际网络/身份路径
- C. 自行重启 EKS 托管 API 服务器
- D. 删除集群中的所有 Pod

<details>
<summary>显示答案</summary>

**答案：B. 检查节点状况/事件、日志、资源以及实际网络/身份路径**

根据状况原因/时间和实际节点身份开展调查。Ready=False、心跳缺失/Ready=Unknown、磁盘压力和内存压力是不同证据；任何一个都不能自动确定根因。

**盘点节点与工作负载**

以下只读示例按名称/UID 选择节点，并用 `spec.nodeName` 选出其 Pod，避免不可靠的 IP/grep 匹配：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NODE_NAME:?}"
NODE_JSON=$(kubectl --context "$KUBE_CONTEXT" get node "$NODE_NAME" -o json)
printf '%s\n' "$NODE_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,labels:.metadata.labels,providerID:.spec.providerID,taints:.spec.taints,unschedulable:.spec.unschedulable,nodeInfo:.status.nodeInfo,conditions:.status.conditions,capacity:.status.capacity,allocatable:.status.allocatable}'
NODE_UID=$(printf '%s\n' "$NODE_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" get events -A --field-selector "involvedObject.uid=$NODE_UID" \
  --sort-by='.metadata.creationTimestamp'
kubectl --context "$KUBE_CONTEXT" get pods -A --field-selector "spec.nodeName=$NODE_NAME" -o wide
```

访问 EC2 或主机之前，先确认节点 ProviderID/账号/Region 和计算类型。对于托管组，检查其运行状况及修复/更新配置：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{status:status,health:health,version:version,release:releaseVersion,nodeRole:nodeRole,repair:nodeRepairConfig,update:updateConfig}'
```

在可访问的标准 Linux 节点上，使用[源指南中的远程会话步骤](../../eks/09-eks-troubleshooting.md)检查 kubelet/containerd 日志、字节数/inode、内存和路由。实际镜像中可能没有 Docker 守护进程或 `/var/log/syslog`。节点 DNS 不会自动等同于 Pod 的集群 DNS。连接端点时使用集群 CA；`curl -k` 会掩盖证书问题。

在清理镜像、删除日志或重启之前保留证据。`kubectl top` 依赖可用的指标路径，在不健康节点上可能失败。检查已配置的证书路径时，不要暴露私钥。`kubeadm alpha certs renew all` 既不是当前通用命令，也不是 EKS 节点修复步骤；`eksctl replace nodegroup` 不受支持。

**恢复操作与自动修复**

确定原因后，结合容量、PDB、数据和节点所有者，协调替换/重启节点。受控 drain 失败时应停止；异步重启后不要继续终止节点或立即取消隔离。

自动节点修复是实际存在的 EKS 机制。`update_config.max_unavailable` 控制版本更新造成的中断，并不会启用修复；`health_check { type = "EKS" }` 也不是 `aws_eks_node_group` 的配置块。当前 provider 提供 `node_repair_config`：

```hcl
# Fragment of a reviewed EKS-optimized-AMI managed node group.
resource "aws_eks_node_group" "self_healing" {
  cluster_name    = var.cluster_name
  node_group_name = var.node_group_name
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnet_ids
  version         = var.node_kubernetes_version
  ami_type        = var.ami_type
  release_version = var.ami_release
  instance_types  = var.instance_types

  scaling_config {
    desired_size = 3
    min_size     = 3
    max_size     = 6
  }
  update_config {
    max_unavailable = 1
  }
  node_repair_config {
    enabled                           = true
    max_parallel_nodes_repaired_count = 1
  }
}
```

这是配置片段，不是经过测试的生产模块。请提供兼容且经过审查的 Kubernetes/AMI/实例输入和现有所有权配置。如果自动扩缩容器管理容量，应协调期望容量。节点组标签不能自动证明底层 ASG 带有必要的 CA 发现标签。

不同计算所有者的修复默认值/阈值不同。Auto Mode 默认启用修复行为；托管节点组需要启用，Karpenter 也有自己的功能要求。节点监控可以报告问题，但不代表已启用修复。当前默认修复表**不会**自动修复 MemoryPressure 或 DiskPressure。机群健康阈值、并行度和 ARC 控制可能限制操作；不要承诺一定替换节点或一定受 PDB 保护。

**监控示例**

不能假定 `AWS/EKS` 中存在名为 `NodeNotReady` 的内置指标。已有的 kube-state-metrics/Prometheus Operator 安装可以根据实际节点状况进行评估：

```yaml
# Existing single-cluster Prometheus Operator/KSM installation required.
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-readiness-example
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
    - name: node-readiness-example
      rules:
        - alert: NodeNotReady
          expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="Ready",status="true"}) == 0
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Node {{ $labels.node }} is not Ready"
            description: "Investigate node conditions, reachability and workload impact before recovery."
```

将命名空间/release/job 选择器设为实际安装所用值。10 分钟等待时间仅为示例。抓取/状况数据缺失时需要单独监控遥测健康，不能把它视为节点健康。此告警既不会配置通知，也不会执行恢复；应分别验证。创建一个未定义的 `node-recovery.zip` Lambda 并不能构成安全的自动修复。

C 不是客户自行重启 EKS 托管 API 服务器的路径；API 连通性确实可能导致节点就绪问题。A 和 D 会扩大中断并可能破坏证据，却未必解决根因。

来源：[EKS 节点修复](https://docs.aws.amazon.com/eks/latest/userguide/node-repair.html)、[Terraform 托管节点资源](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_node_group)、[节点指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/cluster/node-metrics.md)。

</details>

### 3. 在 EKS 上应如何正确调查 ImagePullBackOff？

- A. 提高每个容器的内存限制
- B. 查看拉取错误，核实镜像/平台及实际拉取身份和网络路径
- C. 不看错误就强制重新下载镜像
- D. 删除所有网络策略

<details>
<summary>显示答案</summary>

**答案：B. 查看拉取错误，核实镜像/平台及实际拉取身份和网络路径**

ImagePullBackOff 是重试/退避状态，不代表某个原因“最可能”。检查所有受影响的普通容器/init 容器及 kubelet 给出的准确事件：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
POD_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json)
printf '%s\n' "$POD_JSON" | jq '{
  name:.metadata.name,uid:.metadata.uid,owners:.metadata.ownerReferences,
  node:.spec.nodeName,serviceAccount:.spec.serviceAccountName,
  imagePullSecrets:.spec.imagePullSecrets,
  containers:[.spec.containers[] | {name,image,imagePullPolicy,resources}],
  initContainers:[.spec.initContainers[]? | {name,image,resources}],
  phase:.status.phase,reason:.status.reason,message:.status.message,
  conditions:.status.conditions,containerStatuses:.status.containerStatuses,
  initContainerStatuses:.status.initContainerStatuses
}'
POD_UID=$(printf '%s\n' "$POD_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$POD_UID" --sort-by='.metadata.creationTimestamp'
```

区分仓库/tag/digest 缺失、架构不受支持、凭证/授权、registry 限流、节点 DNS/TLS/出口网络，以及本地磁盘/运行时故障。本地 Docker 拉取使用另一种身份/路径，不能证明节点能够拉取。

**ECR 身份与网络**

EC2 节点通常通过节点拉取凭证路径获取镜像；Fargate 使用 Pod 执行角色。应用的 IRSA/Pod Identity 不是应用启动前下载镜像所用的身份。按需核实仓库策略与跨账号访问。仅创建新 IAM 角色而未将它关联到相关计算资源，不会改变镜像拉取行为。

指定仓库/账号/Region，并用 tag **或** digest；不要用 `cut` 拆分任意镜像字符串：

```bash
set -euo pipefail
: "${REGISTRY_REGION:?Set the image registry Region}"
: "${REGISTRY_ACCOUNT_ID:?Set its account ID}"
: "${REPOSITORY_NAME:?Set the exact repository path}"
: "${ECR_IMAGE_ID:?Set imageTag=... or imageDigest=sha256:...}"
aws ecr describe-images --region "$REGISTRY_REGION" \
  --registry-id "$REGISTRY_ACCOUNT_ID" --repository-name "$REPOSITORY_NAME" \
  --image-ids "$ECR_IMAGE_ID" \
  --query 'imageDetails[].{digest:imageDigest,tags:imageTags,pushedAt:imagePushedAt,mediaType:imageManifestMediaType}'
```

此操作使用操作者的 AWS 凭证检查镜像元数据，不会验证 kubelet 权限。私有 ECR 访问可能需要 ECR API/DKR 与 S3 路径、端点策略/安全组及 DNS。`ecr.dkr` 不是任意私有 registry 的端点。通常 Pod NetworkPolicy 的更改无法修复节点运行时的 registry 身份验证。

**权限示例**

对于明确选定的现有 EC2 节点角色，以下权限示例说明如何只拉取一个仓库。`GetAuthorizationToken` 不能按仓库资源限定，因此对应 statement 使用 `*` 并附加 Region 条件；镜像读取权限则限定到该仓库：

```hcl
# Permission example for a reviewed existing EC2 node role.
# This does not create/associate a new role or create an image-pull Secret.
data "aws_iam_role" "node" {
  name = var.existing_node_role_name
}

resource "aws_iam_policy" "ecr_pull" {
  name = var.pull_policy_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:RequestedRegion" = var.registry_region }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
        Resource = var.repository_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = data.aws_iam_role.node.name
  policy_arn = aws_iam_policy.ecr_pull.arn
}
```

使用实际仓库 ARN/Region，并检查现有授权/边界/SCP 及跨账号仓库策略。添加窄范围策略不会移除已有的宽范围策略。Fargate 需要单独配置执行角色；此 EC2 角色示例既不会创建 Kubernetes Secret，也不会配置 Fargate profile。本次审查没有执行 IAM 更改。

**镜像拉取 Secret**

需要 Secret 的 registry 应使用受保护、自包含的 Docker auth 文件，以及[源指南中的命名空间 Secret/Pod 模板步骤](../../eks/09-eks-troubleshooting.md)。不要打印 Secret 数据/令牌，也不要把密码放在诊断命令行中。桌面 credential-helper 的引用并不是 kubelet 可用的认证数据。

通常无法原地修改现有 Pod 的 imagePullSecrets。应修改所属 Deployment/StatefulSet 模板，在保留当前拉取 Secret 列表的同时进行受控 rollout。更新 ServiceAccount 会影响新准入的 Pod；不要为了一个应用去修改默认 ServiceAccount，影响无关工作负载。

**凭证续期设计**

标准 EKS ECR 拉取不需要旧方案中的 token 续期 CronJob。ECR 授权令牌有效期为 12 小时。如果某个非原生消费者确实需要手动维护 ECR 拉取 Secret，应使用其受支持的凭证机制，或明确设计续期流程。

旧计划 `*/6 * * * *` 表示**每 6 分钟**，不是 6 小时；6 小时一次的例子是 `0 */6 * * *`，并应设置控制器时区或受支持的 `.spec.timeZone`。仅有计划任务还不构成有效续期器：它需要经过审查且包含所需工具的镜像、AWS 身份、范围受限的 Kubernetes 权限、准确目标命名空间、重叠/失败处理和经过测试的轮换流程。完成验证前应保持暂停。更新预先创建的命名 Secret，而不是先删除它造成凭证空档。AWS CLI 官方镜像并不意味着其中有 kubectl。

固定预期的镜像 digest，确保 registry 可用，并先调查实际事件，再决定是否更改拉取策略。`Always` 无法修复不存在的镜像或缺失权限。A/C/D 都不能确定失败的镜像拉取路径。

来源：[Fargate 执行角色](https://docs.aws.amazon.com/eks/latest/userguide/pod-execution-role.html)、[ECR 令牌命令](https://docs.aws.amazon.com/cli/latest/reference/ecr/get-authorization-token.html)、[私有 registry Secret](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)。

</details>

### 4. Service 无法将流量送达其 Pod 时，最有用的首项调查是什么？

- A. 立即重建 Service
- B. 检查其 selector/type、Pod 就绪状态、EndpointSlices、端口及实际允许的路径
- C. 重启所有 Pod
- D. 自行重启托管 API 服务器

<details>
<summary>显示答案</summary>

**答案：B. 检查其 selector/type、Pod 就绪状态、EndpointSlices、端口及实际允许的路径**

修改资源之前，先追踪 Service 的发现/路由过程。使用受影响的命名空间和源客户端，并将 Service 配置与实际应用监听器及就绪探针进行对照：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${SERVICE_NAME:?}"
SERVICE_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service "$SERVICE_NAME" -o json)
printf '%s\n' "$SERVICE_JSON" | jq '{metadata: {name: .metadata.name, namespace: .metadata.namespace}, spec: .spec, status: .status}'
SELECTOR=$(printf '%s\n' "$SERVICE_JSON" | jq -r '(.spec.selector // {}) | to_entries | map("\(.key)=\(.value)") | join(",")')
if [ -n "$SELECTOR" ]; then
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o wide
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$SELECTOR" -o json \
    | jq '.items[] | {name:.metadata.name,phase:.status.phase,ready:[.status.conditions[]? | select(.type=="Ready")],containers:.status.containerStatuses}'
else
  printf 'No selector: inspect ExternalName or explicitly managed EndpointSlices as applicable.\n'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get endpointslices \
  -l "kubernetes.io/service-name=$SERVICE_NAME" -o yaml
```

此辅助逻辑会处理没有 selector 的 Service，不会意外选中所有 Pod。ExternalName 提供别名解析；无头 Service 有意设置 `clusterIP: None`；也可能使用手动管理的 EndpointSlices。检查 endpoint 的 Ready/serving/terminating 状况及流量策略。存在一个就绪 sidecar 或 Pod 的 phase=Running，并不等同于 Pod Ready 条件。

**修正已观察到的问题**

- selector 不匹配：修改所属 Service/Pod 模板，而不是只改一个可被替换的 Pod 标签。
- 端口不匹配：Service 端口、命名 targetPort 和实际应用监听器必须一致；声明 containerPort 不会创建监听器。
- 策略限制：检查源端 egress 和目标端 ingress、标签及实现覆盖范围。不要删除策略，也不要允许所有命名空间访问所有端口。
- DNS/数据平面：区分名称解析与传输，并确认使用标准 kube-proxy、其他实现还是 Auto Mode。纯 Auto Mode 使用节点 DNS；混合集群仍为非 Auto 节点保留 DNS。

此**独立策略示例**仅允许经过审查的对端/端口。使用前应调整标签/命名空间，并审查完整的必要流量矩阵：

```yaml
# Example ingress policy only: review both peers and the complete allowed-flow matrix.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-from-web
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
```

它可能隔离其他后端入口，且不会创建客户端 egress 规则。需要进行正向和负向测试。

**Terraform Service/Deployment 测试夹具**

原始 Service 到 Pod 示例保留为一次性 Linux 测试夹具，其中有真实声明的监听器、匹配标签、就绪探针和受限资源。将 provider 配置到经审查的测试环境，选择新命名空间；不要导入现有应用命名空间：

```hcl
# Disposable example; configure the Kubernetes provider/context externally.
variable "test_namespace" {
  type = string
  validation {
    condition     = can(regex("^docs-service-check-[a-z0-9]{8,16}$", var.test_namespace))
    error_message = "Supply a new unique namespace with the test prefix."
  }
}
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = var.test_namespace
  }
}
resource "kubernetes_deployment_v1" "app" {
  metadata {
    name      = "app-deployment"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    replicas = 2
    selector {
      match_labels = { app = "service-demo" }
    }
    template {
      metadata {
        labels = { app = "service-demo" }
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/os" = "linux" }
        security_context {
          run_as_non_root = true
          run_as_user     = 65532
          run_as_group    = 65532
          fs_group        = "65532"
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }
        container {
          name    = "app"
          image   = "docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
          command = ["sh", "-ec"]
          args    = ["mkdir -p /tmp/www; printf 'ok\\n' > /tmp/www/index.html; exec httpd -f -p 8080 -h /tmp/www"]
          port {
            name           = "http"
            container_port = 8080
          }
          readiness_probe {
            http_get {
              path = "/"
              port = "http"
            }
            period_seconds = 5
          }
          resources {
            requests = { cpu = "10m", memory = "16Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "tmp"
          empty_dir {}
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "app" {
  metadata {
    name      = "app-service"
    namespace = kubernetes_namespace_v1.app.metadata[0].name
  }
  spec {
    selector = { app = "service-demo" }
    type     = "ClusterIP"
    port {
      name        = "http"
      port        = 80
      target_port = "http"
    }
  }
}
```

这不是生产应用，也不是经测量得出的资源建议。它不需要应用 API/RBAC 权限。provider 字段已经本地审查，但不代表在实际环境运行过 Terraform apply 或镜像。

**受限连通性 Job**

测试夹具 Service 和 Pod 就绪后，保存下面的 Job，并将命名空间替换为准备好的命名空间。探测不需要 kubectl 二进制或 Kubernetes API token：

```yaml
# Use kubectl create; replace namespace with the prepared fixture namespace.
apiVersion: batch/v1
kind: Job
metadata:
  generateName: service-probe-
  namespace: docs-service-check-12345678
spec:
  activeDeadlineSeconds: 60
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: probe
          image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
          command: [sh, -ec]
          args:
            - nslookup app-service; wget -T 5 -q -O- http://app-service:80
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              cpu: 100m
              memory: 64Mi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
```

创建具有新生成名称的 Job，不要重用通用名称：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${TEST_NAMESPACE:?}"; : "${SERVICE_PROBE_FILE:?}"
JOB_NAME=$(kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" create \
  -f "$SERVICE_PROBE_FILE" -o jsonpath='{.metadata.name}')
: "${JOB_NAME:?Job creation did not return a name}"
printf 'Created probe: %s/%s\n' "$TEST_NAMESPACE" "$JOB_NAME"
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" wait \
  --for=condition=complete "job/$JOB_NAME" --timeout=90s
kubectl --context "$KUBE_CONTEXT" -n "$TEST_NAMESPACE" logs "job/$JOB_NAME"
```

等待失败时，应保留生成的 Job 并检查其 Pod/事件/日志；不要无条件打印成功消息，也不要删除现有命名空间。记录其 UID，查看证据后只清理自己拥有的测试资源。测试覆盖 DNS 和一次 HTTP 请求，不覆盖所有客户端身份、直接 Pod 路径、负载均衡器或 SLO。需要时使用同一授权来源分别比较直接 Pod 和 Service 访问。

A/C 会在诊断前丢失证据或增加中断。D 不是客户操作 EKS 控制平面的方式；如果证据指向那里，应检查 API/控制器健康。

来源：[Services](https://kubernetes.io/docs/concepts/services-networking/service/)、[EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)、[NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)。

</details>

### 5. PVC 保持 Pending 时应首先调查什么？

- A. 始终添加更大的节点
- B. 检查 claim/class、绑定模式、消费者调度、driver 和配置身份
- C. 始终提高 Pod 优先级
- D. 始终安装 Cluster Autoscaler

<details>
<summary>显示答案</summary>

**答案：B. 检查 claim/class、绑定模式、消费者调度、driver 和配置身份**

Pending 本身并不表示存储故障。采用 WaitForFirstConsumer 时，claim 等待合适的消费者 Pod 完成调度可能是正常行为。先识别实际 driver/计算路径，不要预设为 EBS 或 IAM 故障。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${PVC_NAME:?}"
PVC_JSON=$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc "$PVC_NAME" -o json)
printf '%s\n' "$PVC_JSON" | jq '{name:.metadata.name,uid:.metadata.uid,status:.status,spec:.spec,storageClassFieldPresent:(.spec | has("storageClassName"))}'
PVC_UID=$(printf '%s\n' "$PVC_JSON" | jq -er '.metadata.uid')
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --field-selector "involvedObject.uid=$PVC_UID" --sort-by='.metadata.creationTimestamp'
SC_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.storageClassName // empty')
if [ -n "$SC_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get storageclass "$SC_NAME" -o yaml
else
  printf 'Inspect absent versus explicitly empty storageClassName and default/static binding intent.\n'
fi
PV_NAME=$(printf '%s\n' "$PVC_JSON" | jq -r '.spec.volumeName // empty')
if [ -n "$PV_NAME" ]; then
  kubectl --context "$KUBE_CONTEXT" get pv "$PV_NAME" -o yaml
  kubectl --context "$KUBE_CONTEXT" get volumeattachments -o json \
    | jq --arg pv "$PV_NAME" '.items[] | select(.spec.source.persistentVolumeName == $pv) | {name:.metadata.name,spec,status}'
fi
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -o json \
  | jq --arg pvc "$PVC_NAME" '.items[] | select(any(.spec.volumes[]?; .persistentVolumeClaim.claimName == $pvc)) | {name:.metadata.name,node:.spec.nodeName,phase:.status.phase,conditions:.status.conditions}'
```

此辅助逻辑会区分 storageClassName 缺失与空值，并通过 JSON 选择消费者。Kubernetes 不支持旧的 Pod 字段选择器 `spec.volumes.persistentVolumeClaim.claimName`。如果 claim 已 Bound，应调查挂载/可读性，而不是把绑定当作应用验证完毕。

**检查实际状况**

- Class/provisioner：确认引用的 class 存在，并匹配标准 EBS、Auto Mode、EFS 或其他 driver。显式空 class 与省略默认 class 请求的是不同绑定路径。
- 延迟绑定：检查消费者请求、污点/亲和性、可用区及容量。节点供给、优先级和自动扩缩可能通过消费者间接影响 PVC 进度；A/C/D 不是通用修复方式。
- 身份：检查实际控制器 IRSA/Pod Identity 和 KMS 权限，而不只是节点角色。Fargate 无法挂载 EBS 卷；Auto Mode 使用自己的 provisioner。
- CSI：检查 controller/node 健康、事件、当前兼容的 add-on 版本及所有权。查明错误前不要强制重装。

**Class 与数据生命周期**

不要为修复单个 claim 去修改现有 StorageClass 不可变的绑定模式，也不要把集群默认 class 切换掉。新的、显式指定的标准 driver class 可以这样配置：

```yaml
# New, explicitly selected StorageClass for standard EBS CSI, not an in-place edit.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: diagnostic-ebs-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  csi.storage.k8s.io/fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Retain
```

这是 YAML 配置示例，不是应用到现有 class 的命令。Retain 会保留存储以便单独决定后续生命周期，也可能继续产生费用。PVC YAML 不是数据备份；删除/重建 claim 可能销毁数据，或留下需要有意重新绑定的保留卷。

Auto Mode 要求使用 `ebs.csi.eks.amazonaws.com`，而非上面的标准 provisioner。其节点根卷/数据卷加密并不意味着所有动态 PVC 都已加密。应显式请求 `encrypted: "true"` 并检查实际 EBS 卷/密钥。应使用文档化的快照或适用的 Retain/静态迁移步骤，不要尝试修改已绑定 claim 的 provisioner/class。

**Terraform 所有权示例**

对于现有标准 EBS CSI add-on，应选择经审查的版本、完整且通过 schema 验证的配置以及准备好的 controller 身份。此 IRSA 示例不同时配置 Pod Identity：

```hcl
# Existing standard EBS CSI add-on with a reviewed IRSA identity.
# Preserve/import its existing resource ownership; do not create a duplicate add-on.
resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name                = var.cluster_name
  addon_name                  = "aws-ebs-csi-driver"
  addon_version               = var.reviewed_ebs_addon_version
  service_account_role_arn    = var.controller_irsa_role_arn
  configuration_values        = file(var.reviewed_configuration_file)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}
```

保留/导入现有所有权。controller 角色需要当前、范围受限的 EBS 权限/标签条件，以及适用时的客户密钥权限。旧 IAM module/add-on 版本组合并不能保证当前兼容性；`--role-only` 不会把角色关联到 add-on。请遵循[存储源指南](../../eks/04-eks-storage-part1.md)和当前 add-on 目录。

也可以通过当前 Kubernetes resource 管理同一个新 class：

```hcl
# New standard-driver class, explicitly selected by test PVCs.
resource "kubernetes_storage_class_v1" "ebs_gp3" {
  metadata {
    name = "diagnostic-ebs-gp3"
  }
  storage_provisioner    = "ebs.csi.aws.com"
  volume_binding_mode    = "WaitForFirstConsumer"
  allow_volume_expansion = true
  reclaim_policy         = "Retain"
  parameters = {
    type                        = "gp3"
    encrypted                   = "true"
    "csi.storage.k8s.io/fstype" = "ext4"
  }
}
```

对此 class 选择 YAML **或** Terraform 作为唯一所有者。provider 字段/语法可以在本地审查，但这不能证明目标集群中的 IAM、CSI 配置或数据恢复正常。

**隔离的配置测试**

要测试经过审查的 Linux EC2 路径，应先从 [EKS 升级指南](../../eks/08-eks-upgrades.md)保存完整的 `eks-upgrade-smoke.py` 辅助程序，再使用明确选定的测试 context/class：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?Set the reviewed test context}"
: "${TEST_STORAGE_CLASS:?Set the reviewed compatible test class}"
export KUBE_CONTEXT TEST_STORAGE_CLASS
export RUN_SMOKE_TEST=yes
export CLEANUP_ON_SUCCESS=no
# Save the complete helper from the EKS upgrades source guide first.
python3 eks-upgrade-smoke.py
```

它会创建唯一命名空间和 PVC writer，等待延迟绑定后，再由单独的消费者读取标记。它会记录证据并保留失败现场。实际运行时需考虑存储成本和 Retain 清理。本次审查没有执行云端配置、创建卷、挂载或基准测试；不要使用过去那个创建无关计费卷的 AWS CLI Job 来诊断 PVC。

来源：[StorageClasses](https://kubernetes.io/docs/concepts/storage/storage-classes/)、[EBS CSI](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)、[Auto Mode class](https://docs.aws.amazon.com/eks/latest/userguide/create-storage-class.html)。

</details>

### 6. 自动扩缩行为与预期不符时，最有效的调查方式是什么？

- A. 给所有 Pod 分配更多资源
- B. 手动增加节点后就停止调查
- C. 找出副本/资源/节点分别由谁管理，并检查其指标、状况、限制、身份和事件
- D. 重建集群

<details>
<summary>显示答案</summary>

**答案：C. 找出副本/资源/节点分别由谁管理，并检查其指标、状况、限制、身份和事件**

区分 HPA 的副本扩缩、VPA 的资源建议/更新，以及 CA/Karpenter/Auto Mode 的节点供给。它们管理不同资源、依赖不同信号，而且不一定全部安装。

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get hpa -o json \
  | jq '.items[] | {name:.metadata.name,target:.spec.scaleTargetRef,min:.spec.minReplicas,max:.spec.maxReplicas,current:.status.currentReplicas,desired:.status.desiredReplicas,metrics:.status.currentMetrics,conditions:.status.conditions}'
kubectl --context "$KUBE_CONTEXT" get apiservice v1beta1.metrics.k8s.io
kubectl --context "$KUBE_CONTEXT" get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/$NAMESPACE/pods"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp'
```

检查 HPA 条件、当前指标、requests、min/max 和行为配置。期望/当前副本数不同可能只是正常收敛。指标数据缺失或报错可能阻止缩容。CPU/内存资源指标使用 Metrics Server；自定义/外部指标需要各自的 adapter/integration。查询失败不能证明 API/CRD 不存在。

对于现有托管节点组，应检查其实际 ASG，而不是用猜测的标签搜索所有账号中的组：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"; : "${NODEGROUP_NAME:?}"
aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NODEGROUP_NAME" \
  --region "$AWS_REGION" \
  --query 'nodegroup.{scaling:scalingConfig,health:health,autoScalingGroups:resources.autoScalingGroups}'
: "${ASG_NAME:?Select the actual group returned above}"
aws autoscaling describe-auto-scaling-groups --region "$AWS_REGION" \
  --auto-scaling-group-names "$ASG_NAME" \
  --query 'AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,Instances:Instances,Tags:Tags}'
```

CA 根据无法调度的 Pod 和约束作出响应，并非只看节点平均 CPU 是否高。检查其支持的 Kubernetes 次版本、准确 Pod 身份、最小权限的发现/扩缩权限、ASG 标签、最大规模、EC2/IP 配额和启动失败。节点组标签不能证明 ASG 具有发现标签。托管组限制应优先由 EKS/基础设施所有者管理；直接编辑 ASG 可能造成漂移，而且扩缩配置更改不遵守 PDB。

对于 Karpenter/Auto Mode，应检查对应 NodePool/NodeClaim/provider 限制及事件。不能只因某个固定 CA Pod label 查不到对象，就建议安装 CA。VPA 处于 Off 和 Initial 模式可能是有意的。Auto 已弃用，建议使用 Recreate；更改模式可能中断工作负载，并会影响同时使用相同 CPU/内存信号的 HPA。

**Helm/Terraform 配置示例**

仅当现有 CA 和 Metrics Server 由 Helm 管理时使用。提供经审查的 chart 版本，以及兼容集群次版本的 CA 镜像版本；chart 默认镜像可能落后于目标版本。每个组件只保留一个所有者。

```hcl
# Existing Helm-owned installations only; supply reviewed compatible versions.
# The IRSA trust subject must match kube-system:cluster-autoscaler.
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = var.ca_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  values = [yamlencode({
    autoDiscovery = { clusterName = var.cluster_name }
    awsRegion     = var.aws_region
    image         = { tag = var.ca_image_tag }
    rbac = {
      serviceAccount = {
        create = true
        name   = "cluster-autoscaler"
        annotations = {
          "eks.amazonaws.com/role-arn" = var.ca_irsa_role_arn
        }
      }
    }
  })]
}

resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = var.metrics_server_chart_version
  namespace  = "kube-system"
  wait       = true
  timeout    = 600
  # Retain/migrate the existing owner's reviewed values.
  values = [file(var.metrics_server_values_file)]
}
```

这里的 values 文档兼容 Helm provider 3.x，不使用已移除的重复 `set {}` 写法。CA ServiceAccount 名称是显式值，必须匹配 IRSA trust subject；Pod Identity 是单独配置、单独管理的方案。该角色仍需具备[扩缩成本源指南](../../eks/07-eks-cost-optimization.md)所述的范围受限权限；不要把 AutoScalingFullAccess 当作通用修复而附加。

合并 Metrics Server 安装中实际经过审查的 values。当前上游 chart 默认采用安全的 kubelet 连接路径，并不意味着要用 `--kubelet-insecure-tls`。应先诊断证书/信任/地址问题，再考虑仅用于实验室的变通办法。若 EKS add-on 已拥有组件，不要再创建重复 Helm release。目标环境必须验证 chart/身份/网络/运行时兼容性；本次没有运行 Helm 安装。

**HPA 指标与行为**

此资源指标示例保留 CPU/内存和 scale-up/down 策略概念：

```yaml
# Example resource metrics and behavior; requires an existing target with requests.
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
  namespace: applications
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      selectPolicy: Max
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      selectPolicy: Min
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

利用率目标需要配置 requests。HPA 按各指标建议的副本数中最大值作选择；指标缺失/报错也可能阻止缩容。策略中的 Max/Min 用于选择允许的变更速率；稳定窗口并非一律固定的“冷却时间”。百分比、界限和窗口都只是示例，内存扩缩行为也未必与 CPU 相同。不要让 Terraform/GitOps 和其他扩缩器争相控制同一个副本数。

**仪表板示例**

针对已有的单集群 kube-prometheus-stack 布局：数据源 UID 为 `prometheus`，sidecar 监视 `monitoring` 中带 `grafana_dashboard=1` 标签的资源：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: autoscaling-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  autoscaling-dashboard.json: |
    {
      "uid": "eks-autoscaling-diagnostics",
      "title": "EKS Autoscaling Diagnostics",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "HPA replicas",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_current_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Current {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "B",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_status_desired_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Desired {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "C",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_min_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Min {{namespace}}/{{horizontalpodautoscaler}}"
            },
            {
              "refId": "D",
              "expr": "max by (namespace, horizontalpodautoscaler) (kube_horizontalpodautoscaler_spec_max_replicas{job=\"kube-state-metrics\"})",
              "legendFormat": "Max {{namespace}}/{{horizontalpodautoscaler}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Observed node count",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count(max by (node) (kube_node_info{job=\"kube-state-metrics\"}))",
              "legendFormat": "Nodes"
            }
          ]
        },
        {
          "id": 3,
          "title": "Pod CPU usage (cores)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "cores"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        },
        {
          "id": 4,
          "title": "Pod working set (bytes)",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 8
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "bytes"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace, pod) (max by (namespace, pod, container) (container_memory_working_set_bytes{job=\"kubelet\",metrics_path=\"/metrics/cadvisor\",container!=\"\",container!=\"POD\",image!=\"\"}))",
              "legendFormat": "{{namespace}}/{{pod}}"
            }
          ]
        }
      ]
    }
```

根据实际安装调整选择器/UID/命名空间。HPA 序列保留 namespace 身份；聚合前应去掉 exporter 重复数据。CPU 单位为核，内存是 working-set 字节数，而非百分比。多集群数据源需添加 cluster 维度/筛选器。抓取数据缺失时必须显示无数据/未知，不能显示为健康的零。仪表板不能证明扩缩成功，也不是告警/自动化流程。

A/B 可能暂时改变容量，但不能定位 controller/指标故障。D 会增加迁移风险，却不能用于诊断。记录预期与实际行为，以及哪项准确更改恢复了行为。

来源：[HPA 行为](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)、[AWS Cluster Autoscaler](https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/cloudprovider/aws/README.md)、[CA chart](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler/charts/cluster-autoscaler)、[Metrics Server](https://github.com/kubernetes-sigs/metrics-server)、[VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)。

</details>

### 7. NetworkPolicy 行为异常时，最有效的调查方法是什么？

- A. 删除所有 NetworkPolicy
- B. 检查实际 enforcement 实现、策略 selector/语义、日志和失败流量
- C. 给所有 Pod 设置 hostNetwork
- D. 重建 VPC

<details>
<summary>显示答案</summary>

**答案：B. 检查实际 enforcement 实现、策略 selector/语义、日志和失败流量**

声明的策略与执行策略的实现都要检查。只创建 NetworkPolicy 对象，不会自动安装策略执行引擎。

**盘点和语义**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,labels:.metadata.labels,owners:.metadata.ownerReferences,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,status:.status.phase}'
kubectl --context "$KUBE_CONTEXT" get namespace "$NAMESPACE" --show-labels
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get networkpolicies -o yaml
kubectl --context "$KUBE_CONTEXT" get daemonsets -A -o json \
  | jq '.items[] | {namespace:.metadata.namespace,name:.metadata.name,containers:[.spec.template.spec.containers[] | {name,image}]}'
```

Pod 列表为空时，kubectl 仍可能成功退出。不能把 `if kubectl get pods -l ...` 当作安装了 VPC CNI、Calico 或 Cilium 的证明。应检查配置的所有者、实际对象/镜像、策略 agent 状态，以及支持的计算类型/kernel/版本。Auto Mode 使用内置 NodeClass 网络控制，不支持随意安装其他 CNI。

VPC CNI 支持原生策略。当前 AWS 指南区分标准启动模式（新 Pod 的规则配置期间先允许流量）和严格模式（初始拒绝，因此需配置所需 DNS/依赖路径）。检查实际策略 agent 容器和已启用的事件日志；不要沿用“VPC CNI 不支持策略”的过时说法。

对于标准的 networking.k8s.io/v1 NetworkPolicy，各策略允许的流量采用累加语义，没有规则优先级或后者覆盖前者的冲突解决。连接必须同时通过隔离源端的 egress 和目标端的 ingress。Admin/集群范围或厂商策略 API 语义不同，应另外考虑。HostNetwork 行为也取决于实现；给所有 Pod 设置它不是安全修复。

**受限策略示例**

以下两个文档用 `---` 分隔对象。假设已有后端命名空间、前端 web Pod、数据库 Pod 和传统 CoreDNS Pod endpoint：

```yaml
# Independent example for a reviewed backend namespace and traditional CoreDNS Pods.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: backend
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: backend
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: frontend
          podSelector:
            matchLabels:
              app: web
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: database
          podSelector:
            matchLabels:
              app: db
      ports:
        - protocol: TCP
          port: 5432
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

命名空间与 Pod selector 位于**同一个 peer**，因此两者都必须匹配。分成多个 peer 才是 OR。命名空间名称使用标准的 kubernetes.io/metadata.name 标签；不要假设存在自定义 `name` 标签。

默认拒绝策略选中所有后端 Pod；只有选中的 API Pod 获得上面显示的例外。其他后端工作负载及 API 依赖需要单独审查放行规则。这不会配置前端 egress 或数据库 ingress。DNS 规则目标是 CoreDNS Pod，并非通用 Auto Mode/NodeLocal resolver 路径。

使用适当的所有者管理的测试工作负载，测试允许的 frontend-web→API:8080 路径、错误命名空间/标签/端口的拒绝路径、API→database:5432，以及实际 DNS 路径。新建但未带标签的调试 Pod，其策略可能与受影响 Pod 不同；ping 单独不能证明 TCP/UDP 策略。经授权的抓包应限定到目标网络命名空间/流量和时长；单独的 tcpdump Pod 无法观察其他所有 Pod。

**Terraform 方案**

```hcl
# Alternative owner for the same policy intent; do not also apply duplicate YAML.
resource "kubernetes_network_policy_v1" "default_deny" {
  metadata {
    name      = "default-deny"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}
resource "kubernetes_network_policy_v1" "api" {
  metadata {
    name      = "api-allow"
    namespace = var.backend_namespace
  }
  spec {
    pod_selector {
      match_labels = { app = "api" }
    }
    policy_types = ["Ingress", "Egress"]
    ingress {
      from {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "frontend" }
        }
        pod_selector {
          match_labels = { app = "web" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "8080"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "database" }
        }
        pod_selector {
          match_labels = { app = "db" }
        }
      }
      ports {
        protocol = "TCP"
        port     = "5432"
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        protocol = "UDP"
        port     = "53"
      }
      ports {
        protocol = "TCP"
        port     = "53"
      }
    }
  }
}
```

只使用一个所有者，并在隔离环境审查/应用完整流量矩阵。当前 Kubernetes provider 字段已做本地检查，但本次审计没有应用策略，也没有测试流量 enforcement。安装未固定版本的 Calico/Cilium，或只修改 aws-node 镜像，都不是通用策略修复；应遵循当前实现支持的升级/迁移流程。

**盘点数据不等于 enforcement 证据**

原先的 `kube_networkpolicy_info`/`calico_denied_packets` 示例不能证明这些指标确实存在或带有假设中的标签。当前 kube-state-metrics 文档说明了实验性的 created/ingress-rule/egress-rule gauges。在现有单集群 scrape 布局及 Grafana sidecar 中，此 ConfigMap 展示声明式清单：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: network-policy-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  network-policy-dashboard.json: |
    {
      "uid": "eks-network-policy-inventory",
      "title": "Declared NetworkPolicy Inventory",
      "schemaVersion": 39,
      "version": 1,
      "timezone": "utc",
      "refresh": "30s",
      "time": {
        "from": "now-1h",
        "to": "now"
      },
      "panels": [
        {
          "id": 1,
          "title": "Declared policies by namespace",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 0,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "count by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_created{job=\"kube-state-metrics\"}))",
              "legendFormat": "{{namespace}}"
            }
          ]
        },
        {
          "id": 2,
          "title": "Declared ingress/egress rule counts",
          "type": "timeseries",
          "gridPos": {
            "h": 8,
            "w": 12,
            "x": 12,
            "y": 0
          },
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "fieldConfig": {
            "defaults": {
              "unit": "short"
            },
            "overrides": []
          },
          "targets": [
            {
              "refId": "A",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_ingress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Ingress {{namespace}}"
            },
            {
              "refId": "B",
              "expr": "sum by (namespace) (max by (namespace, networkpolicy) (kube_networkpolicy_spec_egress_rules{job=\"kube-state-metrics\"}))",
              "legendFormat": "Egress {{namespace}}"
            }
          ]
        }
      ]
    }
```

确认确实暴露这些实验性指标，并调整 job/UID/namespace selector。零条规则可能表示全拒绝；策略/规则数量既不衡量连接丢弃，也不能证明 enforcement。遥测缺失时状态是未知，不是健康的零值。要获得拒绝/允许证据，应查看实际实现启用的决策日志/流量可观测性，并验证已发布的标签/schema；不要编造计数器，也不要把每条包含 “policy” 的日志都当成拒绝。

删除策略、对所有工作负载启用 hostNetwork 或重建 VPC，可能扩大暴露面，却找不到原因。保留失败流量证据，只更改已确认有问题的策略/配置。

来源：[Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)、[VPC CNI 策略](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)、[Auto Mode 网络](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[kube-state-metrics 策略指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/policy/networkpolicy-metrics.md)。

</details>

### 8. 遇到 Helm 部署问题时，最有效的做法是什么？

- A. 删除所有 Helm release
- B. 重建 EKS 集群
- C. 检查客户端/chart/依赖配置、release 所有权、权限、事件和工作负载行为
- D. 放弃 release 管理并改用手工对象

<details>
<summary>显示答案</summary>

**答案：C. 检查客户端/chart/依赖配置、release 所有权、权限、事件和工作负载行为**

分别检查客户端/chart 错误、Kubernetes admission/权限、工作负载就绪情况和应用行为。Helm 2/Tiller 属于历史迁移问题；当前 Helm 3/4 操作不需要部署 Tiller。

**检查实际 release**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${RELEASE_NAME:?}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
HELM_EVIDENCE=$(mktemp -d "$EVIDENCE_PARENT/helm-diagnosis.XXXXXXXX")
helm version --short
helm status "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm history "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT"
helm get values "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  --all > "$HELM_EVIDENCE/values.yaml"
helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" --kube-context "$KUBE_CONTEXT" \
  > "$HELM_EVIDENCE/manifest.yaml"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get events \
  --sort-by='.metadata.creationTimestamp' > "$HELM_EVIDENCE/events.txt"
printf 'Review protected evidence in %s\n' "$HELM_EVIDENCE"
```

查询失败可能是权限/网络/context 问题，不代表 release 不存在。values 和渲染后的 manifest 可能包含凭证或 Secret 数据；应保护并在分享前脱敏。app.kubernetes.io/instance 等标签只是惯例，不能构成完整所有权清单。应检查 release manifest，确定准确资源，并检查其状况/事件。

Helm 客户端的 Kubernetes 身份，与 chart values 所选的工作负载 ServiceAccount 不同。当前没有 `helm install --service-account` 选项。使用 chart 文档所述的 ServiceAccount values，并检查实际操作者的 RBAC。模拟身份需要相应权限，而且不能重现 EKS access policy 的所有授权。

**更改前验证配置**

```bash
set -euo pipefail
: "${CHART_DIR:?}"; : "${VALUES_FILE:?}"; : "${KUBE_VERSION:?Set the target capability version}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
RENDER_DIR=$(mktemp -d "$EVIDENCE_PARENT/helm-render.XXXXXXXX")
# For charts with dependencies, first review/commit Chart.lock and build from that lock.
helm lint "$CHART_DIR" --values "$VALUES_FILE"
helm template review "$CHART_DIR" --namespace review \
  --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
  > "$RENDER_DIR/rendered.yaml"
```

渲染/lint 不能证明 server-side API/admission 兼容性、CRD 已安装、镜像可运行、工作负载就绪或应用测试通过。安装时加 `--debug` 仍会执行安装。`helm dependency update` 可能更改 lock/依赖版本选择；为确保可重复性，应使用已审查的 Chart.lock 和 `dependency build`。若没有 lock，build 可能重新解析依赖，不能称作锁定验证。

遇到资源冲突时，先确认现有所有者及预期迁移方案。不要自动卸载 release、删除遗留资源、使用 force/take-ownership 或换 release 名称。这些操作可能影响数据并创建重复 controller。对已有 release 升级前，应保留当前 values、schema/CRD 和有状态依赖。

**Terraform Helm provider 语义**

此示例针对本地检查过 schema 的 Helm provider 3.3，以及已经准备好 namespace/release 所有者的环境。使用配置了经审查 exec credential 流程的 kubeconfig，不要在耗时的 apply 中只使用一次性短期 token：

```hcl
# Choose the existing release/configuration owner and reviewed chart artifact.
variable "verify_chart_provenance" {
  type = bool
}
provider "helm" {
  debug = false
  kubernetes = {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}
resource "helm_release" "example" {
  name              = var.release_name
  repository        = var.chart_repository
  chart             = var.chart_name
  version           = var.chart_version
  namespace         = var.release_namespace
  create_namespace  = false
  values            = [file(var.reviewed_values_file)]
  dependency_update = false
  lint              = true
  wait              = true
  wait_for_jobs     = true
  timeout           = 600
  atomic            = true
  verify            = var.verify_chart_provenance
  keyring           = var.chart_keyring
}
```

`lint` 是**有效的** release 字段，计划阶段会运行 Helm lint。`debug` 属于 provider，不属于 helm_release。Provider 3.x 使用嵌套 values 属性，例如 `set = [...]`；上面的 values-file 形式避免重复使用旧式 set blocks。

`verify` 用受信 keyring 检查 chart 包的来源证明，**不**运行 Helm test hook。仅在具备实际来源/信任配置且验证了相应分发方式时才启用它。`wait_for_jobs` 和 `wait` 等待就绪/Job，并不等于完成所有应用测试。`atomic` 提供 Helm 安装失败清理/升级回滚，不会恢复数据库/PVC 数据，也不会自动撤销每个 hook/CRD/外部副作用。

`set_sensitive` 只会在展示时隐藏内容，并不会让普通 state/release 中保存的值适合公开。应优先引用单独管理的 Secret，并保护 Terraform state 和 Helm release 存储。本次审查未运行 provider apply 或安装 release。

**Chart 测试 hook**

Chart 必须定义 `my-chart.fullname`、使用该 Service 名称并开放配置的 HTTP 路径。以下是两个**独立的模板文件**以及一个 values 片段：

```yaml
# Relevant values fragment for the chart that owns the Service.
service:
  port: 80
tests:
  enabled: true
  image: docker.io/library/busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662
  apiPath: /api/health
```

保存为 `templates/tests/test-connection.yaml`：

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-connection" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v/" (include "my-chart.fullname" .) .Values.service.port | quote }}
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
{{- end }}
```

保存为 `templates/tests/test-api.yaml`：

```yaml
{{- if .Values.tests.enabled }}
apiVersion: v1
kind: Pod
metadata:
  name: {{ printf "%s-test-api" (include "my-chart.fullname" .) | quote }}
  namespace: {{ .Release.Namespace | quote }}
  labels:
    app.kubernetes.io/component: test
  annotations:
    helm.sh/hook: test
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  restartPolicy: Never
  activeDeadlineSeconds: 60
  automountServiceAccountToken: false
  nodeSelector:
    kubernetes.io/os: linux
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: {{ .Values.tests.image | quote }}
      command: [wget]
      args:
        - "-T"
        - "5"
        - "-q"
        - "-O-"
        - {{ printf "http://%s:%v%s" (include "my-chart.fullname" .) .Values.service.port .Values.tests.apiPath | quote }}
      resources:
        requests:
          cpu: 10m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 64Mi
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
{{- end }}
```

测试标签有意不复制应用 selector 标签。探针把响应写入 stdout，不使用 Kubernetes API token，并限制请求/Pod 生命周期。before-hook-creation 允许重复测试；日志结果保留到下次运行/清理所属资源时。HTTP 检查不能验证所有业务行为；`/api/health` 必须确实存在。

对于已经准备好的隔离测试集群，使用明确的 release/namespace 名称：

```bash
set -euo pipefail
: "${TEST_CONTEXT:?Set the owned disposable cluster context}"
: "${TEST_NAMESPACE:?Choose a new unique namespace}"
: "${TEST_RELEASE:?}"; : "${CHART_DIR:?}"; : "${VALUES_FILE:?}"
# Fails on an existing namespace rather than adopting it.
TEST_NAMESPACE_UID=$(kubectl --context "$TEST_CONTEXT" create namespace "$TEST_NAMESPACE" \
  -o jsonpath='{.metadata.uid}')
printf 'Test namespace: %s UID: %s\n' "$TEST_NAMESPACE" "$TEST_NAMESPACE_UID"
helm install "$TEST_RELEASE" "$CHART_DIR" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --values "$VALUES_FILE" --wait --timeout 5m
helm test "$TEST_RELEASE" --kube-context "$TEST_CONTEXT" \
  --namespace "$TEST_NAMESPACE" --logs --timeout 90s
```

失败时应保留资源，并检查 hook/工作负载日志。记录 namespace UID，清理该测试命名空间前再次核实；不要删除预先存在的命名空间。旧的、没有 change triggers 的 null_resource 并不能保证每次 release 更改后重新验证。

**静态 CI 示例**

此 workflow 使用已提交的依赖/Chart.lock 和不含 Secret 的 `ci/values.yaml` 检查 chart。调整 chart 路径和目标 capability 版本。不含依赖项的 chart 应省略 lock/build 步骤。此 workflow 不会创建集群，也不声称运行时测试已通过：

```yaml
name: Static Helm chart validation
on:
  pull_request:
    paths:
      - charts/**
      - ci/values.yaml
      - .github/workflows/helm-validate.yml
permissions:
  contents: read
jobs:
  lint-render:
    runs-on: ubuntu-24.04
    env:
      CHART_DIR: charts/my-chart
      VALUES_FILE: ci/values.yaml
      KUBE_VERSION: "1.36.0"
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: Azure/setup-helm@9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310 # v5.0.1
        with:
          version: v3.21.3
      - name: Build reviewed dependencies, lint and render
        shell: bash
        run: |
          set -euo pipefail
          umask 077
          test -f "$CHART_DIR/Chart.lock"
          helm dependency build "$CHART_DIR"
          helm lint "$CHART_DIR" --values "$VALUES_FILE"
          helm template chart-ci "$CHART_DIR" --namespace chart-ci \
            --kube-version "$KUBE_VERSION" --values "$VALUES_FILE" \
            > "$RUNNER_TEMP/chart-rendered.yaml"
```

setup action/release 的固定版本已根据官方元数据检查。需要时，应在自有的一次性环境中单独运行集成/test-hook 阶段。使用 chart-testing 时，应采用它报告的 release/namespace 和 test 选项；chart 目录名并不保证之后 `helm test` 循环可用。

删除所有 chart、重建 EKS 或放弃 release manager，都无法诊断原始 chart/权限/运行时问题。

来源：[Helm 调试](https://helm.sh/docs/chart_template_guide/debugging/)、[Chart 测试](https://helm.sh/docs/topics/chart_tests/)、[Helm provider release](https://registry.terraform.io/providers/hashicorp/helm/latest/docs/resources/release)、[setup-helm release](https://github.com/Azure/setup-helm/releases/tag/v5.0.1)、[Helm 3.21.3](https://github.com/helm/helm/releases/tag/v3.21.3)。

</details>

### 9. 如何区分内存泄漏与其他内存压力原因？

- A. 重启所有 Pod
- B. 只增大节点
- C. 关联内存/进程证据、限制、运行时 profile 与应用代码
- D. 只增加节点数

<details>
<summary>显示答案</summary>

**答案：C. 关联内存/进程证据、限制、运行时 profile 与应用代码**

working set 上升、容器 OOMKilled 或节点 MemoryPressure 本身都不能诊断为内存泄漏。选择修复方式前，应比较负载、进程生命周期/UID、heap/native memory、缓存和限制。

**收集可比较的证据**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${APP_SELECTOR:?Set an explicit label selector}"
: "${EVIDENCE_PARENT:?Set an existing private directory}"
umask 077
MEMORY_DIR=$(mktemp -d "$EVIDENCE_PARENT/memory-observation.XXXXXXXX")
for sample in {1..10}; do
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "$MEMORY_DIR/sample-$sample.time"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pods -l "$APP_SELECTOR" -o json \
    | jq '[.items[] | {
        name:.metadata.name,uid:.metadata.uid,created:.metadata.creationTimestamp,
        node:.spec.nodeName,phase:.status.phase,
        resources:[.spec.containers[] | {name,resources}],
        containers:((.status.initContainerStatuses // []) + (.status.containerStatuses // []))
      }]' > "$MEMORY_DIR/sample-$sample.pods.json"
  kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" top pods \
    -l "$APP_SELECTOR" --containers > "$MEMORY_DIR/sample-$sample.usage.txt"
  if [ "$sample" -lt 10 ]; then sleep 30; fi
done
printf 'Observations saved to %s; these samples do not establish a leak.\n' "$MEMORY_DIR"
```

该命令每隔 30 秒采集一次，共 10 次，大约符合原先的五分钟采样计划，另加命令执行时间。本次审计没有执行它。短时间窗口不能证明长期泄漏。查询失败会停止采集并留下部分证据；不要把缺失指标变成零用量。

使用明确标签，不要把 Pod 名称前缀当作标签值；使用 kubectl 对资源数量有正确处理的输出，而不是按不存在的第四列排序。Pod 快照记录 UID 以及普通/init 容器状态；替换后名称可能复用。指标与状态请求不是原子快照。检查当前/上次终止原因和重启次数，同时记住 status 只保留有限历史。

**解释内存压力**

- working set、RSS、托管 heap 和 native allocations 是不同测量值。缓存增长或流量增加也可能看起来像泄漏。
- 容器可能触及 cgroup 限制，而节点仍有可用内存。request/limit 差距大本身并非 OOM 原因。
- kubelet 是节点进程，不存在一个通用的 `kubelet-pod` 可供从 kube-system 读取日志。应通过受支持的节点/监控路径调查。
- 内存碎片只是待验证假设；定期重启节点或强制垃圾回收不是通用修复。

**当前指标与单位示例**

对于现有单集群 kube-prometheus-stack 抓取布局，以下规则使用当前容器级 limit 指标、去除 exporter 重复样本，并筛掉缺失/零限制：

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: memory-observation
  namespace: monitoring
  labels:
    release: observability
spec:
  groups:
  - name: memory-observation
    rules:
    - alert: ContainerWorkingSetHigh
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.85
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Container working set is above 85% of its declared limit
        description: Inspect {{ $labels.namespace }}/{{ $labels.pod }}/{{ $labels.container
          }} and actual termination/pressure evidence.
    - alert: ContainerWorkingSetCritical
      expr: max by (namespace, pod, container) (container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""})
        / on (namespace, pod, container) (max by (namespace, pod, container) (kube_pod_container_resource_limits{job="kube-state-metrics",resource="memory",unit="byte"})
        > 0) > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Container working set is above 95% of its declared limit
        description: This is an observation threshold, not proof of a leak or guaranteed
          OOM prediction.
    - alert: ContainerWorkingSetGrowth
      expr: max by (namespace, pod, container) (deriv(container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",container!="",container!="POD",image!=""}[30m]))
        > 5 * 1024 * 1024 / 60
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Estimated working-set slope exceeds 5 MiB/min
        description: The rolling 30-minute regression has stayed above the threshold;
          correlate with load and process lifetime.
    - alert: NodeMemoryPressure
      expr: max by (node) (kube_node_status_condition{job="kube-state-metrics",condition="MemoryPressure",status="true"})
        == 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Node {{ $labels.node }} reports MemoryPressure
        description: Investigate node resources and workloads; this is distinct from
          a container limit OOM.
```

按实际安装调整 namespace/release/job selector。规则使用普通容器限制；init 容器和 Pod 级预算需另行检查。没有报告正数 limit 的容器不会生成该比率；应单独监控覆盖率，不能把它们称作健康。working-set/limit 阈值只是观察值，并非 heap 泄漏探测器。

此处 `deriv` 返回**字节/秒**。将 `5 * 1024 * 1024` 除以 60，阈值才是**5 MiB/分钟**。旧表达式实际比较的是 5 MiB/s，文字却说每分钟。30 分钟回归窗口加上 `for: 30m` 持续期，并不能证明每个时刻都在单调增长。抓取缺失、重启和工作负载变化都会影响解释。

**运行时 profile 的前提**

| Runtime | 正确的调查范围 |
| --- | --- |
| JVM | 使用匹配的 JDK 工具/权限针对目标 JVM PID；`jcmd PID GC.heap_info` 是受支持的检查命令。native-memory 报告需要启动时启用相应跟踪。Heap dump 可能暂停进程并包含 Secret |
| Node.js | 使用目标进程支持的 inspector/profile 机制；启动 `node --inspect` 会创建新进程。限制调试器访问 |
| Python | 在实际应用或受控复现环境配置 profiler/tracemalloc。单独启动的解释器无法查看现有进程的分配情况；Python 分配跟踪也不包含全部 native RSS |
| Go | 采集实际且受保护的 heap profile，并使用匹配二进制/符号信息运行 pprof。不要假设存在未认证 profiling endpoint 或预先生成的 `/tmp/profile` |

在生产环境使用前，验证工具/runtime 版本和采集开销。不要把安装随意的 profiling package 到运行中的应用当作默认步骤。本次未运行 JVM、profiler、heap dump 或实时内存实验。

**应用配置示例**

原有的 256m/768m heap 和 1Gi 容器值仅作示例，并非测得的最优值。OpenJDK 21 会读取 JAVA_TOOL_OPTIONS；只有镜像 entrypoint 转发 JAVA_OPTS 时它才有效。命令行标志或 _JAVA_OPTIONS 可能覆盖这些设置，因此应验证 JVM 实际采用的选项。这些选项可能在 JVM 启动时打印，不要在其中放入 Secret。

```yaml
# Pod-template fragment for an existing reviewed OpenJDK 21 application container.
# Merge through its owner; this is not a standalone Deployment manifest.
spec:
  template:
    spec:
      containers:
        - name: java-app
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
              ephemeral-storage: 2Gi
            limits:
              cpu: "1"
              memory: 1Gi
              ephemeral-storage: 4Gi
          env:
            - name: JAVA_TOOL_OPTIONS
              value: >-
                -XX:+UseG1GC -XX:MaxGCPauseMillis=200
                -Xms256m -Xmx768m
                -XX:+HeapDumpOnOutOfMemoryError
                -XX:HeapDumpPath=/diagnostics
                -XX:+ExitOnOutOfMemoryError
          volumeMounts:
            - name: heap-diagnostics
              mountPath: /diagnostics
      volumes:
        - name: heap-diagnostics
          emptyDir:
            sizeLimit: 2Gi
```

保留应用实际 image、启动行为、其他环境变量/卷和安全上下文。确认其 UID 可以写入诊断挂载点。`MaxGCPauseMillis` 是软目标。Heap 只是进程内存的一部分；还应为 native allocation、线程、代码/metaspace 及其他开销留出经测量的空间。

磁盘型 emptyDir 有容量限制，但 Pod 删除后不持久。应谨慎采集/保护诊断文件，并考虑容器 PID 复用造成的文件名冲突。内核/cgroup 发送 SIGKILL 时，JVM 可能无法处理 heap dump。`ExitOnOutOfMemoryError` 处理 JVM 抛出的 OOM，但不能保证生成 dump，也无法解决分配根因。

旧的 MEMORY_MONITOR_* 变量并非 JVM/Kubernetes 内置功能。只有应用实际启用并公开 Spring Actuator liveness/readiness 路径时它们才适用；应依据应用真实的健康契约，而非假设这些 URL 可用。

**管理现有监控**

```hcl
# Prometheus Operator CRD must already exist before planning this resource.
# Save the reviewed PrometheusRule YAML above as the supplied file.
resource "kubernetes_manifest" "memory_alerts" {
  manifest = yamldecode(file(var.memory_rules_file))
}
```

Kubernetes manifest provider 在 plan 阶段需要 PrometheusRule CRD；用 `depends_on` 等待同一 apply 中 Helm 安装完成，并不能通用地解决 schema discovery。复用现有监控栈和问题 6 中可用的 working-set 面板；不要再安装一个监控栈，也不要引用来历不明的仪表板文件。在真实环境确认 rule 选择、告警路由和遥测健康。

A/B/D 可能临时缓解容量，却不能确认或修复分配缺陷。记录已证实的原因，并在有代表性的负载下验证实际代码/配置修正。

来源：[Prometheus deriv](https://prometheus.io/docs/prometheus/latest/querying/functions/#deriv)、[当前 Pod 指标](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)、[OpenJDK 21 选项处理](https://github.com/openjdk/jdk21u/blob/master/src/hotspot/share/runtime/arguments.cpp)、[Java 21 选项](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)、[jcmd](https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html)。

</details>

### 10. EKS DNS 解析失败时，最有效的调查方式是什么？

- A. 为所有 Pod 分配静态 IP
- B. 追踪实际 Pod resolver、DNS 实现、策略/传输和上游配置
- C. 对所有 Service 使用 ExternalName
- D. 重建 VPC

<details>
<summary>显示答案</summary>

**答案：B. 追踪实际 Pod resolver、DNS 实现、策略/传输和上游配置**

从受影响 Pod 的 resolver 和失败名称入手。区分工具缺失、DNS 响应、UDP/TCP 传输、上游/私有区配置以及应用缓存。

**检查实际 Pod 路径**

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"; : "${NAMESPACE:?}"; : "${POD_NAME:?}"; : "${CONTAINER_NAME:?}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod "$POD_NAME" -o json \
  | jq '{name:.metadata.name,uid:.metadata.uid,node:.spec.nodeName,hostNetwork:.spec.hostNetwork,dnsPolicy:.spec.dnsPolicy,dnsConfig:.spec.dnsConfig}'
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- cat /etc/resolv.conf
# Run only where the selected container actually has this diagnostic tool.
: "${DNS_TEST_NAME:?Set the actual Service FQDN or reviewed external name}"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$POD_NAME" \
  -c "$CONTAINER_NAME" -- nslookup "$DNS_TEST_NAME"
```

镜像中没有 cat/nslookup 是工具限制，不代表 DNS 故障。应使用能保留相关 Pod 网络/身份上下文的预备诊断方式。新建 debug Pod 的标签、策略和 DNS 可能不同。测试 resolver 传输时，直接使用 nameserver IP，不要依赖 DNS 解析 DNS server 自己的 Service 名称。按需检查 UDP/TCP 53；只有 TCP 连接测试不能验证 DNS 响应。

对于传统 CoreDNS，检查 Deployment 就绪状态、Service/EndpointSlices、配置和日志：

```bash
set -euo pipefail
: "${KUBE_CONTEXT:?}"
# Traditional CoreDNS path only; pure Auto Mode node DNS is different.
kubectl --context "$KUBE_CONTEXT" -n kube-system get deployment coredns
kubectl --context "$KUBE_CONTEXT" -n kube-system get pods -l k8s-app=kube-dns -o wide
kubectl --context "$KUBE_CONTEXT" -n kube-system get service kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get endpointslices \
  -l kubernetes.io/service-name=kube-dns
kubectl --context "$KUBE_CONTEXT" -n kube-system get configmap coredns -o yaml
kubectl --context "$KUBE_CONTEXT" -n kube-system logs -l k8s-app=kube-dns \
  --all-containers=true --prefix=true --since=15m --tail=100
```

**Auto Mode 节点以系统服务方式运行 CoreDNS。** 纯 Auto Mode 可能没有传统 Deployment；混合集群必须为非 Auto 节点保留它。不要在所有集群中都把 Deployment 缺失诊断成故障，也不要在 Auto Mode 上再安装一个 node-local DNS 服务。

**Resolver 配置与策略**

如果 Pod 需要集群 DNS，ClusterFirst 是常见路径。有意配置 hostNetwork 的 Pod 通常需用 ClusterFirstWithHostNet。仅为了修复 DNS 而设置 hostNetwork 会改变隔离方式，不是通用补救。DNSPolicy None 要求完整而有意配置 resolver。

旧的 `169.254.20.10` 示例是指定的 NodeLocal DNSCache 地址，不是通用 VPC resolver。像 `8.8.8.8` 这样的公共 resolver 不提供 Kubernetes Service 区域/私有 AWS 名称解析；配置多个 nameserver 也不保证按区域回退。应检查真正的 CoreDNS/NodeLocal 上游及集群域名，不要硬编码 `172.20.0.10` 或公共备用地址。

对于标准 CoreDNS Pod，以下示例仅允许选定后端访问 DNS。应用前应审查其他所有出站流量：

```yaml
# Example for application Pods using traditional CoreDNS Pod endpoints.
# This selects applications and isolates other egress unless another policy allows it.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-dns-egress
  namespace: applications
spec:
  podSelector:
    matchLabels:
      app: example
  policyTypes:
    - Egress
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

源端 egress 和目标端 ingress 可能都需要许可。同一个 peer 中的 namespace 和 Pod selector 通过 AND 组合。Auto Mode/NodeLocal 路径需要按各自实现处理；不要假设 Pod 标签选择器能选中主机级缓存。单独的 tcpdump Pod 无法捕获其他工作负载的查询；应在相应上下文中执行经授权、范围受限的抓包。

**正确读取 VPC DNS 设置**

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
VPC_ID=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query cluster.resourcesVpcConfig.vpcId --output text)
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id "$VPC_ID" --region "$AWS_REGION" \
  --attribute enableDnsHostnames
DHCP_OPTIONS_ID=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$AWS_REGION" \
  --query 'Vpcs[0].DhcpOptionsId' --output text)
aws ec2 describe-dhcp-options --dhcp-options-ids "$DHCP_OPTIONS_ID" --region "$AWS_REGION"
```

DNS 属性来自 DescribeVpcAttribute，而不是 DescribeVpcs 的字段。集群名称和 Region 必须明确指定；任意 kubeconfig alias 不能安全拆解为集群名称。运行这些查询前应核实账号/context。更改共享 VPC 设置前，应检查 DHCP options、DNS 路由/转发和私有 zone；创建并关联新的 DHCP option set 不是通用修复办法。

**CoreDNS 配置与所有权**

对于 EKS 管理的现有 CoreDNS add-on，检查版本/配置及经审查候选的 schema：

```bash
set -euo pipefail
: "${CLUSTER_NAME:?}"; : "${AWS_REGION:?}"
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --addon-name coredns --output json
: "${COREDNS_ADDON_VERSION:?Select a reviewed compatible candidate}"
aws eks describe-addon-configuration --addon-name coredns \
  --addon-version "$COREDNS_ADDON_VERSION" --region "$AWS_REGION" --output json
```

保留自定义 zone/forwarder，并使 health/ready plugin 匹配实际 probe。副本数、CPU/内存、PDB、放置与自动扩缩都需要结合工作负载审查；旧的 3 副本/70Mi/170Mi 示例不是普遍最优配置。不要用旧 EKS-Distro 1.8.7 镜像替换所属 Deployment，也不要把通用 Corefile 覆盖本地自定义项。

Terraform 所有者可以管理现有 add-on 并检查现有 VPC：

```hcl
# Existing EKS-managed CoreDNS for standard/mixed clusters only.
# Preserve/import the existing resource; do not duplicate its ownership.
resource "aws_eks_addon" "coredns" {
  cluster_name                = var.cluster_name
  addon_name                  = "coredns"
  addon_version               = var.reviewed_coredns_version
  configuration_values        = file(var.complete_reviewed_coredns_config)
  resolve_conflicts_on_create = "NONE"
  resolve_conflicts_on_update = "PRESERVE"
}

# Read an existing VPC; do not add a second aws_vpc resource to repair DNS.
data "aws_vpc" "cluster" {
  id = var.cluster_vpc_id
}
output "vpc_dns_attributes" {
  value = {
    enable_dns_support   = data.aws_vpc.cluster.enable_dns_support
    enable_dns_hostnames = data.aws_vpc.cluster.enable_dns_hostnames
  }
}
```

完整配置文件必须按选定 add-on schema 和当前设置进行验证。PRESERVE 并不保证显式 payload 会完整合并。遵循 [EKS 升级](../../eks/08-eks-upgrades.md)中的准确更新步骤，并在之后验证实际 DNS 行为。此示例不会配置 Auto Mode 的节点 DNS，也不授权替换共享 VPC。

**受支持标准节点环境中的可选 NodeLocal DNSCache**

使用[官方安装指南](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)和经审查发布的 manifest。过去手写的 DaemonSet 不完整；只改镜像并不能补齐所有接口、过滤规则、挂载、上游 Service 和 kubelet 配置。

| 决策 | 必需准备 |
| --- | --- |
| 本地地址 | 选择不冲突的 node-local IP 和实际集群域名/CoreDNS Service IP；考虑 IPv6 地址/端口写法 |
| 现有数据平面 | 文档化的 iptables 路径中，缓存监听本地 IP 和 CoreDNS Service IP。受支持的 IPVS 设置中，它只监听本地 IP，且必须更改 kubelet 集群 DNS 配置。其他模式应遵循各自当前集成指南 |
| Manifest/配置 | 渲染文档中的占位符，保留必需权限/接口/过滤/锁文件挂载、探针和上游配置。不要替换成不完整的旧 DaemonSet |
| 工作负载迁移 | 确保节点/kubelet 设置与新旧 Pod resolver 行为一致；分阶段 rollout，并同时规划撤销缓存与 kubelet 更改 |
| 内存/运维 | 根据查询/缓存/并发观察结果调整容量，监控故障并在重启/rollout 期间维持 DNS |

NodeLocal DNSCache 会把缓存未命中的查询转发给适当上游；它不能让每次查询都命中本地缓存。官方指南指出，OOM 终止可能导致包过滤规则仍指向不可用的本地缓存，直至其重启，从而中断 DNS。设置很小的固定内存 request 或增加缓存，都不能自动保证性能。

本次审查没有执行 DNS 查询、抓包、CoreDNS 更新、NodeLocal 安装或 Terraform apply。在受控环境中验证所选拓扑与假设。

静态 Pod IP、对所有 Service 使用 ExternalName 或重建 VPC，都无法确定 resolver 路径在哪里失败。记录实际查询/响应、来源上下文、配置更改及恢复证据。

来源：[EKS CoreDNS](https://docs.aws.amazon.com/eks/latest/userguide/managing-coredns.html)、[Auto Mode DNS](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)、[Pod DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)、[VPC DNS](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-dns.html)、[NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/)。

</details>
