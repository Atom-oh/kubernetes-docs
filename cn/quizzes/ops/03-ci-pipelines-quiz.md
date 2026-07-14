# CI Pipelines 测验

> **相关文档**: [CI Pipelines](../../ops/03-ci-pipelines.md)

## 选择题

### 1. ECR lifecycle policies 的主要用途是什么？

- A) 自动构建 container images
- B) 管理 image 保留并降低存储成本
- C) 扫描 images 中的漏洞
- D) 跨区域复制 images

<details>
<summary>显示答案</summary>

**答案：B) 管理 image 保留并降低存储成本**

**解释：**
ECR lifecycle policies 会根据年龄或数量等规则自动过期并删除旧 images。这可以防止存储无限增长并降低成本，同时无限期保留重要 images（例如 production tags）。

</details>

### 2. 在 EKS 上运行 GitLab Runner 时，建议使用哪种 executor 类型来实现隔离？

- A) Shell executor
- B) Docker executor
- C) Kubernetes executor
- D) SSH executor

<details>
<summary>显示答案</summary>

**答案：C) Kubernetes executor**

**解释：**
Kubernetes executor 会在单独的 pod 中运行每个 CI job，从而在 jobs 之间提供强隔离。它会在 jobs 完成后自动清理资源，并且可以利用 Kubernetes 的 node selectors 和 tolerations 等功能。

</details>

### 3. GitHub Actions Runner Controller (ARC) 是什么？

- A) GitHub 托管的 runner 服务
- B) 用于自托管 GitHub runners 的 Kubernetes operator
- C) GitHub API client library
- D) Container registry controller

<details>
<summary>显示答案</summary>

**答案：B) 用于自托管 GitHub runners 的 Kubernetes operator**

**解释：**
ARC 是一个 Kubernetes operator，会根据 workflow 需求自动扩缩自托管的 GitHub Actions runners。它会在 jobs 排队时创建 runner pods，并在完成后清理它们。

</details>

### 4. 多平台 container builds (linux/amd64, linux/arm64) 的好处是什么？

- A) 更小的 image 大小
- B) 更快的构建时间
- C) 支持不同的 CPU architectures（x86 和 Graviton）
- D) 更好的安全扫描

<details>
<summary>显示答案</summary>

**答案：C) 支持不同的 CPU architectures（x86 和 Graviton）**

**解释：**
多平台 builds 会创建可同时在 x86 (amd64) 和 ARM (arm64/Graviton) processors 上运行的 images。这可以通过使用 Graviton instances 实现成本优化，并支持多样化的部署环境。

</details>

### 5. BuildKit cache 如何提升 container build 性能？

- A) 跳过所有构建步骤
- B) 缓存 layer artifacts 并重用未变化的 layers
- C) 将 images 压缩得更小
- D) 并行化所有操作

<details>
<summary>显示答案</summary>

**答案：B) 缓存 layer artifacts 并重用未变化的 layers**

**解释：**
BuildKit 会智能地缓存 build artifacts 和 layer outputs。当 source files 未发生变化时，它会重用 cached layers，而不是重新构建。Cache 可以存储在 registries、S3 或本地存储中，以便在 builds 之间共享。

</details>

### 6. Kaniko 主要用于什么？

- A) Container orchestration
- B) 在没有 Docker daemon 的情况下构建 container images
- C) Container runtime security
- D) Image vulnerability scanning

<details>
<summary>显示答案</summary>

**答案：B) 在没有 Docker daemon 的情况下构建 container images**

**解释：**
Kaniko 可以从 Dockerfiles 构建 container images，而不需要 Docker daemon 或 privileged mode。这使它非常适合 CI/CD 环境，因为在这些环境中运行 Docker-in-Docker 可能带来安全顾虑，或者根本不可用。

</details>

### 7. 在 GitLab CI 中，`services` 关键字的用途是什么？

- A) 定义 deployment targets
- B) 启动辅助 containers（如 databases）用于测试
- C) 配置 GitLab Pages
- D) 设置 monitoring

<details>
<summary>显示答案</summary>

**答案：B) 启动辅助 containers（如 databases）用于测试**

**解释：**
`services` 关键字定义与主 job container 一起运行的 containers。它们通常用于测试依赖项，例如 tests 需要交互的 databases（PostgreSQL、MySQL）或 caches（Redis）。

</details>

### 8. 在 CI/CD 中存储 container build cache 的推荐方法是什么？

- A) 仅使用本地磁盘
- B) 使用带有 --cache-to 和 --cache-from flags 的 registry-based cache
- C) 绝不在 CI/CD 中使用 cache
- D) 将 cache 存储在 git repository 中

<details>
<summary>显示答案</summary>

**答案：B) 使用带有 --cache-to 和 --cache-from flags 的 registry-based cache**

**解释：**
Registry-based caching 会将 build cache layers 存储在 container registry 中，使其可被不同的 CI runners 访问。BuildKit 的 `--cache-to` 和 `--cache-from` flags 支持这种模式，以实现一致的构建加速。

</details>

### 9. 配置 GitHub ARC 时，`minRunners` 设置控制什么？

- A) 最大并发 jobs 数
- B) 维护的最小空闲 runners 数
- C) Runner memory allocation
- D) Job timeout duration

<details>
<summary>显示答案</summary>

**答案：B) 维护的最小空闲 runners 数**

**解释：**
`minRunners` 可确保始终有一组基线 warm runners 可用，从而减少 job 启动延迟。将其设置为大于零可以避免对时间敏感的 workflows 出现 cold-start delays，但会增加空闲资源成本。

</details>

### 10. 使用 IAM roles 而不是长期凭证来配置 CI/CD runners 的安全优势是什么？

- A) 更快的身份验证
- B) 自动凭证轮换并降低暴露风险
- C) 更简单的配置
- D) Cross-account access

<details>
<summary>显示答案</summary>

**答案：B) 自动凭证轮换并降低暴露风险**

**解释：**
IAM roles 提供会自动轮换的临时凭证，消除了长期 access keys 泄露或被攻破的风险。结合 Pod Identity 或 IRSA，runners 可以获得范围限定的权限，而无需存储 secrets。

</details>
