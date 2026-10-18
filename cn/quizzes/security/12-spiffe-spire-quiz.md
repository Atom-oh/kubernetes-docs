# SPIFFE/SPIRE 测验

> **最后更新**：2026 年 9 月 13 日

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

使用 spiffe URI 协议标识、信任域和可选路径。不允许端口、查询参数和片段。路径结构由站点定义，不限于 /ns/.../sa/...。

</details>

<span id="_2-what-is-the-key-difference-between-x-509-svid-and-jwt-svid"></span>

### 2. 以下哪项正确描述了 X.509/JWT-SVID 验证？

- A) 只检查 X.509 CN
- B) JWT 签名有效就无需验证受众（audience）
- C) 验证 X.509 URI SAN/证书链，以及 JWT 签名、sub、受众和过期时间
- D) JWT 受众检查可防止所有重放攻击

<details>
<summary>显示答案</summary>

**答案：C) 验证 X.509 URI SAN/证书链，以及 JWT 签名、sub、受众和过期时间**

证书 CN 不是 SPIFFE 身份。即使受众匹配，JWT 持有者令牌（bearer token）仍可能被重放。有效期取决于策略；本章讨论的 X.509/JWT 与处于孵化（Incubating）阶段的 WIT-SVID 规范属于不同范围。

</details>

<span id="_3-what-is-the-primary-role-of-the-spire-server"></span>

### 3. SPIRE Server 的作用是什么？

- A) 自动加密每个应用连接
- B) 管理代理身份核验、注册和 SVID 签名
- C) 自动授权每个服务请求
- D) 通过 CSI 向所有 Pod 分发私钥文件

<details>
<summary>显示答案</summary>

**答案：B) 管理代理身份核验、注册和 SVID 签名**

应区分 CA/JWT 签名、DataStore 和 KeyManager 的职责。上游 AWS PCA 对 SPIRE 中间 CA 进行签名；本地仍需签发叶证书并管理密钥。

</details>

<span id="_4-what-is-the-primary-role-of-the-spire-agent"></span>

### 4. 谁识别调用 Workload API 的应用？

- A) 本地 SPIRE 代理的工作负载身份核验器
- B) DNS 解析器
- C) 检查文件名的 CSI
- D) 仅由应用自行声明的 SPIFFE ID

<details>
<summary>显示答案</summary>

**答案：A) 本地 SPIRE 代理的工作负载身份核验器**

代理检查调用方的 PID/cgroups/Pod 元数据，并匹配已授权的条目/缓存。在代理 Pod 内获取身份时，核验的是该调用方，而非实际应用所在的上下文。

</details>

<span id="_5-which-node-attestation-method-is-recommended-for-amazon-eks"></span>

### 5. Server 如何验证 k8s_psat token？

- A) 检查 IRSA 角色的 S3 权限
- B) Kubernetes TokenReview 加上已配置的受众/ServiceAccount 允许列表
- C) 仅对令牌进行 base64 解码
- D) 将其转换为永不过期的加入令牌

<details>
<summary>显示答案</summary>

**答案：B) Kubernetes TokenReview 加上已配置的受众/ServiceAccount 允许列表**

应核对服务器/代理的逻辑集群名称、令牌受众、ServiceAccount 允许列表和 TokenReview 权限是否匹配。aws_iid 是基于不同信任假设的替代方案，不能一概认为它在 EKS 上更强或被禁止。

</details>

<span id="_6-what-selector-types-does-k8s-workload-attestation-support"></span>

### 6. 应如何解读 k8s:container-image:nginx:*？

- A) 自动对每个 nginx 标签执行通配符模式匹配
- B) 一个选择器值；不要假定支持通配符匹配
- C) 证明镜像签名已通过验证
- D) 自动强制执行命名空间 RBAC

<details>
<summary>显示答案</summary>

**答案：B) 一个选择器值；不要假定支持通配符匹配**

应匹配 Kubernetes 实际报告的 image/ImageID 值。仅凭标签无法建立供应链信任。创建和修改 Pod/ServiceAccount/标签的权限也会影响工作负载能否获得相应身份。

</details>

<span id="_7-what-is-the-purpose-of-the-spiffe-csi-driver"></span>

### 7. SPIFFE CSI 0.2.13 会向 Pod 挂载什么？

- A) 自动生成的 svid.pem/svid.key 文件
- B) 包含 Workload API Unix 套接字的目录
- C) SPIRE CA 私钥
- D) 共享的 PostgreSQL 数据

<details>
<summary>显示答案</summary>

**答案：B) 包含 Workload API Unix 套接字的目录**

CSI 提供对 API 套接字的访问。基于文件的应用需要单独的适配器和重新加载处理。应用或代理仍需使用 API；集成并非总能自动完成。

</details>

<span id="_8-what-does-spiffe-federation-enable"></span>

### 8. 引导 https_spiffe federation 需要什么？

- A) 仅需一个端点 URL
- B) 初始可信信任包（bundle）和正确的端点 SPIFFE ID
- C) 交换两个 CA 私钥
- D) 自动授权每个远程工作负载

<details>
<summary>显示答案</summary>

**答案：B) 初始可信信任包（bundle）和正确的端点 SPIFFE ID**

应分别配置各个信任方向。信任包刷新、连通性、TLS 验证和工作负载授权是不同的职责。https_web 使用端点的 Web PKI 验证路径。

</details>

<span id="_9-how-does-spiffe-spire-compare-to-iam-roles-for-service-accounts-irsa"></span>

### 9. 以下哪项正确比较了 IRSA 与 SPIFFE/SPIRE？

- A) IRSA 刷新始终需要重启 Pod
- B) SPIFFE 消除了对 AWS IAM 策略的需求
- C) IRSA 提供 AWS 凭证获取路径；SPIFFE 提供工作负载身份，两者均需验证
- D) 一个 Pod 注解即可完成 IRSA 和 CSI 证书文件交付

<details>
<summary>显示答案</summary>

**答案：C) IRSA 提供 AWS 凭证获取路径；SPIFFE 提供工作负载身份，两者均需验证**

IRSA 通过受支持的 SDK/投射令牌机制刷新凭证，并支持跨账户设计。应验证 ServiceAccount 注解、aud/sub 信任条件和 AWS 权限。SPIFFE mTLS 还需要应用使用凭证并对通信对端进行授权。

</details>

<span id="_10-what-are-best-practices-for-naming-trust-domains-in-spiffe"></span>

### 10. 关于 trust domains 和 CA rotation，以下哪项正确？

- A) 信任域必须是可解析的 DNS 名称
- B) bundle set 会自动轮换 CA 私钥
- C) 选择稳定的名称，并区分信任包变更与 CA 密钥轮换
- D) 数字形式或类似 IPv4 的域始终会被解析器拒绝

<details>
<summary>显示答案</summary>

**答案：C) 选择稳定的名称，并区分信任包变更与 CA 密钥轮换**

类似 DNS 的命名方式是指导原则，并非完整的语法规则。信任包包含公开的信任材料；密钥轮换有独立的生命周期。应核实受信任签发机构的重叠期以及使用方的更新情况。

</details>

## 分数计算

- 9–10：理解深入
- 7–8：重新学习信任、授权和交付路径
- 6 或更少：复习指南和已验证的示例

## 相关文档

- [SPIFFE/SPIRE](../../security/12-spiffe-spire.md)
