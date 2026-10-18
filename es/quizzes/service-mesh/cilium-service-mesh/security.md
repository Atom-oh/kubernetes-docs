# Cuestionario de seguridad de Cilium Service Mesh

Revisado con Cilium 1.20.3. La [guía de seguridad](../../../service-mesh/cilium-service-mesh/03-security.md) distingue la autenticación fuera de banda, el cifrado del transporte y la versión beta de ztunnel, e incluye referencias principales.

### 1. ¿Qué proporciona SPIRE para la autenticación mutua fuera de banda de Cilium?

- **A.** Un sidecar de Istio para cada Pod
- **B.** Credenciales de identidad SVID para el mecanismo de autenticación de los agentes
- **C.** El cifrado automático de todo el tráfico de las aplicaciones
- **D.** Un reemplazo del servidor de API de Kubernetes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Credenciales de identidad SVID para el mecanismo de autenticación de los agentes**

En el mecanismo beta fuera de banda, SPIRE proporciona credenciales de identidad SVID y los agentes de Cilium autentican a sus pares por separado de la conexión de la aplicación. El cifrado con WireGuard/IPsec es una opción independiente. Cilium 1.20.3 también incluye una versión beta distinta de mTLS con ztunnel, con su propia CA, proceso de arranque, inscripción y limitaciones de políticas.

</details>

### 2. ¿Qué comportamiento tiene CiliumNetworkPolicy cuando el modo de autenticación se establece en «required»?

- **A.** Permite todo el tráfico sin autenticación
- **B.** Solo permite el tráfico que supera la autenticación mutua
- **C.** Solo registra advertencias cuando falla la autenticación
- **D.** Deshabilita mTLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Solo permite el tráfico que supera la autenticación mutua**

La regla de permiso correspondiente exige que la autenticación tenga éxito; no es un ajuste global del clúster ni cifra por sí mismo el contenido de la aplicación mediante TLS. Siguen aplicándose los demás requisitos de autorización y autenticación de la aplicación. La API usa `authentication: {mode: required}`, no una matriz.

</details>

### 3. ¿Qué tráfico no cifra Cilium WireGuard por sí solo?

- **A.** El tráfico compatible entre Pods de distintos nodos
- **B.** El tráfico compatible de nodos remotos cuando está habilitado el cifrado entre nodos
- **C.** El tráfico entre Pods del mismo nodo y el tramo entre el cliente externo y el clúster
- **D.** Una ruta compatible entre Pods remotos a través de un servicio ClusterIP

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. El tráfico entre Pods del mismo nodo y el tramo entre el cliente externo y el clúster**

Cilium WireGuard no cifra el tráfico entre Pods del mismo nodo ni el tramo entre un cliente externo y el clúster. La cobertura del tráfico entre nodos remotos depende del modo elegido y de las excepciones documentadas. Se requiere compatibilidad con el kernel; el chart no ofrece una opción `userspaceFallback`.

</details>

### 4. ¿Cuál es la configuración correcta para restringir rutas y métodos específicos con reglas HTTP de capa 7 en CiliumNetworkPolicy?

- **A.** Indicar la ruta y el método en `toEndpoints`
- **B.** Indicar el método y la ruta en `toPorts.rules.http`
- **C.** Indicarlos directamente en `ingress.http`
- **D.** Definir las reglas en `spec.http`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Indicar el método y la ruta en `toPorts.rules.http`**

Las reglas HTTP se configuran en `ingress/egress toPorts.rules.http`. Pueden coincidir con campos compatibles de método, ruta y encabezado, pero comprobar que exista un encabezado o que parezca contener un token Bearer no valida un JWT ni autoriza al usuario final.

</details>

### 5. ¿Qué ventaja tiene la política basada en identidades de Cilium?

- **A.** Los selectores de etiquetas de las políticas pueden seguir siendo estables aunque cambien las IP de los Pods
- **B.** Usa direcciones MAC en vez de etiquetas
- **C.** Todos los ID numéricos son permanentes tras cada reinicio
- **D.** Elimina las actualizaciones de la correspondencia entre direcciones e identidades

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Los selectores de etiquetas de las políticas pueden seguir siendo estables aunque cambien las IP de los Pods**

Las políticas usan conjuntos de etiquetas relevantes para la identidad en lugar de listas de IP de Pods mantenidas manualmente. Varios Pods pueden compartir una identidad, pero Cilium sigue actualizando el estado de direcciones e identidades, y puede recolectar y reasignar ID. Un reinicio no garantiza que los identificadores numéricos sean permanentes.

</details>

### 6. ¿Qué reglas se usan para restringir el acceso a dominios externos con políticas DNS de capa 7 en Cilium?

- **A.** Combinar `toFQDNs` con reglas DNS
- **B.** Usar solo `toEndpoints`
- **C.** Usar solo `toCIDR`
- **D.** Usar solo `toEntities`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A. Combinar `toFQDNs` con reglas DNS**

Las reglas DNS limitan las consultas al solucionador seleccionado; `toFQDNs` y las reglas de puertos controlan por separado las conexiones a las direcciones aprendidas. Incluye el comportamiento real del solucionador con UDP/TCP y los nombres de la lista de búsqueda. El nombre de un servicio incluye las etiquetas del servicio y del espacio de nombres, y permitir DNS no concede permiso universal para conectarse.

</details>

### 7. ¿Qué se debe permitir al introducir una política de denegación predeterminada?

- **A.** Todos los destinos externos
- **B.** Las dependencias explícitas de las cargas de trabajo, incluido el solucionador o las comprobaciones necesarias
- **C.** Todo el tráfico de host como requisito mínimo universal
- **D.** Todas las direcciones que DNS haya devuelto alguna vez

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Las dependencias explícitas de las cargas de trabajo, incluido el solucionador o las comprobaciones necesarias**

Permite solo las dependencias que requieran la carga de trabajo y la topología, como el solucionador DNS real por UDP/TCP 53 y las comprobaciones necesarias. El acceso general a la red del host no es un requisito mínimo universal. Usa las opciones explícitas `enableDefaultDeny` cuando la política de Cilium tenga matrices vacías para las reglas direccionales.

</details>

### 8. ¿Qué función cumple la atestación de cargas de trabajo en SPIRE?

- **A.** Emitir certificados
- **B.** Verificar la identidad de las cargas de trabajo
- **C.** Aplicar políticas de red
- **D.** Cifrar el tráfico

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Verificar la identidad de las cargas de trabajo**

El agente SPIRE realiza la atestación de cargas de trabajo mediante los atestadores y selectores configurados; el servidor atesta a los agentes y firma los SVID. La integración fuera de banda de Cilium también usa la recuperación delegada de identidades y entradas para las identidades de seguridad de Cilium. Esto no cifra automáticamente el contenido de las aplicaciones.

</details>

### 9. ¿Cómo se comporta Cilium al probar políticas de red en modo de auditoría?

- **A.** Bloquea todo el tráfico
- **B.** Registra las infracciones de las políticas, pero permite el tráfico
- **C.** Deshabilita por completo las políticas
- **D.** Solo envía alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Registra las infracciones de las políticas, pero permite el tráfico**

La opción mutable de endpoint `PolicyAuditMode` cambia la aplicación de las políticas en el plano de datos auditado para probar un endpoint aislado. `cilium.io/audit-mode` no es una anotación por política compatible. Restablece la aplicación de las políticas después de la prueba y verifica por separado el comportamiento de capa 7; `enableDefaultDeny:false` tampoco es un modo de auditoría universal.

</details>

### 10. ¿Qué debe modelar una política de privilegio mínimo para un backend de tres capas?

- **A.** Todo el tráfico sin restricciones
- **B.** La entrada necesaria desde el frontend, la salida hacia la base de datos y las dependencias explícitas, como DNS
- **C.** Ninguna entrada, ni siquiera desde el frontend
- **D.** Acceso a Internet sin restricciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. La entrada necesaria desde el frontend, la salida hacia la base de datos y las dependencias explícitas, como DNS**

El backend permite las conexiones necesarias de sus clientes frontend y hacia los destinos de la base de datos, además de dependencias explícitas como DNS. La política de base de datos de la guía habilita explícitamente la denegación de salida predeterminada sin reglas que permitan la salida. Las respuestas con estado siguen siendo posibles; la segmentación de red no equivale a una autorización completa de la aplicación ni a prevención de pérdida de datos.

</details>

### 11. ¿Qué significa `keyRotationDuration: 5m` en IPsec?

- **A.** Generar una clave nueva cada cinco minutos
- **B.** Rotar cada cinco minutos el certificado de todas las cargas de trabajo
- **C.** Permitir un período de transición y limpieza de la clave anterior después de cambiar una clave
- **D.** Reutilizar indefinidamente una clave global

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Permitir un período de transición y limpieza de la clave anterior después de cambiar una clave**

`keyRotationDuration` de IPsec controla el período de transición o de eliminación de la clave anterior después de cambiar el material de clave. No genera claves de forma periódica. Usa el procedimiento compatible de rotación coordinada de claves e ID, y el formato de clave derivada por túnel con `+`. En cambio, WireGuard administra pares de claves generados por los nodos.

</details>

### 12. ¿Qué comando de Hubble selecciona los flujos descartados antes de examinar sus motivos?

- **A.** `hubble observe --verdict FORWARDED`
- **B.** `hubble observe --verdict DROPPED`
- **C.** `hubble policy list`
- **D.** `hubble status --violations`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `hubble observe --verdict DROPPED`**

`DROPPED` selecciona flujos descartados por distintas causas. Añade `--drop-reason-desc POLICY_DENIED` para examinar los descartes informados como denegados por una política, y revisa por separado los fallos de capa 7 o de la aplicación. `AUDIT` es un veredicto distinto. El historial seleccionado con `--last` tiene límites y Relay puede devolverlo por instancia de Hubble.

</details>
