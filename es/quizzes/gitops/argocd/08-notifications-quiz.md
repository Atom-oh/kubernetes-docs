# Cuestionario de notificaciones de ArgoCD

Este cuestionario evalúa tu comprensión del sistema de notificaciones y alertas de ArgoCD.

1. ¿Qué componente gestiona las notificaciones en ArgoCD?
   - A) Application Controller
   - B) Notifications Controller (argocd-notifications)
   - C) API Server
   - D) Repo Server

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Notifications Controller (argocd-notifications)**

**Explicación:**
El ArgoCD Notifications Controller supervisa las Applications de ArgoCD y envía notificaciones según los triggers y templates configurados. Es un componente independiente que se integró en el núcleo de ArgoCD.

</details>

2. ¿Dónde se almacenan las configuraciones de notificaciones en ArgoCD?
   - A) En un CRD dedicado
   - B) En el ConfigMap argocd-notifications-cm
   - C) En la spec de Application
   - D) En variables de entorno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) En el ConfigMap argocd-notifications-cm**

**Explicación:**
Los servicios de notificación, templates y triggers se configuran en el ConfigMap `argocd-notifications-cm`. Los datos confidenciales, como las URL de webhooks, se almacenan en `argocd-notifications-secret`.

</details>

3. ¿Qué es un «trigger» en las notificaciones de ArgoCD?
   - A) Un botón para enviar notificaciones manuales
   - B) Una condición que determina cuándo enviar una notificación
   - C) Un endpoint de webhook
   - D) Un template de notificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una condición que determina cuándo enviar una notificación**

**Explicación:**
Los triggers definen las condiciones (como cambios en el estado de sync, cambios de salud o errores de sync) que determinan cuándo deben enviarse las notificaciones. Hacen referencia a templates que dan formato al contenido de la notificación.

</details>

4. ¿Cómo suscribes una Application para recibir notificaciones?
   - A) Edita el ConfigMap de notificaciones
   - B) Agrega annotations a la Application con suscripciones de notificaciones
   - C) Crea un CRD NotificationSubscription
   - D) Configúralo en la UI de ArgoCD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrega annotations a la Application con suscripciones de notificaciones**

**Explicación:**
Las Applications se suscriben a las notificaciones mediante annotations como `notifications.argoproj.io/subscribe.on-sync-succeeded.slack: my-channel`. Esto especifica el trigger, el servicio y el destinatario.

</details>

5. ¿Qué servicios de notificación admite ArgoCD de forma predeterminada?
   - A) Solo Slack
   - B) Solo correo electrónico
   - C) Varios, incluidos Slack, Teams, correo electrónico, webhooks y más
   - D) Ninguno; todos requieren plugins personalizados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Varios, incluidos Slack, Teams, correo electrónico, webhooks y más**

**Explicación:**
Las notificaciones de ArgoCD admiten muchos servicios, incluidos Slack, Microsoft Teams, Telegram, Opsgenie, Grafana, PagerDuty, GitHub, correo electrónico (SMTP) y webhooks genéricos.

</details>
