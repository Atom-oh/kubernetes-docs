# 第 8 部分：EKS 集成

> **已审查基线**：Calico 3.32.2 / Tigera Operator 1.42.6 / 经 Calico 测试的 Kubernetes 1.34–1.36。**最后更新**：October 12, 2026

## 概述

本指南使用 Calico 在搭载 Amazon VPC CNI 的**普通 Linux EC2 worker node**上实施策略。VPC CNI 分配 Pod IP 并配置 VPC 网络；Calico 在 node 的数据平面中编程策略。以下安装保留 Iptables 数据平面和 kube-proxy。Calico 网络和 eBPF 是具有额外前提条件的独立部署选择。

截至本次审查，EKS 在标准支持中列出 1.34–1.37，在延长支持中列出 1.31–1.33（[EKS Kubernetes 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)）。Calico 3.32 公布的 Kubernetes 测试范围是 1.34–1.36。EKS 可用性、上游 Kubernetes 发布和 Calico 兼容性是独立检查项；EKS 提供 1.37 并不意味着 1.37 属于 Calico 3.32 的已测试矩阵。安装前请确认目标 Region 的 EKS 和 add-on 版本。

## VPC CNI + Calico 架构

![VPC CNI 管理 Pod 接口和 VPC IP 分配，而 Felix 编程 node 的策略数据平面；这些是控制和配置关系，而不是数据包穿过这些进程的路径。](../../.gitbook/assets/en-networking-calico-08-eks-integration-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-08-eks-integration-0.html)

该图总结了组件职责。数据包不会作为转发代理穿过 pause container 或 Felix 进程。Felix 编程由 Linux kernel 评估的规则。其 `iptables / eBPF` 标签表示可选的数据平面；本指南安装 Iptables。Typha 和 kube-controllers 运行在客户 worker 容量上，而非 AWS 托管的 EKS control plane 内。

| 组件 | 此配置中的职责 |
| --- | --- |
| `aws-node` / IPAMD 和 VPC CNI plugin | 管理 ENI/IP 分配并配置 Pod 连通性 |
| `calico-node` 中的 Felix | 为本地 endpoint 编程策略规则 |
| Typha | 向 Felix 分发 datastore 更新；operator 管理扩缩容 |
| kube-controllers | 将 Calico 数据与 Kubernetes 资源协调一致 |
| kube-proxy | 在此基线中提供 Kubernetes Service 转发 |

对于跨 node 流量，kernel 评估适用策略并使用 VPC 路径。同 node 流量可保留在 host 上。被丢弃的数据包会被直接丢弃；策略丢弃不会将数据包返还给发送方。适用的源 egress 和目标 ingress 控制都必须允许该连接。

## 选择策略引擎和安装方法

| 选择 | 安装内容 | 生命周期和范围 |
| --- | --- | --- |
| Amazon VPC CNI network policy | AWS 的策略实现 | 配置兼容的 `vpc-cni` add-on；这不会安装 Calico |
| Tigera Operator manifests | Operator 和 Calico custom resources | 固定发布版本，管理 CRD，然后协调 Installation |
| Tigera Operator Helm chart | 同一 Operator，使用 Helm 管理配置 | 渲染并审查 values；升级时使用现有 release |
| 直接 Calico manifests | 无 operator 的 Calico 组件 | 保留平台定制并自行负责升级过程 |

当发布新的 add-on 版本或 cluster minor 版本更改时，EKS add-on 不会自动更新。AWS、Marketplace 和社区 add-on 也有不同的支持责任方。不要假定存在名为 `calico` 的 add-on，或 Marketplace 产品与此 OSS 安装相同；应检查实际 catalog、发布者、版本、许可和 compute 兼容性。

**对相同 endpoint 只使用一个 network policy 引擎。**Calico EKS 指南要求禁用 AWS VPC CNI network policy。迁移需要经过审查地交接策略、node 状态和可用性；仅在两个引擎都运行时切换一个 flag 不是迁移过程。AWS 警告，移除策略 agent 后规则可能仍然存在，并建议在从第三方引擎迁移时替换受影响 node。参阅 [AWS 策略注意事项](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)和[禁用过程](https://docs.aws.amazon.com/eks/latest/userguide/network-policy-disable.html)。

## 准备现有 VPC CNI 安装

以下命令检查现有的托管 `vpc-cni` add-on。请使用实际的 Region 和 cluster 名称；自托管的 VPC CNI 安装则必须通过其自身的 manifest 或 Helm 所有者进行更改。

```bash
EKS_CLUSTER=my-cluster
EKS_REGION=us-east-1
EKS_VERSION=$(aws eks describe-cluster --name "$EKS_CLUSTER" \
  --region "$EKS_REGION" --query cluster.version --output text)

aws eks describe-addon-versions --addon-name vpc-cni \
  --kubernetes-version "$EKS_VERSION" --region "$EKS_REGION" \
  --query 'addons[0].addonVersions[].{version:addonVersion,compatibility:compatibilities,compute:computeTypes}'

aws eks describe-addon --cluster-name "$EKS_CLUSTER" \
  --addon-name vpc-cni --region "$EKS_REGION" > vpc-cni-current.json

VPC_CNI_VERSION=$(jq -r '.addon.addonVersion' vpc-cni-current.json)
aws eks describe-addon-configuration --addon-name vpc-cni \
  --addon-version "$VPC_CNI_VERSION" --region "$EKS_REGION" \
  --query configurationSchema --output text > vpc-cni-schema.json
```

Calico 需要 `ANNOTATE_POD_IP=true`，以便 VPC CNI 及时发布 `vpc.amazonaws.com/pod-ips`。`aws-node` ServiceAccount 需要有修补 Pod 的权限。当前 VPC CNI 文档说明 EKS add-on 会自动更新此权限；请验证，而不要覆盖现有 ClusterRole：

```bash
kubectl auth can-i patch pods --all-namespaces \
  --as=system:serviceaccount:kube-system:aws-node
```

此授权检查需要模拟该 ServiceAccount 的权限。如果没有该权限，单独的 binding 可添加所需规则，而无需替换现有规则。对于非标准安装，请使用其实际的 ServiceAccount 名称。

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: calico-vpc-pod-annotations
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: calico-vpc-pod-annotations
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: calico-vpc-pod-annotations
subjects:
  - kind: ServiceAccount
    name: aws-node
    namespace: kube-system
```

对于经审查的**新配置或已为仅策略的配置**，请在保留当前 add-on 设置的同时准备以下候选配置：

```bash
jq '(.addon.configurationValues // "") as $current
  | (if $current == "" then {} else ($current | fromjson) end)
  | .enableNetworkPolicy = "false"
  | .env.ANNOTATE_POD_IP = "true"
  | del(.env.NETWORK_POLICY_ENFORCING_MODE)' \
  vpc-cni-current.json > vpc-cni-calico.json
```

此命令预期 JSON 配置值；如果现有值为 YAML，请在准备候选配置前解析并转换它们，且不要丢弃字段。遇到解析错误时停止。针对获取到的 EKS build schema 验证候选配置并审查 diff。`NETWORK_POLICY_ENFORCING_MODE` 变量属于 AWS 策略 agent；在该 agent 不存在时仍保持配置可能会中断 Pod 创建。如果 AWS 策略当前处于活动状态，请在使用此候选配置前完成迁移计划。通过 add-on 所有者应用已批准的配置：

```bash
aws eks update-addon --cluster-name "$EKS_CLUSTER" \
  --addon-name vpc-cni --region "$EKS_REGION" \
  --configuration-values file://vpc-cni-calico.json \
  --resolve-conflicts PRESERVE
```

检查返回的更新状态和最终的 DaemonSet。保留的冲突可能阻止所需字段生效。不要将成功解析 JSON 或已接受的更新请求视为策略执行的证明。

## 使用 Operator 安装 Calico

对于全新安装，请从以下 manifest 或 Helm 路径中选择**一种**。不要在现有 release 上安装第二个 operator。这些示例假定使用普通 EC2 Linux worker、可访问的 Kubernetes API/DNS、兼容的 VPC CNI，且不存在竞争的策略引擎。

### Operator Manifest 路径

Calico 3.32 将 Calico CRD 与 operator manifest 分开：

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
```

将以下内容保存为 `calico-eks-installation.yaml`：

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f calico-eks-installation.yaml
kubectl get tigerastatus
kubectl get pods -n calico-system
```

API server、Goldmane flow aggregator 和 Whisker UI 在 OSS 中可用。请为您的环境配置其访问权限和资源容量。设置 `cni.type: AmazonVPC` 将 IPAM/networking 委派给 VPC CNI；单独设置 `bgp: Disabled` 不会选择 CNI。让 operator 管理 Typha replicas；`typhaDeployment.spec.replicas` 不是受支持的 Installation override。参阅[扩缩容详情](07-advanced-topics.md)。

### Helm 路径

将此内容保存为 `calico-eks-values.yaml`。`installation` 映射到 Installation API。顶层 `nodeSelector` 控制 operator Pod，而非每个 Calico 组件。不受支持的 values 可能被 Helm 静默忽略，因此请检查渲染后的资源。

```yaml
installation:
  enabled: true
  kubernetesProvider: EKS
  cni:
    type: AmazonVPC
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --version v3.32.2 --namespace tigera-operator \
  -f calico-eks-values.yaml > calico-rendered.yaml

# After reviewing the rendered configuration for the prepared cluster:
helm install calico projectcalico/tigera-operator \
  --version v3.32.2 --namespace tigera-operator --create-namespace \
  -f calico-eks-values.yaml
```

使用 `manageCRDs: true` 时，operator 启动后会管理所需的 CRD。对于需要立即使用新字段的升级，请按照[Calico 升级过程](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)，先通过现有所有者应用匹配的 CRD。单独进行 Helm rollback 并不能保证 CRD 或已存储数据的迁移被撤销。

## AWS 原生 Network Policy 作为替代方案

AWS VPC CNI 标准 NetworkPolicy 支持始于 **VPC CNI 1.14**，而不是 EKS 1.14。当前 AWS 指南要求标准和 admin policy 均使用 VPC CNI **1.21+**、兼容的 EKS/platform 版本以及 Linux kernel 5.10+。请使用当前兼容性指南，而非旧的发布版本示例。

AWS 现已记录 `networking.k8s.aws/v1alpha1` **ClusterNetworkPolicy**，包括 Admin 和 Baseline 层级，同时也记录 namespace-scoped `networking.k8s.io/v1` NetworkPolicy。它与 Calico GlobalNetworkPolicy 和 Calico 的可配置层级是不同的 API。不要将原生策略描述为永久仅限于 namespace-scoped 规则。

| 功能 | AWS 原生实现 | 本指南中的 Calico OSS |
| --- | --- | --- |
| Kubernetes NetworkPolicy | 在符合条件的 EC2 Linux node 上受支持 | 在受管理 endpoint 上受支持 |
| Cluster policy | AWS ClusterNetworkPolicy，具有自己的规则和前提条件 | Calico GlobalNetworkPolicy 和 Tier |
| 策略可观测性 | Agent metrics/event logs；单独配置任何 CloudWatch 传递 | Felix/Typha metrics、Goldmane 和 Whisker flow 可观测性 |
| 应用层策略 | 不要从 L3/L4 network policy 推断其存在 | 独立的 Dikastes/Istio 集成；此安装未启用 |
| Calico 中的 DNS/FQDN 策略 | 不是 Calico API 实现 | 已记录的基于 domain 的策略功能需要商业 Calico 版本 |

对于原生替代方案，请通过兼容的 VPC CNI add-on/Helm 设置配置 `enableNetworkPolicy`。在 `aws-node` 上设置虚构的 `ENABLE_NETWORK_POLICY` 环境变量是不够的。原生 `standard` 启动模式在策略被编程时最初允许流量；`strict` 从拒绝开始，并需要所需路径（包括 DNS）。这些 AWS 设置不会配置 Calico 的启动行为。

原生执行具有已记录的限制：仅 EC2 Linux、仅主 Pod 接口、IP-family 限制，以及在 controller-owned Pod 下的可靠运行。审查 port/protocol 限制和 Service-port 要求。保持 AWS 托管的 PolicyEndpoint 资源由 controller 所有。有关完整设置和迁移详情，请使用[维护中的 VPC CNI 指南](../01-vpc-cni.md)。

## Node 类型和网络配置文件

| 配置文件 | 适用性 |
| --- | --- |
| 普通托管或自托管 EC2 Linux node + VPC CNI | 上述基线仅策略安装；仅管理模型本身不决定 Calico 能力 |
| EC2 node + 完整 Calico CNI | 独立的 Tigera 文档化设计；Pod 寻址、control-plane 可达性、CNI 所有权和支持边界会改变 |
| EKS Fargate | Calico 的 node agent 和 VPC CNI 原生 network policy 均不在这些 Pod 上运行；Pod security groups 是独立受支持的控制措施 |
| EKS Auto Mode | 内置 AWS networking/policy；不支持替代 CNI 和 network policy plugin |
| EKS Hybrid Nodes | VPC CNI 不兼容；专用 CNI 指南列出 AWS 维护的 Cilium 1.17/1.18 build；请参阅下面的支持资格说明 |
| Windows nodes | 独立的 Windows/VPC CNI 和 Calico HNS 过程；没有 Calico eBPF 数据平面；请参阅 [Windows 限制](07-advanced-topics.md) |

专用 Hybrid CNI 指南列出了 AWS 维护的 Cilium build，并在其他位置链接 Calico 示例，而[通用替代 CNI 页面](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)仍然将核心 Cilium/Calico 支持描述为适用于 Hybrid Nodes。不要根据示例移动推断 Calico 支持已终止，也不要将任意上游版本视为 AWS 支持。确认具体 distribution/capability 支持边界。

EC2 endpoint 上的 Calico 策略可以限制该 endpoint 涉及 Fargate peer 的流量；这不表示策略在 Fargate 内部执行。混合 compute cluster 需要明确的调度和执行边界，而不是将每个 worker 标记为“完整 Calico 支持”。

完整 Calico CNI 并非通过将 VPC CNI 的 `enableNetworkPolicy` 设为 false 来启用。Tigera 的全新 cluster 过程会在添加 worker 前移除竞争 CNI。不要将现有生产 cluster 中的 `aws-node` 删除作为转换捷径。已记录的 overlay 设计还需要特别考虑 API-server 到 Pod 的流量，例如 admission webhook；受信任的 `hostNetwork` 组件是一个有记录的解决方法。采用该配置文件前，请审查 Pod CIDR、返回路径、MTU、适用时的 node IAM/source-destination 检查，以及 AWS/Tigera 支持边界。

对于 Auto Mode，VPC CNI 环境变量和 ENIConfig 设置不会配置托管网络服务。请使用 NodeClass。Auto Mode 将 CoreDNS 作为 node system service 运行；纯 Auto Mode cluster 不需要传统 CoreDNS Deployment，而混合的非 Auto node 仍需要它。初始 DNS 查询可以是本地的，而上游转发仍会离开 node。

## IAM、IRSA 和 Pod Identity

基础 Calico 仅策略安装使用 Kubernetes RBAC；它不需要为 `calico-node` 配置宽泛的 EC2 discovery 或 CloudWatch IAM role。VPC CNI 需要其自身有文档说明的 AWS 权限。单独的 log exporter 或商业 cloud 集成可能需要为**该组件的** ServiceAccount 添加额外权限。

IRSA 使用 cluster OIDC provider 和适当限定范围的 trust policy，为 ServiceAccount 获取 AWS credentials。EKS Pod Identity 是另一种选择，但需由组件、SDK 和 compute type 支持。IAM policy 和虚构的 `Installation.spec.nodeMetadata` value 都不会将 credentials 接入 workload。请遵循所属组件的配置，并避免与 operator-managed ServiceAccount 竞争。参阅 [VPC CNI IAM 配置](https://docs.aws.amazon.com/eks/latest/userguide/cni-iam-role.html)。

## Security Groups 和 Calico 策略

![Security groups、Calico 策略和应用身份验证提供不同层的访问控制。](../../.gitbook/assets/en-networking-calico-08-eks-integration-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-08-eks-integration-3.html)

该图是概念性的分层图，而非固定评估顺序。Calico 按 tier/order 和规则语义评估策略；NetworkPolicy 并不总是在 GlobalNetworkPolicy 之前。CloudTrail 记录 AWS API 活动，而非数据包决策。VPC Flow Logs 和已配置的策略日志工具提供不同的流量证据。应用 mTLS/authorization 必须单独部署。

Security groups 附加到 ENI。**Pod security groups** 可通过 SecurityGroupPolicy 选择 workload，因此“security groups 仅选择 instance”的说法不正确。若要将 SG-for-Pods 与 Calico 策略结合，AWS 要求 VPC CNI 1.11+ 且 `POD_SECURITY_GROUP_ENFORCING_MODE=standard`；在 strict mode 中，这些 Pod 的流量不受 Calico 执行约束。更改 mode 后，检查 branch-ENI/instance 支持并重新创建受影响的 Pod。SG-for-Pods 不支持 Windows 或 Auto Mode。

在 VPC CNI 常规的 external SNAT 启用（`AWS_VPC_K8S_CNI_EXTERNALSNAT=false`）的 standard mode 下，离开 VPC 的流量使用 node 的主 ENI IP 和 security groups。不要假定 Pod security group egress 规则覆盖每条路径。参阅 [AWS 的确切条件](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)。

### Namespace-Scoped 应用策略

此示例仅选择已准备的 `calico-eks-demo` namespace 中 `app=frontend` 的 Pod。它允许同一 namespace 中的**cluster 内 gateway Pod**访问 TCP 8080，并允许 frontend egress 访问同 namespace backend Pod 上的 TCP 8080。该示例假定使用带有 `k8s-app=kube-dns` 的普通 CoreDNS Pod；NodeLocal DNS 或其他 resolver 需要不同 destination。其他 policy/tier 可改变结果，因此请检查整个有效策略集。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: frontend-policy
  namespace: calico-eks-demo
spec:
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: projectcalico.org/name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: projectcalico.org/name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

将 destination selector 和 port 保留在**同一** `destination` mapping 下。重复的 YAML key 可能静默移除 selector，并允许 TCP 8080 访问非预期 endpoint。ALB/NLB 不是具有 `app=load-balancer` 的 Kubernetes Pod；请使用 [load balancer 指南](../03-aws-lb-controller.md)单独考虑 target mode、health check 和观察到的 source address。

选择 `all()` 的空白 cluster-wide GlobalNetworkPolicy 可能会中断 DNS、API、monitoring 和应用流量。请先在选定的 test namespace 中构建 default-deny 行为，并明确允许依赖项；参阅 [network policy](05-network-policy.md)。

## 升级和恢复

1. 清点 EKS control plane、node OS/kubelet、VPC CNI、kube-proxy、Calico/operator/CRD 和 calicoctl 版本。导出所属配置和策略。
2. 选择同时与**计划转换的两端**兼容的 Calico 版本。不存在通用的“始终先/后升级 Calico”规则。遵循特定安装过程和 CRD 迁移说明。
3. 审查 EKS upgrade insights、已移除 API 和所有 add-on 兼容性。每次将 EKS control plane 升级一个 minor 版本，然后将 node 和适用的 add-on 更新到兼容版本。
4. 在滚动转换期间验证策略和 Service 行为，包括负面情形和新创建的 Pod。明确配置所有权和 rollback 前提条件。

```bash
aws eks describe-cluster --name "$EKS_CLUSTER" --region "$EKS_REGION" \
  --query 'cluster.{version:version,platform:platformVersion,status:status}'
kubectl get nodes -o wide
kubectl get daemonset calico-node -n calico-system -o wide
kubectl get tigerastatus
helm get values calico -n tigera-operator -o yaml
```

当前 EKS 支持在原地升级后的七天内**有条件地 rollback 到上一个 minor 版本**。cluster 必须满足文档化的资格和就绪要求；该窗口并非通用的降级能力。普通托管/self-managed/hybrid node 和不兼容的 add-on 需要在 control plane 前准备。Auto Mode 处理其 node rollback；Fargate 需要独立的 workload 处理。Calico 和 EKS add-on 不会自动恢复，保留 etcd 数据也不会使不兼容资源变得安全。请遵循[当前 rollback 过程](https://docs.aws.amazon.com/eks/latest/userguide/rollback-cluster.html)，不要使用 `--force` 掩盖尚未解决的兼容性问题。在符合资格的时间窗口外，请计划迁移到另一个受支持 cluster。

应用旧版 operator manifest 或运行 `helm rollback` 并不能证明安全降级 Calico。选择恢复步骤前，请检查具体 release 的支持情况以及 schema/data 更改。`calicoctl node status` 报告 node-local BGP 状态，不是仅策略 EKS 的验收测试。

## 成本和性能

| 因素 | 评估内容 |
| --- | --- |
| Worker 资源 | 在实际 policy/endpoint churn 下测量 Felix、Typha、controller 和 flow aggregation；CPU request 不是独立的 AWS 费率 |
| VPC IP 容量 | Prefix delegation 影响地址分配和密度，不会自动获得 ENI 附加折扣 |
| Logging/metrics | 保留、摄取、查询和 exporter 传递具有独立成本；metrics 不是 flow logs |
| Cross-AZ 流量 | 评估实际 source/destination 路径和 Service 定价；本地性也会影响可用性 |
| EKS 生命周期 | 延长支持可能增加 cluster 费用；请使用当前支持日历 |

之前按组件估算的美元金额缺少 Region、instance 定价和分配假设。它们不是可用的成本模型。请使用观测到的资源需求和相关 AWS 价格，而非声称任意资源限制可带来固定的月度节省。

### Prefix Delegation

对于普通 VPC CNI node，请在 add-on 的 **`env`** 设置或其所属 DaemonSet/Helm 配置中配置 `ENABLE_PREFIX_DELEGATION`、`WARM_PREFIX_TARGET`、`MINIMUM_IP_TARGET` 和 `WARM_IP_TARGET`。ConfigMap 中的小写 `enable-prefix-delegation` 条目不会配置 IPAMD。

从一种有文档说明的分配策略开始。`WARM_IP_TARGET` 和 `MINIMUM_IP_TARGET` 覆盖 `WARM_PREFIX_TARGET`；同时设置它们不会叠加其效果。IPv4 prefix 需要连续的 `/28` subnet 空间和适当的 instance。验证 subnet 碎片、reservations、max-Pods/kubelet 配置和 rollout 计划。参阅 [AWS prefix 过程](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses-procedure.html)。

### EKS 上的 Calico eBPF

Calico 为其 eBPF 数据平面记录了 EKS 和兼容 VPC CNI networking，但这会改变 Service 处理并需要独立迁移。遵循[第 6 部分](06-ebpf-dataplane.md)：kernel/platform 检查、直接 API-server FQDN 访问和 bootstrap DNS、kube-proxy 所有权、health port 和 rollback 状态都很重要。

VPC CNI **并非**在所有情况下都要求 kube-proxy 保持运行。如果 kube-proxy 必须共存，Calico 要求同时设置 `bpfKubeProxyIptablesCleanupEnabled: false` 和 `bpfKubeProxyHealthzPort: 0`，以避免已记录的冲突。通用 DaemonSet selector patch 可能被其所有者协调，且不得覆盖无关 selector。DSR 不是默认 EKS 优化：AWS subnet/source-address 检查和外部 load balancer 限制需要单独验证。此基线保留 Iptables 和 kube-proxy。

通用 sysctl preset、将内存降至任意最小值或缩短 conntrack 生命周期均不能证明性能更佳。请对实际 workload 进行基准测试，并保留返回路径、已建立连接和故障恢复。

## eksctl Cluster 规划示例

这是针对普通托管 Linux node 的**规划示例**，不是经过生产测试的配方，也不是 Auto Mode 的转换。预置前通过 `describe-addon-versions` 确认受支持的 add-on build，并在配置中固定已批准的 build。省略 add-on 版本会选择一个兼容的默认值；它并不代表批准所有未来 release。私有 API 访问需要进入 VPC 的管理路径。NAT、logs、worker 容量和地址范围需要环境特定的设计。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: calico-eks-demo
  region: us-east-1
  version: "1.36"
iam:
  withOIDC: true
vpc:
  cidr: 10.0.0.0/16
  clusterEndpoints:
    publicAccess: false
    privateAccess: true
managedNodeGroups:
  - name: linux-workers
    instanceType: m5.large
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 6
    privateNetworking: true
    volumeType: gp3
    volumeSize: 100
addons:
  - name: vpc-cni
    attachPolicyARNs:
      - arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy
    configurationValues: |
      enableNetworkPolicy: "false"
      env:
        ANNOTATE_POD_IP: "true"
  - name: coredns
  - name: kube-proxy
cloudWatch:
  clusterLogging:
    enableTypes: [api, audit, authenticator, controllerManager, scheduler]
```

IPv4 CNI 策略属于 VPC CNI identity，而不是 Calico。请针对其他 IP family 和 identity 方法重新审查 IAM。已批准的 cluster 存在后，执行 annotation/RBAC 检查和上述**一种** Calico 安装路径。

## 验证结果

```bash
kubectl get tigerastatus
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get pods -n calico-eks-demo -o json \
  | jq '.items[] | {name: .metadata.name, ip: .status.podIP,
      annotatedIPs: .metadata.annotations["vpc.amazonaws.com/pod-ips"]}'
kubectl get networkpolicies.projectcalico.org -n calico-eks-demo
```

使用 controller-managed test workload，并在同一 node、跨 node/AZ、Pod 重新创建后以及更新期间检查允许和拒绝的连接。包含应用所需的 DNS、API/identity endpoint、Service 流量和 load balancer health check。Running Pod 或 Ready node 均不能验证所需拒绝，也不能验证不存在启动策略间隙。单独测试 IPv6：Calico 当前 EKS 指南排除对 `ENABLE_V4_EGRESS=true` 的 IPv6 Pod 的策略执行。

本文档示例已经根据已发布的 schema 和渲染后的 chart 进行检查；未创建 EKS cluster、IAM 资源或生产流量来验证它们。

## 参考资料

- [EKS 上的 Calico](https://docs.tigera.io/calico/latest/getting-started/kubernetes/managed-public-cloud/eks)
- [Calico 要求](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [Calico Helm 安装](https://docs.tigera.io/calico/latest/getting-started/kubernetes/helm)
- [Calico 升级](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [VPC CNI 1.23 配置参考](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [EKS 原生 network policy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [EKS add-on 更新](https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html)
- [EKS 版本生命周期](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [EKS Auto Mode networking](https://docs.aws.amazon.com/eks/latest/userguide/auto-networking.html)
- [EKS Hybrid Nodes CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)

## 后续步骤和测验

继续学习[操作](09-operations.md)，审阅[高级主题](07-advanced-topics.md)或[术语表](glossary.md)，并通过 [EKS 集成测验](../../quizzes/networking/calico/08-eks-integration-quiz.md)测试您的理解。
