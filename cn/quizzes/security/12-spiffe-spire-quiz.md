# SPIFFE/SPIRE 测验

> **最后更新**: September 13, 2026

## 问题

<span id="_1-what-is-the-correct-format-for-a-spiffe-id"></span>

### 1. 以下哪个是有效的 SPIFFE ID？

- A) `https://example.org/app`
- B) `spiffe://example.org/app`
- C) `spiffe://example.org:8443/app`
- D) `spiffe://example.org/app?role=admin`

<details>
<summary>显示答案</summary>

**答案：B) spiffe://example.org/app**

使用 spiffe scheme、trust domain 和可选路径。不允许端口、查询和片段。路径结构由站点定义，不限于 /ns/.../sa/...。

</details>

<span id="_2-what-is-the-key-difference-between-x-509-svid-and-jwt-svid"></span>

### 2. 以下哪项正确描述了 X.509/JWT-SVID 验证？

- A) 只检查 X.509 CN
- B) 有效的 JWT signature 使 audience 无需验证
- C) 验证 X.509 URI SAN/chain 以及 JWT signature/sub/audience/expiry
- D) JWT audience 检查可防止所有重放攻击

<details>
<summary>显示答案</summary>

**答案：C) 验证 X.509 URI SAN/chain 以及 JWT signature/sub/audience/expiry**

证书 CN 不是 SPIFFE identity。即使 audience 匹配，JWT bearer token 仍可能被重放。生命周期取决于 policy；本章的 X.509/JWT 范围与处于 Incubating 阶段的 WIT-SVID specification 分开。

</details>

<span id="_3-what-is-the-primary-role-of-the-spire-server"></span>

### 3. SPIRE Server 的作用是什么？

- A) 自动加密每个应用连接
- B) 管理 agent attestation、registration 和 SVID signing
- C) 自动授权每个 Service 请求
- D) 通过 CSI 向所有 Pod 分发 private-key 文件

<details>
<summary>显示答案</summary>

**答案：B) 管理 agent attestation、registration 和 SVID signing**

区分 CA/JWT signing、DataStore 和 KeyManager 的职责。AWS PCA upstream 对 SPIRE intermediate CA 进行签名；它不会免除本地 leaf signing 或 key management。

</details>

<span id="_4-what-is-the-primary-role-of-the-spire-agent"></span>

### 4. 谁识别调用 Workload API 的应用？

- A) 本地 SPIRE agent 的 workload attestor
- B) DNS resolver
- C) 检查文件名的 CSI
- D) 仅由应用自行声明的 SPIFFE ID

<details>
<summary>显示答案</summary>

**答案：A) 本地 SPIRE agent 的 workload attestor**

agent 检查调用方的 PID/cgroups/Pod metadata，并匹配已授权的 entries/cache。在 agent Pod 内获取会 attestation 该调用方，而非实际应用上下文。

</details>

<span id="_5-which-node-attestation-method-is-recommended-for-amazon-eks"></span>

### 5. Server 如何验证 k8s_psat token？

- A) 检查 IRSA role 的 S3 permissions
- B) Kubernetes TokenReview 加上已配置的 audience/SA allowlist
- C) 仅对 token 进行 base64 解码
- D) 将其转换为永不过期的 join token

<details>
<summary>显示答案</summary>

**答案：B) Kubernetes TokenReview 加上已配置的 audience/SA allowlist**

匹配 server/agent logical cluster names、token audience、SA allowlist 和 TokenReview permissions。aws_iid 是具有不同 trust assumptions 的替代方案，并非在 EKS 上普遍更强或被禁止。

</details>

<span id="_6-what-selector-types-does-k8s-workload-attestation-support"></span>

### 6. 应如何解读 k8s:container-image:nginx:*？

- A) 自动对每个 nginx tag 执行 glob matching
- B) 一个 selector value；不要假定支持 wildcard matching
- C) 证明 image signature 已通过验证
- D) 自动强制执行 namespace RBAC

<details>
<summary>显示答案</summary>

**答案：B) 一个 selector value；不要假定支持 wildcard matching**

匹配 Kubernetes 实际报告的 image/ImageID values。仅凭 tag 无法建立 supply-chain trust。创建和修改 Pod/SA/label 的 permissions 也会影响 identity eligibility。

</details>

<span id="_7-what-is-the-purpose-of-the-spiffe-csi-driver"></span>

### 7. SPIFFE CSI 0.2.13 会向 Pod 挂载什么？

- A) 自动生成的 svid.pem/svid.key 文件
- B) 包含 Workload API Unix socket 的目录
- C) SPIRE CA private key
- D) 共享的 PostgreSQL 数据

<details>
<summary>显示答案</summary>

**答案：B) 包含 Workload API Unix socket 的目录**

CSI 提供对 API socket 的访问。基于文件的应用需要单独的 adapter 和 reload handling。应用或 proxy 仍然要使用 API；集成并非普遍自动完成。

</details>

<span id="_8-what-does-spiffe-federation-enable"></span>

### 8. 引导 https_spiffe federation 需要什么？

- A) 仅需一个 endpoint URL
- B) 初始 trusted bundle 和正确的 endpoint SPIFFE ID
- C) 交换两个 CA private key
- D) 自动授权每个远程 workload

<details>
<summary>显示答案</summary>

**答案：B) 初始 trusted bundle 和正确的 endpoint SPIFFE ID**

配置每个 trust direction。bundle refresh、connectivity、TLS verification 和 workload authorization 是不同的职责。https_web 使用 endpoint 的 Web PKI validation path。

</details>

<span id="_9-how-does-spiffe-spire-compare-to-iam-roles-for-service-accounts-irsa"></span>

### 9. 以下哪项正确比较了 IRSA 与 SPIFFE/SPIRE？

- A) IRSA 刷新始终需要重启 Pod
- B) SPIFFE 消除了对 AWS IAM policy 的需求
- C) IRSA 是 AWS credential path；SPIFFE 是 workload identity，两者均需验证
- D) 一个 Pod annotation 即可完成 IRSA 和 CSI certificate-file delivery

<details>
<summary>显示答案</summary>

**答案：C) IRSA 是 AWS credential path；SPIFFE 是 workload identity，两者均需验证**

IRSA 通过受支持的 SDK/projected-token behavior 刷新，并支持 cross-account designs。验证 ServiceAccount annotations、aud/sub trust 和 AWS permissions。SPIFFE mTLS 还需要 credential consumption 和 peer authorization。

</details>

<span id="_10-what-are-best-practices-for-naming-trust-domains-in-spiffe"></span>

### 10. 关于 trust domains 和 CA rotation，以下哪项正确？

- A) trust domain 必须是可解析的 DNS name
- B) bundle set 会自动轮换 CA private key
- C) 选择稳定的名称，并区分 bundle changes 与 CA-key rotation
- D) numeric 或 IPv4-shaped domains 始终会被 parser 拒绝

<details>
<summary>显示答案</summary>

**答案：C) 选择稳定的名称，并区分 bundle changes 与 CA-key rotation**

DNS-like naming 是指导原则，而非完整的 syntax rule。bundles 是公开的 trust material；key rotation 是独立的生命周期。验证 authority overlap 和 consumer updates。

</details>

## 分数计算

- 9–10：理解深入
- 7–8：重新学习 trust、authorization 和 delivery paths
- 6 或更少：复习指南和已验证的示例

## 相关文档

- [SPIFFE/SPIRE](../../security/12-spiffe-spire.md)
