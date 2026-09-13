# Funciones avanzadas

> **Última actualización**: September 11, 2026 · Istio 1.31. Estos ejemplos independientes presuponen que existen las cargas de trabajo, Services y controladores indicados. Siga cada capítulo detallado para la instalación/compatibilidad y validación; los fragmentos no constituyen una pila probada en producción.

Esta sección cubre funciones avanzadas de Istio, como el modo Ambient, multiclúster, EnvoyFilter, compatibilidad con gRPC/WebSocket y otras.

## Índice

1. [Modo Ambient](01-ambient-mode.md)
2. [Multiclúster](02-multi-cluster.md)
3. [EnvoyFilter](03-envoy-filter.md)
4. [Caché DNS](04-dns-cache.md)
5. [gRPC](05-grpc.md)
6. [WebSocket](06-websocket.md)
7. [Inyección de sidecars](07-sidecar-injection.md)
8. [Integración con Argo Rollouts](08-argo-rollouts.md)
9. [Argo Rollouts con reconocimiento de zonas](09-zone-aware-argo-rollouts.md)
10. [Autoescalado con KEDA](10-keda-autoscaling.md)

## Descripción general

Esta sección cubre funciones avanzadas de Istio y temas detallados necesarios para entornos de producción.

### Temas principales

El modo de despliegue, el enrutamiento de protocolos, la personalización, el control del despliegue y el autoescalado son decisiones relacionadas pero distintas. EnvoyFilter no configura ztunnel, que está basado en Rust, y el enrutamiento del tráfico de Istio para Argo Rollouts no depende intrínsecamente de la inyección de sidecars en las aplicaciones.

## 1. Modo Ambient

Ambient se incluyó por primera vez como alpha en Istio 1.18 y alcanzó GA en 1.24. Separa la superposición segura L4 del nodo del procesamiento L7 opcional basado en waypoints.

### Modo Sidecar frente a modo Ambient

| Característica | Modo Sidecar | Modo Ambient |
|----------------|-------------|--------------|
| **Arquitectura** | Proxy Envoy inyectado en cada pod | ztunnel (a nivel de nodo) + waypoint (opcional) |
| **Modelo de recursos** | Asignación de Envoy por Pod | ztunnel compartido más cualquier asignación de waypoint; mida el consumo total |
| **Incorporación** | La inyección generalmente requiere crear nuevos Pods | Incorporación mediante etiquetas con CNI/ztunnel requeridos; la incorporación al waypoint es independiente |
| **Rendimiento** | Depende de la configuración del proxy/carga de trabajo | Depende de la ruta, el uso de waypoints y la capacidad; no siempre es más rápido |
| **Funciones** | Conjunto maduro de funciones L4/L7 | L4 de forma predeterminada; L7 requiere waypoint; verifique la compatibilidad de funciones de la versión |

### Arquitectura del modo Ambient

![Un pod de aplicación sin sidecar envía tráfico de forma transparente al ztunnel del nodo, que reenvía el tráfico L4 directamente al servicio y solo lo desvía a través de un proxy waypoint opcional cuando se requiere enrutamiento L7.](../../../.gitbook/assets/en-service-mesh-istio-advanced-readme-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-readme-1.html)

La figura de arquitectura es conceptual: un recurso debe incorporarse para utilizar un waypoint. El ámbito de tráfico configurado atraviesa entonces ese waypoint; ztunnel no inspecciona las solicitudes HTTP ni decide por solicitud si se necesita L7.

**Más información**: [Guía detallada del modo Ambient](01-ambient-mode.md)

## 2. Multiclúster

Conecte varios clústeres de Kubernetes como una única malla de servicios.

### Topología multiclúster

![El plano de control del clúster primario envía configuración a dos clústeres remotos mientras el Servicio A se comunica directamente por la malla con el servicio de cada clúster remoto.](../../../.gitbook/assets/en-service-mesh-istio-advanced-readme-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-readme-2.html)

**Casos de uso**:
- Despliegue multirregión
- Recuperación ante desastres (DR)
- Despliegue azul/verde de clústeres
- Conexión deliberada de entornos seleccionados; el aislamiento sigue necesitando límites de identidad/red/autorización

La figura ilustra una topología primario/remoto con conectividad supuesta. Múltiples primarios es otra topología; las redes distintas requieren gateways este-oeste/enrutamiento y configuración de confianza adecuados. Conectar clústeres por sí solo no proporciona recuperación ante desastres ni aísla los entornos.

**Más información**: [Guía de configuración multiclúster](02-multi-cluster.md)

## 3. EnvoyFilter

Personalice directamente la configuración del proxy Envoy.

### Casos de uso de EnvoyFilter

Prefiera API compatibles como las cabeceras de VirtualService, AuthorizationPolicy o WasmPlugin cuando expresen el requisito. Este ejemplo Lua ilustra una extensión sidecar sensible a la versión, no una configuración ambient universal ni un sistema de autenticación.


```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: "function envoy_on_request(request_handle)\n  request_handle:headers():replace(\"x-custom-header\", \"value\")\nend\n"
```

**Principales casos de uso**:
- Limitación de tasa
- Autenticación/autorización personalizada
- Manipulación de cabeceras
- Transformación de solicitudes/respuestas
- Plugins WASM

**Más información**: [Guía de EnvoyFilter](03-envoy-filter.md)

## 4. Caché DNS

El proxy DNS de Istio captura las consultas DNS de las aplicaciones y puede responder localmente a las entradas de la malla/servicios. Un grupo de conexiones DestinationRule no habilita la caché DNS. Combine este fragmento de plantilla de Pod y cree nuevos Pods con sidecar:

```yaml
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: "proxyMetadata:\n  ISTIO_META_DNS_CAPTURE: \"true\"\n"
```

**Ventajas**:
- Menor latencia de consulta DNS
- Menor carga en servidores DNS externos
- Respuestas conscientes del registro, sujetas al comportamiento de descubrimiento/TTL/actualización

La captura DNS en sidecars requiere activación explícita; ambient habilita el proxy DNS de forma predeterminada desde 1.25. La captura, la asignación de direcciones del registro y la actualización del DNS ascendente son comportamientos independientes; la caché no garantiza respuestas DNS permanentemente idénticas ni elimina todas las consultas externas.

**Más información**: [Guía de caché DNS](04-dns-cache.md)

## 5. Compatibilidad con gRPC

gRPC utiliza enrutamiento HTTP/2. Este ejemplo presupone un Service `grpc-service` con un puerto gRPC con nombre 9090 y Pods listos etiquetados con `version: v2`. Las RPC no son intrínsecamente idempotentes, por lo que aquí se deshabilitan explícitamente los reintentos de la malla; los clientes siguen necesitando plazos y propagación del contexto.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts:
  - grpc-service
  http:
  - match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    retries:
      attempts: 0
  - route:
    - destination:
        host: grpc-service
        port:
          number: 9090
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: grpc-service
  namespace: default
spec:
  host: grpc-service
  subsets:
  - name: v2
    labels:
      version: v2
```

**Funciones principales**:
- Equilibrio de carga basado en HTTP/2
- Protocolo de estado de la aplicación/sondas de Kubernetes cuando se configuran explícitamente
- Plazos y reintentos
- Enrutamiento basado en metadatos

**Más información**: [Guía de gRPC](05-grpc.md)

## 6. Compatibilidad con WebSocket

Istio admite actualizaciones HTTP a WebSocket. Esto presupone un `my-gateway` existente en `default` para `ws.example.com`, y un Service de backend HTTP8080 que atiende `/ws`. No es necesaria una coincidencia exacta de la cabecera Upgrade sensible a mayúsculas y minúsculas.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
  namespace: default
spec:
  hosts:
  - ws.example.com
  http:
  - match:
    - uri:
        prefix: /ws
    route:
    - destination:
        host: websocket-service
        port:
          number: 8080
    retries:
      attempts: 0
  gateways:
  - my-gateway
```

**Funciones principales**:
- Mantenimiento de conexiones de larga duración
- Configuración de grupos de conexiones
- Gestión del tiempo de espera por inactividad

Este ejemplo omite el tiempo de espera de la ruta HTTP, que está deshabilitado de forma predeterminada en Istio; eso no deshabilita todos los límites de inactividad o duración máxima del equilibrador de carga/proxy/aplicación. Planifique el drenaje de conexiones y el comportamiento de reconexión durante el despliegue.

**Más información**: [Guía de WebSocket](06-websocket.md)

## 7. Inyección de sidecars

Cubre los mecanismos de inyección del proxy sidecar y su personalización.

### Métodos de inyección

![Diagrama de flujo que muestra cómo, al crear un pod, el webhook de inyección comprueba la etiqueta istio-injection del espacio de nombres, inyecta el sidecar Envoy o lo omite, y ambas rutas convergen en el despliegue del pod.](../../../.gitbook/assets/en-service-mesh-istio-advanced-readme-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-readme-3.html)

El diagrama solo muestra la rama sencilla de la etiqueta del espacio de nombres. La inyección real también depende de las etiquetas del Pod, los selectores de revisión/webhook, las exclusiones y el ciclo de vida de sidecar elegido; cambiar una etiqueta de espacio de nombres no inyecta los Pods que ya están ejecutándose.

**Más información**: [Guía de inyección de sidecars](07-sidecar-injection.md)

## 8. Integración con Argo Rollouts

Lo siguiente es un **fragmento de estrategia** para un Rollout completo con selector, plantilla de Pod y contenedores. También requiere el controlador, Services estable/canary y una ruta `primary` de VirtualService con destinos coincidentes. El análisis y la reversión automática requieren su propio AnalysisTemplate y política; los pasos por sí solos no configuran el análisis de métricas. Solo el tráfico gestionado por la ruta de enrutamiento de Istio prevista sigue estos pesos.

```yaml
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary
      steps:
      - setWeight: 10
      - pause:
          duration: 2m
      - setWeight: 50
      - pause:
          duration: 2m
      stableService: myapp-stable
      canaryService: myapp-canary
```

**Funciones principales**:
- Despliegue canary automático basado en métricas
- Análisis y reversión automática
- Despliegue azul/verde
- Entrega progresiva

**Más información**: [Guía de integración con Argo Rollouts](08-argo-rollouts.md)

## 9. Argo Rollouts con reconocimiento de zonas

Realice despliegues canary con reconocimiento de zonas por zona de disponibilidad.

**Más información**: [Guía de Argo Rollouts con reconocimiento de zonas](09-zone-aware-argo-rollouts.md)

## 10. Autoescalado con KEDA

Implemente autoescalado basado en métricas de Istio mediante KEDA.

### KEDA frente a HPA

| Tema | HPA de Kubernetes | KEDA |
|---|---|---|
|Entradas de métricas|API de métricas de recursos/personalizadas/externas|Los escaladores exponen métricas de backend al HPA|
|Funciones de escalado|Ajuste de réplicas, normalmente con minReplicas 1|Activación/desactivación más un HPA gestionado para 1→N|
|Métricas externas|Requiere un adaptador de métricas externas|Proporciona su adaptador de API de métricas|
|Lógica de consultas|Consume valores numéricos de métricas|Consultas PromQL o de métricas/operaciones matemáticas/Metrics Insights de CloudWatch, según el escalador|

Metrics Server proporciona métricas de recursos; no es el adaptador genérico de métricas externas. KEDA 2.20 requiere Kubernetes ≥1.30; verifique la versión elegida, las API y la compatibilidad de la plataforma independientemente de Istio. El escalado a cero también requiere una señal que siga siendo observable con cero réplicas y una ruta de activación viable. CloudWatch Metrics Insights es distinto de CloudWatch Logs Insights.

### Arquitectura de KEDA

![Las métricas de Envoy se recopilan mediante Prometheus o mediante una canalización configurada de ADOT a CloudWatch; KEDA consulta el backend elegido y gestiona un HPA para la carga de trabajo de destino.](../../../.gitbook/assets/en-service-mesh-istio-advanced-readme-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-readme-4.html)

### Estrategias principales de escalado

Este ejemplo de la API de KEDA 2.20 presupone un Deployment `reviews` existente en `default`, métricas de la carga de trabajo de destino recopiladas y un endpoint privado de Prometheus accesible. Configure autenticación/TLS compatibles para su backend. Devuelve un único valor agregado y utiliza un objetivo AverageValue de 100 solicitudes/s por réplica.


```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-rps-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: reviews
  triggers:
  - type: prometheus
    metadata:
      query: sum(rate(istio_requests_total{reporter="destination",destination_workload="reviews",destination_workload_namespace="default"}[1m]))
      threshold: '100'
      serverAddress: http://prometheus.istio-system.svc.cluster.local:9090
      ignoreNullValues: 'false'
    metricType: AverageValue
  minReplicaCount: 1
  maxReplicaCount: 10
```

El mínimo sigue siendo 1 porque las métricas de tráfico de destino desaparecen cuando el destino no tiene Pods en ejecución; este ejemplo no puede activarse por sí solo desde cero. `ignoreNullValues: false` trata un resultado vacío como un error, en vez de tratar silenciosamente la pérdida de telemetría como cero. No asocie un HPA competidor a la misma carga de trabajo. Las proporciones de latencia/error y los indicadores de disyuntores no son intrínsecamente proporcionales a la capacidad de las réplicas; valide su comportamiento de control en vez de añadirlos como señales de escalado arbitrarias.

**Métricas de escalado**:
- **RPS (solicitudes por segundo)**: basado en solicitudes por segundo
- **Latencia (P50/P95/P99)**: basado en percentiles de latencia
- **Tasa de errores**: basado en la tasa de errores 5xx
- **Disyuntor**: basado en el estado del disyuntor
- **Métricas compuestas**: combinación de varias métricas

**Fuentes de métricas**:
- **Prometheus**: métricas de Istio/Envoy en tiempo real
- **AWS CloudWatch**: métricas de CloudWatch mediante ADOT Collector

**Más información**: [Guía de autoescalado con KEDA](10-keda-autoscaling.md)

## Itinerario de aprendizaje

1. **[Modo Ambient](01-ambient-mode.md)** - Comprender la nueva arquitectura
2. **[Multiclúster](02-multi-cluster.md)** - Configuración multiclúster
3. **[EnvoyFilter](03-envoy-filter.md)** - Personalización avanzada
4. **[Inyección de sidecars](07-sidecar-injection.md)** - Mecanismos de inyección
5. **[gRPC](05-grpc.md)** - Compatibilidad con el protocolo gRPC
6. **[WebSocket](06-websocket.md)** - Compatibilidad con WebSocket
7. **[Caché DNS](04-dns-cache.md)** - Optimización del rendimiento
8. **[Argo Rollouts](08-argo-rollouts.md)** - Entrega progresiva
9. **[Argo Rollouts con reconocimiento de zonas](09-zone-aware-argo-rollouts.md)** - Despliegue basado en zonas
10. **[Autoescalado con KEDA](10-keda-autoscaling.md)** - Autoescalado basado en métricas

## Referencias

- [Funciones avanzadas de Istio](https://istio.io/latest/docs/ops/)
- [Documentación del modo Ambient](https://istio.io/latest/docs/ambient/overview/)
- [Documentación multiclúster](https://istio.io/latest/docs/setup/install/multicluster/)
- [Referencia de EnvoyFilter](https://istio.io/latest/docs/reference/config/networking/envoy-filter/)

## Cuestionario

Para comprobar lo aprendido en este capítulo, realice el [cuestionario de funciones avanzadas de Istio](../../../quizzes/service-mesh/istio/advanced.md).
