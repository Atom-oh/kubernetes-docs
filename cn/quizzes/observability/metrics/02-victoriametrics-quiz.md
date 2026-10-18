# VictoriaMetrics 测验

> 复核基线：VictoriaMetrics 1.151.0 · stack chart 0.92.1

1. 将 Prometheus 查询迁移到 VictoriaMetrics 时，哪项说法正确？
   - A) 每个工作负载的压缩率都恰好提升 7 倍
   - B) 所有安装都有固定的 1 亿时间序列上限
   - C) MetricsQL 与 PromQL 有意存在差异，因此应对照实际查询进行比较
   - D) Prometheus 的数据保留时间不能超过 15 天

<details>
<summary>显示答案</summary>

**答案：C**

语法看起来熟悉，并不代表 `rate`/`increase`、NaN、标量或 API 行为完全相同。基准测试应使用实际版本、数据和硬件；默认保留设置也不等于上限。

</details>

---

2. 以下哪项不是集群存储/查询数据面的组件？
   - A) vminsert
   - B) vmstorage
   - C) vmselect
   - D) VictoriaMetrics Operator

<details>
<summary>显示答案</summary>

**答案：D**

vminsert 路由写入，vmstorage 存储数据，vmselect 执行查询。Operator 负责协调 Kubernetes 资源，是单独的控制组件。

</details>

---

3. vmagent 的作用是什么？
   - A) 替代所有持久化存储
   - B) 渲染仪表板
   - C) 收集指标并将其转发到 remote-write 目标
   - D) 替代 Alertmanager 的通知路由

<details>
<summary>显示答案</summary>

**答案：C**

它的队列可在中断期间缓冲数据，但容量有限：达到配置的磁盘上限时会丢弃队列中最旧的数据；如果使用 emptyDir，Pod 被替换时队列也会丢失。持久化和监控需要另行设计。

</details>

---

4. `keep_last_value(q)` 会做什么？使用时要注意什么？
   - A) 返回已存储的最大值
   - B) 使用较早的值填补求值时的间隔，可能掩盖遥测数据缺失
   - C) 恢复所有丢失的 scrape 样本
   - D) 保证可用性告警正常

<details>
<summary>显示答案</summary>

**答案：B**

只有在语义符合预期时才应填补间隔。保留旧的健康值可能掩盖采集缺失，因此应单独监控数据缺失。

</details>

---

5. `dedup.minScrapeInterval` 控制什么？
   - A) 目标采集器的调度间隔
   - B) 对同一时间序列，每个离散时间间隔只保留一个样本
   - C) 无损通用压缩
   - D) 告警评估频率

<details>
<summary>显示答案</summary>

**答案：B**

该间隔可能会删除合法的高分辨率样本，而不只是逐字节完全相同的副本。请根据所选存储与采集器的复制方案，协调 vmstorage 和 vmselect 的设置。

</details>

---

6. 应如何选择单节点模式或集群模式？
   - A) 始终选择集群模式
   - B) 根据负载、活跃时间序列数量/变化率、查询、保留期限和恢复要求进行评估
   - C) 将每天 1 亿个样本作为通用分界线
   - D) 单节点模式没有查询 API

<details>
<summary>显示答案</summary>

**答案：B**

应评估单机容量，以及分别扩展 insert、storage、select 的成本。仅有复制存储或两个进程，并不能证明服务具备经过验证的高可用性。

</details>

---

7. vminsert 的 `replicationFactor=2` 请求什么行为？
   - A) 总共恰好使用两个存储成员
   - B) 在不同的存储成员上保存两份副本，但实际结果取决于可用性和历史数据
   - C) 恰好由两个成员处理查询
   - D) 将压缩率提高一倍

<details>
<summary>显示答案</summary>

**答案：B**

若要在一个存储成员故障期间仍保留两份副本，至少需要三个成员，并满足相应的容量和故障域条件。请一致配置 vmselect 和去重设置；此标志不会补齐历史数据，不会让降级写入变成无损，也不能替代备份。

</details>

---

8. MetricsQL 默认运算符的作用范围是什么？
   - A) 始终创建正确的服务标签
   - B) 用右侧表达式填补缺失点；缺失数据不等于流量自动为零
   - C) 保证所有比率都具有意义
   - D) 更改指标采集间隔

<details>
<summary>显示答案</summary>

**答案：B**

不要把追加 `default 0` 当作通用错误率修复方式。请统一聚合状态标签；只有对已知的分母时间序列才填补缺失的分子，并排除零流量情况。原生 fixture 对健康、全部失败和 10% 失败的流量分别得到 0、1 和 0.1；不存在的服务或零流量服务仍保持缺失。

</details>

---

9. vmalert 负责什么？
   - A) 收集所有应用指标
   - B) 存储所有长期样本
   - C) 评估告警/记录规则，并将告警发送给已配置的 notifier
   - D) 渲染 Grafana 仪表板

<details>
<summary>显示答案</summary>

**答案：C**

必须配置规则输入/导出器、数据源 URL、状态持久化，以及 notifier/路由。重启次数高本身并不能证明发生了 CrashLoopBackOff。记录派生序列不会压缩或删除原始数据。

</details>

---

10. 正确的 vmbackup 工作流是什么？
    - A) 只备份 vminsert 配置
    - B) 从匹配的存储目录读取快照，并将其写入独立的备份目标
    - C) 不做检查就把任意 RWO PVC 挂载到任意节点
    - D) 将存储复制视为完整备份

<details>
<summary>显示答案</summary>

**答案：B**

应将每个 vmstorage 成员备份到不同的前缀，或备份预期使用的单节点存储。支持 S3、GCS、Azure 和本地目标。请核实同节点部署/PVC 身份、工作负载凭证、保留策略，并实际执行恢复验证；本地快照不是独立副本。

</details>

---

[返回学习材料](../../../observability/metrics/02-victoriametrics.md)
