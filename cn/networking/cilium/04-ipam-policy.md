# IPAM 和网络策略

> **审查基线**：Cilium 1.20.2；已测试 Kubernetes 1.33–1.36。资源 API 版本和平台要求会单独检查。
> **最后审查**：October 15, 2026

## 实验环境设置

使用[安装配置文件](README.md)和[网络前提条件](03-networking.md)准备一个可随时销毁的 Linux 集群。将 kubectl 保持在所支持的 API-server 版本偏差范围内。下面的 IPAM 配置文件是用于安装或有文档记录的迁移的替代方案，而不是应按顺序应用到运行中集群的 ConfigMap 切换项。

策略实验使用自己的 namespace 和以下匹配的工作负载，取代了旧的 Cilium 1.14 Star Wars 清单，因为其标签不匹配这些策略。请先检查现有 Kubernetes/Cilium 集群范围的策略和准入设置；新建 namespace 不会覆盖它们。

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

如果实际的 namespace/release 名称不同，请使用实际名称。期望的 Helm values 和 ConfigMaps、节点覆盖设置、operator 设置以及实际的 agent 状态回答的是不同的问题。包含 `ipam` 的 grep 结果并不是完整的有效配置检查。

## IP 地址管理策略

Cilium Pod IPAM 分配工作负载地址。Kubernetes 分配 Service **ClusterIP**；Cilium **LoadBalancer IPAM** 是用于 LoadBalancer 地址的独立功能。`CiliumPodIPPool` 不会分配 Service ClusterIP。

### 分配器和权威状态

| 配置 | 谁分配节点容量 / Pod IP？ | 要检查的状态 |
|---|---|---|
| `cluster-pool`（通用默认值） | Cilium Operator 为每个节点分配 CIDR；每个 agent 分配本地地址 | `CiliumNode.spec.ipam.podCIDRs` 和 operator 状态 |
| `kubernetes` / 主机范围 | Kubernetes 提供节点 PodCIDR；每个 agent 在其中分配 | Kubernetes `Node.spec.podCIDRs` / `spec.podCIDR` 和受支持的 provider 注释 |
| `multi-pool` | Operator 根据 agent 需求从具名池中分配块；agent 分配 Pod IP | `CiliumPodIPPool`、`CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | 外部分配器提供可用地址；agent 使用/释放它们 | `CiliumNode.spec.ipam.pool` / `status.ipam.used`（以及适用的 IPv6 字段） |
| `eni` | Operator 管理 AWS ENI/IP/前缀；agent 将接口状态转换为其 multi-pool 分配器 | `CiliumNode.status.eni.enis` 和特定模式的池/需求状态 |
| `azure` | 用于自行管理的 Azure VM/VMSS 集群的上游 operator/agent 集成 | Azure/CiliumNode 分配状态 |
| `delegated-plugin` | Cilium CNI 调用另一个 IPAM plugin，例如托管 AKS 的 Azure IPAM | Provider/plugin 状态；不要替换上游 Azure IPAM 配置 |
| GKE 集成 | 上游 GKE 集成使用主机范围的 `kubernetes` IPAM；托管 Dataplane V2 有自己的所有权 | Provider 配置和 Node CIDR；不是单独的 `gke` IPAM 值 |

cluster-pool 和 Kubernetes 主机范围都会在本地分配单个 Pod 地址。区别在于谁分配**节点前缀**。两者都不会消除协调需求，也不保证用户提供的池不会与 VPC、节点网络、Service 范围或其他集群重叠。

已发布的 CRD/type 定义对通用 CRD 支持的分配使用 `pool` 和 `used`。一些说明性文档仍使用 `available`/`inuse`；请使用已安装的 schema 和特定模式字段，不要复制这些较旧的名称。1.20.2 中的 ENI 使用接口/multi-pool 路径，因此通用 CRD 支持的字段不是其通用的事实来源。

### Kubernetes/CNI 集成

kubelet 通过容器运行时请求 Pod sandbox 操作；支持 CNI 的运行时调用 Cilium CNI plugin。分配取决于所选 backend，之后 plugin/agent 配置 endpoint 网络。在主机范围模式下，Kubernetes 必须提供所需地址族的 CIDR，例如通过正确配置的 node-CIDR 分配器。

## IPAM 配置

这些是要合并到对应安装配置文件中的 **Helm value 片段**。请先审查 Pod/Service/节点/外部地址范围。

### Cluster Pool

**`cluster-pool-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
ipv4:
  enabled: true
ipv6:
  enabled: false
```


Operator 协调节点块，而不是为每个 Pod 地址发起中心化请求。`clusterPoolIPv4PodCIDRList` 中的多个 CIDR 会扩展公共分配空间；这不同于为每个工作负载选择具名池。

不要通过替换现有池列表条目来扩展运行中的集群。应通过有文档记录的扩展流程添加不冲突的 CIDR。节点掩码大小不是可常规变更的设置。每个块的地址数量不等于可用 Pod 容量，因为有些地址会被保留或供节点本地功能使用。

对于已准备好 Kubernetes/Cilium 双栈的集群：

**`dual-stack-values.yaml`**

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList:
    - 10.244.0.0/16
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList:
    - fd00:10:244::/104
    clusterPoolIPv6MaskSize: 120
ipv4:
  enabled: true
ipv6:
  enabled: true
```


启用这两个 Cilium 地址族标志本身不会配置 Kubernetes Service CIDR、底层 IPv6 连通性或云支持。

### Multi-Pool 和 CiliumPodIPPool

文档化的模式是 `multi-pool`；在 1.20 中，资源 API 仍为 `cilium.io/v2alpha1`（在 **[1.21 pre-release]** 中，`CiliumPodIPPool` 以 `cilium.io/v2` 提供服务，该版本成为存储版本，`v2alpha1` 被弃用，并且 `spec.ipv4.pool`/`spec.ipv6.pool` 为每个 CIDR 添加 `reservedRanges`；这些字段仅存在于 `v2` 中）。不要仅根据该 API 后缀推断功能的成熟度。上游 multi-pool 教程还要求 `kubeProxyReplacement=true` 和 `bpf.masquerade=true`（iptables masquerade 需要 `egressMasqueradeInterfaces`）；以下示例包含了这些配置。有关分配内部机制、池大小和迁移，请参阅 [IPAM deep dive](10-ipam-deep-dive.md)。在使用此模式的新集群上，请为普通分配提供默认池：

**`multi-pool-values.yaml`**

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipam:
  mode: multi-pool
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4:
          cidrs:
          - 10.244.0.0/16
          maskSize: 24
```


此附加具名池使用当前的 `cidrs` 和 `maskSize` 字段：

**`blue-pool.yaml`**

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumPodIPPool
metadata:
  name: blue-pool
spec:
  ipv4:
    cidrs:
    - 10.245.0.0/16
    maskSize: 24
  namespaceSelector:
    matchLabels:
      ipam-pool: blue
  podSelector:
    matchLabels:
      role: blue
```


池资源是集群范围的。`podSelector` 和 `namespaceSelector` 是独立字段，当两者都配置时，二者都必须匹配。旧的 `ipv4.cidr`、`blockSize` 和通用 `selector` 示例无效。

对于 selector 示例：

**`blue-namespace.yaml`**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ipam-selection-demo
  labels:
    ipam-pool: blue
  annotations:
    ipam.cilium.io/require-pool-match: 'true'
```


**`blue-pod.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: blue-client
  namespace: ipam-selection-demo
  labels:
    role: blue
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


仅在已准备好的 multi-pool 安装上应用这些内容。当要求非默认 selector 匹配时，namespace 的 `require-pool-match` 注释会阻止自动回退到默认池。

池选择依次遵循显式的 Pod/namespace `ipam.cilium.io/ip-pool` 或地址族池注释、自动 selector，然后是默认池。自动选择对于地址族必须恰好匹配一个池；重叠的 selector 会导致分配失败。池注释影响**新的分配**，而非已运行的 Pod IP。还可以通过 `CiliumNodeConfig` 配置节点特定的默认值。

池选择不能替代网络授权：控制谁可以更改工作负载标签/注释，并单独执行流量策略。池不得具有重叠的 CIDR。不得随意删除正在使用的范围/池；`maskSize`、`allowFirstIP` 和 `allowLastIP` 是不可变的。首/尾地址保留有已文档化的小前缀例外情况。

目前存在从 **cluster-pool 到 multi-pool** 的有文档记录的在线迁移。这并不授权任意实时 IPAM 变更或未经计划的反向迁移。请遵循其前提条件和工作负载/容量检查；本章不会执行迁移。

### AWS ENI

使用完整的 EKS/ENI 安装配置文件进行路由、operator IAM、subnet/instance 容量和节点准备。以下片段说明当前键，包括可选的 IPv4 前缀委派：

**`eni-values-fragment.yaml`**

```yaml
ipam:
  mode: eni
eni:
  enabled: true
  eniTags:
    team: platform
  awsEnablePrefixDelegation: true
ipv4:
  enabled: true
ipv6:
  enabled: false
```

`eni.enabled=true` 已使 chart 默认将 `routingMode` 设为 `native` 并启用 endpoint routes，因此此处省略这些键（1.20.2 中的 Helm 模板 `cilium-configmap.yaml`）。


`eni.awsEnablePrefixDelegation` 要求 instance/subnet 设置支持所请求的前缀。IPv4 `/28` 包含 16 个地址，并不保证在每种配置中都会额外提供 16 个可调度 Pod。默认值为禁用。不要添加虚构的 `eni-prefix-delegation-enabled` 键。

Operator 发起 EC2 API 调用；预分配可减少每个 Pod 的延迟，但无法消除配额、API 或 subnet 耗尽。`eni.eniTags` 为受管接口添加标签。除非经过深思熟虑且验证过 `eni.ec2APIEndpoint` 覆盖设置，否则应让 SDK 解析合适的 EC2 endpoint。

此示例为 IPv4。ENI 参考文档将 IPv6 记录为 beta，具有不同的前缀/分配行为；平台验证与启用 `ipv6.enabled` 是独立的。AWS VPC CNI chaining 将地址所有权保留给 AWS VPC CNI。普通 EC2、Hybrid Nodes、Fargate 和 Auto Mode 有不同的安装/支持边界；Fargate 和 Auto Mode 无法使用此替换配置文件。

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## 查询每个节点的分配状态

### CiliumNode 示例

这是一个**说明性的只读对象结构**，不是要应用以覆盖 Operator 所有状态的清单：

**`ciliumnode-example.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNode
metadata:
  name: hybrid-node-001
spec:
  addresses:
  - ip: 10.85.0.1
    type: CiliumInternalIP
  - ip: 10.80.1.10
    type: InternalIP
  ipam:
    podCIDRs:
    - 10.85.0.0/25
```


第一个地址可以是 `CiliumInternalIP`，而不是底层节点的 `InternalIP`。可以存在多个 InternalIP/地址族和多个分配条目。即使是带类型的 InternalIP，也只是网络设计的候选项，并非从每个 router 都自动有效的下一跳。

### 特定模式的清单

将此查询保存为 `ciliumnode-inventory.jq`：

**`ciliumnode-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.spec.addresses[]? |
    select(.type == "InternalIP") | .ip] | unique),
  clusterPoolPodCIDRs: (.spec.ipam.podCIDRs // []),
  multiPoolAllocations: (.spec.ipam.pools.allocated // []),
  eniInterfaceIDs: ((.status.eni.enis // {}) | keys),
  operatorStatus: (.status.ipam["operator-status"] // {})
}
```


```bash
kubectl get ciliumnodes -o json | jq -f ciliumnode-inventory.jq
```

对于不同的 IPAM 模式，不存在/为空的字段可能是正常的。对于 Kubernetes 主机范围，请改为检查 Kubernetes Node：

**`kubernetes-node-inventory.jq`**

```text
.items[] | {
  name: .metadata.name,
  internalNodeIPs: ([.status.addresses[]? |
    select(.type == "InternalIP") | .address] | unique),
  podCIDRs: (.spec.podCIDRs // []),
  legacyPodCIDR: (.spec.podCIDR // null)
}
```


```bash
kubectl get nodes -o json | jq -f kubernetes-node-inventory.jq
```

这些查询保留所有相关地址/CIDR，而不是静默选择 `[0]`。它们生成清单，而非 `ip route add` 命令。通过网络的路由流程选择接口/下一跳并验证转发/返回路径。不要假定每个 CIDR 都应通过无关 router 上的第一个地址安装。

该清单可以为 [EKS Hybrid Nodes 网络规划](../../eks-hybrid-nodes/02-network-configuration.md)提供信息，但不能替代该环境的路由和可达性检查。

## 网络策略设计与实现

### 资源和规则语义

- 具 namespace 范围的 `CiliumNetworkPolicy` 选择其 namespace 中的 endpoint；`CiliumClusterwideNetworkPolicy` 提供集群范围。仅后者支持 host-firewall `nodeSelector`，且需配置 host firewall。
- `endpointSelector` 标识主体；ingress/egress 描述相对于它们的流量。Cilium 规则 `spec.labels` 存储可选的标识/元数据，而不是继承另一策略的引用。Kubernetes `metadata.labels` 为资源本身添加标签。
- 适用策略允许的流量会合并；显式拒绝规则具有其文档化的优先级。另一个不受限制的 L4 allow 可绕过重叠的受 L7 限制 allow。
- 默认拒绝是方向特定的。应有意保留必需的 DNS/application 路径，并检查实际策略及真实流量。仅禁用默认拒绝并非通用的 L7 试运行模式。

### 匹配策略实验

在可随时销毁的集群中，在一个 shell 中运行以下步骤：

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

如果 namespace 已存在，请停止操作并始终使用一个新的名称。这些工作负载使用官方 CLI 的测试镜像和策略使用的标签：

**`policy-app.yaml`**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: cilium-ipam-policy-demo
  labels:
    app: frontend
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: v1
kind: Pod
metadata:
  name: outsider
  namespace: cilium-ipam-policy-demo
  labels:
    app: outsider
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      automountServiceAccountToken: false
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: frontend
            topologyKey: kubernetes.io/hostname
      containers:
      - name: http
        image: quay.io/cilium/json-mock:v1.4.1@sha256:6a66df90808a39c02e7a9d58af7bf0e54d8f8b7d4bc528f48c891969a7049195
        ports:
        - containerPort: 8080
          name: http
        readinessProbe:
          httpGet:
            path: /
            port: http
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: cilium-ipam-policy-demo
spec:
  selector:
    app: backend
  ports:
  - name: http
    port: 8080
    targetPort: http
    protocol: TCP
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: cilium-ipam-policy-demo
  labels:
    app: client
spec:
  automountServiceAccountToken: false
  containers:
  - name: client
    image: quay.io/cilium/alpine-curl:v1.10.0@sha256:913e8c9f3d960dde03882defa0edd3a919d529c2eb167caa7f54194528bde364
    command:
    - /usr/bin/pause
```


```bash
kubectl apply -f policy-app.yaml
kubectl -n cilium-ipam-policy-demo wait --for=condition=Ready \
  pod/frontend pod/outsider pod/client --timeout=120s
kubectl -n cilium-ipam-policy-demo rollout status deployment/backend --timeout=120s
kubectl -n cilium-ipam-policy-demo get pods -o wide --show-labels
BACKEND_IP=$(kubectl -n cilium-ipam-policy-demo get service backend -o jsonpath='{.spec.clusterIP}')
test -n "$BACKEND_IP"
kubectl -n cilium-ipam-policy-demo exec frontend -- \
  curl --fail --silent --show-error --max-time 5 "http://$BACKEND_IP:8080/"
```

首先也应确认来自 outsider 的基线连通性。Backend anti-affinity 需要另一个合格节点。以下 database 规则说明了额外的 application 依赖关系；本实验不部署或验证 database server。

### L3/L4 策略

**`backend-l4.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


应用 `backend-l4.yaml`，等待 backend 的 agent 上的策略实现，然后检查新的请求。Frontend 应保留访问权限；outsider 拒绝需要流量证据，而不只是非零 curl 退出。

### L7 HTTP 策略

这是同一 `backend-access` 资源的**替代定义**，不是第二个重叠的 allow 策略。应用它会替换本实验的 L4 版本；仍应检查其他适用策略。

**`backend-http.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: backend-access
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/$
        - method: ^POST$
          path: ^/$
          headerMatches:
          - name: content-type
            value: application/json
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: cilium-ipam-policy-demo
        k8s:app: database
    toPorts:
    - ports:
      - port: '3306'
        protocol: TCP
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
```


```bash
kubectl apply -f backend-http.yaml
kubectl -n cilium-ipam-policy-demo get cnp backend-access -o yaml
```

实现后，该策略允许 GET `/`，以及仅当精确的 `content-type: application/json` 值存在时允许 POST `/`。对其他路径/方法的请求应被 proxy 拒绝。应用程序本身必须实现允许的操作；策略许可不保证应用程序成功。演示 server 已知的就绪路径是 GET `/`。

HTTP method/path 字段是正则表达式。调整示例时应保持锚定并转义元字符。HTTP/gRPC 规则需要 Envoy 和可见的 application 流量；必要时必须配置 TLS 终止/拦截。gRPC service/method 信息位于 HTTP/2 path 和 header 中的 metadata 中，而非单独的 `rules.grpc` 字段或任意 protobuf-payload 过滤。

### Kafka 策略边界

当前 Cilium 不提供已移除的 `rules.kafka` API。不要应用旧的 topic/API-key/client-ID YAML。应对 broker 的**实际 listener port**使用合适的 L4 连通性规则，并在 broker 中配置 topic access 等 authentication/authorization。NetworkPolicy 既不能替代 broker authorization，也不会启用 encryption。

### DNS/FQDN 策略

此示例假设所选 resolver 是位于 `kube-system` 上、使用 TCP/UDP 53 的 CoreDNS/kube-dns Pod。请先检查 Pod 的实际 resolver；NodeLocal DNS、OpenShift 和托管 DNS 路径需要各自匹配的配置。

**`dns-egress.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-egress
  namespace: cilium-ipam-policy-demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```


DNS L7 规则将匹配的 resolver 流量重定向通过 Cilium 的 DNS proxy，以便它能学习名称到 IP 的响应。只允许 port 53 并不能提供这种观测。`matchPattern: "*"` 允许向所选 resolver 发起 DNS 查询；HTTPS egress 则单独限制为为 `toFQDNs` 名称学习到的 IP。在声称外部测试成功之前，请将 `api.example.com` 替换为可解析、受控的测试名称。

`*.googleapis.com` 匹配该后缀下的一个标签；它不匹配顶点或多个标签。在此版本中，`**.googleapis.com` 可匹配一个或多个 subdomain 层级，仍不包括顶点。DNS TTL/cache 状态和新的查找很重要。名称到 IP 的允许并非 HTTP hostname、URL 或 application-user authorization 检查。

默认 DNS proxy 在 agent 中运行；单独的独立 DNS proxy 被记录为 alpha。DNS 策略并不普遍需要 Envoy。对于 OpenShift，官方示例使用 `openshift-dns` resolver 配置和 port 5353，而不是盲目复制此规则。

### CIDR、Services 和 Entities

| 规则 | 边界 |
|---|---|
| `toCIDR` / `toCIDRSet` | 选择 IP 前缀，主要用于外部 peer。默认情况下，它们不能替代 Cilium 管理的 Pod/节点的 selector；已文档化的针对 `pods`/`nodes` 的选择加入 CIDR 匹配为 beta 且会消耗 identity |
| `toServices` | 将 Service selector 或无 selector 的 EndpointSlice 地址解析为策略 selector；它不会创建 Service 或进行路由。无 selector 的情况继承 CIDR 模式限制 |
| `world` | 宽泛的集群外 identity 类别，而不是“仅 public Internet”或具名远程集群 selector |
| `cluster` / `cluster-mesh` | `cluster` 覆盖本地集群 endpoint 以及文档化的保留 entity/远程节点；`cluster-mesh` 还选择 mesh 集群 endpoint |
| `all` | 包括 cluster/mesh 和外部 peer 的宽泛组合；不是最小权限捷径 |

对于 API-server 访问，请使用文档化的 `kube-apiserver` entity 行为，而不要假设 `toServices: default/kubernetes` 具有普通工作负载 selector 语义。

## 多集群场景

Cluster Mesh 在保持 Kubernetes 集群和网络 namespace 独立的同时共享状态。远程节点不会成为本地 Kubernetes Node 对象，策略资源也不会自动分发。

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

Cluster Mesh API server 同步状态；Pod 数据包不需要经过它。control-plane mTLS 本身不会加密 Pod-to-Pod 流量。

### 设置前提条件和部分流程

准备具有不重叠 Pod CIDR、可达节点 InternalIP、允许网络路径、相同 datapath 模式且 Cilium 版本位于文档化的一个次要版本差异范围内的独立集群。Native routing 还需要所有远程 Pod 范围均可达且包含在配置的 native-routing CIDR 中。在安装时分配唯一的 Cilium 名称/ID（例如 `cluster-a`/1 和 `cluster-b`/2），并配置信任 peer certificate。

以下是在准备好这些前提条件和私有 NodePort control-plane 路径**之后**的部分流程。Kubeconfig context 名称不必等于 Cilium cluster 名称：

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

这不会配置 VPC peering/VPN、routes、firewalls、private endpoints 或 certificate trust。请遵循完整的平台特定设置；不要随意更改运行中集群的名称/ID。

### Global Services 和跨集群策略

在每个已准备好的集群中创建匹配的 namespace 和实际 backend 工作负载，然后使用具有兼容 ports 的**相同 Service 名称和 namespace**：

**`global-service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: global-service
  namespace: mesh-demo
  annotations:
    service.cilium.io/global: 'true'
spec:
  type: ClusterIP
  selector:
    app: global-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
```


`service.cilium.io/global` 是当前注释。global service 默认共享本地 backend；`service.cilium.io/shared: "false"` 停止向 peer 共享它们，但不一定阻止本地 client 使用远程 backend。本地 ClusterIP 不必相同。

不要仅凭此注释承诺自动 failover。默认情况下，保留不可达 cluster 状态（`clustermesh.cacheTTL: 0s`）；配置为正值的 TTL 可在 control-plane 断开后撤销过期的远程数据。这不是 application health probe 或零停机保证。

当具名源工作负载存在于 `cluster-a` 时，请在目标集群的 `mesh-demo` namespace 中应用此 ingress 策略：

**`cross-cluster-policy.yaml`**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cluster-a-frontend
  namespace: mesh-demo
spec:
  endpointSelector:
    matchLabels:
      app: global-app
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: frontend-ns
        k8s:io.cilium.k8s.policy.cluster: cluster-a
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```


cluster 标签使用配置的 **Cilium cluster 名称**，而不是 kubeconfig context。在当前 Cilium 中，除非显式选择 peer，否则 endpoint selector 默认使用本地 cluster。在每个 cluster 中独立安装所需策略，并测试两个流量方向。

## 验证和清理

这些示例已针对 release-specific schema、configuration/source contract 和有限的本地 fixture 进行检查。本审计并不声称已经完成实时 IP 分配、kernel 策略执行、cloud 配置、运行中的 database 或成功的跨集群流量。

检查期望和实际状态，验证成功的基线，然后将预期拒绝与相关 flow 关联。仅在验证所有权后清理本次运行的具 namespace 范围策略工作负载。对于独立的 multi-pool 演练，请先释放工作负载并验证池分配不再使用，再考虑删除池；绝不要将删除活跃的 CiliumNode/池状态作为捷径。

## 来源

- [IPAM 模式/迁移](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst), [cluster pool](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst), [host scope](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/kubernetes.rst), [multi-pool](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst), [迁移流程](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [PodIPPool schema](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml), [CiliumNode schema](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml), [ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [Helm values](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [EKS CNI 边界](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [策略规则 API](https://github.com/cilium/cilium/blob/v1.20.2/pkg/policy/api/rule.go), [L3 规则](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer3.rst), [L7 规则](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/policy/layer7.rst), [DNS 策略](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/dns.rst), [通配符实现](https://github.com/cilium/cilium/blob/v1.20.2/pkg/fqdn/matchpattern/matchpattern.go)
- [Cluster Mesh 设置](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/setup.rst), [架构](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/intro.rst), [global services](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/global-services.rst), [跨集群策略](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/clustermesh/policy.rst)


[返回主页](README.md)

## 测验

[检查您对 IPAM 和策略的理解](../../quizzes/networking/cilium/04-ipam-policy-quiz.md)。