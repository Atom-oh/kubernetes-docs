# CI 流水线测验

> **相关文档**：[CI 流水线](../../ops/03-ci-pipelines.md)

## 选择题

### 1. 为什么发布镜像和 BuildKit 缓存使用不同的 ECR 仓库？

- A) 缓存镜像不需要 IAM 身份验证
- B) 不可变的发布标签和可变的缓存引用需要不同的策略
- C) ECR 只支持一个标签
- D) 缓存消除了扫描的必要性

<details>
<summary>显示答案</summary>

**答案：B) 不可变的发布标签和可变的缓存引用需要不同的策略**

**说明：**示例将应用仓库设为不可变，将构建缓存设为可变。仅使用形如提交 SHA 的标签并不能防止覆盖；部署使用的是已验证的摘要。

</details>

### 2. GitLab Kubernetes 执行器的每个作业使用单独的 Pod，有什么作用？

- A) 即使对于特权作业，也能实现完全隔离
- B) 消除所有节点访问风险
- C) 分别管理作业生命周期和资源，但不保证构成完整的安全边界
- D) 为不受信任的 PR 安全地继承 AWS 发布权限

<details>
<summary>显示答案</summary>

**答案：C) 分别管理作业生命周期和资源，但不保证构成完整的安全边界**

**说明：**本指南中的特权 DinD 配置适用于受信任的受保护作业。Pod 隔离、专用 CI 节点和最小权限角色是彼此独立的控制措施；它们单独都不能证明任意不受信任的代码是安全的。

</details>

### 3. poll_interval 和 check_interval 有什么区别？

- A) poll_interval 检查 Kubernetes Pod 状态；check_interval 用于协调器轮询作业
- B) 它们是同一设置的别名
- C) 两者都会使 Docker 镜像缓存过期
- D) poll_interval 会重启 Pod

<details>
<summary>显示答案</summary>

**答案：A) poll_interval 检查 Kubernetes Pod 状态；check_interval 用于协调器轮询作业**

**说明：**Kubernetes 执行器在等待作业 Pod 就绪时使用 poll_interval。Runner 全局的 check_interval 控制的是另一种轮询流程；更改其中一个不能代替更改另一个。

</details>

### 4. 为什么要将 GitLab 管理器和构建 Pod 的 AWS 角色分开？

- A) 让管理器获得所有 AWS 权限
- B) 因为 Pod Identity 会自动创建 ServiceAccount
- C) 因为构建 Pod 必须存储长期密钥
- D) 将管理器的 S3 缓存访问权限与构建 Pod 的 ECR 发布权限分开限定

<details>
<summary>显示答案</summary>

**答案：D) 将管理器的 S3 缓存访问权限与构建 Pod 的 ECR 发布权限分开限定**

**说明：**如果没有 RoleARN，示例中的 S3 缓存会使用管理器的凭证链。构建 Pod 会获得不同的 ECR 角色。ServiceAccount 必须单独创建；AWS Pod Identity 令牌不同于常规 Kubernetes API 令牌。

</details>

### 5. 当前的 ARC 示例如何接收并路由作业？

- A) 只安装 RunnerDeployment 和 HorizontalRunnerAutoscaler
- B) 使用官方的扩缩集图表/监听器，并让 runs-on 与实际的扩缩集名称匹配
- C) 组织运行器组名称始终是作业标签
- D) minRunners=0 可消除所有集群成本

<details>
<summary>显示答案</summary>

**答案：B) 使用官方的扩缩集图表/监听器，并让 runs-on 与实际的扩缩集名称匹配**

**说明：**不要将旧版 CRD 模型与当前的扩缩集图表混用。ARC 0.15.0 也支持 scaleSetLabels。minRunners 指的是空闲运行器数量；它不会消除控制器/监听器成本，也无法保证启动时没有延迟。

</details>

### 6. 哪些 GitHub 作业会获取示例中的 AWS OIDC 凭证？

- A) 每个外部 PR 测试
- B) 执行任意 PR 代码的 pull_request_target 作业
- C) 测试通过后的受信任推送发布作业
- D) 每个启动时运行的自托管运行器

<details>
<summary>显示答案</summary>

**答案：C) 测试通过后的受信任推送发布作业**

**说明：**PR 测试在 GitHub 托管的运行器上运行，不会请求发布凭证。角色信任策略将范围限定为确切的仓库以及 main/受保护标签，并且 ARC Pod 不会继承 AWS 发布角色。

</details>

### 7. 哪种顺序能确保扫描到发布的流程约定得到遵守？

- A) 构建 → 成功扫描同一镜像 → 发布 → 根据获批的摘要创建索引
- B) 发布 → 忽略扫描失败 → 部署 latest
- C) 扫描源代码 → 重新构建不同的镜像 → 始终发布
- D) 将任何 JSON 文件的存在视为扫描成功

<details>
<summary>显示答案</summary>

**答案：A) 构建 → 成功扫描同一镜像 → 发布 → 根据获批的摘要创建索引**

**说明：**GitLab 通过特定于架构的 1:1 依赖项传递镜像归档。GitHub 会在推送前扫描本地构建的镜像。Trivy 错误或漏洞门禁失败都会阻止发布；原生 Trivy JSON 不会被错误标记为 GitLab 报告架构。

</details>

### 8. 关于原生运行器和 QEMU，哪项说法正确？

- A) 仅设置平台标志就能让所有异构指令都可执行
- B) QEMU 本身就是应用程序的交叉编译器
- C) AMD64 镜像可以通过重新打标签变成 ARM64 镜像
- D) 原生运行器在目标 CPU 上构建；QEMU 则模拟另一种 CPU 的指令

<details>
<summary>显示答案</summary>

**答案：D) 原生运行器在目标 CPU 上构建；QEMU 则模拟另一种 CPU 的指令**

**说明：**确保管理器/作业节点选择器、运行器标签和辅助容器架构彼此匹配。最终索引必须引用经过独立检查的平台摘要。交叉编译需要经过专门配置的工具链和 Dockerfile。

</details>

### 9. Next.js standalone 示例需要什么？

- A) npm ci --omit=dev 足以满足所有构建需求
- B) Standalone 输出、构建依赖、复制的静态资源以及正确的服务器路径
- C) public 和 .next/static 总会自动复制到 standalone 中
- D) 每个 monorepo 的入口都是根目录下的 server.js

<details>
<summary>显示答案</summary>

**答案：B) Standalone 输出、构建依赖、复制的静态资源以及正确的服务器路径**

**说明：**示例假设只有一个应用根目录，并使用 npm 锁文件。它会将 public 和 .next/static 复制到运行时目录结构中，并绑定到 0.0.0.0。Monorepo 需要自行检查 tracing-root 和嵌套输出路径。

</details>

### 10. 关于 Kaniko 和无根 BuildKit，哪项说法正确？

- A) 无守护进程就能保证每次构建都无需 root 且完全隔离
- B) 将特权 DinD 镜像重命名就完成了无根配置
- C) 检查维护状态，以及节点对用户命名空间、挂载和安全策略的支持情况
- D) no-process-sandbox 会增强进程隔离

<details>
<summary>显示答案</summary>

**答案：C) 检查维护状态，以及节点对用户命名空间、挂载和安全策略的支持情况**

**说明：**Google Kaniko 仓库已归档。可选的无根 BuildKit 片段需要使用经过单独验证的运行器。no-process-sandbox 会削弱守护进程容器的进程隔离和清理能力；注册表缓存也不会自动持久化所有缓存挂载。

</details>
