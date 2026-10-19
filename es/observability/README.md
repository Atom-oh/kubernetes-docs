# Introducción a la observabilidad

> **Última revisión**: 12 de septiembre de 2026.

## Introducción

En los sistemas distribuidos modernos, en especial las arquitecturas de microservicios basadas en Kubernetes, es esencial poder observar y comprender el estado interno de los sistemas a partir de sus resultados externos. A esto se le llama **observabilidad**.

## Observabilidad y monitorización

La monitorización consiste en recopilar y analizar el comportamiento del sistema y responder a los cambios. La observabilidad describe hasta qué punto sus resultados permiten comprender el estado interno. Ambas se complementan: la monitorización puede incluir registros, trazas y consultas de diagnóstico.

| Aspecto | Monitorización | Observabilidad |
| --- | --- | --- |
| **Enfoque** | Evaluación continua del estado y del impacto en los usuarios | Visibilidad suficiente para explicar el comportamiento del sistema |
| **Práctica** | SLO, paneles, alertas e investigación | Instrumentación, contexto, correlación y exploración |
| **Preguntas** | ¿Qué cambió y por qué está fallando? | ¿Hay suficientes pruebas para responder esas preguntas? |
| **Datos** | Métricas, registros, trazas y otras señales útiles | Calidad, cobertura y conexiones entre esas señales |
| **Complejidad** | Útil en sistemas sencillos y distribuidos | Diseñada en función del sistema y de los objetivos operativos |

## Los tres pilares de la observabilidad

Los registros, las métricas y las trazas son tres señales muy utilizadas, pero no constituyen una definición exhaustiva de la observabilidad. Los perfiles también pueden describir el uso de recursos a nivel del código; la madurez de las señales varía en OpenTelemetry, donde la compatibilidad con perfiles aún está en desarrollo.

### 1. Registros

Los registros son anotaciones de eventos individuales que ocurren en un sistema.

**Características:**
- Registran eventos discretos; la resistencia a manipulaciones y las garantías de retención dependen de la configuración del almacenamiento.
- Incluyen marcas de tiempo e información contextual.
- Pueden tener un formato estructurado (JSON) o no estructurado.
- Son útiles para depurar y auditar si se definen deliberadamente la cobertura de eventos, los controles de acceso y la retención.

**Casos de uso:**
- Seguimiento de errores y excepciones
- Auditoría de seguridad
- Cumplimiento normativo
- Depuración detallada

**Función de las herramientas:** Loki, Elasticsearch/OpenSearch y CloudWatch Logs ofrecen backends de almacenamiento y consulta; Fluent Bit recopila y reenvía registros.

### 2. Métricas

Las métricas son mediciones numéricas a lo largo del tiempo.

**Características:**
- Se almacenan como series temporales.
- Admiten agregaciones y operaciones matemáticas.
- El almacenamiento es eficiente cuando se controlan la cardinalidad y el volumen de recopilación.
- Son adecuadas para analizar tendencias.

**Tipos de métricas comunes de Prometheus:**
- **Counter (contador)**: valores acumulativos crecientes que pueden volver a cero, por ejemplo, tras un reinicio (como el recuento de solicitudes).
- **Gauge (indicador)**: mediciones actuales que pueden aumentar o disminuir (como el uso de memoria).
- **Histogram (histograma)**: distribuciones de observaciones (como la latencia de respuesta); los histogramas clásicos y los nativos difieren en su representación y sintaxis de consulta.
- **Summary (resumen)**: recuento y suma de observaciones y, según la implementación, cuantiles precalculados; promediar los cuantiles de varias instancias no produce un cuantil válido para toda la flota.

**Herramientas:** Prometheus, VictoriaMetrics, CloudWatch Metrics y Datadog.

### 3. Trazas

Las trazas describen el recorrido observado del trabajo relacionado mediante spans. Las brechas de instrumentación, el muestreo, los fallos de propagación y la pérdida de datos pueden dejar una traza parcial.

**Características:**
- Permiten visualizar el flujo de solicitudes entre servicios.
- Miden la latencia en cada paso.
- Ayudan a identificar cuellos de botella.
- Permiten analizar dependencias.

**Componentes:**
- **Trace (traza)**: spans relacionados que comparten un TraceID.
- **Span**: una unidad de trabajo.
- **SpanContext**: TraceID, SpanID, indicadores de traza y tracestate que se usan para propagar el contexto de trazado.

**Herramientas:** Tempo, Jaeger, X-Ray, Zipkin y Datadog APM.

## Correlación entre los tres pilares

Es posible correlacionar señales cuando se configuran la instrumentación, la recopilación y los enlaces con el backend. La mera presencia de las señales no conecta automáticamente todos los eventos.

![Una solicitud HTTP se distribuye desde una puerta de enlace de API entre los servicios de usuario, pedidos y pagos; cada servicio emite registros, métricas y trazas con un mismo ID de traza, que enlaza en ambas direcciones con un exemplar de métrica y con entradas de registro correlacionadas para poder pasar de un pilar a otro.](../.gitbook/assets/en-observability-readme-2.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-readme-2.html)

La figura abrevia los ID con fines ilustrativos. En los datos reales, use los ID completos válidos que se muestran a continuación. La correlación de métricas usa metadatos de exemplars; las etiquetas habituales de las métricas deben tener cardinalidad acotada.

### Correlación de trazas con registros

Registre TraceID y SpanID cuando haya un contexto de traza activo para enlazar los eventos de registro emitidos con los spans. Los registros en segundo plano o sin instrumentar pueden carecer de esos ID. Este es un ejemplo JSON de aplicación, no una carga completa de solicitud OTLP.

```json
{
  "timestamp": "2025-02-15T10:30:00Z",
  "level": "ERROR",
  "message": "Payment processing failed",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "spanId": "00f067aa0ba902b7",
  "service": "payment-service"
}
```

Los TraceID con formato W3C tienen 32 caracteres hexadecimales y los SpanID tienen 16; los ID compuestos solo por ceros no son válidos. El JSON conserva una marca de tiempo histórica con fines ilustrativos.

### Correlación de métricas con trazas (exemplars)

Un exemplar es metadato independiente que enlaza una observación concreta con una traza. Añadir un TraceID por solicitud a las series de métricas habituales generaría una cardinalidad elevada; por eso se deben usar exemplars o campos de registro. El siguiente ejemplo completo de texto OpenMetrics usa un histograma clásico y mediciones ilustrativas.

```text
# HELP http_request_duration_seconds Observed HTTP request duration.
# TYPE http_request_duration_seconds histogram
# UNIT http_request_duration_seconds seconds
http_request_duration_seconds_bucket{le="0.5"} 1000 # {trace_id="4bf92f3577b34da6a3ce929d0e0e4736"} 0.42
http_request_duration_seconds_bucket{le="+Inf"} 1000
http_request_duration_seconds_sum 123.4
http_request_duration_seconds_count 1000
# EOF
```

Un exemplar requiere tanto un conjunto de etiquetas como un valor de observación (`0.42`); la marca de tiempo es opcional. La recopilación y el almacenamiento deben admitir y conservar exemplars, y los enlaces de las fuentes de datos deben asignar la etiqueta `trace_id` al backend de trazas. La traza referenciada también debe haberse muestreado y retenido.

## OpenTelemetry y estandarización

OpenTelemetry (OTel) proporciona API, SDK, instrumentación y herramientas de Collector independientes del proveedor. Las señales admitidas y la instrumentación automática varían según el lenguaje, el framework y la versión del componente.

![Las aplicaciones de cualquiera de cuatro lenguajes se instrumentan de forma automática o manual y envían datos a través de las etapas de recepción, procesamiento y exportación del Collector de OpenTelemetry hacia uno de cinco backends de observabilidad.](../.gitbook/assets/en-observability-readme-3.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-readme-3.html)

Este es un patrón de implementación. Las aplicaciones también pueden exportar directamente a un backend compatible. Los receivers, processors y exporters de Collector deben configurarse para las señales elegidas; la madurez de los componentes varía.

**Ventajas de OpenTelemetry:**
- Estándar independiente del proveedor
- Compatibilidad con SDK para varios lenguajes
- Capacidades de instrumentación automática
- Compatibilidad con varios backends
- Comunidad activa

## Estrategia de observabilidad en entornos EKS

Estrategias para implementar una observabilidad eficaz en Amazon EKS:

### 1. Observabilidad por capas

![Las capas de infraestructura, Kubernetes y aplicaciones envían sus señales a herramientas de observabilidad correspondientes: las métricas de infraestructura van a CloudWatch, las métricas del clúster y del negocio a Prometheus/Grafana, y las trazas y registros de aplicaciones a Tempo/X-Ray y Loki.](../.gitbook/assets/en-observability-readme-4.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-readme-4.html)

Estas son rutas de señal de ejemplo, no asignaciones exclusivas de herramientas a capas. CloudWatch y otros backends pueden abarcar varias capas. Los recopiladores a nivel de nodo requieren el modelo de acceso y despliegue compatible con el modo de cómputo de EKS seleccionado.

### 2. Ejemplos de herramientas

| Función | Ejemplos autogestionados | Ejemplos gestionados por AWS | Plataformas comerciales |
|----------|-------------|------------|------------|
| Métricas | Prometheus, VictoriaMetrics | CloudWatch, AMP | Datadog, New Relic |
| Registros | Loki, Elasticsearch/OpenSearch | CloudWatch Logs | Splunk, Datadog |
| Trazas | Tempo, Jaeger | X-Ray | Datadog APM, Dynatrace |
| Visualización | Grafana | CloudWatch Dashboards | Datadog, Dynatrace |

### 3. Estrategias de optimización de costos

- **Muestreo**: Equilibre el volumen de trazas retenidas con la cobertura para las investigaciones; el muestreo de cola recibe y almacena temporalmente los datos antes de decidir, por lo que no elimina todos los costos previos.
- **Políticas de retención**: Optimice los períodos de retención de datos.
- **Almacenamiento por niveles**: Compruebe los niveles de almacenamiento que admite el backend, las rutas de consulta y la retención necesaria.
- **Agregación y cardinalidad**: Controle el volumen de recopilación y las dimensiones de las etiquetas, teniendo en cuenta la pérdida de detalle de diagnóstico que produce la agregación.

## Modelo de madurez de la observabilidad

Use este modelo práctico para planificar y revisar los objetivos operativos. No es una secuencia de compra de productos ni una escala universal de certificación. Evalúe la cobertura de señales, la rapidez de las investigaciones, la utilidad de las alertas y los costos; introduzca análisis automatizados cuando se haya evaluado su comportamiento.

| Área de revisión | Capacidad que se debe evaluar | Herramientas de ejemplo |
| --- | --- | --- |
| Recopilación básica | Cobertura fiable de las señales necesarias del servicio y la plataforma | kubectl logs, CloudWatch |
| Centralización | Retención, controles de acceso y consultas adecuados | Loki, Prometheus, Grafana |
| Correlación | Enlaces mediante el contexto de solicitudes, servicios e implementaciones | Tempo, exemplars, TraceID |
| Automatización opcional | Asistencia de análisis con falsos positivos, brechas y respuestas evaluados | Datadog Watchdog, Dynatrace Intelligence |

## Guía de secciones

Esta sección sobre observabilidad se organiza así:

### [Registros](./logging/README.md)
Herramientas y estrategias para recopilar, almacenar y analizar registros:
- Loki: backend de agregación y consulta de registros
- Fluent Bit: recopilador de registros de alto rendimiento
- CloudWatch Logs: registro nativo de AWS

### [Métricas](./metrics/README.md)
Recopilación y análisis de métricas de series temporales:
- Prometheus: sistema de métricas de uso extendido
- VictoriaMetrics: backend de almacenamiento y consulta de métricas
- CloudWatch Metrics: métricas nativas de AWS

### [Trazas](./tracing/README.md)
Trazado distribuido y análisis del flujo de solicitudes:
- Tempo: backend de trazas distribuidas de Grafana
- X-Ray: trazado distribuido nativo de AWS
- OpenTelemetry: instrumentación estandarizada
- Dynatrace: APM con tecnología de IA

### [Grafana (paneles)](./grafana/README.md)
Visualización unificada y paneles:
- Integración de fuentes de datos
- Patrones de diseño de paneles
- Configuración de alertas

### [Alertas](./alerting/README.md)
Alertas accionables, enrutamiento e integraciones de respuesta.

### [Optimización de la observabilidad](./09-observability-optimization.md)
Volumen de recopilación, cardinalidad, retención y costos operativos.

### [Laboratorios integrados](../labs/observability/README.md)
Ejercicios paso a paso de infraestructura, pila de observabilidad, aplicaciones, carga y trazado.

## Primeros pasos

Empiece por los objetivos de los servicios, las preguntas que surgen durante las investigaciones y las capacidades existentes de la plataforma y sus colectores. Adapte esta secuencia de ejemplo a esos requisitos:

1. **Configurar las métricas**: Elija Prometheus, VictoriaMetrics o un backend gestionado adecuado.
2. **Configurar la recopilación de registros**: Despliegue Loki y Fluent Bit.
3. **Configurar el trazado**: Despliegue Tempo o X-Ray.
4. **Visualización**: Conecte las fuentes de datos y los paneles necesarios en la plataforma elegida.
5. **Correlación**: Configure enlaces basados en TraceID.

## Referencias

- [Señales de OpenTelemetry](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Modelo de datos de registros de OpenTelemetry](https://opentelemetry.io/docs/specs/otel/logs/data-model/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Tipos de métricas de Prometheus](https://raw.githubusercontent.com/prometheus/docs/main/docs/concepts/metric_types.md)
- [Especificación OpenMetrics](https://raw.githubusercontent.com/prometheus/OpenMetrics/main/specification/OpenMetrics.md)
- [Muestreo de OpenTelemetry](https://opentelemetry.io/docs/concepts/sampling/)
- [Documentación de OpenTelemetry para Grafana](https://grafana.com/docs/opentelemetry/)
- [Monitorización y registro de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/eks-observe.html)
- [Prácticas recomendadas de observabilidad de AWS](https://aws-observability.github.io/observability-best-practices/)
- [SRE Workbook: monitorización](https://sre.google/workbook/monitoring/)
- [Datadog Watchdog](https://docs.datadoghq.com/watchdog/)
- [Dynatrace Intelligence](https://docs.dynatrace.com/docs/dynatrace-intelligence)
