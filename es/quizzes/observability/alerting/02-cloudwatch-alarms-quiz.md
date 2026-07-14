# Cuestionario de CloudWatch Alarms

Un cuestionario para poner a prueba tu comprensión de CloudWatch Alarms.

---

1. ¿Cuáles son los tres estados de una CloudWatch Alarm?
   - A) Active, Inactive, Pending
   - B) OK, ALARM, INSUFFICIENT_DATA
   - C) Normal, Warning, Critical
   - D) Green, Yellow, Red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) OK, ALARM, INSUFFICIENT_DATA**

**Explicación:**
CloudWatch Alarms tienen tres estados:
- **OK**: La métrica está dentro del rango normal
- **ALARM**: La métrica ha superado el umbral definido
- **INSUFFICIENT_DATA**: No hay datos suficientes para evaluar la alarma

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
- `evaluation-periods`: Número de períodos usados para evaluar la alarma (p. ej., 3)
- `datapoints-to-alarm`: Número de puntos de datos que deben superar el umbral para cambiar al estado ALARM (p. ej., 2)

Por ejemplo, con evaluation-periods=3 y datapoints-to-alarm=2, significa «ALARM si el umbral se supera en 2 o más de los 3 períodos». Esto se denomina alarmas «M de N».

</details>

---

3. ¿Cuál es la expresión correcta para calcular la tasa de errores de ALB en CloudWatch Metric Math?
   - A) `errors + requests`
   - B) `(errors / requests) * 100`
   - C) `errors - requests`
   - D) `RATE(errors)`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `(errors / requests) * 100`**

**Explicación:**
La tasa de errores se calcula dividiendo el número de errores entre el número total de solicitudes y multiplicando por 100 para obtener un porcentaje. CloudWatch Metric Math permite combinar varias métricas para estos cálculos, y el resultado se puede usar como condición de alarma.

```
errors = HTTPCode_Target_5XX_Count
requests = RequestCount
error_rate = (errors / requests) * 100
```

</details>

---

4. ¿Qué afirmación sobre Composite Alarms NO es correcta?
   - A) Pueden combinar varias Metric Alarms para definir condiciones complejas
   - B) Pueden usar los operadores lógicos AND, OR y NOT
   - C) Pueden incluir otras Composite Alarms dentro de una Composite Alarm
   - D) Las Composite Alarms pueden definir sus propias métricas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Las Composite Alarms pueden definir sus propias métricas**

**Explicación:**
Las Composite Alarms no definen sus propias métricas. En su lugar, combinan los estados de Metric Alarms existentes para crear condiciones de alarma complejas. Las reglas de Composite Alarm se componen de funciones como `ALARM(alarm-name)`, `OK(alarm-name)` y los operadores AND, OR y NOT. Las Composite Alarms también se pueden anidar dentro de otras Composite Alarms.

</details>

---

5. ¿Qué afirmación describe correctamente cómo funciona CloudWatch Anomaly Detection?
   - A) Detecta anomalías basándose en umbrales fijos
   - B) Usa machine learning para aprender los rangos esperados de las métricas y alerta cuando se superan
   - C) Detecta anomalías analizando correlaciones con otras métricas
   - D) Alerta cuando los patrones no coinciden con patrones definidos por el usuario

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usa machine learning para aprender los rangos esperados de las métricas y alerta cuando se superan**

**Explicación:**
CloudWatch Anomaly Detection utiliza algoritmos de machine learning para analizar datos históricos de métricas y aprende patrones como las variaciones según la hora del día y el día de la semana. A partir de esto, genera una banda esperada y, cuando los valores reales de las métricas quedan fuera de este rango, se detectan como anomalías. La función `ANOMALY_DETECTION_BAND(metric, stddev)` se puede usar para ajustar el multiplicador de desviación estándar.

</details>

---

6. ¿Qué significa la opción `notBreaching` de `treat-missing-data` en CloudWatch Alarms?
   - A) Activar una alarma cuando faltan datos
   - B) Mantener el estado anterior cuando faltan datos
   - C) Tratar los datos faltantes como si no superaran el umbral
   - D) Cambiar al estado INSUFFICIENT_DATA cuando faltan datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Tratar los datos faltantes como si no superaran el umbral**

**Explicación:**
Los significados de los valores de la opción `treat-missing-data`:
- `notBreaching`: Trata los datos faltantes como si no superaran el umbral (se considera OK)
- `breaching`: Trata los datos faltantes como si superaran el umbral (se considera ALARM)
- `ignore`: Mantiene el estado actual
- `missing`: Cambia al estado INSUFFICIENT_DATA

En general, se recomienda `notBreaching` para evitar alertas innecesarias debido a datos faltantes.

</details>

---

7. ¿Qué acción NO se puede ejecutar directamente como una CloudWatch Alarm Action?
   - A) Detener/iniciar/reiniciar una instancia EC2
   - B) Activar una política de Auto Scaling
   - C) Enviar un mensaje a un tema de SNS
   - D) Reiniciar un pod de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Reiniciar un pod de EKS**

**Explicación:**
CloudWatch Alarm Actions pueden ejecutar directamente las siguientes operaciones nativas de AWS:
- Acciones de EC2: Detener, iniciar, reiniciar, recuperar, terminar
- Acciones de Auto Scaling: Activar políticas de escalado horizontal o reducción
- Acciones de SNS: Enviar mensajes a temas

El reinicio de un pod de EKS no se admite directamente y debe implementarse de forma indirecta mediante la cadena SNS -> Lambda -> Kubernetes API.

</details>

---

8. ¿Cuál es la métrica para supervisar el número de reinicios de pods en un clúster de EKS en Container Insights?
   - A) pod_restart_count
   - B) pod_number_of_container_restarts
   - C) container_restart_total
   - D) kube_pod_container_status_restarts

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) pod_number_of_container_restarts**

**Explicación:**
Métricas clave de EKS en Container Insights:
- `pod_number_of_container_restarts`: Número de reinicios de contenedores dentro de un pod
- `pod_cpu_utilization`: Utilización de CPU del Pod
- `pod_memory_utilization`: Utilización de memoria del Pod
- `node_cpu_utilization`: Utilización de CPU del Node
- `cluster_node_count`: Número de Nodes del clúster

Estas métricas están disponibles en el namespace `ContainerInsights`.

</details>

---

9. ¿Cuál NO es una práctica recomendada para la optimización de costos de CloudWatch Alarms?
   - A) Usar Standard Resolution (60 segundos) para alertas no críticas
   - B) Consolidar varias Metric Alarms en Composite Alarms
   - C) Usar High Resolution (10 segundos) para todas las alertas
   - D) Eliminar regularmente las alarmas no utilizadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Usar High Resolution (10 segundos) para todas las alertas**

**Explicación:**
Las alarmas de High Resolution cuestan 3 veces más que las de Standard Resolution ($0.30 frente a $0.10/alarma/mes). Para la optimización de costos:
- Usar High Resolution solo para alertas Critical
- Usar Standard Resolution para alertas Warning/Info
- Consolidar las alarmas relacionadas en Composite Alarms
- Eliminar regularmente las alarmas no utilizadas
- Usar Anomaly Detection solo cuando sea necesario (costo adicional de $0.30/métrica/mes)

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

Con este patrón, puedes activar funciones Lambda, Step Functions, SSM Automation, etc. cuando el estado de alarma cambia a ALARM para implementar una respuesta automatizada.

</details>

---

## Recursos adicionales de aprendizaje

- [Documentación de Amazon CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [CloudWatch Metrics Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)
- [Métricas de Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
