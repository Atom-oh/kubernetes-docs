# Cuestionario de Gateway API

Basado en la versión 1.6 de la API y en los requisitos previos específicos de la implementación descritos en la guía. Cada ejemplo de código representa un escenario independiente.

## 1. ¿Cuál NO es un objetivo de diseño de Gateway API?

- A. Definir con mayor claridad la propiedad de los recursos entre infraestructura, operadores y aplicaciones
- B. Ofrecer tipos de API para varios protocolos de tráfico
- C. Proporcionar campos estándar con niveles definidos de compatibilidad de funciones
- D. Combinar todas las funciones de red en un solo objeto

<details>
<summary>Mostrar respuesta</summary>

D. Los recursos GatewayClass, Gateway y Route separan responsabilidades. Los controladores aún deben implementar la versión, el perfil y las funciones pertinentes de la API; RBAC/admission aplica la propiedad. Los campos estándar mejoran la portabilidad sin eliminar las extensiones específicas de cada implementación.

</details>

## 2. ¿Quién suele administrar GatewayClass en el modelo basado en roles?

- A. Cada desarrollador de aplicaciones por separado
- B. Solo el propietario de un Service de backend
- C. El proveedor de infraestructura o el equipo de plataforma/redes
- D. Un cliente de aplicación sin autenticar

<details>
<summary>Mostrar respuesta</summary>

C. GatewayClass selecciona el controlador instalado y los parámetros específicos de implementación que admita. Los operadores de plataforma administran Gateways y las políticas de asociación; los desarrolladores administran Routes. El propietario del espacio de nombres al que se hace referencia administra su ReferenceGrant. Estos son roles operativos, no permisos automáticos de Kubernetes.

</details>

## 3. ¿Cuál es la diferencia entre la terminación TLS y el paso directo?

- A. La terminación reenvía sin cambios los bytes cifrados
- B. La terminación finaliza TLS descendente en el gateway; con el paso directo, TLS termina en el backend
- C. Ambos requieren un listener HTTPS con modos intercambiables
- D. La terminación siempre obliga a que el tráfico hacia el backend vaya en texto sin cifrar

<details>
<summary>Mostrar respuesta</summary>

B. La terminación HTTPS y el paso directo de TLS usan configuraciones distintas de listener. El cifrado del backend después de la terminación es una decisión independiente y requiere una BackendTLSPolicy compatible o una configuración de la implementación.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-tls
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
  - name: tls-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
```

Deben existir el Secret TLS referenciado y las Routes/backends apropiados. No se puede habilitar el paso directo en un listener HTTPS con solo cambiar el modo.

</details>

## 4. ¿Cómo expresa HTTPRoute una división ponderada entre backends?

- A. Con un campo trafficSplit
- B. Con weight en varios backendRefs
- C. Con una anotación canary obligatoria
- D. Con un CRD TrafficSplit de otra API

<details>
<summary>Mostrar respuesta</summary>

B. Con la configuración de Gateway/Namespace de la guía y los Services de backend existentes:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-split
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

Los pesos expresan una distribución relativa y no tienen que sumar 100. Una muestra pequeña no tiene que coincidir exactamente con la proporción. Los pesos seleccionan backends detrás de este Gateway; no trasladan clientes de un frontend Ingress antiguo a uno Gateway nuevo.

</details>

## 5. ¿En qué espacio de nombres se crea un ReferenceGrant para un backend entre espacios de nombres?

- A. Siempre en el espacio de nombres de la Route
- B. En el espacio de nombres del backend referenciado y a cargo de su propietario
- C. Solo en kube-system
- D. En la estación de trabajo del cliente

<details>
<summary>Mostrar respuesta</summary>

B. El destinatario autoriza la referencia. Por ejemplo:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-shared-api
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /shared
    backendRefs:
    - name: shared-api
      namespace: backend-services
      port: 80
```

El Service shared-api debe existir en backend-services. `to.name` limita la autorización a ese Service. Para asociar una Route a un Gateway se usan `parentRefs` y `allowedRoutes`; esa asociación no necesita un ReferenceGrant. Un grant no autentica a los usuarios de la aplicación.

</details>

## 6. ¿Qué recurso no forma parte del paquete Standard de Gateway API v1.6?

- A. GatewayClass
- B. GRPCRoute
- C. TCPRoute
- D. Istio VirtualService

<details>
<summary>Mostrar respuesta</summary>

D. VirtualService es una API de Istio. El paquete Standard de v1.6 incluye, entre otros recursos, HTTPRoute, GRPCRoute, TCPRoute, TLSRoute y UDPRoute. La respuesta antigua que afirmaba que TCPRoute era Experimental ya no es correcta. El canal y la versión de la API son distintos: ReferenceGrant v1beta1 sigue disponible en Standard junto con v1, mientras que el paquete Experimental puede incluir campos experimentales en recursos v1.

</details>

## 7. ¿Qué filtro reescribe la solicitud al backend sin devolver una redirección al cliente?

- A. RequestHeaderModifier
- B. ResponseHeaderModifier
- C. URLRewrite
- D. RequestMirror

<details>
<summary>Mostrar respuesta</summary>

C. URLRewrite cambia la ruta/Host enviados al backend; `backendRefs` sigue seleccionando el destino. RequestRedirect devuelve al cliente una respuesta 3xx.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-rewrite
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /old-api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /new-api
        hostname: new-api.example.com
    backendRefs:
    - name: new-api-service
      port: 80
```

En este caso, /old-api/users se convierte en /new-api/users. ReplaceFullPath reemplaza, en cambio, toda la ruta. Estos comportamientos son distintos al traducir reescrituras heredadas.

</details>

## 8. ¿Qué componente NO reconcilia recursos de Gateway API?

- A. El controlador Gateway de Istio
- B. El controlador Gateway de Cilium
- C. kube-proxy
- D. Envoy Gateway

<details>
<summary>Mostrar respuesta</summary>

C. kube-proxy gestiona el reenvío de Services y puede participar en una ruta de red del backend, pero no reconcilia recursos GatewayClass/Gateway/Route. Instalar solo los CRD de Gateway API no instala ninguno de los controladores enumerados.

</details>

## 9. ¿Qué construcción de Gateway API expresa una reescritura de ruta HTTP de una configuración Ingress heredada?

- A. El nombre del objeto Gateway
- B. El filtro URLRewrite de HTTPRoute
- C. Un ReferenceGrant de cualquier espacio de nombres
- D. Solo las etiquetas del espacio de nombres

<details>
<summary>Mostrar respuesta</summary>

B. Verifica la semántica de reescritura anterior antes de elegir ReplaceFullPath o ReplacePrefixMatch. El valor constante `rewrite-target: /` de la guía requiere reemplazar toda la ruta, no conservar un sufijo. Otras anotaciones Ingress pueden corresponder a ajustes de Gateway o CRD de políticas del controlador; algunas no tienen un equivalente compatible. Las redirecciones HTTP a HTTPS deben asociarse al listener HTTP.

</details>

## 10. ¿Cómo puede un Gateway restringir los espacios de nombres que asocian Routes?

- A. `from: All` limita la asociación a un espacio de nombres
- B. `from: Same` permite su propio espacio de nombres
- C. `from: Selector` selecciona etiquetas de Namespace
- D. B y C son válidas, pero tienen alcances distintos

<details>
<summary>Mostrar respuesta</summary>

D. Elige un solo valor para `from`. Para usar un selector:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-namespace-selector
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

La etiqueta pertenece a Namespace, no a Route ni a Pod. Controla quién puede cambiar las etiquetas de Namespace. `allowedRoutes` limita las asociaciones; no concede acceso a backends de otros espacios de nombres ni autoriza solicitudes de la aplicación.

</details>

## 11. ¿Qué coincidencia de GRPCRoute selecciona un método concreto de un servicio?

- A. path.service y path.method
- B. method.service y method.method
- C. grpc.service y grpc.method
- D. rpc.service y rpc.method

<details>
<summary>Mostrar respuesta</summary>

B. Para el listener gRPC de la guía:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: quiz-grpc
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: grpc
  hostnames:
  - grpc.example.com
  rules:
  - matches:
    - method:
        service: myapp.UserService
        method: GetUser
    backendRefs:
    - name: user-service
      port: 50051
```

Con la coincidencia Exact predeterminada, el nombre del método distingue mayúsculas de minúsculas. El backend debe ofrecer el transporte gRPC esperado y tener la configuración TLS adecuada; el número de puerto por sí solo no lo demuestra. Una coincidencia solo por servicio abarca los métodos de ese servicio.

</details>

## 12. ¿Qué comparación con Ingress es incorrecta?

- A. Gateway API separa de forma más explícita la propiedad de listeners y Routes
- B. Gateway API define tipos específicos de enrutamiento TCP/UDP/gRPC
- C. Los campos de enrutamiento estándar tienen requisitos de compatibilidad de implementación
- D. Gateway API tiene menos tipos de recursos que Ingress

<details>
<summary>Mostrar respuesta</summary>

D. Gateway API introduce varios tipos de recursos. Ingress también tiene IngressClass y puede usar RBAC/admission; es incorrecto afirmar que carece de controles de autorización o propiedad. Gateway API hace más explícitos varios acuerdos de responsabilidad y de comunicación entre espacios de nombres. Comprueba la compatibilidad del controlador y de la versión, en lugar de suponer que todos los campos de la API se comportan igual en todas partes.

</details>

[Volver a la guía](../../networking/04-gateway-api.md)
