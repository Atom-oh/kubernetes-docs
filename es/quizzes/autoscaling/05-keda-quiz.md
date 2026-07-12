# Cuestionario de KEDA

Este cuestionario evalúa tu comprensión de KEDA (Kubernetes Event-driven Autoscaling).

## Pregunta 1: Conceptos básicos de KEDA

<details>
<summary>¿Qué es KEDA y cuáles son sus principales beneficios?</summary>

**Respuesta:**
KEDA (Kubernetes Event-driven Autoscaling) es un proyecto de código abierto que permite que las aplicaciones de Kubernetes escalen automáticamente según eventos.

**Beneficios principales:**
1. **Escalado basado en eventos**: Escalado basado en diversas fuentes de eventos (colas de mensajes, bases de datos, streams, etc.)
2. **Escalar a cero**: Reduce a 0 réplicas cuando no hay actividad para ahorrar costos
3. **Soporte para diversos scalers**: Más de 50 scalers integrados y soporte para scalers personalizados
4. **Nativo de Kubernetes**: Se integra con el HPA existente de Kubernetes
5. **Agnóstico de la nube**: Funciona en cualquier entorno de Kubernetes
6. **Modelo de Deployment simple**: Deployment sencillo con un solo operator
</details>

## Pregunta 2: Arquitectura de KEDA

<details>
<summary>¿Cuáles son los componentes principales de KEDA?</summary>

**Respuesta:**
- **KEDA Operator**: Administra los recursos ScaledObject y ScaledJob
- **Metrics Adapter**: Proporciona métricas personalizadas al HPA
- **Admission Webhooks**: Validación y mutación de recursos
- **ScaledObject**: Define objetivos y triggers de escalado
- **ScaledJob**: Escalado de workload basado en Job
- **TriggerAuthentication**: Información de autenticación de sistemas externos
- **ClusterTriggerAuthentication**: Autenticación a nivel de cluster
</details>

## Pregunta 3: Tipos de scaler

<details>
<summary>¿Cuáles son los principales scalers compatibles con KEDA?</summary>

**Respuesta:**
**Scalers de colas de mensajes:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**Scalers de bases de datos:**
- MySQL, PostgreSQL, MongoDB, Cassandra

**Scalers de servicios en la nube:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**Otros scalers:**
- Cron (basado en tiempo), HTTP (basado en solicitudes)
- CPU/Memory, External Push

**Scalers personalizados:**
- Métricas definidas por el usuario mediante External Scaler
</details>

## Pregunta 4: Configuración de ScaledObject

<details>
<summary>¿Cuál es un ejemplo de configuración de ScaledObject basado en Kafka?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kafka-scaledobject
spec:
  scaleTargetRef:
    name: kafka-consumer
  minReplicaCount: 0
  maxReplicaCount: 30
  pollingInterval: 30
  cooldownPeriod: 300
  triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka:9092
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: '5'
      offsetResetPolicy: latest
    authenticationRef:
      name: kafka-auth

---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
spec:
  secretTargetRef:
  - parameter: sasl
    name: kafka-secrets
    key: sasl
  - parameter: username
    name: kafka-secrets
    key: username
  - parameter: password
    name: kafka-secrets
    key: password
```
</details>

## Pregunta 5: Escalado con métricas personalizadas

<details>
<summary>¿Cómo configuras el escalado personalizado usando métricas de Prometheus?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: prometheus-scaledobject
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: http_requests_per_second
      threshold: '100'
      query: sum(rate(http_requests_total{job="my-app"}[1m]))

---
# Twitter metrics-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaledobject
spec:
  scaleTargetRef:
    name: twitter-processor
  triggers:
  - type: external-push
    metadata:
      scalerAddress: twitter-scaler:8080
      metricName: twitter_mentions
      threshold: '10'

---
# Google Calendar-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaledobject
spec:
  scaleTargetRef:
    name: meeting-processor
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 9 * * 1-5"  # Weekday 9 AM
      end: "0 18 * * 1-5"   # Weekday 6 PM
      desiredReplicas: "5"
```
</details>

## Pregunta 6: Escalado basado en Cron

<details>
<summary>¿Cómo implementas el escalado basado en tiempo?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaledobject
spec:
  scaleTargetRef:
    name: batch-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  # Business hours scaling (weekdays 9-18)
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 9 * * 1-5"
      end: "0 18 * * 1-5"
      desiredReplicas: "10"

  # Nightly batch processing (daily midnight)
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 0 * * *"
      end: "0 6 * * *"
      desiredReplicas: "5"

  # Weekend minimal operation
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: "0 10 * * 0,6"
      end: "0 16 * * 0,6"
      desiredReplicas: "2"

---
# Special event response scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: event-scaledobject
spec:
  scaleTargetRef:
    name: event-handler
  triggers:
  # Black Friday preparation
  - type: cron
    metadata:
      timezone: America/New_York
      start: "0 0 24 11 *"  # November 24th midnight
      end: "59 23 24 11 *"  # November 24th 23:59
      desiredReplicas: "50"
```
</details>

## Pregunta 7: Configuración de ScaledJob

<details>
<summary>¿Cómo configuras el escalado de workload basado en Job?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-job-scaler
spec:
  jobTargetRef:
    template:
      spec:
        template:
          spec:
            containers:
            - name: batch-processor
              image: my-batch-app:latest
              command: ["./process-batch"]
            restartPolicy: Never
        backoffLimit: 4
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      queueName: batch-queue
      host: amqp://rabbitmq:5672
      queueLength: '5'
    authenticationRef:
      name: rabbitmq-auth

---
# AWS SQS-based Job scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: sqs-job-scaler
spec:
  jobTargetRef:
    template:
      spec:
        template:
          spec:
            containers:
            - name: sqs-processor
              image: sqs-worker:latest
            restartPolicy: Never
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789/my-queue
      queueLength: '10'
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
```
</details>

## Pregunta 8: Escalado con métricas de Istio

<details>
<summary>¿Cómo configuras el escalado usando métricas de Istio service mesh?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaledobject
spec:
  scaleTargetRef:
    name: productpage
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  # Request rate-based scaling
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: istio_request_rate
      threshold: '50'
      query: |
        sum(rate(istio_requests_total{
          destination_service_name="productpage",
          response_code!~"5.*"
        }[1m]))

  # Response time-based scaling
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: istio_response_time
      threshold: '0.5'
      query: |
        histogram_quantile(0.95,
          sum(rate(istio_request_duration_milliseconds_bucket{
            destination_service_name="productpage"
          }[1m])) by (le)
        ) / 1000

---
# Service mesh error rate-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: error-rate-scaler
spec:
  scaleTargetRef:
    name: backend-service
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: error_rate
      threshold: '0.05'  # 5% error rate
      query: |
        sum(rate(istio_requests_total{
          destination_service_name="backend-service",
          response_code=~"5.*"
        }[1m])) /
        sum(rate(istio_requests_total{
          destination_service_name="backend-service"
        }[1m]))
```
</details>

## Pregunta 9: Monitoreo y solución de problemas

<details>
<summary>¿Cómo monitoreas las actividades de escalado de KEDA?</summary>

**Respuesta:**
1. **Revisar las métricas de KEDA**:
   ```bash
   kubectl get scaledobject
   kubectl describe scaledobject <name>
   kubectl get hpa
   ```

2. **Revisar los logs de KEDA**:
   ```bash
   kubectl logs -n keda -l app=keda-operator
   kubectl logs -n keda -l app=keda-metrics-apiserver
   ```

3. **Monitoreo de eventos**:
   ```bash
   kubectl get events --field-selector involvedObject.name=<scaledobject-name>
   ```

4. **Métricas de Prometheus**:
   ```promql
   # KEDA scaler metrics
   keda_scaler_metrics_value
   keda_scaled_object_paused
   keda_scaled_object_errors_total

   # HPA metrics
   kube_horizontalpodautoscaler_status_current_replicas
   kube_horizontalpodautoscaler_status_desired_replicas
   ```

5. **Solución de problemas comunes**:
   ```bash
   # Scaler connection test
   kubectl exec -n keda deployment/keda-operator -- /manager --zap-log-level=debug

   # Check metrics adapter status
   kubectl get apiservice v1beta1.external.metrics.k8s.io

   # Check authentication information
   kubectl get triggerauthentication
   kubectl describe secret <auth-secret>
   ```
</details>

## Pregunta 10: Integración con Amazon EKS

<details>
<summary>¿Cuáles son las consideraciones al integrar KEDA con Amazon EKS?</summary>

**Respuesta:**
1. **Configuración de permisos de IAM**:
   ```yaml
   # IRSA (IAM Roles for Service Accounts) configuration
   serviceAccount:
     annotations:
       eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/keda-role
   ```

2. **Integración de servicios de AWS**:
   ```yaml
   # SQS Scaler
   - type: aws-sqs-queue
     metadata:
       queueURL: https://sqs.region.amazonaws.com/account/queue-name
       awsRegion: us-west-2

   # CloudWatch Scaler
   - type: aws-cloudwatch
     metadata:
       namespace: AWS/ApplicationELB
       metricName: RequestCount
       dimensionName: LoadBalancer
       dimensionValue: app/my-alb/1234567890
   ```

3. **Consideraciones de red**:
   - Usar VPC endpoints (ahorro de costos)
   - Configuración de security group
   - Configuración del enrutamiento de subnets

4. **Integración de monitoreo**:
   ```yaml
   # CloudWatch Container Insights
   annotations:
     prometheus.io/scrape: "true"
     prometheus.io/port: "8080"
     prometheus.io/path: "/metrics"
   ```

5. **Consideraciones de Fargate**:
   - KEDA Operator se ejecuta en nodos EC2
   - Los workloads escalados pueden usar Fargate
   - Ajustar los límites de recursos y las políticas de escalado

6. **Optimización de costos**:
   - Usar con instancias Spot
   - Ahorrar costos con escalado a cero
   - Establecer umbrales de escalado adecuados
</details>

---

**Puntuación:**
- 8-10 correctas: Excelente (nivel de experto en KEDA)
- 6-7 correctas: Bueno (se recomienda aprendizaje adicional)
- 4-5 correctas: Promedio (se necesita revisar los conceptos básicos)
- 0-3 correctas: Insuficiente (se necesita volver a estudiar todo el contenido)
