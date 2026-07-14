# Cuestionario de Gateway API

Este cuestionario evalúa tu comprensión del modelo de recursos de Kubernetes Gateway API, las implementaciones y la migración desde Ingress.

## Preguntas del cuestionario

### 1. ¿Cuál NO es una forma en que Gateway API mejora la API de Ingress existente?

A. Separación de recursos basada en roles (proveedor de infraestructura, operador del clúster, desarrollador de aplicaciones)
B. Compatibilidad nativa con diversos protocolos como TCP, UDP y gRPC
C. Implementación de funcionalidades mediante campos estandarizados en lugar de anotaciones
D. Integración de todas las funciones de red en un único recurso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Integración de todas las funciones de red en un único recurso**

**Explicación:**
Mejoras de Gateway API:
- **Separación de roles**: La responsabilidad se separa en GatewayClass (infraestructura), Gateway (operador) y Routes (desarrollador)
- **Múltiples protocolos**: HTTPRoute, GRPCRoute, TCPRoute, TLSRoute, UDPRoute
- **Estandarización**: Definición de funcionalidades mediante campos explícitos sin anotaciones
- **Extensibilidad**: Facilidad para agregar nuevas funcionalidades basadas en CRD

Gateway API se separa en varios recursos, por lo que la «integración en un único recurso» es incorrecta.

</details>

### 2. En la separación de roles de Gateway API, ¿quién gestiona GatewayClass?

A. Desarrollador de aplicaciones
B. Operador del clúster
C. Proveedor de infraestructura
D. Administrador de seguridad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Proveedor de infraestructura**

**Explicación:**
Separación de roles de Gateway API:

| Rol | Recursos gestionados | Responsabilidad |
|------|------------------|----------------|
| **Proveedor de infraestructura** | GatewayClass | Definir la configuración básica de infraestructura, especificar el controller |
| **Operador del clúster** | Gateway, ReferenceGrant | Aprovisionamiento de balanceador de carga, gestión de permisos de namespace |
| **Desarrollador de aplicaciones** | HTTPRoute, GRPCRoute, etc. | Definir reglas de enrutamiento de aplicaciones |

GatewayClass es definido por proveedores de nube o equipos de red.

</details>

### 3. ¿Cuál es la diferencia correcta entre la terminación y el passthrough de TLS en Gateway?

A. Terminate pasa TLS al backend, Passthrough termina en Gateway
B. Terminate termina TLS en Gateway, Passthrough pasa TLS al backend
C. Ambos modos se comportan de forma idéntica
D. Terminate solo admite HTTP, Passthrough solo admite HTTPS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Terminate termina TLS en Gateway, Passthrough pasa TLS al backend**

**Explicación:**
Modos de TLS:

| Modo | Descripción | Caso de uso |
|------|-------------|----------|
| **Terminate** | TLS termina en Gateway; el backend recibe texto sin cifrar | HTTPS estándar, gestión centralizada de certificados |
| **Passthrough** | TLS se pasa al backend tal cual | Cifrado de extremo a extremo, el backend gestiona los certificados |

```yaml
listeners:
  - name: https
    protocol: HTTPS
    tls:
      mode: Terminate  # or Passthrough
```

</details>

### 4. ¿Cómo se implementa la división de tráfico (ponderaciones) en HTTPRoute?

A. Usar el campo `trafficSplit`
B. Especificar el campo `weight` en varios `backendRefs`
C. Usar la anotación `canary`
D. Crear un CRD TrafficSplit independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar el campo `weight` en varios `backendRefs`**

**Explicación:**
División de tráfico en HTTPRoute:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
spec:
  rules:
    - backendRefs:
        - name: app-stable
          port: 80
          weight: 90  # 90%
        - name: app-canary
          port: 80
          weight: 10  # 10%
```

Casos de uso:
- Despliegues canary
- Pruebas A/B
- Despliegues blue-green

Las ponderaciones no necesitan sumar 100; se calculan como proporciones.

</details>

### 5. ¿Cuál es el propósito principal de ReferenceGrant?

A. Gestión de permisos de recursos Gateway
B. Permitir referencias entre namespaces
C. Gestión de compatibilidad de versiones de API
D. Autorización de certificados TLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir referencias entre namespaces**

**Explicación:**
Uso de ReferenceGrant:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes
  namespace: backend-services
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend
  to:
    - group: ""
      kind: Service
```

Casos de uso:
- Permitir referencias a Services en otros namespaces
- Que Gateway haga referencia a Secrets (certificados TLS) en otros namespaces
- Autorización explícita para seguridad

Las referencias entre namespaces están bloqueadas de forma predeterminada.

</details>

### 6. ¿Cuál NO es un recurso incluido en el canal Standard de Gateway API?

A. GatewayClass
B. Gateway
C. HTTPRoute
D. TCPRoute

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. TCPRoute**

**Explicación:**
Clasificación de canales de Gateway API:

**Canal Standard (GA)**:
- GatewayClass
- Gateway
- HTTPRoute
- ReferenceGrant

**Canal Experimental (Beta/Alpha)**:
- GRPCRoute
- TCPRoute
- TLSRoute
- UDPRoute

Los recursos del canal Standard usan la versión de API `gateway.networking.k8s.io/v1`; Experimental usa `v1alpha2` o `v1beta1`.

</details>

### 7. ¿Qué tipo de filtro de HTTPRoute cambia la solicitud a una URL diferente?

A. RequestHeaderModifier
B. ResponseHeaderModifier
C. URLRewrite
D. RequestMirror

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. URLRewrite**

**Explicación:**
Tipos de filtros de HTTPRoute:

| Filtro | Descripción |
|--------|-------------|
| RequestHeaderModifier | Agregar/modificar/eliminar encabezados de solicitud |
| ResponseHeaderModifier | Agregar/modificar/eliminar encabezados de respuesta |
| **URLRewrite** | Cambiar la ruta o el host de la URL |
| RequestRedirect | Redirigir a una URL diferente (respuesta 3xx) |
| RequestMirror | Duplicar el tráfico (copiar al servicio sombra) |

```yaml
filters:
  - type: URLRewrite
    urlRewrite:
      path:
        type: ReplacePrefixMatch
        replacePrefixMatch: /new-api
      hostname: "new-api.example.com"
```

</details>

### 8. ¿Cuál NO es una implementación compatible con Gateway API?

A. Istio
B. Cilium
C. kube-proxy
D. Envoy Gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. kube-proxy**

**Explicación:**
Implementaciones de Gateway API:

| Implementación | Controller |
|----------------|------------|
| **Istio** | istio.io/gateway-controller |
| **Cilium** | io.cilium/gateway-controller |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller |
| **Contour** | projectcontour.io/gateway-controller |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller |

kube-proxy gestiona el enrutamiento de Service ClusterIP/NodePort y no está relacionado con Gateway API.

</details>

### 9. Al migrar de Ingress a Gateway API, ¿qué funcionalidad de Gateway API corresponde a las anotaciones de Ingress?

A. Metadatos de Gateway
B. Coincidencias y filtros de HTTPRoute
C. Parámetros de GatewayClass
D. Spec de ReferenceGrant

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Coincidencias y filtros de HTTPRoute**

**Explicación:**
Asignación de anotaciones de Ingress → Gateway API:

| Anotación de Ingress | Gateway API |
|-------------------|-------------|
| `nginx.ingress.kubernetes.io/rewrite-target` | Filtro HTTPRoute: URLRewrite |
| `nginx.ingress.kubernetes.io/ssl-redirect` | Filtro HTTPRoute: RequestRedirect |
| `nginx.ingress.kubernetes.io/canary-weight` | Ponderación de backendRefs de HTTPRoute |
| Enrutamiento basado en ruta | Ruta de coincidencias de HTTPRoute |
| Enrutamiento basado en encabezados | Encabezados de coincidencias de HTTPRoute |

Gateway API usa campos explícitos en lugar de anotaciones para una mejor portabilidad.

</details>

### 10. ¿Cuál es la configuración para permitir solo Routes de namespaces específicos en Gateway?

A. `allowedRoutes.namespaces.from: All`
B. `allowedRoutes.namespaces.from: Same`
C. `allowedRoutes.namespaces.from: Selector`
D. Tanto B como C son posibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Tanto B como C son posibles**

**Explicación:**
Configuración de allowedRoutes de Gateway:

```yaml
listeners:
  - name: https
    allowedRoutes:
      namespaces:
        from: All  # All namespaces
        # or
        from: Same  # Only same namespace as Gateway
        # or
        from: Selector  # Select by label selector
        selector:
          matchLabels:
            gateway-access: "true"
```

- **All**: Permitir Routes de todos los namespaces
- **Same**: Permitir solo del mismo namespace que Gateway
- **Selector**: Permitir solo de namespaces con etiquetas específicas

</details>

### 11. ¿Cuál es la configuración de matches para enrutar a un método específico de un servicio específico en GRPCRoute?

A. `path.service` y `path.method`
B. `method.service` y `method.method`
C. `grpc.service` y `grpc.method`
D. `rpc.service` y `rpc.method`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `method.service` y `method.method`**

**Explicación:**
Coincidencia de GRPCRoute:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
spec:
  rules:
    - matches:
        - method:
            service: "myapp.UserService"
            method: "GetUser"
      backendRefs:
        - name: user-service
          port: 50051
```

Opciones de enrutamiento de gRPC:
- Solo servicio: Todos los métodos de ese servicio
- Servicio + método: Solo el método específico
- También se admite el enrutamiento basado en encabezados

</details>

### 12. ¿Qué comparación entre Gateway API e Ingress API NO es correcta?

A. Gateway API admite separación basada en roles; Ingress no
B. Gateway API admite TCP/UDP de forma nativa; Ingress no
C. Gateway API admite división de tráfico de forma nativa; Ingress requiere anotaciones
D. Gateway API usa menos tipos de recursos que Ingress

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. Gateway API usa menos tipos de recursos que Ingress**

**Explicación:**
Gateway API frente a Ingress:

| Funcionalidad | Ingress | Gateway API |
|---------|---------|-------------|
| Número de recursos | 1 (Ingress) | Varios (GatewayClass, Gateway, Routes, etc.) |
| Separación de roles | Ninguna | Separación en 3 niveles |
| TCP/UDP | No compatible | Compatibilidad nativa |
| División de tráfico | Anotación | Nativa (weight) |
| Extensibilidad | Limitada | Basada en CRD |

Gateway API usa más tipos de recursos, pero esto proporciona separación de roles y flexibilidad.

</details>

---

## Recursos adicionales de aprendizaje

- [Documentación oficial de Gateway API](https://gateway-api.sigs.k8s.io/)
- [GitHub de Gateway API](https://github.com/kubernetes-sigs/gateway-api)
- [Guías específicas de implementación](https://gateway-api.sigs.k8s.io/implementations/)
