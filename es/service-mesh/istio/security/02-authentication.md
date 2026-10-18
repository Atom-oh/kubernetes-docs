# Autenticación

Istio admite la autenticación entre servicios (Peer Authentication) y la autenticación de usuarios finales (Request Authentication).

## Tabla de contenido

1. [Descripción general de la autenticación](#authentication-overview)
2. [Autenticación de solicitudes (JWT)](#request-authentication-jwt)
3. [Integración de OAuth/OIDC](#oauthoidc-integration)
4. [Ejemplos prácticos](#practical-examples)
5. [Solución de problemas](#troubleshooting)

<span id="authentication-overview"></span>

## Descripción general de la autenticación

RequestAuthentication rechaza los JWT presentados que no sean válidos, pero acepta las solicitudes sin credenciales, salvo que AuthorizationPolicy exija que las incluyan. Verifica los tokens; no gestiona el inicio de sesión, las redirecciones de OAuth, la renovación de tokens ni la introspección de tokens de acceso opacos. Usa el documento de descubrimiento del emisor para obtener el emisor y el JWKS exactos, y configura la audiencia prevista. Los ejemplos son alternativas para la carga de trabajo HTTP `app=myapp` en el espacio de nombres `default`; el diagrama muestra un despliegue de gateway, al que se debe asociar la política en lugar de a la aplicación.

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authn.svg" alt="Autenticación de Istio" width="800">
</p>

Istio proporciona dos tipos de autenticación:

1. **Peer Authentication (autenticación entre servicios)**
   - Autenticación entre servicios mediante mTLS
   - Verificación de identidad basada en SPIFFE ID
   - Configuración mediante el CRD PeerAuthentication

2. **Request Authentication (autenticación de usuarios finales)**
   - Autenticación de usuarios mediante tokens JWT
   - Integración con proveedores de OAuth/OIDC
   - Configuración mediante el CRD RequestAuthentication

![Un usuario inicia sesión con un proveedor de OAuth/OIDC para obtener un JWT y lo envía a Request Authentication en el Istio Gateway, que reenvía a la aplicación las solicitudes verificadas y devuelve al usuario las que no superan la verificación.](../../../.gitbook/assets/en-service-mesh-istio-security-02-authentication-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-security-02-authentication-0.html)

<span id="request-authentication-jwt"></span>

## Autenticación de solicitudes (JWT)

### Verificación básica de JWT

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
```

### Compatibilidad con varios emisores

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: multi-issuer-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
  - issuer: "https://login.microsoftonline.com/tenant-id/v2.0"
    jwksUri: "https://login.microsoftonline.com/tenant-id/discovery/v2.0/keys"
    audiences: ["<your-api-application-client-id>"]
```

### Encabezado personalizado

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-custom-header
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences: ["my-api"]
    fromHeaders:
    - name: "x-auth-token"
      prefix: "Bearer "
```

<span id="oauthoidc-integration"></span>

## Integración de OAuth/OIDC

### AWS Cognito

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: cognito-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EXAMPLE"
    jwksUri: "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EXAMPLE/.well-known/jwks.json"
```

Para acceder a la API de Cognito, valida que `token_use=access` y el `client_id` previsto. Los tokens de ID usan `aud` para el ID de cliente de la aplicación; `aud` solo está presente en los tokens de acceso cuando hay una vinculación con un recurso, así que no apliques sin más la regla de audiencia del token de ID a un token de acceso. Añade la autorización específica de la API mediante scopes o grupos según sea necesario. Sustituye los valores de ejemplo del grupo de usuarios y del cliente.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: cognito-access-token
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals:
        - "https://cognito-idp.us-west-2.amazonaws.com/us-west-2_EXAMPLE/*"
    when:
    - key: request.auth.claims[token_use]
      values: ["access"]
    - key: request.auth.claims[client_id]
      values: ["<your-app-client-id>"]
```

### Keycloak

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: keycloak-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://keycloak.example.com/realms/myrealm"
    jwksUri: "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"
    audiences: ["my-api"]
```

La ruta de contexto predeterminada actual de Keycloak no incluye `/auth`. Si el despliegue está configurado con `http-relative-path=/auth`, usa en su lugar la ruta del emisor configurada.

### Auth0

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: auth0-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://your-tenant.auth0.com/"
    jwksUri: "https://your-tenant.auth0.com/.well-known/jwks.json"
    audiences:
    - "https://your-api.example.com"
```

<span id="practical-examples"></span>

## Ejemplos prácticos

### Verificación de JWT y autorización

```yaml
# JWT Verification
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  jwtRules:
  - issuer: "https://auth.example.com"
    jwksUri: "https://auth.example.com/.well-known/jwks.json"
    audiences: ["my-api"]
---
# Deny requests without JWT
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: myapp
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["*"]
```

<span id="troubleshooting"></span>

## Solución de problemas

### Error en la verificación de JWT

```bash
# 1. Check RequestAuthentication
kubectl get requestauthentication -A
kubectl describe requestauthentication <name> -n <namespace>

# 2. Decode JWT token
python3 - <<'PYJWT'
import base64, getpass, json
segment = getpass.getpass("JWT (not echoed): ").split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
print({k: claims.get(k) for k in ("iss", "aud", "exp", "nbf", "token_use", "client_id")})
PYJWT

# 3. Verify JWKS endpoint
curl -fsS https://auth.example.com/.well-known/jwks.json

# 4. Check Envoy logs
kubectl logs <pod-name> -c istio-proxy -n <namespace> | grep JWT
```

Las claims decodificadas no son confiables hasta que se validen la firma, el emisor, la audiencia y el tiempo. No pegues tokens activos en el historial de comandos ni en decodificadores públicos. La verificación local de JWT no consulta automáticamente el estado de revocación del emisor. Prueba casos sin token, con token caducado, con emisor/audiencia incorrectos y con un token válido. Para la autenticación L7 en modo ambient, usa `targetRefs` del waypoint en lugar de selectores de cargas de trabajo.

## Referencias

- [Autenticación de solicitudes de Istio](https://istio.io/latest/docs/reference/config/security/request_authentication/)
- [Autenticación JWT](https://istio.io/latest/docs/tasks/security/authentication/authn-policy/)

- [Referencia principal 1](https://istio.io/latest/docs/reference/config/security/request_authentication/)
- [Referencia principal 2](https://istio.io/latest/docs/reference/config/security/authorization-policy/)
- [Referencia principal 3](https://istio.io/latest/docs/reference/config/security/peer_authentication/)
- [Referencia principal 4](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html)
- [Referencia principal 5](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html)
- [Referencia principal 6](https://www.keycloak.org/migration/migrating-to-quarkus)
- [Referencia principal 7](https://www.keycloak.org/securing-apps/oidc-layers)
