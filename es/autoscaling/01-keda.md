# KEDA (Kubernetes Event-driven Autoscaling)

> **Versión de ejemplo**: KEDA/Helm chart 2.21.0; consulta la matriz de Kubernetes probada más abajo.
> **Última actualización**: 16 de octubre de 2026

## Tabla de contenidos
- [Introducción](#introduction)
- [Arquitectura](#architecture)
- [Instalación y configuración](#installation-and-configuration)
- [Scalers](#scalers)
- [Escalado con métricas personalizadas](#custom-metric-scaling)
- [Escalado con métricas de Twitter](#twitter-metric-scaling)
- [Escalado con Google Calendar](#google-calendar-scaling)
- [Escalado con métricas de Istio](#istio-metric-scaling)
- [Escalado basado en Cron](#cron-based-scaling)
- [Integración con Amazon EKS](#integration-with-amazon-eks)
- [Prácticas recomendadas](#best-practices)
- [Solución de problemas](#troubleshooting)
- [Conclusión](#conclusion)

## Introducción {#introduction}

KEDA (Kubernetes Event-driven Autoscaling) es un proyecto de código abierto que permite el escalado automático basado en eventos de las aplicaciones de Kubernetes. KEDA amplía el Horizontal Pod Autoscaler (HPA) nativo de Kubernetes para permitir el escalado de cargas de trabajo en función de diversas fuentes de eventos y métricas, además del uso de CPU y memoria.

### Ventajas principales de KEDA

1. **Escalado basado en eventos**: escalado según diversas fuentes de eventos (colas de mensajes, bases de datos, flujos, etc.)
2. **Escalado a cero**: los activadores de eventos compatibles pueden activar una carga de trabajo inactiva; configura el mínimo, el umbral de activación y el periodo de espera para esa carga de trabajo.
3. **Compatibilidad con diversos Scalers**: más de 50 Scalers integrados y compatibilidad con Scalers personalizados
4. **Nativo de Kubernetes**: integración con el HPA existente de Kubernetes
5. **Independiente de la nube**: se ejecuta en distribuciones compatibles de Kubernetes que dispongan de las API, el acceso de red y la configuración de identidad necesarios.
6. **Modelo de implementación**: la instalación estándar incluye un operador, un servidor de API de métricas y webhooks de admisión.

### Comparación con los métodos de escalado existentes

| Característica | KEDA | Kubernetes HPA | Autoscaler del proveedor de nube |
|---------|------|----------------|---------------------------|
| Fuentes de métricas | Scalers de eventos integrados y externos | Métricas de recursos, personalizadas y externas mediante adaptadores adecuados | Depende del producto |
| Escalado a cero | Activadores y configuración compatibles | Depende de la versión y las funciones; la compatibilidad con métricas de objeto/externas permite escalar a cero en Kubernetes 1.37 beta | Depende del producto |
| Basado en eventos | Integraciones con fuentes de eventos y activación | Posible mediante adaptadores de métricas personalizadas/externas | Depende del producto |
| Independiente de la nube | ✅ | ✅ | ❌ |
| Complejidad de implementación | Operador, servidor de métricas, webhooks y credenciales | Controlador integrado; pueden hacer falta adaptadores | Depende del producto |
| Métricas personalizadas | Integración con Scaler o productor HTTP/gRPC | Requiere un adaptador de métricas adecuado | Depende del producto |

## Arquitectura {#architecture}

KEDA se basa en el patrón de operador de Kubernetes: supervisa fuentes de métricas externas y administra automáticamente el HPA de Kubernetes.

![El operador de KEDA administra la activación de ScaledObject y el ciclo de vida del HPA, expone los resultados de los Scalers al servidor de API de métricas y crea directamente Jobs para ScaledJob. El HPA administra las réplicas distintas de cero de ScaledObject; los webhooks de admisión validan los recursos.](../.gitbook/assets/en-autoscaling-01-keda-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-autoscaling-01-keda-0.html)


### Componentes principales

1. **Operador de KEDA**: reconcilia ScaledObjects y sus HPA, gestiona la activación y desactivación desde cero y crea Jobs para ScaledJobs.
2. **Servidor de métricas de KEDA**: sirve métricas externas mediante la API agregada de Kubernetes y obtiene los resultados de los Scalers a través del servicio de métricas del operador.
3. **ScaledObject**: define la configuración de escalado para Deployments, StatefulSets, etc.
4. **ScaledJob**: define la configuración de escalado para Kubernetes Jobs
5. **Triggers/Scalers**: obtienen métricas de fuentes de eventos y evalúan la activación; los webhooks de admisión validan las configuraciones de recursos compatibles.

### Cómo funciona

1. Un ScaledObject hace referencia a un destino de escalado compatible en su espacio de nombres. KEDA administra un HPA para ese destino; usa un solo responsable del escalado por destino.
2. El operador consulta los activadores para determinar si debe activar la carga de trabajo, según `pollingInterval`, incluso cuando está en cero.
3. Para las réplicas distintas de cero, el HPA solicita métricas externas a través del servidor de API de métricas y del operador. La sincronización del HPA y la configuración de almacenamiento en caché de métricas afectan la frecuencia de las consultas.
4. El HPA ajusta las réplicas distintas de cero; KEDA gestiona la activación y el periodo de espera configurado para escalar a cero. `cooldownPeriod` no sustituye la estabilización del escalado descendente del HPA desde N réplicas a 1.
5. ScaledJob sigue una ruta distinta: KEDA crea Jobs por lotes según los eventos y su estrategia de escalado; no crea un HPA para esos Jobs.

## Instalación y configuración {#installation-and-configuration}

Los ejemplos son alternativas, no un único conjunto de manifiestos. Prepara las cargas de trabajo, Services, Secrets e imágenes a las que se hace referencia; sustituye los marcadores de posición de cuentas, colas, URL e imágenes. No asocies varios ScaledObjects/HPA al mismo destino. Una vez que el escalado automático administra las réplicas, coordina la propiedad de `spec.replicas` en GitOps/applies. Estas recetas no se han implementado ni medido en producción.

Kubernetes 1.37 introdujo el escalado a cero del HPA para métricas de objeto/externas en versión beta, habilitado de forma predeterminada mediante `HPAScaleToZero`; las métricas que solo usan CPU/memoria no pueden activar el escalado desde cero. Esto no cambia la separación entre operador y HPA de KEDA 2.21 ni demuestra la compatibilidad con Kubernetes 1.37.

### Requisitos previos

- Elige una versión de Kubernetes compatible con tu proveedor y con la versión de KEDA seleccionada. La documentación de implementación de KEDA 2.21 publica una **matriz probada de 1.34–1.36**. Esa matriz no demuestra la compatibilidad con 1.37; valida esa combinación por separado.
- Si vas a actualizar desde KEDA 2.20, revisa primero la [guía de migración 2.21](https://keda.sh/docs/2.21/migration/#upgrading-from-keda-220-to-221). Como corrección para CVE-2026-77524, 2.21 aplica de forma predeterminada la validación de las audiencias de los tokens de cuentas de servicio (`operator.serviceAccountTokens.mode: enforce-audience`) para la autenticación de Vault en Kubernetes y `boundServiceAccountToken`. También elimina la configuración obsoleta del Scaler de Temporal y cambia el valor predeterminado de `scaleOnInFlight` de Azure Pipelines. Los ejemplos de este capítulo no utilizan esos métodos de autenticación ni esos Scalers.
- kubectl configurado
- Helm (opcional)

### Métodos de instalación

#### 1. Instalación mediante Helm

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --version 2.21.0 --namespace keda --create-namespace
```

#### 2. Instalación mediante manifiestos YAML

```bash
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.21.0/keda-2.21.0.yaml
```

#### 3. Verificar la instalación

```bash
kubectl get deployments,pods -n keda
kubectl wait --for=condition=Available deployment --all -n keda --timeout=180s
kubectl get apiservice v1beta1.external.metrics.k8s.io
```

Salida ilustrativa (los nombres y las cantidades dependen de la configuración del chart; no es una ejecución capturada):
```
NAME                                      READY   STATUS    RESTARTS   AGE
keda-operator-<hash>-<id>                  1/1     Running   0          1m
keda-operator-metrics-apiserver-<hash>-<id> 1/1     Running   0          1m
keda-admission-webhooks-<hash>-<id>        1/1     Running   0          1m
```

### Configuración básica

Los valores de IRSA que se muestran más adelante deben combinarse con los mismos valores de Helm fijados a una versión antes de aplicar una actualización. Verifica la anotación resultante de ServiceAccount y reinicia los Pods del operador mediante el proceso normal de despliegue cuando cambies la identidad.

Los siguientes valores corresponden a Helm chart 2.21.0. Dos réplicas del operador proporcionan una instancia en espera para la elección de líder, no dos reconciliadores activos. La redundancia del servidor de métricas también depende del enrutamiento de agregación de API y no implica alta disponibilidad integral de extremo a extremo. Los valores de recursos son un punto de partida, no un dimensionamiento medido.

#### Configuración personalizada mediante un archivo de valores de Helm

```yaml
operator:
  replicaCount: 2
metricsServer:
  replicaCount: 1
resources:
  operator:
    limits:
      cpu: '1'
      memory: 1000Mi
    requests:
      cpu: 100m
      memory: 100Mi
  metricServer:
    limits:
      cpu: '1'
      memory: 1000Mi
    requests:
      cpu: 100m
      memory: 100Mi
  webhooks:
    limits:
      cpu: '1'
      memory: 1000Mi
    requests:
      cpu: 100m
      memory: 100Mi
logging:
  operator:
    level: info
  metricServer:
    level: 0
```

```bash
helm upgrade --install keda kedacore/keda --version 2.21.0 --namespace keda --create-namespace -f values.yaml
```

## Scalers

KEDA ofrece Scalers para diversas fuentes de eventos. Cada Scaler recopila métricas de una fuente de eventos específica y escala las cargas de trabajo en función de ellas.

### Scalers principales

KEDA admite más de 50 Scalers; entre los principales se incluyen:

1. **Colas de mensajes**:
   - Apache Kafka
   - RabbitMQ
   - AWS SQS
   - Azure Service Bus
   - Google Cloud Pub/Sub

2. **Bases de datos**:
   - MySQL
   - PostgreSQL
   - MongoDB
   - Redis

3. **Plataformas de streaming**:
   - Apache Kafka
   - AWS Kinesis
   - Azure Event Hubs

4. **Servicios en la nube**:
   - AWS CloudWatch
   - Azure Monitor
   - Google Cloud Monitoring

5. **Otros**:
   - Prometheus
   - InfluxDB
   - Cron
   - CPU/Memory

### Ejemplo básico de ScaledObject

Crea `rabbitmq-credentials` en el espacio de nombres de destino con la clave `host`, que debe contener un URI de conexión AMQP/AMQPS completo y autorizado. El Deployment `rabbitmq-consumer` al que se hace referencia debe estar configurado para consumir de esa cola. En redes que no estén aisladas, prefiere TLS con la confianza verificada; el ejemplo no implementa un broker ni inventa credenciales.

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: rabbitmq-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: host
    name: rabbitmq-credentials
    key: host
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rabbitmq-consumer
  pollingInterval: 15
  cooldownPeriod: 30
  minReplicaCount: 0
  maxReplicaCount: 30
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: hello
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
```

### Ejemplo básico de ScaledJob

Reutiliza `rabbitmq-auth` y `rabbitmq-credentials` anteriores. Proporciona una imagen real de worker cuyo proceso consuma una cantidad acotada de trabajo, lo confirme y termine; de lo contrario, los Jobs no terminarán nunca. Los reintentos pueden repetir el procesamiento, así que usa idempotencia en la aplicación y confirmaciones/tiempos de espera de visibilidad adecuados. `jobTargetRef` es un JobSpec, no otro Job anidado ni un PodTemplate.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: rabbitmq-scaledjob
  namespace: default
spec:
  jobTargetRef:
    template:
      spec:
        containers:
        - name: rabbitmq-worker
          image: rabbitmq-worker:latest
          imagePullPolicy: Always
          env:
          - name: RABBITMQ_HOST
            valueFrom:
              secretKeyRef:
                name: rabbitmq-credentials
                key: host
        restartPolicy: Never
    backoffLimit: 4
  pollingInterval: 15
  maxReplicaCount: 30
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
  - type: rabbitmq
    metadata:
      protocol: amqp
      queueName: hello
      mode: QueueLength
      value: '5'
    authenticationRef:
      name: rabbitmq-auth
```
## Escalado con métricas personalizadas {#custom-metric-scaling}

Además de diversos Scalers integrados, KEDA permite escalar con flexibilidad en función de métricas personalizadas. Esto permite implementar una lógica de escalado única, adaptada a los requisitos de tu negocio.

### Uso de la API de métricas externas

El ejemplo del contador usa `rate(...[2m])`, así que su objetivo son eventos por segundo por réplica, no un total acumulado. Las consultas de Prometheus deben producir un único resultado numérico. `ignoreNullValues: false` presenta las series ausentes como un error; decide deliberadamente si un resultado vacío significa cero o una interrupción de la telemetría.

Puedes implementar el escalado basado en métricas personalizadas con fuentes de métricas externas como Prometheus:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: custom-metrics-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server.monitoring.svc.cluster.local
      threshold: '100'
      query: sum(rate(custom_metric_total{namespace="default",pod=~"my-app-.*"}[2m]))
      ignoreNullValues: 'false'
```

### Uso de HTTP Scaler

Este es el Scaler `metrics-api` para datos numéricos de un endpoint, no el complemento independiente de KEDA para HTTP, que intercepta y almacena en búfer solicitudes para activar la carga de trabajo. El endpoint debe permanecer disponible independientemente de la carga de trabajo que se escale, especialmente cuando esta está en cero.

Puedes obtener métricas de un endpoint HTTP para realizar el escalado:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: http-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: metrics-api
    metadata:
      targetValue: '100'
      url: https://metrics.example.com/metrics
      valueLocation: value
```

### Desarrollo de Scalers personalizados

El ejemplo en Go a continuación es un **productor HTTP de métricas JSON para el Scaler integrado `metrics-api`**, no una implementación de Kubernetes external.metrics.k8s.io ni del protocolo de external-scaler de KEDA. En cambio, un servicio KEDA `external`/`external-push` implementa los métodos gRPC documentados `IsActive`, `GetMetricSpec`, `GetMetrics` y, para la activación push, `StreamIsActive`.

1. Implementación del servidor de métricas:

El servidor Go completo lee `METRICS_FILE`, una instantánea JSON que se sustituye de forma atómica y contiene un `value` numérico y `observed_at` en formato RFC3339. Un productor independiente de métricas de negocio debe escribirla. Si faltan datos, son no válidos o negativos, o tienen más de dos minutos, devuelve HTTP503. Créalo e impleméntalo con un Service correspondiente antes de usar el siguiente ScaledObject; no es un servidor de API agregada de Kubernetes.

```go
package main

import (
    "encoding/json"
    "errors"
    "io"
    "log"
    "net/http"
    "os"
    "time"
)

type snapshot struct {
    Value *float64 `json:"value"`
    ObservedAt time.Time `json:"observed_at"`
}

func metricsHandler(path string) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodGet {
            w.Header().Set("Allow", "GET")
            http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
            return
        }
        f, err := os.Open(path)
        if err != nil {
            http.Error(w, "metric unavailable", http.StatusServiceUnavailable)
            return
        }
        defer f.Close()
        var v snapshot
        decoder := json.NewDecoder(io.LimitReader(f, 1<<20))
        if err = decoder.Decode(&v); err == nil {
            var extra any
            if err = decoder.Decode(&extra); !errors.Is(err, io.EOF) {
                http.Error(w, "invalid snapshot", http.StatusServiceUnavailable)
                return
            }
        } else {
            http.Error(w, "invalid snapshot", http.StatusServiceUnavailable)
            return
        }
        age := time.Since(v.ObservedAt)
        if v.Value == nil || *v.Value < 0 || v.ObservedAt.IsZero() || age < -5*time.Second || age > 2*time.Minute {
            http.Error(w, "stale or invalid metric", http.StatusServiceUnavailable)
            return
        }
        w.Header().Set("Content-Type", "application/json")
        w.Header().Set("Cache-Control", "no-store")
        _ = json.NewEncoder(w).Encode(v)
    }
}

func main() {
    path := os.Getenv("METRICS_FILE")
    if path == "" { log.Fatal("METRICS_FILE is required") }
    mux := http.NewServeMux()
    mux.HandleFunc("/metrics", metricsHandler(path))
    server := &http.Server{
        Addr: ":8080", Handler: mux,
        ReadHeaderTimeout: 5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout: 60 * time.Second,
    }
    log.Fatal(server.ListenAndServe())
}
```

2. Integración con KEDA:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: custom-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: metrics-api
    metadata:
      targetValue: '100'
      url: http://custom-metrics-server:8080/metrics
      valueLocation: value
```

## Escalado con métricas de Twitter {#twitter-metric-scaling}

Este ejemplo utiliza el endpoint de recuentos recientes de la API v2 de X (antes Twitter). Cuenta las coincidencias en una ventana de cinco minutos que termina 30 segundos antes de la recopilación; no es un recuento acumulado ni una tasa instantánea de publicaciones. Deben verificarse el acceso de la cuenta, la semántica de las consultas, la facturación y los límites de frecuencia para el uso previsto.

### Requisitos previos

- Una aplicación para desarrolladores de X con acceso a los recuentos recientes de Posts y un token de portador de la aplicación; este ejemplo no implica que exista acceso a la API ni que sea gratuito.
- Un servicio para recopilar y exponer métricas

### Pasos de implementación

1. Implementa el servicio de recopilación de métricas de Twitter:

Guarda este ejemplo independiente como `app.py` en la imagen de tu recopilador, junto con las dependencias Flask, requests y Gunicorn. El Deployment usa un solo worker de Gunicorn y `app:create_app()` para que el recopilador en segundo plano se inicie correctamente bajo WSGI. Varios workers/réplicas multiplican las consultas a la API. Si se produce un error parcial de recuento, de límite de frecuencia o de autenticación, se devuelve HTTP503; el código no usa silenciosamente una página de búsqueda truncada como si fuera una tasa. Ajusta la frecuencia de consulta a los permisos de tu API.

```python
import datetime as dt
import os
import threading
import time

import requests
from flask import Flask, jsonify

TOKEN = os.environ["X_BEARER_TOKEN"]
QUERY = os.environ.get("X_QUERY", "#kubernetes")
POLL_SECONDS = 60
MAX_AGE_SECONDS = 120
METRIC_NAME = "tweet_count"


def fetch_value():
    # Five-minute window ending 30 seconds ago; not a lifetime count or live rate.
    end = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=30)
    start = end - dt.timedelta(minutes=5)
    response = requests.get(
        "https://api.x.com/2/tweets/counts/recent",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params={"query": QUERY, "granularity": "minute",
                "start_time": start.isoformat(), "end_time": end.isoformat()},
        timeout=(3, 10),
    )
    response.raise_for_status()
    body = response.json()
    meta = body["meta"]
    # Never silently scale from a partial result or an API error payload.
    if body.get("errors") or meta.get("next_token"):
        raise ValueError("incomplete counts response")
    value = meta["total_tweet_count"]
    if type(value) is not int or value < 0:
        raise ValueError("invalid count")
    return value


def create_app():
    app = Flask(__name__)
    lock = threading.Lock()
    state = {"value": None, "updated": 0.0, "healthy": False}

    def collect():
        while True:
            try:
                value = fetch_value()
                if type(value) is not int or value < 0:
                    raise ValueError("invalid metric")
                with lock:
                    state.update(value=value, updated=time.monotonic(), healthy=True)
            except Exception as exc:
                with lock:
                    state["healthy"] = False
                app.logger.warning("Metric refresh failed: %s", type(exc).__name__)
            time.sleep(POLL_SECONDS)

    @app.get("/metrics")
    def get_metrics():
        with lock:
            current = state.copy()
        if not current["healthy"] or time.monotonic() - current["updated"] > MAX_AGE_SECONDS:
            return jsonify(error="metric unavailable or stale"), 503
        response = jsonify({METRIC_NAME: current["value"]})
        response.headers["Cache-Control"] = "no-store"
        return response

    threading.Thread(target=collect, daemon=True).start()
    return app


if __name__ == "__main__":
    # Local development only; use a WSGI server for the deployment example.
    create_app().run(host="127.0.0.1", port=8080)
```

2. Implementa el servicio de recopilación de métricas:

Crea y fija la versión de la imagen del recopilador antes de implementarlo. Crea el archivo existente del token como entrada de Secret sin poner su valor en un argumento de shell:

```bash
kubectl create secret generic twitter-api-secrets --namespace default --from-file=bearer-token=./x-bearer-token
```

Este comando crea un Secret de Kubernetes cuando se ejecuta; no se ejecutó durante esta auditoría. Mantén el archivo de origen fuera del control de versiones.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twitter-metrics-collector
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: twitter-metrics-collector
  template:
    metadata:
      labels:
        app: twitter-metrics-collector
    spec:
      containers:
      - name: collector
        image: twitter-metrics-collector:latest
        ports:
        - containerPort: 8080
        env:
        - name: X_BEARER_TOKEN
          valueFrom:
            secretKeyRef:
              name: twitter-api-secrets
              key: bearer-token
        command:
        - gunicorn
        args:
        - --bind
        - 0.0.0.0:8080
        - --workers
        - '1'
        - --threads
        - '4'
        - app:create_app()
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /metrics
            port: 8080
          periodSeconds: 10
          failureThreshold: 3
      automountServiceAccountToken: false
---
apiVersion: v1
kind: Service
metadata:
  name: twitter-metrics-collector
  namespace: default
spec:
  selector:
    app: twitter-metrics-collector
  ports:
  - port: 80
    targetPort: 8080
```

3. Configura el ScaledObject de KEDA:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: twitter-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: twitter-processor
  minReplicaCount: 1
  maxReplicaCount: 20
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: metrics-api
    metadata:
      targetValue: "10"
      url: "http://twitter-metrics-collector/metrics"
      valueLocation: "tweet_count"
```

Con el valor predeterminado AverageValue, la proporción entre recuento y objetivo propone réplicas dentro de los límites configurados; no representa directamente el rendimiento de procesamiento. El recopilador permanece en una réplica de forma independiente, devuelve 503 cuando no está disponible y no tiene una sonda de actividad que lo reinicie solo por una interrupción del servicio ascendente. El uso en producción sigue requiriendo credenciales probadas, límites, gestión del ciclo de vida y observabilidad.

## Escalado con Google Calendar {#google-calendar-scaling}

Este ejemplo cuenta las instancias de eventos de Google Calendar **que se solapan con la siguiente hora**, incluidos los eventos que ya están en curso. `timeMin` filtra las horas de finalización de los eventos y `timeMax` filtra las horas de inicio. Se cuentan todas las páginas; si la recopilación es parcial, falla o los datos están obsoletos, la métrica se declara no disponible en lugar de devolver un cero falso.

### Requisitos previos

- Habilita la API de Calendar y usa una cuenta de servicio con acceso de lectura a un calendario compartido específico. Establece el ID real del calendario; `primary` no sustituye el hecho de compartir un calendario de usuario con esa cuenta de servicio.
- Un servicio para recopilar y exponer métricas

### Pasos de implementación

1. Implementa el servicio de recopilación de métricas de Google Calendar:

Guarda este ejemplo independiente como `app.py` en su propia imagen, junto con Flask, requests, google-auth y Gunicorn. Un único hilo recopilador sigue todas las páginas e informa de un fallo si se repiten los tokens o se alcanza el límite de seguridad de páginas. El valor escalar cuenta instancias de eventos que se solapan, no asistentes ni réplicas necesarias. Debe concederse acceso al calendario a la cuenta de servicio; el alcance de OAuth por sí solo no concede ese acceso.

```python
import datetime as dt
import os
import threading
import time
from urllib.parse import quote

from flask import Flask, jsonify
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

CALENDAR_ID = os.environ["CALENDAR_ID"]
SERVICE_ACCOUNT_FILE = "/etc/secrets/service-account.json"
POLL_SECONDS = 300
MAX_AGE_SECONDS = 360
METRIC_NAME = "upcoming_events"


def fetch_value():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    now = dt.datetime.now(dt.timezone.utc)
    params = {"timeMin": now.isoformat(),
              "timeMax": (now + dt.timedelta(hours=1)).isoformat(),
              "singleEvents": "true", "showDeleted": "false",
              "orderBy": "startTime", "maxResults": 2500}
    url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(CALENDAR_ID, safe='')}/events"
    total = 0
    seen_tokens = set()
    with AuthorizedSession(credentials) as session:
        for _ in range(100):
            response = session.get(url, params=params, timeout=(3, 10))
            response.raise_for_status()
            body = response.json()
            if body.get("error") or body.get("kind") != "calendar#events" or not isinstance(body.get("items", []), list):
                raise ValueError("invalid events response")
            total += len(body.get("items", []))
            token = body.get("nextPageToken")
            if not token:
                return total
            if token in seen_tokens:
                raise ValueError("repeated page token")
            seen_tokens.add(token)
            params["pageToken"] = token
    raise ValueError("pagination limit exceeded; result is incomplete")


def create_app():
    app = Flask(__name__)
    lock = threading.Lock()
    state = {"value": None, "updated": 0.0, "healthy": False}

    def collect():
        while True:
            try:
                value = fetch_value()
                if type(value) is not int or value < 0:
                    raise ValueError("invalid metric")
                with lock:
                    state.update(value=value, updated=time.monotonic(), healthy=True)
            except Exception as exc:
                with lock:
                    state["healthy"] = False
                app.logger.warning("Metric refresh failed: %s", type(exc).__name__)
            time.sleep(POLL_SECONDS)

    @app.get("/metrics")
    def get_metrics():
        with lock:
            current = state.copy()
        if not current["healthy"] or time.monotonic() - current["updated"] > MAX_AGE_SECONDS:
            return jsonify(error="metric unavailable or stale"), 503
        response = jsonify({METRIC_NAME: current["value"]})
        response.headers["Cache-Control"] = "no-store"
        return response

    threading.Thread(target=collect, daemon=True).start()
    return app


if __name__ == "__main__":
    # Local development only; use a WSGI server for the deployment example.
    create_app().run(host="127.0.0.1", port=8080)
```

2. Implementa el servicio de recopilación de métricas:

Usa el ID real del calendario compartido y un archivo JSON existente de la cuenta de servicio. El siguiente comando crea el Secret cuando se ejecuta; no se ejecutó durante la revisión.

```bash
kubectl create secret generic google-calendar-secrets --namespace default --from-file=service-account.json=./service-account.json
```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calendar-metrics-collector
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: calendar-metrics-collector
  template:
    metadata:
      labels:
        app: calendar-metrics-collector
    spec:
      containers:
      - name: collector
        image: calendar-metrics-collector:latest
        ports:
        - containerPort: 8080
        env:
        - name: CALENDAR_ID
          value: REPLACE_WITH_SHARED_CALENDAR_ID
        volumeMounts:
        - name: google-calendar-credentials
          mountPath: /etc/secrets
          readOnly: true
        command:
        - gunicorn
        args:
        - --bind
        - 0.0.0.0:8080
        - --workers
        - '1'
        - --threads
        - '4'
        - app:create_app()
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            memory: 256Mi
        readinessProbe:
          httpGet:
            path: /metrics
            port: 8080
          periodSeconds: 10
          failureThreshold: 3
      volumes:
      - name: google-calendar-credentials
        secret:
          secretName: google-calendar-secrets
      automountServiceAccountToken: false
---
apiVersion: v1
kind: Service
metadata:
  name: calendar-metrics-collector
  namespace: default
spec:
  selector:
    app: calendar-metrics-collector
  ports:
  - port: 80
    targetPort: 8080
```

3. Configura el ScaledObject de KEDA:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: calendar-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: calendar-processor
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: metrics-api
    metadata:
      targetValue: "1"
      url: "http://calendar-metrics-collector/metrics"
      valueLocation: "upcoming_events"
```

Con el valor predeterminado AverageValue, la proporción entre recuento y objetivo propone réplicas dentro de los límites configurados; no representa directamente el rendimiento de procesamiento. El recopilador permanece en una réplica de forma independiente, devuelve 503 cuando no está disponible y no tiene una sonda de actividad que lo reinicie solo por una interrupción del servicio ascendente. El uso en producción sigue requiriendo credenciales probadas, límites, gestión del ciclo de vida y observabilidad.
## Escalado con métricas de Istio {#istio-metric-scaling}

Este ejemplo muestra cómo escalar aplicaciones según las métricas recopiladas de la malla de servicios de Istio. Veremos cómo escalar según las solicitudes por segundo (RPS).

### Requisitos previos

- Malla de servicios de Istio instalada
- Prometheus instalado e integrado con Istio

### Pasos de implementación

1. Verifica una instalación existente de Istio sidecar y la política de inyección. El ejemplo usa enrutamiento dentro de la malla; no requiere un recurso inventado de Gateway de entrada:

```bash
istioctl proxy-status
kubectl get namespace default --show-labels
kubectl get pods -n default
```

2. Implementa una aplicación de ejemplo:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sample-app
  template:
    metadata:
      labels:
        app: sample-app
    spec:
      containers:
      - name: sample-app
        image: nginx:1.30.6
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: sample-app
  namespace: default
spec:
  selector:
    app: sample-app
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: sample-app
  namespace: default
spec:
  hosts:
  - sample-app.default.svc.cluster.local
  gateways:
  - mesh
  http:
  - route:
    - destination:
        host: sample-app
        port:
          number: 80
```

3. Configura el ScaledObject de KEDA:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      threshold: '10'
      query: sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local"}[2m]))
      ignoreNullValues: 'false'
```

Con el tipo de métrica predeterminado `AverageValue`, una tasa total de 100 solicitudes por segundo y un objetivo de 10 solicitudes por segundo por réplica sugieren unas 10 réplicas antes de tener en cuenta la tolerancia, la estabilización y los límites del HPA. La consulta selecciona los informes de destino para evitar contar la misma solicitud tanto desde los proxies de origen como desde los de destino. Prometheus debe recopilar realmente esas solicitudes.

### Configuración avanzada

El siguiente ejemplo requiere una etiqueta de telemetría `request_path` **personalizada y acotada**; no es una dimensión predeterminada de las métricas de Istio. Configura y verifica primero esa etiqueta (evita una cardinalidad arbitraria de URL) o usa la consulta anterior sin ella. Este es un ScaledObject alternativo para el mismo destino, no un responsable de escalado adicional.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-path-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      threshold: '5'
      query: sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local",request_path="/api/v1/products"}[2m]))
      ignoreNullValues: 'false'
```

La proporción de errores y la latencia suelen ser mejores señales de alerta que entradas para el escalado. La siguiente ilustración opcional usa `metricType: Value` para una proporción de todo el servicio, evita una división por cero y limita la velocidad del escalado ascendente. Se supone que más réplicas alivian realmente la sobrecarga diagnosticada; de lo contrario, los errores de servicios posteriores o el ruido de muestras escasas pueden causar un escalado perjudicial. No se ha medido su eficacia en producción.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: istio-error-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.istio-system:9090
      threshold: '0.05'
      query: (sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local",response_code=~"5.*"}[2m]))
        or vector(0)) / clamp_min(sum(rate(istio_requests_total{reporter="destination",destination_service="sample-app.default.svc.cluster.local"}[2m])),
        0.001)
      ignoreNullValues: 'false'
    metricType: Value
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          policies:
          - type: Pods
            value: 1
            periodSeconds: 60
        scaleDown:
          stabilizationWindowSeconds: 300
```

## Escalado basado en Cron {#cron-based-scaling}

KEDA admite el escalado basado en horarios mediante expresiones Cron. Esto permite preescalar aplicaciones según patrones de tráfico o calendarios previsibles.

### Cron Scaler básico

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 0
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 30 * * * *
      end: 45 * * * *
      desiredReplicas: "5"
```

Durante los minutos 30 a 45 de cada hora, el activador Cron solicita un mínimo de 5 réplicas. Fuera de ese intervalo, queda inactivo; el escalado a cero espera al sondeo y al periodo de espera configurado (30 segundos en este ejemplo), además de la programación del controlador. No se garantiza que la transición se produzca exactamente en el minuto 45.

### Horario laboral y fuera del horario laboral

Usa `minReplicaCount: 2` como nivel base fuera del horario laboral y una sola ventana Cron entre semana para 5 réplicas. Así se evitan ventanas nocturnas y de fin de semana superpuestas. La estabilización del HPA puede retrasar la reducción una vez finalizado el horario laboral.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: multi-cron-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 2
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '5'
```

### Combinación de Cron con otros Scalers

Puedes combinar Scalers Cron con otros Scalers para establecer el comportamiento base del escalado y, además, escalar según la carga real:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: combined-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sample-app
  minReplicaCount: 1
  maxReplicaCount: 20
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Seoul
      start: 0 9 * * 1-5
      end: 0 18 * * 1-5
      desiredReplicas: '5'
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      threshold: '10'
      query: sum(rate(http_requests_total{app="sample-app"}[1m]))
      ignoreNullValues: 'false'
```

## Integración con Amazon EKS {#integration-with-amazon-eks}

KEDA puede escalar cargas de trabajo de EKS mediante métricas de AWS cuando se configuran la compatibilidad con Kubernetes, la identidad del operador, los permisos y la conectividad. KEDA no agrega capacidad de cómputo por sí solo; acompaña el escalado de cargas de trabajo con un diseño adecuado de capacidad de nodos/Fargate.

### Instalación de KEDA en EKS

```bash
helm status keda -n keda
kubectl get deployment -n keda
```

### Escalado basado en servicios de AWS

#### Escalado basado en una cola SQS

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: aws-sqs-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sqs-consumer
  minReplicaCount: 0
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: aws-sqs-queue
    metadata:
      queueURL: https://sqs.us-west-2.amazonaws.com/123456789012/my-queue
      queueLength: '5'
      awsRegion: us-west-2
    authenticationRef:
      name: aws-credentials
```

#### Escalado basado en métricas de CloudWatch

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: aws-credentials
  namespace: default
spec:
  podIdentity:
    provider: aws
    identityOwner: keda
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: aws-cloudwatch-scaler
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cloudwatch-app
  minReplicaCount: 1
  maxReplicaCount: 10
  pollingInterval: 15
  cooldownPeriod: 30
  triggers:
  - type: aws-cloudwatch
    metadata:
      namespace: AWS/SQS
      dimensionName: QueueName
      dimensionValue: my-queue
      metricName: ApproximateNumberOfMessagesVisible
      targetMetricValue: '5'
      minMetricValue: '0'
      awsRegion: us-west-2
      metricStat: Average
      metricStatPeriod: '60'
      metricCollectionTime: '300'
    authenticationRef:
      name: aws-credentials
```

### Integración de IRSA (IAM Roles for Service Accounts)

Este ejemplo supone que ya existe un rol de IRSA para `system:serviceaccount:keda:keda-operator`, vinculado al proveedor OIDC de este clúster con `aud: sts.amazonaws.com`. Concede `sqs:GetQueueAttributes` en la cola seleccionada y la acción necesaria para leer las métricas de CloudWatch (como `cloudwatch:GetMetricData`); las acciones de CloudWatch que no admiten recursos específicos requieren un recurso comodín y pueden limitarse según la región solicitada. Los permisos del consumidor son independientes. Los comandos siguientes inspeccionan la configuración; el aprovisionamiento del rol corresponde a la configuración de infraestructura revisada.

```bash
: "${KEDA_IAM_ROLE_NAME:?Set the existing IRSA role name}"
aws iam get-role --role-name "$KEDA_IAM_ROLE_NAME" --query Role.AssumeRolePolicyDocument
kubectl get serviceaccount keda-operator -n keda -o yaml
```

```yaml
serviceAccount:
  operator:
    create: true
    name: keda-operator
    annotations:
      eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/keda-operator-role
      eks.amazonaws.com/sts-regional-endpoints: 'true'
```

## Prácticas recomendadas {#best-practices}

### Optimización del rendimiento

1. **Establece intervalos de sondeo adecuados**: ajusta los intervalos de sondeo a las características de tu carga de trabajo
2. **Configura por separado el periodo de espera y el comportamiento del HPA**: el periodo de espera rige el escalado a cero; la estabilización y las políticas del HPA rigen los cambios entre cantidades de réplicas distintas de cero.
3. **Establece solicitudes y límites de recursos**: asigna recursos adecuados a los componentes de KEDA
4. **Escribe consultas eficientes**: optimiza las consultas de métricas

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: optimized-scaler
  namespace: default
spec:
  pollingInterval: 30
  cooldownPeriod: 300
  scaleTargetRef:
    name: my-app
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      threshold: '100'
      query: sum(rate(http_requests_total{namespace="default",app="my-app"}[2m]))
      ignoreNullValues: 'false'
```

### Mejora de la fiabilidad

1. **Comprende el funcionamiento de varios activadores**: normalmente, el HPA toma la recomendación de réplicas más alta; los activadores no suman capacidad y los errores pueden impedir el escalado descendente.
2. **Establece cantidades mínimas y máximas de réplicas adecuadas**: configura intervalos que correspondan a los requisitos de la carga de trabajo
3. **Estrategia de gestión de fallos**: en KEDA 2.21, el fallback admite activadores Value y AverageValue, excepto CPU/memoria, y se aplica a ScaledObjects, no a ScaledJobs. Prueba el comportamiento ante interrupciones y fallos de autenticación.
4. **Configura la supervisión y las alertas**: supervisa el estado operativo de KEDA

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reliable-scaler
  namespace: default
spec:
  minReplicaCount: 2
  maxReplicaCount: 20
  fallback:
    failureThreshold: 3
    replicas: 5
  scaleTargetRef:
    name: my-app
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc.cluster.local:9090
      threshold: '100'
      query: sum(rate(http_requests_total{namespace="default",app="my-app"}[2m]))
      ignoreNullValues: 'false'
```

### Refuerzo de la seguridad

La NetworkPolicy siguiente restringe el tráfico de entrada al recopilador de Twitter para permitir solo al operador de KEDA por TCP8080; no es una política completa para el plano de control de KEDA. Su aplicación requiere compatibilidad con NetworkPolicy. Antes de restringir KEDA, ten en cuenta el acceso del servidor de API a la API de métricas y al webhook de admisión, el tráfico entre el operador y el servidor de métricas, DNS, la API de Kubernetes y cada endpoint de Scaler. Un plano de control de EKS no es simplemente un Pod en `kube-system`.

1. **Aplica el principio de privilegio mínimo**: concede solo los permisos necesarios
2. **Gestión de Secrets**: gestiona la información confidencial de forma segura
3. **Aplica políticas de red**: restringe el acceso a los componentes de KEDA
4. **Configura RBAC**: establece un control de acceso basado en roles adecuado

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: secure-auth
  namespace: default
spec:
  secretTargetRef:
  - parameter: host
    name: rabbitmq-credentials
    key: host
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: twitter-metrics-from-keda
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: twitter-metrics-collector
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: keda
      podSelector:
        matchLabels:
          app: keda-operator
    ports:
    - protocol: TCP
      port: 8080
```

## Solución de problemas {#troubleshooting}

### Problemas comunes

#### 1. El escalado no funciona

**Síntoma**: los Pods no escalan aunque las métricas superen el umbral

**Solución**:
- Revisa los registros de KEDA
- Verifica la conectividad con la fuente de métricas
- Verifica la configuración de autenticación

```bash
# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator

# Check KEDA metrics server logs
kubectl logs -n keda -l app=keda-operator-metrics-apiserver

# Check ScaledObject status
kubectl get scaledobject -n <namespace> <name> -o yaml
```

#### 2. Problemas con el escalado a cero

**Síntoma**: no escala a 0 cuando no hay actividad

**Solución**:
- Revisa la configuración de minReplicaCount
- Verifica los valores de las métricas
- Revisa el estado del HPA

```bash
# Check HPA status
kubectl get hpa -n <namespace>

# Check metric values directly
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/<namespace>/<metric-name>?labelSelector=scaledobject.keda.sh%2Fname%3D<scaledobject-name>" | jq
```

#### 3. Problemas de autenticación

**Síntoma**: no se puede conectar a la fuente de métricas

**Solución**:
- Verifica la configuración de TriggerAuthentication
- Revisa los Secrets o las variables de entorno
- Verifica los permisos

```bash
# Check TriggerAuthentication
kubectl get triggerauthentication -n <namespace> <name> -o yaml

# Check secrets
kubectl get secret -n <namespace> <name> -o json | jq '{name: .metadata.name, type: .type, keys: ((.data // {}) | keys)}'
```

### Herramientas de depuración

```bash
# Check KEDA version
kubectl get deployment -n keda keda-operator -o jsonpath="{.spec.template.spec.containers[0].image}"

# Check ScaledObject status
kubectl describe scaledobject -n <namespace> <name>

# Check HPA status
kubectl describe hpa -n <namespace> <name>

# Check metric values
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/<namespace>/<metric-name>?labelSelector=scaledobject.keda.sh%2Fname%3D<scaledobject-name>"

# Check KEDA logs
kubectl logs -n keda -l app=keda-operator --tail=100
```

## Conclusión

KEDA (Kubernetes Event-driven Autoscaling) es una herramienta eficaz que proporciona escalado automático basado en eventos en entornos de Kubernetes. Amplía el HPA básico de Kubernetes para permitir el escalado de cargas de trabajo según diversas fuentes de eventos y métricas.

Este documento abordó los conceptos básicos de KEDA, los métodos de instalación, el uso de diversos Scalers, el escalado con métricas personalizadas, la integración con servicios externos como Twitter y Google Calendar, el escalado basado en métricas de Istio, el escalado basado en Cron, la integración con Amazon EKS, las prácticas recomendadas y la solución de problemas.

Con KEDA, puedes escalar aplicaciones de forma más eficiente, optimizar el uso de recursos y reducir los costes. Es especialmente útil para implementar arquitecturas basadas en eventos y patrones sin servidor.

### Próximos pasos

- Implementa arquitecturas sin servidor con KEDA
- Explora la integración con diversas fuentes de eventos
- Desarrolla Scalers personalizados
- Aprovecha KEDA en entornos de varios clústeres
- Integra KEDA con otras herramientas nativas de la nube

## Referencias

- [Documentación oficial de KEDA](https://keda.sh/docs/)
- [Repositorio de KEDA en GitHub](https://github.com/kedacore/keda)
- [Lista de Scalers de KEDA](https://keda.sh/docs/latest/scalers/)
- [KEDA Operator Hub](https://operatorhub.io/operator/keda)
- [Configuración de AWS IRSA](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html)

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, responde el [cuestionario del tema](../quizzes/autoscaling/05-keda-quiz.md).

Referencias verificadas para esta revisión: [compatibilidad de KEDA](https://keda.sh/docs/2.21/operate/cluster/), [ScaledObject](https://keda.sh/docs/2.21/reference/scaledobject-spec/), [ScaledJob](https://keda.sh/docs/2.21/reference/scaledjob-spec/), [autenticación de AWS](https://keda.sh/docs/2.21/authentication-providers/aws/), [gRPC de external scaler](https://keda.sh/docs/2.21/concepts/external-scalers/), [recuentos de X](https://docs.x.com/x-api/posts/counts/quickstart), [eventos de Calendar](https://developers.google.com/workspace/calendar/api/v3/reference/events/list), [HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).
