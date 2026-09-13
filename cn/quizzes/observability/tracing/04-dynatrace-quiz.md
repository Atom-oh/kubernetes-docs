# Dynatrace 测验

> **最后更新**: September 13, 2026

---

1. 关于 OneAgent 的说法中，哪一项是错误的？
   - A) 它可以发现受支持的进程。
   - B) 它可以对受支持的技术进行插桩（instrument）。
   - C) 安装后即可免除所有权限、范围和连通性方面的前提条件。
   - D) 覆盖范围取决于部署模式和技术支持情况。

<details>
<summary>显示答案</summary>

**答案：C) 安装后即可免除所有权限、范围和连通性方面的前提条件。**

自动发现并不能消除安装权限、受支持运行时的要求、出站网络访问（egress）、令牌配置、注入选择或数据隐私方面的决策。它也不保证捕获每一个方法或请求。

</details>

---

2. 哪个组件负责在 Kubernetes 中管理 DynaKube 资源和 Dynatrace 工作负载？
   - A) 独立的 kubectl 二进制文件。
   - B) Dynatrace Operator。
   - C) 仅 OneAgent 进程。
   - D) 自动创建的 Lambda 函数。

<details>
<summary>显示答案</summary>

**答案：B) Dynatrace Operator。**

Helm 或 manifest 都用于安装 Operator，二者并非互相竞争的监控模式。所审阅的 Operator/chart 版本为 1.10.2。其发布的 CRD 提供 v1beta5 和 v1beta6，其中 v1beta6 为存储版本；旧的 v1beta2 示例已不是当前提供的 API。组件版本和更新行为仍需审查。

</details>

---

3. 启用问题检测和根因分析并不意味着以下哪种结果？
   - A) 基线与异常分析。
   - B) 具备拓扑感知的调查。
   - C) 自动授权未经审查的生产代码变更。
   - D) 使用所收集证据进行影响分析。

<details>
<summary>显示答案</summary>

**答案：C) 自动授权未经审查的生产代码变更。**

Davis 这一术语仍出现在较旧的资料中；当前文档使用 Dynatrace Intelligence。可以配置经批准的智能体式（agentic）操作/工作流，包括 Preview 功能，因此“AI 永远不能执行操作”这种说法也过于绝对。仅有检测能力并不赋予修复权限，也不能证明诊断结论正确。

</details>

---

4. cloudNativeFullStack 结合了什么？
   - A) 仅 Windows 监控。
   - B) 主机监控与基于 webhook 的应用代码模块注入。
   - C) 仅应用监控，不含主机组件。
   - D) 保证在所有工作负载中降低开销。

<details>
<summary>显示答案</summary>

**答案：B) 主机监控与基于 webhook 的应用代码模块注入。**

已发布的 Operator 将 cloudNativeFullStack 描述为结合 hostMonitoring 和 applicationMonitoring，并使用其 CSI 基础设施。它不仅仅是一个应用 sidecar。classicFullStack 在所审阅的版本中仍然存在，不要称其已被移除。模式、操作系统和 CSI 权限决定其适用性。

</details>

---

5. 与 PurePath 相关联的能力是什么？
   - A) 日志压缩。
   - B) 具备受支持的代码级上下文的分布式追踪。
   - C) 通用抓包设备。
   - D) 数据库备份。

<details>
<summary>显示答案</summary>

**答案：B) 具备受支持的代码级上下文的分布式追踪。**

追踪和代码可见性取决于受支持的技术、插桩、捕获/采样设置以及可用的遥测数据。“完整路径”并不能证明每个请求、方法或异步关系都被保留。

</details>

---

6. 当前基于主机的 DPS Full-Stack Monitoring 使用哪种计量方式？
   - A) vCPU 加 RAM。
   - B) 按适用价目表计费的受监控内存 GiB 小时数。
   - C) max(RAM/16, vCPU/1.5) 个 Host Unit。
   - D) 每个 Kubernetes namespace 一个固定单位。

<details>
<summary>显示答案</summary>

**答案：B) 按适用价目表计费的受监控内存 GiB 小时数。**

厂商文档说明了 15 分钟的计费间隔、RAM 按 0.25 GiB 取整以及每主机 4 GiB 的最低值。基于容器的仅应用监控具有不同的内存和最低值规则。旧的 CPU/RAM 取最大值公式不是当前 DPS 的计算方式。用量计算不等于账单：承诺用量、价目表、额度以及单独计费的功能都会产生影响。

</details>

---

7. 以下哪项不是 ActiveGate 的职责？
   - A) 路由遥测数据。
   - B) 已配置的 Kubernetes API 监控。
   - C) 作为长期分析数据湖仓（data lakehouse）。
   - D) 提供经批准的到环境的连通路径。

<details>
<summary>显示答案</summary>

**答案：C) 作为长期分析数据湖仓（data lakehouse）。**

路由/监控和本地缓冲与长期后端存储不同。某些容器化 ActiveGate 的数据摄取配置需要 PVC。SaaS 路径仍然需要连通性；代理并不能让完全断网的网络访问到 SaaS。

</details>

---

8. oneAgent.cloudNativeFullStack.namespaceSelector 选择的是什么？
   - A) 要创建的 namespace。
   - B) 符合所配置的 webhook 注入条件的 namespace。
   - C) 网络隔离边界。
   - D) 主机监控和 Kubernetes API 监控的完整范围。

<details>
<summary>显示答案</summary>

**答案：B) 符合所配置的 webhook 注入条件的 namespace。**

该选择器和 Pod 注入注解控制 webhook 注入。它们不会限制 OneAgent 的主机监控或 ActiveGate 的 Kubernetes API 监控。元数据增强和 OTLP exporter 自动配置各有自己的选择器。请保护标签和 DynaKube 的更新权限；选择器既不是 RBAC，也不是计费上限。

</details>

---

9. 文档中记载的原生 Dynatrace SaaS/ActiveGate OTLP API 接受哪种传输方式？
   - A) 仅 gRPC。
   - B) 使用二进制 Protocol Buffers 的 HTTP。
   - C) gRPC 和 HTTP/JSON 可互换使用。
   - D) 仅一种专有的非 OTLP 格式。

<details>
<summary>显示答案</summary>

**答案：B) 使用二进制 Protocol Buffers 的 HTTP。**

原生端点支持 HTTP/protobuf，不支持 gRPC 或 protobuf JSON。Collector 可以接收 gRPC 并以 HTTP 方式导出到 Dynatrace。请使用正确的 /api/v2/otlp 基础路径和信号后缀、TLS 以及所选端点要求的令牌类型/权限范围。不要用 .apps 浏览器 URL 代替。

</details>

---

10. Smartscape 提供什么？
   - A) 通用的告警静音开关。
   - B) 基于观测数据的拓扑和依赖关系映射。
   - C) 自动授权扩缩容。
   - D) 源代码审查。

<details>
<summary>显示答案</summary>

**答案：B) 基于观测数据的拓扑和依赖关系映射。**

依赖关系图支持影响分析和问题调查。其覆盖范围取决于受监控的技术和遥测数据；不能把缺失的关系或数据空缺当作不存在依赖关系的证据。

</details>

---

[返回指南](../../../observability/tracing/04-dynatrace.md)
