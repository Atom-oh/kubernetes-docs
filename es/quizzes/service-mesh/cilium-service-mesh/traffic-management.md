# Cuestionario de gestión de tráfico de Cilium Service Mesh

Revisado con Cilium 1.20.3 y Gateway API 1.6.3. Consulta la [guía de tráfico](../../../service-mesh/cilium-service-mesh/02-traffic-management.md) para ver ejemplos completos y referencias primarias.

### 1. ¿Qué filtro de Envoy define reglas de enrutamiento HTTP en CiliumEnvoyConfig?

- **A.** `envoy.filters.network.tcp_proxy`
- **B.** `envoy.filters.network.http_connection_manager`
- **C.** `envoy.filters.http.fault`
- **D.** `envoy.filters.network.redis_proxy`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `envoy.filters.network.http_connection_manager`**

HTTP Connection Manager procesa tráfico HTTP y obtiene las rutas de `route_config` en línea o de RDS. También se necesitan el filtro HTTP router y los recursos Cluster referenciados; enumerar solo los Services backend no basta.

</details>

### 2. ¿Qué campo no se puede usar para definir reglas HTTP L7 en CiliumNetworkPolicy?

- **A.** `method`
- **B.** `path`
- **C.** `headers`
- **D.** `body`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D. `body`**

La política HTTP puede coincidir con el método, la ruta y los encabezados, incluidos los campos estructurados `headerMatches`. No autoriza campos arbitrarios del cuerpo de una solicitud. La autenticación y la autorización a nivel de aplicación se gestionan por separado.

</details>

### 3. ¿Cómo se controla el acceso por tema de Kafka con Cilium 1.20.3?

- **A.** Usando sin cambios `rules.kafka` de Cilium
- **B.** Inspeccionando mensajes Kafka con una regla HTTP sobre el cuerpo
- **C.** Usando ACL del broker Kafka y, por separado, una política L4 para controlar la conectividad
- **D.** Eliminando todas las reglas y suponiendo que se conservan los permisos por tema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Usando ACL del broker Kafka y, por separado, una política L4 para controlar la conectividad**

El esquema de reglas L7 de Cilium 1.20.3 admite HTTP y DNS, y rechaza el objeto heredado `rules.kafka`. Usa una política de red L4 para la conectividad al broker y Kafka TLS/SASL con ACL del broker para temas, grupos y operaciones. Eliminar reglas Kafka obsoletas no conserva la autorización por tema.

</details>

### 4. ¿Qué proporciona Maglev para el balanceo eBPF de Cilium en los casos admitidos?

- **A.** Distribución completamente aleatoria
- **B.** Selección consistente de backends con menos reasignaciones cuando cambian los miembros
- **C.** Garantía de que sobrevivan las conexiones a backends eliminados
- **D.** El menor consumo de memoria posible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Selección consistente de backends con menos reasignaciones cuando cambian los miembros**

Maglev minimiza la reasignación de flujos cuando cambia el conjunto de backends para el balanceo externo admitido. Es independiente de la afinidad de sesión ClientIP y no conserva conexiones a backends no disponibles. La ruta este-oeste a nivel de socket de Cilium no usa esta selección Maglev.

</details>

### 5. ¿Cuál es la forma correcta de configurar la división del tráfico por peso en HTTPRoute de Gateway API?

- **A.** Usar el campo `split`
- **B.** Especificar el campo `weight` en `backendRefs`
- **C.** Usar `trafficPolicy`
- **D.** Usar `destinationRule`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Especificar el campo `weight` en `backendRefs`**

Los pesos de `backendRefs` expresan probabilidades relativas de selección. Los valores 90 y 10 expresan una proporción de 90:10, no un recuento exacto en cada grupo de diez solicitudes ni una garantía de sesión por usuario. Los Services, puertos y listener principal deben ser válidos y aceptar la ruta.

</details>

### 6. ¿Cuál no es una condición válida para el campo `retry_on` al configurar reintentos en CiliumEnvoyConfig?

- **A.** `5xx`
- **B.** `reset`
- **C.** `timeout`
- **D.** `connect-failure`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. `timeout`**

`timeout` no es un valor de `retry_on`. `per_try_timeout` limita cada intento hacia el upstream, incluido el primero; no es un intervalo de espera entre reintentos. La guía habilita reintentos solo para operaciones GET seguras, desactiva explícitamente los de otros métodos y elimina las anulaciones de reintento o tiempo de espera de Envoy proporcionadas por el cliente antes del enrutamiento.

</details>

### 7. ¿Cuál es la función principal de las políticas DNS L7 de Cilium?

- **A.** Mejorar el rendimiento del servidor DNS
- **B.** Permitir solo consultas DNS para dominios específicos
- **C.** Invalidar la caché DNS
- **D.** Admitir DNS sobre HTTPS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Permitir solo consultas DNS para dominios específicos**

Las reglas DNS limitan los nombres consultados en el resolver de confianza seleccionado. Por sí solas no permiten conexiones a las direcciones devueltas ni garantizan impedir la exfiltración o DoH. Agrega políticas separadas de destino y puerto, y considera UDP/TCP y el comportamiento real del resolver y de su lista de búsqueda.

</details>

### 8. ¿Qué filtro configura la limitación de tasa local en CiliumEnvoyConfig?

- **A.** `envoy.filters.http.ratelimit`
- **B.** `envoy.filters.http.local_ratelimit`
- **C.** `envoy.filters.http.bandwidth_limit`
- **D.** `envoy.filters.http.throttle`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `envoy.filters.http.local_ratelimit`**

`envoy.filters.http.local_ratelimit` usa un bucket de tokens con fracciones `enabled` y `enforced` explícitas. Esas fracciones empiezan en 0 %, incluidas las anulaciones por ruta. Los ejemplos usan un bucket por proceso de Envoy, compartido por sus hilos de trabajo; no es una cuota para todo el clúster ni por usuario.

</details>

### 9. ¿Qué tipo de filtro configura una redirección de HTTP a HTTPS en Gateway API?

- **A.** `URLRewrite`
- **B.** `RequestMirror`
- **C.** `RequestRedirect`
- **D.** `ResponseHeaderModifier`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. `RequestRedirect`**

`RequestRedirect` puede devolver una redirección con `scheme: https`. Una respuesta 301 es permanente, pero algunos clientes pueden cambiar el método de la solicitud. Configura por separado la ruta del listener HTTP y prepara un listener HTTPS y su certificado operativos; evita redirigir silenciosamente operaciones de escritura con una semántica que cambie el método.

</details>

### 10. ¿Para qué sirve el espejado de tráfico en Cilium Service Mesh?

- **A.** Cifrar el tráfico
- **B.** Enviar una copia del tráfico de producción a un entorno de prueba
- **C.** Optimizar el balanceo de carga
- **D.** Invalidar la caché

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Enviar una copia del tráfico de producción a un entorno de prueba**

`request_mirror_policies` envía una copia a un backend de prueba en sombra e ignora su respuesta al determinar el resultado que recibe el cliente. Aun así, copia datos, consume recursos y puede causar efectos secundarios. La guía espeja solicitudes GET/HEAD aprobadas a un backend aislado y deja sin espejar los otros métodos; no garantiza que el usuario no note ningún impacto.

</details>

### 11. ¿Cómo determina Envoy actual el total de pesos para `weighted_clusters`?

- **A.** Limita la cantidad total de solicitudes
- **B.** Usa la suma de los pesos de Cluster; `total_weight` está obsoleto
- **C.** Trata los pesos como tiempos de espera
- **D.** Exige que cada solicitud use el Cluster de menor peso

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usa la suma de los pesos de Cluster; `total_weight` está obsoleto**

Envoy actual usa la suma de los pesos individuales de Cluster. `total_weight` está obsoleto y se omite en el ejemplo actualizado. Los pesos 90 y 10 expresan una proporción de selección de 90:10; no implementan promoción o reversión automática ni una cuota estricta de solicitudes por intervalo.

</details>

### 12. ¿Qué campo de la sección `matches` configura coincidencias por encabezado en HTTPRoute de Gateway API?

- **A.** `headerMatchers`
- **B.** `headers`
- **C.** `requestHeaders`
- **D.** `matchHeaders`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `headers`**

`HTTPRoute.matches.headers` expresa las condiciones de coincidencia de encabezados. En una misma coincidencia, varios encabezados se combinan con AND; las reglas de precedencia de ruta y encabezado de Gateway API determinan cuál se selecciona. Un encabezado de versión o canary enviado por el cliente no autentica al usuario.

</details>
