# Gateway y VirtualService

Gateway y VirtualService son recursos fundamentales para gestionar el tráfico en Istio.

## Tabla de contenido

1. [Descripción general de Gateway](#gateway-overview)
2. [Descripción general de VirtualService](#virtualservice-overview)
3. [Configuración básica](#basic-configuration)
4. [Ejemplos prácticos](#practical-examples)
5. [Patrones avanzados](#advanced-patterns)
6. [Solución de problemas](#troubleshooting)

## Descripción general de Gateway

Gateway define el punto de entrada para el tráfico externo hacia la malla.

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
      credentialName: myapp-tls-secret
    hosts:
    - "myapp.example.com"
```

## Descripción general de VirtualService

VirtualService define cómo enrutar el tráfico que entra a través de Gateway.

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

## Configuración básica

### Tráfico HTTP

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: http-gateway
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
  - http-gateway
  http:
  - route:
    - destination:
        host: myapp
        port:
          number: 8080
```

### Tráfico HTTPS

```yaml
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

## Ejemplos prácticos

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
  - my-gateway
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

### Configuración multidominio

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: multi-domain-gateway
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
  - multi-domain-gateway
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
  - multi-domain-gateway
  http:
  - route:
    - destination:
        host: admin-service
```

## Patrones avanzados

### Redirección de HTTP a HTTPS

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: secure-gateway
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
  - my-gateway
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

### Adición/modificación de encabezados

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
          x-forwarded-proto: "https"
        set:
          x-api-version: "v2"
        remove:
          - x-internal-header
      response:
        add:
          x-response-time: "100ms"
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
  - my-gateway
  http:
  - match:
    - uri:
        prefix: "/old-page"
    redirect:
      uri: "/new-page"
      authority: "newapp.example.com"
```

## Solución de problemas

### Gateway no funciona

```bash
# 1. Check Gateway status
kubectl get gateway -n istio-system

# 2. Check Ingress Gateway pods
kubectl get pods -n istio-system -l istio=ingressgateway

# 3. Check Gateway configuration
kubectl describe gateway my-gateway -n istio-system

# 4. Check Envoy configuration
istioctl proxy-config listeners -n istio-system istio-ingressgateway-xxx
```

### Error de enrutamiento de VirtualService

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

1. **Separación de Namespace**: Gateway en `istio-system`, VirtualService en el Namespace de la aplicación
2. **TLS obligatorio**: Use siempre HTTPS en entornos de producción
3. **Especificación explícita de Host**: Use dominios explícitos en lugar de comodines (`*`)
4. **Orden de las condiciones de coincidencia**: Primero las condiciones específicas; al final, las generales
5. **Nomenclatura de recursos**: Use convenciones de nomenclatura coherentes

## Referencias

- [Istio Gateway](https://istio.io/latest/docs/reference/config/networking/gateway/)
- [Istio VirtualService](https://istio.io/latest/docs/reference/config/networking/virtual-service/)
- [Ingress Traffic](https://istio.io/latest/docs/tasks/traffic-management/ingress/)
