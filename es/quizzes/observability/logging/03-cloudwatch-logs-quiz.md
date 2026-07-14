# Cuestionario de CloudWatch Logs

Pon a prueba tus conocimientos sobre Amazon CloudWatch Logs.

---

1. ¿Cuál NO es un tipo de log compatible con el logging del control plane de EKS?

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) worker**

**Explicación:**
El control plane de EKS admite 5 tipos de log: api, audit, authenticator, controllerManager y scheduler. Los logs de los nodos worker no son logs del control plane y deben recopilarse por separado mediante Container Insights o FluentBit.

</details>

---

2. ¿Cuál es el elemento más costoso en la estructura de precios de CloudWatch Logs?

   - A) Almacenamiento
   - B) Ingestión
   - C) Consulta (Logs Insights)
   - D) Exportación a S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ingestión**

**Explicación:**
La ingesta de CloudWatch Logs cuesta $0.50/GB, lo cual es mucho más alto que el almacenamiento ($0.03/GB/mes) o las consultas ($0.005/GB analizado). Por lo tanto, filtrar logs innecesarios es importante para la optimización de costos.

</details>

---

3. ¿Qué comando de CloudWatch Logs Insights extrae campos específicos?

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) parse**

**Explicación:**
En CloudWatch Logs Insights, el comando `parse` extrae campos que coinciden con patrones específicos de los mensajes de log. Ejemplo: `parse @message '"level":"*"' as level`

</details>

---

4. ¿Cuál es el formato de la ruta del grupo de logs para los logs recopilados mediante Container Insights?

   - A) `/aws/eks/cluster-name/logs`
   - B) `/aws/containerinsights/cluster-name/application`
   - C) `/var/log/containers/cluster-name`
   - D) `/kubernetes/cluster-name/logs`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `/aws/containerinsights/cluster-name/application`**

**Explicación:**
Container Insights crea grupos de logs en la ruta `/aws/containerinsights/{cluster-name}/`, incluidos los grupos de logs de aplicación, host, dataplane y rendimiento.

</details>

---

5. ¿Qué característica de CloudWatch Logs entrega logs a funciones Lambda para el procesamiento de logs en tiempo real?

   - A) Log Stream
   - B) Metric Filter
   - C) Subscription Filter
   - D) Log Insight

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Subscription Filter**

**Explicación:**
Los Subscription Filters entregan logs de grupos de logs en tiempo real a otros servicios (Lambda, Kinesis Data Firehose, Kinesis Data Streams). Puedes especificar patrones de filtro para entregar solo logs específicos.

</details>

---

6. ¿Cuál es el nombre del plugin OUTPUT de FluentBit para enviar logs a CloudWatch Logs?

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) cloudwatch_logs**

**Explicación:**
El plugin de salida de CloudWatch Logs de FluentBit se llama `cloudwatch_logs`. Está incluido de forma predeterminada en la imagen `aws-for-fluent-bit` proporcionada por AWS.

</details>

---

7. ¿Cuál es la consulta correcta de CloudWatch Logs Insights para agregar recuentos de logs por período de tiempo?

   - A) `stats count(*) group by hour`
   - B) `stats count(*) as log_count by bin(1h)`
   - C) `select count(*) from logs group by hour`
   - D) `aggregate count by time(1h)`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `stats count(*) as log_count by bin(1h)`**

**Explicación:**
En CloudWatch Logs Insights, la agregación basada en tiempo utiliza el comando `stats` y la función `bin()`. `bin(1h)` agrupa los datos en intervalos de 1 hora.

</details>

---

8. ¿Cuál NO es una estrategia recomendada para la optimización de costos de CloudWatch Logs?

   - A) Filtrar logs innecesarios (healthcheck, etc.)
   - B) Establecer distintos períodos de retención por entorno
   - C) Recopilar todos los logs en el nivel DEBUG
   - D) Archivar logs de retención prolongada en S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recopilar todos los logs en el nivel DEBUG**

**Explicación:**
Los logs de nivel DEBUG son muy detallados y aumentan significativamente el volumen de logs. En entornos de producción, recopilar solo el nivel INFO y superiores ayuda con la optimización de costos.

</details>

---

9. ¿Cuál es el propósito principal de usar Metric Filters en CloudWatch Logs?

   - A) Exportar logs a S3
   - B) Crear métricas de CloudWatch a partir de patrones de log
   - C) Establecer períodos de retención de logs
   - D) Configurar el cifrado de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Crear métricas de CloudWatch a partir de patrones de log**

**Explicación:**
Los Metric Filters detectan patrones específicos (por ejemplo, ERROR) en los logs y crean métricas de CloudWatch. Basándote en estas métricas, puedes configurar CloudWatch Alarms para recibir notificaciones.

</details>

---

10. ¿Qué permiso NO se requiere para IRSA (IAM Roles for Service Accounts) al configurar Container Insights en un clúster de EKS?

    - A) logs:CreateLogGroup
    - B) logs:PutLogEvents
    - C) s3:PutObject
    - D) cloudwatch:PutMetricData

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) s3:PutObject**

**Explicación:**
La configuración básica de Container Insights no requiere permisos de S3. Solo se necesitan permisos de CloudWatch Logs (logs:*) y CloudWatch Metrics (cloudwatch:PutMetricData). Los permisos de S3 solo son necesarios al configurar exportaciones de logs independientes a S3.

</details>
