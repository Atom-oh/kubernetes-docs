# CloudWatch Metrics 测验

用于测试您对 CloudWatch Metrics 理解程度的测验。

---

1. Amazon CloudWatch Container Insights 的主要功能是什么？
   - A) 构建 Container 镜像
   - B) 对 EKS 集群进行 Container/Pod 级监控
   - C) Container 编排
   - D) CI/CD pipeline 管理

<details>
<summary>显示答案</summary>

**答案：B) 对 EKS 集群进行 Container/Pod 级监控**

**说明：**
Container Insights 是 CloudWatch 的一项功能，用于监控 EKS、ECS 和 Kubernetes 环境中的 Container 化工作负载。它会自动收集并可视化集群、节点、Pod 和 Container 级别的 CPU、内存、网络和文件系统指标。

</details>

---

2. 将 CloudWatch Agent 部署到 EKS 的推荐方法是什么？
   - A) 部署为单个 Pod
   - B) 作为 DaemonSet 部署到所有节点
   - C) 使用 Deployment 部署 3 个副本
   - D) 部署为 StatefulSet

<details>
<summary>显示答案</summary>

**答案：B) 作为 DaemonSet 部署到所有节点**

**说明：**
CloudWatch Agent 以 DaemonSet 的形式部署，以便从每个节点收集指标和日志。这可确保从所有节点一致地收集系统指标、Container 指标和日志。

</details>

---

3. CloudWatch Metric Math 中 `SEARCH()` 函数的用途是什么？
   - A) 日志搜索
   - B) 动态搜索与模式匹配的指标
   - C) 告警搜索
   - D) Dashboard 搜索

<details>
<summary>显示答案</summary>

**答案：B) 动态搜索与模式匹配的指标**

**说明：**
`SEARCH()` 函数使用 namespace、dimension 和指标名称模式动态搜索指标。例如，`SEARCH('{AWS/EC2,InstanceId} MetricName="CPUUtilization"', 'Average')` 会搜索所有 EC2 实例的 CPU 利用率。

</details>

---

4. CloudWatch Anomaly Detection 如何工作？
   - A) 基于手动设置的阈值进行检测
   - B) 基于 ML 的自动异常模式检测
   - C) 日志模式分析
   - D) 网络流量分析

<details>
<summary>显示答案</summary>

**答案：B) 基于 ML 的自动异常模式检测**

**说明：**
CloudWatch Anomaly Detection 使用机器学习来学习指标的正常模式，并自动检测异常值。它会考虑季节性、趋势和每周日期模式，生成动态预期范围（band），并在值超出这些范围时识别异常。

</details>

---

5. 使用 AWS Distro for OpenTelemetry (ADOT) 将 Prometheus 指标发送到 CloudWatch 时，使用哪个 exporter？
   - A) prometheus-exporter
   - B) awsemf (AWS EMF Exporter)
   - C) cloudwatch-exporter
   - D) metric-exporter

<details>
<summary>显示答案</summary>

**答案：B) awsemf (AWS EMF Exporter)**

**说明：**
要在 ADOT 中将 Prometheus 指标发送到 CloudWatch，请使用 AWS EMF (Embedded Metric Format) Exporter。该 exporter 会将指标转换为 CloudWatch Logs 中的 EMF 格式并发送，随后 CloudWatch 将其提取为指标。

</details>

---

6. 以下哪项不是有效的 CloudWatch 成本优化方法？
   - A) 设置日志保留期
   - B) 移除不必要的高分辨率指标
   - C) 以 1 秒间隔收集所有指标
   - D) 使用 Infrequent Access 日志类别

<details>
<summary>显示答案</summary>

**答案：C) 以 1 秒间隔收集所有指标**

**说明：**
高分辨率指标（1 秒间隔）成本较高。为了进行成本优化，仅以高分辨率收集必要的指标，而大多数指标应以 60 秒间隔（默认值）收集。设置日志保留期、筛选不必要的指标以及使用 Infrequent Access 日志类别也有助于降低成本。

</details>

---

7. 在 CloudWatch 中创建自定义指标时使用哪个 API？
   - A) CreateMetric
   - B) PutMetricData
   - C) PublishMetric
   - D) SendMetric

<details>
<summary>显示答案</summary>

**答案：B) PutMetricData**

**说明：**
`PutMetricData` API 用于向 CloudWatch 发送自定义指标。您可以指定 namespace、指标名称、dimensions、值、单位、时间戳等。可以通过 AWS SDK 或 CLI 调用它。

</details>

---

8. Dimensions 在 CloudWatch 中的作用是什么？
   - A) 指定指标单位
   - B) 用于细分指标的键值对
   - C) 指定告警严重性
   - D) 指定日志组

<details>
<summary>显示答案</summary>

**答案：B) 用于细分指标的键值对**

**说明：**
Dimensions 是用于细分和标识指标的键值对。例如，在 EC2 实例指标中，`InstanceId` dimension 用于标识特定实例。单个指标最多可以指定 30 个 dimensions。

</details>

---

9. Enhanced Container Insights 与基础 Container Insights 有何不同？
   - A) 免费提供
   - B) 提供额外指标和更详细的监控
   - C) 移除日志收集功能
   - D) 仅提供告警功能

<details>
<summary>显示答案</summary>

**答案：B) 提供额外指标和更详细的监控**

**说明：**
Enhanced Container Insights 收集的指标比基础 Container Insights 更多。它提供预留 CPU/内存容量、GPU 指标（如适用）以及 Kubernetes control plane 指标等额外信息。虽然成本更高，但可实现更详细的监控。

</details>

---

10. `ANOMALY_DETECTION_BAND()` 函数在 CloudWatch 告警中的作用是什么？
    - A) 设置固定阈值
    - B) 返回异常检测模型的预期范围
    - C) 日志筛选
    - D) 创建 Dashboard

<details>
<summary>显示答案</summary>

**答案：B) 返回异常检测模型的预期范围**

**说明：**
`ANOMALY_DETECTION_BAND()` 函数返回由异常检测模型学习到的预期值范围（上限/下限）。该范围可用于告警，以便在指标超出预期范围时触发通知。第二个参数指定用于调整 band 宽度的标准差乘数。

</details>
