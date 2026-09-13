# Prometheus Alertmanager 测验

> **最后更新**: September 13, 2026

---

1. 当 Prometheus 告警规则具有正的 `for` 持续时间时，Firing 之前的状态是什么？
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>显示答案</summary>

**答案：B) Pending**

Pending 属于 Prometheus 规则评估，而不是 Alertmanager 评估阶段。该条件必须在连续评估中持续存在达到配置的时长。未设置 `for`（或将其设为零）时，它可以在首次匹配的评估中触发。通知分组会增加单独的延迟；`keep_firing_for` 可以在表达式不再匹配后保持 Firing 状态。

</details>

---

2. 关于分组计时器，哪项说法正确？
   - A) `group_wait` 会延迟新分组的第一条通知。
   - B) `group_interval` 仅是未变化告警的重复间隔。
   - C) `repeat_interval` 是新加入告警的首次延迟。
   - D) 三个计时器完全相同。

<details>
<summary>显示答案</summary>

**答案：A) `group_wait` 会延迟新分组的第一条通知。**

`group_interval` 会安排后续的分组检查，其中包括变更和已解决的告警。`repeat_interval` 控制未变化且处于 Firing 状态的告警的重复通知，并在分组间隔时进行检查；应使用 `group_interval` 的倍数。通知日志保留可能导致更早的重复通知。这些计时器独立于 Prometheus 规则的 `for`。

</details>

---

3. 抑制（inhibition）的作用是什么？
   - A) 在一个时间窗口内忽略每条告警。
   - B) 当匹配的源告警处于活动状态时，抑制匹配目标的通知。
   - C) 自动更改告警严重级别。
   - D) 从 Prometheus 中删除重复告警。

<details>
<summary>显示答案</summary>

**答案：B) 当匹配的源告警处于活动状态时，抑制匹配目标的通知。**

抑制改变的是通知资格，而非底层告警条件。源/目标匹配器和相等标签必须表示预期的依赖关系。缺失的相等标签会像空值一样比较，因此应要求使用非空的关联标签，例如 `cluster` 和 `node`，以避免抑制无关告警。规则列表顺序不是优先级系统。

</details>

---

4. 此规则中的 `for` 表示什么？

   ```yaml
   - alert: HighCPU
     expr: 100 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100 > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) CPU 超过 80% 时立即通知。
   - B) 当条件在多次评估中持续五分钟后进入 Firing 状态。
   - C) 每五分钟才评估一次 CPU。
   - D) 保证在物理 CPU 使用率升高后的恰好五分钟时送达通知。

<details>
<summary>显示答案</summary>

**答案：B) 当条件在多次评估中持续五分钟后进入 Firing 状态。**

这假定已抓取 node-exporter CPU 计数器，并且评估间隔合适。`for` 不设置抓取/评估间隔，也不保证通知送达期限。变更后的标签集会标识不同的告警；除非应用了单独的 Firing 保留行为，否则恢复会重置 Pending。CrashLoop 示例首先使用五分钟观测窗口，然后使用 `for: 10m`：这可以跨越重试间隙并排除一次性的等待，同时会有与回溯相关的清除延迟。

</details>

---

5. `send_resolved: true` 启用了什么？
   - A) 此集成的解决通知。
   - B) 自动修复说明。
   - C) 将告警条件更改为健康状态。
   - D) 授予接收器修复 cluster 的权限。

<details>
<summary>显示答案</summary>

**答案：A) 此集成的解决通知。**

它控制所选集成的已解决通知；不同接收器的默认值有所不同。Resolved 是告警生命周期状态，并非 Service 已恢复的独立证据。表达式更改、数据缺失或客户端更新/过期行为也会影响该状态。

</details>

---

6. Alertmanager cluster 状态同步使用哪种协议？
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>显示答案</summary>

**答案：C) Gossip**

Gossip 通过最终一致性共享静默和通知日志状态。应将相同的告警发送到每个副本；Gossip 层不能取代这种扇出。去重是尽力而为的，网络分区可能产生重复通知。这并非恰好一次交付，也不能保证避免所有通知丢失。

</details>

---

7. 对于 `severity=critical, team=infra`，下面会选择哪个路由？

   ```yaml
   route:
     receiver: default
     routes:
       - matchers: ['severity="critical"']
         receiver: critical-receiver
       - matchers: ['team="infra"']
         receiver: infra-team
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) 两个子路由

<details>
<summary>显示答案</summary>

**答案：B) critical-receiver**

默认的 `continue: false` 会使第一个匹配的同级路由停止同级遍历。对其设置 `continue: true` 可继续考虑后续同级路由。此题仅测试标签路由：未激活/被静音的路由仍可能停止遍历，因此时间窗口行为需要单独检查。一个接收器中的多个集成不需要 `continue`。Provider 目标规则仍然适用：Slack incoming-webhook URL 与 channel 绑定，因此普通和关键 channel 需要不同的 webhook 文件/Secret 键，而不是 channel 覆盖。

</details>

---

8. 由 namespace 拥有的 AlertmanagerConfig 能实现什么？
   - A) 自动绕过所有 namespace 限制。
   - B) 管理由 Alertmanager 实例选择的结构化路由/接收器。
   - C) 定义 PromQL 记录和告警规则。
   - D) 替换 Gossip peer 配置。

<details>
<summary>显示答案</summary>

**答案：B) 管理由 Alertmanager 实例选择的结构化路由/接收器。**

Operator 必须选择对象的标签和 namespace，且被引用的 Secret 必须存在于所需 namespace 中。其匹配器策略控制 namespace 强制执行。已审查的 Operator 0.93.1 chart 提供 `v1alpha1`；不要虚构必需的 API 升级。全局配置使用是另一个选项，而 namespace 标签匹配并不是对告警发送方的身份验证。

</details>

---

9. 哪项不是 Silence 的适当用途？
   - A) 计划内维护。
   - B) 有界的调查窗口。
   - C) 永久禁用一条告警规则。
   - D) 经审核的 Deployment 窗口。

<details>
<summary>显示答案</summary>

**答案：C) 永久禁用一条告警规则。**

静默必须有有限的结束时间，并且会影响通知。过期会结束抑制；并不会立即从已存储的静默历史中删除。永久性的规则/路由变更需要单独审核。记录负责人、原因和获批范围；到期提醒需要明确配置的工作流。

</details>

---

10. 哪个表达式是无效的 Go template 语法？
   - A) `{{ .CommonLabels.alertname }}`
   - B) `{{ if eq .Status "firing" }}Danger{{ end }}`
   - C) `{{ range .Alerts }}{{ .Labels.severity }}{{ end }}`
   - D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`

<details>
<summary>显示答案</summary>

**答案：D) `{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}`**

Go template 不支持此三元表达式。在根级别，Alertmanager 提供带有 CommonLabels/CommonAnnotations 的 Data；Labels/Annotations/StartsAt 属于 `range .Alerts` 内的单个 Alert。下面的示例会为每个 description 最多格式化 100 个 rune，避免按字节切片而可能拆分韩文文本。这是输出格式化，而不是敏感数据脱敏。

```text
{{ range .Alerts }}
{{ printf "%.100s" .Annotations.description }}
{{ end }}
```

</details>

---

<span id="附加学习资源"></span>

## 补充学习资源

- [Alertmanager 0.34 配置](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/configuration.md)
- [通知模板参考](https://github.com/prometheus/alertmanager/blob/v0.34.0/docs/notifications.md)
- [Prometheus Operator 告警](https://prometheus-operator.dev/docs/developer/alerting/)

[返回指南](../../../observability/alerting/01-alertmanager.md)
