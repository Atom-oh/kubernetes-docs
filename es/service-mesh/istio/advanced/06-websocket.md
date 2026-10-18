# Compatibilidad con WebSocket

> **Base de verificación**: Istio 1.31.0, Kubernetes 1.32–1.37
> **Última revisión**: 16 de octubre de 2026

Istio habilita el protocolo de actualización de WebSocket en el administrador de conexiones HTTP (HCM) que genera. Este ejemplo cubre Upgrade de HTTP/1.1 con TLS terminado en el gateway de entrada. HTTP/2 Extended CONNECT y HTTP/3 requieren compatibilidad y configuración específicas en toda la ruta.

## Configuración básica

Requisitos previos: un Deployment/Service de gateway de entrada existente que exponga el puerto 443 con la etiqueta indicada; DNS funcional para `ws.example.com`; un Secret `ws-tls` con certificado/clave en el espacio de nombres donde se ejecuta la carga de trabajo del gateway; y Pods existentes con `app: websocket-service` que atiendan `/ws` en el puerto 8080. Sustituya el dominio de ejemplo por el nombre real cubierto por el certificado. Los siguientes recursos no despliegan la aplicación ni aprovisionan el balanceador de carga o el certificado.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
  namespace: default
spec:
  selector:
    app: websocket-service
  ports:
  - name: http
    port: 8080
    targetPort: 8080
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
  namespace: default
spec:
  hosts: ["ws.example.com"]
  gateways: ["istio-system/websocket-gateway"]
  http:
  - match:
    - uri:
        exact: /ws
    - uri:
        prefix: /ws/
    route:
    - destination:
        host: websocket-service.default.svc.cluster.local
        port:
          number: 8080
    retries:
      attempts: 0
```

La ruta está vinculada explícitamente al Gateway que se muestra a continuación. Hacer coincidir la ruta evita una comprobación innecesaria del encabezado `Upgrade`, que distingue mayúsculas de minúsculas; aun así, la aplicación valida el protocolo de enlace de WebSocket. Los reintentos del mesh están deshabilitados. Se omite el timeout de solicitud de VirtualService y se usa el timeout de ruta de Istio, deshabilitado de forma predeterminada; esto no deshabilita todos los timeouts de conexión o de flujo de la ruta.

## Configuración del Gateway

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: websocket-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: ws-tls
    hosts: ["ws.example.com"]
```

Los clientes usan `wss://ws.example.com/ws`. El gateway termina la conexión TLS del cliente y después usa el transporte configurado para la malla de servicios y el backend. Siguen siendo necesarios la autenticación de la aplicación y las comprobaciones de `Origin` y autorización. Si un proxy o balanceador de carga termina TLS antes, revise por separado el protocolo, el certificado y la confianza en los encabezados de esa topología.

## Administración de conexiones y timeouts

Esta DestinationRule opcional conserva los límites del ejemplo original como **valores ilustrativos para pruebas de carga**:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: websocket-service
  namespace: default
spec:
  host: websocket-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 1000
      http:
        http1MaxPendingRequests: 1000
        idleTimeout: 3600s
```

`maxConnections` y las solicitudes pendientes son controles del pool de destinos de cada proxy, no una garantía de capacidad de WebSocket para todo el clúster. `connectionPool.http.idleTimeout` significa que una conexión HTTP no tiene solicitudes o flujos activos; no establece una duración máxima de una hora ni un límite de mensajes inactivos para un WebSocket activo.

Inspeccione los ajustes generados de inactividad de flujos HCM/rutas, la duración máxima de flujos/conexiones, la política de latidos/cierre de la aplicación y el timeout de inactividad de cada intermediario. La generación HCM de Istio y las ConnectionSettings instaladas pueden reemplazar los valores predeterminados de Envoy. Los filtros de almacenamiento en búfer/procesamiento de cuerpos pueden ser incompatibles con las actualizaciones. Los WebSocket existentes no migran cuando se escala el número de réplicas; planifique el drenaje y la reconexión compatible con la aplicación, sin repetir escrituras a ciegas.

## Verificación

```bash
# Inspect the selected gateway and backend configuration.
istioctl proxy-config routes <gateway-pod> -n istio-system
istioctl proxy-config clusters <gateway-pod> -n istio-system --fqdn websocket-service.default.svc.cluster.local

# Bounded HTTP/1.1 handshake check; certificate validation remains enabled.
curl --http1.1 --include --max-time 5 https://ws.example.com/ws -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
```

En esta comprobación de HTTP/1.1, un servidor válido suele responder con 101 y un `Sec-WebSocket-Accept` correspondiente. El comando curl comprueba solo el protocolo de enlace; su límite de 5 segundos puede cerrar una conexión que seguiría abierta y devolver el código de salida 28. Use un cliente WebSocket real para probar tramas, ping/pong, autenticación de la aplicación, períodos prolongados de inactividad, códigos de cierre y el comportamiento de reconexión durante las actualizaciones. Esta auditoría de documentación no probó ningún despliegue ni sesión activa.

## Referencias

- [Actualizaciones HTTP de Envoy](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/http/upgrades)
- [Tipos de timeout de Envoy](https://www.envoyproxy.io/docs/envoy/latest/faq/configuration/timeouts)
- [Entrada segura de Istio](https://istio.io/latest/docs/tasks/traffic-management/ingress/secure-ingress/)
- [VirtualService de Istio](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [DestinationRule de Istio](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Generación de HCM en Istio 1.31](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/listener_builder.go)
