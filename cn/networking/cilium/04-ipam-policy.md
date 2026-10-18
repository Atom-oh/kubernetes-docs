# IPAM 和网络策略

> **审查基线**：Cilium 1.20.3；已在 Kubernetes 1.33–1.36 上测试。资源 API 版本和平台要求另行检查。
> **上次审查**：October 16, 2026

## 实验环境设置

使用[安装配置](README.md)和[网络前置条件](03-networking.md)来准备一个可随时销毁的 Linux 集群。确保 kubectl 与 API 服务器版本偏差处于支持范围内。以下 IPAM 配置是安装时可选的方案，或有文档记录的迁移方案，并非可在运行中的集群上依次应用的 ConfigMap 开关。

策略实验使用自己的命名空间和下方相匹配的工作负载，替换旧版 Cilium 1.14 Star Wars 清单；旧清单中的标签与这些策略不匹配。请先检查现有的 Kubernetes/Cilium 集群范围策略和准入设置；新建命名空间不会覆盖这些设置。

```bash
cilium status --wait
kubectl -n kube-system get configmap cilium-config -o yaml
kubectl get ciliumnodeconfigs --all-namespaces -o yaml
helm -n kube-system get values cilium --all
```

如果命名空间或 release 名称不同，请使用实际名称。期望的 Helm 值和 ConfigMap、节点覆盖设置、Operator 设置以及实际生效的 Agent 状态，分别回答不同的问题。包含 `ipam` 的 grep 结果并不能完整检查有效配置。

## IP 地址管理策略

Cilium Pod IPAM 分配工作负载地址。Kubernetes 分配 Service **ClusterIP**；Cilium **LoadBalancer IPAM** 是用于 LoadBalancer 地址的独立功能。`CiliumPodIPPool` 不分配 Service ClusterIP。

### 分配器和权威状态

| 配置 | 谁分配节点容量 / Pod IP？ | 要检查的状态 |
|---|---|---|
| `cluster-pool`（通用默认值） | Cilium Operator 为每个节点分配 CIDR；每个 Agent 在本地分配地址 | `CiliumNode.spec.ipam.podCIDRs` 和 Operator 状态 |
| `kubernetes` / host scope | Kubernetes 提供节点 PodCIDR；每个 Agent 在其中分配地址 | Kubernetes `Node.spec.podCIDRs` / `spec.podCIDR` 和受支持的提供商注解 |
| `multi-pool` | Operator 根据 Agent 需求从命名池中分配地址块；Agent 分配 Pod IP | `CiliumPodIPPool`、`CiliumNode.spec.ipam.pools.requested` / `allocated` |
| `crd` | 外部分配器提供可用地址；Agent 使用/释放这些地址 | `CiliumNode.spec.ipam.pool` / `status.ipam.used`（以及适用的 IPv6 字段） |
| `eni` | Operator 管理 AWS ENI/IP/前缀；Agent 将接口状态转换为其 multi-pool 分配器使用的状态 | `CiliumNode.status.eni.enis` 和特定模式的池/需求状态 |
| `azure` | 面向自托管 Azure VM/VMSS 集群的上游 Operator/Agent 集成 | Azure/CiliumNode 分配状态 |
| `delegated-plugin` | Cilium CNI 调用另一个 IPAM 插件，例如托管 AKS 的 Azure IPAM | 提供商/插件状态；不要用上游 Azure IPAM 配置替代 |
| GKE 集成 | 上游 GKE 集成使用 host-scope `kubernetes` IPAM；托管 Dataplane V2 有其自身的管理机制 | 提供商配置和 Node CIDR；不是单独的 `gke` IPAM 值 |

cluster-pool 和 Kubernetes host scope 都在本地分配单个 Pod 地址。区别在于由谁分配**节点前缀**。二者都不会消除协调需求，也都不能保证用户提供的池不会与 VPC、节点网络、Service 范围或其他集群重叠。

已发布的 CRD/类型定义中，通用 CRD 后端分配使用 `pool` 和 `used`。部分说明文档仍使用 `available`/`inuse`；请使用已安装的 schema 和特定模式字段，不要照搬旧名称。1.20.3 中的 ENI 使用接口/multi-pool 路径，因此通用 CRD 后端字段并非其通用事实来源。

### Kubernetes/CNI 集成

kubelet 通过容器运行时请求 Pod sandbox 操作；支持 CNI 的运行时会调用 Cilium CNI 插件。地址分配取决于所选后端，之后由插件/Agent 配置 endpoint 网络。在 host-scope 模式下，Kubernetes 必须提供所需地址族的 CIDR，例如通过正确配置的节点 CIDR 分配器提供。

## IPAM 配置

以下内容是要合并到相应安装配置中的 **Helm 值片段**。请先检查 Pod/Service/节点/外部地址范围。

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


Operator 协调节点地址块，而不是集中为每个 Pod 地址逐一处理请求。在 `clusterPoolIPv4PodCIDRList` 中配置多个 CIDR 会扩大共用的分配空间；这与按工作负载选择命名池不同。

不要通过替换现有池列表条目来扩展运行中的集群。应按照文档化的扩展流程添加不冲突的 CIDR。节点掩码大小不是日常可变更的设置。每个地址块中的地址数量并不等同于可用 Pod 容量，因为部分地址会被保留或被节点本地设施使用。

对于已为 Kubernetes/Cilium 双栈做好准备的集群：

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


启用这两个 Cilium 地址族标志，本身并不会配置 Kubernetes Service CIDR、底层网络 IPv6 连通性或云平台支持。

### Multi-Pool 和 CiliumPodIPPool

文档记录的模式是 `multi-pool`；在 1.20 中，资源 API 仍为 `cilium.io/v2alpha1`（在 **[1.21 预发布版]**中，`CiliumPodIPPool` 以 `cilium.io/v2` 提供，该版本将成为存储版本，`v2alpha1` 将弃用，并且 `spec.ipv4.pool`/`spec.ipv6.pool` 增加了按 CIDR 配置的 `reservedRanges`；这些字段仅存在于 `v2` 中）。不要仅凭 API 后缀推断功能的成熟度。上游 multi-pool 教程还要求设置 `kubeProxyReplacement=true` 和 `bpf.masquerade=true`（如使用 iptables masquerade，则需要设置 `egressMasqueradeInterfaces`）；下方示例包含这些设置。有关分配内部机制、池大小和迁移，请参阅 [IPAM 深入介绍](10-ipam-deep-dive.md)。在使用此模式的新集群上，请提供默认池以处理常规分配：

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


此额外命名池使用当前的 `cidrs` 和 `maskSize` 字段：

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


该池资源的作用范围是整个集群。`podSelector` 和 `namespaceSelector` 是两个独立字段；如果同时配置，两者都必须匹配。旧示例中的 `ipv4.cidr`、`blockSize` 和通用 `selector` 无效。

选择器示例如下：

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


仅在已准备好的 multi-pool 安装上应用这些内容。如果需要匹配非默认选择器，命名空间的 `require-pool-match` 注解会阻止自动回退到默认池。

池的选择顺序为：显式 Pod/namespace `ipam.cilium.io/ip-pool` 或地址族池注解，然后是自动选择器，最后是默认池。自动选择必须为相应地址族精确匹配一个池；选择器重叠会导致分配失败。池注解影响的是**新分配**，不会更改已运行 Pod 的 IP。也可以通过 `CiliumNodeConfig` 配置节点专用默认值。

池选择不能替代网络授权：应控制谁可以更改工作负载标签/注解，并单独实施流量策略。池的 CIDR 不得重叠。不要随意移除正在使用的范围/池；`maskSize`、`allowFirstIP` 和 `allowLastIP` 均不可变。首/末地址保留规则对小前缀有文档说明的例外情况。

目前有文档记录的在线迁移路径是从 **cluster-pool 迁移到 multi-pool**。这并不意味着可以随意在线更改 IPAM，也不代表可以未经规划反向迁移。请遵循其前置条件以及工作负载/容量检查；本章不会执行任何迁移。

### AWS ENI

请使用完整的 EKS/ENI 安装配置，以便设置路由、Operator IAM、子网/实例容量和节点准备工作。以下片段展示了当前的键，包括可选的 IPv4 前缀委派：

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

`eni.enabled=true` 会使 chart 默认将 `routingMode` 设为 `native`，并启用 endpoint 路由，因此此处省略这些键（1.20.2 中的 Helm 模板 `cilium-configmap.yaml`）。


`eni.awsEnablePrefixDelegation` 要求实例/子网配置支持所请求的前缀。一个 IPv4 `/28` 包含 16 个地址，但这并不保证在所有配置中都能额外调度 16 个 Pod。此选项默认禁用。不要添加虚构的 `eni-prefix-delegation-enabled` 键。

Operator 会调用 EC2 API；预分配可以减少每个 Pod 的延迟，但无法消除配额、API 或子网耗尽问题。`eni.eniTags` 会为受管接口添加标签。除非确有需要且已验证，否则应让 SDK 解析适当的 EC2 endpoint，不要设置 `eni.ec2APIEndpoint` 覆盖值。

此示例使用 IPv4。ENI 参考文档将 IPv6 标记为 beta，且其前缀/分配行为不同；平台验证与启用 `ipv6.enabled` 是两回事。AWS VPC CNI chaining 会将地址管理权保留给 AWS VPC CNI。普通 EC2、Hybrid Nodes、Fargate 和 Auto Mode 的安装/支持范围各不相同；Fargate 和 Auto Mode 不能使用此替代配置。

<span id="querying-per-node-podcidrs-via-ciliumnode-cr"></span>


## 查询每个节点的分配状态

### CiliumNode 示例

这是一个**示意性的只读对象结构**，不是可用于覆盖 Operator 管理状态的清单：

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


第一个地址可能是 `CiliumInternalIP`，而不是底层节点的 `InternalIP`。可能存在多个 InternalIP/地址族和多个分配条目。即使地址类型为 InternalIP，它也只是网络设计中的候选地址，并不意味着它自动成为每台路由器都可用的下一跳。

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

对于其他 IPAM 模式，某个字段不存在/为空可能是正常情况。对于 Kubernetes host scope，请检查 Kubernetes Node：

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

这些查询会保留所有相关地址/CIDR，而不是悄悄选取 `[0]`。它们生成的是清单，不是 `ip route add` 命令。请通过网络的路由流程选择接口/下一跳，并验证转发/返回路径。不要假设应该通过某个无关路由器上的第一个地址安装每个 CIDR。

此清单可用于制定 [EKS Hybrid Nodes 网络规划](../../eks-hybrid-nodes/02-network-configuration.md)，但不能替代该环境的路由和可达性检查。

## 网络策略设计与实施

### 资源和规则语义

- 带命名空间的 `CiliumNetworkPolicy` 用于选择其命名空间中的 endpoint；`CiliumClusterwideNetworkPolicy` 用于整个集群范围。只有在配置了 host firewall 时，后一种资源才支持 host-firewall `nodeSelector`。
- `endpointSelector` 用于标识策略作用对象；ingress/egress 描述相对于这些对象的流量。Cilium 规则中的 `spec.labels` 用于存储可选的标识/元数据，不是继承其他策略的引用。Kubernetes `metadata.labels` 用于标记资源本身。
- 适用策略所允许的流量会合并；显式 deny 规则具有文档所述的优先级。另一个不受限制的 L4 allow 可能绕过重叠的 L7 限制性 allow。
- 默认拒绝按流量方向分别生效。应有意保留必要的 DNS/应用路径，并检查实际生效的策略和真实流量。仅仅禁用默认拒绝并不是通用的 L7 试运行模式。

### 匹配策略的实验环境

在可随时销毁的集群中，于同一个 shell 里运行以下步骤：

```bash
set -euo pipefail
kubectl create namespace cilium-ipam-policy-demo
kubectl label namespace cilium-ipam-policy-demo docs-audit-lab=cilium-ipam-policy-04
```

如果命名空间已存在，请停止操作，并始终一致地选择一个新名称。这些工作负载使用官方 CLI 的测试镜像，以及策略所使用的标签：

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

首先也要从 outsider 确认基线连通性。Backend 的反亲和性要求有另一个符合条件的节点。下方的数据库规则用于演示额外的应用依赖；本实验不会部署或验证数据库服务器。

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


应用 `backend-l4.yaml`，等待 backend 所在 Agent 上的策略生效，并检查新的请求。Frontend 应保留访问权限；要确认 outsider 被拒绝，需要流量证据，不能只看 curl 是否返回非零退出码。

### L7 HTTP 策略

这是对同一 `backend-access` 资源的**另一种定义**，而不是第二条存在重叠的 allow 策略。应用此文件会替换本实验的 L4 版本；仍需检查其他适用策略。

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

策略生效后，将允许 GET `/`，也允许仅在 `content-type: application/json` 值完全匹配时执行 POST `/`。对其他路径/方法的请求应被代理拒绝。应用本身必须实现允许的操作；策略允许并不保证应用执行成功。演示服务器已知的 readiness 路径是 GET `/`。

HTTP 方法/路径字段是正则表达式。示例应使用锚点；改编时要转义元字符。HTTP/gRPC 规则需要 Envoy 和可见的应用流量；必要时还要配置 TLS 终止/拦截。gRPC 服务/方法信息通过 HTTP/2 路径传递，元数据通过标头传递，不存在单独的 `rules.grpc` 字段，也不支持任意过滤 protobuf 负载。

### Kafka 策略边界

当前 Cilium 不提供已移除的 `rules.kafka` API。不要应用旧版 topic/API key/client ID YAML。应使用适当的 L4 连通性规则连接到 broker 的**实际监听端口**，并在 broker 中配置 topic 访问等身份验证/授权。NetworkPolicy 既不能替代 broker 授权，也不会启用加密。

### DNS/FQDN 策略

此示例假设所选 resolver 是位于 `kube-system` 中、监听 TCP/UDP 53 端口的 CoreDNS/kube-dns Pod。请先检查 Pod 实际使用的 resolver；NodeLocal DNS、OpenShift 和托管 DNS 路径需要各自匹配的配置。

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


DNS L7 规则会将匹配的 resolver 流量重定向到 Cilium DNS 代理，以便其学习名称到 IP 的解析结果。仅允许端口 53 并不能提供这种观测能力。`matchPattern: "*"` 允许向选定的 resolver 发起 DNS 查询；HTTPS 出站流量则单独限制为 `toFQDNs` 名称所解析到的 IP。在声称外部测试成功之前，应将 `api.example.com` 替换为可解析且受控的测试名称。

`*.googleapis.com` 匹配该后缀下的一级标签；它不会匹配顶级域名本身或多级标签。在此版本中，`**.googleapis.com` 可以匹配一个或多个子域层级，但仍不包括顶级域名本身。DNS TTL/缓存状态和新查询都很重要。允许名称对应的 IP，并不等于检查 HTTP hostname、URL 或应用用户授权。

默认 DNS 代理在 Agent 中运行；独立 DNS 代理仍属于文档记录的 alpha 功能。DNS 策略并非在所有情况下都需要 Envoy。对于 OpenShift，官方示例使用 `openshift-dns` resolver 配置和 5353 端口，不应盲目照搬此规则。

### CIDR、Service 和实体

| 规则 | 范围 |
|---|---|
| `toCIDR` / `toCIDRSet` | 选择 IP 前缀，主要用于外部对等端。默认情况下，它们不能替代 Cilium 管理的 Pod/节点选择器；针对 `pods`/`nodes` 的文档化 CIDR 匹配可选功能属于 beta，且会占用 identities |
| `toServices` | 将 Service 选择器或无选择器的 EndpointSlice 地址解析为策略选择器；不会创建 Service 或路由。无选择器的情况受 CIDR 模式限制 |
| `world` | 范围宽泛的集群外身份类别，不等于“仅限公共互联网”，也不是命名的远程集群选择器 |
| `cluster` / `cluster-mesh` | `cluster` 涵盖本地集群 endpoint 以及文档所述的保留实体/远程节点；`cluster-mesh` 还会选择已建立 mesh 的集群中的 endpoint |
| `all` | 范围宽泛的组合，包含集群/mesh 和外部对等端；不是最小权限的捷径 |

对于 API server 访问，请使用文档所述的 `kube-apiserver` entity 行为，不要假设 `toServices: default/kubernetes` 具有普通工作负载选择器语义。

## 多集群场景

Cluster Mesh 会共享状态，同时保持 Kubernetes 集群和网络命名空间相互独立。远程节点不会成为本地 Kubernetes Node 对象，策略资源也不会自动分发。

```text
State:  cluster A Cluster Mesh control plane <-- mTLS --> cluster B control plane
Data:   Pod A --> node A datapath --> reachable network --> node B datapath --> Pod B
```

Cluster Mesh API server 会同步状态；Pod 数据包不需要经过它。控制平面的 mTLS 本身不会加密 Pod 到 Pod 的流量。

### 设置前置条件和部分步骤

准备独立的集群，确保 Pod CIDR 不重叠、节点 InternalIP 可达、网络路径已放行、数据平面模式相同，并且 Cilium 版本处于文档规定的一个次要版本差异范围内。Native routing 还要求所有远程 Pod 范围均可达，并且包含在配置的 native-routing CIDR 中。在安装时分配唯一的 Cilium 名称/ID（例如 `cluster-a`/1 和 `cluster-b`/2），并配置对等证书信任。

以下是在这些前置条件以及专用 NodePort 控制平面路径准备好**之后**执行的部分步骤。Kubeconfig context 名称不必与 Cilium 集群名称相同：

```bash
export CTX_A=prepared-context-a
export CTX_B=prepared-context-b
cilium clustermesh enable --context "$CTX_A" --service-type NodePort
cilium clustermesh enable --context "$CTX_B" --service-type NodePort
cilium clustermesh connect --context "$CTX_A" --destination-context "$CTX_B"
cilium clustermesh status --context "$CTX_A" --wait
cilium clustermesh status --context "$CTX_B" --wait
```

此流程不会创建 VPC peering/VPN、路由、防火墙、私有 endpoint 或证书信任。请遵循完整的平台特定设置流程；不要随意更改运行中集群的名称/ID。

### Global Service 和跨集群策略

在每个已准备好的集群中创建匹配的命名空间和实际后端工作负载，然后使用**相同的 Service 名称和命名空间**以及兼容的端口：

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


`service.cilium.io/global` 是当前使用的注解。默认情况下，global service 会共享本地后端；设置 `service.cilium.io/shared: "false"` 会停止向对等集群共享这些后端，但不一定会阻止本地客户端使用远程后端。本地 ClusterIP 不必相同。

不要仅凭此注解就承诺自动故障转移。默认情况下，不可达集群的状态会保留（`clustermesh.cacheTTL: 0s`）；配置为正数的 TTL 可以在控制平面断开后撤销过期的远程数据。这不等同于应用健康探测，也不保证零停机。

当 `cluster-a` 中存在指定的源工作负载时，在目标集群的 `mesh-demo` 命名空间中应用此 ingress 策略：

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


集群标签使用已配置的 **Cilium 集群名称**，而不是 kubeconfig context。在当前 Cilium 中，endpoint selector 默认限定在本地集群，除非显式指定对等集群。请分别在每个集群中安装所需策略，并测试两个方向的流量。

## 验证和清理

示例已依据特定版本的 schema、配置/源代码约定和范围有限的本地 fixture 进行检查。此次审查并未声称实际 IP 分配、内核策略强制、云资源创建、数据库运行或跨集群流量成功。

检查期望状态和实际生效状态，确认基线连通性成功，然后将预期拒绝与相关流量关联起来。确认所有权后，仅清理本次运行创建的命名空间策略工作负载。对于单独的 multi-pool 实验，请先释放工作负载并确认池分配已不再使用，再考虑移除池；切勿把删除活动中的 CiliumNode/池状态当作捷径。

## 来源

- [IPAM 模式/迁移](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/index.rst)、[cluster pool](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/cluster-pool.rst)、[host scope](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/kubernetes.rst)、[multi-pool](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/multi-pool.rst)、[迁移流程](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst)
- [PodIPPool schema](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2alpha1/ciliumpodippools.yaml)、[CiliumNode schema](https://github.com/cilium/cilium/blob/v1.20.3/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnodes.yaml)、[ENI IPAM](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)、[Helm 值](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)、[EKS CNI 边界](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [策略规则 API](https://github.com/cilium/cilium/blob/v1.20.3/pkg/policy/api/rule.go)、[L3 规则](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer3.rst)、[L7 规则](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)、[DNS 策略](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/dns.rst)、[通配符实现](https://github.com/cilium/cilium/blob/v1.20.3/pkg/fqdn/matchpattern/matchpattern.go)
- [Cluster Mesh 设置](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/setup.rst)、[架构](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/intro.rst)、[global service](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/global-services.rst)、[跨集群策略](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/clustermesh/policy.rst)


[返回主页](README.md)

## 测验

[检查你对 IPAM 和策略的理解](../../quizzes/networking/cilium/04-ipam-policy-quiz.md)。
