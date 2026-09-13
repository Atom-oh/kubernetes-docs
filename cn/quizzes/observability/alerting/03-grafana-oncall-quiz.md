# Grafana OnCall 测验

> **最后更新**: September 13, 2026

本测验涵盖对已归档的 OnCall OSS 部署进行审查/迁移的内容。

用于检验你对 Grafana OnCall 理解程度的测验。

**Cloud Connection 已于 2026-03-24 终止。** 通过 Grafana IRM 应用的 OSS 移动推送，以及依赖 Cloud Connection 的短信/语音通知均已不再可用。单独配置的 Twilio 或其他通知服务属于不同的路径；这并不意味着所有自托管的电话/短信机制都已终止。

---

1. 以下哪一项**不是** Grafana OnCall 的核心功能？
   - A) On-call 排班管理
   - B) 升级链（escalation chain）配置
   - C) 指标采集与存储
   - D) ChatOps 集成（Slack、Teams）

<details>
<summary>显示答案</summary>

**答案：C) 指标采集与存储**

**解析：**
OnCall 负责接收和管理告警、排班、路由以及响应人操作；它不是指标数据库。OSS 已于 2026-03-24 归档。现有部署中的通道/API 可用性必须与仍在维护的 Cloud IRM 分开单独确认。

</details>

---

2. Grafana OnCall 升级策略中 `wait` 类型的作用是什么？
   - A) 在发送告警前等待数据采集完成
   - B) 在进入下一个升级步骤前等待
   - C) 等待用户响应后自动解决
   - D) 等待告警分组

<details>
<summary>显示答案</summary>

**答案：B) 在进入下一个升级步骤前等待**

**解析：**
wait 步骤会延迟下一个升级步骤。它既不会确认（acknowledge）也不会解决（resolve）事件。经查阅的公共 serializer 接受从 1 分钟到 24 小时的等待时间（以秒为单位）；实际的停止/重新呼叫行为取决于升级链和告警组（alert group）状态。

</details>

---

3. Grafana OnCall 的 on-call 排班中的 “Override” 是什么？
   - A) 完全删除并重建排班
   - B) 在现有排班中临时更改某一特定时段的响应人
   - C) 更改排班的时区
   - D) 修改轮转周期

<details>
<summary>显示答案</summary>

**答案：B) 在现有排班中临时更改某一特定时段的响应人**

**解析：**
override 会更改某个既定时段的值班覆盖。在经查阅的 API 中，它属于 on_call_shifts 类型，需要显式指定时区，并必须关联到目标排班。请核实现有班次的 ID、优先级、空档以及最终响应人；不要假设仍存在旧的嵌套 overrides 端点。

</details>

---

4. 将 Grafana OnCall 与 Alertmanager 集成时采用什么方式？
   - A) Alertmanager 直接采集 OnCall 的指标
   - B) 通过 Alertmanager 的 webhook_configs 将告警发送到 OnCall
   - C) OnCall 定期轮询 Alertmanager 的 API
   - D) 两个系统共享一个数据库

<details>
<summary>显示答案</summary>

**答案：B) 通过 Alertmanager 的 webhook_configs 将告警发送到 OnCall**

**解析：**
使用 webhook_configs 并填入对应实际集成类型所生成的 URL，必要时将其保存在受保护的 url_file 中。所有被引用的 receiver 都必须定义，并使用当前版本的 matchers。公共 API 的原始 token 认证与 webhook URL 是两回事；send_resolved 并不会让 OnCall 去更新源规则。

</details>

---

5. Grafana OnCall 中告警分组的主要目的是什么？
   - A) 按时间排序告警
   - B) 将相关告警归为一组，以减少告警疲劳
   - C) 按严重程度对告警分类
   - D) 自动删除重复告警

<details>
<summary>显示答案</summary>

**答案：B) 将相关告警归为一组，以减少告警疲劳**

**解析：**
分组可以减少响应人的重复工作，但必须使用与事件域相匹配的分组键。标签过少会把无关事件合并在一起；使用无界的 ID 则会导致分组碎片化。源端 Alertmanager 的时序与 OnCall 的分组/解决模板是相互独立的，并且投递也无法保证恰好一次。

</details>

---

6. 在 Grafana OnCall 升级策略中，当 `notify_on_call_from_schedule` 的 `important` 标志为 true 时会发生什么？
   - A) 告警被标记为最高优先级
   - B) 选用该用户配置的 important 通知规则集
   - C) 跳过升级链，告警立即发送给主管
   - D) 告警被永久保存

<details>
<summary>显示答案</summary>

**答案：B) 选用该用户配置的 important 通知规则集**

**解析：**
important 会选用该用户的 important 个人通知规则集。已配置的规则顺序、等待时间、通道及可用性依然生效。它不会自动通过所有通道发送；默认规则也并非一律只用 Slack。

</details>

---

7. 在现有 OnCall 部署中使用 Slack 操作的正确做法是什么？
   - A) 假定每个部署都支持 /oncall ack
   - B) 把斜杠命令当作 Bash 来处理
   - C) 核实已安装应用的命令、权限和操作按钮
   - D) 假定确认（acknowledge）会解决源监控项

<details>
<summary>显示答案</summary>

**答案：C) 核实已安装应用的命令、权限和操作按钮**

**解析：**
请检查已安装 Slack 应用的实际根命令/帮助信息以及已授权的操作按钮。经查阅的源码使用可配置的根命令和 /grafana 示例，而不是此前所声称的旧 /oncall 命令集。Acknowledge、Resolve 和 Silence 是各自独立的操作；它们并不意味着会执行部署。

</details>

---

8. 选择新的 on-call 工具或做出迁移决策的恰当依据是什么？
   - A) 仅按旧的集成数量来选择
   - B) 假定 OSS 没有运营成本
   - C) 考察维护状况、所需功能、实际成本以及迁移/恢复
   - D) 默认安装已归档的 OnCall OSS

<details>
<summary>显示答案</summary>

**答案：C) 考察维护状况、所需功能、实际成本以及迁移/恢复**

**解析：**
应依据当前的维护/生命周期状况、所需功能、运营成本和合同条款。固定的旧集成数量或按用户计价并不足以作为依据。OnCall OSS 已归档；Opsgenie 已宣布服务/支持将于 2027-04-05 终止。请评估仍在维护的目标平台，并测试迁移与恢复流程。

</details>

---

9. 对于现有 OnCall 部署的可用性，必须验证哪些内容？
   - A) 三个 API 副本即可保证可用性
   - B) 依赖项、状态、投递、故障与恢复行为
   - C) 仅集群数量
   - D) 仅一个只读数据库副本

<details>
<summary>显示答案</summary>

**答案：B) 依赖项、状态、投递、故障与恢复行为**

**解析：**
仅靠副本数量并不能消除所有故障点。现有部署需要验证依赖项、broker/缓存/数据库、调度器、密钥、TLS、投递以及恢复能力。已归档的 OSS 不应作为新建生产环境的默认选择；本次审查中并未实际演练任何 HA 部署。

</details>

---

10. 在 Grafana OnCall 中设置路由（route）的主要目的是什么？
    - A) 网络流量分发
    - B) 根据告警条件应用不同的升级链
    - C) 数据库查询优化
    - D) 用户认证路径配置

<details>
<summary>显示答案</summary>

**答案：B) 根据告警条件应用不同的升级链**

**解析：**
路由会依据集成的实际负载、匹配模式、顺序和回退（fallback）来选择升级/通知行为。经查阅的 serializer 使用嵌套的 slack.channel_id/enabled。请测试字段缺失/冲突的情况；对消息文本做任意正则匹配并不是所有提供方都遵循的通用约定。

</details>

---

## 补充学习资源

- [Grafana OnCall Documentation](https://grafana.com/docs/oncall/latest/)
- [Grafana OnCall GitHub](https://github.com/grafana-cold-storage/oncall)
- [Grafana OnCall Helm Chart](https://github.com/grafana-cold-storage/oncall/tree/af0fbd40558c9a63bcf438589894c440fc434a54/helm/oncall)
- [Grafana IRM (Incident Response Management)](https://grafana.com/products/cloud/irm/)

- [指南](../../../observability/alerting/03-grafana-oncall.md)
