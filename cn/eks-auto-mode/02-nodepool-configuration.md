# NodePool 配置与优化

> **支持的版本**：EKS Auto Mode GA；示例基线为 EKS 1.36
> **最后更新**：2026年10月21日

本章将 AWS 管理的默认设置、自定义 NodePool 约束以及 AWS 专用的 NodeClass API 区分开来。请先完成[入门](./01-getting-started.md)，使用预期的账户和上下文，并在应用模板前检查所有 IAM/配置文件名称和网络标签。此处显示的容量上限仅供示例参考，实际仍可能产生大量费用。

NodePool 示例已根据已发布的 Karpenter 1.14.1 CRD 的结构 Schema 进行检查；AWS 专用的 NodeClass 字段则与 AWS 文档进行了比对。这并未确认 Auto Mode 内部控制器的版本，也不能证明其在活动集群上的准入或就绪情况。本次审计期间未预置任何节点。

## 了解内置 NodePool

启用 Auto Mode 后，它会提供以下池。这些池由 AWS 管理；如需自定义配置，请创建自定义池，而不要编辑 AWS 管理的配置。

| 池 | 架构 | 容量和实例选择 | 用途 |
|------|--------------|----------------------------------|---------|
| `general-purpose` | `amd64` | 按需型，C/M/R 系列，第 5 代或更新代际 | 通用工作负载 |
| `system` | `amd64` 和 `arm64` | 按需型，C/M/R 系列，第 5 代或更新代际 | 可容忍 `CriticalAddonsOnly` 的集群关键工作负载 |

内置的通用池**不会**启用 Spot。需要 Spot 或不同的架构/实例约束时，请使用自定义池。Auto Mode 提供节点本地 DNS 和服务网络功能；纯 Auto Mode 集群无需仅为了填充 system 池而运行普通的 CoreDNS/kube-proxy Pod。混合集群仍需要传统的 CoreDNS Deployment 来服务非 Auto 节点。

请检查实际的受管对象，了解中断设置和污点详情，而不要应用猜测出来的默认 YAML：

```bash
kubectl --context "$CLUSTER_NAME" get nodepool general-purpose system -o yaml
kubectl --context "$CLUSTER_NAME" get nodeclass default -o yaml
```

AWS 至少需要启用一个内置池，才会提供 `default` NodeClass。如果两个池都已禁用，请创建自己的 NodeClass 并更新下方引用。在 `computeConfig.nodePools` 中移除某个内置池名称会删除该池，并排空/终止其节点；这不只是让新工作负载看不到该池。

## 创建自定义 NodePool

以下示例引用现有的 `default` NodeClass，以便重点展示调度约束。若要使用本章稍后介绍的自定义 NodeClass，请先创建它，并修改目标池中的 `nodeClassRef.name`。`template` 下的所有标签和污点都会应用到新节点；仅添加在 NodePool 元数据上的标签不会添加到节点上。

### 计算优化型工作负载

代际条件 `Gt ["6"]` 允许第 7 代及更新代际；它不会只选择最新代际。此示例允许使用 x86 C 系列按需型实例，并为该池设置了高于内存示例的预置优先级。

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

此示例允许使用第 6 代及更新代际的 R 系列实例，架构可以是任意一种。容器镜像和应用依赖项必须支持调度器所选的架构。

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

Auto Mode 使用 `eks.amazonaws.com/v1` 和 `NodeClass` 类型。它的字段不同于自管理的 AWS Karpenter `EC2NodeClass`：不要将 `amiFamily`、`blockDeviceMappings`、任意 Shell `userData` 或 `metadataOptions` 复制到此 API 中。AWS 会选择其受管的 Bottlerocket 变体。

将以下内容保存为 `custom-nodeclass.yaml`，并将示例配置文件和选择器值替换为经过审核的资源。此处支持 `instanceProfile`；其名称必须以 `eks` 开头。或者，将 `role` 设置为节点 IAM 角色名称。**必须且只能指定 `role` 或 `instanceProfile` 中的一个。配置文件中包含的角色需要适当的** Auto Mode EKS 访问条目和权限；重用已配置的角色无需重复添加访问条目。对于新角色，请遵循 AWS NodeClass 参考文档中的访问条目操作流程。

子网标签用于选择资源，但不会建立路由或隔离。请验证 VPC、可用区（AZ）可用性、路由表和安全组规则。`associatePublicIPAddress: false` 会阻止分配公有 IP；节点仍需要适当的出站连接能力。

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

请确认集群角色有权使用 `spec.tags` 中的任何自定义键创建和标记资源；NodeClass 本身不会授予 IAM 权限。

`ephemeralStorage` 用于配置节点临时存储，而不是任意块设备映射。`100Gi` 大小以及 3000 IOPS/125 MiB/s 设置仅为示例；请检查 Auto Mode 当前字段限制、实例存储行为和成本。客户 KMS 配置应放在 `ephemeralStorage.kmsKeyID` 中，并应用于节点的根卷/数据 **EBS** 卷。它不会为本地 NVMe 实例存储加密选择密钥，也不会为应用 PVC 建立加密配置。

旧的引导示例修改了 `vm.max_map_count`。支持的替代方式是使用 `advancedCompute.kernel.sysctl`，并在节点启动时应用。更改受支持的内核设置会将现有节点标记为发生偏移并触发替换；这不是立即在运行中的节点上通过 Shell 原地更新。仅当工作负载需要此设置时才进行配置，并检查中断行为。

### Kubelet 设置

Auto Mode 会应用自己的 kubelet 默认设置。只有当工作负载需要不同的 Pod 密度、驱逐、日志轮转或 OOM 行为时，才应通过 `spec.advancedCompute.kubelet` 覆盖这些设置。以下是 AWS 文档记录的完整覆盖项；自管理 Karpenter `EC2NodeClass` 的 `spec.kubelet` 字段中未列出的字段（例如 `kubeReserved`、`systemReserved`、`clusterDNS`、`podsPerCore` 和镜像 GC 阈值）不会通过 Auto Mode NodeClass 暴露。

将以下内容保存为 `kubelet-nodeclass.yaml`。这些值仅为示例，并非建议值；请像前面的示例一样，将身份和选择器值替换为经过审核的资源。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: kubelet-nodeclass
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
  advancedCompute:
    kernel:
      sysctl:
        user.max_user_namespaces: 65536   # required because idsPerPod is set below
    kubelet:
      maxPods: 60
      podPidsLimit: 4096
      idsPerPod: 65536
      singleProcessOOMKill: false
      eviction:
        hard:
          memory.available: 100Mi
          nodefs.available: 10%
        soft:
          memory.available: 500Mi
          nodefs.available: 15%
        softGracePeriod:                  # required for every soft signal
          memory.available: 1m30s
          nodefs.available: 2m
        maxPodGracePeriod: 60
      logging:
        containerLogMaxSize: 10Mi
        containerLogMaxFiles: 5
      allowedUnsafeSysctls:
      - net.core.somaxconn
```

| 字段 | 含义 | 约束 |
|-------|---------|------------|
| `maxPods` | 每个节点上 Pod 数量的上限 | 1–110；实际生效值取此设置、实例类型可提供的 IP 地址数和 Auto Mode 的 110 上限三者中的最小值 |
| `podPidsLimit` | 每个 Pod 的最大进程 ID 数量 | `-1` 表示不设限制；否则必须为 100 或更大（0–99 会被拒绝） |
| `idsPerPod` | kubelet 为每个 Pod 的用户命名空间分配的 UID 和 GID 数量 | 必须是 65536 至 4294967295 范围内的 65536 的倍数；同一 NodeClass 中要求 `advancedCompute.kernel.sysctl.user.max_user_namespaces` 大于 0 |
| `singleProcessOOMKill` | OOM 时逐个杀死容器中的进程，而不是将其作为整体杀死 | 需要 Kubernetes 1.32 或更高版本；在较早版本中无效，且 EKS 会在 NodeClass 上发出警告事件 |
| `eviction.hard` / `eviction.soft` | 每种信号的驱逐阈值，可使用数量（`500Mi`）或百分比（`10%`） | 信号：`memory.available`、`nodefs.available`、`nodefs.inodesFree`、`imagefs.available`、`imagefs.inodesFree`、`pid.available` |
| `eviction.softGracePeriod` | 软阈值必须持续多长时间才开始驱逐 | 对每个设置了软阈值的信号都必须指定 |
| `eviction.maxPodGracePeriod` | 因软阈值被驱逐的 Pod 的最长终止宽限时间，单位为秒 | `0` 表示使用每个 Pod 的 `terminationGracePeriodSeconds` |
| `logging.containerLogMaxSize` / `logging.containerLogMaxFiles` | 容器日志轮转大小和保留文件数 | `containerLogMaxFiles` 至少为 2 |
| `allowedUnsafeSysctls` | 节点上的 Pod 可以设置的不安全 sysctl，或以 `*` 结尾的模式 | 最多 64 项；允许的模式为 `kernel.shm*`、`kernel.msg*`、`kernel.sem`、`fs.mqueue.*` 和 `net.*` |

修改生产环境 NodeClass 前，请先了解以下行为：

- **节点会被替换，而不是修补**。更改现有 NodeClass 的 kubelet 设置会将其节点标记为发生偏移，EKS 会用使用新配置的节点替换它们。设置不会原地应用到运行中的节点，因此请先检查中断预算和 PDB。
- **`maxPods` 是上限。请使用** `kubectl get node <node> -o jsonpath='{.status.capacity.pods}'` 在替换节点上确认实际结果，而不要想当然地认为它等于配置值。
- **软阈值必须比硬阈值更早触发**。对于同一种信号，软阈值的宽松程度必须高于硬阈值。数量和百分比可以混用；EKS 会针对每种实例类型解析两者，并将违反规则的实例类型标记为与 NodeClass 不兼容。
- **`allowedUnsafeSysctls` 仅授予许可。它允许节点上的** Pod 请求设置该 sysctl；每个 Pod 仍必须在 `securityContext.sysctls` 中列出它。节点级内核值需另行通过 `advancedCompute.kernel.sysctl` 设置。

### 固定的 IMDS 安全配置

Auto Mode 强制使用 IMDSv2，并将跳数限制设为 1；无法通过 NodeClass 更改这些默认设置。普通的非 host-network Pod 无法通过该路径访问 IMDS，但这并不构成对所有 Pod 的隔离保证：`hostNetwork` 会改变可达性。应用访问 AWS 时，优先使用工作负载身份，并明确提供区域或其他配置，而不要依赖节点元数据。

### 客户 KMS、CA 证书包和独立 Pod 网络

不要将截断的证书粘贴到清单中。此可选生成器会读取经过审核的基础模板，检查已批准的公有 PEM 证书包，将其进行 Base64 编码后写入 `certificateBundles[].data`，并生成完整的第二个 NodeClass。它需要 Python 3 和 PyYAML。设置 `NODE_KMS_KEY_ARN` 和 `CA_BUNDLE_FILE`，并保留上一章中已审核的 `AWS_REGION`/`EXPECTED_ACCOUNT_ID`。

请单独批准 CA 颁发者、指纹和有效期。以下语法检查无法证明其可信度、KMS 权限或云资源是否存在。应用生成结果前，请检查密钥策略/IAM 授权和 Pod 网络标签选择。

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
| `ephemeralStorage.kmsKeyID` | 用于节点根卷/数据 EBS 卷的客户管理密钥；应使用与集群位于同一区域的密钥 |
| `certificateBundles[].data` | 用于节点信任的 Base64 编码证书包；它不会自动更改每个应用的容器信任存储 |
| `podSubnetSelectorTerms` | 为此 NodeClass 选择的独立 Pod 子网 |
| `podSecurityGroupSelectorTerms` | Pod 网络安全组；需与 Pod 子网选择器一同配置 |

Pod 子网和安全组选择器必须一起配置，并覆盖兼容的 VPC/AZ。此配置按 NodeClass 生效，而不是按命名空间或 ServiceAccount 生效。host-network 流量使用节点网络；出站 SNAT 也可能改变源地址和适用的安全组。在声称所有流量都已隔离之前，请检查路由、SNAT 和 Pod 密度的影响。

## 隔离工作负载和环境

### 前端和后端池

污点会阻止没有匹配容忍度的 Pod 调度到这些节点上。容忍度只允许调度；如果工作负载必须使用指定节点，还需添加选择器或必需的亲和性规则。

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

例如，创建一个自有的 `nodepool-lab` 命名空间，并在前端放置检查中同时使用选择器和容忍度：

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

应用前请先检查：此 Pod 可能导致产生计费节点。检查分配给它的节点、就绪状态和节点标签，然后从该命名空间中删除测试 Pod。`NoSchedule` 不会驱逐已经运行的 Pod；仅凭标签/污点也无法在不可信租户之间建立安全边界。

### 开发池

AWS 当前支持的实例列表包含 T 系列可突增实例类型，也包含 M 系列类型。不要仅基于较早的 Auto Mode 认知而移除 T 系列。Auto Mode 要求实例具有多于一个 CPU，并排除 nano/micro/small 规格；仍需验证区域内实例类型的可用性、CPU 积分行为和工作负载适用性。

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

`limits.cpu` 和 `limits.memory` 限制池内资源总量；它们不是节点数量上限，也不是货币预算。请将 CPU 数量加引号，避免整数/字符串在 GitOps 中产生漂移。例如，`memory: 4000Gi` 表示 4000 GiB（约 3.91 TiB），而非恰好 4 TB。

上游 Karpenter 文档指出，在快速预置期间，最终一致性可能导致超出限制。不要承诺这些字段能即时限制账单。请为替换留出余量、监控使用情况，并测试受管环境的行为。

`weight` 会影响符合条件的池之间的预置优先级。它不会提高节点在 Kubernetes 调度器中的优先级，不会驱逐现有工作负载，也不会强制 Pod 使用特定池。请使用明确的工作负载约束，并避免不必要的重叠。

```bash
# Validate against the target cluster's actual schemas; no object is persisted.
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f custom-nodeclass.yaml
kubectl --context "$CLUSTER_NAME" apply --dry-run=server -f secure-network-nodeclass.json
# After an approved apply, inspect conditions rather than assuming readiness.
kubectl --context "$CLUSTER_NAME" get nodeclasses,nodepools
kubectl --context "$CLUSTER_NAME" describe nodeclass secure-network-nodeclass
kubectl --context "$CLUSTER_NAME" get nodeclaims
```

服务器端 dry-run 可以检查准入，但无法证明 IAM、网络连接、预置、存储或应用行为正常。请解决就绪状态为 false/unknown 的情况，并在生产环境使用前验证受控工作负载。

## 参考资料

- [内置 NodePool](https://docs.aws.amazon.com/eks/latest/userguide/set-builtin-node-pools.html)
- [Auto Mode NodePool 字段和标签](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode NodeClass 规范](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [受管实例类型和 IMDS 限制](https://docs.aws.amazon.com/eks/latest/userguide/automode-learn-instances.html)
- [Auto Mode 节点安全](https://docs.aws.amazon.com/whitepapers/latest/security-overview-amazon-eks-auto-mode/eks-auto-mode-data-plane.html)
- [上游 Karpenter NodePool 限制](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter 加权预置](https://karpenter.sh/docs/concepts/scheduling/#weighted-nodepools)
- [节点 CA、KMS 和网络功能](https://aws.amazon.com/blogs/containers/new-amazon-eks-auto-mode-features-for-enhanced-security-network-control-and-performance/)

< [上一页：入门](./01-getting-started.md) | [目录](./README.md) | [下一页：扩缩行为](./03-scaling-behavior.md) >
