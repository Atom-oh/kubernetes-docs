# Grafana OnCall 测验

用于测试您对 Grafana OnCall 理解程度的测验。

---

1. 以下哪项**不是** Grafana OnCall 的核心功能？
   - A) 值班排班管理
   - B) 升级链配置
   - C) 指标收集与存储
   - D) ChatOps 集成 (Slack, Teams)

<details>
<summary>显示答案</summary>

**答案：C) 指标收集与存储**

**说明：**
Grafana OnCall 是一款值班管理和事件响应工具，提供以下功能：
- 值班排班管理（轮换、替班）
- 升级链配置
- Alert 分组与路由
- ChatOps 集成 (Slack, MS Teams, Telegram)
- 移动应用通知

指标收集与存储是 Prometheus 或 Grafana Mimir 等其他工具的职责。OnCall 接收并处理由这些工具生成的 Alert。

</details>

---

2. Grafana OnCall 升级策略中的 `wait` 类型有什么作用？
   - A) 在发送 Alert 前等待数据收集完成
   - B) 在进入下一个升级步骤前等待
   - C) 等待用户响应后自动解决
   - D) 等待 Alert 分组

<details>
<summary>显示答案</summary>

**答案：B) 在进入下一个升级步骤前等待**

**说明：**
在升级链中，`wait` 类型用于设置当前步骤与下一步骤之间的等待时间。例如：
1. 步骤 1：通知当前值班响应人员
2. 步骤 2：wait 900 秒（15 分钟）
3. 步骤 3：若无响应，通知次级响应人员

这样可为主要响应人员留出响应时间，只有在未收到响应时才会继续升级。

</details>

---

3. Grafana OnCall 值班排班中的“替班”是什么？
   - A) 完全删除并重新创建排班
   - B) 在现有排班中临时更改特定时间段的响应人员
   - C) 更改排班的时区
   - D) 修改轮换周期

<details>
<summary>显示答案</summary>

**答案：B) 在现有排班中临时更改特定时间段的响应人员**

**说明：**
替班是指在常规值班排班中，临时更改特定时间段响应人员的功能。主要使用场景包括：
- 因休假更换响应人员
- 因紧急情况临时变更
- 因培训/会议临时调换

替班会在维持现有排班的同时，为特定时间段指定不同的响应人员。

</details>

---

4. 将 Grafana OnCall 与 Alertmanager 集成时使用什么方法？
   - A) Alertmanager 直接收集 OnCall 的指标
   - B) 通过 Alertmanager 的 webhook_configs 向 OnCall 发送 Alert
   - C) OnCall 定期轮询 Alertmanager 的 API
   - D) 两个系统共享数据库

<details>
<summary>显示答案</summary>

**答案：B) 通过 Alertmanager 的 webhook_configs 向 OnCall 发送 Alert**

**说明：**
Alertmanager 与 Grafana OnCall 通过 webhook 集成：
```yaml
receivers:
  - name: 'grafana-oncall'
    webhook_configs:
      - url: 'https://oncall.example.com/api/v1/webhook/<integration-id>/'
        send_resolved: true
```

当 Alertmanager 触发 Alert 时，它会向已配置的 webhook URL 发送 HTTP POST 请求，OnCall 将接收并处理该请求。

</details>

---

5. Grafana OnCall 中 Alert 分组的主要目的是什么？
   - A) 按时间排序 Alert
   - B) 将相关 Alert 分组为一个，以减少 Alert 疲劳
   - C) 按严重程度分类 Alert
   - D) 自动删除重复 Alert

<details>
<summary>显示答案</summary>

**答案：B) 将相关 Alert 分组为一个，以减少 Alert 疲劳**

**说明：**
Alert 分组会将由同一问题引起的多个 Alert 作为一个组进行管理。例如，如果因 Node 故障发生多个 Pod Alert，它们会被归为一组，因此响应人员只会收到一个分组 Alert，而不是数十个单独的 Alert。通过定义分组键（例如 alertname + namespace）来确定哪些 Alert 应归为一组。

</details>

---

6. 当 Grafana OnCall 升级策略中 `notify_on_call_from_schedule` 的 `important` 标志为 true 时，会发生什么？
   - A) Alert 被标记为最高优先级
   - B) 通过所有已配置的渠道（电话、SMS、推送等）发送 Alert
   - C) 跳过升级链并立即将 Alert 发送给主管
   - D) 永久存储 Alert

<details>
<summary>显示答案</summary>

**答案：B) 通过所有已配置的渠道（电话、SMS、推送等）发送 Alert**

**说明：**
`important` 标志的含义：
- `important: true`: 通过用户配置的所有通知渠道发送 Alert（电话、SMS、移动推送、Slack 等）
- `important: false`: 仅通过默认渠道发送 Alert（例如 Slack）

这可根据严重程度调整 Alert 强度。Critical Alert 可设置为 important=true 以包含电话/SMS，而 Warning 可设置为 important=false 以仅使用 Slack。

</details>

---

7. 使用 Grafana OnCall 的 Slack 集成时，以下哪项**不是**可用命令？
   - A) /oncall ack（确认 Alert）
   - B) /oncall resolve（解决 Alert）
   - C) /oncall deploy（执行 Deployment）
   - D) /oncall silence 2h（静默 2 小时）

<details>
<summary>显示答案</summary>

**答案：C) /oncall deploy（执行 Deployment）**

**说明：**
Grafana OnCall Slack 命令：
- `/oncall` - 查看当前值班响应人员
- `/oncall schedule` - 查看排班
- `/oncall ack` - 确认 Alert
- `/oncall resolve` - 解决 Alert
- `/oncall silence 2h` - 静默 2 小时
- `/oncall unsilence` - 取消静默
- `/oncall escalate` - 升级 Alert

执行 Deployment 不是 OnCall 的功能。OnCall 专注于 Alert 管理和待命管理。

</details>

---

8. 与 PagerDuty/OpsGenie 相比，以下哪项**不是** Grafana OnCall 的优势？
   - A) 开源且可自托管
   - B) 与 Grafana stack 原生集成
   - C) 支持 700+ 集成
   - D) 可免费使用（OSS 版本）

<details>
<summary>显示答案</summary>

**答案：C) 支持 700+ 集成**

**说明：**
支持 700+ 集成是 PagerDuty 的优势。对比：
- **Grafana OnCall**: 30+ 集成、开源、支持自托管、Grafana 原生集成、免费（OSS）
- **PagerDuty**: 700+ 集成、仅 SaaS、先进的分析/报告、AIOps 功能
- **OpsGenie**: 200+ 集成、仅 SaaS、Atlassian 生态系统集成

对于使用 Grafana stack 的环境，OnCall 是一种具有成本效益的选择；但当需要集成各种外部系统时，PagerDuty 可能更合适。

</details>

---

9. Grafana OnCall 生产 Deployment 的高可用性推荐配置是什么？
   - A) 单个实例即可
   - B) 增加 API server 和 Celery worker 的副本数量，并使用外部 PostgreSQL/Redis
   - C) 跨多个 cluster 进行分布式 Deployment
   - D) 仅添加只读副本

<details>
<summary>显示答案</summary>

**答案：B) 增加 API server 和 Celery worker 的副本数量，并使用外部 PostgreSQL/Redis**

**说明：**
Grafana OnCall 生产环境 HA 配置：
- **API server**: 3+ 个副本，配置 Pod Anti-Affinity
- **Celery workers**: 3+ 个副本，配置 Pod Anti-Affinity
- **PostgreSQL**: 使用外部托管 DB（AWS RDS 等）
- **Redis**: 使用外部托管 Redis（AWS ElastiCache 等）

此配置可消除单点故障，即使单个组件发生故障，服务仍可继续运行。

</details>

---

10. 在 Grafana OnCall 中设置路由的主要目的是什么？
    - A) 网络流量分发
    - B) 根据 Alert 条件应用不同的升级链
    - C) 数据库查询优化
    - D) 用户身份验证路径配置

<details>
<summary>显示答案</summary>

**答案：B) 根据 Alert 条件应用不同的升级链**

**说明：**
路由根据传入 Alert 的属性（标签、严重程度、团队等）将其连接到适当的升级链：
- `severity=critical` -> Critical 升级链（包括电话/SMS）
- `team=infra` -> Infrastructure 团队升级链
- `namespace=production` -> Production 值班排班

路由规则使用正则表达式定义，并根据 Alert payload 内容进行匹配。这使得可以针对不同 Alert 类型应用适当的响应人员和升级策略。

</details>

---

## 附加学习资源

- [Grafana OnCall 文档](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana/helm-charts/tree/main/charts/oncall)
- [Grafana IRM（事件响应管理）](https://grafana.com/products/cloud/irm/)
