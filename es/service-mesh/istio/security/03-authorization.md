# Autorización

AuthorizationPolicy permite controlar de forma detallada los permisos de acceso a los servicios.

## Tabla de contenido

1. [Descripción general de la autorización](#authorization-overview)
2. [Políticas básicas](#basic-policies)
3. [Políticas avanzadas](#advanced-policies)
4. [Ejemplos prácticos](#practical-examples)
5. [Mejores prácticas](#best-practices)

## Descripción general de la autorización

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Autorización de Istio" width="700">
</p>

Istio AuthorizationPolicy proporciona control de acceso detallado para los servicios. El diagrama anterior muestra cómo funciona Authorization Policy:

1. **Recepción de solicitudes**: Envoy recibe solicitudes entrantes
2. **Evaluación de políticas**: Las reglas de AuthorizationPolicy se evalúan en orden
3. **Decisión de acceso**: Se aplica la acción ALLOW, DENY o CUSTOM
4. **Registro de auditoría**: Todas las decisiones se registran

**Condiciones compatibles**:
- **Origen**: Origen de la solicitud (ServiceAccount, Namespace, IP)
- **Operación**: Método HTTP, ruta, puerto
- **Condiciones**: Condiciones personalizadas (encabezados, claims de JWT, etc.)

```mermaid
flowchart TB
    Request[Request]

    subgraph AuthZ["Authorization Policy"]
        Check1{Service Account<br/>Check}
        Check2{Namespace<br/>Check}
        Check3{HTTP Method<br/>Check}
    end

    Allow[Allow]
    Deny[Deny]

    Request --> Check1
    Check1 -->|Match| Check2
    Check1 -.->|No Match| Deny
    Check2 -->|Match| Check3
    Check2 -.->|No Match| Deny
    Check3 -->|Match| Allow
    Check3 -.->|No Match| Deny

    %% Style definitions
    classDef request fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef check fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef result fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef deny fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Class applications
    class Request request;
    class Check1,Check2,Check3 check;
    class Allow result;
    class Deny deny;
```

## Políticas básicas

### Denegación predeterminada (Denegar todo)

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: DENY
  rules:
  - {}  # Deny all requests
```

### Permitir de forma predeterminada (Permitir todo)

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-all
  namespace: default
spec:
  action: ALLOW
  rules:
  - {}  # Allow all requests
```

### Basada en método HTTP

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin-get-only
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - to:
    - operation:
        methods: ["GET"]  # Allow only GET
```

## Políticas avanzadas

### Basada en ServiceAccount

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ratings-sa-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]  # Allow only reviews SA
```

### Basada en Namespace

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: db-namespace-policy
  namespace: database
spec:
  selector:
    matchLabels:
      app: postgresql
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production", "staging"]  # Specific namespaces only
```

### Basada en ruta

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: path-based-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: api
  action: ALLOW
  rules:
  - to:
    - operation:
        paths: ["/api/public/*"]  # Allow only public API
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/admin"]
    to:
    - operation:
        paths: ["/api/admin/*"]  # admin SA can access admin API
```

### Basada en claims de JWT

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: jwt-claims-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - when:
    - key: request.auth.claims[role]
      values: ["admin", "superuser"]  # role claim is admin or superuser
```

## Referencias

- [Política de autorización de Istio](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Ejemplos de autorización](https://istio.io/latest/docs/tasks/security/authorization/)
