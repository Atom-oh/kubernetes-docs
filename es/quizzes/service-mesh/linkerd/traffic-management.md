# Cuestionario de gestión de tráfico de Linkerd

Basado en la [guía de gestión de tráfico mantenida](../../../service-mesh/linkerd/03-traffic-management.md), revisada el 16 de octubre de 2026.

### 1. ¿Qué no se puede configurar por ruta en un ServiceProfile?

- A. Tiempo de espera
- B. Si se pueden reintentar las solicitudes
- C. Algoritmo del balanceador de carga
- D. Condición de ruta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Las rutas de ServiceProfile pueden especificar el tiempo de espera, `isRetryable` y condiciones de método o ruta. No permiten seleccionar un algoritmo de balanceo de carga. Esto no implica que exista una opción global universal para cambiar ese algoritmo.

</details>

### 2. ¿Qué describe el balanceo de carga HTTP de Linkerd?

- A. Round robin estricto
- B. Selección constante de la conexión con menos conexiones
- C. Comportamiento EWMA que tiene en cuenta la latencia
- D. Selección siempre aleatoria de un endpoint sin considerar la latencia

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** EWMA favorece candidatos adecuados con baja latencia, pero no garantiza que cada solicitud seleccione el endpoint cuyo valor mostrado sea el más bajo de forma global. El tráfico HTTP se balancea por solicitud; el TCP, por conexión.

</details>

### 3. ¿Qué especificación define el recurso heredado TrafficSplit?

- A. CNCF
- B. SMI (Service Mesh Interface)
- C. OpenAPI
- D. gRPC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** TrafficSplit es un recurso de SMI. TrafficSplit de Linkerd y linkerd-smi están obsoletos y requieren la extensión y sus CRD. Para configuraciones nuevas, la guía mantenida usa HTTPRoute de Gateway API. Aplicar solo un recurso heredado no instala esa extensión.

</details>

### 4. ¿Qué aporta `retryRatio: 0.2` de un ServiceProfile al presupuesto de reintentos?

- A. Exige reintentar exactamente el 20 % de cada flujo de solicitudes
- B. Permite reintentar solo el 20 % de las solicitudes fallidas
- C. Una asignación proporcional respecto de las solicitudes originales, además de `minRetriesPerSecond`
- D. Restablece el presupuesto cada 20 segundos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La contribución proporcional no impone un límite total estricto del 20 % cuando `minRetriesPerSecond` también agrega capacidad. `ttl` es la ventana de observación y retención, no un restablecimiento periódico. Los criterios de elegibilidad, el almacenamiento en búfer y los plazos aún limitan los reintentos reales.

</details>

### 5. ¿Cuál de estos datos, por sí solo, no permite inferir las operaciones de la aplicación necesarias para un ServiceProfile?

- A. Una especificación OpenAPI
- B. El tráfico observado en vivo con Tap
- C. Una definición de servicio protobuf
- D. El selector y la lista de puertos de un Service de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** La CLI permite generar perfiles a partir de OpenAPI o protobuf, y Viz admite generarlos mediante Tap. Usa un nombre corto de Service con `-n`; además, el comando Tap necesita el argumento posicional del Service. Revisa las coincidencias generadas y la seguridad de los reintentos, porque el tráfico muestreado no es un inventario completo de la API.

</details>

### 6. ¿Qué afirmación sobre los pesos de los backends es correcta?

- A. Deben sumar exactamente 100
- B. Deben sumar exactamente 1
- C. Los pesos relativos no negativos válidos necesitan una suma positiva utilizable; 90/10 y 9/1 expresan la misma proporción
- D. Los pesos negativos y una suma de cero siempre funcionan

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los pesos son relativos, sujetos al esquema de recursos seleccionado y a la validez de los backends. No tienen que sumar 100, y la proporción configurada no garantiza recuentos exactos de solicitudes en intervalos breves. Los ejemplos nuevos usan HTTPRoute; TrafficSplit es la ruta heredada de SMI.

</details>

### 7. ¿Cuál no es un campo de coincidencia de solicitudes de HTTPRoute?

- A. Encabezado HTTP
- B. Ruta HTTP
- C. Método HTTP
- D. IP de origen

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

**Explicación:** HTTPRoute admite coincidencias por encabezado, ruta y método. Una coincidencia exacta del encabezado Cookie compara el valor completo del encabezado, no sus pares de cookies individuales. Un encabezado de cohorte o depuración controlado por quien llama no es autorización. Usa una política de red o seguridad adecuada para restringir las direcciones de origen.

</details>

### 8. ¿Qué proveedor usan las plantillas MetricTemplate personalizadas de Flagger de la guía?

- A. Kubernetes Metrics Server
- B. Prometheus
- C. Un Service InfluxDB no declarado
- D. Un backend Datadog obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Estas plantillas consultan Prometheus de Linkerd Viz con el espacio de nombres, el Deployment y la dirección especificados. Flagger también admite otros proveedores. El ejemplo usa el enrutamiento `gatewayapi:v1` y nombres de métricas personalizados; en Flagger 1.45.0, `meshProvider:linkerd` sigue seleccionando el enrutador SMI heredado.

</details>

### 9. ¿Qué significa `isRetryable: false` para una ruta de ServiceProfile coincidente?

- A. Fallan todas las solicitudes coincidentes
- B. El mecanismo de ServiceProfile no reintenta esa ruta
- C. Se ignoran todas las políticas de tiempo de espera
- D. Se deshabilita la ruta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La solicitud aún se puede reenviar normalmente. Este ajuste no impide los reintentos del cliente, el SDK u otro proxy. En la ruta actual de anotaciones, `limit:0` no es una forma fiable de deshabilitarlos en edge-26.10.1; mantén los valores predeterminados de los Service sin reintentos y habilítalos solo para las rutas de lectura previstas.

</details>

### 10. ¿Cómo se configura el circuit breaking HTTP de Linkerd?

- A. Con un CRD CircuitBreaker que se instala automáticamente
- B. Con anotaciones opcionales de acumulación de fallos del Service
- C. Con una regla predeterminada e incondicional de cinco fallos de conexión
- D. Con un ciclo periódico de sondas sintéticas de disponibilidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La acumulación de fallos está deshabilitada de forma predeterminada y es incompatible con un ServiceProfile para el mismo Service. La política consecutiva tiene un valor predeterminado de siete fallos de respuesta admitidos. La prueba de recuperación envía una solicitud real de la aplicación después del periodo de espera; no es una sonda sintética periódica.

</details>

### 11. ¿Cómo puede un cliente llamar explícitamente a un servicio exportado representado por un Service réplica de multiclúster?

- A. Aplicando un CRD TrafficMirror ficticio
- B. Llamando al nombre DNS del Service réplica, con la conectividad y política necesarias
- C. Duplicando automáticamente todas las solicitudes locales
- D. Suponiendo que nunca se puede llamar a un Service réplica

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La réplica de servicios de multiclúster proporciona descubrimiento y enrutamiento a un servicio remoto. Llamar a su nombre DNS envía la solicitud a ese servicio; no duplica la solicitud automáticamente para hacer pruebas en sombra. La duplicación de solicitudes es una función separada y hay que comprobar si la admite la implementación y versión elegidas.

</details>

### 12. ¿Qué significa omitir `timeout` en una ruta de ServiceProfile?

- A. Se aplica automáticamente un tiempo de espera de cinco segundos al perfil
- B. Ese campo de ServiceProfile no agrega un tiempo de espera a la ruta
- C. La solicitud falla inmediatamente
- D. Se eliminan todos los límites de tiempo de las demás capas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El campo no agrega un tiempo de espera a la ruta, pero aún pueden aplicarse límites de la aplicación, el cliente, el transporte, el proxy o el balanceador de carga. No garantiza un tiempo de espera ilimitado de extremo a extremo. Los plazos y la cancelación de flujos requieren un diseño explícito que tenga en cuenta la aplicación.

</details>
