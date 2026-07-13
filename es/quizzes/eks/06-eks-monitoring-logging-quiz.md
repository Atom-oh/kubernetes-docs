# Cuestionario sobre monitoreo y logging de Amazon EKS

Este cuestionario evalúa tu comprensión de las características, herramientas y mejores prácticas de monitoreo y logging de Amazon EKS.

## Descripción general del cuestionario
- Monitoreo de EKS Cluster
- Logging de containers y aplicaciones
- Recopilación y análisis de métricas de rendimiento
- Alertas y detección de anomalías
- Arquitectura de monitoreo y logging
- Mejores prácticas y herramientas

## Preguntas de opción múltiple

### 1. ¿Cuál es el enfoque más efectivo para crear una solución integral de monitoreo para un Amazon EKS cluster?

A. Usar solo CloudWatch
B. Usar solo Prometheus y Grafana
C. Usar CloudWatch, Prometheus, Grafana y X-Ray integrados
D. Escribir scripts de monitoreo personalizados

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Usar CloudWatch, Prometheus, Grafana y X-Ray integrados**

**Explicación:**
El enfoque más efectivo para crear una solución integral de monitoreo para un Amazon EKS cluster es integrar CloudWatch, Prometheus, Grafana y X-Ray. Este enfoque integrado proporciona visibilidad completa en los niveles de infraestructura, cluster, aplicación y trazabilidad distribuida.

**Beneficios clave de una solución de monitoreo integrada:**

1. **Monitoreo multicapa**:
   - Métricas a nivel de infraestructura de AWS (CloudWatch)
   - Métricas a nivel de Kubernetes cluster (Prometheus)
   - Métricas a nivel de aplicación (CloudWatch, Prometheus)
   - Trazabilidad distribuida (X-Ray)

2. **Recopilación integral de datos**:
   - Métricas del sistema (CPU, memoria, disco, red)
   - Métricas de recursos de Kubernetes (pods, nodes, controllers)
   - Métricas personalizadas de aplicaciones
   - Trazabilidad de transacciones de servicios distribuidos

3. **Visualización y análisis flexibles**:
   - Dashboards preconfigurados (CloudWatch, Grafana)
   - Dashboards personalizados (Grafana)
   - Consultas y alertas avanzadas (PromQL, CloudWatch Alarms)
   - Mapas de servicios y análisis de trazas (X-Ray)

**Métodos de implementación:**

1. **Configurar CloudWatch Container Insights**:
   ```bash
   # Install CloudWatch agent
   kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
   ```

2. **Instalar Prometheus y Grafana**:
   ```bash
   # Create Prometheus namespace
   kubectl create namespace prometheus

   # Install Prometheus using Helm
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/prometheus \
     --namespace prometheus \
     --set alertmanager.persistentVolume.storageClass="gp2" \
     --set server.persistentVolume.storageClass="gp2"

   # Install Grafana
   helm repo add grafana https://grafana.github.io/helm-charts
   helm install grafana grafana/grafana \
     --namespace prometheus \
     --set persistence.storageClassName="gp2" \
     --set persistence.enabled=true \
     --set adminPassword='EKS!sAWSome' \
     --set datasources."datasources\\.yaml".apiVersion=1 \
     --set datasources."datasources\\.yaml".datasources[0].name=Prometheus \
     --set datasources."datasources\\.yaml".datasources[0].type=prometheus \
     --set datasources."datasources\\.yaml".datasources[0].url=http://prometheus-server.prometheus.svc.cluster.local \
     --set datasources."datasources\\.yaml".datasources[0].access=proxy \
     --set datasources."datasources\\.yaml".datasources[0].isDefault=true
   ```

3. **Configurar AWS Distro for OpenTelemetry (ADOT) y X-Ray**:
   ```bash
   # Install ADOT operator
   kubectl apply -f https://github.com/aws-observability/aws-otel-collector/releases/latest/download/opentelemetry-operator.yaml

   # Configure ADOT collector with X-Ray integration
   cat <<EOF | kubectl apply -f -
   apiVersion: opentelemetry.io/v1alpha1
   kind: OpenTelemetryCollector
   metadata:
     name: adot-collector
   spec:
     mode: deployment
     serviceAccount: adot-collector
     config: |
       receivers:
         otlp:
           protocols:
             grpc:
               endpoint: 0.0.0.0:4317
             http:
               endpoint: 0.0.0.0:4318
       processors:
         batch:
           timeout: 1s
       exporters:
         awsxray:
           region: ${AWS_REGION}
         awsemf:
           region: ${AWS_REGION}
       service:
         pipelines:
           traces:
             receivers: [otlp]
             processors: [batch]
             exporters: [awsxray]
           metrics:
             receivers: [otlp]
             processors: [batch]
             exporters: [awsemf]
   EOF
   ```

4. **Integrar CloudWatch con Prometheus**:
   ```bash
   # Create Amazon Managed Prometheus workspace
   aws amp create-workspace --alias eks-monitoring

   # Configure CloudWatch agent
   cat <<EOF | kubectl apply -f -
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: prometheus-cwagent-config
     namespace: amazon-cloudwatch
   data:
     cwagentconfig.json: |
       {
         "logs": {
           "metrics_collected": {
             "prometheus": {
               "prometheus_config_path": "/etc/prometheusconfig/prometheus.yaml",
               "emf_processor": {
                 "metric_declaration": [
                   {
                     "source_labels": ["job", "pod_name"],
                     "label_matcher": "^kubernetes-pods;.*$",
                     "dimensions": [["ClusterName", "Namespace", "PodName"]],
                     "metric_selectors": ["^.*$"]
                   }
                 ]
               }
             }
           }
         }
       }
   EOF
   ```

**Componentes clave de monitoreo:**

1. **CloudWatch Container Insights**:
   - Métricas a nivel de cluster, node y pod
   - Recopilación de logs de containers
   - Dashboards y alertas automáticos

2. **Prometheus y Grafana**:
   - Métricas detalladas de Kubernetes
   - Métricas y dashboards personalizados
   - Consultas y alertas avanzadas

3. **AWS X-Ray**:
   - Trazabilidad distribuida
   - Mapas de servicios
   - Análisis de rutas de solicitudes

4. **AWS Distro for OpenTelemetry**:
   - Recopilación estandarizada de telemetría
   - Compatibilidad con diversos backends
   - Instrumentación neutral respecto al proveedor

**Mejores prácticas:**

1. **Implementar una estrategia de monitoreo por capas**:
   - Nivel de infraestructura: nodes, red, almacenamiento
   - Nivel de cluster: control plane, nodes, pods
   - Nivel de aplicación: services, endpoints, métricas de negocio

2. **Establecer una estrategia efectiva de alertas**:
   - Configurar alertas según la prioridad
   - Evitar la fatiga por alertas
   - Definir rutas de escalamiento

3. **Implementar respuestas automatizadas**:
   - Triggers de auto-scaling
   - Mecanismos de autorreparación
   - Mantenimiento proactivo

4. **Optimización de costos**:
   - Recopilar solo las métricas necesarias
   - Muestreo y agregación adecuados
   - Optimizar las políticas de retención de datos

**Ejemplos prácticos de implementación:**

1. **Arquitectura de monitoreo integral**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  EKS Cluster      |    |  CloudWatch       |    |  Amazon Managed   |
   |                   |    |                   |    |  Prometheus       |
   +-------------------+    +-------------------+    +-------------------+
           |                        ^                        ^
           |                        |                        |
           v                        |                        |
   +-------------------+            |                        |
   |                   |            |                        |
   |  ADOT Collector   |------------+                        |
   |                   |                                     |
   +-------------------+                                     |
           |                                                 |
           v                                                 |
   +-------------------+                                     |
   |                   |                                     |
   |  Prometheus       |------------------------------------|
   |                   |
   +-------------------+
           |
           v
   +-------------------+    +-------------------+
   |                   |    |                   |
   |  Grafana          |    |  X-Ray           |
   |                   |    |                   |
   +-------------------+    +-------------------+
   ```

2. **Configurar infraestructura de monitoreo con Terraform**:
   ```hcl
   # Amazon Managed Prometheus workspace
   resource "aws_prometheus_workspace" "eks_monitoring" {
     alias = "eks-monitoring"
   }

   # Amazon Managed Grafana workspace
   resource "aws_grafana_workspace" "eks_monitoring" {
     name                     = "eks-monitoring"
     account_access_type      = "CURRENT_ACCOUNT"
     authentication_providers = ["AWS_SSO"]
     permission_type          = "SERVICE_MANAGED"
     data_sources             = ["PROMETHEUS", "CLOUDWATCH", "XRAY"]
   }

   # CloudWatch log group
   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/logs"
     retention_in_days = 30
   }
   ```

Problemas con las otras opciones:
- **A. Usar solo CloudWatch**: CloudWatch proporciona métricas de infraestructura de AWS y métricas básicas de containers, pero tiene limitaciones para métricas específicas de Kubernetes o monitoreo detallado a nivel de aplicación.
- **B. Usar solo Prometheus y Grafana**: Esta combinación proporciona monitoreo potente de Kubernetes, pero carece de integración con servicios de AWS o capacidades de trazabilidad distribuida.
- **D. Escribir scripts de monitoreo personalizados**: Los scripts personalizados son difíciles de mantener, no escalan bien y no aprovechan las funciones avanzadas de las herramientas estándar de la industria.
</details>
### 2. ¿Cuál es el mejor enfoque para recopilar y analizar de manera efectiva los logs de containers en Amazon EKS?

A. Recuperar manualmente archivos de logs de cada node
B. Leer archivos de logs directamente desde dentro de los containers
C. Usar Fluentd/Fluent Bit para enviar logs a CloudWatch Logs o Elasticsearch
D. Enviar logs solo a la salida estándar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Usar Fluentd/Fluent Bit para enviar logs a CloudWatch Logs o Elasticsearch**

**Explicación:**
El mejor enfoque para recopilar y analizar de manera efectiva los logs de containers en Amazon EKS es usar recolectores de logs como Fluentd o Fluent Bit para enviar logs a CloudWatch Logs, Amazon OpenSearch Service (anteriormente Elasticsearch Service) u otros sistemas de análisis de logs. Este enfoque proporciona escalabilidad, centralización y capacidades de búsqueda y análisis.

**Beneficios clave del logging basado en Fluentd/Fluent Bit:**

1. **Gestión centralizada de logs**:
   - Recopilar todos los logs de containers en una única ubicación
   - Búsqueda y análisis de logs en todo el cluster
   - Retención y archivado de logs a largo plazo

2. **Escalabilidad y confiabilidad**:
   - Compatibilidad con clusters a gran escala
   - Mecanismos de buffering y reintento
   - Minimizar la pérdida de logs

3. **Procesamiento flexible de logs**:
   - Filtrado y transformación de logs
   - Compatibilidad con logging estructurado
   - Compatibilidad con varios destinos de salida

4. **Análisis y visualización integrados**:
   - CloudWatch Logs Insights
   - OpenSearch Dashboards (anteriormente Kibana)
   - Búsqueda y consultas avanzadas

**Métodos de implementación:**

1. **Integración de Fluent Bit con CloudWatch Logs**:
   ```bash
   # Create Fluent Bit namespace
   kubectl create namespace amazon-cloudwatch

   # Install AWS for Fluent Bit
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/cloudwatch-namespace.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-service-account.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-role.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-role-binding.yaml

   # Deploy Fluent Bit ConfigMap and DaemonSet
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-configmap.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/aws-for-fluent-bit/master/eks/fluent-bit-ds.yaml
   ```

2. **Integración de Fluentd con Amazon OpenSearch Service**:
   ```yaml
   # Fluentd ConfigMap
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: fluentd-config
     namespace: kube-system
   data:
     fluent.conf: |
       <source>
         @type tail
         path /var/log/containers/*.log
         pos_file /var/log/fluentd-containers.log.pos
         tag kubernetes.*
         read_from_head true
         <parse>
           @type json
           time_format %Y-%m-%dT%H:%M:%S.%NZ
         </parse>
       </source>

       <filter kubernetes.**>
         @type kubernetes_metadata
         @id filter_kube_metadata
       </filter>

       <match kubernetes.**>
         @type elasticsearch
         host search-eks-logs.us-west-2.es.amazonaws.com
         port 443
         scheme https
         ssl_verify false
         index_name fluentd.${record['kubernetes']['namespace_name']}.${record['kubernetes']['pod_name']}
         type_name fluentd
         logstash_format true
         logstash_prefix fluentd.${record['kubernetes']['namespace_name']}
         <buffer>
           @type file
           path /var/log/fluentd-buffers/kubernetes.system.buffer
           flush_mode interval
           retry_type exponential_backoff
           flush_thread_count 2
           flush_interval 5s
           retry_forever
           retry_max_interval 30
           chunk_limit_size 2M
           queue_limit_length 8
           overflow_action block
         </buffer>
       </match>
   ```

3. **Recopilación de logs usando AWS Distro for OpenTelemetry (ADOT)**:
   ```yaml
   # ADOT collector configuration
   apiVersion: opentelemetry.io/v1alpha1
   kind: OpenTelemetryCollector
   metadata:
     name: adot-collector
   spec:
     mode: daemonset
     serviceAccount: adot-collector
     config: |
       receivers:
         filelog:
           include: [ /var/log/containers/*.log ]
           start_at: beginning
           include_file_path: true
           operators:
             - type: json_parser
               timestamp:
                 parse_from: attributes.time
                 layout: '%Y-%m-%dT%H:%M:%S.%LZ'
       processors:
         batch:
           timeout: 1s
       exporters:
         awscloudwatchlogs:
           log_group_name: "/aws/eks/my-cluster/logs"
           log_stream_name: "{pod_name}.{container_name}"
           region: us-west-2
       service:
         pipelines:
           logs:
             receivers: [filelog]
             processors: [batch]
             exporters: [awscloudwatchlogs]
   ```

**Mejores prácticas de recopilación y análisis de logs:**

1. **Implementar logging estructurado**:
   - Usar logs en formato JSON
   - Campos y formatos de logs consistentes
   - Incluir IDs de correlación

2. **Optimizar niveles de logs**:
   - Establecer niveles de logs adecuados
   - Minimizar logs de depuración en producción
   - Proporcionar contexto suficiente para eventos importantes

3. **Estrategia de retención y archivado de logs**:
   - Equilibrar costos y requisitos de cumplimiento
   - Usar almacenamiento por niveles
   - Configurar archivado automático

4. **Consideraciones de seguridad de logs**:
   - Filtrar información sensible
   - Controlar el acceso a logs
   - Garantizar la integridad de los logs

**Ejemplos prácticos de implementación:**

1. **Configuración de Fluent Bit con múltiples destinos de salida**:
   ```
   [INPUT]
       Name                tail
       Tag                 kube.*
       Path                /var/log/containers/*.log
       Parser              docker
       DB                  /var/log/flb_kube.db
       Mem_Buf_Limit       5MB
       Skip_Long_Lines     On
       Refresh_Interval    10

   [FILTER]
       Name                kubernetes
       Match               kube.*
       Kube_URL            https://kubernetes.default.svc:443
       Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
       Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
       Merge_Log           On
       K8S-Logging.Parser  On
       K8S-Logging.Exclude Off

   [OUTPUT]
       Name                cloudwatch_logs
       Match               kube.*
       region              us-west-2
       log_group_name      /aws/eks/my-cluster/logs
       log_stream_prefix   ${kubernetes['namespace_name']}.${kubernetes['pod_name']}.
       auto_create_group   true

   [OUTPUT]
       Name                es
       Match               kube.*
       Host                search-eks-logs.us-west-2.es.amazonaws.com
       Port                443
       TLS                 On
       Index               eks-logs
       Suppress_Type_Name  On
   ```

2. **Consulta de CloudWatch Logs Insights para análisis de logs**:
   ```
   fields @timestamp, @message, kubernetes.pod_name, kubernetes.namespace_name, log
   | filter kubernetes.namespace_name = "production"
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 100
   ```

3. **Configurar infraestructura de logging con Terraform**:
   ```hcl
   # CloudWatch log group
   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/logs"
     retention_in_days = 30
     tags = {
       Environment = "production"
       Application = "eks-cluster"
     }
   }

   # OpenSearch domain
   resource "aws_elasticsearch_domain" "eks_logs" {
     domain_name           = "eks-logs"
     elasticsearch_version = "OpenSearch_1.3"

     cluster_config {
       instance_type  = "m5.large.elasticsearch"
       instance_count = 3
     }

     ebs_options {
       ebs_enabled = true
       volume_size = 100
     }

     encrypt_at_rest {
       enabled = true
     }

     node_to_node_encryption {
       enabled = true
     }

     domain_endpoint_options {
       enforce_https       = true
       tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
     }

     advanced_security_options {
       enabled                        = true
       internal_user_database_enabled = true
       master_user_options {
         master_user_name     = "admin"
         master_user_password = var.opensearch_master_password
       }
     }
   }
   ```

Problemas con las otras opciones:
- **A. Recuperar manualmente archivos de logs de cada node**: No es escalable, no está automatizado y los logs pueden perderse si los nodes fallan.
- **B. Leer archivos de logs directamente desde dentro de los containers**: No se puede acceder a los logs cuando los containers terminan, y el análisis centralizado es difícil.
- **D. Enviar logs solo a la salida estándar**: Enviar logs a la salida estándar es una buena práctica, pero sin un mecanismo para recopilar y centralizar estos logs, el análisis efectivo es difícil.
</details>
### 3. ¿Cuál es el mejor enfoque para crear un sistema de alertas efectivo en Amazon EKS?

A. Revisar manualmente archivos de logs
B. Usar solo CloudWatch Alarms
C. Usar solo Prometheus AlertManager
D. Integrar CloudWatch Alarms, Prometheus AlertManager y EventBridge para admitir varios canales de notificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Integrar CloudWatch Alarms, Prometheus AlertManager y EventBridge para admitir varios canales de notificación**

**Explicación:**
El mejor enfoque para crear un sistema de alertas efectivo en Amazon EKS es integrar CloudWatch Alarms, Prometheus AlertManager y EventBridge para admitir varios canales de notificación. Este enfoque integrado proporciona alertas integrales en los niveles de infraestructura, cluster y aplicación, y admite varios canales de notificación y mecanismos de respuesta.

**Beneficios clave de un sistema de alertas integrado:**

1. **Alertas multicapa**:
   - Alertas a nivel de infraestructura de AWS (CloudWatch)
   - Alertas a nivel de Kubernetes cluster (Prometheus)
   - Alertas a nivel de aplicación (métricas personalizadas)
   - Alertas basadas en eventos (EventBridge)

2. **Compatibilidad con varios canales de notificación**:
   - Email, SMS (SNS)
   - Slack, Microsoft Teams (webhooks)
   - PagerDuty, OpsGenie (gestión de incidentes)
   - Funciones Lambda personalizadas

3. **Gestión inteligente de alertas**:
   - Agrupación y deduplicación de alertas
   - Enrutamiento y escalamiento de alertas
   - Supresión y silenciamiento de alertas

**Métodos de implementación:**

1. **Configurar CloudWatch Alarms**:
   ```bash
   # Create CloudWatch alarm for node CPU usage
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-Node-High-CPU \
     --alarm-description "Alarm when CPU exceeds 80%" \
     --metric-name CPUUtilization \
     --namespace AWS/EC2 \
     --dimensions Name=AutoScalingGroupName,Value=eks-node-group-1 \
     --statistic Average \
     --period 300 \
     --threshold 80 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 2 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts
   ```

2. **Configurar Prometheus AlertManager**:
   ```yaml
   # alertmanager-config.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: alertmanager-config
     namespace: prometheus
   data:
     alertmanager.yml: |
       global:
         resolve_timeout: 5m
       route:
         group_by: ['alertname', 'job', 'severity']
         group_wait: 30s
         group_interval: 5m
         repeat_interval: 12h
         receiver: 'sns-forwarder'
         routes:
         - match:
             severity: critical
           receiver: 'pagerduty-critical'
         - match:
             severity: warning
           receiver: 'slack-warnings'
       receivers:
       - name: 'sns-forwarder'
         webhook_configs:
         - url: 'http://sns-forwarder.monitoring.svc.cluster.local:9087/alert'
       - name: 'pagerduty-critical'
         pagerduty_configs:
         - service_key: '<PAGERDUTY_SERVICE_KEY>'
       - name: 'slack-warnings'
         slack_configs:
         - api_url: '<SLACK_WEBHOOK_URL>'
           channel: '#eks-alerts'
           title: '{{ .GroupLabels.alertname }}'
           text: '{{ .CommonAnnotations.description }}'
   ```

3. **Definir reglas de alertas de Prometheus**:
   ```yaml
   # prometheus-rules.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: prometheus-rules
     namespace: prometheus
   data:
     alert-rules.yml: |
       groups:
       - name: node-alerts
         rules:
         - alert: NodeHighCPU
           expr: instance:node_cpu_utilization:rate5m > 80
           for: 5m
           labels:
             severity: warning
           annotations:
             summary: "High CPU usage on {{ $labels.instance }}"
             description: "CPU usage is above 80% for 5 minutes on {{ $labels.instance }}"

         - alert: NodeMemoryFilling
           expr: instance:node_memory_utilization:rate5m > 80
           for: 5m
           labels:
             severity: warning
           annotations:
             summary: "High memory usage on {{ $labels.instance }}"
             description: "Memory usage is above 80% for 5 minutes on {{ $labels.instance }}"

       - name: pod-alerts
         rules:
         - alert: PodCrashLooping
           expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
           for: 10m
           labels:
             severity: warning
           annotations:
             summary: "Pod {{ $labels.pod }} is crash looping"
             description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} is crash looping"

         - alert: PodNotReady
           expr: sum by (namespace, pod) (kube_pod_status_phase{phase=~"Pending|Unknown"}) > 0
           for: 15m
           labels:
             severity: warning
           annotations:
             summary: "Pod {{ $labels.pod }} is not ready"
             description: "Pod {{ $labels.pod }} in namespace {{ $labels.namespace }} has been in non-ready state for more than 15 minutes"
   ```

4. **Configurar reglas de EventBridge**:
   ```bash
   # Create EventBridge rule for EKS events
   aws events put-rule \
     --name EKS-Control-Plane-Events \
     --event-pattern '{"source":["aws.eks"],"detail-type":["EKS Cluster Control Plane Health"]}'

   # Set SNS topic as target
   aws events put-targets \
     --rule EKS-Control-Plane-Events \
     --targets 'Id"="1","Arn"="arn:aws:sns:us-west-2:123456789012:eks-alerts"'
   ```

**Integración y enrutamiento de alertas:**

1. **Integración de alertas mediante SNS Topics**:
   ```bash
   # Create SNS topic
   aws sns create-topic --name eks-alerts

   # Add email subscription
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --protocol email \
     --notification-endpoint ops-team@example.com

   # Add Lambda subscription
   aws sns subscribe \
     --topic-arn arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --protocol lambda \
     --notification-endpoint arn:aws:lambda:us-west-2:123456789012:function:process-eks-alerts
   ```

2. **Procesamiento y enrutamiento de alertas usando Lambda**:
   ```python
   import json
   import boto3
   import requests

   def lambda_handler(event, context):
       message = json.loads(event['Records'][0]['Sns']['Message'])

       # Route to different channels based on alert severity
       if 'AlarmName' in message:
           severity = get_alarm_severity(message['AlarmName'])
       else:
           severity = 'info'

       if severity == 'critical':
           send_to_pagerduty(message)
       elif severity == 'warning':
           send_to_slack(message, '#eks-warnings')
       else:
           send_to_slack(message, '#eks-info')

       return {
           'statusCode': 200,
           'body': json.dumps('Alert processed successfully!')
       }

   def get_alarm_severity(alarm_name):
       if 'Critical' in alarm_name:
           return 'critical'
       elif 'Warning' in alarm_name:
           return 'warning'
       else:
           return 'info'

   def send_to_pagerduty(message):
       # Implement PagerDuty API call
       pass

   def send_to_slack(message, channel):
       # Implement Slack webhook call
       pass
   ```

**Mejores prácticas de alertas:**

1. **Evitar la fatiga por alertas**:
   - Centrarse solo en alertas importantes
   - Agrupar y deduplicar alertas
   - Limitar la frecuencia de alertas

2. **Proporcionar contenido claro en las alertas**:
   - Descripción del problema e impacto
   - Acciones recomendadas para la resolución
   - Recursos y contexto relacionados

3. **Prioridad y escalamiento de alertas**:
   - Clasificar las alertas según la severidad
   - Rutas de escalamiento claras
   - Establecer objetivos de tiempo de respuesta

4. **Probar y validar alertas**:
   - Probar alertas regularmente
   - Monitorear falsos positivos y falsos negativos
   - Revisar la efectividad de las alertas

**Ejemplos prácticos de implementación:**

1. **Arquitectura integral de alertas**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  CloudWatch       |    |  Prometheus       |    |  EventBridge      |
   |  Alarms           |    |  AlertManager     |    |  Rules            |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  SNS Topic        |<---|  Lambda           |<---|  SQS Queue        |
   |                   |    |  Forwarder        |    |                   |
   +-------------------+    +-------------------+    +-------------------+
           |
           v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Email/SMS        |    |  Slack/Teams      |    |  PagerDuty        |
   |                   |    |                   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
   ```

2. **Configurar infraestructura de alertas con Terraform**:
   ```hcl
   # SNS topic
   resource "aws_sns_topic" "eks_alerts" {
     name = "eks-alerts"
   }

   # CloudWatch alarm
   resource "aws_cloudwatch_metric_alarm" "node_cpu" {
     alarm_name          = "EKS-Node-High-CPU"
     comparison_operator = "GreaterThanThreshold"
     evaluation_periods  = 2
     metric_name         = "CPUUtilization"
     namespace           = "AWS/EC2"
     period              = 300
     statistic           = "Average"
     threshold           = 80
     alarm_description   = "This metric monitors EC2 CPU utilization for EKS nodes"
     alarm_actions       = [aws_sns_topic.eks_alerts.arn]
     dimensions = {
       AutoScalingGroupName = "eks-node-group-1"
     }
   }

   # EventBridge rule
   resource "aws_cloudwatch_event_rule" "eks_events" {
     name        = "EKS-Control-Plane-Events"
     description = "Capture EKS control plane events"
     event_pattern = jsonencode({
       source      = ["aws.eks"]
       detail-type = ["EKS Cluster Control Plane Health"]
     })
   }

   resource "aws_cloudwatch_event_target" "sns" {
     rule      = aws_cloudwatch_event_rule.eks_events.name
     target_id = "SendToSNS"
     arn       = aws_sns_topic.eks_alerts.arn
   }
   ```

Problemas con las otras opciones:
- **A. Revisar manualmente archivos de logs**: La revisión manual no es escalable, no proporciona alertas en tiempo real y no admite respuestas automatizadas.
- **B. Usar solo CloudWatch Alarms**: CloudWatch Alarms son útiles para alertas a nivel de infraestructura de AWS, pero tienen limitaciones para métricas específicas de Kubernetes o alertas detalladas a nivel de aplicación.
- **C. Usar solo Prometheus AlertManager**: Prometheus AlertManager proporciona alertas potentes para métricas de Kubernetes, pero tiene integración limitada con eventos de servicios de AWS o alertas a nivel de infraestructura.
</details>
### 4. ¿Cuál es el enfoque más efectivo para el monitoreo del rendimiento de aplicaciones en Amazon EKS?

A. Monitorear solo métricas básicas del sistema
B. Recopilar y analizar métricas personalizadas de aplicaciones
C. Implementar observabilidad integrada que incluya trazabilidad distribuida, métricas y logs
D. Realizar pruebas manuales periódicas de rendimiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Implementar observabilidad integrada que incluya trazabilidad distribuida, métricas y logs**

**Explicación:**
El enfoque más efectivo para el monitoreo del rendimiento de aplicaciones en Amazon EKS es implementar observabilidad integrada que incluya trazabilidad distribuida, métricas y logs. Este enfoque integral proporciona visibilidad completa del rendimiento de las aplicaciones e información detallada para la resolución de problemas y la optimización.

**Componentes clave de la observabilidad integrada:**

1. **Trazabilidad distribuida**:
   - Rastrear el flujo de solicitudes entre services
   - Identificar cuellos de botella de latencia
   - Comprender las rutas de propagación de errores

2. **Métricas**:
   - Uso de recursos y del sistema
   - Indicadores de rendimiento de aplicaciones
   - Métricas de negocio

3. **Logs**:
   - Eventos detallados de aplicaciones
   - Información de errores y excepciones
   - Contexto de depuración

4. **Profiling**:
   - Análisis de uso de CPU y memoria
   - Identificar hotspots y cuellos de botella
   - Descubrir oportunidades de optimización a nivel de código

**Métodos de implementación:**

1. **Configurar AWS Distro for OpenTelemetry (ADOT)**:
   ```bash
   # Install ADOT operator
   kubectl apply -f https://github.com/aws-observability/aws-otel-collector/releases/latest/download/opentelemetry-operator.yaml

   # Configure ADOT collector
   cat <<EOF | kubectl apply -f -
   apiVersion: opentelemetry.io/v1alpha1
   kind: OpenTelemetryCollector
   metadata:
     name: adot-collector
   spec:
     mode: deployment
     serviceAccount: adot-collector
     config: |
       receivers:
         otlp:
           protocols:
             grpc:
               endpoint: 0.0.0.0:4317
             http:
               endpoint: 0.0.0.0:4318
         prometheus:
           config:
             scrape_configs:
             - job_name: 'kubernetes-pods'
               kubernetes_sd_configs:
               - role: pod
               relabel_configs:
               - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                 action: keep
                 regex: true

       processors:
         batch:
           timeout: 1s
         resource:
           attributes:
           - key: service.name
             action: upsert
             value: "${SERVICE_NAME}"

       exporters:
         awsxray:
           region: "${AWS_REGION}"
         awsemf:
           region: "${AWS_REGION}"
           namespace: EKSApplicationMetrics
         awscloudwatchlogs:
           region: "${AWS_REGION}"
           log_group_name: "/aws/eks/my-cluster/application-logs"

       service:
         pipelines:
           traces:
             receivers: [otlp]
             processors: [batch, resource]
             exporters: [awsxray]
           metrics:
             receivers: [otlp, prometheus]
             processors: [batch, resource]
             exporters: [awsemf]
           logs:
             receivers: [otlp]
             processors: [batch, resource]
             exporters: [awscloudwatchlogs]
   EOF
   ```

2. **Instrumentación de aplicaciones**:
   ```java
   // Java application example (Spring Boot)

   // build.gradle
   dependencies {
       implementation 'io.opentelemetry:opentelemetry-api'
       implementation 'io.opentelemetry:opentelemetry-sdk'
       implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
       implementation 'io.opentelemetry.instrumentation:opentelemetry-spring-boot-starter:1.18.0-alpha'
   }

   // application.properties
   otel.service.name=order-service
   otel.exporter.otlp.endpoint=http://adot-collector:4317
   ```

   ```python
   # Python application example
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.sdk.resources import SERVICE_NAME, Resource

   # Set up resource and tracer
   resource = Resource(attributes={
       SERVICE_NAME: "payment-service"
   })

   tracer_provider = TracerProvider(resource=resource)
   processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="adot-collector:4317"))
   tracer_provider.add_span_processor(processor)
   trace.set_tracer_provider(tracer_provider)

   # Use tracer
   tracer = trace.get_tracer(__name__)

   @app.route('/process-payment', methods=['POST'])
   def process_payment():
       with tracer.start_as_current_span("process-payment") as span:
           span.set_attribute("payment.amount", request.json.get('amount'))
           # Perform business logic
           result = process_transaction(request.json)
           span.set_attribute("payment.status", result['status'])
           return jsonify(result)
   ```

3. **Configurar dashboard de Amazon Managed Grafana**:
   ```bash
   # Create Amazon Managed Grafana workspace
   aws grafana create-workspace \
     --name eks-monitoring \
     --authentication-providers AWS_SSO \
     --permission-type SERVICE_MANAGED \
     --data-sources PROMETHEUS CLOUDWATCH XRAY
   ```

4. **Mapa de servicios y análisis de trazas de X-Ray**:
   ```bash
   # Create X-Ray group
   aws xray create-group \
     --group-name "EKS-Applications" \
     --filter-expression "service(\"order-service\") OR service(\"payment-service\")"
   ```

**Métricas y dimensiones clave de observabilidad:**

1. **Indicadores principales de rendimiento de aplicaciones**:
   - Latencia de solicitudes (p50, p90, p99)
   - Throughput de solicitudes (RPS)
   - Tasa de errores
   - Saturación (utilización de recursos)

2. **Dimensiones y labels clave**:
   - Service y endpoint
   - Cluster, namespace, pod
   - Versión y entorno
   - ID de cliente o tenant

3. **Métricas de experiencia de usuario**:
   - Tiempo de carga de página
   - Tiempo de respuesta de API
   - Latencia de interacción de usuario
   - Tasa de errores del cliente

**Mejores prácticas:**

1. **Implementar instrumentación estandarizada**:
   - Usar estándares como OpenTelemetry
   - Convenciones de nombres y labels consistentes
   - Combinar instrumentación automática y manual

2. **Garantizar la propagación de contexto**:
   - Pasar el contexto de trazas entre services
   - Mantener el contexto en operaciones asíncronas
   - Integración con sistemas externos

3. **Optimizar la estrategia de muestreo**:
   - Equilibrar costo y visibilidad
   - Muestreo basado en errores y latencia
   - Priorizar transacciones críticas

4. **Correlacionar datos de observabilidad**:
   - Conectar trazas, métricas y logs
   - Usar identificadores y labels comunes
   - Dashboards y análisis integrados

**Ejemplos prácticos de implementación:**

1. **Observabilidad integrada para arquitectura de microservices**:
   ```
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Frontend         |    |  Order Service    |    |  Payment Service  |
   |  (React)          |    |  (Java)           |    |  (Python)         |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  Browser SDK      |    |  OpenTelemetry    |    |  OpenTelemetry    |
   |  (RUM)            |    |  SDK              |    |  SDK              |
   +-------------------+    +-------------------+    +-------------------+
           |                        |                        |
           v                        v                        v
   +---------------------------------------------------------------+
   |                                                               |
   |                  ADOT Collector                               |
   |                                                               |
   +---------------------------------------------------------------+
           |                        |                        |
           v                        v                        v
   +-------------------+    +-------------------+    +-------------------+
   |                   |    |                   |    |                   |
   |  AWS X-Ray        |    |  Amazon           |    |  CloudWatch       |
   |  (Traces)         |    |  Managed Service  |    |  Logs             |
   |                   |    |  for Prometheus   |    |                   |
   +-------------------+    +-------------------+    +-------------------+
                                     |
                                     v
                            +-------------------+
                            |                   |
                            |  Amazon           |
                            |  Managed Grafana  |
                            |                   |
                            +-------------------+
   ```

2. **Configurar infraestructura de observabilidad con Terraform**:
   ```hcl
   # Amazon Managed Service for Prometheus workspace
   resource "aws_prometheus_workspace" "eks_monitoring" {
     alias = "eks-monitoring"
   }

   # Amazon Managed Grafana workspace
   resource "aws_grafana_workspace" "eks_monitoring" {
     name                     = "eks-monitoring"
     account_access_type      = "CURRENT_ACCOUNT"
     authentication_providers = ["AWS_SSO"]
     permission_type          = "SERVICE_MANAGED"
     data_sources             = ["PROMETHEUS", "CLOUDWATCH", "XRAY"]
   }

   # X-Ray group
   resource "aws_xray_group" "eks_applications" {
     group_name        = "EKS-Applications"
     filter_expression = "service(\"order-service\") OR service(\"payment-service\")"
   }

   # CloudWatch log group
   resource "aws_cloudwatch_log_group" "application_logs" {
     name              = "/aws/eks/my-cluster/application-logs"
     retention_in_days = 30
   }

   # IAM role and policy
   resource "aws_iam_role" "adot_collector" {
     name = "adot-collector"
     assume_role_policy = jsonencode({
       Version = "2012-10-17",
       Statement = [{
         Effect = "Allow",
         Principal = {
           Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${module.eks.oidc_provider}"
         },
         Action = "sts:AssumeRoleWithWebIdentity",
         Condition = {
           StringEquals = {
             "${module.eks.oidc_provider}:sub" = "system:serviceaccount:opentelemetry:adot-collector"
           }
         }
       }]
     })
   }
   ```

Problemas con las otras opciones:
- **A. Monitorear solo métricas básicas del sistema**: Las métricas del sistema son importantes para comprender el estado de la infraestructura, pero no son suficientes para identificar las causas raíz de los problemas de rendimiento de aplicaciones.
- **B. Recopilar y analizar métricas personalizadas de aplicaciones**: Las métricas de aplicaciones son importantes, pero comprender las interacciones entre services en sistemas distribuidos también requiere trazas y logs.
- **D. Realizar pruebas manuales periódicas de rendimiento**: Las pruebas de rendimiento son importantes, pero no pueden reemplazar el monitoreo continuo en entornos de producción en tiempo real ni simular completamente los patrones reales de usuarios.
</details>
### 5. ¿Cuál es la mejor forma de monitorear de manera efectiva los logs del control plane en Amazon EKS?

A. Acceder directamente a los nodes del control plane mediante SSH
B. Habilitar el logging del control plane de EKS y enviarlo a CloudWatch Logs
C. Desplegar recolectores de logs personalizados
D. Solicitar logs periódicamente al equipo de AWS Support

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Habilitar el logging del control plane de EKS y enviarlo a CloudWatch Logs**

**Explicación:**
La mejor forma de monitorear de manera efectiva los logs del control plane en Amazon EKS es habilitar el logging del control plane de EKS y enviar los logs a CloudWatch Logs. Este método aprovecha las características de EKS como servicio administrado para acceder y analizar fácilmente los logs de los componentes del control plane.

**Beneficios clave del logging del control plane de EKS:**

1. **Recopilación integral de logs**:
   - Logs del API server
   - Logs de auditoría
   - Logs del authenticator
   - Logs del controller manager
   - Logs del scheduler

2. **Solución administrada**:
   - Recopilación de logs administrada por AWS
   - No se requieren agentes adicionales
   - No se necesita acceso directo al control plane

3. **Análisis y alertas integrados**:
   - Consultas y análisis mediante CloudWatch Logs Insights
   - Integración con CloudWatch Alarms
   - Retención y archivado de logs a largo plazo

**Métodos de implementación:**

1. **Habilitar logging al crear el EKS Cluster**:
   ```bash
   # Create EKS cluster with all log types enabled
   aws eks create-cluster \
     --name my-cluster \
     --role-arn arn:aws:iam::123456789012:role/EKSClusterRole \
     --resources-vpc-config subnetIds=subnet-12345,subnet-67890,securityGroupIds=sg-12345 \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

2. **Habilitar logging para un EKS Cluster existente**:
   ```bash
   # Enable all log types for existing cluster
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
   ```

3. **Habilitar solo tipos de logs específicos**:
   ```bash
   # Enable only API server and audit logs
   aws eks update-cluster-config \
     --name my-cluster \
     --logging '{"clusterLogging":[{"types":["api","audit"],"enabled":true},{"types":["authenticator","controllerManager","scheduler"],"enabled":false}]}'
   ```

**Tipos de logs clave y usos:**

1. **Logs del API Server (api)**:
   - Solicitudes y respuestas de API
   - Creación, modificación y eliminación de recursos
   - Mensajes de error y advertencia

2. **Logs de auditoría (audit)**:
   - Registros detallados de todas las llamadas a la API
   - Rastrear quién, qué, cuándo y dónde
   - Cumplir requisitos de seguridad y cumplimiento

3. **Logs del Authenticator (authenticator)**:
   - Solicitudes de autenticación usando credenciales de AWS IAM
   - Autenticaciones correctas y fallidas
   - Depurar problemas de permisos

4. **Logs del Controller Manager (controllerManager)**:
   - Operaciones y estado de controllers
   - Actividades de reconciliación de recursos
   - Errores y reintentos de controllers

5. **Logs del Scheduler (scheduler)**:
   - Decisiones de scheduling de Pods
   - Fallos de scheduling y motivos
   - Problemas de asignación de recursos

**Análisis y monitoreo de logs:**

1. **Consultas usando CloudWatch Logs Insights**:
   ```
   # Search for API server errors
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-/
   | filter @message like /Error/
   | sort @timestamp desc
   | limit 100

   # Search audit logs for specific user
   fields @timestamp, @message
   | filter @logStream like /kube-apiserver-audit/
   | parse @message "user.username*:*" as user_prefix, username
   | filter username like /admin/
   | sort @timestamp desc
   | limit 100

   # Search for authentication failures
   fields @timestamp, @message
   | filter @logStream like /authenticator/
   | filter @message like /failed/
   | sort @timestamp desc
   | limit 100
   ```

2. **Crear dashboard de CloudWatch**:
   ```bash
   # Create dashboard monitoring API server error rate
   aws cloudwatch put-dashboard \
     --dashboard-name EKS-Control-Plane-Monitoring \
     --dashboard-body '{
       "widgets": [
         {
           "type": "log",
           "x": 0,
           "y": 0,
           "width": 24,
           "height": 6,
           "properties": {
             "query": "SOURCE \'/aws/eks/my-cluster/cluster\' | fields @timestamp, @message\n| filter @logStream like /kube-apiserver-/\n| filter @message like /Error/\n| stats count() as errorCount by bin(5m)",
             "region": "us-west-2",
             "title": "API Server Errors",
             "view": "timeSeries"
           }
         }
       ]
     }'
   ```

3. **Configurar CloudWatch Alarms**:
   ```bash
   # Create API server error alarm
   aws cloudwatch put-metric-alarm \
     --alarm-name EKS-APIServer-Errors \
     --alarm-description "Alarm when API server errors exceed threshold" \
     --metric-name ErrorCount \
     --namespace EKS \
     --statistic Sum \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 1 \
     --alarm-actions arn:aws:sns:us-west-2:123456789012:eks-alerts \
     --dimensions Name=ClusterName,Value=my-cluster
   ```

**Mejores prácticas:**

1. **Habilitación selectiva de logs**:
   - Habilitar solo los tipos de logs necesarios
   - Habilitar logs de auditoría según los requisitos de cumplimiento
   - Equilibrar costo y visibilidad

2. **Establecer política de retención de logs**:
   ```bash
   # Set CloudWatch log group retention period
   aws logs put-retention-policy \
     --log-group-name /aws/eks/my-cluster/cluster \
     --retention-in-days 90
   ```

3. **Configurar cifrado de logs**:
   ```bash
   # Set CloudWatch log group encryption
   aws logs associate-kms-key \
     --log-group-name /aws/eks/my-cluster/cluster \
     --kms-key-id arn:aws:kms:us-west-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab
   ```

4. **Controlar el acceso a logs**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:GetLogEvents",
           "logs:FilterLogEvents",
           "logs:StartQuery",
           "logs:GetQueryResults"
         ],
         "Resource": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/my-cluster/cluster:*"
       }
     ]
   }
   ```

**Ejemplos prácticos de implementación:**

1. **Configurar logging de EKS Cluster con Terraform**:
   ```hcl
   resource "aws_eks_cluster" "main" {
     name     = "my-cluster"
     role_arn = aws_iam_role.eks_cluster.arn

     vpc_config {
       subnet_ids         = var.subnet_ids
       security_group_ids = [aws_security_group.eks_cluster.id]
     }

     enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

     depends_on = [
       aws_iam_role_policy_attachment.eks_cluster_policy,
       aws_cloudwatch_log_group.eks_logs
     ]
   }

   resource "aws_cloudwatch_log_group" "eks_logs" {
     name              = "/aws/eks/my-cluster/cluster"
     retention_in_days = 90
     kms_key_id        = aws_kms_key.eks_logs.arn
   }

   resource "aws_kms_key" "eks_logs" {
     description             = "KMS key for EKS cluster logs encryption"
     deletion_window_in_days = 7
     enable_key_rotation     = true
   }
   ```

2. **Dashboard de CloudWatch Logs Insights**:
   ```hcl
   resource "aws_cloudwatch_dashboard" "eks_control_plane" {
     dashboard_name = "EKS-Control-Plane-Monitoring"

     dashboard_body = jsonencode({
       widgets = [
         {
           type = "log"
           x    = 0
           y    = 0
           width = 24
           height = 6
           properties = {
             query = "SOURCE '/aws/eks/my-cluster/cluster' | fields @timestamp, @message\n| filter @logStream like /kube-apiserver-/\n| filter @message like /Error/\n| stats count() as errorCount by bin(5m)"
             region = "us-west-2"
             title = "API Server Errors"
             view = "timeSeries"
           }
         },
         {
           type = "log"
           x    = 0
           y    = 6
           width = 24
           height = 6
           properties = {
             query = "SOURCE '/aws/eks/my-cluster/cluster' | fields @timestamp, @message\n| filter @logStream like /kube-apiserver-audit/\n| stats count() as auditCount by bin(5m)"
             region = "us-west-2"
             title = "Audit Events"
             view = "timeSeries"
           }
         }
       ]
     })
   }
   ```

Problemas con las otras opciones:
- **A. Acceder directamente a los nodes del control plane mediante SSH**: EKS es un servicio administrado, por lo que no puedes acceder directamente a los nodes del control plane.
- **C. Desplegar recolectores de logs personalizados**: Dado que el control plane es administrado por AWS, desplegar recolectores de logs personalizados no te dará acceso a los logs del control plane.
- **D. Solicitar logs periódicamente al equipo de AWS Support**: Esto es ineficiente, no proporciona monitoreo en tiempo real y no admite análisis ni alertas automatizados.
</details>
### 6. ¿Cuál es la estrategia de monitoreo más efectiva para la optimización de costos en Amazon EKS?

A. Recopilar todas las métricas posibles
B. Centrarse en monitorear el uso de recursos, tags de asignación de costos y recursos inactivos
C. Centrarse solo en el rendimiento sin monitoreo de costos
D. Revisar solo las facturas mensuales de AWS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Centrarse en monitorear el uso de recursos, tags de asignación de costos y recursos inactivos**

**Explicación:**
La estrategia de monitoreo más efectiva para la optimización de costos en Amazon EKS es centrarse en monitorear el uso de recursos, tags de asignación de costos y recursos inactivos. Este enfoque garantiza el uso eficiente de los recursos del cluster, clarifica la asignación de costos y optimiza los costos al identificar recursos desperdiciados.

**Componentes clave del monitoreo de optimización de costos:**

1. **Monitoreo del uso de recursos**:
   - Utilización de CPU, memoria y almacenamiento
   - Uso real frente a requests y limits
   - Tendencias y patrones de uso de recursos

2. **Asignación de costos y tagging**:
   - Análisis de costos por namespace, service y equipo
   - Implementar y monitorear tags de asignación de costos
   - Rastrear gastos por centro de costos y proyecto

3. **Identificar recursos inactivos y desperdiciados**:
   - Volúmenes EBS sin usar
   - Recursos sobreaprovisionados
   - Nodes y pods inactivos

4. **Detección de anomalías de costos**:
   - Alertar sobre aumentos de costos inesperados
   - Análisis de tendencias de costos
   - Monitorear gasto real frente al presupuesto

**Métodos de implementación:**

1. **Monitorear el uso de recursos de Kubernetes**:
   ```yaml
   # Monitor resource usage with Prometheus
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: kubernetes-resources
     namespace: monitoring
   spec:
     selector:
       matchLabels:
         k8s-app: kubelet
     namespaceSelector:
       matchNames:
       - kube-system
     endpoints:
     - port: https-metrics
       scheme: https
       interval: 30s
       tlsConfig:
         insecureSkipVerify: true
       bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
     - port: cadvisor
       scheme: https
       interval: 30s
       tlsConfig:
         insecureSkipVerify: true
       bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
       metricRelabelings:
       - action: keep
         sourceLabels: [__name__]
         regex: container_cpu_usage_seconds_total|container_memory_working_set_bytes|container_fs_usage_bytes
   ```

2. **Implementar tags de asignación de costos**:
   ```bash
   # Enable cost allocation tags
   aws ce update-cost-allocation-tags-status \
     --cost-allocation-tags-status '[{"TagKey": "kubernetes.io/cluster/my-cluster", "Status": "Active"}, {"TagKey": "kubernetes.io/namespace", "Status": "Active"}, {"TagKey": "app", "Status": "Active"}, {"TagKey": "team", "Status": "Active"}]'

   # Tag nodes
   aws ec2 create-tags \
     --resources i-1234567890abcdef0 \
     --tags Key=team,Value=platform Key=environment,Value=production
   ```

3. **Desplegar Kubecost**:
   ```bash
   # Install Kubecost using Helm
   helm repo add kubecost https://kubecost.github.io/cost-analyzer/
   helm install kubecost kubecost/cost-analyzer \
     --namespace kubecost \
     --create-namespace \
     --set kubecostToken="<YOUR_KUBECOST_TOKEN>" \
     --set prometheus.server.persistentVolume.size=100Gi \
     --set prometheus.nodeExporter.enabled=true \
     --set serviceMonitor.enabled=true
   ```

4. **Configurar dashboard de AWS Cost Explorer**:
   ```bash
   # Create AWS Cost Explorer dashboard
   aws ce create-cost-category \
     --name EKS-Clusters \
     --rule-version "CostCategoryExpression.v1" \
     --rules '[{"Value": "my-cluster-prod", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-prod", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}, {"Value": "my-cluster-dev", "Rule": {"Tags": {"Key": "kubernetes.io/cluster/my-cluster-dev", "Values": ["owned", "shared"], "MatchOptions": ["EQUALS"]}}}]'
   ```

**Métricas y dimensiones clave de monitoreo:**

1. **Métricas de eficiencia de recursos**:
   - Utilización de CPU = CPU usada / CPU solicitada
   - Utilización de memoria = memoria usada / memoria solicitada
   - Relación entre requests y limits de recursos

2. **Dimensiones de asignación de costos**:
   - Cluster
   - Namespace
   - Deployment/StatefulSet
   - Labels (equipo, aplicación, entorno)

3. **Métricas de identificación de desperdicio**:
   - Número de pods inactivos (utilización de CPU/memoria < 5%)
   - Volúmenes EBS no asociados
   - Load balancers sin usar

**Mejores prácticas:**

1. **Optimizar requests y limits de recursos**:
   - Establecer requests de recursos según el uso real
   - Utilizar Vertical Pod Autoscaler
   - Revisar regularmente los requests de recursos

2. **Implementar una estrategia de tagging efectiva**:
   ```yaml
   # Namespace labels example
   apiVersion: v1
   kind: Namespace
   metadata:
     name: team-a
     labels:
       team: team-a
       cost-center: cc-123
       environment: production
   ```

3. **Optimizar auto-scaling**:
   - Ajustar la configuración de Cluster Autoscaler
   - Utilizar Karpenter
   - Utilizar spot instances

4. **Revisión y optimización de costos periódicas**:
   - Reuniones semanales/mensuales de revisión de costos
   - Establecer objetivos de reducción de costos
   - Rastrear acciones de optimización

**Ejemplos prácticos de implementación:**

1. **Dashboard de costos en Grafana**:
   ```bash
   # Import Grafana dashboard
   kubectl -n monitoring create configmap cost-dashboard \
     --from-file=cost-dashboard.json
   ```

2. **Consultas de monitoreo de requests frente a uso de recursos**:
   ```
   # Prometheus query examples
   # CPU utilization vs. requests
   sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod) /
   sum(kube_pod_container_resource_requests{resource="cpu", namespace="production"}) by (pod)

   # Memory utilization vs. requests
   sum(container_memory_working_set_bytes{namespace="production"}) by (pod) /
   sum(kube_pod_container_resource_requests{resource="memory", namespace="production"}) by (pod)
   ```

3. **Script de automatización de optimización de costos**:
   ```python
   # Script example for identifying and reporting idle resources
   import boto3
   import kubernetes
   from kubernetes import client, config

   # Set up Kubernetes client
   config.load_kube_config()
   v1 = client.CoreV1Api()

   # Set up AWS client
   ec2 = boto3.client('ec2')
   elb = boto3.client('elb')

   def find_unused_volumes():
       volumes = ec2.describe_volumes(
           Filters=[
               {'Name': 'status', 'Values': ['available']},
               {'Name': 'tag:kubernetes.io/cluster/my-cluster', 'Values': ['owned']}
           ]
       )
       return volumes['Volumes']

   def find_underutilized_pods():
       pods = v1.list_pod_for_all_namespaces(watch=False)
       underutilized = []
       for pod in pods.items:
           # Get usage data from metrics API or Prometheus
           # Identify pods with low utilization
           pass
       return underutilized

   # Main function
   def main():
       unused_volumes = find_unused_volumes()
       underutilized_pods = find_underutilized_pods()

       # Generate report and alert
       generate_report(unused_volumes, underutilized_pods)

   if __name__ == "__main__":
       main()
   ```

4. **Configurar infraestructura de monitoreo de costos con Terraform**:
   ```hcl
   # AWS budget alert setup
   resource "aws_budgets_budget" "eks_monthly" {
     name              = "eks-monthly-budget"
     budget_type       = "COST"
     limit_amount      = "1000"
     limit_unit        = "USD"
     time_unit         = "MONTHLY"
     time_period_start = "2023-01-01_00:00"

     cost_filter {
       name = "TagKeyValue"
       values = [
         "kubernetes.io/cluster/my-cluster$owned"
       ]
     }

     notification {
       comparison_operator        = "GREATER_THAN"
       threshold                  = 80
       threshold_type             = "PERCENTAGE"
       notification_type          = "ACTUAL"
       subscriber_email_addresses = ["team@example.com"]
     }
   }

   # CloudWatch dashboard
   resource "aws_cloudwatch_dashboard" "eks_cost" {
     dashboard_name = "EKS-Cost-Monitoring"

     dashboard_body = jsonencode({
       widgets = [
         {
           type   = "metric"
           x      = 0
           y      = 0
           width  = 12
           height = 6
           properties = {
             metrics = [
               ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "eks-node-group-1", {"stat": "Average"}]
             ]
             period = 300
             region = "us-west-2"
             title  = "Node Group CPU Utilization"
           }
         },
         {
           type   = "metric"
           x      = 12
           y      = 0
           width  = 12
           height = 6
           properties = {
             metrics = [
               ["AWS/EC2", "NetworkIn", "AutoScalingGroupName", "eks-node-group-1", {"stat": "Sum"}],
               ["AWS/EC2", "NetworkOut", "AutoScalingGroupName", "eks-node-group-1", {"stat": "Sum"}]
             ]
             period = 300
             region = "us-west-2"
             title  = "Node Group Network Traffic"
           }
         }
       ]
     })
   }
   ```

Problemas con las otras opciones:
- **A. Recopilar todas las métricas posibles**: Recopilar todas las métricas aumenta los costos de almacenamiento, las señales importantes de optimización de costos pueden quedar enterradas en el ruido y el análisis se vuelve más complejo.
- **C. Centrarse solo en el rendimiento sin monitoreo de costos**: El rendimiento es importante, pero sin optimización de costos pueden producirse gastos innecesarios.
- **D. Revisar solo las facturas mensuales de AWS**: La revisión mensual de facturas es reactiva, no proporciona información detallada de asignación de costos y puede perder oportunidades de optimización en tiempo real.
</details>
