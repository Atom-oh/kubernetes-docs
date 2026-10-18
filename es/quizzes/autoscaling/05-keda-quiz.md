# Cuestionario de KEDA

> **Última actualización**: 16 de octubre de 2026

Este cuestionario evalúa tu comprensión de KEDA (Kubernetes Event-driven Autoscaling).

## Pregunta 1: Conceptos básicos de KEDA

<details>
<summary>¿Qué es KEDA y cuáles son sus principales beneficios?</summary>

**Respuesta:**
KEDA (Kubernetes Event-driven Autoscaling) es un proyecto de código abierto que permite que las aplicaciones de Kubernetes escalen automáticamente según eventos.

**Beneficios principales:**
1. **Escalado basado en eventos**: Escalado basado en diversas fuentes de eventos (colas de mensajes, bases de datos, streams, etc.)
2. **Escalado a cero**: Los triggers admitidos activan o desactivan las cargas de trabajo según el mínimo de réplicas, los umbrales de activación y el periodo de cooldown.
3. **Amplia compatibilidad de escaladores**: Más de 50 escaladores integrados y compatibilidad con escaladores personalizados.
4. **Integración nativa con Kubernetes**: Se integra con el HPA existente de Kubernetes.
5. **Independencia de la nube**: Funciona en entornos Kubernetes compatibles que proporcionen las API, la identidad y la conectividad necesarias.
6. **Modelo de implementación**: Una instalación estándar incluye un operador, un servidor de API de métricas y webhooks de admisión.

Los ejemplos de KEDA 2.21 usan el intervalo de versiones de Kubernetes 1.34–1.36 que se ha probado. El HPA de Kubernetes 1.37 también admite el escalado a cero en fase beta para métricas de tipo Object y External; KEDA no es la única forma de lograrlo.
</details>

## Pregunta 2: Arquitectura de KEDA

<details>
<summary>¿Cuáles son los componentes principales de KEDA?</summary>

**Respuesta:**
- **KEDA Operator**: Administra los recursos ScaledObject y ScaledJob
- **Adaptador de métricas**: Expone métricas externas al HPA mediante la agregación de API de Kubernetes y el servicio de métricas del operador.
- **Webhooks de admisión**: Validan configuraciones compatibles de recursos de KEDA.
- **ScaledObject**: Define los destinos de escalado y los triggers.
- **ScaledJob**: Jobs creados por el operador; no los escala un HPA.
- **TriggerAuthentication**: Información de autenticación para sistemas externos.
- **ClusterTriggerAuthentication**: Autenticación a nivel de clúster.

KEDA gestiona la activación y el escalado a cero de ScaledObject; el HPA gestiona las réplicas por encima de cero. El intervalo de sondeo, la sincronización del HPA y la caché de métricas son distintos. Usa un solo controlador de escalado por carga de trabajo.
</details>

## Pregunta 3: Tipos de scaler

<details>
<summary>¿Cuáles son los principales scalers compatibles con KEDA?</summary>

**Respuesta:**
**Scalers de colas de mensajes:**
- Apache Kafka, RabbitMQ, Azure Service Bus, AWS SQS
- Redis Lists/Streams, Google Pub/Sub

**Scalers de bases de datos:**
- MySQL, PostgreSQL y MongoDB

**Scalers de servicios en la nube:**
- AWS CloudWatch, Azure Monitor, GCP Pub/Sub
- Prometheus, InfluxDB

**Otros scalers:**
- Cron (basado en horarios), metrics-api (endpoint HTTP numérico); la interceptación o el almacenamiento temporal de solicitudes pertenecen al complemento HTTP independiente.
- CPU/Memory y External Push

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
  namespace: default
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
      bootstrapServers: kafka.default.svc.cluster.local:9093
      consumerGroup: my-group
      topic: my-topic
      lagThreshold: '5'
      offsetResetPolicy: latest
      tls: enable
    authenticationRef:
      name: kafka-auth
---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
  namespace: default
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

Da por existentes un listener Kafka con TLS, una CA de confianza y un Secret kafka-secrets con la configuración y las credenciales SASL válidas. Añade una referencia a la CA cuando el broker use una CA privada. La aplicación consumidora también debe usar una autenticación y un comportamiento de offsets compatibles. Con el valor predeterminado allowIdleConsumers=false, el número de réplicas está limitado por la cantidad de particiones; un grupo nuevo con offsets latest o no válidos tiene limitaciones de activación.
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
  namespace: default
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '100'
      query: sum(rate(http_requests_total{job="my-app"}[1m]))
      ignoreNullValues: 'false'
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: twitter-processor
  triggers:
  - type: metrics-api
    metadata:
      url: http://twitter-metrics-collector.default.svc.cluster.local/metrics
      targetValue: '10'
      valueLocation: tweet_count
  minReplicaCount: 1
  maxReplicaCount: 20
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: calendar-processor
  triggers:
  - type: metrics-api
    metadata:
      url: http://calendar-metrics-collector.default.svc.cluster.local/metrics
      targetValue: '1'
      valueLocation: upcoming_events
  minReplicaCount: 1
  maxReplicaCount: 10
```

Estas son alternativas independientes que usan los recolectores HTTP del capítulo de origen. Un horario fijo de Cron no consulta Google Calendar y external-push requiere un servicio gRPC real de KEDA. Mantén los recolectores disponibles por separado; las métricas ausentes o desactualizadas son errores, no equivalen a cero.
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
  namespace: default
spec:
  scaleTargetRef:
    name: batch-processor
  minReplicaCount: 0
  maxReplicaCount: 20
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '10'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 0 * * *
      end: 0 6 * * *
      desiredReplicas: '5'
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 10 * * 0,6
      end: 0 16 * * 0,6
      desiredReplicas: '2'
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: event-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: event-handler
  triggers:
  - type: cron
    metadata:
      timezone: America/New_York
      start: 0 0 24 11 *
      end: 59 23 24 11 *
      desiredReplicas: '50'
```

Las ventanas de Cron establecen un mínimo de réplicas; el HPA elige la recomendación más alta, no las suma. El escalado a cero espera el cooldown y la temporización del controlador. El segundo ejemplo programa cada 24 de noviembre; no calcula automáticamente el Black Friday, y Cron no tiene un campo de año. Revisa o elimina los horarios puntuales después de usarlos.
</details>

## Pregunta 7: Configuración de ScaledJob

<details>
<summary>¿Cómo se configura el escalado de cargas de trabajo basadas en Jobs?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: batch-job-scaler
  namespace: default
spec:
  jobTargetRef:
    backoffLimit: 4
    template:
      spec:
        containers:
        - name: batch-processor
          image: my-batch-app:latest
          command:
          - ./process-batch
        restartPolicy: Never
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: batch-queue
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
---
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: sqs-job-scaler
  namespace: default
spec:
  jobTargetRef:
    backoffLimit: 4
    template:
      spec:
        containers:
        - name: sqs-processor
          image: sqs-worker:latest
        restartPolicy: Never
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
      queueLength: '10'
      awsRegion: us-east-1
    authenticationRef:
      name: aws-credentials
  maxReplicaCount: 10
```

Usa los Secrets rabbitmq-auth/credentials y aws-credentials del capítulo de origen (provider: aws, identityOwner: keda), adaptados a estas colas. Proporciona imágenes reales de workers, una identidad de consumidor, confirmaciones, tiempos de visibilidad e idempotencia. jobTargetRef es un JobSpec con una plantilla; ScaledJob no usa HPA.
</details>

## Pregunta 8: Escalado con métricas de Istio

<details>
<summary>¿Cómo se configura el escalado usando métricas del service mesh de Istio?</summary>

**Respuesta:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: productpage
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '50'
      query: "sum(rate(istio_requests_total{\n  reporter=\"destination\",\n      \
        \    destination_service_namespace=\"default\",\n          destination_service_name=\"\
        productpage\",\n  response_code!~\"5.*\"\n}[1m]))\n"
      ignoreNullValues: 'false'
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '0.5'
      query: "histogram_quantile(0.95,\n  sum(rate(istio_request_duration_milliseconds_bucket{\n\
        \    reporter=\"destination\",\n          destination_service_namespace=\"\
        default\",\n          destination_service_name=\"productpage\"\n  }[1m]))\
        \ by (le)\n) / 1000\n"
      ignoreNullValues: 'false'
    metricType: Value
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: error-rate-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: backend-service
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      threshold: '0.05'
      query: (sum(rate(istio_requests_total{reporter="destination",destination_service_namespace="default",destination_service_name="backend-service",response_code=~"5.*"}[2m]))
        or vector(0)) / clamp_min(sum(rate(istio_requests_total{reporter="destination",destination_service_namespace="default",destination_service_name="backend-service"}[2m])),
        0.001)
      ignoreNullValues: 'false'
    metricType: Value
  minReplicaCount: 1
  maxReplicaCount: 10
```

Los totales de solicitudes por segundo usan AverageValue (total/objetivo). La latencia p95 de todo el servicio y la proporción de errores usan Value (réplicas actuales × métrica/objetivo), que crea un bucle de realimentación distinto. Los ejemplos presuponen métricas del lado de destino para el namespace indicado y muestras representativas no vacías. Controla las series ausentes o NaN, limita el escalado y comprueba que añadir réplicas ayude de verdad; la latencia y los errores pueden originarse en servicios dependientes y suelen ser señales de alerta más seguras. No se han medido resultados de escalado en producción.
</details>

## Pregunta 9: Monitoreo y solución de problemas

<details>
<summary>¿Cómo se supervisan las actividades de escalado de KEDA?</summary>

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
   kubectl logs -n keda -l app=keda-operator-metrics-apiserver
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
   # Inspect existing operator diagnostics
   kubectl logs -n keda deployment/keda-operator --since=10m

   # Check metrics adapter status
   kubectl get apiservice v1beta1.external.metrics.k8s.io

   # Check authentication information
   kubectl get triggerauthentication
   kubectl get secret <auth-secret> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
   ```

El segundo proceso manager se eliminó: iniciar otro /manager dentro de un Pod del operador no es una prueba de conectividad. Usa los registros existentes, las condiciones de los recursos y el estado de APIService. Las métricas de KEDA enumeradas se verificaron para la versión 2.20; las métricas de réplicas del HPA requieren kube-state-metrics y un recolector configurado.
</details>

## Pregunta 10: Integración con Amazon EKS

<details>
<summary>¿Qué consideraciones hay que tener en cuenta al integrar KEDA con Amazon EKS?</summary>

**Respuesta:**
1. **Configuración de permisos de IAM**:
   ```yaml
   serviceAccount:
     operator:
       create: true
       name: keda-operator
       annotations:
         eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-role
         eks.amazonaws.com/sts-regional-endpoints: 'true'
   ```

2. **Integración de servicios de AWS**:
   ```yaml
   - type: aws-sqs-queue
     metadata:
       queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/my-queue
       awsRegion: us-west-2
       queueLength: '5'
     authenticationRef:
       name: aws-credentials
   - type: aws-cloudwatch
     metadata:
       namespace: AWS/ApplicationELB
       metricName: RequestCount
       dimensionName: LoadBalancer
       dimensionValue: app/my-alb/1234567890
       awsRegion: us-west-2
       targetMetricValue: '100'
       minMetricValue: '0'
       metricStat: Sum
       metricStatPeriod: '60'
       metricCollectionTime: '300'
     authenticationRef:
       name: aws-credentials
   ```

3. **Consideraciones de red**:
   - Evalúa los endpoints de VPC, DNS, rutas, políticas y el costo total de NAT, endpoints y zonas de disponibilidad; el ahorro depende de la carga de trabajo.
   - Configuración de los grupos de seguridad.
   - Configuración del enrutamiento de subredes.

4. **Integración de monitoreo**:
   ```yaml
   annotations:
     prometheus.io/scrape: 'true'
     prometheus.io/port: '8080'
     prometheus.io/path: /metrics
   ```

5. **Consideraciones de Fargate**:
   - Es habitual ubicar los componentes de KEDA en EC2, pero no es un requisito universal del protocolo. Valida la ubicación de cómputo, el acceso a la agregación de API y los webhooks.
   - Los destinos aptos pueden usar Fargate con perfiles y capacidad compatibles. EKS Pod Identity no admite Fargate; usa un mecanismo de identidad aplicable, como IRSA.
   - Ajusta los límites de recursos y las políticas de escalado.

6. **Optimización de costos**:
   - Usa instancias Spot cuando corresponda.
   - Reduce costos con el escalado a cero.
   - Establece umbrales de escalado adecuados.

La lista de triggers YAML es un fragmento para ScaledObjects independientes y presupone la autenticación aws-credentials del capítulo de origen. RequestCount de CloudWatch con Sum/60 segundos es un recuento por periodo, no RPS. IRSA requiere una relación de confianza OIDC existente y correctamente acotada, además de permisos de lectura; los permisos del consumidor son independientes. Las anotaciones de scrape no instalan ni configuran por sí solas CloudWatch Container Insights: configura el recolector, IAM y el destino de exportación. Escalar la carga de trabajo a cero no elimina automáticamente los nodos ni todos los costos.
</details>

---

**Puntuación:**
- 8-10 correctas: Excelente (nivel de experto en KEDA)
- 6-7 correctas: Bueno (se recomienda aprendizaje adicional)
- 4-5 correctas: Promedio (se necesita revisar los conceptos básicos)
- 0-3 correctas: Insuficiente (se necesita volver a estudiar todo el contenido)
