# Linkerd 架构测验

本测验用于测试你对 Linkerd 架构的理解。

## 测验题目

### 1. 以下哪项不是 Linkerd control plane 的核心组件？

A. Destination Controller
B. Identity Controller
C. Proxy Injector
D. Envoy Proxy

<details>
<summary>显示答案</summary>

**答案：D. Envoy Proxy**

**说明：**
Linkerd control plane 由 Destination、Identity 和 Proxy Injector 组成。Envoy 是 Istio 的 data plane proxy；Linkerd 使用其自有的、用 Rust 编写的 linkerd2-proxy。

</details>

### 2. linkerd2-proxy 使用什么编程语言编写？

A. Go
B. C++
C. Rust
D. Java

<details>
<summary>显示答案</summary>

**答案：C. Rust**

**说明：**
linkerd2-proxy 使用 Rust 编写，提供内存安全性和高性能。它仅使用约 10MB 内存，并增加不到 1ms 的 p99 延迟。

</details>

### 3. 以下哪项不是 Destination Controller 的主要职责？

A. 服务发现
B. 证书签发
C. ServiceProfile 信息传递
D. Endpoint 更新

<details>
<summary>显示答案</summary>

**答案：B. 证书签发**

**说明：**
Certificate issuance 是 Identity Controller 的职责。Destination Controller 负责 Service discovery、Endpoint updates，以及分发 ServiceProfile 和 TrafficSplit 策略。

</details>

### 4. Linkerd certificate hierarchy 的顶层是什么？

A. Workload Certificate
B. Identity Issuer
C. Trust Anchor
D. Proxy Certificate

<details>
<summary>显示答案</summary>

**答案：C. Trust Anchor**

**说明：**
Certificate hierarchy 为 Trust Anchor (Root CA) → Identity Issuer (Intermediate CA) → Workload Certificate。Trust Anchor 是 PKI 的根，也是所有 certificate chain 的信任基础。

</details>

### 5. workload certificate 的默认有效期是多长？

A. 1 小时
B. 24 小时
C. 7 天
D. 30 天

<details>
<summary>显示答案</summary>

**答案：B. 24 小时**

**说明：**
Linkerd workload certificate 的默认有效期为 24 hours。Proxy 会在 certificate 过期前自动续期。较短的有效期可在 certificate 泄露时将风险降至最低。

</details>

### 6. Proxy Injector 使用哪种 Kubernetes 机制？

A. DaemonSet
B. CronJob
C. Admission Webhook
D. Custom Controller

<details>
<summary>显示答案</summary>

**答案：C. Admission Webhook**

**说明：**
Proxy Injector 作为 Mutating Admission Webhook 运行。它会拦截 Pod 创建请求，并自动注入 linkerd-proxy sidecar 和 linkerd-init init container。

</details>

### 7. linkerd-init container 的作用是什么？

A. 下载 Proxy 配置
B. 设置 iptables 规则
C. 生成证书
D. 收集指标

<details>
<summary>显示答案</summary>

**答案：B. 设置 iptables 规则**

**说明：**
linkerd-init 作为 Init container 运行，以设置 iptables rules。这些规则会将所有入站/出站流量重定向到 linkerd-proxy。

</details>

### 8. Linkerd proxy 的入站端口是什么？

A. 4140
B. 4143
C. 4191
D. 8080

<details>
<summary>显示答案</summary>

**答案：B. 4143**

**说明：**
Linkerd proxy 端口：4143（入站）、4140（出站）、4191（admin/metrics）。入站端口接收来自其他 Service 的流量。

</details>

### 9. 正确的 SPIFFE ID 格式是什么？

A. `spiffe://cluster/namespace/service`
B. `spiffe://trust-domain/ns/namespace/sa/service-account`
C. `https://linkerd.io/identity/namespace/pod`
D. `urn:linkerd:identity:namespace:pod`

<details>
<summary>显示答案</summary>

**答案：B. `spiffe://trust-domain/ns/namespace/sa/service-account`**

**说明：**
Linkerd 的 SPIFFE ID 遵循格式 `spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>`。示例：`spiffe://root.linkerd.cluster.local/ns/production/sa/web-server`

</details>

### 10. 与 Istio 的 Envoy 相比，以下哪项不是 linkerd2-proxy 的特性？

A. 更低的内存使用量
B. Wasm 扩展支持
C. 更低的延迟
D. 更小的二进制文件大小

<details>
<summary>显示答案</summary>

**答案：B. Wasm 扩展支持**

**说明：**
linkerd2-proxy 不支持 Wasm extensions（可扩展性有限）。相较之下，它更加轻量：约 10MB 内存（Envoy 约 50-100MB）、<1ms p99 延迟（Envoy 2-5ms），以及约 10MB 二进制文件（Envoy 约 60MB）。

</details>

### 11. Identity Controller 在签发 certificate 前会验证什么？

A. Pod 的 IP 地址
B. ServiceAccount 令牌
C. Namespace 标签
D. ConfigMap 设置

<details>
<summary>显示答案</summary>

**答案：B. ServiceAccount 令牌**

**说明：**
Identity Controller 会验证 Proxy 提交的 CSR 随附的 ServiceAccount token。这可确认 Proxy 的身份（SPIFFE ID）与实际 workload 相匹配。

</details>

### 12. 以下哪项不由 Linkerd proxy admin port (4191) 提供？

A. Prometheus 指标
B. Health check 端点
C. 流量路由配置
D. Proxy 版本信息

<details>
<summary>显示答案</summary>

**答案：C. 流量路由配置**

**说明：**
admin port (4191) 提供 Prometheus metrics (/metrics)、health checks (/ready, /live) 和 Proxy 信息。Traffic routing configuration 通过 Destination Controller 的 gRPC 传递给 Proxy。

</details>
