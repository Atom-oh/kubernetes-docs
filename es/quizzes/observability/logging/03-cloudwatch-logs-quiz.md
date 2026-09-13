# Cuestionario de CloudWatch Logs

> **Última actualización**: September 13, 2026

[Guía](../../../observability/logging/03-cloudwatch-logs.md)

---

1. ¿Cuál no es un tipo de log del control plane de EKS?

   - A) api
   - B) audit
   - C) worker
   - D) scheduler

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los cinco tipos son api, audit, authenticator, controllerManager y scheduler. Los logs de worker/aplicación y la entrega de componentes administrados de Auto Mode son rutas independientes.

</details>

---

2. ¿Cómo se deben comparar los factores de costo de CloudWatch Logs?

   - A) La ingesta siempre es el cargo mensual más alto
   - B) El almacenamiento siempre es gratuito
   - C) Todas las rutas de entrega a S3 son gratuitas
   - D) Comparar el volumen real, la retención, los escaneos, la clase, la Region y los cargos posteriores

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Un precio por GB ingerido no se puede clasificar por sí solo frente al almacenamiento en GB-mes o al volumen de escaneo repetido. El ejemplo de $1,575 de la guía es un cálculo hipotético, no los precios actuales de Seúl ni una factura completa.

</details>

---

3. ¿Qué comando de Logs Insights QL extrae campos mediante un glob o una expresión regular?

   - A) extract
   - B) parse
   - C) select
   - D) filter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

parse extrae campos; jsonParse puede analizar un mensaje JSON. La envoltura del collector coloca los campos de la aplicación bajo log_processed. No asumas un orden arbitrario de claves JSON en un glob.

</details>

---

4. ¿Qué grupo usa el collector manual de la aplicación en esta guía?

   - A) /aws/containerinsights/example-eks/application
   - B) /aws/eks/example-eks/logs
   - C) /var/log/containers/example-eks
   - D) Cada clúster usa un único nombre de grupo universal e inmutable

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

El grupo de aplicación configurado es diferente de /aws/eks/example-eks/cluster para los logs del control plane. El grupo se prepara primero; el collector no lo crea ni modifica la retención.

</details>

---

5. ¿Qué afirmación sobre la entrega mediante suscripción es correcta?

   - A) Un ARN de bucket de S3 es un destino directo de filtro de suscripción
   - B) Los lotes de suscripción de CloudWatch funcionan a través del destino OpenSearch de Firehose
   - C) Una suscripción puede enviar a Lambda, Kinesis o Firehose; el archivado en S3 mediante Firehose es un paso posterior independiente
   - D) Las suscripciones garantizan entrega exactamente una vez y rellenan todo el historial

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La API de destino y el formato de entrada son importantes. CloudWatch Logs→Firehose→OpenSearch no es compatible específicamente. Las suscripciones son asíncronas y al menos una vez; las tareas de exportación y la entrega de vended-log son API diferentes.

</details>

---

6. ¿Cuál es el plugin de salida nativo de C de Fluent Bit para CloudWatch Logs?

   - A) cloudwatch
   - B) cloudwatch_logs
   - C) aws_cloudwatch
   - D) cw_logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

cloudwatch_logs es el plugin nativo. cloudwatch nombra el plugin anterior de Go. Las credenciales, el ServiceAccount real, el grupo de salida y la política IAM aún deben coincidir.

</details>

---

7. ¿Qué consulta de QL cuenta eventos por hora y ordena los buckets de tiempo resultantes?

   - A) stats count(*) group by hour
   - B) stats count(*) as log_count by bin(1h) as bucket | sort bucket asc
   - C) select count(*) from logs group by hour
   - D) stats count(*) by bin(1h) | sort @message

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

stats cambia los campos de salida disponibles, así que ordena por el alias de su bucket. La función de percentil de latencia es pct, no percentile, y las expresiones regulares sin distinción entre mayúsculas y minúsculas usan (?i) dentro de las barras.

</details>

---

8. ¿Qué política de logging no es segura como enfoque predeterminado de control de costos?

   - A) Revisar los filtros frente a los registros que se deben conservar
   - B) Establecer la retención a través del único propietario del grupo de logs
   - C) Conservar toda la salida DEBUG indefinidamente y descartar indiscriminadamente los registros relevantes para la seguridad como compensación
   - D) Medir la ingesta y los escaneos antes de cambiar el diseño

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los controles de volumen deben conservar los diagnósticos y registros de seguridad requeridos. LOG_LEVEL en un ConfigMap solo tiene efecto si la aplicación lo consume. Los cambios de retención pueden eliminar datos.

</details>

---

9. ¿Qué hace un filtro de métricas y qué significa un valor predeterminado de cero?

   - A) Exporta todos los registros históricos a S3
   - B) Deriva métricas de los logs nuevos que coinciden; el cero predeterminado se aplica cuando llegan logs pero ningún registro coincide
   - C) Siempre emite cero incluso cuando no llegan logs
   - D) Es compatible con todas las funciones en todas las clases de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Este capítulo usa un filtro JSON de clase Standard en $.log_processed.level. Sin logs entrantes, pueden faltar datos. La alarma comprueba un recuento de errores en dos períodos de cinco minutos, no una tasa de errores ni una prueba de la salud del Service.

</details>

---

10. ¿Qué disposición de IAM/propiedad se ajusta al collector manual solo para logs?

   - A) Otorgar a todos los Pods un rol de administrador
   - B) Adjuntar una política a cloudwatch-agent mientras se implementa un ServiceAccount no relacionado
   - C) Usar solo s3:PutObject
   - D) Crear previamente el grupo, autorizar logs:CreateLogStream/logs:PutLogEvents en su ARN y asignar el ServiceAccount real del collector

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El perfil manual usa logging/fluent-bit-cloudwatch y una relación de confianza IRSA aprobada. No necesita PutMetricData ni logs:* amplios para esta ruta. El chart completo de observabilidad es un perfil independiente cuyos Pods de Fluent Bit usan cloudwatch-agent.

</details>
