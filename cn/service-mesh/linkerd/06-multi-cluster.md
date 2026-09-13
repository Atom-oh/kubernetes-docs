# Linkerd 多集群

> **最后更新**：2026 年 9 月 11 日 · Linkerd edge-26.9.1 / chart 2026.9.1 · Gateway API 1.5.1

Linkerd 跨集群边界镜像选定服务信息。需要正常控制平面发现路径和适当数据平面网络路径。它不合并集群、不复制应用数据，也不为影子测试复制每个请求。

## 通信模式

| 模式 | 发现/服务选择 | 数据路径和身份 |
|---|---|---|
| 分层 | 默认 `mirror.linkerd.io/exported=true` | 源客户端代理 → 目标集群网关 → 服务器；原始调用方身份在网关丢失 |
| 扁平 / 远程发现 | `mirror.linkerd.io/exported=remote-discovery` | 直接跨集群 Pod 连接；保留原始工作负载身份 |
| 联邦 Service | `mirror.linkerd.io/federated=member` | 扁平网络中同名/同命名空间服务的并集；要求网格客户端 |

源集群镜像控制器监视**目标 Kubernetes API**，不是另一镜像控制器。镜像 Service 是 Kubernetes 发现对象，不是执行 TLS 的进程。通常在对应命名空间命名为 `<service>-<Link cluster name>`。

![分层路径：源客户端代理连接远程网关，网关另建连接到网格服务器。无需源侧网关跳点，最终服务器无法通过该网关收到原始客户端身份。](../../.gitbook/assets/en-service-mesh-linkerd-06-multi-cluster-2.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-06-multi-cluster-2.html)

分层模式要求源客户端可访问目标网关。扁平/联邦模式还要求集群间直接、无歧义 Pod IP 路由及相同 Linkerd 控制平面命名空间。仅内部负载均衡器或 VPC 端点不建立扁平网络。

## 前提条件和共享信任

使用两个准备好的集群，显式 kubeconfig 上下文为 `west` 和 `east`。这些是本地别名，不证明其 AWS 账户或区域。使用[安装指南](01-installation.md)中的兼容 Kubernetes/Gateway API 版本、Linux 工作节点/CNI 设置和固定 CLI；不要将最新 Kubernetes 版本等同于 Linkerd 兼容。

两套 Linkerd 安装必须信任相关签发者链。共同公有根是最简单安排；也支持包含多个适当根的共享包。集群不必共享签发者私钥或工作负载证书。

![一种常见 PKI 安排：共享公有根，各集群独立签发者，每代理独立叶证书。根私钥不分发到所有代理；独立签发者不会天然让同名 ServiceAccount 成为不同集群身份。](../../.gitbook/assets/en-service-mesh-linkerd-06-multi-cluster-3.png)

[查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-linkerd-06-multi-cluster-3.html)

**仅用于全新隔离实验**，以下创建共同根及独立 ECDSA P-256 签发者。十年根寿命是示例，不是 CLI 默认或通用建议：

```bash
set -euo pipefail
umask 077
# New lab PKI only. The chosen root lifetime is an example, not a default.
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca --kty EC --curve P-256 \
  --not-after 87600h --no-password --insecure
step certificate create identity.linkerd.cluster.local issuer-west.crt issuer-west.key \
  --profile intermediate-ca --kty EC --curve P-256 \
  --ca ca.crt --ca-key ca.key --not-after 8760h --no-password --insecure
step certificate create identity.linkerd.cluster.local issuer-east.crt issuer-east.key \
  --profile intermediate-ca --kty EC --curve P-256 \
  --ca ca.crt --ca-key ca.key --not-after 8760h --no-password --insecure
cp ca.crt shared-roots.pem
```

`--no-password --insecure` 生成未加密私钥文件。保留在受保护工作位置，仅分发公有信任包及各集群所需签发者材料。现有网格使用分阶段[信任轮换流程](04-security.md)；不要仅为遵循新安装示例而替换根。

### 使用显式上下文安装核心

下方是在两集群完成安装指南 Gateway API/CNI 前提后的 CLI 管理核心安装路径。Helm 管理核心应保留原所有者，并通过其已审核 values 传入各集群对应凭证。

命令展示兼容 Linux 工作节点的默认 proxy-init 路径。Linkerd CNI 安装还必须通过所选安装配置传入 `cniEnabled:true`。

```bash
set -euo pipefail
# New CLI-owned installations only; complete Gateway API/CNI prerequisites first.
linkerd --context west install --crds | kubectl --context west apply -f -
linkerd --context west install \
  --identity-trust-anchors-file shared-roots.pem \
  --identity-issuer-certificate-file issuer-west.crt \
  --identity-issuer-key-file issuer-west.key | kubectl --context west apply -f -

linkerd --context east install --crds | kubectl --context east apply -f -
linkerd --context east install \
  --identity-trust-anchors-file shared-roots.pem \
  --identity-issuer-certificate-file issuer-east.crt \
  --identity-issuer-key-file issuer-east.key | kubectl --context east apply -f -
linkerd --context west check
linkerd --context east check
```

需要流量统计时单独安装 Viz。多集群扩展自身检查不是应用/业务验证。

## 扩展和定向链接

本练习使用 Helm 管理多集群扩展及对等控制器。所选 CLI 旧 `multicluster link` 已弃用；使用 `link-gen` 生成 Link 和凭证 Secret，配合 chart 的 `controllers` 列表。

### 基础安装

对于**已安装 AWS Load Balancer Controller 的 EKS**，保存为 `mc-base-values.yaml`。它请求内部 TCP NLB；确保已设计对端路由、DNS、安全组和必需端口。其他平台需要自己的受支持负载均衡配置。

```yaml
gateway:
  enabled: true
  serviceType: LoadBalancer
  loadBalancerClass: service.k8s.aws/nlb
  serviceAnnotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
```

```bash
helm repo add linkerd-edge https://helm.linkerd.io/edge
helm repo update linkerd-edge
# Initially install gateway/remote-access prerequisites, without peer controllers.
helm --kube-context west upgrade --install linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster --create-namespace -f mc-base-values.yaml \
  --wait --timeout 10m
helm --kube-context east upgrade --install linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster --create-namespace -f mc-base-values.yaml \
  --wait --timeout 10m
kubectl --context west -n linkerd-multicluster get svc linkerd-gateway -o yaml
kubectl --context east -n linkerd-multicluster get svc linkerd-gateway -o yaml
```

目标 Service 必须具有入口 IP **或主机名**，基于网关的 Link 生成才会成功。AWS NLB 通常暴露主机名，`link-gen` 可接受。网关数据流量默认 4143；就绪探测默认 4191。任一端口可达都不证明远程 Kubernetes API 或每个应用健康。

### East 使用 West

将期望控制器列表保存为 `mc-east-links.yaml`：

```yaml
controllers:
- link:
    ref:
      name: west
```

```bash
set -euo pipefail
umask 077
# Read West's configuration; install the generated credentials/Link into East.
linkerd --context west multicluster link-gen --cluster-name west > west-link.yaml
# Review public metadata and target endpoint without printing credential values.
kubectl --context east apply -f west-link.yaml
helm --kube-context east upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster -f mc-base-values.yaml -f mc-east-links.yaml \
  --wait --timeout 10m
kubectl --context east -n linkerd-multicluster get links.multicluster.linkerd.io
linkerd --context east multicluster check
linkerd --context east multicluster gateways
```

`link-gen` 读取 West API 位置/CA 和选定远程访问 ServiceAccount 令牌。输出一个 Link 和两个凭证 Secret，分别位于 `linkerd-multicluster` 和控制平面命名空间 `linkerd`。它本身不安装网络路由或源镜像控制器。

将生成文件视为凭证：限制访问，不提交或把内容打印到日志。生成 kubeconfig 必须可由控制器使用，含自包含 API CA 数据及可达、证书有效的服务器地址。工作站端点不适用时，用受支持 `--api-server-address` 覆盖为实际控制器可达 API 端点。

Link 有方向：在 West 生成并应用到 East，使 **East 能发现 West**。更新既有安装时，在期望 Helm 控制器列表保留所有现有对等体；用此单条目示例替换数组可能移除其他控制器。

### 可选反向连接

保存 `mc-west-links.yaml`：

```yaml
controllers:
- link:
    ref:
      name: east
```

```bash
set -euo pipefail
umask 077
linkerd --context east multicluster link-gen --cluster-name east > east-link.yaml
kubectl --context west apply -f east-link.yaml
helm --kube-context west upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster -f mc-base-values.yaml -f mc-west-links.yaml \
  --wait --timeout 10m
linkerd --context west multicluster check
```

每对等体使用不同远程访问 ServiceAccount，可更精细撤销。协调 RBAC 和凭证续订；这些是 Kubernetes API 凭证，独立于网格工作负载证书。

## 导出和使用服务

在两集群准备应用命名空间。Chart 默认不创建缺失镜像命名空间。

保存为 `mc-namespace.yaml`：

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mc-demo
  annotations:
    linkerd.io/inject: enabled
```

使用已测试网格 `web` 工作负载，监听 8080、带 `app:web` 标签，并准备现有网格 `client` 工作负载检查请求。本页不部署未指定的 `client:latest` 镜像，也不声称不完整 Deployment 有效。

将此 **West** Service 保存为 `west-web-service.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: mc-demo
  labels:
    mirror.linkerd.io/exported: 'true'
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
```

```bash
# Apply the Namespace manifest to both contexts before creating workloads/mirrors.
kubectl --context west apply -f mc-namespace.yaml
kubectl --context east apply -f mc-namespace.yaml
kubectl --context west apply -f west-web-service.yaml
# Alternative for an existing West Service:
kubectl --context west -n mc-demo label service/web mirror.linkerd.io/exported=true --overwrite
kubectl --context east -n mc-demo get service web-west
# Hierarchical mode: current service-mirror still manages legacy Endpoints.
kubectl --context east -n mc-demo get endpoints web-west -o yaml
kubectl --context east -n mc-demo get endpointslices.discovery.k8s.io \
  -l kubernetes.io/service-name=web-west -o yaml
# Existing meshed client with curl installed and the expected app endpoint.
kubectl --context east -n mc-demo exec deployment/client -c client -- \
  curl --fail --show-error --retry 0 --max-time 10 http://web-west.mc-demo.svc.cluster.local/
```

新建 Service 应在命名空间创建和工作负载准备后应用清单。标签命令是现有 Service 的替代方法。导出标签选择发现；不是访问控制边界，仅影响 Link 选择器/RBAC 匹配的对等体。

所选 service-mirror 实现仍为分层镜像维护旧 `Endpoints`。存在 EndpointSlice 时也检查，但不要假装更改诊断命令就迁移控制器。远程发现模式下，本地 Endpoints 可有意缺失：destination 组件改为查询远程端点。

## 显式本地/远程路由

对于 **East** 本地 web 工作负载，将入口/本地后端 Service 保存为 `east-web-services.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: mc-demo
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
---
apiVersion: v1
kind: Service
metadata:
  name: web-local
  namespace: mc-demo
spec:
  selector:
    app: web
  ports:
  - name: http
    port: 80
    targetPort: 8080
    appProtocol: http
```

保存 `east-web-route.yaml`，在本地后端和导入 Service 之间拆分合格网格客户端流量：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-cluster-route
  namespace: mc-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - backendRefs:
    - name: web-local
      port: 80
      weight: 80
    - name: web-west
      port: 80
      weight: 20
```

```bash
kubectl --context east apply -f east-web-services.yaml
kubectl --context east apply -f east-web-route.yaml
kubectl --context east -n mc-demo get httproute web-cluster-route -o yaml
linkerd --context east diagnostics policy -n mc-demo service/web 80 -o json
```

使用核心 Service 组 `""` 和 Service 端口 80。确认本地及远程路径就绪、路由接受和有效客户端策略。冲突 ServiceProfile 可覆盖当前出站策略；参阅[流量管理](03-traffic-management.md)。

### 手动转换与自动故障转移

100/0 配置不会自动将零权重后端变为活动备用。对于此手动管理路由，显式审核的仅远程状态如下：

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: web-cluster-route
  namespace: mc-demo
spec:
  parentRefs:
  - group: ''
    kind: Service
    name: web
    port: 80
  rules:
  - backendRefs:
    - name: web-local
      port: 80
      weight: 0
    - name: web-west
      port: 80
      weight: 100
```

有意应用选定状态，在视为恢复前验证应用结果、远程容量和数据一致性。现有请求和写入结果可能不确定；路由更改不复制数据库或撤销已提交操作。

旧 Flagger 回滚 webhook 引用未部署/验证的 `/failover` 服务，并修改另一名称的 TrafficSplit。它未建立可靠区域故障转移。Flagger 渐进交付在流量指南单独介绍。

SMI TrafficSplit 和 Linkerd Failover 扩展已弃用。官方迁移方向是在扁平网络可用时使用联邦服务；联邦不会自动替代每种分层网络或严格本地主节点要求。


## 扁平网络和联邦服务

对于独立的**仅扁平设置**，基础 values 省略网关。保存为 `flat-base-values.yaml`：

```yaml
gateway:
  enabled: false
```

East 的对等控制器 values `flat-east-links.yaml` 也省略网关探测：

```yaml
controllers:
- link:
    ref:
      name: west
  gateway:
    enabled: false
```

使用这些文件并在 Link 生成时加 `--gateway=false`，遵循相同基础安装 → Link/Secret → Helm 控制器顺序。先准备两集群 Pod 路由、命名空间和信任。迁移现有安装时，保留网关直到最后一个分层使用方迁移。

```bash
set -euo pipefail
umask 077
# Separate flat-network setup: both base installs omit the gateway.
# Use flat-base-values.yaml plus the corresponding flat controller values.
linkerd --context west multicluster link-gen --cluster-name west \
  --gateway=false > west-flat-link.yaml
kubectl --context east apply -f west-flat-link.yaml
helm --kube-context east upgrade linkerd-multicluster \
  linkerd-edge/linkerd-multicluster --version 2026.9.1 \
  -n linkerd-multicluster -f flat-base-values.yaml -f flat-east-links.yaml \
  --wait --timeout 10m
kubectl --context west -n mc-demo label service/web \
  mirror.linkerd.io/exported=remote-discovery --overwrite
linkerd --context east diagnostics endpoints web-west.mc-demo.svc.cluster.local:80
```

远程发现改变端点查找位置；不创建 Pod 路由、安全组规则或远程 API 访问。对应控制平面凭证也必须能从 destination 组件使用。

### 联邦服务成员关系

同名同命名空间 Service 可加入联邦 Service，本示例通常名为 `web-federated`：

```bash
# Flat connectivity, matching namespaces and the required directional Links first.
kubectl --context west -n mc-demo label service/web mirror.linkerd.io/federated=member --overwrite
kubectl --context east -n mc-demo label service/web mirror.linkerd.io/federated=member --overwrite
kubectl --context east -n mc-demo get service web-federated
kubectl --context east -n linkerd-multicluster get link west -o yaml
linkerd --context east diagnostics endpoints web-federated.mc-demo.svc.cluster.local:80
```

联邦 Service 存在于配置相关定向 Link/控制器的位置。网格客户端直接在发现的成员端点间均衡，不经过网关。这提供韧性基础，但不保证即时恢复、严格本地优先顺序或应用/数据可用性。

审核端点就绪、故障累积设置、网络分区、发现新鲜度和客户端重试语义。成员 Service 不同时，联邦元数据/端口选择也重要；不要假定所有冲突注解都按预期合并。

无头服务镜像是独立可选控制器能力（对应控制器设置中的 `enableHeadlessServices`）。要求合适命名主机，端点行为不同；无头 Service 不能加入联邦 Service。

## 跨集群授权

分层网关验证入站网格连接，并创建独立出站连接。最终服务器无法使用原始远程客户端身份区分经过网关的调用方。

对于**扁平/联邦流量**，West 中此策略允许保留的 `client.mc-demo.serviceaccount.identity.linkerd.cluster.local` 身份：

```yaml
apiVersion: policy.linkerd.io/v1beta3
kind: Server
metadata:
  name: web-http
  namespace: mc-demo
spec:
  podSelector:
    matchLabels:
      app: web
  port: 8080
  proxyProtocol: HTTP/1
  accessPolicy: deny
---
apiVersion: policy.linkerd.io/v1alpha1
kind: AuthorizationPolicy
metadata:
  name: web-from-client
  namespace: mc-demo
spec:
  targetRef:
    group: policy.linkerd.io
    kind: Server
    name: web-http
  requiredAuthenticationRefs:
  - kind: ServiceAccount
    name: client
    namespace: mc-demo
```

API 是 Linkerd AuthorizationPolicy 配 Server `v1beta3`，不是不存在的 ServerAuthorization `v1beta2`。标准 Kubernetes 身份为 DNS 形式，不是先前 Istio 式 SPIFFE URI。

相同 ServiceAccount/命名空间/信任域组合可在多个集群具有相同身份。独立签发者密钥不会引入隐式密码学集群 ID。此策略允许该工作负载身份；不证明“仅 East”。按需设计不同身份和信任边界，并评估各执行点实际可见身份。

网关模式部署应考虑最终服务器看到的网关身份及网关/网络边界控制。导出标签和内部负载均衡器不能替代授权。

## EKS 连接和所有权

上方基础 values 假定 **AWS Load Balancer Controller**、`service.k8s.aws/nlb`、IP 目标和内部 NLB。使用当前负载均衡器属性注解，不使用已弃用跨可用区注解。EKS Auto Mode 使用不同所有者/类 `eks.amazonaws.com/nlb`，支持的注解需单独检查。

保持 Linkerd TCP/mTLS 路径完整；ALB HTTP 路由或 TLS 终止不是可互换网关传输。分别考虑源到网关数据端口 4143、镜像控制器到网关探测端口 4191，以及源控制平面到目标 Kubernetes API 访问。根据实际路由/SNAT/安全组设计限制来源。

| 连接方式 | 提供的能力 |
|---|---|
| VPC 对等连接 / 适当 Transit Gateway 路由 | 配置路由、地址、DNS 和安全控制后提供私有网络连接 |
| AWS PrivateLink | 通过端点访问选定服务/资源；不是 VPC 对等连接或自动任意 Pod 间路由 |
| EKS 私有 Kubernetes API 端点 | 从集群 VPC/适当连接网络访问其 Kubernetes API |
| EKS 接口 VPC 端点 | 私有访问 AWS EKS 管理 API；不是 Kubernetes API 端点 |

扁平模式应确保 Pod 地址无冲突且直接可达；仅网关连接不够。分层模式即使无法任意路由远程 Pod，也需设计网关和远程 API 可达性。

通过审核过的基础设施流程预置集群和网络连接，选择目标 AWS 账户/profile 和兼容版本。给两条 `eksctl create cluster` 命令不同名称，不会使其位于不同账户。本审计未执行集群创建、网关预置或真实跨区域流量。

管理 AWS 资源的操作员/控制器需要 AWS IAM 权限。Linkerd 生成的镜像凭证用 Kubernetes ServiceAccount 令牌和 RBAC 认证；并非每个运行时 Link 都需要宽泛跨账户 IAM 角色。将这些信任关系分开。

## 可观测性和联邦

`multicluster gateways` 报告目标网关探测，不报告每个导出应用的端到端健康。探测指标属于源镜像控制器，如 `gateway_alive` 和 `gateway_probe_latency_ms`，带 `target_cluster_name` 标签。不是本地网关代理的普通指标。

对集中 Prometheus，以下是**针对已部署私有 HTTPS 端点、使用 Basic 身份验证的客户端配置示例**。提供实际 DNS、CA/密码文件、服务器端身份验证、可达性和抓取授权。默认 Viz 不自动暴露这些端点。

```yaml
scrape_configs:
- job_name: federate-west
  scheme: https
  honor_labels: true
  metrics_path: /federate
  params:
    match[]:
    - '{job=~"linkerd-proxy|linkerd-controller"}'
  static_configs:
  - targets:
    - prometheus-west.internal.example.com:443
  tls_config:
    ca_file: /etc/prometheus/federation/ca.crt
  basic_auth:
    username: federation-reader
    password_file: /etc/prometheus/federation/west/password
  metric_relabel_configs:
  - target_label: origin_cluster
    replacement: west
- job_name: federate-east
  scheme: https
  honor_labels: true
  metrics_path: /federate
  params:
    match[]:
    - '{job=~"linkerd-proxy|linkerd-controller"}'
  static_configs:
  - targets:
    - prometheus-east.internal.example.com:443
  tls_config:
    ca_file: /etc/prometheus/federation/ca.crt
  basic_auth:
    username: federation-reader
    password_file: /etc/prometheus/federation/east/password
  metric_relabel_configs:
  - target_label: origin_cluster
    replacement: east
```

`honor_labels:true` 保留源指标标签；仅目标重标记不能可靠覆盖冲突导出标签。此处指标重标记在抓取后分配 Collector 控制的 `origin_cluster`。聚合时保留来源标签，避免重复采集路径。

按指标来源的后端成功比例：

```promql
(sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound",classification="success"}[5m]))
 or on(origin_cluster) (0 * sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound"}[5m])))) / sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound"}[5m]))
and on(origin_cluster) (sum by (origin_cluster) (rate(response_total{namespace="mc-demo",deployment="web",direction="inbound"}[5m])) > 0)
```

按指标来源的客户端观测 TTFB：

```promql
histogram_quantile(0.99,
  sum by (le, origin_cluster) (rate(response_latency_ms_bucket{namespace="mc-demo",deployment="client",direction="outbound"}[5m]))
)
```

演示客户端必须发送预期远程流量，第二个查询才代表该路径。它包括应用/代理/网络时间，不是纯跨区域 RTT。此设置不保证添加 `src_cluster` 和 `dst_cluster` 标签。构建更具体跨集群维度前检查实际序列。

缺失成功序列与每集群总量对齐；空闲/缺失总量不会报告为 100% 成功。分类、单位、抓取健康和仪表板前提参阅[可观测性指南](05-observability.md)。

## 故障排除

```bash
linkerd --context east multicluster check
linkerd --context east multicluster gateways
kubectl --context east -n linkerd-multicluster get link west -o yaml
kubectl --context east -n linkerd-multicluster logs deployment/controller-west -c controller --tail=100
kubectl --context west -n linkerd-multicluster logs deployment/linkerd-gateway -c linkerd-proxy --tail=100
linkerd --context east viz stat deployment/client -n mc-demo --to service/web-west
linkerd --context west check --proxy
linkerd --context east check --proxy
```

针对远程 API/RBAC/命名空间问题，检查 Link 状态和控制器日志。网关问题检查**目标** Service 入口地址、探测路径/端口和网络路径。健康探测不验证数据端口或业务逻辑。扁平模式使用 destination 端点诊断和直接 Pod 连接，不应期待网关统计。

读取实际公有信任包：

```bash
set -euo pipefail
# Public bundle data, not private keys or the generated Link kubeconfig.
kubectl --context west -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > west-trust.pem
kubectl --context east -n linkerd get configmap linkerd-identity-trust-roots -o json \
  | jq -er '.data["ca-bundle.crt"] | select(length > 0)' > east-trust.pem
openssl crl2pkcs7 -nocrl -certfile west-trust.pem | openssl pkcs7 -print_certs -text -noout
openssl crl2pkcs7 -nocrl -certfile east-trust.pem | openssl pkcs7 -print_certs -text -noout
```

检查每张证书的有效期/签发者链。仅 PEM 顺序/格式不是信任等价测试，简短 grep 旧配置字段也不是完整验证。更改使用安全指南的分阶段轮换流程。

## 参考资料和后续步骤

- [最佳实践](07-best-practices.md)、[多集群测验](../../quizzes/service-mesh/linkerd/multi-cluster.md)
- [多集群参考](https://linkerd.io/docs/reference/multicluster/)和[安装](https://linkerd.io/docs/tasks/installing-multicluster/)
- [Pod 间模式](https://linkerd.io/docs/tasks/pod-to-pod-multicluster/)和[联邦服务](https://linkerd.io/docs/tasks/federated-services/)
- [已弃用故障转移扩展](https://linkerd.io/docs/tasks/automatic-failover/)
- [发布的 link-gen 实现](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/multicluster/cmd/link-gen.go)
- [发布的 service-mirror 端点处理](https://github.com/linkerd/linkerd2/blob/edge-26.9.1/multicluster/service-mirror/cluster_watcher.go)
- [AWS Load Balancer Controller 注解](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/)
- [EKS Auto Mode NLB](https://docs.aws.amazon.com/eks/latest/userguide/auto-configure-nlb.html)
- [VPC 对等连接](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html)和 [AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html)
- [EKS Kubernetes API 端点](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)和 [EKS 接口端点](https://docs.aws.amazon.com/eks/latest/userguide/vpc-interface-endpoints.html)
