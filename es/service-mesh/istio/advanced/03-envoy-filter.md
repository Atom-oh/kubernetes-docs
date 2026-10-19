# EnvoyFilter

> **Base de verificación**: Istio 1.31.0, Kubernetes 1.32–1.37; sidecars y gateways Envoy de Istio
> **Última revisión**: 16 de octubre de 2026

EnvoyFilter es una función avanzada que permite personalizar directamente la configuración del proxy Envoy.

## Tabla de contenido

1. [Descripción general](#overview)
2. [Estructura](#structure)
3. [Principales casos de uso](#main-use-cases)
4. [X-Forwarded-For y configuración de saltos](#x-forwarded-for-and-hop-settings)
5. [Configuración de respuestas estáticas](#static-response-configuration)
6. [Ejemplos prácticos](#practical-examples)
7. [Prácticas recomendadas](#best-practices)
8. [Solución de problemas](#troubleshooting)

## Descripción general {#overview}

Estos ejemplos son alternativas independientes. Si se aplican todos a la misma carga de trabajo, se acumularán filtros, rutas y políticas. Comprueba los namespaces, las etiquetas y los listeners reales, integra los cambios con la configuración existente y verifica la configuración Envoy generada y el comportamiento de las solicitudes en un entorno de pruebas. EnvoyFilter depende de API internas de Envoy y debe volver a validarse con cada actualización de Istio; no es compatible con los waypoints del modo ambient.

Con EnvoyFilter puedes:
- Añadir, modificar o eliminar encabezados personalizados
- Aplicar limitación de tasa
- Integrar autorización externa
- Integrar complementos WASM

## Estructura {#structure}

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-filter
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
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                request_handle:headers():replace("x-custom-header", "value")
              end
```

## Principales casos de uso {#main-use-cases}

### 1. Añadir encabezados personalizados

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: add-header
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
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                request_handle:headers():replace("x-client-service", "myapp")
              end
```

### 2. Limitación de tasa

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value: {numerator: 100, denominator: HUNDRED}
          filter_enforced:
            default_value: {numerator: 100, denominator: HUNDRED}
```

Este bucket de tokens se aplica **a cada proceso proxy**: comienza con una ráfaga de 100 tokens y repone 10 tokens por segundo. No es un límite global entre réplicas. Los porcentajes de habilitación y aplicación deben configurarse explícitamente para que se rechacen las solicitudes.

### 3. Complemento WASM

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: wasm-filter
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.wasm
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm
          config:
            vm_config:
              runtime: "envoy.wasm.runtime.v8"
              code:
                local:
                  filename: "/var/local/lib/wasm-filters/my_plugin.wasm"
```

El ejemplo local de Wasm presupone que ya hay un módulo compatible montado en esa ruta del contenedor proxy mediante un volumen de solo lectura. Un archivo del contenedor de la aplicación no queda disponible automáticamente, y este YAML no descarga el módulo. Valida la compatibilidad del módulo, la ABI, el entorno de ejecución y el comportamiento ante fallos; para distribuirlo, prefiere la [API WasmPlugin](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/).

## X-Forwarded-For y configuración de saltos {#x-forwarded-for-and-hop-settings}

### Descripción general de X-Forwarded-For

Un proxy HTTP suele añadir la dirección del **cliente que se conectó a él**, no la suya propia. Con el modo `append` predeterminado de ALB, el Gateway recibe `203.0.113.5` si el cliente se conecta directamente, o `203.0.113.5, 192.0.2.20` si la solicitud pasa por CloudFront. El par directo del Gateway es ALB. Estas direcciones de documentación no son rangos IP reales de CloudFront.

### Opciones de configuración de XFF

Prefiere la [configuración oficial de la topología del gateway](https://istio.io/latest/docs/ops/configuration/traffic-management/network-topologies/) con `gatewayTopology.numTrustedProxies`. Integra este **fragmento de la plantilla Pod** en el Deployment de ingreso existente, reinicia los Pods del Gateway afectados e inspecciona la configuración efectiva.

```yaml
# Existing ingress Deployment: spec.template fragment, not a complete Deployment
metadata:
  annotations:
    proxy.istio.io/config: |
      gatewayTopology:
        numTrustedProxies: 1
```

La alternativa de nivel inferior es este EnvoyFilter. No configures valores en conflicto mediante ambos mecanismos. Verifica el namespace de ingreso real y la etiqueta de Pod `istio: ingressgateway`.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: gateway-xff-config
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: NETWORK_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
    patch:
      operation: MERGE
      value:
        name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          use_remote_address: true
          xff_num_trusted_hops: 1
          skip_xff_append: false
          via: istio-gateway
```

| Opción | Significado |
|---|---|
| `use_remote_address: true`, saltos 0 | Usa el par de la conexión directa |
| `true`, saltos N>0 | Usa la **enésima dirección desde la derecha en el XFF recibido** |
| `false`, saltos N | Usa la dirección N+1 desde la derecha |
| Hay muy pocas direcciones XFF | Recurre al par directo; esto no significa que el acceso esté permitido |
| `skip_xff_append: true` | No añade aquí otra dirección a XFF; es independiente de la selección de dirección |
| `via` | Añade un identificador Via a las solicitudes o respuestas; no es autenticación |

No configures `use_remote_address: false` solo porque un servicio sea interno: podrías confiar en un XFF enviado por quien llama. Inspecciona primero las conexiones reales y las transformaciones de encabezados. La decisión del Gateway es **una propiedad de su propio flujo de solicitudes**; no pasa automáticamente a ser la dirección `remote.ip` de confianza del Envoy de backend.

### Configuración según el escenario

Estos valores presuponen `use_remote_address: true`, que cada proxy HTTP añada el par de su conexión y que las rutas que permiten eludir el flujo estén bloqueadas.

| Ruta | XFF que recibe el Gateway | Par directo | Saltos de confianza |
|---|---|---|---|
| Cliente → ALB → Gateway | `203.0.113.5` | ALB | 1 |
| Cliente → CloudFront → ALB → Gateway | `203.0.113.5, 192.0.2.20` | ALB | 2 |
| Cliente → CloudFront → NLB → ALB → Gateway | El mismo, si la configuración de NLB con destinos ALB conserva la dirección del cliente | ALB | 2 |
| Cliente → Gateway directo | Valor arbitrario enviado por quien llama | Cliente | 0 |

NLB opera en la capa L4 y no modifica XFF. Esto no significa que cualquier configuración de NLB conserve la dirección original del socket. Verifica el tipo de destino, los puertos de listener y destino compatibles, la conservación de direcciones y los encabezados que se reciben realmente. Los modos `preserve` y `remove` de ALB, otras CDN, el protocolo PROXY y las rutas alternativas requieren un análisis aparte.

### Ejemplo para obtener la IP real del cliente

No trates como confiable el valor situado más a la izquierda de XFF. En el Gateway con el límite de confianza configurado arriba, usa la dirección calculada por Envoy para el diagnóstico. La API de Lua devuelve una **cadena**, que puede incluir la notación IPv6 o el puerto; no devuelve un objeto de dirección.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: gateway-client-address
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
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
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                local address = handle:streamInfo():downstreamRemoteAddress()
                handle:headers():replace("x-client-address", address)
              end
```

`x-client-address` no sirve para autenticar la aplicación. Úsalo solo para el diagnóstico si el Gateway de confianza lo sobrescribe y se impide el acceso directo al backend. Define límites de privacidad y retención para los registros de direcciones y encabezados.

### Restricción selectiva de IP por aplicación (Gateway + AuthorizationPolicy)

Aplica las restricciones de IP externas **en el Gateway que determina la IP original**, con el encabezado HTTP Host como ámbito para las aplicaciones F y G. Las aplicaciones A–E no coinciden con esta regla DENY. También se aplican las políticas existentes de malla, namespace y Gateway, así como la autenticación de la aplicación; que no haya un archivo de política específico para una aplicación no garantiza el acceso.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: restricted-app-ingress
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: DENY
  rules:
  - from:
    - source:
        notRemoteIpBlocks: ["203.0.113.0/24"]
    to:
    - operation:
        hosts:
        - "app-f.example.com"
        - "app-f.example.com:*"
        - "app-g.example.com"
        - "app-g.example.com:*"
```

El Gateway debe terminar HTTP y dirigir cada Host a la aplicación prevista. Usa un Gateway dedicado que termine HTTP. Si hay listeners mixtos con TCP passthrough, limita la política a puertos verificados de la carga de trabajo; la ausencia de atributos HTTP puede hacer que coincida una regla DENY. Revisa alias, hosts comodín y otras rutas que podrían exponer F o G. Protege también los backends contra el acceso directo, por ejemplo, con mTLS y una AuthorizationPolicy que permita la cuenta de servicio real del Gateway. Las restricciones de IP no sustituyen la autenticación de usuarios.

### Control de acceso por IP basado en XFF

Los siguientes ejemplos son alternativas independientes para un **API Gateway dedicado**. Cuando una política ALLOW selecciona una carga de trabajo, la solicitud debe coincidir con una regla ALLOW. Varias políticas ALLOW se combinan; no apiles estos ejemplos en un Gateway compartido sin tener en cuenta las demás aplicaciones.

#### 1. Lista de direcciones IP permitidas y denegadas

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-ip-allowlist
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.10/32", "203.0.113.11/32", "2001:db8:1234::/48"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-ip-denylist
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: DENY
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.11/32"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
```

La dirección permitida `203.0.113.11` sigue siendo rechazada por DENY. Istio evalúa CUSTOM, DENY y luego ALLOW; AUDIT no cambia la decisión. Elige `remoteIpBlocks` para las direcciones originales derivadas de XFF de confianza o del protocolo PROXY, y `ipBlocks` para el origen del paquete recibido, según la conexión real.

#### 2. IP + ruta + método

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-path-ip-policy
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.10/32"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/admin", "/admin/*"]
  - from:
    - source:
        remoteIpBlocks: ["10.0.0.0/8"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/api/v1/*"]
        methods: ["GET"]
  - to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/api/v1/public/*"]
        methods: ["GET", "POST"]
```

Protege tanto `/admin` como `/admin/*`. Si omites la condición de origen en la ruta pública, se cubren IPv4 e IPv6. La regla `10.0.0.0/8` solo tiene sentido en una ruta de cliente privado donde realmente se observe esa dirección; no puede recuperar una dirección oculta tras una NAT de Internet.

### Verificación y depuración de XFF

```bash
# Local CLI reads the effective gateway configuration; no curl binary in proxy required.
istioctl proxy-config listeners <gateway-pod> -n istio-system -o json |
  jq '.. | objects |
      select(.["@type"]? == "type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager") |
      {useRemoteAddress, xffNumTrustedHops, skipXffAppend}'

# Through the real ALB/CDN path, from a source outside the allowed NAT range:
curl -i https://app-f.example.com/
curl -i -H "X-Forwarded-For: 203.0.113.10" https://app-f.example.com/
# Both must be denied. A user-supplied header must not grant access.

# Run this separately from the real approved NAT egress:
curl -i https://app-f.example.com/

kubectl get authorizationpolicy -n istio-system
kubectl logs -n istio-system <gateway-pod> -c istio-proxy
```

Anteponer a XFF una IP permitida cuando el origen no está permitido debe seguir dando un fallo. Prueba el acceso permitido desde la salida NAT aprobada real. Que una solicitud directa al Gateway tenga éxito con un encabezado falsificado demuestra que se puede eludir el control, no que la validación haya funcionado. Prueba también IPv6, la ausencia de XFF o un XFF corto, el acceso directo al Gateway, los alias de Host y las rutas alternativas.

Distingue `%DOWNSTREAM_DIRECT_REMOTE_ADDRESS%` (par del socket), `%DOWNSTREAM_REMOTE_ADDRESS%` (dirección calculada), `%REQ(X-FORWARDED-FOR)%` y `%RESPONSE_CODE_DETAILS%` en los registros de acceso. Activa los registros con Telemetry y configura su formato en el proveedor de registros de acceso seleccionado para la malla; consulta [ProxyConfig y configuración de observabilidad](#envoy-configuration-with-proxyconfig).

### Consideraciones de seguridad

Limita cada salto descendente **al proxy de confianza real**, por ejemplo, ALB → Gateway y CloudFront → ALB, mediante grupos de seguridad, controles de red y controles de acceso al origen. El número de saltos no autentica al remitente; `use_remote_address: true` por sí solo no evita la suplantación. Eliminar un encabezado más adelante en Lua no revierte una dirección calculada previamente ni una decisión de autorización anterior.

## Configuración de respuestas estáticas {#static-response-configuration}

Puedes devolver respuestas estáticas directamente, sin pasar por servicios de backend, para solicitudes concretas. Esto resulta útil para el modo de mantenimiento, páginas de error o respuestas a comprobaciones de estado, entre otros casos.

### Descripción general de las respuestas estáticas

![Diagrama de flujo: una solicitud del cliente llega al proxy Envoy, que devuelve la respuesta estática directamente al cliente cuando se cumple una condición; de lo contrario, la envía al servicio de backend.](../../../.gitbook/assets/en-service-mesh-istio-advanced-03-envoy-filter-7.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-03-envoy-filter-7.html)

### Casos de uso

1. **Modo de mantenimiento**: devolver 503 Service Unavailable
2. **Endpoint de comprobación de estado**: devolver 200 OK
3. **Páginas de error personalizadas**: respuestas JSON o HTML
4. **Respuestas de prueba o simulación**: respuestas predefinidas para rutas específicas
5. **Rechazo rápido**: devolver 401 Unauthorized inmediatamente si falla la autenticación

### Guía para elegir el método de implementación

Istio ofrece varias formas de implementar respuestas estáticas:

| Método | Cuándo usarlo | Ventajas | Desventajas |
|------|----------|------|------|
| **VirtualService** | Respuestas estáticas sencillas e integración con reglas de enrutamiento | Declarativo, fácil de entender | Personalización limitada |
| **AuthorizationPolicy** | Control de acceso basado en IP o encabezado | Se integra con las políticas de seguridad | No se limita a respuestas estáticas |
| **EnvoyFilter** | Solo cuando los métodos anteriores no bastan | Flexibilidad máxima | Complejo, con riesgo durante las actualizaciones |

**Recomendación**: cuando sea posible, usa primero **VirtualService** y **AuthorizationPolicy**; recurre a EnvoyFilter solo cuando sea necesario.

### Implementación de respuestas estáticas con VirtualService

#### 1. Respuesta estática básica (directResponse)

La marca de tiempo es una cadena fija de ejemplo, no la hora actual. Comprueba el límite del cuerpo de la respuesta en la configuración de rutas generada. Istio 1.31 establece un límite de 1 MiB para estas rutas VirtualService de salida; Envoy sin modificar usa 4 KiB. Los cuerpos estáticos grandes consumen memoria del proxy. Estos VirtualService de salida de la malla son alternativas independientes; no los apiles para el mismo host.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
  namespace: default
spec:
  hosts:
  - api-service
  http:
  # Maintenance mode
  - match:
    - uri:
        exact: "/api/v1"
    - uri:
        prefix: "/api/v1/"
    directResponse:
      status: 503
      body:
        string: |
          {
            "error": {
              "code": "SERVICE_UNAVAILABLE",
              "message": "The service is currently under maintenance",
              "timestamp": "2025-11-26T10:00:00Z",
              "retry_after": 3600
            }
          }
    headers:
      response:
        set:
          content-type: "application/json"
          retry-after: "3600"
```

**Resultado**:
```text
$ curl -i http://api-service/api/v1/users
HTTP/1.1 503 Service Unavailable
content-type: application/json
retry-after: 3600

{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "The service is currently under maintenance",
    "timestamp": "2025-11-26T10:00:00Z",
    "retry_after": 3600
  }
}
```

#### 2. Punto de comprobación de estado

Una respuesta estática 200 solo comprueba el enrutamiento del proxy. Usa una comprobación real del backend si el estado de readiness de Kubernetes o el estado del destino de ALB deben reflejar el estado de salud de la aplicación.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-health
  namespace: default
spec:
  hosts:
  - api-service
  http:
  # Health check path
  - match:
    - uri:
        exact: "/health"
    directResponse:
      status: 200
      body:
        string: "OK"

  # Normal traffic
  - route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

#### 3. Bloquear rutas específicas

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: block-admin
  namespace: default
spec:
  hosts:
  - api-service
  http:
  # Block Admin paths
  - match:
    - uri:
        exact: "/admin"
    - uri:
        prefix: "/admin/"
    directResponse:
      status: 403
      body:
        string: |
          {
            "error": "Access to admin endpoints is forbidden"
          }
    headers:
      response:
        set:
          content-type: "application/json"

  # Normal traffic
  - route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

#### 4. Simulación de errores con inyección de fallos

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: fault-injection
  namespace: default
spec:
  hosts:
  - api-service
  http:
  - fault:
      abort:
        httpStatus: 503
        percentage:
          value: 100  # Apply to 100% traffic
    route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

### Control de acceso con AuthorizationPolicy

`ipBlocks` evalúa el origen del paquete recibido. Puede ser el cliente original en un ingreso L4 que conserva el origen, o un proxy o una NAT detrás de ALB u otro intermediario. Para las direcciones obtenidas de XFF, usa los ejemplos anteriores de `remoteIpBlocks` en el Gateway. Si una política ALLOW seleccionada ya rechaza las solicitudes que no coinciden, no hace falta añadir otra regla DENY complementaria.

#### Respuesta de denegación personalizada

Esto unifica **todas las respuestas HTTP 403 generadas localmente por este Gateway**. No modifica las respuestas 403 del backend ni todas las denegaciones TCP. Usa el código genérico `FORBIDDEN` en vez de inferir que se denegó una IP a partir del texto del cuerpo. Puede que un filtro Lua posterior no se ejecute si un filtro RBAC anterior rechaza la solicitud; usa `local_reply_config` de HCM y revisa el orden y el ámbito al integrar los mappers existentes.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-local-forbidden
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: NETWORK_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
    patch:
      operation: MERGE
      value:
        name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          local_reply_config:
            mappers:
            - filter:
                status_code_filter:
                  comparison:
                    op: EQ
                    value:
                      default_value: 403
                      runtime_key: local_reply_403
              body_format_override:
                json_format:
                  error: "Access denied"
                  code: "FORBIDDEN"
```

### Configuración de Envoy con ProxyConfig {#envoy-configuration-with-proxyconfig}

El recurso ProxyConfig de `networking.istio.io` tiene campos distintos del mensaje ProxyConfig de la malla. Expone opciones como `concurrency`, `environmentVariables` e `image`; no acepta campos arbitrarios de registro, trazado o pools de conexiones. Los cambios requieren reiniciar los Pods afectados.

#### Hilos de trabajo y observabilidad

```yaml
apiVersion: networking.istio.io/v1beta1
kind: ProxyConfig
metadata:
  name: api-service-config
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  concurrency: 4
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: api-observability
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  accessLogging:
  - providers:
    - name: envoy
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 1
```

Los proveedores de registros de acceso `envoy` y trazas `otel-tracing` deben existir previamente en `extensionProviders` de la malla. Configura allí el formato y la salida de los registros, así como el endpoint OTLP y TLS. `concurrency: 4` solicita cuatro hilos de trabajo; comprueba la capacidad de CPU y la carga. El muestreo al inicio de la traza configurado al 1 % no garantiza la retención completa de las trazas.

#### Estadísticas y periodo de gracia para el apagado

```yaml
# Existing application Deployment: spec.template fragment
metadata:
  annotations:
    proxy.istio.io/config: |
      terminationDrainDuration: 5s
      proxyStatsMatcher:
        inclusionRegexps:
        - ".*outlier_detection.*"
        - ".*upstream_rq_retry.*"
        inclusionSuffixes:
        - upstream_rq_timeout
```

Integra esto en la plantilla Pod del Deployment de la aplicación y reinicia los Pods afectados. El periodo de gracia de terminación de Kubernetes debe permitir el apagado de la aplicación y el drenaje del proxy. Las estadísticas Envoy adicionales aumentan el número de series y el coste de memoria.

#### Pool de conexiones de destino

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-outbound-pool
  namespace: default
spec:
  host: api-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 10s
        maxConnections: 10000
```

Estos son ajustes de conexiones salientes del proxy para este destino; no limitan las solicitudes simultáneas de todo el Gateway ni configuran el timeout de la aplicación. Valida los límites del ejemplo bajo carga.

### Ejemplo integrado: VirtualService + AuthorizationPolicy

Este es un **fragmento de laboratorio HTTP independiente**. Requiere un Deployment y un Service de ingreso Gateway existentes que expongan el puerto 80, `default/api-service` en el puerto 8080 del Service con endpoints en estado saludable, DNS y enrutamiento de ALB funcionales, y la configuración de confianza de XFF validada arriba. El uso externo también requiere un límite TLS revisado y protección contra el acceso directo al backend. Este fragmento no se ha desplegado ni probado con carga de producción.

La autorización y el enrutamiento se evalúan en el mismo Gateway. Las rutas pública, de comprobación de estado y retirada están permitidas explícitamente; el resto de las rutas no coincidentes se deniega. `/health` solo demuestra que se alcanza la ruta del proxy, no la salud de la aplicación o la base de datos. Los reintentos de malla son 0 en la ruta general, que puede transportar escrituras.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: api-lab
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts: ["api.example.com"]
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-access-control
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.10/32"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/api/v1/admin", "/api/v1/admin/*"]
  - to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/health", "/api/v0/*", "/api/v1/public/*"]
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-routes
  namespace: default
spec:
  hosts: ["api.example.com"]
  gateways: ["istio-system/api-lab"]
  http:
  - match:
    - uri:
        exact: /health
    directResponse:
      status: 200
      body:
        string: '{"status":"proxy-route-reachable"}'
    headers:
      response:
        set:
          content-type: application/json
          cache-control: no-store
  - match:
    - uri:
        prefix: /api/v0/
    directResponse:
      status: 410
      body:
        string: '{"error":"API v0 is retired","supported_versions":["v1","v2"]}'
    headers:
      response:
        set:
          content-type: application/json
          cache-control: no-store
  - route:
    - destination:
        host: api-service.default.svc.cluster.local
        port:
          number: 8080
    timeout: 30s
    retries:
      attempts: 0
```

### Respuestas estáticas dinámicas con Lua

Los scripts Lua pueden generar respuestas estáticas dinámicas según distintas condiciones.

#### Detección automática de la ventana de mantenimiento

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: maintenance-window
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              local function is_maintenance(hour)
                return hour >= 2 and hour < 4
              end

              function envoy_on_request(request_handle)
                -- Current time (UTC)
                local current_hour = tonumber(os.date("!%H"))

                -- Daily maintenance window 2-4 AM
                if is_maintenance(current_hour) then
                  request_handle:respond(
                    {[":status"] = "503",
                     ["content-type"] = "application/json",
                     ["retry-after"] = "60",
                     ["cache-control"] = "no-store"},
                    '{"error": "Maintenance in progress", "window": "02:00-04:00 UTC"}'
                  )
                end
              end
```

#### Respuesta basada en el encabezado de la solicitud

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: header-based-response
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                local api_version = request_handle:headers():get("x-api-version")

                -- Unsupported API version
                if api_version and api_version == "v1" then
                  request_handle:respond(
                    {[":status"] = "410",
                     ["content-type"] = "application/json"},
                    '{"error": "API v1 is deprecated", "supported_versions": ["v2", "v3"]}'
                  )
                end
              end
```

### Integración con VirtualService

Un único `directResponse` puede establecer el estado y el cuerpo del mensaje de mantenimiento. Un filtro Lua del lado del destino no puede modificar un fallo que ya haya generado el VirtualService del lado de origen, y los encabezados de respuesta no incluyen la `:path` de la solicitud. Este es un ejemplo independiente de salida de la malla, no un ejemplo de autorización. Para el ingreso, enlaza explícitamente el gateway y el host externo como en el ejemplo anterior.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: maintenance-response
  namespace: default
spec:
  hosts: ["api-service"]
  http:
  - match:
    - uri:
        exact: /maintenance
    - uri:
        prefix: /maintenance/
    directResponse:
      status: 503
      body:
        string: '{"message":"Service under maintenance"}'
    headers:
      response:
        set:
          content-type: application/json
          cache-control: no-store
          retry-after: "60"
  - route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

### Escenarios prácticos

#### Escenario 1: bloquear el tráfico durante un despliegue azul/verde

Esto cambia intencionadamente a 503 todas las rutas HTTP entrantes de la carga de trabajo v1 seleccionada. No implementa una migración sin interrupciones ni el drenaje de conexiones. Protobuf `MERGE` cambia la opción `Route` del `oneof` a `direct_response`; no controla rechazos de filtros anteriores ni rutas TCP. `cutoff_date` es un valor fijo de ejemplo que debes sustituir por la programación real del despliegue.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: deployment-block
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-service
      version: v1  # Block only old version
  configPatches:
  - applyTo: HTTP_ROUTE
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: MERGE
      value:
        direct_response:
          status: 503
          body:
            inline_string: |
              {
                "message": "This version is being deprecated",
                "migration": {
                  "new_endpoint": "https://api-v2.example.com",
                  "cutoff_date": "2025-12-31"
                }
              }
        response_headers_to_add:
        - header:
            key: "Content-Type"
            value: "application/json"
        - header:
            key: "X-Migration-Required"
            value: "true"
```

#### Escenario 2: respuesta 429 al superar el límite de tasa

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: ratelimit-response
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  # Rate Limit filter
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            runtime_key: local_rate_limit_enforced
            default_value:
              numerator: 100
              denominator: HUNDRED
          local_rate_limit_per_downstream_connection: false
          # Custom 429 response
          status:
            code: 429
          response_headers_to_add:
          - header:
              key: x-local-rate-limit
              value: "true"
            append_action: OVERWRITE_IF_EXISTS_OR_ADD
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit-json
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: NETWORK_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
    patch:
      operation: MERGE
      value:
        name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          local_reply_config:
            mappers:
            - filter:
                status_code_filter:
                  comparison:
                    op: EQ
                    value:
                      default_value: 429
                      runtime_key: local_reply_429
              body_format_override:
                json_format:
                  error: "Too many requests"
                  code: "RATE_LIMIT_EXCEEDED"
```

Ambos recursos seleccionan la misma carga de trabajo. El mapeador convierte en JSON las respuestas 429 generadas localmente; las respuestas 429 del upstream no cambian. La reposición de tokens no garantiza cuándo podrá volver a intentarlo correctamente cada cliente, por lo que no se envía un `Retry-After: 60` arbitrario.

#### Escenario 3: respuesta de prueba para un despliegue canario

Úsalo solo en una carga de trabajo de pruebas aislada. Quien llama puede proporcionar este encabezado; la respuesta 200 resultante no demuestra autenticación, ejecución del backend ni el estado de la versión. Cualquier exposición operativa requiere autorización validada por separado y confianza en los encabezados.

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: canary-test-response
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
      version: canary
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                local test_header = request_handle:headers():get("x-canary-test")

                -- Return predefined response if canary test header present
                if test_header == "dry-run" then
                  request_handle:respond(
                    {[":status"] = "200",
                     ["content-type"] = "application/json",
                     ["x-canary-version"] = "v2.0.0"},
                    '{"message": "Canary version response", "version": "v2.0.0"}'
                  )
                end
              end
```

### Pruebas y verificación

#### Prueba de respuestas estáticas

Usa un cliente de pruebas cuyo tráfico cruce realmente el proxy que implementa el ejemplo elegido. `/health` o los encabezados informativos por sí solos no validan autenticación ni autorización.

```bash
curl -i http://api-service:8080/api/v1
curl -i http://api-service:8080/health
curl -i http://api-service:8080/admin
curl -i http://api-service:8080/admin/users
```

Prueba el predicado de mantenimiento en un entorno aislado de Lua con las horas UTC 1, 2, 3 y 4; se esperan los resultados false, true, true y false. No cambies los relojes de los Pods o nodos. Para una prueba real de integración del filtro, usa una entrada de tiempo controlada o una función temporal revisada en un entorno aislado; después, restablece la función normal.

Para la limitación de tasa, dirige las solicitudes a un proxy conocido y mide conjuntamente los 100 tokens iniciales, la reposición de 10 por segundo, el tiempo transcurrido y la cantidad real de respuestas 429. Una secuencia de 150 solicitudes con curl no garantiza que haya respuestas 429. El número de réplicas y la distribución de carga requieren pruebas independientes.

#### Verificar la configuración de Envoy

```bash
# 1. Verify static response route
istioctl proxy-config routes <pod-name> -n default -o json | \
  jq '.[] | .virtualHosts[]? | .routes[]? | select(.directResponse != null)'

# 2. Check full route configuration
istioctl proxy-config routes <pod-name> -n default

# 3. Verify EnvoyFilter applied
kubectl get envoyfilter -n default maintenance-window -o yaml

# 4. Verify via Envoy Admin API
kubectl port-forward -n default <pod-name> 15000:15000
# Run in a second local terminal while port-forward is active:
curl http://127.0.0.1:15000/config_dump | jq '.configs[] | select(.["@type"] == "type.googleapis.com/envoy.admin.v3.RoutesConfigDump")'
```

### Prácticas recomendadas {#best-practices}

1. **Mensajes de error claros**:
   - Indica a los usuarios la causa y la solución
   - Especifica el tiempo de reintento mediante el encabezado `Retry-After`

2. **Formato de error coherente**:
   - Usa el mismo esquema JSON para todas las respuestas de error
   - Mantén la coherencia entre los códigos de estado HTTP y los códigos de error

3. **Registro y supervisión**:
   - Registra cuándo se devuelven respuestas estáticas
   - Haz seguimiento de su frecuencia con métricas

4. **Aplicación gradual**:
   - Aplica los cambios gradualmente al activar el modo de mantenimiento
   - Prueba con un despliegue canario antes de aplicarlos por completo

5. **Plan de reversión**:
   - Restaura la configuración revisada y luego verifica la aceptación de xDS, las rutas y las solicitudes
   - Mantén scripts de reversión automatizada para emergencias

### Precauciones

1. **Prioridad**: el comportamiento de la respuesta depende del proxy que la procese, del orden de los filtros y de la ruta generada
2. **Rendimiento**: los scripts Lua se ejecutan en cada solicitud; ten en cuenta su impacto en el rendimiento
3. **Seguridad**: evita exponer información confidencial en los mensajes de error
4. **Caché**: las respuestas estáticas también necesitan encabezados `Cache-Control`
5. **Métricas**: inspecciona `response_code`, `details`, `flags` y `reporter`; las respuestas estáticas no tienen por qué crear una familia de métricas independiente

## Ejemplos prácticos {#practical-examples}

### Ejemplo 1: registro de solicitudes y respuestas

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: request-response-logging
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
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
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                request_handle:logInfo("Request method: " .. (request_handle:headers():get(":method") or "unknown"))
              end

              function envoy_on_response(response_handle)
                response_handle:logInfo("Response: " .. (response_handle:headers():get(":status") or "unknown"))
              end
```

### Ejemplo 2: validación de JWT

Usa RequestAuthentication de Istio junto con AuthorizationPolicy. Sustituye el emisor, la audiencia y la URL JWKS de ejemplo por los valores reales del proveedor; verifica que el verificador pueda alcanzar DNS, TLS y JWKS. RequestAuthentication por sí solo acepta que falte el token; la política ALLOW exige una identidad verificada. Comprueba que otra política ALLOW de la carga de trabajo no conceda un acceso más amplio.

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: api-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  jwtRules:
  - issuer: https://issuer.example.com/
    audiences: ["api.example.com"]
    jwksUri: https://issuer.example.com/.well-known/jwks.json
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-require-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["*"]
```

## Prácticas recomendadas

1. **Usa `workloadSelector`**: aplícalo solo a cargas de trabajo específicas
2. **Empieza en un entorno de pruebas**: realiza pruebas suficientes antes de pasar a producción
3. **Compatibilidad con la versión de Istio**: comprueba la API en cada versión
4. **Supervisión del rendimiento**: vigila el rendimiento después de añadir EnvoyFilter

## Solución de problemas {#troubleshooting}

```bash
# Check EnvoyFilter
kubectl get envoyfilter -A

# Verify Envoy configuration
istioctl proxy-config listeners <pod-name> -n <namespace> -o json

# Check logs
kubectl logs -n <namespace> <pod-name> -c istio-proxy
```

## Referencias

- [Referencia de EnvoyFilter](https://istio.io/latest/docs/reference/config/networking/envoy-filter/)
- [Documentación de Envoy](https://www.envoyproxy.io/docs/envoy/latest/)
- [Complementos WASM](https://istio.io/latest/docs/concepts/wasm/)
- [XFF y direcciones de confianza](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers)
- [Autorización de ingreso de Istio](https://istio.io/latest/docs/tasks/security/authorization/authz-ingress/)
- [Encabezados X-Forwarded de ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html)
- [Comportamiento de solicitudes de CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html)
- [Destinos de NLB de tipo Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/application-load-balancer-target.html)
- [API del filtro Lua](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/lua_filter)
- [Configuración de respuestas locales](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/local_reply)
- [Recurso ProxyConfig](https://istio.io/latest/docs/reference/config/networking/proxy-config/)
- [API Telemetry](https://istio.io/latest/docs/reference/config/telemetry/)
- [ProxyConfig de la malla y estadísticas](https://istio.io/latest/docs/reference/config/istio.mesh.v1alpha1/)
- [RequestAuthentication](https://istio.io/latest/docs/reference/config/security/request_authentication/)
- [Límite de respuestas directas en Istio 1.31](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/route/route.go)
