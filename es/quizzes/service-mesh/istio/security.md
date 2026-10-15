# Cuestionario de seguridad

> **Última actualización**: October 12, 2026
>
> **Versiones**: Istio 1.31, que admite Kubernetes 1.32–1.37 (soporte estándar de EKS: 1.34–1.37).
> Consulta la [matriz de instalación](../../../service-mesh/istio/01-installation.md).

Este cuestionario evalúa la seguridad de Istio con ejemplos de sidecar. Cada pregunta es un escenario independiente; no combines todas las políticas ALLOW en la misma carga de trabajo. Ambient requiere `targetRefs` de waypoint para políticas HTTP/JWT y no admite PeerAuthentication `DISABLE`. Las cargas de trabajo con nombre, ServiceAccounts, puertos e identidades deben coincidir con el despliegue real.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Modo PeerAuthentication

¿Qué afirmación describe correctamente el modo mTLS **PERMISSIVE** en PeerAuthentication?

A. Permite tráfico mTLS y de texto sin formato\
B. Solo permite mTLS y rechaza el texto sin formato\
C. Rechaza todo el tráfico\
D. Deshabilita mTLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

El modo PERMISSIVE **permite tráfico mTLS y de texto sin formato** para admitir una migración gradual.

**Explicación:**

**Modos mTLS de PeerAuthentication:**

| Modo           | Descripción                    | Escenario de uso                          |
| -------------- | ------------------------------ | ------------------------------------- |
| **PERMISSIVE** | Permite mTLS y texto sin formato | Migración gradual, entornos mixtos |
| **STRICT**     | Solo permite mTLS               | Endurecimiento de seguridad de producción         |
| **DISABLE**    | Deshabilita mTLS de la malla en el receptor seleccionado | Excepción heredada explícita             |

**Ejemplo de modo PERMISSIVE:**

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

**Comparación con el modo STRICT:**

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

### Pregunta 2: Acción de AuthorizationPolicy

Si esta es la única AuthorizationPolicy que selecciona las cargas de trabajo de su espacio de nombres, ¿qué significa?

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
spec:
  {}
```

A. Permite todas las solicitudes\
B. Deniega todas las solicitudes\
C. No aplica ninguna política\
D. Solo permite mTLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

Una especificación vacía usa de forma predeterminada ALLOW sin reglas coincidentes, por lo que esta política por sí sola **deniega todas las solicitudes**. Otras políticas ALLOW coincidentes pueden proporcionar excepciones; una política explícita DENY-all no puede ser anulada por ALLOW.

**Explicación:**

**Comportamiento predeterminado de AuthorizationPolicy:**

1. **No existe ninguna política**: se permiten todas las solicitudes
2. **Especificación vacía (como el ejemplo)**: se deniegan todas las solicitudes
3. **Tiene reglas**: permite/deniega según las reglas

**Patrón de denegación predeterminada:**

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

**Evaluación:** CUSTOM → DENY → ALLOW. Un proveedor CUSTOM coincidente debe permitir la solicitud; después, cualquier DENY coincidente la rechaza. Si existen políticas ALLOW aplicables, al menos una regla debe coincidir. Sin una política ALLOW aplicable, esta etapa permite la solicitud. Las reglas y las políticas ALLOW forman una unión, no una lista ordenada de restricciones adicionales. AUDIT marca las solicitudes coincidentes para un complemento de auditoría configurado; no es una cuarta etapa de aplicación y no registra por sí solo.

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

**Prueba:** ejecútala desde la carga de trabajo frontend integrada en la malla mediante ServiceAccount `frontend`; configura la detección de protocolo/puerto HTTP de backend.

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

¿Qué campos se usan para validar tokens JWT en RequestAuthentication?

A. issuer y audiences\
B. principals y namespaces\
C. methods y paths\
D. hosts y ports

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

RequestAuthentication utiliza los campos **issuer** y **audiences** para validar tokens JWT.

**Explicación:**

Un token, cuando está presente, debe superar las comprobaciones de firma, emisor, audiencia y tiempo. RequestAuthentication por sí solo acepta que falte un token; AuthorizationPolicy debe requerir `requestPrincipals`. Los valores de marca de tiempo siguientes son una ilustración histórica expirada, no un token utilizable.

**Estructura de token JWT:**

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

**Configuración de RequestAuthentication:**

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

**Proceso de validación de JWT:**

![Diagrama de flujo que muestra cómo un sidecar valida un JWT entrante: comprueba secuencialmente el emisor del token, las audiencias, la firma JWKS y la expiración; rechaza la solicitud con 401 Unauthorized si alguna comprobación falla y solo la permite cuando las cuatro comprobaciones se superan.](../../../.gitbook/assets/en-quizzes-service-mesh-istio-security-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-quizzes-service-mesh-istio-security-0.html)

El diagrama describe la validación de un token presente, no la autorización ni el manejo de tokens ausentes. Los ejemplos de proveedores siguientes son alternativas; configura el tipo de token y la audiencia que espera la aplicación.

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

¿Cuál es el período de validez predeterminado de los certificados mTLS en Istio?

A. 1 hora\
B. 24 horas\
C. 7 días\
D. 90 días

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B**

El período de validez predeterminado de los certificados mTLS en Istio es de **24 horas** y se renuevan automáticamente.

**Explicación:**

El agente solicita de forma predeterminada un certificado hoja de 24 horas y lo renueva aproximadamente a la mitad de su vida útil, con fluctuación (`SECRET_GRACE_PERIOD_RATIO=0.5`). Istiod o la CA externa seleccionada firma la solicitud; el agente entrega el resultado a Envoy mediante SDS. Las vidas útiles de raíz/intermedios son independientes. La raíz autofirmada predeterminada firma directamente los certificados hoja de las cargas de trabajo; una jerarquía intermedia es una elección del administrador.

Inspecciona el certificado público sin suponer un archivo `/etc/certs` en disco ni un orden fijo de la matriz SDS:

```bash
istioctl proxy-config secret <pod-name> -n <namespace> -o json | \
  jq -r '.dynamicActiveSecrets[] | select(.secret.name == "default") | .secret.tlsCertificate.certificateChain.inlineBytes' | \
  base64 -d | openssl x509 -noout -dates -issuer -ext subjectAltName
```

**Personalización del período de validez:**

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

Este es un fragmento de entrada para `istioctl install -f`, no un recurso de operador dentro del clúster. El emisor puede limitar el TTL de 48 horas solicitado; verifica el certificado emitido y rota los proxies seleccionados al cambiar la configuración de bootstrap.

Si falla la renovación, inspecciona los registros del agente e istiod, la conectividad de CA, la autenticación de tokens, la sincronización del reloj y los paquetes de confianza antes de reiniciar las cargas de trabajo. Un reinicio por sí solo no corrige una CA expirada. La integración con cert-manager requiere **istio-csr** y sus requisitos previos de instalación; `EXTERNAL_CA=ISTIOD_RA_KUBERNETES_API` por sí solo no es una configuración de cert-manager. Consulta la [guía del ciclo de vida de certificados](../../../service-mesh/istio/security/01-mtls.md).

</details>

***

### Pregunta 5: Autenticación basada en Service Account

¿Qué identidad se utiliza para la autenticación de servicio a servicio en Istio?

A. Nombre de Pod\
B. Nombre de Service\
C. Service Account\
D. Nombre de Namespace

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Istio administra la identidad de servicio a servicio basada en **Service Account**.

**Explicación:**

**Identidad basada en Service Account:**

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

**Formato de ID SPIFFE:**

```
spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>

Examples:
spiffe://cluster.local/ns/default/sa/frontend
spiffe://cluster.local/ns/production/sa/backend
```

**Uso de Service Account en AuthorizationPolicy:**

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

La imagen anterior es un marcador de posición de aplicación. Kubernetes RBAC controla el acceso a la API de Kubernetes; no otorga automáticamente permisos de tráfico de malla. La autorización de Istio usa por separado la identidad autenticada de ServiceAccount. Un principal también incluye el namespace y el dominio de confianza.

**Service Account frente a nombre de Pod/Service:**

| Elemento                 | Service Account         | Nombre de Pod            | Nombre de Service    |
| -------------------- | ----------------------- | ------------------- | --------------- |
| **Estabilidad**        | Estable                  | Cambia dinámicamente | Estable          |
| **Seguridad**         | Basada en certificados       | No confiable     | No confiable |
| **Integración con RBAC** | Kubernetes RBAC         | No posible        | No posible    |
| **mTLS**             | Incluido en el certificado | No incluido        | No incluido    |

**Ejemplo práctico: aplicación de 3 niveles:**

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

**Comprobación de Service Account:**

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
* [Política de autorización](../../../service-mesh/istio/security/03-authorization.md)

</details>

***

## Preguntas de respuesta corta (6-10)

### Pregunta 6: Implementación de una política de seguridad de denegación predeterminada

Explica paso a paso cómo implementar una política de seguridad de **denegación predeterminada** mediante Istio en un clúster de Kubernetes. Incluye los **recursos requeridos** (PeerAuthentication, AuthorizationPolicy) y los métodos de **manejo de excepciones**.

<details>

<summary>Mostrar respuesta</summary>

1. Haz un inventario de los llamadores reales, ServiceAccounts, puertos de cargas de trabajo y protocolos de aplicación. Incorpora las cargas de trabajo a la malla y, después de comprobar la compatibilidad, aplica `STRICT` al namespace. PeerAuthentication por sí solo no autoriza a los llamadores.
2. Aplica una política ALLOW vacía como línea base del namespace; añade reglas explícitas para el grafo de llamadas requerido. No uses `DENY` con `rules: [{}]` cuando se pretendan excepciones.
3. El ejemplo supone el namespace `app`, cargas de trabajo frontend/backend/database integradas en la malla con etiquetas `app` y ServiceAccounts coincidentes, puerto HTTP 8080, puerto PostgreSQL 5432 y ServiceAccount de gateway `istio-ingressgateway` en `istio-system`. Verifica esa identidad desde el Pod real del gateway. El Service de gateway asigna HTTPS 443 al **puerto de carga de trabajo 8443**, que es el puerto de AuthorizationPolicy. Configura por separado la terminación TLS y un VirtualService para `myapp.example.com/api/*`.

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

4. Conserva la reescritura de sondas predeterminada de Istio para sidecars: las sondas HTTP/TCP/gRPC de kubelet se dirigen a través del agente (normalmente 15020). Una ruta HTTP ALLOW no hace que el texto sin formato atraviese STRICT. Si un endpoint de estado heredado necesita una excepción de texto sin formato, `portLevelMtls` requiere un selector de carga de trabajo y el puerto de la carga de trabajo; las restricciones de autorización/red también deben limitar ese endpoint. No deshabilites mTLS en el puerto de la aplicación como solución genérica de estado.
5. Los puertos de métricas de agente/Envoy (15020/15090) son distintos de los endpoints de métricas de aplicación interceptados. Para un endpoint de métricas de aplicación protegido, limita una política ALLOW a la carga de trabajo, al puerto/ruta real y a un principal de Prometheus autenticado mediante mTLS. Para las métricas del agente, configura el scraping y el acceso de red; una AuthorizationPolicy sobre tráfico entrante de aplicación no es suficiente.
6. Valida la configuración efectiva y el tráfico permitido/denegado:

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

Frontend → backend debe llegar a la aplicación; frontend → database debe fallar en la capa TCP, no devolver HTTP 403. Backend → database debe llegar a PostgreSQL (las credenciales de database son una comprobación independiente). La falta de enrutamiento puede producir 404 antes de que una prueba de autorización alcance el backend esperado. Usa Pods calificados por namespace, contenedores de aplicación y clientes de prueba reales. Consulta [autorización](../../../service-mesh/istio/security/03-authorization.md) y [comprobaciones de estado](https://istio.io/latest/docs/ops/configuration/mesh/app-health-check/).

</details>

***

### Pregunta 7: Autenticación dual JWT + mTLS

Implementa un escenario en el que se usen juntos la **autenticación de usuario final (JWT)** y la **autenticación de servicio a servicio (mTLS)** en Istio. Incluye cómo integrarlo con proveedores OAuth2/OIDC (por ejemplo, Keycloak).

<details>

<summary>Mostrar respuesta</summary>

Configura el realm de Keycloak `myrealm`, un cliente OIDC y una audiencia de API explícita `myapp`. Usa el flujo de código de autorización con PKCE y URI de redirección HTTPS exactas. El tipo/autenticación de cliente depende de si la aplicación puede conservar un secreto. Los roles de Keycloak normalmente aparecen en `realm_access.roles`; usa un mapeador de audiencia/ámbito de cliente para que el token de API tenga el `aud` esperado.

Cada proxy que evalúe `requestPrincipals` o `request.auth.claims` necesita su propia RequestAuthentication. Un JWT verificado en el gateway no establece la identidad de la solicitud en frontend ni backend. `forwardOriginalToken` conserva el token en esa solicitud reenviada y **la aplicación frontend debe propagar Authorization a su nueva solicitud de backend**.

Lo siguiente reemplaza las políticas relacionadas de la Pregunta 6. No mantengas una política ALLOW más amplia junto a las reglas de backend restringidas por rol: las políticas ALLOW forman una unión. Los requisitos previos de Deployment y gateway HTTPS son los mismos que en la Pregunta 6.

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

Para una aplicación que necesite una reclamación escalar como encabezado, RequestAuthentication admite el campo experimental `outputClaimToHeaders`, por ejemplo, `header: x-user-id` con `claim: sub`. Usa reclamaciones JWT validadas para la autorización; no confíes en encabezados de identidad proporcionados por quien llama. `outputPayloadToHeader` contiene una carga útil codificada y el tiempo de ejecución Lua de Envoy no incluye un módulo arbitrario `require("json")`. Las matrices de roles deben coincidir como reclamaciones en lugar de concatenarse ciegamente en encabezados.

Obtén un token de prueba mediante el flujo de inicio de sesión configurado y después prueba HTTPS. No incluyas contraseñas/secretos de cliente en los comandos del cuestionario:

```bash
read -rsp "Test access token: " TOKEN; echo
curl -i -H "Authorization: Bearer $TOKEN" https://myapp.example.com/api/users/test
unset TOKEN
curl -i https://myapp.example.com/api/users/test
# No JWT: 403 from AuthorizationPolicy.
curl -i -H "Authorization: Bearer invalid-token" https://myapp.example.com/api/users/test
# Invalid JWT: 401 from RequestAuthentication.
```

Prueba también un token válido de ServiceAccount incorrecta, audiencia incorrecta y rol insuficiente. Los cambios de roles JWT no revocan instantáneamente los tokens ya emitidos; importan la vida útil del token y los mecanismos de revocación del emisor/aplicación. Consulta [autenticación](../../../service-mesh/istio/security/02-authentication.md) y [tipos de concesión de Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).

</details>

***

### Pregunta 8: Control de acceso a servicios externos

Explica cómo controlar el **tráfico de Egress** en Istio para permitir el acceso únicamente a servicios externos específicos. Incluye ejemplos completos con **ServiceEntry**, **VirtualService** y **AuthorizationPolicy**.

<details>

<summary>Mostrar respuesta</summary>

`ALLOW_ANY` reenvía destinos desconocidos; `REGISTRY_ONLY` rechaza los destinos desconocidos en el registro del proxy. El registro incluye servicios de Kubernetes además de ServiceEntry. Ninguno de los modos es un firewall, y una aplicación puede omitir el proxy sin restricciones de red independientes. Aplica los ajustes de malla mediante los valores de instalación existentes; no reemplaces todo el ConfigMap `istio` por un fragmento de un campo.

AuthorizationPolicy evalúa el tráfico recibido por su proxy seleccionado. Una política de namespace en sidecars de cliente no es una ACL de salida. Para control de identidad/método/ruta, enruta a través de un gateway de egress que termina mTLS de malla, autoriza allí y después origina TLS al servidor externo. La aplicación envía HTTP al sidecar; el paso directo de HTTPS ocultaría las rutas y los métodos HTTP.

Requisitos previos: clientes integrados en la malla en el namespace `app`, un gateway de egress dedicado con la etiqueta `istio: egressgateway`, Service `istio-egressgateway.istio-system.svc.cluster.local` que asigna 443 al puerto de carga de trabajo 8443 y ninguna otra política ALLOW amplia de gateway. La confianza de CA pública del proxy instalado debe validar el certificado de GitHub.

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

El cliente de malla llama a `http://api.github.com/users/octocat`. Su sidecar se conecta al gateway con ISTIO_MUTUAL. El listener HTTP del gateway puede aplicar ServiceAccount de backend y GET `/users/*`; luego envía HTTPS a GitHub mediante el puerto 80 → targetPort 443. Los reintentos mostrados son para este caso de uso GET idempotente, no para API arbitrarias con efectos secundarios.

```bash
kubectl exec <backend-pod> -n app -c backend -- curl -i http://api.github.com/users/octocat
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://api.github.com/users/octocat
# Gateway should reject the second caller with HTTP 403.
istioctl proxy-config clusters <egress-pod> -n istio-system --fqdn api.github.com -o json
istioctl x authz check <egress-pod>.istio-system
```

Para una base de datos externa privada, usa un ServiceEntry STATIC con endpoints/dirección explícitos y puerto TCP 5432; la autenticación TLS/base de datos debe diseñarse para ese protocolo. Un servicio solo HTTP puede usar un ServiceEntry HTTP, pero los datos sensibles requieren cifrado. Almacena las credenciales de API en la aplicación o en un componente de firma/autenticación compatible respaldado por secretos; los literales de encabezado de VirtualService son configuración legible, no almacenamiento de secretos.

Por último, aplica el patrón mediante controles de CNI NetworkPolicy/firewall: los clientes pueden alcanzar los servicios de malla requeridos, DNS, istiod y el gateway de egress, pero no IP de Internet arbitrarias; el gateway obtiene el acceso externo requerido. Considera IPv4/IPv6, puertos de omisión/excluidos y cargas de trabajo privilegiadas. NetworkPolicy estándar no filtra nombres DNS; usa un control compatible con reconocimiento de FQDN cuando sea necesario. Prueba la omisión directa de IP/HTTPS además de la ruta aprobada. Consulta [control de egress](../../../service-mesh/istio/traffic-management/11-egress-control.md) y [originación TLS](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway-tls-origination/).

</details>

***

### Pregunta 9: Auditoría y registro de seguridad

Explica cómo **auditar** y registrar eventos relacionados con la seguridad en Istio. Incluye la **acción AUDIT de AuthorizationPolicy** y la configuración de **Access Log**.

<details>

<summary>Mostrar respuesta</summary>

`AUDIT` marca las solicitudes coincidentes para un **complemento de auditoría instalado**. Sin ese complemento, la política no tiene efecto de registro y no permite ni deniega tráfico. Este ejemplo audita una conjunción (DELETE y ruta de administrador), no dos condiciones ordenadas:

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

El registro de acceso es independiente. Combina este proveedor personalizado con la configuración de instalación de Istio existente mediante `istioctl install -f` (conserva los demás proveedores/ajustes) y habilítalo solo para el backend seleccionado. Las cadenas de consulta, los tokens Bearer y las cargas útiles JWT completas se excluyen deliberadamente del formato.

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

El recurso Telemetry también añade una dimensión `security_operation` acotada (`admin`/`other`) a los recuentos de solicitudes. `request_method` y la ruta URL sin procesar no son etiquetas de métricas predeterminadas de Istio. Evita etiquetas de URL completas debido a la cardinalidad y los datos sensibles. Los errores, solicitudes DELETE y accesos de administrador se registran aunque no haya un complemento AUDIT instalado. Para habilitar todas las solicitudes, omite el filtro; para cubrir un namespace, omite el selector; una política de namespace raíz sin selector abarca toda la malla.

Para CloudWatch, implementa/configura el agente de registro de EKS compatible o un DaemonSet de Fluent Bit con montajes de registros de nodo, análisis de CRI/containerd, análisis JSON del campo `log`, credenciales IAM y una salida de CloudWatch. Un ConfigMap por sí solo no inicia un agente. Para Elasticsearch/OpenSearch, usa una salida de recopilador configurada para ese destino; Telemetry con el proveedor `envoy` escribe en stdout y no configura Elasticsearch. Fargate necesita su mecanismo de registro compatible en lugar de un DaemonSet de nodo.

Después de ingerir los campos JSON estructurados, ejecuta cada consulta de CloudWatch Logs Insights por separado:

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

Un 403 puede provenir de la aplicación, la autorización JWT o un proveedor externo. Inspecciona `response_code_details`, los registros RBAC del proxy y la política efectiva antes de atribuirlo a Istio. No supongas que `envoy_http_rbac_logged_total` es un contador AUDIT integrado. Las estadísticas reales de RBAC/ejecución en seco experimental dependen de la configuración y nomenclatura del proxy; inspecciona las series exportadas.

Grafana puede representar la tasa estándar de 403 informada por el destino y la dimensión personalizada de administrador. Un PrometheusRule seleccionado por el Prometheus Operator instalado puede alertar sobre esta última:

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

Antes de aplicar una nueva política, la anotación experimental `istio.io/dry-run: "true"` en ALLOW/DENY puede informar decisiones sombra; es distinta de AUDIT y su salida de diagnóstico no es una API estable. Establece la retención, los controles de acceso y el enmascaramiento según los requisitos reales de organización/legales; no existe un mandato universal de retención de 90 días/un año. Consulta [registro de acceso](https://istio.io/latest/docs/tasks/observability/logs/access-log/) y [ejecución en seco de autorización](https://istio.io/latest/docs/tasks/security/authorization/authz-dry-run/).

</details>

***

### Pregunta 10: Implementación de una red Zero Trust

Explica cómo implementar los principios de **red Zero Trust** mediante Istio. Incluye ejemplos completos que apliquen los principios de **mTLS STRICT**, **denegación predeterminada** y **mínimo privilegio**.

<details>

<summary>Mostrar respuesta</summary>

Zero Trust combina identidades autenticadas, autorización explícita de mínimo privilegio y controles que siguen siendo efectivos cuando una carga de trabajo se ve comprometida. Istio protege el tráfico capturado por su plano de datos; no reemplaza Kubernetes RBAC, la política de admisión, el aislamiento de red ni la autorización de la aplicación.

1. Asigna ServiceAccounts separadas a frontend/backend/database e impide que las cargas de trabajo asuman libremente las cuentas de las demás. Incorpora las cargas de trabajo a la malla; verifica el dominio de confianza, la emisión y renovación de certificados.
2. Aplica STRICT al namespace objetivo y una línea base ALLOW vacía allí. Una política en `default` no cubre automáticamente `app`; una línea base de namespace raíz tiene efectos más amplios y requiere excepciones explícitas de gateway/operación.
3. Permite únicamente gateway → frontend → backend → database. Con los mismos requisitos previos de despliegue que la Pregunta 6, el conjunto completo de políticas de tráfico es:

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

4. Cuando se necesite aislamiento de namespace, haz coincidir namespaces/principals autenticados. Un DENY que selecciona `production` con `notNamespaces: [production, istio-system]` bloquea **a otros llamadores hacia production**, no production → staging. Considera los gateways y operadores; DENY prevalece sobre ALLOW.
5. Si el acceso depende del horario comercial, usa autorización de aplicación o un proveedor de autorización externa CUSTOM configurado con una zona horaria, fuente de reloj y política de fallo explícitas. Una comprobación Lua `os.date()` con un punto de inserción/zona horaria no especificados no es un diseño de autorización completo. El permiso CUSTOM aún debe superar DENY/ALLOW.
6. Aplica egress mediante el patrón de gateway de la Pregunta 8 más controles de red; ni REGISTRY_ONLY ni una política de sidecar llamada `deny-all-egress` son un firewall. En cambio, un DENY entrante que coincida con cada host bloquearía el tráfico de aplicación y no puede deshacerse mediante ALLOW.
7. Conserva la reescritura de sondas, diseña el scraping para los puertos correctos y añade solo las excepciones necesarias como se explica en la Pregunta 6. Usa la validación JWT y la propagación de token por salto de la Pregunta 7 para la autorización de usuario final. Registra y alerta mediante la Pregunta 9, con supervisión de expiración de certificados del capítulo mTLS.
8. Comprueba la política real y prueba la matriz prevista de permitir/denegar, el acceso TCP a database y la omisión de egress después de cada cambio:

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

Una puntuación del cuestionario no es evidencia de preparación para producción. Revisa la asignación de identidad de cargas de trabajo, las rutas de omisión de red, la confianza del emisor, las reglas de mínimo privilegio, la observabilidad, la reversión y los propios permisos de la aplicación para el entorno real. Consulta [conceptos de seguridad](https://istio.io/latest/docs/concepts/security/) y [autorización](../../../service-mesh/istio/security/03-authorization.md).

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (50 puntos en total)
* Respuesta corta 6-10: 10 puntos cada una (50 puntos en total)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: comprensión excelente de estos temas del cuestionario
* 80-89 puntos: buena comprensión; valida los despliegues reales por separado
* 70-79 puntos: promedio (se recomienda estudio adicional)
* 60-69 puntos: por debajo del promedio (se necesita revisión de conceptos básicos)
* 0-59 puntos: necesita volver a estudiar

## Recursos de aprendizaje

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Política de autorización](../../../service-mesh/istio/security/03-authorization.md)
* [Autenticación de solicitudes](../../../service-mesh/istio/security/02-authentication.md)
* [Autenticación de pares](../../../service-mesh/istio/security/01-mtls.md)
