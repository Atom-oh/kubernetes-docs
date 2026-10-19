# Seguridad

> **Versión revisada**: Istio 1.31.0
> **Última actualización**: 11 de septiembre de 2026

Istio ofrece funciones de seguridad sólidas dentro de la malla de servicios. Basado en el modelo de seguridad Zero Trust, cifra automáticamente la comunicación entre servicios y ofrece un control de acceso detallado.

## Tabla de contenidos

1. [Descripción general de la arquitectura de seguridad](#security-architecture-overview)
2. [Características principales de seguridad](#core-security-features)
3. [Componentes de seguridad](#security-components)
4. [Documentación detallada](#next-steps)
5. [Prácticas recomendadas de seguridad](#security-best-practices)
6. [Supervisión de seguridad](#3-security-monitoring)

## Descripción general de la arquitectura de seguridad {#security-architecture-overview}

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/arch-sec.svg" alt="Istio Security Architecture" width="900">
</p>

Istio implementa un **modelo de seguridad Zero Trust** para el tráfico de las cargas de trabajo incorporadas a la malla. El tráfico excluido, los clientes que usan texto sin cifrar y los protocolos no compatibles aún requieren controles explícitos. A continuación se describen las principales responsabilidades de seguridad:

### Capas de la arquitectura de seguridad

![Diagrama de la autoridad de certificación de istiod y de la API de configuración que distribuyen certificados y políticas a los sidecars Envoy de dos pods; el cifrado mTLS se aplica solo entre los sidecars, sobre una cadena de cinco capas de seguridad desde la identidad hasta la autorización.](../../../.gitbook/assets/en-service-mesh-istio-security-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-security-readme-0.html)

### Componentes de seguridad {#security-components}

1. **Plano de control (istiod)**
   - Autoridad de certificación (CA): emisión y administración de certificados X.509
   - API de configuración: distribución y administración de políticas de seguridad
   - Descubrimiento de servicios: administración de identidades de cargas de trabajo

2. **Plano de datos (sidecars Envoy o ztunnel/waypoints de ambient)**
   - Puntos de terminación de mTLS: comunicación cifrada entre servicios
   - Aplicación de políticas: aplicación de políticas de autenticación y autorización
   - Telemetría de seguridad: recopilación de métricas de seguridad

3. **Administración de identidades**
   - Administración de identidades sólidas basada en el estándar SPIFFE
   - Integración con Kubernetes ServiceAccount
   - La validez predeterminada de los certificados es de 24 horas; se rotan antes de que caduquen

4. **Motor de políticas**
   - Políticas de seguridad declarativas (basadas en CRD)
   - Control de acceso detallado (RBAC)
   - Compatibilidad con registros de auditoría

## Características principales de seguridad {#core-security-features}

Istio ofrece las siguientes funciones principales de seguridad:

### 1. Seguridad de la comunicación (mTLS)

Migre las cargas de trabajo incluidas de PERMISSIVE a STRICT después de verificar que todos los clientes necesarios usan mTLS.

El mecanismo auto mTLS cifra la comunicación entre pares de cargas de trabajo incorporadas a la malla; PERMISSIVE también acepta texto sin cifrar. Use STRICT para exigir mTLS de la malla en las cargas de trabajo de entrada seleccionadas.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Production: STRICT, Migration: PERMISSIVE
```

**Descripción de los modos**:
- **STRICT**: solo permite mTLS (recomendado para producción)
- **PERMISSIVE**: permite tanto mTLS como texto sin cifrar (para la migración)
- **DISABLE**: deshabilita mTLS de transporte de Istio en el modo sidecar; no es compatible con ambient

Los siguientes ejemplos de políticas usan selectores de sidecars. ztunnel de ambient aplica seguridad L4; JWT y otras políticas L7 requieren un waypoint adecuado y la asociación mediante `targetRefs`.

### 2. Autenticación

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authn.svg" alt="Authentication Architecture" width="700">
</p>

Istio ofrece dos capas de autenticación:

- **Autenticación de pares (Peer Authentication)**: autenticación entre servicios (mTLS + SPIFFE ID)
- **Autenticación de solicitudes (Request Authentication)**: verificación de JWT para emisores compatibles; los flujos de inicio de sesión y OAuth siguen siendo externos

**Ejemplo**:
```yaml
# Request Authentication (JWT)
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: default
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
    audiences: ["<your-google-client-id>"]
```

### 3. Autorización

<p align="center">
  <img src="https://istio.io/latest/docs/concepts/security/authz.svg" alt="Authorization Architecture" width="600">
</p>

Se aplican políticas detalladas de control de acceso. AuthorizationPolicy permite controlar el acceso según:
- Cuenta de servicio / espacio de nombres
- Método HTTP / ruta
- Dirección IP
- Claims del JWT

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-read
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/myapp"]
    to:
    - operation:
        methods: ["GET"]
        paths: ["/api/*"]
```

## Prácticas recomendadas de seguridad {#security-best-practices}

### 1. Defensa en profundidad

Combine la identidad de transporte, credenciales de solicitud verificadas y reglas de autorización explícitas.

Implemente una defensa en profundidad aplicando controles de seguridad en varias capas:

**Capa de red**:
```yaml
# 1. Enable mTLS STRICT mode
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT
```

**Capa de aplicación**:
```yaml
# 2. Enable JWT authentication
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: require-jwt
  namespace: default
spec:
  jwtRules:
  - issuer: "https://your-auth-provider.com"
    jwksUri: "https://your-auth-provider.com/.well-known/jwks.json"
    audiences: ["<your-api-audience>"]
```

**Capa de control de acceso**:
```yaml
# 3. Default deny policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: default
spec:
  action: ALLOW
  rules: []
---
# 4. Allow only required access
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-specific
  namespace: default
spec:
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/frontend/sa/webapp"]
        requestPrincipals: ["*"]
    to:
    - operation:
        methods: ["GET", "POST"]
```

RequestAuthentication por sí sola acepta solicitudes sin token. El ejemplo ALLOW anterior requiere que se verifiquen tanto la identidad del par como el principal de la solicitud; una política ALLOW sin reglas establece la denegación predeterminada. Una regla DENY para todo tendría prioridad y bloquearía esas excepciones. Estos ejemplos de ámbito de espacio de nombres afectan a todas las cargas de trabajo coincidentes; delimite el alcance de forma intencionada con selectores o `targetRefs`. AUDIT requiere una implementación de auditoría configurada, y los registros de acceso deben habilitarse por separado.

### 2. Principio de privilegio mínimo

- Conceda a cada servicio solo los permisos mínimos necesarios
- Separe las cuentas de servicio con granularidad
- Use el aislamiento de espacios de nombres

<span id="3-security-monitoring"></span>

### 3. Supervisión de seguridad

- Habilite los registros de acceso de Istio
- Recopile métricas de seguridad con Prometheus
- Supervise el estado de mTLS con Kiali

## Próximos pasos {#next-steps}

1. **[mTLS](01-mtls.md)**: cifrado entre servicios y administración de identidades
2. **[Autenticación](02-authentication.md)**: integración de JWT y OAuth/OIDC
3. **[Autorización](03-authorization.md)**: políticas detalladas de control de acceso

## Referencias

### Documentación oficial
- [Conceptos de seguridad de Istio](https://istio.io/latest/docs/concepts/security/)
- [Prácticas recomendadas de seguridad](https://istio.io/latest/docs/ops/best-practices/security/)
- [Referencia de seguridad](https://istio.io/latest/docs/reference/config/security/)

### Estándares relacionados
- [Especificación SPIFFE](https://github.com/spiffe/spiffe)
- [OAuth 2.0 / OIDC](https://oauth.net/2/)
- [JWT (RFC 7519)](https://datatracker.ietf.org/doc/html/rfc7519)

## Cuestionario

Para poner a prueba sus conocimientos de este capítulo, pruebe el [cuestionario de seguridad de Istio](../../../quizzes/service-mesh/istio/security.md).
