# Cuestionario de descripción general de métricas

> **Última actualización**: September 12, 2026

1. ¿Qué tipo representa un recuento acumulativo que puede reiniciarse?

   - A) Gauge
   - B) Counter
   - C) Un p99 precalculado
   - D) Una marca de tiempo de scrape

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Un Counter acumula incrementos no negativos. Los reinicios pueden ocurrir cuando se vuelve a crear el estado medido. rate() maneja los reinicios observados, pero no puede recuperar incrementos no observados.

</details>

2. ¿Cinco métodos, veinte rutas y diez estados implican qué?

   - A) Exactamente 1.000 series almacenadas en cada Deployment
   - B) Como máximo 1.000 combinaciones de etiquetas de aplicación si todas las combinaciones son posibles
   - C) Exactamente 1.000 muestras por día
   - D) Ningún efecto sobre el uso de recursos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El producto es un límite superior. Las combinaciones reales, las etiquetas de target/réplica, los buckets de Histogram y la rotación histórica determinan la huella real de series/almacenamiento.

</details>

3. ¿Qué uso de Pushgateway es apropiado?

   - A) Usar una clave de agrupación HOSTNAME para cada Pod de corta duración y depender de la expiración automática
   - B) Usarlo para un batch adecuado de nivel de servicio con agrupación estable, marcas de tiempo de éxito y una política de retirada explícita
   - C) Tratar gateway up=1 como prueba de que cada batch tuvo éxito
   - D) Enviar marcas de tiempo de éxito incluso cuando el batch falla

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Pushgateway no es la opción predeterminada para todos los jobs de corta duración y los grupos no tienen TTL automático. Su estado de scrape es independiente de la actualidad del batch. El scrape con honor_labels conserva la identidad del job enviado.

</details>

4. ¿Qué afirmación sobre Histogram y Summary es correcta?

   - A) Los cuantiles de Summary siempre son exactos
   - B) Promediar valores p99 de instancias produce el p99 de la flota
   - C) Los buckets de histogramas clásicos compatibles se pueden combinar; sum/count de Summary se puede combinar para una media
   - D) Ningún dato de Summary puede agregarse jamás

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los buckets clásicos los cuenta el productor instrumentado; Prometheus calcula los cuantiles en el momento de la consulta. Los cuantiles de Summary tienen un error que depende del algoritmo/ventana y no se pueden agregar para obtener un cuantil de flota, mientras que las tasas sum/count de duración no negativa pueden producir una media de flota.

</details>

5. ¿Cuál NO es la convención recomendada para una nueva métrica de aplicación de Prometheus?

   - A) Usar un prefijo descriptivo
   - B) Usar un sufijo de unidad como _seconds o _bytes
   - C) Preferir camelCase y unidades de milisegundos en lugar de la convención habitual de unidades base
   - D) Usar _total para identificar un Counter acumulativo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Prefiera nombres descriptivos separados por guiones bajos y unidades base. _total es un marcador de Counter, no una unidad física. Las API de exporter existentes, como node_memory_MemAvailable_bytes, conservan su ortografía publicada.

</details>

6. ¿Qué afirmación sobre la retención de Prometheus es correcta?

   - A) Nunca puede retener más de 30 días
   - B) El valor predeterminado es 15 días sin configuración explícita de retención por tiempo/tamaño; una retención más prolongada necesita configuración y capacidad adecuadas
   - C) No comprime los datos locales
   - D) Las réplicas de recopilación independientes son imposibles sin Mimir

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La retención predeterminada no es un máximo. La TSDB local no es un almacén distribuido replicado; la redundancia de recopilación, la deduplicación de consultas, la durabilidad y la recuperación son decisiones de diseño independientes.

</details>

7. ¿Qué afirmación sobre producto/almacenamiento es incorrecta?

   - A) Las implementaciones de nodo único y de clúster de VictoriaMetrics tienen distintos requisitos operativos
   - B) La resolución de métricas tradicional de CloudWatch se vuelve más gruesa con el tiempo
   - C) El almacenamiento de objetos de Mimir garantiza escala ilimitada y elimina todos los requisitos de almacenamiento local
   - D) Las métricas de Datadog usan rollups de consulta, por lo que la retención no garantiza la resolución original en cada gráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El almacenamiento de objetos forma parte de la arquitectura de Mimir, no es una garantía de capacidad ilimitada. Los recursos de ingesta/locales, los límites de consulta, la replicación y la capacidad operativa siguen siendo importantes. No confunda los destinos de backup ni las características específicas de una edición con el almacén principal de un producto.

</details>

8. ¿Qué enfoque no logra controlar la cardinalidad de métricas?

   - A) Usar plantillas de rutas normalizadas
   - B) Evitar los ID de usuario/sesión como etiquetas ordinarias
   - C) Agrupar códigos de estado cuando sea aceptable perder detalle
   - D) Asignar un nuevo valor de etiqueta request_id a cada solicitud

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Los valores de etiqueta distintos crean series distintas, incluso cuando los valores están hasheados. El contexto específico de la solicitud pertenece a logs/traces controlados adecuadamente cuando sea necesario. Tanto la cardinalidad como la exposición de datos sensibles requieren revisión.

</details>

9. ¿Qué rol de métricas de Kubernetes está correctamente asociado?

   - A) node-exporter — estado de objeto de la API de Kubernetes
   - B) kube-state-metrics — uso medido de CPU del contenedor
   - C) métricas de cAdvisor/kubelet — mediciones de recursos del contenedor
   - D) metrics-server — Prometheus TSDB a largo plazo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

node-exporter informa métricas del sistema operativo host; kube-state-metrics expone el estado de los objetos de la API; metrics-server sirve la Resource Metrics API. Las reglas de Prometheus/vmalert/Mimir evalúan alertas y Alertmanager las enruta. vmagent es un recopilador/reenviador, no una TSDB consultable.

</details>

10. ¿Qué hace que una comparación de costos sea revisable?

   - A) Una clasificación de productos basada solo en el tamaño del equipo
   - B) El número de nodos sin intervalo de muestras ni supuestos de características
   - C) El volumen medido de series/muestras, los requisitos de retención/resolución, HA/consulta y los precios actuales para las características seleccionadas
   - D) Suponer que las longitudes del nombre/valor de las métricas nunca importan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Un millón de series exportadas reales a intervalos de 15 segundos durante 30 días implica 172,8 mil millones de muestras antes del filtrado/deduplicación de entrega. La infraestructura, los índices/WAL, las réplicas, el trabajo de consulta, las asignaciones de métricas personalizadas y el esfuerzo del operador pueden modificar los costos. Este es un cálculo de carga de trabajo, no una cotización de proveedor.

</details>

[Volver a la guía](../../../observability/metrics/README.md)
