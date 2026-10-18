# Cuestionario sobre alertas de observabilidad

> **Documento relacionado**: [Alertas de observabilidad](../../ops/07-observability-alerts.md)

## Preguntas de opción múltiple

### 1. ¿Qué expresión PromQL detecta el throttling de CPU en contenedores?

- A) `container_cpu_usage_seconds_total`
- B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`
- C) `container_memory_usage_bytes`
- D) `kube_pod_status_phase`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate(container_cpu_cfs_throttled_seconds_total[5m]) > 0`**

**Explicación:**
El throttling de CPU puede ocurrir cuando se agota la cuota CFS disponible; interprétalo junto con la cuota de la carga de trabajo y el contexto de rendimiento. La métrica `container_cpu_cfs_throttled_seconds_total` registra el tiempo que se pasa bajo throttling. Una tasa positiva indica throttling activo que puede afectar al rendimiento de la aplicación.

</details>

### 2. ¿Cuál es el propósito de la configuración `group_by` de Alertmanager?

- A) Eliminar alertas
- B) Agrupar las alertas con etiquetas coincidentes en una sola notificación
- C) Aumentar la severidad de las alertas
- D) Enrutar alertas a logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrupar las alertas con etiquetas coincidentes en una sola notificación**

**Explicación:**
`group_by` combina varias alertas activas que comparten los valores de las etiquetas especificadas en una sola notificación. Esto reduce la fatiga por alertas durante incidentes que activan muchas alertas similares (por ejemplo, cuando fallan todos los Pods de un Deployment).

</details>

### 3. ¿Qué métrica ayuda a observar la preparación de un Node de Kubernetes?

- A) `node_cpu_seconds_total`
- B) `kube_node_status_condition` con condition="Ready"
- C) `container_memory_usage_bytes`
- D) `node_filesystem_size_bytes`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `kube_node_status_condition` con condition="Ready"**

**Explicación:**
La condición Ready informa sobre la preparación de un Node observado. False o Unknown pueden deberse a varias causas y no demuestran que el Node haya terminado ni que lo hayan reemplazado. Correlaciona el inventario, las condiciones de Node/NodeClaim y los eventos o registros de auditoría reales.

</details>

### 4. ¿Qué especifica la duración `for` en una regla de alertas de Prometheus?

- A) Durante cuánto tiempo se conservan las alertas en el historial
- B) Durante cuánto tiempo debe ser verdadera una condición antes de activar la alerta
- C) El intervalo de evaluación de las alertas
- D) El tiempo de espera de la notificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Durante cuánto tiempo debe ser verdadera una condición antes de activar la alerta**

**Explicación:**
La cláusula `for` especifica cuánto tiempo debe mantenerse continuamente una condición antes de que la alerta pase de "pending" a "firing". Así se evitan alertas por picos breves y se reducen los falsos positivos.

</details>

### 5. ¿Cómo se deben definir los niveles de severidad de las alertas?

- A) Todas las alertas deben ser críticas
- B) Según el impacto en el negocio y el tiempo de respuesta requerido
- C) Asignados al azar
- D) Según el nombre de la métrica

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Según el impacto en el negocio y el tiempo de respuesta requerido**

**Explicación:**
La severidad debe reflejar el impacto: crítica para interrupciones que afectan a los clientes y requieren respuesta inmediata; advertencia para una degradación que necesita atención en cuestión de horas; e informativa para avisos que no requieren acción. Esto permite un enrutamiento y una escalación de guardia adecuados.

</details>

### 6. ¿Qué función de PromQL calcula la tasa de aumento a lo largo del tiempo?

- A) `sum()`
- B) `rate()`
- C) `max()`
- D) `count()`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate()`**

**Explicación:**
`rate()` calcula la tasa media de aumento por segundo durante un intervalo. Está diseñada para contadores y maneja sus reinicios. Por ejemplo, `rate(http_requests_total[5m])` da el promedio de solicitudes por segundo durante cinco minutos.

</details>

### 7. ¿Cuál es el enfoque recomendado para las alertas por pérdida de paquetes?

- A) Alertar ante la pérdida de un solo paquete
- B) Alertar cuando la tasa de pérdida supere un umbral de forma sostenida
- C) No alertar nunca por pérdida de paquetes
- D) Registrar únicamente las pérdidas de paquetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Alertar cuando la tasa de pérdida supere un umbral de forma sostenida**

**Explicación:**
En las redes son normales algunas pérdidas ocasionales de paquetes. Las alertas deben activarse ante tasas de pérdida elevadas y sostenidas que indiquen problemas reales. Usar `rate()` sobre una ventana (por ejemplo, 5m) junto con un umbral evita alertas por picos transitorios.

</details>

### 8. En el enrutamiento de Alertmanager, ¿qué hace `continue: true`?

- A) Detiene el procesamiento de las rutas posteriores
- B) Permite que la alerta también coincida con rutas posteriores a la actual
- C) Repite la notificación de alerta
- D) Silencia la alerta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Permite que la alerta también coincida con rutas posteriores a la actual**

**Explicación:**
`continue: true` permite que la alerta también coincida con rutas hermanas posteriores. Si ya coincidió con una ruta hija, el receptor raíz no funciona automáticamente como alternativa. Prueba el árbol completo, incluidas las alertas críticas que no coincidan con una ruta de equipo.

</details>

### 9. ¿Qué expresión ayuda a medir el caudal de transmisión de la red?

- A) `container_cpu_usage_seconds_total`
- B) `rate(node_network_transmit_bytes_total[5m])` con unidades que correspondan al contrato de capacidad real
- C) `kube_pod_container_status_running`
- D) `container_fs_writes_bytes_total`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate(node_network_transmit_bytes_total[5m])` con unidades que correspondan al contrato de capacidad real**

**Explicación:**
`node_network_transmit_bytes_total` y `node_network_receive_bytes_total` registran la E/S de red. La tasa se expresa en bytes/s; multiplícala por ocho para obtener bits/s y compárala con la línea base, la capacidad de ráfaga y los límites de la ruta que se hayan verificado. El contador acumulativo por sí solo, la velocidad anunciada de una NIC virtual o un límite universal supuesto de 10 Gbps no demuestran saturación.

</details>

### 10. ¿Cuál es el propósito de las reglas de inhibición de alertas en Alertmanager?

- A) Aumentar la prioridad de las alertas
- B) Suprimir las alertas dependientes cuando se activa una alerta principal
- C) Enrutar alertas a distintos receptores
- D) Crear alertas nuevas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Suprimir las alertas dependientes cuando se activa una alerta principal**

**Explicación:**
La inhibición suprime las notificaciones que coinciden según los selectores de origen y destino configurados y las etiquetas que deben ser iguales. No determina automáticamente la causa raíz. Exige identificadores de clúster o entidad no vacíos para que las etiquetas ausentes no supriman alertas que no guardan relación; la evaluación de Prometheus continúa.

</details>
