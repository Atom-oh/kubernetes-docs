# Linkerd 架构测验

已于 2026 年 10 月 16 日针对 edge-26.10.1 审核。请阅读[架构指南](../../../service-mesh/linkerd/02-architecture.md)，了解有来源支持的模型及其限制。

### 1. 以下哪项不是 Linkerd 控制平面组件？

A. Destination 控制器

B. Identity 控制器

C. Proxy Injector

D. Envoy 代理

<details>
<summary>答案与解释</summary>

**答案：D**

Linkerd 使用 Rust 数据平面代理。固定版本的控制平面包含三个核心 Deployment，此外还有策略等在其中运行的逻辑控制器。Envoy 用于 Istio sidecar/waypoint，而不是 Linkerd 控制器。

</details>

### 2. linkerd2-proxy 是用哪种语言编写的？

A. Go

B. C++

C. Rust

D. Java

<details>
<summary>答案与解释</summary>

**答案：C**

它是用 Rust 编写的。语言选择并不能证明其占用空间始终为 10MB、p99 始终低于一毫秒，或始终优于其他代理。应比较实际构建版本、工作负载和配置。

</details>

### 3. 以下哪项不是 Destination 的主要职责？

A. 服务发现

B. 工作负载证书签发

C. 支持的 ServiceProfile 信息

D. 端点更新

<details>
<summary>答案与解释</summary>

**答案：B**

Identity 使用其配置的签发者凭据签发工作负载证书。Destination 提供服务发现和 ServiceProfile 相关信息；当前的 Gateway API 路由和授权也涉及策略（policy）控制器。旧版 TrafficSplit 扩展并不构成当前完整的策略模型。

</details>

### 4. 默认证书层级顶端的信任依据是什么？

A. 工作负载证书

B. Identity 签发者

C. 信任锚

D. 唯一的 Pod 名称

<details>
<summary>答案与解释</summary>

**答案：C**

公开的信任锚构成证书链验证的信任依据。通常，它用于签署中间签发者的证书，再由中间签发者的密钥签署工作负载证书。Linkerd 不要求根私钥处理每一个工作负载 CSR。

</details>

### 5. 工作负载证书默认设定的有效期是多久？

A. 1 小时

B. 24 小时

C. 7 天

D. 30 天

<details>
<summary>答案与解释</summary>

**答案：B**

默认配置的签发有效期为 24 小时，并会在到期前续期。实际有效期和刷新时间取决于配置和证书状态。证书续期并不意味着一定会生成新的私钥、轮换签发者或轮换根证书。

</details>

### 6. 哪种 Kubernetes 机制负责自动注入代理？

A. DaemonSet

B. CronJob

C. 可变更准入 Webhook

D. 应用负载均衡器

<details>
<summary>答案与解释</summary>

**答案：C**

Webhook 会修改符合条件的新建 Pod。在所选版本中，代理通常会成为原生 sidecar；配置 Linkerd CNI 时会省略 linkerd-init。现有 Pod、被排除在注入范围之外的 Pod，以及通过显式配置覆盖注入设置的 Pod，需要另行考虑。

</details>

### 7. 不使用 Linkerd CNI 时，linkerd-init 会执行什么操作？

A. 下载所有路由策略

B. 配置 Pod 网络流量捕获

C. 充当根 CA

D. 存储 Prometheus 时间序列数据

<details>
<summary>答案与解释</summary>

**答案：B**

它会在 Pod 网络命名空间内配置流量捕获规则。在重定向被拦截的 TCP 流量前，必须考虑代理 UID 和已配置的绕过规则。这并不意味着代理会处理所有协议和所有绕过的端口。

</details>

### 8. 默认的入站代理端口是什么？

A. 4140

B. 4143

C. 4191

D. 8080

<details>
<summary>答案与解释</summary>

**答案：B**

默认端口为：入站 4143、出站 4140、管理/指标 4191。入站/出站端口处理被拦截的 TCP 流量，其中可能承载 HTTP/gRPC 或不透明负载。端口可以配置。

</details>

### 9. 对于 my-app 中名为 web-service 的 ServiceAccount，当控制平面命名空间为 linkerd 且信任域为 cluster.local 时，默认 Kubernetes 身份是什么？

A. spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service

B. web-service.my-app.serviceaccount.identity.linkerd.cluster.local

C. `https://linkerd.io/identity/my-pod`

D. urn:linkerd:my-pod

<details>
<summary>答案与解释</summary>

**答案：B**

Kubernetes TokenReview 返回 ServiceAccount 身份，其格式为 DNS 名称。使用该 ServiceAccount 的多个 Pod 共享此身份。SPIFFE/SPIRE 外部工作负载身份使用不同的引导路径，并非这种默认的 Kubernetes URI 格式。

</details>

### 10. 在没有匹配的基准测试时，以下哪种比较是合理的？

A. Linkerd 始终恰好占用 10MB

B. 比较架构和支持的 API；针对实际工作负载测量资源/延迟差异

C. Istio 的 p99 始终增加 2–5ms

D. 配置的内存请求值较小，就能证明运行时消耗更低

<details>
<summary>答案与解释</summary>

**答案：B**

配置的预留资源、二进制文件大小、实际内存用量和延迟是不同的属性。应使用匹配的版本/构建、架构、流量模式和策略集进行比较。还应针对所选模式/API 检查可扩展性，而不能根据笼统的产品排名推断。

</details>

### 11. 默认的 Kubernetes 身份验证器会检查什么？

A. 仅 Pod IP

B. 通过 Kubernetes TokenReview 检查提交的 ServiceAccount 令牌

C. 仅命名空间标签

D. 仅 ConfigMap 名称

<details>
<summary>答案与解释</summary>

**答案：B**

已发布的验证器会验证令牌，并根据 Kubernetes 用户信息推导出 DNS 格式的身份。证书请求还包含身份和 CSR 数据。这并不意味着只要调用方提供的 SPIFFE URI 看起来合理，就会被接受。

</details>

### 12. 动态更新的路由/策略设置通常如何传递给代理？

A. 写入其 Prometheus 指标端点

B. 更改根证书的主体（Subject）

C. 通过控制平面 API，包括流式 gRPC

D. 在节点命名空间中应用任意 REDIRECT 规则

<details>
<summary>答案与解释</summary>

**答案：C**

管理端口提供健康状态和指标接口，不能替代控制平面策略 API。启动环境变量/注入配置与动态传递的策略是不同的输入；诊断行为时应同时检查二者。

</details>
