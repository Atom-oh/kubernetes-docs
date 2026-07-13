# Cuestionario de debugging avanzado de Amazon EKS

Este cuestionario evalúa tu comprensión de técnicas avanzadas de debugging en Amazon EKS, incluyendo respuesta a incidentes, debugging del control plane, resolución de problemas de Node, kubectl debug, consultas PromQL y observabilidad.

## Descripción general del cuestionario
- Proceso de respuesta a incidentes
- Debugging del control plane de EKS
- Resolución de problemas de Node y kubelet
- Uso del comando kubectl debug
- Consultas PromQL y análisis de métricas
- Trazado distribuido y análisis de logs

## Preguntas de opción múltiple

### 1. ¿Dónde debes revisar los audit logs del EKS API server?

A. Directorio /var/log/kubernetes/
B. Amazon CloudWatch Logs
C. Base de datos etcd
D. Comando kubectl logs

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Amazon CloudWatch Logs**

**Explicación:**
Los logs del EKS control plane son administrados por AWS y enviados a CloudWatch Logs. Los audit logs se pueden encontrar en el log group `/aws/eks/<cluster-name>/cluster`.

**Tipos de log:**
- `api`: Logs del API server
- `audit`: Audit logs
- `authenticator`: Logs de autenticación
- `controllerManager`: Logs del controller manager
- `scheduler`: Logs del scheduler

```bash
# Enable control plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# CloudWatch Logs Insights Query
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like "403"
| sort @timestamp desc
| limit 100
```

</details>

### 2. ¿Qué flag se usa para agregar un debugging container a un Pod en ejecución con kubectl debug?

A. --attach
B. --copy-to
C. --ephemeral
D. --sidecar

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. --copy-to**

**Explicación:**
El flag `--copy-to` crea una copia de un Pod existente y permite agregar debugging containers o configuraciones modificadas. Usarlo con `--share-processes` habilita compartir el process namespace.

```bash
# Add debug container to Pod copy
kubectl debug myapp-pod --copy-to=myapp-debug --container=debugger --image=busybox -- sh

# Share process namespace
kubectl debug myapp-pod --copy-to=myapp-debug --share-processes --container=debugger --image=busybox

# Direct debugging with Ephemeral container (no Pod copy)
kubectl debug -it myapp-pod --image=busybox --target=myapp-container
```

**Opciones clave:**
- `--copy-to`: Crear copia de Pod
- `--share-processes`: Compartir process namespace
- `--target`: Especificar target container (para ephemeral containers)

</details>

### 3. ¿Qué debes revisar primero cuando un Node está en estado NotReady?

A. Logs de Pod
B. Estado y logs de kubelet
C. Estado de etcd
D. Logs de CoreDNS

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Estado y logs de kubelet**

**Explicación:**
La causa más común de que un Node pase a NotReady son problemas de kubelet. Cuando kubelet no puede comunicarse con el API server, el estado del Node cambia a NotReady.

```bash
# Check node status
kubectl describe node <node-name>

# SSH to node and check kubelet status
systemctl status kubelet

# Check kubelet logs
journalctl -u kubelet -f

# Restart kubelet
sudo systemctl restart kubelet
```

**Lista de comprobación de NotReady:**
1. Estado del proceso kubelet
2. Conectividad de red (acceso al API server)
3. Espacio en disco
4. Memoria (OOM)
5. Estado del container runtime

</details>

### 4. ¿Qué consulta PromQL encuentra Pods con utilización de CPU superior al 80% durante los últimos 5 minutos?

A. `cpu_usage > 80`
B. `rate(container_cpu_usage_seconds_total[5m]) > 0.8`
C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`
D. `container_cpu_percent > 80`

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. `sum(rate(container_cpu_usage_seconds_total[5m])) by (pod) / sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod) > 0.8`**

**Explicación:**
La utilización de CPU es la proporción entre el uso real y el límite. La función `rate()` calcula el uso de CPU por segundo, que luego se divide por el límite para obtener el porcentaje.

```promql
# CPU utilization (against limit)
sum(rate(container_cpu_usage_seconds_total{container!=""}[5m])) by (pod, namespace)
/
sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod, namespace)
* 100 > 80

# Memory utilization
sum(container_memory_working_set_bytes{container!=""}) by (pod, namespace)
/
sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)
* 100 > 80

# Top 10 CPU usage in specific namespace
topk(10, sum(rate(container_cpu_usage_seconds_total{namespace="production"}[5m])) by (pod))
```

</details>

### 5. ¿Qué herramienta NO es adecuada para depurar problemas de red entre nodes en EKS?

A. tcpdump
B. wireshark
C. Pruebas ping/curl mediante kubectl exec
D. etcdctl

<details>
<summary>Ver respuesta</summary>

**Respuesta: D. etcdctl**

**Explicación:**
etcdctl es una herramienta para administrar la base de datos etcd y no está relacionada con el debugging de red. En EKS, etcd es administrado por AWS, por lo que de todos modos no puedes acceder directamente a él.

**Herramientas de debugging de red:**
```bash
# Capture packets with tcpdump
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- tcpdump -i eth0

# Test connectivity between nodes
kubectl debug node/<node-name> -it --image=nicolaka/netshoot -- ping <other-node-ip>

# Test network from within Pod
kubectl exec -it <pod-name> -- curl -v http://service-name

# DNS test
kubectl exec -it <pod-name> -- nslookup kubernetes.default.svc.cluster.local
```

</details>

### 6. ¿Cuál es la forma más efectiva de reducir el MTTD (Mean Time To Detect) en la respuesta a incidentes?

A. Monitoreo manual mejorado
B. Establecer umbrales de alerta muy bajos
C. Crear reglas de alerta apropiadas y sistemas de monitoreo automatizado
D. Extender el período de retención de logs

<details>
<summary>Ver respuesta</summary>

**Respuesta: C. Crear reglas de alerta apropiadas y sistemas de monitoreo automatizado**

**Explicación:**
Para reducir el MTTD, necesitas umbrales de alerta apropiados y monitoreo automatizado. Las alertas demasiado sensibles causan fatiga de alertas.

```yaml
# Prometheus AlertRule Example
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: eks-alerts
spec:
  groups:
  - name: eks.rules
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        / sum(rate(http_requests_total[5m])) > 0.05
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "High error rate detected"

    - alert: PodCrashLooping
      expr: |
        rate(kube_pod_container_status_restarts_total[15m]) > 0
      for: 5m
      labels:
        severity: warning
```

**Estrategias de optimización de MTTD:**
- Alertas basadas en SLO
- Alertas de burn rate de múltiples ventanas
- Clasificación de prioridad de alertas
- Rotación on-call y escalamiento

</details>

### 7. ¿Cuál es el comando para crear un Pod de debugging directamente en un Node con kubectl debug?

A. `kubectl debug node/<node-name> -it --image=busybox`
B. `kubectl exec node/<node-name> -- sh`
C. `kubectl attach node/<node-name>`
D. `kubectl run debug --node=<node-name>`

<details>
<summary>Ver respuesta</summary>

**Respuesta: A. `kubectl debug node/<node-name> -it --image=busybox`**

**Explicación:**
En Kubernetes 1.20+, el comando `kubectl debug node/` crea un Pod privilegiado en el Node con acceso al filesystem y a la red del host.

```bash
# Node debugging
kubectl debug node/ip-10-0-1-100.us-west-2.compute.internal -it --image=busybox

# Access host filesystem (mounted at /host)
# Inside the Pod:
chroot /host

# Use image with more tools
kubectl debug node/<node-name> -it --image=nicolaka/netshoot

# Check node's kubelet logs (inside Pod)
journalctl -u kubelet --no-pager | tail -100
```

**Notas importantes:**
- Los Pods de debugging de Node se ejecutan en modo privilegiado
- Tienen acceso a los host namespaces
- Restringe el acceso con RBAC en entornos de producción

</details>

### 8. ¿Qué significa "Span" en distributed tracing?

A. Tiempo total de procesamiento de una solicitud
B. Medición de tiempo de una sola unidad de trabajo
C. Latencia de red entre Services
D. Timestamp de mensajes de log

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. Medición de tiempo de una sola unidad de trabajo**

**Explicación:**
Un Span representa una sola unidad de trabajo en un sistema distribuido, incluyendo hora de inicio, hora de finalización y metadata. Varios Spans juntos forman un Trace.

**Conceptos de distributed tracing:**
- **Trace**: Colección de Spans que representa todo el flujo de la solicitud
- **Span**: Unidad de trabajo única (por ejemplo, solicitud HTTP, consulta a DB)
- **Relación parent-child**: Relaciones de llamadas entre Spans
- **Baggage**: Información de contexto propagada entre Spans

```yaml
# OpenTelemetry Collector Configuration
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: otel-collector
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    processors:
      batch:
    exporters:
      jaeger:
        endpoint: jaeger-collector:14250
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [jaeger]
```

</details>

### 9. ¿Cuál es el comando más útil para depurar problemas de CoreDNS en EKS?

A. `kubectl logs -n kube-system -l k8s-app=kube-dns`
B. `kubectl describe service kubernetes`
C. `aws eks describe-cluster`
D. `kubectl get endpoints`

<details>
<summary>Ver respuesta</summary>

**Respuesta: A. `kubectl logs -n kube-system -l k8s-app=kube-dns`**

**Explicación:**
Revisar los logs de los Pods de CoreDNS revela el estado del procesamiento de consultas DNS, errores y timeouts.

```bash
# Check CoreDNS logs
kubectl logs -n kube-system -l k8s-app=kube-dns -f

# Check CoreDNS Pod status
kubectl get pods -n kube-system -l k8s-app=kube-dns

# Check CoreDNS ConfigMap
kubectl get configmap coredns -n kube-system -o yaml

# Create DNS test Pod
kubectl run dns-test --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes.default

# Debug DNS queries
kubectl exec -it <pod-name> -- nslookup -debug kubernetes.default.svc.cluster.local
```

**Problemas comunes de CoreDNS:**
- Restricciones de recursos del Pod (CPU/memoria)
- Errores de configuración de ConfigMap
- Problemas de conexión con DNS upstream
- Problemas de conectividad del Service Cluster IP

</details>

### 10. ¿Qué comando kubectl muestra el uso de recursos de Pod en tiempo real?

A. `kubectl describe pod`
B. `kubectl top pods`
C. `kubectl get pods -o wide`
D. `kubectl logs`

<details>
<summary>Ver respuesta</summary>

**Respuesta: B. `kubectl top pods`**

**Explicación:**
El comando `kubectl top` muestra datos de uso de recursos recopilados por Metrics Server. Puedes revisar el uso de CPU y memoria en tiempo real.

```bash
# Pod resource usage across all namespaces
kubectl top pods -A

# Pods in specific namespace
kubectl top pods -n production

# Resource usage by container
kubectl top pods --containers

# Node resource usage
kubectl top nodes

# Sort by CPU
kubectl top pods --sort-by=cpu

# Sort by memory
kubectl top pods --sort-by=memory
```

**Requisitos previos:**
- Metrics Server debe estar instalado
- `kubectl top` solo proporciona snapshots en tiempo real (sin historial)
- Usa Prometheus + Grafana para monitoreo a largo plazo

</details>

## Preguntas de respuesta corta

### 1. ¿Cuál es el patrón de nombre del log group para ver logs del EKS control plane en CloudWatch Logs?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** `/aws/eks/<cluster-name>/cluster`

**Explicación:**
Los logs del EKS control plane se envían automáticamente a este log group.

```bash
# CloudWatch Logs Insights Query Example
# Log group: /aws/eks/my-cluster/cluster

# Search API server error logs
fields @timestamp, @message
| filter @logStream like /kube-apiserver/
| filter @message like /error|Error|ERROR/
| sort @timestamp desc
| limit 50

# Search specific user activity in audit logs
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"user":.*"admin"/
| sort @timestamp desc
```

</details>

### 2. ¿Qué nombre de feature gate se necesita para habilitar Ephemeral Containers en Kubernetes?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** `EphemeralContainers` (habilitado de forma predeterminada en Kubernetes 1.25+)

**Explicación:**
Esta feature pasó a beta en Kubernetes 1.23 y a GA (Generally Available) en 1.25, habilitada de forma predeterminada. No se necesita configuración adicional en EKS 1.25+.

```bash
# Add Ephemeral Container
kubectl debug -it <pod-name> --image=busybox --target=<container-name>

# Check Ephemeral Containers
kubectl get pod <pod-name> -o jsonpath='{.spec.ephemeralContainers}'

# List Ephemeral Containers added to Pod
kubectl describe pod <pod-name> | grep -A 10 "Ephemeral Containers"
```

</details>

### 3. ¿Cuál es la diferencia entre las funciones rate() e irate() en PromQL?

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
- `rate()`: Calcula la tasa promedio de cambio durante todo el rango de tiempo especificado (suave)
- `irate()`: Calcula la tasa instantánea de cambio usando solo los dos últimos puntos de datos (volátil)

**Ejemplos de uso:**
```promql
# rate() - Average request rate over 5 minutes (good for alerts, dashboards)
rate(http_requests_total[5m])

# irate() - Instant request rate (good for detecting sudden changes)
irate(http_requests_total[5m])

# CPU utilization - rate() recommended
rate(container_cpu_usage_seconds_total[5m])

# Spike detection - irate() recommended
irate(http_requests_total[1m]) > 1000
```

**Guía de selección:**
- Reglas de alerta: usa `rate()` (reduce el ruido)
- Debugging/detección de cambios repentinos: usa `irate()`
- Análisis de tendencias a largo plazo: usa `rate()`

</details>

### 4. ¿En qué path se monta el host filesystem cuando te conectas a un Node con kubectl debug?

<details>
<summary>Ver respuesta</summary>

**Respuesta:** `/host`

**Explicación:**
Cuando se crea un Pod con `kubectl debug node/`, el root filesystem del host se monta en `/host`.

```bash
# Create node debugging Pod
kubectl debug node/<node-name> -it --image=busybox

# Access host filesystem inside Pod
ls /host
cat /host/etc/kubernetes/kubelet/kubelet-config.json

# chroot to host environment
chroot /host

# After chroot, run host commands
systemctl status kubelet
journalctl -u kubelet -n 100
```

</details>

### 5. ¿Cuáles son los dos componentes principales del MTTR (Mean Time To Resolve) en la respuesta a incidentes?

<details>
<summary>Ver respuesta</summary>

**Respuesta:**
1. **MTTD (Mean Time To Detect)**: Tiempo desde que ocurre el problema hasta su detección
2. **MTTI (Mean Time To Investigate/Identify)**: Tiempo desde la detección hasta la identificación de la causa raíz y la resolución

O:
- MTTD + MTTI + MTTFix (tiempo real de corrección)

**Estrategias de mejora de MTTR:**
```
MTTR = MTTD + MTTI + MTTFix

MTTD Improvement:
- Effective monitoring and alerting
- SLO-based alerting

MTTI Improvement:
- Create runbooks
- Automated diagnostic tools

MTTFix Improvement:
- Auto-recovery mechanisms
- Rollback automation
- GitOps-based deployment
```

</details>

## Ejercicios prácticos

### 1. Escribe una consulta PromQL que cumpla los siguientes requisitos:
- Encontrar containers que se hayan reiniciado en el namespace production durante los últimos 5 minutos
- Filtrar por conteo de reinicios de 2 o más

<details>
<summary>Ver respuesta</summary>

```promql
# Containers with restart count >= 2 over last 5 minutes
increase(kube_pod_container_status_restarts_total{namespace="production"}[5m]) >= 2
```

**Consultas variantes:**
```promql
# Show Pod name with restart count
sum by (pod, container) (
  increase(kube_pod_container_status_restarts_total{namespace="production"}[5m])
) >= 2

# Total restart count (cumulative)
kube_pod_container_status_restarts_total{namespace="production"} > 5

# Top 10 most restarted Pods over last hour
topk(10,
  increase(kube_pod_container_status_restarts_total{namespace="production"}[1h])
)
```

**Para Grafana Dashboard:**
```promql
# Time series graph
rate(kube_pod_container_status_restarts_total{namespace="production"}[5m])

# Table (current status)
kube_pod_container_status_restarts_total{namespace="production"}
```

</details>

### 2. Escribe comandos paso a paso para depurar un Pod en estado CrashLoopBackOff.

<details>
<summary>Ver respuesta</summary>

```bash
# 1. Check Pod status
kubectl get pods -n <namespace> | grep CrashLoopBackOff

# 2. Check Pod detailed info (including events)
kubectl describe pod <pod-name> -n <namespace>

# 3. Check previous container logs (pre-crash logs)
kubectl logs <pod-name> -n <namespace> --previous

# 4. Check current container logs
kubectl logs <pod-name> -n <namespace>

# 5. Override container start command for debugging
kubectl debug <pod-name> -n <namespace> --copy-to=debug-pod \
  --container=<container-name> -- sleep infinity

# 6. Connect to debug Pod
kubectl exec -it debug-pod -n <namespace> -- sh

# 7. Check environment variables
kubectl exec -it debug-pod -n <namespace> -- env

# 8. Check filesystem and configuration
kubectl exec -it debug-pod -n <namespace> -- ls -la /app
kubectl exec -it debug-pod -n <namespace> -- cat /app/config.yaml

# 9. Cleanup after debugging
kubectl delete pod debug-pod -n <namespace>
```

**Causas comunes de CrashLoopBackOff:**
- Archivos de configuración no válidos
- Variables de entorno o secrets faltantes
- Restricciones de recursos (OOM Kill)
- Fallos de health check
- Fallos de conexión a Services dependientes

</details>

### 3. Escribe una consulta CloudWatch Logs Insights para buscar eventos de permiso denegado (403) en los audit logs de EKS durante la última hora.

<details>
<summary>Ver respuesta</summary>

```sql
# CloudWatch Logs Insights Query
# Log group: /aws/eks/<cluster-name>/cluster

# Basic 403 error search
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| filter @message like /"responseStatus":\s*\{\s*"code":\s*403/
| sort @timestamp desc
| limit 100

# Parse detailed information
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"}' as username
| parse @message '"verb":"*"' as verb
| parse @message '"resource":"*"' as resource
| parse @message '"responseStatus":{"code":*}' as statusCode
| filter statusCode = 403
| display @timestamp, username, verb, resource
| sort @timestamp desc
| limit 100

# Aggregate 403 errors by user
fields @timestamp, @message
| filter @logStream like /kube-apiserver-audit/
| parse @message '"user":{"username":"*"}' as username
| parse @message '"responseStatus":{"code":*}' as statusCode
| filter statusCode = 403
| stats count(*) as errorCount by username
| sort errorCount desc
```

**Ejecutar mediante AWS CLI:**
```bash
aws logs start-query \
  --log-group-name "/aws/eks/my-cluster/cluster" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @logStream like /kube-apiserver-audit/ | filter @message like /"code":403/ | sort @timestamp desc | limit 50'
```

</details>

## Preguntas avanzadas

### 1. En una arquitectura de microservices, una API específica está experimentando tiempos de respuesta lentos de forma intermitente. Desarrolla una estrategia integral de debugging usando distributed tracing, métricas y logs.

<details>
<summary>Ver respuesta</summary>

**Estrategia integral de debugging: análisis de latencia intermitente**

**Paso 1: Definir el alcance del problema (métricas)**

```promql
# Check P99 response time
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[5m])) by (le, endpoint)
)

# Check response time distribution (for heatmap)
sum(rate(http_request_duration_seconds_bucket{service="api-gateway"}[1m])) by (le)

# Slow request ratio
sum(rate(http_request_duration_seconds_count{service="api-gateway"}[5m]))
-
sum(rate(http_request_duration_seconds_bucket{service="api-gateway",le="0.5"}[5m]))
```

**Paso 2: Identificar cuellos de botella con distributed tracing**

```yaml
# Jaeger Query Strategy
# 1. Search slow traces (>2s)
service=api-gateway minDuration=2s

# 2. Traces with errors
service=api-gateway tags={"error":"true"}

# 3. Traces for specific endpoint
service=api-gateway operation="GET /api/products"
```

**Paso 3: Análisis de correlación de logs**

```bash
# Search related logs by Trace ID
kubectl logs -l app=api-gateway | grep "trace_id=abc123"

# CloudWatch Logs Insights
fields @timestamp, @message
| filter @message like /trace_id=abc123/
| sort @timestamp asc
```

**Paso 4: Análisis a nivel de infraestructura**

```promql
# Check Pod CPU Throttling
rate(container_cpu_cfs_throttled_seconds_total[5m])

# Network latency
rate(container_network_receive_bytes_total[5m])

# GC impact analysis (Java)
rate(jvm_gc_pause_seconds_sum[5m])
```

**Paso 5: Dashboard integrado**

```yaml
# Grafana Dashboard Configuration
panels:
  - title: "Request Latency (P50, P95, P99)"
    query: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

  - title: "Request Rate by Status"
    query: sum(rate(http_requests_total[5m])) by (status_code)

  - title: "Slow Requests Heatmap"
    query: sum(increase(http_request_duration_seconds_bucket[1m])) by (le)

  - title: "Downstream Service Latency"
    query: histogram_quantile(0.99, sum(rate(downstream_request_duration_seconds_bucket[5m])) by (le, service))

  - title: "Pod Resource Usage"
    queries:
      - container_cpu_usage_seconds_total
      - container_memory_working_set_bytes
```

**Paso 6: Detección automatizada de anomalías**

```yaml
# Prometheus AlertRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: latency-anomaly-detection
spec:
  groups:
  - name: latency.rules
    rules:
    - alert: LatencyAnomaly
      expr: |
        (
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))
          -
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, service))
        )
        /
        histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[1h])) by (le, service))
        > 0.5
      for: 5m
      annotations:
        summary: "Latency increased by 50% compared to 1h average"
```

**Lista de comprobación de análisis:**
- [ ] ¿Ocurre solo en endpoints específicos?
- [ ] ¿Se concentra en horarios específicos?
- [ ] ¿La causa es un downstream service específico?
- [ ] ¿Lo está afectando una limitación de recursos (CPU throttling)?
- [ ] ¿Es un problema relacionado con GC o JVM?
- [ ] ¿Es un problema a nivel de red?

</details>

### 2. Los Nodes de un cluster de EKS pasan a NotReady de forma intermitente. Establece un proceso sistemático de Root Cause Analysis (RCA) y medidas preventivas.

<details>
<summary>Ver respuesta</summary>

**Proceso de Root Cause Analysis (RCA)**

**Fase 1: Recolección de datos**

```bash
# 1. Check node event history
kubectl get events --field-selector involvedObject.kind=Node --sort-by='.lastTimestamp'

# 2. Check detailed node status
kubectl describe node <node-name> | grep -A 20 "Conditions:"

# 3. Check node metrics in CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name StatusCheckFailed \
  --dimensions Name=InstanceId,Value=<instance-id> \
  --start-time $(date -d '24 hours ago' -u +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

**Fase 2: Análisis de logs del sistema**

```bash
# Deploy debugging Pod on node
kubectl debug node/<node-name> -it --image=amazonlinux:2 -- bash

# Access host environment with chroot
chroot /host

# Check system logs
journalctl -u kubelet --since "24 hours ago" | grep -i "error\|fail\|timeout"
dmesg | tail -100

# Check memory/CPU status
free -h
vmstat 1 5
cat /proc/pressure/memory
cat /proc/pressure/cpu
```

**Fase 3: Análisis de red**

```bash
# Check API server connectivity
curl -k https://kubernetes.default.svc.cluster.local/healthz

# Check VPC CNI status
kubectl logs -n kube-system -l k8s-app=aws-node --tail=100

# Check ENI and IP allocation status
aws ec2 describe-network-interfaces \
  --filters Name=attachment.instance-id,Values=<instance-id>
```

**Fase 4: Análisis de presión de recursos**

```promql
# Node memory pressure
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90

# Node disk pressure
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85

# Node PID pressure
node_processes_threads / node_processes_max_threads * 100 > 80
```

**Fase 5: Clasificación de la causa raíz**

| Categoría | Causa posible | Método de verificación |
|---------|------------|----------|
| Recurso | OOM Kill | `dmesg \| grep -i oom` |
| Recurso | Disco lleno | `df -h` |
| Red | Problema de CNI | logs de aws-node |
| Red | Conexión al API server | curl healthz |
| Sistema | Caída de kubelet | `journalctl -u kubelet` |
| Infraestructura | Problema de instancia EC2 | Métricas de CloudWatch |

**Fase 6: Medidas preventivas**

```yaml
# 1. Deploy Node Problem Detector
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-problem-detector
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: node-problem-detector
  template:
    spec:
      containers:
      - name: node-problem-detector
        image: registry.k8s.io/node-problem-detector/node-problem-detector:v0.8.13
        securityContext:
          privileged: true
        volumeMounts:
        - name: log
          mountPath: /var/log
          readOnly: true
        - name: kmsg
          mountPath: /dev/kmsg
          readOnly: true
      volumes:
      - name: log
        hostPath:
          path: /var/log/
      - name: kmsg
        hostPath:
          path: /dev/kmsg
```

```yaml
# 2. Resource-based Alerts
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: node-health-rules
spec:
  groups:
  - name: node.health
    rules:
    - alert: NodeMemoryPressure
      expr: |
        (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.85
      for: 5m
      labels:
        severity: warning

    - alert: NodeDiskPressure
      expr: |
        (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes) > 0.85
      for: 5m
      labels:
        severity: warning

    - alert: NodeNotReady
      expr: |
        kube_node_status_condition{condition="Ready",status="true"} == 0
      for: 2m
      labels:
        severity: critical
```

```bash
# 3. Node auto-recovery setup (Karpenter)
# Karpenter automatically replaces NotReady nodes

# 4. kubelet configuration optimization
# /etc/kubernetes/kubelet/kubelet-config.json
{
  "evictionHard": {
    "memory.available": "500Mi",
    "nodefs.available": "10%",
    "imagefs.available": "15%"
  },
  "evictionSoft": {
    "memory.available": "1Gi",
    "nodefs.available": "15%"
  },
  "evictionSoftGracePeriod": {
    "memory.available": "1m",
    "nodefs.available": "1m"
  }
}
```

**Plantilla de reporte RCA:**
```markdown
## Incident Summary
- Occurrence time: 2024-01-15 14:30 PST
- Impact scope: 3 nodes, 45 Pods affected
- Resolution time: 2024-01-15 15:15 PST (MTTR: 45min)

## Timeline
- 14:30 - Alert triggered: NodeNotReady
- 14:35 - Initial analysis started
- 14:50 - Root cause identified: kubelet OOM due to memory pressure
- 15:00 - Node drain and restart
- 15:15 - Normalization confirmed

## Root Cause
Application with memory leak caused node memory exhaustion

## Preventive Measures
1. [Complete] Set memory limit on problematic application
2. [In Progress] Adjust node memory pressure alert threshold (90% -> 80%)
3. [Planned] Deploy Node Problem Detector
```

</details>
