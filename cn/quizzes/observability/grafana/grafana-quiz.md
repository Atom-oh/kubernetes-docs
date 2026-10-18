# Grafana 仪表板测验

> **最后更新**: 2026 年 9 月 13 日

测试您对 Grafana 13.2.1 配置和运维的理解。

---

1. 以下哪项**不是** Grafana 中用于配置数据源的方法？
   - A) 配合边车容器（sidecar）的 ConfigMap
   - B) Grafana API
   - C) 环境变量
   - D) provisioning 目录

<details>
<summary>显示答案</summary>

**答案：C) 环境变量**

**说明：**
Grafana 数据源可以通过 provisioning 目录中的 YAML 文件、使用 ConfigMap 的边车容器方案或 Grafana API 进行配置。环境变量可以提供 grafana.ini 设置，以及数据源 provisioning YAML 中的 URL 或凭证等值。变量本身不会创建数据源对象。

</details>

---

2. 在 RED 方法中，“R”“E”“D”分别代表什么？
   - A) Resource（资源）、Error（错误）、Duration（持续时间）
   - B) Rate（速率）、Error（错误）、Duration（持续时间）
   - C) Request（请求）、Exception（异常）、Delay（延迟）
   - D) Response（响应）、Event（事件）、Data（数据）

<details>
<summary>显示答案</summary>

**答案：B) Rate（速率）、Error（错误）、Duration（持续时间）**

**说明：**
RED 方法是一种用于分析服务级指标的方法论。它监控三个关键指标：Rate（请求处理速率）、Error（错误率）和 Duration（响应时间）。这是理解微服务健康状况的有效框架。

</details>

---

3. 在 Grafana 中连接 Tempo 和 Loki 以实现追踪与日志关联时，需要什么配置？
   - A) 使用同一个数据库
   - B) 在 Tempo 数据源中配置 tracesToLogsV2
   - C) 安装单独的插件
   - D) Grafana Enterprise 许可证

<details>
<summary>显示答案</summary>

**答案：B) 在 Tempo 数据源中配置 tracesToLogsV2**

**说明：**
在 Tempo 数据源设置中配置 tracesToLogsV2 部分后，可以从追踪直接导航到相关日志。使用 datasourceUid 指定 Loki，并通过 tags 将实际追踪属性映射到 Loki 标签。trace_id 等日志字段必须与管道约定相匹配。这是 Grafana 的内置功能，不需要额外插件。

</details>

---

4. 在 USE 方法中，“U”“S”“E”分别代表什么？
   - A) User（用户）、Service（服务）、Event（事件）
   - B) Utilization（利用率）、Saturation（饱和度）、Errors（错误）
   - C) Uptime（正常运行时间）、Status（状态）、Exceptions（异常）
   - D) Usage（使用量）、Speed（速度）、Efficiency（效率）

<details>
<summary>显示答案</summary>

**答案：B) Utilization（利用率）、Saturation（饱和度）、Errors（错误）**

**说明：**
USE 方法是一种用于分析系统资源的方法论。它监控 Utilization（利用率）、Saturation（饱和度）和 Errors（错误）。通过分析每种资源（CPU、内存、磁盘、网络）的这三个指标，您可以识别瓶颈。

</details>

---

5. Grafana Alerting 中评估间隔的作用是什么？
   - A) 告警消息发送间隔
   - B) 告警规则评估频率
   - C) 数据保留期限
   - D) 仪表板刷新间隔

<details>
<summary>显示答案</summary>

**答案：B) 告警规则评估频率**

**说明：**
评估间隔决定告警规则的评估频率。例如，将其设置为 1m 会每分钟检查一次条件。这会影响告警敏感度和资源使用情况。间隔过短会增加资源使用；间隔过长会延迟问题检测。

</details>

---

6. 以下哪项未包含在 Google SRE 的 4 Golden Signals 中？
   - A) 延迟
   - B) 流量
   - C) 可用性
   - D) 饱和度

<details>
<summary>显示答案</summary>

**答案：C) 可用性**

**说明：**
4 Golden Signals 是 Latency（延迟）、Traffic（流量）、Errors（错误）和 Saturation（饱和度）。Availability（可用性）是一项重要指标，但不包含在 4 Golden Signals 中。Availability 与 Errors 相关，但属于独立的概念。

</details>

---

7. 在 Grafana 中使用仪表板变量的主要好处是什么？
   - A) 提高仪表板加载速度
   - B) 通过动态筛选提高仪表板的可复用性
   - C) 减少数据存储容量
   - D) 增强安全性

<details>
<summary>显示答案</summary>

**答案：B) 通过动态筛选提高仪表板的可复用性**

**说明：**
使用仪表板变量可以通过一个仪表板监控多个集群、命名空间和服务。当您从下拉列表中选择一个值时，所有面板查询都会动态更新。这能减少仪表板数量并简化维护。

</details>

---

8. 将 Grafana 与 Prometheus 集成时，Exemplar 功能的作用是什么？
   - A) 指标数据压缩
   - B) 关联指标和追踪数据
   - C) 查询缓存
   - D) 数据备份

<details>
<summary>显示答案</summary>

**答案：B) 关联指标和追踪数据**

**说明：**
Exemplar 将选定的指标观测结果关联到 TraceID；它们不会捕获每一个请求。通过在直方图或计数器指标中存储样本 TraceID，单击 Grafana 中指标图表上的特定点后，您便可立即查询当时的追踪数据。

</details>

---

9. Grafana Cloud 与自托管 Grafana 的一项正确区别是什么？
   - A) Grafana Cloud 免费
   - B) 自托管 Grafana 无法安装插件
   - C) Grafana Cloud 是托管服务，其 SLA 取决于合同
   - D) 自托管 Grafana 存在数据源限制

<details>
<summary>显示答案</summary>

**答案：C) Grafana Cloud 是托管服务，其 SLA 取决于合同**

**说明：**
请查看实际的 Cloud 套餐和服务协议，以了解其 SLA、使用限制和功能。自托管版本的运维人员负责管理数据库、备份、升级以及插件兼容性/签名策略。不要假设每个 Cloud 套餐都适用固定的 99.9% SLA。

</details>

---

10. 本章的边车配置方案（label=grafana_dashboard, labelValue="true"）会选择哪个 ConfigMap 标签？
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>显示答案</summary>

**答案：B) grafana_dashboard: "true"**

**说明：**
此配置方案选择 `grafana_dashboard: "true"`。label 和 labelValue 均可配置，并非 Grafana 的通用要求。可选配置方案仅监视 monitoring 命名空间中的 ConfigMap。

</details>

---
