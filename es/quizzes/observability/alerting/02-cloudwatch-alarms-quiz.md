# Cuestionario de CloudWatch Alarms

Un cuestionario sobre las alarmas de métricas clásicas y las alarmas compuestas de CloudWatch, revisado con la documentación oficial el 2026-09-13.

---

1. ¿Cuáles son los tres estados de una alarma de métrica clásica de CloudWatch?
   - A) Active, Inactive, Pending
   - B) OK, ALARM, INSUFFICIENT_DATA
   - C) Normal, Warning, Critical
   - D) Green, Yellow, Red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) OK, ALARM, INSUFFICIENT_DATA**

**Explicación:**
CloudWatch Alarms tiene tres estados:
- **OK**: La métrica está dentro del rango normal
- **ALARM**: La métrica ha incumplido el umbral definido
- **INSUFFICIENT_DATA**: No hay suficientes datos para evaluar la alarma

Estos estados cambian automáticamente según los valores de las métricas y la configuración de la alarma.

</details>

---

2. ¿Cuál es la diferencia entre las configuraciones `evaluation-periods` y `datapoints-to-alarm` en CloudWatch Alarms?
   - A) Ambas configuraciones realizan la misma función
   - B) evaluation-periods es el número de períodos de evaluación, datapoints-to-alarm es el número de puntos de datos necesarios para activar el estado ALARM
   - C) evaluation-periods está en segundos, datapoints-to-alarm está en minutos
   - D) evaluation-periods es el intervalo de recopilación de métricas, datapoints-to-alarm es el intervalo de notificación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) evaluation-periods es el número de períodos de evaluación, datapoints-to-alarm es el número de puntos de datos necesarios para activar el estado ALARM**

**Explicación:**
- `evaluation-periods`: Número de períodos utilizados para evaluar la alarma (p. ej., 3)
- `datapoints-to-alarm`: Número de puntos de datos que deben incumplir el umbral para cambiar al estado ALARM (p. ej., 2)

Por ejemplo, con evaluation-periods=3 y datapoints-to-alarm=2, significa "ALARM si se incumple el umbral en 2 o más de los 3 períodos". Esto se denomina alarmas "M de N".

</details>

---

3. ¿Cuál es la proporción básica para la tasa de errores de destino de ALB cuando las solicitudes son positivas en CloudWatch Metric Math?
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `(errors / requests) * 100`**

**Explicación:**
La tasa de errores se calcula dividiendo el número de errores entre el número total de solicitudes y multiplicando por 100 para obtener un porcentaje. El denominador cuenta las solicitudes reenviadas a los destinos, no cada error generado por ALB. Defina por separado el manejo de solicitudes cero, 5xx ausentes y recopilación ausente.

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. ¿Qué afirmación sobre Composite Alarms NO es correcta?
   - A) Puede combinar varias Metric Alarms para definir condiciones complejas
   - B) Puede usar los operadores lógicos AND, OR, NOT
   - C) Puede incluir otras Composite Alarms dentro de una Composite Alarm
   - D) Las Composite Alarms pueden definir sus propias métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Las Composite Alarms pueden definir sus propias métricas**

**Explicación:**
Las Composite Alarms no definen sus propias métricas. En su lugar, combinan los estados de Metric Alarms existentes para crear condiciones de alarma complejas. Las reglas de Composite Alarm se componen de funciones como `ALARM(alarm-name)`, `OK(alarm-name)` y los operadores AND, OR, NOT. Las Composite Alarms también se pueden anidar dentro de otras Composite Alarms.

</details>

---

5. ¿Qué afirmación describe correctamente cómo funciona CloudWatch Anomaly Detection?
   - A) Detecta anomalías según umbrales fijos
   - B) Usa machine learning para aprender los rangos esperados de las métricas y alerta cuando se superan
   - C) Detecta anomalías mediante el análisis de correlaciones con otras métricas
   - D) Alerta cuando los patrones no coinciden con los patrones definidos por el usuario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa machine learning para aprender los rangos esperados de las métricas y alerta cuando se superan**

**Explicación:**
CloudWatch Anomaly Detection utiliza algoritmos de machine learning para analizar datos históricos de métricas y aprende patrones como las variaciones según la hora del día y el día de la semana. A partir de ello, genera una banda esperada y, cuando los valores reales de las métricas quedan fuera de este rango, se detectan como anomalías. El parámetro `ANOMALY_DETECTION_BAND(metric, stddev)` controla el ancho de la banda; no garantiza un intervalo de confianza fijo del 95 % o del 99,7 %.

</details>

---

6. ¿Qué significa la opción `notBreaching` de `treat-missing-data` en CloudWatch Alarms?
   - A) Activar una alarma cuando faltan datos
   - B) Mantener el estado anterior cuando faltan datos
   - C) Tratar los datos ausentes como si no incumplieran el umbral
   - D) Cambiar al estado INSUFFICIENT_DATA cuando faltan datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Tratar los datos ausentes como si no incumplieran el umbral**

**Explicación:**
Los significados de los valores de la opción `treat-missing-data`:
- `notBreaching`: Tratar los datos ausentes como si no incumplieran el umbral (considerarlos como OK)
- `breaching`: Tratar los datos ausentes como si incumplieran el umbral (considerarlos como ALARM)
- `ignore`: Mantener el estado actual
- `missing`: INSUFFICIENT_DATA cuando faltan todos los datos de evaluación

Elija según la semántica de la métrica. `notBreaching` puede ser adecuado para conteos de errores poco frecuentes, pero puede ocultar un heartbeat ausente. Use `missing` para alarmas con acciones de mutación de EC2 y actívelas solo en ALARM. Los suficientes puntos reales adicionales tienen prioridad sobre el relleno de datos ausentes.

</details>

---

7. ¿Qué acción NO se puede ejecutar directamente como una CloudWatch Alarm Action?
   - A) Detener, terminar, reiniciar o recuperar una instancia EC2
   - B) Activar una política de Auto Scaling
   - C) Enviar un mensaje a un tema SNS
   - D) Reiniciar un Pod de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Reiniciar un Pod de EKS**

**Explicación:**
CloudWatch Alarm Actions puede ejecutar directamente las siguientes operaciones nativas de AWS:
- EC2 Actions: Detener, reiniciar, recuperar, terminar (iniciar no es una acción directa)
- Auto Scaling Actions: Activar políticas de aumento o reducción del número de instancias (scale-out/scale-in)
- SNS Actions: Enviar mensajes a temas

El reinicio de un Pod de EKS no es compatible directamente y requiere una ruta de Lambda/workflow y Kubernetes API autorizada por separado.

</details>

---

8. ¿Cuál es la métrica para supervisar el número de reinicios de Pod en un clúster de EKS en Container Insights?
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) pod_number_of_container_restarts**

**Explicación:**
Métricas clave de EKS en Container Insights:
- `pod_number_of_container_restarts`: Número acumulado de reinicios de contenedores para un Pod; requiere ClusterName, Namespace y PodName
- `pod_cpu_utilization`: Utilización de CPU del Pod
- `pod_memory_utilization`: Utilización de memoria del Pod
- `node_cpu_utilization`: Utilización de CPU del Node
- `cluster_node_count`: Número de Nodes del clúster

Estas métricas están disponibles en el namespace `ContainerInsights`.

</details>

---

9. ¿Cuál NO es una práctica recomendada para la optimización de costos de CloudWatch Alarms?
   - A) Usar Standard Resolution (60 segundos) para alertas no críticas
   - B) Tener en cuenta las métricas evaluadas y los cargos por alarmas secundarias conservadas
   - C) Usar High Resolution (10 segundos) para todas las alertas
   - D) Eliminar regularmente las alarmas no utilizadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar High Resolution (10 segundos) para todas las alertas**

**Explicación:**
Elija alta resolución solo cuando los requisitos de latencia y la resolución recopilada lo justifiquen. 60 segundos es la resolución estándar. Una alarma compuesta conserva sus alarmas secundarias y añade cargos; reducir el ruido de las notificaciones no disminuye automáticamente el costo. Una alarma de anomalías incluye la métrica evaluada y las métricas de las bandas superior e inferior. Consulte los precios actuales para la Region correspondiente.

</details>

---

10. Al integrar EventBridge con CloudWatch Alarms para una respuesta automatizada, ¿cuál es el `detail-type` para detectar cambios de estado de alarma?
    - A) "AWS CloudWatch Alarm"
    - B) "CloudWatch Alarm State Change"
    - C) "CloudWatch Metric Alarm"
    - D) "AWS Alarm Notification"

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) "CloudWatch Alarm State Change"**

**Explicación:**
Patrón de eventos para detectar cambios de estado de CloudWatch Alarm en EventBridge:
```json
{
  "source": ["aws.cloudwatch"],
  "detail-type": ["CloudWatch Alarm State Change"],
  "detail": {
    "state": {
      "value": ["ALARM"]
    }
  }
}
```

Con este patrón, puede activar funciones Lambda, Step Functions, SSM Automation, etc. cuando el estado de la alarma cambia a ALARM para implementar una respuesta automatizada.

</details>

---

## Recursos de aprendizaje adicionales

- [Documentación de Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Métricas de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
