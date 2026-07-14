# Cuestionario sobre alertas de observabilidad

> **Documento relacionado**: [Alertas de observabilidad](../../ops/07-observability-alerts.md)

## Preguntas de opción múltiple

### 1. ¿Qué expresión PromQL detecta CPU throttling en contenedores?

- A) `container_cpu_usage_seconds_total`
- B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`
- C) `container_memory_usage_bytes`
- D) `kube_pod_status_phase`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`**

**Explicación:**
CPU throttling ocurre cuando un contenedor supera su límite de CPU. La métrica `container_cpu_cfs_throttled_seconds_total` registra el tiempo que se pasa con throttling. Una tasa positiva indica throttling activo que puede afectar el rendimiento de la aplicación.

</details>

### 2. ¿Cuál es el propósito de la configuración `group_by` de Alertmanager?

- A) Eliminar alertas
- B) Agregar alertas con etiquetas coincidentes en notificaciones individuales
- C) Aumentar la severidad de las alertas
- D) Enrutar alertas a logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agregar alertas con etiquetas coincidentes en notificaciones individuales**

**Explicación:**
`group_by` combina múltiples alertas activas que comparten valores de etiquetas especificados en una sola notificación. Esto reduce la fatiga por alertas durante incidentes que activan muchas alertas similares (por ejemplo, todos los Pods de un Deployment fallando).

</details>

### 3. ¿Qué métrica es más importante para detectar la terminación de un Node en EKS Auto Mode?

- A) `node_cpu_seconds_total`
- B) `kube_node_status_condition` con condition="Ready"
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `kube_node_status_condition` con condition="Ready"**

**Explicación:**
Monitorear `kube_node_status_condition` para Ready=false detecta Nodes que dejan de estar disponibles. En Auto Mode, esto indica la terminación o el reemplazo de un Node. Combinado con etiquetas, puedes rastrear el ciclo de vida de los Nodes y los patrones de reemplazo.

</details>

### 4. ¿Qué especifica la duración `for` en una regla de alerting de Prometheus?

- A) Cuánto tiempo conservar las alertas en el historial
- B) Cuánto tiempo debe ser verdadera una condición antes de activarse
- C) El intervalo de evaluación de alertas
- D) El timeout de notificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuánto tiempo debe ser verdadera una condición antes de activarse**

**Explicación:**
La cláusula `for` especifica la duración durante la cual una condición debe ser verdadera continuamente antes de que la alerta pase de "pending" a "firing". Esto evita alertas por picos breves y reduce los falsos positivos.

</details>

### 5. ¿Cómo deben definirse los niveles de severidad de las alertas?

- A) Todas las alertas deben ser críticas
- B) Según el impacto en el negocio y el tiempo de respuesta requerido
- C) Asignados aleatoriamente
- D) Según el nombre de la métrica

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Según el impacto en el negocio y el tiempo de respuesta requerido**

**Explicación:**
La severidad debe reflejar el impacto: crítica para interrupciones de cara al cliente que requieren respuesta inmediata, advertencia para degradación que necesita atención en cuestión de horas e informativa para conocimiento sin acción. Esto permite el enrutamiento y la escalación de guardia adecuados.

</details>

### 6. ¿Qué función PromQL calcula la tasa de aumento a lo largo del tiempo?

- A) `sum()`
- B) `rate()`
- C) `max()`
- D) `count()`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate()`**

**Explicación:**
`rate()` calcula la tasa promedio por segundo de aumento durante un rango de tiempo. Está diseñada para contadores y maneja reinicios de contadores. Por ejemplo, `rate(http_requests_total[5m])` da las solicitudes por segundo promediadas durante 5 minutos.

</details>

### 7. ¿Cuál es el enfoque recomendado para las alertas de pérdida de paquetes?

- A) Alertar ante cualquier pérdida de un solo paquete
- B) Alertar cuando la tasa de pérdida supere un umbral sostenido a lo largo del tiempo
- C) Nunca alertar por pérdidas de paquetes
- D) Solo registrar pérdidas de paquetes en logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Alertar cuando la tasa de pérdida supere un umbral sostenido a lo largo del tiempo**

**Explicación:**
Las pérdidas ocasionales de paquetes son normales en las redes. Las alertas deben activarse ante tasas de pérdida elevadas sostenidas que indiquen problemas reales. Usar `rate()` sobre una ventana (por ejemplo, 5m) con un umbral evita alertas por picos transitorios.

</details>

### 8. En el enrutamiento de Alertmanager, ¿qué hace `continue: true`?

- A) Detiene el procesamiento de rutas adicionales
- B) Permite que la alerta coincida con rutas adicionales después de la actual
- C) Repite la notificación de alerta
- D) Silencia la alerta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permite que la alerta coincida con rutas adicionales después de la actual**

**Explicación:**
De forma predeterminada, Alertmanager se detiene en la primera ruta coincidente. Establecer `continue: true` permite que una alerta coincida con múltiples rutas, lo que habilita escenarios como enviar alertas críticas tanto a PagerDuty como a Slack simultáneamente.

</details>

### 9. ¿Qué métrica indica que se excedió el ancho de banda de red en Nodes de EKS?

- A) `container_cpu_usage_seconds_total`
- B) `node_network_transmit_bytes_total` acercándose a los límites de red de la instancia
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `node_network_transmit_bytes_total` acercándose a los límites de red de la instancia**

**Explicación:**
`node_network_transmit_bytes_total` y `node_network_receive_bytes_total` registran la E/S de red. Comparar la tasa con los límites de ancho de banda de red de la instancia EC2 ayuda a identificar cuándo las cargas de trabajo están alcanzando restricciones de red.

</details>

### 10. ¿Cuál es el propósito de las reglas de inhibición de alertas en Alertmanager?

- A) Aumentar la prioridad de las alertas
- B) Suprimir alertas dependientes cuando se está activando una alerta principal
- C) Enrutar alertas a diferentes receptores
- D) Crear alertas nuevas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Suprimir alertas dependientes cuando se está activando una alerta principal**

**Explicación:**
Las reglas de inhibición evitan tormentas de alertas silenciando alertas descendentes cuando se activa una alerta de causa raíz. Por ejemplo, cuando se activa "NodeDown", inhibe todas las alertas "PodNotReady" para los Pods en ese Node, ya que son síntomas del mismo problema.

</details>
