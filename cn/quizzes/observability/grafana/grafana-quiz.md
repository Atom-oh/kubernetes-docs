# Grafana Dashboard 测验

测试你对 Grafana 的理解。

---

1. 以下哪项不是 Grafana 中用于配置数据源的方法？
   - A) 使用 sidecar 的 ConfigMap
   - B) Grafana API
   - C) 环境变量
   - D) provisioning 目录

<details>
<summary>显示答案</summary>

**答案：C) 环境变量**

**说明：**
Grafana 数据源可以通过 provisioning 目录中的 YAML 文件、使用 ConfigMap 的 sidecar 方式或 Grafana API 进行配置。环境变量用于 Grafana 配置（grafana.ini），但不会用于直接定义数据源。

</details>

---

2. RED Method 中的“R”、“E”、“D”分别代表什么？
   - A) 资源、错误、持续时间
   - B) 速率、错误、持续时间
   - C) 请求、异常、延迟
   - D) 响应、事件、数据

<details>
<summary>显示答案</summary>

**答案：B) 速率、错误、持续时间**

**说明：**
RED Method 是一种用于分析服务级别指标的方法论。它监控三个关键指标：Rate（请求处理速率）、Error（错误率）和 Duration（响应时间）。这是理解微服务健康状况的有效框架。

</details>

---

3. 在 Grafana 中连接 Tempo 和 Loki 以实现 trace-to-log 关联时，需要什么配置？
   - A) 使用相同的数据库
   - B) 在 Tempo 数据源中配置 tracesToLogs
   - C) 安装单独的插件
   - D) Grafana Enterprise 许可证

<details>
<summary>显示答案</summary>

**答案：B) 在 Tempo 数据源中配置 tracesToLogs**

**说明：**
在 Tempo 数据源设置中配置 tracesToLogs 部分，可从 traces 直接导航到相关日志。使用 datasourceUid 指定 Loki，并使用 tags 设置用于连接的 labels。这是 Grafana 的内置功能，无需额外插件。

</details>

---

4. USE Method 中的“U”、“S”、“E”分别代表什么？
   - A) 用户、服务、事件
   - B) 利用率、饱和度、错误
   - C) 运行时间、状态、异常
   - D) 使用率、速度、效率

<details>
<summary>显示答案</summary>

**答案：B) 利用率、饱和度、错误**

**说明：**
USE Method 是一种用于分析系统资源的方法论。它监控 Utilization（利用率）、Saturation（饱和度）和 Errors（错误）。通过分析每种资源（CPU、内存、磁盘、网络）的这三个指标，你可以识别瓶颈。

</details>

---

5. Grafana Alerting 中 evaluation interval 的作用是什么？
   - A) 告警消息传送间隔
   - B) 告警规则评估频率
   - C) 数据保留期限
   - D) Dashboard 刷新间隔

<details>
<summary>显示答案</summary>

**答案：B) 告警规则评估频率**

**说明：**
Evaluation interval 决定评估告警规则的频率。例如，将其设置为 1m 会每分钟检查一次条件。这会影响告警敏感度和资源使用情况。间隔过短会增加资源使用；间隔过长会延迟问题检测。

</details>

---

6. 以下哪项不属于 Google SRE 的 4 Golden Signals？
   - A) 延迟
   - B) 流量
   - C) 可用性
   - D) 饱和度

<details>
<summary>显示答案</summary>

**答案：C) 可用性**

**说明：**
4 Golden Signals 是 Latency、Traffic、Errors 和 Saturation。Availability 是一个重要指标，但不属于 4 Golden Signals。Availability 与 Errors 相关，但属于不同的概念。

</details>

---

7. 在 Grafana 中使用 Dashboard variables 的主要好处是什么？
   - A) 提高 Dashboard 加载速度
   - B) 通过动态筛选提高 Dashboard 的可复用性
   - C) 减少数据存储容量
   - D) 增强安全性

<details>
<summary>显示答案</summary>

**答案：B) 通过动态筛选提高 Dashboard 的可复用性**

**说明：**
使用 Dashboard variables 可以通过单个 Dashboard 监控多个集群、namespaces 和服务。当你从下拉列表中选择一个值时，所有面板查询都会动态更新。这可减少 Dashboard 的数量并简化维护。

</details>

---

8. 将 Grafana 与 Prometheus 集成时，Exemplar 功能的作用是什么？
   - A) 指标数据压缩
   - B) 关联指标和 trace 数据
   - C) 查询缓存
   - D) 数据备份

<details>
<summary>显示答案</summary>

**答案：B) 关联指标和 trace 数据**

**说明：**
Exemplar 是一项将 TraceIDs 与 Prometheus 指标关联的功能。通过在 histogram 或 counter 指标中存储示例 TraceIDs，点击 Grafana 中指标图上的特定点即可立即查询该时刻的 trace 数据。

</details>

---

9. Grafana Cloud 与 Self-hosted Grafana 之间的正确区别是什么？
   - A) Grafana Cloud 免费
   - B) Self-hosted 无法安装插件
   - C) Grafana Cloud 提供自动扩缩容和 SLA
   - D) Self-hosted 存在数据源限制

<details>
<summary>显示答案</summary>

**答案：C) Grafana Cloud 提供自动扩缩容和 SLA**

**说明：**
Grafana Cloud 是一项托管服务，提供自动扩缩容、99.9% SLA、自动更新等功能。Self-hosted 提供完全控制并允许安装所有插件，但需要进行基础设施管理。两种选项都支持各种数据源。

</details>

---

10. 使用 sidecar 进行 Grafana Dashboard provisioning 时，ConfigMap 上需要什么 label？
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>显示答案</summary>

**答案：B) grafana_dashboard: "true"**

**说明：**
使用 Grafana Helm chart 的 sidecar 功能时，需要为包含 Dashboard JSON 的 ConfigMap 添加 `grafana_dashboard: "true"` label。sidecar 容器会监视带有此 label 的 ConfigMap，并自动配置 Dashboard。

</details>

---
