# OpenTelemetry

> **Base de revisión**: Collector Contrib 0.160.0; Operator 0.158.0; versiones de los lenguajes indicadas más abajo
> **Última actualización**: 12 de octubre de 2026

## Introducción

OpenTelemetry (OTel) es un marco de observabilidad para software nativo de la nube. Proporciona estándares neutrales respecto a los proveedores para generar, recopilar y gestionar tres señales: trazas, métricas y registros. La retrospectiva de la CNCF, fechada el 24 de julio de 2026, lo describió como el segundo proyecto, después de Kubernetes, en velocidad de contribución. La madurez del proyecto y la estabilidad de cada SDK o componente son aspectos distintos.

### Actualización de julio de 2026: graduación de la CNCF

OpenTelemetry alcanzó el estado de proyecto **graduado** de la CNCF en **mayo de 2026**; el artículo del 24 de julio es una retrospectiva. Este es el nivel de madurez más alto de la fundación, que también tienen proyectos como Kubernetes y Prometheus. La graduación indica que se han evaluado la gobernanza, las prácticas de seguridad y la adopción del proyecto para su uso en producción. La retrospectiva aborda las convenciones semánticas de GenAI, la observabilidad de navegadores y dispositivos móviles, la gobernanza de esquemas y las herramientas de implementación gradual. Consulta la publicación del blog de la CNCF ["OpenTelemetry has graduated… Now what?"](https://www.cncf.io/blog/2026/07/24/opentelemetry-has-graduated-now-what/) para conocer los antecedentes y la hoja de ruta.

## ¿Qué es OpenTelemetry?

OpenTelemetry nació de la fusión de los proyectos OpenTracing y OpenCensus:

![Los hitos históricos incluyen la incorporación de OpenTracing a la CNCF (2016), el repositorio de OpenCensus Go (2017) y la fusión de OpenTelemetry (2019), seguidos por Specification, SDKs, Collector y Protocol.](../../.gitbook/assets/en-observability-tracing-03-opentelemetry-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-tracing-03-opentelemetry-0.html)

## Conceptos fundamentales

### Tres señales

Este capítulo se centra en las trazas, las métricas y los registros. La creación de perfiles es otra señal en evolución; la compatibilidad y la estabilidad varían según la implementación. Los ID de trazas y registros, así como los ejemplares de métricas, requieren la instrumentación y la configuración del backend adecuadas.

| Señal | Descripción | Casos de uso |
|--------|-------------|-----------|
| **Trazas** | Seguimiento distribuido de solicitudes | Análisis de latencia, mapeo de dependencias |
| **Métricas** | Mediciones numéricas | Uso de recursos, SLI/SLO |
| **Registros** | Registros de eventos | Depuración, auditoría |

### Componentes principales

![El código de la aplicación emite telemetría mediante la API y el SDK de OTel hacia una canalización de recepción, procesamiento y exportación que se distribuye entre cinco backends de observabilidad: Tempo, Prometheus, Loki, X-Ray y Datadog.](../../.gitbook/assets/en-observability-tracing-03-opentelemetry-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-observability-tracing-03-opentelemetry-2.html)

La figura enumera las opciones de backend por señal. Solo están activos los exportadores configurados; el ejemplo base de abajo no habilita automáticamente todos los proveedores.


## SDK de OpenTelemetry

Collector, Operator, el agente de Java y los SDK de los lenguajes tienen números de versión independientes. Estas plantillas de cargas de trabajo Linux se han comprobado con los esquemas de Kubernetes 1.35: sus propietarios deben preparar las imágenes de aplicación, los espacios de nombres, los certificados y los servicios de destino. La matriz más amplia de Operator no elimina requisitos específicos de cada receta, como los sidecars nativos. Las comprobaciones locales no demuestran que haya una aplicación implementada en EKS.

| Componente | Base y límites |
|---|---|
| Collector Contrib independiente | 0.160.0; componentes y esquemas comprobados con su binario real |
| Operator | 0.158.0; su tabla de compatibilidad indica Kubernetes 1.25–1.36 y cert-manager v1 |
| Agente de Java | 2.31.1, con SDK 1.65.0 como objetivo; no es la misma versión que la imagen de Java predeterminada de Operator |
| Python | SDK/exportador 1.44.0 e instrumentación/distribución 0.65b0; Python ≥3.10 |
| Ejemplo de Node.js con CommonJS | SDK-node 0.220.0, auto-instrumentations-node 0.78.0, resources 2.9.0, API 1.9.1 |

Operator usa Collector 0.158.0 de forma predeterminada. Las cargas de trabajo independientes con la versión 0.160.0 que aparecen abajo no son una actualización de Collector gestionada por Operator. Comprueba la intersección con las versiones de EKS compatibles; la versión más reciente de Kubernetes no forma parte automáticamente de la matriz de Operator.

### Instrumentación automática

A fecha de 12 de octubre de 2026, la compatibilidad estándar de EKS incluye las versiones 1.34–1.37. La base de esquemas 1.35 está dentro de esta lista y de la matriz de Operator; aun así, esto no sustituye las comprobaciones de aceptación de la plataforma y sus complementos en funcionamiento.

La instrumentación sin código conecta con bibliotecas compatibles; no descubre operaciones de negocio arbitrarias. Para un proceso, elige entre preparar directamente un agente o lanzador y usar la inyección de Operator. No inicialices un segundo SDK sobre un proveedor que ya esté configurado. Las siguientes imágenes de aplicación son marcadores de posición para tus propias compilaciones, incluidos sus comandos de inicio y dependencias.

Prepara un espacio de nombres `ecommerce` y crea allí un Secret `otel-client-tls` que contenga `ca.crt`, `tls.crt` y `tls.key`. El Collector debe aceptar el certificado de cliente y su certificado debe coincidir con `otel-collector.otel.svc.cluster.local`. Los archivos del Secret se montan como solo lectura; adapta el acceso UID/GID a tu imagen. En las variables de entorno solo aparecen las **rutas** de los certificados, no el contenido de las claves ni los tokens de portador. Estas plantillas usan OTLP HTTP/protobuf sobre el puerto TLS 4318.

#### Instrumentación automática de Java

Descarga el agente fijado en la compilación de tu aplicación y verifica la suma de comprobación del recurso de la versión. El JAR 2.31.1 tiene 25,107,554 bytes, por lo que supera el límite de 1 MiB de un ConfigMap de Kubernetes. Inclúyelo en la imagen o usa la inyección de Operator; un ConfigMap no es un mecanismo de distribución de binarios de agentes.


```bash
curl --fail --location --output opentelemetry-javaagent.jar \
  https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v2.31.1/opentelemetry-javaagent.jar
printf '%s  %s\n' \
  bbf83c151b6400709e2f225bdd07a04f839d9d13b8b93464241333fd25d3e3ba \
  opentelemetry-javaagent.jar | sha256sum --check -
```

```dockerfile
# Add to the application's existing Dockerfile; not a complete image build.
COPY opentelemetry-javaagent.jar /opt/otel/opentelemetry-javaagent.jar
```
Combina la opción del agente con cualquier `JAVA_TOOL_OPTIONS` existente; no descartes las opciones de la JVM de la aplicación. El selector del Deployment y las etiquetas del Pod deben coincidir.


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/order-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: order-service
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        - name: JAVA_TOOL_OPTIONS
          value: -javaagent:/opt/otel/opentelemetry-javaagent.jar
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
#### Instrumentación automática de Python

Para una aplicación Flask, instala paquetes compatibles en su entorno de compilación y fija las dependencias resueltas de la aplicación. Otros frameworks necesitan su paquete de instrumentación correspondiente. Este ejemplo selecciona explícitamente el exportador HTTP, en vez de enviar el valor predeterminado HTTP de Python al puerto gRPC 4317.


```bash
python -m pip install \
  opentelemetry-api==1.44.0 opentelemetry-sdk==1.44.0 \
  opentelemetry-distro==0.65b0 \
  opentelemetry-instrumentation-flask==0.65b0 \
  opentelemetry-exporter-otlp-proto-http==1.44.0
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/payment-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: payment-service
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
        command:
        - opentelemetry-instrument
        - python
        - app.py
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
#### Instrumentación automática de Node.js


```bash
npm install --save-exact \
  @opentelemetry/api@1.9.1 @opentelemetry/resources@2.9.0 \
  @opentelemetry/sdk-node@0.220.0 \
  @opentelemetry/auto-instrumentations-node@0.78.0
# Commit package-lock.json and use npm ci for subsequent application builds.
```
Guarda esto como `tracing.cjs` y cárgalo antes que los módulos de la aplicación o del framework. Este es un ejemplo de CommonJS; la carga de ESM requiere la configuración independiente que se describe en la guía del lenguaje. El SDK lee las variables de entorno OTEL explícitas para el exportador y TLS que aparecen abajo. Para los lectores de métricas configurados mediante código, la configuración actual usa `metricReaders`, que sustituye a la opción singular obsoleta. Integra `shutdownTelemetry()` después del paso de drenaje de solicitudes de la propia aplicación.


```javascript
// Load before application/framework modules in a CommonJS application.
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { envDetector } = require('@opentelemetry/resources');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');

const sdk = new NodeSDK({
  resourceDetectors: [envDetector],
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs': { enabled: false },
      '@opentelemetry/instrumentation-http': {
        ignoreIncomingRequestHook: (request) =>
          String(request.url || '').split('?')[0] === '/health',
      },
    }),
  ],
});

// OTEL_* variables configure exporters, protocol, TLS and metric interval.
sdk.start();

// Call after the application's own request-draining step on shutdown.
module.exports = { shutdownTelemetry: () => sdk.shutdown() };
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notification-service
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: notification-service
  template:
    metadata:
      labels:
        app: notification-service
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/notification-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: notification-service
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
        command:
        - node
        - --require
        - ./tracing.cjs
        - app.cjs
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
Estos ejemplos establecen `OTEL_LOGS_EXPORTER=none` de forma deliberada. Habilitar un exportador de registros no hace que se sigan los datos de stdout de la aplicación: instala el puente o controlador de registro adecuado, o un recopilador de registros, y revisa antes la exposición de los datos. El muestreador `parentbased_always_on` sigue respetando un padre no muestreado. Si en su lugar eliges un muestreo inicial del 10 %, el Collector de muestreo de cola no puede recuperar los fragmentos descartados.

### Instrumentación manual

Reutiliza la instancia o el proveedor de OpenTelemetry inicializado por el agente o la aplicación. Sin un proveedor SDK, las llamadas a la API pueden no hacer nada. Estos fragmentos de flujos de trabajo de negocio son INTERNAL: los clientes HTTP/de base de datos instrumentados crean sus propios fragmentos CLIENT y propagan el contexto. Crear manualmente solo un fragmento CLIENT no envía una solicitud ni inyecta el contexto de traza.

#### Instrumentación manual de Java

La aplicación proporciona las devoluciones de llamada de inventario y pago. No se registran ID de pedido o cliente, importes, ID de transacción ni mensajes de excepciones sin procesar. Se trata de operaciones de aplicación, no de una implementación de servicio de pagos ni de una implementación de Spring probada.


```java
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.SpanKind;
import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.context.Scope;

public final class OrderTelemetry {
    private final Tracer tracer;

    public OrderTelemetry(OpenTelemetry telemetry) {
        this.tracer = telemetry.getTracer("example.order-workflow", "1.0.0");
    }

    public void processOrder(Runnable validateInventory, Runnable processPayment) {
        Span parent = tracer.spanBuilder("processOrder")
                .setSpanKind(SpanKind.INTERNAL).startSpan();
        try (Scope ignored = parent.makeCurrent()) {
            parent.addEvent("validation.started");
            child("checkInventory", validateInventory);
            child("processPayment", processPayment);
            parent.addEvent("processing.completed");
        } catch (RuntimeException error) {
            parent.setStatus(StatusCode.ERROR);
            parent.setAttribute("error.type", error.getClass().getName());
            throw error;
        } finally {
            parent.end();
        }
    }

    private void child(String name, Runnable operation) {
        Span span = tracer.spanBuilder(name).setSpanKind(SpanKind.INTERNAL).startSpan();
        try (Scope ignored = span.makeCurrent()) {
            operation.run();
        } catch (RuntimeException error) {
            span.setStatus(StatusCode.ERROR);
            span.setAttribute("error.type", error.getClass().getName());
            throw error;
        } finally {
            span.end();
        }
    }
}
```
#### Instrumentación manual de Python

El decorador síncrono conserva los resultados y los errores, y finaliza los fragmentos anidados. Solo registra el tipo de error, para evitar eventos de excepción sin procesar duplicados. Una función asíncrona requiere un contenedor compatible con asincronía. Proporciona tus propias devoluciones de llamada parametrizadas para las consultas a la base de datos, la validación, la persistencia y la publicación de eventos; la validación local usó devoluciones de llamada sintéticas y un exportador en memoria.


```python
"""Manual spans for synchronous application callbacks; no database is created."""
from functools import wraps
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode

# Reuse the SDK provider initialized by auto-instrumentation or the application.
tracer = trace.get_tracer("example.user-workflow", "1.0.0")

@contextmanager
def operation(name):
    with tracer.start_as_current_span(
        name, kind=SpanKind.INTERNAL,
        record_exception=False, set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except Exception as error:
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", type(error).__name__)
            raise

def traced(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with operation(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate

@traced("get_user")
def get_user(user_id, lookup):
    # lookup is supplied by the application, with parameterized queries.
    # The ID and SQL text are not added to telemetry.
    with operation("lookup_user"):
        result = lookup(user_id)
    trace.get_current_span().set_attribute("app.user.found", result is not None)
    return result

@traced("create_user")
def create_user(user_data, validate, save, publish):
    # These callbacks are the application's own implementations.
    with operation("validate_user_data"):
        validate(user_data)
    with operation("save_user"):
        result = save(user_data)
    with operation("publish_user_event"):
        publish(result)
    return result
```
Para instrumentar bases de datos o mensajería reales, sigue la versión de las convenciones implementada, por ejemplo `db.system.name`, `db.operation.name` y `messaging.destination.name`. No copies los ID de usuario en cadenas de telemetría SQL ni uses consultas sin procesar como etiquetas de métricas. Las devoluciones de llamada de negocio anteriores no demuestran que se haya ejecutado PostgreSQL o Kafka.

## Collector de OTEL

### Arquitectura


```mermaid
flowchart TD
    R["OTLP receiver / mTLS"]
    R -->|traces| P["Trace preprocessing: memory, resource, redaction, health filter"]
    P --> S["tail_sampling"]
    S --> B["batch"]
    B --> T["Tempo / OTLP gRPC mTLS"]
    P --> C["span_metrics before tail sampling"]
    C --> M["Metrics: memory, resource, batch"]
    R -->|metrics| M
    M --> W["Prometheus remote write / HTTPS"]
    R -->|logs| L["Logs: memory, resource, attribute redaction, batch"]
    L --> K["Loki native OTLP HTTP / mTLS"]
```

Rutas de señales para la configuración siguiente. El cuadro de preprocesamiento de trazas resume un procesamiento equivalente en dos canalizaciones de trazas separadas. Las métricas de fragmentos se derivan antes del muestreo de cola; las métricas y los registros entrantes usan sus propias canalizaciones.

### Configuración de Collector

Guárdala como `otel-collector-config.yaml`. Es una única instancia activa de muestreo y agregación con estado para un laboratorio, no una garantía de alta disponibilidad ni de capacidad. Una canalización de trazas independiente deriva métricas **antes del muestreo de cola**. Los fragmentos muestreados inicialmente o filtrados siguen ausentes de esas métricas. Estos contadores contabilizan fragmentos observados, no solicitudes únicas de usuarios finales; selecciona tipos de fragmento adecuados y dimensiones acotadas para los SLI de solicitudes. Los contadores acumulativos de métricas de fragmentos se exportan inicialmente con valor cero en 0.160.0; evalúa las descargas posteriores antes de interpretar el primer valor como ausencia de tráfico.

Prepara Tempo con OTLP habilitado, un receptor compatible con escritura remota de Prometheus y la ingesta OTLP nativa de Loki, con puertas de enlace TLS/autenticación proporcionadas por el operador. Los nombres de las puertas de enlace de abajo no son servicios creados por esta guía. Prometheus necesita habilitar su receptor de escritura remota (`--web.enable-remote-write-receiver` si se usa Prometheus). La ruta base del exportador de Loki termina en `/otlp`; el exportador HTTP añade `/v1/logs`. Configura los metadatos estructurados de Loki y el mapeo de inquilinos de confianza según sea necesario; un encabezado de inquilino no es autenticación.

Las variables de entorno identifican certificados y endpoints existentes. Todos los receptores configurados usan TLS mutuo; no se habilitan CORS de navegador con comodín ni endpoints públicos de creación de perfiles. Las eliminaciones de atributos indicadas son controles limitados, no un enmascaramiento completo de cuerpos de registros, eventos de fragmentos, atributos de recursos ni cargas útiles arbitrarias. Reduce también los datos en el SDK.


```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        max_recv_msg_size_mib: 16
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}

processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 384
    spike_limit_mib: 96
  resource/cluster:
    attributes:
      - key: k8s.cluster.name
        value: ${env:K8S_CLUSTER_NAME}
        action: insert
  attributes/redact:
    actions:
      - key: http.request.header.authorization
        action: delete
      - key: user.email
        action: delete
      - key: user.id
        action: delete
      - key: customer.id
        action: delete
      - key: db.statement
        action: delete
      - key: db.query.text
        action: delete
  filter/health:
    error_mode: propagate
    traces:
      span:
        - 'attributes["http.route"] == "/health"'
        - 'attributes["http.route"] == "/ready"'
        - 'attributes["http.route"] == "/metrics"'
  tail_sampling:
    decision_wait: 10s
    num_traces: 10000
    expected_new_traces_per_sec: 100
    policies:
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow
        type: latency
        latency:
          threshold_ms: 1000
      - name: selected-services
        type: string_attribute
        string_attribute:
          key: service.name
          values: [payment-service, order-service]
      - name: baseline
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
  batch:
    timeout: 5s
    send_batch_size: 512
    send_batch_max_size: 1024

connectors:
  span_metrics:
    histogram:
      unit: s
      explicit:
        buckets: [5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2s, 5s]
    dimensions:
      - name: http.request.method
      - name: http.response.status_code
    aggregation_cardinality_limit: 1000
    metrics_flush_interval: 15s

exporters:
  otlp_grpc/tempo:
    endpoint: ${env:TEMPO_OTLP_GRPC_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
  prometheus_remote_write:
    endpoint: ${env:PROMETHEUS_REMOTE_WRITE_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
  otlp_http/loki:
    endpoint: ${env:LOKI_OTLP_HTTP_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource/cluster, attributes/redact, filter/health, tail_sampling, batch]
      exporters: [otlp_grpc/tempo]
    traces/span-metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource/cluster, attributes/redact, filter/health]
      exporters: [span_metrics]
    metrics:
      receivers: [otlp, span_metrics]
      processors: [memory_limiter, resource/cluster, batch]
      exporters: [prometheus_remote_write]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource/cluster, attributes/redact, batch]
      exporters: [otlp_http/loki]
  telemetry:
    logs:
      level: info
      encoding: json
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 127.0.0.1
                port: 8888
```
Las políticas de muestreo positivas son condiciones OR, no una jerarquía de prioridades ordenada. Los servicios seleccionados pueden conservarse independientemente de la probabilidad de referencia. La latencia usa una comparación estricta `>1000 ms`. Las decisiones basadas en temporizadores no demuestran que la traza esté completa, y el filtro de estado elimina deliberadamente los fragmentos coincidentes incluso si contienen errores; filtrar fragmentos individuales puede dejar trazas parciales.

El límite estricto de memoria es 384 MiB y el límite flexible es 288 MiB, lo que deja margen por debajo del límite de 512 MiB del contenedor de la plantilla. Aun así, hay que medir los rechazos, los reintentos, las colas y los picos. Los límites de lotes, trazas y cardinalidad son valores de demostración, no resultados de pruebas de rendimiento.

### Carga de trabajo y configuración de una sola instancia

Prepara el espacio de nombres `otel` y los Secrets `otel-ingest-tls` y `otel-backend-tls` con `tls.crt`, `tls.key`, `ca.crt`. Usa SAN de certificados que coincidan con los nombres de Service o de las puertas de enlace correspondientes, un paquete de confianza adecuado y certificados con los usos de servidor/cliente correctos. Adapta el acceso a los archivos para UID/GID 10001. El ConfigMap contiene configuración de texto, no claves privadas. `Recreate` evita la superposición normal de la actualización gradual para esta instancia única de muestreo, a cambio de tiempo de inactividad; no conserva las trazas en memoria durante los reinicios.


```bash
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
kubectl --context "$KUBE_CONTEXT" -n otel create configmap otel-collector-config \
  --from-file=otel-collector-config.yaml --dry-run=client -o yaml > otel-collector-configmap.yaml
# Inspect the namespace, Secrets, endpoints and workloads before any real apply.
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: otel-collector
  namespace: otel
automountServiceAccountToken: false
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: otel
spec:
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-collector-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 384MiB
        - name: OTEL_SERVER_CERT
          value: /var/run/otel/ingest/tls.crt
        - name: OTEL_SERVER_KEY
          value: /var/run/otel/ingest/tls.key
        - name: OTEL_CLIENT_CA
          value: /var/run/otel/ingest/ca.crt
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        - name: K8S_CLUSTER_NAME
          value: REPLACE_WITH_CLUSTER_NAME
        - name: TEMPO_OTLP_GRPC_ENDPOINT
          value: tempo-gateway.tempo.svc.cluster.local:4317
        - name: PROMETHEUS_REMOTE_WRITE_ENDPOINT
          value: https://prometheus-gateway.monitoring.svc.cluster.local/api/v1/write
        - name: LOKI_OTLP_HTTP_ENDPOINT
          value: https://loki-gateway.loki.svc.cluster.local/otlp
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: ingest-tls
          mountPath: /var/run/otel/ingest
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
      - name: ingest-tls
        secret:
          secretName: otel-ingest-tls
          defaultMode: 288
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
  replicas: 1
  strategy:
    type: Recreate
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: otel
spec:
  type: ClusterIP
  selector:
    app: otel-collector
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
```
### Recopilación y enriquecimiento opcionales

| Requisito | Configuración independiente necesaria |
|---|---|
| Clientes heredados de Jaeger/Zipkin | Sus componentes de receptor siguen disponibles; habilita solo los protocolos y puertos necesarios y haz coincidir los ID de receptor en una canalización. Exporta a Jaeger mediante OTLP, no con el exportador de Jaeger eliminado. |
| Métricas propias de Collector | `service.telemetry.metrics.readers` configura el lector actual de Prometheus. El campo antiguo `address` se ha eliminado. Recopila datos del endpoint de loopback mediante una ruta de monitorización diseñada deliberadamente. |
| Métricas del clúster de Kubernetes | Ejecuta un único receptor `k8s_cluster` activo o configura su extensión de elección de líder. Proporciona credenciales de API y RBAC revisado, y luego conéctalo a una canalización de métricas. Las cargas de trabajo anteriores, sin token de forma predeterminada, no proporcionan esos requisitos previos. |
| Registros de nodos/contenedores o métricas de host | Añade el receptor, los montajes y los permisos adecuados; un DaemonSet por sí solo no los recopila. |
| Detección de recursos de EC2/EKS | Configura deliberadamente el detector deseado y su acceso a metadatos/API; no sustituyas la identidad de la carga de trabajo por la identidad del host de Collector. |
| Métricas derivadas de fragmentos | Usa el conector `span_metrics`, con una unidad de duración explícita y dimensiones acotadas. El procesador spanmetrics antiguo se ha eliminado. |

Consulta la [guía de Collector](../logging/05-collectors.md) y el [receptor de clúster de Kubernetes](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/receiver/k8sclusterreceiver). No declares un receptor o procesador sin usar y supongas que está activo.

## Patrones de implementación en EKS

Estos son patrones de implementación alternativos, no una pila que se deba aplicar indiscriminadamente. Un relay sin estado reenvía las tres señales al nivel único de muestreo de arriba. No coloques el muestreo de cola ni la agregación de fragmentos en un nivel de nodo, sidecar o HPA con balanceo de carga arbitrario. Varias instancias de muestreo requieren enrutamiento basado en el ID de traza y un plan para los cambios de endpoint, las trazas en curso, los reinicios y el almacenamiento; un Service o un HPA por sí solos no proporcionan nada de eso.

Guarda `otel-relay-config.yaml` y crea `otel-relay-config` con el mismo procedimiento de generación de ConfigMap del lado del cliente. `OTEL_UPSTREAM_ENDPOINT` y el certificado de cliente identifican el Collector ascendente preparado por separado. El relay no mantiene estado respecto a las decisiones de muestreo; sus colas de exportación y lotes en memoria siguen sujetas a límites ante fallos y durante el apagado.


```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
        max_recv_msg_size_mib: 16
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}
      http:
        endpoint: 0.0.0.0:4318
        tls:
          cert_file: ${env:OTEL_SERVER_CERT}
          key_file: ${env:OTEL_SERVER_KEY}
          client_ca_file: ${env:OTEL_CLIENT_CA}
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 384
    spike_limit_mib: 96
  batch:
    timeout: 5s
    send_batch_size: 512
    send_batch_max_size: 1024
exporters:
  otlp_grpc/upstream:
    endpoint: ${env:OTEL_UPSTREAM_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health
service:
  extensions:
  - health_check
  pipelines:
    traces:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    metrics:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
  telemetry:
    logs:
      level: info
      encoding: json
    metrics:
      readers:
      - pull:
          exporter:
            prometheus:
              host: 127.0.0.1
              port: 8888
```
### Patrón de DaemonSet

Un DaemonSet se ejecuta en los nodos Linux que cumplan los requisitos, no en EKS Fargate. Configura selectores y tolerancias para los nodos aprobados; aquí no se incluye ninguna tolerancia general ni reserva de hostPort. `internalTrafficPolicy: Local` dirige este Service únicamente a un endpoint listo en el nodo del cliente y descarta el tráfico si no hay ninguno. No es un mecanismo alternativo para los clientes de Fargate. Las aplicaciones deben enviar explícitamente la telemetría a este endpoint.


```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: otel-agent
  namespace: otel
spec:
  selector:
    matchLabels:
      app: otel-agent
  template:
    metadata:
      labels:
        app: otel-agent
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-relay-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 384MiB
        - name: OTEL_SERVER_CERT
          value: /var/run/otel/ingest/tls.crt
        - name: OTEL_SERVER_KEY
          value: /var/run/otel/ingest/tls.key
        - name: OTEL_CLIENT_CA
          value: /var/run/otel/ingest/ca.crt
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: ingest-tls
          mountPath: /var/run/otel/ingest
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
      volumes:
      - name: config
        configMap:
          name: otel-relay-config
      - name: ingest-tls
        secret:
          secretName: otel-ingest-tls
          defaultMode: 288
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
---
apiVersion: v1
kind: Service
metadata:
  name: otel-agent
  namespace: otel
spec:
  type: ClusterIP
  selector:
    app: otel-agent
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
  internalTrafficPolicy: Local
```
### Patrón de sidecar

Usa un ConfigMap `otel-sidecar-config` independiente con la configuración de abajo. Solo el mismo Pod usa el receptor OTLP sin cifrar en loopback; el tráfico ascendente utiliza TLS mutuo. Este perfil establece un límite estricto de 192 MiB y flexible de 144 MiB para un sidecar de 256 MiB. La imagen de la aplicación debe incluir el SDK o agente que elijas; una variable de endpoint no añade instrumentación por sí sola. Este ejemplo con esquema de Kubernetes 1.35 utiliza un sidecar nativo (`initContainers` con `restartPolicy: Always`, GA en 1.33). Su sonda de inicio se ejecuta antes de iniciar la aplicación, y durante el apagado normal los contenedores de la aplicación se detienen antes que el sidecar. La entrega al backend y la recuperación ante fallos abruptos siguen siendo comprobaciones independientes.


```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 127.0.0.1:4317
      http:
        endpoint: 127.0.0.1:4318
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 192
    spike_limit_mib: 48
  batch:
    timeout: 5s
    send_batch_size: 512
    send_batch_max_size: 1024
exporters:
  otlp_grpc/upstream:
    endpoint: ${env:OTEL_UPSTREAM_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health
service:
  extensions:
  - health_check
  pipelines:
    traces:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    metrics:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
    logs:
      receivers:
      - otlp
      processors:
      - memory_limiter
      - batch
      exporters:
      - otlp_grpc/upstream
  telemetry:
    logs:
      level: info
      encoding: json
    metrics:
      readers:
      - pull:
          exporter:
            prometheus:
              host: 127.0.0.1
              port: 8888
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-with-sidecar
  namespace: otel
spec:
  selector:
    matchLabels:
      app: order-with-sidecar
  template:
    metadata:
      labels:
        app: order-with-sidecar
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: app
        image: registry.example.com/order-service:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: order-service
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: http://127.0.0.1:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
      volumes:
      - name: config
        configMap:
          name: otel-sidecar-config
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
      initContainers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-sidecar-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 192MiB
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 500m
            memory: 256Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
        restartPolicy: Always
        startupProbe:
          httpGet:
            path: /health
            port: 13133
          periodSeconds: 2
          failureThreshold: 30
  replicas: 1
```
### Patrón de puerta de enlace

Este HPA escala el **relay** sin estado, no el muestreador con estado. Metrics Server y solicitudes/capacidad adecuadas son requisitos previos. Las tres réplicas, la antiafinidad preferida y el intervalo de 3 a 10 son elecciones ilustrativas, no una prueba de alta disponibilidad ni de rendimiento. Se pueden considerar Collectors basados en Deployment para Fargate o Auto Mode solo después de comprobar sus requisitos de ejecución, almacenamiento, red y receptores.


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-relay
  namespace: otel
spec:
  selector:
    matchLabels:
      app: otel-relay
  template:
    metadata:
      labels:
        app: otel-relay
    spec:
      serviceAccountName: otel-collector
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/os: linux
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/conf/otel-relay-config.yaml
        env:
        - name: GOMEMLIMIT
          value: 384MiB
        - name: OTEL_SERVER_CERT
          value: /var/run/otel/ingest/tls.crt
        - name: OTEL_SERVER_KEY
          value: /var/run/otel/ingest/tls.key
        - name: OTEL_CLIENT_CA
          value: /var/run/otel/ingest/ca.crt
        - name: BACKEND_CA
          value: /var/run/otel/backend/ca.crt
        - name: BACKEND_CLIENT_CERT
          value: /var/run/otel/backend/tls.crt
        - name: BACKEND_CLIENT_KEY
          value: /var/run/otel/backend/tls.key
        - name: OTEL_UPSTREAM_ENDPOINT
          value: otel-collector.otel.svc.cluster.local:4317
        ports:
        - name: otlp-grpc
          containerPort: 4317
        - name: otlp-http
          containerPort: 4318
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: config
          mountPath: /conf
          readOnly: true
        - name: ingest-tls
          mountPath: /var/run/otel/ingest
          readOnly: true
        - name: backend-tls
          mountPath: /var/run/otel/backend
          readOnly: true
        readinessProbe:
          httpGet:
            path: /health
            port: 13133
        livenessProbe:
          httpGet:
            path: /health
            port: 13133
          initialDelaySeconds: 15
      volumes:
      - name: config
        configMap:
          name: otel-relay-config
      - name: ingest-tls
        secret:
          secretName: otel-ingest-tls
          defaultMode: 288
      - name: backend-tls
        secret:
          secretName: otel-backend-tls
          defaultMode: 288
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: otel-relay
              topologyKey: kubernetes.io/hostname
  replicas: 3
---
apiVersion: v1
kind: Service
metadata:
  name: otel-relay
  namespace: otel
spec:
  type: ClusterIP
  selector:
    app: otel-relay
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: otel-relay
  namespace: otel
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: otel-relay
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Operator de Kubernetes

Operator 0.158.0 tiene una matriz de compatibilidad independiente. Su manifiesto de versión presupone que cert-manager v1 ya está preparado; usa una versión compatible mantenida de la [guía de cert-manager](../../security/10-cert-manager.md), en vez del ejemplo obsoleto 1.13.3. Antes de actualizar una instalación existente gestionada por su propietario, revisa los cambios de CRD y las políticas de red predeterminadas de 0.158.0.

### Instalación de Operator


```bash
curl --fail --location --output opentelemetry-operator.yaml \
  https://github.com/open-telemetry/opentelemetry-operator/releases/download/v0.158.0/opentelemetry-operator.yaml
printf '%s  %s\n' \
  3c258efb3d64834a857ce4ed5256af2883dc9c77a300eee465df833ab2354c8e \
  opentelemetry-operator.yaml | sha256sum --check -
# After prerequisites and ownership/upgrade review; this changes the cluster:
: "${KUBE_CONTEXT:?Set the reviewed cluster context}"
kubectl --context "$KUBE_CONTEXT" apply -f opentelemetry-operator.yaml
```
### CR de Instrumentation

El recurso y la aplicación de ejemplo están en `ecommerce`. El Operator fijado proporciona sus imágenes de instrumentación predeterminadas versionadas; inspecciona las imágenes inyectadas y no las sustituyas todas por `latest`. Sus valores predeterminados para Java y Python no son las versiones instaladas directamente más arriba. Usa una sola vía de instrumentación por proceso. Los montajes de Secrets TLS siguen siendo responsabilidad de la aplicación.


```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: otel-instrumentation
  namespace: ecommerce
spec:
  exporter:
    endpoint: https://otel-collector.otel.svc.cluster.local:4318
  propagators:
  - tracecontext
  - baggage
  sampler:
    type: parentbased_always_on
  env:
  - name: OTEL_RESOURCE_ATTRIBUTES
    value: service.namespace=ecommerce,deployment.environment.name=demo
  - name: OTEL_EXPORTER_OTLP_PROTOCOL
    value: http/protobuf
  - name: OTEL_EXPORTER_OTLP_CERTIFICATE
    value: /var/run/otel-client/ca.crt
  - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
    value: /var/run/otel-client/tls.crt
  - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
    value: /var/run/otel-client/tls.key
  - name: OTEL_TRACES_EXPORTER
    value: otlp
  - name: OTEL_METRICS_EXPORTER
    value: otlp
  - name: OTEL_LOGS_EXPORTER
    value: none
  - name: OTEL_METRIC_EXPORT_INTERVAL
    value: '60000'
```
Aquí se seleccionan W3C Trace Context y baggage. B3 es una opción de interoperabilidad cuando el paquete de propagador del lenguaje y los sistemas pares son compatibles. No incluyas credenciales ni datos personales en baggage; la propagación puede atravesar límites de servicio y confianza.

### Inyección de instrumentación automática

La anotación debe ir en la plantilla del Pod, no solo en los metadatos del Deployment. `otel-instrumentation` selecciona el recurso con nombre del espacio de nombres del Pod; `namespace/name` permite seleccionar explícitamente otro espacio de nombres. Existen anotaciones para todo el espacio de nombres, pero no habilites Java, Python y Node.js indiscriminadamente para todos los Pods. La inyección se realiza al admitir Pods nuevos, no de forma retroactiva en los que ya están en ejecución.


```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-injected
  namespace: ecommerce
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-injected
  template:
    metadata:
      labels:
        app: order-injected
      annotations:
        instrumentation.opentelemetry.io/inject-java: otel-instrumentation
    spec:
      automountServiceAccountToken: false
      securityContext:
        fsGroup: 10001
      containers:
      - name: app
        image: registry.example.com/order-injected:otel-demo
        env:
        - name: OTEL_SERVICE_NAME
          value: order-injected
        - name: OTEL_RESOURCE_ATTRIBUTES
          value: service.namespace=ecommerce,deployment.environment.name=demo
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: https://otel-collector.otel.svc.cluster.local:4318
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: http/protobuf
        - name: OTEL_EXPORTER_OTLP_CERTIFICATE
          value: /var/run/otel-client/ca.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE
          value: /var/run/otel-client/tls.crt
        - name: OTEL_EXPORTER_OTLP_CLIENT_KEY
          value: /var/run/otel-client/tls.key
        - name: OTEL_TRACES_EXPORTER
          value: otlp
        - name: OTEL_METRICS_EXPORTER
          value: otlp
        - name: OTEL_LOGS_EXPORTER
          value: none
        - name: OTEL_TRACES_SAMPLER
          value: parentbased_always_on
        - name: OTEL_METRIC_EXPORT_INTERVAL
          value: '60000'
        volumeMounts:
        - name: otel-client-tls
          mountPath: /var/run/otel-client
          readOnly: true
      volumes:
      - name: otel-client-tls
        secret:
          secretName: otel-client-tls
          defaultMode: 288
```
Java, Python, Node.js, .NET, Go, Apache HTTPD y Nginx tienen requisitos previos distintos. En esta versión, la instrumentación automática de Go necesita la ruta al ejecutable de destino e inyecta un componente con UID 0 privilegiado; no es una receta general para Restricted-PSS/Fargate. Verifica la configuración de funciones de Operator y la guía específica de cada lenguaje. Los valores predeterminados HTTP de Python/.NET/Go no deben apuntarse a un endpoint gRPC sin una configuración de protocolo compatible.

## Configuración de varios backends

Combina este fragmento con la configuración base revisada; no es independiente. Cada backend necesita su propio endpoint, confianza y autorización. AWS X-Ray usa la Región y la identidad de carga de trabajo configuradas; consulta la [guía de X-Ray](./02-xray.md) para conocer las relaciones de confianza y los permisos exactos de IAM. Deshabilitar la indexación de atributos no es enmascaramiento. El objeto api de Datadog se obtiene de un `api.yaml` gestionado mediante Secret y que contiene key (una cadena entre comillas) y site. Añade el montaje de solo lectura de ese Secret a la carga de trabajo; la carga de trabajo base no lo monta. No se coloca ninguna clave en variables de entorno. En esta auditoría no se ejecutó ninguna llamada a servicios de AWS, Datadog o Jaeger.


```yaml
exporters:
  awsxray:
    region: ap-northeast-2
    index_all_attributes: false
    telemetry:
      enabled: false
  datadog:
    api: ${file:/var/run/secrets/datadog/api.yaml}
  otlp_grpc/jaeger:
    endpoint: ${env:JAEGER_OTLP_GRPC_ENDPOINT}
    tls:
      ca_file: ${env:BACKEND_CA}
      cert_file: ${env:BACKEND_CLIENT_CERT}
      key_file: ${env:BACKEND_CLIENT_KEY}
service:
  pipelines:
    traces:
      exporters:
      - otlp_grpc/tempo
      - awsxray
      - datadog
      - otlp_grpc/jaeger
```
La distribución a varios backends no proporciona entregas atómicas ni una retención idéntica entre ellos.

### Actualización de julio de 2026: observación de un límite de red para el tráfico de agentes de IA

El [artículo de la CNCF del 8 de julio](https://www.cncf.io/blog/2026/07/08/network-boundary-for-ai-agents-using-nginx-and-opentelemetry/) informa de un prototipo de un solo nodo que usa NGINX y OTel. Su límite depende de reglas de red que bloquean rutas de salida alternativas, no solo de establecer una variable de proxy. Los fragmentos describen el tráfico visible para el proxy configurado; siguen siendo importantes la gestión de TLS, el muestreo, la retención de Collector y la seguridad del proxy. Esta es una capa de control de red y no demuestra que las decisiones de un agente sean correctas o seguras.

### Actualización de agosto de 2026: convertir consultas SQL lentas en métricas de fiabilidad

El [artículo de la CNCF del 21 de agosto](https://www.cncf.io/blog/2026/08/21/how-to-turn-slow-queries-into-actionable-reliability-metrics-with-opentelemetry/) y su [laboratorio](https://github.com/causely-oss/slow-query-lab) comparan la duración de las consultas, el impacto ponderado por el tráfico y las métricas derivadas de fragmentos con líneas de base de anomalías. Conserva los ejemplos históricos del artículo como ejemplos, no como mediciones de capacidad de tu clúster. El propio artículo advierte sobre el SQL sin procesar en etiquetas de métricas, los parámetros sensibles, la cardinalidad y el calentamiento de la línea de base. Desinfecta y acota las dimensiones antes de adoptar una configuración de laboratorio; una anomalía de latencia es un síntoma, no una prueba de la causa raíz.

### Actualización de octubre de 2026: reconstrucción de la detección de incidentes sobre flujos de OTel

En la [publicación de la CNCF del 30 de septiembre](https://www.cncf.io/blog/2026/09/30/from-40-seconds-to-under-10-rebuilding-incident-detection-on-opentelemetry-apache-kafka-and-apache-flink-on-kubernetes/), Atlassian describe dieciocho meses de trabajo para reconstruir su plataforma automatizada de creación de incidentes con OpenTelemetry, Apache Kafka y Apache Flink en Kubernetes, reduciendo la latencia de evento a métrica de más de 40 segundos a menos de 10. Como señala la propia publicación, la recuperación dentro del ámbito definido aumentó de alrededor del 60 % al 86 %, pero bajó al 64 % durante un mes desfavorable, y la precisión sigue por debajo del objetivo. Considera estas cifras mediciones de esa organización, no resultados garantizados por la arquitectura; lo más útil de la publicación es su análisis de compensaciones, por ejemplo, aislar vecinos ruidosos en colas compartidas y el coste.

## Prácticas recomendadas

### 1. Estandarizar los atributos de recursos

| Atributo | Ejemplo / origen |
|---|---|
| `service.name`, `service.version`, `service.namespace` | `order-service`, `1.2.3`, `ecommerce`; configuración de la aplicación |
| `deployment.environment.name` | `demo`; sustituye a `deployment.environment`, que está obsoleto |
| `cloud.provider`, `cloud.region`, `cloud.availability_zone` | Metadatos de implementación verificados, no conjeturas basadas en el host de Collector |
| `k8s.cluster.name`, `k8s.namespace.name`, `k8s.pod.name`, `k8s.deployment.name` | Enriquecimiento de Kubernetes configurado correctamente o metadatos de la carga de trabajo |

Este es un inventario de atributos, no YAML de procesador de Collector. Un Resource identifica al productor. Evita copiar todos los atributos de recursos a las etiquetas de métricas; los nombres de Pod, los ID de usuario y el texto de consultas sin procesar pueden causar una cardinalidad elevada. Los perfiles son otra señal en evolución; esta guía se centra en trazas, métricas y registros, sin afirmar que los SDK tengan una estabilidad uniforme.

### 2. Estrategia de muestreo

En un ejemplo avanzado (errores, latencia >2 segundos, una condición del 50 % para servicios críticos y una línea de base del 5 %), considera cada regla positiva una condición OR, no una prioridad de primera coincidencia ni una cuota reservada. Otra regla puede conservar una traza. Si necesitas clases exclusivas o un presupuesto de tasa de fragmentos, diseña y prueba esa política explícitamente. El muestreo inicial, los fragmentos descartados, los cambios de partición y las llegadas tardías siguen siendo limitaciones independientes.


```yaml
# Replace the base policies list; positive rules are OR conditions, not priorities.
processors:
  tail_sampling:
    policies:
    - name: errors
      type: status_code
      status_code:
        status_codes:
        - ERROR
    - name: slow
      type: latency
      latency:
        threshold_ms: 2000
    - name: critical-services
      type: and
      and:
        and_sub_policy:
        - name: service-name
          type: string_attribute
          string_attribute:
            key: service.name
            values:
            - payment-service
            - order-service
        - name: probabilistic
          type: probabilistic
          probabilistic:
            sampling_percentage: 50
    - name: default
      type: probabilistic
      probabilistic:
        sampling_percentage: 5
```
### 3. Consideraciones de seguridad

TLS de servidor sin `client_ca_file` no equivale a exigir certificados de cliente. Protege ambos sentidos, valida los nombres y el ciclo de vida de los certificados y restringe el acceso a Services, a la red y a los backends. El tráfico sin cifrar por loopback del mismo Pod en el ejemplo de sidecar corresponde a un límite de confianza distinto. La telemetría de navegador necesita su propio diseño de origen, autenticación y limitación de tasa, no CORS con comodín.

La acción `hash` del procesador de atributos usa SHA-1. Aplicar un hash a ID predecibles o texto SQL no es anonimización; siguen siendo posibles la recuperación mediante diccionario y la vinculación. Es preferible no recopilar valores sensibles y después eliminar explícitamente los campos identificados antes de la exportación. Revisa por separado los cuerpos de registros, los eventos de fragmentos y los atributos de recursos. Los exportadores de depuración detallada o los endpoints de creación de perfiles pueden exponer datos y deben usarse como diagnósticos temporales y controlados.

### Validación y límites

La validación local utilizó el Collector real 0.160.0 con tráfico OTLP sintético y endpoints de loopback con TLS mutuo, incluido el procesamiento de trazas y registros y las métricas de fragmentos previas al muestreo de cola. La comprobación de escritura remota confirmó la entrega HTTPS a un receptor de prueba, no un resultado de ingesta en una instancia activa de Prometheus. Los fragmentos manuales de Python utilizaron SDK 1.44.0 y un exportador en memoria. Se comprobaron los esquemas de Kubernetes/Instrumentation y la sintaxis de Node.js; no se ejecutaron el inicio de aplicaciones Java/Node, la inyección sin código, productos de backend reales, EKS, IAM ni el escalado automático.

### Referencias oficiales

- [Componentes de Collector 0.160.0](https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.160.0/distributions/otelcol-contrib/manifest.yaml)
- [Compatibilidad de Operator 0.158.0](https://github.com/open-telemetry/opentelemetry-operator/blob/v0.158.0/docs/getting-started/compatibility.md)
- [Instrumentación automática de Operator](https://github.com/open-telemetry/opentelemetry-operator/blob/v0.158.0/docs/auto-instrumentation/README.md)
- [Agente de Java 2.31.1](https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/tag/v2.31.1)
- [Configuración del exportador OTLP](https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/)
- [Escalado de Collector](https://opentelemetry.io/docs/collector/scaling/)
- [Muestreo de cola](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/processor/tailsamplingprocessor)
- [Conector de métricas de fragmentos](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.160.0/connector/spanmetricsconnector)
- [Limitador de memoria](https://github.com/open-telemetry/opentelemetry-collector/tree/v0.160.0/processor/memorylimiterprocessor)
- [OTLP nativo de Loki](https://grafana.com/docs/loki/latest/send-data/otel/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Sidecars nativos de Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [Ciclo de vida de Kubernetes en EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [Hitos de OpenTracing en la CNCF](https://www.cncf.io/projects/opentracing/)
- [Repositorio de OpenCensus Go](https://github.com/census-instrumentation/opencensus-go)

## Cuestionario

Pon a prueba tus conocimientos con el [Cuestionario de OpenTelemetry](../../quizzes/observability/tracing/03-opentelemetry-quiz.md).
