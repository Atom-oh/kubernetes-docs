# Cuestionario sobre las métricas de CloudWatch

Revisado con la guía del 13 de septiembre de 2026.

1. ¿Qué responsabilidad del equipo elimina un backend administrado de CloudWatch?

   - A) Toda tarea de recopilación y de IAM
   - B) Solo la operación del backend de AWS; el equipo sigue teniendo que hacerse cargo de los recopiladores, la identidad, la retención y la respuesta
   - C) Todos los requisitos de red
   - D) Todos los cargos por consultas y registros

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La recopilación tradicional, mejorada y de OTel tiene distintos modelos de nombres y facturación. El almacenamiento administrado no elimina el trabajo operativo.

</details>

2. ¿Qué afirmación sobre la instalación en EKS es correcta?

   - A) update-cluster-logging instala Container Insights
   - B) Todas las plataformas ejecutan el mismo DaemonSet en los hosts
   - C) Elige un complemento compatible o una instalación propia con Helm y verifica los requisitos previos de plataforma e identidad
   - D) Helm 6.6.0 necesariamente es la versión del complemento de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El registro del plano de control es independiente. Fargate no ejecuta el DaemonSet de host que se muestra; en Auto Mode y en entornos con cómputo mixto hay que verificar la compatibilidad. Pod Identity o IRSA también requieren una configuración real.

</details>

3. ¿Qué genera una vista de los diez primeros elementos a partir de SEARCH?

   - A) SEARCH por sí sola siempre limita los resultados a diez
   - B) SLICE(SORT(SEARCH(...), AVG, DESC), 0, 10)
   - C) PERCENTILE(SEARCH(...), 10)
   - D) Una alarma normal sobre el arreglo de SEARCH

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

SEARCH devuelve las series que coinciden. Ordénalas y recórtalas de forma explícita; la clasificación usa el intervalo evaluado. No se puede crear una alarma directamente sobre SEARCH.

</details>

4. ¿Qué afirmación sobre percentiles y proporciones es correcta?

   - A) PERCENTILE(METRICS(),95) da el p95 global de solicitudes
   - B) Todo período sin tráfico representa un resultado saludable con cero errores
   - C) AVG(METRICS()) PERIOD(300) es un promedio móvil
   - D) Usa un estadístico p95 compatible; controla la proporción para evitar divisiones entre cero cuando no haya tráfico e inspecciona la telemetría faltante

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

La guía usa Sum para los conteos de ALB y IF(m2>0,100*m1/m2). La aritmética de CloudWatch trata los valores faltantes como cero y descarta los resultados de divisiones entre cero; los valores p95 de los servicios no permiten reconstruir un p95 global.

</details>

5. ¿Qué debe incluir una declaración de métricas ADOT/EMF en la telemetría real?

   - A) Las etiquetas y los valores de las dimensiones, proporcionados mediante el descubrimiento, el reetiquetado o la aplicación
   - B) Solo los nombres de las dimensiones en la configuración del exportador
   - C) Una clave de acceso secreta en cada etiqueta
   - D) Una réplica en cada nodo que extraiga métricas de todos los pods

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

awsemf envía eventos de registro de los que se extraen métricas tradicionales. El ejemplo crea las dimensiones ClusterName/Namespace/Service y usa un gauge. Las rutas modernas de OTLP directo son otra opción.

</details>

6. ¿Qué acción para reducir costos es incompatible o insegura según esta guía?

   - A) Medir el uso de ingesta y consultas
   - B) Establecer la retención aprobada en un grupo de registros administrado por el equipo
   - C) Mover los registros de EMF/Container Insights a Infrequent Access y acortar la retención de todos los grupos de registros cuya retención no está limitada
   - D) Revisar las extracciones duplicadas y las etiquetas innecesarias

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Infrequent Access no admite la ingesta de registros de EMF ni de Container Insights. Reducir la retención puede hacer que caduque el historial existente. La alta resolución puede aumentar los costos de solicitudes y alarmas; eso no implica que el almacenamiento de métricas siempre cueste diez veces más.

</details>

7. ¿Qué es cierto sobre las funciones auxiliares de PutMetricData?

   - A) Aprovisionan IAM automáticamente
   - B) Usan clientes proporcionados por el llamador y marcas de tiempo UTC; los errores se propagan al llamador
   - C) Los reintentos garantizan que los conteos de negocio se procesen exactamente una vez
   - D) CloudWatch crea todos los conjuntos agregados de dimensiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El conjunto completo de dimensiones identifica la métrica personalizada. PutMetricData no tiene un token de idempotencia; los reintentos ambiguos pueden duplicar muestras. El ejemplo informa los conteos por intervalo y usa Sum.

</details>

8. ¿En qué se diferencian las dimensiones de las métricas tradicionales y las etiquetas de OTel?

   - A) Ambas siempre son ilimitadas
   - B) El límite de 150 etiquetas sustituye el límite de PutMetricData
   - C) Las métricas tradicionales permiten 30 dimensiones; el modelo de OTel documentado admite hasta 150 etiquetas
   - D) Las etiquetas nunca afectan el tamaño de la carga útil ni la exposición de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Son modelos de ingesta distintos. Las etiquetas adicionales aumentan el tamaño de la carga útil y la exposición de metadatos; los nombres de las dimensiones por sí solos no permiten medir la cardinalidad.

</details>

9. ¿Qué interpretación de las métricas es correcta?

   - A) node_network_total_bytes se expresa en bytes por segundo; namespace_number_of_running_pods cuenta pods
   - B) cluster_cpu_utilization es la métrica estándar publicada
   - C) Los contenedores en estado Running siempre equivalen a los pods en estado Running
   - D) Todas las métricas de capacidad reservada son exclusivas de la observabilidad mejorada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Verifica los catálogos de métricas y los conjuntos de dimensiones reales. La utilización de CPU y memoria de un pod puede usar los límites del nodo como denominador. La observabilidad mejorada agrega métricas y dimensiones, y tiene su propio modelo de facturación.

</details>

10. ¿Qué se debe comprobar para una alarma de anomalía o de reinicios?

   - A) La creación de una alarma demuestra que hay telemetría activa
   - B) Un total de reinicios siempre es un incremento por intervalo
   - C) Quita ReturnData incondicionalmente de la serie de anomalías observada
   - D) El historial, la identidad exacta de la métrica, si representa un total o un incremento, los datos faltantes y la entrega de notificaciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

ANOMALY_DETECTION_BAND devuelve límites esperados aprendidos. El formato de anomalía documentado puede devolver tanto la serie observada como la banda. Un total de reinicios con PodName/Namespace/ClusterName no equivale automáticamente a cinco reinicios nuevos en cinco minutos.

</details>

---

[Volver a la guía](../../../observability/metrics/04-cloudwatch-metrics.md)
