# Parte 4: Pruebas de carga y escalado

> **Dificultad**: Intermedia
> **Tiempo estimado**: 45 minutos
> **Última actualización**: February 22, 2026

## Objetivos de aprendizaje

- Diseñar y ejecutar escenarios de pruebas de carga con k6 y Locust
- Observar el autoscaling de Pods impulsado por KEDA en tiempo real
- Monitorear el autoscaling de Nodes de Karpenter durante picos de carga
- Crear dashboards de Grafana para visualizar eventos de escalado

## Requisitos previos

- [ ] Completó la [Parte 3: Implementación de MSA](./03-msa-deployment-lab.md)
- [ ] Servicios MSA en ejecución con instrumentación de OTel
- [ ] KEDA y Karpenter configurados
- [ ] k6 instalado localmente (`brew install k6` o `apt install k6`)

---

## Cronología de pruebas de carga y escalado

```mermaid
sequenceDiagram
    participant k6 as k6 Load Test
    participant API as API Gateway
    participant KEDA as KEDA Controller
    participant Karpenter as Karpenter
    participant Grafana as Grafana

    Note over k6,Grafana: Phase 1: Ramp-up (0-5 min)
    k6->>API: 10 → 100 VUs
    API-->>KEDA: Metrics increase
    KEDA->>KEDA: Scale Pods 2 → 8

    Note over k6,Grafana: Phase 2: Sustained Load (5-15 min)
    k6->>API: 100 VUs sustained
    KEDA->>KEDA: Maintain Pod count
    Grafana->>Grafana: Stable metrics

    Note over k6,Grafana: Phase 3: Spike (15-20 min)
    k6->>API: 100 → 500 VUs
    API-->>KEDA: Metrics spike
    KEDA->>KEDA: Scale Pods 8 → 30
    KEDA-->>Karpenter: Node capacity needed
    Karpenter->>Karpenter: Provision new nodes

    Note over k6,Grafana: Phase 4: Cool-down (20-30 min)
    k6->>API: 500 → 0 VUs
    KEDA->>KEDA: Scale Pods 30 → 2
    Karpenter->>Karpenter: Consolidate/terminate nodes
```

---

## Ejercicio 1: Escenario de prueba de carga con k6

### Pasos

**Paso 1.1: Crear script de prueba de carga con k6**

```bash
cat > ~/obs-lab/k6-load-test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const orderLatency = new Trend('order_latency', true);

// Test configuration
export const options = {
  stages: [
    // Phase 1: Ramp-up
    { duration: '2m', target: 50 },   // Warm up
    { duration: '3m', target: 100 },  // Ramp to 100 VUs

    // Phase 2: Sustained load
    { duration: '10m', target: 100 }, // Hold at 100 VUs

    // Phase 3: Spike
    { duration: '2m', target: 300 },  // Spike to 300 VUs
    { duration: '3m', target: 500 },  // Peak at 500 VUs
    { duration: '2m', target: 500 },  // Hold peak

    // Phase 4: Cool-down
    { duration: '3m', target: 100 },  // Ramp down
    { duration: '2m', target: 50 },   // Further down
    { duration: '3m', target: 0 },    // Complete cool-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.1'],
    order_latency: ['p(95)<800'],
  },
};

const BASE_URL = __ENV.API_URL || 'http://api-gateway.msa.svc.cluster.local:8080';

// Test data
const products = ['PROD-001', 'PROD-002', 'PROD-003', 'PROD-004', 'PROD-005'];
const quantities = [1, 2, 3, 5, 10];

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateOrder() {
  return {
    customer_id: `CUST-${Math.floor(Math.random() * 10000)}`,
    product_id: randomItem(products),
    quantity: randomItem(quantities),
    payment_method: Math.random() > 0.5 ? 'credit_card' : 'debit_card',
  };
}

export default function () {
  // Scenario 1: Create Order (60% of traffic)
  if (Math.random() < 0.6) {
    const orderPayload = JSON.stringify(generateOrder());
    const orderStart = Date.now();

    const orderRes = http.post(`${BASE_URL}/api/v1/orders`, orderPayload, {
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      },
      tags: { name: 'CreateOrder' },
    });

    orderLatency.add(Date.now() - orderStart);

    const orderSuccess = check(orderRes, {
      'order created': (r) => r.status === 201,
      'order has id': (r) => r.json('order_id') !== undefined,
    });
    errorRate.add(!orderSuccess);
  }

  // Scenario 2: Get Order Status (30% of traffic)
  else if (Math.random() < 0.9) {
    const orderId = `ORD-${Math.floor(Math.random() * 100000)}`;
    const statusRes = http.get(`${BASE_URL}/api/v1/orders/${orderId}`, {
      tags: { name: 'GetOrderStatus' },
    });

    const statusSuccess = check(statusRes, {
      'status retrieved': (r) => r.status === 200 || r.status === 404,
    });
    errorRate.add(!statusSuccess);
  }

  // Scenario 3: List Orders (10% of traffic)
  else {
    const listRes = http.get(`${BASE_URL}/api/v1/orders?limit=10`, {
      tags: { name: 'ListOrders' },
    });

    const listSuccess = check(listRes, {
      'list retrieved': (r) => r.status === 200,
    });
    errorRate.add(!listSuccess);
  }

  // Think time
  sleep(Math.random() * 2 + 0.5);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    '/tmp/k6-summary.json': JSON.stringify(data),
  };
}
EOF
```

**Paso 1.2: Explicación de las fases de la prueba de carga**

| Fase | Duración | VUs | Propósito |
|-------|----------|-----|---------|
| Aumento gradual | 5 min | 10 → 100 | Calentamiento gradual, activar el escalado inicial |
| Sostenida | 10 min | 100 | Estado estable, observar métricas estables |
| Pico | 7 min | 100 → 500 | Prueba de estrés, activar un escalado agresivo |
| Enfriamiento | 8 min | 500 → 0 | Observación del scale-in, limpieza de recursos |

**Paso 1.3: Obtener la URL de API Gateway**

```bash
kubectl config use-context $(kubectl config get-contexts -o name | grep obs-service)

API_URL=$(kubectl -n msa get svc api-gateway \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "API Gateway URL: http://$API_URL:8080"
```

**Paso 1.4: Ejecutar prueba de carga con k6**

```bash
# Run load test
k6 run --env API_URL=http://$API_URL:8080 ~/obs-lab/k6-load-test.js

# Or run with output to Prometheus
k6 run --env API_URL=http://$API_URL:8080 \
  --out experimental-prometheus-rw \
  ~/obs-lab/k6-load-test.js
```

---

## Ejercicio 2: Alternativa con Locust (basada en Python)

### Pasos

**Paso 2.1: Crear Deployment de Locust**

```bash
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: locust-script
  namespace: msa
data:
  locustfile.py: |
    from locust import HttpUser, task, between
    import random
    import json

    class OrderUser(HttpUser):
        wait_time = between(0.5, 2)

        products = ['PROD-001', 'PROD-002', 'PROD-003', 'PROD-004', 'PROD-005']

        @task(6)
        def create_order(self):
            order = {
                'customer_id': f'CUST-{random.randint(1, 10000)}',
                'product_id': random.choice(self.products),
                'quantity': random.choice([1, 2, 3, 5, 10]),
                'payment_method': random.choice(['credit_card', 'debit_card']),
            }
            with self.client.post(
                '/api/v1/orders',
                json=order,
                headers={'Content-Type': 'application/json'},
                catch_response=True
            ) as response:
                if response.status_code == 201:
                    response.success()
                else:
                    response.failure(f'Status: {response.status_code}')

        @task(3)
        def get_order_status(self):
            order_id = f'ORD-{random.randint(1, 100000)}'
            self.client.get(f'/api/v1/orders/{order_id}')

        @task(1)
        def list_orders(self):
            self.client.get('/api/v1/orders?limit=10')
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-master
  namespace: msa
spec:
  replicas: 1
  selector:
    matchLabels:
      app: locust
      role: master
  template:
    metadata:
      labels:
        app: locust
        role: master
    spec:
      containers:
        - name: locust
          image: locustio/locust:2.22.0
          ports:
            - containerPort: 8089
            - containerPort: 5557
          command:
            - locust
            - --master
            - --host=http://api-gateway:8080
          volumeMounts:
            - name: locust-script
              mountPath: /home/locust
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
      volumes:
        - name: locust-script
          configMap:
            name: locust-script
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: locust-worker
  namespace: msa
spec:
  replicas: 4
  selector:
    matchLabels:
      app: locust
      role: worker
  template:
    metadata:
      labels:
        app: locust
        role: worker
    spec:
      containers:
        - name: locust
          image: locustio/locust:2.22.0
          command:
            - locust
            - --worker
            - --master-host=locust-master
          volumeMounts:
            - name: locust-script
              mountPath: /home/locust
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
      volumes:
        - name: locust-script
          configMap:
            name: locust-script
---
apiVersion: v1
kind: Service
metadata:
  name: locust-master
  namespace: msa
spec:
  selector:
    app: locust
    role: master
  ports:
    - name: web
      port: 8089
      targetPort: 8089
    - name: master
      port: 5557
      targetPort: 5557
  type: LoadBalancer
EOF
```

**Paso 2.2: Acceder a la UI web de Locust**

```bash
LOCUST_URL=$(kubectl -n msa get svc locust-master \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Locust UI: http://$LOCUST_URL:8089"
```

---

## Ejercicio 3: Observar el autoscaling durante la carga

### Pasos

**Paso 3.1: Abrir varias ventanas de terminal para el monitoreo**

```bash
# Terminal 1: Watch Pod scaling
watch -n 2 'kubectl get pods -n msa -l app=order-service -o wide'

# Terminal 2: Watch HPA status
watch -n 5 'kubectl get hpa -n msa'

# Terminal 3: Watch Node scaling (Karpenter)
watch -n 10 'kubectl get nodes -l workload-type=msa'

# Terminal 4: Watch Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -f
```

**Paso 3.2: Puntos de observación durante la prueba de carga**

| Métrica | Dónde observar | Comportamiento esperado |
|--------|-----------------|-------------------|
| Cantidad de Pods | `kubectl get pods -n msa` | 2 → 8 → 30 → 2 |
| Métricas de HPA | `kubectl get hpa -n msa` | Aumento de CPU/tasa de solicitudes |
| Cantidad de Nodes | `kubectl get nodes` | Nuevos Nodes aprovisionados |
| Profundidad de la cola SQS | Consola de AWS / CloudWatch | Pico durante el máximo |
| Métricas de Prometheus | Explorador de Grafana | Tasa de solicitudes, latencia |
| Trazas | Tempo / Grafana | Latencia de extremo a extremo |

**Paso 3.3: Eventos de escalado de KEDA**

```bash
# Watch KEDA events
kubectl get events -n msa --field-selector reason=KEDAScaleTargetActivated -w

# Check ScaledObject status
kubectl describe scaledobject -n msa order-service-scaler
```

**Paso 3.4: Eventos de aprovisionamiento de Karpenter**

```bash
# Watch node provisioning
kubectl get events -A --field-selector reason=Provisioned -w

# Check NodePool status
kubectl describe nodepool msa-workloads
```

---

## Ejercicio 4: Observación del enfriamiento y scale-in

### Pasos

**Paso 4.1: Monitorear el scale-in después de completar la prueba de carga**

```bash
# Watch Pod termination
kubectl get pods -n msa -l app=order-service -w

# Watch node consolidation
kubectl get events -A --field-selector reason=Consolidated -w
```

**Paso 4.2: Cronología de scale-in**

| Tiempo después de la carga | Cantidad de Pods | Cantidad de Nodes | Notas |
|-----------------|-----------|------------|-------|
| 0 min | 30 | 8+ | Estado máximo |
| 2 min | 20 | 8+ | Inicio del cooldown de HPA |
| 5 min | 10 | 6 | Pods terminándose |
| 10 min | 4 | 4 | Karpenter consolidando |
| 15 min | 2 | 3 | Cerca de la línea base |
| 20 min | 2 | 2 | Línea base restaurada |

**Paso 4.3: Verificar la optimización de costos**

```bash
# Check spot instance usage
kubectl get nodes -o custom-columns=NAME:.metadata.name,TYPE:.metadata.labels.karpenter\\.sh/capacity-type,INSTANCE:.metadata.labels.node\\.kubernetes\\.io/instance-type

# Expected: Mix of spot and on-demand instances
```

---

## Ejercicio 5: Dashboard de escalado de Grafana

### Pasos

**Paso 5.1: Crear paneles del dashboard de escalado**

| Panel | Consulta de métrica | Visualización |
|-------|-------------|---------------|
| Cantidad de Pods | `sum(kube_deployment_status_replicas{namespace="msa"}) by (deployment)` | Serie temporal |
| Cantidad de Nodes | `count(kube_node_info{node=~".*msa.*"})` | Estadística |
| Uso de CPU | `sum(rate(container_cpu_usage_seconds_total{namespace="msa"}[5m])) by (pod)` | Serie temporal |
| Uso de memoria | `sum(container_memory_working_set_bytes{namespace="msa"}) by (pod)` | Serie temporal |
| Profundidad de la cola SQS | `aws_sqs_approximate_number_of_messages_visible_average{queue_name="obs-lab-orders"}` | Serie temporal |
| Tasa de solicitudes | `sum(rate(http_server_request_count{namespace="msa"}[1m])) by (service)` | Serie temporal |
| Tasa de errores | `sum(rate(http_server_request_count{namespace="msa",http_status_code=~"5.."}[1m])) / sum(rate(http_server_request_count{namespace="msa"}[1m]))` | Indicador |
| Latencia P99 | `histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{namespace="msa"}[5m])) by (le, service))` | Serie temporal |

**Paso 5.2: Importar JSON del dashboard**

```bash
cat > /tmp/scaling-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "MSA Scaling Dashboard",
    "tags": ["obs-lab", "scaling", "k6"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Pod Replicas by Deployment",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [{
          "expr": "sum(kube_deployment_status_replicas{namespace=\"msa\"}) by (deployment)",
          "legendFormat": "{{deployment}}"
        }]
      },
      {
        "title": "Node Count",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
        "targets": [{
          "expr": "count(kube_node_info)"
        }]
      },
      {
        "title": "Request Rate",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
        "targets": [{
          "expr": "sum(rate(http_server_request_count{namespace=\"msa\"}[1m])) by (service)",
          "legendFormat": "{{service}}"
        }]
      },
      {
        "title": "P99 Latency (ms)",
        "type": "timeseries",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
        "targets": [{
          "expr": "histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{namespace=\"msa\"}[5m])) by (le, service)) * 1000",
          "legendFormat": "{{service}}"
        }]
      }
    ]
  }
}
EOF

# Import via Grafana API
curl -X POST -H "Content-Type: application/json" \
  -u admin:ObsLab2026! \
  -d @/tmp/scaling-dashboard.json \
  "http://$GRAFANA_URL/api/dashboards/db"
```

**Paso 5.3: Crear anotaciones para eventos de escalado**

```bash
# Add Prometheus recording rules for scaling events
cat <<'EOF' | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: scaling-events
  namespace: monitoring
spec:
  groups:
    - name: scaling-events
      rules:
        - record: scaling:pod_scale_up
          expr: |
            changes(kube_deployment_status_replicas{namespace="msa"}[5m]) > 0
            and
            delta(kube_deployment_status_replicas{namespace="msa"}[5m]) > 0

        - record: scaling:pod_scale_down
          expr: |
            changes(kube_deployment_status_replicas{namespace="msa"}[5m]) > 0
            and
            delta(kube_deployment_status_replicas{namespace="msa"}[5m]) < 0

        - record: scaling:node_added
          expr: |
            changes(kube_node_created{node=~".*msa.*"}[10m]) > 0
EOF
```

### Verificación

```bash
# Open Grafana dashboard
echo "Grafana URL: http://$GRAFANA_URL"
echo "Dashboard: MSA Scaling Dashboard"

# Verify metrics are populated
curl -s -u admin:ObsLab2026! \
  "http://$GRAFANA_URL/api/datasources/proxy/1/api/v1/query?query=kube_deployment_status_replicas" | jq
```

---

## Resumen

En este laboratorio, usted ha:

| Tarea | Estado |
|------|--------|
| Script de prueba de carga con k6 | Creado |
| Deployment de Locust | Implementado |
| Autoscaling de Pods (KEDA) | Observado |
| Autoscaling de Nodes (Karpenter) | Observado |
| Comportamiento de scale-in | Verificado |
| Dashboard de escalado | Creado |

### Observaciones clave

| Métrica | Línea base | Pico | Recuperación |
|--------|----------|------|----------|
| Pods de Order Service | 2 | 30 | 2 |
| Total de Nodes | 3 | 8+ | 3 |
| Tasa de solicitudes | 0 | 500+ RPS | 0 |
| Latencia P99 | <100ms | <500ms | <100ms |
| Tasa de errores | 0% | <1% | 0% |

## Limpieza

La limpieza se realizará en la [Parte 6](./06-distributed-tracing-lab.md#cleanup).

## Solución de problemas

<details>
<summary>k6 no puede alcanzar API Gateway</summary>

- Verifique que LoadBalancer tenga una IP externa: `kubectl get svc -n msa api-gateway`
- Compruebe que los security groups permitan tráfico entrante
- Pruebe la conectividad: `curl http://$API_URL:8080/health`
</details>

<details>
<summary>Los Pods no escalan</summary>

- Compruebe el estado de HPA: `kubectl describe hpa -n msa`
- Verifique KEDA ScaledObject: `kubectl describe scaledobject -n msa`
- Compruebe la disponibilidad de métricas: `kubectl top pods -n msa`
</details>

<details>
<summary>Los Nodes no se aprovisionan</summary>

- Compruebe los logs de Karpenter: `kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter`
- Verifique los límites de NodePool: `kubectl describe nodepool msa-workloads`
- Compruebe los límites de instancias EC2 en la cuenta de AWS
</details>

## Próximos pasos

Continúe con la [Parte 5: Alertas y AIOps](./05-alerting-aiops-lab.md) para configurar alertas y la respuesta a incidentes impulsada por IA.

## Referencias

- [Documentación de k6](https://k6.io/docs/)
- [Documentación de Locust](https://docs.locust.io/)
- [Documentación de KEDA](../../autoscaling/01-keda.md)
- [Documentación de Karpenter](../../autoscaling/02-karpenter.md)
