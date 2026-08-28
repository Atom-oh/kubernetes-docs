# Cuestionario de comparación de Istio

> **Versiones compatibles**: Istio 1.30 / EKS 1.36
> **Última actualización**: August 21, 2026

Este cuestionario evalúa tu comprensión de los criterios para seleccionar entre sidecar y modo ambient, especialmente los resultados de las pruebas de EKS 1.36.

## Preguntas de opción múltiple (1-6)

### Pregunta 1: Causa raíz de los 503 del waypoint en ambient

¿Cuál es la causa raíz de los 503 intermitentes en la ruta del waypoint durante los rollouts en modo ambient?

A. Asignación de IP duplicada cuando un Pod se reinicia
B. El waypoint reutiliza conexiones indexadas por IP:Port de destino, y ztunnel no notifica al waypoint cuando un Pod termina
C. NetworkPolicy bloquea el tráfico del waypoint
D. El mTLS STRICT no es compatible con el waypoint

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

El waypoint (Envoy) administra y reutiliza un pool de conexiones indexado por IP:Port de destino. ztunnel no notifica explícitamente al waypoint cuando un Pod de destino termina. Si la IP del Pod terminado se reasigna a un Pod nuevo, el waypoint puede reutilizar una conexión que ya no es válida y devolver un 503. Este es el mecanismo detrás del problema — **gestión del ciclo de vida de las conexiones**, no asignación de IP duplicada — y las tasas de 503 medidas en §4 son coherentes con ello.

**Referencias:**
- [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode: Waypoint Proxy](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### Pregunta 2: Interpretación de los resultados de las pruebas de EKS 1.36

Con una carga de 100 qps x 600s (60,000 solicitudes) y rollouts repetidos en un clúster EKS 1.36 dedicado de un solo inquilino, sidecar mostró una tasa de 503 del 0.5%, ambient-L4 (sin waypoint) no mostró 503 reales (pero sí un 0.3% de errores TCP), y ambient-L7 (con waypoint) mostró un 2.6%. ¿Cuál es la interpretación correcta?

A. Ambient siempre es más estable que sidecar
B. El enrutamiento a través de un waypoint produce una tasa de 503 más alta que sidecar, pero usar solo L4 (sin waypoint) no produce 503 reales
C. Los errores TCP de ambient-L4 (0.3%) son el mismo fenómeno que los 503 del waypoint
D. El modo con el menor uso de sockets es el más estable

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

Los datos muestran que "ambient" no es universalmente mejor ni peor que sidecar — que el tráfico pase por un **waypoint** es la variable decisiva. Ambient-L7 (con un waypoint) tuvo aproximadamente 5 veces la tasa de 503 de sidecar (2.6% frente a 0.5%), mientras que ambient-L4 (sin waypoint) no tuvo 503 reales. Sin embargo, eso no significa que ambient-L4 esté libre de fallos — presentó en cambio un modo de fallo diferente: pérdidas de conexión a nivel TCP (0.3%), lo cual no es lo mismo que el waypoint reenvíe una solicitud a través de una conexión inactiva y devuelva un 503 (por lo que C es incorrecta). El uso de sockets no es una métrica de estabilidad, sino solo un indicador de la frecuencia con la que se restablecieron las conexiones (por lo que D es incorrecta) — de hecho, ambient-L4 consumió la *mayor* cantidad de sockets y aun así tuvo cero 503.

**Referencias:**
- [Sidecar vs Ambient Mode Selection Guide: Zero-Downtime Rollout Results](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Pregunta 3: NetworkPolicy y ambient

En un clúster que usa NetworkPolicies basadas en puertos, el tráfico no llega a los Pods en modo ambient. La aplicación escucha en el puerto 8080. ¿Cuál es la causa y corrección más probables?

A. Ambient no es compatible con NetworkPolicy, por lo que se debe eliminar la NetworkPolicy
B. El tráfico real llega a través del túnel HBONE (TCP 15008), por lo que la NetworkPolicy necesita una regla de permiso de entrada para 15008
C. PeerAuthentication se debe cambiar a PERMISSIVE
D. Se debe reiniciar el DaemonSet istio-cni

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

En modo ambient, ztunnel encapsula el tráfico del Pod en un túnel HBONE (mTLS) y lo entrega en el puerto 15008. Una NetworkPolicy que solo permite el puerto de la aplicación (8080) bloquea el tráfico 15008 que realmente llega. La corrección es agregar una regla de permiso de entrada para TCP 15008 en los Pods de destino. Sidecar no necesita esta regla adicional porque el sidecar comparte el mismo espacio de nombres de red del Pod que la aplicación.

**Referencias:**
- [Sidecar vs Ambient Mode Selection Guide: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Pregunta 4: API no idempotentes y políticas de reintento

¿Por qué se recomienda no habilitar de forma predeterminada los reintentos a nivel de mesh (por ejemplo, reintento del waypoint, reintentos de VirtualService) en rutas de API no idempotentes como la creación de pedidos?

A. Los reintentos añaden demasiada sobrecarga de CPU
B. Cuando un waypoint reenvía una solicitud a través de una conexión inactiva y devuelve un 503, un reintento puede volver a ejecutar una solicitud que ya se había completado en el servidor, lo que provoca una ejecución duplicada (por ejemplo, un pedido duplicado)
C. El reintento es incompatible con mTLS STRICT
D. El reintento no es compatible con el modo ambient

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

Un 503 es un fallo visible para el cliente, pero dentro de esa categoría de fallo hay casos en los que la solicitud realmente llegó al servidor y terminó de procesarse — solo se perdió la *respuesta*, debido a una condición de carrera entre la caída de la conexión y la finalización del trabajo por parte de la aplicación. En ese caso, un reintento del mesh reenvía la misma solicitud lógica a través de una conexión diferente y, si el servidor no garantiza la idempotencia, la solicitud se procesa dos veces. Este riesgo es especialmente grave para operaciones irreversibles como la creación de pedidos, por lo que es más seguro no habilitar los reintentos de forma predeterminada y verificarlos por separado. Una prueba de seguimiento (T2) ejecutó 300s de cambios continuos de rollout contra reintentos de sidecar y waypoint de ambient-L7 y no encontró ejecuciones duplicadas en esa ejecución — lo que reduce la confianza en que la condición de carrera sea *común*, pero no establece que sea *segura*, ya que requiere una ventana de tiempo muy estrecha que una prueba más larga o de mayor rendimiento aún podría detectar.

**Referencias:**
- [Sidecar vs Ambient Mode Selection Guide: The Risk of Retry as a Mitigation](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Pregunta 5: Comparación justa de rollouts de sidecar y ambient

Sidecar produjo menos 503 visibles para el cliente que ambient en una prueba de rollout. ¿Qué experimento determina mejor si eso refleja un plano de datos inherentemente más estable?

A. Enviar solo solicitudes GET y comparar los conteos finales de 200
B. Mantener el reintento predeterminado en sidecar pero deshabilitar el reintento en ambient
C. Establecer el reintento de la ruta de escritura en `attempts: 0` en ambos modos y registrar por separado los fallos HTTP/TCP sin procesar, los conteos de reintentos y los resultados finales
D. Considerar más estable el modo con menor uso promedio de CPU

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

**Explicación:**

Envoy de sidecar y Envoy de waypoint pueden ocultar un fallo sin procesar al cliente mediante un reintento L7, mientras que ztunnel es un proxy L4 que no puede interpretar un HTTP 503 ni reproducir una solicitud HTTP. Deshabilita los reintentos de escritura de manera equivalente y registra por separado HTTP 503, restablecimiento/EOF de TCP, `upstream_rq_retry`, entregas reales al upstream y resultados finales del cliente. De lo contrario, la prueba no puede distinguir entre "ocurrieron menos fallos" y "el reintento ocultó más fallos".

**Referencias:**
- [Sidecar vs Ambient Mode Selection Guide: raw failure measurement](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Retry and Timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### Pregunta 6: Autenticación y cifrado de Cilium

¿Qué afirmación es correcta para un plano de datos Cilium establecido con la autenticación mutua configurada como `required`?

A. Cada carga útil de la aplicación se cifra automáticamente con TLS de workload
B. La autenticación de identidad de endpoint y el cifrado de la carga útil son independientes; la confidencialidad requiere WireGuard/IPsec o mTLS nativo de ztunnel compatible
C. Es idéntica a `PeerAuthentication STRICT` de Istio en implementación, madurez y semántica operativa
D. Habilitar la autenticación mutua elimina la necesidad de CiliumNetworkPolicy

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

La autenticación mutua establecida de Cilium verifica la identidad del par mediante un handshake fuera de banda separado de la ruta de datos de la aplicación. La política de autenticación por sí sola no cifra automáticamente las cargas útiles, por lo que debes seleccionar WireGuard/IPsec por separado o validar la vista previa de mTLS nativo de ztunnel en una plataforma compatible. Evalúa por separado la autorización de identidad, la autenticación de pares y el cifrado en tránsito en vez de tratar el resultado como idéntico al mTLS de workload `STRICT` de Istio.

**Referencias:**
- [Cilium Service Mesh Security](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## Puntuación

- Cuenta cuántas de las 6 preguntas respondiste correctamente.
- 6/6: Puedes explicar la selección entre sidecar, ambient y Cilium, además del riesgo de reintento, usando evidencia medida.
- 4-5/6: Revisa la medición de fallos sin procesar o la distinción entre autenticación y cifrado.
- 0-3/6: Vuelve a leer desde el principio la [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md).

## Recursos de aprendizaje

- [Sidecar vs Ambient Mode Selection Guide](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient Mode](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Cilium Service Mesh Security](../../../service-mesh/cilium-service-mesh/03-security.md)
