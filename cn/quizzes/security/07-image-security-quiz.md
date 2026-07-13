# Container Image 安全测验

本测验测试你对 image scanning、image signing、supply chain security 以及 base image 选择的理解。

## 测验题目

### 1. 使用 Trivy 扫描 container image 的正确命令是什么？

A. trivy scan nginx:latest
B. trivy image nginx:latest
C. trivy container nginx:latest
D. trivy check nginx:latest

<details>
<summary>显示答案</summary>

**答案：B. trivy image nginx:latest**

**解释：**
Trivy 的 image scanning 命令：
```bash
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL nginx:latest
trivy image --format json nginx:latest
```

`trivy image` 会扫描 container image 中的漏洞。

</details>

### 2. 哪个工具用于 image signing 和验证？

A. Trivy
B. Cosign/Sigstore
C. Clair
D. Anchore

<details>
<summary>显示答案</summary>

**答案：B. Cosign/Sigstore**

**解释：**
Cosign 是 Sigstore 项目的一部分，是用于 container image signing 和验证的工具：
```bash
# Sign image
cosign sign --key cosign.key myregistry/myimage:tag

# Verify signature
cosign verify --key cosign.pub myregistry/myimage:tag
```

Trivy、Clair 和 Anchore 是 vulnerability scanners。

</details>

### 3. “Shift-Left” 安全方法是什么意思？

A. 将安全推迟到运维阶段
B. 将安全前移到早期开发阶段
C. 仅由安全团队负责
D. 移除自动化

<details>
<summary>显示答案</summary>

**答案：B. 将安全前移到早期开发阶段**

**解释：**
Shift-Left 安全将安全检查移动到开发周期中尽可能早的阶段：
- 在 IDE 阶段进行扫描
- CI/CD pipeline 中的 build gates
- PR review 期间的安全检查

问题发现得越早，修复成本就越低。

</details>

### 4. Distroless images 的主要特征是什么？

A. 包含所有 Linux 实用程序
B. 只包含运行应用程序所需的最小组件
C. 包含调试工具
D. 包含 package managers

<details>
<summary>显示答案</summary>

**答案：B. 只包含运行应用程序所需的最小组件**

**解释：**
Distroless images 具有：
- 无 shell（bash、sh 等）
- 无 package manager
- 无不必要的实用程序
- 最小攻击面
- 仅应用程序 runtime

在安全性和 image 大小方面都有好处。

</details>

### 5. Amazon ECR image scanning 的两种类型是什么？

A. Basic scanning, Enhanced scanning
B. Automatic scanning, Manual scanning
C. Quick scanning, Deep scanning
D. Free scanning, Paid scanning

<details>
<summary>显示答案</summary>

**答案：A. Basic scanning, Enhanced scanning**

**解释：**
Amazon ECR scanning 类型：
- **Basic scanning**：基于 Clair 的 OS package vulnerability scan
- **Enhanced scanning**：基于 Amazon Inspector，支持 OS + programming language packages，并进行 continuous scanning

Enhanced scanning 有额外费用，但更全面。

</details>

### 6. 什么是 SBOM (Software Bill of Materials)？

A. software licenses 列表
B. software components 列表
C. security vulnerabilities 列表
D. build commands 列表

<details>
<summary>显示答案</summary>

**答案：B. software components 列表**

**解释：**
SBOM 是软件中包含的所有组件（库、依赖项、版本等）的列表。它对 supply chain security 和 vulnerability management 至关重要：
```bash
# Generate SBOM with Trivy
trivy image --format spdx-json -o sbom.json nginx:latest
```

</details>

### 7. 哪种 policy 类型会在 Kyverno 中验证 image signatures？

A. validate
B. mutate
C. verifyImages
D. generate

<details>
<summary>显示答案</summary>

**答案：C. verifyImages**

**解释：**
Kyverno 的 `verifyImages` 规则会验证 container image signatures：
```yaml
spec:
  rules:
  - name: verify-signature
    verifyImages:
    - imageReferences:
      - "myregistry/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              ...
              -----END PUBLIC KEY-----
```

</details>

### 8. 为什么应该使用 digests 而不是 image tags？

A. 名称更短
B. 保证不可变性
C. 拉取更快
D. 节省存储空间

<details>
<summary>显示答案</summary>

**答案：B. 保证不可变性**

**解释：**
Tags（例如 `nginx:latest`）可以被更改为指向不同的 images。Digests（例如 `nginx@sha256:abc123...`）是特定 image 内容的哈希，并且不可变：
```yaml
image: nginx@sha256:abc123def456...
```

这可以确保可复现性和安全性。

</details>

### 9. Trivy 不会扫描什么？

A. OS package vulnerabilities
B. Language-specific dependencies
C. Runtime behavior
D. Secret detection

<details>
<summary>显示答案</summary>

**答案：C. Runtime behavior**

**解释：**
Trivy 是一个 static analysis 工具，会扫描：
- OS package vulnerabilities
- Language-specific dependencies（npm、pip、go 等）
- IaC misconfigurations
- Hardcoded secrets
- Licenses

Runtime behavior analysis 是 Falco 等 runtime security tools 的领域。

</details>

### 10. 哪一项不是 container image registry 安全最佳实践？

A. 使用 private registry
B. 启用 image scanning
C. 允许 anonymous pulling
D. 阻止 vulnerable image push

<details>
<summary>显示答案</summary>

**答案：C. 允许 anonymous pulling**

**解释：**
Registry 安全最佳实践：
- 使用 private registry
- 基于 IAM 的 authentication
- 启用 image scanning
- 阻止 vulnerable image push/pull
- Image signature verification
- 使用 immutable tags 或 digests

Anonymous pulling 是安全风险，应在生产环境中禁用。

</details>

### 11. 当 CI/CD pipeline 中 image scanning 失败时，建议的操作是什么？

A. 仅记录 warning
B. 停止 build
C. 自动修复
D. 忽略并继续

<details>
<summary>显示答案</summary>

**答案：B. 停止 build**

**解释：**
在 CI/CD pipelines 中，当发现 Critical/High 漏洞时，build 应该停止：
```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myimage:tag
```

当发现漏洞时，`--exit-code 1` 会返回非零退出码，从而使 pipeline 失败。

</details>

### 12. 哪一项不是 Alpine base images 的优势？

A. 体积小
B. 漏洞更少
C. glibc 兼容性
D. build 速度快

<details>
<summary>显示答案</summary>

**答案：C. glibc 兼容性**

**解释：**
Alpine Linux 特性：
- 体积小（~5MB）
- 最少 packages
- 使用 musl libc（不是 glibc）

Alpine 使用 musl libc 而不是 glibc，因此某些依赖 glibc 的应用程序可能存在兼容性问题。

</details>
