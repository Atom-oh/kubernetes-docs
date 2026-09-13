# Cuestionario de seguridad

> **Última actualización**: 11 de septiembre de 2026 · Istio 1.31 · Kubernetes 1.32–1.36 (soporte estándar EKS: 1.34–1.36). Consulte la [matriz de instalación](../../../service-mesh/istio/01-installation.md).

El cuestionario evalúa seguridad Istio con ejemplos sidecar. Cada pregunta es independiente; no combine todas las políticas ALLOW sobre la misma carga. Ambient requiere `targetRefs` de waypoint para HTTP/JWT y no admite PeerAuthentication `DISABLE`. Cargas, ServiceAccounts, puertos e identidades deben coincidir con el despliegue real.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Modo PeerAuthentication

¿Qué afirmación describe correctamente el modo mTLS **PERMISSIVE**?

A. Permite tráfico mTLS y texto plano\
B. Solo permite mTLS y rechaza texto plano\
C. Rechaza todo el tráfico\
D. Desactiva mTLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

PERMISSIVE **permite tanto mTLS como texto plano** para facilitar migraciones graduales.

**Explicación:**

**Modos mTLS de PeerAuthentication:**

| Modo | Descripción | Escenario |
| -------------- | ------------------------------ | ------------------------------------- |
| **PERMISSIVE** | Permite mTLS + texto plano | Migración gradual, entornos mixtos |
| **STRICT** | Solo permite mTLS | Refuerzo de seguridad productiva |
| **DISABLE** | Desactiva mTLS de malla en el receptor seleccionado | Excepción heredada explícita |

**Ejemplo PERMISSIVE:**

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE  # Allows both mTLS + plaintext
```

**Comportamiento:**

```
Client A (Istio Sidecar) -> [mTLS] -> Server (PERMISSIVE)  Allowed
Client B (No Sidecar)    -> [Plaintext] -> Server (PERMISSIVE)  Allowed
```

**Comparación con STRICT:**

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: production
spec:
  mtls:
    mode: STRICT  # Only allows mTLS
```

```
Client A (Istio Sidecar) -> [mTLS] -> Server (STRICT)  Allowed
Client B (No Sidecar)    -> [Plaintext] -> Server (STRICT)  Rejected
```

**Estrategia de migración:**

```
Step 1: PERMISSIVE (Allow mixed traffic)
  |
Step 2: Inject Sidecars to all services
  |
Step 3: STRICT (Enforce mTLS)
```

**Referencia:**

* [PeerAuthentication](../../../service-mesh/istio/security/01-mtls.md)
* [mTLS](../../../service-mesh/istio/security/01-mtls.md)

</details>

***

### Pregunta 2: Acción AuthorizationPolicy

Si esta es la única AuthorizationPolicy que selecciona las cargas de su namespace, ¿qué significa?

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec:
  {}
```

A. Permite todas las solicitudes\
B. Rechaza todas las solicitudes\
C. No aplica ninguna política\
D. Solo permite mTLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

Un spec vacío usa ALLOW por defecto sin reglas coincidentes, por lo que esta política sola **rechaza todas las solicitudes**. Otras ALLOW coincidentes pueden dar excepciones; un DENY-all explícito no puede anularse con ALLOW.

**Explicación:**

**Comportamiento predeterminado:**

1. **No hay política**: Se permiten todas las solicitudes
2. **Spec vacío, como el ejemplo**: Se rechazan todas
3. **Con reglas**: Se permite/rechaza según ellas

**Patrón de denegación por defecto:**

```yaml
# Step 1: Deny all requests
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec: {}  # Empty spec = deny all requests

---
# Step 2: Selectively allow only what's needed
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

**Evaluación:** CUSTOM → DENY → ALLOW. Un proveedor CUSTOM coincidente debe permitir; después cualquier DENY coincidente rechaza. Si hay ALLOW aplicables, debe coincidir al menos una regla. Sin ALLOW aplicable, esta etapa permite. Reglas y políticas ALLOW forman una unión, no una lista ordenada de restricciones adicionales. AUDIT marca solicitudes para un plugin configurado; no es una cuarta etapa de aplicación ni registra por sí solo.

**Ejemplo práctico:**

```yaml
# Scenario: Restrict HTTP methods
---
# DENY: Prohibit DELETE
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-delete
spec:
  selector:
    matchLabels:
      app: backend
  action: DENY
  rules:
  - to:
    - operation:
        methods: ["DELETE"]

---
# ALLOW: Only allow GET, POST
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-read-write
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/frontend"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

**Prueba:** Ejecute desde el frontend mallado con ServiceAccount `frontend`; configure detección de protocolo/puerto HTTP del backend.

```bash
# GET request -> Matches ALLOW policy -> Allowed
curl http://backend/api

# POST request -> Matches ALLOW policy -> Allowed
curl -X POST http://backend/api

# DELETE request -> Matches DENY policy -> Rejected
curl -X DELETE http://backend/api

# PUT request -> No ALLOW policy match -> Rejected
curl -X PUT http://backend/api
```

**Referencia:**

* [Política de autorización](../../../service-mesh/istio/security/03-authorization.md)

</details>

***

### Pregunta 3: Autenticación JWT

¿Qué campos validan tokens JWT en RequestAuthentication?

A. issuer y audiences\
B. principals y namespaces\
C. methods y paths\
D. hosts y ports

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

RequestAuthentication usa **issuer** y **audiences** para validar JWT.

**Explicación:**

Si hay token, debe superar firma, issuer, audience y tiempo. RequestAuthentication sola acepta ausencia de token; AuthorizationPolicy debe exigir `requestPrincipals`. Los timestamps siguientes son una ilustración histórica caducada, no un token utilizable.

**Estructura JWT:**

```
Header.Payload.Signature

Payload example:
{
  "iss": "https://auth.example.com",        # issuer
  "sub": "user@example.com",                # subject
  "aud": ["api.example.com"],               # audiences
  "exp": 1735689600,                        # expiration
  "iat": 1735686000                         # issued at
}
```

**Configuración RequestAuthentication:**

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: "https://auth.example.com"      # Validate iss field
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences:
    - "api.example.com"                     # Validate aud field
    forwardOriginalToken: true
```

**Proceso de validación JWT:**

![Un sidecar comprueba sucesivamente issuer, audiences, firma JWKS y caducidad del JWT; rechaza con 401 Unauthorized si falla alguna y permite continuar solo tras superar las cuatro.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-security-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-security-0.html)

El diagrama valida un token presente; no describe autorización ni ausencia de token. Los proveedores siguientes son alternativas; configure tipo y audience esperados por la aplicación.

**Integración con proveedores OIDC:**

```yaml
# Google OAuth2 example
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: google-jwt
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences:
    - "123456789-abcdefg.apps.googleusercontent.com"

---
# Keycloak example
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: keycloak-jwt
spec:
  jwtRules:
  - issuer: "https://keycloak.example.com/realms/myrealm"
    jwksUri: "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"
    audiences:
    - "myapp"
```

**Combinación con AuthorizationPolicy:**

```yaml
# 1. RequestAuthentication: Validate JWT
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences: ["api.example.com"]

---
# 2. AuthorizationPolicy: Only allow authenticated requests
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["https://auth.example.com/*"]  # Verified issuer + method in the same rule
    to:
    - operation:
        methods: ["GET", "POST"]

```

**Prueba:**

```bash
# Request without JWT -> Passes RequestAuthentication, denied by AuthorizationPolicy
curl http://backend/api
# 403 Forbidden

# Request with valid JWT
read -rsp "Test access token: " TOKEN; echo
curl -H "Authorization: Bearer $TOKEN" http://backend/api
unset TOKEN
# 200 OK
```

**Referencia:**

* [Autenticación de solicitudes](../../../service-mesh/istio/security/02-authentication.md)

</details>

***

### Pregunta 4: Gestión de certificados mTLS

¿Cuál es la validez predeterminada de certificados mTLS en Istio?

A. 1 hora\
B. 24 horas\
C. 7 días\
D. 90 días

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

La validez predeterminada es **24 horas**, con renovación automática.

**Explicación:**

El agente solicita una hoja de 24 horas y renueva alrededor de la mitad de su vida, con jitter (`SECRET_GRACE_PERIOD_RATIO=0.5`). Istiod o la CA externa elegida firma; el agente entrega el resultado a Envoy mediante SDS. Las vidas de raíz/intermedias son independientes. La raíz autofirmada predeterminada firma directamente hojas; usar una jerarquía intermedia es decisión administrativa.

Inspeccione el certificado público sin asumir archivo `/etc/certs` ni orden fijo del array SDS:

```bash
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates -issuer -ext subjectAltName
```

**Personalizar validez:**

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    # Change certificate validity period
    defaultConfig:
      proxyMetadata:
        SECRET_TTL: "48h"  # Extend to 48 hours
```

Es un fragmento de entrada `istioctl install -f`, no un operador dentro del clúster. El issuer puede limitar el TTL solicitado de 48 horas; verifique lo emitido y rote proxies seleccionados al cambiar bootstrap.

Si falla la renovación, revise logs de agente/istiod, conectividad CA, autenticación de token, reloj y paquetes de confianza antes de reiniciar. Reiniciar no arregla una CA caducada. Integrar cert-manager requiere **istio-csr** y sus requisitos; `EXTERNAL_CA=ISTIOD_RA_KUBERNETES_API` por sí solo no lo configura. Consulte el [ciclo de vida de certificados](../../../service-mesh/istio/security/01-mtls.md).

</details>

***

### Pregunta 5: Autenticación por ServiceAccount

¿Qué identidad se usa para autenticar servicios entre sí?

A. Nombre Pod\
B. Nombre Service\
C. ServiceAccount\
D. Nombre namespace

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Istio gestiona identidad entre servicios mediante **ServiceAccount**.

**Explicación:**

**Identidad por ServiceAccount:**

```yaml
# 1. Create Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: frontend
  namespace: default

---
# 2. Use Service Account in Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: default
spec:
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      serviceAccountName: frontend  # Used as identity
      containers:
      - name: frontend
        image: registry.example.com/team/frontend:REPLACE_WITH_TESTED_TAG
```

**Formato SPIFFE ID:**

```
spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>

Examples:
spiffe://cluster.local/ns/default/sa/frontend
spiffe://cluster.local/ns/production/sa/backend
```

**Uso en AuthorizationPolicy:**

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: default
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  # Only allow frontend Service Account
  - from:
    - source:
        principals:
        - "cluster.local/ns/default/sa/frontend"
    to:
    - operation:
        methods: ["GET", "POST"]
        paths: ["/api/*"]

  # admin Service Account allowed for all operations
  - from:
    - source:
        principals:
        - "cluster.local/ns/default/sa/admin"
```

La imagen anterior es un marcador de aplicación. RBAC Kubernetes gobierna acceso a su API, no concede automáticamente permisos de tráfico de malla. Istio usa por separado la identidad ServiceAccount autenticada. El principal también incluye namespace y dominio de confianza.

**ServiceAccount frente a nombres Pod/Service:**

| Elemento | ServiceAccount | Nombre Pod | Nombre Service |
| -------------------- | ----------------------- | ------------------- | --------------- |
| **Estabilidad** | Estable | Cambia dinámicamente | Estable |
| **Seguridad** | Basada en certificado | No confiable | No confiable |
| **Integración RBAC** | RBAC Kubernetes | No posible | No posible |
| **mTLS** | Incluida en certificado | No incluido | No incluido |

**Ejemplo práctico: aplicación de 3 capas:**

```yaml
# Frontend -> Backend only allowed
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: frontend
  namespace: app

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: backend
  namespace: app

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: database
  namespace: app

---
# Backend policy: Only allow Frontend access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/app/sa/frontend"]

---
# Database policy: Only allow Backend access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/app/sa/backend"]
```

**Comprobar ServiceAccount:**

```bash
# Check pod's Service Account
kubectl get pod <pod-name> -o jsonpath='{.spec.serviceAccountName}'

# Check SPIFFE ID in mTLS certificate
istioctl proxy-config secret <pod-name> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -text -noout | grep URI

# Output:
# URI:spiffe://cluster.local/ns/default/sa/frontend
```

**Comunicación entre namespaces:**

```yaml
# Allow production namespace's frontend -> staging namespace's backend access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: staging
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - "cluster.local/ns/production/sa/frontend"
        namespaces:
        - "production"
```

**Referencia:**

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Autorización](../../../service-mesh/istio/security/03-authorization.md)

</details>

***

## Preguntas breves (6-10)

### Pregunta 6: Implementar denegación por defecto

Explique paso a paso una política **de denegación por defecto** con Istio en Kubernetes. Incluya **recursos necesarios** (PeerAuthentication, AuthorizationPolicy) y **gestión de excepciones**.

<details>

<summary>Mostrar respuesta</summary>

1. Inventaríe llamantes, ServiceAccounts, puertos y protocolos reales. Inscriba cargas y aplique `STRICT` al namespace tras verificar compatibilidad. PeerAuthentication sola no autoriza llamantes.
2. Aplique ALLOW vacía como base y añada reglas del grafo de llamadas necesario. No use `DENY` con `rules: [{}]` si pretende permitir excepciones.
3. Se supone namespace `app`, frontend/backend/database mallados con etiquetas `app` y ServiceAccounts correspondientes, HTTP 8080, PostgreSQL 5432 y ServiceAccount gateway `istio-ingressgateway` en `istio-system`. Verifique esa identidad en el Pod real. El Service gateway mapea HTTPS 443 al **puerto de carga 8443**, que usa AuthorizationPolicy. Configure aparte terminación TLS y VirtualService para `myapp.example.com/api/*`.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: default-deny
  namespace: app
spec: {}
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ingress-public-api
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - to:
    - operation:
        ports:
        - '8443'
        hosts:
        - myapp.example.com
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/istio-ingressgateway
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/backend
    to:
    - operation:
        ports:
        - '5432'
```

4. Conserve la reescritura predeterminada de probes sidecar: HTTP/TCP/gRPC de kubelet pasan por el agente, normalmente 15020. Una ruta HTTP ALLOW no permite texto plano con STRICT. Si un endpoint heredado necesita excepción, `portLevelMtls` exige selector de carga y puerto real; autorización/red deben seguir restringiéndolo. No desactive mTLS del puerto de negocio como arreglo genérico.
5. Puertos métricos agente/Envoy 15020/15090 difieren de endpoints de aplicación interceptados. Para métricas protegidas de aplicación, limite ALLOW a carga, puerto/ruta y principal Prometheus autenticado por mTLS. Para métricas de agente, configure scrape y red; una AuthorizationPolicy de aplicación entrante no basta.
6. Valide configuración efectiva y tráfico permitido/rechazado:

```bash
istioctl analyze -n app
istioctl proxy-config secret <backend-pod> -n app
istioctl proxy-config clusters <frontend-pod> -n app -o json
istioctl x authz check <backend-pod>.app
# Run from the indicated application containers with the test clients installed.
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://backend:8080/api/users
kubectl exec <frontend-pod> -n app -c frontend -- pg_isready -h database -p 5432
kubectl exec <backend-pod> -n app -c backend -- pg_isready -h database -p 5432
```

Frontend → backend debe alcanzar la aplicación; frontend → database debe fallar en TCP, no devolver HTTP 403. Backend → database debe alcanzar PostgreSQL, con credenciales DB comprobadas aparte. Rutas ausentes pueden generar 404 antes de llegar al backend previsto para la prueba. Use Pods con namespace, contenedores de aplicación y clientes reales. Consulte [autorización](../../../service-mesh/istio/security/03-authorization.md) y [probes de salud](https://istio.io/latest/docs/ops/configuration/mesh/app-health-check/).

</details>

***

### Pregunta 7: Autenticación doble JWT + mTLS

Implemente **autenticación de usuario final (JWT)** junto con **autenticación entre servicios (mTLS)** en Istio. Incluya integración OAuth2/OIDC, por ejemplo Keycloak.

<details>

<summary>Mostrar respuesta</summary>

Configure realm `myrealm`, cliente OIDC y audience API explícita `myapp`. Use authorization code con PKCE y URI HTTPS exactas. El tipo/autenticación del cliente depende de si puede guardar un secreto. Los roles Keycloak suelen estar en `realm_access.roles`; use un mapper de audience/client scope para obtener el `aud` esperado.

Cada proxy que evalúe `requestPrincipals` o `request.auth.claims` necesita RequestAuthentication propia. Verificar JWT en el gateway no establece identidad en frontend/backend. `forwardOriginalToken` conserva el token en esa solicitud reenviada, y **la aplicación frontend debe propagar Authorization a su nueva solicitud backend**.

Lo siguiente sustituye las políticas relacionadas de la pregunta 6. No conserve una ALLOW más amplia junto a reglas backend restringidas por rol: ALLOW forma una unión. Los requisitos de despliegue/gateway HTTPS son los mismos.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: default-deny
  namespace: app
spec: {}
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-ingress
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  jwtRules:
  - issuer: https://keycloak.example.com/realms/myrealm
    jwksUri: https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs
    audiences:
    - myapp
    forwardOriginalToken: true
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ingress-public-api
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - to:
    - operation:
        ports:
        - '8443'
        hosts:
        - myapp.example.com
        paths:
        - /api/*
        methods:
        - GET
        - POST
        - DELETE
    from:
    - source:
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-frontend
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  jwtRules:
  - issuer: https://keycloak.example.com/realms/myrealm
    jwksUri: https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs
    audiences:
    - myapp
    forwardOriginalToken: true
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/istio-ingressgateway
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
        - DELETE
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-backend
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://keycloak.example.com/realms/myrealm
    jwksUri: https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs
    audiences:
    - myapp
    forwardOriginalToken: true
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/users/*
        methods:
        - GET
        - POST
    when:
    - key: request.auth.claims[realm_access][roles]
      values:
      - user
      - admin
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - https://keycloak.example.com/realms/myrealm/*
    to:
    - operation:
        ports:
        - '8080'
        methods:
        - DELETE
        paths:
        - /api/admin/*
    when:
    - key: request.auth.claims[realm_access][roles]
      values:
      - admin
```

Para enviar un claim escalar como cabecera, RequestAuthentication admite `outputClaimToHeaders` experimental, por ejemplo `header: x-user-id` con `claim: sub`. Autorice usando claims verificados, no cabeceras de identidad suministradas por llamantes. `outputPayloadToHeader` contiene payload codificado y Lua de Envoy no incluye un módulo arbitrario `require("json")`. Los arrays de roles deben compararse como claims, no concatenarse ciegamente en cabeceras.

Obtenga un token por el login configurado y pruebe HTTPS. No incruste contraseñas/secretos de cliente en comandos del cuestionario:

```bash
read -rsp "Test access token: " TOKEN; echo
curl -i -H "Authorization: Bearer $TOKEN" https://myapp.example.com/api/users/test
unset TOKEN
curl -i https://myapp.example.com/api/users/test
# No JWT: 403 from AuthorizationPolicy.
curl -i -H "Authorization: Bearer invalid-token" https://myapp.example.com/api/users/test
# Invalid JWT: 401 from RequestAuthentication.
```

Pruebe también token válido con ServiceAccount incorrecta, audience errónea y rol insuficiente. Cambiar roles JWT no revoca instantáneamente tokens emitidos; importan duración y mecanismos del issuer/aplicación. Consulte [autenticación](../../../service-mesh/istio/security/02-authentication.md) y [grants Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).

</details>

***

### Pregunta 8: Control de servicios externos

Explique cómo controlar **tráfico de salida** en Istio permitiendo solo servicios externos concretos. Incluya ejemplos completos de **ServiceEntry**, **VirtualService** y **AuthorizationPolicy**.

<details>

<summary>Mostrar respuesta</summary>

`ALLOW_ANY` reenvía destinos desconocidos; `REGISTRY_ONLY` rechaza destinos desconocidos en el registro del proxy. El registro incluye servicios Kubernetes y ServiceEntry. Ninguno es firewall; sin restricciones de red independientes una aplicación puede evitar el proxy. Aplique ajustes mediante values existentes, sin reemplazar todo `istio` ConfigMap por un campo.

AuthorizationPolicy evalúa tráfico recibido por su proxy seleccionado. Una política de namespace sobre sidecars cliente no es ACL saliente. Para controlar identidad/método/ruta, use gateway de salida que termine mTLS de malla, autorice allí y origine TLS al servidor externo. La aplicación envía HTTP al sidecar; HTTPS passthrough ocultaría métodos y rutas.

Requisitos: clientes mallados en `app`, gateway dedicado etiquetado `istio: egressgateway`, Service `istio-egressgateway.istio-system.svc.cluster.local` mapeando 443 a carga 8443 y ninguna otra ALLOW amplia en gateway. La confianza CA pública del proxy debe validar el certificado GitHub.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: github-api
  namespace: app
spec:
  hosts:
  - api.github.com
  location: MESH_EXTERNAL
  resolution: DNS
  ports:
  - number: 80
    targetPort: 443
    name: http
    protocol: HTTP
---
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: github-egress
  namespace: istio-system
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - api.github.com
    tls:
      mode: ISTIO_MUTUAL
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: to-egress
  namespace: app
spec:
  host: istio-egressgateway.istio-system.svc.cluster.local
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
      sni: api.github.com
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: github-through-egress
  namespace: app
spec:
  hosts:
  - api.github.com
  gateways:
  - mesh
  - istio-system/github-egress
  http:
  - match:
    - gateways:
      - mesh
      port: 80
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - istio-system/github-egress
      port: 443
    timeout: 10s
    retries:
      attempts: 2
      perTryTimeout: 3s
      retryOn: connect-failure,reset
    route:
    - destination:
        host: api.github.com
        port:
          number: 80
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: github-origin-tls
  namespace: istio-system
spec:
  host: api.github.com
  workloadSelector:
    matchLabels:
      istio: egressgateway
  trafficPolicy:
    tls:
      mode: SIMPLE
      sni: api.github.com
      subjectAltNames:
      - api.github.com
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: github-egress-allow
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: egressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/backend
    to:
    - operation:
        hosts:
        - api.github.com
        methods:
        - GET
        paths:
        - /users/*
        ports:
        - '8443'
```

El cliente llama a `http://api.github.com/users/octocat`. Su sidecar conecta al gateway con ISTIO_MUTUAL. El listener HTTP puede exigir la ServiceAccount backend y GET `/users/*`, después enviar HTTPS a GitHub mediante puerto 80 → targetPort 443. Los reintentos son para ese GET idempotente, no para cualquier API con efectos secundarios.

```bash
kubectl exec <backend-pod> -n app -c backend -- curl -i http://api.github.com/users/octocat
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://api.github.com/users/octocat
# Gateway should reject the second caller with HTTP 403.
istioctl proxy-config clusters <egress-pod> -n istio-system --fqdn api.github.com -o json
istioctl x authz check <egress-pod>.istio-system
```

Para una DB externa privada, use ServiceEntry STATIC con endpoints/dirección explícitos y TCP 5432; diseñe TLS/autenticación para ese protocolo. Un servicio solo HTTP puede usar ServiceEntry HTTP, pero datos sensibles requieren cifrado. Guarde credenciales API en la aplicación o un componente de firma/autenticación admitido respaldado por secretos; valores literales de cabeceras VirtualService son configuración legible, no almacén secreto.

Finalmente fuerce la ruta con NetworkPolicy CNI/firewall: clientes pueden alcanzar servicios de malla, DNS, istiod y gateway necesarios, no IP arbitrarias de Internet; el gateway obtiene acceso externo requerido. Considere IPv4/IPv6, puertos excluidos/bypass y cargas privilegiadas. NetworkPolicy estándar no filtra DNS; use control FQDN admitido si se necesita. Pruebe bypass directo por IP/HTTPS además de la ruta permitida. Consulte [control egress](../../../service-mesh/istio/traffic-management/11-egress-control.md) y [originación TLS](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway-tls-origination/).

</details>

***

### Pregunta 9: Auditoría y registros de seguridad

Explique cómo **auditar** y registrar eventos de seguridad Istio. Incluya **la acción AUDIT de AuthorizationPolicy** y configuración de **registros de acceso**.

<details>

<summary>Mostrar respuesta</summary>

`AUDIT` marca solicitudes para un **plugin de auditoría instalado**. Sin él, la política no registra y no permite ni deniega tráfico. El ejemplo audita una conjunción, DELETE y ruta admin, no dos condiciones ordenadas:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: audit-sensitive
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: AUDIT
  rules:
  - to:
    - operation:
        methods:
        - DELETE
        paths:
        - /api/admin/*
```

Los logs de acceso son independientes. Combine este proveedor en la instalación con `istioctl install -f`, conservando otros ajustes/proveedores, y actívelo solo para el backend seleccionado. Se excluyen deliberadamente query strings, bearer tokens y payloads JWT completos.

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    extensionProviders:
    - name: security-json
      envoyFileAccessLog:
        path: /dev/stdout
        logFormat:
          labels:
            start_time: '%START_TIME%'
            method: '%REQ(:METHOD)%'
            path: '%REQ_WITHOUT_QUERY(:PATH)%'
            response_code: '%RESPONSE_CODE%'
            response_code_details: '%RESPONSE_CODE_DETAILS%'
            response_flags: '%RESPONSE_FLAGS%'
            peer: '%DOWNSTREAM_PEER_URI_SAN%'
            request_id: '%REQ(X-REQUEST-ID)%'
```

```yaml
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: backend-security
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  accessLogging:
  - providers:
    - name: security-json
    filter:
      expression: response.code >= 400 || request.method == "DELETE" || request.url_path.startsWith("/api/admin/")
  metrics:
  - providers:
    - name: prometheus
    overrides:
    - match:
        metric: REQUEST_COUNT
        mode: SERVER
      tagOverrides:
        security_operation:
          value: 'request.url_path.startsWith("/api/admin/") ? "admin" : "other"'
```

Telemetry añade la dimensión acotada `security_operation` (`admin`/`other`) al contador de solicitudes. `request_method` y ruta URL bruta no son etiquetas estándar Istio. Evite URL completas por cardinalidad y sensibilidad. Errores, DELETE y acceso admin se registran incluso sin plugin AUDIT. Para todas las solicitudes omita filtro; para un namespace omita selector; una política raíz sin selector cubre toda la malla.

Para CloudWatch, despliegue/configure agente EKS admitido o Fluent Bit DaemonSet con montajes de logs, parsing CRI/containerd, parsing JSON de `log`, IAM y salida CloudWatch. ConfigMap solo no inicia un agente. Elasticsearch/OpenSearch requieren salida de collector configurada; Telemetry con `envoy` escribe stdout, no configura Elasticsearch. Fargate necesita su mecanismo de logs, no un DaemonSet de nodo.

Tras ingerir campos JSON estructurados, ejecute cada consulta CloudWatch Logs Insights por separado:

```sql
fields @timestamp, method, path, response_code, peer
| filter method = "DELETE"
| sort @timestamp desc
| limit 100
```

```sql
fields @timestamp, path, response_code, response_code_details
| filter path like /^\/api\/admin\//
| filter response_code = "403"
| stats count() by bin(5m), response_code_details
```

Un 403 puede venir de la aplicación, autorización JWT o proveedor externo. Inspeccione `response_code_details`, logs RBAC y política efectiva antes de atribuirlo a Istio. No asuma que `envoy_http_rbac_logged_total` sea contador AUDIT integrado. Las estadísticas RBAC/dry-run experimental dependen de configuración y nombres; inspeccione series exportadas.

Grafana puede representar la tasa 403 del reporter destination y la dimensión admin personalizada. Una PrometheusRule seleccionada por el Operator puede alertar sobre esta última:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: istio-security-alerts
  namespace: monitoring
spec:
  groups:
  - name: istio-security
    rules:
    - alert: AdminHTTP403Responses
      expr: sum(rate(istio_requests_total{reporter="destination",security_operation="admin",response_code="403"}[5m]))
        > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Admin API returned HTTP 403; inspect response_code_details to identify
          the cause
```

Antes de aplicar una política, la anotación experimental `istio.io/dry-run: "true"` en ALLOW/DENY puede informar decisiones sombra; difiere de AUDIT y su diagnóstico no es API estable. Configure retención, acceso y ocultación de datos sensibles según requisitos organizativos/legales reales; no hay mandato universal de 90 días/un año. Consulte [logs de acceso](https://istio.io/latest/docs/tasks/observability/logs/access-log/) y [dry-run de autorización](https://istio.io/latest/docs/tasks/security/authorization/authz-dry-run/).

</details>

***

### Pregunta 10: Implementar una red zero trust

Explique cómo aplicar principios de **red zero trust** con Istio. Incluya ejemplos completos de **mTLS STRICT**, **denegación por defecto** y **mínimo privilegio**.

<details>

<summary>Mostrar respuesta</summary>

Zero trust combina identidades autenticadas, autorización explícita de mínimo privilegio y controles que siguen vigentes si una carga se compromete. Istio protege tráfico capturado por su plano; no sustituye RBAC, admisión, aislamiento de red ni autorización de aplicación.

1. Asigne ServiceAccounts separadas a frontend/backend/database e impida que las cargas adopten libremente cuentas ajenas. Inscriba cargas y verifique dominio de confianza, emisión y renovación.
2. Aplique STRICT y una ALLOW vacía al namespace objetivo. Una política en `default` no cubre `app` automáticamente; la base raíz tiene mayor alcance y necesita excepciones operativas/gateway explícitas.
3. Permita solo gateway → frontend → backend → database. Con los mismos requisitos de la pregunta 6, el conjunto completo es:

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: default-deny
  namespace: app
spec: {}
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: ingress-public-api
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - to:
    - operation:
        ports:
        - '8443'
        hosts:
        - myapp.example.com
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: frontend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: frontend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/istio-ingressgateway
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
    to:
    - operation:
        ports:
        - '8080'
        paths:
        - /api/*
        methods:
        - GET
        - POST
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-policy
  namespace: app
spec:
  selector:
    matchLabels:
      app: database
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/backend
    to:
    - operation:
        ports:
        - '5432'
```

4. Para aislamiento de namespaces, compare namespaces/principales autenticados. Un DENY sobre `production` con `notNamespaces: [production, istio-system]` bloquea **otros llamantes hacia production**, no production → staging. Considere gateways y operadores; DENY prevalece sobre ALLOW.
5. Si depende del horario laboral, use autorización de aplicación o proveedor CUSTOM configurado con zona horaria, reloj y política de fallo explícitos. Un Lua `os.date()` sin punto de inserción/zona definidos no es diseño completo. CUSTOM aún debe superar DENY/ALLOW.
6. Fuerce egress con el gateway de la pregunta 8 y controles de red; ni REGISTRY_ONLY ni una política sidecar `deny-all-egress` son firewall. Un DENY entrante para todo host bloquearía la aplicación y ALLOW no lo anula.
7. Conserve reescritura de probes, diseñe scraping para puertos correctos y añada solo excepciones necesarias de la pregunta 6. Use JWT y propagación por salto de la 7 para usuarios. Registre/alerte como en la 9, más caducidad de certificados del capítulo mTLS.
8. Después de cada cambio, revise política real y pruebe matriz permitida/rechazada, TCP a DB y bypass egress:

```bash
istioctl analyze -n app
istioctl proxy-config secret <backend-pod> -n app
istioctl proxy-config clusters <frontend-pod> -n app -o json
istioctl x authz check <backend-pod>.app
# Run from the indicated application containers with the test clients installed.
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://backend:8080/api/users
kubectl exec <frontend-pod> -n app -c frontend -- pg_isready -h database -p 5432
kubectl exec <backend-pod> -n app -c backend -- pg_isready -h database -p 5432
```

Una puntuación no demuestra preparación productiva. Revise asignación de identidad, bypass de red, confianza del issuer, mínimo privilegio, observabilidad, rollback y permisos de la aplicación en el entorno real. Consulte [conceptos de seguridad](https://istio.io/latest/docs/concepts/security/) y [autorización](../../../service-mesh/istio/security/03-authorization.md).

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (50 en total)
* Respuesta breve 6-10: 10 puntos cada una (50 en total)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: Excelente comprensión de estos temas
* 80-89 puntos: Buena comprensión; valide despliegues reales aparte
* 70-79 puntos: Media (se recomienda más estudio)
* 60-69 puntos: Por debajo de la media (repasar conceptos básicos)
* 0-59 puntos: Necesita volver a estudiar

## Recursos de aprendizaje

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Política de autorización](../../../service-mesh/istio/security/03-authorization.md)
* [Autenticación de solicitudes](../../../service-mesh/istio/security/02-authentication.md)
* [Autenticación entre peers](../../../service-mesh/istio/security/01-mtls.md)
