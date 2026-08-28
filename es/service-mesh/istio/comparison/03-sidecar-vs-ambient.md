# Guía de selección entre Sidecar y modo Ambient (resultados de pruebas de EKS 1.36)

> **Versiones compatibles**: Istio 1.30 / EKS 1.36
> **Última actualización**: August 21, 2026

Este documento es una guía basada en resultados de pruebas para decidir si adoptar Istio en **modo sidecar o modo ambient** para cargas de trabajo de misión crítica en EKS (por ejemplo, la ruta de órdenes/emparejamiento de un exchange de criptomonedas). La arquitectura en sí ya se trata en [Ambient Mode](../advanced/01-ambient-mode.md), por lo que este documento no la repite; en su lugar, presenta los resultados de pruebas y una recomendación frente a 4 requisitos concretos.

1. mTLS requerido (comunicación Pod a Pod interna del clúster)
2. NetworkPolicy requerida
3. Cargas de trabajo sensibles a la latencia
4. Rollout sin tiempo de inactividad — verificación de la preocupación por los 503 del waypoint ambient

> 💡 Cada cifra de este documento procede de un **clúster EKS dedicado y de un solo tenant** (`mesh-isolated-test`) creado únicamente para este ciclo de pruebas y eliminado después. Consulta la [nota sobre el aislamiento de las pruebas](#a-note-on-test-isolation) al final de §4 para saber por qué fue necesario un clúster dedicado.

## Resumen de decisión

| Requisito | Sidecar | Ambient (L4, sin waypoint) | Ambient (L7, waypoint) | Cilium |
|---|---|---|---|---|
| mTLS | ✅ STRICT compatible, verificado | ✅ STRICT compatible, verificado | ✅ STRICT compatible, verificado | ⚠️ No medido en este ciclo — documentado como autenticación mutua de identidad más WireGuard/IPsec habilitado por separado, no como un único interruptor equivalente a STRICT (consulta [abajo](#separate-raw-failures-from-failures-hidden-by-retry)) |
| NetworkPolicy | ✅ Las reglas existentes funcionan sin cambios, verificado | ⚠️ Debe permitir el puerto HBONE (15008), verificado | ⚠️ Debe permitir el puerto HBONE (15008), verificado | ⚠️ No medido en este ciclo — CiliumNetworkPolicy es el mecanismo nativo, no un complemento de K8s NetworkPolicy |
| Latencia (P50 sobre la referencia sin mesh) | +1.29ms, medido | +0.04ms (insignificante), medido | +1.86ms, medido | No medido en este ciclo |
| Rollout sin tiempo de inactividad | Se producen 503 (0.5%, medido) | **Cero 503 reales**, reemplazados por 0.3% de restablecimientos TCP | Se producen 503 **2.6%, ~5x sidecar** (medido) | No medido en este ciclo |

> ✅ **Conclusión en una línea**: ambient sin waypoint (solo L4) fue el más estable bajo actividad intensa de rollouts y tuvo una sobrecarga de latencia insignificante. Adjuntar un waypoint (L7) eleva la tasa de 503 por encima de la de sidecar y la latencia aproximadamente al mismo nivel que sidecar. La evidencia está en §3–§4 a continuación. Cilium se incluye para una comparación de seguridad equivalente (consulta [abajo](#separate-raw-failures-from-failures-hidden-by-retry)); no se desplegó en el clúster de pruebas, por lo que su fila solo indica propiedades documentadas, nunca un sustituto de una medición.

## 1. mTLS — Resultados de pruebas (EKS 1.36.2, Istio 1.30.2)

**Entorno de prueba**
- Clúster dedicado de un solo tenant `mesh-isolated-test` (VPC propia, sin otras cargas de trabajo), plano de control de EKS y nodos worker ambos v1.36.2, Amazon Linux 2023 (arm64, m7g.xlarge)
- `PeerAuthentication` STRICT con ámbito de Namespace aplicado a 3 Namespaces de prueba (sidecar / ambient-L4 / ambient-L7), no en todo el mesh

### Comprobación 1 — acceso directo de texto sin cifrar a IP de Pod (debe bloquearse)

```
plaintext-client -> sidecar echo pod:8080
  [E] Read error, err="read tcp ...: read: connection reset by peer"
plaintext-client -> ambient-L4 echo pod:8080
  [E] Read error, err="EOF"
plaintext-client -> ambient-L7 echo pod:8080
  [E] Read error, err="EOF"
```

### Comprobación 2 — acceso dentro del mesh mediante Service (debe funcionar)

```
sidecar client -> http://echo:8080/     => HTTP/1.1 200 OK (server: envoy)
ambient-L4 client -> http://echo:8080/  => HTTP/1.1 200 OK (no envoy headers, pure L4 passthrough)
ambient-L7 client -> http://echo:8080/  => HTTP/1.1 200 OK (server: istio-envoy, x-envoy-decorator-operation)
```

### Comprobación 3 — certificados SPIFFE

Verificado mediante `istioctl ztunnel-config certificates` / `istioctl proxy-config secret`:

| Carga de trabajo | Emisor del certificado | ID SPIFFE | CA raíz |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | compartida |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | compartida |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | compartida |

> ✅ **Veredicto**: los tres modos bloquean inmediatamente el acceso de texto sin cifrar, solo el tráfico dentro del mesh devuelve 200, y cada carga de trabajo lleva su propio ID SPIFFE emitido desde la misma CA raíz. Tanto sidecar como ambient satisfacen el requisito de que el tráfico Pod a Pod interno del clúster debe usar mTLS.

**Cómo difieren**: ambient aplica mTLS de forma transparente — `istio-cni` configura la redirección de tráfico dentro del Namespace de red del Pod, y ztunnel lo transporta por un túnel HBONE (mTLS) en el puerto 15008 — sin requerir código de aplicación ni inyección de sidecar. Sidecar logra lo mismo mediante el contenedor istio-proxy dentro del Pod de la aplicación. Consulta [mTLS](../security/01-mtls.md) para detalles sobre la rotación de certificados y la estrategia de migración de ambos modos.

## 2. NetworkPolicy — Resultados de pruebas

Ambient reenvía el tráfico real de un Pod a ztunnel mediante un túnel HBONE (TCP 15008), que ztunnel descifra y entrega al destino. Esto significa que **una NetworkPolicy que permita solo el puerto de aplicación (por ejemplo, 8080) bloqueará el tráfico entrante a un Pod inscrito en ambient**, porque los paquetes llegan realmente al 15008. Para usar ambient junto con NetworkPolicy, debes **agregar una regla de permiso entrante para TCP 15008** en los Pods de destino.

**Configuración de prueba**: se habilitó la aplicación de NetworkPolicy de VPC CNI (`enableNetworkPolicy=true`, `aws-network-policy-agent v1.3.5-eksbuild.3`, eBPF) en el clúster dedicado `mesh-isolated-test`; esto no se podía hacer de forma segura en el clúster compartido utilizado en una ronda anterior, ya que habría activado simultáneamente 13 NetworkPolicies inactivas preexistentes de otros equipos. Un clúster dedicado de un solo tenant eliminó por completo esa preocupación de radio de impacto.

> ⚠️ **Problema operativo detectado durante las pruebas**: los Pods creados *antes* de activar `enableNetworkPolicy` no se aplican retroactivamente — los hooks eBPF solo se adjuntan durante la configuración de red del Pod (CNI ADD). Una comprobación de cordura lo confirmó directamente: aplicar una política que permitía *solo* el puerto 9999 a Pods ya en ejecución aún dejaba pasar sin bloqueo el tráfico del puerto 8080. Fue necesario ejecutar `kubectl rollout restart` (recrear los Pods) después de habilitar el addon antes de que cualquier NetworkPolicy surtiera efecto. Es un problema real que conviene conocer antes de habilitar NetworkPolicy en un clúster activo.

**Prueba 1 — ingreso restringido solo a TCP 8080** (Pods nuevos, aplicación confirmada como activa)

| Modo | Resultado |
|---|---|
| sidecar | ✅ 200 OK — sin cambios |
| ambient-L4 | ❌ bloqueado (`i/o timeout`) |
| ambient-L7 | ❌ bloqueado (`i/o timeout`) |

**Prueba 2 — el ingreso permite TCP 8080 + TCP 15008 (HBONE)**

| Modo | Resultado |
|---|---|
| ambient-L4 | ✅ 200 OK — restaurado |
| ambient-L7 | ✅ 200 OK — restaurado |

> ✅ **Veredicto**: confirma la hipótesis anterior con tráfico real. El paquete entrante real de ambient en el Namespace de red del Pod de carga de trabajo llega al puerto HBONE de ztunnel (15008), no al puerto de la aplicación (8080); una NetworkPolicy limitada al puerto de la aplicación rompe silenciosamente los Pods inscritos en ambient. Sidecar no se ve afectado porque la captura de tráfico de sidecar ocurre por completo dentro del Namespace de red del propio Pod después de que el paquete ya llegó al puerto de la aplicación.

Recomendamos defensa en profundidad: aplica conjuntamente controles a nivel de red (NetworkPolicy) y a nivel de identidad (AuthorizationPolicy). El conflicto del modo sidecar entre mTLS y NetworkPolicy se trata en [mTLS and NetworkPolicy Conflict](../security/01-mtls.md#7-mtls-and-networkpolicy-conflict).

## 3. Latencia — Resultados de pruebas (T5)

**Configuración de prueba**: carga fortio, 200 qps, 60s, 16 conexiones, 12,000 solicitudes por caso, estado estable (sin reinicios de rollout en ejecución) — referencia sin mesh (Namespace sin mesh) frente a sidecar frente a ambient-L4 frente a ambient-L7, todos en los mismos nodos Graviton (m7g.xlarge) de `mesh-isolated-test`. Todos los casos devolvieron 100% Code 200.

| Caso | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh (referencia) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (sin waypoint) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |

**Sobrecarga P50 frente a la referencia sin mesh**: sidecar +1.29ms · ambient-L4 +0.04ms (insignificante) · ambient-L7 +1.86ms

> ✅ **Veredicto**: coherente con el benchmark publicado anteriormente citado del modo ambient (solo L4 inferior a sidecar, waypoint aproximadamente a la par o ligeramente por encima de sidecar); estas son ahora mediciones de primera parte, no una cita. Para una carga de trabajo sensible a la latencia como una ruta de trading de criptomonedas, esto concuerda con §4 a continuación: **evitar el waypoint ayuda tanto a la latencia como a la estabilidad del rollout**.

## 4. Rollout sin tiempo de inactividad — Resultados de pruebas de 503 (hallazgo principal)

### Antecedentes

La preocupación con ambient es que **el waypoint L7 (Envoy) reutiliza conexiones de su pool, indexadas por IP:Puerto de destino**, mientras que **ztunnel no notifica al waypoint cuando un Pod termina**. Si la IP del Pod terminado se reasigna a un Pod nuevo, el waypoint puede reutilizar una conexión ya no válida y devolver un 503. Sidecar puede sufrir una carrera de terminación de Pod similar (consulta [Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination) para el mecanismo). Medimos ambos modos de fallo cara a cara en EKS 1.36.

**Entorno de prueba**
- Clúster dedicado de un solo tenant `mesh-isolated-test`, plano de control de EKS y nodos worker ambos v1.36.2, arm64 (Graviton m7g.xlarge), Istio 1.30.2
- 3 Namespaces (sidecar / ambient-L4 / ambient-L7) que ejecutan **cargas de trabajo idénticas byte a byte** (un Deployment de servidor echo con 6 réplicas + un cliente fortio) — solo difiere la etiqueta del Namespace
- El cliente fortio mantuvo conexiones keepalive a 100 req/s mientras se ejecutaba repetidamente `rollout restart` en el Deployment `echo` del Namespace de destino
- 60,000 solicitudes recopiladas por modo (= 100 qps × 600s)

### Resultados

| Modo | Ciclos de rollout | Solicitudes | Cantidad de 503 | Tasa de 503 | Otros errores (-1, TCP reset/EOF) | Sockets usados |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4 (sin waypoint) | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7 (waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |

> Un keepalive perfecto implicaría 16 sockets usados. Ambient-L7 también dejó 87 de 60,000 llamadas incompletas al finalizar la ejecución, y su latencia media (50.4ms) estuvo muy por encima de los otros dos modos (~2-3ms).

<details>
<summary>Salida sin procesar de la ejecución de fortio</summary>

```
[sidecar]      42 rollouts, Sockets used: 350 (16 would be perfect keepalive)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- connection dropped with no HTTP response, not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 of 60,000 calls completed; avg latency 50.4ms vs. ~2-3ms for the other two modes)
```

</details>

**Veredicto**

1. **La tasa de 503 de Ambient-L7 (waypoint) (2.6%) es aproximadamente 5x la de sidecar (0.5%)** en este clúster dedicado — una brecha incluso mayor de lo que había sugerido una medición anterior el mismo día en un clúster compartido y con contención (consulta la nota de aislamiento a continuación), reforzando en vez de suavizar la preocupación original de que «el pool de conexiones del waypoint reutiliza conexiones obsoletas y produce 503» bajo actividad intensa de rollouts.
2. **Ambient-L4 (sin waypoint) volvió a producir cero 503 HTTP reales.** En cambio, vio errores TCP a nivel de conexión ("-1", sin respuesta) al 0.3%. En L4 un fallo aparece como una *conexión descartada*, no como una *respuesta 503*, dejando el manejo de reconexión al cliente/aplicación en lugar de a un proxy que sintetiza una respuesta de error.
3. Ambient-L7 también mostró un gran pico de latencia media y 87 solicitudes que nunca se completaron durante la ejecución, coherente con un waypoint que tiene dificultades bajo la combinación de actividad intensa de rollouts y carga sostenida, distinto de los otros dos modos.
4. Los ciclos de rollout completados en la misma ventana de 600 segundos (42 / 64 / 65 para sidecar / ambient-L4 / ambient-L7) fueron mucho más altos que en una medición anterior en un clúster compartido ocupado, porque este clúster dedicado no tenía otros tenants compitiendo por CPU/red; el orden *relativo* (sidecar más lento, ambient-L4 más rápido) se mantuvo, pero la velocidad absoluta de rollout depende mucho de la contención del clúster y no debe interpretarse en exceso como una propiedad intrínseca de ningún modo.

### Seguimiento: después del refuerzo de apagado ordenado

Las cifras de referencia anteriores reflejan **ningún ajuste de apagado en absoluto**. Repetimos la misma prueba T1 (100 qps × 600s, 60,000 solicitudes/modo) después de añadir dos cambios:

- **Los tres modos**: `lifecycle.preStop.sleep.seconds: 10` en el contenedor `echo` (la acción sleep nativa de K8s 1.29+, sin requerir exec/shell) más `terminationGracePeriodSeconds: 40`, dando tiempo para que la eliminación de Endpoint se propague por el clúster antes de que el Pod deje realmente de aceptar conexiones
- **Solo sidecar**: `EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true` + `terminationDrainDuration: 30s` inyectados en istio-proxy mediante la anotación de Pod `proxy.istio.io/config` (se confirmó su presencia en el env real del contenedor init de istio-proxy) — sale en cuanto las conexiones activas llegan a cero en lugar de esperar siempre los 30s completos

| Modo | Ciclos de rollout | Code 200 | Code 503 | Code -1 | Sockets usados | Latencia media |
|---|---|---|---|---|---|---|
| sidecar (reforzado) | 42 | 60,000 (100%) | **0** | **0** | 16 (keepalive perfecto) | 2.630ms |
| ambient-L4 (reforzado) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (reforzado) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |

**Comparación referencia → reforzado**

| Modo | Tasa de error de referencia | Tasa de error reforzada | Cambio |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **503 eliminados por completo** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **Errores TCP también eliminados por completo** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | Tasa de 503 reducida en más de la mitad |

> ✅ **Veredicto**: esto confirma, con mediciones, la hipótesis de que estos 503 provienen de que un Pod no se apaga ordenadamente antes de que se propague la eliminación de su Endpoint; `preStop sleep 10` por sí solo eliminó completamente los errores para sidecar y ambient-L4. Ambient-L7 (waypoint) también mejoró sustancialmente, pero no llegó a cero; esto significa que el propio mecanismo de reutilización de conexiones obsoletas del waypoint (el hallazgo principal de §4 anterior) no se resuelve por completo solo con el ajuste de apagado ordenado del lado de la carga de trabajo. Si enrutas a través de un waypoint, aplica este refuerzo como referencia y sigue presupuestando el riesgo residual de 503 que no elimina.

### El riesgo del reintento como mitigación — Resultados de pruebas (T2)

**Configuración de prueba**: un arnés de `order` (6 réplicas, `POST /order` no idempotente con un retraso de 0.1s dentro del handler, informa su ID de solicitud a un `collector`), `collector` (cuenta ID de solicitudes distintos y marca cualquiera visto más de una vez), y `order-client` (carga POST continua a 20 req/s con un UUID único por solicitud). Se aplicó una política de reintento (`attempts: 3, perTryTimeout: 2s, retryOn: 503,reset,connect-failure`) mediante la misma configuración Istio VirtualService tanto a sidecar (istio-proxy) como a ambient-L7 (waypoint). Cada modo se ejecutó durante 300s con `rollout restart` concurrente del Deployment `order`.

| Modo | Ciclos de rollout | Solicitudes enviadas | Fallos visibles para el cliente (los 3 reintentos agotados) | Ejecuciones duplicadas |
|---|---|---|---|---|
| sidecar (reintento VirtualService) | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7 (reintento waypoint) | 12 | 7,229 | 21 (0.29%) | **0** |

> ✅ **Veredicto**: no se observaron ejecuciones no idempotentes duplicadas en ninguno de los modos. Las bajas tasas de fallo visibles para el cliente confirman que los reintentos se activaron y en su mayoría ocultaron errores transitorios de actividad de rollout; sin embargo, ninguno de los reintentos exitosos resultó en que la misma solicitud lógica se procesara dos veces.

> ⚠️ **Esto no significa que la carrera sea imposible.** Significa que no se manifestó bajo estas condiciones específicas (perTryTimeout=2s, 20 req/s, 6 réplicas, apagado ordenado predeterminado, sin hook `preStop`). El mecanismo teórico — un reintento reenviado después de que la solicitud original ya llegó a la aplicación pero antes de que su respuesta regresara al llamador — requiere que la conexión se corte en una ventana estrecha *después* de que la aplicación comenzara a procesar pero *antes* de que la respuesta volviera. 300s de actividad continua de rollout no detectaron una instancia para ninguno de los modos, pero una ruta de producción no idempotente debería seguir tratando el reintento a nivel de mesh como inseguro de forma predeterminada sin claves de idempotencia del lado del servidor: esta prueba reduce la confianza de que la carrera sea *común*, no establece que sea *segura*.

### Separar los fallos sin procesar de los fallos ocultos por reintento

La selección del plano de datos mTLS y la política de reintento HTTP son decisiones independientes. Sidecar Envoy y waypoint Envoy pueden reintentar solicitudes HTTP en L7, mientras que ambient ztunnel es un [proxy L4](https://istio.io/latest/docs/ambient/architecture/data-plane/) que no puede interpretar un HTTP 503 ni repetir una solicitud HTTP. Por tanto, comparar solo las cantidades finales de 503 visibles para el cliente no puede mostrar si sidecar/waypoint tuvieron menos fallos sin procesar o simplemente los ocultaron mediante reintentos.

Para una comparación de rollout justa, establece `attempts: 0` en rutas de escritura POST/PATCH y registra estas dimensiones por separado:

- Eventos HTTP 503, TCP reset/EOF y connection-refused antes del reintento
- Contadores Envoy `upstream_rq_retry` y `upstream_rq_retry_success`
- Cantidad real de entregas upstream, incluida la solicitud original
- Éxito/fallo final visible para el cliente después del procesamiento de reintentos
- Si el servidor procesó la misma clave de idempotencia o ID de comando más de una vez

| Plano de datos | Significado de mTLS/cifrado | Ubicación del reintento L7 | Uso recomendado |
|---|---|---|---|
| Istio sidecar | mTLS de certificado SPIFFE de carga de trabajo | Envoy por Pod | Referencia conservadora para rutas críticas no idempotentes |
| Istio ambient L4 | mTLS de carga de trabajo HBONE entre ztunnels | Ninguno | Primer candidato cuando solo se requieren mTLS de Istio y política L4 |
| Istio ambient L7 | HBONE más waypoint Envoy | Waypoint compartido | Agregar solo a Services que requieran enrutamiento HTTP o política L7 |
| Cilium | La autenticación mutua de identidad y el cifrado de transporte como WireGuard/IPsec se seleccionan por separado | Ninguno en la capa de cifrado L3/L4 | Planos de datos Cilium existentes que necesitan política de identidad y cifrado de red |

> **Regla operativa:** si mTLS es el único requisito, valida primero ambient L4 y agrega waypoints solo a Services que necesiten política L7 o enrutamiento HTTP este-oeste. Mantén sidecar como referencia para rutas críticas no idempotentes cuando los errores de rollout ambient, medidos con reintentos de escritura deshabilitados, superen el presupuesto de errores de la carga de trabajo.

### Una nota sobre el aislamiento de las pruebas

<details>
<summary>Por qué fue necesario un clúster dedicado y qué siguió saliendo mal (haz clic para expandir)</summary>

Una ronda anterior de pruebas T1/T3 del mismo día se ejecutó en un clúster compartido (`fsi-demo-cluster`) en 4 Namespaces dedicados. El Namespace `benchmark` de ese clúster ejecutaba simultáneamente un gran barrido de trabajos de benchmark de Kafka en más de 100 tipos de instancias EC2 y, inmediatamente después de que se completara la carga T1 de ambient-L7, todos los recursos que había creado esa ronda (los 4 Namespaces, `istio-system` y todos los CRD de Istio/Gateway API) desaparecieron simultáneamente sin causa raíz confirmada (no se encontró Application de ArgoCD coincidente ni política Kyverno/Gatekeeper), dejando T2, T4 y T5 sin ejecutar y generando dudas sobre la validez de los números T1 recopilados bajo esa contención de recursos.

Esta ronda utilizó un clúster completamente nuevo de un solo tenant (`mesh-isolated-test`, su propia VPC, sin otras cargas de trabajo) específicamente para eliminar esa clase de interferencia y completó T1–T5 de extremo a extremo sin anomalías de recursos. En cambio, surgió una *diferente* brecha de aislamiento: a mitad del primer intento de T1 en el nuevo clúster, el current-context compartido de `~/.kube/config` de la estación de trabajo local cambió silenciosamente de `mesh-isolated-test` a un clúster no relacionado, invalidando ese intento (el bucle de rollout-restart comenzó a fallar con `namespace not found` al cambiar el contexto, aunque la conexión de carga fortio en curso, ya establecida, no se vio afectada). Se confirmó que los Namespaces y recursos de `mesh-isolated-test` permanecían completamente intactos mediante una comprobación explícita de kubeconfig; fue una confusión de contexto a nivel de estación de trabajo, no una eliminación del lado del clúster. La solución: un archivo kubeconfig limitado solo a `mesh-isolated-test`, referenciado explícitamente por cada script de prueba, con una protección que aborta si el contexto vuelve a desviarse. Todas las cifras finales de este documento proceden de las repeticiones corregidas y con contexto bloqueado.

</details>

## 5. Recomendación: un enfoque por niveles

En lugar de una elección binaria «sidecar o ambient», recomendamos **aplicar diferentes modos de mesh por nivel de carga de trabajo**. Esto coincide con la guía de casos de uso de [Ambient Mode](../advanced/01-ambient-mode.md#use-cases), y esta ronda de pruebas lo respalda con evidencia.

| Nivel | Ejemplo | Recomendación | Fundamento |
|---|---|---|---|
| Núcleo (creación/emparejamiento/liquidación de órdenes, no idempotente) | API de trading | **Solo Ambient L4 (sin waypoint) o mantener sidecar** | §4: la tasa de 503 es ~5x sidecar al enrutar a través de un waypoint; solo L4 tuvo cero 503. Si las funciones L7 son realmente necesarias, sidecar es la opción más madura. T2 no encontró instancias de ejecución duplicada bajo reintento para ninguno de los modos, pero eso no establece que sea seguro; mantén el reintento desactivado de forma predeterminada en este nivel sin importar el modo de mesh. |
| Seminúcleo (API de lectura idempotentes) | Consultas de precio/saldo | Ambient (L4, L7 si es necesario) | Las solicitudes idempotentes son seguras de reintentar, por lo que el riesgo del waypoint importa menos |
| Periferia (consultas, notificaciones, batch) | Dashboards, alertas | Adoptar ambient de forma agresiva | Maximiza el beneficio de recursos/operación; mTLS y comportamiento de rollout verificados como seguros por la prueba |

**El despliegue mixto a nivel de Namespace** se validó realmente en esta ronda de pruebas: los Namespaces sidecar, ambient-L4 y ambient-L7 se ejecutaron simultáneamente en el mismo clúster, cada uno aplicando independientemente mTLS STRICT.

### Limitaciones de solo L4: ¿aún puedo hacer despliegues canary?

Ambient solo L4 no tiene waypoint, por lo que ztunnel nunca mira dentro de la solicitud HTTP. Esto significa que **las funciones L7 — enrutamiento basado en encabezado/ruta HTTP, reintentos, circuit breaking, traffic mirroring — no se pueden aplicar a un Service solo L4.** Que esto bloquee realmente los despliegues canary depende de por dónde entra el tráfico.

> ✅ **El canary de ingreso no se ve afectado.** Un Istio Ingress Gateway o un `Gateway` de Gateway API siempre es un proxy Envoy completo e independiente (su propio Deployment), independientemente de si la carga de trabajo backend se ejecuta en modo ambient o sidecar. La división ponderada entre subconjuntos v1/v2 mediante `VirtualService`/`HTTPRoute` se decide por completo en el gateway; ztunnel (L4) solo tuneliza después la conexión al Pod de destino ya seleccionado. Los despliegues canary para API expuestas externamente funcionan bien con backends solo L4.

> ⚠️ **El canary interno del mesh (este-oeste) necesita L7 en ese Service específico.** Si el Service A llama al Service B dentro del mesh y quieres dividir el tráfico entre B-v1 y B-v2 por porcentaje, algo tiene que tomar esa decisión de enrutamiento en L7; ztunnel no puede. Necesitarías **desplegar un waypoint delante de B (cambiar B a ambient-L7) o ejecutar B con un sidecar** para que ese canary funcione.

**Conclusión**: los despliegues canary para API expuestas externamente funcionan bien con solo L4. Recurre a un waypoint o sidecar solo en el Service específico que necesite canary interno del mesh, que es exactamente cómo se pretende aplicar en la práctica la recomendación por niveles anterior.

**Lista de comprobación antes de la adopción**

- [ ] ¿La ruta de órdenes/emparejamiento/liquidación requiere realmente funciones L7 (enrutamiento HTTP, reintentos, división de tráfico)? Si no, ambient solo L4 es el candidato principal
- [ ] ¿Se actualizaron las NetworkPolicies para permitir el puerto HBONE (15008)? (§2, verificado; y si habilitas `enableNetworkPolicy` en un clúster activo por primera vez, recrea los Pods existentes, porque la aplicación no es retroactiva)
- [ ] ¿Se aplica una política de reintento a una ruta de API no idempotente? (§4 — T2 no encontró ejecuciones duplicadas en las pruebas, pero mantén el reintento deshabilitado de forma predeterminada en rutas no idempotentes sin claves de idempotencia del lado del servidor)
- [ ] ¿Se volvió a medir la latencia frente a tu propia carga de trabajo? (§3, verificado en los nodos Graviton de este clúster; vuelve a medir si tu tipo de instancia o perfil de carga de trabajo difiere sustancialmente)

## Apéndice: reproducción de estas pruebas

A continuación se muestran los archivos de configuración y procedimientos reales que produjeron cada cifra de este documento. Cópialos directamente para reproducir los resultados en tu propio clúster.

### A. Aprovisionamiento de clúster (eksctl)

El clúster dedicado de un solo tenant se creó con eksctl, utilizando subredes completamente públicas sin gateway NAT (un atajo exclusivo de pruebas para evitar necesitar nuevas Elastic IP; habilita NAT para clústeres de producción).

<details>
<summary>eksctl-cluster.yaml</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: "1.36"
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: "true"

availabilityZones:
  - ap-northeast-2a
  - ap-northeast-2c

vpc:
  nat:
    gateway: Disable

managedNodeGroups:
  - name: mesh-test-ng-arm64
    instanceType: m7g.xlarge
    amiFamily: AmazonLinux2023
    desiredCapacity: 3
    minSize: 3
    maxSize: 3
    volumeSize: 40
    privateNetworking: false
    labels:
      role: istio-mesh-test
    tags:
      ephemeral: "true"

addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: eks-pod-identity-agent
```

</details>

```bash
eksctl create cluster -f eksctl-cluster.yaml
```

### B. Instalación de Istio (CRD de Gateway API + perfil ambient)

El waypoint del modo Ambient es un recurso `Gateway` de Gateway API, por lo que los CRD de Gateway API deben existir antes de instalar Istio.

```bash
# 1) Gateway API CRDs (v1.1.0, compatible with Istio 1.30)
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.1.0/standard-install.yaml

# 2) Istio 1.30.2 ambient profile (via istioctl, not Helm)
istioctl install -f ambient-overlay.yaml -y
```

<details>
<summary>ambient-overlay.yaml (programa CNI/ztunnel/istiod en nodos arm64)</summary>

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  profile: ambient
  values:
    cni:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values: ["arm64"]
  components:
    pilot:
      k8s:
        affinity:
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: kubernetes.io/arch
                  operator: In
                  values: ["arm64"]
```

</details>

### C. Manifiestos de Namespace y carga de trabajo

4 Namespaces — `mesh-test-base` (sin mesh, para la referencia de latencia), `mesh-test-sidecar`, `mesh-test-ambient-l4`, `mesh-test-ambient-l7`. Solo difieren las etiquetas; todo lo demás es idéntico byte a byte.

<details>
<summary>namespaces.yaml</summary>

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-base
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-sidecar
  labels:
    istio-injection: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l4
  labels:
    istio.io/dataplane-mode: ambient
---
apiVersion: v1
kind: Namespace
metadata:
  name: mesh-test-ambient-l7
  labels:
    istio.io/dataplane-mode: ambient
```

</details>

<details>
<summary>Manifiesto de carga de trabajo (servidor echo, 6 réplicas + cliente fortio) — idéntico en los 4 Namespaces; solo cambia el campo namespace</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar   # swap for base / ambient-l4 / ambient-l7
  labels:
    app: echo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: echo
  template:
    metadata:
      labels:
        app: echo
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: echo
        image: fortio/fortio:1.69.4
        args: ["server", "-http-port", "8080"]
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /fortio/
            port: 8080
          initialDelaySeconds: 2
          periodSeconds: 3
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  selector:
    app: echo
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fortio-client
  namespace: mesh-test-sidecar
  labels:
    app: fortio-client
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fortio-client
  template:
    metadata:
      labels:
        app: fortio-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4
        command: ["/usr/bin/fortio"]
        args: ["server", "-http-port", "8081", "-redirect-port", "disabled"]
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

### D. mTLS — PeerAuthentication (§1)

<details>
<summary>peerauth-strict.yaml</summary>

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-sidecar
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l4
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict
  namespace: mesh-test-ambient-l7
spec:
  mtls:
    mode: STRICT
```

</details>

El Namespace ambient-L7 además necesita un waypoint desplegado:

```bash
istioctl waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
```

### E. NetworkPolicy (§2)

Habilita la aplicación de NetworkPolicy basada en eBPF de VPC CNI mediante la configuración del addon. Como se trata en §2, esto **solo se aplica a Pods creados o recreados después de este punto**.

```bash
aws eks update-addon --cluster-name mesh-isolated-test --addon-name vpc-cni --region ap-northeast-2 \
  --configuration-values '{"enableNetworkPolicy":"true"}' --resolve-conflicts OVERWRITE

# recreate existing pods so the eBPF hooks attach
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-sidecar
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l4
kubectl rollout restart deployment/echo deployment/fortio-client -n mesh-test-ambient-l7
```

<details>
<summary>Manifiestos NetworkPolicy (Prueba 1: solo 8080 → Prueba 2: 8080 + 15008)</summary>

```yaml
# Test 1 — this blocks ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4   # apply the same to ambient-l7 and sidecar
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
```

```yaml
# Test 2 — adding the HBONE port restores ambient
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-8080-only
  namespace: mesh-test-ambient-l4
spec:
  podSelector:
    matchLabels:
      app: echo
  policyTypes:
  - Ingress
  ingress:
  - ports:
    - protocol: TCP
      port: 8080
    - protocol: TCP
      port: 15008
```

</details>

### F. Ejecución de la prueba de rollout sin tiempo de inactividad (T1, §4)

Ejecuta simultáneamente el generador de carga fortio (primer plano, bloquea durante la duración de la prueba) y un bucle `rollout restart` (segundo plano); después detén el bucle cuando finalice la carga.

```bash
NS=mesh-test-sidecar   # repeat for ambient-l4, ambient-l7
DUR=600
CLIENT=$(kubectl get pods -n "$NS" -l app=fortio-client -o jsonpath='{.items[0].metadata.name}')

# ① rollout-restart loop (background) for DUR seconds
(
  START=$(date +%s)
  while [ $(( $(date +%s) - START )) -lt "$DUR" ]; do
    kubectl rollout restart deployment/echo -n "$NS"
    kubectl rollout status deployment/echo -n "$NS" --timeout=60s
  done
) &
ROLLOUT_PID=$!

# ② fortio load generator (foreground, 100qps x 600s = 60,000 requests)
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors http://echo:8080/

kill "$ROLLOUT_PID" 2>/dev/null
```

> 💡 Sin `-allow-initial-errors`, fortio aborta toda la ejecución si su solicitud de calentamiento coincide con un rollout y recibe un 503. Esta opción es obligatoria para cualquier prueba de carga que se superponga con actividad de rollout.

**Parche de refuerzo de apagado ordenado** (usado para la repetición «después del refuerzo» en §4, aplicado a los Deployments existentes mediante `kubectl patch --type strategic`):

```yaml
# common to all 3 modes — ambient-l4/l7 get only this patch
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```yaml
# sidecar namespace only, additionally (EXIT_ON_ZERO_ACTIVE_CONNECTIONS)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 30s
          proxyMetadata:
            EXIT_ON_ZERO_ACTIVE_CONNECTIONS: "true"
    spec:
      terminationGracePeriodSeconds: 40
      containers:
      - name: echo
        lifecycle:
          preStop:
            sleep:
              seconds: 10
```

```bash
kubectl patch deployment/echo -n mesh-test-sidecar --type strategic --patch-file patch-prestop-sidecar.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l4 --type strategic --patch-file patch-prestop-ambient.yaml
kubectl patch deployment/echo -n mesh-test-ambient-l7 --type strategic --patch-file patch-prestop-ambient.yaml
```

### G. Ejecución de la prueba de latencia (T5, §3)

El mismo comando fortio, ejecutado en estado estable sin bucle de rollout.

```bash
kubectl exec -n "$NS" "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors http://echo:8080/
```

### H. Arnés de prueba de reintento/ejecución duplicada (T2, §4)

Un arnés de 3 Pods — `order` (maneja el POST no idempotente), `collector` (detecta ID de solicitudes duplicados), `order-client` (carga continua) — desplegado de forma idéntica en los Namespaces sidecar y ambient-L7.

<details>
<summary>ConfigMap — order_server.py / collector.py / client.py</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
data:
  order_server.py: |
    import http.server, urllib.request, time, os

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404); self.end_headers(); return
            rid = self.headers.get("X-Request-Id", "unknown")
            time.sleep(0.1)  # widen the SIGTERM-mid-request race window
            try:
                req = urllib.request.Request(COLLECTOR_URL, data=rid.encode(), method="POST")
                urllib.request.urlopen(req, timeout=2)
            except Exception as e:
                print(f"collector report failed for {rid}: {e}", flush=True)
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 8080), Handler).serve_forever()
  collector.py: |
    import http.server, json, threading

    lock = threading.Lock()
    counts = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "dupe_count": len(dupes)}).encode()
            else:
                self.send_response(404); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    if __name__ == "__main__":
        http.server.ThreadingHTTPServer(("", 9090), Handler).serve_forever()
  client.py: |
    import urllib.request, uuid, time, os

    TARGET = os.environ.get("TARGET_URL", "http://order.mesh-test-sidecar.svc.cluster.local:8080/order")
    RPS = float(os.environ.get("RPS", "20"))
    interval = 1.0 / RPS
    sent = 0
    failed = 0
    while True:
        rid = str(uuid.uuid4())
        t0 = time.time()
        try:
            req = urllib.request.Request(TARGET, data=b"{}", method="POST", headers={"X-Request-Id": rid})
            urllib.request.urlopen(req, timeout=3)
            sent += 1
        except Exception:
            failed += 1
        dt = time.time() - t0
        if dt < interval:
            time.sleep(interval - dt)
```

</details>

<details>
<summary>Deployments + Services de order / collector / order-client</summary>

```yaml
apiVersion: v1
kind: Service
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  selector:
    app: collector
  ports:
  - port: 9090
    targetPort: 9090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collector
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collector
  template:
    metadata:
      labels:
        app: collector
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: collector
        image: python:3.12-alpine
        command: ["python3", "/scripts/collector.py"]
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: v1
kind: Service
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  selector:
    app: order
  ports:
  - port: 8080
    targetPort: 8080
    name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order
  namespace: mesh-test-sidecar
spec:
  replicas: 6
  selector:
    matchLabels:
      app: order
  template:
    metadata:
      labels:
        app: order
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order
        image: python:3.12-alpine
        command: ["python3", "/scripts/order_server.py"]
        env:
        - name: COLLECTOR_URL
          value: "http://collector.mesh-test-sidecar.svc.cluster.local:9090/record"
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-client
  namespace: mesh-test-sidecar
spec:
  replicas: 1
  selector:
    matchLabels:
      app: order-client
  template:
    metadata:
      labels:
        app: order-client
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine
        command: ["python3", "/scripts/client.py"]
        env:
        - name: TARGET_URL
          value: "http://order.mesh-test-sidecar.svc.cluster.local:8080/order"
        - name: RPS
          value: "20"
        volumeMounts:
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

Aplica la política de reintento al Service `order` (el istio-proxy de sidecar y el waypoint ya desplegado de ambient-L7 recogen ambos este VirtualService):

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar   # deploy the same into ambient-l7
spec:
  hosts:
  - order
  http:
  - route:
    - destination:
        host: order
        port:
          number: 8080
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

El procedimiento de ejecución refleja el bucle de rollout en (F), pero apunta al Deployment `order`, restablece el contador de `collector` antes de medir y consulta después el recuento de duplicados:

```bash
kubectl rollout restart deployment/collector -n "$NS"   # reset the counter

# ... same rollout-loop pattern as §F, targeting `order`, for 300s ...

CLIENT=$(kubectl get pods -n "$NS" -l app=order-client -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n "$NS" "$CLIENT" -c order-client -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://collector.$NS.svc.cluster.local:9090/dupes', timeout=5).read().decode())"
```

## Referencias

- [Ambient Mode](../advanced/01-ambient-mode.md) — arquitectura ztunnel/waypoint, comparación de recursos frente a sidecar
- [mTLS](../security/01-mtls.md) — modos STRICT/PERMISSIVE, gestión de certificados, conflictos de NetworkPolicy
- [Istio VirtualService Retry](https://istio.io/latest/docs/reference/config/networking/virtual-service/#HTTPRetry) — `attempts: 0` y condiciones de reintento
- [Envoy Retry Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/router_filter) — comportamiento de reintento y observabilidad
- [Troubleshooting: Connection Errors During Pod Termination](../troubleshooting/common-errors.md#connection-errors-during-pod-termination)
- [Sidecar Injection](../advanced/07-sidecar-injection.md)
- [Service Mesh Solution Comparison](01-service-mesh-comparison.md)
