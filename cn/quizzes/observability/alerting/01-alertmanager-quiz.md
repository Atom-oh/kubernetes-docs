# Prometheus Alertmanager 测验

用于测试您对 Prometheus Alertmanager 理解程度的测验。

---

1. 在 Alertmanager 中，告警在触发前会经历的中间状态是什么？
   - A) Active
   - B) Pending
   - C) Warning
   - D) Waiting

<details>
<summary>显示答案</summary>

**答案：B) Pending**

**说明：**
Prometheus 告警有三种状态：Inactive、Pending 和 Firing。当告警规则的条件（expr）满足时，告警会先转换为 Pending 状态；如果该条件在 `for` 子句指定的时长内持续满足，告警将转换为 Firing 状态并发送至 Alertmanager。该机制可避免因临时峰值产生不必要的告警。

</details>

---

2. 下列哪项正确描述了 Alertmanager 路由配置中 `group_wait`、`group_interval` 和 `repeat_interval` 的作用？
   - A) group_wait：发送告警组的第一条通知前的等待时间
   - B) group_interval：重新发送相同告警的间隔
   - C) repeat_interval：向组中添加新告警时的等待时间
   - D) 三者执行相同的功能

<details>
<summary>显示答案</summary>

**答案：A) group_wait：发送告警组的第一条通知前的等待时间**

**说明：**
- `group_wait`：创建新的告警组后，发送第一条通知前的等待时间。在此期间，属于同一组的其他告警会被收集并一同发送。
- `group_interval`：当同一组中添加新告警时，发送下一条通知前的等待时间。
- `repeat_interval`：同一告警尚未解决时重新发送该告警的间隔。

</details>

---

3. 下列哪项正确描述了 Alertmanager 的 Inhibition 功能？
   - A) 在特定时间段内忽略所有告警的功能
   - B) 特定告警触发时抑制相关告警的功能
   - C) 自动降低告警严重程度的功能
   - D) 合并重复告警的功能

<details>
<summary>显示答案</summary>

**答案：B) 特定告警触发时抑制相关告警的功能**

**说明：**
Inhibition 是一种功能，当特定条件告警（source）触发时，会抑制相关告警（target）。例如，当某个节点宕机时，可以抑制来自该节点的所有与 Pod 相关的告警，以防止告警风暴。Silencing 是一项独立功能，用于在特定时间段内忽略告警。

</details>

---

4. PrometheusRule CRD 中的以下告警规则表示什么含义？
   ```yaml
   - alert: HighCPU
     expr: node_cpu_usage > 80
     for: 5m
     labels:
       severity: warning
   ```
   - A) CPU 使用率超过 80% 时立即触发告警
   - B) CPU 使用率连续 5 分钟超过 80% 时触发告警
   - C) 每 5 分钟检查一次 CPU 使用率，若超过 80% 则触发告警
   - D) CPU 超过 80% 后 5 分钟发送告警通知

<details>
<summary>显示答案</summary>

**答案：B) CPU 使用率连续 5 分钟超过 80% 时触发告警**

**说明：**
`for: 5m` 设置表示，告警条件（expr）必须连续满足 5 分钟，才会转换为 Firing 状态。首次满足条件时，状态会变为 Pending；如果条件持续满足 5 分钟，则转换为 Firing 并发送至 Alertmanager。该机制可避免因临时峰值产生不必要的告警。

</details>

---

5. Alertmanager 的 receiver 配置中的 `send_resolved: true` 表示什么？
   - A) 同时将已解决的告警发送给 receiver
   - B) 在告警消息中包含解决方法
   - C) 自动将告警更改为已解决状态
   - D) 授予 receiver 解决告警的权限

<details>
<summary>显示答案</summary>

**答案：A) 同时将已解决的告警发送给 receiver**

**说明：**
`send_resolved: true` 设置会在告警解决时（条件不再满足时）向 receiver 发送解决通知。这使响应人员能够知道问题已经解决。默认值因 receiver 类型而异，但通常建议启用此设置。

</details>

---

6. 在 Alertmanager 高可用配置中，集群成员之间使用什么协议同步状态？
   - A) Raft
   - B) Paxos
   - C) Gossip
   - D) gRPC

<details>
<summary>显示答案</summary>

**答案：C) Gossip**

**说明：**
Alertmanager 集群使用 Gossip 协议在成员之间同步状态。这使 Silence 信息和通知日志（nflog）能够在所有实例之间共享，从而防止重复的告警通知。配置集群时，请使用 `--cluster.peer` 标志指定其他成员。

</details>

---

7. 在以下 Alertmanager 路由配置中，`severity=critical` 且 `team=infra` 的告警会发送给哪个 receiver？
   ```yaml
   route:
     receiver: 'default'
     routes:
       - match:
           severity: critical
         receiver: 'critical-receiver'
       - match:
           team: infra
         receiver: 'infra-team'
   ```
   - A) default
   - B) critical-receiver
   - C) infra-team
   - D) critical-receiver 和 infra-team 两者

<details>
<summary>显示答案</summary>

**答案：B) critical-receiver**

**说明：**
Alertmanager 路由以树形结构运行，默认情况下在第一个匹配的路由处结束处理。在此示例中，`severity=critical` 条件最先匹配，因此告警会发送至 `critical-receiver`。要发送至多个路由，需要使用 `continue: true` 设置。

</details>

---

8. AlertmanagerConfig CRD 的主要目的是什么？
   - A) 定义 Alertmanager 的全局配置
   - B) 按 namespace 分离告警配置
   - C) 定义 Prometheus 告警规则
   - D) 配置 Alertmanager 集群

<details>
<summary>显示答案</summary>

**答案：B) 按 namespace 分离告警配置**

**说明：**
AlertmanagerConfig CRD 是 Prometheus Operator 提供的资源，可按 namespace 分别管理 Alertmanager 配置（receivers、routes、inhibition rules 等）。这样，每个团队都可以在自己的 namespace 中独立管理告警配置。

</details>

---

9. 以下哪项不是在 Alertmanager 中创建 Silence 的适当使用场景？
   - A) 在计划维护期间抑制告警
   - B) 防止已知问题的重复告警
   - C) 永久禁用特定告警
   - D) 在 Deployment 期间抑制告警

<details>
<summary>显示答案</summary>

**答案：C) 永久禁用特定告警**

**说明：**
Silence 是一项临时抑制告警的功能，并且必须始终指定结束时间。要永久禁用告警，需要修改或删除告警规则本身。Silence 的主要使用场景是维护、Deployment 或调查已知问题等临时情况。

</details>

---

10. 以下哪项不是可在 Alertmanager 模板中使用的有效 Go template 语法？
    - A) <code v-pre>{{ .Labels.alertname }}</code>
    - B) <code v-pre>{{ if eq .Status "firing" }}Danger{{ end }}</code>
    - C) <code v-pre>{{ range .Alerts }}{{ .Labels.severity }}{{ end }}</code>
    - D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>

<details>
<summary>显示答案</summary>

**答案：D) <code v-pre>{{ .Annotations.description | length > 100 ? substring(0, 100) : .Annotations.description }}</code>**

**说明：**
Go template 不支持三元运算符（`? :`）。应使用 <code v-pre>{{ if }}</code> 语句。正确语法如下：
```
{{ if gt (len .Annotations.description) 100 }}
  {{ slice .Annotations.description 0 100 }}...
{{ else }}
  {{ .Annotations.description }}
{{ end }}
```
Go template 支持管道（`|`）、条件语句（`if`/`else`）、循环（`range`）、内置函数等。

</details>

---

## 附加学习资源

- [Prometheus 告警文档](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Alertmanager 配置](https://prometheus.io/docs/alerting/latest/configuration/)
- [Prometheus Operator - AlertmanagerConfig](https://prometheus-operator.dev/docs/user-guides/alerting/)
