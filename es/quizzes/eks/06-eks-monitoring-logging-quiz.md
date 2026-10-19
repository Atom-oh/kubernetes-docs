# Cuestionario sobre monitoreo y registro de Amazon EKS

> **Última actualización**: 16 de octubre de 2026

Este cuestionario evalúa tu comprensión de las funciones, herramientas y prácticas recomendadas de monitoreo y registro de Amazon EKS.

## Descripción general del cuestionario
- Monitoreo de clústeres de EKS
- Registro de contenedores y aplicaciones
- Recopilación y análisis de métricas de rendimiento
- Alertas y detección de anomalías
- Arquitectura de monitoreo y registro
- Prácticas recomendadas y herramientas

## Preguntas de opción múltiple

### 1. ¿Qué principio orienta correctamente el diseño de una solución de monitoreo para EKS?

- A. CloudWatch no puede recopilar trazas de aplicaciones.
- B. Instalar Grafana por sí solo recopila automáticamente todas las métricas de los Pod.
- C. Seleccionar las señales necesarias, configurar los recopiladores y las fuentes de datos propios, y verificar la entrega y la cobertura.
- D. Instalar CloudWatch, Prometheus, Grafana y X-Ray siempre garantiza una visibilidad completa.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Seleccionar y verificar el diseño de señales, recopiladores y backends.**

**Explicación:**

Combinar herramientas puede ser útil, pero las señales necesarias y las limitaciones operativas determinan el diseño. CloudWatch admite más que las métricas básicas de infraestructura; entre otras cosas, ofrece trazas/APM de Application Signals para cargas de trabajo compatibles. Grafana puede consultar fuentes de datos de AWS y de trazas, pero la interfaz de usuario no recopila por sí sola todas las señales. Los recopiladores, la instrumentación, las identidades, los endpoints accesibles y las configuraciones compatibles deben conectarse explícitamente; ninguna lista de productos garantiza una cobertura completa.

**Conserva las capas útiles:**

| Capa | Ejemplos de señales | Dependencia importante |
| --- | --- | --- |
| Infraestructura | CPU/memoria de los nodos, disco, red | Recopilador de nodos compatible y dimensiones de métricas correctas |
| Kubernetes | Estado de los objetos, preparación, actividad de la API | Permisos del exportador/API/auditoría y targets reales |
| Aplicación | Latencia de solicitudes, errores, métricas de negocio | Instrumentación de la aplicación y un Schema de métricas acotado |
| Solicitudes distribuidas | Intervalos de traza y relaciones entre servicios | Propagación de contexto, muestreo y exportación correcta |

**Secuencia de implementación:**

1. Sigue el [capítulo de referencia](../../eks/06-eks-monitoring-logging.md) para revisar el catálogo, el Schema y las identidades del complemento de CloudWatch administrado. Deben revisarse Auto Monitor de la versión 5+ y la configuración de reinicio; no añadas otro agente a cargas de trabajo ya instrumentadas sin revisar posibles conflictos.
2. Si necesitas recopilación o consultas de Prometheus, usa los valores de KPS92.9.0 indicados en la fuente y los requisitos previos de almacenamiento preparado, Secret de Grafana y certificado de la CA de servicio de kubelet. El Operator gestiona ServiceMonitor/PrometheusRule; una instalación independiente de Prometheus no es equivalente. Comprueba los targets reales después de la instalación.
3. Para la ruta ADOT explícita, usa el ejemplo de la fuente con Operator0.158/Collector0.50 v1beta1, configuración de tipo objeto, TLS y su ServiceAccount preparado. La versión de Collector no incluye el manifiesto de instalación de Operator. Esta ruta, que solo envía trazas, las envía a X-Ray; las aplicaciones siguen necesitando instrumentación y propagación.
4. Para AMP, configura el endpoint de remote-write real del workspace y la identidad de escritura. Configura por separado la identidad de consulta/fuente de datos de Grafana/AMG; AMG12+ usa el complemento de AMP. Un exportador awsemf publica a través de CloudWatch, no automáticamente en AMP.

**Ejemplos de rutas de datos:**

```text
EKS control-plane logs -------------------------------> CloudWatch Logs
Container stdout/stderr -> chosen log collector ------> configured log store
Application spans ------> ADOT OTLP receiver ----------> X-Ray
Metric targets ----------> Prometheus -----------------> local TSDB
                              |-- SigV4 remote_write -> AMP
Grafana/AMG -- configured queries --> Prometheus / AMP / CloudWatch / X-Ray
```

Estas son rutas seleccionables; no significan que todos los recopiladores exporten a todos los backends. Verifica los permisos, TLS, el descubrimiento/los selectores, los datos descartados y las consultas representativas antes de confiar en los paneles. Define las prioridades y la escalación de las alertas, y controla la cardinalidad, el muestreo y la retención; prueba por separado cualquier respuesta automatizada.

**Ejemplo de planificación con Terraform:**

El siguiente ejemplo de recursos utiliza AWS provider 6.69.1. Presupone la cuenta/Región seleccionada, un rol de workspace de Grafana existente y revisado, una versión compatible de AMG y una configuración apta de IAM Identity Center. Los recursos existentes requieren el procedimiento de importación/cambio de su propietario. El nombre del grupo de registros de la aplicación coincide con la ruta del recopilador de la fuente; no crees un segundo propietario para un grupo que ya administre un complemento u otra pila.

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

Esto define recursos, no una ruta funcional de recopilación o inicio de sesión. Configura los permisos de consulta del rol para el ARN real del workspace, asigna usuarios/grupos, añade fuentes de datos y conecta los recopiladores con los ID/endpoints devueltos. CUSTOMER_MANAGED deja explícitamente la gestión de IAM en manos del propietario; el fragmento antiguo SERVICE_MANAGED/data_sources no demostraba que un workspace creado mediante API tuviera esos roles y conexiones. Revisa por separado los requisitos de cifrado, retención, acceso y costo. En esta auditoría no se ejecutó ningún plan/apply de Terraform, inicio de sesión ni consulta de telemetría activa.

**Por qué las otras opciones son incorrectas:** A minimiza las capacidades actuales de CloudWatch; B confunde visualización con recopilación; D trata la instalación como garantía de cobertura. Los scripts personalizados aún pueden ser útiles para comprobaciones y automatización acotadas si se definen claramente su propiedad, errores y alcance.

</details>

### 2. ¿Qué enfoque conecta correctamente los registros de los contenedores con la retención y el análisis centralizados?

- A. Considerar que copiar manualmente y de forma periódica archivos de nodos constituye una canalización de registros completa y duradera.
- B. Suponer que los archivos dentro de un contenedor siempre sobreviven a la sustitución del contenedor y del nodo.
- C. Usar un recopilador administrado por un propietario, con el analizador del runtime, los permisos, el almacenamiento y el backend configurados correctamente.
- D. Instalar dos recopiladores para los mismos archivos y suponer que así se garantiza una entrega sin pérdidas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Configurar y verificar una ruta de recopilación administrada por un propietario.**

**Explicación:**

Por lo general, las aplicaciones deben escribir registros estructurados adecuados en stdout/stderr, mientras que la plataforma proporciona la recopilación y la retención. stdout es una buena interfaz, pero no es por sí mismo un almacén centralizado y duradero. Un recopilador puede añadir análisis, filtrado, almacenamiento en búfer y enrutamiento; la rotación, los búferes finitos, la pérdida de nodos y los reintentos siguen afectando la cobertura y los duplicados. Controla el acceso, los campos sensibles y la retención en vez de afirmar que un recopilador garantiza la integridad o una entrega sin pérdidas.

**Configuración básica conectada de Fluent Bit:**

Usa el [capítulo de referencia](../../eks/06-eks-monitoring-logging.md) en lugar de aplicar manifiestos sin relación de la rama master. Su ejemplo independiente utiliza AWS chart0.2.0/image3.4.14, ajustes nativos de cloudWatchLogs, análisis CRI, registros de nodos de solo lectura, almacenamiento/almacenamiento en búfer separados y un post-renderer de RBAC revisado. Prepara el grupo de registros real y la identidad de IAM. Si el complemento de CloudWatch ya administra Fluent Bit, usa la configuración de ese propietario en lugar de crear accidentalmente un segundo lector.

Para distribuir también a OpenSearch, combina esta superposición de la fuente con sus valores base completos y su post-renderer, según el procedimiento de instalación/actualización del propietario:

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

Sustituye el endpoint/Región por los valores inspeccionados del dominio. Los permisos SigV4, la política del dominio, la asignación de roles de FGAC y la verificación de TLS son requisitos distintos. No combines credenciales de autenticación básica con SigV4 en una misma solicitud. Cada salida tiene un comportamiento independiente de éxito/reintento; que haya éxito en CloudWatch no demuestra que la entrega a OpenSearch se haya completado. Usa plantillas de accesores de registros compatibles y un nombre alternativo para el flujo; log_stream_prefix no admite expansiones arbitrarias de estilo shell de los campos de registros de Kubernetes.

**Alternativa con Fluentd: contratos explícitos de complementos y entradas:**

Fluentd sigue siendo una opción cuando la imagen administrada por el propietario incluye los complementos necesarios de análisis, metadatos de Kubernetes y OpenSearch. Hay que decodificar el envoltorio de containerd/CRI-O antes de tratar el cuerpo de la aplicación como JSON. Configura la entrada tail, los permisos de metadatos, el almacenamiento de posiciones y búferes por recopilador y la configuración montada; lo siguiente es solo un fragmento de salida de OpenSearch, no una instalación completa de ConfigMap/DaemonSet:

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

Usa los campos de endpoint IRSA oficiales de fluent-plugin-opensearch y un índice fijo. Prepara las variables de entorno OPENSEARCH_URL y las del rol/archivo de token inyectadas por IRSA. logstash_format=true ignoraría index_name; las expresiones arbitrarias de índices por Pod no sustituyen un diseño de enrutamiento/retención verificado. Elige índices/alias acotados y revisa las políticas de rollover. Los búferes de archivos necesitan una ruta de almacenamiento grabable y aislada adecuada; el bloqueo/reintento aún puede perder registros sin leer tras la rotación o la pérdida de un nodo. En esta auditoría no se ejecutó la composición de complementos/entradas.

**La recopilación de registros con ADOT es compatible con los componentes seleccionados:**

ADOT0.50.0 incluye filelog, file_storage y awscloudwatchlogs. El exportador de CloudWatch Logs correspondiente de upstream0.158 está marcado como alfa; se trata de un ejemplo específico de versión con requisitos previos explícitos del runtime, no de una afirmación de preparación para producción. Úsalo como recopilador alternativo para el conjunto de datos seleccionado, no como duplicado accidental de Fluent Bit.

Prepara Operator0.158, el namespace de registro y el ServiceAccount adot-logs con su rol IRSA revisado y permisos de escritura de registros de AWS. Limita la confianza a este proveedor OIDC del clúster, sub=system:serviceaccount:logging:adot-logs y aud=sts.amazonaws.com; proporciona la ruta de red necesaria para STS/Logs. El ejemplo es para nodos EC2 Linux estándar y requiere permiso de admisión para un agente de nodo root con /var/log/pods de solo lectura y un directorio de estado dedicado y grabable. El filtro de inclusión del namespace default limita los datos exportados; no convierte el montaje del host de todo el nodo en una frontera de seguridad del sistema de archivos. Revisa la ubicación/las taints de los nodos, la propiedad de los archivos y la política del namespace. Establece los valores reales de Región/grupo de registros antes del despliegue:

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

El operador de contenedores procesa los envoltorios CRI/registros parciales y obtiene los metadatos del Pod a partir de log.file.path. Un analizador JSON genérico aplicado a líneas CRI sin procesar es incorrecto. El nombre del flujo proviene del nombre del nodo de la Downward API mediante la sustitución de variables de entorno de Collector, no de marcadores {pod_name}.{container_name} no compatibles.

El exportador puede crear grupos/flujos y log_retention se aplica a los grupos creados recientemente; configura la retención de grupos existentes con el propietario del grupo de registros. Su manejo documentado de EMF puede sustituir los nombres configurados de grupo/flujo, así que limita el alcance de destino de IAM e inspecciona el formato real de los datos. Una cadena de configuración por sí sola no es una frontera de autorización.

file_storage conserva los offsets del receptor, no todos los lotes sin exportar. El ejemplo utiliza una cola de envío en memoria y reintentos finitos; el estado de los checkpoints, los lotes y los datos de hostPath tienen comportamientos de fallo/ciclo de vida distintos. start_at=end omite el contenido existente en una lectura inicial si no hay offsets guardados. Supervisa los reintentos, la cola, los errores de descarte/almacenamiento y la rotación de nodos. No se probaron procesos de Collector, montajes, flujo de credenciales de AWS ni ingesta.

**Comprobaciones de análisis e infraestructura:**

Para el Schema de la fuente de Fluent Bit, inspecciona los errores estructurados con los campos reales de namespace/contenedor. El envoltorio de ADOT u otro recopilador puede generar un Schema almacenado diferente:

```
fields @timestamp, @log, kubernetes.pod_name, data.level, data.message
| filter kubernetes.namespace_name = "default"
| filter toupper(data.level) = "ERROR"
| sort @timestamp desc
| limit 100
```

Un ejemplo de inspección independiente con Terraform lee un dominio existente de OpenSearch aprobado:

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

La fuente de datos no configura la red, la política de dominio/IAM, FGAC ni la entrega. Mantén separada la administración de la ingesta, evita las contraseñas maestras en el código/estado y revisa cualquier migración de recursos/direcciones. Las consultas y pruebas de acceso requieren el entorno real; la validación de Terraform no realiza esas comprobaciones.

**Por qué las otras opciones son incorrectas:** La inspección manual de archivos es útil para el diagnóstico, pero no constituye una canalización centralizada completa. El ciclo de vida del contenedor/nodo y los tipos de volumen determinan qué archivos sobreviven. Los lectores duplicados pueden duplicar datos/costos y aun así fallar; el almacenamiento en búfer y los reintentos necesitan capacidad medida y pruebas de fallos.

Referencias: [componentes de ADOT](https://github.com/aws-observability/aws-otel-collector/tree/v0.50.0), [analizador de contenedores](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.158.0/pkg/stanza/docs/operators/container.md), [exportador de CloudWatch Logs](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.158.0/exporter/awscloudwatchlogsexporter), [complemento de OpenSearch para Fluentd](https://github.com/fluent/fluent-plugin-opensearch).

</details>

### 3. ¿Qué enfoque crea una ruta de alertas eficaz y verificable para EKS?

- A. Suponer que la revisión manual de registros garantiza una detección inmediata.
- B. Crear una alarma de CloudWatch y suponer que cubre todos los fallos de Kubernetes/aplicaciones.
- C. Crear un ConfigMap arbitrario de alertmanager-config y suponer que el Operator lo consume.
- D. Seleccionar las señales necesarias, conectar las reglas de métricas/eventos con receptores autorizados y probar cada ruta de entrega.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Conectar y verificar las rutas de alertas necesarias.**

**Explicación:**

Las alarmas de CloudWatch, Prometheus/Alertmanager y EventBridge cubren distintas necesidades de señales/enrutamiento y pueden combinarse de forma deliberada. CloudWatch también admite métricas de aplicaciones/personalizadas, mientras que Prometheus puede consumir los exportadores de AWS adecuados; no debe descartarse ninguno con una afirmación genérica de que solo cubren la infraestructura. La instalación por sí sola no establece la cobertura de métricas, los umbrales correctos, los permisos de publicación ni una entrega correcta.

**Las reglas de métricas deben coincidir con series y unidades reales:**

El siguiente PrometheusRule usa los selectores KPS de la fuente y series reales de node-exporter/kube-state-metrics. Los cálculos de CPU y memoria disponible producen explícitamente porcentajes, por lo que un umbral de 80 tiene sentido. CrashLoopBackOff usa el motivo de espera, no cualquier reinicio; se incluye Ready=false en un Pod en estado Running, mientras que se excluyen los Pod terminales. Añade una identidad de clúster estable al combinar clústeres y comprueba si ya hay reglas equivalentes incluidas antes de desplegar duplicados:

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

Estos umbrales y tiempos de espera son ilustrativos. MemAvailable estima la disponibilidad de memoria recuperable; no es la condición MemoryPressure de kubelet ni un porcentaje de las solicitudes de los Pod. Que falten series o estén desactualizadas no significa que todo esté bien o que el uso sea cero. Supervisa por separado los fallos de scrape y la evaluación de reglas.

**Conecta la configuración real de Alertmanager:**

Usa el Secret alertmanager-routing de la fuente, con la clave alertmanager.yaml, su alertmanager-values.yaml y el montaje notification-credentials. Prepara el webhook real de Slack y la clave de enrutamiento de PagerDuty Events API v2 en ese Secret. Para SNS nativo, prepara la identidad AWS del ServiceAccount real de Alertmanager con permisos de publicación limitados al topic y los permisos KMS aplicables; el rol IRSA de otro componente no se comparte automáticamente.

Sustituye la cuenta/Región/topic SNS de ejemplo antes de usarlo. Este ejemplo completo de enrutamiento envía las alertas críticas a PagerDuty, las de advertencia a Slack y las alertas sin coincidencia a SNS; la ruta de ejemplo Watchdog se descarta a la espera de configurar por separado un monitor de heartbeat:

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

El receptor predeterminado es una alternativa, no una distribución automática cuando coincide una ruta secundaria. Configura continue/rutas hermanas explícitas solo cuando se necesite una distribución intencionada. Valida el archivo completo con el amtool correspondiente y prueba las etiquetas de las rutas. No se necesita ningún servicio sns-forwarder indefinido ni un ConfigMap con credenciales.

**Permisos de publicación de CloudWatch y EventBridge:**

- Para las alarmas de Container Insights, usa la métrica y las dimensiones reales de la fuente. El nombre de un grupo de nodos administrado no es necesariamente el nombre de un grupo de Auto Scaling de EC2; no inventes un valor de dimensión de AWS/EC2.
- Un publicador de alarmas de CloudWatch necesita la política SNS apropiada para el topic. Si el topic está cifrado, AWS documenta que alias/aws/sns no es suficiente para las alarmas de CloudWatch; usa una clave KMS administrada por el cliente cuya política permita las operaciones de publicador necesarias con las restricciones adecuadas.
- EventBridge usa eventos publicados sobre el estado de los complementos de EKS o eventos de API de CloudTrail compatibles. EKS Cluster Control Plane Health no está en el catálogo de eventos directos de EKS. Un intento de API no demuestra que la actualización haya finalizado.
- Para un destino SNS, prepara el rol de ejecución de EventBridge o la alternativa documentada basada en una política de recursos. Comprueba los fallos de PutTargets y las métricas de entrega. La existencia del topic o una respuesta correcta de la API de reglas no demuestra que se haya entregado.

**Ejemplo de planificación con Terraform:**

Este ejemplo independiente hace referencia a un topic SNS estándar existente y administrado por un propietario, y a un rol de destino preparado. Son requisitos previos las políticas del topic/clave, las suscripciones y los datos reales de ContainerInsights. La alarma de CPU de nodo usa Maximum para la serie ClusterName seleccionada, mientras que la regla de eventos del complemento abarca toda la cuenta/Región. Las acciones y la regla empiezan deshabilitadas para su revisión:

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

El ejemplo de CPU requiere dos máximos de cinco minutos que superen el umbral, no un uso continuo del 80 % durante diez minutos. Los datos faltantes no se consideran automáticamente saludables. Revisa la propiedad de los recursos, el acceso del publicador, los datos de métricas y las notificaciones esperadas antes de habilitarlo mediante el cambio controlado del propietario. Este fragmento no crea ni sustituye la política del topic, no configura suscripciones y no se planificó/aplicó en AWS.

**Suscripciones SNS y procesamiento opcional con Lambda:**

Las suscripciones por correo electrónico requieren confirmación. Las suscripciones de Lambda requieren permiso en la función para el topic SNS previsto; una suscripción por sí sola no concede permisos de invocación. SNS invoca Lambda de forma asíncrona para topics estándar y puede haber procesamiento duplicado. Un adaptador personalizado necesita código de entrega real, dependencias empaquetadas, credenciales protegidas, validación de entradas, idempotencia, manejo de fallos/reintentos y resultados observables.

No despliegues el antiguo controlador de ejemplo cuyas funciones de envío solo contienen pass y luego devuelven «procesado correctamente». Una respuesta con un statusCode que parece HTTP no es un acuse de recibo de notificación para una invocación asíncrona de SNS. Expón correctamente los fallos de entrega, inspecciona la forma documentada del registro SNS y no deduzcas la gravedad de subcadenas arbitrarias de AlarmName. Configura por separado los fallos de entrega de suscripciones y los fallos de ejecución de Lambda. El almacenamiento en búfer de SQS es otro diseño opcional que requiere una cola/mapa de origen de eventos reales y sus propios controles de fallos; no se deduce de un esquema de arquitectura.

**Rutas correctamente separadas:**

```text
CloudWatch alarm -----------------------------> SNS -> confirmed subscribers
EventBridge rule -- authorized target role ---> SNS -> confirmed subscribers
Prometheus -> Alertmanager -- default --------> SNS
                         |-- warning --------> Slack
                         |-- critical -------> PagerDuty
Optional SNS subscriber -> implemented Lambda adapter -> chosen external channel
```

Agrupa las alertas relacionadas, limita las repeticiones, define la gravedad y los plazos de respuesta explícitos, incluye evidencia e impacto, y prueba rutas representativas de activación/resolución y de fallos en un destino de prueba aprobado. Ni una cobertura completa ni una entrega correcta se derivan de instalar un conjunto de herramientas. Durante esta auditoría no se creó ni ejecutó ningún topic, suscripción, alarma, invocación de Lambda o notificación.

Referencias: [capítulo de referencia](../../eks/06-eks-monitoring-logging.md), [receptores de Alertmanager](https://prometheus.io/docs/alerting/latest/configuration/), [eventos de EKS](https://docs.aws.amazon.com/eventbridge/latest/ref/events-ref-eks.html), [SNS/Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sns.html), [SNS cifrado para alarmas de CloudWatch](https://repost.aws/knowledge-center/cloudwatch-configure-alarm-sns).

</details>

### 4. ¿Qué diseño de observabilidad de aplicaciones conserva evidencia útil?

- A. Considerar que la CPU del nodo por sí sola demuestra la causa de toda latencia de las aplicaciones.
- B. Sobrescribir todos los atributos service.name entrantes con un único nombre compartido del recopilador.
- C. Correlacionar métricas, registros y trazas seleccionados, conservando la identidad del servicio y verificando sus rutas reales.
- D. Suponer que un muestreador head del 10 % siempre conserva todos los errores y solicitudes lentas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Correlacionar rutas de señales verificadas sin colapsar la identidad.**

**Explicación:**

Las métricas describen tasas/distribuciones/estado de recursos, los registros añaden detalles de eventos y las trazas conectan operaciones instrumentadas. Ayudan a investigar, pero no garantizan una visibilidad completa ni demuestran la causa raíz. La generación de perfiles puede aportar evidencia de CPU/asignaciones/heap si se habilita y revisa explícitamente; no la proporciona automáticamente todo recopilador de trazas.

**Usa el recopilador y las rutas de señales correctos:**

Usa la configuración de trazas solo con TLS del Operator0.158/ADOT0.50 administrado por un propietario que aparece en el capítulo de referencia, y la alternativa de registro de Q2, con alcance separado. El manifiesto de Operator proviene de su propia versión, no de un artefacto de versión de Collector. Conserva service.name en el límite de la aplicación; un procesador de recursos compartido no debe aplicar mediante upsert un único valor global por encima de order-service, payment-service y otros servicios de origen.

Para las métricas de Prometheus, usa la ruta ServiceMonitor/Service conectada de la fuente o un receptor de Prometheus verificado por separado. El descubrimiento mediante anotaciones por sí solo no configura el puerto/ruta correcto, RBAC ni la distribución entre réplicas de los targets. awsemf exporta a CloudWatch, mientras que AMP requiere un endpoint real de remote-write y una identidad SigV4. No dibujes una ruta a AMP si la configuración solo tiene awsemf.

**Ejemplo de instrumentación Java:**

Una alternativa a un starter de Spring Boot es el agente Java de OpenTelemetry upstream. La versión inspeccionada es 2.31.1; prepara su JAR revisado y una aplicación/JVM compatible mediante el proceso de compilación de la aplicación. Así se evita mezclar declaraciones de Gradle y application.properties dentro de un bloque de código Java o copiar un starter 1.18-alpha no alineado. No añadas otro agente a un proceso ya instrumentado por CloudWatch Auto Monitor u otro propietario.

Esta es una configuración de runtime de la aplicación, no un comando de prueba de auditoría. Selecciona trazas OTLP/HTTP para el receptor TLS de la fuente y deja desactivada la exportación de métricas/registros del SDK para estas rutas separadas. Monta la CA de confianza y conserva cualquier otra opción de inicio de JVM necesaria:

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

Java agent 2.x usa http/protobuf de forma predeterminada; el ejemplo explicita esa elección. Un endpoint HTTP específico de señal incluye /v1/traces. El endpoint gRPC 4317 usa otro protocolo y no puede sustituirse cambiando únicamente el puerto. Se verificaron los metadatos de versión/configuración; aquí no se ejecutó ningún agente Java, JDK ni aplicación.

**Ejemplo de instrumentación Python:**

Usa el adaptador RequestTracing de la fuente con Python 3.10+ y SDK/exportador HTTP 1.44.0 alineados. Establece estos valores en el entorno de la aplicación de pagos, sustituye el nombre de clúster de ejemplo y monta la CA de confianza:

```bash
export OTEL_SERVICE_NAME=payment-service
export CLUSTER_NAME=my-owned-cluster
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://adot-traces-collector.tracing-demo.svc:4318/v1/traces
export OTEL_EXPORTER_OTLP_TRACES_CERTIFICATE=/etc/otel/ca.crt
```

A continuación se reproduce el adaptador para dejar explícitos el ciclo de vida y el límite de la solicitud:

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

Crea una instancia al iniciar la aplicación, llama a handle_request desde el controlador real del framework con nombres normalizados de encabezados entrantes y la operación de negocio real, y llama a close durante el apagado ordenado. Esto no es un servidor Flask ni una implementación de pagos; no se presupone que existan app/request/jsonify/process_transaction. Propaga el contexto suministrado a las llamadas salientes reales y al trabajo asíncrono usando el mecanismo compatible del framework.

La auditoría ejercitó este adaptador con la exportación del SDK deshabilitada, incluida la conservación de resultados/errores de negocio y las comprobaciones puras de propagación/muestreo. Esto no demuestra que se exportaran trazas activas ni que se desplegara un Collector.

**Alinea la confianza IRSA, los permisos y el ServiceAccount:**

El siguiente ejemplo independiente de Terraform coincide con la identidad tracing-demo/adot-traces del Collector de la fuente. Usa entradas declaradas y un proveedor OIDC de IAM ya existente para el emisor real del clúster. Las condiciones de confianza incluyen sub y aud. X-Ray PutTraceSegments no admite un ARN de alcance a nivel de recurso, por lo que la política usa el recurso comodín requerido, con una acción/Región restringidas y la confianza acotada. Esto no concede permisos no relacionados de CloudWatch o AMP:

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

Antes de crear el Collector, se puede crear de forma atómica un ServiceAccount nuevo y administrado por un propietario, con la anotación de su rol, en el namespace ya preparado. Los ServiceAccount/roles existentes requieren el procedimiento de actualización/importación de su propietario; no sobrescribas otra identidad ni combines una asociación de Pod Identity no relacionada:

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

Un cambio en la anotación no inyecta credenciales retroactivamente en los Pod en ejecución; revisa si es necesario realizar un rollout. Verifica el emisor/proveedor real, la audiencia del token, el rol asumido y la ruta de red. El grupo X-Ray filtra las trazas coincidentes; no instrumenta las aplicaciones ni concede permisos al recopilador. Usa la configuración de workspace/fuente de datos de Q1 en vez de duplicar un comando create de AMG incompleto. En esta auditoría no se creó ningún rol/grupo/ServiceAccount de IAM.

**Browser RUM es una ruta distinta:**

El cliente web de CloudWatch RUM envía datos PutRumEvents a CloudWatch RUM, no automáticamente a un receptor OTLP de ADOT. Cuando se habilita el trazado de X-Ray, puede añadir X-Amzn-Trace-Id a las solicitudes HTTP permitidas. De forma predeterminada, las trazas de cliente/servidor no están conectadas: revisa la propagación/puenteo del servidor compatible y los encabezados permitidos de CORS. Los ejemplos anteriores, que solo usan W3C, no consumen automáticamente un encabezado de X-Ray. Un cliente de navegador genérico de OpenTelemetry necesitaría su propio diseño compatible de endpoint OTLP/autenticación/CORS.

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

- Mide las distribuciones de latencia, el rendimiento, las tasas de error y la saturación con una población/período definidos. Un conjunto de trazas muestreadas no es automáticamente una distribución métrica imparcial.
- Usa nombres de servicio acotados, rutas normalizadas, versión/entorno e identidad de clúster/namespace. Los ID de cliente/tenant y las URL de solicitudes sin procesar pueden crear problemas de cardinalidad y privacidad; no son etiquetas de métricas predeterminadas.
- El muestreo head decide antes de conocer el resultado final de una solicitud. No puede garantizar que se conserven todos los errores/solicitudes lentas, y el muestreo tail no puede recuperar los spans descartados previamente. El muestreo tail necesita enrutamiento con afinidad de traza y búferes/ventanas de tiempo adecuados.
- Los datos de sesión/usuario de RUM, los registros, las trazas y los perfiles requieren controles de acceso, políticas de consentimiento/recopilación y retención adecuados. Los ID de correlación son metadatos, no autenticación.
- Las pruebas de rendimiento y la generación de perfiles complementan las señales de runtime. Estos ejemplos no afirman haber obtenido un nuevo benchmark ni resultados de rendimiento en producción.

Referencias: [configuración del agente Java](https://opentelemetry.io/docs/zero-code/java/agent/configuration/), [configuración del SDK Java](https://opentelemetry.io/docs/languages/java/configuration/), [CloudWatch RUM/X-Ray](https://docs.aws.amazon.com/xray/latest/devguide/xray-services-RUM.html), [capítulo de referencia](../../eks/06-eks-monitoring-logging.md).

</details>

### 5. ¿Cómo se deben monitorear los registros del plano de control de EKS administrado por AWS?

- A. Conectándose por SSH directamente a los nodos del plano de control administrado por AWS.
- B. Configurando los tipos de registros de EKS necesarios, verificando su entrega a CloudWatch Logs y aplicando consultas/controles de acceso adecuados.
- C. Suponiendo que un DaemonSet de nodos de trabajo puede leer el sistema de archivos del plano de control administrado.
- D. Creando un panel de registros y suponiendo que publica automáticamente una métrica ErrorCount.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Configurar y verificar la ruta de registro administrada.**

**Explicación:**

EKS envía directamente a CloudWatch Logs de la cuenta los tipos de registros del plano de control seleccionados. Un recopilador de nodos de trabajo no es la fuente de estos registros administrados. Esto proporciona evidencia diagnóstica/de auditoría sin acceso SSH al plano de control, pero no garantiza un registro de todas las llamadas a la API ni demuestra el cumplimiento. La política de auditoría, las fases, el momento de habilitación, la ingesta y la retención determinan qué está disponible.

**Tipos de registros y su alcance:**

| Tipo | Uso |
| --- | --- |
| api | Diagnóstico y errores del servidor de API; no es un archivo completo de solicitudes/respuestas |
| audit | Eventos de auditoría registrados de la API de Kubernetes y campos de identidad/recurso/estado |
| authenticator | Diagnóstico de autenticación/asignación de IAM; distingue la autenticación de la autorización de RBAC |
| controllerManager | Diagnóstico de conciliación del controlador |
| scheduler | Decisiones/fallos de programación y diagnósticos relacionados |

Inspecciona primero la configuración existente del clúster. Para un cambio aprobado que active los cinco tipos, la actualización del capítulo de referencia captura un ID de actualización y comprueba el estado; sigue comprobándolo hasta que finalice correctamente y después verifica la entrega real de los registros:

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

La llamada final a DescribeUpdate comprueba el estado, no es un waiter ni una prueba de ingesta. Si solo seleccionas algunos tipos, conserva todos los tipos existentes necesarios; no copies un bloque que desactive explícitamente authenticator/controllerManager/scheduler solo para habilitar api/audit. En un clúster nuevo, incluye el registro en su configuración revisada de creación/IaC. No crees otro clúster incompleto solo para configurar el monitoreo. Los registros del controlador de EKS Capabilities usan la ruta de entrega independiente descrita en la fuente.

**Consulta los campos JSON reales:**

Selecciona el grupo propio /aws/eks/CLUSTER/cluster y un intervalo de tiempo acotado. Ejemplo de respuestas 5xx registradas:

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

Inspecciona los registros del autenticador antes de definir filtros de fallos específicos del formato. Una subcadena de fallo/denegación puede pasar por alto casos reales o coincidir con texto no relacionado, y un mensaje de autenticación de IAM por sí solo no describe todos los resultados de autorización de Kubernetes.

**Un panel no publica una métrica:**

Un widget de Logs Insights ejecuta una consulta. Una alarma basada en una métrica personalizada necesita un publicador real, como un filtro de métricas. El siguiente ejemplo independiente de Terraform conecta un grupo de registros STANDARD, un filtro, su métrica, una alarma y un panel. Administra/importa el grupo de registros existente mediante su propietario real antes de usar esta configuración; la clave KMS y los permisos del topic SNS/publicador deben estar preparados de antemano. No crea un clúster de EKS ni una clave KMS nuevos.

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

El filtro cuenta los nuevos registros de auditoría ResponseComplete ingeridos con responseStatus.code>=500. El nombre de métrica con prefijo del clúster distingue el clúster sin inventar una dimensión ClusterName que no existe en el JSON de auditoría. El filtro, la alarma y el widget de métricas usan exactamente el mismo namespace/nombre y no tienen dimensiones. La consulta del panel puede incluir registros antiguos, pero el filtro de métricas no rellena datos históricos. Son recuentos de eventos registrados, no una tasa de errores de API ni un total de solicitudes deduplicado; pueden producirse entregas duplicadas.

Un default_value de 0 se emite cuando llegan registros, pero ninguno coincide; si no entran registros, los datos aún pueden faltar. Los filtros de métricas no pueden combinar un valor predeterminado con dimensiones. La alarma empieza intencionadamente con las acciones deshabilitadas, trata explícitamente los datos faltantes y usa un umbral ilustrativo. Verifica los nuevos datapoints de métricas, los permisos, las suscripciones y una prueba de entrega controlada antes de habilitarla.

jsonencode evita las comillas rotas de shell del comando antiguo del panel. Si usas la CLI, pasa un archivo JSON válido con --dashboard-body file://dashboard.json e inspecciona DashboardValidationMessages. PutDashboard sustituye el contenido existente; conserva los widgets y la configuración de su propietario. La validación local de HCL/JSON no ejecuta el motor de filtros/consultas de AWS.

**KMS y retención:**

CloudWatch Logs cifra los datos de registro de forma predeterminada. Asociar una clave KMS simétrica administrada por el cliente modifica el cifrado de los datos ingeridos posteriormente; no es la primera capa de cifrado y no vuelve a cifrar los registros antiguos. Usa una clave de la Región del grupo de registros, conserva las claves/permisos antiguos mientras se necesiten los datos antiguos y distingue los permisos de asociación de los de lectura. Al desasociarla, los datos nuevos vuelven al cifrado predeterminado; deshabilitar/eliminar una clave antigua puede hacer que no se puedan leer los datos que conserva.

El servicio regional de Logs necesita permiso para usar la clave. El siguiente fragmento es solo una sentencia que el propietario de la clave debe integrar en una política existente conservando las sentencias de administración/delegación. Sustituye de manera coherente todos los identificadores de ejemplo; no lo uses como política completa de sustitución de la clave:

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

El ARN del grupo de registros en el contexto de cifrado no lleva el sufijo :*. El operador que asocia la clave necesita los permisos documentados de Logs y kms:DescribeKey. Los lectores/escritores necesitan los permisos KMS adecuados para sus operaciones, a través del servicio regional de Logs. La rotación de claves o un período de espera de eliminación breve no elimina la necesidad de conservar el acceso de descifrado para los datos históricos. La retención de 90 días es un ejemplo, no una garantía de cumplimiento o inmutabilidad.

**Limita correctamente el acceso de lectura:**

Esta política de identidad ilustrativa permite el grupo seleccionado y sus flujos, además del descifrado de una clave a través de Logs. La política de la clave también debe permitir al principal previsto. No concede acciones de administración de registros o claves:

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

La documentación actual de autorización de AWS admite limitar StartQuery y GetQueryResults al grupo de registros; no los amplíes a Resource:* basándote en suposiciones antiguas. DescribeLogStreams y FilterLogEvents son acciones de grupo, mientras que GetLogEvents es una acción de flujo. El formato ARN de LogGroup de AWS incluye :* para la mayoría de las acciones de IAM; las formas logGroupArn y el contexto de cifrado/etiquetado lo omiten. Los flujos de consola/detección pueden necesitar acciones de lectura adicionales; DescribeLogGroups es un permiso de alcance independiente que no admite ARN a nivel de recurso, y la política anterior no lo concede implícitamente.

Durante esta auditoría no se modificó ni ejecutó la configuración de registro del clúster, la retención, la política de clave, el filtro de métricas, el panel, la alarma ni ninguna consulta en la nube. Referencias: [filtros de métricas de CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html), [formas de ARN de LogGroup](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html), [acciones IAM de Logs](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html), [cifrado de registros de KMS](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html).

</details>

### 6. ¿Qué estrategia de monitoreo ayuda más a optimizar los costos de Amazon EKS?

- A. Recopilar todas las métricas disponibles independientemente de su utilidad
- B. Combinar el uso de recursos, la asignación de costos y los posibles desperdicios revisados por los propietarios
- C. Supervisar el rendimiento sin examinar el gasto
- D. Revisar únicamente la factura mensual final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Combinar el uso de recursos, la asignación de costos y los posibles desperdicios revisados por los propietarios**

**Explicación:** Compara la CPU, la memoria, el almacenamiento, las solicitudes, los límites y las tendencias de las cargas de trabajo con los costos asignados. Investiga las anomalías y las desviaciones del presupuesto con el propietario del recurso. Estas señales identifican oportunidades; no garantizan ahorros ni demuestran que se pueda eliminar un recurso.

**Eficiencia de recursos y asignación de costos**

Reutiliza la instalación de kube-prometheus-stack de la guía fuente, kube-state-metrics y ServiceMonitor de kubelet con certificados de servicio verificados. cAdvisor usa `/metrics/cadvisor` en el puerto HTTPS de métricas de kubelet; no es un puerto de Service independiente llamado `cadvisor`. No añadas un monitor duplicado ni desactives la verificación de TLS para que funcione el scrape.

Las siguientes expresiones de CPU y memoria devuelven **ratios de uso/solicitud por contenedor**, no utilización de la capacidad del nodo ni costo monetario. Un ratio puede superar 1. Las solicitudes nulas/ausentes no producen ningún ratio; eso no significa que el uso sea cero. `max` elimina copias duplicadas del scrape con la identidad indicada; confirma que las copias representan realmente la misma carga de trabajo. Este ejemplo se dirige al Prometheus local de un clúster. Para un backend compartido, ambas familias de métricas deben llevar una etiqueta de clúster coherente. También hay que tener cuidado al interpretar un intervalo de tiempo, debido a la reutilización de nombres de Pod y a los reinicios de contenedores. Estas métricas de contenedores no describen la reserva completa del scheduler para los recursos a nivel de Pod, los contenedores init ni la sobrecarga de Pod.

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

Crea dos paneles en Grafana usando la fuente de datos de Prometheus existente y estas consultas; llama al panel **Uso de recursos frente a solicitudes**, usa una unidad de ratio/porcentaje y conserva la identidad del clúster, namespace, Pod y contenedor. Un ConfigMap que contenga un `cost-dashboard.json` no especificado no crea un panel utilizable. Con el sidecar de Grafana de la guía fuente, para aprovisionar un panel JSON revisado también se necesita la etiqueta configurada `grafana_dashboard: "1"`.

**OpenCost o Kubecost**

Para evaluar OpenCost por primera vez con el Prometheus existente de la guía fuente, guarda lo siguiente como `opencost-values.yaml`. El chart comprobado es **2.5.31**, aplicación **1.121.2**. Configura el ID real del clúster y la URL de Prometheus. La etiqueta de ServiceMonitor debe coincidir con el selector de Prometheus; permite el namespace `opencost` en la selección de namespaces. Esto no instala otro Prometheus/node exporter.

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

Abre `http://localhost:9090` mientras se ejecuta el reenvío de puertos. Esta configuración básica usa una caché de exportador efímera, desactiva la ingesta de Cloud Cost y MCP, y solo expone un Service ClusterIP. Revisa la persistencia, el dimensionamiento, la autenticación/el acceso de red, RBAC y el estado del scrape antes de compartirlo; ClusterIP no es una frontera de autorización entre tenants. Las estimaciones de precios bajo demanda deben conciliarse con la facturación real, los descuentos, los precios de Spot, los créditos, los costos compartidos, el almacenamiento y los cargos de red. La integración de facturación de AWS es una configuración independiente; la autenticación admitida mediante cuenta de servicio/SDK predeterminado de AWS no requiere incorporar claves de acceso de larga duración.

Kubecost es una opción distinta. Su chart **3.3.1**, verificado, es `kubecost/kubecost` de `https://kubecost.github.io/kubecost/`. El antiguo repositorio `cost-analyzer` y los valores de Prometheus de 2.x no son una receta de instalación para 3.x: 3.x usa ClickHouse y la recopilación directa de finops-agent. Revisa su licencia, almacenamiento, compatibilidad con Kubernetes y la migración documentada de 2.x antes de instalar o actualizar. Consulta la [guía de plataforma FinOps](../../ops/13-finops-cost-platform.md) relacionada y la [documentación del chart de Kubecost](https://github.com/kubecost/cost-analyzer-helm-chart).

**Etiquetas, tags de facturación y categorías**

Las etiquetas de namespace ayudan a agrupar dentro de Kubernetes:

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

No etiquetan automáticamente los recursos EC2/EBS ni activan tags de facturación de AWS. El responsable de facturación debe aplicar tags reales de recursos de AWS y, después, activar las claves de asignación de costos aptas. Ten en cuenta los retrasos del procesamiento de facturación y verifica que aparezcan en Cost Explorer/CUR. La asignación de costos dividida de AWS es una ruta de suscripción independiente que crea registros a nivel de Pod de EKS y atributos generados por AWS como `aws:eks:namespace`; no convierte todas las etiquetas de namespace en tags de EC2. Revisa sus requisitos previos de fuentes de datos y el mayor volumen de informes.

El retrocompletado de tags de asignación de costos puede abarcar hasta 12 meses **si los recursos ya estaban etiquetados históricamente**; no puede inventar tags históricos que faltan. Una Cost Category clasifica registros de facturación mediante reglas revisadas; no es un panel. La operación CLI para crearla es `aws ce create-cost-category-definition`, no `create-cost-category`. Usa claves y valores que aparezcan realmente en los datos de facturación y configura por separado los informes o paneles guardados de Cost Explorer.

**Inventario de solo lectura de volúmenes sin adjuntar**

Ejecuta lo siguiente solo con la cuenta/Región previstas y un tag de propiedad existente. Mantiene habilitada la paginación de AWS CLI e imprime una lista de posibles candidatos en JSON. La sintaxis limitada de tags es intencionada; adapta los filtros JSON si tu tag real contiene otros caracteres.

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

`available` significa que ahora no está adjunto, no que no se use o que sea seguro eliminarlo. La fecha de creación no es la última fecha de uso. Verifica con el propietario la propiedad de PV/PVC, la política de recuperación, las cargas de trabajo pendientes, las copias de seguridad, las snapshots y los requisitos de recuperación ante desastres. Del mismo modo, una CPU/memoria baja (incluido un umbral arbitrario del 5 %) no demuestra que un Pod o balanceador de carga sea innecesario. Usa un historial representativo y señales de aplicación/SLO; no sustituyas métricas faltantes por un resultado vacío de «Pod inactivos».

**Ejemplo de presupuesto**

Este ejemplo independiente de Terraform usa un tag de facturación real y activado, y un destinatario aprobado. El **límite mensual de 1.000 USD y la alerta del 80 %** son valores ilustrativos, no costos observados. Importa/reconcilia un presupuesto existente en vez de crear un propietario en conflicto. Valida la base de costos elegida y la cobertura de tags; un filtro de tags puede omitir cargos sin etiquetar/compartidos. Aplicar este ejemplo crea una configuración de notificación real.

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

Budgets usan datos de facturación procesados y no imponen un límite de gasto estricto. Budget Actions puede aplicar controles IAM/SCP o dirigirse a instancias EC2/RDS compatibles, pero requiere permisos y revisión operativa independientes. El panel de eficiencia de recursos anterior no es un panel de facturación.

Revisa las solicitudes junto con las recomendaciones de VPA y el historial de picos/SLO, y coordina HPA con el escalado de nodos. Karpenter/Cluster Autoscaler y Spot pueden reducir costos solo cuando lo permiten las limitaciones de cargas de trabajo, interrupciones, capacidad y disrupción. Reducir las solicitudes por sí solo no reduce la factura a menos que cambien la capacidad aprovisionada o los precios. Haz seguimiento de las acciones acordadas y los resultados medidos en revisiones periódicas con los propietarios.

Las otras opciones no ofrecen este ciclo de retroalimentación: recopilar todo aumenta el costo/ruido de telemetría; el rendimiento por sí solo no muestra el gasto; esperar a la factura mensual final retrasa demasiado la investigación oportuna.

**Referencias principales:** [instalación de OpenCost](https://opencost.io/docs/installation/helm), [activación de tags de AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/activating-tags.html), [retrocompletado de tags](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-allocation-backfill.html), [asignación de costos dividida](https://docs.aws.amazon.com/cur/latest/userguide/split-cost-allocation-data.html), [acciones de presupuesto](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html).

</details>
