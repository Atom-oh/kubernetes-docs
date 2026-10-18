# 先决条件

> **支持的版本**：示例已针对 EKS 1.36 / hybrid nodeadm 1.0.20 进行审查；以下列出特定操作系统的要求
> **上次更新**：2026 年 9 月 13 日

在加入混合节点之前，请准备好主机、网络、凭证和集群访问权限。本地架构、加密和输入检查无法验证实际物理网络、GPU 运行时或生产集群。本次审计未执行任何云、主机网络、GPU 驱动程序或映像构建更改。

![混合节点以及 VPC/本地网络的双向路由。声明远程 CIDR 并不会创建所有路由或防火墙规则。](../.gitbook/assets/en-eks-hybrid-nodes-prereq-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-eks-hybrid-nodes-prereq-0.html)

## 操作系统和运行时

| 经 AWS 验证的混合集成 | 版本 / 范围 |
|---------------------------------|------------------|
| Ubuntu | 20.04、22.04、24.04；请另行审查发行版安全维护情况 |
| RHEL | 8、9；请审查内核/CNI 以及 Red Hat 订阅/支持情况 |
| AL2023 | 本地**虚拟化**环境；不适用于通用裸机，也不代表 EC2 之外的 AWS 操作系统支持资格 |
| Bottlerocket | VMware 变体 v1.37.0+，适用于 Kubernetes 1.28+，**仅限 x86_64**；采用不同的引导流程 |

这些最低版本并不意味着较旧的 Kubernetes 版本目前仍受 EKS 支持。请选择处于活跃支持期的 EKS 版本以及匹配的操作系统/运行时/CNI 组合。AWS 支持 Ubuntu/RHEL 混合集成，但不负责供应商提供的操作系统维护。

全新安装/升级 SSM 需要 **nodeadm 1.0.19+**，因为较旧的二进制文件包含过时的 SSM 签名密钥。本次审查的版本为 **v1.0.20**。请使用混合节点 nodeadm，而不是名称相似的 EC2 EKS AMI 工具。

EKS kube-proxy 1.31+ 在 ARM 上需要 ARMv8.2+crypto。Pi 5 之前的硬件/Cortex-A72 硬件不满足此要求；仅凭 Pi 5 CPU 不能证明完整堆栈兼容。旧版 kube-proxy 1.30 解决方法的 EKS 延长支持已于 2026 年 7 月结束。

必须使用 Containerd；不需要 Docker Engine。“containerd 1.6+”或 Docker 版本检查并不能证明当前 CRI 兼容性。

| 操作系统 / 选项 | nodeadm containerd 来源 |
|-------------|--------------------------|
| Ubuntu / AL2023 | `distro` 是受支持的默认选项 |
| RHEL | 使用 `docker`，或在预装兼容运行时时使用 `none`；`distro` 无效 |
| AL2023 | 不支持 `docker` |
| 手动安装运行时 | `none` 会跳过安装；它不会提供运行时 |

Ubuntu 24.04 过去针对 Pod 终止/AppArmor 的修复需要 containerd 1.7.19+ 或相应的 AppArmor 更新。这并不是建议安装旧版本。请审查所选 CNI 的内核要求；“内核 5.4+”和盲目替换内核都不足以满足要求。

### 容量规划和主机检查

AWS 建议主机至少具备 **1 个 vCPU 和 1 GiB 内存**。实际容量需求取决于工作负载和运行配置。

请根据容器运行时、CNI、管理代理和工作负载的总使用量规划 CPU 和内存。请为操作系统、容器映像和日志预留磁盘空间，并留出充足的运行余量。

```bash
# Run these read-only checks on the intended hybrid host.
cat /etc/os-release
uname -m
uname -r
free -h
df -h /
swapon --show
ip -j link show
# When already installed, inspect the actual CRI runtime:
containerd --version
```

二进制文件版本无法证明 kubelet 使用了该运行时套接字。请与主机所有者一起审查交换空间、cgroups、转发、CNI 模块和防火墙。对所有受支持的主机一律执行 swapoff/fstab/sysctl/MTU 修改并不具备通用性。

### 安装、验证，然后初始化

对于已准备好的 Ubuntu/AL2023 主机，以下顺序会在加入之前安装依赖项。RHEL 需要使用上述运行时来源；Bottlerocket 则使用不同流程。

```bash
set -euo pipefail
# Installation/bootstrap sequence for prepared Ubuntu/AL2023 hosts.
# RHEL requires --containerd-source docker, or none with a preinstalled compatible runtime.
# These commands mutate the host; review OS/runtime/network/identity first.
sudo nodeadm install 1.36 --credential-provider ssm --containerd-source distro \
  --region ap-northeast-2 --timeout 20m
sudo nodeadm config check -c file:///etc/eks/nodeConfig.yaml
sudo nodeadm init -c file:///etc/eks/nodeConfig.yaml
```

节点配置必须预先包含预期的集群/提供商输入。请将包含凭证的配置文件权限设为 0600，并确保激活码不会进入黄金映像和日志。这些命令会修改主机。不要通过跳过验证阶段来掩盖故障。`nodeadm upgrade` 会造成中断，且需要先疏散工作负载。

## Packer 映像准备

AWS 示例涵盖 Ubuntu 22.04/24.04 和 RHEL 8/9，并使用 vSphere OVA 和 QEMU qcow2/raw 目标。本次审查的 **v1.0.20 模板并不是可直接用于 EKS 1.36 的映像流水线**：

- `K8S_VERSION` 验证仍只允许 1.26–1.31。请维护经过审查的当前分支；不要为了满足示例而降级。
- `NODEADM_ARCH` 期望值为 **`amd` 或 `arm`**，随后会追加 `64`；原来的 `amd64` 会变成 `amd6464`。
- Packer 的 `CREDENTIAL_PROVIDER=iam` 会映射到 nodeadm 的 **`iam-ra`**。
- 实际文件是 `hybrid-nodes-template.pkr.hcl`；不存在 `general-build.qemu.al2023` 源。
- 请审查可变的 `releases/latest` 下载、vSphere 的 `insecure_connection=true`、默认构建器密码以及全局变量要求。RHEL 配置程序将 x86 仓库硬编码在内；仅更改二进制文件架构并不能构建 ARM 映像。

| 输入组 | 审查内容 |
|-------------|--------|
| 工具 | Packer ≥1.11、vSphere 插件 ≥1.4 或 QEMU 1.x；请固定经过测试的组合 |
| 通用 | `ISO_URL`、已验证的 `ISO_CHECKSUM`、`PKR_SSH_PASSWORD`、`K8S_VERSION`、`NODEADM_ARCH`、`CREDENTIAL_PROVIDER` |
| RHEL | `RH_USERNAME`、`RH_PASSWORD`、`RHEL_VERSION`；请勿将机密留在最终映像/日志中 |
| vSphere | 服务器/用户名/密码、数据中心、集群、数据存储、网络、**VSPHERE_OUTPUT_FOLDER** |
| QEMU | **PACKER_OUTPUT_FORMAT**（`qcow2`/`raw`）、CPU/虚拟化兼容性 |

源代码还包含会产生费用的 AWS AMI 构建器；这并不意味着可以将云主机作为混合节点运行。请验证受维护的模板和生成的映像。本次未执行 Packer/虚拟机映像构建。

## GPU 兼容性

请综合检查 GPU 变体、CPU 架构、操作系统/内核、受支持的 NVIDIA 驱动程序、容器工具包/运行时、CUDA/框架映像和内存。此前的驱动程序 525/535/545/550 和 CUDA 11.8/12.x 数值混合了历史最低要求和建议值；它们并非适用于所有情况的当前 Hybrid Nodes 要求。

H100 80GB、H200 141GB、A100 40/80GB 和 L40S 48GB 仅为示例变体，并非完整的认证列表。对所有模型而言，4 GB 都不能算作有意义的最低要求。要运行封装正确的 GPU 容器，并不需要主机安装 CUDA 编译器；驱动程序和编译器版本代表不同的内容。

```bash
# On a host where the driver is already installed:
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
# Optional: nvcc reports the locally installed compiler, if present.
if command -v nvcc >/dev/null 2>&1; then nvcc --version; fi
```

请遵循所选组合当前的 NVIDIA 兼容性/平台说明。请先在已清空工作负载的测试主机上试运行驱动程序/内核更改。在运行中的工作节点安装旧版驱动程序分支或重启 containerd 并非无害的先决条件检查。

## 网络、CIDR 和 MTU

Hybrid Nodes 需要可靠的**私有双向连接**，包括控制平面访问 kubelet 和托管在混合节点上的 webhook。公开 API 访问会改变节点→API 的流量，但不会改变所需的私有反向路径。

AWS 建议将 **100 Mbps 带宽和不超过 200ms 的 RTT** 作为一般连接指导。请根据工作负载需求设定带宽、延迟和丢包目标，并通过实际连接路径进行测量。设置 MTU 时，请考虑隧道封装开销以及路径中设备支持的大小。

远程节点/Pod CIDR 使用 IPv4 RFC1918 或 CGNAT 地址，彼此之间不得与 VPC 或 Service 网络重叠。每种远程 CIDR 最多可有 15 个，并放入**一个** remote-node-network 和**一个** remote-pod-network 包装对象中。跨集群 Pod 路由也需要有计划地进行隔离。

请保存经过审查的 `network-plan.json`：

```json
{
  "vpcCidrs": [
    "10.0.0.0/16"
  ],
  "serviceCidrs": [
    "10.100.0.0/16"
  ],
  "remoteNodeCidrs": [
    "10.80.0.0/16"
  ],
  "remotePodCidrs": [
    "10.85.0.0/16"
  ]
}
```
```bash
: "${NETWORK_PLAN_JSON:?Set the reviewed local network plan JSON}"
export NETWORK_PLAN_JSON
python3 - <<'PY'
import ipaddress, itertools, json, os
from pathlib import Path
plan = json.loads(Path(os.environ["NETWORK_PLAN_JSON"]).read_text())
allowed = [ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]
groups = {}
for key in ("vpcCidrs", "serviceCidrs", "remoteNodeCidrs", "remotePodCidrs"):
    values = plan[key]
    if not isinstance(values, list) or not values:
        raise SystemExit(f"{key} must be a nonempty list for this example")
    groups[key] = [ipaddress.ip_network(v, strict=True) for v in values]
    if any(n.version != 4 for n in groups[key]):
        raise SystemExit("This Hybrid Nodes plan requires IPv4")
for key in ("remoteNodeCidrs", "remotePodCidrs"):
    if len(groups[key]) > 15 or any(not any(n.subnet_of(a) for a in allowed) for n in groups[key]):
        raise SystemExit("Remote CIDRs must use RFC1918/CGNAT ranges, at most 15 per kind")
flat = [(key, n) for key, networks in groups.items() for n in networks]
for (ka, a), (kb, other) in itertools.combinations(flat, 2):
    if a.overlaps(other):
        raise SystemExit(f"Overlapping CIDRs: {ka} {a}, {kb} {other}")
print("CIDR syntax/range/non-overlap checks passed; routing and reachability remain unverified")
PY
```

此检查只验证语法/范围/重叠情况，不验证可达性。请通过实际 TGW/VGW 配置 VPC 返回路由，并配置本地网络返回路由/逐节点 Pod 路由。

| 流量 | 审查内容 |
|------|--------|
| 远程节点/Pod → API TCP443 | 为目标 CIDR 添加额外的集群 SG 入站规则 |
| 控制平面 ENI → 节点 TCP10250 | 受限的集群出站规则、私有路由以及本地主机/防火墙入站规则 |
| 控制平面 → webhook | 实际 Pod IP、端口、路由和防火墙 |
| 主机/Pod → 凭证/映像/DNS/时间 | 提供商端点、注册表、DNS 和时钟同步 |

TCP10250 并不是进入 API-server SG 的 kubelet 入站流量。EKS 不会单独创建所有自定义远程规则；eksctl 可能会自动配置其拥有的 VPC 侧资源。请检查实际规则配额，不要将 60 当作不可变的上限。

AWS 建议仅使用公开端点或仅使用私有端点。如果两者都启用，VPC 外部的节点会解析为公开地址；如果路径/访问规则不同，**可能**无法加入集群。这并非 API 一概拒绝。仅使用私有端点时，也需要私有 DNS 和管理访问能力。

## 提供商专用凭证

请使用预期的管理员身份准备 AWS 输入。将激活材料存放在私有目录中：

```bash
set -euo pipefail
: "${EXPECTED_ACCOUNT_ID:?Set the intended account}"
: "${AWS_REGION:?Set the intended Region}"
: "${CLUSTER_NAME:?Set the intended cluster}"
check_account() {
  local actual
  actual=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text) || return
  test "$actual" = "$EXPECTED_ACCOUNT_ID" || { printf 'Account mismatch.\n' >&2; return 1; }
}
check_account
umask 077
export WORK_DIR
WORK_DIR=$(mktemp -d "$PWD/hybrid-preflight.XXXXXXXX")
export EXPECTED_ACCOUNT_ID AWS_REGION CLUSTER_NAME
printf 'Private preparation directory: %s\n' "$WORK_DIR"
```

SSM 和 Roles Anywhere 都需要连接 AWS。本地 CA 或更长的缓存凭证并不能创建离线控制平面。

### SSM 角色和激活

该角色需要 `eks:DescribeCluster`、ECR 拉取权限以及 SSM core/cleanup 权限。**仅有 AmazonEKSWorkerNodeMinimalPolicy 并不包含 DescribeCluster。**Pod Identity 的 `eks-auth:AssumeRoleForPodIdentity` 权限是单独的。

请一致地替换示例中的账户/区域/集群值。以下列表操作缺少针对单个实例的资源范围限制，因此其通配符仅限于目标区域：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ssm.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "123456789012"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:ssm:ap-northeast-2:123456789012:*"
        }
      }
    }
  ]
}
```
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "eks:DescribeCluster",
      "Resource": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DescribeInstanceInformation",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DeregisterManagedInstance",
      "Resource": "arn:aws:ssm:ap-northeast-2:123456789012:managed-instance/*",
      "Condition": {
        "StringEquals": {
          "ssm:resourceTag/EKSClusterARN": "arn:aws:eks:ap-northeast-2:123456789012:cluster/my-hybrid-cluster"
        }
      }
    }
  ]
}
```

附加经过审查的 `AmazonEC2ContainerRegistryPullOnly` 和 `AmazonSSMManagedInstanceCore` 策略或等效权限。激活的 `EKSClusterARN` 标签必须与注销策略匹配。

请为注册设置合理的限制，并将 24 小时设为**注册**有效期：

```bash
: "${HYBRID_ROLE_NAME:?Use the reviewed SSM-trusting role name}"
: "${REGISTRATION_LIMIT:?Set a deliberate node registration limit}"
export HYBRID_ROLE_NAME REGISTRATION_LIMIT
python3 - <<'PY'
import json, os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
account, region, cluster = (os.environ[k] for k in ("EXPECTED_ACCOUNT_ID", "AWS_REGION", "CLUSTER_NAME"))
if not re.fullmatch(r"\d{12}", account) or not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
    raise SystemExit("Invalid account/Region")
if region.startswith(("cn-", "us-gov-")):
    raise SystemExit("Hybrid Nodes is not available in this Region family")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", cluster):
    raise SystemExit("Invalid cluster name")
role = os.environ["HYBRID_ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Use the actual IAM role name, not a role ARN")
limit = int(os.environ["REGISTRATION_LIMIT"])
if not 1 <= limit <= 1000:
    raise SystemExit("RegistrationLimit must be 1..1000 per activation; review service quotas separately")
body = {"DefaultInstanceName": "eks-hybrid-node", "IamRole": role, "RegistrationLimit": limit,
        "Description": "Reviewed EKS hybrid activation",
        "Tags": [{"Key": "EKSClusterARN", "Value": f"arn:aws:eks:{region}:{account}:cluster/{cluster}"}],
        "ExpirationDate": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()}
(Path(os.environ["WORK_DIR"]) / "activation-request.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```
```bash
set -euo pipefail
# Run only after the role/trust/tag policy and registration scope are prepared.
check_account
aws ssm create-activation --region "$AWS_REGION" \
  --cli-input-json "file://$WORK_DIR/activation-request.json" --output json \
  > "$WORK_DIR/activation-response.json"
chmod 600 "$WORK_DIR/activation-response.json"
# The response contains the secret ActivationCode. Do not print or commit it.
```

ActivationCode 只会返回一次；请通过安全方式分发它和 ActivationId。激活过期/删除并不会注销已有的托管实例。[CreateActivation RegistrationLimit](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_CreateActivation.html) 仍规定每个激活的范围为 1–1,000。它不是整个实例队列的免费套餐门槛；当前定价请参阅[凭证提供商比较](README.md#credential-providers)。

SSM 使用 `mi-...` 节点名称和固定的一小时凭证。网络中断后，刷新退避机制可能会延迟重新连接。请勿记录凭证。

### Roles Anywhere 信任和持续时间

请使用适合该提供商的角色、信任锚和配置文件。应将会话名称绑定到证书身份/nodeName；此前的 PrincipalTag/RequestTag 比较并未做到这一点。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": [
        "sts:TagSession",
        "sts:SetSourceIdentity"
      ],
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        }
      }
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "rolesanywhere.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:rolesanywhere:ap-northeast-2:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555"
        },
        "StringEquals": {
          "sts:RoleSessionName": "${aws:PrincipalTag/x509Subject/CN}"
        }
      }
    }
  ]
}
```
```json
{
  "name": "hybrid-node-profile",
  "roleArns": [
    "arn:aws:iam::123456789012:role/EKSHybridNodeRole"
  ],
  "enabled": true,
  "acceptRoleSessionName": true,
  "durationSeconds": 3600
}
```

请替换信任锚 ARN，授予范围受限的 DescribeCluster/ECR 权限，并设置 **acceptRoleSessionName=true**。

```text
effectiveDuration = min(profileDuration, requestedDuration)
                    or profileDuration when the request omits duration
effectiveDuration <= role.MaxSessionDuration
```

请求/配置文件持续时间范围为 900–43,200 秒。CreateSession **允许相等**：配置文件为 3,600、未覆盖请求值、角色最大值为 3,600，都是有效的。此前关于“必须大于”的严格说法不准确。证书有效性/吊销检查以及 AWS 可达性仍是必要条件。

### 每个节点的密钥和证书

请在预期的新节点上使用私有目录。生成唯一密钥/CSR；此示例接受简单的小写 DNS 标签。请将 CSR 发送给获准的签发机构；不要将 CA 签名密钥放在节点上。

```bash
set -euo pipefail
umask 077
: "${WORK_DIR:?Set a private preparation directory on this node}"
: "${NODE_NAME:?Use a unique certificate CN / node name}"
export NODE_NAME
python3 - <<'PY'
import os, re
name = os.environ["NODE_NAME"]
if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]", name):
    raise SystemExit("This example requires a lowercase DNS label of 2..63 characters")
PY
test ! -e "$WORK_DIR/node.key"
test ! -e "$WORK_DIR/node.csr"
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$WORK_DIR/node.key"
chmod 600 "$WORK_DIR/node.key"
openssl req -new -key "$WORK_DIR/node.key" -out "$WORK_DIR/node.csr" -subj "/CN=$NODE_NAME"
# Send the CSR to the approved PKI issuer; do not copy its CA private key to nodes.
```

请验证颁发的证书链、获准的 CA、有效期/吊销状态、密钥匹配情况和 CN。请保持时钟同步。仅适用于新节点：

```bash
set -euo pipefail
: "${ISSUED_NODE_CERT:?Set the verified certificate/chain issued for this node}"
: "${WORK_DIR:?Set the private directory containing the node key}"
# New-node installation only; do not overwrite an existing identity.
sudo test ! -e /etc/iam/pki/server.key
sudo test ! -e /etc/iam/pki/server.pem
sudo install -d -m 0700 /etc/iam/pki
sudo install -m 0644 "$ISSUED_NODE_CERT" /etc/iam/pki/server.pem
sudo install -m 0600 "$WORK_DIR/node.key" /etc/iam/pki/server.key
```

这些文件不是 EKS Kubernetes API CA 文件。请勿将节点身份克隆到映像中，也不要在不提示的情况下覆盖现有密钥。

## CloudFormation 准备

固定到 v1.0.20 的模板是配置资源的起点。SSM 模板会创建角色，**不会创建激活**。在用于多个集群之前，请审查范围较宽的 DescribeCluster 权限和固定导出名称。

IRA 的 `CertAttributeTrustPolicy` 值是字面值 **`${aws:PrincipalTag/x509Subject/CN}`**，而不是 `"CN"`。以下 Python `cryptography` 辅助程序会正确序列化 PEM，并检查基本 CA 形态/当前有效性，但不会验证签发者权限或吊销状态：

```bash
: "${CA_PEM_FILE:?Set the approved CA certificate file, not a private key}"
: "${ROLE_NAME:?Set the new role name selected by the IaC owner}"
export CA_PEM_FILE ROLE_NAME
python3 - <<'PY'
import json, os, re
from pathlib import Path
from cryptography import x509
from datetime import datetime, timezone
raw = Path(os.environ["CA_PEM_FILE"]).read_bytes()
if b"PRIVATE KEY" in raw or raw.count(b"-----BEGIN CERTIFICATE-----") != 1:
    raise SystemExit("Provide one reviewed CA certificate")
cert = x509.load_pem_x509_certificate(raw)
if not cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
    raise SystemExit("Certificate is not a CA")
now = datetime.now(timezone.utc)
if not cert.not_valid_before.replace(tzinfo=timezone.utc) <= now <= cert.not_valid_after.replace(tzinfo=timezone.utc):
    raise SystemExit("CA certificate is not currently valid")
role = os.environ["ROLE_NAME"]
if not re.fullmatch(r"[\w+=,.@-]{1,64}", role, re.ASCII):
    raise SystemExit("Invalid IAM role name")
body = [
    {"ParameterKey": "RoleName", "ParameterValue": role},
    {"ParameterKey": "CertAttributeTrustPolicy", "ParameterValue": "${aws:PrincipalTag/x509Subject/CN}"},
    {"ParameterKey": "CABundleCert", "ParameterValue": raw.decode("ascii")}
]
(Path(os.environ["WORK_DIR"]) / "cfn-iamra-parameters.json").write_text(json.dumps(body, indent=2) + "\n")
PY
```

请由 IaC 负责人对照固定版本的模板检查参数键/AllowedValues、权限范围和命名空间导出，然后审查变更集。不要部署格式错误的 PEM 简写或未经审查的可变 main 分支模板。

## 集群访问和创建方案

请优先为节点 IAM 角色使用 **HYBRID_LINUX 访问条目**：

```json
{
  "clusterName": "my-hybrid-cluster",
  "principalArn": "arn:aws:iam::123456789012:role/EKSHybridNodeRole",
  "type": "HYBRID_LINUX"
}
```

该映射使用 `system:node:{{SessionName}}` 和节点引导组。请确认 API/API_AND_CONFIG_MAP 身份验证模式和所有权。不要应用会清除现有映射的替代型单角色 `aws-auth` ConfigMap；对旧版映射的更改需要受控迁移。

请将下面的所有标识符替换为经过审查的现有资源。明确指定了仅私有端点、IPv4 和版本 1.36。引导创建者的管理员权限适用于受控实验环境；请谨慎决定生产环境操作人员的访问权限。

对于 eksctl 0.229.0，请使用文档规定的 **SSM/IRA** 提供商值。使用提供的 roleARN 时，请单独准备提供商资源：

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-hybrid-cluster
  region: ap-northeast-2
  version: '1.36'
iam:
  serviceRoleARN: arn:aws:iam::123456789012:role/EKSClusterRole
accessConfig:
  authenticationMode: API_AND_CONFIG_MAP
  bootstrapClusterCreatorAdminPermissions: true
kubernetesNetworkConfig:
  ipFamily: IPv4
  serviceIPv4CIDR: 10.100.0.0/16
vpc:
  id: vpc-0123456789abcdef0
  subnets:
    private:
      ap-northeast-2a:
        id: subnet-0123456789abcdef0
      ap-northeast-2c:
        id: subnet-0123456789abcdef1
  controlPlaneSecurityGroupIDs:
  - sg-0123456789abcdef0
  clusterEndpoints:
    privateAccess: true
    publicAccess: false
remoteNetworkConfig:
  iam:
    provider: SSM
    roleARN: arn:aws:iam::123456789012:role/EKSHybridNodeRole
  vpcGatewayID: tgw-0123456789abcdef0
  remoteNodeNetworks:
  - cidrs:
    - 10.80.0.0/16
  remotePodNetworks:
  - cidrs:
    - 10.85.0.0/16
```

使用 eksctl 配置资源时，请使用 `--without-nodegroup` 和明确指定的私有 kubeconfig 路径。架构有效并不能证明 IAM、路由或网关可达性正常。旧版 eksctl 中仅描述集群启动的文档已过时：当前 EKS 支持通过相应 API 工作流为现有集群配置混合远程网络。

等效的 EKS CreateCluster 请求：

```json
{
  "name": "my-hybrid-cluster",
  "version": "1.36",
  "roleArn": "arn:aws:iam::123456789012:role/EKSClusterRole",
  "resourcesVpcConfig": {
    "subnetIds": [
      "subnet-0123456789abcdef0",
      "subnet-0123456789abcdef1"
    ],
    "securityGroupIds": [
      "sg-0123456789abcdef0"
    ],
    "endpointPrivateAccess": true,
    "endpointPublicAccess": false
  },
  "kubernetesNetworkConfig": {
    "ipFamily": "ipv4",
    "serviceIpv4Cidr": "10.100.0.0/16"
  },
  "accessConfig": {
    "authenticationMode": "API_AND_CONFIG_MAP",
    "bootstrapClusterCreatorAdminPermissions": true
  },
  "remoteNetworkConfig": {
    "remoteNodeNetworks": [
      {
        "cidrs": [
          "10.80.0.0/16"
        ]
      }
    ],
    "remotePodNetworks": [
      {
        "cidrs": [
          "10.85.0.0/16"
        ]
      }
    ]
  }
}
```

请选择一个基础设施管理方；不要同时执行两条路径。在加入主机之前，请验证真实集群/端点身份、操作人员权限和节点访问。这些 AWS 示例标识符并非经过验证的资源。

## 附加组件

以下有文档记录的混合兼容性最低版本**并非**适用于每个 Kubernetes 版本的安装目标：

| 附加组件 | 混合兼容性最低版本 |
|--------|-----------------------------|
| kube-proxy / CoreDNS | 1.25.14-eksbuild.2 / 1.9.3-eksbuild.7 |
| ADOT / CloudWatch Observability | 0.102.1-eksbuild.2 / 2.2.1-eksbuild.1 |
| Pod Identity Agent | 通常为 1.3.3-eksbuild.1；**Bottlerocket 上为 1.3.7-eksbuild.2**，并且还要求 **Bottlerocket OS 1.39.0+** |
| 节点监控 / snapshot controller | 1.2.0-eksbuild.1 / 8.1.0-eksbuild.2 |
| Private CA Connector / FSx CSI / Secrets Store provider | 1.6.0-eksbuild.1 / 1.7.0-eksbuild.1 / 2.1.1-eksbuild.1 |
| Metrics Server / cert-manager | 0.7.2-eksbuild.1 / 1.17.2-eksbuild.1 |
| Node Exporter / kube-state-metrics / External DNS | 1.9.1-eksbuild.2 / 2.15.0-eksbuild.4 / 0.19.0-eksbuild.1 |

```bash
check_account
: "${ADDON_NAME:?Select one add-on to review}"
aws eks describe-addon-versions --region "$AWS_REGION" --addon-name "$ADDON_NAME" \
  --kubernetes-version 1.36 --output json > "$WORK_DIR/addon-catalog.json"
jq '[.addons[].addonVersions[] |
     {addonVersion,architecture,computeTypes,compatibilities}]' "$WORK_DIR/addon-catalog.json"
```

请审查所选版本的混合/操作系统/内核配置。VPC CNI 不管理混合节点；请配置兼容的 CNI，并确保仅将代理放置在云端。目录中存在某项附加组件，并不能证明它已安装或就绪。

## 参考资料

- [混合节点先决条件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-prereqs.html)
- [操作系统和 nodeadm 最低版本](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-os.html)
- [nodeadm 参考](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-nodeadm.html)
- [混合网络](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-networking.html)
- [凭证和 Hybrid Nodes IAM 角色](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-creds.html)
- [断开连接期间的主机凭证](https://docs.aws.amazon.com/eks/latest/best-practices/hybrid-nodes-host-creds.html)
- [IAM Roles Anywhere CreateSession](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-create-session.html)
- [受支持的混合附加组件](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-add-ons.html)
- [eksctl 混合配置](https://docs.aws.amazon.com/eks/latest/eksctl/hybrid-nodes.html)
- [已发布的 nodeadm v1.0.20](https://github.com/aws/eks-hybrid/releases/tag/v1.0.20)
- [固定版本的 Packer 源代码](https://github.com/aws/eks-hybrid/tree/v1.0.20/example/packer)
- [固定版本的 SSM CloudFormation 模板](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ssm-cfn.yaml)
- [固定版本的 Roles Anywhere CloudFormation 模板](https://github.com/aws/eks-hybrid/blob/v1.0.20/example/hybrid-ira-cfn.yaml)
- [NVIDIA CUDA 兼容性](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [NVIDIA Container Toolkit 安装](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)


< [目录](./README.md) | [下一步：网络配置](02-network-configuration.md) >
