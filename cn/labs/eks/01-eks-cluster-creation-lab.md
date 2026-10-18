# EKS 集群创建实验指南

> **难度**：中级
> **预计时间**：60–90 分钟；配置和删除所需时间因情况而异
> **最后更新**：September 12, 2026

## 学习目标

- 使用 eksctl 创建专用 EKS 集群。
- 在更改资源前，验证 AWS 账户和集群身份。
- 检查节点，部署示例应用并进行扩缩容。
- 删除实验资源并检查是否有未完成的清理工作。

## 先决条件

- [ ] 已获批准的 AWS 实验账户和临时角色凭证，例如通过 IAM Identity Center 获取。请让管理员为此配置批准所需的 EKS、EC2、CloudFormation、IAM/PassRole 及相关权限；不要仅为了本指南创建长期 IAM 用户或授予 AdministratorAccess。
- [ ] AWS CLI v2、eksctl、kubectl、Bash、Python 3、jq 和 curl。
- [ ] 已获批准的公共 IPv4 客户端 CIDR，通常为你当前工作站的出站地址 `/32`。生成器会拒绝比 `/24` 更宽的范围；如有要求，请遵守组织规定的更窄范围。
- [ ] 已完成 [EKS 集群创建](../../eks/02-eks-cluster-creation-part1.md)。

本实验使用 EKS 1.36 托管节点组。在审查日期，AWS 将 1.36 列为标准支持版本；先前示例中的 1.31 已进入扩展支持。运行本实验前，请查看当前 AWS 支持日历。使用与 API server 版本差距不超过一个次版本的 kubectl；本示例优先使用 1.36。

示例已使用 eksctl 0.229.0 和 kubectl 1.36.2，通过 schema 和本地 mock 进行检查。**本次审计未配置集群或测量部署时间。**账户权限、配额、实例可用性和网络访问仍需在你的实验账户中验证。

EKS、EC2、EBS、NAT gateway 和数据传输都会产生费用。此配置创建带有一个 NAT gateway 的私有节点；这是实验环境的成本/可用性选择，并非生产环境的可用性设计。`STANDARD` 支持策略允许后续自动升级版本，以避免进入扩展支持；它不会停止集群或停止产生其他费用。

请在专用 Bash 终端（**终端 A**）中按顺序运行命令。保留打印出的私有实验目录，不要提交其中的 kubeconfig 或身份记录。后续命令依赖该目录中的变量和函数。

## 练习 1：工具和账户

### 1.1 检查工具

```bash
aws --version
eksctl version
kubectl version --client
python3 --version
jq --version
```

### 1.2 设置目标账户和客户端网段

在运行此代码块前，将 `EXPECTED_ACCOUNT_ID` 和 `CLIENT_CIDR` 设置为已获批准的值。不要复制示例账户 ID 或仅供文档使用的 IP 地址。`AWS_REGION` 默认为首尔；两个区域变量会保持一致。

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended 12-digit lab account ID}"
: "${CLIENT_CIDR:?Set your approved public client IPv4 CIDR, usually a /32}"
export AWS_REGION="${AWS_REGION:-ap-northeast-2}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export EXPECTED_ACCOUNT_ID CLIENT_CIDR
umask 077
export LAB_DIR
LAB_DIR=$(mktemp -d "$PWD/eks-lab.XXXXXXXX")
export LAB_RUN_ID
LAB_RUN_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
export CLUSTER_NAME="eks-lab-$LAB_RUN_ID"
export KUBECONFIG="$LAB_DIR/kubeconfig"
printf 'Private lab directory: %s\nCluster: %s\nRegion: %s\n' "$LAB_DIR" "$CLUSTER_NAME" "$AWS_REGION"
```

配置生成器会验证这些输入，并在创建前记录目标集群：

```bash
python3 - <<'PY'
import ipaddress, json, os, re
from pathlib import Path
account = os.environ["EXPECTED_ACCOUNT_ID"]
region = os.environ["AWS_REGION"]
name = os.environ["CLUSTER_NAME"]
run_id = os.environ["LAB_RUN_ID"]
network = ipaddress.ip_network(os.environ["CLIENT_CIDR"], strict=True)
if not re.fullmatch(r"\d{12}", account):
    raise SystemExit("Expected a 12-digit account ID")
if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid Region")
if not re.fullmatch(r"eks-lab-[0-9a-f]{12}", name) or name != "eks-lab-" + run_id:
    raise SystemExit("Unexpected lab name")
if network.version != 4 or network.prefixlen < 24:
    raise SystemExit("Use a reviewed narrow IPv4 CIDR (/24 or narrower); never 0.0.0.0/0")
config = {
    "apiVersion": "eksctl.io/v1alpha5", "kind": "ClusterConfig",
    "metadata": {"name": name, "region": region, "version": "1.36",
                 "tags": {"content-lab-id": run_id}},
    "accessConfig": {"authenticationMode": "API"},
    "upgradePolicy": {"supportType": "STANDARD"},
    "vpc": {"clusterEndpoints": {"publicAccess": True, "privateAccess": True},
            "publicAccessCIDRs": [str(network)], "nat": {"gateway": "Single"}},
    "managedNodeGroups": [{
        "name": "workers", "instanceType": "t3.medium", "amiFamily": "AmazonLinux2023",
        "desiredCapacity": 2, "minSize": 1, "maxSize": 3,
        "privateNetworking": True, "volumeSize": 20, "volumeType": "gp3",
        "volumeEncrypted": True
    }]
}
directory = Path(os.environ["LAB_DIR"])
(directory / "cluster.json").write_text(json.dumps(config, indent=2) + "\n")
(directory / "lab-state.json").write_text(json.dumps({
    "account": account, "region": region, "cluster": name, "labId": run_id
}, indent=2) + "\n")
PY
```

```bash
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text)
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf '%s\n' 'Account mismatch; stop.' >&2; return 1; }
}
check_account
aws sts get-caller-identity --region "$AWS_REGION"
```

返回的账户必须与 `EXPECTED_ACCOUNT_ID` 匹配；临时凭证使用的假定角色 ARN 属于正常情况。如果不匹配或身份验证失败，请停止操作。

## 练习 2：创建并识别集群

### 2.1 检查配置

```bash
cat "$LAB_DIR/cluster.json"
```

此配置选择 EKS 1.36、基于 API 的访问条目、两个 `t3.medium` 托管节点、AL2023、加密的 20 GiB gp3 节点磁盘，以及唯一的 `content-lab-id` 标签。两个 API 端点均已启用：节点使用私有访问，公共端点则仅允许已获批准的客户端 CIDR。节点仍需要出站访问镜像/软件包端点。

### 2.2 创建集群

下一条命令会创建产生费用的资源。请为创建和清理预留充足时间；45 分钟超时是等待时限，不代表操作一定会在该时限内完成。

```bash
# MUTATION: creates billed CloudFormation/EKS/VPC/NAT/EC2/EBS resources.
check_account
eksctl create cluster --config-file "$LAB_DIR/cluster.json" \
  --write-kubeconfig=false --timeout=45m
```

如果创建失败或中断，**不要启动另一个随机命名的集群，也不要不加判断地运行常规清理代码块**。保留 `lab-state.json` 和 `cluster.json`，检查命名的 CloudFormation 堆栈，并先核对其标签、账户和资源。CLI 返回失败并不能证明没有创建任何资源；未解决的资源可能会继续产生费用。

### 2.3 保存身份信息和私有 kubeconfig

仅在创建成功后运行此步骤。上面的 `--write-kubeconfig=false` 不会改动你常用的 kubeconfig；以下命令只会写入专用的实验路径。

```bash
check_account
aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --query 'cluster.{arn:arn,createdAt:createdAt,endpoint:endpoint,tags:tags}' \
  --output json > "$LAB_DIR/cluster-identity.json"
jq -e --arg id "$LAB_RUN_ID" '.tags["content-lab-id"] == $id' "$LAB_DIR/cluster-identity.json"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
```

定义一个保护函数，在后续更改前检查账户、集群 ARN、创建时间、所有权标签和 kubeconfig 端点：

```bash
check_lab() {
  check_account || return
  local current endpoint
  current=$(aws eks describe-cluster --region "$AWS_REGION" --name "$CLUSTER_NAME" --output json) || return
  jq -e --arg id "$LAB_RUN_ID" --slurpfile saved "$LAB_DIR/cluster-identity.json" '
    .cluster.arn == $saved[0].arn and
    .cluster.createdAt == $saved[0].createdAt and
    .cluster.tags["content-lab-id"] == $id and
    .cluster.endpoint == $saved[0].endpoint
  ' <<<"$current" >/dev/null || { printf '%s\n' 'Cluster identity mismatch; stop.' >&2; return 1; }
  endpoint=$(kubectl --kubeconfig "$KUBECONFIG" --context "$CLUSTER_NAME" config view --minify \
    -o jsonpath='{.clusters[0].cluster.server}') || return
  jq -e --arg endpoint "$endpoint" '.endpoint == $endpoint' "$LAB_DIR/cluster-identity.json" >/dev/null ||
    { printf '%s\n' 'Kubeconfig endpoint mismatch; stop.' >&2; return 1; }
}
check_lab
```

### 验证

```bash
check_lab
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes -o wide
kubectl --context "$CLUSTER_NAME" wait node --selector=eks.amazonaws.com/nodegroup=workers \
  --for=condition=Ready --timeout=300s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/nodegroup=workers -o json |
  jq -e '(.items | length) == 2 and all(.items[];
    any(.status.conditions[]; .type == "Ready" and .status == "True"))'
```

两个节点都应处于 Ready 状态。如果注册的节点少于两个，请检查节点组和 CloudFormation 事件；控制平面创建成功并不能证明工作节点运行正常。

## 练习 3：探索集群

从已验证的节点列表中选择一个 `NODE_NAME`，并在运行此代码块前设置它。本实验使用常规托管节点，因此其系统组件视图与纯 Auto Mode 集群有所不同。

```bash
check_lab
: "${NODE_NAME:?Choose a node name from the preceding list}"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s describe node "$NODE_NAME"
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get pods
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n kube-system get services
# Run separately; preserve the actual error if the metrics API is unavailable.
if ! kubectl --context "$CLUSTER_NAME" --request-timeout=15s top nodes; then
  printf 'Metrics query failed; inspect the error and metrics API status.\n' >&2
fi
```

`kubectl top` 需要 metrics API。失败可能表示缺少 metrics-server、指标不可用、RBAC 或连接问题。请保留实际错误并进行诊断，不要据此断定 metrics-server 不存在。

## 练习 4：部署并扩缩容应用

### 4.1 部署 nginx

此 Deployment 配置了明确的资源请求/限制和就绪探针。Service 类型为 `ClusterIP`；本练习不会安装负载均衡控制器，也不会分配公共负载均衡器。

```bash
cat > "$LAB_DIR/app.yaml" <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  namespace: eks-lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      containers:
      - name: nginx
        image: nginx:1.30.6
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 128Mi
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nginx
  namespace: eks-lab
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
YAML
```

```bash
# MUTATION in the verified dedicated lab cluster.
check_lab
kubectl --context "$CLUSTER_NAME" create namespace eks-lab
kubectl --context "$CLUSTER_NAME" label namespace eks-lab "content-lab-id=$LAB_RUN_ID"
kubectl --context "$CLUSTER_NAME" apply -f "$LAB_DIR/app.yaml"
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
```

### 4.2 验证本地访问

在终端 A 中启动端口转发，然后在同一台工作站的**终端 B**中运行 curl 命令。监听器仅绑定到回环地址。端口转发连接会访问一个选定的 Pod；这并不代表对外部负载均衡或每个副本进行了测试。

```bash
# Keep this in Terminal A; it binds only loopback. Stop with Ctrl+C before continuing.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab port-forward service/nginx 8080:80 --address=127.0.0.1 || test "$?" -eq 130
```

```bash
# Terminal B on the same workstation; no AWS credentials are needed for this local URL.
curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  http://127.0.0.1:8080/ --output /dev/null --write-out 'HTTP %{http_code}\n'
```

成功的检查会打印 `HTTP 200`。继续操作前，请在终端 A 中按 Ctrl+C 停止前台端口转发。该命令允许此预期中断，同时保留其他失败检查。

### 4.3 扩缩容至四个副本

```bash
# MUTATION: after stopping port-forward in Terminal A.
check_lab
kubectl --context "$CLUSTER_NAME" -n eks-lab scale deployment/nginx --replicas=4
kubectl --context "$CLUSTER_NAME" -n eks-lab rollout status deployment/nginx --timeout=180s
kubectl --context "$CLUSTER_NAME" --request-timeout=15s -n eks-lab get deployment nginx -o json |
  jq -e '.spec.replicas == 4 and .status.observedGeneration >= .metadata.generation and
         .status.readyReplicas == 4 and .status.availableReplicas == 4'
```

如果还想练习公共 LoadBalancer，请先按照 [EKS 网络](../../eks/03-eks-networking-part1.md) 配置预期的控制器、IAM 权限和暴露设置。必须单独跟踪并移除相关资源及其费用；仅有已分配的主机名或 Deployment 就绪状态，并不能证明端到端负载均衡器运行正常。

## 清理

先停止端口转发。此代码块会删除带有实验标签的命名空间和专用集群。允许命名空间不存在；如果无法读取命名空间或其标签不匹配，则不会将其视为可安全删除。

```bash
# DESTRUCTIVE: only the verified dedicated lab resources.
check_lab
namespace_json=$(kubectl --context "$CLUSTER_NAME" --request-timeout=15s \
  get namespace eks-lab --ignore-not-found -o json)
if [ -n "$namespace_json" ]; then
  jq -e --arg id "$LAB_RUN_ID" '.metadata.labels["content-lab-id"] == $id' \
    <<<"$namespace_json" >/dev/null
  kubectl --context "$CLUSTER_NAME" delete namespace eks-lab --wait=true --timeout=180s
fi
check_lab
eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" --wait --timeout=45m
aws eks wait cluster-deleted --name "$CLUSTER_NAME" --region "$AWS_REGION"
# Keep private config/identity records until remaining resources/billing are checked.
```

必须使用 `--wait`，以便发现删除失败。EKS 删除等待器确认控制平面对象已消失，但不能确认所有依赖资源或费用都已消失。请检查保存的实验对应的 CloudFormation 堆栈状态，以及任何仍然存在的带标签 EC2/EBS/NAT/VPC 资源，包括 `DELETE_FAILED` 或保留的资源。完成检查前，请保留本地身份/配置凭证。不要用固定时长的 sleep 代替删除验证。

如果创建过程尚未到达身份信息捕获步骤，请使用私有意图记录和 CloudFormation 事件/标签手动验证资源归属。不要为了让保护函数通过而伪造 `cluster-identity.json`。

## 故障排查

<details>
<summary>集群创建失败</summary>

检查已获批准的角色权限、服务配额、子网/IP 容量，以及所选区域中的实例可用性。eksctl 使用 CloudFormation；请检查实际故障，不要默认通过授予广泛的管理员权限来解决问题。

```bash
check_account
eksctl utils describe-stacks --region "$AWS_REGION" --cluster "$CLUSTER_NAME"
```

部分创建后的恢复过程中，请保留私有实验目录。执行任何建议的删除操作前，请根据实际资源归属进行核查。

</details>

<details>
<summary>kubectl 无法连接</summary>

检查角色凭证、访问条目、DNS，以及工作站当前的出站地址是否仍在已获批准的 CIDR 范围内。如果需要重建私有 kubeconfig，请先验证集群身份，然后仅写入此实验的路径：

```bash
check_account
aws eks update-kubeconfig --region "$AWS_REGION" --name "$CLUSTER_NAME" \
  --kubeconfig "$KUBECONFIG" --alias "$CLUSTER_NAME"
check_lab
```

不要为了应对客户端地址变更而将端点访问范围扩大到整个互联网。

</details>

## 参考资料

- [EKS 支持的版本](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS 升级策略](https://docs.aws.amazon.com/eks/latest/userguide/view-upgrade-policy.html)
- [集群端点访问](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [eksctl IAM 权限](https://docs.aws.amazon.com/eks/latest/eksctl/minimum-iam-policies.html)
- [eksctl 创建/删除集群](https://docs.aws.amazon.com/eks/latest/eksctl/creating-and-managing-clusters.html)
- [kubectl 版本偏差](https://kubernetes.io/releases/version-skew-policy/)
- [端口转发](https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/)
- [nginx 官方镜像定义](https://github.com/docker-library/official-images/blob/master/library/nginx)

## 后续步骤

- [EKS 集群创建测验](../../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)
- [EKS 网络](../../eks/03-eks-networking-part1.md)
