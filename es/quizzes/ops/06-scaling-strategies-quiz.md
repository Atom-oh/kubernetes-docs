# Cuestionario sobre estrategias de escalado

> **Documento relacionado**: [Estrategias de escalado](../../ops/06-scaling-strategies.md)

## Preguntas de opción múltiple

### 1. ¿Qué se requiere para usar métricas personalizadas con HPA?

- A) Kubernetes 1.30 o posterior
- B) Prometheus Adapter u otro servidor de métricas personalizadas similar
- C) Integración con AWS Auto Scaling
- D) Escalado manual de pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prometheus Adapter u otro servidor de métricas personalizadas similar**

**Explicación:**
HPA con métricas personalizadas requiere un servidor de métricas que implemente la API `custom.metrics.k8s.io`. Prometheus Adapter consulta Prometheus y expone métricas en el formato que HPA espera, lo que permite escalar según métricas específicas de la aplicación, como solicitudes por segundo.

</details>

### 2. ¿Qué añade KEDA al bucle de control nativo de HPA?

- A) Utilización de CPU
- B) Uso de memoria
- C) Escaladores para fuentes de eventos y gestión de la activación y del escalado a cero
- D) Recuentos de reinicios de pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Escaladores para fuentes de eventos y gestión de la activación y del escalado a cero**

**Explicación:**
KEDA (Kubernetes Event-Driven Autoscaling) incluye escaladores para sistemas externos como AWS SQS, Kafka, RabbitMQ, bases de datos y otros. Proporciona métricas externas a HPA y gestiona la activación y las transiciones a cero para las cargas de trabajo compatibles. HPA también puede consumir métricas externas mediante un adaptador; KEDA no impide que HPA las lea.

</details>

### 3. ¿Cuál es la diferencia entre los modos de VPA «Recreate» y «Off»?

- A) Recreate habilita HPA; Off lo deshabilita
- B) Recreate puede expulsar y volver a crear pods; Off solo proporciona recomendaciones
- C) Recreate garantiza que no habrá interrupciones; Off es instantáneo
- D) Recreate usa instancias Spot; Off usa instancias On-Demand

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Recreate puede expulsar y volver a crear pods; Off solo proporciona recomendaciones**

**Explicación:**
VPA 1.8.0 deja obsoleto Auto, que actualmente se comporta como Recreate. Recreate puede aplicar cambios mediante la expulsión y recreación del pod; Off deja recomendaciones para que se revisen. InPlaceOrRecreate, configurado explícitamente, y el modo InPlace habilitado mediante una feature gate son modos distintos, con comportamientos diferentes al recurrir a una alternativa.

</details>

### 4. ¿Qué es Pod Deletion Cost y cómo afecta al escalado?

- A) El costo económico de eliminar un pod
- B) Una anotación que influye en qué pods se eliminan primero al reducir la escala
- C) El tiempo necesario para eliminar un pod
- D) Los costos de almacenamiento asociados a la terminación de un pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Una anotación que influye en qué pods se eliminan primero al reducir la escala**

**Explicación:**
La anotación `controller.kubernetes.io/pod-deletion-cost` asigna un valor de costo a los pods. Dentro de un ReplicaSet, se prefieren los valores más bajos después de considerar los criterios previos de asignación, fase y disponibilidad. Es un mecanismo de mejor esfuerzo, no una protección contra expulsiones, recuperación de instancias Spot, el comportamiento de Jobs/StatefulSets ni el escalado entre distintos Deployments.

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
HPA calcula las réplicas deseadas comparando los valores actuales de las métricas con los valores objetivo y ajustando la cantidad proporcionalmente. Esta fórmula simplificada presupone métricas utilizables y pods listos. La tolerancia, los datos faltantes, los límites mínimo/máximo y el comportamiento de escalado pueden impedir o limitar un cambio real; aplicar el redondeo superior no garantiza que se añada un pod.

</details>

### 6. ¿Cuál es la estrategia recomendada para gestionar las interrupciones de nodos Spot?

- A) Ignorar las interrupciones
- B) Usar Pod Disruption Budgets y terminación ordenada con gestores de interrupciones
- C) Ejecutar solo cargas de trabajo sin estado
- D) Deshabilitar por completo las instancias Spot

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar Pod Disruption Budgets y terminación ordenada con gestores de interrupciones**

**Explicación:**
Elige el manejo adecuado para el modo de nodo: Auto Mode administrado, Karpenter autogestionado y configurado, o una instalación completa de Node Termination Handler cuando sea necesario. Evita los controladores de drenaje duplicados. Los PDB y los periodos de gracia no impiden la pérdida de una instancia Spot ni garantizan una ventana completa de dos minutos para que la aplicación se cierre.

</details>

### 7. En KEDA, ¿qué configura `pollingInterval`?

- A) Cada cuánto se reinician los pods
- B) Cada cuánto KEDA consulta la fuente de métricas externa
- C) El retraso entre las operaciones de escalado
- D) La frecuencia de las comprobaciones de estado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cada cuánto KEDA consulta la fuente de métricas externa**

**Explicación:**
`pollingInterval` define la frecuencia con que KEDA consulta el escalador externo (por ejemplo, SQS o Prometheus) para obtener valores de métricas. Los intervalos más cortos permiten reaccionar más rápido, pero aumentan la carga en la fuente de métricas.

</details>

### 8. ¿Qué función de Kubernetes permite que VPA redimensione pods sin reiniciarlos en versiones recientes?

- A) Actualizaciones progresivas
- B) Escalado vertical de pods in situ (In-place Pod Vertical Scaling)
- C) Despliegue azul/verde
- D) Versiones canary

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Escalado vertical de pods in situ (In-place Pod Vertical Scaling)**

**Explicación:**
El redimensionamiento de pods in situ pasó de alfa en la versión 1.27 a beta en la 1.33 y a estable en la 1.35. Los modos compatibles de VPA pueden usarlo, pero `resizePolicy` aún puede requerir el reinicio de un contenedor, y las restricciones de capacidad/QoS pueden aplazar o rechazar una actualización.

</details>

### 9. ¿Qué ventaja ofrece Prometheus Adapter frente a metrics-server para HPA?

- A) Menor consumo de recursos
- B) Compatibilidad con métricas personalizadas y externas, además de CPU/memoria
- C) Recopilación de métricas más rápida
- D) Alertas integradas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Compatibilidad con métricas personalizadas y externas, además de CPU/memoria**

**Explicación:**
Metrics-server solo proporciona métricas de CPU y memoria. Prometheus Adapter expone las series configuradas y disponibles a través de la API `custom.metrics.k8s.io`, lo que permite que HPA escale según métricas de la aplicación, como solicitudes por segundo, profundidad de cola o latencia.

</details>

### 10. ¿Qué debes tener en cuenta al combinar HPA y VPA?

- A) No se pueden usar juntos
- B) Configurarlos en dimensiones de recursos distintas (HPA para CPU, VPA para memoria)
- C) Deshabilitar siempre HPA cuando VPA esté habilitado
- D) Se coordinan automáticamente sin configuración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurarlos en dimensiones de recursos distintas (HPA para CPU, VPA para memoria)**

**Explicación:**
HPA y VPA pueden entrar en conflicto si ambos gestionan la misma dimensión de recursos. Algunas opciones son usar VPA solo para recomendaciones, o usar métricas de carga de trabajo como RPS o la longitud de la cola para que HPA escale mientras VPA ajusta los recursos. El modo Initial también cambia las solicitudes de recursos de los pods nuevos, por lo que no elimina las interacciones con el denominador de utilización de CPU. Valida también los efectos sobre los reinicios y la planificación.

</details>

