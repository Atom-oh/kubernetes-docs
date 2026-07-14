# 日志收集器对比测验

测试你对日志收集器（FluentBit、Promtail、Alloy、OTEL Collector）的理解。

---

1. 以下哪个日志收集器的内存使用量最低？

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) OpenTelemetry Collector

<details>
<summary>显示答案</summary>

**答案：B) FluentBit**

**说明：**
FluentBit 使用 C 编写，内存使用量最低，约为 10-50MB。其他收集器使用 Go 编写，内存使用量约为 50-100MB。

</details>

---

2. 哪个 FluentBit FILTER 会向日志添加 Kubernetes 元数据（namespace、pod_name 等）？

   - A) [FILTER] Name modify
   - B) [FILTER] Name kubernetes
   - C) [FILTER] Name parser
   - D) [FILTER] Name record_modifier

<details>
<summary>显示答案</summary>

**答案：B) [FILTER] Name kubernetes**

**说明：**
FluentBit 的 `kubernetes` filter 会通过 Kubernetes API 自动向日志添加 pod、namespace 和 labels 等元数据。

</details>

---

3. Promtail 的主要限制是什么？

   - A) 不支持 JSON 解析
   - B) 无法发送到 Loki 以外的目标
   - C) 无法在 Kubernetes 环境中使用
   - D) 无法处理多行日志

<details>
<summary>显示答案</summary>

**答案：B) 无法发送到 Loki 以外的目标**

**说明：**
Promtail 被设计为 Grafana Loki 的专用 agent，不支持发送到 OpenSearch 或 CloudWatch 等其他目标。如果需要多个目标，请使用 FluentBit 或 OTEL Collector。

</details>

---

4. Grafana Alloy 使用什么配置语言？

   - A) YAML
   - B) JSON
   - C) River（类似 HCL）
   - D) INI

<details>
<summary>显示答案</summary>

**答案：C) River（类似 HCL）**

**说明：**
Grafana Alloy 使用 River，这是一种类似 HCL（HashiCorp Configuration Language）的配置语言。它比 YAML 更具表达力，并且允许定义可复用的组件。

</details>

---

5. OpenTelemetry Collector 中 pipeline 组件的顺序是什么？

   - A) Processors → Receivers → Exporters
   - B) Receivers → Exporters → Processors
   - C) Receivers → Processors → Exporters
   - D) Exporters → Processors → Receivers

<details>
<summary>显示答案</summary>

**答案：C) Receivers → Processors → Exporters**

**说明：**
OTEL Collector pipeline 按以下顺序组成：Receivers（接收数据）→ Processors（处理/转换数据）→ Exporters（发送数据）。

</details>

---

6. 在 FluentBit 中可以使用什么脚本语言来实现复杂的日志处理逻辑？

   - A) Python
   - B) JavaScript
   - C) Lua
   - D) Ruby

<details>
<summary>显示答案</summary>

**答案：C) Lua**

**说明：**
FluentBit 支持使用 Lua 脚本实现复杂的日志处理逻辑（字段转换、条件处理、敏感数据脱敏等）。请使用 `[FILTER] Name lua` filter。

</details>

---

7. Promtail 配置中的哪个 pipeline_stages 设置可以排除特定日志？

   - A) stage.filter
   - B) stage.drop
   - C) stage.exclude
   - D) stage.ignore

<details>
<summary>显示答案</summary>

**答案：B) stage.drop**

**说明：**
Promtail 的 `stage.drop` 会排除与 regex 或条件匹配的日志行。例如：使用 `expression: "healthcheck|readiness"` 排除 healthcheck 日志。

</details>

---

8. 在 AWS 环境中，当需要将日志同时发送到 CloudWatch Logs 和 OpenSearch 时，哪个收集器最合适？

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) Logstash

<details>
<summary>显示答案</summary>

**答案：B) FluentBit**

**说明：**
FluentBit 原生支持 `cloudwatch_logs` 和 `opensearch` 两种 output plugin。它可以使用 AWS 提供的 `aws-for-fluent-bit` image 轻松部署。Promtail 和 Alloy 针对 Loki 进行了优化。

</details>

---

9. OpenTelemetry Collector 中哪个 processor 会限制内存使用量？

   - A) batch
   - B) memory_limiter
   - C) resource
   - D) filter

<details>
<summary>显示答案</summary>

**答案：B) memory_limiter**

**说明：**
`memory_limiter` processor 会监控 OTEL Collector 的内存使用量，并在达到配置的限制时暂时暂停数据收集以防止 OOM。

</details>

---

10. 当需要在现有 Promtail 环境中同时收集 metrics 和 traces 时，推荐迁移到哪个目标？

    - A) FluentBit
    - B) Logstash
    - C) Grafana Alloy
    - D) Filebeat

<details>
<summary>显示答案</summary>

**答案：C) Grafana Alloy**

**说明：**
Grafana Alloy 是 Promtail 的后继项目，包含所有 Promtail 功能，同时还能够收集 metrics（Prometheus）和 traces（Tempo）。Promtail 配置可以轻松迁移到 River syntax。

</details>
