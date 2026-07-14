# Cuestionario de comparación

> **Versiones compatibles**: Istio 1.30 / EKS 1.36 **Última actualización**: July 7, 2026

Este cuestionario evalúa tu comprensión de los criterios de selección entre sidecar y modo ambient, especialmente los resultados de las pruebas de EKS 1.36.

## Preguntas de opción múltiple (1-4)

### Pregunta 1: Causa raíz de los 503 del waypoint de ambient

¿Cuál es la causa raíz de los 503 intermitentes en la ruta del waypoint durante los rollouts en modo ambient?

A. Asignación de IP duplicada cuando se reinicia un Pod B. El waypoint reutiliza conexiones indexadas por IP:Port de destino, y ztunnel no notifica al waypoint cuando un Pod termina C. NetworkPolicy bloquea el tráfico del waypoint D. STRICT mTLS no es compatible con el waypoint

<details>

<summary>Respuesta &#x26; explicación</summary>

**Respuesta: B**

**Explicación:**

El waypoint (Envoy) administra y reutiliza un pool de conexiones indexado por IP:Port de destino. ztunnel no notifica explícitamente al waypoint cuando un Pod de destino termina. Si la IP del Pod terminado se reasigna a un Pod nuevo, el waypoint puede reutilizar una conexión que ya no es válida y devolver un 503. Este es el mecanismo detrás de la preocupación — **gestión del ciclo de vida de las conexiones**, no asignación de IP duplicada — y las tasas de 503 medidas en §4 son coherentes con ello.

**Referencias:**

* [Guía de selección entre modo sidecar y ambient](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
* [Modo ambient: Proxy waypoint](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

***

### Pregunta 2: Interpretación de los resultados de las pruebas de EKS 1.36

Con una carga de 100 qps x 600s (60,000 solicitudes) y rollouts repetidos en un clúster dedicado de EKS 1.36 de un solo inquilino, sidecar mostró una tasa de 503 del 0.5%, ambient-L4 (sin waypoint) no mostró 503 reales (pero sí 0.3% de errores TCP), y ambient-L7 (con waypoint) mostró 2.6%. ¿Cuál es la interpretación correcta?

A. Ambient siempre es más estable que sidecar B. El enrutamiento a través de un waypoint produce una tasa de 503 más alta que sidecar, pero usar solo L4 (sin waypoint) no produce 503 reales C. Los errores TCP de ambient-L4 (0.3%) son el mismo fenómeno que los 503 del waypoint D. El modo con el menor uso de sockets es el más estable

<details>

<summary>Respuesta &#x26; explicación</summary>

**Respuesta: B**

**Explicación:**

Los datos muestran que "ambient" no es ni universalmente mejor ni peor que sidecar — que el tráfico pase por un **waypoint** es la variable decisiva. Ambient-L7 (con un waypoint) tuvo aproximadamente 5 veces la tasa de 503 de sidecar (2.6% frente a 0.5%), mientras que ambient-L4 (sin waypoint) tuvo cero 503 reales. Sin embargo, eso no significa que ambient-L4 esté libre de fallos — en su lugar, mostró un modo de fallo diferente: caídas de conexión a nivel de TCP (0.3%), que no son lo mismo que el waypoint reenvíe una solicitud a través de una conexión inactiva y devuelva un 503 (lo que hace que C sea incorrecta). El uso de sockets no es una métrica de estabilidad, solo un indicador indirecto de la frecuencia con la que se restablecieron las conexiones (lo que hace que D sea incorrecta) — de hecho, ambient-L4 consumió la _mayor_ cantidad de sockets y aun así tuvo cero 503.

**Referencias:**

* [Guía de selección entre modo sidecar y ambient: Resultados de rollouts sin tiempo de inactividad](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

### Pregunta 3: NetworkPolicy y ambient

En un clúster que usa NetworkPolicies basadas en puertos, el tráfico no está llegando a los Pods en modo ambient. La aplicación escucha en el puerto 8080. ¿Cuál es la causa y solución más probable?

A. Ambient no es compatible con NetworkPolicy, por lo que se debe eliminar la NetworkPolicy B. El tráfico real llega a través del túnel HBONE (TCP 15008), por lo que la NetworkPolicy necesita una regla de permiso de entrada para 15008 C. PeerAuthentication se debe cambiar a PERMISSIVE D. Se debe reiniciar el DaemonSet istio-cni

<details>

<summary>Respuesta &#x26; explicación</summary>

**Respuesta: B**

**Explicación:**

En modo ambient, ztunnel encapsula el tráfico del Pod en un túnel HBONE (mTLS) y lo entrega en el puerto 15008. Una NetworkPolicy que solo permite el puerto de la aplicación (8080) bloquea el tráfico del puerto 15008 que realmente llega. La solución es añadir una regla de permiso de entrada para TCP 15008 en los Pods de destino. Sidecar no necesita esta regla adicional porque el sidecar comparte el mismo espacio de nombres de red del Pod que la aplicación.

**Referencias:**

* [Guía de selección entre modo sidecar y ambient: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

### Pregunta 4: API no idempotentes y políticas de reintento

¿Por qué se recomienda no habilitar de forma predeterminada los reintentos a nivel de mesh (por ejemplo, reintento de waypoint, reintentos de VirtualService) en rutas de API no idempotentes como la creación de pedidos?

A. El reintento agrega demasiada sobrecarga de CPU B. Cuando un waypoint reenvía una solicitud a través de una conexión inactiva y devuelve un 503, un reintento puede volver a ejecutar una solicitud que ya se había completado del lado del servidor, provocando una ejecución duplicada (por ejemplo, un pedido duplicado) C. El reintento es incompatible con STRICT mTLS D. El reintento no es compatible con el modo ambient

<details>

<summary>Respuesta &#x26; explicación</summary>

**Respuesta: B**

**Explicación:**

Un 503 es un fallo visible para el cliente, pero dentro de esa categoría de fallo se ocultan casos en los que la solicitud realmente llegó al servidor y terminó de procesarse — solo se perdió la _respuesta_, debido a una condición de carrera entre la caída de la conexión y que la aplicación completara su trabajo. En ese caso, un reintento del mesh reenvía la misma solicitud lógica por una conexión diferente y, si el servidor no garantiza la idempotencia, la solicitud se procesa dos veces. Este riesgo es especialmente grave para operaciones irreversibles como la creación de pedidos, por lo que es más seguro no habilitar los reintentos de forma predeterminada y verificarlos por separado. Una prueba de seguimiento (T2) ejecutó 300s de cambios continuos de rollouts contra reintentos de sidecar y del waypoint de ambient-L7, y encontró cero ejecuciones duplicadas en esa ejecución — lo que reduce la confianza en que la condición de carrera sea _común_, pero no establece que sea _segura_, ya que requiere una ventana de tiempo muy estrecha que una prueba más larga o de mayor rendimiento aún podría detectar.

**Referencias:**

* [Guía de selección entre modo sidecar y ambient: El riesgo del reintento como mitigación](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

***

## Puntuación

* Cuenta cuántas de las 4 preguntas respondiste correctamente.
* 4/4: Puedes explicar la decisión entre sidecar y ambient con evidencia de los resultados de las pruebas.
* 2-3/4: Comprendes los conceptos fundamentales, pero deberías revisar nuevamente las secciones de NetworkPolicy y riesgo de reintento.
* 0-1/4: Vuelve a leer la [Guía de selección entre modo sidecar y ambient](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md) desde el principio.

## Recursos de aprendizaje

* [Guía de selección entre modo sidecar y ambient](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
* [Modo ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
* [mTLS](../../../service-mesh/istio/security/01-mtls.md)
