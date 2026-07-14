# 日志概述测验

测试你对日志基本概念的理解。

---

1. 以下哪项不是结构化日志记录的主要优势？

   - A) 提高搜索和筛选效率
   - B) 减小日志文件大小
   - C) 一致的日志格式
   - D) 与自动化分析工具兼容

<details>
<summary>显示答案</summary>

**答案：B) 减小日志文件大小**

**解释：**
结构化日志记录（尤其是 JSON 格式）实际上可能会比非结构化文本日志产生更大的文件大小。这是因为增加了字段名称和分隔符。结构化日志记录的真正优势在于搜索效率、一致性以及与自动化工具的兼容性。

</details>

---

2. 生产环境推荐使用哪种日志级别？

   - A) DEBUG
   - B) TRACE
   - C) INFO 或 WARN
   - D) FATAL

<details>
<summary>显示答案</summary>

**答案：C) INFO 或 WARN**

**解释：**
生产环境推荐使用 INFO 或 WARN 级别。DEBUG 或 TRACE 过于冗长，会导致日志量过大，而仅使用 FATAL 则可能遗漏重要的运行信息。

</details>

---

3. Kubernetes 中最推荐的日志收集模式是什么？

   - A) 基于文件的日志记录 + Sidecar
   - B) stdout/stderr + DaemonSet agent
   - C) 直接传输到远程日志服务器
   - D) 使用本地文件存储并手动收集

<details>
<summary>显示答案</summary>

**答案：B) stdout/stderr + DaemonSet agent**

**解释：**
在 Kubernetes 中，标准方法是让容器将日志输出到 stdout/stderr，并由以 DaemonSet 部署的 agent 从节点上的 `/var/log/containers/` 收集日志。这种方法具有与 kubectl logs 命令兼容、自动轮换以及无需单独卷等优点。

</details>

---

4. 当日志存储选择的最高优先级是“成本优化”时，推荐使用哪种解决方案？

   - A) Amazon OpenSearch Service
   - B) CloudWatch Logs
   - C) Grafana Loki + S3
   - D) EC2 上的 Elasticsearch

<details>
<summary>显示答案</summary>

**答案：C) Grafana Loki + S3**

**解释：**
Loki 仅对标签建立索引，而不对日志内容建立索引，因此可显著降低存储成本。使用 S3 作为后端时，存储成本最低可达每 GB $0.023。

</details>

---

5. 在分布式追踪中，JSON 日志格式必须包含哪些字段？

   - A) user_id, session_id
   - B) trace_id, span_id
   - C) request_id, response_time
   - D) level, message

<details>
<summary>显示答案</summary>

**答案：B) trace_id, span_id**

**解释：**
对于分布式追踪，必须包含 trace_id（追踪整个请求）和 span_id（标识单个操作）。这些字段可用于追踪请求在多个 Service 间的流转。

</details>

---

6. 以下哪项不是日志收集管道中“处理层”的职责？

   - A) 日志解析和规范化
   - B) 添加 Kubernetes 元数据
   - C) 日志存储和索引
   - D) 筛选和采样

<details>
<summary>显示答案</summary>

**答案：C) 日志存储和索引**

**解释：**
日志存储和索引属于“存储层”的职责。处理层负责解析、添加元数据、筛选、缓冲等工作。

</details>

---

7. 为满足金融监管合规要求，推荐的日志保留期限是多久？

   - A) 30 天
   - B) 1 年
   - C) 7 年
   - D) 90 天

<details>
<summary>显示答案</summary>

**答案：C) 7 年**

**解释：**
对于金融监管合规（例如与 SOX、PCI-DSS 相关的要求），通常建议将日志保留 7 年。医疗保健（HIPAA）要求保留 6 年，而一般运行日志通常需要保留约 1 年。

</details>

---

8. 何时应使用 Sidecar 模式收集日志？

   - A) 所有标准 Kubernetes 工作负载
   - B) 当旧版应用程序仅将日志输出到文件时
   - C) CPU 资源受限的环境
   - D) 仅单容器 Pod

<details>
<summary>显示答案</summary>

**答案：B) 当旧版应用程序仅将日志输出到文件时**

**解释：**
Sidecar 模式用于旧版应用程序（使用文件日志记录而非 stdout/stderr）、多租户环境中的日志隔离，以及需要特殊日志格式处理的情况。由于它存在资源开销，对于标准工作负载，DaemonSet 方法效率更高。

</details>

---

9. 哪种日志存储解决方案在查询性能和全文搜索方面都“出色”？

   - A) Grafana Loki
   - B) CloudWatch Logs
   - C) Amazon OpenSearch Service
   - D) ClickHouse

<details>
<summary>显示答案</summary>

**答案：C) Amazon OpenSearch Service**

**解释：**
OpenSearch（Elasticsearch 的分支）同时支持基于 Lucene 的强大全文搜索功能和复杂的聚合查询。Loki 的全文搜索能力有限，而 CloudWatch 和 ClickHouse 的全文搜索能力适中。

</details>

---

10. 在 EKS control plane logging 中，为进行安全审计必须启用哪种日志类型？

    - A) scheduler
    - B) controllerManager
    - C) audit
    - D) api

<details>
<summary>显示答案</summary>

**答案：C) audit**

**解释：**
审计日志会记录对 Kubernetes API server 的所有请求。它们对于安全审计和监管合规至关重要，因为可以追踪谁在何时执行了什么操作。API 日志也很重要，但对于安全审计而言，audit 是最关键的。

</details>

---
