# Trazado distribuido de Istio

> **Versiones compatibles**: Istio 1.31
> **Última actualización**: September 11, 2026

> **Ámbito de validación**: Estas configuraciones de laboratorio se comprobaron con referencias oficiales y validadores sin conexión, sin desplegar un clúster. Cada ejemplo indica los supuestos de espacio de nombres, identidad, almacenamiento, backend y carga, que deben verificarse para el entorno de destino.

El trazado distribuido sigue y visualiza los flujos de solicitudes entre microservicios, lo que permite identificar cuellos de botella de latencia, analizar las causas de los errores y comprender las dependencias entre servicios.

## Índice

1. [Descripción general del trazado distribuido](#distributed-tracing-overview)
2. [Integración con OpenTelemetry](#opentelemetry-integration)
3. [Integración con Jaeger](#jaeger-integration)
4. [Integración con Zipkin](#zipkin-integration)
5. [Propagación del contexto](#context-propagation)
6. [Estrategias de muestreo](#sampling-strategies)
7. [Análisis de trazas](#trace-analysis)
8. [Añadir spans personalizados](#adding-custom-spans)
9. [Optimización del rendimiento](#performance-optimization)
10. [Solución de problemas](#troubleshooting)

## Descripción general del trazado distribuido {#distributed-tracing-overview}

### Contexto de trazas W3C

Istio admite el contexto de trazas W3C con proveedores de trazado compatibles. Las aplicaciones siguen teniendo que propagar el contexto entre sus propias solicitudes; los spans de aplicación del diagrama requieren un SDK o agente inicializado. Los ejemplos cubren sidecars/waypoints: ztunnel no genera spans de trazado HTTP.

![Diagrama de secuencia de una solicitud cliente que propaga el contexto de trazas W3C a través de sidecars Envoy y contenedores de aplicaciones en los Servicios A y B, mientras cada sidecar Envoy y aplicación exporta spans de forma asíncrona a Jaeger Collector.](../../../.gitbook/assets/en-service-mesh-istio-observability-02-tracing-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-observability-02-tracing-0.html)

### Conceptos básicos

#### Traza

Una colección de spans que representa la ruta completa de una única solicitud a través del sistema

#### Span

Una unidad que representa el inicio y el fin de una operación específica
- **ID de span**: identificador único
- **ID de span padre**: referencia al span padre
- **ID de traza**: identificador de toda la traza
- **Nombre de operación**: nombre de la operación (p. ej., `HTTP GET /api/products`)
- **Duración**: tiempo que tarda la operación
- **Etiquetas**: metadatos (nombre del servicio, estado HTTP, etc.)
- **Registros**: eventos con marca de tiempo

#### Baggage

Pares clave-valor de contexto propagados cuando la aplicación o el propagador admite baggage. Baggage no es automáticamente un atributo del span y no debe contener secretos.

## Integración con OpenTelemetry {#opentelemetry-integration}

OpenTelemetry proporciona instrumentación, protocolos y recopiladores; no es un backend de almacenamiento de trazas. Este ejemplo envía OTLP a un recopilador y después a Jaeger. Zipkin y Tempo son backends alternativos.

### 1. Instalar OpenTelemetry Collector

Cree el espacio de nombres `observability` y despliegue el backend Jaeger indicado más adelante antes de probar. Este ejemplo de recopilador tiene una sola réplica y mantiene en memoria el estado del muestreo al final. Un Service de Kubernetes simple que distribuye entre varios muestreadores al final no mantiene juntos todos los spans de una traza; el escalado en producción necesita enrutamiento basado en el ID de traza, planificación de capacidad y tratamiento de spans tardíos. El OTLP interno usa texto sin cifrar en este laboratorio: restrinja el acceso de red o configure TLS/mTLS para el despliegue. La extensión de estado y el listener de métricas internas están habilitados explícitamente.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: observability
data:
  config.yaml: |
    extensions:
      health_check:
        endpoint: 0.0.0.0:13133
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      memory_limiter:
        check_interval: 1s
        limit_mib: 1024
      resource:
        attributes:
        - key: k8s.cluster.name
          value: production-k8s
          action: upsert
        - key: deployment.environment.name
          value: production
          action: upsert
      filter/health:
        error_mode: ignore
        trace_conditions:
        - span.name == "/health" or span.name == "/readiness" or span.name == "/liveness"
      tail_sampling:
        decision_wait: 30s
        num_traces: 50000
        policies:
        - name: errors
          type: status_code
          status_code:
            status_codes:
            - ERROR
        - name: slow
          type: latency
          latency:
            threshold_ms: 1000
        - name: baseline
          type: probabilistic
          probabilistic:
            sampling_percentage: 10
      batch:
        timeout: 10s
        send_batch_size: 1024
        send_batch_max_size: 2048
    exporters:
      otlp_grpc/jaeger:
        endpoint: jaeger-collector.observability.svc.cluster.local:4317
        tls:
          insecure: true
      debug:
        verbosity: basic
    service:
      extensions:
      - health_check
      pipelines:
        traces:
          receivers:
          - otlp
          processors:
          - memory_limiter
          - resource
          - filter/health
          - tail_sampling
          - batch
          exporters:
          - otlp_grpc/jaeger
          - debug
      telemetry:
        logs:
          level: info
        metrics:
          readers:
          - pull:
              exporter:
                prometheus:
                  host: 0.0.0.0
                  port: 8888
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-contrib:0.160.0
        args:
        - --config=/etc/otel/config.yaml
        ports:
        - containerPort: 4317
          name: otlp-grpc
          protocol: TCP
        - containerPort: 4318
          name: otlp-http
          protocol: TCP
        - containerPort: 8888
          name: metrics
          protocol: TCP
        - containerPort: 13133
          name: health
        volumeMounts:
        - name: config
          mountPath: /etc/otel
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /
            port: 13133
        readinessProbe:
          httpGet:
            path: /
            port: 13133
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
  namespace: observability
  labels:
    app: otel-collector
spec:
  selector:
    app: otel-collector
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: 4317
  - name: otlp-http
    port: 4318
    targetPort: 4318
  - name: metrics
    port: 8888
    targetPort: 8888
  type: ClusterIP
```

El exportador retirado `jaeger` se sustituye por OTLP/gRPC y `logging` por `debug`. El filtro coincide con nombres exactos de spans observados; ajústelo a la instrumentación y tenga en cuenta cómo descartar spans afecta a la integridad de las trazas. Las políticas de muestreo al final conservan las trazas aptas que realmente llegan; no pueden recuperar spans descartados antes. Elimine la exportación de diagnóstico después de verificar.

### 2. Habilitar OpenTelemetry en Istio

#### Configuración de MeshConfig

Combine este proveedor con los ajustes de instalación existentes mediante `istioctl install -f`; no sobrescriba todo el ConfigMap `istio`. `maxTagLength` limita la etiqueta de ruta, no todos los atributos de los spans.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel-tracing
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
        maxTagLength: 256
```

#### Habilitar el trazado con la API Telemetry

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: otel-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 100.0
    customTags:
      cluster_id:
        literal:
          value: "production-cluster"
      environment:
        literal:
          value: "production"
```

Utilice un único recurso Telemetry aplicable sin selector por espacio de nombres; combine los ajustes de trazado y registro en vez de aplicar ejemplos incompatibles. Las etiquetas de cabecera son metadatos de solicitud no confiables, no identidad autenticada. Utilice únicamente valores seudónimos aprobados para correlacionar usuarios. Las etiquetas de entorno leen el entorno del proxy, no las variables de entorno de la aplicación.

### 3. Configuración del trazado por espacio de nombres

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: namespace-tracing
  namespace: production
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 100.0
    customTags:
      namespace:
        literal:
          value: "production"
      team:
        literal:
          value: "backend-team"
      # Add request headers as tags
      user_id:
        header:
          name: x-user-id
          defaultValue: "unknown"
      request_id:
        header:
          name: x-request-id
      # Add environment variables as tags
      pod_name:
        environment:
          name: POD_NAME
          defaultValue: "unknown"
```

## Integración con Jaeger {#jaeger-integration}

### Despliegue de Jaeger 2 para desarrollo

Jaeger 2 utiliza la imagen `jaegertracing/jaeger` con un archivo de configuración explícito. La siguiente instancia respaldada por memoria es para desarrollo; reiniciarla pierde las trazas. Los endpoints de consulta y OTLP permanecen dentro del clúster; utilice reenvío de puertos para acceder a la interfaz.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jaeger-config
  namespace: observability
data:
  config.yaml: |
    extensions:
      jaeger_storage:
        backends:
          traces:
            memory:
              max_traces: 50000
      jaeger_query:
        storage:
          traces: traces
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      batch: {}
    exporters:
      jaeger_storage_exporter:
        trace_storage: traces
    service:
      extensions:
      - jaeger_storage
      - jaeger_query
      pipelines:
        traces:
          receivers:
          - otlp
          processors:
          - batch
          exporters:
          - jaeger_storage_exporter
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/jaeger:2.20.0
        args:
        - --config=/etc/jaeger/config.yaml
        ports:
        - containerPort: 4317
          name: otlp-grpc
        - containerPort: 4318
          name: otlp-http
        - containerPort: 16686
          name: query-http
        volumeMounts:
        - name: config
          mountPath: /etc/jaeger
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
      volumes:
      - name: config
        configMap:
          name: jaeger-config
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger-collector
  namespace: observability
spec:
  selector:
    app: jaeger
  ports:
  - name: otlp-grpc
    port: 4317
    targetPort: otlp-grpc
  - name: otlp-http
    port: 4318
    targetPort: otlp-http
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger-query
  namespace: observability
spec:
  selector:
    app: jaeger
  ports:
  - name: query-http
    port: 16686
    targetPort: query-http
  type: ClusterIP
```

### Almacenamiento y escalado en producción

Para almacenamiento duradero, utilice un despliegue gestionado y compatible de Elasticsearch/OpenSearch y el controlador de almacenamiento correspondiente de Jaeger. La matriz publicada de Elasticsearch de Jaeger 2.20 enumera **7.x/8.x**; no deduzca compatibilidad con una versión principal más reciente de Elasticsearch a partir de su última versión. Los despliegues ECK existentes también requieren comprobar la compatibilidad del operador/clúster; el almacenamiento `gp3` de EKS requiere el controlador EBS CSI y un StorageClass real.

Para Elasticsearch, sustituya el backend en memoria de `jaeger-config` por este fragmento; conserve los ajustes de receptor, exportador, consultas y canalización usando el nombre de almacenamiento `traces`. Cree el Secret `jaeger-es-client` con `password` para un usuario `jaeger` restringido y el `ca.crt` público que corresponda al certificado del servidor. La verificación del nombre del host del servidor permanece habilitada.

```yaml
extensions:
  jaeger_storage:
    backends:
      traces:
        elasticsearch:
          server_urls:
          - https://jaeger-es-es-http.observability.svc.cluster.local:9200
          auth:
            basic:
              username: jaeger
              password_file: /etc/jaeger/es/password
          tls:
            ca_file: /etc/jaeger/es/ca.crt
          indices:
            index_prefix: production
```

Combine el siguiente fragmento de Deployment con el Deployment `jaeger` existente (conserve la imagen, los argumentos, el montaje de configuración y los demás campos). Con almacenamiento duradero compartido, estas instancias combinadas de recopilación/consulta no tienen estado y pueden ejecutarse como réplicas. Se pueden configurar funciones independientes de recopilación/consulta con el mismo binario de Jaeger 2 cuando se necesite escalado independiente.

```yaml
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: jaeger
        volumeMounts:
        - name: es-client
          mountPath: /etc/jaeger/es
          readOnly: true
      volumes:
      - name: es-client
        secret:
          secretName: jaeger-es-client
```

Configure la inicialización del almacenamiento, la rotación/retención de índices, las copias de seguridad y los permisos del almacenamiento mediante la [guía de Jaeger para Elasticsearch](https://www.jaegertracing.io/docs/2.20/storage/elasticsearch/) y el esquema publicado. El antiguo despliegue con variables de entorno/imágenes de 1.x no es una configuración de Jaeger 2. Revise las notas de la versión antes de migrar las trazas almacenadas existentes.

### Alternativa OTLP directa de Istio → Jaeger

Esta opción omite el recopilador independiente y, por tanto, sus políticas de muestreo al final. Utilice un muestreo al inicio adecuado para la carga de trabajo. Es una selección alternativa de proveedor: combínela con la instalación existente y seleccione únicamente el proveedor previsto en el recurso Telemetry aplicable.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: jaeger
      opentelemetry:
        service: jaeger-collector.observability.svc.cluster.local
        port: 4317
        maxTagLength: 256
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: jaeger-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: jaeger
    randomSamplingPercentage: 1
```

## Integración con Zipkin {#zipkin-integration}

### Despliegue de Zipkin para desarrollo

Esta alternativa utiliza Zipkin 3.6.1 con almacenamiento en memoria para pruebas; pierde los datos al reiniciarse. La producción necesita un backend de almacenamiento persistente compatible, autenticación/TLS y acceso de red configurado. Seleccione un backend mediante la [configuración del servidor de Zipkin](https://github.com/openzipkin/zipkin/blob/3.6.1/zipkin-server/README.md); no lo dirija a un `elasticsearch:9200` sin desplegar.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zipkin
  namespace: observability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: zipkin
  template:
    metadata:
      labels:
        app: zipkin
      annotations:
        sidecar.istio.io/inject: 'false'
    spec:
      containers:
      - name: zipkin
        image: openzipkin/zipkin:3.6.1
        ports:
        - containerPort: 9411
          name: http
        env:
        - name: STORAGE_TYPE
          value: mem
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: zipkin
  namespace: observability
spec:
  selector:
    app: zipkin
  ports:
  - name: http
    port: 9411
    targetPort: http
  type: ClusterIP
```

### Configurar el proveedor de Istio

El proveedor debe existir antes de que Telemetry pueda referenciarlo. Combine esta entrada de instalación y utilice este Telemetry como alternativa a la selección de recopilador/Jaeger.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: zipkin
      zipkin:
        service: zipkin.observability.svc.cluster.local
        port: 9411
        maxTagLength: 256
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: zipkin-tracing
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: zipkin
    randomSamplingPercentage: 1
```

## Propagación del contexto {#context-propagation}

La clave del trazado distribuido es propagar correctamente el contexto de la traza entre servicios.

### Cabeceras HTTP requeridas

Propague el formato configurado para el proxy/backend; W3C y B3 son alternativas o una propagación multiformato configurada explícitamente. Reenvíe también `x-request-id`. B3 sigue siendo compatible; no debe habilitarse indiscriminadamente la opción de depuración `X-B3-Flags: 1`.

#### Contexto de trazas W3C (recomendado)

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
tracestate: congo=t61rcWkgMzE
```

#### Cabeceras B3

**Formato de una sola cabecera (recomendado)**:
```
b3: 80f198ee56343ba864fe8b2a57d3eff7-e457b5a2e4d86bd1-1-05e3ac9a4f6e3b90
```

**Formato de varias cabeceras**:
```
X-B3-TraceId: 80f198ee56343ba864fe8b2a57d3eff7
X-B3-SpanId: e457b5a2e4d86bd1
X-B3-ParentSpanId: 05e3ac9a4f6e3b90
X-B3-Sampled: 1
```

### Propagación del contexto por aplicación

Los siguientes ejemplos presuponen un recopilador existente y un endpoint `service-b:8080/api/service-b`. Instale dependencias compatibles de API/SDK/exportador/instrumentación e inicialice el SDK **antes de atender solicitudes**. Estos endpoints de laboratorio utilizan OTLP sin cifrar dentro del clúster; configure TLS/mTLS confiables y restricciones de red para el despliegue real. La instrumentación automática del SDK y la propagación manual no deben crear spans de cliente duplicados. Conserve `x-request-id` por separado para la correlación de solicitudes de Istio.

#### Python (Flask + OpenTelemetry)

Instale Flask, requests, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-flask` y `opentelemetry-instrumentation-requests` en el entorno de la aplicación. La instrumentación de Flask/requests gestiona la extracción y la inyección; para propagación manual, la API es `opentelemetry.propagate.extract`, no la importación original mal formada.

```python
import atexit
import requests
from flask import Flask, request
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

provider = TracerProvider(resource=Resource.create({"service.name": "service-a"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(
    endpoint="otel-collector.observability.svc.cluster.local:4317", insecure=True
)))
trace.set_tracer_provider(provider)
set_global_textmap(TraceContextTextMapPropagator())
atexit.register(provider.shutdown)
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
tracer = trace.get_tracer(__name__)

@app.get("/api/service-a")
def service_a():
    # Flask instrumentation extracted the parent; requests instrumentation injects its child.
    with tracer.start_as_current_span("process-request"):
        headers = {}
        if request.headers.get("x-request-id"):
            headers["x-request-id"] = request.headers["x-request-id"]
        response = requests.get("http://service-b:8080/api/service-b",
                                headers=headers, timeout=3)
        response.raise_for_status()
        return response.text, response.status_code, {
            "Content-Type": response.headers.get("Content-Type", "text/plain")
        }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

El servidor de desarrollo de Flask es solo para pruebas locales; despliegue con el servidor de producción de la aplicación y el ciclo de vida de cierre del SDK.

#### Go (Gin + OpenTelemetry)

Inicialice un proveedor de trazado real y un propagador W3C. Utilice el contexto devuelto por `Start` para la solicitud descendente, gestione los errores y cierre el cuerpo de la respuesta. Añada los módulos importados al `go.mod` de la aplicación; no descarte los valores de retorno de contexto/error.

```go
package main

import (
	"context"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func main() {
	exporter, err := otlptracegrpc.New(context.Background(),
		otlptracegrpc.WithEndpoint("otel-collector.observability.svc.cluster.local:4317"),
		otlptracegrpc.WithInsecure())
	if err != nil {
		log.Fatal(err)
	}
	provider := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(resource.NewSchemaless(attribute.String("service.name", "service-a"))))
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.TraceContext{})
	defer func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := provider.Shutdown(ctx); err != nil {
			log.Print(err)
		}
	}()
	client := &http.Client{Transport: otelhttp.NewTransport(http.DefaultTransport), Timeout: 3 * time.Second}
	router := gin.Default()
	router.Use(otelgin.Middleware("service-a"))
	router.GET("/api/service-a", func(c *gin.Context) {
		ctx, span := otel.Tracer("service-a").Start(c.Request.Context(), "process-request")
		defer span.End()
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, "http://service-b:8080/api/service-b", nil)
		if err != nil {
			c.Status(http.StatusInternalServerError)
			return
		}
		if id := c.GetHeader("x-request-id"); id != "" {
			req.Header.Set("x-request-id", id)
		}
		resp, err := client.Do(req)
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, "downstream request failed")
			c.Status(http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()
		// Bound this demonstration response to 1 MiB.
		body, err := io.ReadAll(io.LimitReader(resp.Body, (1<<20)+1))
		if err != nil || len(body) > 1<<20 {
			c.Status(http.StatusBadGateway)
			return
		}
		c.Data(resp.StatusCode, resp.Header.Get("Content-Type"), body)
	})
	if err := router.Run(":8080"); err != nil {
		log.Print(err)
	}
}
```

#### Java (Spring WebFlux + agente Java de OpenTelemetry)

Inicie la aplicación Spring WebFlux con un agente Java de OpenTelemetry compatible y un endpoint OTLP. El agente instrumenta el ciclo de vida reactivo del servidor/cliente y la propagación del contexto. Un `try (Scope ...) { return Mono... } finally { span.end(); }` termina un span antes de que finalice la suscripción y es incorrecto para trabajo asíncrono. Este controlador se basa en la instrumentación WebFlux/Reactor compatible del agente:

```bash
OTEL_SERVICE_NAME=service-a \
OTEL_EXPORTER_OTLP_PROTOCOL=grpc \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317 \
java -javaagent:/opt/otel/opentelemetry-javaagent.jar -jar app.jar
```

```java
import java.time.Duration;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

@RestController
public class ServiceAController {
    private final WebClient webClient;
    public ServiceAController(WebClient.Builder builder) {
        this.webClient = builder.baseUrl("http://service-b:8080").build();
    }

    @GetMapping("/api/service-a")
    public Mono<String> serviceA(@RequestHeader(value = "x-request-id", required = false) String requestId) {
        return webClient.get().uri("/api/service-b")
                .headers(headers -> { if (requestId != null) headers.set("x-request-id", requestId); })
                .retrieve().bodyToMono(String.class)
                .timeout(Duration.ofSeconds(3));
    }
}
```

#### Node.js (CommonJS Express + OpenTelemetry)

Instale `express`, `axios`, `@opentelemetry/api`, `@opentelemetry/sdk-node`, `@opentelemetry/auto-instrumentations-node` y `@opentelemetry/exporter-trace-otlp-grpc`. Cargue la instrumentación antes de las importaciones de la aplicación; importar la API por sí solo no configura un SDK ni un exportador.

```javascript
// instrumentation.cjs: load before Express, HTTP clients, or application modules.
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter(),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
process.once('SIGTERM', () => sdk.shutdown().finally(() => process.exit(0)));
```

```javascript
// app.cjs
const express = require('express');
const axios = require('axios');
const { trace, SpanStatusCode } = require('@opentelemetry/api');
const app = express();
const tracer = trace.getTracer('service-a');
app.get('/api/service-a', async (req, res) => {
  await tracer.startActiveSpan('process-request', async (span) => {
    try {
      const headers = {};
      if (req.headers['x-request-id']) headers['x-request-id'] = req.headers['x-request-id'];
      const response = await axios.get('http://service-b:8080/api/service-b', {headers, timeout: 3000});
      res.json({result: response.data});
    } catch (error) {
      span.recordException(error);
      span.setStatus({code: SpanStatusCode.ERROR});
      res.status(502).json({error: 'Downstream request failed'});
    } finally {
      span.end();
    }
  });
});
app.listen(8080);
```

```bash
OTEL_SERVICE_NAME=service-a \
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.observability.svc.cluster.local:4317 \
node --require ./instrumentation.cjs app.cjs
```

### Verificación del contexto de trazas

Verifique que una solicitud de prueba produce spans con el mismo ID de traza y las relaciones padre-hijo previstas en el backend. Inspeccione las cabeceras entrantes y salientes en una prueba controlada de la aplicación. Los registros de acceso predeterminados de Envoy no incluyen todas las cabeceras de trazas; habilitar el registro de depuración del proxy no habilita los registros de acceso ni garantiza la salida de cabeceras. Configure explícitamente el formato del registro de acceso si necesita cabeceras y evite registrar credenciales/baggage.

```bash
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("tracing")) | .tracing'
istioctl proxy-config clusters <pod-name> -n <namespace> \
  --fqdn otel-collector.observability.svc.cluster.local
kubectl logs -n observability deployment/otel-collector --tail=100
```

## Estrategias de muestreo {#sampling-strategies}

### Niveles de muestreo

#### 1. Muestreo al inicio (muestreo inicial)

El muestreo al inicio decide pronto. Los porcentajes siguientes son alternativas; las decisiones de muestreo anteriores y los muestreadores del SDK también afectan a qué spans llegan. Si el recopilador debe evaluar cada traza en busca de errores/latencia, envíele todos los spans aptos en vez de descartar el 90% antes del muestreo al final.

**Nivel de toda la malla**:
```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: mesh-head-sampling
  namespace: istio-system
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 10.0
```

**Nivel de espacio de nombres**:
```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: sampling-config
  namespace: production
spec:
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 25.0  # 25% sampling
```

**Nivel de carga de trabajo**:
```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: critical-service-tracing
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 100.0  # 100% sampling for critical services
```

#### 2. Muestreo al final (muestreo posterior)

El muestreo al final decide a partir de los spans acumulados durante su ventana de decisión, no de una traza cuya integridad esté garantizada. Dimensione la ventana y los búferes para la duración/volumen esperados, dirija una traza al mismo recopilador y tenga en cuenta los spans tardíos, reinicios y desbordamientos. Las políticas siguientes conservan las trazas coincidentes que llegan al recopilador. Combine este procesador con la canalización de trazas antes del procesador de lotes.

```yaml
# OpenTelemetry Collector's tail_sampling processor
processors:
  tail_sampling:
    decision_wait: 10s  # Wait time for trace completion
    num_traces: 100000  # Number of traces to keep in memory
    expected_new_traces_per_sec: 1000
    policies:
      # Keep all traces with errors
      - name: errors
        type: status_code
        status_code:
          status_codes: [ERROR]

      # Keep all slow requests (> 1 second)
      - name: slow-traces
        type: latency
        latency:
          threshold_ms: 1000

      # 100% sampling for specific services
      - name: critical-services
        type: string_attribute
        string_attribute:
          key: service.name
          values:
          - payment-service
          - auth-service

      # Keep all HTTP 5xx errors
      - name: http-errors
        type: numeric_attribute
        numeric_attribute:
          key: http.response.status_code
          min_value: 500
          max_value: 599
      - name: legacy-http-errors
        type: numeric_attribute
        numeric_attribute:
          key: http.status_code
          min_value: 500
          max_value: 599

      # 5% sampling for the rest
      - name: probabilistic
        type: probabilistic
        probabilistic:
          sampling_percentage: 5
```

### Muestreo con limitación de tasa

La política de limitación de tasa es un depósito de tokens basado en la tasa de spans, no un muestreador de errores/latencia que se ajuste solo. Esta es una lista de políticas alternativa; añadirla junto a otras políticas de conservación no impone un límite global a las trazas que esas políticas conservan. Las ráfagas y las decisiones sobre trazas completas afectan a los intervalos cortos.

```yaml
processors:
  tail_sampling:
    policies:
      - name: rate-limited-sampling
        type: rate_limiting
        rate_limiting:
          spans_per_second: 1000  # Keep maximum 1000 spans per second
```

### Guía de estrategias de muestreo

| Objetivo | Entrada del muestreo al inicio | Decisión del recopilador/almacenamiento |
|------|------------|----------------------------|
| Prueba pequeña de desarrollo | 100% | Conservar todo y verificar la propagación |
| Volumen acotado en producción | Porcentaje medido | Almacenar las muestras recibidas |
| Conservar errores/trazas lentas | Todos los spans aptos | Las políticas al final conservan las trazas coincidentes más una base |
| Limitar el volumen conservado | Todos los spans aptos para las decisiones al final | Política explícita de tasa/compuesta y límites de capacidad |

Son decisiones de diseño, no valores predeterminados universales por entorno. Un muestreo al inicio bajo combinado con muestreo al final no puede garantizar la conservación de todos los errores. Compruebe el estado real de los spans y los nombres de atributos (`http.response.status_code` para las convenciones actuales de OpenTelemetry, `http.status_code` para algunos spans de proxy/antiguos).

## Análisis de trazas {#trace-analysis}

### Buscar trazas en la interfaz de Jaeger

```bash
# Access Jaeger UI
kubectl port-forward -n observability svc/jaeger-query 16686:16686

# Browser: http://localhost:16686
```

**Opciones de búsqueda**:
- **Servicio**: nombre del servicio
- **Operación**: nombre de la operación (p. ej., `GET /api/products`)
- **Etiquetas**: filtro de etiquetas (p. ej., `http.status_code=500`)
- **Duración mínima**: latencia mínima
- **Duración máxima**: latencia máxima
- **Límite de resultados**: límite del número de resultados

### Consultas útiles de trazas

#### 1. Encontrar trazas con errores

```
Tags: error=true
```

O

```
Tags: http.status_code=500
```

#### 2. Encontrar solicitudes lentas

```
Min Duration: 1s
```

#### 3. Seguir solicitudes de un usuario específico

```
Tags: user_id=12345
```

#### 4. Analizar endpoints de API específicos

```
Operation: GET /api/products/{id}
```

### Diagnóstico con la API de la interfaz de Jaeger

Tras el reenvío de puertos anterior, estos endpoints de consulta de la interfaz ayudan al diagnóstico interactivo. Son API internas de la interfaz, no un contrato estable para aplicaciones; utilice las API de consulta documentadas de Jaeger para integraciones duraderas.

```bash
# Query traces for a specific service
curl "http://localhost:16686/api/traces?service=productpage&limit=10"

# Query specific trace ID
curl "http://localhost:16686/api/traces/0af7651916cd43dd8448eb211c80319c"

# Query service list
curl "http://localhost:16686/api/services"

# Query operations for a specific service
curl "http://localhost:16686/api/services/productpage/operations"
```

### Identificar cuellos de botella de latencia

1. **Inspeccione la cascada y el tiempo exclusivo**: los spans padre incluyen el tiempo de los hijos; el padre más largo por sí solo no localiza el cuello de botella.
2. **Compruebe la ruta crítica**: la ruta que más afecta al tiempo total de la solicitud
3. **Ejecución paralela frente a secuencial**: compruebe si las tareas que podrían ejecutarse en paralelo se ejecutan secuencialmente

### Integración con Grafana Tempo

Tempo es un backend de trazas alternativo. Su puerto HTTP de **consulta** predeterminado es 3200; la ingesta OTLP utiliza receptores configurados independientes, como 4317. Monte el siguiente archivo en el directorio `provisioning/datasources` de Grafana (o configure el aprovisionamiento de fuentes de datos del chart). Un ConfigMap por sí solo no se carga automáticamente.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: observability
data:
  tempo.yaml: |
    apiVersion: 1
    datasources:
    - name: Tempo
      uid: tempo
      type: tempo
      access: proxy
      url: http://tempo.observability.svc.cluster.local:3200
      jsonData:
        tracesToLogsV2:
          datasourceUid: loki
          tags:
          - key: service.name
            value: app
          filterByTraceID: false
          filterBySpanID: false
        tracesToMetrics:
          datasourceUid: prometheus
          tags:
          - key: service.name
            value: destination_canonical_service
          queries:
          - name: Request rate
            query: sum(rate(istio_requests_total{reporter="destination",$$__tags}[5m]))
        nodeGraph:
          enabled: true
```

El ejemplo requiere los UID de fuentes de datos existentes `loki` y `prometheus`. Alinee `service.name` del SDK, `app` de Loki y `destination_canonical_service` de Istio; si los valores reales difieren, cambie las correspondencias. Añada correspondencias de espacio de nombres/clúster cuando coincidan nombres de servicios. El aprovisionamiento de Grafana convierte `$$__tags` en la variable de consulta literal `$__tags`. Habilite el filtrado por ID de traza solo cuando los registros contengan ese ID. Un gráfico de servicios de Tempo requiere además métricas de gráficos de servicios/spans generadas en Prometheus; las métricas de solicitudes ordinarias de Istio por sí solas no proporcionan esas series.

## Añadir spans personalizados {#adding-custom-spans}

Añada spans personalizados al código de la aplicación para un trazado más detallado.

### Ejemplo de Python

Esta función pertenece a una aplicación inicializada; `check_inventory`, `process_payment` y `PaymentError` son funciones de devolución de llamada/tipos definidos por la aplicación.

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)

def process_order(order_id):
    with tracer.start_as_current_span("process-order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.amount", 99.99)

        # Check inventory
        with tracer.start_as_current_span("check-inventory") as inventory_span:
            inventory = check_inventory(order_id)
            inventory_span.set_attribute("inventory.available", inventory)

        # Process payment
        with tracer.start_as_current_span("process-payment", record_exception=False,
                                          set_status_on_exception=False) as payment_span:
            try:
                payment_result = process_payment(order_id)
                payment_span.set_attribute("payment.status", "success")
            except PaymentError as e:
                payment_span.set_status(Status(StatusCode.ERROR))
                payment_span.record_exception(e)
                raise

        # Record event
        span.add_event("Order processed successfully", {
            "order.id": order_id
        })

        return {"status": "success"}
```

### Ejemplo de Go

Esta función es un fragmento de aplicación; `checkInventory` y `processPayment` son funciones de la aplicación. Ambos spans hijos utilizan el contexto del proceso padre, para que el pago no quede accidentalmente como hijo de un span de inventario ya terminado.

```go
import (
    "context"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/codes"
)

func processOrder(ctx context.Context, orderID string) error {
    tracer := otel.Tracer("order-service")

    ctx, span := tracer.Start(ctx, "process-order")
    defer span.End()

    span.SetAttributes(
        attribute.String("order.id", orderID),
        attribute.Float64("order.amount", 99.99),
    )

    // Check inventory
    inventoryCtx, inventorySpan := tracer.Start(ctx, "check-inventory")
    inventory, err := checkInventory(inventoryCtx, orderID)
    if err != nil {
        inventorySpan.RecordError(err)
        inventorySpan.SetStatus(codes.Error, err.Error())
        inventorySpan.End()
        return err
    }
    inventorySpan.SetAttributes(attribute.Bool("inventory.available", inventory))
    inventorySpan.End()

    // Process payment
    paymentCtx, paymentSpan := tracer.Start(ctx, "process-payment")
    err = processPayment(paymentCtx, orderID)
    if err != nil {
        paymentSpan.RecordError(err)
        paymentSpan.SetStatus(codes.Error, err.Error())
        paymentSpan.End()
        return err
    }
    paymentSpan.SetAttributes(attribute.String("payment.status", "success"))
    paymentSpan.End()

    // Record event
    span.AddEvent("Order processed successfully")

    return nil
}
```

## Optimización del rendimiento {#performance-optimization}

### Optimización del tamaño de los datos de trazas

Utilice el `maxTagLength` del proveedor y las etiquetas personalizadas de Telemetry ya mostradas. Limite los atributos/eventos en el SDK/recopilador cuando corresponda; truncar una ruta no oculta los secretos de una URL o etiqueta. Almacene únicamente los atributos necesarios y utilice plantillas de rutas en lugar de identificadores sin procesar cuando sea posible.

### Ajuste del rendimiento del recopilador

```yaml
processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
    send_batch_max_size: 2048

  memory_limiter:
    check_interval: 1s
    limit_mib: 1024
    spike_limit_mib: 256
```

### Optimización del almacenamiento

Para el despliegue persistente de Jaeger, configure una política de retención para el prefijo de índice real `production` y el modo de rotación elegido. Dimensione los fragmentos/réplicas según la carga medida de ingesta y consultas. Utilice la inicialización de índices compatible con la versión de Jaeger y Elasticsearch ILM (o el mecanismo de ciclo de vida del backend de almacenamiento), y verifique las copias de seguridad y el período retrospectivo de consultas antes de hacer caducar los datos. Siete días es una decisión de retención de ejemplo, no un valor predeterminado universal.

La antigua receta independiente de Curator no coincidía con el prefijo de índice configurado y omitía credenciales/TLS de almacenamiento y requisitos de rotación. Siga el [procedimiento de ciclo de vida del almacenamiento de Jaeger 2.20](https://www.jaegertracing.io/docs/2.20/storage/elasticsearch/) y el esquema publicado; no ejecute comandos amplios de eliminación de índices para diagnosticar trazas.

## Solución de problemas {#troubleshooting}

### Faltan trazas

Compruebe la configuración efectiva de trazado del gestor de conexiones HTTP y el clúster del proveedor, y luego distinga entre recepción, exportación y almacenamiento en el backend. Comprobar únicamente `.bootstrap.tracing` pasa por alto el trazado configurado dinámicamente. Utilice estas comprobaciones de solo lectura:

```bash
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("tracing")) | .tracing'
istioctl proxy-config clusters <pod-name> -n <namespace> \
  --fqdn otel-collector.observability.svc.cluster.local
kubectl logs -n observability deployment/otel-collector --tail=100
kubectl logs -n observability deployment/jaeger --tail=100
# Keep this running; use a second terminal for the curl command below.
kubectl port-forward -n observability svc/otel-collector 8888:8888
```

```bash
curl -fsS http://localhost:8888/metrics | \
  rg 'otelcol_(receiver_accepted|exporter_sent|exporter_send_failed)_spans'
```

Los spans aceptados no demuestran exportación ni almacenamiento duradero. Inspeccione los errores del exportador, la conectividad/autenticación del backend y los ID de trazas almacenadas. El muestreo al final y el almacenamiento en memoria reducen deliberadamente los datos conservados. Los sufijos de métricas pueden variar con la configuración de telemetría del recopilador.

### Propagación de contexto interrumpida

Utilice un ID de traza de prueba nuevo para cada solicitud independiente e inspeccione los spans de aplicación/servidor en el backend. La aplicación debe inyectar el contexto hijo activo al realizar una nueva llamada saliente. Compruebe que los formatos W3C/B3 coincidan con el proveedor y los propagadores del SDK configurados, y que la instrumentación se inicie antes de cargar las bibliotecas HTTP. Cambiar el nivel de registro del proxy no habilita el registro de acceso; configure explícitamente un proveedor de registros de acceso de Telemetry cuando sea necesario.

### Muestreo inesperado

```bash
kubectl get telemetry -A
kubectl describe telemetry <name> -n <namespace>
istioctl analyze -n <namespace>
istioctl proxy-config listeners <pod-name> -n <namespace> -o json | \
  jq '.. | objects | select(has("tracing")) | .tracing'
```

Revise conjuntamente la herencia de políticas raíz/espacio de nombres/carga de trabajo, las marcas de muestreo anteriores, el muestreador del SDK y la política del recopilador. Un recopilador no puede reconstruir una traza descartada por el muestreo al inicio.

## Referencias

- [Trazado distribuido de Istio](https://istio.io/latest/docs/tasks/observability/distributed-tracing/)
- [Documentación de OpenTelemetry](https://opentelemetry.io/docs/)
- [Documentación de Jaeger](https://www.jaegertracing.io/docs/)
- [Documentación de Zipkin](https://zipkin.io/)
- [Contexto de trazas W3C](https://www.w3.org/TR/trace-context/)
- [Propagación B3](https://github.com/openzipkin/b3-propagation)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
