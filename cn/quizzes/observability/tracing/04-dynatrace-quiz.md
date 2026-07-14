# Dynatrace 测验

测试您对 Dynatrace 的了解。

---

1. 以下哪项不是 Dynatrace 核心技术 OneAgent 的特性？
   - A) 使用单个 agent 进行全栈监控
   - B) 自动代码插桩
   - C) 需要手动配置
   - D) 自动进程发现

<details>
<summary>显示答案</summary>

**答案：C) 需要手动配置**

**说明：**
OneAgent 的关键特性是自动发现和自动插桩。安装后，它会自动发现并监控主机上的进程、Service 和应用程序，无需额外手动配置。这体现了 Dynatrace 的“零配置”理念。

</details>

---

2. 在 EKS 中部署 Dynatrace 的推荐方式是什么？
   - A) 直接使用 kubectl apply 部署
   - B) 使用 Dynatrace Operator
   - C) 仅使用 Helm 部署 OneAgent
   - D) 使用 Lambda 函数部署

<details>
<summary>显示答案</summary>

**答案：B) 使用 Dynatrace Operator**

**说明：**
Dynatrace Operator 可自动管理 Kubernetes 环境中 Dynatrace 组件（OneAgent、ActiveGate 等）的生命周期。通过 DynaKube CR 以声明式方式进行配置，并提供自动更新、滚动部署和状态监控。

</details>

---

3. 以下哪项不是 Davis AI 引擎的主要功能？
   - A) 自动学习基线
   - B) 异常检测
   - C) 自动修复代码
   - D) 根本原因分析

<details>
<summary>显示答案</summary>

**答案：C) 自动修复代码**

**说明：**
Davis AI 可自动学习基线、检测异常并分析问题的根本原因。但是，它不会自动修复代码。Davis 可以诊断问题并提出解决方向，但实际的代码修复必须由开发人员完成。

</details>

---

4. Dynatrace 中 Cloud Native Full Stack 和 Classic Full Stack 部署模式有什么区别？
   - A) Cloud Native 仅支持 Windows
   - B) Cloud Native 使用代码模块注入
   - C) Classic 无法在云环境中使用
   - D) 两种模式提供完全相同的功能

<details>
<summary>显示答案</summary>

**答案：B) Cloud Native 使用代码模块注入**

**说明：**
Cloud Native Full Stack 是一种轻量级方法，它通过 CSI Driver 将代码模块注入到 Pod 中。Classic Full Stack 则在每个节点上以 DaemonSet 的形式部署完整的 OneAgent。Cloud Native 的资源使用量更低，并且支持在 Pod 级别进行精细控制，但对主机级监控存在限制。

</details>

---

5. Dynatrace 的 PurePath 技术提供什么功能？
   - A) 日志压缩
   - B) 代码级分布式追踪
   - C) 网络数据包捕获
   - D) 数据库备份

<details>
<summary>显示答案</summary>

**答案：B) 代码级分布式追踪**

**说明：**
PurePath 是 Dynatrace 专有的分布式追踪技术，可将请求在系统中的完整路径追踪到代码级别。它不仅记录 Service 之间的调用，还会详细记录每个 Service 内的方法调用、数据库查询和外部 API 调用。

</details>

---

6. 计算 Dynatrace Host Units 的正确公式是什么？
   - A) vCPU + Memory(GB)
   - B) max(Memory(GB) / 16, vCPU / 1.5)
   - C) vCPU * Memory(GB) / 100
   - D) (vCPU + Memory(GB)) / 2

<details>
<summary>显示答案</summary>

**答案：B) max(Memory(GB) / 16, vCPU / 1.5)**

**说明：**
Dynatrace Host Units 根据内存和 CPU 中数值较大的一项计算。16GB 内存或 1.5 vCPU 等于 1 个 Host Unit。例如，一台拥有 8 vCPU 和 32GB RAM 的主机，其结果为 max(2, 5.33) = 5.33 Host Units。

</details>

---

7. 以下哪项不是 Dynatrace ActiveGate 的角色？
   - A) 数据路由
   - B) Kubernetes API 监控
   - C) 长期数据存储
   - D) 网络区域隔离

<details>
<summary>显示答案</summary>

**答案：C) 长期数据存储**

**说明：**
ActiveGate 负责 OneAgent 与 Dynatrace SaaS 之间的数据路由、Kubernetes API 监控，以及隔离网络环境中的代理角色。长期数据存储由 Dynatrace 的 Grail 数据湖仓负责；ActiveGate 不存储数据，只负责转发。

</details>

---

8. 在 Dynatrace 中使用 namespaceSelector 的目的是什么？
   - A) 创建 namespace
   - B) 仅监控特定 namespace
   - C) 阻止 namespace 之间的通信
   - D) 设置资源配额

<details>
<summary>显示答案</summary>

**答案：B) 仅监控特定 namespace**

**说明：**
在 DynaKube CR 中使用 namespaceSelector，可以将带有特定标签的 namespace 指定为监控目标。这使得仅监控生产环境或选择性监控特定团队的 namespace 成为可能，从而优化成本。

</details>

---

9. 将 Dynatrace 与 OpenTelemetry 集成时使用什么协议？
   - A) 仅支持 gRPC
   - B) 仅支持 HTTP
   - C) OTLP (gRPC and HTTP)
   - D) 仅支持专有协议

<details>
<summary>显示答案</summary>

**答案：C) OTLP (gRPC and HTTP)**

**说明：**
Dynatrace 原生支持 OpenTelemetry Protocol (OTLP)。使用 OTEL Collector 中的 otlphttp exporter，您可以将 traces、metrics 和 logs 发送到 Dynatrace API endpoint。gRPC 和 HTTP 均受支持。

</details>

---

10. Dynatrace 的 Smartscape 提供什么功能？
    - A) 智能告警过滤
    - B) 实时拓扑映射
    - C) 自动扩缩容
    - D) 代码审查

<details>
<summary>显示答案</summary>

**答案：B) 实时拓扑映射**

**说明：**
Smartscape 是 Dynatrace 的实时拓扑映射技术。它会自动发现并可视化基础设施（主机、容器）、进程、Service 和应用程序之间的关系。这有助于了解系统依赖关系，并识别问题影响的范围。

</details>

---
