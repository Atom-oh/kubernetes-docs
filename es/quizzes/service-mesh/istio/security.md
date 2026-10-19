# Cuestionario de seguridad

> **Última actualización**: 12 de octubre de 2026
>
> **Versiones**: Istio 1.31, que admite Kubernetes 1.32–1.37 (soporte estándar de EKS: 1.34–1.37).
> Consulta la [matriz de instalación](../../../service-mesh/istio/01-installation.md).

Este cuestionario evalúa la seguridad de Istio mediante ejemplos con sidecars. Cada pregunta plantea un escenario independiente: no combines todas las políticas ALLOW sobre una misma carga de trabajo. En ambient, las políticas HTTP/JWT requieren `targetRefs` asociados a un waypoint; PeerAuthentication `DISABLE` no está admitido. Los nombres de las cargas de trabajo, las cuentas de servicio, los puertos y las identidades deben corresponder al despliegue real.

## Preguntas de opción múltiple (1-5)

### Pregunta 1: Modo PeerAuthentication

¿Qué afirmación describe correctamente el modo mTLS **PERMISSIVE** en PeerAuthentication?

A. Permite tráfico mTLS y tráfico sin cifrar\
B. Solo permite mTLS y rechaza el tráfico sin cifrar\
C. Rechaza todo el tráfico\
D. Deshabilita mTLS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A**

El modo PERMISSIVE **permite tanto tráfico mTLS como tráfico sin cifrar** para facilitar una migración gradual.

**Explicación:**

**Modos mTLS de PeerAuthentication:**

| Modo           | Descripción                    | Escenario de uso                          |
| -------------- | ------------------------------ | ------------------------------------- |
| **PERMISSIVE** | Permite mTLS y tráfico sin cifrar | Migración gradual, entornos mixtos |
| **STRICT**     | Solo permite mTLS               | Refuerzo de la seguridad en producción         |
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

Una especificación vacía usa la acción ALLOW de forma predeterminada, sin reglas que puedan coincidir. Por eso, esta política por sí sola **deniega todas las solicitudes**. Otras políticas ALLOW aplicables pueden crear excepciones; una política DENY explícita que deniegue todo no puede anularse con ALLOW.

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

**Evaluación:** CUSTOM → DENY → ALLOW. El proveedor CUSTOM aplicable debe permitir la solicitud; después, cualquier regla DENY que coincida la rechaza. Si hay políticas ALLOW aplicables, debe coincidir al menos una regla. Si no las hay, esta etapa permite la solicitud. Las reglas y las políticas ALLOW suman los permisos que conceden; no forman una lista ordenada de restricciones acumulativas. AUDIT marca las solicitudes coincidentes para un complemento de auditoría configurado: no constituye una cuarta etapa de control ni genera registros por sí solo.

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

**Prueba:** ejecuta las solicitudes desde la carga de trabajo frontend integrada en la malla, con la cuenta de servicio `frontend`. Configura la detección del protocolo HTTP y del puerto del backend.

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

Cuando se presenta un token, este debe superar las comprobaciones de firma, emisor, audiencia y vigencia. RequestAuthentication por sí solo permite solicitudes sin token; para exigirlo, AuthorizationPolicy debe requerir `requestPrincipals`. Las marcas de tiempo del ejemplo siguiente ya han caducado: ilustran la estructura del token y no sirven para generar uno utilizable.

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

El diagrama muestra la validación de un token presente, no la autorización ni el tratamiento de solicitudes sin token. Los proveedores del ejemplo siguiente son alternativas; configura el tipo de token y la audiencia que espera la aplicación.

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

El agente solicita de forma predeterminada un certificado de carga de trabajo con una validez de 24 horas y lo renueva aproximadamente a mitad de su vigencia, con una variación aleatoria en el momento de renovación (`SECRET_GRACE_PERIOD_RATIO=0.5`). Istiod o la CA externa elegida firma la solicitud; el agente entrega el certificado a Envoy mediante SDS. Las duraciones de los certificados raíz e intermedios son independientes. La raíz autofirmada predeterminada firma directamente los certificados de las cargas de trabajo; usar una jerarquía con una CA intermedia es una decisión del administrador.

Inspecciona el certificado público sin dar por hecho que existe un archivo en `/etc/certs` ni que los elementos de SDS aparecen en un orden fijo:

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

Este fragmento se usa como entrada de `istioctl install -f`; no es un recurso de Operator que se aplique dentro del clúster. El emisor puede limitar el TTL solicitado de 48 horas. Comprueba el certificado emitido y renueva de forma controlada los proxies seleccionados cuando cambies sus parámetros de inicialización.

Si falla la renovación, revisa los registros del agente y de istiod, la conectividad con la CA, la autenticación del token, la sincronización del reloj y los certificados de confianza antes de reiniciar las cargas de trabajo. Un reinicio por sí solo no resuelve la caducidad de una CA. La integración con cert-manager requiere **istio-csr** y sus requisitos de instalación; `EXTERNAL_CA=ISTIOD_RA_KUBERNETES_API` por sí solo no configura cert-manager. Consulta la [guía del ciclo de vida de los certificados](../../../service-mesh/istio/security/01-mtls.md).

</details>

***

### Pregunta 5: Autenticación basada en cuentas de servicio

¿Qué identidad se utiliza para la autenticación de servicio a servicio en Istio?

A. Nombre de Pod\
B. Nombre de Service\
C. Service Account\
D. Nombre de Namespace

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C**

Istio gestiona la identidad de servicio a servicio a partir de una **cuenta de servicio (Service Account)**.

**Explicación:**

**Identidad basada en una cuenta de servicio:**

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

La imagen de contenedor del ejemplo es ilustrativa y debe sustituirse por la de la aplicación. Kubernetes RBAC controla el acceso a la API de Kubernetes; no concede automáticamente permisos de tráfico en la malla. La autorización de Istio utiliza por separado la identidad autenticada de la cuenta de servicio. Esa identidad también incluye el espacio de nombres y el dominio de confianza.

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

Explica paso a paso cómo aplicar una política de seguridad de **denegación predeterminada** con Istio en un clúster de Kubernetes. Incluye los **recursos necesarios** (PeerAuthentication y AuthorizationPolicy) y cómo **definir las excepciones**.

<details>

<summary>Mostrar respuesta</summary>

1. Identifica los clientes reales, sus cuentas de servicio, los puertos de las cargas de trabajo y los protocolos de las aplicaciones. Incorpora las cargas de trabajo a la malla y aplica `STRICT` al espacio de nombres después de comprobar su compatibilidad. PeerAuthentication por sí solo no autoriza a los clientes.
2. Aplica una política ALLOW vacía como política base del espacio de nombres y añade reglas explícitas para las llamadas necesarias. No uses `DENY` con `rules: [{}]` si necesitas permitir excepciones.
3. El ejemplo supone un espacio de nombres `app`, cargas de trabajo frontend/backend/database integradas en la malla con etiquetas `app` y cuentas de servicio coincidentes, un puerto HTTP 8080, un puerto PostgreSQL 5432 y la cuenta de servicio del gateway `istio-ingressgateway` en `istio-system`. Verifica esa identidad en el Pod real del gateway. Su Service dirige HTTPS 443 al **puerto 8443 de la carga de trabajo**, que es el puerto que evalúa AuthorizationPolicy. Configura por separado la terminación TLS y un VirtualService para `myapp.example.com/api/*`.

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

4. Conserva la reescritura de sondas que Istio aplica de forma predeterminada a los sidecars: las sondas HTTP/TCP/gRPC de kubelet pasan por el agente, normalmente por el puerto 15020. Permitir una ruta HTTP mediante ALLOW no permite que el tráfico sin cifrar atraviese STRICT. Si un endpoint de salud heredado necesita una excepción sin mTLS, `portLevelMtls` requiere un selector de carga de trabajo y el puerto de esa carga; las restricciones de autorización y de red deben seguir limitando el acceso. No deshabilites mTLS en el puerto de la aplicación como solución general para las sondas de salud.
5. Los puertos de métricas del agente y de Envoy (15020/15090) son distintos de los endpoints de métricas de aplicación interceptados. Para proteger estos últimos, limita la política ALLOW a la carga de trabajo, al puerto y la ruta reales, y a una identidad de Prometheus autenticada mediante mTLS. Para las métricas del agente, configura la recopilación y el acceso de red; una AuthorizationPolicy sobre el tráfico entrante de la aplicación no basta.
6. Comprueba la configuración efectiva y prueba tanto el tráfico permitido como el denegado:

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

La llamada frontend → backend debe llegar a la aplicación. La llamada frontend → database debe fallar en la capa TCP, sin devolver HTTP 403. Backend → database debe llegar a PostgreSQL; sus credenciales se comprueban por separado. Un problema de enrutamiento puede devolver 404 antes de que la prueba de autorización alcance el backend previsto. Indica el espacio de nombres de los Pods y usa los contenedores de aplicación y clientes de prueba reales. Consulta [autorización](../../../service-mesh/istio/security/03-authorization.md) y [comprobaciones de salud](https://istio.io/latest/docs/ops/configuration/mesh/app-health-check/).

</details>

***

### Pregunta 7: Autenticación dual JWT + mTLS

Implementa un escenario en el que se combinen la **autenticación de usuario final (JWT)** y la **autenticación de servicio a servicio (mTLS)** en Istio. Incluye cómo integrarlo con proveedores OAuth2/OIDC (por ejemplo, Keycloak).

<details>

<summary>Mostrar respuesta</summary>

Configura el realm `myrealm` de Keycloak, un cliente OIDC y una audiencia de API explícita, `myapp`. Usa el flujo de código de autorización con PKCE y URI de redirección HTTPS exactas. El tipo de cliente y su autenticación dependen de si la aplicación puede custodiar un secreto. Los roles de Keycloak suelen aparecer en `realm_access.roles`; configura un mapeador de audiencia o un ámbito de cliente para que el token de la API incluya el `aud` esperado.

Cada proxy que evalúe `requestPrincipals` o `request.auth.claims` necesita su propia RequestAuthentication. Validar el JWT en el gateway no establece la identidad de la solicitud en el frontend ni en el backend. `forwardOriginalToken` conserva el token al reenviar esa solicitud, pero **la aplicación frontend debe propagar el encabezado Authorization cuando cree una nueva solicitud al backend**.

El ejemplo siguiente sustituye las políticas correspondientes de la pregunta 6. No conserves una política ALLOW más amplia junto a las reglas del backend restringidas por rol: las políticas ALLOW suman sus permisos. Los requisitos del despliegue y del gateway HTTPS son los mismos que en la pregunta 6.

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

Si la aplicación necesita un atributo escalar del JWT en un encabezado, RequestAuthentication ofrece el campo experimental `outputClaimToHeaders`; por ejemplo, `header: x-user-id` con `claim: sub`. Usa atributos JWT validados para autorizar y no confíes en los encabezados de identidad enviados por el cliente. `outputPayloadToHeader` contiene el contenido del token codificado, y el entorno de ejecución Lua de Envoy no incluye automáticamente un módulo arbitrario `require("json")`. Evalúa las listas de roles como atributos del token, en lugar de concatenarlas sin comprobación en encabezados.

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

Prueba también un token válido en una solicitud realizada desde una cuenta de servicio incorrecta, con una audiencia incorrecta y con un rol insuficiente. Cambiar los roles no revoca al instante los JWT ya emitidos: importan la vigencia del token y los mecanismos de revocación del emisor y de la aplicación. Consulta [autenticación](../../../service-mesh/istio/security/02-authentication.md) y [tipos de concesión de Keycloak](https://www.keycloak.org/securing-apps/oidc-layers).

</details>

***

### Pregunta 8: Control de acceso a servicios externos

Explica cómo controlar el **tráfico de salida (egress)** en Istio para permitir acceso solo a determinados servicios externos. Incluye ejemplos completos con **ServiceEntry**, **VirtualService** y **AuthorizationPolicy**.

<details>

<summary>Mostrar respuesta</summary>

`ALLOW_ANY` reenvía el tráfico hacia destinos desconocidos; `REGISTRY_ONLY` rechaza los destinos que no figuran en el registro del proxy. Ese registro incluye tanto servicios de Kubernetes como ServiceEntry. Ninguno de estos modos es un cortafuegos: sin restricciones de red independientes, una aplicación puede evitar el proxy. Modifica la configuración de la malla mediante los valores de su instalación existente; no sustituyas el ConfigMap `istio` completo por un fragmento con un solo campo.

AuthorizationPolicy evalúa el tráfico que recibe el proxy seleccionado. Una política de espacio de nombres aplicada a los sidecars de los clientes no constituye una ACL de salida. Para controlar identidad, método y ruta, dirige el tráfico a un gateway de salida que termine mTLS de la malla, autorice la solicitud y después establezca TLS con el servidor externo. La aplicación envía HTTP al sidecar; si HTTPS pasara sin terminarse, sus rutas y métodos quedarían ocultos.

Requisitos: clientes integrados en la malla en el espacio de nombres `app`, un gateway de salida dedicado con la etiqueta `istio: egressgateway`, el Service `istio-egressgateway.istio-system.svc.cluster.local` que dirija el puerto 443 al puerto 8443 de la carga de trabajo, y ninguna otra política ALLOW amplia sobre el gateway. Los certificados de CA pública en los que confía el proxy instalado deben permitir validar el certificado de GitHub.

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

El cliente de la malla llama a `http://api.github.com/users/octocat` y su sidecar se conecta al gateway mediante ISTIO_MUTUAL. El listener HTTP del gateway puede exigir la identidad de la cuenta de servicio del backend y el método GET para `/users/*`. Después envía HTTPS a GitHub mediante el puerto 80 → targetPort 443. Los reintentos mostrados corresponden a este GET idempotente; no deben aplicarse sin más a API que produzcan efectos secundarios.

```bash
kubectl exec <backend-pod> -n app -c backend -- curl -i http://api.github.com/users/octocat
kubectl exec <frontend-pod> -n app -c frontend -- curl -i http://api.github.com/users/octocat
# Gateway should reject the second caller with HTTP 403.
istioctl proxy-config clusters <egress-pod> -n istio-system --fqdn api.github.com -o json
istioctl x authz check <egress-pod>.istio-system
```

Para una base de datos externa privada, usa un ServiceEntry STATIC con dirección y endpoints explícitos y el puerto TCP 5432. Diseña TLS y la autenticación de la base de datos para ese protocolo. Un servicio que use solo HTTP puede tener un ServiceEntry HTTP, pero los datos sensibles requieren cifrado. Guarda las credenciales de la API en la aplicación o en un componente de firma o autenticación compatible que obtenga sus credenciales de secretos; los encabezados literales de un VirtualService son configuración legible y no sirven como almacén de secretos.

Por último, exige esa ruta mediante controles de NetworkPolicy del CNI y del cortafuegos. Los clientes deben poder acceder a los servicios necesarios de la malla, DNS, istiod y el gateway de salida, pero no a cualquier IP de Internet; el gateway recibe el acceso externo necesario. Ten en cuenta IPv4/IPv6, los puertos excluidos o que evitan el proxy y las cargas de trabajo privilegiadas. NetworkPolicy estándar no filtra nombres DNS: usa un mecanismo compatible que reconozca FQDN cuando sea necesario. Prueba también los accesos directos por IP y HTTPS que puedan evitar la ruta aprobada. Consulta [control de salida](../../../service-mesh/istio/traffic-management/11-egress-control.md) y [establecimiento de TLS en el gateway](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-gateway-tls-origination/).

</details>

***

### Pregunta 9: Auditoría y registro de seguridad

Explica cómo **auditar** y registrar los eventos de seguridad de Istio. Incluye la **acción AUDIT de AuthorizationPolicy** y la configuración de los **registros de acceso**.

<details>

<summary>Mostrar respuesta</summary>

`AUDIT` marca las solicitudes coincidentes para un **complemento de auditoría instalado**. Sin ese complemento, la política no genera registros y tampoco permite ni deniega tráfico. El ejemplo exige que coincidan DELETE y la ruta de administración a la vez; no son dos condiciones que se evalúen por orden:

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

Los registros de acceso se configuran por separado. Integra este proveedor personalizado en la configuración existente de Istio mediante `istioctl install -f`, conservando los demás proveedores y ajustes, y habilítalo solo para el backend seleccionado. El formato excluye deliberadamente las cadenas de consulta, los tokens Bearer y el contenido completo de los JWT.

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

Para CloudWatch, despliega y configura un agente de registros compatible con EKS o un DaemonSet de Fluent Bit: requiere montar los registros del nodo, interpretar CRI/containerd, analizar el JSON del campo `log`, disponer de credenciales IAM y configurar la salida a CloudWatch. Un ConfigMap por sí solo no ejecuta ningún agente. Para Elasticsearch/OpenSearch, configura la salida del recolector para ese destino; Telemetry con el proveedor `envoy` escribe en stdout y no configura Elasticsearch. Fargate necesita su mecanismo de registros compatible, en lugar de un DaemonSet en los nodos.

Una vez que los campos JSON estructurados se hayan incorporado a los registros, ejecuta cada consulta de CloudWatch Logs Insights por separado:

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

Antes de aplicar una política nueva, la anotación experimental `istio.io/dry-run: "true"` en ALLOW/DENY permite observar qué decisiones se tomarían sin aplicarlas. Esto es distinto de AUDIT y su salida de diagnóstico no es una API estable. Define la retención, los controles de acceso y la ocultación de datos sensibles según los requisitos reales de la organización y de la legislación aplicable; no hay una obligación universal de conservar registros durante 90 días o un año. Consulta [registros de acceso](https://istio.io/latest/docs/tasks/observability/logs/access-log/) y [pruebas de autorización sin aplicación](https://istio.io/latest/docs/tasks/security/authorization/authz-dry-run/).

</details>

***

### Pregunta 10: Implementación de una red Zero Trust

Explica cómo implementar los principios de **red Zero Trust** mediante Istio. Incluye ejemplos completos que apliquen los principios de **mTLS STRICT**, **denegación predeterminada** y **mínimo privilegio**.

<details>

<summary>Mostrar respuesta</summary>

Zero Trust combina identidades autenticadas, autorización explícita de mínimo privilegio y controles que siguen siendo efectivos cuando una carga de trabajo se ve comprometida. Istio protege el tráfico capturado por su plano de datos; no reemplaza Kubernetes RBAC, la política de admisión, el aislamiento de red ni la autorización de la aplicación.

1. Asigna cuentas de servicio distintas a frontend/backend/database e impide que las cargas de trabajo puedan usar libremente las cuentas de las demás. Incorpóralas a la malla y comprueba el dominio de confianza, la emisión y la renovación de certificados.
2. Aplica STRICT al espacio de nombres elegido y una política base ALLOW vacía. Una política en `default` no cubre automáticamente `app`; una política base en el espacio de nombres raíz afecta a un ámbito mayor y requiere excepciones explícitas para gateways y tareas operativas.
3. Permite únicamente gateway → frontend → backend → database. Con los requisitos del despliegue de la pregunta 6, el conjunto completo de políticas de tráfico es:

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

4. Para aislar espacios de nombres, aplica reglas sobre los espacios de nombres o las identidades autenticadas. Una regla DENY que seleccione `production` y use `notNamespaces: [production, istio-system]` bloquea **las llamadas de otros clientes hacia production**, no el tráfico production → staging. Ten en cuenta gateways y operadores: DENY prevalece sobre ALLOW.
5. Si el acceso depende del horario laboral, usa autorización en la aplicación o un proveedor externo CUSTOM configurado con zona horaria, fuente de reloj y política de fallo explícitas. Una comprobación Lua con `os.date()` sin definir su punto de inserción y zona horaria no constituye un diseño de autorización completo. Una autorización CUSTOM aún debe superar DENY/ALLOW.
6. Exige la salida mediante el gateway de la pregunta 8 y los controles de red. Ni REGISTRY_ONLY ni una política de sidecar llamada `deny-all-egress` son cortafuegos. Una regla DENY de entrada que coincida con cualquier host bloquearía el tráfico de la aplicación y no podría anularse con ALLOW.
7. Conserva la reescritura de sondas, configura la recopilación de métricas en los puertos correctos y añade solo las excepciones necesarias, como se explica en la pregunta 6. Para autorizar a los usuarios finales, aplica la validación JWT y la propagación del token en cada salto de la pregunta 7. Configura registros y alertas según la pregunta 9, y supervisa la caducidad de certificados como indica el capítulo de mTLS.
8. Comprueba la política efectiva y prueba, después de cada cambio, la matriz de accesos permitidos y denegados, el acceso TCP a la base de datos y las rutas que puedan evitar el gateway de salida:

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

La puntuación del cuestionario no demuestra que un despliegue esté listo para producción. En el entorno real, revisa la asignación de identidades a las cargas de trabajo, las rutas que puedan eludir los controles de red, la confianza en el emisor, las reglas de mínimo privilegio, la observabilidad, la reversión y los permisos propios de la aplicación. Consulta [conceptos de seguridad](https://istio.io/latest/docs/concepts/security/) y [autorización](../../../service-mesh/istio/security/03-authorization.md).

</details>

***

## Cálculo de puntuación

* Opción múltiple 1-5: 10 puntos cada una (50 puntos en total)
* Respuesta corta 6-10: 10 puntos cada una (50 puntos en total)
* **Total: 100 puntos**

**Criterios de evaluación:**

* 90-100 puntos: excelente comprensión de los temas del cuestionario
* 80-89 puntos: buena comprensión; comprueba por separado los despliegues reales
* 70-79 puntos: comprensión media; se recomienda ampliar el estudio
* 60-69 puntos: comprensión inferior a la media; conviene repasar los conceptos básicos
* 0-59 puntos: es necesario volver a estudiar los temas

## Recursos de aprendizaje

* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
* [Política de autorización](../../../service-mesh/istio/security/03-authorization.md)
* [Autenticación de solicitudes](../../../service-mesh/istio/security/02-authentication.md)
* [Autenticación de pares](../../../service-mesh/istio/security/01-mtls.md)
