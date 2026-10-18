# Notificaciones de ArgoCD

> **Revisado con respecto a**: Argo CD 3.5.2 (Notifications Engine incluido 0cff13b8a717); actualizado al parche 3.5.4, que fija el mismo commit de Notifications Engine, tras revisar las notas de la versión (los ejemplos no se ejecutaron de nuevo)
> **Última actualización**: October 12, 2026

## Índice

- [Descripción general](#overview)
- [Arquitectura](#architecture)
- [Servicios de notificación](#notification-services)
- [Disparadores](#triggers)
- [Plantillas](#templates)
- [Suscripciones](#subscriptions)
- [Configuración avanzada](#advanced-configuration)
- [Integración con AWS](#aws-integration)

## Descripción general {#overview}

ArgoCD Notifications es un componente que supervisa las aplicaciones de ArgoCD y envía notificaciones cuando se cumplen ciertas condiciones. Admite varios servicios de notificación y proporciona plantillas flexibles.

### Características principales

| Característica | Descripción |
|---------|-------------|
| Varios servicios | Slack, Teams, correo electrónico, webhook, GitHub y más |
| Disparadores flexibles | Disparadores de notificación basados en condiciones |
| Plantillas Go | Sintaxis de plantillas enriquecida para el formato de mensajes |
| Modelo de suscripción | Suscripciones de notificación por aplicación |
| Catálogo de ejemplos | Definiciones opcionales de disparadores/plantillas para combinar con su configuración |

## Arquitectura {#architecture}

![Diagrama de flujo de las notificaciones de ArgoCD: los eventos de Application llegan al Notifications Controller, que evalúa los disparadores y renderiza las plantillas; después, envía mensajes a las suscripciones configuradas coincidentes.](../../.gitbook/assets/en-gitops-argocd-08-notifications-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-08-notifications-0.html)

### Controlador y configuración

La instalación completa de Argo CD 3.5.4 incluye el controlador de Notifications. Compruebe que esté habilitado en los valores de su instalación/Helm. El archivo notifications_catalog/install.yaml contiene configuración de ejemplo; no es un instalador para un controlador ausente. Combine las entradas seleccionadas del catálogo con su ConfigMap y Secret existentes.

```bash
kubectl get deployment argocd-notifications-controller -n argocd
```

## Servicios de notificación {#notification-services}

Combine estos fragmentos de datos en una configuración de argocd-notifications-cm; no reemplace el mismo ConfigMap/Secret con cada fragmento independiente. Almacene los tokens, las URL de webhook firmadas y las claves privadas en valores protegidos de argocd-notifications-secret fuera de Git. Los nombres de servicio, plantilla, disparador y suscripción deben coincidir.

### Slack

Configure chat:write e invite al bot a los canales previstos. chat:write.public solo se necesita para publicar en canales públicos a los que el bot no se ha unido. signingSecret no sustituye una URL de Incoming Webhook.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  slack-token: xoxb-your-bot-token
```

Configuración de Slack Bot:
1. Cree una Slack App en https://api.slack.com/apps
2. Añada `chat:write`; use `chat:write.public` solo si el caso de uso indicado lo requiere
3. Instale la aplicación en el espacio de trabajo
4. Copie el Bot User OAuth Token

### Microsoft Teams Workflows

Use un endpoint de Workflows con teams-workflows en vez de los conectores heredados de Office365. Verifique la autenticación real del endpoint y el ciclo de vida de propiedad/copropiedad del flujo. Guarde su URL firmada en un Secret; no suponga que un endpoint heredado de MessageCard es intercambiable.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.teams-workflows: |
    recipientUrls:
      deployments: $teams-webhook-deployments
      alerts: $teams-webhook-alerts
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  teams-webhook-deployments: REPLACE_WITH_TEAMS_WORKFLOWS_URL
  teams-webhook-alerts: REPLACE_WITH_TEAMS_WORKFLOWS_URL
```

### Correo electrónico (SMTP)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.email: |
    host: smtp.example.com
    port: 587
    username: $email-username
    password: $email-password
    from: argocd@example.com
    html: true
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  email-username: argocd@example.com
  email-password: your-smtp-password
```

### Webhook

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.webhook.custom: |
    url: https://api.example.com/webhooks/argocd
    headers:
    - name: Authorization
      value: $webhook-authorization
    - name: Content-Type
      value: application/json
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  webhook-authorization: Bearer REPLACE_WITH_RECEIVER_TOKEN
```

### GitHub (estado de commit)

Instale la GitHub App en el repositorio objetivo y conceda acceso de escritura a los estados de commit. Sustituya los ID y la clave privada de ejemplo por los valores de esa instalación.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.github: |
    appID: 123456
    installationID: 12345678
    privateKey: $github-privateKey
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-notifications-secret
  namespace: argocd
type: Opaque
stringData:
  github-privateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

### Grafana

Use un token de cuenta de servicio con los permisos necesarios para escribir anotaciones. Este motor espera apiUrl incluido /api y añade anotaciones. Evite establecer de forma predeterminada un token de administrador o una duración innecesariamente larga.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.grafana: |
    apiUrl: https://grafana.example.com/api
    apiKey: $grafana-api-key
```

### PagerDuty Events API v2

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.pagerdutyv2: |
    serviceKeys:
      production: $pagerduty-key-prod
      staging: $pagerduty-key-staging
```

## Disparadores {#triggers}

Estos son ejemplos definidos explícitamente, no supuestos sobre un catálogo instalado automáticamente. Sus entradas `send` hacen referencia a `template.app-status` a continuación. **Combine los fragmentos en un ConfigMap** junto con la configuración del servicio que haya seleccionado.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  context: |
    argocdUrl: https://argocd.example.com
  trigger.on-sync-succeeded: |
    - when: app.status?.operationState?.phase == 'Succeeded'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-sync-failed: |
    - when: app.status?.operationState?.phase in ['Failed', 'Error']
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-sync-running: |
    - when: app.status?.operationState?.phase == 'Running'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-sync-status-unknown: |
    - when: app.status?.sync?.status == 'Unknown'
      send:
      - app-status
  trigger.on-health-degraded: |
    - when: app.status?.health?.status == 'Degraded'
      send:
      - app-status
  trigger.on-deployed: |
    - when: app.status?.operationState?.phase == 'Succeeded' && app.status?.sync?.status == 'Synced' && app.status?.health?.status
        == 'Healthy'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
```

`?.` gestiona las Applications que aún no tienen `status` u `operationState`. El éxito de la sincronización por sí solo no significa que la aplicación esté lista. `on-deployed` requiere una operación realizada correctamente y el estado **Synced + Healthy** actual, lo que excluye un cambio nuevo OutOfSync con una operación realizada correctamente anterior.

### Condiciones personalizadas

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-production-deployed: |
    - when: app.metadata?.labels?.environment == 'production' && app.status?.operationState?.phase == 'Succeeded' &&
        app.status?.sync?.status == 'Synced' && app.status?.health?.status == 'Healthy'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-resource-failed: |
    - when: app.status?.resources != nil && any(app.status.resources, {#.health?.status == 'Degraded'})
      send:
      - app-status
  trigger.on-many-images: |
    - when: app.status?.summary?.images != nil && len(app.status.summary.images) > 5
      oncePer: app.metadata.generation
      send:
      - app-status
  trigger.on-long-sync: |
    - when: app.status?.operationState?.phase == 'Running' && app.status.operationState.startedAt != nil && time.Now().Sub(time.Parse(app.status.operationState.startedAt)).Minutes()
        > 10
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-declared-rollback: |
    - when: 'app.status?.operationState?.phase == ''Succeeded'' && app.status.operationState.operation?.info != nil
        && any(app.status.operationState.operation.info, {#.name == ''release-action'' && #.value == ''rollback''})'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-critical-failure: |
    - when: app.status?.operationState?.phase in ['Failed', 'Error'] && app.metadata?.labels?.tier == 'critical'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-production-namespace-failure: |
    - when: app.status?.operationState?.phase in ['Failed', 'Error'] && app.spec?.destination?.namespace != nil && app.spec.destination.namespace
        matches '^prod-.*$'
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
  trigger.on-utc-window: |
    - when: app.status?.operationState?.phase == 'Succeeded' && time.Now().UTC().Hour() >= 9 && time.Now().UTC().Hour()
        < 18
      oncePer: app.status.operationState.startedAt
      send:
      - app-status
```

- `summary.images` cuenta imágenes, no réplicas. Use `any(...)` para matrices de recursos y `matches` para expresiones regulares.
- Las condiciones de tiempo se ejecutan cuando se evalúa una Application. No son temporizadores precisos de diez minutos y no ponen en cola notificaciones para la próxima ventana laboral UTC.
- Las diferencias de revisión no demuestran un rollback. `on-declared-rollback` lee información explícita de la operación. Tras revisar un cambio de recuperación en Git, un flujo de trabajo de sincronización manual puede usar `argocd app sync my-app --info release-action=rollback`. La sincronización automática no añade este marcador automáticamente.

### Supervisión sostenida de OutOfSync

El `finishedAt` de la última operación no es la hora a la que comenzó OutOfSync. Para una condición continua de treinta minutos, recopile métricas de Argo CD con Prometheus y use una regla como esta. Requiere Prometheus Operator y etiquetas/namespaces que coincidan con su configuración de `ruleSelector` de Prometheus.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-sync-alerts
  namespace: monitoring
spec:
  groups:
  - name: argocd-sync
    rules:
    - alert: ArgoCDApplicationOutOfSync
      expr: argocd_app_info{sync_status="OutOfSync"} == 1
      for: 30m
      labels:
        severity: warning
      annotations:
        summary: Application {{ $labels.name }} has remained OutOfSync for 30 minutes
```

## Plantillas {#templates}

Esta plantilla común define formatos para Slack, Teams Workflows, correo electrónico HTML, webhook e incidentes. **Las suscripciones seleccionan los destinos**; incluir un formato de servicio no difunde a todos los proveedores. Suscriba PagerDuty/Opsgenie solo a los disparadores de fallo o Degraded. Este ejemplo no resuelve automáticamente los incidentes.

Esta versión del motor usa Go `text/template` con funciones Sprig. Escape los valores JSON con `toJson` y los valores HTML con `html`. Los campos se renderizan independientemente, por lo que las variables locales se declaran en cada campo. La plantilla gestiona la ausencia de estado, una revisión de operación única y `revisions` de múltiples fuentes. No reenvía mensajes de error sin procesar de la operación a canales externos.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  template.app-status: |
    message: |
      {{- $status := default (dict) .app.status -}}
      {{- $sync := default (dict) $status.sync -}}
      {{- $health := default (dict) $status.health -}}
      {{- $op := default (dict) $status.operationState -}}
      {{- $result := default (dict) $op.syncResult -}}
      {{- $applied := default (list) $result.revisions -}}
      {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
      {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
      Application {{.app.metadata.namespace}}/{{.app.metadata.name}}: phase={{default "None" $op.phase}}, sync={{default "Unknown" $sync.status}}, health={{default "Unknown" $health.status}}.
      Details: {{$url}}
    slack:
      attachments: |
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        [{
          "color": "#f4c030",
          "title": {{.app.metadata.name | toJson}},
          "title_link": {{$url | toJson}},
          "fields": [
            {"title":"Sync","value":{{default "Unknown" $sync.status | toJson}},"short":true},
            {"title":"Health","value":{{default "Unknown" $health.status | toJson}},"short":true},
            {"title":"Operation revision(s)","value":{{join ", " $applied | toJson}},"short":false}
          ]
        }]
    teams-workflows:
      title: 'Application status changed: {{.app.metadata.name}}'
      text: |-
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        Application {{.app.metadata.namespace}}/{{.app.metadata.name}}
        {{$url}}
      themeColor: Accent
      facts: |-
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        [{"name":"Sync","value":{{default "Unknown" $sync.status | toJson}}},{"name":"Health","value":{{default "Unknown" $health.status | toJson}}}]
    email:
      subject: '[Argo CD] Application status changed: {{.app.metadata.name}}'
      body: |-
        {{- $status := default (dict) .app.status -}}
        {{- $sync := default (dict) $status.sync -}}
        {{- $health := default (dict) $status.health -}}
        {{- $op := default (dict) $status.operationState -}}
        {{- $result := default (dict) $op.syncResult -}}
        {{- $applied := default (list) $result.revisions -}}
        {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
        {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
        <h2>Application status changed</h2><p>Application: {{.app.metadata.namespace | html}}/{{.app.metadata.name | html}}</p><p>Sync: {{default "Unknown" $sync.status | html}}; health: {{default "Unknown" $health.status | html}}</p><a href="{{$url | html}}">View in Argo CD</a>
    webhook:
      custom:
        method: POST
        body: |
          {{- $status := default (dict) .app.status -}}
          {{- $sync := default (dict) $status.sync -}}
          {{- $health := default (dict) $status.health -}}
          {{- $op := default (dict) $status.operationState -}}
          {{- $result := default (dict) $op.syncResult -}}
          {{- $applied := default (list) $result.revisions -}}
          {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
          {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
          {{ dict "event" "application-status" "application" .app.metadata.name "namespace" .app.metadata.namespace "uid" (default "" .app.metadata.uid) "project" (default "default" .app.spec.project) "phase" (default "" $op.phase) "syncStatus" (default "Unknown" $sync.status) "healthStatus" (default "Unknown" $health.status) "appliedRevisions" $applied "operationStartedAt" (default "" $op.startedAt) "url" $url | toJson }}
    pagerdutyv2:
      summary: 'Application status changed: {{.app.metadata.namespace}}/{{.app.metadata.name}}'
      severity: error
      source: argocd
      dedupKey: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}/application-status
    opsgenie:
      description: 'Application status changed: {{.app.metadata.namespace}}/{{.app.metadata.name}}'
      priority: P2
      alias: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}/application-status
```

`service.email.html: true` habilita cuerpos HTML. Teams usa el campo `teams-workflows` y los nombres de color de Adaptive Card. El nombre del servicio para `service.webhook.custom` es **custom**, con su cuerpo en `webhook.custom`; establezca `POST` explícitamente. Grafana usa el `message` común para su anotación.

| Función | Propósito |
|---|---|
| `upper`, `lower` | Cambiar mayúsculas y minúsculas |
| `default`, `dict`, `list` | Valores predeterminados y colecciones |
| `join`, `splitList` | Unir/dividir listas |
| `toJson` | Codificar valores JSON |
| `html` | Escapar caracteres especiales de HTML |

### Estado de commit de GitHub

Use disparadores/plantillas separados para el estado de commit. Este ejemplo está limitado a una fuente HTTPS de GitHub y publica solo cuando el resultado de la operación identifica su repositorio y revisión. Las fuentes múltiples, Helm/OCI y SSH requieren una asignación explícita. Los fallos antes de que se registre una revisión de resultado no se publican. `status.label` proporciona el contexto del estado de GitHub; `context` y `description` no son campos de este esquema de plantilla.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  trigger.on-github-deployed: |
    - when: app.spec?.source?.repoURL != nil && app.spec.source.repoURL startsWith 'https://github.com/' && app.spec?.sources
        == nil && app.status?.operationState?.syncResult?.revision != nil && app.status.operationState.syncResult?.source?.repoURL
        == app.spec.source.repoURL && app.status?.operationState?.phase == 'Succeeded' && app.status?.sync?.status ==
        'Synced' && app.status?.health?.status == 'Healthy'
      oncePer: app.status.operationState.startedAt
      send:
      - github-deployed
  trigger.on-github-failed: |
    - when: app.spec?.source?.repoURL != nil && app.spec.source.repoURL startsWith 'https://github.com/' && app.spec?.sources
        == nil && app.status?.operationState?.syncResult?.revision != nil && app.status.operationState.syncResult?.source?.repoURL
        == app.spec.source.repoURL && app.status?.operationState?.phase in ['Failed', 'Error']
      oncePer: app.status.operationState.startedAt
      send:
      - github-failed
  template.github-deployed: |
    github:
      repoURLPath: '{{.app.status.operationState.syncResult.source.repoURL}}'
      revisionPath: '{{.app.status.operationState.syncResult.revision}}'
      status:
        state: success
        label: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}
        targetURL: '{{.context.argocdUrl}}/applications/{{.app.metadata.namespace}}/{{.app.metadata.name}}'
  template.github-failed: |
    github:
      repoURLPath: '{{.app.status.operationState.syncResult.source.repoURL}}'
      revisionPath: '{{.app.status.operationState.syncResult.revision}}'
      status:
        state: failure
        label: argocd/{{.app.metadata.namespace}}/{{.app.metadata.name}}
        targetURL: '{{.context.argocdUrl}}/applications/{{.app.metadata.namespace}}/{{.app.metadata.name}}'
```

## Suscripciones {#subscriptions}

### Anotaciones de Application

Combine este **fragmento de metadata en una Application existente**; no es un manifiesto de Application independiente. Haga coincidir los nombres de destinatario configurados por cada servicio y seleccione las suscripciones que necesite. Los destinatarios múltiples se separan por **punto y coma**, no por comas.

```yaml
metadata:
  name: my-app
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.slack: deployments;alerts
    notifications.argoproj.io/subscribe.on-health-degraded.slack: alerts
    notifications.argoproj.io/subscribe.on-deployed.teams-workflows: deployments
    notifications.argoproj.io/subscribe.on-sync-failed.email: ops@example.com
    notifications.argoproj.io/subscribe.on-deployed.custom: ''
    notifications.argoproj.io/subscribe.on-github-deployed.github: ''
    notifications.argoproj.io/subscribe.on-github-failed.github: ''
```

### Disparadores predeterminados y suscripciones globales

`defaultTriggers` proporciona nombres de disparadores para anotaciones como `notifications.argoproj.io/subscribe.slack: alerts`. No crea suscripciones en todas las Applications. Use `subscriptions` para destinatarios administrados centralmente; `selector` coincide con las **etiquetas de Application**.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  defaultTriggers: |
    - on-sync-failed
    - on-health-degraded
  subscriptions: |
    - recipients:
      - slack:alerts
      triggers:
      - on-sync-failed
      - on-health-degraded
    - recipients:
      - email:ops@example.com
      triggers:
      - on-sync-failed
      selector: environment=production
```

### Suscripciones de AppProject

Combine este fragmento de metadata en el AppProject existente para cubrir sus Applications, conservando las políticas de fuente/destino/RBAC del capítulo anterior.

```yaml
metadata:
  name: production
  namespace: argocd
  annotations:
    notifications.argoproj.io/subscribe.on-sync-failed.slack: production-alerts
    notifications.argoproj.io/subscribe.on-health-degraded.pagerdutyv2: production
```

## Configuración avanzada {#advanced-configuration}

### oncePer y gestión de duplicados

`oncePer` reduce las notificaciones duplicadas para una condición mediante el valor de la expresión. No es un límite de solicitudes por segundo ni una garantía de entrega exactamente una vez. Los disparadores de operación aquí usan `operationState.startedAt` para distinguir nuevos intentos de sincronización en la misma revisión. Gestione los límites de velocidad en el servicio/puente receptor y haga idempotentes a los consumidores de webhook/SQS.

### Validación de consola

Guarde el ConfigMap compuesto como `notifications.yaml`. Estos comandos leen Application/AppProject mediante su kubeconfig actual y renderizan explícitamente en `console:stdout`. Los permisos y la entrega reales de Slack/Teams/GitHub/SQS requieren pruebas de integración independientes.

```bash
kubectl get application my-app -n argocd -o yaml > sample-application.yaml
argocd admin notifications trigger run on-deployed ./sample-application.yaml \
  --config-map ./notifications.yaml --secret :empty
argocd admin notifications template notify app-status ./sample-application.yaml \
  --config-map ./notifications.yaml --secret :empty --recipient console:stdout
```

## Integración con AWS {#aws-integration}

### Servicio SQS nativo

Esta versión proporciona un servicio `awssqs`. Una URL de AWS API o una cadena estática `Authorization: AWS4-HMAC-SHA256 ...` en un webhook genérico no firma una solicitud SigV4. Las credenciales de IRSA/Pod Identity por sí solas no hacen que el webhook genérico reconozca el firmante.

Primero aprovisione una **cola Standard** llamada `argocd-notifications` en la misma cuenta/región y asocie la cuenta de servicio de Notifications Controller con IRSA o EKS Pod Identity. La cadena de credenciales predeterminada del SDK evita aquí las claves de acceso estáticas. Sustituya los valores de cuenta/región/cola y combine la configuración de `context` anterior.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.awssqs: |
    queue: argocd-notifications
    region: ap-northeast-2
    account: '123456789012'
  trigger.on-aws-sync-completed: |
    - when: app.status?.operationState?.phase in ['Succeeded', 'Failed', 'Error']
      oncePer: app.status.operationState.startedAt
      send:
      - aws-app-event
  template.aws-app-event: |
    message: |
      {{- $status := default (dict) .app.status -}}
      {{- $sync := default (dict) $status.sync -}}
      {{- $health := default (dict) $status.health -}}
      {{- $op := default (dict) $status.operationState -}}
      {{- $result := default (dict) $op.syncResult -}}
      {{- $applied := default (list) $result.revisions -}}
      {{- if and (not $applied) $result.revision -}}{{- $applied = list $result.revision -}}{{- end -}}
      {{- $url := printf "%s/applications/%s/%s" (trimSuffix "/" .context.argocdUrl) .app.metadata.namespace .app.metadata.name -}}
      {{ dict "event" "sync-completed" "application" .app.metadata.name "namespace" .app.metadata.namespace "uid" (default "" .app.metadata.uid) "project" (default "default" .app.spec.project) "phase" (default "" $op.phase) "syncStatus" (default "Unknown" $sync.status) "healthStatus" (default "Unknown" $health.status) "appliedRevisions" $applied "operationStartedAt" (default "" $op.startedAt) "url" $url | toJson }}
```

Permisos de remitente de ejemplo para el rol del controlador, suponiendo cifrado administrado por SQS. Una clave KMS administrada por el cliente requiere además la política de claves apropiada y permisos de KMS.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueUrl",
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:ap-northeast-2:123456789012:argocd-notifications"
    }
  ]
}
```

Añada esta entrada a las anotaciones de una Application existente. El destinatario es un nombre de cola y anula la cola predeterminada del servicio.

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-aws-sync-completed.awssqs: argocd-notifications
```

El motor incluido establece un retraso de diez segundos en `SendMessage`. Las colas FIFO no admiten retraso por mensaje, por lo que no sustituya una cola FIFO en este ejemplo. No suponga que se envían los `messageAttributes` configurados; incluya los metadatos requeridos en el cuerpo del mensaje JSON.

### Integración con Lambda, SNS y EventBridge

Una ruta de integración compatible es **Notifications → SQS → Lambda → SNS o EventBridge**. Implemente y despliegue los recursos descendentes por separado; el ConfigMap no los crea.

| Salto | Configuración requerida |
|---|---|
| SQS → Lambda | Asignación de origen de eventos en la misma región; permisos de recibir/eliminar/atributos de cola; tiempo de espera de visibilidad ajustado al procesamiento; reintentos/DLQ |
| Lambda → SNS | Permiso `sns:Publish` del rol de ejecución en el tema objetivo; llamada firmada de AWS SDK |
| Lambda → EventBridge | `events:PutEvents` en el bus objetivo; inspeccione `FailedEntryCount` y los errores de las entradas individuales |
| Consumidor | Validación JSON; clave de idempotencia que considere UID de Application, evento, operationStartedAt y estado actual; configuración de respuesta de fallo parcial por lote de SQS |

Si se requiere un webhook de API Gateway, cree un puente autenticado por separado. Una API key/usage plan por sí sola no es autenticación. La revisión de este capítulo no aprovisionó recursos de AWS ni envió mensajes reales.

## Referencias

- [Notificaciones](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/)
- [Disparadores](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/triggers/)
- [Suscripciones](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/subscriptions/)
- [Teams Workflows](https://argo-cd.readthedocs.io/en/release-3.5/operator-manual/notifications/services/teams-workflows/)
- [Implementación de plantilla del motor](https://github.com/argoproj/notifications-engine/blob/0cff13b8a717/pkg/templates/service.go)
- [Implementación de SQS del motor](https://github.com/argoproj/notifications-engine/blob/0cff13b8a717/pkg/services/awssqs.go)
- [Lambda con SQS](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)

## Cuestionario

Ponga a prueba sus conocimientos con el [cuestionario de notificaciones](../../quizzes/gitops/argocd/08-notifications-quiz.md).
