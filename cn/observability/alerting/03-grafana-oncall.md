# Grafana OnCall

> **最后更新**: September 13, 2026

## 目录

- [Grafana OnCall 概述](#grafana-oncall-overview)
- [架构](#architecture)
- [安装](#installation)
- [集成配置](#integration-setup)
- [On-Call 排班配置](#on-call-schedule-configuration)
- [升级链（Escalation Chains）](#escalation-chains)
- [告警分组与路由](#alert-grouping-and-routing)
- [ChatOps 集成](#chatops-integration)
- [Grafana IRM 集成](#grafana-irm-integration)
- [移动应用](#mobile-app)
- [PagerDuty/OpsGenie 对比](#pagerduty-opsgenie-comparison)
- [最佳实践](#best-practices)

---

## Grafana OnCall 概述 {#grafana-oncall-overview}

**Grafana OnCall OSS 已于 2026-03-24 归档。** 其仓库已迁移至 `grafana-cold-storage/oncall`，且为只读状态。本章用于支持对现有安装的评审/迁移，并不表示推荐将其用于新的生产环境 OSS 部署。请另行确认仍在维护的 Grafana Cloud IRM 功能、API 与套餐。

**Cloud Connection 已于 2026-03-24 终止。** 通过 Grafana IRM 应用的 OSS 移动推送，以及依赖 Cloud Connection 的 SMS/语音通知均已不再可用。单独配置的 Twilio 或其他通知服务属于不同的路径；这并不意味着所有自托管的电话/SMS 机制都已终止。

本次评审所依据的归档源代码为 `af0fbd40558c9a63bcf438589894c440fc434a54`。最新发布版本标记为 v1.16.11，而该源代码的 Helm chart/appVersion 为 1.15.6；这两个版本标识不可互换使用。示例均已对照该源代码与官方 OnCall API 文档进行核对。未实际创建任何 OnCall 账户、执行 API 写入或发送通知。

### 主要功能

1. **On-Call 排班管理**：轮值（rotation）、覆盖（override）、假期管理
2. **升级链（Escalation Chains）**：基于时间的自动升级
3. **告警分组**：合并相关告警
4. **多种集成**：Alertmanager、Grafana、CloudWatch、Webhook
5. **ChatOps**：Slack、MS Teams、Telegram 集成
6. **通知渠道**：可用性取决于部署方式、集成以及用户规则

### Grafana OnCall vs PagerDuty vs OpsGenie

| 选项 | 当前评审依据 |
|---|---|
| OnCall OSS | 已归档的现有安装；依赖项、恢复与迁移的归属责任 |
| Grafana Cloud IRM / PagerDuty | 确认维护状态、所需渠道/排班/API、区域与合同条款 |
| Opsgenie | 2025-06-04 停止销售；服务/支持计划于 2027-04-05 终止。现有用户需要制定迁移计划 |

不要基于固定的集成数量、过时的价格或主观的“基础/高级”排名来选择产品。

---

## 架构 {#architecture}

### Grafana OnCall 组件

以下是逻辑职责划分，并不一定对应独立的 Deployment。请检查已安装配置中的 database.type、broker.type、Redis、engine/Celery 的部署位置以及插件连通性。



![已归档 OnCall 安装的逻辑组件，包含已配置的 database/broker/cache 角色以及有条件可用的渠道。Cloud Connection 已于 2026-03-24 终止；须确认独立受支持的渠道。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-0.html)

### 告警处理流程

![HTTP 接收与后台路由和人工确认（acknowledgment）相互独立；不意味着会自动更新源端规则。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-1.html)

---

## 安装 {#installation}

### 通过 Helm 安装（EKS）

在考虑做出变更之前，先盘点现有的 release/chart/image 摘要（digest）、数据库、broker、Grafana 插件、认证与渠道依赖。对比 helm list、工作负载镜像以及受保护的 helm get values/manifest 输出。Values/manifests 可能包含真实凭据：请私密保存，不要放入聊天、Git 或构建日志中。

已归档的 chart 包含旧版本的 cert-manager、ingress-nginx 与数据库依赖。不要将不相关的当前版本 Grafana chart 与已归档源代码版本混用，也不要把一条简单的 helm install 命令当作当前仍有安全支持的证据。

### 基本 values.yaml 配置

以下是所检查的归档 chart 中的实际键（key）。它们区分了旧示例可能会被静默忽略或错误解读的设置。

| 职责 | 归档 chart 键 |
|---|---|
| API/engine 副本数 | `engine.replicaCount`，而非 `oncall.replicaCount` |
| URL | `base_url` 以及 `base_url_protocol` |
| 附加环境变量 | `env` map，而非原生 Kubernetes env 列表 |
| 外部 PostgreSQL | `externalPostgresql.db_name`、`existingSecret`、`passwordKey`、TLS 选项 |
| 外部 Redis | `externalRedis.existingSecret`、`passwordKey`、`ssl_options` |
| 应用加密密钥 | `oncall.secrets.existingSecret`、`secretKey`、`mirageSecretKey` |
| Telegram/Twilio | 嵌套的 `oncall.telegram` 与 `oncall.twilio` 设置 |

默认配置会启用 MariaDB、RabbitMQ、Redis、Grafana、ingress-nginx、cert-manager 等组件。把 database.type 改为 PostgreSQL 并不会自动禁用 MariaDB 或其他不相关的依赖。settings.hobby 与通用的 Firebase YAML 并非经过验证的生产配置。

### 生产环境 values.yaml

仅增加副本数并不能消除单点故障。请测试 engine、Celery、scheduler/beat、数据库、broker/cache、插件、通知服务商、DNS 与证书等各类故障，包括队列持久性、重复处理、重试与恢复。请区分 RabbitMQ broker 与 Redis 的职责，并检查实际的 broker.type。

现有部署的负责人必须评审 DB/Redis 的 TLS 校验、按角色分发密钥、网络访问、备份/恢复与迁移。面向互联网的 ALB 或外部数据库主机名并不能使配置达到生产就绪。本次审查未部署 EKS、未测试 HA，也未调用真实的通知服务商。

### 创建 Secret

不要通过 --from-literal 参数或明文 Helm values 传递真实值。请使用经批准的密钥存储/受保护文件，并将现有加密密钥与数据库备份一并管理。盲目更改现有安装的 Mirage key/IV 可能导致已存储数据无法解密。公共 API token、集成 webhook URL 以及 Slack/Twilio/Telegram 凭据具有不同的权限与轮换要求。

---

## 集成配置 {#integration-setup}

### Alertmanager 集成

请使用**所选集成类型生成的完整 URL**。该 URL 本身可能就是机密，因此应保存在受保护的文件中。不要自行编造 `/api/v1/webhook/<id>/` 路径并与公共 API token 组合使用。下面的 Alertmanager 配置定义了当前的 matchers 与两个 receiver；它并未被用于实际发送通知。

```yaml
# Materialize the generated integration URL in this protected file.
# This example is not enabled or contacted during the documentation audit.
route:
  receiver: no-page
  group_by: [alertname, cluster, namespace, service]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers: ['severity=~"critical|warning"']
      receiver: oncall
receivers:
  - name: no-page
  - name: oncall
    webhook_configs:
      - url_file: /etc/oncall/integration-url
        send_resolved: true
```

amtool 0.34 验证了语法以及 critical/warning/info/fallback 四种路由场景。send_resolved 会转发源端的 resolved 消息；它并不会让在 OnCall 中的手动 resolve 自动更改源端规则。

### Grafana Alerting 集成

请针对已安装的 Grafana/OnCall 插件版本，确认所支持的 contact point 与生成的集成。INI 设置、provisioning YAML 与 UI API 各不相同；旧示例错误地将 INI 标注为 YAML。Grafana Alerting 的规则/通知状态与 OnCall 的 alert-group 状态同样彼此独立。

### CloudWatch 集成

请遵循 CloudWatch 专用集成对 SNS 订阅确认、签名与负载（payload）处理的要求。将 SNS 订阅到任意通用 webhook 并不能保证兼容性。请测试 ALARM/OK/INSUFFICIENT_DATA 状态转换、订阅确认、重复/重试、topic/endpoint 权限以及实际投递情况。本次审查未创建任何 SNS 订阅或告警动作。

### Webhook 集成

通用 webhook 负载必须与显式配置的解析、分组与 resolution 模板相匹配。发送 alert_uid、state 与 labels 并不意味着每个集成都会以相同方式解读它们。请正确序列化 JSON，并设计好 HTTPS 校验、超时、错误处理以及重试/去重行为。不要将 URL、token 与个人数据写入日志。

公共 API 使用文档所述的**原始 Authorization token**；不要自动添加 Bearer。使用 Grafana service-account-token 认证时还需要 X-Grafana-URL。API 来源与集成 webhook 属于两条独立的认证路径。

该[只读盘点工具](https://github.com/Atom-oh/kubernetes-docs/tree/main/examples/observability/oncall)仅使用 GET，并会校验分页的来源/集合/计数、TLS、重定向与文件权限。其输出可能包含机密的集成 URL 与个人数据；它并非完整的数据库/密钥/历史备份，也不是原子性的迁移快照。12 项本地 TLS fixture 测试均已通过，且未查询任何真实账户。

---

## On-Call 排班配置 {#on-call-schedule-configuration}

### 排班概念

请将时区、班次优先级与覆盖（override）一并评审。把层级命名为 primary/secondary 并不会自动配置备份升级。请在 API/UI 中检查最终的响应人，并测试空档、重叠、DST（夏令时）与交接边界。

![班次 ID、优先级、时区与覆盖共同决定最终排班；备份升级需要单独的策略。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-2.html)

### 创建排班（API）

web 类型排班的 `shifts` 包含的是**已有班次的 ID**，而不是嵌套的班次对象。请先在 `/api/v1/on_call_shifts/` 下创建班次，然后将返回的 ID 附加到 `/api/v1/schedules/` 的 web 排班上。以下是需由运维人员评审的请求示例，需要填入真实的 ID/日期；未执行任何写入操作。

```json
{
  "name": "Illustrative weekly rotation",
  "type": "rolling_users",
  "time_zone": "Asia/Seoul",
  "start": "2026-09-14T09:00:00",
  "duration": 604800,
  "frequency": "weekly",
  "interval": 1,
  "week_start": "MO",
  "start_rotation_from_user_index": 0,
  "rolling_users": [
    ["REPLACE_WITH_USER_ID_A"],
    ["REPLACE_WITH_USER_ID_B"]
  ]
}
```

```json
{
  "name": "Illustrative SRE schedule",
  "type": "web",
  "time_zone": "Asia/Seoul",
  "shifts": ["REPLACE_WITH_EXISTING_SHIFT_ID"]
}
```


### 轮值类型

按周重复需要 `week_start`、为正数的 `interval`，以及 rolling_users 的起始用户索引。按日/周/小时重复并不等同于仅修改 duration。源代码中的校验器接受 `YYYY-MM-DDTHH:MM:SS` 格式的 start，并搭配独立的 time_zone；不要照抄旧的带偏移量的字符串。JSON 中的日期仅为示例，并非实际运行的排班。

19 项检查实际执行了上游的纯校验器并检查了 serializer 字段。它们无法证明数据库中用户/班次的存在性，也无法证明最终的日历分配结果。

### 覆盖（Override）设置

在该源代码中，override 是 `/api/v1/on_call_shifts/` 下的一种独立类型，而不是旧文档所假设的 `/schedules/<id>/overrides/` 请求。请在保留现有班次 ID 的前提下，将其关联到目标排班。请确认所安装 API 的关联/优先级行为，并在受限的测试时间段内检查最终响应人。

```json
{
  "name": "Illustrative temporary replacement",
  "type": "override",
  "time_zone": "Asia/Seoul",
  "start": "2026-09-15T09:00:00",
  "duration": 28800,
  "users": ["REPLACE_WITH_EXISTING_USER_ID"]
}
```


---

## 升级链（Escalation Chains） {#escalation-chains}

### 升级链结构

Acknowledge、Resolve 与 Silence 是不同的状态。确认（acknowledgment）并不会修复根本问题，也不会停用源端规则。请依据实际策略与集成状态确认 wait、stop 与重新呼叫（re-page）的条件。图中的 15 分钟窗口只是示例策略，并非产品保证。

![示例中的等待与通知步骤最终导向确认（acknowledgment）；确认并不等于源端问题已解决。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-3.html)

### 创建升级链

请确认现有的 chain、schedule 与用户 ID 以及权限，并分别评审创建/更新请求。下面是 /api/v1/escalation_policies/ 的**一个 wait 步骤**，而不是完整的链创建请求。所检查的源代码接受 1 分钟到 24 小时的等待时长，以秒为单位表示。

```json
{
  "escalation_chain_id": "REPLACE_WITH_EXISTING_CHAIN_ID",
  "position": 1,
  "type": "wait",
  "duration": 900
}
```


### 升级策略类型

源代码中的 serializer 支持 schedule/user/team/group 通知、等待、时间/次数条件、自定义 webhook 以及在启用相应功能时声明 incident。自定义 webhook 的引用字段是 action_to_trigger；不要假设仍是旧的 webhook_id 或存在通用的 repeat_after 字段。declare_incident 确实存在，但需要在组织层面启用该功能。

important:true 会选用该用户配置的**重要通知规则**；它不会无条件地向所有渠道扩散。请评审每个用户的默认/重要规则顺序、等待时间、渠道以及实际可用性。


### 按严重级别划分的升级链

请就各严重级别的用途、响应窗口、备份人员、工作时间与重新呼叫行为达成一致。再次通知同一个排班并不总意味着会通知到下一位不同的响应人。请确认实际的 repeat/条件步骤 API 字段，避免同一事件产生重复呼叫。真实的电话/SMS/webhook 投递需要经批准的测试路径，本次并未执行。


---

## 告警分组与路由 {#alert-grouping-and-routing}

### 路由设置

请检查每个集成的实际负载、路由顺序，以及用于未匹配事件的默认路由。Alertmanager、Grafana 与 CloudWatch 的负载各不相同；匹配任意消息文本的正则可能导致错误路由。请测试正常、缺失、格式错误与相互冲突的场景。

![示例中按集成划分的路由，包含已配置的顺序、兜底（fallback）以及嵌套的 Slack 渠道设置。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-4.html)

### 创建路由

该示例使用的是所检查的 route serializer 中存在的字段。Slack 使用嵌套的 slack.channel_id/enabled，而不是旧的扁平字段 slack_channel_id。需要真实的 integration/chain/channel ID 与授权。其中的正则仅针对特定负载作示例，并非适用于所有服务商的通用模板。

```json
{
  "integration_id": "REPLACE_WITH_EXISTING_INTEGRATION_ID",
  "routing_type": "regex",
  "routing_regex": "\"severity\"\\s*:\\s*\"critical\"",
  "position": 0,
  "escalation_chain_id": "REPLACE_WITH_EXISTING_CHAIN_ID",
  "slack": {
    "channel_id": "REPLACE_WITH_EXISTING_SLACK_CHANNEL_ID",
    "enabled": true
  }
}
```


### 告警分组配置

请在分组键中纳入合适的 cluster/environment/namespace/service 范围，以避免冲突。字段过少会把不相关的事件合并；使用无边界的 ID 则会把分组碎片化。旧的混合了 group_wait/group_interval/resolve_timeout 的 YAML 并不是通用的 OnCall 集成 schema。请区分 Alertmanager 的计时器与 OnCall 的分组/resolution 模板。

请从集成的实际负载中选择模板变量。payload.labels 并不保证存在，也并非在所有 Alertmanager 请求中都位于顶层。请正确转义 JSON，且不要把用户输入当作可信代码。


---

## ChatOps 集成 {#chatops-integration}

### Slack 集成

请确认已安装 Slack 应用的 OAuth/signing secret、scope 与工作区连接。请通过路由中嵌套的 Slack 设置来引用已发现的 slack_channels；不要假设旧的 POST /slack_channels 示例会创建/连接渠道。应用安装与用户操作需要单独的授权操作流程，本次并未执行。


### Slack 命令

旧文档中的 /oncall ack、/oncall resolve 与 /oncall silence 列表并未在所检查的源代码中得到确认。该源代码使用可配置的根命令，并以 /grafana 作为示例。请查看已安装应用当前的帮助/文档与按钮；斜杠命令不是 Bash 命令。


### Slack 工作流

Acknowledge/Resolve/Silence 按钮通过已授权用户的操作来改变 OnCall 状态。投递确认、Slack 消息更新与源端监控系统的状态彼此独立；不要假设会自动反向同步状态。

![已授权的 Slack 操作会更新 OnCall 与消息；源端监控系统的状态有其独立的生命周期。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-5.html)

### MS Teams 集成

请确认 Microsoft 当前支持的 webhook/workflow 与卡片格式。不要把旧的 Office connector URL 与 MessageCard JSON 照搬为通用的新集成方式。仅编写 YAML 并不会安装 outgoing webhook；其模板上下文、认证、负载、投递与失败处理都需要实际配置。未发送任何 Teams 消息。


### Telegram 集成

已归档的 chart 使用嵌套的 oncall.telegram token/existingSecret/tokenKey 设置以及独立的 telegramPolling。旧文档中标注为 Bash 的顶层 telegram.enabled 配置块并不是正确的 Helm 配置。请确认 bot 凭据、webhook/polling 的归属、用户关联以及当前可用性。未创建任何 bot，也未发送用户消息。


---

## Grafana IRM 集成 {#grafana-irm-integration}

### 事件响应管理（IRM）

请区分仍在维护的 Grafana Cloud IRM 告警/on-call/事件能力与已归档的 OnCall OSS。IRM 既不是 Grafana Incident 的简单改名，也不保证与 OSS 具有相同的 API、权限或功能覆盖。请确认目标平台当前的功能、合同、数据保留以及导出/导入支持。

![事件联动需要启用相应功能并配置对应步骤；alert-group 与 incident 的状态仍然彼此独立。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-6.html)

### 自动创建事件

所检查的源代码中确实包含真实的 declare_incident 步骤，但会校验组织是否启用了该功能。随意添加 severity/title_template YAML 并不能配置出一个事件集成。请区分 alert group、incident、确认、解决与复盘（postmortem），并在经批准的测试中确认归属与状态转换。

---

## 移动应用 {#mobile-app}

### 移动应用功能

受支持的应用/部署组合可以提供告警信息流、状态操作、排班与通知，但受后端连通性、操作系统权限、网络与用户规则的限制。并不保证在每个自托管安装上都能即时投递或推送正常工作。


### 移动应用配置

旧文档中的 mobile.firebase 配置块并不是所检查的归档 chart 中的键。随意提供一个 Firebase 服务账号文件并不能让推送正常工作。Cloud Connection 已终止：使用该连接的 OSS Grafana IRM 应用推送以及 SMS/语音均不可用。请配置并验证独立受支持的 Twilio/通知服务路径或迁移目标。未创建任何 Firebase 项目/账户，也未发送推送通知。


### 通知渠道优先级

Important/default 分别对应不同的个人通知规则集。其顺序、等待时间、渠道与可用性均生效；important 并不意味着同时向所有渠道投递。请测试投递、确认与升级行为。

![Important 与 default 选择的是已配置的个人通知规则，而非无条件向所有渠道扩散。Cloud Connection 已于 2026-03-24 终止；须确认独立受支持的渠道。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-7.html)

---

<span id="pagerdutyopsgenie-comparison"></span>

## PagerDuty/OpsGenie 对比 {#pagerduty-opsgenie-comparison}

### 功能对比

请以相同的需求为基准，对照实际的套餐、用量与合同进行比较。旧的按用户价格、集成数量以及基础/高级排名并不能作为当前的选型依据。请检查排班/覆盖、条件升级、SSO、数据保留、API 权限、渠道/国家限制、支持以及迁移成本。OnCall OSS 已归档，而 Opsgenie 需要依据其公布的生命周期制定迁移计划。


### 迁移注意事项

默认方向已不再是从 PagerDuty/Opsgenie 新迁入 OnCall OSS。请先盘点现有 OnCall/即将停服工具的数据与依赖，然后验证仍在维护的目标平台的功能差异与恢复能力。免费的代码并不能消除托管、运维、支持与沟通成本。

![盘点、备份、合同评审、投递/恢复测试，以及受控切换到仍在维护的目标平台。Cloud Connection 已于 2026-03-24 终止；须确认独立受支持的渠道。](../../.gitbook/assets/en-observability-alerting-03-grafana-oncall-8.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-alerting-03-grafana-oncall-8.html)

### 迁移检查清单

- [ ] 盘点用户/团队、排班/时区/覆盖、升级链/路由、模板与集成
- [ ] 准备独立的数据库/密钥/配置/历史备份并进行恢复测试
- [ ] 确认目标平台的功能、ID 映射、权限、隐私与数据保留
- [ ] 测试合成的 firing/resolved/缺失/重试/重复/无响应/交接等场景
- [ ] 在并行运行期间防止重复呼叫；明确责任归属、切换与回滚标准
- [ ] 按经批准的顺序切换源端 URL/token，并在验证后收回不必要的访问权限
- [ ] 完成响应人培训与运维交接

固定的一到两周并行期并不是一种保证，通过 API 做的盘点也不等于完整备份。


---

## 最佳实践 {#best-practices}

### On-Call 排班设计

请依据实际时区、假期、交接、备份与人员配置来商定排班。每周班次、09:00 交接或至少三/四人并不是普适答案。请移交进行中的事件、即将到期的 silence 以及覆盖空档。


### 升级设计

请记录各严重级别的处理动作/响应目标、备份/管理上报路径、重新呼叫与停止条件。会打断人的呼叫必须对应可执行的响应；非紧急信息可以走其他路径。Important 并不保证电话/SMS 一定送达。


### 告警质量管理

请评审重复、误报、漏报、投递失败以及实际的响应结果。在更改过滤器/模板/分组/源端 URL 之后，重新核对数据与状态转换，并保留一条安全的恢复路径。


### On-Call 健康度

请与团队就工作量、补偿、恢复时间与责任范围达成一致。减少反复发生的事件根因，并改进 runbook、自动化与交接流程。具体的班次/恢复时长属于因情况而定的运营策略。


---

## 测验

通过 [Grafana OnCall 测验](../../quizzes/observability/alerting/03-grafana-oncall-quiz.md) 测试你的知识。

## 参考资料

- [OnCall OSS lifecycle](https://grafana.com/docs/oncall/latest/)
- [OnCall API reference](https://grafana.com/docs/oncall/latest/oncall-api-reference/)
- [Archived source contract](https://github.com/grafana-cold-storage/oncall/tree/af0fbd40558c9a63bcf438589894c440fc434a54)
- [Opsgenie lifecycle](https://www.atlassian.com/software/opsgenie)
- [Cloud Connection cutoff and alternatives](https://grafana.com/docs/oncall/latest/set-up/open-source/)
