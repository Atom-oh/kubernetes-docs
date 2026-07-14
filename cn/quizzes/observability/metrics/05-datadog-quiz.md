# Datadog 测验

用于测试您对 Datadog 理解程度的测验。

---

1. Datadog 的主要部署模式是什么？
   - A) 仅自托管
   - B) SaaS（Software as a Service）
   - C) 仅本地部署
   - D) 必须采用混合模式

<details>
<summary>显示答案</summary>

**答案：B) SaaS（Software as a Service）**

**说明：**
Datadog 是以 SaaS 模式提供的统一可观测性平台。用户只需部署 Datadog Agent，而数据存储、处理和可视化均由 Datadog 的云基础设施负责。这使您无需承担运维开销即可使用强大的监控功能。

</details>

---

2. Datadog Cluster Agent 的作用是什么？
   - A) 容器日志收集
   - B) 集群级指标和事件收集
   - C) APM 追踪处理
   - D) Dashboard 渲染

<details>
<summary>显示答案</summary>

**答案：B) 集群级指标和事件收集**

**说明：**
Datadog Cluster Agent 从 Kubernetes 集群收集集群级指标和事件。它还为 HPA（Horizontal Pod Autoscaler）提供自定义指标服务器角色，并通过 Admission Controller 自动注入 APM 插桩。

</details>

---

3. 如何在 Datadog 中启用自动 APM 插桩？
   - A) 必须修改应用程序代码
   - B) 使用 Admission Controller 和 Pod 标签
   - C) 部署独立的 APM 服务器
   - D) 手动注入库

<details>
<summary>显示答案</summary>

**答案：B) 使用 Admission Controller 和 Pod 标签**

**说明：**
启用 Datadog Admission Controller 后，APM 插桩库会自动注入带有 `admission.datadoghq.com/enabled: "true"` 标签的 Pod。它支持包括 Java、Python、Node.js、.NET 和 Ruby 在内的主要语言，让您无需修改代码即可开始追踪。

</details>

---

4. DogStatsD 的作用是什么？
   - A) 日志收集
   - B) 自定义指标收集（兼容 StatsD）
   - C) 创建 Dashboard
   - D) 告警路由

<details>
<summary>显示答案</summary>

**答案：B) 自定义指标收集（兼容 StatsD）**

**说明：**
DogStatsD 是 Datadog Agent 内置的、兼容 StatsD 的指标收集守护进程。应用程序可以通过 UDP 发送自定义指标（计数器、仪表、直方图、分布）。它兼容 StatsD 协议，并增加了标签功能。

</details>

---

5. 如何在 Datadog 中关联追踪和日志？
   - A) 手动上传日志文件
   - B) 在日志中包含 trace_id 和 span_id
   - C) 部署独立的关联服务
   - D) 匹配日志和追踪的时间戳

<details>
<summary>显示答案</summary>

**答案：B) 在日志中包含 trace_id 和 span_id**

**说明：**
要在 Datadog 中关联追踪和日志，日志必须包含 `dd.trace_id` 和 `dd.span_id`。Datadog APM 库可以通过 MDC（Mapped Diagnostic Context）自动注入此信息。这样便可直接从 APM 查看相关日志。

</details>

---

6. 在 Datadog 的成本结构中，基础设施监控的计费单位是什么？
   - A) 指标数量
   - B) 主机数量
   - C) API 调用次数
   - D) 数据传输量

<details>
<summary>显示答案</summary>

**答案：B) 主机数量**

**说明：**
Datadog 基础设施监控按主机数量计费。每个节点、实例和容器主机都是一个可计费项。APM、日志管理和其他功能具有独立的计费结构，而基于主机的计费使成本预测更容易。

</details>

---

7. Datadog Watchdog 的功能是什么？
   - A) 手动配置告警
   - B) 基于 AI 的自动异常检测
   - C) 日志搜索
   - D) 创建 Dashboard

<details>
<summary>显示答案</summary>

**答案：B) 基于 AI 的自动异常检测**

**说明：**
Watchdog 是 Datadog 基于 AI/ML 的自动异常检测功能。它会自动检测基础设施、APM 和日志数据中的异常模式并生成告警。您无需手动设置阈值即可识别异常。

</details>

---

8. 如何使用 Datadog Agent 收集 Prometheus 指标？
   - A) 必须使用独立的 Prometheus 服务器
   - B) 使用 Pod 注解配置自动发现
   - C) 手动注册每个端点
   - D) 用 Datadog 替换 Prometheus

<details>
<summary>显示答案</summary>

**答案：B) 使用 Pod 注解配置自动发现**

**说明：**
Datadog Agent 使用 `ad.datadoghq.com/<container>.checks` 注解自动发现并收集 Prometheus 指标端点。配置方式与 Prometheus 抓取设置类似，无需独立的 Prometheus 服务器即可收集指标。

</details>

---

9. 在 Datadog 中设置 SLO（Service Level Objective）时可以使用哪些类型的指标？
   - A) 仅日志事件
   - B) 基于指标、基于监控器、基于时间片
   - C) 仅 APM 追踪
   - D) 仅基础设施指标

<details>
<summary>显示答案</summary>

**答案：B) 基于指标、基于监控器、基于时间片**

**说明：**
Datadog SLO 支持三种类型：基于指标（成功/失败计数）、基于监控器（现有监控器状态）和基于时间片（每个时间间隔的状态）。可使用包括 APM 追踪、自定义指标和基于日志的指标在内的各种数据源。

</details>

---

10. 以下哪项不是有效的 Datadog 成本优化策略？
    - A) 调整 APM 追踪采样率
    - B) 过滤不必要的日志
    - C) 以最高分辨率收集所有指标
    - D) 管理自定义指标基数

<details>
<summary>显示答案</summary>

**答案：C) 以最高分辨率收集所有指标**

**说明：**
对于 Datadog 成本优化，APM 追踪采样、日志过滤和自定义指标基数管理非常重要。以最高分辨率收集所有指标会导致成本激增。应仅选择性收集必要指标并采用适当的采样。

</details>
