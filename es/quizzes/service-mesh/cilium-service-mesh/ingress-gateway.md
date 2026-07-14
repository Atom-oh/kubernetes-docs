# Cuestionario de Cilium Service Mesh Ingress & Gateway

Este cuestionario evalúa tu comprensión de Cilium Ingress Controller, Gateway API, terminación de TLS y patrones de integración con EKS.

## Preguntas del cuestionario

### 1. ¿Qué significa el modo 'shared' en la opción loadbalancerMode de Cilium Ingress Controller?

A. Crea un load balancer independiente para cada Ingress
B. Todos los Ingress comparten un load balancer
C. Usa solo NodePort sin load balancer
D. Gestiona únicamente tráfico interno

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Todos los Ingress comparten un load balancer**

**Explicación:**
La configuración loadbalancerMode: shared hace que todos los recursos Ingress usen un único load balancer compartido. Esto es rentable, mientras que el modo dedicated crea un load balancer independiente para cada Ingress.

</details>

### 2. ¿Cuál es el rol del campo parentRefs en el HTTPRoute de Gateway API?

A. Define el Pod padre
B. Especifica a qué Gateway se conecta esta ruta
C. Hace referencia al namespace padre
D. Define las políticas que se heredarán

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especifica a qué Gateway se conecta esta ruta**

**Explicación:**
parentRefs especifica a qué Gateway se conecta el HTTPRoute. Al hacer referencia al nombre y al namespace del Gateway, determina a qué listener se aplica la ruta.

</details>

### 3. ¿Qué annotation habilita el passthrough de TLS en Cilium Ingress?

A. ingress.cilium.io/tls-mode: passthrough
B. ingress.cilium.io/tls-passthrough: "true"
C. cilium.io/tls: passthrough
D. nginx.ingress.kubernetes.io/ssl-passthrough

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. ingress.cilium.io/tls-passthrough: "true"**

**Explicación:**
La annotation `ingress.cilium.io/tls-passthrough: "true"` reenvía el tráfico TLS directamente al Service de backend sin terminarlo. Esto es útil cuando el backend necesita gestionar TLS.

</details>

### 4. ¿Qué campo se usa en el recurso Gateway de Gateway API para admitir varios protocolos?

A. protocols
B. listeners
C. endpoints
D. handlers

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. listeners**

**Explicación:**
Se pueden definir varios listeners en el campo listeners del Gateway para admitir diversos protocolos como HTTP, HTTPS, TCP y TLS. Cada listener puede configurar individualmente el protocolo, el puerto, el hostname, etc.

</details>

### 5. ¿Qué annotation se requiere para usar NLB con Cilium Ingress en EKS?

A. service.kubernetes.io/load-balancer-type: nlb
B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
C. eks.amazonaws.com/load-balancer: nlb
D. aws.load-balancer/type: network

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"**

**Explicación:**
Para usar Network Load Balancer en AWS EKS, agrega la annotation `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` al Service. Annotations adicionales como scheme y target-type pueden configurar aún más el comportamiento de NLB.

</details>

### 6. ¿Qué tipo de filter se usa para configurar la reescritura de URL en el HTTPRoute de Gateway API?

A. PathRewrite
B. URLRewrite
C. RequestTransform
D. PathModifier

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. URLRewrite**

**Explicación:**
En la sección filters del HTTPRoute, type: URLRewrite se usa para reescribir las URL de las solicitudes. Se pueden modificar tanto la ruta como el hostname.

</details>

### 7. ¿Qué configuración de Gateway se necesita para permitir el enrutamiento entre namespaces en Cilium Gateway API?

A. allowedRoutes.namespaces.from: All
B. allowedRoutes.namespaces.from: Selector
C. crossNamespace: true
D. routes.scope: cluster

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. allowedRoutes.namespaces.from: Selector**

**Explicación:**
En los listeners del Gateway, configurar allowedRoutes.namespaces.from: Selector permite rutas únicamente desde namespaces con etiquetas específicas mediante un selector. 'All' permite todos los namespaces y 'Same' permite únicamente el mismo namespace.

</details>

### 8. ¿Qué tipo de recurso Envoy se usa para configurar health checks de Service en CiliumEnvoyConfig?

A. envoy.config.listener.v3.Listener
B. envoy.config.cluster.v3.Cluster
C. envoy.config.route.v3.Route
D. envoy.config.endpoint.v3.Endpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. envoy.config.cluster.v3.Cluster**

**Explicación:**
La configuración de health checks se define en el campo health_checks del recurso Cluster. Se pueden configurar health checks de HTTP, health checks de TCP, intervalos, umbrales, etc.

</details>

### 9. ¿Cuál es el statusCode recomendado al redirigir de HTTP a HTTPS en Gateway API?

A. 302 (Found)
B. 307 (Temporary Redirect)
C. 301 (Moved Permanently)
D. 303 (See Other)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 301 (Moved Permanently)**

**Explicación:**
Para una redirección permanente de HTTP a HTTPS, se recomienda el código de estado 301. Esto informa a los navegadores y motores de búsqueda de que la URL ha cambiado permanentemente, lo que es beneficioso para el caché y el SEO.

</details>

### 10. ¿Cuál es la principal diferencia entre Cilium y AWS Load Balancer Controller?

A. Cilium solo admite L4
B. AWS LBC proporciona menor latencia
C. Cilium usa únicamente recursos del nodo sin costos adicionales de LB
D. AWS LBC admite completamente Gateway API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Cilium usa únicamente recursos del nodo sin costos adicionales de LB**

**Explicación:**
Cilium Ingress/Gateway gestiona el tráfico externo mediante eBPF y Envoy del nodo, por lo que no hay costos independientes de AWS load balancer. En cambio, AWS LBC aprovisiona ALB/NLB, lo que genera costos adicionales.

</details>

### 11. ¿Para qué se usa TCPRoute en Gateway API?

A. Enrutamiento de tráfico HTTP
B. Tráfico que requiere terminación de TLS
C. Enrutamiento de tráfico TCP sin procesar (no HTTP)
D. Solo tráfico UDP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Enrutamiento de tráfico TCP sin procesar (no HTTP)**

**Explicación:**
TCPRoute se usa para enrutar tráfico TCP sin procesar que no es HTTP, como conexiones a bases de datos y colas de mensajes. Funciona con el listener TCP del Gateway para proporcionar acceso externo a Services no HTTP.

</details>

### 12. ¿Qué configuración de NLB se usa para conservar la IP del cliente en Cilium Ingress?

A. Header X-Forwarded-For
B. Proxy Protocol
C. Deshabilitar Source NAT
D. Direct Server Return

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Proxy Protocol**

**Explicación:**
Para conservar la IP del cliente con NLB, se debe habilitar Proxy Protocol. Usa la annotation `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"`. Envoy extrae la IP original del cliente del header Proxy Protocol.

</details>
