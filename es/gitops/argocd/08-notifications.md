# Notificaciones de ArgoCD

> **Versión utilizada en la revisión**: Argo CD 3.5.2 (con Notifications Engine 0cff13b8a717 incluido). Tras revisar las notas de la versión, se actualizó al parche 3.5.4, que utiliza el mismo commit de Notifications Engine; los ejemplos no se volvieron a ejecutar.
> **Última actualización**: 12 de octubre de 2026

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
| Varios servicios | Slack, Teams, correo electrónico, webhook, GitHub y otros |
| Disparadores flexibles | Activación de notificaciones cuando se cumplen determinadas condiciones |
| Plantillas Go | Sintaxis avanzada para dar formato a los mensajes |
| Modelo de suscripción | Suscripciones de notificación por aplicación |
| Catálogo de ejemplos | Definiciones opcionales de disparadores y plantillas que puede incorporar a su configuración |

## Arquitectura {#architecture}

![Flujo de las notificaciones de ArgoCD: los eventos de Application llegan al controlador de Notifications, que evalúa los disparadores y genera los mensajes a partir de las plantillas. Después, envía los mensajes a los destinatarios de las suscripciones configuradas que correspondan.](../../.gitbook/assets/en-gitops-argocd-08-notifications-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-gitops-argocd-08-notifications-0.html)

### Controlador y configuración

La instalación completa de Argo CD 3.5.4 incluye el controlador de Notifications. Compruebe que esté habilitado en su instalación o en los valores de Helm. El archivo notifications_catalog/install.yaml contiene configuración de ejemplo; no instala un controlador que falte. Incorpore las entradas del catálogo que necesite a su ConfigMap y Secret existentes.

```bash
kubectl get deployment argocd-notifications-controller -n argocd
```

## Servicios de notificación {#notification-services}

Reúna estos fragmentos de datos en una única configuración de argocd-notifications-cm. No aplique cada ejemplo independiente de forma que sustituya el mismo ConfigMap o Secret. Guarde los tokens, las URL firmadas de webhooks y las claves privadas en valores protegidos de argocd-notifications-secret, fuera de Git. Los nombres de los servicios, las plantillas, los disparadores y las suscripciones deben corresponderse.

### Slack

Configure chat:write e invite al bot a los canales previstos. chat:write.public solo es necesario para publicar en canales públicos a los que el bot no se haya unido. signingSecret no sustituye una URL de Incoming Webhook.

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

Configuración del bot de Slack:
1. Cree una aplicación de Slack en https://api.slack.com/apps
2. Añada `chat:write`; utilice `chat:write.public` solo si el caso de uso indicado lo requiere
3. Instale la aplicación en el espacio de trabajo
4. Copie el token OAuth del usuario del bot

### Microsoft Teams Workflows

Utilice un endpoint de Workflows con teams-workflows en lugar de los antiguos conectores Office365. Compruebe la autenticación real del endpoint y cómo se mantiene la propiedad y la copropiedad del flujo durante su ciclo de vida. Guarde su URL firmada en un Secret; no dé por supuesto que puede sustituirse por un endpoint antiguo de MessageCard.

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

Instale la aplicación de GitHub en el repositorio de destino y concédale permiso de escritura sobre los estados de commit. Sustituya los ID y la clave privada del ejemplo por los valores de esa instalación.

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

Utilice un token de cuenta de servicio con permiso para escribir anotaciones. Este motor requiere que apiUrl incluya /api y añade el segmento annotations a esa ruta. Evite utilizar por defecto un token de administrador o un token con una vigencia innecesariamente larga.

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

Estos ejemplos definen los disparadores de forma explícita; no dependen de que un catálogo se instale automáticamente. Sus entradas `send` hacen referencia a `template.app-status`, definido más adelante. **Reúna los fragmentos en un único ConfigMap**, junto con la configuración de los servicios que haya seleccionado.

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

`?.` permite trabajar con Applications que aún no tienen `status` u `operationState`. Una sincronización correcta no demuestra por sí sola que la aplicación esté lista. `on-deployed` requiere que la operación haya finalizado correctamente y que el estado actual sea **Synced + Healthy**. Así se excluye un cambio nuevo OutOfSync aunque exista una operación anterior que finalizara correctamente.

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

- `summary.images` cuenta imágenes, no réplicas. Utilice `any(...)` para los arrays de recursos y `matches` para las expresiones regulares.
- Las condiciones temporales se evalúan cuando se evalúa una Application. No son temporizadores exactos de diez minutos ni dejan notificaciones en cola hasta la siguiente franja laboral UTC.
- Una diferencia entre revisiones no demuestra que se haya realizado un rollback. `on-declared-rollback` lee información explícita de la operación. Después de revisar en Git el cambio de recuperación, un workflow de sincronización manual puede utilizar `argocd app sync my-app --info release-action=rollback`. La sincronización automática no añade este marcador por sí sola.

### Supervisión de un estado OutOfSync persistente

El campo `finishedAt` de la última operación no indica cuándo comenzó el estado OutOfSync. Para detectar que ese estado persista durante treinta minutos, recopile las métricas de Argo CD con Prometheus y utilice una regla como la siguiente. Se necesita Prometheus Operator, y las etiquetas y los namespaces deben coincidir con la configuración de `ruleSelector` de Prometheus.

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

Esta plantilla común define formatos para Slack, Teams Workflows, correo electrónico HTML, webhooks e incidentes. **Las suscripciones seleccionan los destinos**: incluir el formato de un servicio no envía mensajes a todos los proveedores. Suscriba PagerDuty y Opsgenie únicamente a disparadores de fallo o de estado Degraded. El ejemplo no resuelve los incidentes automáticamente.

Esta versión del motor utiliza Go `text/template` con funciones Sprig. Escape los valores JSON con `toJson` y los valores HTML con `html`. Cada campo se genera de forma independiente, por lo que sus variables locales se declaran dentro de él. La plantilla admite que falte el estado, una única revisión de operación y `revisions` de varias fuentes. No reenvía los mensajes de error originales de las operaciones a canales externos.

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

`service.email.html: true` habilita los cuerpos de mensaje HTML. Teams utiliza el campo `teams-workflows` y los nombres de colores de Adaptive Card. El nombre del servicio definido mediante `service.webhook.custom` es **custom**; el cuerpo se configura bajo `webhook.custom`. Establezca `POST` de forma explícita. Grafana utiliza el `message` común para su anotación.

| Función | Uso |
|---|---|
| `upper`, `lower` | Convertir letras a mayúsculas o minúsculas |
| `default`, `dict`, `list` | Definir valores predeterminados y colecciones |
| `join`, `splitList` | Unir o dividir listas |
| `toJson` | Codificar valores JSON |
| `html` | Escapar los caracteres especiales de HTML |

### Estado de commit de GitHub

Utilice disparadores y plantillas independientes para los estados de commit. Este ejemplo solo admite una fuente de GitHub con URL HTTPS y publica el estado cuando el resultado de la operación identifica el repositorio y la revisión correspondientes. Las configuraciones con varias fuentes, Helm, OCI o SSH requieren una asignación explícita. Si el fallo ocurre antes de que se registre la revisión del resultado, no se publica. `status.label` define el contexto del estado en GitHub; `context` y `description` no son campos de este esquema de plantilla.

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

Incorpore este **fragmento de metadata a una Application existente**; no es un manifiesto completo de Application. Utilice los nombres de destinatarios configurados en cada servicio y seleccione las suscripciones que necesite. Para indicar varios destinatarios, sepárelos con **punto y coma**, no con comas.

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

`defaultTriggers` proporciona los nombres de los disparadores para anotaciones como `notifications.argoproj.io/subscribe.slack: alerts`. No crea una suscripción en todas las Applications. Utilice `subscriptions` para gestionar los destinatarios de forma centralizada; `selector` selecciona mediante las **etiquetas de Application**.

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

Incorpore este fragmento de metadata al AppProject existente para cubrir sus Applications. Conserve las políticas de origen, destino y RBAC del capítulo anterior.

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

`oncePer` utiliza el valor de la expresión para reducir las notificaciones duplicadas de una condición. No limita las solicitudes por segundo ni garantiza que cada mensaje se entregue exactamente una vez. Los disparadores de operación del ejemplo utilizan `operationState.startedAt` para distinguir nuevos intentos de sincronización de la misma revisión. Gestione los límites de frecuencia en el servicio receptor o en el componente que conecta los servicios, y haga idempotentes los consumidores de webhooks y SQS.

### Validación de consola

Guarde el ConfigMap que reúne la configuración como `notifications.yaml`. Estos comandos leen la Application y el AppProject mediante su kubeconfig actual y generan explícitamente la salida en `console:stdout`. Los permisos y la entrega reales mediante Slack, Teams, GitHub o SQS requieren pruebas de integración independientes.

```bash
kubectl get application my-app -n argocd -o yaml > sample-application.yaml
argocd admin notifications trigger run on-deployed ./sample-application.yaml \
  --config-map ./notifications.yaml --secret :empty
argocd admin notifications template notify app-status ./sample-application.yaml \
  --config-map ./notifications.yaml --secret :empty --recipient console:stdout
```

## Integración con AWS {#aws-integration}

### Servicio SQS nativo

Esta versión incluye el servicio `awssqs`. Configurar una URL de la API de AWS o una cadena estática `Authorization: AWS4-HMAC-SHA256 ...` en un webhook genérico no firma la solicitud con SigV4. Proporcionar credenciales mediante IRSA o Pod Identity tampoco hace que el webhook genérico firme automáticamente las solicitudes.

Primero, aprovisione una **cola Standard** llamada `argocd-notifications` en la misma cuenta y región, y asocie el ServiceAccount del controlador de Notifications con IRSA o EKS Pod Identity. La cadena de credenciales predeterminada del SDK evita utilizar claves de acceso estáticas. Sustituya los valores de cuenta, región y cola, e incorpore la configuración de `context` anterior.

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

El siguiente ejemplo concede permisos de envío al rol del controlador y presupone cifrado administrado por SQS. Si utiliza una clave KMS administrada por el cliente, también debe configurar su política y los permisos KMS correspondientes.

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

Añada esta entrada a las anotaciones de una Application existente. El destinatario es el nombre de una cola y sustituye la cola predeterminada del servicio.

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-aws-sync-completed.awssqs: argocd-notifications
```

El motor incluido configura un retraso de diez segundos en `SendMessage`. Las colas FIFO no admiten retrasos por mensaje, por lo que no debe utilizarlas en este ejemplo. No dé por supuesto que se envían los `messageAttributes` configurados: incluya los metadatos necesarios en el cuerpo JSON del mensaje.

### Integración con Lambda, SNS y EventBridge

Una ruta de integración compatible es **Notifications → SQS → Lambda → SNS o EventBridge**. Implemente y despliegue por separado los recursos que procesan los mensajes después de Notifications; el ConfigMap no los crea.

| Conexión | Configuración necesaria |
|---|---|
| SQS → Lambda | Mapeo de origen de eventos en la misma región; permisos para recibir y eliminar mensajes y consultar los atributos de la cola; tiempo de visibilidad adecuado al procesamiento; reintentos y DLQ |
| Lambda → SNS | Permiso `sns:Publish` del rol de ejecución sobre el tema de destino; llamada firmada mediante el SDK de AWS |
| Lambda → EventBridge | Permiso `events:PutEvents` sobre el bus de destino; comprobación de `FailedEntryCount` y de los errores de cada entrada |
| Consumidor | Validación JSON; clave de idempotencia que considere el UID de Application, el evento, operationStartedAt y el estado actual; configuración de respuestas para fallos parciales de lotes SQS |

Si necesita un webhook de API Gateway, cree un componente de conexión con autenticación propia. Una clave de API y un plan de uso no bastan para autenticar solicitudes. La revisión descrita en el original no aprovisionó recursos de AWS ni envió mensajes reales.

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
