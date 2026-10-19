# cert-manager 测验

> **最后更新**：2026 年 9 月 13 日

本测验共十题，涵盖证书签发、续期、信任分发以及与 AWS 集成的边界。

## 问题

### 1. cert-manager 在 CNCF 中处于什么项目状态？

- A) Sandbox（沙箱）
- B) Incubating（孵化）
- C) Graduated（毕业）
- D) Archived（归档）

<details>
<summary>显示答案</summary>

**答案：C) Graduated（毕业）**

cert-manager 于 2024 年 9 月 29 日毕业。它于 2022 年 9 月 19 日进入 Incubating 阶段。项目成熟度并不能证明某个具体安装具有安全性或高可用性。

</details>

<span id="_2-which-component-in-cert-manager-watches-certificate-resources-and-triggers-certificate-issuance"></span>

### 2. 哪个组件负责监视 Certificate 并协调签发和续期？

- A) cainjector
- B) webhook
- C) controller
- D) scheduler

<details>
<summary>显示答案</summary>

**答案：C) controller**

controller 协调证书生命周期。webhook 负责验证、设置默认值并转换自定义资源；cainjector 则将 CA bundle 注入受支持的 API 和 webhook 配置中。

</details>

<span id="_3-what-is-the-key-difference-between-issuer-and-clusterissuer-resources"></span>

### 3. Issuer 与 ClusterIssuer 有什么主要区别？

- A) 只有 Issuer 支持 ACME
- B) Issuer 的作用域是命名空间；ClusterIssuer 的作用域是集群
- C) 只有 ClusterIssuer 会自动续期
- D) 创建 ClusterIssuer 会自动强制执行 SAN 策略

<details>
<summary>显示答案</summary>

**答案：B) Issuer 的作用域是命名空间；ClusterIssuer 的作用域是集群**

Issuer 必须在其命名空间内引用。ClusterIssuer 使用的凭证或 CA Secret 位于控制器的集群资源命名空间，通常是 `cert-manager`。资源作用域本身不会授权 SAN 或 `issuerRef`；仍需单独配置审批或准入策略。

</details>

<span id="_4-which-acme-challenge-type-supports-wildcard-certificate-issuance"></span>

### 4. 哪种验证方式支持 Let’s Encrypt ACME 签发普通通配符证书？

- A) HTTP-01
- B) DNS-01
- C) TLS-ALPN-01
- D) 只检查 443 端口是否可连接

<details>
<summary>显示答案</summary>

**答案：B) DNS-01**

DNS-01 通过 TXT 记录证明域名控制权。HTTP-01 要求开放 80 端口，但不支持通配符证书。应将 DNS API 权限限制到预期的区域和 TXT 名称。复用已有授权或使用 ACM 预验证，可以避免每次请求都创建新的 Challenge。

</details>

<span id="_5-in-a-certificate-resource-what-does-the-secretname-field-specify"></span>

### 5. Certificate.spec.secretName 指定什么？

- A) ACME 账户密钥 Secret
- B) 在同一命名空间中保存签发证书和私钥的 Secret
- C) 始终用于分发根 CA 的 ConfigMap
- D) Issuer 身份验证所用的 Secret

<details>
<summary>显示答案</summary>

**答案：B) 在同一命名空间中保存签发证书和私钥的 Secret**

输出 Secret 包含 `tls.crt` 和 `tls.key`。`ca.crt` 可能不存在，也不能替代客户端信任配置。默认的 `privateKey.rotationPolicy` 自 1.18 起为 `Always`。Secret 更新后，应用是否重新加载必须另行验证。

</details>

<span id="_6-what-is-the-primary-use-case-for-the-aws-private-ca-issuer"></span>

### 6. 哪个扩展可将 AWS Private CA 接入 cert-manager，作为外部签发者？

- A) aws-pca-controller
- B) aws-privateca-issuer
- C) acmesolver
- D) trust-manager

<details>
<summary>显示答案</summary>

**答案：B) aws-privateca-issuer**

`aws-privateca-issuer` 负责处理 AWSPCAIssuer 和 AWSPCAClusterIssuer。它需要限定到 CA 的 IAM 权限、工作负载身份、请求审批，以及兼容的 CA 模式、模板和有效期。使用私有 CA 并不意味着证书受公共浏览器信任或无需付费。

</details>

<span id="_7-what-does-trust-manager-do-in-the-cert-manager-ecosystem"></span>

### 7. trust-manager 的主要职责是什么？

- A) 签发证书和私钥
- B) 向选定的命名空间分发 CA bundle
- C) 将 CA 私钥复制到每个 Pod
- D) 自动吊销证书

<details>
<summary>显示答案</summary>

**答案：B) 向选定的命名空间分发 CA bundle**

默认的 0.25.0 chart 使用 Bundle v1alpha1。它从配置的 trust namespace 读取来源，并由 `namespaceSelector` 限定目标命名空间。支持将目标设为 ConfigMap；若要使用 Secret 目标，则需单独启用并配置 RBAC。通过 `subPath` 挂载的内容不会收到更新，而目录投影也不能保证应用进程重新加载。

</details>

<span id="_8-what-does-the-renewbefore-field-control-in-a-certificate-resource"></span>

### 8. 请求有效期为 90 天，但收到的证书只有 45 天。在没有显式续期设置或 ARI 时，默认会在何时安排续期？

- A) 实际有效期约过 30 天时
- B) 按请求的 90 天计算，在第 60 天
- C) 始终在到期前 30 天
- D) 签发后始终在第 75 天

<details>
<summary>显示答案</summary>

**答案：A) 实际有效期约过 30 天时**

默认续期时间是实际 X.509 有效期的三分之二处。只有实际证书有效期为 90 天且设置了 `renewBefore:360h` 时，第 75 天才是正确时间。不要同时设置 `renewBefore` 和 `renewBeforePercentage`。1.21 版本的续期策略/时间窗口或受支持的 ARI 路径可能改变安排；请检查 `status.renewalTime`。

</details>

<span id="_9-what-is-the-role-of-istio-csr-in-cert-manager-s-istio-integration"></span>

### 9. 哪项准确描述了 Istio sidecar 的证书签发路径？

- A) Envoy 使用 CA 私钥签名
- B) istio-agent → istio-csr → CertificateRequest/Issuer；SDS 将材料交付给 Envoy
- C) 同一 Pod 内的每个连接都会自动启用 mTLS
- D) 设置 rootCAFile 路径后就不需要挂载真实 CA 文件

<details>
<summary>显示答案</summary>

**答案：B) istio-agent → istio-csr → CertificateRequest/Issuer；SDS 将材料交付给 Envoy**

istio-agent 会创建 CSR，再由 istio-csr 将请求接入 cert-manager 签发流程。对等代理之间的 mTLS 与本地应用这一跳是不同的连接。应挂载实际信任根证书、准备就绪的 Issuer，并配置 Istio 外部 CA 设置；不要将其与独立的 Kubernetes CSR RA 模式混为一谈。

</details>

<span id="_10-what-is-a-key-difference-between-cert-manager-and-aws-certificate-manager-acm"></span>

### 10. 关于当前 ACM 与 cert-manager 的行为，哪项说法正确？

- A) ACM 证书绝不能用于 Pod 或本地环境
- B) ALB 会直接读取 Kubernetes TLS Secret
- C) ACM 可导出证书支持显式导出；ACM ACME 有独立的生命周期和限制
- D) 只修改服务器 URL 就能完成 ACM ACME 注册

<details>
<summary>显示答案</summary>

**答案：C) ACM 可导出证书支持显式导出；ACM ACME 有独立的生命周期和限制**

ACK ACM 导出需要 `options.export:ENABLED`、`exportTo`、输出 Secret，以及单独进行域名验证。ACM ACME 要求域名预先验证并配置 EAB，密钥和续期由客户端管理；其 45 天证书不能直接附加到托管 ALB、CloudFront 或 API Gateway 集成。cert-manager 会协调 Kubernetes Secret 和多个签发者，但控制器、信任配置和 CA 费用仍由运维人员负责。

</details>

## 评分

- 9–10：理解扎实。
- 7–8：请重新查看错过的签发和信任流程。
- 6 分及以下：请复习指南和示例。

## 相关文档

- [使用 cert-manager 管理证书](../../security/10-cert-manager.md)
