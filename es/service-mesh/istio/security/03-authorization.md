# Autorización

AuthorizationPolicy permite controlar con precisión los permisos de acceso a los servicios.

## Tabla de contenido

1. [Descripción general de la autorización](#authorization-overview)
2. [Políticas básicas](#basic-policies)
3. [Políticas avanzadas](#advanced-policies)
4. [Ejemplos prácticos](#practical-examples)
5. [Prácticas recomendadas](#best-practices)

## Descripción general de la autorización {#authorization-overview}

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Autorización de Istio" width="700">
</p>

AuthorizationPolicy de Istio proporciona control de acceso detallado para los servicios. El diagrama anterior muestra cómo funciona la política de autorización:

1. **Recepción de la solicitud**: Envoy recibe la solicitud entrante.
2. **Evaluación de políticas**: se evalúan primero las políticas CUSTOM coincidentes, después DENY y, por último, ALLOW; el orden de creación del YAML no influye.
3. **Decisión de acceso**: se aplica la acción ALLOW, DENY o CUSTOM.
4. **Registro de auditoría**: requiere que se configure el registro de acceso/auditoría; AUDIT por sí solo solo marca una solicitud.

**Condiciones compatibles**:
- **Origen**: origen de la solicitud (ServiceAccount, namespace, IP)
- **Operación**: método HTTP, ruta, puerto
- **Condiciones**: condiciones personalizadas (cabeceras, claims de JWT, etc.)

![Diagrama de flujo de una política AuthorizationPolicy de Istio que evalúa una solicitud mediante tres comprobaciones secuenciales (ServiceAccount, namespace y método HTTP): si las tres coinciden, permite la solicitud; ante cualquier discrepancia, la deniega de inmediato.](../../../.gitbook/assets/en-service-mesh-istio-security-03-authorization-0.png)

[🔍 Ver el diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-security-03-authorization-0.html)

## Políticas básicas {#basic-policies}

El diagrama ilustra una regla conjuntiva. Dentro de una regla se combinan las restricciones `from`, `to` y `when`; las reglas separadas y las políticas ALLOW coincidentes son alternativas. Si una carga de trabajo no tiene ninguna política ALLOW, las solicitudes se permiten salvo que CUSTOM/DENY las rechace. Cuando se aplica una política ALLOW, se requiere al menos una coincidencia ALLOW. Los ejemplos siguientes son alternativas; permitir todo ampliaría una política limitada a `get`.

### Denegación predeterminada (denegar todo)

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: ALLOW
  rules: []  # Default deny with room for specific ALLOW exceptions
```

### Permiso predeterminado (permitir todo)

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

### Basada en el método HTTP

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

## Políticas avanzadas {#advanced-policies}

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

### Basada en namespace

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

## Ejemplos prácticos {#practical-examples}

Para establecer una denegación predeterminada con excepciones, aplique la política ALLOW vacía y solo las reglas ALLOW específicas previstas. Un DENY explícito con `rules: [{}]` es un bloqueo estricto que ninguna regla ALLOW puede anular. Una política sin selector se aplica a su namespace; la asociación con el namespace raíz y las reglas de conexión mediante `targetRefs` requieren atención aparte.

Las coincidencias de ServiceAccount/namespace requieren una identidad de par autenticada mediante mTLS. El ejemplo del rol JWT requiere un RequestAuthentication coincidente y la validación prevista del emisor/audiencia. Las cabeceras del cliente no sustituyen ninguna de esas identidades. Para TCP nativo, haga coincidencias por identidad/IP/puertos en lugar de métodos HTTP o claims de JWT; si faltan atributos HTTP en reglas DENY, estas pueden coincidir inesperadamente con TCP.

## Prácticas recomendadas {#best-practices}

- Limite las políticas a la carga de trabajo/recurso previsto y revise en conjunto todas las reglas ALLOW aplicables.
- Use `targetRefs` de waypoint para las políticas L7 de ambient; un selector de sidecar no asocia una política a un waypoint.
- Valide los casos de ausencia de política, falta de coincidencia, denegación explícita y solicitud permitida, incluidos los límites entre namespaces.
- Configure el registro de forma explícita e inspeccione las políticas efectivas con `istioctl x authz check <pod> -n <namespace>`.

## Referencias

- [Política de autorización de Istio](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Ejemplos de autorización](https://istio.io/latest/docs/tasks/security/authorization/)
