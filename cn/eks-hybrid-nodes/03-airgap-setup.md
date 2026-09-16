# 受限互联网设置（S3、私有端点和代理）

< [上一节：网络配置](./02-network-configuration.md) | [目录](./README.md) | [下一节：节点引导](./04-node-bootstrap.md) >

> **支持的版本**：EKS Hybrid Nodes；已检查 nodeadm v1.0.20 源代码。请为您的集群选择 Kubernetes、OS、运行时和附加组件的对应组合。
> **最后更新**：September 16, 2026

本章用于准备公共互联网访问受限的 Hybrid Nodes。**Hybrid Nodes 仍需要连接到 AWS 托管的 EKS 控制平面以及用于凭证的 AWS 服务。**通过物理方式传输软件，并不会使 Hybrid Nodes 成为断开连接的 Kubernetes 发行版。

这些示例是准备和审查流程，而非经过测试的生产部署。审计验证了源代码、配置和本地失败情形；未构建 OS 镜像、发布构件、注册节点或验证实际私有网络。由于 TLS 主机名验证失败，审计环境无法获取公共构件清单。没有绕过任何证书检查，也不会根据该失败的获取操作推断当前构件补丁或摘要。

**安全团队配套资料：**[Hybrid Nodes 网络隔离审查](11-network-separation-security.md)说明了新的控制平面到本地连接、端点类型、权限和数据边界，以及审查证据。私有连接本身并不能确保合规性。

## 连接性和隔离边界

| 模式 | 提供的能力 | Hybrid Nodes 注意事项 |
|---|---|---|
| 物理断开网络 | 没有到 AWS 的实时连接 | 无法提供所需的 EKS 控制平面和凭证服务连接性 |
| 受控出口代理 | 已批准的外部 HTTPS 目标和日志 | 分别为安装程序、包管理器、主机守护进程和适用的 Pods 配置 |
| 使用私有端点的 VPN/Direct Connect | 到集群和受支持 AWS API 的私有路径 | 需要双向路由、DNS、安全组和授权；端点并不覆盖每个公共下载主机 |
| 离线软件传输 | 导入已审查构件的受控方式 | 与私有 AWS 连接配合时很有用；不能替代该连接性 |

网络限制可减少暴露，但不能保证监管合规性、消除数据外泄或阻止所有供应链攻击。证书信任、已批准的发布者、签名、修补、操作员访问和应用程序数据流仍是独立控制措施。私有连接也仍依赖 AWS 服务和本地网络。

![物理隔离、代理出口和私有 AWS 连接的比较。只有已连接的模式可以运行 EKS Hybrid Nodes。](../.gitbook/assets/en-eks-hybrid-nodes-03-airgap-setup-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-03-airgap-setup-0.html)

> **图表说明：**物理隔离选项仅用于比较，并非受支持的 Hybrid Nodes 运行模式。

## 架构和构件职责

![受控准备主机将已审查的软件暂存到私有存储中；节点使用已验证的下载 URL 和私有 AWS 连接。](../.gitbook/assets/en-eks-hybrid-nodes-03-airgap-setup-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-03-airgap-setup-1.html)

> **图表更正：**`hybrid-assets.eks.amazonaws.com → PHZ → S3` 捷径并非可用的透明镜像。请使用以下安装路径。仅 DNS 更改无法提供原始主机名的 TLS 证书、S3 对象路由或请求授权。

| 构件 | 准备和交付 |
|---|---|
| Hybrid `nodeadm` | 从 `aws/eks-hybrid` 批准一个版本；以 root 身份运行前，验证来源和校验和。这与 EC2 的 `amazon-eks-ami` nodeadm 不同 |
| kubelet、kubectl、CNI 插件、ECR 凭证提供程序、IAM 身份验证器 | 从已批准构件清单中选择一个精确的版本/构建/OS/架构 |
| IAM Roles Anywhere 签名帮助程序 | 选择并验证其自身版本；不要随意选择数组中的第一个条目 |
| SSM 安装程序/代理 | 独立的区域下载、签名和注册路径；不会被自定义 EKS 构件清单完全重定向 |
| containerd、runc、iptables 和 OS 依赖项 | 已批准的 OS/运行时软件包组合，包括传递依赖项和已签名的仓库元数据 |
| CNI、CoreDNS、kube-proxy、sandbox 和工作负载镜像 | 清点实际清单、init containers、镜像摘要和平台；二进制清单不提供镜像标签 |

Amazon VPC CNI (`aws-node` / `vpc-cni-init`) 并非 Hybrid Nodes 的 CNI。请使用[网络配置](./02-network-configuration.md)中受支持的 Hybrid CNI 流程。仅当所选 CNI 数据路径使用 kube-proxy 时才包含 kube-proxy。CNI 插件二进制包并不是已部署的 CNI 控制器。

## 选择安装路径

### 路径 A：预安装 OS 镜像

在受控构建器上，安装已批准的 Hybrid nodeadm，并使用集群所选的 Kubernetes 版本和凭证提供程序运行 `nodeadm install`。AWS 记录了此镜像构建用途。将已安装的构件和 nodeadm 跟踪器保留在镜像中。

```bash
# Controlled image builder only; installs software on this host.
set -euo pipefail
: "${KUBERNETES_VERSION:?Approved cluster-compatible version}"
: "${REGION:?}" "${CREDENTIAL_PROVIDER:?ssm or iam-ra}"
case "$CREDENTIAL_PROVIDER" in ssm|iam-ra) ;; *) exit 1 ;; esac
sudo nodeadm install "$KUBERNETES_VERSION" \
  --credential-provider "$CREDENTIAL_PROVIDER" --region "$REGION"
```

默认运行时来源是 OS 发行版；RHEL 不支持该来源。对于 RHEL，请选择有文档说明的 Docker 软件包来源，或预安装兼容运行时并使用 `--containerd-source none`。AL2023 不支持 Docker 来源。`none` 不会为您安装 containerd。

**不要**初始化/注册构建器并克隆其身份。通过已批准的每节点流程交付每个节点的 SSM 激活信息或 IAM Roles Anywhere 证书/私钥。不要将激活代码、私钥、SSM 注册状态、kubelet 证书或操作员凭证打包进可复用镜像。Bottlerocket 有自己的准备/引导工作流，不使用此 nodeadm 流程。

新的 SSM 安装/升级需要 nodeadm **1.0.19 或更高版本**，因为旧版本包含过期的 SSM 签名密钥。本章检查的是 **v1.0.20**，而不是无边界的 `latest` 二进制文件。

### 路径 B：自定义构件清单

发布的 **v1.0.20 源代码**支持以下标志，即使用户指南的标志表未列出所有标志：

| 命令/设置 | 已检查版本中的实际行为 |
|---|---|
| `install --manifest-override file:///path/manifest.json` | 读取本地清单；YAML 解码器接受 JSON |
| `install --manifest-override https://mirror.example.com/manifest.json` | 使用普通 HTTP 客户端下载清单 |
| `install --private-mode` | 要求使用 `--manifest-override`；跳过 OS 软件包安装，但仍安装凭证和 EKS 构件 |
| `init --manifest-override ... --private-mode` | 要求清单参数并从中获取 Region 元数据；不会移除 AWS 身份验证或 EKS 连接性要求 |
| 单个构件 `uri` / `checksum_uri` | 通过 HTTP(S) 获取，不使用 S3 SigV4 签名。`file://` **清单**并不意味着支持 `file://` **构件** URL |
| `gzip_uri` | 存在时优先于 `uri`；解压后进行校验和验证 |

在使用这些标志前，请检查精确部署二进制文件的 `install --help` 和 `init --help`。私有模式不是完整的离线软件包安装程序。请预安装带有 systemd 单元的 containerd、runc、iptables、CA 证书和所有必需 OS 依赖项。

使用 `--credential-provider ssm` 时，v1.0.20 仍会分别构造区域 `ssm-setup-cli` 和签名 URL。清单的 `ssm_releases` 字段不会重定向该安装路径。请规划对这些 S3 对象以及后续代理安装/注册依赖项的访问，或者使用经过验证的预安装镜像工作流。

### 审查清单并选择一个组合

上游清单包含 `supported_eks_releases`、`iam_roles_anywhere_releases` 和 `region_config`。Kubernetes 记录包含 `major_minor_version`、`latest_patch_version`、`patch_releases[].version`、**`patch_version`**、**`release_date`**以及每个构件的 URL。多个构建可能共享同一个补丁版本。先前的 `1.33.3` 示例是历史架构说明，而不是当前已批准补丁的证据。

保留下载的上游清单、其获取日期/哈希值和批准记录。选择前验证其 HTTPS 来源。以下本地选择器要求精确的 Kubernetes 补丁、构建日期、签名帮助程序版本和架构。它会拒绝歧义选择、缺失构件、重复 YAML 键和未知 Region。它保留实际 Region 元数据，而不是猜测 ECR 账户。

在准备主机上保存为 `select-mirror.py`；它需要 Python 3 和 PyYAML：

```python
#!/usr/bin/env python3
"""Build a local review plan, not an installer. Requires PyYAML."""
import copy
import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("duplicate YAML key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping
)


def https_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError("URL must be a nonempty HTTPS URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("HTTPS URL must not contain credentials, query or fragment")
    return value


def select(manifest, version, build_date, iam_version, arch, region, mirror):
    if not re.fullmatch(r"1\.\d+\.\d+", version):
        raise ValueError("an exact approved Kubernetes patch is required")
    datetime.date.fromisoformat(build_date)
    if arch not in ("amd64", "arm64"):
        raise ValueError("unsupported architecture")
    mirror = https_url(mirror).rstrip("/")
    region_info = manifest["region_config"][region]  # No account fallback.
    if (region_info.get("partition") != "aws"
            or region_info.get("dns_suffix") != "amazonaws.com"
            or not region_info.get("cred_providers", {}).get("iam-ra")
            or not re.fullmatch(r"\d{12}", str(region_info.get("ecr_account_id", "")))):
        raise ValueError("review a supported commercial Region with IAM Roles Anywhere")
    minor, patch = version.rsplit(".", 1)
    releases = [
        release
        for family in manifest["supported_eks_releases"]
        if family["major_minor_version"] == minor
        for release in family["patch_releases"]
        if release["version"] == version and release["patch_version"] == patch
        and release["release_date"] == build_date
    ]
    iam = [
        release for release in manifest["iam_roles_anywhere_releases"]
        if release["version"] == iam_version
    ]
    if len(releases) != 1 or len(iam) != 1:
        raise ValueError("release selection must be unique")
    eks_release, iam_release = copy.deepcopy(releases[0]), copy.deepcopy(iam[0])
    plan = []
    for release, names in [
        (eks_release, ["kubelet", "kubectl", "cni-plugins",
                       "ecr-credential-provider", "aws-iam-authenticator"]),
        (iam_release, ["aws_signing_helper"]),
    ]:
        chosen = []
        for name in names:
            matches = [a for a in release["artifacts"]
                       if a["name"] == name and a["arch"] == arch and a["os"] == "linux"]
            if len(matches) != 1:
                raise ValueError("missing or duplicate artifact: " + name)
            artifact = matches[0]
            item_id = "a%02d" % len(plan)
            plan.append({"id": item_id, "name": name,
                         "uri": https_url(artifact["uri"]),
                         "checksum_uri": https_url(artifact["checksum_uri"])})
            # Use the original, uncompressed URI; its checksum is not a gzip-file hash.
            artifact.pop("gzip_uri", None)
            artifact["uri"] = mirror + "/" + item_id + "/data"
            artifact["checksum_uri"] = mirror + "/" + item_id + "/data.sha256"
            chosen.append(artifact)
        release["artifacts"] = chosen
    selected = {
        "supported_eks_releases": [{
            "major_minor_version": minor, "latest_patch_version": patch,
            "patch_releases": [eks_release],
        }],
        "iam_roles_anywhere_releases": [iam_release],
        "region_config": {region: copy.deepcopy(region_info)},
    }
    return selected, {"artifacts": plan}


def main():
    if len(sys.argv) != 9:
        raise ValueError(
            "usage: select-mirror.py UPSTREAM VERSION BUILD_DATE IAM_VERSION "
            "ARCH REGION HTTPS_MIRROR_PREFIX NEW_OUTPUT_DIR"
        )
    source, version, date, iam, arch, region, mirror, output = sys.argv[1:]
    manifest = yaml.load(Path(source).read_text(), Loader=UniqueLoader)
    selected, plan = select(manifest, version, date, iam, arch, region, mirror)
    out = Path(output)
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    (out / "upstream.yaml").write_bytes(Path(source).read_bytes())
    (out / "manifest.json").write_text(json.dumps(selected, indent=2) + "\n")
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")


if __name__ == "__main__":
    main()
```

输出目录必须是新的。HTTPS 镜像前缀必须映射到发布所用的同一不可变对象前缀。此脚本仅构建计划；它既不下载，也不对镜像进行身份验证。

```bash
set -euo pipefail
: "${APPROVED_PATCH:?}" "${APPROVED_BUILD_DATE:?}" "${APPROVED_IAM_VERSION:?}"
: "${ARCH:?amd64 or arm64}" "${REGION:?}"
: "${MIRROR_PREFIX:?HTTPS URL for this reviewed candidate}"
: "${NEW_PLAN_DIR:?A new local directory}"
python3 select-mirror.py upstream.yaml "$APPROVED_PATCH" "$APPROVED_BUILD_DATE" \
  "$APPROVED_IAM_VERSION" "$ARCH" "$REGION" "$MIRROR_PREFIX" "$NEW_PLAN_DIR"
```

下载前审查所有源主机和六个选定构件。这是一个 **IAM Roles Anywhere 构件示例**，不是 SSM 安装程序镜像。它不包括 nodeadm 本身、OS 软件包、镜像、签名密钥或证书。

保存为 `download-plan.sh`：

```bash
#!/usr/bin/env bash
# Download into a new plan directory. No AWS writes or host installation.
set -euo pipefail
umask 077
cd -- "${1:?Use the directory produced by select-mirror.py}"
test ! -e checksums.sha256
test ! -e queue.tsv
jq -er '.artifacts[] | [.id, .uri, .checksum_uri] | @tsv' plan.json > queue.tsv
test "$(wc -l < queue.tsv)" -eq 6
while IFS=$'\t' read -r item_id uri checksum_uri; do
  [[ "$item_id" =~ ^a[0-9]{2}$ ]]
  mkdir -- "$item_id"  # Refuse a partial run or existing directory.
  curl --fail --show-error --silent --location \
    --proto '=https' --proto-redir '=https' --connect-timeout 10 \
    --max-time 300 --max-filesize 268435456 \
    "$uri" -o "$item_id/data"
  curl --fail --show-error --silent --location \
    --proto '=https' --proto-redir '=https' --connect-timeout 10 \
    --max-time 30 --max-filesize 4096 \
    "$checksum_uri" -o "$item_id/upstream.sha256"
  expected=$(python3 - "$item_id/upstream.sha256" <<'CHECKSUM_PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text().strip()
match = re.fullmatch(r"([0-9a-fA-F]{64})(?:[ \t]+[^\r\n]+)?", text)
if not match:
    raise SystemExit("missing, malformed or multi-record upstream checksum")
print(match.group(1).lower())
CHECKSUM_PY
)
  actual=$(sha256sum "$item_id/data")
  [[ "${actual%% *}" == "$expected" ]]
  # nodeadm v1.0.20 requires GNU format: digest, space, filename.
  printf '%s  data\n' "$expected" > "$item_id/data.sha256"
done < queue.tsv
sha256sum manifest.json plan.json upstream.yaml a*/data a*/data.sha256 \
  > checksums.sha256
sha256sum --strict --check checksums.sha256
printf '%s\n' 'Six artifacts verified locally; publishing and node installation remain separate.'
```

每个构件 256 MiB 的大小限制是有意设定的；如果已批准构件超出此限制，请审查它。下载失败、校验和格式错误或哈希不匹配都会停止脚本。会保留部分目录以供检查；解决原因后开始新的候选项。请勿删除共享的 `/tmp` 目录或跳过缺失的校验和。

这些哈希将所选字节与获取的校验和绑定。它们不是独立签名，也不能证明已遭入侵的发布者可信。请保护已审查的清单/校验和记录，并在可用时使用发布者验证。

## 私有 S3 发布和授权

使用一个**预先创建且归您所有**的 bucket，并启用 Block Public Access、已批准的加密、版本控制/保留以及单独的发布者/读取者权限。以下示例不会创建 bucket 或替换其策略。AccessDenied、过期凭证和超时均为失败，并非 bucket/object 不存在的证据。

现有 bucket 的一个示例*读取者策略语句*如下：

```json
{
  "Sid": "ReadApprovedHybridArtifacts",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::111122223333:role/HybridArtifactReader"},
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::example-hybrid-artifacts/hybrid-candidates/*",
  "Condition": {"StringEquals": {"aws:SourceVpce": "vpce-0123456789abcdef0"}}
}
```

请将账户、角色、bucket、前缀和端点替换为已审查的值。此语句授予一个路径；它不会撤销其他现有授权。对于一个端点外的每个请求，bucket 范围的 `Deny s3:*` 也可能阻止已连接的发布者和管理恢复。在应用此类边界前，请明确设计这些路径。

指定主体策略需要已签名的请求。**nodeadm 的普通 HTTPS 下载器不会因为节点具有 IAM 角色就变成经过 IAM 身份验证的 S3 客户端。**以下两种可行设计需要验证：

1. 使用经过身份验证的准备代理/CLI 获取已批准的文件，然后通过由组织控制、具有适当网络访问控制及其自身主机名证书的 HTTPS 构件服务提供它们。
2. 使用预安装镜像路径，不依赖运行时二进制镜像。

返回 `403` 的私有 S3 object URL 无法通过 DNS 覆盖修复。不要将 bearer 预签名 URL 或凭证放入清单、进程参数或已发布日志中。如果组织选择允许仅限私有网络的非机密二进制文件进行未经身份验证的读取，这是一项独立且经明确审查的策略——不是上面的指定主体策略。

保存为 `publish-plan.sh`。仅在 bucket 所有者批准候选项和权限后运行；此脚本**会写入 S3 objects**：

```bash
#!/usr/bin/env bash
# Owner-approved publication only; creates billable S3 objects, never a bucket.
set -euo pipefail
umask 077
cd -- "${1:?Use a verified plan directory}"
: "${REGION:?}" "${BUCKET:?}" "${EXPECTED_ACCOUNT_ID:?}" "${PREFIX:?}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
[[ "$PREFIX" =~ ^hybrid-candidates/[A-Za-z0-9-]+$ ]]
sha256sum --strict --check checksums.sha256
aws s3api head-bucket --region "$REGION" --bucket "$BUCKET" \
  --expected-bucket-owner "$EXPECTED_ACCOUNT_ID"
# Manifest is last. Any failed write stops; retain the partial prefix for review.
for file in a{00..05}/data a{00..05}/data.sha256 checksums.sha256 \
            upstream.yaml plan.json manifest.json; do
  test -f "$file"
  aws s3api put-object --region "$REGION" --bucket "$BUCKET" \
    --expected-bucket-owner "$EXPECTED_ACCOUNT_ID" \
    --key "$PREFIX/$file" --body "$file" --if-none-match '*' \
    --server-side-encryption AES256 --checksum-algorithm SHA256 \
    --output json > "${file//\//_}.upload.json"
done
printf '%s\n' 'Candidate uploaded. Verify readback, mirror URL mapping and hashes before promotion.'
```

对于要求 SSE-KMS 的 bucket，请使用其已批准的密钥和 KMS 权限，而不是 AES256 示例。条件写入可防止覆盖现有键；它们不会使多 object 上传具备原子性。最后上传清单，失败的候选项会保持未发布状态，直到验证读取、实际 HTTPS 镜像映射和哈希。记录返回的 object VersionIds/校验和及保留设置；S3 ETags 并非通用 SHA-256 摘要。

## DNS 和私有端点要求

`hybrid-assets.eks.amazonaws.com` 是 AWS CloudFront 下载主机。创建同名的 PHZ 并将其别名设为 S3，无法保留：

- TLS 证书/SNI 主机名；
- HTTP Host 标头和 S3 bucket/object 键映射；
- 原始路径，尤其在上传者扁平化所有名称时；
- 请求授权。

不要通过禁用 TLS 检查来修复此问题。请通过受控代理保持已批准来源可访问，使用预安装镜像，或使用具有实际镜像 URL 的受支持清单覆盖。

S3 **Interface** 端点可通过 VPN/Direct Connect 为本地客户端提供服务。支持 S3 私有 DNS。**仅用于入站 Resolver 的私有 DNS**选项要求 VPC 侧维护 S3 gateway endpoint；或者，将 VPC 和本地请求都通过 interface endpoint 路由。gateway endpoint 本身无法从本地直接访问。

请按已审查的 VPC 和端点 ID 选择端点，而非选择 Region 中第一个 S3 端点。请使用[网络配置](./02-network-configuration.md)中的 DNS/路由流程。EKS 管理 API 端点不是 Kubernetes API 端点；私有 ECR 端点不提供对公共 ECR 或 CloudFront 的通用访问。

## 安装和初始化已准备节点

对于自定义 IAM Roles Anywhere 路径，必须已准备好运行时、OS 依赖项、已批准的 nodeadm 和镜像服务。该命令会在目标节点上安装软件：

```bash
set -euo pipefail
: "${APPROVED_PATCH:?}" "${REGION:?}" "${LOCAL_MANIFEST:?Absolute local path}"
[[ "$LOCAL_MANIFEST" = /* ]]
test -s "$LOCAL_MANIFEST"
sudo nodeadm install "$APPROVED_PATCH" --region "$REGION" \
  --credential-provider iam-ra --containerd-source none \
  --manifest-override "file://$LOCAL_MANIFEST" --private-mode
```

使用[先决条件](./01-prerequisites.md)和[节点引导](./04-node-bootstrap.md)准备每节点配置。例如，SSM 配置**形态**如下：

```yaml
apiVersion: node.eks.aws/v1alpha1
kind: NodeConfig
spec:
  cluster:
    name: my-hybrid-cluster
    region: ap-northeast-2
  hybrid:
    ssm:
      activationCode: REPLACE_WITH_NODE_ACTIVATION_CODE
      activationId: REPLACE_WITH_NODE_ACTIVATION_ID
```

请准确使用节点上安装的提供程序；此 SSM 形态不是上述 IAM Roles Anywhere 命令的配置。保护填充后的文件（root 所有，模式 `0600`），绝不提交它，也不要将机密放入 shell 历史记录。提供手写 API endpoint/CA 字段并不能消除对文档所述集群发现和身份验证路径的需求。

```bash
# Local config validation; this is not a join or an end-to-end network test.
sudo nodeadm config check --config-source file:///etc/eks/nodeconfig.yaml
```

网络、身份和 CNI 先决条件通过后，所有者可以运行 `nodeadm init`。在私有清单路径上，请再次传递已批准清单：

```bash
# Mutates the target node and registers it with EKS.
sudo nodeadm init --config-source file:///etc/eks/nodeconfig.yaml \
  --manifest-override file:///etc/eks/manifest.json --private-mode
```

已检查版本中没有 `nodeadm init --dry-run`。不要为了完成不完整的准备流程而跳过初始化验证。

## 容器镜像交付

私有 ECR 拉取需要 ECR API 和 DKR 路径、S3 layer-download 路径、DNS 以及适当的 image-pull 权限。成功调用 `describe-repositories` 并不能证明可以下载镜像层。请预填充并测试任何 pull-through cache；ECR 端点文档说明首次未缓存拉取还需要额外的互联网要求。

使用已部署附加组件清单中的实际 registry 账户/Region/镜像引用。不要通过向 Kubernetes 补丁追加 `-eksbuild.1` 构造镜像标签，也不要从无关集群复制过时的 pause/CoreDNS 版本。

nodeadm 会在 `/etc/eks/image-credential-provider/ecr-credential-provider` 安装 ECR helper，并在 `/etc/eks/image-credential-provider/config.json` 初始化其配置。请检查生成的 kubelet 配置，而不是在不同目录下写入未使用的文件。`ctr images pull` 是独立客户端，不会自动使用 kubelet 的 exec credential provider。

### 离线镜像传输

选择已批准的摘要和所需平台。对于多平台归档，请在源/目标格式支持的情况下保留索引和摘要：

```bash
# Preparation host: downloads images; requires reviewed registry authentication.
set -euo pipefail
: "${SOURCE_DIGEST_REF:?registry/repository@sha256:approved-digest}"
: "${NEW_IMAGE_DIR:?New directory}"
[[ "$SOURCE_DIGEST_REF" =~ @sha256:[0-9a-f]{64}$ ]]
mkdir -m 700 -- "$NEW_IMAGE_DIR"
skopeo copy --all --preserve-digests "docker://$SOURCE_DIGEST_REF" \
  "oci-archive:$NEW_IMAGE_DIR/image.tar:approved"
(cd "$NEW_IMAGE_DIR" && sha256sum image.tar > image.tar.sha256)
```

传输归档及其受独立保护的批准/哈希记录。在导入或推送前，在该目录中运行 `sha256sum --strict --check image.tar.sha256`，失败时停止。对于内部 registry 目标：

```bash
# Internal staging host: writes an image to the reviewed destination registry.
set -euo pipefail
: "${DEST_DIGEST_REF:?approved-registry/repository@sha256:approved-digest}"
[[ "$DEST_DIGEST_REF" =~ @sha256:[0-9a-f]{64}$ ]]
sha256sum --strict --check image.tar.sha256
skopeo copy --all --preserve-digests oci-archive:image.tar:approved \
  "docker://$DEST_DIGEST_REF"
```

不要禁用 registry TLS 验证。更改压缩/清单格式可能无法保留摘要；请停止并审查生成的身份，而不是悄然声称其未改变。

直接 containerd 预加载是另一种选择，但必须针对部署的运行时进行测试：Kubernetes 使用 `k8s.io` 命名空间，导入的引用必须与 Pod/sandbox 引用匹配，并且所有必需的平台 blob 都必须存在。归档的 `approved` 注释不会自动成为 Pod 请求的 registry 名称。镜像垃圾回收和 `imagePullPolicy` 也可能导致后续拉取。仅成功导入 tar 并不能证明离线 Pod 会启动。

## 已签名的本地软件包仓库

将 OS 版本、架构、传递依赖项和元数据作为已审查的组合进行镜像。保留供应商签名，或使用单独受信任密钥对组织维护的仓库签名。

用于**已准备并已签名**本地 flat repository 的 Ubuntu 客户端配置示例：

```text
deb [signed-by=/etc/apt/keyrings/hybrid-mirror.gpg] file:///srv/apt-repo ./
```

仓库需要有效的 `Release` 以及 `InRelease` 或 `Release.gpg`，而不仅仅是 `Packages.gz`。通过独立的可信路径分发并验证密钥指纹。不要使用 `trusted=yes` 来绕过仓库身份验证。

DNF/YUM repository 配置示例：

```ini
[hybrid-local]
name=Reviewed hybrid packages
baseurl=file:///srv/yum-repo
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-hybrid-mirror
```

这要求有效的软件包签名和已签名的仓库元数据。元数据和软件包签名密钥可能不同；请配置已批准的密钥集。验证失败时，不要设置 `gpgcheck=0`。软件包安装和服务重启应属于镜像构建或已排空的维护操作，而非任意在线节点验证脚本。

## 代理配置

先构建每客户端目标映射。包括 loopback、实际私有 API/registry 名称以及必须绕过代理的节点/Pod/Service 范围。CIDR 和后缀匹配因客户端而异。不要盲目将 **`.eks.amazonaws.com`** 放进 `NO_PROXY`：它也会匹配公共 `hybrid-assets.eks.amazonaws.com` 下载主机。

已审查且非机密代理配置的 shell 示例：

```bash
export HTTP_PROXY=http://proxy.internal.example.com:3128
export HTTPS_PROXY=http://proxy.internal.example.com:3128
export NO_PROXY=localhost,127.0.0.1,::1,.svc,.cluster.local,registry.internal.example.com
export http_proxy="$HTTP_PROXY" https_proxy="$HTTPS_PROXY" no_proxy="$NO_PROXY"
```

添加实际私有 API 主机名/IP 和其他绕过目标；这不是完整站点配置。登录 shell 的环境不会配置现有 systemd 服务。不要 source 或反复追加到 `/etc/environment`。

对于 `containerd.service` 和 `kubelet.service`，请在 `/etc/systemd/system/UNIT.service.d/http-proxy.conf` 下使用所有者管理的 drop-in：

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.internal.example.com:3128"
Environment="HTTPS_PROXY=http://proxy.internal.example.com:3128"
Environment="NO_PROXY=localhost,127.0.0.1,::1,.svc,.cluster.local,registry.internal.example.com"
```

审查现有 drop-in，并仅在已批准的构建/维护阶段重启受影响的单元。containerd TOML 中的 `[proxy.http]` 节不是 HTTP 代理配置。

| 组件 | 配置和条件 |
|---|---|
| nodeadm 进程 | 仅通过 `sudo` 传递已审查的代理环境；不要用 `sudo -E` 转发整个操作员环境 |
| containerd / kubelet | 独立的 systemd 环境；生成的 kubelet 配置和主机环境是不同层 |
| 使用文档所述 snap 安装的 Ubuntu 上的 SSM | `snap.amazon-ssm-agent.amazon-ssm-agent.service.d/http-proxy.conf` |
| AL2023/RHEL 上的 SSM | `amazon-ssm-agent.service.d/http-proxy.conf`；确认实际安装的单元 |
| IAM Roles Anywhere 凭证进程 | nodeadm 在生成 `--with-proxy` 时检测代理变量；调用守护进程也必须接收正确环境 |
| 使用 `spec.hybrid.enableCredentialsFile: true` 的 IAM Roles Anywhere | 在此模式下，`aws_signing_helper_update.service` **确实存在**；初始化前配置其 drop-in。不要假定该服务存在于每个 IAM Roles Anywhere 安装中 |
| apt | 具有 `Acquire::http::Proxy` 和 `Acquire::https::Proxy` 的所有者管理 `/etc/apt/apt.conf.d/` 文件 |
| snap | 实际使用 snap 时，使用 `snap set system proxy.http=... proxy.https=...` |
| dnf / yum | 审查并更新现有配置的 `proxy` 设置；不要替换其其他设置或追加重复项 |
| kube-proxy / 其他 Pods | 仅在其流量需要代理时配置其 Pod 环境 |

对于文档所述的代理拓扑，请在创建集群后、加入 hybrid nodes 前配置 kube-proxy。保留现有 `NODE_NAME` 环境和所有命令参数。以下是**策略合并补丁片段**，不是独立 DaemonSet：

```yaml
spec:
  template:
    spec:
      containers:
        - name: kube-proxy
          env:
            - name: HTTP_PROXY
              value: http://proxy.internal.example.com:3128
            - name: HTTPS_PROXY
              value: http://proxy.internal.example.com:3128
            - name: NO_PROXY
              value: localhost,127.0.0.1,::1,.svc,.cluster.local
```

审查/扩展绕过目标，并通过附加组件的所有者应用。内置 DaemonSet 策略合并使用 container/env 名称；JSON Patch `add /containers/0/env` 可能替换整个现有环境，并假定 container 索引。如果所选 CNI 替代 kube-proxy，请不要仅为此示例部署 kube-proxy。

## 验证和受控更新

| 检查 | 所需证据 | 不充分的情况 |
|---|---|---|
| 构件完整性 | 每个选定文件、校验和、已批准清单和组合均匹配 | 跳过缺失文件或接受零个已验证文件 |
| DNS/TLS | 在预期路由上正确的目标和主机名/CA 验证 | `10.*` 地址、任意 `172.*` 地址或 `curl -k` |
| S3 | 精确 bucket/key/version、预期所有者和哈希的实际授权读取 | 列出前缀或将 API 错误视为不存在 |
| ECR | 通过工作负载凭证路径实际拉取所需摘要/平台和层 | `describe-repositories` 或独立且未经身份验证的 `ctr` 调用 |
| nodeadm 配置 | 使用受保护且已填充的文件，`nodeadm config check` 成功 | 将缺失配置视为成功，或不存在的 `init --dry-run` |
| 节点运行 | 凭证刷新、Kubernetes API 信任/身份验证、CNI/DNS 和有限工作负载测试 | 成功的本地解析器检查或一次 `/healthz` 响应 |

当 AWS 读取已获授权时，请使用 `nodeadm debug --config-source file:///etc/eks/nodeconfig.yaml` 进行文档所述的连接性/身份诊断。它会联系服务，并可能输出敏感诊断上下文；请将输出保持私密，并在分享前进行敏感信息处理。不要将未知/失败的检查变为“可用于生产”。

更新自动化应**发现候选项**，然后在提升前要求来源验证、兼容性审查、OS/镜像扫描、本地验证、代表性节点金丝雀测试和批准。在新的不可变版本/构建前缀下发布，保留先前已批准组合，并记录回滚限制。不要运行会悄然覆盖生产 `latest` 键的 cron 作业；`nodeadm upgrade` 具有破坏性并需要迁移工作负载。

先前测验中的历史带宽估计——layer caching **50–80%**、compression **30–50%**、platform filtering **50%**——没有可归属的测量。仅将其作为未经验证的历史说明保留，而不是预测的节省。针对您的层复用、平台集和压缩格式测量实际字节数；不要在声称内容摘要不变的同时重新压缩已批准内容。

## 主要参考资料

- [AWS Hybrid nodeadm 参考](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [准备 Hybrid 操作系统](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [Hybrid 代理配置](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-proxy.html)
- [nodeadm v1.0.20 安装标志](https://github.com/aws/eks-hybrid/blob/v1.0.20/cmd/nodeadm/install/install.go)和 [init 标志](https://github.com/aws/eks-hybrid/blob/v1.0.20/cmd/nodeadm/init/init.go)
- [构件选择/下载实现](https://github.com/aws/eks-hybrid/blob/v1.0.20/internal/aws/source.go)和 [SSM 源代码](https://github.com/aws/eks-hybrid/blob/v1.0.20/internal/ssm/source.go)
- [S3 interface endpoints/private DNS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/privatelink-interface-endpoints.html)
- [ECR VPC endpoints](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)
- [Skopeo copy](https://github.com/containers/skopeo/blob/main/docs/skopeo-copy.1.md)
- [APT repository authentication](https://manpages.ubuntu.com/manpages/noble/man8/apt-secure.8.html)
- [DNF repository signature settings](https://github.com/rpm-software-management/dnf/blob/master/doc/conf_ref.rst)
- [S3 PutObject conditions, encryption and checksums](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)
- [Kubernetes image names, digests and pull policies](https://kubernetes.io/docs/concepts/containers/images/)

< [上一节：网络配置](./02-network-configuration.md) | [目录](./README.md) | [下一节：节点引导](./04-node-bootstrap.md) >
