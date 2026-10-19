# Guía de selección entre Sidecar y Ambient Mode (resultados de pruebas en EKS 1.36)

> **Versiones de prueba informadas**: Istio 1.30.2 / EKS 1.36.2 / Fortio 1.69.4
> **Fecha del informe original**: 21 de agosto de 2026 · **Revisión del contenido**: 11 de septiembre de 2026

Este documento conserva las mediciones informadas de mTLS, NetworkPolicy, latencia y despliegue gradual. No se adjuntaron los archivos completos con los datos sin procesar ni los scripts exactos de ejecución, y esta revisión no recreó los clústeres de AWS. Las comprobaciones de configuración y aritmética no constituyen una replicación independiente de estos resultados.

El apéndice ahora es una **ilustración de laboratorio revisada** que corrige defectos concretos de los scripts y la configuración. No debe describirse como la fuente exacta de las cifras históricas. Conserve el software real, los resúmenes criptográficos de las imágenes, las políticas y los artefactos junto con las nuevas mediciones; no vuelva a etiquetar estos resultados como Istio 1.31 ni como otra versión.

## Resumen de la decisión

| Requisito | Sidecar | Ambient (L4, sin waypoint) | Ambient (L7, con waypoint) | Cilium |
|---|---|---|---|---|
| mTLS | Se informó que las comprobaciones STRICT pasaron | Se informó que las comprobaciones STRICT pasaron | Se informó que las comprobaciones STRICT pasaron | No se midió; la autenticación mutua de identidades y WireGuard/IPsec habilitado por separado no equivalen a un único interruptor STRICT |
| NetworkPolicy | La regla probada para el puerto de la aplicación funcionó | El flujo probado también necesitó TCP 15008 | El flujo probado también necesitó TCP 15008 | No se midió; Cilium aplica la NetworkPolicy estándar de Kubernetes y las extensiones CiliumNetworkPolicy/de ámbito de clúster |
| P50 informado sobre la línea base |+1.29 ms|+0.04 ms|+1.86 ms|No se midió|
| Despliegue gradual sin ajustes |324 HTTP 503 + 2 errores no HTTP /60,000|0 HTTP 503 + 195 errores no HTTP /60,000|1,528 HTTP 503 + 84 errores no HTTP /59,913|No se midió|
| Despliegue gradual con medidas de robustecimiento |0 errores observados /60,000|0 errores observados /60,000|648 HTTP 503 /60,000|No se midió|

En este informe, Ambient L4 presentó una pequeña diferencia de P50 observada y menos respuestas no exitosas que Sidecar sin ajustes. Tanto Sidecar como Ambient L4 registraron cero errores en las muestras con medidas de robustecimiento. Un recuento de cero HTTP 503 no significa por sí solo que no haya habido interrupciones, y la fracción de errores observada en el waypoint no demuestra una tasa de fallos intrínseca ni prueba que la reutilización de IP haya sido la causa.

Elija primero las funciones necesarias y luego valide los errores totales, la latencia, la identidad y las operaciones frente al presupuesto de la carga de trabajo. La columna de Cilium describe únicamente las capacidades documentadas; Cilium no se implementó en este ciclo de pruebas.

## 1. mTLS: resultados de las pruebas (EKS 1.36.2, Istio 1.30.2)

El informe original menciona un clúster dedicado `mesh-isolated-test`, su propia VPC, nodos Amazon Linux 2023 arm 64 m 7g.xlarge y PeerAuthentication con ámbito de espacio de nombres en modo STRICT en los tres espacios de nombres de la malla. Se informó que las versiones de Kubernetes del plano de control y de los nodos de trabajo eran 1.36.2.

Se registró que los intentos de comunicación en texto sin cifrar a las IP de los Pod fallaron:

```text
plaintext-client -> sidecar echo pod:8080  => connection reset
plaintext-client -> ambient-L4 echo:8080  => EOF
plaintext-client -> ambient-L7 echo:8080  => EOF
```

Las llamadas registradas dentro de la malla a los Service devolvieron HTTP 200 en los tres modos. Las cabeceras de respuesta relacionadas con Envoy fueron distintas, pero la presencia o ausencia de una cabecera no prueba el cifrado ni la ruta completa del proxy.

Los comandos de certificados inspeccionaron los proxies que tenían o solicitaban certificados. Un proxy no es quien emite el certificado:

| Carga de trabajo | Proxy inspeccionado | ID SPIFFE | CA raíz |
|---|---|---|---|
| ambient-L4 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | compartida |
| ambient-L7 echo | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | compartida |
| sidecar echo | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | compartida |


Los ID que se muestran son **identidades de espacio de nombres/ServiceAccount**. Los Pod echo y cliente que utilizan la misma ServiceAccount predeterminada comparten esa identidad; no son ID SPIFFE únicos por Pod. Istiod o la CA configurada proporciona los certificados de las cargas de trabajo.

Los casos negativos y positivos informados concuerdan con la aplicación de STRICT para esos flujos. No demuestran la cobertura de todas las rutas, los protocolos, los orígenes o las vías de elusión del clúster. Ambient utiliza la ruta de captura de espacios de nombres de red de Istio CNI y HBONE por TCP 15008; el modo Sidecar utiliza el proxy de la carga de trabajo. Consulte la [guía de mTLS](../security/01-mtls.md) para conocer los límites de aplicación.

## 2. NetworkPolicy: resultados de las pruebas

El informe utilizó la aplicación de políticas de red de VPC CNI e identificó el agente como `v1.3.5-eksbuild.3`. No archiva la configuración/versión completa del complemento, los endpoints de las políticas ni pruebas del estado de los nodos. Conserve la versión informada en los resultados históricos.

**Prueba registrada del puerto de entrada, después de que el autor informara haber confirmado la aplicación de la política:**

| Modo | Resultado |
|---|---|
| sidecar | ✅ 200 OK (sin cambios) |
| ambient-L4 | ❌ bloqueado (`i/o timeout`) |
| ambient-L7 | ❌ bloqueado (`i/o timeout`) |


**Resultado registrado después de permitir 8080 y HBONE15008:**

| Modo | Resultado |
|---|---|
| ambient-L4 | ✅ 200 OK (restablecido) |
| ambient-L7 | ✅ 200 OK (restablecido) |


Estos resultados muestran la importancia de HBONE para la ruta probada. No significan que todas las políticas existentes funcionen sin cambios con Sidecar ni que permitir 15008 constituya una política Ambient completa de mínimo privilegio. Importan los selectores de origen, las rutas al waypoint, el egreso de DNS/plano de control y la implementación de CNI. La política de red ve el puerto del túnel; utilice una política adecuada de identidad/puerto para el tráfico que circula dentro del túnel.

El autor informó que recrear los Pod después de habilitar la aplicación de las políticas hizo que un control negativo surtiera efecto. Esa es una observación para la configuración informada, no una prueba de que todos los agentes actuales solo puedan asociarse durante CNI ADD o de que las políticas nunca se apliquen retroactivamente. Verifique la conciliación y la aplicación real antes de medir. La documentación actual de AWS distingue el inicio estándar, que permite el tráfico hasta que se configura la política, del inicio estricto, que necesita permisos explícitos para las dependencias necesarias.

La documentación actual de AWS admite los Pod administrados por controladores, incluidos Deployments, StatefulSets, DaemonSets y Jobs; los Pod independientes tienen limitaciones adicionales. Cilium admite por separado la NetworkPolicy estándar y sus propias CRD de políticas. No debe inferirse ninguno de esos comportamientos a partir de un resultado obtenido con otra implementación.

## 3. Latencia: resultados de las pruebas (T5)

El informe describe una prueba Fortio en estado estable, con una carga solicitada de 200 QPS durante 60 segundos y 16 conexiones, con 12,000 solicitudes exitosas por caso en el mismo clúster Graviton:

| Caso | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| sin malla (línea base) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (sin waypoint) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (con waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |


Las diferencias de P50 informadas son 1.29 ms para Sidecar, 0.04 ms para Ambient L4 y 1.86 ms para Ambient L7. Estas restas son correctas. Se necesitan datos de variación entre ejecuciones, detalles de recursos/ubicación y el JSON real de los resultados antes de calificar una diferencia pequeña como insignificante o aplicarla al presupuesto de trading/SLO.

El apéndice utiliza un comando de Fortio basado en duración. QPS solicitado × duración es el volumen de trabajo nominal ofrecido, no una garantía de recuento exacto de llamadas; utilice DurationHistogram.Count/RetCodes registrados en cada ejecución. No actualice las etiquetas históricas de versión sin volver a ejecutar el experimento y conservar sus resultados.


## 4. Despliegue gradual sin interrupciones: resultados de las pruebas 503 (hallazgo principal)

### Antecedentes

La terminación de los Pod, la propagación de endpoints, el drenaje de la aplicación/el proxy, los grupos de conexiones y los tiempos de espera pueden afectar los fallos durante el despliegue gradual. La atribución original a una condición de carrera por reutilización de la IP de destino y a la falta de una notificación de ztunnel es una **hipótesis**, no una causa demostrada por los recuentos presentados. Confírmela con las marcas de respuesta del proxy, los hosts upstream reales, las líneas de tiempo de endpoints/UID de Pod y las pruebas de conexión antes de atribuir el resultado a un único mecanismo.

El informe utilizó seis réplicas de echo y un cliente Fortio en cada espacio de nombres de la malla, con una carga solicitada de 100 QPS durante 600 segundos, y reinició repetidamente el Deployment de destino. Se pretendía que los manifiestos de la aplicación coincidieran; los recursos de proxy inyectados/compartidos y la exposición real al despliegue gradual seguían siendo distintos según el modo.

### Resultados

| Modo | Ciclos de despliegue gradual | Solicitudes | Recuento 503 | Tasa 503 | Resultados no HTTP (-1) | Sockets utilizados |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4 (sin waypoint) | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7 (con waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |


El artículo original también presentó este resumen anotado, no los artefactos completos legibles por máquina:

<details>
<summary>Recuentos registrados (anotaciones interpretativas corregidas)</summary>

```text
[sidecar]      42 rollouts, Sockets used: 350 (client concurrency: 16)
  Code 200 : 59674 (99.5 %)
  Code 503 : 324 (0.5 %)
  Code  -1 : 2   (0.0 %)

[ambient-L4]   64 rollouts, Sockets used: 1652
  Code 200 : 59805 (99.7 %)
  Code  -1 : 195 (0.3 %)   <- no HTTP response recorded; not a 503

[ambient-L7]   65 rollouts, Sockets used: 2486
  Code 200 : 58301 (97.3 %)
  Code 503 : 1528 (2.6 %)
  Code  -1 : 84  (0.1 %)
  (59,913 counted calls; nominal offered calls: 60,000; avg latency 50.4ms vs. ~2-3ms for the other two modes)

```

</details>

Interprete los valores teniendo presentes estos límites:

1. Las fracciones HTTP 503 calculadas a partir de las llamadas contabilizadas son 324/60,000 =0.54% y 1,528/59,913 ≈2.55%; la proporción entre ellas es de aproximadamente 4.72. El redondeo original de 0.5%/2.6% y la expresión «unas 5 veces» describen esta muestra, no un multiplicador intrínseco del producto.
2. Ambient L4 tuvo 195 fallos no HTTP, por lo que cero HTTP 503 no significa cero fallos. Fortio -1 abarca resultados no HTTP; para determinar la causa específica (reset/EOF/timeout) se necesitan los errores subyacentes.
3. La diferencia de 87 llamadas respecto de las 60,000 nominales no demuestra que 87 solicitudes iniciadas nunca se completaran. Una ejecución en modo de duración puede contabilizar menos llamadas. Conserve el valor informado de 59,913 y la latencia promedio de 50.4 ms sin inventar el estado de las solicitudes faltantes.
4. SocketCount de Fortio describe los sockets del cliente. No mide directamente el grupo de conexiones upstream del waypoint. Dieciséis sockets coincidirían con la concurrencia configurada del cliente si se reutilizaran de forma sostenida, pero no demuestran que todas las conexiones upstream estuvieran en buen estado.
5. Los recuentos de despliegues graduales completados en la línea base fueron 42/64/65; Ambient L7, no L4, tuvo el mayor recuento. La exposición desigual al despliegue gradual y la falta de artefactos de recursos/líneas de tiempo limitan una comparación causal.

### Seguimiento: después de reforzar el apagado gradual

El informe original aplicó a todos los modos una espera preStop de 10 segundos y un período de gracia de terminación del Pod de 40 segundos. Sidecar también recibió EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true y terminationDrainDuration 30s:

| Modo | Ciclos de despliegue gradual | Código 200 | Código 503 | Código -1 | Sockets utilizados | Latencia promedio |
|---|---|---|---|---|---|---|
| sidecar (con medidas de robustecimiento) | 42 | 60,000 (100%) | **0** | **0** | 16 | 2.630ms |
| ambient-L4 (con medidas de robustecimiento) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (con medidas de robustecimiento) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |


| Modo | Tasa de errores de la línea base | Tasa de errores con medidas de robustecimiento | Cambio |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **0 HTTP 503 observados en esta muestra** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **0 errores no HTTP observados en esta muestra** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | La tasa 503 se redujo en más de la mitad |


Estas son observaciones de las muestras indicadas. En Sidecar se cambiaron **dos factores**, por lo que el resultado no puede atribuirse únicamente a preStop. Los recuentos de despliegues graduales con medidas de robustecimiento también difieren: 42/38/45. Los ajustes del apagado de la carga de trabajo mejoraron los resultados informados, pero no demuestran que los errores restantes del waypoint compartan una única causa ni que los otros dos modos siempre vayan a tener cero errores.

El período de gracia incluye preStop y la terminación del contenedor. Una espera de diez segundos da tiempo, pero no confirma que se haya propagado la actualización de todos los endpoints. En el código publicado de la versión 1.30.2, EXIT_ON_ZERO_ACTIVE_CONNECTIONS primero espera el período mínimo de drenaje configurado y luego consulta cada segundo las estadísticas de conexiones del listener downstream. Esa rama no utiliza el temporizador habitual terminationDrainDuration; los límites de terminación de Kubernetes y los errores de observación siguen siendo relevantes. No la describa como una salida inmediata ni como un máximo incondicional de 30 segundos.

### Riesgo de usar reintentos como medida paliativa: resultados de las pruebas (T2)

El informe original describió un servicio de pedidos con seis réplicas, un colector y un cliente, con una configuración de 20 solicitudes/s, ejecuciones de 300 segundos y una política VirtualService con tres reintentos y un tiempo de espera de dos segundos por intento. Los siguientes valores se conservan como **informados, no reproducidos de forma independiente**:

| Modo | Ciclos de despliegue gradual | Solicitudes enviadas | Fallos visibles para el cliente informados | Informes duplicados (según lo informado) |
|---|---|---|---|---|
| sidecar (reintento VirtualService) | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7 (reintento en waypoint) | 12 | 7,229 | 21 (0.29%) | **0** |


El apéndice original no permite respaldar estas interpretaciones:

- Su único cliente secuencial se ejecutaba indefinidamente, nunca imprimía estadísticas y solo incrementaba el contador de envíos al tener éxito. Con un límite de 20 iteraciones/s, una ejecución de 300 segundos no puede contabilizar 9,135 ni 7,229 iteraciones; el retraso de 0.1 segundos del servidor limita aún más la tasa alcanzada.
- Un tiempo de espera de tres segundos para el cliente puede vencer antes de que terminen los intentos nominales: el original más tres intentos de dos segundos. Un fallo final no demuestra que se agotaran todos los reintentos.
- Se descartaban los errores de informe del colector, mientras el servidor de pedidos devolvía 201. El reinicio del contador coincidió con un cliente que ya se estaba ejecutando, y los manifiestos de Ambient copiados seguían apuntando a los Service del espacio de nombres de Sidecar.
- X-Request-Id es un identificador de proxy/trazado, no necesariamente un ID inmutable del comando de negocio. Un recuento de cero informes duplicados con observación incompleta no demuestra que no se haya repetido ninguna ejecución de negocio.
- Las bajas tasas de fallos finales no demuestran que se activaran los reintentos. El informe no incluyó las rutas efectivas, los contadores de reintentos ni las entregas reales.

El apéndice revisado limita y permite observar el controlador, utiliza un identificador de negocio independiente y trata los fallos del observador como un resultado desconocido/de error. No corrige la procedencia de las cifras antiguas. El colector en memoria no es un registro de transacciones duradero ni una implementación de idempotencia.

### Separar los fallos sin procesar de los fallos ocultos por los reintentos

La selección del plano de datos mTLS y la política de reintentos HTTP son decisiones independientes. Envoy de Sidecar y Envoy del waypoint pueden reintentar solicitudes HTTP en L7; ztunnel es un [proxy L4](https://istio.io/latest/docs/ambient/architecture/data-plane/) y no puede interpretar HTTP 503 ni volver a enviar una solicitud HTTP.

Para obtener una línea base justa, establezca explícitamente attempts:0 en las rutas de escritura como POST/PUT/PATCH/DELETE y mida por separado lo siguiente:

- Errores HTTP y fallos no HTTP antes de reintentar.
- Contadores Envoy upstream_rq_retry y upstream_rq_retry_success del proxy/clúster pertinente.
- Recuentos de entregas upstream/registros del observador, incluidas las solicitudes originales.
- Éxitos/fallos finales del cliente y contabilización completa del cliente.
- ID estables de comandos de negocio repetidos, fallos del observador y reinicios del observador.

| Plano de datos | Significado de mTLS/cifrado | Dónde se aplica el reintento L7 | Uso recomendado |
|---|---|---|---|
| Istio sidecar | mTLS con certificado SPIFFE de la carga de trabajo | Envoy por Pod | Línea base conservadora para rutas críticas no idempotentes |
| Istio ambient L4 | mTLS de carga de trabajo mediante HBONE entre ztunnels | Ninguno | Primer candidato cuando solo se necesitan mTLS de Istio y políticas L4 |
| Istio ambient L7 | HBONE más Envoy del waypoint | Waypoint compartido | Añadirlo solo a los Service que necesiten enrutamiento HTTP o políticas L7 |
| Cilium fuera de banda + WireGuard/IPsec | La autenticación mutua de identidades y el cifrado de transporte, como WireGuard/IPsec, se seleccionan por separado | Ninguno en la capa de cifrado L3/L4 | Planos de datos Cilium existentes que necesiten políticas de identidad y cifrado de red |


La entrada de Cilium se refiere a su capa de autenticación/cifrado L3/L4; no significa que Cilium carezca de funciones opcionales de proxy L7. Aquí no se midió su rendimiento ni su comportamiento durante el despliegue gradual.

Cilium 1.20.1 también proporciona una versión beta independiente de [cifrado transparente con ztunnel](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), seleccionada con `encryption.type: ztunnel`. Proporciona mTLS para cargas de trabajo TCP con inscripción por espacio de nombres; ambos extremos deben estar inscritos. Excluye ClusterMesh y los Pod que utilizan la red del host, y la guía publicada advierte que las políticas L4 ordinarias no funcionan en esta ruta, salvo cuando se dirigen al puerto HBONE 15008. Se trata de una opción de despliegue distinta, con sus propios requisitos de CA/inicialización.

La versión beta de ztunnel no formó parte de las mediciones presentadas en este capítulo.

> **Regla operativa:** si el único requisito es mTLS, valide primero Ambient L4 y añada waypoints solo a los Service que necesiten políticas L7 o enrutamiento HTTP este-oeste. Mantenga Sidecar como línea base para las rutas críticas no idempotentes cuando los errores totales de Ambient, medidos con los reintentos de escritura deshabilitados, superen el presupuesto de errores de la carga de trabajo. Los reintentos de la aplicación y la idempotencia siguen necesitando controles independientes.

### Nota sobre el aislamiento de las pruebas

El autor original informó de interferencias/desaparición de recursos en un clúster compartido y de un cambio del contexto actual en una estación de trabajo independiente durante un intento inicial con un clúster dedicado. No se adjunta ningún archivo forense, por lo que estos informes no identifican una causa de eliminación ni demuestran que se trate de un defecto de Istio.

El requisito útil es un aislamiento explícito: un clúster de pruebas controlado, comprobaciones del servidor/contexto/kubeconfig dedicado, un inventario completo de recursos y la conservación de los artefactos. El apéndice anterior omitía las comprobaciones del contexto mencionadas en su descripción. El procedimiento revisado las hace explícitas. Los espacios de nombres por sí solos no garantizan condiciones independientes de CPU/red o del plano de control.

## 5. Recomendación: enfoque por niveles

Los niveles de carga de trabajo son etiquetas de planificación, no garantías de seguridad:

| Requisito de la carga de trabajo | Candidato | Validación necesaria |
|---|---|---|
| Solo mTLS y políticas L4 | Empezar por Ambient L4; conservar una línea base Sidecar probada cuando corresponda | Identidad real, aplicación de NetworkPolicy/puertos internos, fallos totales y latencia |
| Enrutamiento HTTP o autorización L7 | El waypoint adecuado, el Sidecar del cliente o un gateway | Asociación correcta de la política, configuración efectiva y presupuesto de errores de la carga de trabajo |
| Comandos críticos no idempotentes | Cualquier plano de datos elegido, con una política explícita de reintentos de escritura y controles de corrección del lado del servidor | ID estables de negocio, idempotencia/transacciones duraderas, pruebas de pérdida de respuesta y recuperación |
| API de lectura, notificaciones y procesamiento por lotes | Elegir según la semántica real y las funciones necesarias | Las notificaciones y el procesamiento por lotes pueden tener efectos secundarios; incluso las lecturas seguras ante reintentos pueden amplificar la carga |

La coexistencia informada de tres espacios de nombres de malla es útil, pero no demuestra que todas las implementaciones mixtas, cargas de trabajo o combinaciones de políticas sean seguras.

### Limitaciones de L4 únicamente: ¿puedo seguir haciendo despliegues canary?

ztunnel no proporciona enrutamiento, duplicación ni reintentos HTTP por cabecera/ruta de cada solicitud HTTP. Un gateway de entrada **administrado por Istio** puede tomar decisiones de enrutamiento L7 antes de reenviar el tráfico a los backends Ambient. Gateway API es una API, no necesariamente un Deployment de Envoy: el comportamiento depende de GatewayClass/controlador.

Istio VirtualService puede seleccionar subconjuntos de DestinationRule; los backendRefs de HTTPRoute estándar normalmente seleccionan Service. No los describa como si fueran la misma API de subconjuntos.

Para el enrutamiento de solicitudes HTTP este-oeste, la decisión L7 debe tomarse en la ruta real del cliente/gateway/waypoint. Añadir un Sidecar únicamente al destino B no hace que un cliente Ambient L4 elija B-v 1/B-v 2 mediante una política HTTP de salida. Utilice el waypoint de B, un proxy adecuado en el lado del cliente u otro salto L7 diseñado explícitamente. La distribución a nivel de conexión L4 y las estrategias de despliegue gradual basadas en réplicas son distintas de la división HTTP por solicitud.

Revise los requisitos reales de funciones, el comportamiento de CNI/políticas, los reintentos de escritura y las mediciones de la propia carga de trabajo. La siguiente ilustración de laboratorio recopila nuevos datos; no puede demostrar retroactivamente los hechos que faltan en el informe original.


## Apéndice: reproducción de estas pruebas

Este es un procedimiento revisado para un seguimiento controlado, no una garantía de que al copiarlo y pegarlo se obtengan los resultados originales. Las comprobaciones locales abarcan la sintaxis, la generación de configuración y el comportamiento del cliente/observador Python. La programación en el clúster, la asociación de políticas de malla, la aplicación de CNI y la integridad de las mediciones aún deben validarse en el laboratorio real.

### A. Aprovisionamiento del clúster (eksctl)

Lo siguiente es la **entrada archivada** descrita en el informe original. Explica las opciones de nodos/red; esta auditoría no la ejecutó:

<details>
<summary>eksctl-cluster.yaml registrado</summary>

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: mesh-isolated-test
  region: ap-northeast-2
  version: '1.36'
  tags:
    purpose: istio-sidecar-vs-ambient-retest
    ephemeral: 'true'
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
    ephemeral: 'true'
addons:
- name: vpc-cni
- name: coredns
- name: kube-proxy
- name: eks-pod-identity-agent
```

</details>

La versión secundaria de Kubernetes, los complementos sin fijar y la selección actual de AMI no recrean el parche exacto del plano de control original, la imagen de los nodos ni las versiones del agente. Una disposición de prueba con subred pública/sin NAT no es una recomendación para producción; los endpoints privados, IPv 6 o el egreso basado en NAT dependen de los requisitos reales de red.

Para nuevos trabajos, utilice un clúster de pruebas aprobado y aislado, y registre su ARN/endpoint de API, las versiones de los nodos/AMI/kernel, la configuración de CNI/agente y el inventario de recursos. No active políticas que antes estaban inactivas ni sustituya CRD compartidas en un clúster ajeno.

### B. Instalación de Istio (CRD de Gateway API + perfil ambient)

Configure estos valores a partir del registro del clúster previsto. Los auxiliares seleccionan explícitamente el kubeconfig/contexto y vuelven a comprobar la asignación del servidor de API:

```bash
set -euo pipefail
: "${TEST_KUBECONFIG:?Set the dedicated kubeconfig file}"
: "${TEST_CONTEXT:?Set its explicit test context}"
: "${ISTIOCTL_BIN:?Set the path to the intended Istio 1.30.2 CLI}"
: "${EXPECTED_API_SERVER:?Set the approved API-server URL}"
: "${NS:?Select the test namespace}"
: "${RUN_DIR:?Set a new artifact directory for this run}"
case "$NS" in
  mesh-test-base|mesh-test-sidecar|mesh-test-ambient-l4|mesh-test-ambient-l7) ;;
  *) echo "Unexpected test namespace" >&2; exit 1 ;;
esac
check_mesh_context() {
  local actual
  actual=$(kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
    config view --minify -o jsonpath='{.clusters[0].cluster.server}') || return 1
  if [ "$actual" != "$EXPECTED_API_SERVER" ]; then
    echo "API-server mismatch; stopping" >&2
    return 1
  fi
}
kmesh() {
  check_mesh_context &&
    kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
imesh() {
  check_mesh_context &&
    "$ISTIOCTL_BIN" --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" "$@"
}
check_mesh_context
mkdir -p "$RUN_DIR"
```

Esto evita depender del valor del contexto actual compartido; no protege contra todos los cambios simultáneos del clúster o las credenciales. Mantenga bajo control el archivo dedicado y conserve la identidad del clúster verificada.

La versión informada fue Istio 1.30.2. La afirmación del apéndice original sobre la compatibilidad con Gateway API 1.1.0 no estaba respaldada por un archivo del paquete instalado. Las dependencias/conformidad de la versión publicada 1.30.2 usan 1.5.1. Para los casos revisados con Gateway/HTTPRoute, utilice el paquete estándar correspondiente después de comprobar los demás controladores instalados; no considere que la entrada más reciente del catálogo demuestra compatibilidad.

```bash
# Only for a new dedicated lab needing this compatible bundle.
kmesh apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
imesh manifest generate -f ambient-overlay.yaml > "$RUN_DIR/istio-rendered.yaml"
# Review the render, existing ownership and installed version before installation.
imesh install -f ambient-overlay.yaml
```

Ambient L4 por sí solo no requiere un recurso waypoint. Este experimento incluye un caso L7, por lo que se necesitan recursos compatibles de Gateway API antes de crear el waypoint. Utilice la versión prevista y adecuada de la CLI de Istio y una ruta de actualización compatible; no actualice silenciosamente una prueba histórica a una nueva versión.

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
                values:
                - arm64
    ztunnel:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - arm64
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
                  values:
                  - arm64
```

La afinidad arm 64 de CNI, ztunnel e Istiod de esta capa adicional se comprobó en una representación sin conexión, nativa de la versión 1.30.2. Una representación no es una prueba de despliegue.

### C. Manifiestos de espacio de nombres y cargas de trabajo

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

La siguiente plantilla de aplicación corresponde a un caso. Cambie todos los valores metadata.namespace por el caso seleccionado y aplíquela con `-n "$NS"` explícito para que se produzca un error si no coinciden. Mantenga equivalentes los ajustes de la aplicación, pero registre también la configuración distinta de los proxy inyectados/compartidos.

<details>
<summary>Plantilla revisada de la carga de trabajo echo y Fortio</summary>

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo
  namespace: mesh-test-sidecar
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
        kubernetes.io/os: linux
      containers:
      - name: echo
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        args:
        - server
        - -http-port
        - '8080'
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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: fortio-client
        image: fortio/fortio:1.69.4@sha256:65633fc5e70f9745be8c311637fb8e484da31a366463028a11083ac0a098e3d3
        command:
        - /usr/bin/fortio
        args:
        - server
        - -http-port
        - '8081'
        - -redirect-port
        - disabled
        resources:
          requests:
            cpu: 50m
            memory: 32Mi
          limits:
            cpu: 300m
            memory: 128Mi
```

</details>

La nueva ilustración fija la versión informada de Fortio a un resumen criptográfico del registro comprobado durante esta revisión y especifica los puertos HTTP. El informe original no archivó el resumen criptográfico de la imagen ni todos los ajustes del protocolo; estas revisiones no demuestran que la ejecución anterior utilizara los mismos bytes. La imagen de Fortio está basada en scratch: utilice su binario, no dé por sentado que incluye utilidades sh/curl/cat.

### D. mTLS: PeerAuthentication (§1)

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

Para el espacio de nombres L7:

```bash
imesh waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
kmesh -n mesh-test-ambient-l7 get gateways.gateway.networking.k8s.io -o yaml
```

Verifique la inyección/inscripción real de los Pod, los certificados y la ruta del tráfico del Service antes de generar carga. Rechazar texto sin cifrar dirigido directamente a la IP del Pod comprueba la aplicación L4; no demuestra que todas las llamadas posibles pasen por un waypoint o una política L7.

### E. NetworkPolicy (§2)

Combine la habilitación de la política de red con la configuración existente del complemento **ya revisada**, a través de su propietario:

```json
{"enableNetworkPolicy":"true"}
```

Registre la versión real de CNI/agente y el modo de inicio estándar/estricto. No sustituya a ciegas otros ajustes del complemento por una actualización de un solo campo y OVERWRITE. Compruebe los endpoints de política generados y el tráfico de control negativo después de la conciliación. Si la configuración instalada lo requiere, recree los Pod de prueba previstos; la observación histórica no es una regla universal de falta de aplicación retroactiva.

```bash
kmesh -n "$NS" get policyendpoints.networking.k8s.aws
```

Las pruebas 1 y 2 son alternativas sucesivas para la misma carga de trabajo/nombre de política seleccionados:

```yaml
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
```

```yaml
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

Aplique cada una en el espacio de nombres del caso seleccionado. Estas reglas de puertos, que no restringen el origen de forma deliberada, son un experimento de alcanzabilidad, no un aislamiento completo entre tenants. Otras políticas seleccionadas se combinan con ellas. Pruebe los requisitos reales de DNS, plano de control, origen y puerto/identidad interno, en lugar de dar por sentado que permitir un solo puerto del túnel conserva todos los límites de la política original.


### F. Prueba de despliegue gradual + 503 (T1, §4)

Para cada caso, empiece con las cargas de trabajo listas y un directorio de artefactos nuevo. El bucle limitado que se muestra a continuación registra los intervalos de despliegue gradual junto con los resultados reales de Fortio. Su inicio no es una barrera atómica con el generador de carga: utilice las marcas de tiempo para identificar el período de exposición coincidente, incluido un despliegue que termine después de que cese la carga.

```bash
# Run after loading the context helpers above. Requires GNU timeout.
DUR=600
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
kmesh -n "$NS" rollout status deployment/fortio-client --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
STOP_FILE="$RUN_DIR/stop-rollouts"
test ! -e "$STOP_FILE"
trap 'touch "$STOP_FILE"' EXIT INT TERM
(
  begin=$(date +%s)
  while [ $(( $(date +%s) - begin )) -lt "$DUR" ] && [ ! -e "$STOP_FILE" ]; do
    cycle_start=$(date +%s)
    kmesh --request-timeout=15s -n "$NS" rollout restart deployment/echo || exit 1
    kmesh --request-timeout=75s -n "$NS" rollout status deployment/echo \
      --timeout=60s || exit 1
    printf '%s,%s\n' "$cycle_start" "$(date +%s)" >> "$RUN_DIR/rollout-times.csv"
  done
) >"$RUN_DIR/rollouts.log" 2>&1 &
ROLLOUT_PID=$!

check_mesh_context
load_status=0
timeout --signal=TERM --kill-after=5s "$((DUR+30))s" \
  kubectl --kubeconfig "$TEST_KUBECONFIG" --context "$TEST_CONTEXT" \
  -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 100 -t "${DUR}s" -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio.json" 2>"$RUN_DIR/load.log" || load_status=$?
touch "$STOP_FILE"
rollout_status=0
wait "$ROLLOUT_PID" || rollout_status=$?
trap - EXIT INT TERM
if [ "$load_status" -ne 0 ] || [ "$rollout_status" -ne 0 ]; then
  echo "Invalid run: inspect load/rollout logs" >&2
  exit 1
fi
jq -e '.DurationHistogram.Count > 0 and (.RetCodes | type == "object")' \
  "$RUN_DIR/fortio.json" >/dev/null
```

Conserve el JSON de resultados, ambos registros de salida de error, los intervalos de despliegue gradual, las líneas de tiempo de Pod/endpoints y la configuración del proxy. Si se agota el tiempo o falla el despliegue gradual, la ejecución queda incompleta; no trate silenciosamente los resultados parciales como una muestra válida. `SocketCount` mide los sockets del lado del cliente de Fortio.

Para el seguimiento, combine el fragmento adecuado que aparece a continuación con el Deployment echo existente. Son **fragmentos de strategic merge**, no manifiestos Deployment independientes: el primero es el cambio común de la aplicación; el segundo también modifica los ajustes de apagado del proxy Sidecar.

```yaml
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
---
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

Repita el experimento en un directorio de ejecución nuevo y etiquete los factores que hayan cambiado. El hook de ciclo de vida sleep de kubelet se puede utilizar en la versión de Kubernetes informada; compruebe por separado la compatibilidad con esa función en los clústeres más antiguos. El período de gracia del Pod incluye preStop. Una espera no confirma que los endpoints hayan convergido, y la ruta exit-on-zero del proxy no garantiza un tiempo máximo de drenaje fijo de 30 segundos.

### G. Prueba de latencia (T5, §3)

Utilice cargas de trabajo estables, sin el bucle de despliegue gradual:

```bash
# No rollout loop for this steady-state case.
kmesh -n "$NS" rollout status deployment/echo --timeout=120s
CLIENT=$(kmesh -n "$NS" get pods -l app=fortio-client \
  -o jsonpath='{.items[0].metadata.name}')
test -n "$CLIENT"
kmesh -n "$NS" exec "$CLIENT" -c fortio-client -- \
  fortio load -qps 200 -t 60s -c 16 -allow-initial-errors \
  -json - -quiet -loglevel Error http://echo:8080/ \
  >"$RUN_DIR/fortio-latency.json" 2>"$RUN_DIR/latency.log"
jq '{Version, RequestedQPS, ActualQPS, ActualDuration,
     count: .DurationHistogram.Count, RetCodes, SocketCount}' \
  "$RUN_DIR/fortio-latency.json"
```

Informe los recuentos reales, los QPS alcanzados, los códigos de error, todos los percentiles necesarios y la variación entre ejecuciones. Solicitar 200 QPS durante 60 segundos es un ajuste de carga, no una prueba de que se hayan realizado exactamente 12,000 llamadas exitosas.

### H. Observación de ejecuciones duplicadas (T2, §4)

El siguiente harness de juguete revisado sustituye al cliente sin límite original y a los fallos silenciosos del observador. Registra un `Idempotency-Key` estable para cada comando lógico del cliente; las cabeceras de trazado de Envoy no se utilizan como identificador de negocio. Deliberadamente **no deduplica** los comandos ni implementa una transacción de negocio duradera.

Guarde el ConfigMap como t 2-configmap.yaml:

<details>
<summary>Cliente limitado, servidor de pedidos y observador en memoria</summary>

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: t2-scripts
  namespace: mesh-test-sidecar
data:
  order_server.py: |
    import http.server
    import os
    import time
    import urllib.error
    import urllib.request

    COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://collector:9090/record")


    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/order":
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            command_id = self.headers.get("Idempotency-Key", "").strip()
            if not command_id:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            time.sleep(0.1)  # Processing delay before the observer record, not a post-commit delay.
            try:
                request = urllib.request.Request(
                    COLLECTOR_URL, data=command_id.encode(), method="POST"
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    response.read()
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                # The record may have committed before an ambiguous transport failure.
                print(f"observer outcome unknown for {command_id}: {error}", flush=True)
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
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
            if self.path != "/record":
                self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
            length = int(self.headers.get("Content-Length", 0))
            rid = self.rfile.read(length).decode().strip()
            with lock:
                counts[rid] = counts.get(rid, 0) + 1
            self.send_response(200); self.send_header("Content-Length","0"); self.end_headers()

        def do_GET(self):
            with lock:
                total = len(counts)
                deliveries = sum(counts.values())
                dupes = {k: v for k, v in counts.items() if v > 1}
            if self.path == "/dupes":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes), "dupes": dupes}).encode()
            elif self.path == "/stats":
                body = json.dumps({"total_ids": total, "delivery_count": deliveries, "dupe_count": len(dupes)}).encode()
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
    import json
    import math
    import os
    import time
    import urllib.error
    import urllib.request
    import uuid


    def run():
        target = os.environ.get("TARGET_URL", "http://order:8080/order")
        rps = float(os.environ.get("RPS", "20"))
        duration = float(os.environ.get("DURATION_SECONDS", "300"))
        timeout = float(os.environ.get("TIMEOUT_SECONDS", "12"))
        if not all(math.isfinite(value) and value > 0 for value in (rps, duration, timeout)):
            raise ValueError("RPS, DURATION_SECONDS and TIMEOUT_SECONDS must be finite and positive")
        interval = 1.0 / rps
        attempted = succeeded = failed = 0
        start = time.monotonic()
        deadline = start + duration
        while time.monotonic() < deadline:
            tick = time.monotonic()
            command_id = str(uuid.uuid4())
            attempted += 1
            request = urllib.request.Request(
                target, data=b"{}", method="POST", headers={"Idempotency-Key": command_id}
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    response.read()
                    if 200 <= response.status < 300:
                        succeeded += 1
                    else:
                        failed += 1
            except urllib.error.HTTPError as error:
                error.close()
                failed += 1
            except (urllib.error.URLError, TimeoutError, OSError):
                failed += 1
            pause = min(interval - (time.monotonic() - tick), deadline - time.monotonic())
            if pause > 0:
                time.sleep(pause)
        elapsed = time.monotonic() - start
        return {
            "attempted": attempted,
            "succeeded": succeeded,
            "failed": failed,
            "requested_rps_cap": rps,
            "elapsed_seconds": elapsed,
            "achieved_rps": attempted / elapsed if elapsed else 0,
        }


    if __name__ == "__main__":
        print(json.dumps(run()), flush=True)
```

</details>

El retraso de 0.1 segundos del servidor de pedidos ocurre **antes** del registro, por lo que no es una prueba de pérdida de respuesta después de confirmar una transacción. Un timeout/error del colector devuelve 503 y deja un resultado desconocido: el observador podría haber registrado antes de que se perdiera su respuesta. En este modelo de juguete, el éxito del cliente significa que el observador confirmó la recepción; no demuestra una ejecución real de negocio exactamente una vez.

Guarde los primeros cuatro recursos siguientes como t 2-servers.yaml y el Job final como order-client-job.yaml. Para cada caso, utilice un colector nuevo, sin clientes anteriores, y cambie de forma coherente todos los valores metadata.namespace. Los nombres cortos de Service mantienen las llamadas dentro del espacio de nombres seleccionado.

<details>
<summary>Deployments, Service del colector y de pedidos, y Job limitado del cliente</summary>

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
    name: http
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: collector
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/collector.py
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 9090
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
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
    appProtocol: http
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
        kubernetes.io/os: linux
      containers:
      - name: order
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/order_server.py
        env:
        - name: COLLECTOR_URL
          value: http://collector:9090/record
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: scripts
          mountPath: /scripts
        readinessProbe:
          tcpSocket:
            port: 8080
          periodSeconds: 1
          timeoutSeconds: 1
          failureThreshold: 3
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
---
apiVersion: batch/v1
kind: Job
metadata:
  generateName: order-client-
  namespace: mesh-test-sidecar
spec:
  backoffLimit: 0
  activeDeadlineSeconds: 360
  template:
    metadata:
      labels:
        app: order-client
      annotations:
        sidecar.istio.io/nativeSidecar: 'true'
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/os: linux
        kubernetes.io/arch: arm64
      containers:
      - name: order-client
        image: python:3.12-alpine@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a
        command:
        - python3
        - /scripts/client.py
        env:
        - name: TARGET_URL
          value: http://order:8080/order
        - name: RPS
          value: '20'
        - name: DURATION_SECONDS
          value: '300'
        - name: TIMEOUT_SECONDS
          value: '12'
        volumeMounts:
        - name: scripts
          mountPath: /scripts
          readOnly: true
      volumes:
      - name: scripts
        configMap:
          name: t2-scripts
```

</details>

El Job no tiene reintentos automáticos y utiliza la anotación native-sidecar para que la inyección de Sidecar seleccionada no impida que el Job termine. Esa anotación no inscribe un Pod Ambient ni habilita por sí sola la inyección de Sidecar. Verifique el Pod Job real y la inscripción del espacio de nombres. Las plantillas revisadas añaden comprobaciones de disponibilidad TCP y fijan la imagen Python a un resumen criptográfico del registro verificado durante la revisión; el informe anterior no archivó ese resumen. El comportamiento local de Python se probó con la biblioteca estándar de Python 3.9 del host; esta revisión no ejecutó el contenedor Python 3.12 ni desplegó estos recursos.

El cliente es **secuencial**: RPS20 limita los nuevos intentos, pero no garantiza una tasa constante de 20 QPS en modo abierto. El retraso de 0.1 segundos del servicio y los fallos reducen el caudal alcanzado. DURATION_SECONDS limita el inicio de nuevas solicitudes; la última solicitud puede prolongar el tiempo transcurrido hasta su timeout. El JSON final incluye attempted/succeeded/failed y achieved_rps, con attempted = succeeded + failed.

Empiece con rutas explícitas sin reintentos para el comando de pedido **y la escritura del observador**, guardadas juntas como order-no-retry.yaml:

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 0
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: collector-observer-no-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - collector
  http:
  - name: observer-record
    match:
    - method:
        exact: POST
      uri:
        exact: /record
    route:
    - destination:
        host: collector
        port:
          number: 9090
    timeout: 10s
    retries:
      attempts: 0
```

Únicamente para un **experimento aislado de reintentos deliberadamente inseguro**, sustituya la política de pedidos por el order-retry-experiment.yaml que se muestra a continuación. Mantenga la política sin reintentos del colector. El experimento pretende revelar posibles entregas repetidas; no es una recomendación para reintentar escrituras de producción.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: order-retry
  namespace: mesh-test-sidecar
spec:
  hosts:
  - order
  http:
  - name: order-lab
    match:
    - method:
        exact: POST
      uri:
        exact: /order
    route:
    - destination:
        host: order
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 2s
      retryOn: 503,reset,connect-failure
```

Tres reintentos permiten hasta cuatro intentos. El ajuste de dos segundos por intento y el timeout de ruta de diez segundos interactúan con el tiempo de conexión/inicialización; el timeout de doce segundos del cliente proporciona una ventana de observación mayor, pero no demuestra que se hayan realizado todos los intentos. Capture la configuración real del proxy y los contadores de reintentos.

En la línea Istio 1.30 informada, el uso de VirtualService con Ambient es Alpha, y no se admite mezclarlo con la configuración de tráfico de Gateway API. No instale un HTTPRoute que compita con ella en este experimento. Compruebe las rutas efectivas en el Sidecar real del cliente o en el waypoint de destino; Ambient L4 por sí solo no puede aplicar esta política de reintentos HTTP.

```bash
# A fresh collector and no earlier client must be running for this case.
# Replace metadata.namespace in every input with NS; explicit -n catches mismatches.
kmesh -n "$NS" apply -f t2-configmap.yaml -f t2-servers.yaml -f order-no-retry.yaml
kmesh -n "$NS" rollout status deployment/collector --timeout=120s
kmesh -n "$NS" rollout status deployment/order --timeout=120s
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-before.json"

# For the deliberate retry experiment only, replace the no-retry policy with
# order-retry-experiment.yaml and verify the effective proxy configuration first.
JOB_RESOURCE=$(kmesh -n "$NS" create -f order-client-job.yaml -o name)
JOB_NAME=${JOB_RESOURCE#*/}
if ! kmesh -n "$NS" wait --for=condition=complete "$JOB_RESOURCE" --timeout=370s; then
  kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client-failed.log" || true
  echo "Invalid/incomplete client run" >&2
  exit 1
fi
kmesh -n "$NS" logs "$JOB_RESOURCE" -c order-client >"$RUN_DIR/client.json"
jq -e '.attempted > 0 and .attempted == (.succeeded + .failed)' \
  "$RUN_DIR/client.json" >/dev/null
kmesh -n "$NS" get pods -l "batch.kubernetes.io/job-name=$JOB_NAME" \
  -o json >"$RUN_DIR/client-pods.json"
kmesh -n "$NS" get pods -l app=collector -o json >"$RUN_DIR/collector-after.json"
kmesh -n "$NS" logs -l app=order -c order --prefix --tail=-1 \
  --max-log-requests=10 >"$RUN_DIR/available-order.log"
kmesh -n "$NS" exec deployment/collector -c collector -- python3 -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:9090/dupes', timeout=5).read().decode())" \
  >"$RUN_DIR/observer.json"
```

Este controlador gestiona la configuración y la contabilización; **no** inicia el bucle de despliegue gradual de pedidos. Para un experimento con cambios continuos, coordine una versión limitada por separado de §F que tenga como objetivo deployment/order durante la ventana de 300 segundos del cliente y conserve ambas líneas de tiempo. Sin esa coordinación, el resultado es una prueba del observador en estado estable.

No reinicie el observador mientras haya un cliente en ejecución. Compare los UID de los Pod del colector y los recuentos de reinicios antes y después, conserve todos los errores de pedidos/observador y utilice una retención de registros que sobreviva a la eliminación de los Pod. El comando anterior solo recupera los registros que sigan disponibles en los Pod actuales. Un reinicio del observador, la falta de registros o un error del observador invalida cualquier afirmación de detección completa de duplicados. Para investigar la seguridad real de las transacciones se necesita un registro duradero por comando y pruebas controladas de pérdida de respuesta posterior a la confirmación.

## Referencias y límites de verificación

- [Versión de Istio 1.30.2](https://github.com/istio/istio/releases/tag/1.30.2), [dependencias publicadas](https://github.com/istio/istio/blob/1.30.2/go.mod) e [implementación del apagado del proxy](https://github.com/istio/istio/blob/1.30.2/pkg/envoy/agent.go)
- [Estado de las funciones L7 de Ambient en Istio 1.30](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md) y [gestión del tráfico](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/traffic-distribution/index.md)
- [Hooks del ciclo de vida de contenedores de Kubernetes](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/) y [contenedores Sidecar nativos](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [NetworkPolicy de Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) y [modos de configuración/inicio](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Compatibilidad de Cilium con políticas](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/index.rst)
- [Código fuente y uso de Fortio 1.69.4](https://github.com/fortio/fortio/tree/v1.69.4) y [compilación del contenedor](https://github.com/fortio/fortio/blob/v1.69.4/Dockerfile)

La generación de configuración, las comprobaciones de Schema, la aritmética y las pruebas HTTP locales respaldan las correcciones concretas anteriores. No reproducen las mediciones históricas de EKS ni demuestran el rendimiento en producción, la compatibilidad con una combinación de complementos no probada o la ejecución de negocio exactamente una vez.
