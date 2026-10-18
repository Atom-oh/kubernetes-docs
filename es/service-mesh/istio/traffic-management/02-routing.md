# Enrutamiento

Las funciones avanzadas de enrutamiento de Istio permiten controlar con precisión el tráfico según distintos atributos de las solicitudes.

## Tabla de contenido

1. [Resumen del enrutamiento](#routing-overview)
2. [Condiciones de coincidencia](#match-conditions)
3. [Enrutamiento basado en URI](#uri-based-routing)
4. [Enrutamiento basado en encabezados](#header-based-routing)
5. [Enrutamiento basado en parámetros de consulta](#query-parameter-based-routing)
6. [Enrutamiento basado en métodos HTTP](#http-method-based-routing)
7. [Enrutamiento basado en el origen](#source-based-routing)
8. [Prioridad y ruta alternativa](#priority-and-fallback)
9. [Ejemplos prácticos](#practical-examples)
10. [Solución de problemas](#troubleshooting)

## Resumen del enrutamiento {#routing-overview}

Estos son ejemplos independientes de enrutamiento para sidecars. Cree los Services y los subsets con nombre y aplique solo un VirtualService con reglas superpuestas por host. Si no se especifica `gateways`, las rutas se aplican a los sidecars de la malla; los ejemplos de entrada para hosts externos también requieren una asociación a un Gateway existente y un nombre de host coincidente. Los encabezados, parámetros de consulta y etiquetas del workload de origen son datos de entrada para el enrutamiento, no una prueba de la identidad del usuario. Aplique la autenticación y una AuthorizationPolicy para hacer cumplir los permisos de usuarios o tenants.

Las reglas de enrutamiento de VirtualService constan de **condiciones de coincidencia** y **destinos de ruta**.

![Diagrama que muestra cómo una solicitud entrante se evalúa frente a condiciones de coincidencia ordenadas en un VirtualService de Istio y se dirige al servicio de destino correspondiente; se aplica una regla de alternativa predeterminada si ninguna condición anterior coincide.](../../../.gitbook/assets/en-service-mesh-istio-traffic-management-02-routing-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-traffic-management-02-routing-0.html)

### Estructura básica

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: routing-example
spec:
  hosts:
  - myapp.example.com
  http:
  - match:
    - uri:
        prefix: "/api/v1"
    route:
    - destination:
        host: api-v1
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: mobile-app
  - route:  # Default route (no match)
    - destination:
        host: web-app
```

## Condiciones de coincidencia {#match-conditions}

### Tipos de condiciones de coincidencia

| Condición | Descripción | Tipo de coincidencia |
|-----------|-------------|------------|
| **uri** | Ruta de la solicitud | `exact`, `prefix`, `regex` |
| **scheme** | HTTP/HTTPS | `exact`, `prefix`, `regex` |
| **method** | Método HTTP | `exact`, `prefix`, `regex` |
| **authority** | Encabezado Host | `exact`, `prefix`, `regex` |
| **headers** | Encabezados HTTP | `exact`, `prefix`, `regex` |
| **queryParams** | Parámetros de consulta | `exact`, `prefix`, `regex` |
| **sourceLabels** | Etiquetas del workload de origen | Selector de etiquetas |
| **gateways** | Nombre del Gateway | Lista |

### Tipos de coincidencia

```yaml
# exact: Exact match
match:
- uri:
    exact: "/login"
```

```yaml
# prefix: Prefix match
match:
- uri:
    prefix: "/api/"
```

```yaml
# regex: Regular expression match
match:
- uri:
    regex: "^/api/v[0-9]+/.*"
```

### Combinación de varias condiciones

```yaml
# AND condition: All conditions must match
http:
- match:
  - uri:
      prefix: "/api"
    headers:
      x-api-version:
        exact: "v2"
    queryParams:
      debug:
        exact: "true"
  route:
  - destination:
      host: api-debug
```

```yaml
# OR condition: Use multiple match blocks
http:
- match:
  - uri:
      prefix: "/api/v1"
  - uri:
      prefix: "/api/v2"
  route:
  - destination:
      host: api-service
```

## Enrutamiento basado en URI {#uri-based-routing}

### Coincidencia por prefijo

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: uri-prefix-routing
spec:
  hosts:
  - myapp.example.com
  http:
  # API traffic
  - match:
    - uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-service
        port:
          number: 8080

  # Admin traffic
  - match:
    - uri:
        prefix: "/admin/"
    route:
    - destination:
        host: admin-service
        port:
          number: 9000

  # Static files
  - match:
    - uri:
        prefix: "/static/"
    route:
    - destination:
        host: static-service
        port:
          number: 8000

  # Default traffic
  - route:
    - destination:
        host: frontend-service
        port:
          number: 3000
```

### Coincidencia exacta

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: uri-exact-routing
spec:
  hosts:
  - myapp.example.com
  http:
  # Login page
  - match:
    - uri:
        exact: "/login"
    route:
    - destination:
        host: auth-service

  # Logout
  - match:
    - uri:
        exact: "/logout"
    route:
    - destination:
        host: auth-service

  # Health check
  - match:
    - uri:
        exact: "/health"
    route:
    - destination:
        host: health-service
```

### Coincidencia con expresiones regulares

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: uri-regex-routing
spec:
  hosts:
  - myapp.example.com
  http:
  # API version routing: /api/v1/, /api/v2/, etc.
  - match:
    - uri:
        regex: "^/api/v[0-9]+/.*"
    route:
    - destination:
        host: api-service

  # Numeric resource ID: /users/123
  - match:
    - uri:
        regex: "^/users/[0-9]+$"
    route:
    - destination:
        host: user-service

  # File extension: .jpg, .png, .gif
  - match:
    - uri:
        regex: ".*\\.(jpg|png|gif)$"
    route:
    - destination:
        host: image-service
```

## Enrutamiento basado en encabezados {#header-based-routing}

### Enrutamiento basado en User-Agent

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-user-agent-routing
spec:
  hosts:
  - reviews
  http:
  # Tablet devices
  - match:
    - headers:
        user-agent:
          regex: ".*(iPad|Tablet).*"
    route:
    - destination:
        host: reviews
        subset: tablet

  # Mobile devices
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile

  # Desktop (default)
  - route:
    - destination:
        host: reviews
        subset: desktop
```

### Enrutamiento basado en encabezados personalizados

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-custom-routing
spec:
  hosts:
  - myapp
  http:
  # Developer/Tester routing
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: dev

  # Beta testers
  - match:
    - headers:
        x-beta-tester:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: beta

  # VIP users
  - match:
    - headers:
        x-user-tier:
          exact: "vip"
    route:
    - destination:
        host: myapp
        subset: vip

  # Regular users
  - route:
    - destination:
        host: myapp
        subset: stable
```

### Enrutamiento basado en la versión de la API

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-api-version-routing
spec:
  hosts:
  - api.example.com
  http:
  # API v3
  - match:
    - headers:
        x-api-version:
          exact: "v3"
    route:
    - destination:
        host: api-service
        subset: v3

  # API v2
  - match:
    - headers:
        x-api-version:
          exact: "v2"
    route:
    - destination:
        host: api-service
        subset: v2

  # API v1 (default)
  - route:
    - destination:
        host: api-service
        subset: v1
```

## Enrutamiento basado en parámetros de consulta {#query-parameter-based-routing}

### Coincidencia básica de parámetros de consulta

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: query-param-routing
spec:
  hosts:
  - search.example.com
  http:
  # Debug mode: ?debug=true
  - match:
    - queryParams:
        debug:
          exact: "true"
    route:
    - destination:
        host: search-service
        subset: debug

  # Premium search: ?premium=1
  - match:
    - queryParams:
        premium:
          exact: "1"
    route:
    - destination:
        host: search-service
        subset: premium

  # A/B testing: ?variant=b
  - match:
    - queryParams:
        variant:
          exact: "b"
    route:
    - destination:
        host: search-service
        subset: variant-b

  # Default search
  - route:
    - destination:
        host: search-service
        subset: standard
```

### Combinación de varios parámetros de consulta

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: query-param-combined-routing
spec:
  hosts:
  - api.example.com
  http:
  # Debug mode + verbose logging
  - match:
    - queryParams:
        debug:
          exact: "true"
        verbose:
          exact: "true"
    route:
    - destination:
        host: api-service
        subset: debug-verbose

  # Debug mode only
  - match:
    - queryParams:
        debug:
          exact: "true"
    route:
    - destination:
        host: api-service
        subset: debug

  # Normal mode
  - route:
    - destination:
        host: api-service
        subset: production
```

## Enrutamiento basado en métodos HTTP {#http-method-based-routing}

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: method-based-routing
spec:
  hosts:
  - api.example.com
  http:
  # POST requests → Write-only service
  - match:
    - method:
        exact: "POST"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-write-service

  # PUT/PATCH requests → Update service
  - match:
    - method:
        regex: "PUT|PATCH"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-update-service

  # DELETE requests → Delete service
  - match:
    - method:
        exact: "DELETE"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-delete-service

  # GET requests → Read-only service
  - match:
    - method:
        exact: "GET"
      uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-read-service
```

## Enrutamiento basado en el origen {#source-based-routing}

`sourceLabels` y `sourceNamespace` seleccionan a qué sidecars de origen se envía la configuración; no son condiciones de coincidencia autenticadas por solicitud en una gateway de entrada. La lista explícita de gateways del nivel superior debe incluir `mesh` para que se apliquen estos selectores. El ejemplo de la base de datos supone un servicio que acepta HTTP, no un protocolo SQL opaco.

### Enrutamiento basado en el espacio de nombres

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: source-namespace-routing
  namespace: production
spec:
  hosts:
  - database.production.svc.cluster.local
  http:
  # Requests from production namespace
  - match:
    - sourceNamespace: production
    route:
    - destination:
        host: database
        subset: production

  # Requests from staging namespace
  - match:
    - sourceNamespace: staging
    route:
    - destination:
        host: database
        subset: staging

  # Illustrative HTTP rejection; enforce identity policy at the destination
  - directResponse:
      status: 403
```

### Enrutamiento basado en las etiquetas del workload de origen

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: source-sa-routing
spec:
  hosts:
  - payment-service
  http:
  # Select configuration for matching source workload labels
  - match:
    - sourceLabels:
        app: frontend
        version: v2
    route:
    - destination:
        host: payment-service
        subset: v2

  # Legacy service
  - match:
    - sourceLabels:
        app: frontend
        version: v1
    route:
    - destination:
        host: payment-service
        subset: v1
```

## Prioridad y ruta alternativa {#priority-and-fallback}

### Prioridad de las reglas de coincidencia

Istio evalúa las reglas de enrutamiento HTTP de VirtualService **de arriba abajo**.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: priority-example
spec:
  hosts:
  - myapp.example.com
  http:
  # Priority 1: Most specific condition
  - match:
    - uri:
        exact: "/api/v2/users/admin"
      headers:
        x-admin:
          exact: "true"
    route:
    - destination:
        host: admin-api-v2

  # Priority 2: Medium specificity
  - match:
    - uri:
        prefix: "/api/v2/"
    route:
    - destination:
        host: api-v2

  # Priority 3: Less specific
  - match:
    - uri:
        prefix: "/api/"
    route:
    - destination:
        host: api-v1

  # Priority 4 (last): Default fallback
  - route:
    - destination:
        host: frontend
```

### Estrategia de ruta alternativa

En este contexto, la ruta alternativa es la ruta final para solicitudes que no coincidieron con ninguna regla. Cuando una ruta coincide, un error del servicio ascendente no reinicia la evaluación en la siguiente ruta. Configure reintentos, detección de valores atípicos o un controlador de despliegues por separado para recuperarse de errores.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: fallback-strategy
spec:
  hosts:
  - myapp
  http:
  # Requests matching specific conditions
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: myapp
        subset: canary
    # No fallback on canary failure - return error

  # Default route for requests that did not match the canary condition
  - route:
    - destination:
        host: myapp
        subset: stable
      weight: 100
```

## Ejemplos prácticos {#practical-examples}

### Ejemplo 1: Enrutamiento multiinquilino

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: multi-tenant-routing
spec:
  hosts:
  - api.example.com
  - tenant-b.api.example.com
  http:
  # Tenant A (identified by header)
  - match:
    - headers:
        x-tenant-id:
          exact: "tenant-a"
    route:
    - destination:
        host: api-service
        subset: tenant-a

  # Tenant B (identified by subdomain)
  - match:
    - authority:
        exact: "tenant-b.api.example.com"
    route:
    - destination:
        host: api-service
        subset: tenant-b

  # Tenant C (identified by path)
  - match:
    - uri:
        prefix: "/tenant-c/"
    rewrite:
      uri: "/"
    route:
    - destination:
        host: api-service
        subset: tenant-c
```

### Ejemplo 2: Enrutamiento basado en indicadores de funciones

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: feature-flag-routing
spec:
  hosts:
  - myapp
  http:
  # Users with new feature enabled
  - match:
    - headers:
        x-feature-new-ui:
          exact: "enabled"
    route:
    - destination:
        host: myapp
        subset: new-ui

  # Beta feature testers
  - match:
    - headers:
        x-feature-beta:
          exact: "enabled"
    route:
    - destination:
        host: myapp
        subset: beta

  # Workloads labeled role=employee with the feature header
  - match:
    - headers:
        x-feature-experimental:
          exact: "enabled"
      sourceLabels:
        role: employee
    route:
    - destination:
        host: myapp
        subset: experimental

  # Default (stable version)
  - route:
    - destination:
        host: myapp
        subset: stable
```

### Ejemplo 3: Enrutamiento geográfico

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: geo-routing
spec:
  hosts:
  - content.example.com
  http:
  # Korean users
  - match:
    - headers:
        x-country-code:
          exact: "KR"
    route:
    - destination:
        host: content-service
        subset: korea

  # Japanese users
  - match:
    - headers:
        x-country-code:
          exact: "JP"
    route:
    - destination:
        host: content-service
        subset: japan

  # US users
  - match:
    - headers:
        x-country-code:
          exact: "US"
    route:
    - destination:
        host: content-service
        subset: us

  # European users
  - match:
    - headers:
        x-country-code:
          regex: "DE|FR|GB|IT|ES"
    route:
    - destination:
        host: content-service
        subset: europe

  # Other regions (global)
  - route:
    - destination:
        host: content-service
        subset: global
```

### Ejemplo 4: Patrón de API Gateway

Asocie `api-gateway` a la gateway real y aplique [autenticación JWT y autorización](../security/02-authentication.md) a las rutas protegidas antes de exponerlas. Buscar el texto `Bearer ...` no valida un token. Una ruta protegida no debe continuar hacia una ruta pública o general si faltan las credenciales. Si los encabezados de ubicación geográfica o tenant influyen en las decisiones de acceso, deben proceder de una fuente confiable y autenticada.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-gateway-routing
spec:
  hosts:
  - api.example.com
  gateways:
  - api-gateway
  http:
  # Route protected paths; JWT/authorization must be enforced separately
  - match:
    - uri:
        prefix: "/api/v1/protected/"
    route:
    - destination:
        host: protected-api-service

  # Public APIs
  - match:
    - uri:
        prefix: "/api/v1/public/"
    route:
    - destination:
        host: public-api-service

  # GraphQL endpoint
  - match:
    - uri:
        exact: "/graphql"
      method:
        exact: "POST"
    route:
    - destination:
        host: graphql-service

  # REST API
  - match:
    - uri:
        prefix: "/api/v1/"
    route:
    - destination:
        host: rest-api-service

  # Health check
  - match:
    - uri:
        exact: "/health"
    route:
    - destination:
        host: health-service

  # 404 response for unmatched paths
  - directResponse:
      status: 404
```

## Solución de problemas {#troubleshooting}

### El enrutamiento no funciona

```bash
# 1. Check VirtualService status
kubectl get virtualservice -A
kubectl describe virtualservice <name> -n <namespace>

# 2. Check routing rules
istioctl proxy-config routes <pod-name> -n <namespace>

# 3. Check routing to specific service
istioctl proxy-config routes <pod-name> -n <namespace> --name <route-name> -o json

# 4. Validate configuration
istioctl analyze -n <namespace>
```

### Depuración de las condiciones de coincidencia

```bash
# Increase Envoy log level
istioctl proxy-config log <pod-name> -n <namespace> --level debug

# Trace requests
kubectl logs -n <namespace> <pod-name> -c istio-proxy -f

# Debug Pilot
kubectl logs -n istio-system -l app=istiod --tail=100
```

### Problemas comunes

#### 1. Problemas con el orden de coincidencia

```yaml
# ❌ Wrong order - default route first ignores other rules
http:
- route:  # All traffic goes here
  - destination:
      host: myapp
- match:  # Never executed
  - uri:
      prefix: "/api"
  route:
  - destination:
      host: api-service
```

```yaml
# ✅ Correct order
http:
- match:  # Specific rules first
  - uri:
      prefix: "/api"
  route:
  - destination:
      host: api-service
- route:  # Default route last
  - destination:
      host: myapp
```

#### 2. Alcance de coincidencia de las expresiones regulares

RE2 compara la cadena completa. `/api/v[1-3]` es sintaxis válida y coincide con `/api/v1`, pero no con `/api/v1/users`; no es necesario escapar `/`. Para que coincidan tanto la ruta raíz de la versión como sus rutas descendientes:

```yaml
match:
- uri:
    regex: "^/api/v[1-3](/.*)?$"
```

#### 3. Nombres de encabezados

Los nombres de encabezados HTTP no distinguen mayúsculas de minúsculas durante la transmisión, pero las claves del mapa de coincidencias de Istio deben estar en minúsculas. Los valores de los encabezados sí distinguen mayúsculas de minúsculas, salvo que la expresión indique lo contrario.

```yaml
match:
- headers:
    x-custom-header:
      exact: "value"
```

## Prácticas recomendadas

### 1. Coloque primero las reglas específicas

```yaml
# ✅ Good example
http:
- match:
  - uri:
      exact: "/api/v2/admin"  # Most specific
  route:
  - destination:
      host: admin-v2
- match:
  - uri:
      prefix: "/api/v2/"  # Medium
  route:
  - destination:
      host: api-v2
- match:
  - uri:
      prefix: "/api/"  # General
  route:
  - destination:
      host: api-v1
- route:  # Default
  - destination:
      host: frontend
```

### 2. Reduzca al mínimo las expresiones regulares

```yaml
# ❌ Avoid - complex regex degrades performance
match:
- uri:
    regex: "^/(api|admin|public)/v[0-9]+/(users|products|orders)/[a-zA-Z0-9_-]+$"
```

```yaml
# ✅ Recommended - use prefix or exact
match:
- uri:
    prefix: "/api/v1/"
```

### 3. Use nombres claros

```yaml
# ✅ Use clear names
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: product-api-routing  # Clear name
  labels:
    app: product-service
    purpose: routing
spec:
  hosts:
  - product-api.example.com
  http:
  - route:
    - destination:
        host: product-api-service
```

### 4. Documentación

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp-routing
  annotations:
    description: "Routes traffic based on API version and user type"
    owner: "platform-team"
spec:
  hosts:
  - myapp.example.com
  http:
  # Route VIP users to dedicated instance
  - match:
    - headers:
        x-user-tier:
          exact: "vip"
    route:
    - destination:
        host: myapp
        subset: vip
```

### 5. Estrategia de pruebas

Defina `GATEWAY_URL` con la dirección y el puerto de entrada instalados, y adapte Host y los encabezados al único ejemplo que esté desplegado en ese momento. Antes de ejecutar estas pruebas `curl` externas, asocie los ejemplos exclusivos de la malla a esa gateway. Después de la investigación, restaure cualquier nivel temporal de registro de depuración del proxy.

```bash
# Routing rule test script
#!/bin/bash

# API v1 test
curl -H "Host: api.example.com" http://$GATEWAY_URL/api/v1/users

# API v2 test
curl -H "Host: api.example.com" http://$GATEWAY_URL/api/v2/users

# Mobile user test
curl -H "Host: myapp.example.com" -H "User-Agent: Mobile" "http://$GATEWAY_URL/"

# Header-based test
curl -H "Host: myapp.example.com" -H "x-canary: true" "http://$GATEWAY_URL/"
```

## Referencias

- [Gestión del tráfico de Istio](https://istio.io/latest/docs/concepts/traffic-management/)
- [Referencia de VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Coincidencia de rutas HTTP](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPMatchRequest)
- [Enrutamiento del tráfico](https://istio.io/latest/docs/tasks/traffic-management/request-routing/)
