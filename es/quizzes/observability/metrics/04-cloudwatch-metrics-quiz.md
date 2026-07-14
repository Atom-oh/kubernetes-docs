# Cuestionario de métricas de CloudWatch

Un cuestionario para evaluar tu comprensión de las métricas de CloudWatch.

---

1. ¿Cuál es la función principal de Amazon CloudWatch Container Insights?
   - A) Creación de imágenes de contenedor
   - B) Monitoreo a nivel de contenedor/Pod para clústeres de EKS
   - C) Orquestación de contenedores
   - D) Administración de pipelines de CI/CD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Monitoreo a nivel de contenedor/Pod para clústeres de EKS**

**Explicación:**
Container Insights es una característica de CloudWatch para monitorear cargas de trabajo en contenedores en entornos de EKS, ECS y Kubernetes. Recopila y visualiza automáticamente métricas de CPU, memoria, red y sistema de archivos a nivel de clúster, nodo, Pod y contenedor.

</details>

---

2. ¿Cuál es el método recomendado para implementar CloudWatch Agent en EKS?
   - A) Implementar como un único Pod
   - B) Implementar en todos los nodos como un DaemonSet
   - C) Implementar 3 réplicas con Deployment
   - D) Implementar como un StatefulSet

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Implementar en todos los nodos como un DaemonSet**

**Explicación:**
CloudWatch Agent se implementa como un DaemonSet para recopilar métricas y logs de cada nodo. Esto garantiza una recopilación coherente de métricas del sistema, métricas de contenedores y logs de todos los nodos.

</details>

---

3. ¿Cuál es el propósito de la función `SEARCH()` en CloudWatch Metric Math?
   - A) Búsqueda de logs
   - B) Buscar dinámicamente métricas que coincidan con un patrón
   - C) Búsqueda de alertas
   - D) Búsqueda de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Buscar dinámicamente métricas que coincidan con un patrón**

**Explicación:**
La función `SEARCH()` busca dinámicamente métricas mediante patrones de namespace, dimensión y nombre de métrica. Por ejemplo, `SEARCH('{AWS/EC2,InstanceId} MetricName="CPUUtilization"', 'Average')` busca la utilización de CPU de todas las instancias de EC2.

</details>

---

4. ¿Cómo funciona CloudWatch Anomaly Detection?
   - A) Detección basada en umbrales establecidos manualmente
   - B) Detección automática de patrones anómalos basada en ML
   - C) Análisis de patrones de logs
   - D) Análisis de tráfico de red

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Detección automática de patrones anómalos basada en ML**

**Explicación:**
CloudWatch Anomaly Detection utiliza machine learning para aprender los patrones normales de las métricas y detectar automáticamente valores anormales. Genera rangos esperados dinámicos (bandas) teniendo en cuenta la estacionalidad, las tendencias y los patrones por día de la semana, e identifica anomalías cuando los valores quedan fuera de estos rangos.

</details>

---

5. Al usar AWS Distro for OpenTelemetry (ADOT) para enviar métricas de Prometheus a CloudWatch, ¿qué exporter se utiliza?
   - A) prometheus-exporter
   - B) awsemf (AWS EMF Exporter)
   - C) cloudwatch-exporter
   - D) metric-exporter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) awsemf (AWS EMF Exporter)**

**Explicación:**
Para enviar métricas de Prometheus a CloudWatch en ADOT, utiliza AWS EMF (Embedded Metric Format) Exporter. Este exporter convierte las métricas al formato EMF en CloudWatch Logs y las envía; CloudWatch luego las extrae como métricas.

</details>

---

6. ¿Cuál NO es un método válido para la optimización de costos de CloudWatch?
   - A) Establecer períodos de retención de logs
   - B) Eliminar métricas de alta resolución innecesarias
   - C) Recopilar todas las métricas en intervalos de 1 segundo
   - D) Usar la clase de logs Infrequent Access

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilar todas las métricas en intervalos de 1 segundo**

**Explicación:**
Las métricas de alta resolución (intervalos de 1 segundo) son costosas. Para optimizar costos, recopila solo las métricas necesarias con alta resolución y la mayoría de las métricas en intervalos de 60 segundos (predeterminado). Establecer períodos de retención de logs, filtrar métricas innecesarias y utilizar la clase de logs Infrequent Access también ayuda a reducir costos.

</details>

---

7. ¿Qué API se utiliza para crear métricas personalizadas en CloudWatch?
   - A) CreateMetric
   - B) PutMetricData
   - C) PublishMetric
   - D) SendMetric

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) PutMetricData**

**Explicación:**
La API `PutMetricData` se utiliza para enviar métricas personalizadas a CloudWatch. Puedes especificar namespace, nombre de métrica, dimensiones, valor, unidad, timestamp, etc. Se puede llamar mediante AWS SDK o CLI.

</details>

---

8. ¿Cuál es la función de Dimensions en CloudWatch?
   - A) Especificar unidades de métrica
   - B) Pares clave-valor que segmentan las métricas
   - C) Especificar la gravedad de la alerta
   - D) Especificar grupos de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Pares clave-valor que segmentan las métricas**

**Explicación:**
Las dimensiones son pares clave-valor que segmentan e identifican métricas. Por ejemplo, en las métricas de instancias EC2, la dimensión `InstanceId` identifica instancias específicas. Se pueden especificar hasta 30 dimensiones para una sola métrica.

</details>

---

9. ¿En qué se diferencia Enhanced Container Insights de Container Insights básico?
   - A) Se proporciona de forma gratuita
   - B) Proporciona métricas adicionales y un monitoreo más detallado
   - C) Elimina la funcionalidad de recopilación de logs
   - D) Proporciona únicamente funcionalidad de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Proporciona métricas adicionales y un monitoreo más detallado**

**Explicación:**
Enhanced Container Insights recopila más métricas que Container Insights básico. Proporciona información adicional, como capacidad reservada de CPU/memoria, métricas de GPU (cuando corresponde) y métricas del plano de control de Kubernetes. Tiene un costo mayor, pero permite un monitoreo más detallado.

</details>

---

10. ¿Cuál es la función de `ANOMALY_DETECTION_BAND()` en las alertas de CloudWatch?
    - A) Establecer umbrales fijos
    - B) Devolver el rango esperado del modelo de detección de anomalías
    - C) Filtrado de logs
    - D) Creación de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Devolver el rango esperado del modelo de detección de anomalías**

**Explicación:**
La función `ANOMALY_DETECTION_BAND()` devuelve el rango de valores esperados (límites superior/inferior) aprendido por el modelo de detección de anomalías. Este rango se puede utilizar en alertas para activar notificaciones cuando las métricas quedan fuera del rango esperado. El segundo argumento especifica el multiplicador de desviación estándar para ajustar el ancho de la banda.

</details>
