# Cuestionario de Ingress y Gateway de Cilium Service Mesh

Base de revisión: Cilium 1.20.3, Gateway API 1.6.3 y AWS LBC 3.6.0. Consulta la [guía](../../../service-mesh/cilium-service-mesh/05-ingress-gateway.md) y sus fuentes principales.

## Preguntas del cuestionario

### 1. ¿Qué comparte Cilium Ingress con `loadbalancerMode: shared`?

- A. Un frontend entre todos los controladores del clúster
- B. El servicio Cilium Ingress compartido para los recursos que usan ese modo
- C. Solo un NodePort interno
- D. Todos los Gateway API Gateway de forma automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. El servicio Cilium Ingress compartido para los recursos que usan ese modo**

El ajuste se aplica a los recursos Ingress administrados por Cilium que usan el modo compartido. Las anulaciones del modo dedicado y otros controladores son independientes. Una GatewayClass compartida tampoco implica que se comparta un balanceador de carga en la nube.

</details>

### 2. ¿Cómo se asocia explícitamente una HTTPRoute solo al listener HTTPS de un Gateway?

- A. Se indica un Pod principal
- B. Se usa `parentRefs` con el nombre del Gateway y `sectionName: https`
- C. Se establece solo el espacio de nombres de la Route
- D. Se usa una anotación de listener arbitraria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Se usa `parentRefs` con el nombre del Gateway y `sectionName: https`**

El nombre de la sección debe coincidir con el listener; `allowedRoutes` debe permitir la asociación, y el nombre de host y el protocolo deben ser compatibles. Inspecciona la entrada correcta del estado del padre para comprobar `Accepted` y `ResolvedRefs`; una referencia al padre por sí sola no demuestra que haya conectividad.

</details>

### 3. ¿Qué anotación de Cilium Ingress habilita el paso directo de TLS?

- A. `ingress.cilium.io/tls-mode: passthrough`
- B. `ingress.cilium.io/tls-passthrough: "true"`
- C. `cilium.io/tls: passthrough`
- D. Una anotación específica de nginx

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `ingress.cilium.io/tls-passthrough: "true"`**

El backend termina TLS. Ingress requiere un host y la ruta `/`; Cilium usa SNI en lugar de inspeccionar rutas HTTP. El backend ve la conexión de Envoy/nodo, no la dirección del socket del cliente original.

</details>

### 4. ¿Dónde se configuran el protocolo y el puerto de un Gateway?

- A. `protocols`
- B. `listeners`
- C. `endpoints`
- D. `handlers`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `listeners`**

Cada listener define su protocolo y puerto, además de los ajustes aplicables de nombre de host, TLS y asociación. Las combinaciones de protocolos disponibles dependen del controlador. Por ejemplo, LBC 3.6 no admite combinar sus listeners L4/NLB y L7/ALB en un mismo Gateway.

</details>

### 5. ¿Qué configuración selecciona AWS LBC para el frontend NLB de Cilium Ingress compartido de la guía?

- A. Solo la anotación antigua `aws-load-balancer-type: nlb`
- B. `Service spec.loadBalancerClass: service.k8s.aws/nlb`, destinos de tipo instancia y NodePorts asignados
- C. Destinos IP sin comprobar EndpointSlices
- D. Una etiqueta arbitraria del espacio de nombres de EKS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `Service spec.loadBalancerClass: service.k8s.aws/nlb`, destinos de tipo instancia y NodePorts asignados**

El equivalente en Helm es `ingressController.service.loadBalancerClass`. El EndpointSlice de Cilium Ingress L7 compartido es sintético y no tiene referencias a Pods de destino; el solucionador IP de LBC lo omite. Aun así, hay que validar los requisitos previos de las instancias de EC2 y de NodePort.

</details>

### 6. ¿Qué filtro de HTTPRoute reescribe el nombre de host o la ruta enviados al backend sin redirigir al cliente?

- A. `PathRewrite`
- B. `URLRewrite`
- C. `RequestTransform`
- D. `RequestRedirect`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `URLRewrite`**

URLRewrite modifica la solicitud que se reenvía al backend. RequestRedirect envía una redirección al cliente. Los valores de encabezado de la guía son cadenas literales; no generan automáticamente un UUID ni una latencia.

</details>

### 7. ¿Qué ajuste de listener restringe la asociación de Routes entre espacios de nombres a los espacios que tengan una etiqueta aprobada?

- A. `allowedRoutes.namespaces.from: All`
- B. `allowedRoutes.namespaces.from: Selector` con un selector coincidente
- C. `crossNamespace: true`
- D. `routes.scope: cluster`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `allowedRoutes.namespaces.from: Selector` con un selector coincidente**

`All` también permite asociaciones entre espacios de nombres, pero no las restringe por etiqueta. `Same` las limita al espacio de nombres del Gateway. La referencia de backend a un Service de otro espacio de nombres requiere, además, un ReferenceGrant en el espacio de nombres de backend; es una comprobación independiente.

</details>

### 8. ¿Dónde se configuran las comprobaciones de estado activas de Envoy?

- A. En el nombre del listener
- B. En `health_checks` del Cluster
- C. En el nombre de la Route
- D. En el espacio de nombres del endpoint

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. En `health_checks` del Cluster**

Un CEC funcional todavía necesita una cadena Service→Listener→route→Cluster. El host y la ruta de comprobación HTTP deben funcionar con el backend real. El intervalo de estados esperado excluye su límite superior, así que el rango inicial 200/final 300 abarca todos los códigos 2xx.

</details>

### 9. ¿Qué redirección permanente conserva el método y el cuerpo de la solicitud, y a qué listener debe asociarse la Route HTTP→HTTPS?

- A. 302 en los listeners HTTP y HTTPS
- B. 307 en los listeners HTTP y HTTPS
- C. 308 solo en el listener HTTP
- D. 303 solo en el listener HTTPS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. 308 solo en el listener HTTP**

308 es permanente y conserva el método y el cuerpo; 307 es su equivalente temporal. Asociar la redirección de esquema solo a HTTP evita un bucle de redirección de HTTPS a sí mismo. Las redirecciones no protegen los datos que ya se enviaron en la solicitud inicial sin cifrar.

</details>

### 10. ¿Qué comparación de costos y capacidades es correcta?

- A. Cilium nunca necesita un balanceador de carga en la nube
- B. AWS LBC siempre es más rápido
- C. Los costos de nodos/proxy de Cilium pueden sumarse a los cargos del balanceador de carga en la nube; compara las funciones según la versión
- D. Todos los controladores admiten todas las funciones de Gateway API

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Los costos de nodos/proxy de Cilium pueden sumarse a los cargos del balanceador de carga en la nube; compara las funciones según la versión**

Cilium puede ejecutarse detrás de ALB/NLB, que siguen generando cargos. LBC 3.6 asigna las Routes HTTP/GRPC a ALB y las Routes TCP/UDP/TLS a NLB. El mTLS de cargas de trabajo y los certificados de servidor ACM son mecanismos distintos; el rendimiento se debe comparar mediante mediciones equivalentes.

</details>

### 11. ¿Qué hace TCPRoute en la base de Gateway API 1.6.3 de la guía?

- A. Inspecciona rutas HTTP
- B. Termina TLS de forma predeterminada
- C. Reenvía un flujo TCP opaco mediante la API v1 servida
- D. Solo gestiona UDP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Reenvía un flujo TCP opaco mediante la API v1 servida**

TCP puede transportar HTTP o TLS, pero TCPRoute no adquiere por ello su semántica L7. La API TCPRoute v1alpha2 antigua no se sirve en esta base. TLSRoute v1 requiere, en cambio, un listener compatible con el paso directo de TLS para enrutar por SNI.

</details>

### 12. Si se habilita NLB PPv2 para esta topología de Cilium Ingress, ¿qué debe coordinarse?

- A. Solo un encabezado X-Forwarded-For del cliente
- B. Tanto el emisor NLB como el receptor `enableProxyProtocol` de Cilium, las comprobaciones de estado y la ruta de acceso de confianza
- C. No hace falta cambiar el receptor
- D. PPv2 es obligatorio para todos los NLB

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Tanto el emisor NLB como el receptor `enableProxyProtocol` de Cilium, las comprobaciones de estado y la ruta de acceso de confianza**

El analizador requiere un encabezado PROXY, así que habilitarlo en un solo lado interrumpe el tráfico. PPv2 es opcional; la conservación de la IP del cliente también depende del tipo y los atributos del destino. AWS LBC desaconseja PPv2 con destinos de tipo instancia y `externalTrafficPolicy Local`. Los metadatos PROXY no son una identidad autenticada.

</details>
