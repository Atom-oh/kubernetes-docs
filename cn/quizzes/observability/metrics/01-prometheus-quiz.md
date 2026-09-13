# Prometheus 测验

> **最后更新**: September 12, 2026

1. Prometheus 的常规指标采集路径是什么？

   - A) 应用程序必须直接推送每个样本
   - B) Prometheus 通过 HTTP 抓取已配置的目标
   - C) 仅使用流式事件日志
   - D) 仅使用定期 CSV 导入

<details>
<summary>显示答案</summary>

**答案：B**

常规路径是拉取/抓取。remote write 和可选的批处理集成提供了其他传递路径。up 报告的是抓取成功，而非完整的应用程序可用性。

</details>

2. 哪个表达式能给出 Counter 在五分钟内的每秒平均速率？

   - A) `rate(http_requests_total, 5m)`
   - B) `rate(http_requests_total[5m])`
   - C) `increase(http_requests_total[5m])`
   - D) `avg(http_requests_total[5m])`

<details>
<summary>显示答案</summary>

**答案：B**

rate() 使用范围向量，并处理观察到的重置/外推。increase() 估算总增量，而不是每秒速率。应先应用 rate 再进行聚合，并且不要将其理解为恢复每一次遗漏的增量。

</details>

3. 一个可正常工作的 ServiceMonitor 必须描述什么？

   - A) 一个 Grafana 仪表板
   - B) 仅一个 Prometheus 容器镜像
   - C) 已选择的 Service 和抓取端点，其 selectors/端口名称与 Prometheus 设置匹配
   - D) 一个完整的应用程序 Deployment

<details>
<summary>显示答案</summary>

**答案：C**

Prometheus 首先选择监控器的 namespace 和标签；监控器会选择目标 Service。其端点端口是 Service 端口名称。RBAC、TLS/网络访问以及已埋点的应用程序是额外要求。

</details>

4. histogram_quantile() 对经典直方图返回什么？

   - A) 精确的 Summary 百分位数
   - B) 基于桶的分位数估计
   - C) 独立于桶分辨率的精确百分位数
   - D) Counter 的请求速率

<details>
<summary>显示答案</summary>

**答案：B**

在保留 le 的同时聚合兼容的经典桶。结果会在桶内进行插值。Summary 分位数同样具有依赖算法/窗口的误差，且无法平均为整个集群的百分位数。

</details>

5. 哪个组件不属于 kube-prometheus-stack 软件包？

   - A) Prometheus Operator
   - B) Grafana
   - C) VictoriaMetrics
   - D) Alertmanager

<details>
<summary>显示答案</summary>

**答案：C**

该 chart 打包了 Prometheus/Alertmanager、Operator、Grafana 和 exporters，具体取决于已启用的 values。VictoriaMetrics 是独立的 Deployment。应固定所检查的 chart 组，而不要混用任意镜像版本。

</details>

6. remote write 的用途是什么？

   - A) 发送 Alertmanager 通知
   - B) 将样本异步传递给已配置的外部接收器
   - C) 保证无限的故障缓冲
   - D) 同步 Grafana 仪表板

<details>
<summary>显示答案</summary>

**答案：B**

接收器包括 AMP、VictoriaMetrics 和 Mimir。每个接收器都有自己的端点、身份、配额和 HA 合约。WAL 缓冲是有限的，本地 Prometheus 保留期本身可配置，而不是普遍限制为 30 天。

</details>

7. 告警规则的 for 持续时间控制什么？

   - A) 指标保留期
   - B) 相同告警条件/标签集在触发前保持 pending 状态的时长
   - C) Alertmanager 的重复间隔
   - D) Prometheus 副本数量

<details>
<summary>显示答案</summary>

**答案：B**

对于该告警身份，条件必须在多次评估期间持续满足。缺失数据或标签变化可能会中断 pending 状态。通知分组和时间安排是独立的 Alertmanager 设置。

</details>

8. 应如何解读 predict_linear()？

   - A) 有保证的磁盘故障截止时间
   - B) 拟合后外推至未来的 Gauge 趋势
   - C) 季节性三重指数预测
   - D) 所有容量测量的替代方案

<details>
<summary>显示答案</summary>

**答案：B**

它预测观察到的线性趋势。工作负载变化、清理、稀疏数据和非线性行为都可能使其失效。旧的 holt_winters 名称在 Prometheus 3 中被一个明确标记为实验性的双指数平滑函数所替代；它不是季节性模型。

</details>

9. AlertmanagerConfig 的 groupBy 有什么作用？

   - A) 自动授权来自每个 namespace 的告警
   - B) 按选定标签对通知进行分组
   - C) 定义 Prometheus 的 for 持续时间
   - D) 使每个匹配的同级路由都运行

<details>
<summary>显示答案</summary>

**答案：B**

groupBy 在原生配置中变为 group_by。除非配置了 continue，否则路由通常会在第一个同级匹配项处停止。抑制需要有意义的资源身份相等标签，以避免抑制无关的 Service/node 警告。

</details>

10. TSDB WAL 提供什么？

   - A) 查询结果缓存
   - B) 支持在持久化为块之前进行崩溃恢复的顺序记录
   - C) 在丢失卷后仍可存活的备份
   - D) 无限的 remote-write 传递队列

<details>
<summary>显示答案</summary>

**答案：B**

WAL 重放是一种持久性机制，并不承诺在损坏、卷故障或长期远程中断的情况下零数据丢失。保留期以及 WAL/head/compaction 的磁盘要求是独立的；应保留经过验证的备份和恢复流程。

</details>

[返回指南](../../../observability/metrics/01-prometheus.md)
