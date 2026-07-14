# Cuestionario sobre la gestión de tráfico de Cilium Service Mesh

Este cuestionario evalúa tu comprensión de la gestión de tráfico L7, CiliumEnvoyConfig, balanceo de carga, división de tráfico e integración de Gateway API en Cilium Service Mesh.

## Preguntas del cuestionario

### 1. ¿Qué filtro de Envoy se utiliza para definir reglas de enrutamiento HTTP en CiliumEnvoyConfig?

A. envoy.filters.network.tcp_proxy
B. envoy.filters.network.http_connection_manager
C. envoy.filters.http.fault
D. envoy.filters.network.redis_proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. envoy.filters.network.http_connection_manager**

**Explicación:**
El HTTP Connection Manager es el filtro principal de Envoy para procesar tráfico HTTP. Dentro de este filtro, puedes definir reglas de enrutamiento basadas en rutas, encabezados y métodos mediante route_config.

</details>

### 2. ¿Qué campo NO está disponible al definir reglas HTTP L7 en CiliumNetworkPolicy?

A. method
B. path
C. headers
D. body

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. body**

**Explicación:**
Las reglas HTTP L7 de CiliumNetworkPolicy permiten filtrar según method (método HTTP), path (ruta URL) y headers (encabezados HTTP). body (cuerpo de la solicitud) no es compatible con las reglas L7.

</details>

### 3. ¿Cuál NO es un apiKey válido al aplicar políticas Kafka L7 en Cilium?

A. produce
B. fetch
C. delete
D. metadata

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. delete**

**Explicación:**
Las políticas Kafka L7 de Cilium admiten apiKeys como produce (producción de mensajes), fetch (consumo de mensajes), metadata (consultas de metadatos), offsetcommit, offsetfetch, joingroup, etc. 'delete' no es una clave de API de Kafka compatible.

</details>

### 4. ¿Cuál es la ventaja del hash Maglev en el balanceo de carga L4 basado en eBPF de Cilium?

A. Distribución completamente aleatoria
B. Persistencia de sesión incluso cuando cambian los backends
C. Menor uso de memoria
D. Compatibilidad con enrutamiento L7

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Persistencia de sesión incluso cuando cambian los backends**

**Explicación:**
Maglev es un algoritmo de hash consistente que mantiene la mayoría de las conexiones existentes en el mismo backend incluso cuando se agregan o eliminan servidores backend. Esto es útil para aplicaciones con estado o cuando se requiere afinidad de sesión.

</details>

### 5. ¿Cuál es la forma correcta de configurar la división de tráfico basada en pesos en Gateway API HTTPRoute?

A. Usar el campo split
B. Especificar el campo weight en backendRefs
C. Usar trafficPolicy
D. Usar destinationRule

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar el campo weight en backendRefs**

**Explicación:**
En Gateway API HTTPRoute, la división de tráfico se configura especificando el campo weight para cada backend en el array backendRefs. Por ejemplo, usar `weight: 90` y `weight: 10` divide el tráfico en una proporción de 90:10.

</details>

### 6. ¿Cuál NO es una condición válida para el campo retry_on al configurar políticas de reintento en CiliumEnvoyConfig?

A. 5xx
B. reset
C. timeout
D. connect-failure

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. timeout**

**Explicación:**
Las condiciones retry_on de Envoy incluyen 5xx (errores del servidor), reset (restablecimiento de conexión), connect-failure (fallo de conexión), retriable-4xx, etc. 'timeout' no es una condición retry_on directa; per_try_timeout se utiliza para establecer el tiempo de espera de cada intento de reintento.

</details>

### 7. ¿Cuál es el principal beneficio de usar políticas DNS L7 en Cilium?

A. Mejor rendimiento del servidor DNS
B. Permitir únicamente consultas DNS para dominios específicos
C. Invalidación de la caché DNS
D. Compatibilidad con DNS sobre HTTPS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir únicamente consultas DNS para dominios específicos**

**Explicación:**
Las políticas DNS L7 permiten restringir qué dominios pueden consultar las cargas de trabajo. Mediante matchPattern o matchName, puedes garantizar que solo se consulten los dominios permitidos, evitando la exfiltración de datos o el acceso a dominios maliciosos.

</details>

### 8. ¿Qué filtro se utiliza para configurar Rate Limiting local en CiliumEnvoyConfig?

A. envoy.filters.http.ratelimit
B. envoy.filters.http.local_ratelimit
C. envoy.filters.http.bandwidth_limit
D. envoy.filters.http.throttle

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. envoy.filters.http.local_ratelimit**

**Explicación:**
Rate Limiting local utiliza el filtro envoy.filters.http.local_ratelimit. Este filtro limita las tasas de solicitudes mediante la configuración token_bucket. envoy.filters.http.ratelimit se utiliza para Rate Limiting global que se comunica con servicios externos de Rate Limit.

</details>

### 9. ¿Qué tipo de filtro se utiliza para configurar la redirección HTTP -> HTTPS en Gateway API?

A. URLRewrite
B. RequestMirror
C. RequestRedirect
D. ResponseHeaderModifier

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. RequestRedirect**

**Explicación:**
En Gateway API, el filtro RequestRedirect se utiliza para redirigir de HTTP a HTTPS. Establecer scheme: https y statusCode: 301 configura una redirección permanente.

</details>

### 10. ¿Cuál es el propósito del mirroring de tráfico (shadowing) en Cilium Service Mesh?

A. Cifrado de tráfico
B. Replicar tráfico de producción en el entorno de pruebas
C. Optimización del balanceo de carga
D. Invalidación de caché

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Replicar tráfico de producción en el entorno de pruebas**

**Explicación:**
El mirroring de tráfico envía una copia del tráfico de producción a otro Service (por ejemplo, a un entorno de pruebas con una nueva versión). Esto permite probar nuevas versiones con tráfico real sin afectar a los usuarios. Se configura mediante request_mirror_policies.

</details>

### 11. ¿Cuál es el rol de total_weight en una implementación canary que usa weighted_clusters en CiliumEnvoyConfig?

A. Limitar el número total de solicitudes
B. Definir el valor de referencia para la suma de pesos
C. Configuración de tiempo de espera
D. Límite de conexiones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Definir el valor de referencia para la suma de pesos**

**Explicación:**
total_weight define el valor de referencia para la suma de los pesos de los clústeres individuales. Por ejemplo, establecer total_weight: 100 y asignar 90 al clúster A y 10 al clúster B genera respectivamente un 90 % y un 10 % de tráfico.

</details>

### 12. ¿Qué campo se utiliza en la sección matches para configurar el enrutamiento basado en encabezados en Gateway API HTTPRoute?

A. headerMatchers
B. headers
C. requestHeaders
D. matchHeaders

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. headers**

**Explicación:**
En la sección matches de HTTPRoute, el campo headers se utiliza para configurar el enrutamiento basado en encabezados. Al especificar name y value para cada encabezado, puedes enrutar las solicitudes con valores de encabezado específicos a diferentes backends.

</details>
