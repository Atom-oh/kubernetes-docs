# Linkerd 安装测验

本测验用于检验你对 Linkerd 安装和设置的理解。

## 测验题目

### 1. 安装 Linkerd CLI 的正确命令是什么？

A. `apt-get install linkerd`
B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`
C. `kubectl install linkerd`
D. `helm install linkerd`

<details>
<summary>显示答案</summary>

**答案：B. `curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh`**

**说明：**
Linkerd CLI 通过官方安装脚本安装。该脚本会检测操作系统并下载相应的二进制文件。也可以使用 Homebrew（`brew install linkerd`）或 Chocolatey（`choco install linkerd2`），但官方脚本是最常用的方法。

</details>

### 2. 哪个命令可在安装 Linkerd 前验证 Cluster 要求？

A. `linkerd check`
B. `linkerd check --pre`
C. `linkerd verify`
D. `linkerd install --dry-run`

<details>
<summary>显示答案</summary>

**答案：B. `linkerd check --pre`**

**说明：**
`linkerd check --pre` 命令会验证 Cluster 是否满足安装 Linkerd 前的要求。它会验证 Kubernetes API 的可访问性、版本兼容性以及必要的权限。安装后，使用 `linkerd check` 验证完整状态。

</details>

### 3. 使用 Helm 安装 Linkerd 时必须提供什么？

A. Envoy proxy 镜像
B. Trust Anchor 和 Identity Issuer 证书
C. Prometheus 配置文件
D. Kubernetes 版本信息

<details>
<summary>显示答案</summary>

**答案：B. Trust Anchor 和 Identity Issuer 证书**

**说明：**
与 CLI 安装不同，Helm 安装不会自动生成证书。用户必须自行创建并提供 Trust Anchor（Root CA）和 Identity Issuer（Intermediate CA）证书。这样可以在生产环境中更好地控制证书管理。

</details>

### 4. Linkerd HA 安装建议使用多少个 Control plane 副本？

A. 1
B. 2
C. 3
D. 5

<details>
<summary>显示答案</summary>

**答案：C. 3**

**说明：**
HA 配置建议 Destination、Identity 和 Proxy Injector 各使用 3 个副本。即使其中一个失败，三个副本仍可维持法定人数，并确保滚动更新期间的可用性。

</details>

### 5. 以下哪项不是 Viz 扩展的主要功能？

A. Web dashboard
B. Prometheus 指标收集
C. 自动 Canary 部署
D. 实时流量 tap

<details>
<summary>显示答案</summary>

**答案：C. 自动 Canary 部署**

**说明：**
Viz 扩展提供 Web dashboard、基于 Prometheus 的指标收集、Grafana dashboard 和实时流量 tap 功能。自动 Canary 部署通过 Flagger 等独立工具实现。

</details>

### 6. 在 EKS 上，Multicluster gateway 推荐使用哪种 Load Balancer 类型？

A. Classic Load Balancer
B. Application Load Balancer (ALB)
C. Network Load Balancer (NLB)
D. Internal Load Balancer

<details>
<summary>显示答案</summary>

**答案：C. Network Load Balancer (NLB)**

**说明：**
NLB 针对 TCP/TLS 流量进行了优化，因此适合 Linkerd 的 mTLS gateway 流量。ALB 针对 HTTP/HTTPS 进行了优化，而 Linkerd gateway 在 TCP 层运行，因此推荐使用 NLB。

</details>

### 7. Linkerd 升级的正确顺序是什么？

A. Data plane → CRD → Control plane
B. CRD → Control plane → Data plane
C. Control plane → CRD → Data plane
D. CRD → Data plane → Control plane

<details>
<summary>显示答案</summary>

**答案：B. CRD → Control plane → Data plane**

**说明：**
正确的升级顺序为：1) CLI 升级，2) CRD 升级，3) Control plane 升级，4) Data plane（proxy）升级。必须先升级 CRD，才能使用新的 API 版本。

</details>

### 8. `linkerd install --crds` 命令的用途是什么？

A. 安装 Linkerd CLI
B. 安装 Custom Resource Definitions
C. 生成证书
D. 注入 proxy

<details>
<summary>显示答案</summary>

**答案：B. 安装 Custom Resource Definitions**

**说明：**
`linkerd install --crds` 仅安装 Linkerd 使用的 CRD（Custom Resource Definitions）。其中包括 ServiceProfile、Server、ServerAuthorization 等的 CRD。Control plane 使用 `linkerd install` 单独安装。

</details>

### 9. 安装 Jaeger 扩展的命令是什么？

A. `linkerd install jaeger`
B. `linkerd jaeger install | kubectl apply -f -`
C. `kubectl apply -f jaeger.yaml`
D. `helm install jaeger linkerd/jaeger`

<details>
<summary>显示答案</summary>

**答案：B. `linkerd jaeger install | kubectl apply -f -`**

**说明：**
Linkerd 扩展会以 `linkerd <extension> install` 格式生成 manifest，并使用 kubectl 应用它们。Jaeger 扩展提供分布式追踪功能。

</details>

### 10. 完全移除 Linkerd 的正确顺序是什么？

A. Control plane → Extensions → CRD
B. Extensions → Control plane → CRD
C. CRD → Control plane → Extensions
D. 所有内容都可以同时移除

<details>
<summary>显示答案</summary>

**答案：B. Extensions → Control plane → CRD**

**说明：**
移除顺序与安装顺序相反：1) 移除 Viz、Jaeger、Multicluster 等 Extensions，2) 移除 Control plane，3) 移除 CRD。这是因为 Extensions 依赖于 Control plane，而 Control plane 依赖于 CRD。

</details>

### 11. `linkerd check` 命令不会验证什么？

A. Kubernetes API 连接
B. 证书有效性
C. 应用程序业务逻辑
D. Control plane Pod 状态

<details>
<summary>显示答案</summary>

**答案：C. 应用程序业务逻辑**

**说明：**
`linkerd check` 仅验证 Linkerd 基础设施状态：Kubernetes API 连接、证书有效性、Control plane Pod 状态、proxy 状态等。它不会验证应用程序业务逻辑或功能。

</details>

### 12. 要启用自动 proxy 注入，必须向 Namespace 添加什么 annotation？

A. `linkerd.io/inject: enabled`
B. `linkerd.io/proxy: true`
C. `sidecar.linkerd.io/inject: true`
D. `linkerd/auto-inject: yes`

<details>
<summary>显示答案</summary>

**答案：A. `linkerd.io/inject: enabled`**

**说明：**
向 Namespace 添加 `linkerd.io/inject: enabled` annotation 会自动将 linkerd-proxy 注入该 Namespace 中所有新建的 Pod。相同的 annotation 也可以用于单个 Pod。

</details>
