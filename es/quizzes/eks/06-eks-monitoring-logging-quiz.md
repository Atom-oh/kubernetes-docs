# Cuestionario sobre monitoreo y registro de Amazon EKS

> **Última actualización**: 16 de octubre de 2026

Este cuestionario evalúa tu comprensión de las funciones, herramientas y prácticas recomendadas de monitoreo y registro de Amazon EKS.

## Descripción general del cuestionario
- Monitoreo de clústeres EKS
- Registro de contenedores y aplicaciones
- Recopilación y análisis de métricas de rendimiento
- Alertas y detección de anomalías
- Arquitectura de monitoreo y registro
- Prácticas recomendadas y herramientas

## Preguntas de opción múltiple

### 1. ¿Qué principio debe guiar el diseño de una solución de monitoreo para EKS?

- A. CloudWatch no puede recopilar trazas de aplicaciones.
- B. Instalar Grafana por sí solo recopila automáticamente todas las métricas de los Pods.
- C. Seleccionar las señales necesarias, configurar los recolectores y fuentes de datos bajo control del equipo, y verificar la entrega y la cobertura.
- D. Instalar CloudWatch, Prometheus, Grafana y X-Ray siempre garantiza visibilidad completa.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Seleccionar y verificar el diseño de señales, recolectores y backends.**

**Explicación:**

Una combinación de herramientas puede resultar útil, pero el diseño depende de las señales necesarias y de las restricciones operativas. CloudWatch admite más que métricas básicas de infraestructura; también ofrece trazas/APM de Application Signals en cargas de trabajo compatibles. Grafana puede consultar fuentes de datos de AWS y de trazas, pero la interfaz no recopila por sí sola todas las señales. Es necesario conectar de forma explícita los recolectores, la instrumentación, las identidades, los endpoints accesibles y las configuraciones compatibles; ninguna lista de productos garantiza una cobertura completa.

**Conserva las capas útiles:**

| Capa | Ejemplos de señales | Dependencia importante |
| --- | --- | --- |
| Infraestructura | CPU/memoria de nodos, disco, red | Recolector de nodos compatible y dimensiones de métricas correctas |
| Kubernetes | Estado de objetos, disponibilidad, actividad de la API | Permisos de exporter/API/auditoría y destinos reales |
| Aplicación | Latencia de solicitudes, errores, métricas de negocio | Instrumentación de la aplicación y esquema de métricas acotado |
| Solicitudes distribuidas | Spans de trazas y relaciones entre servicios | Propagación de contexto, muestreo y exportación correcta |

**Secuencia de implementación:**

1. Sigue el [capítulo fuente](../../eks/06-eks-monitoring-logging.md) para revisar el catálogo/esquema/identidades del complemento CloudWatch que controla el equipo. Deben revisarse la configuración de Auto Monitor versión 5+ y los reinicios; antes de instalar otro agente en cargas ya instrumentadas, comprueba los posibles conflictos.
2. Si necesitas recopilación o consultas de Prometheus, usa los valores KPS92.9.0 de la fuente y prepara el almacenamiento, el Secret de Grafana y los requisitos previos de CA para servir kubelet. El Operator gestiona ServiceMonitor/PrometheusRule; una instalación independiente de Prometheus no es equivalente. Tras la instalación, verifica los destinos reales.
3. Para la ruta explícita de ADOT, usa el ejemplo v1beta1 de Operator0.158/Collector0.50 de la fuente, con configuración como objeto, TLS y su ServiceAccount preparado. La versión de Collector no incluye el manifiesto de instalación de Operator. Esta ruta, solo para trazas, envía spans a X-Ray; las aplicaciones siguen necesitando instrumentación y propagación.
4. Para AMP, configura el endpoint real de remote write del workspace y la identidad de escritura. Configura por separado la identidad de consulta/fuente de datos de Grafana/AMG; AMG12+ usa el complemento de AMP. Un exporter awsemf publica en CloudWatch, no automáticamente en AMP.

**Ejemplos de rutas de datos:**

```text
EKS control-plane logs -------------------------------> CloudWatch Logs
Container stdout/stderr -> chosen log collector ------> configured log store
Application spans ------> ADOT OTLP receiver ----------> X-Ray
Metric targets ----------> Prometheus -----------------> local TSDB
                              |-- SigV4 remote_write -> AMP
Grafana/AMG -- configured queries --> Prometheus / AMP / CloudWatch / X-Ray
```

Estas son rutas que pueden elegirse, no una afirmación de que cada recolector exporte a todos los backends. Antes de depender de los dashboards, verifica permisos, TLS, descubrimiento/selectores, datos descartados y consultas representativas. Define prioridades de alertas y escalamiento, controla la cardinalidad, el muestreo y la retención, y prueba cualquier respuesta automatizada por separado.

**Ejemplo de planificación con Terraform:**

El siguiente ejemplo de recursos usa AWS provider 6.69.1. Presupone la cuenta/Región elegida, un rol existente y revisado para el workspace de Grafana, una versión compatible de AMG y una configuración apta de IAM Identity Center. Los recursos existentes requieren el procedimiento de importación/cambio de su propietario. El nombre del grupo de logs de la aplicación coincide con la ruta del recolector de la fuente; no crees un segundo propietario para un grupo que ya administre un complemento u otra pila.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "grafana_workspace_role_arn" {
  type = string
}

variable "grafana_version" {
  type        = string
  description = "A reviewed AMG version supported in the selected Region."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_prometheus_workspace" "eks_monitoring" {
  alias = "${var.cluster_name}-monitoring"
}

resource "aws_grafana_workspace" "eks_monitoring" {
  name                     = "${var.cluster_name}-monitoring"
  account_access_type      = "CURRENT_ACCOUNT"
  authentication_providers = ["AWS_SSO"]
  permission_type          = "CUSTOMER_MANAGED"
  role_arn                 = var.grafana_workspace_role_arn
  grafana_version          = var.grafana_version
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/containerinsights/${var.cluster_name}/application"
  log_group_class   = "STANDARD"
  retention_in_days = 30
}

output "amp_workspace_id" {
  value = aws_prometheus_workspace.eks_monitoring.id
}

output "amp_prometheus_endpoint" {
  value = aws_prometheus_workspace.eks_monitoring.prometheus_endpoint
}

output "grafana_workspace_id" {
  value = aws_grafana_workspace.eks_monitoring.id
}
```

Esto define recursos, no una ruta funcional de recopilación o inicio de sesión. Configura los permisos de consulta del rol para el ARN real del workspace, asigna usuarios/grupos, agrega fuentes de datos y conecta los recolectores mediante los ID/endpoints devueltos. CUSTOMER_MANAGED deja explícitamente la gestión de IAM en manos del propietario; el fragmento anterior de SERVICE_MANAGED/data_sources no demostraba que un workspace creado mediante API tuviera esos roles y conexiones. Revisa por separado los requisitos de cifrado, retención, acceso y costo. En esta auditoría no se ejecutaron un plan/aplicación de Terraform, un inicio de sesión ni una consulta de telemetría en vivo.

**Por qué las otras opciones son incorrectas:** A subestima las capacidades actuales de CloudWatch; B confunde la visualización con la recopilación; D trata la instalación como garantía de cobertura. Los scripts personalizados pueden seguir siendo útiles para automatización y comprobaciones acotadas si se definen claramente su propietario, errores y alcance.

</details>

### 2. ¿Qué enfoque conecta correctamente los logs de contenedores con la retención y el análisis centralizados?

- A. Tratar las copias manuales periódicas de archivos de nodos como una canalización de logs duradera y completa.
- B. Suponer que los archivos dentro de un contenedor siempre sobreviven a la sustitución del contenedor y del nodo.
- C. Usar un recolector bajo control del equipo, con el parser de runtime, permisos, almacenamiento y backend configurados correctamente.
- D. Instalar dos recolectores para los mismos archivos y suponer que así se garantiza una entrega sin pérdidas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Configurar y verificar una ruta de recopilación bajo control del equipo.**

**Explicación:**

Normalmente, las aplicaciones deben escribir registros estructurados apropiados en stdout/stderr, mientras la plataforma proporciona la recopilación y la retención. stdout es una buena interfaz, pero no es por sí mismo un almacén centralizado y duradero. Un recolector puede agregar análisis sintáctico, filtrado, búferes y enrutamiento; la rotación, los búferes finitos, la pérdida de nodos y los reintentos siguen afectando la cobertura y los duplicados. Controla el acceso, los campos sensibles y la retención, en lugar de afirmar que un recolector garantiza la integridad o una entrega sin pérdidas.

**Una base conectada de Fluent Bit:**

Usa el [capítulo fuente](../../eks/06-eks-monitoring-logging.md) en vez de aplicar manifiestos ajenos de la rama master. Su ejemplo independiente usa AWS chart0.2.0/image3.4.14, configuración nativa de cloudWatchLogs, análisis CRI, logs de nodos de solo lectura, almacenamiento separado para estado/búferes y un post-renderer de RBAC revisado. Prepara el grupo de logs y la identidad IAM reales. Si el complemento CloudWatch ya controla Fluent Bit, usa la configuración de ese propietario en lugar de crear accidentalmente un segundo lector.

Para enviar también a OpenSearch, combina este overlay de la fuente con sus valores base completos y el post-renderer del procedimiento de instalación/actualización del propietario:

```yaml
opensearch:
  enabled: true
  host: vpc-eks-logs-EXAMPLE.us-west-2.es.amazonaws.com
  port: '443'
  tls: 'On'
  awsAuth: 'On'
  awsRegion: us-west-2
  index: eks-logs
  generateId: 'On'
  suppressTypeName: 'On'
  extraOutputs: 'tls.verify On

    storage.total_limit_size 512M

    '
```

Sustituye el endpoint/Región por los valores inspeccionados del dominio. Los permisos de SigV4, la política del dominio, el mapeo de roles FGAC y la verificación de TLS son requisitos separados. No combines credenciales de autenticación básica con SigV4 en una misma solicitud. Cada salida tiene su propio comportamiento de éxito/reintento; tener éxito en CloudWatch no demuestra que la entrega a OpenSearch funcione. Usa plantillas de accessor de registros compatibles y un nombre de stream alternativo; `log_stream_prefix` no expande arbitrariamente campos de registros como si fueran variables de shell.

**Alternativa de Fluentd: contratos explícitos de plugins y entradas:**

Fluentd sigue siendo una opción si la imagen controlada por el equipo incluye el parser necesario y los plugins de metadatos de Kubernetes y OpenSearch. Antes de tratar el cuerpo de la aplicación como JSON, debe decodificarse el sobre de containerd/CRI-O. Configura la entrada tail, los permisos de metadatos, el almacenamiento de posiciones/búferes de cada recolector y la configuración montada; lo siguiente es solo un fragmento de salida de OpenSearch, no una instalación completa de ConfigMap/DaemonSet:

```text
<match kubernetes.**>
  @type opensearch
  ssl_verify true
  logstash_format false
  include_timestamp true
  index_name eks-logs
  suppress_type_name true
  <endpoint>
    url "#{ENV.fetch('OPENSEARCH_URL')}"
    region "#{ENV.fetch('AWS_REGION')}"
    assume_role_arn "#{ENV.fetch('AWS_ROLE_ARN')}"
    assume_role_web_identity_token_file "#{ENV.fetch('AWS_WEB_IDENTITY_TOKEN_FILE')}"
  </endpoint>
  <buffer>
    @type file
    path /var/lib/fluentd/opensearch
    total_limit_size 256m
    chunk_limit_size 2m
    retry_timeout 1h
    overflow_action block
  </buffer>
</match>
```

Esto usa los campos de endpoint IRSA del plugin oficial fluent-plugin-opensearch y un índice fijo. Prepara OPENSEARCH_URL y las variables de entorno del archivo de token/rol inyectadas por IRSA. `logstash_format=true` ignora `index_name`; las expresiones arbitrarias de índice por Pod no sustituyen un diseño verificado de enrutamiento/retención. Elige índices/alias acotados y revisa las políticas de rollover. Los búferes de archivos necesitan una ruta de almacenamiento escribible y aislada; bloquear/reintentar aún puede perder logs no leídos después de una rotación o pérdida del nodo. La composición de plugin/entrada no se ejecutó en esta auditoría.

**La recopilación de logs de ADOT es compatible con los componentes seleccionados:**

ADOT0.50.0 incluye filelog, file_storage y awscloudwatchlogs. El exporter de CloudWatch Logs correspondiente de upstream0.158 está marcado como alpha; este es un ejemplo específico de versión con requisitos previos explícitos de runtime, no una afirmación de que esté listo para producción. Úsalo como recolector alternativo para el conjunto de datos seleccionado, no como duplicado accidental de Fluent Bit.

Prepara Operator0.158, el namespace de registro y ServiceAccount adot-logs con su rol IRSA revisado y permisos de escritura en AWS Logs. Limita la confianza al proveedor OIDC de este clúster, sub=system:serviceaccount:logging:adot-logs y aud=sts.amazonaws.com; proporciona la ruta de red requerida para STS/Logs. El ejemplo es para nodos EC2 Linux estándar y necesita permiso de admisión para un agente de nodo root con `/var/log/pods` montado como solo lectura y un directorio de estado escribible dedicado. El filtro de inclusión del namespace predeterminado limita los datos exportados; no convierte el montaje del host en todo el nodo en una frontera de seguridad del sistema de archivos. Revisa la ubicación/taints de los nodos, la propiedad de archivos y la política del namespace. Configura los valores reales de Región/grupo de logs antes del despliegue:

```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: adot-logs
  namespace: logging
spec:
  mode: daemonset
  image: public.ecr.aws/aws-observability/aws-otel-collector:v0.50.0
  serviceAccount: adot-logs
  nodeSelector:
    kubernetes.io/os: linux
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: eks.amazonaws.com/compute-type
            operator: NotIn
            values: [fargate, auto, hybrid]
  env:
  - name: AWS_REGION
    value: us-west-2
  - name: AWS_EC2_METADATA_DISABLED
    value: "true"
  - name: K8S_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
  - name: LOG_GROUP_NAME
    value: /aws/containerinsights/my-owned-cluster/application
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 512Mi
  podSecurityContext:
    runAsUser: 0
    runAsGroup: 0
    runAsNonRoot: false
    seccompProfile:
      type: RuntimeDefault
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: [ALL]
  volumes:
  - name: pod-logs
    hostPath:
      path: /var/log/pods
      type: Directory
  - name: collector-state
    hostPath:
      path: /var/lib/adot-logs
      type: DirectoryOrCreate
  volumeMounts:
  - name: pod-logs
    mountPath: /var/log/pods
    readOnly: true
  - name: collector-state
    mountPath: /var/lib/adot-logs
  config:
    extensions:
      file_storage:
        directory: /var/lib/adot-logs/checkpoints
        create_directory: true
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      filelog:
        include: [/var/log/pods/default_*/*/*.log]
        include_file_path: true
        start_at: end
        storage: file_storage
        retry_on_failure:
          enabled: true
          max_elapsed_time: 5m
        operators:
        - type: container
          add_metadata_from_filepath: true
          max_log_size: 1MiB
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 384
        spike_limit_mib: 64
      batch: {}
    exporters:
      awscloudwatchlogs:
        region: us-west-2
        log_group_name: ${env:LOG_GROUP_NAME}
        log_stream_name: ${env:K8S_NODE_NAME}
        log_retention: 30
        raw_log: false
        sending_queue:
          num_consumers: 2
          queue_size: 100
    service:
      extensions: [file_storage, health_check]
      pipelines:
        logs:
          receivers: [filelog]
          processors: [memory_limiter, batch]
          exporters: [awscloudwatchlogs]
```

El operador de contenedores gestiona los sobres CRI/registros parciales y deriva los metadatos del Pod de log.file.path. Un parser JSON genérico sobre líneas CRI sin procesar es incorrecto. El nombre del stream se obtiene del nombre del nodo mediante la API Downward y la sustitución de variables del Collector, no mediante marcadores de posición no compatibles como {pod_name}.{container_name}.

El exporter puede crear grupos/streams y `log_retention` se aplica a los grupos nuevos; configura la retención existente mediante el propietario del grupo de logs. El manejo EMF documentado puede anular los nombres de grupo/stream configurados, así que limita el ámbito IAM de destino e inspecciona el formato real de los datos. Una cadena de configuración no es una frontera de autorización.

file_storage conserva los offsets del receptor, no cada lote que aún no se exportó. El ejemplo usa una cola de envío en memoria y reintentos finitos; el estado de checkpoint, los lotes y los datos hostPath tienen comportamientos de fallo/ciclo de vida distintos. start_at=end omite el contenido existente durante la lectura inicial si no hay offsets guardados. Supervisa reintentos, errores de cola/pérdida/almacenamiento y rotación de nodos. En esta auditoría no se probaron el proceso Collector, el montaje, el flujo de credenciales de AWS ni la ingesta.

**Comprobaciones de análisis e infraestructura:**

Para el esquema fuente de Fluent Bit, inspecciona los errores estructurados con los campos reales de namespace/contenedor. El wrapper de ADOT u otro recolector puede producir un esquema almacenado diferente:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message
| filter kubernetes.namespace_name = "default"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 100
```

Un ejemplo independiente de inspección con Terraform consulta un dominio OpenSearch existente y aprobado:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.69.1"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "opensearch_domain_name" {
  type        = string
  description = "Existing domain approved for this workload's logs"
}

provider "aws" {
  region = var.aws_region
}

data "aws_opensearch_domain" "eks_logs" {
  domain_name = var.opensearch_domain_name
}

output "opensearch_endpoint" {
  value = coalesce(
    data.aws_opensearch_domain.eks_logs.endpoint_v2,
    data.aws_opensearch_domain.eks_logs.endpoint
  )
}

output "opensearch_domain_arn" {
  value = data.aws_opensearch_domain.eks_logs.arn
}
```

La fuente de datos no configura red, IAM/política del dominio, FGAC ni entrega. Mantén separada la administración de la ingesta, evita contraseñas maestras en el código/estado y revisa cualquier migración de recursos/direcciones. Las consultas y pruebas de acceso requieren el entorno real; la validación de Terraform no las realiza.

**Por qué las otras opciones son incorrectas:** La inspección manual de archivos es útil para diagnóstico, pero no es una canalización centralizada completa. El ciclo de vida de contenedores/nodos y los tipos de volumen determinan qué archivos sobreviven. Los lectores duplicados pueden duplicar datos/costos y aun así fallar; los búferes y reintentos requieren capacidad medida y pruebas de fallo.

Referencias: [componentes ADOT](https://github.com/aws-observability/aws-otel-collector/tree/v0.50.0), [parser de contenedor](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.158.0/pkg/stanza/docs/operators/container.md), [exporter CloudWatch Logs](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awscloudwatchlogsexporter), [plugin OpenSearch de Fluentd](https://github.com/fluent/fluent-plugin-opensearch).

</details>

### 3. ¿Qué enfoque crea una ruta de alertas efectiva y verificable para EKS?

- A. Suponer que la revisión manual de logs garantiza una detección inmediata.
- B. Crear una sola alarma de CloudWatch y suponer que cubre todos los fallos de Kubernetes/aplicaciones.
- C. Crear un ConfigMap arbitrario alertmanager-config y suponer que el Operator lo consume.
- D. Seleccionar las señales necesarias, conectar reglas de métricas/eventos con receptores autorizados y probar cada ruta de entrega.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Conectar y verificar las rutas de alerta necesarias.**

**Explicación:**

Las alarmas de CloudWatch, Prometheus/Alertmanager y EventBridge cubren necesidades distintas de señales/enrutamiento y pueden combinarse de forma deliberada. CloudWatch también admite métricas personalizadas/de aplicaciones, mientras Prometheus puede consumir exporters apropiados de AWS; no debe descartarse ninguno con una afirmación genérica de que solo sirve para infraestructura. La instalación por sí sola no establece cobertura de métricas, umbrales correctos, permisos de publicación ni entrega satisfactoria.

**Las reglas de métricas deben coincidir con series y unidades reales:**

La PrometheusRule siguiente usa los selectores KPS de la fuente y series reales de node-exporter/kube-state-metrics. Los cálculos de CPU y memoria disponible producen explícitamente porcentajes, por lo que un umbral de 80 tiene sentido. CrashLoopBackOff usa el motivo de espera y no cualquier reinicio; se incluye Ready=false en un Pod Running, pero se excluyen los Pods terminales. Al combinar clústeres, agrega una identidad estable de clúster y antes de desplegar reglas duplicadas comprueba si ya hay reglas equivalentes incluidas en el paquete:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-observability-alerts
  namespace: monitoring
  labels:
    release: monitoring
spec:
  groups:
  - name: eks-observability-example
    rules:
    - alert: NodeHighCPU
      expr: (100 * (1 - avg by (cluster, instance) (max by (cluster, instance, cpu) (rate(node_cpu_seconds_total{job="node-exporter",mode="idle"}[5m]))))) > 80
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High non-idle CPU on {{ $labels.instance }}
        description: The node-exporter percentage has exceeded the example threshold; inspect workload and metric health.
    - alert: NodeMemoryFilling
      expr: (100 * (1 - max by (cluster, instance) (node_memory_MemAvailable_bytes{job="node-exporter"}) / max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}))) > 80 and on (cluster, instance) (max by (cluster, instance) (node_memory_MemTotal_bytes{job="node-exporter"}) > 0)
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Low available memory on {{ $labels.instance }}
        description: This is a MemAvailable-based estimate, not a MemoryPressure condition or Pod request utilization.
    - alert: KubernetesPodCrashLooping
      expr: max by (cluster, namespace, pod, uid, container) (max_over_time(kube_pod_container_status_waiting_reason{job="kube-state-metrics",reason="CrashLoopBackOff"}[5m])) >= 1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: CrashLoopBackOff observed for {{ $labels.namespace }}/{{ $labels.pod }}
        description: Inspect container {{ $labels.container }} logs and events; the rule tracks recent waiting reasons, not a restart-count guarantee.
    - alert: PodNotReady
      expr: (max by (cluster, namespace, pod, uid) (kube_pod_status_ready{job="kube-state-metrics",condition="true"}) == 0) and on (cluster, namespace, pod, uid) (max by (cluster, namespace, pod, uid) (kube_pod_status_phase{job="kube-state-metrics",phase=~"Pending|Running|Unknown"}) == 1)
      for: 15m
      labels:
        severity: warning
      annotations:
        summary: Active Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready
        description: Inspect Ready conditions and probes; terminal Succeeded/Failed Pods are excluded from this example.
```

Estos umbrales y tiempos de espera son ilustrativos. MemAvailable estima la memoria recuperable disponible; no es la condición MemoryPressure de kubelet ni un porcentaje de las solicitudes de los Pods. Las series ausentes u obsoletas no significan un estado saludable ni un uso de cero. Supervisa por separado los fallos de scrape y de evaluación de reglas.

**Conecta la configuración real de Alertmanager:**

Usa el Secret alertmanager-routing de la fuente, con la clave alertmanager.yaml, su alertmanager-values.yaml y el montaje notification-credentials. Prepara en ese Secret el webhook real de Slack y la clave de enrutamiento de PagerDuty Events API v2. Para SNS nativo, prepara la identidad AWS de la ServiceAccount real de Alertmanager con permiso de publicación limitado al tema y los permisos KMS aplicables; el rol IRSA de otro componente no se comparte automáticamente.

Sustituye la cuenta/Región/tema SNS del ejemplo antes de usarlo. Este ejemplo de enrutamiento completo envía las alertas críticas a PagerDuty, las advertencias a Slack y las alertas sin coincidencia a SNS; la ruta Watchdog de ejemplo se descarta mientras no haya un monitor de heartbeat configurado por separado:

```yaml
global:
  resolve_timeout: 5m
route:
  group_by:
  - cluster
  - namespace
  - alertname
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: sns-notifications
  routes:
  - matchers:
    - alertname="Watchdog"
    receiver: discard
  - matchers:
    - severity="critical"
    receiver: pagerduty-notifications
  - matchers:
    - severity="warning"
    receiver: slack-notifications
receivers:
- name: discard
- name: slack-notifications
  slack_configs:
  - api_url_file: /etc/alertmanager/secrets/notification-credentials/slack-url
    channel: '#eks-alerts'
    send_resolved: true
    title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
    text: "{{ range .Alerts }}{{ .Annotations.summary }} \u2014 {{ .Annotations.description }}{{ \"\\n\" }}{{ end }}"
- name: sns-notifications
  sns_configs:
  - sigv4:
      region: us-west-2
    topic_arn: arn:aws:sns:us-west-2:123456789012:eks-alerts
    send_resolved: true
    subject: EKS {{ .CommonLabels.alertname }}
- name: pagerduty-notifications
  pagerduty_configs:
  - routing_key_file: /etc/alertmanager/secrets/notification-credentials/pagerduty-routing-key
    send_resolved: true
    severity: '{{ if eq .CommonLabels.severity "critical" }}critical{{ else }}warning{{ end }}'
    description: '{{ .CommonLabels.alertname }}'
```

El receptor predeterminado es una alternativa, no un fan-out automático cuando coincide una ruta hija. Configura `continue`/rutas hermanas explícitas solo si el fan-out intencionado lo requiere. Valida el archivo completo con el amtool correspondiente y prueba las etiquetas de ruta. No hace falta un servicio sns-forwarder no definido ni un ConfigMap que contenga credenciales.

**Permisos de publicación para CloudWatch y EventBridge:**

- Para las alarmas de Container Insights, usa las métricas y dimensiones reales del capítulo fuente. El nombre de un grupo de nodos administrado no tiene por qué ser el nombre de un grupo EC2 Auto Scaling; no inventes un valor de dimensión AWS/EC2.
- Quien publica una alarma de CloudWatch necesita la política adecuada para el tema SNS. Si el tema está cifrado, AWS documenta que alias/aws/sns no basta para las alarmas de CloudWatch; usa una clave KMS administrada por el cliente cuya política permita las operaciones de publicación requeridas con las restricciones apropiadas.
- EventBridge usa eventos publicados de estado de complementos de EKS o eventos de API de CloudTrail compatibles. EKS Cluster Control Plane Health no está en el catálogo de eventos directos de EKS. Un intento de API no demuestra que la actualización se haya completado.
- Para un destino SNS, prepara el rol de ejecución de EventBridge o la alternativa documentada de política de recursos. Comprueba los fallos de PutTargets y las métricas de entrega. La existencia del tema o una respuesta satisfactoria de la API de reglas no demuestra que se haya entregado.

**Ejemplo de planificación con Terraform:**

Este ejemplo independiente hace referencia a un tema SNS estándar existente y bajo control del propietario, y a un rol de destino preparado. Las políticas del tema/clave, las suscripciones y los datos reales de ContainerInsights son requisitos previos. La alarma de CPU de nodos usa Maximum en las series ClusterName seleccionadas, mientras la regla de eventos del complemento abarca toda la cuenta/Región. Las acciones y la regla empiezan deshabilitadas para su revisión:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_name" {
  type = string
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with reviewed publisher/subscription/key permissions."
}

variable "eventbridge_role_arn" {
  type        = string
  description = "Prepared target execution role allowed to publish to the selected topic."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_cloudwatch_metric_alarm" "node_cpu" {
  alarm_name          = "${var.cluster_name}-node-cpu-warning"
  alarm_description   = "Example node CPU Maximum threshold; confirm actual ContainerInsights data."
  namespace           = "ContainerInsights"
  metric_name         = "node_cpu_utilization"
  dimensions          = { ClusterName = var.cluster_name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_event_rule" "addon_health" {
  name_prefix = "eks-addon-health-"
  description = "Account/Region add-on health events; not filtered to a single cluster."
  state       = "DISABLED"
  event_pattern = jsonencode({
    source      = ["aws.eks"]
    account     = [var.account_id]
    region      = [var.region]
    detail-type = ["EKS Addon Health Degraded", "EKS Addon Health Restored"]
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.addon_health.name
  target_id = "ops-sns"
  arn       = var.sns_topic_arn
  role_arn  = var.eventbridge_role_arn
}
```

El ejemplo de CPU necesita dos máximos de cinco minutos que excedan el umbral, no un uso continuo del 80 % durante diez minutos. Los datos ausentes no se consideran automáticamente saludables. Antes de habilitarlo mediante el cambio controlado del propietario, revisa la propiedad de recursos, el acceso del publicador, los datos de métricas y las notificaciones esperadas. Este fragmento no crea ni reemplaza la política del tema ni configura sus suscripciones y no se planificó/aplicó en AWS.

**Suscripciones SNS y procesamiento opcional con Lambda:**

Las suscripciones por email requieren confirmación. Las suscripciones de Lambda requieren permiso en la función para el tema SNS previsto; la suscripción por sí sola no concede permiso de invocación. SNS invoca Lambda de forma asíncrona para los temas estándar y puede producirse procesamiento duplicado. Un adaptador personalizado necesita código de entrega real, dependencias empaquetadas, credenciales protegidas, validación de entradas, idempotencia, gestión de fallos/reintentos y resultados observables.

No despliegues el antiguo handler de marcador de posición, cuyas funciones de envío solo contienen pass y luego devuelven “processed successfully”. Un valor de retorno con statusCode que parece HTTP no es un acuse de recibo de notificación para una invocación asíncrona de SNS. Expón correctamente los fallos de entrega, inspecciona la forma documentada del registro SNS y no infieras la gravedad a partir de subcadenas arbitrarias de AlarmName. Configura por separado los fallos de entrega de la suscripción y los fallos de ejecución de Lambda. El almacenamiento en búfer con SQS es otro diseño opcional que requiere una cola real, un mapeo de origen de eventos y sus propios controles de fallos; nada de eso se desprende de un esquema de arquitectura.

**Rutas correctamente separadas:**

```text
CloudWatch alarm -----------------------------> SNS -> confirmed subscribers
EventBridge rule -- authorized target role ---> SNS -> confirmed subscribers
Prometheus -> Alertmanager -- default --------> SNS
                         |-- warning --------> Slack
                         |-- critical -------> PagerDuty
Optional SNS subscriber -> implemented Lambda adapter -> chosen external channel
```

Agrupa las alertas relacionadas, limita las repeticiones, define explícitamente la gravedad y los plazos de respuesta, incluye evidencia e impacto y prueba rutas representativas de activación/resolución y fallo en un destino de prueba aprobado. Instalar un conjunto de herramientas no garantiza ni una cobertura completa ni una entrega satisfactoria. En esta auditoría no se crearon ni ejecutaron un tema, una suscripción, una alarma, una invocación de Lambda ni una notificación.

Referencias: [capítulo fuente](../../eks/06-eks-monitoring-logging.md), [receptores de Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/), [eventos de EKS](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html), [SNS/Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html), [SNS cifrado para alarmas de CloudWatch](https://repost.aws/knowledge-center/cloudwatch-configure-alarm-sns).

</details>

### 4. ¿Qué diseño de observabilidad de aplicaciones conserva evidencia útil?

- A. Tratar el CPU del nodo por sí solo como prueba de toda causa de latencia de la aplicación.
- B. Sobrescribir todos los atributos service.name entrantes con el nombre común del Collector.
- C. Correlacionar métricas, logs y trazas seleccionados sin perder la identidad del servicio, y verificar sus rutas reales.
- D. Suponer que un muestreador head del 10 % siempre conserva cada error y solicitud lenta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Correlacionar rutas de señales verificadas sin colapsar identidades.**

**Explicación:**

Las métricas describen tasas/distribuciones/estado de recursos, los logs agregan detalles de eventos y las trazas conectan operaciones instrumentadas. Ayudan a investigar, pero no garantizan visibilidad completa ni demuestran una causa raíz. El profiling puede aportar evidencia de CPU/asignación/heap cuando se habilita y revisa de forma explícita; no todos los recolectores de trazas lo proporcionan automáticamente.

**Usa el Collector y las rutas de señales correctos:**

Usa la configuración TLS de Operator0.158/ADOT0.50, solo para trazas y bajo control del equipo, del capítulo fuente, y la alternativa de registro de Q2, con alcance separado. El manifiesto de Operator procede de su propio release, no de un recurso del release de Collector. Mantén service.name en el límite de la aplicación; un procesador de recursos compartido no debe sobrescribir con un único valor global order-service, payment-service y otros emisores.

Para las métricas de Prometheus, usa la ruta ServiceMonitor/Service conectada de la fuente o un receptor Prometheus verificado por separado. El descubrimiento basado solo en anotaciones no configura el puerto/ruta correctos, RBAC ni la distribución entre réplicas. awsemf exporta a CloudWatch, mientras AMP necesita un endpoint real de remote write y una identidad SigV4. No dibujes una ruta a AMP si la configuración solo tiene awsemf.

**Ejemplo de instrumentación Java:**

Una alternativa a un starter de Spring Boot es el agente Java upstream de OpenTelemetry. La versión inspeccionada es 2.31.1; prepara su JAR revisado y una aplicación/JVM compatible mediante el proceso de compilación de la aplicación. Así se evita mezclar declaraciones Gradle y application.properties dentro de un bloque de código Java, o copiar un starter alpha 1.18 desalineado. No agregues otro agente a un proceso que ya esté instrumentado por CloudWatch Auto Monitor u otro propietario.

Esta es una configuración del runtime de la aplicación, no un comando de prueba de auditoría. Selecciona trazas OTLP/HTTP para el receptor TLS de la fuente y mantiene deshabilitada la exportación de métricas/logs del SDK en estas rutas separadas. Monta la CA de confianza y conserva cualquier otra opción de inicio JVM necesaria:

```bash
set -euo pipefail
: "${OTEL_JAVA_AGENT_JAR:?Set the reviewed OpenTelemetry Java agent 2.31.1 JAR path}"
: "${APP_JAR:?Set the application JAR path}"
test -r "$OTEL_JAVA_AGENT_JAR"
test -r "$APP_JAR"
export OTEL_SERVICE_NAME=order-service
export OTEL_RESOURCE_ATTRIBUTES=k8s.cluster.name=my-owned-cluster
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
export OTEL_PROPAGATORS=tracecontext,baggage
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
java "-javaagent:$OTEL_JAVA_AGENT_JAR" -jar "$APP_JAR"
```

El agente Java 2.x usa http/protobuf de forma predeterminada; el ejemplo lo especifica explícitamente. Un endpoint HTTP específico de señal incluye /v1/traces. El endpoint gRPC 4317 usa otro protocolo y no puede sustituirse cambiando solo el puerto. Se verificaron los metadatos del release/configuración; aquí no se ejecutó ningún agente Java, JDK ni aplicación.

**Ejemplo de instrumentación Python:**

Usa el adaptador RequestTracing de la fuente con Python 3.10+ y el SDK/exporter HTTP alineados en 1.44.0. Configura estos valores en el entorno de la aplicación de pagos, sustituyendo el nombre de clúster de ejemplo y montando la CA de confianza:

```bash
export OTEL_SERVICE_NAME=payment-service
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

El adaptador se reproduce a continuación para explicitar el ciclo de vida y el límite de la solicitud:

```python
import os
from urllib.parse import urlsplit

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class RequestTracing:
    def __init__(self):
        endpoint = os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or parsed.path != "/v1/traces":
            raise ValueError("Set the HTTPS OTLP/HTTP traces endpoint including /v1/traces")
        self.provider = TracerProvider(
            resource=Resource.create({
                "service.name": os.environ["OTEL_SERVICE_NAME"],
                "k8s.cluster.name": os.environ["CLUSTER_NAME"],
            }),
            sampler=ParentBased(TraceIdRatioBased(0.1)),
        )
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            certificate_file=os.environ["OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE"],
            timeout=10,
        )
        self.provider.add_span_processor(BatchSpanProcessor(exporter))
        self.tracer = self.provider.get_tracer("example.request-handler")
        self.propagator = TraceContextTextMapPropagator()

    def handle_request(self, incoming_headers, operation):
        parent = self.propagator.extract(incoming_headers)
        with self.tracer.start_as_current_span("request", context=parent, kind=SpanKind.SERVER):
            outgoing_headers = {}
            self.propagator.inject(outgoing_headers)
            return operation(outgoing_headers)

    def close(self):
        self.provider.shutdown()
```

Crea una instancia al iniciar la aplicación, llama a handle_request desde el handler real del framework con nombres de encabezados entrantes normalizados y la operación de negocio real, y llama a close durante el apagado ordenado. Esto no es un servidor Flask ni una implementación de pagos; no se supone silenciosamente que existan app/request/jsonify/process_transaction. Propaga el contexto suministrado a las llamadas salientes reales y al trabajo asíncrono mediante el mecanismo compatible del framework.

La auditoría probó este adaptador con la exportación del SDK deshabilitada, incluida la conservación de resultados/errores de negocio y comprobaciones puras de propagación/muestreo. Eso no demuestra exportación de spans en vivo ni un Collector desplegado.

**Ajusta la confianza IRSA, los permisos y la ServiceAccount:**

El siguiente ejemplo independiente de Terraform coincide con la identidad tracing-demo/adot-traces del Collector fuente. Usa entradas declaradas y un proveedor OIDC IAM que ya existe para el emisor real del clúster. Las condiciones de confianza incluyen sub y aud. X-Ray PutTraceSegments no admite limitar el recurso a un ARN, por lo que la política usa el comodín obligatorio con acción/Región restringidas y la confianza acotada. Esto no concede permisos no relacionados de CloudWatch o AMP:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "Use the approved 12-digit AWS account ID."
  }
}

variable "cluster_oidc_issuer_url" {
  type        = string
  description = "The actual EKS cluster OIDC issuer URL; its IAM OIDC provider must already exist."
  validation {
    condition     = startswith(var.cluster_oidc_issuer_url, "https://")
    error_message = "Use the HTTPS issuer returned by the owned cluster."
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

data "aws_partition" "current" {}

locals {
  oidc_hostpath     = trimsuffix(trimprefix(var.cluster_oidc_issuer_url, "https://"), "/")
  oidc_provider_arn = "arn:${data.aws_partition.current.partition}:iam::${var.account_id}:oidc-provider/${local.oidc_hostpath}"
}

resource "aws_iam_role" "adot_traces" {
  name = "adot-traces-example"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_hostpath}:aud" = "sts.amazonaws.com"
          "${local.oidc_hostpath}:sub" = "system:serviceaccount:tracing-demo:adot-traces"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "xray_write" {
  name = "xray-trace-write"
  role = aws_iam_role.adot_traces.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments"]
      Resource = "*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_xray_group" "applications" {
  group_name        = "EKS-Applications"
  filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
}

output "adot_traces_role_arn" {
  value = aws_iam_role.adot_traces.arn
}
```

Antes de crear el Collector, se puede crear atómicamente una ServiceAccount nueva y bajo control propio, con la anotación de rol, en el namespace ya preparado. Las ServiceAccount/roles existentes requieren el procedimiento de actualización/importación de su propietario; no sobrescribas otra identidad ni combines una asociación de Pod Identity no relacionada:

```bash
set -euo pipefail
: "${ADOT_ROLE_ARN:?Set the reviewed role ARN from the owned Terraform stack}"
python3 - "$ADOT_ROLE_ARN" <<'PY' | kubectl create -f -
import json
import sys
print(json.dumps({
    "apiVersion": "v1",
    "kind": "ServiceAccount",
    "metadata": {
        "name": "adot-traces",
        "namespace": "tracing-demo",
        "annotations": {"eks.amazonaws.com/role-arn": sys.argv[1]},
    },
}))
PY
```

Un cambio de anotación no inyecta credenciales retroactivamente en los Pods en ejecución; revisa si hace falta un rollout. Verifica el emisor/proveedor real, la audiencia del token, el rol asumido y la ruta de red. El grupo X-Ray filtra las trazas coincidentes; no instrumenta las aplicaciones ni concede permisos al Collector. Usa la configuración de workspace/fuente de datos de Q1 en vez de duplicar un comando incompleto para crear AMG. En esta auditoría no se crearon un rol/grupo IAM ni una ServiceAccount.

**RUM del navegador es una ruta distinta:**

El cliente web de CloudWatch RUM envía datos PutRumEvents a CloudWatch RUM, no automáticamente a un receptor OTLP de ADOT. Cuando se habilita el tracing de X-Ray, puede agregar X-Amzn-Trace-Id a las solicitudes HTTP permitidas. Las trazas de cliente/servidor no se conectan de forma predeterminada: revisa la propagación/puente del servidor compatible y los encabezados permitidos por CORS. Los ejemplos anteriores que solo usan W3C no consumen automáticamente un encabezado de X-Ray. Un cliente genérico de OpenTelemetry para navegador necesitaría su propio diseño compatible de endpoint/autenticación/CORS de OTLP.

```text
Browser CloudWatch RUM client -----> CloudWatch RUM
                 | optional X-Ray header/segment integration
Java order-service <--- propagated requests ---> Python payment-service
       | OTLP/HTTP TLS                              | OTLP/HTTP TLS
       +--------------> ADOT traces collector <-----+
                              |
                              v
                            X-Ray
Application metrics -> configured Prometheus -> optional SigV4 remote_write -> AMP
Application stdout  -> chosen log collector -> configured log store
Grafana/AMG         -> queries the configured data sources
```

**Cobertura, muestreo y privacidad:**

- Mide distribuciones de latencia, rendimiento, tasas de error y saturación con una población/ventana definidas. Un conjunto de trazas muestreadas no es automáticamente una distribución de métricas sin sesgo.
- Usa nombres de servicios acotados, rutas normalizadas, versión/entorno e identidad de clúster/namespace. Los ID de cliente/tenant y las URL sin procesar pueden causar problemas de cardinalidad y privacidad; no son etiquetas de métricas predeterminadas.
- El muestreo head decide antes del resultado final de la solicitud. No puede garantizar todos los errores/solicitudes lentas, y el muestreo tail no recupera spans ya descartados en etapas anteriores. El muestreo tail necesita enrutamiento afín a las trazas y búferes/ventanas de tiempo adecuados.
- Los datos de sesión/usuario de RUM, logs, spans y perfiles requieren controles adecuados de acceso, consentimiento/política de recopilación y retención. Los ID de correlación son metadatos, no autenticación.
- Las pruebas de rendimiento y el profiling complementan las señales de runtime. Estos ejemplos no afirman que se haya obtenido ningún benchmark ni resultado de rendimiento en producción.

Referencias: [configuración del agente Java](https://opentelemetry.io/docs/zero-code/java/agent/configuration/), [configuración del SDK Java](https://opentelemetry.io/docs/languages/java/configuration/), [CloudWatch RUM/X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html), [capítulo fuente](../../eks/06-eks-monitoring-logging.md).

</details>

### 5. ¿Cómo se deben supervisar los registros del plano de control de EKS administrado por AWS?

- A. Conectándose por SSH directamente a los nodos del plano de control administrado por AWS.
- B. Configurando los tipos de registro necesarios de EKS, verificando su entrega a CloudWatch Logs y aplicando consultas y controles de acceso adecuados.
- C. Suponiendo que un DaemonSet de los nodos de trabajo puede leer el sistema de archivos del plano de control administrado.
- D. Creando un panel de registros y suponiendo que publica automáticamente una métrica ErrorCount.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Configurar y verificar la ruta de registro administrada.**

**Explicación:**

EKS envía los tipos seleccionados de registros del plano de control directamente a CloudWatch Logs en la cuenta. Un recopilador de los nodos de trabajo no es la fuente de estos registros administrados. Esto aporta evidencia de diagnóstico y auditoría sin acceder al plano de control por SSH, pero no garantiza un registro de cada llamada a la API ni demuestra cumplimiento. La política y las etapas de auditoría, el momento de habilitación, la ingesta y la retención determinan qué datos están disponibles.

**Tipos de registro y su alcance:**

| Tipo | Uso |
| --- | --- |
| api | Diagnóstico y errores del servidor de API; no es un archivo completo de solicitudes y respuestas |
| audit | Eventos de auditoría de la API de Kubernetes registrados y campos de identidad, recurso y estado |
| authenticator | Diagnóstico de autenticación/mapeo de IAM; distingue la autenticación de la autorización de RBAC |
| controllerManager | Diagnóstico de reconciliación del controlador |
| scheduler | Decisiones y fallos de programación, y diagnósticos relacionados |

Primero inspecciona la configuración existente del clúster. Para un cambio aprobado que habilite los cinco tipos, la actualización del capítulo fuente captura un ID de actualización y consulta su estado; sigue comprobándolo hasta que finalice correctamente y luego verifica la entrega real de los registros:

```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the owned cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
aws eks describe-cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --query 'cluster.{ARN:arn,Status:status,Logging:logging}'
```



```bash
set -euo pipefail
: "${CLUSTER_NAME:?Set the reviewed cluster name}"
: "${AWS_REGION:?Set the cluster Region}"
UPDATE_ID=$(aws eks update-cluster-config \
  --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}' \
  --query 'update.id' --output text)
if [[ -z "$UPDATE_ID" || "$UPDATE_ID" == None ]]; then
  printf '%s\n' 'No update ID returned; inspect the request result.' >&2
  exit 1
fi
aws eks describe-update --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --update-id "$UPDATE_ID" \
  --query 'update.{ID:id,Status:status,Errors:errors}'
```

La llamada final a DescribeUpdate comprueba el estado; no es una espera automática ni una prueba de ingesta. Si seleccionas solo algunos tipos, conserva todos los tipos existentes que se necesiten; no copies un bloque que deshabilite explícitamente authenticator/controllerManager/scheduler solo para habilitar api/audit. Para un clúster nuevo, incluye el registro en su configuración de creación/IaC revisada. No crees otro clúster incompleto solo para configurar la supervisión. Los registros del controlador EKS Capabilities siguen la ruta de entrega separada que se describe en la fuente.

**Consulta campos JSON reales:**

Selecciona el grupo /aws/eks/CLUSTER/cluster del que eres responsable y un intervalo de tiempo acotado. Ejemplo de respuestas 5xx registradas:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1" and stage = "ResponseComplete"
| filter responseStatus.code >= 500
| sort @timestamp desc
| limit 100
```

Para un nombre de usuario de auditoría conocido, usa el campo JSON anidado en lugar de analizar una cadena literal user.username. Sustituye el nombre de usuario de ejemplo por la identidad real observada en tus registros:

```
fields @timestamp, auditID, user.username, verb, objectRef.resource, responseStatus.code
| filter apiVersion = "audit.k8s.io/v1"
| filter user.username = "example-user"
| sort @timestamp desc
| limit 100
```

Inspecciona los registros de authenticator antes de definir filtros de fallo específicos de un formato. Buscar una subcadena failed/denied puede omitir casos reales o coincidir con texto no relacionado; además, un mensaje de autenticación de IAM por sí solo no describe todos los resultados de autorización de Kubernetes.

**Un panel no publica una métrica:**

Un widget de Logs Insights ejecuta una consulta. Una alarma sobre una métrica personalizada necesita un publicador real, como un filtro de métricas. El ejemplo independiente de Terraform que sigue conecta un grupo de registros STANDARD, un filtro, su métrica, una alarma y un panel. Antes de usar esta configuración, gestiona o importa el grupo de registros existente a través de su propietario real; la clave KMS y los permisos del publicador/tópico de SNS deben estar preparados. No crea un clúster EKS ni una clave KMS nuevos.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "logs_kms_key_arn" {
  type        = string
  description = "Prepared symmetric key in the log-group Region with reviewed Logs/caller permissions."
}

variable "sns_topic_arn" {
  type        = string
  description = "Prepared standard SNS topic with confirmed subscriptions and publisher/key permissions."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

locals {
  metric_namespace = "EKS/ControlPlane"
  metric_name      = "${var.cluster_name}-AuditResponse5xxCount"
  filter_pattern   = "{ ($.apiVersion = \"audit.k8s.io/v1\") && ($.stage = \"ResponseComplete\") && ($.responseStatus.code >= 500) }"
}

resource "aws_cloudwatch_log_group" "control_plane" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  log_group_class   = "STANDARD"
  retention_in_days = 90
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_cloudwatch_log_metric_filter" "audit_5xx" {
  name           = "${var.cluster_name}-audit-response-5xx"
  log_group_name = aws_cloudwatch_log_group.control_plane.name
  pattern        = local.filter_pattern

  metric_transformation {
    namespace     = local.metric_namespace
    name          = local.metric_name
    value         = "1"
    default_value = 0
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "audit_5xx" {
  alarm_name          = "${var.cluster_name}-audit-response-5xx"
  alarm_description   = "Example threshold for ingested audit ResponseComplete records with code>=500."
  namespace           = local.metric_namespace
  metric_name         = local.metric_name
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false
  alarm_actions       = [var.sns_topic_arn]
}

resource "aws_cloudwatch_dashboard" "control_plane" {
  dashboard_name = "${var.cluster_name}-control-plane"
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "log"
        x      = 0
        y      = 0
        width  = 24
        height = 6
        properties = {
          region = var.region
          title  = "Recorded audit 5xx responses per five minutes"
          view   = "timeSeries"
          query  = "SOURCE '${aws_cloudwatch_log_group.control_plane.name}' | fields @timestamp\n| filter apiVersion = \"audit.k8s.io/v1\" and stage = \"ResponseComplete\" and responseStatus.code >= 500\n| stats count(*) as recordedResponses by bin(5m)"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          region  = var.region
          title   = "Metric filter: new ingested audit 5xx records"
          view    = "timeSeries"
          metrics = [[local.metric_namespace, local.metric_name]]
          period  = 300
          stat    = "Sum"
        }
      }
    ]
  })
}
```

El filtro cuenta los registros ResponseComplete de auditoría recién ingeridos cuyo responseStatus.code>=500. El nombre de métrica con prefijo del clúster distingue el clúster sin inventar una dimensión ClusterName que no existe en el JSON de auditoría. El filtro, la alarma y el widget de métricas del panel usan exactamente el mismo espacio de nombres y nombre, sin dimensiones. La consulta del panel puede abarcar registros más antiguos, pero el filtro de métricas no rellena el historial. Son recuentos de eventos registrados, no una tasa de error de API ni un total de solicitudes deduplicado; pueden producirse entregas duplicadas.

Se emite un valor default_value de 0 cuando llegan registros, pero ninguno coincide; si no llega ningún registro, los datos aún pueden faltar. Los filtros de métricas no pueden combinar un valor predeterminado con dimensiones. La alarma empieza intencionadamente con las acciones deshabilitadas, trata explícitamente los datos ausentes y usa un umbral ilustrativo. Antes de habilitarla, verifica nuevos puntos de datos de la métrica, permisos, suscripciones y una prueba de entrega controlada.

jsonencode evita las comillas de shell incorrectas del antiguo comando del panel. Si en su lugar usas la CLI, pasa un archivo JSON válido con --dashboard-body file://dashboard.json e inspecciona DashboardValidationMessages. PutDashboard reemplaza un cuerpo existente; conserva los widgets y la configuración de su propietario. La validación local de HCL/JSON no ejecuta el motor de consultas/filtros de AWS.

**KMS y retención:**

CloudWatch Logs cifra los datos de registro de forma predeterminada. Asociar una clave KMS simétrica administrada por el cliente cambia el cifrado de los datos recién ingeridos; no es la primera capa de cifrado ni vuelve a cifrar registros antiguos. Usa una clave de la misma Región que el grupo de registros, conserva las claves/permisos antiguos mientras se necesiten los datos anteriores y distingue los permisos para asociar la clave de los permisos para leer. Al desasociarla, los datos nuevos vuelven al cifrado predeterminado; deshabilitar o eliminar una clave antigua puede volver ilegibles los datos que aún conserva.

El servicio regional de Logs necesita permiso para usar la clave. Lo siguiente es solo un fragmento de declaración que el propietario de la clave debe combinar con una política existente, conservando las declaraciones de administración/delegación. Sustituye todos los identificadores de ejemplo de forma coherente; no lo uses como política de clave completa de reemplazo:

```json
{
  "Sid": "AllowLogsServiceForOneGroup",
  "Effect": "Allow",
  "Principal": {
    "Service": "logs.us-west-2.amazonaws.com"
  },
  "Action": [
    "kms:Encrypt",
    "kms:Decrypt",
    "kms:ReEncrypt*",
    "kms:GenerateDataKey*",
    "kms:DescribeKey"
  ],
  "Resource": "*",
  "Condition": {
    "ArnEquals": {
      "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
    }
  }
}
```

El ARN del grupo de registros en el contexto de cifrado no lleva :* al final. El operador que asocia la clave necesita los permisos de Logs documentados y kms:DescribeKey. Quienes lean/escriban necesitan los permisos KMS adecuados para sus operaciones, a través del servicio regional de Logs. La rotación de claves o un periodo de espera breve antes de eliminarlas no elimina la necesidad de conservar acceso de descifrado para los datos históricos. La retención de 90 días es un ejemplo, no una garantía de cumplimiento o inmutabilidad.

**Limita correctamente el acceso de lectura:**

Esta política de identidad ilustrativa permite acceder al grupo seleccionado y sus flujos, además de descifrar con una clave mediante Logs. La política de clave también debe permitir al principal previsto. No concede acciones de administración de registros ni de claves:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadAndQueryThisLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
    },
    {
      "Sid": "ReadThisGroupStreams",
      "Effect": "Allow",
      "Action": "logs:GetLogEvents",
      "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:log-stream:*"
    },
    {
      "Sid": "DecryptThisGroupsDataViaLogs",
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:us-west-2:123456789012:key/11111111-2222-3333-4444-555555555555",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "logs.us-west-2.amazonaws.com"
        },
        "ArnEquals": {
          "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster"
        }
      }
    }
  ]
}
```

La documentación actual de autorización de AWS admite limitar StartQuery y GetQueryResults al grupo de registros; no los amplíes a Resource:* basándote en suposiciones antiguas. DescribeLogStreams y FilterLogEvents son acciones de grupo, mientras que GetLogEvents es una acción de flujo. El formato ARN de LogGroup de AWS incluye :* para la mayoría de las acciones IAM; logGroupArn y el contexto de cifrado/etiquetado lo omiten. Los flujos de trabajo de consola/detección pueden necesitar acciones de lectura adicionales; DescribeLogGroups es un permiso separado, con ámbito propio y sin compatibilidad con ARN a nivel de recurso, que la política anterior no concede implícitamente.

Durante esta auditoría no se modificó ni ejecutó el registro del clúster, la retención, la política de clave, el filtro de métricas, el panel, la alarma ni ninguna consulta de CloudWatch. Referencias: [filtros de métricas de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html), [formatos de ARN de LogGroup](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html), [acciones IAM de Logs](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html), [cifrado KMS de Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html).

</details>

### 6. ¿Qué estrategia de supervisión ayuda mejor a optimizar los costes en Amazon EKS?

- A. Recopilar todas las métricas disponibles, independientemente de su utilidad.
- B. Combinar el uso de recursos, la asignación de costes y los candidatos a desperdicio revisados por sus responsables.
- C. Supervisar el rendimiento sin examinar el gasto.
- D. Revisar solo la factura mensual final.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Combinar el uso de recursos, la asignación de costes y los candidatos a desperdicio revisados por sus responsables.**

**Explicación:** Compara la CPU, la memoria, el almacenamiento, las solicitudes, los límites y las tendencias de las cargas de trabajo con los costes asignados. Investiga las anomalías y desviaciones presupuestarias junto con el responsable del recurso. Estas señales ayudan a identificar oportunidades; no garantizan ahorros ni demuestran que se pueda eliminar un recurso.

**Eficiencia de recursos y asignación de costes**

Reutiliza la instalación kube-prometheus-stack, kube-state-metrics y ServiceMonitor de kubelet de la guía fuente, con certificados de servicio verificados. cAdvisor usa `/metrics/cadvisor` en el puerto HTTPS de métricas de kubelet; no es un puerto de Service independiente llamado `cadvisor`. No añadas un monitor duplicado ni deshabilites la verificación TLS para que funcione el scraping.

Las siguientes expresiones de CPU y memoria devuelven **ratios de uso/solicitud por contenedor**, no la utilización de capacidad del nodo ni el coste monetario. Un ratio puede superar 1. Las solicitudes cero o ausentes no generan un ratio; tampoco equivalen a un uso cero. `max` elimina copias de scraping duplicadas con la identidad indicada; confirma que las copias representen realmente la misma carga de trabajo. Este ejemplo se dirige al Prometheus local de un clúster. Para un backend compartido, ambas familias de métricas deben incluir una etiqueta de clúster coherente. También hay que tener en cuenta la reutilización de nombres de Pod y los reinicios de contenedores al interpretar un intervalo de tiempo. Estas métricas de contenedor no describen toda la reserva del planificador para recursos a nivel de Pod, contenedores init ni la sobrecarga del Pod.

```promql
max by (cluster, namespace, pod, container) (
  rate(container_cpu_usage_seconds_total{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}[5m])
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="cpu",unit="core",container!=""}
  ) > 0
)
```

```promql
max by (cluster, namespace, pod, container) (
  container_memory_working_set_bytes{job="kubelet",metrics_path="/metrics/cadvisor",namespace!="",container!="",container!="POD"}
)
/ on (cluster, namespace, pod, container)
(
  max by (cluster, namespace, pod, container) (
    kube_pod_container_resource_requests{job="kube-state-metrics",resource="memory",unit="byte",container!=""}
  ) > 0
)
```

Crea dos paneles en Grafana con la fuente de datos Prometheus existente y estas consultas; llama al panel **Uso de recursos frente a solicitudes**, usa una unidad de ratio/porcentaje y conserva la identidad de clúster, namespace, Pod y contenedor. Un ConfigMap con un `cost-dashboard.json` sin especificar no crea un panel utilizable. Con el sidecar de Grafana de la guía fuente, aprovisionar un JSON de panel revisado también requiere la etiqueta configurada `grafana_dashboard: "1"`.

**OpenCost o Kubecost**

Para evaluar OpenCost por primera vez con el Prometheus existente de la guía fuente, guarda esto como `opencost-values.yaml`. El chart verificado es **2.5.31** y la aplicación **1.121.2**. Establece el ID real del clúster y la URL de Prometheus. La etiqueta de ServiceMonitor debe coincidir con el selector de Prometheus; permite el namespace `opencost` en la selección de namespaces. Esto no instala otro Prometheus/node exporter.

```yaml
service:
  type: ClusterIP
opencost:
  exporter:
    defaultClusterId: my-cluster
  prometheus:
    internal:
      enabled: false
    external:
      enabled: true
      url: http://monitoring-kube-prometheus-prometheus.monitoring.svc:9090
  metrics:
    serviceMonitor:
      enabled: true
      additionalLabels:
        release: monitoring
  cloudCost:
    enabled: false
  mcp:
    enabled: false
  ui:
    enabled: true
    ingress:
      enabled: false
```

```bash
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update opencost
helm template opencost opencost/opencost --version 2.5.31 \
  --namespace opencost -f opencost-values.yaml > opencost-rendered.yaml
# After reviewing RBAC, images, resources, selectors, and network access:
helm install opencost opencost/opencost --version 2.5.31 \
  --namespace opencost --create-namespace -f opencost-values.yaml
kubectl -n opencost port-forward --address 127.0.0.1 svc/opencost 9090:9090
```

Abre `http://localhost:9090` mientras se ejecuta el port-forward. Esta configuración base usa una caché efímera del exporter, deshabilita la ingesta de costes en la nube y MCP, y solo expone un Service ClusterIP. Antes de compartirla, revisa la persistencia, el dimensionamiento, la autenticación/el acceso de red, RBAC y el estado del scraping; ClusterIP no es un límite de autorización entre tenants. Las estimaciones de precios bajo demanda deben reconciliarse con la facturación real, descuentos, precios Spot, créditos, costes compartidos, almacenamiento y cargos de red. La integración de facturación de AWS es una configuración aparte; la autenticación documentada con cuentas de servicio/SDK predeterminadas de AWS no requiere insertar claves de acceso de larga duración.

Kubecost es otra opción independiente. Su chart verificado **3.3.1** es `kubecost/kubecost` y procede de `https://kubecost.github.io/kubecost/`. El repositorio antiguo `cost-analyzer` y los valores Prometheus de la versión 2.x no son una receta de instalación para 3.x: 3.x usa ClickHouse y recopila datos directamente con finops-agent. Antes de instalar o actualizar, revisa su licencia, almacenamiento, compatibilidad con Kubernetes y la migración documentada desde 2.x. Consulta la [guía de la plataforma FinOps](../../ops/13-finops-cost-platform.md) y la [documentación del chart de Kubecost](https://github.com/kubecost/cost-analyzer-helm-chart).

**Etiquetas, tags de facturación y categorías**

Las etiquetas de namespace ayudan a agrupar datos en Kubernetes:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    cost-center: cc-123
    environment: production
```

No etiquetan automáticamente recursos EC2/EBS ni activan los tags de facturación de AWS. El responsable de facturación debe aplicar tags reales de recursos de AWS y después activar las claves de asignación de costes que cumplan los requisitos. Ten en cuenta los retrasos del procesamiento de facturación y verifica que aparezcan en Cost Explorer/CUR. La asignación dividida de costes de AWS es una ruta de habilitación independiente que crea registros de nivel Pod de EKS y atributos generados por AWS, como `aws:eks:namespace`; no convierte cada etiqueta de namespace en un tag EC2. Revisa sus requisitos previos de fuentes de datos y el mayor volumen de informes.

El relleno retroactivo de tags de asignación de costes puede cubrir hasta 12 meses **si esos recursos ya tenían tags durante ese periodo**; no puede inventar tags históricos ausentes. Una Cost Category clasifica registros de facturación mediante reglas revisadas; no es un panel. Su operación de creación por CLI es `aws ce create-cost-category-definition`, no `create-cost-category`. Usa claves y valores que realmente aparezcan en los datos de facturación y configura por separado los informes o paneles guardados de Cost Explorer.

**Inventario de volúmenes no conectados, de solo lectura**

Ejecuta lo siguiente solo en la cuenta/Región previstas y con un tag de propiedad existente. Mantiene habilitada la paginación de AWS CLI e imprime una lista de candidatos en JSON. La sintaxis limitada del tag es intencionada; adapta los filtros JSON si tu tag real incluye otros caracteres.

```bash
set -euo pipefail
: "${AWS_REGION:?Set the reviewed Region}"
: "${EXPECTED_ACCOUNT_ID:?Set the reviewed 12-digit account ID}"
: "${OWNER_TAG_KEY:?Set an existing ownership tag key}"
: "${OWNER_TAG_VALUE:?Set its exact value}"
[[ "$EXPECTED_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]
# This example accepts a restricted literal subset, excluding wildcards/shorthand separators.
[[ "$OWNER_TAG_KEY" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
[[ "$OWNER_TAG_VALUE" =~ ^[a-zA-Z0-9_./:@+-]+$ ]]
actual_account=$(aws sts get-caller-identity --region "$AWS_REGION" \
  --query Account --output text --no-cli-pager)
[[ "$actual_account" == "$EXPECTED_ACCOUNT_ID" ]] || {
  echo "Account mismatch" >&2
  exit 1
}
aws ec2 describe-volumes --region "$AWS_REGION" --page-size 100 \
  --filters Name=status,Values=available \
    "Name=tag:$OWNER_TAG_KEY,Values=$OWNER_TAG_VALUE" \
  --query 'Volumes[].{id:VolumeId,zone:AvailabilityZone,sizeGiB:Size,created:CreateTime,state:State}' \
  --output json --no-cli-pager
```

`available` significa que ahora no está conectado; no significa que no se use ni que sea seguro eliminarlo. La hora de creación no indica el último uso. Consulta con el responsable la propiedad PV/PVC, la política de recuperación, las cargas pendientes, las copias de seguridad, las instantáneas y los requisitos de recuperación ante desastres. Del mismo modo, una CPU/memoria baja (incluso un umbral arbitrario del 5 %) no demuestra que un Pod o balanceador de carga sea innecesario. Usa un historial representativo y señales de aplicación/SLO; no reemplaces métricas ausentes por un resultado vacío de «Pods inactivos».

**Ejemplo de presupuesto**

Este ejemplo independiente de Terraform utiliza un tag de facturación real y activado, y un destinatario aprobado. El **límite mensual de 1.000 USD y la alerta del 80 %** son valores ilustrativos, no costes observados. Importa/reconcilia un presupuesto existente en lugar de crear otro que entre en conflicto con su propietario. Valida la base de costes elegida y la cobertura de tags; un filtro por tag puede omitir cargos compartidos o sin tag. Aplicar este ejemplo crea una configuración real de notificación.

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.69.1"
    }
  }
}

variable "account_id" {
  type = string
}

variable "region" {
  type = string
}

variable "budget_name" {
  type = string
}

variable "activated_tag_key" {
  type = string
}

variable "tag_value" {
  type = string
}

variable "notification_email" {
  type        = string
  description = "Approved budget owner; applying this example configures real email notifications."
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
}

resource "aws_budgets_budget" "eks_monthly" {
  account_id   = var.account_id
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = "1000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = [join("$", [var.activated_tag_key, var.tag_value])]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }
}
```

Budgets usa datos de facturación procesados y no impone un límite máximo de gasto. Budget Actions puede aplicar controles IAM/SCP o dirigirse a instancias EC2/RDS compatibles, pero requiere permisos y revisión operativa separados. El panel de eficiencia de recursos anterior no es un panel de facturación.

Revisa las solicitudes con las recomendaciones de VPA y el historial de picos/SLO, y coordina HPA con el escalado de nodos. Karpenter/Cluster Autoscaler y Spot pueden reducir los costes solo cuando lo permiten las restricciones de carga, interrupción, capacidad y disrupción. Reducir las solicitudes por sí solo no baja la factura, salvo que cambie la capacidad aprovisionada o el precio. Registra las acciones acordadas y los resultados medidos en revisiones periódicas con los responsables.

Las demás opciones no ofrecen este ciclo de retroalimentación: recopilarlo todo aumenta el coste/ruido de telemetría; el rendimiento por sí solo no muestra el gasto; una factura mensual final llega demasiado tarde para investigar a tiempo.

**Referencias principales:** [instalación de OpenCost](https://opencost.io/docs/installation/helm), [activación de tags de AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html), [relleno retroactivo de tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html), [asignación dividida de costes](https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html), [Budget Actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html).

</details>
