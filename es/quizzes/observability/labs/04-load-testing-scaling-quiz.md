# Cuestionario del laboratorio de Observability, parte 4: pruebas de carga y autoscaling

> **Última actualización**: February 22, 2026

Comprueba tu comprensión de los conceptos de pruebas de carga y autoscaling tratados en la parte 4 del laboratorio integral de Observability.

---

1. ¿Qué es un Virtual User (VU) en k6 y cómo se configuran los patrones de carga por fases?
   - A) Un VU es una conexión de red; las fases se configuran en archivos JSON
   - B) Un VU representa un usuario simulado que ejecuta el script de prueba de forma concurrente; las fases se configuran mediante stages con VUs objetivo y duración
   - C) Un VU es un hilo de CPU; las fases se establecen únicamente mediante flags de línea de comandos
   - D) Un VU es una cola de solicitudes; las fases requieren scripts de prueba independientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un VU representa un usuario simulado que ejecuta el script de prueba de forma concurrente; las fases se configuran mediante stages con VUs objetivo y duración**

**Explicación:**
En k6, un Virtual User (VU) es un contexto de ejecución independiente que ejecuta tu script de prueba; cada VU simula a un usuario real que realiza solicitudes. Los patrones de carga por fases usan la opción `stages` en el bloque `options`: cada stage define un `target` (número de VUs) y una `duration` (tiempo para alcanzar ese objetivo). Por ejemplo, aumenta gradualmente a 100 VUs durante 2 minutos, mantén esa carga durante 5 minutos y luego redúcela gradualmente. Esto permite perfiles de carga realistas, como aumento gradual, estado estable y pruebas de picos.

</details>

---

2. ¿Cuáles son las diferencias clave entre k6 y Locust para las pruebas de carga?
   - A) k6 está escrito en Python, mientras que Locust está escrito en Go
   - B) k6 usa JavaScript para los scripts de prueba con un runtime de Go para el rendimiento, mientras que Locust usa Python con una arquitectura distribuida
   - C) Locust solo admite HTTP/1.1, mientras que k6 admite todos los protocolos
   - D) k6 requiere una GUI, mientras que Locust solo tiene CLI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) k6 usa JavaScript para los scripts de prueba con un runtime de Go para el rendimiento, mientras que Locust usa Python con una arquitectura distribuida**

**Explicación:**
k6 ofrece alto rendimiento gracias a su runtime basado en Go, mientras usa JavaScript/ES6 familiar para los scripts de prueba, métricas integradas y una excelente integración de CI/CD. Locust usa Python para los scripts de prueba, lo que lo hace accesible para los desarrolladores de Python y muy flexible para lógica de prueba compleja, con una web UI para monitoreo en tiempo real y pruebas distribuidas sencillas. k6 suele gestionar una carga mayor por instancia; Locust ofrece más flexibilidad en la lógica de prueba y una experiencia más visual.

</details>

---

3. ¿Cómo determina el scaler de SQS de KEDA cuándo escalar pods?
   - A) Escala según la utilización de CPU de los pods existentes
   - B) Consulta las métricas de la cola de SQS y escala pods según la proporción entre los mensajes de la cola y un valor objetivo configurado por pod
   - C) Escala según la antigüedad de los mensajes en la cola
   - D) Solo escala durante ventanas de tiempo programadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Consulta las métricas de la cola de SQS y escala pods según la proporción entre los mensajes de la cola y un valor objetivo configurado por pod**

**Explicación:**
El scaler de SQS de KEDA consulta periódicamente SQS para obtener métricas de profundidad de la cola. Calcula las réplicas deseadas como: `queue_length / queueLength_target`. Por ejemplo, con 100 mensajes y `queueLength: 10`, KEDA establece como objetivo 10 pods. También respeta los límites de `minReplicaCount` y `maxReplicaCount`. Cuando la cola está vacía, puede escalar a cero (si se configura así) y escala hacia arriba a medida que llegan mensajes. El scaler usa credenciales de IAM (mediante IRSA) para acceder a las métricas de SQS.

</details>

---

4. ¿Cómo consulta métricas el scaler de Prometheus de KEDA para tomar decisiones de escalado?
   - A) Solo admite las métricas integradas de Prometheus
   - B) Ejecuta una consulta PromQL configurada contra un servidor de Prometheus y escala según el valor devuelto comparado con un umbral
   - C) Requiere un exporter de métricas especial de KEDA en Prometheus
   - D) Solo puede consultar métricas de contador, no gauges

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ejecuta una consulta PromQL configurada contra un servidor de Prometheus y escala según el valor devuelto comparado con un umbral**

**Explicación:**
El scaler de Prometheus de KEDA ejecuta cualquier consulta PromQL válida contra un endpoint de Prometheus configurado. Especificas `serverAddress`, `query` (PromQL) y `threshold`. KEDA escala pods para que `query_result / threshold = replica_count`. Esto permite escalar según métricas de negocio (solicitudes/segundo, profundidad de cola), métricas de aplicaciones personalizadas o cualquier dato consultable. La autenticación admite bearer tokens o TLS para instancias de Prometheus protegidas.

</details>

---

5. ¿Cómo detecta Karpenter los pods pendientes y aprovisiona los nodos adecuados?
   - A) Consulta la API de Kubernetes para pods con PodScheduled=False y compara sus requisitos con plantillas de NodePool
   - B) Requiere que los pods soliciten explícitamente el aprovisionamiento de Karpenter mediante annotations
   - C) Monitorea el uso de CPU del cluster y aprovisiona nodos previamente
   - D) Espera señales de Horizontal Pod Autoscaler antes de aprovisionar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Consulta la API de Kubernetes para pods con PodScheduled=False y compara sus requisitos con plantillas de NodePool**

**Explicación:**
Karpenter observa los pods no programables (aquellos pendientes porque ningún nodo existente puede satisfacer sus requisitos). Cuando los detecta, analiza los requisitos de los pods (solicitudes de recursos, selectores de nodos, tolerations, restricciones de topología) y aprovisiona instancias de EC2 óptimas desde los NodePools configurados. El algoritmo de bin-packing de Karpenter agrupa eficientemente los pods pendientes y selecciona tipos de instancia que minimizan el costo mientras satisfacen los requisitos. Este aprovisionamiento "just-in-time" es más rápido que el enfoque de Cluster Autoscaler basado en grupos de nodos.

</details>

---

6. ¿Qué hace la política de Consolidation de Karpenter para la optimización de costos?
   - A) Solo consolida pods dentro de nodos existentes
   - B) Identifica nodos infrautilizados o vacíos y migra workloads para reducir el número total de nodos, terminando los nodos innecesarios
   - C) Consolida logs de varios nodos
   - D) Solo funciona durante ventanas de mantenimiento programadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Identifica nodos infrautilizados o vacíos y migra workloads para reducir el número total de nodos, terminando los nodos innecesarios**

**Explicación:**
La Consolidation de Karpenter evalúa continuamente la eficiencia del cluster. Identifica oportunidades para reducir costos mediante: terminar inmediatamente nodos vacíos, reemplazar nodos por alternativas más económicas que aún satisfagan los requisitos y consolidar workloads de varios nodos infrautilizados en menos nodos. La Consolidation respeta los pod disruption budgets y usa terminación ordenada. Este ajuste automatizado del tamaño garantiza que solo pagues por la capacidad necesaria y complementa el escalado hacia arriba con un escalado hacia abajo inteligente.

</details>

---

7. ¿Cuáles son las métricas RED clave que se deben observar durante las pruebas de carga en los dashboards de Grafana?
   - A) RAM, Ethernet, Disk
   - B) Rate (solicitudes/segundo), Errors (tasa/recuento de errores), Duration (distribución de latencia)
   - C) Replicas, Events, Deployments
   - D) Reads, Executions, Deletions

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Rate (solicitudes/segundo), Errors (tasa/recuento de errores), Duration (distribución de latencia)**

**Explicación:**
Las métricas RED son una metodología estándar para el monitoreo de servicios: Rate mide el rendimiento (solicitudes por segundo), Errors rastrea la tasa o el recuento de fallos (respuestas 4xx, 5xx) y Duration captura la distribución de latencia (tiempos de respuesta p50, p95, p99). Durante las pruebas de carga, estas métricas revelan cómo se comporta el sistema bajo estrés: ¿el rendimiento alcanza una meseta? ¿los errores se disparan? ¿la latencia se degrada? Los dashboards RED proporcionan visibilidad inmediata de la salud del servicio y ayudan a identificar puntos de ruptura.

</details>

---

8. ¿Cómo puedes rastrear los cambios en el recuento de pods durante eventos de escalado mediante métricas de Prometheus?
   - A) Usando solo la marca de tiempo de `kube_pod_created`
   - B) Usando `kube_deployment_status_replicas` para rastrear el recuento actual de réplicas y comparándolo con `kube_deployment_spec_replicas` para el recuento deseado
   - C) Las métricas de recuento de pods no están disponibles en Prometheus
   - D) Usando `container_cpu_usage` agregado por pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usando `kube_deployment_status_replicas` para rastrear el recuento actual de réplicas y comparándolo con `kube_deployment_spec_replicas` para el recuento deseado**

**Explicación:**
kube-state-metrics expone información sobre las réplicas de Deployment: `kube_deployment_spec_replicas` muestra las réplicas deseadas (a las que se dirigen HPA/KEDA), `kube_deployment_status_replicas` muestra las réplicas listas actuales y `kube_deployment_status_replicas_available` muestra las réplicas disponibles. Graficar estas métricas a lo largo del tiempo revela el comportamiento del escalado: con qué rapidez las réplicas reales coinciden con las deseadas, cualquier oscilación y los tiempos de escalado hacia arriba o hacia abajo. Para métricas específicas de HPA, las métricas `kube_horizontalpodautoscaler_*` proporcionan detalles adicionales.

</details>

---

9. ¿Qué función desempeña la configuración `stabilizationWindowSeconds` en el comportamiento de escalado de KEDA?
   - A) Establece el tiempo mínimo que un pod debe ejecutarse antes de su terminación
   - B) Define una ventana retrospectiva durante el escalado hacia abajo para evitar oscilaciones rápidas al considerar la recomendación más alta durante ese período
   - C) Configura el intervalo entre consultas de métricas
   - D) Establece el tiempo máximo para el inicio del pod

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Define una ventana retrospectiva durante el escalado hacia abajo para evitar oscilaciones rápidas al considerar la recomendación más alta durante ese período**

**Explicación:**
`stabilizationWindowSeconds` evita la inestabilidad durante el escalado hacia abajo. Al escalar hacia abajo, KEDA examina todas las recomendaciones de escalado de los últimos N segundos (la ventana de estabilización) y usa el valor más alto. Esto evita escenarios en los que caídas breves de las métricas activan un escalado hacia abajo, seguido inmediatamente por un escalado hacia arriba cuando regresa la carga. Por ejemplo, una ventana de 300 segundos significa que el escalado hacia abajo solo ocurre si las métricas se han mantenido bajas de forma constante durante 5 minutos. Normalmente, el escalado hacia arriba no se estabiliza para garantizar una respuesta rápida a los aumentos de carga.

</details>

---

10. ¿Cómo se correlaciona la profundidad de la cola de SQS con el escalado de pods en una arquitectura de workload basada en colas?
    - A) La profundidad de la cola y el recuento de pods siempre son inversamente proporcionales
    - B) A medida que aumenta la profundidad de la cola, KEDA escala pods hacia arriba para procesar mensajes más rápido y reducir la profundidad de la cola; a medida que la cola se vacía, los pods escalan hacia abajo
    - C) La profundidad de la cola solo afecta a la asignación de memoria, no al recuento de pods
    - D) El escalado de pods ocurre independientemente de la profundidad de la cola

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) A medida que aumenta la profundidad de la cola, KEDA escala pods hacia arriba para procesar mensajes más rápido y reducir la profundidad de la cola; a medida que la cola se vacía, los pods escalan hacia abajo**

**Explicación:**
En las arquitecturas basadas en colas, hay un ciclo de retroalimentación: los mensajes entrantes aumentan la profundidad de la cola, KEDA lo detecta y escala los pods consumidores hacia arriba, más pods procesan mensajes más rápido (aumentando el rendimiento), la profundidad de la cola disminuye y, finalmente, KEDA escala los pods hacia abajo cuando la cola es manejable. El umbral de `queueLength` determina el objetivo de mensajes por pod. Observar la profundidad de la cola junto con el recuento de pods revela la capacidad de procesamiento: si la profundidad de la cola aumenta a pesar del máximo de pods, has encontrado un cuello de botella que requiere optimización o límites más altos.

</details>
