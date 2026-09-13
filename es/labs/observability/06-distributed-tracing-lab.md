# Parte 6: Análisis de trazas distribuidas

<span id="cleanup-steps-table"></span>
<span id="drill-down-analysis-workflow"></span>
<span id="exercise-1-traceql-trace-search"></span>
<span id="exercise-2-service-graph-visualization"></span>
<span id="exercise-3-latency-identification-workflow"></span>
<span id="exercise-4-loki-tempo-correlation"></span>
<span id="exercise-5-exemplar-usage"></span>
<span id="exercise-6-comprehensive-dashboard-setup"></span>
<span id="final-verification-checklist"></span>
<span id="full-cleanup-script"></span>
<span id="key-takeaways"></span>
<span id="learning-objectives"></span>
<span id="next-steps"></span>
<span id="prerequisites"></span>
<span id="references"></span>
<span id="steps"></span>
<span id="steps-1"></span>
<span id="steps-2"></span>
<span id="steps-3"></span>
<span id="steps-4"></span>
<span id="steps-5"></span>
<span id="summary"></span>
<span id="traceql-query-reference"></span>
<span id="verification"></span>

> **Dificultad**: Avanzado · **Tiempo estimado**: 45 minutos
> **Última actualización**: September 13, 2026

Sigue una petición real desde las métricas, pasando por un exemplar, hasta su trace (traza) y sus logs (registros), separando las observaciones de las hipótesis causales. Esto requiere la ruta de ingesta de la [Parte 2](./02-observability-stack-lab.md) y la propagación de contexto de la [Parte 3](./03-msa-deployment-lab.md). El TraceQL que aparece a continuación se comprobó con el parser real de Tempo **3.0.3** y usa los atributos actuales de OTel.

![Investigate a metric through its trace and logs](../../.gitbook/assets/en-labs-observability-06-distributed-tracing-lab-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-06-distributed-tracing-lab-0.html)

## 1. Búsqueda con TraceQL {#traceql}

```traceql
{ resource.service.name = "order-service" && span:duration > 1s }

{ trace:duration > 2s && resource.service.name = "order-service" }

{ span:kind = server && span.http.response.status_code >= 500 }

{ span.db.system.name = "postgresql" && span:duration > 100ms }

{ span.messaging.system = "aws_sqs" && span.messaging.operation.type = "send" }

{ resource.service.name = "api-gateway" } >> { resource.service.name = "order-service" }

{ resource.service.name = "order-service" } >> { span.db.system.name = "postgresql" }

{ span:status = error } | select(resource.service.name, span.http.response.status_code, span:duration)
```

`span:duration` mide un span individual; `trace:duration` mide el trace completo. Usa `span:` para los intrínsecos explícitos y `span.`/`resource.` para los atributos. `>>` encuentra los spans de la derecha que descienden de los spans de la izquierda. Buscar descendientes de un span de base de datos no es lo mismo que encontrar trabajo de base de datos por debajo de un Service.

`sort(duration)`, el `order by` de SQL, `| limit 20` y `{ duration > p99 }` no forman parte de esta sintaxis de búsqueda. Configura el orden de los resultados, el límite de búsqueda y el rango temporal en Grafana, y sustituye un p99 medido por un literal de duración como `800ms`. `select()` solicita los atributos que se muestran; no puede recrear spans que nunca se almacenaron.

Los SDK más antiguos pueden emitir `http.status_code`, `http.method`, `db.system`, `db.statement` o `messaging.operation`. Inspecciona los spans reales y las versiones del SDK antes de usar los actuales `http.response.status_code`, `http.request.method`, `db.system.name`, `db.query.text` o `messaging.operation.type`. Renombrar un atributo de consulta no transforma los datos ya recopilados. Captura el texto de las consultas solo bajo una política explícita de saneamiento; excluye contraseñas, literales SQL y datos de clientes.

## 2. Requisitos previos del grafo de servicios {#service-graph}

Recibir trazas en Tempo no basta por sí solo para completar el grafo de servicios de Grafana. Habilita el procesador service-graphs del metrics-generator, entrega sus métricas a un backend de métricas real y enlaza el UID de serviceMap del datasource de Tempo en Grafana con ese backend. Los spans cliente/servidor o productor/consumidor deben compartir contexto. El muestreo, los spans ausentes y los tipos de span incorrectos afectan a las aristas resultantes.

```promql
sum by (client, server) (rate(traces_service_graph_request_total[5m]))

(
  sum by (client, server) (rate(traces_service_graph_request_failed_total[5m]))
  or on (client, server)
  (0 * sum by (client, server) (rate(traces_service_graph_request_total[5m])))
)
/ on (client, server)
(sum by (client, server) (rate(traces_service_graph_request_total[5m])) > 0)

sum by (client, server) (rate(traces_service_graph_request_server_seconds_sum[5m]))
/
sum by (client, server) (rate(traces_service_graph_request_server_seconds_count[5m]))
```

El contador de fallos puede no tener ninguna serie hasta el primer fallo. Rellena su numerador ausente con cero a partir de la serie de total de peticiones correspondiente y luego exige un denominador positivo para distinguir un 0% saludable de la ausencia de tráfico o de una ingesta que falta.

La última consulta mide la duración media del lado del servidor. La duración del lado del cliente usa `traces_service_graph_request_client_seconds_*`; no consultes la familia inexistente `traces_service_graph_request_duration_seconds_*`. Trata los intervalos sin tráfico como evidencia ausente. Los colores y el grosor de las aristas dependen de la configuración de Grafana y del dashboard; inspecciona los valores de peticiones, errores y duración en lugar de asumir reglas de color fijas del 1%/5%.

## 3. Formula hipótesis de cuellos de botella a partir del waterfall {#waterfall}

| Observación | Seguimiento |
|---|---|
| Span de base de datos lento | Revisa el plan de consulta, los bloqueos, el pool de conexiones y las métricas de la base de datos |
| Span de cliente prolongado | Compara los intervalos de DNS/TLS/red/espera del servidor/reintentos |
| Hueco entre el span padre y el hijo | Revisa el trabajo no instrumentado, las colas, el GC y la planificación |
| Spans hijos en paralelo | Analiza el solapamiento y la ruta crítica en lugar de sumar duraciones |
| Retraso en la mensajería | Separa la duración de envío/recepción/procesamiento de la espera en cola y las reentregas |

La duración del padre incluye la duración de los hijos; sumar todos los spans cuenta el tiempo dos veces. Un span de base de datos de 1,8 segundos no prueba por sí solo que falte un índice. Compara logs y métricas sobre la misma release, el mismo tráfico y el mismo rango temporal antes de aceptar una hipótesis.

## 4. Enlaza logs y trazas {#correlation}

```logql
{service_name="order-service"} | json | level="ERROR"

{service_name="order-service"} | json | trace_id="0123456789abcdef0123456789abcdef"
```

Estas consultas dan por supuesto que existen realmente una etiqueta de stream `service_name` y un campo JSON `trace_id`. Sustituye el trace ID de ejemplo de 32 caracteres por un ID de petición real. `traceID`, `traceId` y `trace_id` son campos distintos. Mantén los trace ID en campos de log o en metadatos estructurados, no en etiquetas de stream únicas. Define los límites temporales en Grafana o en los parámetros HTTP; no añadas `timestamp >= 2025-...` a LogQL.

Un derived field de Loki extrae el trace ID y enlaza con el UID del datasource de Tempo. En el YAML de provisioning de Grafana, escapa la expresión del enlace interno como `$${__value.raw}`. Las expresiones regulares entre comillas dobles y un envsubst de shell demasiado amplio pueden alterar las barras invertidas o las variables de Grafana; usa comillas simples cuando corresponda y sustituciones de alcance reducido.

Configura `tracesToLogsV2` de Tempo con el UID de Loki, el mapeo real de etiquetas de recurso a log, el margen temporal y el filtrado por trace ID. Inspecciona el LogQL generado después de hacer clic en «Logs for this span». Que el enlace exista y que se recupere correctamente la misma petición son comprobaciones distintas.

## 5. Significado y verificación de los exemplars {#exemplars}

![Follow a representative exemplar to its trace and logs](../../.gitbook/assets/en-labs-observability-06-distributed-tracing-lab-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-labs-observability-06-distributed-tracing-lab-1.html)

Un exemplar es una **observación representativa** adjunta a un agregado. Hacer clic en un punto de una gráfica de p99 no prueba que esa petición determinara el límite exacto del percentil. La producción de exemplars, su conservación en el exporter/remote-write, el almacenamiento en Prometheus y el enlace del datasource en Grafana deben funcionar todos. El muestreo o la retención pueden dejar un ID de exemplar cuyo trace no esté disponible.

Inspecciona los resultados reales de la API de exemplars de Prometheus y consulta Tempo con el `trace_id` devuelto. Habilitar una opción de visualización en Grafana o buscar un ConfigMap de Prometheus inexistente no valida la ingesta. Verifica los ajustes de almacenamiento de exemplars frente a la versión instalada de Prometheus o del chart y frente al recurso de Prometheus renderizado y sus argumentos de ejecución.

## 6. Dashboards RED y SLI/SLO {#slo}

Construye los paneles RED a partir de los nombres de métrica, las etiquetas y las unidades de histograma reales. Compara la tasa de peticiones, la proporción de fallos y la distribución de duraciones sobre el mismo alcance de Service/ruta. Define qué peticiones son elegibles y qué cuenta como éxito antes de calcular la disponibilidad; indica cómo se tratan las respuestas 4xx, los health checks y los reintentos.

Un SLO de 30 días requiere retención y observaciones reales a lo largo de ese periodo. Una consulta `[30d]` en un laboratorio recién creado no genera 30 días de evidencia. Gestiona la ausencia de tráfico, las series ausentes y los reinicios de contadores; declara las limitaciones de los percentiles con volúmenes bajos. Calcula el presupuesto de errores usando los fallos permitidos y los fallos observados en la misma ventana. Registra el periodo, el denominador y el valor en lugar de afirmar un fijo «99,9% conseguido».

## 7. Verifica el flujo y luego limpia {#cleanup}

Antes de la limpieza, registra una petición cuyo ID de exemplar, trace ID en Tempo y trace ID en los logs coincidan; verifica las dependencias reales del grafo de servicios y la entrega de alertas. Conserva los valores medidos, las marcas de tiempo y las versiones de configuración en lugar de rellenar los resultados con estimaciones.

| Orden | Acción y condición de finalización |
|---|---|
| 1 | Detén k6/Locust, la inyección de fallos y los disparadores de análisis con IA; guarda los resultados |
| 2 | Detén la recreación del ApplicationSet/padre de GitOps y elimina en cascada la aplicación real |
| 3 | Elimina los LoadBalancers/Ingresses, workloads y PVCs del clúster de servicio; verifica la limpieza de los LB y volúmenes externos |
| 4 | Elimina los custom resources de telemetría antes de desinstalar sus operators usando los nombres reales de release/namespace |
| 5 | Vacía/elimina los NodeClaims de Karpenter antes de retirar el controlador; conserva los controladores de API/LB/almacenamiento mientras existan dependencias |
| 6 | Revisa los planes de destrucción con el mismo estado de IaC; usa los IDs/ARNs exactos registrados para los recursos de AWS creados manualmente |
| 7 | Elimina EKS/VPC después de limpiar las dependencias y luego verifica la eliminación de los servicios gestionados y los recursos residuales |

No elimines namespaces compartidos ni CRDs de ámbito de clúster. Usa la release/namespace/versión de instalación registrados, no una URL de instalador `latest`. En S3 con versionado hay que revisar las versiones antiguas y los delete markers además de los objetos actuales. Reconcilia la política de snapshots de Aurora, el bucket de MWAA/DAG, AMG, AMP, OpenSearch, SNS/SQS/DLQ, Lambda/API Gateway, las asociaciones de IAM, EBS/LBs, los log groups y las alarmas con tu inventario. Las solicitudes de eliminación aceptadas no equivalen a una eliminación completada.

Revisa la propiedad de los recursos y preserva la evidencia y el estado en lugar de usar una destrucción autoaprobada sin comprobar, silenciar todos los errores o eliminar todo el directorio de trabajo.

## Alcance de la validación y referencias

El parser actual de Tempo validó 12 consultas aceptadas y rechazó tres consultas erróneas anteriores. Una instancia local efímera de Loki 3.7.7 recibió dos líneas de log sintéticas; ambas consultas LogQL recuperaron exactamente el trace ID esperado. No se ejecutaron la búsqueda en Tempo del servicio real, la recopilación en Loki, el enlace de datos en Grafana ni la eliminación en la nube.

- [TraceQL](https://grafana.com/docs/tempo/latest/traceql/)
- [Métricas del grafo de servicios](https://grafana.com/docs/tempo/latest/metrics-from-traces/service_graphs/)
- [Spans HTTP de OTel](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)
- [Spans de base de datos de OTel](https://opentelemetry.io/docs/specs/semconv/database/database-spans/)
- [Derived fields de Loki](https://grafana.com/docs/grafana/latest/datasources/loki/configure-loki-data-source/)
- [Guía de Tempo](../../observability/tracing/01-tempo.md)
- [Guía de Loki](../../observability/logging/01-loki.md)
- [Índice de la serie](./README.md)
