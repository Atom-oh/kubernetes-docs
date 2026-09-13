<span id="quiz-questions"></span>

# 容器镜像安全测验
> **最后更新**：2026 年 9 月 13 日

<span id="_1-what-is-the-correct-command-to-scan-a-container-image-with-trivy"></span>

### 1. 哪个命令使用 Trivy 扫描给定镜像引用？

- A. trivy scan "$IMAGE_REF"
- B. trivy image "$IMAGE_REF"
- C. trivy container "$IMAGE_REF"
- D. trivy check "$IMAGE_REF"

<details>
<summary>显示答案</summary>

**答案：B. trivy image "$IMAGE_REF"**

trivy image 是镜像扫描命令。将 IMAGE_REF 设为真实摘要引用。仅语法有效不证明仓库访问、数据库新鲜度或软件包检测覆盖。

</details>

<span id="_2-which-tool-is-used-for-image-signing-and-verification"></span>

### 2. 哪个工具验证镜像摘要与获准签名者之间的关系？

- A. Trivy 的 CVE 数据库
- B. Cosign/Sigstore
- C. Clair 软件包扫描器
- D. Docker imagePullPolicy

<details>
<summary>显示答案</summary>

**答案：B. Cosign/Sigstore**

Cosign 验证密钥或 OIDC 身份/签发者、摘要及必需透明性证据。签名不保证没有已知漏洞。

</details>

<span id="_3-what-does-the-shift-left-security-approach-mean"></span>

### 3. 安全左移是什么意思？

- A. 将检查推迟到生产
- B. 在开发、PR 和构建中更早检查
- C. 将源码访问限于安全团队
- D. 移除生产重新扫描

<details>
<summary>显示答案</summary>

**答案：B. 在开发、PR 和构建中更早检查**

更早检查缩短反馈循环。发布后新 CVE 和运行时行为仍需要仓库重新扫描和运行时检测。

</details>

<span id="_4-what-is-the-main-characteristic-of-distroless-images"></span>

### 4. 标准 distroless 运行时镜像有什么特点？

- A. 包含所有 Linux 工具
- B. 仅包含最小应用运行时组件集
- C. 总是包含 shell 和调试器
- D. 必须包含软件包管理器

<details>
<summary>显示答案</summary>

**答案：B. 仅包含最小应用运行时组件集**

标准运行时不含 shell/软件包管理器；调试变体不同。应用二进制和库仍可包含漏洞。

</details>

<span id="_5-what-are-the-two-types-of-amazon-ecr-image-scanning"></span>

### 5. 当前 ECR Basic 与 Enhanced 扫描有何不同？

- A. Basic 使用 AWS 原生操作系统扫描；Enhanced 使用 Inspector 扫描操作系统/语言软件包
- B. Basic 总使用 Clair；Enhanced 仅扫描操作系统包
- C. 两者都自动拒绝推送
- D. Enhanced 永久扫描每个镜像

<details>
<summary>显示答案</summary>

**答案：A. Basic 使用 AWS 原生操作系统扫描；Enhanced 使用 Inspector 扫描操作系统/语言软件包**

Basic 支持手动/推送时扫描；Enhanced 支持推送时/持续扫描。区分 findings 与 enhancedFindings，以及 ECR 与 Inspector 事件。

</details>

<span id="_6-what-is-sbom-software-bill-of-materials"></span>

### 6. SBOM 提供什么？

- A. 无漏洞认证
- B. 工具检测到的软件组件清单
- C. 获准签名者的自动证明
- D. 部署授权

<details>
<summary>显示答案</summary>

**答案：B. 工具检测到的软件组件清单**

SBOM 记录组件和关系，但覆盖可能不完整。单独评估将其绑定摘要的签名证明和验证策略。

</details>

<span id="_7-what-policy-type-verifies-image-signatures-in-kyverno"></span>

### 7. 旧 Kyverno ClusterPolicy 中哪个规则执行镜像签名检查？

- A. 仅 validate
- B. 仅 mutate
- C. verifyImages
- D. 仅 generate

<details>
<summary>显示答案</summary>

**答案：C. verifyImages**

区分旧 verifyImages 和较新的 ImageValidatingPolicy。Kyverno 1.19.1 示例使用 CEL 策略，配合覆盖普通、初始化和临时容器的仓库/摘要限制。

</details>

<span id="_8-why-should-you-use-digests-instead-of-image-tags"></span>

### 8. 为什么固定镜像摘要而非标签？

- A. 总是更短
- B. 标识特定镜像内容
- C. 自动验证签名
- D. 移除 CVE

<details>
<summary>显示答案</summary>

**答案：B. 标识特定镜像内容**

标签可移动；摘要标识内容。这支持可复现制品选择，但不替代签名者信任、漏洞检查或可用性验证。

</details>

<span id="_9-what-does-trivy-not-scan"></span>

### 9. 哪个领域独立于 Trivy 静态检查？

- A. 操作系统软件包识别
- B. 语言依赖扫描
- C. 实时系统调用/进程行为检测
- D. 源码密钥检测

<details>
<summary>显示答案</summary>

**答案：C. 实时系统调用/进程行为检测**

软件包、错误配置和密钥扫描不同于运行时行为检测。单独设计 Falco 等运行时工具。

</details>

<span id="_10-which-is-not-a-container-image-registry-security-best-practice"></span>

### 10. 哪种仓库访问做法不合适？

- A. 为私有镜像使用获准拉取身份
- B. 验证公共镜像摘要/签名
- C. 允许任意匿名镜像推送/删除
- D. 分离仓库、准入和扫描门禁权限

<details>
<summary>显示答案</summary>

**答案：C. 允许任意匿名镜像推送/删除**

有意公开镜像的匿名读取本身不是漏洞。分别控制保密性、写入/删除权限、来源和限速。

</details>

<span id="_11-what-is-the-recommended-action-when-image-scanning-fails-in-ci-cd-pipeline"></span>

### 11. 约定的 CI 扫描门禁未通过时应如何处理？

- A. 始终忽略
- B. 在发布/签名前停止并检查原因
- C. 重建另一镜像，不扫描就推送
- D. 强制退出码为 0

<details>
<summary>显示答案</summary>

**答案：B. 在发布/签名前停止并检查原因**

区分策略违规与扫描器/数据库/权限错误，并保留结果。不要部署扫描后重新构建的不同制品。例外需要理由、所有者和到期时间。

</details>

<span id="_12-what-is-not-an-advantage-of-alpine-base-images"></span>

### 12. 关于 Alpine 的哪个假设不正确？

- A. 使用 musl libc
- B. 使用 apk 软件包管理器
- C. 总是与依赖 glibc 的应用完全兼容
- D. 必须检查所选发布版本的支持寿命

<details>
<summary>显示答案</summary>

**答案：C. 总是与依赖 glibc 的应用完全兼容**

Alpine 使用 musl，因此依赖 glibc 的二进制可能有兼容性问题。仅镜像大小既不保证漏洞数量，也不保证构建速度。

</details>
