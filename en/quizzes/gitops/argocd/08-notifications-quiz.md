# ArgoCD Notifications Quiz

This quiz tests your understanding of ArgoCD notification system and alerting.

1. What component handles notifications in ArgoCD?
   - A) Application Controller
   - B) Notifications Controller (argocd-notifications)
   - C) API Server
   - D) Repo Server

<details>
<summary>Show Answer</summary>

**Answer: B) Notifications Controller (argocd-notifications)**

**Explanation:**
The ArgoCD Notifications Controller monitors ArgoCD Applications and sends notifications based on configured triggers and templates. It's a separate component that was merged into core ArgoCD.

</details>

2. Where are notification configurations stored in ArgoCD?
   - A) In a dedicated CRD
   - B) In the argocd-notifications-cm ConfigMap
   - C) In the Application spec
   - D) In environment variables

<details>
<summary>Show Answer</summary>

**Answer: B) In the argocd-notifications-cm ConfigMap**

**Explanation:**
Notification services, templates, and triggers are configured in the `argocd-notifications-cm` ConfigMap. Sensitive data like webhook URLs are stored in `argocd-notifications-secret`.

</details>

3. What is a "trigger" in ArgoCD notifications?
   - A) A button to send manual notifications
   - B) A condition that determines when to send a notification
   - C) A webhook endpoint
   - D) A notification template

<details>
<summary>Show Answer</summary>

**Answer: B) A condition that determines when to send a notification**

**Explanation:**
Triggers define the conditions (like sync status changes, health changes, or sync failures) that determine when notifications should be sent. They reference templates that format the notification content.

</details>

4. How do you subscribe an Application to receive notifications?
   - A) Edit the notifications ConfigMap
   - B) Add annotations to the Application with notification subscriptions
   - C) Create a NotificationSubscription CRD
   - D) Configure it in the ArgoCD UI

<details>
<summary>Show Answer</summary>

**Answer: B) Add annotations to the Application with notification subscriptions**

**Explanation:**
Applications subscribe to notifications via annotations like `notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel`. This specifies the trigger, service, and recipient.

</details>

5. Which notification services does ArgoCD support out of the box?
   - A) Only Slack
   - B) Only email
   - C) Multiple including Slack, Teams, email, webhooks, and more
   - D) None, all require custom plugins

<details>
<summary>Show Answer</summary>

**Answer: C) Multiple including Slack, Teams, email, webhooks, and more**

**Explanation:**
ArgoCD notifications supports many services including Slack, Microsoft Teams, Telegram, Opsgenie, Grafana, PagerDuty, GitHub, email (SMTP), and generic webhooks.

</details>
