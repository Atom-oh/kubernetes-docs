# EKS 网络测验 - 第 1 部分

> **最后更新**: September 11, 2026

本测验回顾 EKS 网络、地址规划、策略和控制器所有权。除非另有说明，示例使用传统 Linux EC2 网络。API/配置已根据官方来源和本地架构进行检查；未执行任何云网络更改或实时数据包测试。

## 选择题

1. 传统 EKS EC2 节点的默认 CNI 是什么？
   * A) Calico
   * B) Flannel
   * C) Amazon VPC CNI
   * D) Weave Net

<details>
<summary>显示答案</summary>

**答案：C) Amazon VPC CNI**

传统 EKS EC2 节点使用 Amazon VPC CNI。Auto Mode 提供托管网络功能，Hybrid Nodes 使用受支持的替代 CNI，因此“每个 EKS 集群都运行此 DaemonSet”这一说法范围过宽。

CNI 使用 VPC 地址配置普通 Pod 网络，并提供不同的辅助 IP、前缀和 Pod 安全组路径。可路由的地址并不能绕过路由、安全组、NACL 或策略；不使用 overlay 也不代表经过测量的性能保证。

对于 Linux，这里展示的配置机制不是旧式 `amazon-vpc-cni` ConfigMap 中小写的 `warm-ip-target`/`enable-pod-eni` 键。应通过其所有者使用实际的插件架构/Helm values 或受支持的 `aws-node` 环境变量。首先检查已安装的构建版本：

```bash
set -euo pipefail
CNI_ADDON_VERSION=$(aws eks describe-addon --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --addon-name vpc-cni --query addon.addonVersion --output text)
aws eks describe-addon-configuration --region "$EXAMPLE_REGION" --addon-name vpc-cni \
  --addon-version "$CNI_ADDON_VERSION" --query configurationSchema --output text
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" -n kube-system get daemonset aws-node \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{": "}{.image}{"\n"}{end}'
```
例如，以下内容是一个**插件配置片段**，不是 Kubernetes ConfigMap。其值是用于说明的预留池目标；应将其与经过审查的现有设置合并，并检查所选版本的架构。Windows IPAM ConfigMap 设置属于另一种接口。

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```
Pod 安全组和原生 NetworkPolicy 各自有额外的前提条件。不要将其作为 IP 池示例的无关副作用启用，也不要在正常运行的集群上应用未经配置的第二个 CNI。

</details>

2. 在 IPv4 辅助 IP 模式下，普通 Pod 如何获得地址？
   * A) 每个 Pod 一个专用 VPC
   * B) 来自节点 ENI/IP 池的地址
   * C) 仅使用 overlay 地址
   * D) 每个 Pod 一个独立子网

<details>
<summary>显示答案</summary>

**答案：B) 来自节点 ENI/IP 池的地址**

在普通 IPv4 辅助 IP 模式下，IPAMD 管理节点上的 ENI/IP 池，CNI 设置会将池中的一个地址分配给 Pod 网络命名空间。CNI 清理完成并经过任何适用的复用延迟后，地址可以返回预留池；它们不一定会立即从 EC2 取消分配。

下面的传统 max-Pods 计算适用于该模式。每个 ENI 的主地址都保留；历史公式中额外加的两个地址用于 host-network 系统 Pod：

```text
ENIs × (IPv4 addresses per ENI − 1) + 2
m5.large: 3 × (10 − 1) + 2 = 29
```
这不是适用于所有工作负载的统一上限。子网空间、kubelet maxPods、计算资源、自定义网络和 branch-ENI 限制也会产生影响。前缀模式会将一个 /28 分配到一个 ENI 地址槽位，而不是每个 ENI 恰好分配一个前缀；Pod 安全组使用独立的 branch-ENI 路径。Host-network Pod 共享节点网络，是简单地描述为每个 Pod 一个辅助 IP 时的另一个例外。

</details>

3. 什么使普通 VPC CNI 的 VPC 内路由模型成为可能？
   * A) 所有 Pod 必须使用同一个子网
   * B) 所有 Pod 共享主机网络
   * C) 可在 VPC 中路由的 Pod 地址，以及必需的路由和控制
   * D) 必须使用服务网格

<details>
<summary>显示答案</summary>

**答案：C) 可在 VPC 中路由的 Pod 地址，以及必需的路由和控制**

在普通 VPC CNI 路径中，Pod 使用可在 VPC 中路由的地址。跨节点流量可以通过节点/ENI 和 VPC 路由；同一节点上的流量可以留在主机网络栈中。SG、NACL、策略规则和自定义流量检查路由仍会决定是否可达。

示例 `10.0.1.23 → 10.0.2.45` 描述的是普通 VPC 内路径，并不能证明每个数据包始终经过 VPC 路由表，或绝不会经过已配置的设备路由。同一节点上的 Pod 流量无法完全显示在 VPC Flow Logs 中。大多数 Pod 都有自己的网络命名空间；hostNetwork Pod 是例外。

不要因为没有使用 overlay，就推断延迟/吞吐量一定会改善。应测量实际路径，并考虑跨 AZ 传输、目标类型、SNAT 和工作负载行为。服务网格是可选的附加层，不是普通 Pod 路由的前提条件。

</details>

4. 哪种 Kubernetes 资源用于声明 Pod 入站/出站策略？
   * A) Service
   * B) Ingress
   * C) NetworkPolicy
   * D) SecurityContext

<details>
<summary>显示答案</summary>

**答案：C) NetworkPolicy**

NetworkPolicy 选择 Pod，并仅隔离指定流量方向。如果没有策略选择某个 Pod/方向，该方向就是非隔离状态。策略是叠加的：另一个看似更严格的策略无法移除已由其他策略允许的流量。

应使用兼容的强制执行实现。目前的 Amazon VPC CNI 在启用后支持原生网络策略；旧说法称其无法强制执行这些策略，这是错误的。托管插件使用 `enableNetworkPolicy` 配置字段，而不是假定的 `ENABLE_NETWORK_POLICY` 环境变量：

```json
{"enableNetworkPolicy":"true"}
```
这是一个片段，应根据所选插件版本/架构进行合并。测试前请确认策略代理以及 AWS 计算、内核、Pod 所有者和接口方面的限制。标准启动模式下，策略附加前流量可能会短暂放行；严格启动模式需要允许所有必需的系统/DNS 流量。不要在没有受支持的迁移设计时，同时安装随时变化的 Calico 清单和原生策略强制执行功能。

以下内容适用于经过审查的实验命名空间和由控制器管理的工作负载。同一个 peer 条目中的命名空间选择器和 Pod 选择器之间是 **AND 关系**；分开的 peer 条目之间是 OR 关系。DNS 例外是显式声明的：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow
  namespace: policy-lab
spec:
  podSelector:
    matchLabels: {app: api}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: frontend-lab
      podSelector:
        matchLabels: {role: frontend}
    ports:
    - {protocol: TCP, port: 8080}
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: database-lab
      podSelector:
        matchLabels: {app: database}
    ports:
    - {protocol: TCP, port: 5432}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels: {k8s-app: kube-dns}
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
```
应使用实际的命名空间/Pod 标签和监听端口。NodeLocal DNSCache 或其他 DNS 路径需要不同的允许规则。Service/Ingress 会路由流量，但不能取代这些 L3/L4 访问规则。SecurityContext 控制工作负载权限，而不是声明式网络允许列表。

</details>

5. 传统 EKS 集群服务发现通常配置哪个 DNS 组件？
   * A) 仅使用 Route 53 私有托管区
   * B) CoreDNS
   * C) 必须使用旧式 kube-dns Deployment
   * D) 仅使用 Cloud Map

<details>
<summary>显示答案</summary>

**答案：B) CoreDNS**

传统 EKS 使用 CoreDNS 提供集群 DNS。不要假设每种 EKS 模式都会自动创建可见的 CoreDNS Deployment：Auto Mode 提供托管 DNS，而禁用默认引导插件的工具必须显式配置所选插件。

对于 EKS 托管的 CoreDNS 插件，应通过其受支持的 `corefile` 配置值和精确版本架构保留自定义配置。直接编辑 ConfigMap 可能会被插件覆盖。对于自行管理的 CoreDNS，应通过其清单/GitOps 所有者更改配置。应检查必需的 `ready`、转发、Kubernetes 区域和重新加载行为，而不是用通用示例替换整个 ConfigMap。

DNS 应答取决于资源类型：

| 资源 | 典型 DNS 行为 |
| --- | --- |
| 普通 Service | `<service>.<namespace>.svc.<cluster-domain>` 解析为 Service IP 地址族 |
| Headless Service | Endpoint 地址，具体取决于就绪状态/发布设置 |
| ExternalName Service | 指向所配置外部名称的 CNAME |
| 旧式 IPv4 Pod 记录 | 形如 `10-0-1-23.<namespace>.pod.<cluster-domain>` 的带连字符地址，具体取决于 CoreDNS 的 `pods` 模式 |

`cluster.local` 是常见默认值，但并非所有集群都使用此域名。`pods insecure` 会提供基于旧式 IP 的应答，而不会验证 Pod 是否存在；这并非安全保证。应从经批准的集群内诊断工作负载测试 DNS，而不是使用任意笔记本电脑上的解析器。

EKS 托管的 CoreDNS 支持为兼容的插件版本配置自动扩缩。应只保留一个副本数所有者；在托管自动扩缩/HPA 生效时，手动执行 `kubectl scale` 并非正确的控制循环。

以下 **Corefile 片段**在经过审查后用于替换现有的 cache 配置段；它不是 YAML。CoreDNS 1.14.7 接受 `denial 1000`，但会将其规范化为最低有效容量 1024。示例明确设置了该容量；`success 10000` 会向下取整为 9984：

```text
cache {
    success 10000
    denial 1024
    prefetch 10 10m 20%
}
```
缓存容量/TTL/prefetch 设置需要根据工作负载测量结果确定；这不是性能基准。经过可控更改后，应观察 DNS 错误、缓存行为以及 CPU/内存使用情况。

</details>

## 简答题

6. 哪些因素限制 Pod 密度，前缀委派会如何改变这一点？

<details>
<summary>显示答案</summary>

应区分三种限制：EC2 接口/地址容量、可用子网地址和 Kubernetes/计算容量。在普通 IPv4 辅助 IP 模式下，历史公式为 `ENIs × (IPs per ENI − 1) + 2`：t3.small 为 11，m5.large 为 29，c5.4xlarge 为 234。这些是公式计算结果，并非每个托管组的实际有效上限。

在 IPv4 前缀模式下，一个 `/28` 可提供 16 个地址，并占用一个辅助地址槽位。一个 ENI 可以容纳多个前缀。旧公式“每个 ENI 一个前缀减去一个地址”得出的 m5.large 为 47，这是错误的。对于兼容的托管组，vCPU 少于 30 时 maxPods 上限为 110，否则为 250；CPU/内存和实际 CNI 配置还可能进一步限制可用工作负载容量。

托管插件配置片段示例如下：

```json
{"env":{"ENABLE_PREFIX_DELEGATION":"true","WARM_PREFIX_TARGET":"1"}}
```
合并前应检查精确版本架构和现有配置。WARM_PREFIX_TARGET 表示备用前缀容量，而不是每个 ENI 最多一个前缀。配置 WARM_IP_TARGET/MINIMUM_IP_TARGET 时，它们会覆盖其行为。前缀模式需要连续的 /28 空间和受支持的实例/CNI；它不会扩大子网。

前缀委派可以与 Pod 安全组共存。Branch-ENI Pod 仍使用各自的每实例 branch 容量，不会因此提高前缀密度。应规划新建/回收节点，并进行考虑 PDB 的迁移；不要只切换变量，就假定所有运行中的 Pod/maxPods 都已更改。自定义 AL2023 AMI 可能需要经过审查的 NodeConfig maxPods；单独提高 kubelet 限制不会创建 IP 或 CPU。

```bash
kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get nodes \
  -o custom-columns=NAME:.metadata.name,PODS:.status.allocatable.pods,POD_ENI:.status.allocatable.vpc\\.amazonaws\\.com/pod-eni
```
检查实际可分配容量和 CNI/EC2 分配情况。不要假设 aws-node 容器中包含 curl；应使用针对已安装构建版本和所选节点的文档化内省/调试路径。

</details>

7. 在传统 EKS EC2 节点上，如何为选定的 Pod 分配安全组？

<details>
<summary>显示答案</summary>

Pod 安全组使用**节点上的 trunk ENI 和选定 Pod 的 branch ENI**。EKS VPC 资源控制器使用**集群 IAM 角色**上的权限创建/管理该路径，其中包括 `AmazonEKSVPCResourceController`；这些权限并非简单的逐 Pod ServiceAccount 权限。

对于传统 Linux EC2 示例，应确认实例类型兼容 trunking（并非所有 Nitro 类型都符合条件）、VPC CNI 版本兼容，并通过其配置所有者设置 `ENABLE_POD_ENI=true`。检查 `POD_SECURITY_GROUP_ENFORCING_MODE`、DNS/探测、路由和 SG 规则。严格模式和标准模式在 SNAT 以及适用哪些 SG 方面有所不同，尤其是在 VPC 外部和节点本地路径上。

创建专用的 `sgp-lab` 命名空间，并将 SG 占位符替换为正确 VPC 中经批准的组。这个由控制器管理的休眠客户端用于演示选择过程，不代表数据库访问成功：

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: db-client-policy
  namespace: sgp-lab
spec:
  podSelector:
    matchLabels: {role: db-client}
  securityGroups:
    groupIds: [sg-REPLACE_WITH_APPROVED_GROUP]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db-client
  namespace: sgp-lab
spec:
  replicas: 1
  selector:
    matchLabels: {role: db-client}
  template:
    metadata:
      labels: {role: db-client}
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: client
        image: public.ecr.aws/docker/library/busybox:1.38.0
        command: [sleep, '3600']
        resources:
          requests: {cpu: 10m, memory: 16Mi}
          limits: {cpu: 100m, memory: 32Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
```
根据需要使用 podSelector 或 serviceAccountSelector。验证新创建的 Pod、CNINode/branch 容量以及允许/拒绝的应用程序连接。更改 SecurityGroupPolicy 选择不会追溯应用到正在运行的 Pod；单独的 SG 规则更改有自己的连接跟踪行为。Host-network Pod 使用节点网络。

前缀委派兼容此功能，但不会扩大 branch-ENI Pod 容量。传统的 SecurityGroupPolicy 功能并非 Auto Mode NodeClass Pod 子网/SG 选择功能；应遵循适用的计算类型专用 API，不要将二者视为相同功能。

</details>

8. 对于 LoadBalancer Service，AWS Load Balancer Controller 会创建哪种负载均衡器，如何配置所有权？

<details>
<summary>显示答案</summary>

AWS Load Balancer Controller 会将 LoadBalancer Service 协调为 **NLB**，而不是 CLB。旧测验将其与旧式内置 Service 控制器混为一谈。目前的 LBC 使用 `service.k8s.aws/nlb` 显式指定所有权，并且自 v2.2 起，新 NLB 的默认值为**内部**。应显式配置预期的方案。

这是一个新 Service，用于 `lb-lab` 中现有且经过审查的 `app=echo` 工作负载；前提是已安装/授权控制器，并验证了符合条件的子网/SG 规则。它会创建一个需要付费的内部 NLB；不要随意将其应用到生产命名空间：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-nlb
  namespace: lb-lab
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
spec:
  type: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  allocateLoadBalancerNodePorts: false
  selector: {app: echo}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
```
IP targets 会将流量发送到符合条件的 Pod IP；instance targets 使用节点/NodePort 路径。此示例在 IP 模式下禁用了未使用的 NodePort 分配。Auto Mode 使用自己的所有权类 (`eks.amazonaws.com/nlb`) 和受支持的配置集。不要为了尝试未经审查的迁移，去修改现有旧式 Service 的控制器选择注解/类；这可能导致资源泄漏或暴露。

**配置选项**必须与所选控制器版本和监听器设计匹配：表中的注解名称省略了通用前缀 `service.beta.kubernetes.io/`。

| 要求 | 当前配置/注意事项 |
| --- | --- |
| 内部或公有方案 | `aws-load-balancer-scheme: internal` 或 `internet-facing`；路由/子网必须匹配 |
| IP targets | `aws-load-balancer-nlb-target-type: ip` |
| 自定义前端 SG | `aws-load-balancer-security-groups`；检查后端规则管理和运行状况检查路径 |
| 显式指定子网 | `aws-load-balancer-subnets`；仍须满足资格/AZ/IP 限制 |
| 跨区行为 | 使用 `aws-load-balancer-attributes` 配置 `load_balancing.cross_zone.enabled`；评估可用性、拓扑和成本 |
| 旧式 S3 访问日志 | 使用 `aws-load-balancer-attributes` 配置 `access_logs.s3.*`；NLB 访问日志仅涵盖 TLS 请求，并需要经过审查的存储桶/传输权限 |
| TLS 终止 | 使用 `aws-load-balancer-ssl-cert`，并通过 `aws-load-balancer-ssl-ports` 配置匹配的 Service 监听端口；这是 NLB TLS 终止，不是 ALB HTTP 路由 |

旧式 `aws-load-balancer-internal`、跨区和访问日志注解已弃用，应改用方案/属性设置。目前的 NLB 还支持增强型 CloudWatch 日志传输；应选择其文档化集成，不要假设 S3 注解可以配置该功能。访问日志采用尽力而为方式，并非完整的请求台账。
**ALB 替代方案：**使用带有已配置 `alb` IngressClass 的 Ingress，并通过 IP targets 指向 ClusterIP 后端。这样可以避免为同一个示例后端意外同时创建 NLB 和 ALB：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: echo-backend
  namespace: lb-lab
spec:
  type: ClusterIP
  selector: {app: echo}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: echo-alb
  namespace: lb-lab
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
spec:
  ingressClassName: alb
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: echo-backend
            port: {number: 8080}
```
安装前，应准备好控制器 ServiceAccount 和范围受限的 IAM 权限。经过审查的 chart 3.5.0 包含控制器 v3.5.0；对于无法进行 IMDS 自动发现的环境，应显式指定区域/VPC。部署前先渲染并检查：

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update eks
helm template aws-load-balancer-controller eks/aws-load-balancer-controller \
  --version 3.5.0 --kube-version 1.36.0 --namespace kube-system \
  --set-string clusterName="${EXAMPLE_CLUSTER:?}" \
  --set-string region="${EXAMPLE_REGION:?}" --set-string vpcId="${EXAMPLE_VPC_ID:?}" \
  --set serviceAccount.create=false --set-string serviceAccount.name=aws-load-balancer-controller \
  > lbc-reviewed.yaml
```
| 功能 | CLB（旧式） | NLB | ALB |
| --- | --- | --- | --- |
| 主要路由层 | L4/L7 旧式监听器 | L4 | HTTP/HTTPS L7 |
| 直接 IP targets | 否 | 是 | 是 |
| 每个 AZ 的静态地址选项 | 否 | 是 | 没有原生静态前端 IP |
| HTTP 路径路由 | 否 | 否 | 是 |

NLB 目前支持 TCP、TLS、UDP、TCP_UDP、QUIC 和 TCP_QUIC 监听器。应单独检查控制器支持/配置（LBC 3.5 文档包含 QUIC 端口注解）。旧表中定性的“良好/非常好”性能描述并非基准测试。应根据应用程序进行选择和测量；无论是始终启用跨区功能，还是笼统排列延迟高低，都不是生产规则。

</details>

## 实操题

9. 实现并验证同一命名空间内的流量，配置 DNS 例外，并阻止跨命名空间 TCP 路径。

<details>
<summary>显示答案</summary>

使用一个选择目标命名空间中所有 Pod 的策略，允许同一命名空间内的对等 Pod，并显式添加 DNS 例外。这是 L3/L4 策略，并不能证明租户或节点已完全隔离。

**前提条件：**使用经过批准的传统 IPv4 Linux 测试集群，通过受支持的所有者/配置启用了原生 VPC CNI NetworkPolicy，测试 Pod 由控制器管理，CoreDNS 正常运行，且没有相冲突的组织级策略。不要在此实验中安装 Calico，也不要切换虚构的 `ENABLE_NETWORK_POLICY` 变量。

创建两个新命名空间并记录其 UID。以下代码片段应在同一个 Bash 会话中运行：

```bash
set -euo pipefail
umask 077
: "${EXAMPLE_KUBECONFIG:?Use the reviewed IPv4 Linux lab cluster kubeconfig}"
NP_LAB_DIR=$(mktemp -d /tmp/eks-network-policy.XXXXXX)
NP_LAB_ID="$(date +%s)-$$"
NP_NAMESPACE_A="np-a-$NP_LAB_ID"
NP_NAMESPACE_B="np-b-$NP_LAB_ID"
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" create namespace "$ns" -o json \
    > "$NP_LAB_DIR/$ns-created.json"
  jq -e '.metadata.uid | type == "string" and length > 0' \
    "$NP_LAB_DIR/$ns-created.json" >/dev/null
done
```
HTTP 服务器还提供已知的 Python TCP 诊断方式。每个 Service 和容器均使用端口 8080。这些是测试工作负载，并非生产环境容量规划；应记录镜像摘要以保证可重复性。

```bash
for ns in "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"; do
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" create -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: network-probe
spec:
  replicas: 1
  selector:
    matchLabels: {app: network-probe}
  template:
    metadata:
      labels: {app: network-probe}
    spec:
      automountServiceAccountToken: false
      nodeSelector: {kubernetes.io/os: linux}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile: {type: RuntimeDefault}
      containers:
      - name: probe
        image: python:3.13-alpine
        command: [python, -m, http.server, "8080", --directory, /tmp]
        ports:
        - containerPort: 8080
        readinessProbe:
          tcpSocket: {port: 8080}
        resources:
          requests: {cpu: 50m, memory: 64Mi}
          limits: {cpu: 200m, memory: 128Mi}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities: {drop: [ALL]}
---
apiVersion: v1
kind: Service
metadata:
  name: network-probe
spec:
  type: ClusterIP
  selector: {app: network-probe}
  ports:
  - {port: 8080, targetPort: 8080, protocol: TCP}
EOF
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$ns" \
    rollout status deployment/network-probe --timeout=180s
done
```
**基线：**应用策略前，必须确认同一命名空间内和跨命名空间的 TCP 连接都成功。DNS/exec 失败不同于 TCP 连接被拒绝。ICMP ping 不是可移植的 NetworkPolicy 强制执行测试。

```bash
check_tcp() {
  kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$1" exec deployment/network-probe \
    -c probe -- python -c '
import socket, sys
try:
    address = socket.gethostbyname(sys.argv[1])
except OSError as error:
    print("DNS failed:", error, file=sys.stderr)
    sys.exit(43)
try:
    connection = socket.create_connection((address, 8080), timeout=3)
    connection.close()
except OSError as error:
    print("TCP failed:", error, file=sys.stderr)
    sys.exit(42)
print("TCP succeeded")
' "network-probe.$2"
}

# All four paths must work before applying the policy.
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_B"
check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"
```
**仅应用于命名空间 A：**空的 peer podSelector 会选择该策略所在命名空间中的 Pod。DNS peer 将 kube-system 命名空间与 CoreDNS Pod 标签组合起来。如使用 NodeLocal DNSCache 或其他 DNS 路径，请相应调整。标准策略附加为异步操作，因此应通过正向控制和对两个阻断方向的测试来确认传播情况：

```bash
kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" -n "$NP_NAMESPACE_A" create -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: namespace-boundary
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
  - from:
    - podSelector: {}
  egress:
  - to:
    - podSelector: {}
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - {protocol: UDP, port: 53}
    - {protocol: TCP, port: 53}
EOF

expect_tcp_block() {
  if check_tcp "$1" "$2"; then
    return 1
  else
    result=$?
    [ "$result" -eq 42 ] || {
      printf '%s\n' 'DNS or exec failure is not proof of policy denial.' >&2
      exit 1
    }
    return 0
  fi
}
NP_VERIFIED=false
for attempt in $(seq 1 30); do
  check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
  check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
  if expect_tcp_block "$NP_NAMESPACE_A" "$NP_NAMESPACE_B" &&
     expect_tcp_block "$NP_NAMESPACE_B" "$NP_NAMESPACE_A"; then
    # Repeat positive controls after observing both blocked cross-namespace paths.
    check_tcp "$NP_NAMESPACE_A" "$NP_NAMESPACE_A"
    check_tcp "$NP_NAMESPACE_B" "$NP_NAMESPACE_B"
    NP_VERIFIED=true
    break
  fi
  sleep 2
done
[ "$NP_VERIFIED" = true ] || {
  printf '%s\n' 'Expected policy behavior was not observed; inspect the enforcement path.' >&2
  exit 1
}
```
成功表示在 DNS 和服务器可用性检查均通过的情况下，所测试的 TCP 路径表现符合预期。这并不能证明每种协议/接口都已被过滤。应单独保留平台的节点、元数据服务和安全组控制。

**扩展：**若要只允许特定的同命名空间 Pod 或端口，请替换/审查宽泛的同命名空间允许规则。添加更窄的策略无法移除现有的宽泛允许规则。对于经过审查的外部 API，可以添加额外的出站策略，选择所需的 CIDR/端口；此文档前缀不是实际目的地：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-reviewed-external-api
  namespace: app-namespace
spec:
  podSelector:
    matchLabels: {app: web}
  policyTypes: [Egress]
  egress:
  - to:
    - ipBlock:
        cidr: 203.0.113.0/24
    ports:
    - {protocol: TCP, port: 443}
```
标准 NetworkPolicy 不提供 FQDN 允许列表。NAT/Endpoint 选择会影响实际检查的 IP。笼统允许 `0.0.0.0/0`，仅排除 RFC1918 网段，既不是针对特定外部服务的规则，也不能全面保护链路本地元数据 Endpoint。

测试后，只清理已记录的命名空间：

```bash
for ns in "${NP_NAMESPACE_A:?}" "${NP_NAMESPACE_B:?}"; do
  expected_uid=$(jq -er '.metadata.uid' "${NP_LAB_DIR:?}/$ns-created.json") || exit 1
  current_uid=$(kubectl --kubeconfig "${EXAMPLE_KUBECONFIG:?}" get namespace "$ns" \
    --ignore-not-found -o jsonpath='{.metadata.uid}') || exit 1
  if [ -z "$current_uid" ]; then
    continue
  elif [ "$current_uid" = "$expected_uid" ]; then
    kubectl --kubeconfig "$EXAMPLE_KUBECONFIG" delete namespace "$ns" --wait=true || exit 1
  else
    printf '%s\n' 'Namespace UID changed; no deletion attempted for this namespace.' >&2
    exit 1
  fi
done
```

</details>

## 高级问题

10. 比较 VPC CNI 地址耗尽的补救方法，并区分节点密度和总地址空间。

<details>
<summary>显示答案</summary>

首先确定耗尽的是哪种资源：子网地址、连续前缀块、每节点 ENI 槽位、branch ENI、kubelet maxPods 还是计算容量。它们需要不同的补救方法。旧结论“前缀委派始终是最简单的解决方案”范围过宽。

| 方法 | 可解决的问题 | 重要限制 |
| --- | --- | --- |
| 前缀委派 | 增加普通 ENI 槽位中的 Pod 地址；提高分配效率 | 需要连续的 /28；不会扩大 IPv4 空间或 branch-ENI 容量 |
| 预留池/最小池调优 | 未使用的预分配地址 | 在地址使用量与分配就绪时间/API 调用之间权衡 |
| 自定义网络 | 分离节点和 Pod 子网需求 | 仍要求位于同一 VPC/AZ，并需要路由/SG 和计划好的节点迁移 |
| 添加 VPC CIDR/子网 | 增加可分配地址空间 | 必须审查重叠/配额/路由/控制平面协调 |
| 扩大新建子网范围 | 规划地址增长 | 现有子网不能简单调整大小；范围必须适合关联的 VPC CIDR |
| IPv6 集群设计 | 消除大部分共享 IPv4 Pod 地址压力 | 需要规划新集群/IP 地址族、受支持的计算/CNI 和出站要求 |
| 替代 CNI | 改用不同的 IPAM/路由模型 | 需要受支持且经过测试的迁移；不能在原位切换清单 |
| Fargate | 将节点/IP 分配操作委托出去 | 每个 Pod 仍会消耗子网/VPC 地址；无法修复已耗尽的子网 |

**前缀模式：**普通 IPv4 前缀是 /28 网段，每个前缀占用一个地址槽位。原先“最高 5 倍”的说法是未经验证的通用声明，并非基准测试；应使用实际的实例/CNI/kubelet 限制。Pod 安全组可以共存，但 branch Pod 仍有自身的限制。检查碎片情况，并在需要时预留前缀空间或使用新子网；不要假设空闲单个 IP 的数量能证明存在连续地址块。

**预留池：**`WARM_IP_TARGET` 表示空闲地址余量，`MINIMUM_IP_TARGET` 表示最小总分配量。它们可能会覆盖前缀/ENI 预留目标行为。示例值 5/10 应根据工作负载和 API 调用预算进行调优：

```json
{"env":{"WARM_IP_TARGET":"5","MINIMUM_IP_TARGET":"10"}}
```
`MAX_ENI` 会将节点分配量限制在 EC2 实例类型上限以内；将其设为 5 并不会让只支持更少 ENI 的实例类型支持 5 个 ENI。更改限制前，应检查实际分配指标。

**自定义网络：**准备好位于同一 VPC、同一 AZ 的 Pod 子网和 SG 后，应通过现有 CNI 所有者合并此配置。稳定的区域标签为 `topology.kubernetes.io/zone`，而不是已弃用的 beta 标签：

```json
{
  "env": {
    "AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG": "true",
    "ENI_CONFIG_LABEL_DEF": "topology.kubernetes.io/zone"
  }
}
```

```yaml
apiVersion: crd.k8s.amazonaws.com/v1alpha1
kind: ENIConfig
metadata:
  name: us-west-2a
spec:
  subnet: subnet-REPLACE_WITH_POD_SUBNET_IN_SAME_VPC_AND_AZ
  securityGroups:
  - sg-REPLACE_WITH_APPROVED_POD_GROUP
```
为每个使用的 AZ 创建匹配的 ENIConfig。必须审查节点注解覆盖。带有正确区域标签的替换节点可以复用现有 ENIConfig，无需每次都重新创建。现有 Pod 不会立即全部切换网络。应验证替换节点，并在检查容量、PDB 和数据后执行迁移。

**CIDR/子网更改：**通过相应的 IaC 所有者添加符合条件且不重叠的 CIDR 和关联子网，然后审查路由、安全、Endpoint 和发现标签。对于控制平面操作，EKS 最多可能需要一小时才能识别新关联的 VPC CIDR。创建 /16 子网也需要一个可用且已关联的 /16 范围；“更大”并不能绕过 VPC 限制。

**替代 CNI/IPv6：**规划完整的控制平面、DNS、Service/负载均衡器、策略、引导和回滚路径。不要在运行中的集群上应用随时变化的 Calico overlay 清单并禁用 aws-node，将其作为通用切换方式。现有 EKS 集群的 IP 地址族无法简单切换为 IPv6。具体支持情况和 AWS 集成取决于所用的计算/CNI 模式。

**Fargate：**命名空间标签不会创建配置文件，`eks.amazonaws.com/v1alpha1 kind: FargateProfile` 也不是内置 Kubernetes API。请使用 EKS API 或 eksctl（或明确安装的受支持控制器）。此 API 示例需要一个未使用的配置文件名称、经过审查的私有子网和执行角色：

```bash
# New profile example; this does not create or enlarge subnet address space.
aws eks create-fargate-profile --cluster-name "${EXAMPLE_CLUSTER:?}" \
  --region "${EXAMPLE_REGION:?}" --fargate-profile-name "${NEW_FARGATE_PROFILE:?}" \
  --pod-execution-role-arn "${FARGATE_EXECUTION_ROLE_ARN:?}" \
  --subnets "${PRIVATE_SUBNET_A:?}" "${PRIVATE_SUBNET_B:?}" \
  --selectors '[{"namespace":"ipam-fargate"}]'
```
应单独创建匹配的命名空间/工作负载，并验证配置文件已激活。Fargate 改变的是运维责任，而不是所选子网有限的地址容量。应根据测量得到的需求比较各种补救方法，而不是同时套用所有策略。本次审计未执行网络迁移或性能基准测试。

</details>


## VPC 基础检查

11. 哪一对子网网段对齐，且不与公有的 10.0.0.0/24 和 10.0.1.0/24 重叠？
   * A) 10.0.2.0/22 和 10.0.6.0/22
   * B) 10.0.4.0/22 和 10.0.8.0/22
   * C) 10.0.0.0/22 和 10.0.1.0/22
   * D) 任意两个不同的字符串

<details>
<summary>显示答案</summary>

**答案：B) 10.0.4.0/22 和 10.0.8.0/22**

/22 的起始位置必须是第三个八位组中四的倍数。将 10.0.2.0/22 规范化后会得到 10.0.0.0/22，因而与公有网段重叠。

</details>

12. 在使用任何资源之前，普通 AWS IPv4 /24 子网可分配多少个地址？
   * A) 256
   * B) 254
   * C) 251
   * D) 始终为 240

<details>
<summary>显示答案</summary>

**答案：C) 251**

AWS 会在普通子网中保留前四个地址和最后一个地址。总数为 256，可分配数量为 251；BYOIP 有文档记录的例外情况。

</details>

13. elb 子网角色标签会创建到 Internet Gateway 的路由吗？
   * A) 会
   * B) 不会；路由配置与控制器发现彼此独立
   * C) 仅在私有子网中会
   * D) 它还会开放所有安全组

<details>
<summary>显示答案</summary>

**答案：B) 不会；路由配置与控制器发现彼此独立**

标签可能会影响发现行为，具体取决于控制器/版本/功能开关。它们不会创建路由，也不构成安全边界。

</details>

14. 每个 EKS 节点都必须通过公有互联网路径访问网络吗？
   * A) 是，始终通过 NAT gateway
   * B) 是，始终通过 IGW
   * C) 否；所需的服务访问可以使用适当的私有 Endpoint/镜像
   * D) 不需要任何网络访问

<details>
<summary>显示答案</summary>

**答案：C) 否；所需的服务访问可以使用适当的私有 Endpoint/镜像**

应规划实际的 API、注册表、DNS 和工作负载依赖项。AWS EKS 服务 Endpoint 与 Kubernetes 集群 API Endpoint 不同。

</details>

15. 控制平面流量通常使用哪个 kubelet 目标端口？
   * A) 所有 TCP 端口 1025–65535
   * B) TCP 10250
   * C) 默认情况下的所有 NodePort
   * D) 仅 UDP 53

<details>
<summary>显示答案</summary>

**答案：B) TCP 10250**

应分别检查私有 API TCP443、DNS TCP/UDP53、实际 webhook/工作负载端口和真实 SG 关联。SG 的有状态返回流量与无状态 NACL 规则不同。

</details>

## 参考资料

- [VPC/子网要求](https://docs.aws.amazon.com/eks/latest/userguide/network-reqs.html)
- [VPC CNI 1.23.0](https://github.com/aws/amazon-vpc-cni-k8s/blob/v1.23.0/README.md)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS 原生策略](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html)
- [LBC 3.5 Service 注解](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [LBC 子网发现](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/deploy/subnet_discovery.md)
- [NLB 监听器](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [NLB 日志](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-access-logs.html)
- [CoreDNS cache](https://coredns.io/plugins/cache/)
- [CoreDNS cache 实现](https://github.com/coredns/coredns/blob/v1.14.7/plugin/pkg/cache/cache.go)
