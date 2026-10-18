# Compatibilidad con gRPC

> **Base de verificación**: Istio 1.31.0, Kubernetes 1.32–1.37
> **Última revisión**: 16 de octubre de 2026

Istio puede enrutar solicitudes gRPC en texto claro sobre HTTP/2 según la ruta RPC y los metadatos, y balancear nuevas llamadas RPC entre endpoints aptos. Un flujo de larga duración permanece en el backend seleccionado; escalar las réplicas no migra un flujo existente.

## Descripción general

- Identifique explícitamente el puerto del Service como `grpc` o `http2`. El TLS administrado por la aplicación es opaco para un sidecar, salvo que termine en un límite configurado; el mTLS del mesh es una capa de transporte independiente.
- El enrutamiento basado en metadatos trata los encabezados como entrada, no como una identidad autenticada.
- Las sondas de estado, la detección pasiva de instancias atípicas, los plazos del cliente y los reintentos del mesh son mecanismos distintos que requieren configuración.

## Configuración básica

Este ejemplo con sidecar presupone que ya existen cargas de trabajo con `app: grpc-service`, un backend apto con `version: v2` que escucha en el puerto 9090 y una implementación de `mypackage.MyService`. No despliega el servidor. La declaración del puerto `grpc` establece HTTP/2; aquí no hace falta una política general `h2UpgradePolicy`. Verifique los endpoints y las rutas generados, y ejecute una llamada RPC real en el entorno de destino.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grpc-service
  namespace: default
spec:
  selector:
    app: grpc-service
  ports:
  - name: grpc
    port: 9090
    targetPort: 9090
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts: ["grpc-service"]
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
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: grpc-service
  namespace: default
spec:
  host: grpc-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    outlierDetection:
      consecutiveGatewayErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v2
    labels:
      version: v2
```

`LEAST_REQUEST` opera entre hosts aptos para las nuevas solicitudes. `outlierDetection` observa de forma pasiva los fallos del tráfico real; no envía sondas `grpc.health.v1.Health`, y sus contadores siguen la clasificación de errores configurada en Envoy.

## Comprobación de estado de gRPC

Implemente en la aplicación el protocolo estándar de comprobación de estado de gRPC. Kubernetes admite sondas nativas de gRPC para readiness, liveness y startup; por ejemplo, integre este fragmento de readiness en el contenedor existente de la aplicación:

```yaml
# Existing application container fragment, not a complete Pod
name: app
readinessProbe:
  grpc:
    port: 9090
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 1
  failureThreshold: 3
```

La sonda nativa usa un puerto numérico y no admite parámetros personalizados de autenticación o TLS. Revise el listener de estado de la aplicación y la ruta de reescritura de sondas/mTLS de Istio. Readiness determina si un endpoint es apto; liveness reinicia los contenedores y no debería provocar un reinicio ante cada fallo de una dependencia posterior.

## Configuración de reintentos

La siguiente alternativa presupone que `GetItem` es una **lectura unaria idempotente**. La mayoría de los métodos gRPC usan HTTP POST, por lo que el método HTTP por sí solo no permite distinguir las lecturas seguras de las escrituras. Haga coincidir la ruta RPC exacta y mantenga deshabilitados los reintentos del mesh para las demás RPC, incluidos los flujos y las escrituras.

```yaml
# Alternative to the VirtualService above; do not create a second competing route.
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
  namespace: default
spec:
  hosts: ["grpc-service"]
  http:
  - name: idempotent-unary-read
    match:
    - uri:
        exact: /mypackage.MyService/GetItem
    route:
    - destination:
        host: grpc-service
        subset: v2
        port:
          number: 9090
    timeout: 3s
    retries:
      attempts: 2
      perTryTimeout: 1s
      retryOn: unavailable
  - name: other-rpcs
    match:
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
```

`attempts: 2` permite hasta dos reintentos después de la solicitud inicial, dentro del timeout total de 3 segundos del mesh y del plazo propio del cliente. El backoff y el procesamiento implican que no se garantizan tres intentos completados. No reintente automáticamente la cancelación, el vencimiento del plazo ni el agotamiento de recursos. Establezca plazos realistas en el cliente y asegúrese de que el servidor responda a la cancelación; el timeout del mesh no es, por sí solo, un contrato de cancelación de la aplicación.

Las bibliotecas de cliente también pueden realizar reintentos transparentes o configurados. Coordine la responsabilidad y los presupuestos de reintentos entre capas para evitar amplificar la carga. Repetir escrituras requiere garantías de idempotencia o deduplicación en la aplicación, y este ejemplo de ruta no reanuda de forma segura un flujo que ya está entregando respuestas.

## Referencias

- [Selección de protocolos de Istio](https://istio.io/latest/docs/ops/configuration/traffic-management/protocol-selection/)
- [API de reintentos de VirtualService de Istio](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [DestinationRule de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Plazos de gRPC](https://grpc.io/docs/guides/deadlines/)
- [Reintentos de gRPC](https://grpc.io/docs/guides/retry/)
- [Comprobación de estado de gRPC](https://grpc.io/docs/guides/health-checking/)
- [Sondas de Kubernetes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Introducción al balanceo de carga de gRPC](https://grpc.io/blog/grpc-load-balancing/)
