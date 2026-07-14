# Cuestionario sobre estrategias de escalado

> **Documento relacionado**: [Estrategias de escalado](../../ops/06-scaling-strategies.md)

## Preguntas de opción múltiple

### 1. ¿Qué se requiere para usar métricas personalizadas con HPA?

- A) Kubernetes 1.30 o superior
- B) Prometheus Adapter o un servidor de métricas personalizadas similar
- C) Integración con AWS Auto Scaling
- D) Escalado manual de pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prometheus Adapter o un servidor de métricas personalizadas similar**

**Explicación:**
HPA con métricas personalizadas requiere un servidor de métricas que implemente la API custom.metrics.k8s.io. Prometheus Adapter consulta Prometheus y expone métricas en el formato que HPA espera, lo que permite escalar según métricas específicas de la aplicación, como solicitudes por segundo.

</details>

### 2. ¿Sobre qué tipo de eventos puede escalar KEDA que HPA no puede?

- A) Utilización de CPU
- B) Uso de memoria
- C) Eventos externos como la profundidad de una cola SQS o el retraso de Kafka
- D) Conteos de reinicios de Pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Eventos externos como la profundidad de una cola SQS o el retraso de Kafka**

**Explicación:**
KEDA (Kubernetes Event-Driven Autoscaling) incluye scalers para sistemas externos como AWS SQS, Kafka, RabbitMQ, bases de datos y más. Puede escalar a cero y reaccionar a eventos fuera del sistema de métricas de Kubernetes.

</details>

### 3. ¿Cuál es la diferencia entre los modos de VPA: "Auto" y "Off"?

- A) Auto habilita HPA, Off lo deshabilita
- B) Auto actualiza pods in-place, Off solo proporciona recomendaciones
- C) Auto requiere reinicio, Off es instantáneo
- D) Auto usa instancias Spot, Off usa On-Demand

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Auto actualiza pods in-place, Off solo proporciona recomendaciones**

**Explicación:**
El modo "Auto" de VPA expulsa y recrea automáticamente pods con solicitudes de recursos actualizadas. El modo "Off" solo genera recomendaciones sin realizar cambios, lo que resulta útil para revisar sugerencias antes de implementarlas manualmente.

</details>

### 4. ¿Qué es Pod Deletion Cost y cómo afecta al escalado?

- A) El costo financiero de eliminar un pod
- B) Una annotation que influye en qué pods se eliminan primero durante el scale-down
- C) El tiempo requerido para eliminar un pod
- D) Costos de almacenamiento asociados con la terminación de un pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una annotation que influye en qué pods se eliminan primero durante el scale-down**

**Explicación:**
La annotation `controller.kubernetes.io/pod-deletion-cost` asigna un valor de costo a los pods. Durante el scale-down, los pods con menor costo de eliminación se terminan primero. Esto ayuda a preservar pods que ejecutan cargas de trabajo importantes o que tienen datos en caché.

</details>

### 5. Al usar HPA con métricas personalizadas, ¿cuál es la fórmula para calcular las réplicas deseadas?

- A) currentReplicas + 1
- B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))
- C) maxReplicas / 2
- D) currentMetricValue * targetUtilization

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) desiredReplicas = ceil(currentReplicas * (currentMetricValue / desiredMetricValue))**

**Explicación:**
HPA calcula las réplicas deseadas comparando los valores actuales de las métricas con los valores objetivo y luego escalando proporcionalmente. La función de techo garantiza que se agregue al menos una réplica adicional al escalar hacia arriba.

</details>

### 6. ¿Cuál es la estrategia recomendada para manejar interrupciones de nodos Spot?

- A) Ignorar las interrupciones
- B) Usar Pod Disruption Budgets y terminación graceful con manejadores de interrupción
- C) Ejecutar solo cargas de trabajo stateless
- D) Deshabilitar por completo las instancias Spot

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar Pod Disruption Budgets y terminación graceful con manejadores de interrupción**

**Explicación:**
El manejo de interrupciones Spot combina AWS Node Termination Handler (o el manejo nativo de Karpenter), Pod Disruption Budgets para garantizar la disponibilidad, periodos de gracia de terminación adecuados y un diseño de cargas de trabajo que maneje la preempción de forma graceful.

</details>

### 7. En KEDA, ¿qué configura `pollingInterval`?

- A) Con qué frecuencia se reinician los pods
- B) Con qué frecuencia KEDA comprueba la fuente de métricas externa
- C) El retraso entre operaciones de escalado
- D) Frecuencia de health checks

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Con qué frecuencia KEDA comprueba la fuente de métricas externa**

**Explicación:**
`pollingInterval` define con qué frecuencia KEDA consulta el scaler externo (por ejemplo, SQS, Prometheus) para obtener valores de métricas. Intervalos más bajos proporcionan tiempos de reacción más rápidos, pero aumentan la carga sobre la fuente de métricas.

</details>

### 8. ¿Qué característica de Kubernetes permite a VPA redimensionar pods sin reinicio (en versiones más recientes)?

- A) Rolling updates
- B) In-place Pod Vertical Scaling
- C) Blue/green deployment
- D) Canary releases

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) In-place Pod Vertical Scaling**

**Explicación:**
Kubernetes 1.27+ admite escalado vertical in-place mediante el campo `resizePolicy`, lo que permite cambios de CPU y memoria sin reiniciar el pod. VPA puede aprovechar esto para ajustes de recursos menos disruptivos.

</details>

### 9. ¿Cuál es el beneficio de usar Prometheus Adapter en lugar de metrics-server para HPA?

- A) Menor uso de recursos
- B) Compatibilidad con métricas personalizadas y externas más allá de CPU/memoria
- C) Recolección de métricas más rápida
- D) Alertas integradas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Compatibilidad con métricas personalizadas y externas más allá de CPU/memoria**

**Explicación:**
Metrics-server solo proporciona métricas de CPU y memoria. Prometheus Adapter expone cualquier métrica de Prometheus a través de la API custom.metrics.k8s.io, lo que permite a HPA escalar según métricas de aplicación como solicitudes por segundo, profundidad de cola o latencia.

</details>

### 10. ¿Qué deberías considerar al combinar HPA y VPA?

- A) No se pueden usar juntos
- B) Configurarlos en distintas dimensiones de recursos (HPA en CPU, VPA en memoria)
- C) Deshabilitar siempre HPA cuando VPA esté habilitado
- D) Se coordinan automáticamente sin configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurarlos en distintas dimensiones de recursos (HPA en CPU, VPA en memoria)**

**Explicación:**
HPA y VPA pueden entrar en conflicto si ambos intentan gestionar la misma dimensión de recursos. Un patrón común es usar HPA para escalado horizontal basado en CPU y VPA en modo de recomendación para memoria, o usar el modo "Initial" de VPA, que solo establece recursos al crear el pod.

</details>
