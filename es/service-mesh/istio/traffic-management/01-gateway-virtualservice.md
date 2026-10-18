# Gateway y VirtualService

Gateway y VirtualService son recursos fundamentales para gestionar el tráfico de Istio.

## Índice

1. [Descripción general de Gateway](#gateway-overview)
2. [Descripción general de VirtualService](#virtualservice-overview)
3. [Configuración básica](#basic-configuration)
4. [Ejemplos prácticos](#practical-examples)
5. [Patrones avanzados](#advanced-patterns)
6. [Solución de problemas](#troubleshooting)

Este capítulo usa el recurso Gateway de Istio `networking.istio.io/v1`, distinto de la Kubernetes Gateway API. Los ejemplos presuponen que ya existe una carga de trabajo/Service de gateway con la etiqueta `istio=ingressgateway` en `istio-system`, que los Services de las aplicaciones están en `default` y que los puertos de servicio coinciden. Un Gateway de Istio configura un proxy existente; no crea ni aprovisiona uno. Cree cada Secret TLS en el **namespace de la carga de trabajo del gateway** y vincule el VirtualService al Gateway que se está probando. Los ejemplos con hosts superpuestos son alternativas entre sí.

## Descripción general de Gateway {#gateway-overview}

Gateway define el punto de entrada del tráfico externo a la malla.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pods
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

## Descripción general de VirtualService {#virtualservice-overview}

VirtualService define el enrutamiento para los sidecars de la malla o para los gateways a los que se hace referencia explícitamente.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: myapp
  namespace: default
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/api"
    route:
    - destination:
        host: api-service
        port:
          number: 8080
  - route:
    - destination:
        host: frontend-service
        port:
          number: 3000
```

## Configuración básica {#basic-configuration}

### Tráfico HTTP

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: http-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"  # Allow all hosts
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: app-routes
spec:
  hosts:
  - "*"
  gateways:
  - istio-system/http-gateway
  http:
  - route:
    - destination:
        host: myapp
        port:
          number: 8080
```

### Tráfico HTTPS

```bash
# Create TLS certificate Secret
kubectl create secret tls myapp-tls \
  --cert=myapp.crt \
  --key=myapp.key \
  -n istio-system
```

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: https-gateway
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
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

## Ejemplos prácticos {#practical-examples}

### Enrutamiento basado en rutas

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: path-routing
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  # API traffic
  - match:
    - uri:
        prefix: "/api/v1"
    route:
    - destination:
        host: api-v1
        port:
          number: 8080
  # Admin traffic
  - match:
    - uri:
        prefix: "/admin"
    route:
    - destination:
        host: admin-service
        port:
          number: 9000
  # Default traffic
  - route:
    - destination:
        host: frontend
        port:
          number: 3000
```

### Enrutamiento basado en encabezados

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-routing
spec:
  hosts:
  - reviews
  http:
  # Mobile traffic
  - match:
    - headers:
        user-agent:
          regex: ".*Mobile.*"
    route:
    - destination:
        host: reviews
        subset: mobile-v2
  # Developer traffic
  - match:
    - headers:
        x-dev-user:
          exact: "true"
    route:
    - destination:
        host: reviews
        subset: v3
  # Default traffic
  - route:
    - destination:
        host: reviews
        subset: v1
```

Antes de usar el ejemplo de enrutamiento por encabezados, cree los subconjuntos `mobile-v2`, `v3` y `v1` de DestinationRule con etiquetas de Pod coincidentes. Los encabezados de enrutamiento proporcionados por el cliente no son un mecanismo de autorización. Los encabezados de respuesta estáticos que aparecen abajo son ejemplos; no representan latencias medidas.

### Configuración multidominio

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: multi-domain-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https-api
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: api-tls
    hosts:
    - "api.example.com"
  - port:
      number: 443
      name: https-admin
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: admin-tls
    hosts:
    - "admin.example.com"
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-routes
spec:
  hosts:
  - "api.example.com"
  gateways:
  - istio-system/multi-domain-gateway
  http:
  - route:
    - destination:
        host: api-service
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: admin-routes
spec:
  hosts:
  - "admin.example.com"
  gateways:
  - istio-system/multi-domain-gateway
  http:
  - route:
    - destination:
        host: admin-service
```

## Patrones avanzados {#advanced-patterns}

### Redirección de HTTP a HTTPS

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: secure-gateway
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  # HTTP (for redirect)
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "myapp.example.com"
    tls:
      httpsRedirect: true  # Redirect to HTTPS
  # HTTPS
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: myapp-tls
    hosts:
    - "myapp.example.com"
```

### Reescritura de URL

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: url-rewrite
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-api"
    rewrite:
      uri: "/api/v2"  # URL rewrite
    route:
    - destination:
        host: api-service
```

### Adición o modificación de encabezados

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: header-manipulation
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
    headers:
      request:
        add:
          x-custom-header: "custom-value"
          x-demo-stage: "gateway"
        set:
          x-api-version: "v2"
        remove:
          - x-internal-header
      response:
        add:
          x-demo-response: "configured-value"
```

### Redirección

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: redirect-example
spec:
  hosts:
  - "myapp.example.com"
  gateways:
  - istio-system/my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-page"
    redirect:
      uri: "/new-page"
      authority: "newapp.example.com"
```

## Solución de problemas {#troubleshooting}

### Gateway no funciona

```bash
# 1. Check Gateway status
kubectl get gateways.networking.istio.io -n istio-system

# 2. Check Ingress Gateway pods
kubectl get pods -n istio-system -l istio=ingressgateway

# 3. Check Gateway configuration
kubectl describe gateways.networking.istio.io my-gateway -n istio-system

# 4. Check Envoy configuration
istioctl proxy-config listeners -n istio-system istio-ingressgateway-xxx
```

### Fallo de enrutamiento de VirtualService

```bash
# 1. Check VirtualService
kubectl get virtualservice

# 2. Analyze configuration
istioctl analyze

# 3. Check routing rules
istioctl proxy-config routes -n istio-system istio-ingressgateway-xxx

# 4. Check logs
kubectl logs -n istio-system -l istio=ingressgateway --tail=100
```

### Problemas con el certificado TLS

```bash
# Check Secret
kubectl get secret -n istio-system myapp-tls

# Check Secret contents
kubectl describe secret -n istio-system myapp-tls

# Check Gateway TLS configuration
istioctl proxy-config secret -n istio-system istio-ingressgateway-xxx
```

## Prácticas recomendadas

1. **Separación de namespaces**: Gateway en `istio-system` y VirtualService en el namespace de la aplicación
2. **TLS obligatorio**: use siempre HTTPS en entornos de producción
3. **Especificación explícita de host**: use dominios explícitos en lugar de comodines (`*`)
4. **Orden de las condiciones de coincidencia**: primero las condiciones específicas y al final las generales
5. **Nombres de recursos**: use convenciones de nomenclatura coherentes

## Referencias

- [Istio Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Tráfico de entrada](https://istio.io/latest/docs/tasks/traffic-management/ingress/)
