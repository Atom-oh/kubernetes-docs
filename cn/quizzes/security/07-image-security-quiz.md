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

trivy image 是镜像扫描命令。应将 IMAGE_REF 设为真实的摘要引用。仅语法有效，并不能证明能访问镜像仓库、数据库足够新，也不能确认软件包检测的覆盖范围。

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

Cosign 会验证密钥或 OIDC 身份/签发者、摘要，以及所要求的透明性证据。签名并不能保证不存在已知漏洞。

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

更早开展检查可以缩短反馈周期。发布后，仍需通过镜像仓库重新扫描和运行时检测来应对新 CVE 和运行时行为。

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

标准运行时镜像不含 shell/软件包管理器；调试变体有所不同。应用二进制文件和库仍可能包含漏洞。

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

Basic 支持手动/推送时扫描；Enhanced 支持推送时/持续扫描。应区分 findings 与 enhancedFindings，以及 ECR 事件与 Inspector 事件。

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

SBOM 记录组件及其关系，但检测覆盖可能不完整。还应分别评估将 SBOM 绑定到摘要的签名证明，以及验证策略。

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

应区分旧的 verifyImages 和较新的 ImageValidatingPolicy。Kyverno 1.19.1 示例使用 CEL 策略，配合覆盖普通、初始化和临时容器的仓库/摘要限制。

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

标签可以指向不同内容；摘要则标识具体内容。这有助于选择可复现的制品，但不能替代对签名者信任、漏洞和可用性的验证。

</details>

<span id="_9-what-does-trivy-not-scan"></span>

### 9. 哪个领域独立于 Trivy 静态检查？

- A. 操作系统软件包识别
- B. 语言依赖扫描
- C. 实时系统调用/进程行为检测
- D. 源码中的机密信息检测

<details>
<summary>显示答案</summary>

**答案：C. 实时系统调用/进程行为检测**

软件包、错误配置和机密信息扫描不同于运行时行为检测。应单独设计 Falco 等运行时工具的使用方案。

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

对有意公开的镜像进行匿名读取，本身并不构成漏洞。应分别控制保密性、写入/删除权限、来源和速率限制。

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

应区分策略违规与扫描器/数据库/权限错误，并保留结果。不要部署扫描后重新构建的不同制品。例外必须明确理由、负责人和到期时间。

</details>

<span id="_12-what-is-not-an-advantage-of-alpine-base-images"></span>

### 12. 关于 Alpine 的哪个假设不正确？

- A. 使用 musl libc
- B. 使用 apk 软件包管理器
- C. 总是与依赖 glibc 的应用完全兼容
- D. 必须检查所选发布版本的支持期限

<details>
<summary>显示答案</summary>

**答案：C. 总是与依赖 glibc 的应用完全兼容**

Alpine 使用 musl，因此依赖 glibc 的二进制文件可能存在兼容性问题。仅凭镜像大小，既无法保证漏洞数量，也无法保证构建速度。

</details>
