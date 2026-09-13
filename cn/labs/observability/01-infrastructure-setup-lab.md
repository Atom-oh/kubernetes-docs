# 第 1 部分：基础设施搭建

<span id="cleanup"></span>
<span id="exercise-1-environment-setup"></span>
<span id="exercise-2-managed-cluster-eks-setup"></span>
<span id="exercise-3-service-cluster-eks-setup"></span>
<span id="exercise-4-aws-managed-services-setup"></span>
<span id="exercise-5-argocd-setup-on-managed-cluster"></span>
<span id="exercise-6-argo-rollouts-setup-on-service-cluster"></span>
<span id="exercise-7-irsa-configuration"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="references"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="steps-6"></span>
<span id="summary"></span>
<span id="troubleshooting"></span>
<span id="verification"></span>
<span id="verification-1"></span>
<span id="verification-2"></span>
<span id="verification-3"></span>
<span id="verification-4"></span>
<span id="verification-5"></span>

> **难度**: 高级
> **最后更新**: September 13, 2026
准备两个 EKS 集群以及一条专用的实验数据库/消息链路。可执行文件位于[应用示例](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application)中。在创建计费资源之前，请先审查账户、Region（区域）、网络、权限和清理方案。本次审阅并未创建任何 AWS 资源。

![管理/服务集群与专用实验资源](../../.gitbook/assets/en-labs-observability-01-infrastructure-setup-lab-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-01-infrastructure-setup-lab-0.html)

## 1. 验证环境与归属 {#prerequisites}

示例是在 AWS CLI v2、eksctl 0.229.0、kubectl 1.36.2、Helm 3.21.3、Python 3.12、Docker、Git 和 jq 环境下审阅的。在审阅时，EKS 1.36 处于标准支持阶段。旧的 1.31 示例处于扩展支持阶段，并非已经停止支持。实际执行时请重新确认版本与 Region 的可用性。

```bash
aws --version
eksctl version
kubectl version --client
helm version
python3 --version
aws sts get-caller-identity
```
请使用经过批准的临时角色。对照部署计划审查所需的 EKS、EC2/VPC、CloudFormation、IAM/PassRole、RDS、SNS/SQS、KMS 和 Logs 操作权限。不要为本练习为每个服务授予 FullAccess，也不要创建长期有效的 IAM 访问密钥。

```bash
umask 077
export LAB_STATE="$(mktemp -d "$PWD/obs-lab.XXXXXXXX")"
# Set AWS_REGION, EXPECTED_ACCOUNT_ID and a unique LAB_PREFIX first.
test "$(aws sts get-caller-identity --query Account --output text)" = "$EXPECTED_ACCOUNT_ID"
```

## 2. 网络与两个集群 {#clusters}

该示例复用了一个已审阅的 VPC 以及位于不同 AZ（可用区）中的两个私有子网。请先准备好 NAT/所需的 VPC 端点、DNS、地址容量以及 SG/NACL 规则。Kubernetes service CIDR172.20.0.0/16 和172.21.0.0/16 不得与实际的 VPC/互联网络重叠。使用不同的 VPC 时需要额外的对等连接/TGW、双向路由、DNS 以及源 IP 验证。

```bash
cd examples/labs/observability/application
python3 prepare_clusters.py --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --subnet-a "$PRIVATE_SUBNET_A" --az-a "$AZ_A" \
  --subnet-b "$PRIVATE_SUBNET_B" --az-b "$AZ_B" \
  --client-cidr "$CLIENT_CIDR" --prefix "$LAB_PREFIX" \
  --output-directory "$LAB_STATE/clusters"
```
生成器会选择 EKS 1.36、API access entry、OIDC、AL2023 托管节点、加密的 gp3 以及范围收窄的公共 API 客户端 CIDR。节点规格/数量是实验设置，并非经过实测的容量。创建之前请审查 JSON 和成本。若失败，请先检查以该名称部分创建出的资源，然后再重新创建任何内容。

```bash
eksctl create cluster -f "$LAB_STATE/clusters/managed.json" --write-kubeconfig=false
eksctl create cluster -f "$LAB_STATE/clusters/service.json" --write-kubeconfig=false
export KUBECONFIG="$LAB_STATE/kubeconfig"
aws eks update-kubeconfig --name "$LAB_PREFIX-managed" --alias managed --kubeconfig "$KUBECONFIG"
aws eks update-kubeconfig --name "$LAB_PREFIX-service" --alias service --kubeconfig "$KUBECONFIG"
kubectl --context managed get nodes
kubectl --context service get nodes
```
请套用 [EKS 创建指南](../../eks/02-eks-cluster-creation-part1.md)和[集群实验](../eks/01-eks-cluster-creation-lab.md)中的账户/端点/归属检查。确认两个 context 分别选中了预期的、彼此不同的集群。

## 3. 存储、负载均衡器与 OIDC 前置条件 {#platform-prerequisites}

安装 EBS CSI 和已审阅的 `gp3` StorageClass、一个真正会强制执行 NetworkPolicy 的 CNI，以及 AWS Load Balancer Controller（`service.k8s.aws/nlb`）。不要盲目覆盖共享的 StorageClass。获取每个集群的 OIDC issuer 及对应的 IAM provider ARN。去掉 https:// 后的 issuer 主机/路径必须与 provider ARN 的后缀一致。

```bash
aws eks describe-cluster --name "$LAB_PREFIX-managed" --query cluster.identity.oidc.issuer --output text
aws eks describe-cluster --name "$LAB_PREFIX-service" --query cluster.identity.oidc.issuer --output text
kubectl --context managed get storageclass gp3
kubectl --context service get storageclass gp3
```

## 4. Aurora、SNS/SQS 与角色 {#managed-resources}

`application/infra.yaml` 会创建一个私有的 Aurora writer、托管的 master Secret、SNS 扇出、彼此独立的消费者队列/DLQ、一个 CloudWatch 日志组以及若干角色。数据库入站规则仅允许实际的 service 节点 SG。单 writer 练习并不等于 Multi-AZ 高可用。请查询并显式提供该 Region 支持的 Aurora 引擎版本。

```bash
aws rds describe-db-engine-versions --engine aurora-postgresql \
  --query "DBEngineVersions[].EngineVersion" --output table
```
提供 VpcId、PrivateSubnetIds、ServiceNodeSecurityGroupId、AuroraEngineVersion 以及两组 OIDC provider/issuer 配对；审查并执行 CloudFormation 变更集。验证账户、ARN 与 ServiceAccount 的一致性。应用运行时角色、KEDA 队列读取身份和管理侧 Collector 日志身份是彼此独立的。

```bash
aws cloudformation describe-stacks --stack-name "$LAB_STACK" \
  --query "Stacks[0].Outputs" --output json > "$LAB_STATE/infra-outputs.json"
```

在此为第 2 部分生成 Collector 身份所需的输入。现在就确定镜像仓库和不可变标签；镜像的构建/推送在第 3 部分进行。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt PyYAML==6.0.3
.venv/bin/python prepare_values.py --outputs-file "$LAB_STATE/infra-outputs.json"   --region "$AWS_REGION" --image-repository "$IMAGE_REPOSITORY"   --image-tag "$IMAGE_TAG" --output-directory "$LAB_STATE/helm-inputs"
```

## 5. 运行时数据库账户与下一步 {#database-and-next}

只在经过授权的环境中读取 master Secret，并将连接信息保存为私有的 JSON 文件。使用 RDS CA 证书包和 `sslmode=verify-full`。[bootstrap_db.py 流程](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/labs/observability/application#infrastructure-and-credentials)会创建专用的 `lab_runtime` DML 访问权限，且不会覆盖已有密码。将其 Pod CA 路径设置为 `/run/database-ca/global-bundle.pem`。

在归属清单中记录 stack、集群、保留的快照、IAM 附加关系、LB 和 PVC。针对实际的 Region 和用量估算 EKS/节点/NAT/EBS/Aurora/Logs/SNS/SQS/KMS/流量传输成本。不要给出固定的每小时总额，也不要把 AMG 的按用户月度价格换算成工作区的每小时费用。继续阅读[第 2 部分](./02-observability-stack-lab.md)。

## 验证范围

检查涵盖了 eksctl schema、CloudFormation lint/角色结构以及本地 PostgreSQL 行为。实际的 EKS/VPC/OIDC/IRSA/Aurora/TLS、配额以及预配时长均未实际验证。
