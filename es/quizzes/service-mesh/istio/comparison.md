# Cuestionario comparativo de Istio

> **Informe histórico**: Istio 1.30.2 / EKS 1.36.2; no es una matriz actual de soporte
> **Última actualización**: 11 de septiembre de 2026

Evalúa criterios sidecar/ambient, especialmente los límites de las mediciones EKS publicadas. La auditoría no reprodujo esos experimentos.

## Preguntas de opción múltiple (1-6)

### Pregunta 1: Evidencia sobre los 503 del waypoint ambient

¿Qué puede concluirse de los conteos agregados de rollout sobre la causa de los 503?

A. Se demostró asignación IP duplicada

B. La carrera del ciclo de conexión es una hipótesis; hacen falta flags de respuesta y cronologías de endpoints/conexiones

C. Se demostró que NetworkPolicy causó todos los fallos

D. Los conteos prueban que STRICT mTLS no está soportado

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

Los estados HTTP agregados no determinan una causa. Terminación Pod, propagación de endpoints, drenaje, timeouts y pools pueden contribuir. La explicación original de reutilización IP/notificación ztunnel no tenía una cronología diagnóstica conservada. Investigue hosts upstream, flags, UID de Pods y eventos de conexión, sin enseñar esa hipótesis como mecanismo probado.

**Referencias:**

- [Guía de selección sidecar y ambient](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Ambient: proxy waypoint](../../../service-mesh/istio/advanced/01-ambient-mode.md)

</details>

---

### Pregunta 2: Interpretar los resultados EKS

Las muestras sin ajustar registraron 324 HTTP 503 y 2 errores no HTTP en 60,000 llamadas sidecar; 0 y 195 en 60,000 ambient L4; y 1,528 y 84 en 59,913 ambient L7. ¿Qué interpretación está respaldada?

A. Ambient siempre es más estable

B. L7 tuvo mayor fracción observada de HTTP 503; cero 503 en L4 todavía dejó 195 fallos no HTTP

C. Se probó una misma causa para todas las categorías

D. SocketCount de Fortio mide directamente el pool upstream del waypoint

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

Las fracciones son 0.54% en sidecar y aproximadamente 2.55% en L7, una razón de 4.72 en estas muestras, no un multiplicador propio del producto. Cero 503 no es cero fallos. El código no HTTP -1 de Fortio no identifica reset/EOF/timeout sin detalles. SocketCount mide sockets cliente; L7 tuvo más (2,486), no L4 (1,652). QPS solicitado por duración no garantiza llamadas completadas exactas, y distintos conteos de rollout limitan la comparación causal.

**Referencias:**

- [Guía sidecar/ambient: resultados de rollout sin interrupciones](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Pregunta 3: NetworkPolicy y ambient

En el experimento VPC CNI se verificó aplicación de políticas y una regla de entrada solo para 8080 bloqueó la ruta HBONE observada. ¿Qué debe comprobarse después?

A. Eliminar todas las NetworkPolicies

B. Permitir TCP 15008 con alcance adecuado y verificar origen, identidad y límites de política del puerto interior

C. Cambiar mTLS a PERMISSIVE

D. Reiniciar CNI y asumir que la política es correcta

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

El flujo se recuperó tras permitir TCP 15008. Es evidencia de esa ruta probada, no de comportamiento idéntico en todo CNI o política. Permitir el túnel exterior no constituye una política completa de mínimo privilegio para su tráfico interno. Verifique selectores de origen, paso por waypoint, dependencias DNS/control plane y aplicación real. La observación del puerto de aplicación sidecar también tiene alcance limitado.

**Referencias:**

- [Guía sidecar/ambient: NetworkPolicy](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Pregunta 4: API no idempotentes y reintentos

¿Por qué desactivar explícitamente por defecto los reintentos mesh en comandos no idempotentes, como crear pedidos?

A. Siempre consumen más CPU que la aplicación

B. Una respuesta fallida o perdida puede dejar el resultado desconocido y repetir un comando ya confirmado

C. Son incompatibles con STRICT mTLS

D. Ambient no tiene reintentos L7

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

Timeout, reset o error no siempre prueban ausencia de efecto. Repetir una escritura ambigua puede duplicar trabajo si el servidor no aporta idempotencia durable/transacciones adecuadas. No depende de probar una carrera concreta del waypoint. Cero duplicados en el antiguo T2 no demuestra seguridad ni una frecuencia fiable: cliente ilimitado, conteos incompatibles con duración/tasa y posibles errores del observador ocultos. Un observador revisado y limitado tampoco es un registro transaccional de negocio. Mida ID estables y pérdida de respuesta con observación completa.

**Referencias:**

- [Guía sidecar/ambient: riesgo de usar reintentos como mitigación](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)

</details>

---

### Pregunta 5: Comparación justa del plano de datos

¿Qué experimento inicial permite separar fallos de fallos ocultos por reintentos?

A. Comparar solo éxitos GET finales

B. Mantener reintentos sidecar y desactivar ambient

C. Usar attempts: 0 en escrituras de ambos modos y recoger errores HTTP/no HTTP, contadores de retry, entregas upstream y resultados finales

D. Elegir el modo con menor CPU media

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: C**

**Explicación:**

Sidecar y waypoint Envoy pueden reintentar L7; ztunnel no interpreta 503 ni repite HTTP. Desactive equivalentemente escrituras y registre upstream_rq_retry, entregas reales, ID estables y contabilidad cliente. Controle carga, versiones, recursos y exposición a rollout; repita el experimento. Separa mejor las observaciones, pero una ejecución no demuestra estabilidad intrínseca.

**Referencias:**

- [Guía sidecar/ambient: medición de fallos brutos](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Reintentos y timeout](../../../service-mesh/istio/traffic-management/05-retry-timeout.md)

</details>

---

### Pregunta 6: Autenticación y cifrado Cilium

En la autenticación mutua fuera de banda documentada, ¿qué implica authentication required?

A. Todos los datos usan TLS de carga automáticamente

B. Handshake de identidad y cifrado de datos son separados; el cifrado se configura y verifica aparte

C. Es idéntico a PeerAuthentication STRICT en implementación y madurez

D. Ya no se necesita autorización

<details>
<summary>Respuesta y explicación</summary>

**Respuesta: B**

**Explicación:**

La documentación publicada de Cilium 1.20.1 califica este mecanismo como Beta y describe una negociación fuera de banda separada de la ruta de datos de la aplicación. La política de autenticación por sí sola no cifra el contenido de la aplicación. Evalúe por separado el cifrado compatible de WireGuard/IPsec, incluidos sus límites de plataforma y cobertura de tráfico. Cilium 1.20.1 también tiene una beta de cifrado ztunnel independiente, con incorporación por espacio de nombres, solo TCP y restricciones de políticas/plataforma. Este ajuste de política de autenticación fuera de banda no la activa.

**Referencias:**

- [Seguridad de Cilium Service Mesh](../../../service-mesh/cilium-service-mesh/03-security.md)

</details>

---

## Puntuación

- Cuente aciertos entre las 6 preguntas.
- 6/6: Puede explicar selección sidecar/ambient/Cilium y riesgo de retry con evidencia medida.
- 4-5/6: Repase medición de fallos brutos o diferencia autenticación/cifrado.
- 0-3/6: Relea desde el inicio la [guía de selección](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md).

## Recursos de aprendizaje

- [Guía de selección sidecar/ambient](../../../service-mesh/istio/comparison/03-sidecar-vs-ambient.md)
- [Modo ambient](../../../service-mesh/istio/advanced/01-ambient-mode.md)
- [mTLS](../../../service-mesh/istio/security/01-mtls.md)
- [Seguridad Cilium Service Mesh](../../../service-mesh/cilium-service-mesh/03-security.md)

## Evidencia oficial

- [Estado de funciones L7 ambient](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md)
- [Autenticación mutua Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst)
