# Part 1: Prerequisites

> **最后更新**: October 12, 2026

创建 Amazon EKS 集群有多种方式。在本章中，我们将学习如何使用各种工具和方法创建 EKS 集群。

**当前版本：**EKS 1.37 于 2026 年 10 月 1 日发布。

**示例基线：**集群创建章节使用经过审查的 EKS 1.36 基线。在选择其他受支持版本之前，请检查其与相关工具、节点镜像和附加组件的兼容性。

## Table of Contents

1. [前提条件](#prerequisites)
2. [eksctl](02-eks-cluster-creation-part2.md)
3. [AWS Management Console and CLI](02-eks-cluster-creation-part3.md)
4. [Terraform](02-eks-cluster-creation-part4.md)
5. [访问、验证、升级和删除](02-eks-cluster-creation-part5.md)
6. [完整指南和 CDK](02-eks-cluster-creation.md)

## Prerequisites

在创建 EKS 集群之前，需要满足以下前提条件：

### 1. AWS Account

需要有效的 AWS 账户。如果您没有 AWS 账户，可以在 [AWS 网站](https://aws.amazon.com/) 注册。

### 2. IAM Permissions

所需权限取决于工具及其管理的资源。对每个资源授予 `eks:*`、`ec2:*`、`iam:*` 和 `cloudformation:*` 的策略并非必需的最小权限策略。

| Task | Permission scope to review |
| --- | --- |
| EKS cluster/node group management | Required EKS actions and target resources |
| Passing existing IAM roles | `iam:PassRole` for approved role ARNs and service conditions |
| Creating IAM roles/policies/OIDC providers | Tool-managed IAM resources and name/tag scope |
| Creating networking | EC2 actions for the new VPC, subnets and security groups |
| Using eksctl/CDK | Relevant CloudFormation stacks, execution roles and bootstrap resources |

配置身份、集群服务角色和节点角色彼此独立。SCP、权限边界和会话策略仍然适用。请根据合成的模板/计划，审核您组织的配置权限。Auto Mode 的角色要求与传统节点组不同。

参考资料：[EKS IAM 操作和资源](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelastickubernetesservice.html)、[Auto Mode 角色](https://docs.aws.amazon.com/eks/latest/userguide/auto-cluster-iam-role.html)。

### 3. Tool Installation

#### AWS CLI

请选择适用于您的操作系统/CPU 的软件包，并按照[官方 AWS CLI v2 安装指南](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)完成签名验证。对于现有的 v1/v2 安装，请先查看其更新/迁移流程。

| Environment | Official package/installation method |
| --- | --- |
| macOS | Signed `AWSCLIV2.pkg` |
| Linux x86_64 | `awscli-exe-linux-x86_64.zip` with PGP signature verification |
| Linux ARM64 | `awscli-exe-linux-aarch64.zip` with PGP signature verification |
| Windows | MSI installer for supported Windows versions |

不要在 ARM 上原样使用 Linux x86_64 软件包。使用 `aws --version` 检查当前活动的 CLI。如果您的组织使用 IAM Identity Center，请按如下方式配置已批准的 profile。否则，请遵循其联合身份验证流程，而不要假定使用长期访问密钥。

```bash
aws configure sso --profile eks-docs
aws sso login --profile eks-docs
aws sts get-caller-identity --profile eks-docs
export AWS_PROFILE=eks-docs
```

请参阅 [IAM Identity Center 身份验证](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)。对于后续命令，请继续使用已批准的账户、角色和区域。

#### kubectl and eksctl — Linux/macOS

本章的 EKS 1.36 示例以 kubectl **1.36.4** 和 eksctl **0.230.0** 为基线。优先选择与服务器具有相同次要版本的 kubectl；支持的版本偏差为 ±1 个次要版本。对于较旧的 EKS 集群，不要盲目从上游 `stable.txt` 安装最新的次要版本。

此 Bash 示例会选择 AMD64/ARM64，并在安装前验证官方校验和。它需要 `curl`、`tar`、`awk` 以及 `sha256sum` 或 `shasum`；安装到 `/usr/local/bin` 需要管理员权限。下载或校验和验证失败将停止安装。

```bash
(
  set -e
  case "$(uname -s)" in
    Linux) EKS_TOOL_OS=linux; EKS_ARCHIVE_OS=Linux ;;
    Darwin) EKS_TOOL_OS=darwin; EKS_ARCHIVE_OS=Darwin ;;
    *) printf 'Use the official installer for this operating system\n' >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64) EKS_TOOL_ARCH=amd64 ;;
    aarch64|arm64) EKS_TOOL_ARCH=arm64 ;;
    *) printf 'Select a supported CPU architecture\n' >&2; exit 1 ;;
  esac
  EKS_TOOL_ARCHIVE="eksctl_${EKS_ARCHIVE_OS}_${EKS_TOOL_ARCH}.tar.gz"
  EKS_TOOL_DIR=$(mktemp -d)
  : "${EKS_TOOL_DIR:?}"
  trap 'rm -f -- "$EKS_TOOL_DIR/kubectl" "$EKS_TOOL_DIR/kubectl.sha256" "$EKS_TOOL_DIR/eksctl" "$EKS_TOOL_DIR/eksctl_checksums.txt" "$EKS_TOOL_DIR/$EKS_TOOL_ARCHIVE" "$EKS_TOOL_DIR/selected.sha256"; rmdir -- "$EKS_TOOL_DIR"' EXIT
  cd "$EKS_TOOL_DIR" || exit 1
  verify_sha() {
    if command -v sha256sum >/dev/null 2>&1; then
      sha256sum --check "$1"
    else
      shasum -a 256 --check "$1"
    fi
  }
  EKS_KUBECTL_VERSION=v1.36.4
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl" -o kubectl || exit 1
  curl -fL "https://dl.k8s.io/release/$EKS_KUBECTL_VERSION/bin/$EKS_TOOL_OS/$EKS_TOOL_ARCH/kubectl.sha256" -o kubectl.sha256 || exit 1
  printf '%s  kubectl\n' "$(tr -d '[:space:]' < kubectl.sha256)" > selected.sha256
  verify_sha selected.sha256 || exit 1

  EKSCTL_VERSION=0.230.0
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/$EKS_TOOL_ARCHIVE" -o "$EKS_TOOL_ARCHIVE" || exit 1
  curl -fL "https://github.com/eksctl-io/eksctl/releases/download/v$EKSCTL_VERSION/eksctl_checksums.txt" -o eksctl_checksums.txt || exit 1
  awk -v name="$EKS_TOOL_ARCHIVE" '$2 == name {print; count++} END {if (count != 1) exit 1}' \
    eksctl_checksums.txt > selected.sha256 || exit 1
  verify_sha selected.sha256 || exit 1
  tar -xzf "$EKS_TOOL_ARCHIVE" eksctl || exit 1
  sudo install -m 0755 kubectl /usr/local/bin/kubectl || exit 1
  sudo install -m 0755 eksctl /usr/local/bin/eksctl || exit 1
  kubectl version --client
  eksctl version
)
```

官方流程：[Linux kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/)、[macOS kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/)、[eksctl 安装](https://eksctl.io/installation/)。

#### Windows

请在 PowerShell 中遵循[官方 kubectl 安装流程](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)。对于本章的 AMD64 示例，请使用 [kubectl 1.36.4](https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe) 及相同路径下的 `.sha256` 文件。从 [eksctl 0.230.0 发布版本](https://github.com/eksctl-io/eksctl/releases/tag/v0.230.0)中选择与您的 CPU 匹配的 Windows ZIP 和 `eksctl_checksums.txt`。

请将 `Get-FileHash -Algorithm SHA256` 的结果与官方哈希进行比较，并在不匹配时停止。验证后，解压 ZIP，将可执行文件目录添加到 PATH，并检查 `kubectl version --client` 和 `eksctl version`。不要在 Bash 中运行 PowerShell 语法。

还请为 AWS CLI 示例准备好用于生成 JSON 的 `jq`。本次审核期间未执行实际的客户端下载/安装或登录。

### 4. VPC and Subnets

![展示 EKS VPC 架构的示意图：负载均衡器位于公有子网中，包含 NAT Gateway，以及跨两个 Availability Zone 的私有子网中的工作节点。](../.gitbook/assets/en-eks-02-eks-cluster-creation-part1-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-02-eks-cluster-creation-part1-0.html)

该图展示了一种基于 NAT 的布局，而非要求每个集群都必须拥有互联网访问权限。

区域性 EKS 集群需要在同一 VPC 的不同 AZ 中至少有两个子网。每个集群子网至少需要为 EKS 提供六个可用 IP；AWS 建议至少提供十六个。请为节点、Pod、负载均衡器和升级规划额外的地址。启用 VPC DNS 主机名和 DNS 解析。

并非每个 EKS 集群都必须能够访问互联网。节点和工作负载需要通过 NAT/互联网路径，或所需的 VPC endpoint 和镜像副本，访问 Kubernetes API、镜像和必需的 AWS 服务。私有 Kubernetes endpoint 可从 VPC 或具备适当 DNS 和路由的已连接网络访问。

#### VPC Tags for EKS Cluster

`kubernetes.io/cluster/<cluster-name>` VPC tag 是一种旧机制，并非通用的当前 EKS 创建要求。请遵循所选控制器的负载均衡子网发现规则：

- 用于公有负载均衡器的子网：`kubernetes.io/role/elb=1`
- 用于内部负载均衡器的子网：`kubernetes.io/role/internal-elb=1`

标签不会配置路由、安全组或空闲 IP 容量。请参阅 [VPC/子网要求](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html) 和[无互联网访问的集群](https://docs.aws.amazon.com/eks/latest/userguide/private-clusters.html)。

## Quiz

要测试您在本章学到的内容，请尝试 [EKS 集群创建 - 第 1 部分测验](../quizzes/eks/02-eks-cluster-creation-part1-quiz.md)。