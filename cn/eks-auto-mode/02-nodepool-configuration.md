# NodePool 配置与优化

> **支持的版本**：EKS Auto Mode GA；示例基线 EKS 1.36
> **最后更新**：2026 年 9 月 12 日

本章区分 AWS 托管默认值、自定义 NodePool 约束以及 AWS 专属的 NodeClass API。请先完成[入门](./01-getting-started.md)，使用预期的账户/上下文，并在应用模板前检查所有 IAM/配置文件名称和网络标签。此处显示的容量限制仅供参考，仍可能产生大量费用。

这些 NodePool 示例已根据已发布的 Karpenter 1.14.1 CRD 结构架构进行检查；AWS 专属的 NodeClass 字段已与 AWS 文档进行比对。这并不能确定 Auto Mode 内部控制器的版本，也不能证明其在实时集群中能够通过准入检查或达到就绪状态。本次审查期间未预置任何节点。

## 了解内置 NodePool

启用 Auto Mode 后，它会提供以下 NodePool。这些由 AWS 托管；请创建自定义 NodePool，而不是编辑其托管配置。

| NodePool | 架构 | 容量和实例选择 | 用途 |
|------|--------------|----------------------------------|---------|
| `general-purpose` | `amd64` | 按需，C/M/R 系列，第 5 代或更新版本 | 通用工作负载 |
| `system` | `amd64` 和 `arm64` | 按需，C/M/R 系列，第 5 代或更新版本 | 可容忍 `CriticalAddonsOnly` 的集群关键工作负载 |

内置的通用 NodePool **不会**启用 Spot。需要 Spot 或不同的架构/实例约束时，请使用自定义 NodePool。Auto Mode 提供节点本地 DNS 和服务网络功能；纯 Auto Mode 集群无需仅为填充 system 池而运行普通的 CoreDNS/kube-proxy Pod。混合集群仍需要传统的 CoreDNS Deployment 为非 Auto 节点提供服务。

请检查实际的托管对象以查看中断设置和污点详情，不要套用猜测的默认 YAML：

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

AWS 至少需要启用一个内置 NodePool 才会提供 `default` NodeClass。如果两个池都已禁用，请创建自己的 NodeClass，并更新下方的引用。从 `computeConfig.nodePools` 中移除内置池名称会删除该池并排空/终止其节点；这并非只是让新工作负载看不到该池。

## 创建自定义 NodePool

这些示例引用现有的 `default` NodeClass，以便聚焦于调度约束。若要使用本章后面的自定义 NodeClass，请先创建它，然后更改目标 NodePool 中的 `nodeClassRef.name`。`template` 下的所有标签和污点都会应用于新节点；仅添加在 NodePool 元数据上的标签不会给节点打标签。

### 计算优化型工作负载

代数条件 `Gt ["6"]` 允许第 7 代及更新版本，并非只选择最新一代。该示例允许使用 x86 C 系列按需实例，并且此池的预置优先级高于内存优化示例。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
  labels:
    workload-type: compute-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: compute-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '6'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - xlarge
        - 2xlarge
        - 4xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '1000'
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
  weight: 10
```

### 内存优化型工作负载

该示例允许使用第 6 代及更新版本的 R 系列实例，架构不限。你的容器镜像和应用依赖项必须支持调度器所选择的架构。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: memory-optimized
  labels:
    workload-type: memory-intensive
spec:
  template:
    metadata:
      labels:
        workload-type: memory-intensive
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - r
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '5'
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - 2xlarge
        - 4xlarge
        - 8xlarge
        - 12xlarge
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '500'
    memory: 8000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
  weight: 5
```

## 配置 AWS NodeClass

Auto Mode 使用 `eks.amazonaws.com/v1` 和 `NodeClass` 类型。其字段不同于自托管的 AWS Karpenter `EC2NodeClass`：不要将 `amiFamily`、`blockDeviceMappings`、任意 shell `userData` 或 `metadataOptions` 复制到此 API 中。AWS 会选择其托管的 Bottlerocket 变体。

将以下内容保存为 `custom-nodeclass.yaml`，并将示例配置文件和选择器值替换为经过审查的资源。支持 `instanceProfile`；其名称必须以 `eks` 开头。也可以将 `role` 设置为节点 IAM 角色名称。**`role` 和 `instanceProfile` 必须恰好指定其中一个。** 配置文件中包含的角色需要相应的 Auto Mode EKS 访问条目和权限；重复使用已配置的角色无需添加重复条目。对于新角色，请按照 AWS NodeClass 参考中的访问条目流程操作。

子网标签用于选择资源，但不会建立路由或隔离。请验证 VPC、AZ 可用性、路由表和安全组规则。`associatePublicIPAddress: false` 会阻止分配公有 IP；节点仍需要适当的出站连接。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: custom-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      kubernetes.io/role/internal-elb: '1'
      Environment: production
  securityGroupSelectorTerms:
  - tags:
      kubernetes.io/cluster/my-cluster: owned
      Type: worker-node
  ephemeralStorage:
    size: 100Gi
    iops: 3000
    throughput: 125
  advancedNetworking:
    associatePublicIPAddress: false
  advancedCompute:
    kernel:
      sysctl:
        vm.max_map_count: 262144
  tags:
    Environment: production
    ManagedBy: eks-auto-mode
```

请确认集群角色可以使用 `spec.tags` 中的任何自定义键创建资源并为其添加标签；NodeClass 本身不会授予 IAM 权限。

`ephemeralStorage` 配置的是节点临时存储，而不是任意块设备映射。`100Gi` 大小以及 3000 IOPS/125 MiB/s 设置仅为示例；请检查当前 Auto Mode 字段限制、实例存储行为和成本。客户 KMS 配置应放在 `ephemeralStorage.kmsKeyID`，并应用于节点的根/数据 **EBS** 卷。它不会选择本地 NVMe 实例存储加密所用的密钥，也不会为应用 PVC 配置加密。

旧版引导示例修改了 `vm.max_map_count`。受支持的替代方式是使用 `advancedCompute.kernel.sysctl`，并在节点启动时应用。更改受支持的内核设置会将现有节点标记为需要漂移/替换；这不是立即进行的原地 shell 更新。仅在工作负载需要该设置时进行配置，并检查中断行为。

### 固定的 IMDS 安全配置

Auto Mode 强制使用 IMDSv2 和跳数限制 1；无法通过 NodeClass 更改这些默认值。普通的非 host-network Pod 无法通过该路径访问 IMDS，但这并不意味着 Pod 一定完全隔离：`hostNetwork` 会改变可达性。应用访问 AWS 时优先使用工作负载身份，并显式提供区域或其他配置，而不要依赖节点元数据。

### 客户 KMS、CA 证书包和独立 Pod 网络

不要将截断的证书粘贴到清单中。此可选生成器会读取经过审查的基础模板，检查获批的公有 PEM 证书包，将其进行 base64 编码并写入 `certificateBundles[].data`，然后生成完整的第二个 NodeClass。它需要安装 PyYAML 的 Python 3。请设置 `NODE_KMS_KEY_ARN` 和 `CA_BUNDLE_FILE`，并保留上一章中经过审查的 `AWS_REGION`/`EXPECTED_ACCOUNT_ID`。

请分别批准 CA 颁发者、指纹和有效期。以下语法检查不能证明可信度、KMS 权限或云资源是否存在。应用生成结果前，请检查密钥策略/IAM 授权以及 Pod 网络标签选择。

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed cluster region}"
: "${EXPECTED_ACCOUNT_ID:?Set the intended AWS account}"
: "${NODE_KMS_KEY_ARN:?Set the approved same-region customer-managed KMS key ARN}"
: "${CA_BUNDLE_FILE:?Set the path to an approved public CA PEM bundle}"
export AWS_REGION EXPECTED_ACCOUNT_ID NODE_KMS_KEY_ARN CA_BUNDLE_FILE
umask 077
python3 - <<'PY'
import base64, json, os, re, ssl
from pathlib import Path
import yaml

doc = yaml.safe_load(Path("custom-nodeclass.yaml").read_text())
if doc.get("kind") != "NodeClass" or doc.get("apiVersion") != "eks.amazonaws.com/v1":
    raise SystemExit("Expected the reviewed Auto Mode NodeClass template")
spec = doc["spec"]
if ("role" in spec) == ("instanceProfile" in spec):
    raise SystemExit("Set exactly one reviewed role or instanceProfile")
key = os.environ["NODE_KMS_KEY_ARN"]
prefix = "arn:aws:kms:" + os.environ["AWS_REGION"] + ":" + os.environ["EXPECTED_ACCOUNT_ID"] + ":key/"
if not key.startswith(prefix) or not re.fullmatch(r"(?:[a-f0-9-]{36}|mrk-[a-f0-9]{32})", key[len(prefix):]):
    raise SystemExit("KMS key ARN must match the reviewed account and region")
pem = Path(os.environ["CA_BUNDLE_FILE"]).read_bytes()
if b"PRIVATE KEY" in pem:
    raise SystemExit("Use public CA certificates only, never a private key")
ssl.create_default_context().load_verify_locations(cadata=pem.decode("ascii"))
doc["metadata"]["name"] = "secure-network-nodeclass"
spec["ephemeralStorage"]["kmsKeyID"] = key
spec["certificateBundles"] = [{"name": "corporate-ca",
                               "data": base64.b64encode(pem).decode("ascii")}]
spec["podSubnetSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
spec["podSecurityGroupSelectorTerms"] = [{"tags": {"Purpose": "pod-network"}}]
Path("secure-network-nodeclass.json").write_text(json.dumps(doc, indent=2) + "\n")
PY
```

| 字段 | 含义 |
|-------|---------|
| `ephemeralStorage.kmsKeyID` | 用于节点根/数据 EBS 卷的客户托管密钥；请使用集群所在区域的密钥 |
| `certificateBundles[].data` | 用于节点信任的 base64 编码证书包；它不会自动更改每个应用的容器信任存储 |
| `podSubnetSelectorTerms` | 为此 NodeClass 选择的独立 Pod 子网 |
| `podSecurityGroupSelectorTerms` | Pod 网络安全组；应与 Pod 子网选择器一起配置 |

Pod 子网和安全组选择器必须同时配置，并且 VPC/AZ 覆盖范围必须兼容。此配置针对每个 NodeClass，而非每个命名空间或 ServiceAccount。host-network 流量使用节点网络；出口 SNAT 也可能改变源地址和适用的安全组。在声称所有流量都已隔离之前，请检查路由、SNAT 和 Pod 密度所带来的影响。

## 隔离工作负载和环境

### 前端和后端池

污点会阻止没有匹配容忍度的 Pod 调度到这些节点上。容忍度只允许调度；如果工作负载必须使用指定节点，还要添加选择器或必需的亲和性。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend
spec:
  template:
    metadata:
      labels:
        workload-tier: frontend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
        - on-demand
      taints:
      - key: workload-tier
        value: frontend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 400Gi
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: backend
spec:
  template:
    metadata:
      labels:
        workload-tier: backend
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
        - r
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      taints:
      - key: workload-tier
        value: backend
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  weight: 10
  limits:
    cpu: '100'
    memory: 800Gi
```

例如，创建一个归你管理的 `nodepool-lab` 命名空间，并在前端放置检查中同时使用选择器和容忍度：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend-placement-check
  namespace: nodepool-lab
spec:
  automountServiceAccountToken: false
  nodeSelector:
    workload-tier: frontend
  tolerations:
  - key: workload-tier
    operator: Equal
    value: frontend
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
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
      periodSeconds: 5
```

应用前请先检查：此 Pod 可能触发需要付费的节点预置。请检查其分配到的节点、就绪状态和节点标签，然后从该命名空间删除测试 Pod。`NoSchedule` 不会驱逐已在运行的 Pod；仅靠标签/污点也无法在不可信租户之间建立安全边界。

### 开发池

AWS 当前支持的实例列表包括 T 系列突增型实例和 M 系列实例。不要仅根据旧版 Auto Mode 假设就移除 T 系列。Auto Mode 要求 CPU 数量大于 1，并排除 nano/micro/small 规格；仍需验证区域内的实例类型可用性、CPU 积分行为和工作负载适用性。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: dev-pool
spec:
  template:
    metadata:
      labels:
        environment: development
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - t
        - m
      - key: eks.amazonaws.com/instance-size
        operator: In
        values:
        - medium
        - large
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      taints:
      - key: environment
        value: development
        effect: NoSchedule
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
  limits:
    cpu: '100'
    memory: 400Gi
  weight: 1
```

## 资源限制、权重和验证

`limits.cpu` 和 `limits.memory` 限制的是池中资源总量；它们不是节点数量上限，也不是货币预算。CPU 数量应使用引号括起，以避免 GitOps 中出现整数/字符串漂移。例如，`memory: 4000Gi` 是 4000 GiB（约 3.91 TiB），并非恰好 4 TB。

上游 Karpenter 文档指出，最终一致性以及快速预置期间可能超出限制。不要承诺这些字段能即时限制账单。请预留替换余量、监控用量，并测试托管环境的行为。

`weight` 会影响符合条件的池之间的预置优先级。它不会提高节点的 Kubernetes 调度优先级、驱逐现有工作负载，也不会强制 Pod 使用特定池。请使用明确的工作负载约束，避免池之间出现非预期的重叠。

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

Server dry-run 可以检查准入，但无法证明 IAM、网络连接、预置、存储或应用行为正常。请解决 false/unknown 就绪条件，并在投入生产前验证受控工作负载。

## 参考资料

- [内置 NodePool](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Auto Mode NodePool 字段和标签](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode NodeClass 规范](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [托管实例类型和 IMDS 限制](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Auto Mode 节点安全](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [上游 Karpenter NodePool 限制](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter 加权预置](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [节点 CA、KMS 和网络功能](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [上一页：入门](./01-getting-started.md) | [目录](./README.md) | [下一页：扩缩行为](./03-scaling-behavior.md) >
