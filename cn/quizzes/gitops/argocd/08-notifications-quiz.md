# ArgoCD Notifications 测验

本测验用于测试您对 ArgoCD 通知系统和告警的理解。

1. ArgoCD 中哪个组件负责处理通知？
   - A) Application Controller
   - B) Notifications Controller (argocd-notifications)
   - C) API Server
   - D) Repo Server

<details>
<summary>显示答案</summary>

**答案：B) Notifications Controller (argocd-notifications)**

**说明：**
ArgoCD Notifications Controller 监控 ArgoCD Applications，并根据配置的触发器和模板发送通知。它是一个已合并到核心 ArgoCD 的独立组件。

</details>

2. ArgoCD 中的通知配置存储在哪里？
   - A) 在专用的 CRD 中
   - B) 在 argocd-notifications-cm ConfigMap 中
   - C) 在 Application spec 中
   - D) 在环境变量中

<details>
<summary>显示答案</summary>

**答案：B) 在 argocd-notifications-cm ConfigMap 中**

**说明：**
通知服务、模板和触发器均在 `argocd-notifications-cm` ConfigMap 中配置。webhook URL 等敏感数据存储在 `argocd-notifications-secret` 中。

</details>

3. ArgoCD 通知中的“触发器”是什么？
   - A) 用于发送手动通知的按钮
   - B) 决定何时发送通知的条件
   - C) webhook 端点
   - D) 通知模板

<details>
<summary>显示答案</summary>

**答案：B) 决定何时发送通知的条件**

**说明：**
触发器定义条件（例如同步状态变化、健康状态变化或同步失败），以决定何时应发送通知。它们引用用于格式化通知内容的模板。

</details>

4. 如何为 Application 订阅通知？
   - A) 编辑通知 ConfigMap
   - B) 为 Application 添加带有通知订阅的注解
   - C) 创建 NotificationSubscription CRD
   - D) 在 ArgoCD UI 中进行配置

<details>
<summary>显示答案</summary>

**答案：B) 为 Application 添加带有通知订阅的注解**

**说明：**
Applications 通过注解订阅通知，例如 `notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel`。这指定了触发器、服务和接收者。

</details>

5. ArgoCD 开箱即用支持哪些通知服务？
   - A) 仅 Slack
   - B) 仅电子邮件
   - C) 包括 Slack、Teams、电子邮件、webhooks 等在内的多种服务
   - D) 不支持，全部需要自定义插件

<details>
<summary>显示答案</summary>

**答案：C) 包括 Slack、Teams、电子邮件、webhooks 等在内的多种服务**

**说明：**
ArgoCD notifications 支持许多服务，包括 Slack、Microsoft Teams、Telegram、Opsgenie、Grafana、PagerDuty、GitHub、电子邮件 (SMTP) 和通用 webhooks。

</details>
