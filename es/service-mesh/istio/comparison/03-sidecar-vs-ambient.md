# Guía para elegir entre sidecar y modo ambient (resultados de pruebas en EKS 1.36)

> **Versiones indicadas en las pruebas**: Istio 1.30.2 / EKS 1.36.2 / Fortio 1.69.4
> **Fecha del informe original**: 21 de agosto de 2026 · **Revisión del contenido**: 11 de septiembre de 2026

Este documento conserva las mediciones de mTLS, NetworkPolicy, latencia y despliegues recogidas en el informe original. No se adjuntaron los archivos completos de resultados ni los scripts exactos de ejecución, y esta revisión no recreó los clústeres de AWS. Comprobar la configuración y los cálculos no equivale a reproducir estos resultados de forma independiente.

El apéndice contiene ahora un **ejemplo de laboratorio revisado** que corrige defectos concretos de los scripts y la configuración. No debe presentarse como el procedimiento exacto que produjo las cifras históricas. Para cada nueva medición, conserve las versiones del software, los digests de las imágenes, las políticas y los archivos de resultados utilizados. No atribuya estos resultados a Istio 1.31 ni a otra versión.

## Resumen para la elección

| Requisito | Sidecar | Ambient (L4, sin waypoint) | Ambient (L7, con waypoint) | Cilium |
|---|---|---|---|---|
| mTLS | Las comprobaciones STRICT del informe se superaron | Las comprobaciones STRICT del informe se superaron | Las comprobaciones STRICT del informe se superaron | No medido; la autenticación mutua de identidades y el cifrado WireGuard/IPsec se habilitan por separado, no mediante un único ajuste equivalente a STRICT |
| NetworkPolicy | La regla probada para el puerto de aplicación funcionó | El flujo probado también necesitó TCP 15008 | El flujo probado también necesitó TCP 15008 | No medido; Cilium aplica NetworkPolicy estándar de Kubernetes y las extensiones CiliumNetworkPolicy y de ámbito de clúster |
| Diferencia de P50 respecto a la referencia, según el informe | +1.29 ms | +0.04 ms | +1.86 ms | No medido |
| Despliegue sin ajustes | 324 HTTP 503 + 2 errores sin respuesta HTTP / 60,000 | 0 HTTP 503 + 195 errores sin respuesta HTTP / 60,000 | 1,528 HTTP 503 + 84 errores sin respuesta HTTP / 59,913 | No medido |
| Despliegue con ajustes de cierre | 0 errores observados / 60,000 | 0 errores observados / 60,000 | 648 HTTP 503 / 60,000 | No medido |

En este informe, ambient L4 mostró una pequeña diferencia de P50 y menos resultados fallidos que sidecar sin ajustes. Tanto sidecar como ambient L4 registraron cero errores en las muestras con ajustes de cierre. Contar cero HTTP 503 no demuestra por sí solo la ausencia de interrupciones. La proporción de errores observada con waypoint tampoco establece una tasa de fallo intrínseca ni demuestra que su causa sea la reutilización de IP.

Elija primero las funciones necesarias y después contraste los errores totales, la latencia, la identidad y las operaciones con el presupuesto de la carga de trabajo. La columna Cilium describe únicamente capacidades documentadas; Cilium no se desplegó en este ciclo de pruebas.

## 1. mTLS: resultados de las pruebas (EKS 1.36.2, Istio 1.30.2)

El informe original describe un clúster dedicado `mesh-isolated-test`, con VPC propia, nodos Amazon Linux 2023 arm64 m7g.xlarge y PeerAuthentication STRICT con ámbito de namespace en los tres namespaces de la malla. Tanto el plano de control como los nodos de trabajo se indicaron como Kubernetes 1.36.2.

Los intentos registrados de conexión sin cifrar a la IP del Pod fallaron:

```text
plaintext-client -> sidecar echo pod:8080  => connection reset
plaintext-client -> ambient-L4 echo:8080  => EOF
plaintext-client -> ambient-L7 echo:8080  => EOF
```

Las llamadas registradas a Services desde dentro de la malla devolvieron HTTP 200 en los tres modos. Los encabezados de respuesta relacionados con Envoy variaron, pero su presencia o ausencia no demuestra el cifrado ni el recorrido completo por los proxies.

Los comandos de certificados inspeccionaron los proxies que conservan o solicitan certificados. Un proxy no es el emisor del certificado:

| Carga de trabajo | Proxy inspeccionado | ID SPIFFE | CA raíz |
|---|---|---|---|
| echo de ambient-L4 | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l4/sa/default` | compartida |
| echo de ambient-L7 | ztunnel | `spiffe://cluster.local/ns/mesh-test-ambient-l7/sa/default` | compartida |
| echo de sidecar | istio-proxy | `spiffe://cluster.local/ns/mesh-test-sidecar/sa/default` | compartida |


Los ID mostrados son **identidades de namespace/ServiceAccount**. Los Pods echo y cliente que usan el mismo ServiceAccount default comparten esa identidad; no son ID SPIFFE exclusivos de cada Pod. Istiod o la CA configurada proporciona los certificados de las cargas de trabajo.

Los casos fallidos y satisfactorios descritos concuerdan con la aplicación de STRICT a esos flujos. No demuestran cobertura de todas las rutas, protocolos, orígenes o mecanismos de omisión del clúster. Ambient captura el tráfico mediante Istio CNI en el namespace de red y usa HBONE sobre TCP 15008; el modo sidecar usa el proxy de la carga de trabajo. Consulte los límites de aplicación en la [guía de mTLS](../security/01-mtls.md).

## 2. NetworkPolicy: resultados de las pruebas

El informe utilizó la aplicación de políticas de red de VPC CNI e identificó al agente como `v1.3.5-eksbuild.3`. No conserva la configuración y versión completas del complemento, los endpoints de política ni pruebas del estado de los nodos. Mantenga la versión indicada al presentar resultados históricos.

**Prueba registrada del puerto de entrada, después de que el autor indicara haber confirmado la aplicación de la política:**

| Modo | Resultado |
|---|---|
| sidecar | ✅ 200 OK (sin cambios) |
| ambient-L4 | ❌ bloqueado (`i/o timeout`) |
| ambient-L7 | ❌ bloqueado (`i/o timeout`) |


**Resultado registrado después de permitir 8080 y HBONE 15008:**

| Modo | Resultado |
|---|---|
| ambient-L4 | ✅ 200 OK (restablecido) |
| ambient-L7 | ✅ 200 OK (restablecido) |


Estos resultados muestran la importancia de HBONE en la ruta probada. No significan que todas las políticas existentes funcionen sin cambios con sidecars ni que permitir 15008 constituya una política completa de mínimo privilegio para ambient. Importan los selectores de origen, las rutas por waypoint, las salidas hacia DNS y el plano de control y la implementación del CNI. La política de red observa el puerto del túnel; aplique políticas adecuadas de identidad y puerto al tráfico que circula dentro de él.

El autor indicó que recrear los Pods después de habilitar la aplicación de políticas hizo efectivo un control negativo. Es una observación de esa configuración, no una prueba de que todos los agentes actuales solo puedan conectarse durante CNI ADD o de que las políticas nunca se apliquen retroactivamente. Antes de medir, verifique la reconciliación y la aplicación efectiva. La documentación actual de AWS distingue el arranque estándar, que permite tráfico hasta configurar la política, del arranque estricto, que requiere permisos explícitos para las dependencias necesarias.

La documentación actual de AWS admite Pods gestionados por controladores, incluidos Deployments, StatefulSets, DaemonSets y Jobs; los Pods independientes tienen limitaciones adicionales. Cilium admite por separado NetworkPolicy estándar y sus propios CRD de políticas. No deduzca el comportamiento de una implementación a partir de resultados obtenidos en otra.

## 3. Latencia: resultados de las pruebas (T5)

El informe describe una prueba de Fortio en estado estable, con una carga solicitada de 200 QPS durante 60 segundos y 16 conexiones, que registró 12,000 solicitudes satisfactorias por caso en el mismo clúster Graviton:

| Caso | P50 | P75 | P90 | P99 | P99.9 |
|---|---|---|---|---|---|
| no-mesh (referencia) | 0.82ms | 1.33ms | 1.73ms | 1.97ms | 2.00ms |
| sidecar | 2.11ms | 2.60ms | 2.89ms | 3.91ms | 8.00ms |
| ambient-L4 (sin waypoint) | 0.86ms | 1.34ms | 1.74ms | 1.98ms | 2.93ms |
| ambient-L7 (con waypoint) | 2.68ms | 3.06ms | 3.63ms | 3.98ms | 7.67ms |


Las diferencias de P50 indicadas son 1.29 ms para sidecar, 0.04 ms para ambient L4 y 1.86 ms para ambient L7. Estas restas son correctas. Antes de considerar insignificante una pequeña diferencia o aplicarla al presupuesto de una operación financiera o un SLO, se necesitan la variación entre ejecuciones, los detalles de recursos y ubicación y los JSON reales de resultados.

El apéndice usa un comando Fortio basado en duración. Los QPS solicitados multiplicados por la duración expresan la carga nominal ofrecida; no garantizan un número exacto de llamadas. Use los valores DurationHistogram.Count/RetCodes registrados en cada ejecución. No cambie las etiquetas de versiones históricas sin repetir y conservar el experimento.


## 4. Despliegues sin interrupciones: resultados de las pruebas de 503 (hallazgo principal)

### Antecedentes

La terminación de Pods, la propagación de endpoints, el cierre gradual de aplicaciones y proxies, los pools de conexiones y los tiempos de espera pueden influir en los fallos durante un despliegue. La atribución original a una condición de carrera por reutilización de la IP de destino y a la falta de notificación de ztunnel es una **hipótesis**, no una causa demostrada por los recuentos. Antes de atribuir el resultado a un mecanismo, contraste los indicadores de respuesta del proxy, los destinos upstream reales, las cronologías de endpoints y UID de Pods y las pruebas de conexiones.

El informe utilizó seis réplicas de echo y un cliente Fortio en cada namespace de la malla, solicitó 100 QPS durante 600 segundos y reinició repetidamente el Deployment de destino. Se pretendía que los manifiestos de aplicación coincidieran, pero los recursos de proxy inyectados o compartidos y la exposición efectiva a los despliegues variaron entre modos.

### Resultados

| Modo | Ciclos de despliegue | Solicitudes | Cantidad de 503 | Tasa de 503 | Resultados sin respuesta HTTP (-1) | Sockets utilizados |
|---|---|---|---|---|---|---|
| sidecar | 42 | 60,000 | 324 | **0.5%** | 2 (0.0%) | 350 |
| ambient-L4 (sin waypoint) | 64 | 60,000 | **0** | **0%** | 195 (0.3%) | 1,652 |
| ambient-L7 (con waypoint) | 65 | 59,913 | 1,528 | **2.6%** | 84 (0.1%) | 2,486 |


El artículo original también incluía este resumen anotado, pero no los archivos completos en formato procesable:

<details>
<summary>Recuentos registrados (con las anotaciones interpretativas corregidas)</summary>

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

Interprete los valores teniendo en cuenta estos límites:

1. Las proporciones de HTTP 503 calculadas a partir de las llamadas contadas son 324/60,000 = 0.54% y 1,528/59,913 ≈ 2.55%; su relación es aproximadamente 4.72. Los valores originales redondeados de 0.5%/2.6% y «unas 5 veces» describen esta muestra, no un multiplicador intrínseco del producto.
2. Ambient L4 registró 195 fallos sin respuesta HTTP, por lo que cero HTTP 503 no equivale a cero fallos. Fortio -1 agrupa resultados sin respuesta HTTP; para distinguir resets, EOF o tiempos de espera se necesitan los errores subyacentes.
3. La diferencia de 87 llamadas respecto a las 60,000 nominales no demuestra que 87 solicitudes iniciadas quedaran sin completar. Una ejecución basada en tiempo puede contar menos llamadas. Conserve las 59,913 llamadas y la media de 50.4 ms indicadas sin inventar estados de solicitudes perdidas.
4. SocketCount de Fortio describe sockets del cliente. No mide directamente el pool upstream del waypoint. Dieciséis sockets corresponderían a la concurrencia configurada del cliente con reutilización sostenida, pero no demostrarían que todas las conexiones upstream funcionaran correctamente.
5. Los despliegues completados en la referencia fueron 42/64/65; ambient L7, no L4, tuvo el mayor recuento. La exposición desigual a los despliegues y la falta de archivos de recursos y cronologías limitan la comparación causal.

### Seguimiento: después de ajustar el cierre ordenado

El informe original aplicó un preStop de 10 segundos y un período de gracia de terminación de Pod de 40 segundos a todos los modos. Sidecar también recibió EXIT_ON_ZERO_ACTIVE_CONNECTIONS=true y terminationDrainDuration 30s:

| Modo | Ciclos de despliegue | Code 200 | Code 503 | Code -1 | Sockets utilizados | Latencia media |
|---|---|---|---|---|---|---|
| sidecar (con ajustes) | 42 | 60,000 (100%) | **0** | **0** | 16 | 2.630ms |
| ambient-L4 (con ajustes) | 38 | 60,000 (100%) | **0** | **0** | 395 | 1.189ms |
| ambient-L7 (con ajustes) | 45 | 59,352 (98.9%) | 648 (1.1%) | **0** | 678 | 3.843ms |


| Modo | Tasa de error de referencia | Tasa de error con ajustes | Cambio |
|---|---|---|---|
| sidecar | 0.5% 503 + 0% TCP | 0% 503 + 0% TCP | **0 respuestas 503 observadas en esta muestra** |
| ambient-L4 | 0% 503 + 0.3% TCP | 0% 503 + 0% TCP | **0 errores sin respuesta HTTP observados en esta muestra** |
| ambient-L7 | 2.6% 503 + 0.1% TCP | 1.1% 503 + 0% TCP | La tasa de 503 se redujo en más de la mitad |


Son observaciones de las muestras indicadas. En sidecar se cambiaron **dos factores**, por lo que el resultado no puede atribuirse únicamente a preStop. Los recuentos de despliegues con ajustes, 42/38/45, también difieren. Ajustar el cierre de la carga de trabajo mejoró los resultados registrados, pero no demuestra que los errores restantes del waypoint tengan una sola causa ni que los otros dos modos siempre registren cero errores.

El período de gracia incluye preStop y la terminación del contenedor. Una espera de diez segundos da margen, pero no confirma que todas las actualizaciones de endpoints se hayan propagado. En el código publicado de 1.30.2, EXIT_ON_ZERO_ACTIVE_CONNECTIONS primero espera el período mínimo de drenaje configurado y después consulta cada segundo las estadísticas de conexiones de los listeners downstream. Esa rama no utiliza el temporizador ordinario de terminationDrainDuration; los límites de terminación de Kubernetes y los errores de observación siguen siendo relevantes. No lo describa como una salida inmediata ni como un máximo incondicional de 30 segundos.

### Riesgo de usar reintentos como mitigación: resultados de las pruebas (T2)

El informe original describía un servicio order con seis réplicas, un collector y un cliente, una configuración de 20 solicitudes/s, ejecuciones de 300 segundos y una política de VirtualService con tres reintentos y dos segundos de tiempo de espera por intento. Se conservan los siguientes valores como **resultados del informe, no reproducidos de forma independiente**:

| Modo | Ciclos de despliegue | Solicitudes enviadas | Fallos visibles para el cliente según el informe | Registros duplicados según el informe |
|---|---|---|---|---|
| sidecar (reintentos con VirtualService) | 11 | 9,135 | 15 (0.16%) | **0** |
| ambient-L7 (reintentos con waypoint) | 12 | 7,229 | 21 (0.29%) | **0** |


El apéndice original no permite respaldar estas interpretaciones:

- Su único cliente secuencial se ejecutaba indefinidamente, no imprimía estadísticas y solo incrementaba sent cuando había éxito. Con un límite de 20 iteraciones/s, una ejecución de 300 segundos no puede explicar 9,135 ni 7,229 iteraciones; el retraso de 0.1 segundos del servidor reduce aún más la tasa alcanzable.
- Un tiempo de espera del cliente de tres segundos puede agotarse antes de completar el intento original más tres reintentos de dos segundos cada uno. Un fallo final no demuestra que se agotaran todos los reintentos.
- Los errores al informar a collector se ignoraban mientras el servidor order devolvía 201. El contador se reiniciaba con un cliente ya en ejecución y los manifiestos copiados de ambient seguían apuntando a los servicios del namespace de sidecar.
- X-Request-Id es un identificador de proxy o trazabilidad, no necesariamente un ID inmutable de comando de negocio. Un recuento cero de registros duplicados con observación incompleta no demuestra que ninguna operación de negocio se ejecutara varias veces.
- Las bajas tasas de fallo final no demuestran que se ejecutaran reintentos. El informe no incluía rutas efectivas, contadores de reintentos ni entregas reales.

El apéndice revisado limita la ejecución del cliente y permite observarla, usa un identificador de negocio independiente y trata el fallo del observador como un resultado desconocido o erróneo. No subsana la procedencia de las cifras antiguas. Su collector en memoria no es un registro transaccional duradero ni una implementación de idempotencia.

### Separar los fallos originales de los ocultos por reintentos

La elección del plano de datos mTLS y la política de reintentos HTTP son decisiones independientes. Envoy en sidecar y en waypoint puede reintentar solicitudes HTTP en L7; ztunnel es un [proxy L4](https://istio.io/latest/docs/ambient/architecture/data-plane/) y no puede interpretar HTTP 503 ni repetir una solicitud HTTP.

Para obtener una referencia comparable, establezca explícitamente attempts:0 en las rutas de escritura, como POST/PUT/PATCH/DELETE, y mida por separado:

- Errores HTTP y fallos sin respuesta HTTP antes del reintento.
- Contadores Envoy upstream_rq_retry y upstream_rq_retry_success del proxy y clúster que intervienen realmente.
- Recuentos de entregas upstream y registros del observador, incluidas las solicitudes originales.
- Éxitos y fallos finales del cliente y su contabilidad completa.
- Repeticiones de ID estables de comandos de negocio, fallos del observador y reinicios del observador.

| Plano de datos | Significado de mTLS/cifrado | Ubicación del reintento L7 | Uso recomendado |
|---|---|---|---|
| Istio sidecar | mTLS con certificados SPIFFE de la carga de trabajo | Envoy por Pod | Referencia conservadora para rutas críticas no idempotentes |
| Istio ambient L4 | mTLS de cargas de trabajo mediante HBONE entre ztunnels | Ninguna | Primer candidato cuando solo se requieren mTLS de Istio y políticas L4 |
| Istio ambient L7 | HBONE y Envoy en waypoint | Waypoint compartido | Añadir únicamente a servicios que necesitan enrutamiento HTTP o políticas L7 |
| Cilium fuera de banda + WireGuard/IPsec | La autenticación mutua de identidades y el cifrado de transporte, como WireGuard/IPsec, se eligen por separado | Ninguna en la capa de cifrado L3/L4 | Planos de datos Cilium existentes que necesitan políticas de identidad y cifrado de red |


La fila Cilium se refiere a su capa de autenticación y cifrado L3/L4; no significa que Cilium carezca de funciones opcionales de proxy L7. Aquí no se midieron su rendimiento ni su comportamiento durante despliegues.

Cilium 1.20.1 también ofrece una [versión beta de cifrado transparente con ztunnel](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/network/encryption-ztunnel.rst), que se selecciona por separado con `encryption.type: ztunnel`. Proporciona mTLS TCP de cargas de trabajo mediante la inscripción de namespaces; ambos extremos deben estar inscritos. Excluye ClusterMesh y los Pods que usan la red del host. La guía publicada advierte que las políticas L4 ordinarias no funcionan en esta ruta salvo si se dirigen al puerto HBONE 15008. Es una alternativa de despliegue distinta, con sus propios requisitos de CA e inicialización.

La versión beta de ztunnel no formó parte de las mediciones presentadas en este capítulo.

> **Regla operativa:** si mTLS es el único requisito, valide primero ambient L4 y añada waypoints solo a los servicios que necesitan políticas L7 o enrutamiento HTTP este-oeste. Mantenga sidecar como referencia para rutas críticas no idempotentes si los errores totales de ambient, medidos con los reintentos de escritura deshabilitados, superan el presupuesto de errores de la carga de trabajo. Los reintentos y la idempotencia de la aplicación también requieren controles independientes.

### Nota sobre el aislamiento de las pruebas

El autor original informó de interferencias y desaparición de recursos en un clúster compartido, y de un cambio de current-context en una estación de trabajo durante un primer intento con un clúster dedicado. No se adjunta un archivo de investigación, por lo que estos informes no identifican la causa de la eliminación ni establecen un defecto de Istio.

El requisito útil es un aislamiento explícito: un clúster de pruebas controlado, comprobaciones de kubeconfig, contexto y servidor dedicados, un inventario completo de recursos y conservación de los archivos de resultados. El apéndice anterior omitía las comprobaciones de contexto descritas en el relato; el procedimiento revisado las incluye. Los namespaces, por sí solos, no garantizan condiciones independientes de CPU, red o plano de control.

## 5. Recomendación: enfoque por niveles

Los niveles de carga de trabajo sirven para planificar; no garantizan seguridad:

| Requisito de la carga de trabajo | Candidato | Validación necesaria |
|---|---|---|
| Solo mTLS y políticas L4 | Probar primero ambient L4; conservar una referencia sidecar validada cuando corresponda | Identidad real, aplicación de NetworkPolicy y puertos internos, fallos totales y latencia |
| Enrutamiento HTTP o autorización L7 | Waypoint, sidecar del emisor o gateway adecuados | Vinculación correcta de políticas, configuración efectiva y presupuesto de errores de la carga de trabajo |
| Comandos críticos no idempotentes | Cualquier plano de datos elegido con política explícita de reintentos de escritura y controles de corrección en el servidor | ID de negocio estables, idempotencia y transacciones duraderas, pruebas de pérdida de respuesta y recuperación |
| API de lectura, notificaciones y procesamiento por lotes | Elegir según la semántica real y las funciones necesarias | Las notificaciones y los lotes pueden tener efectos secundarios; incluso las lecturas que admiten reintentos pueden amplificar la carga |

La coexistencia de los tres namespaces de la malla descrita en el informe es útil, pero no demuestra que todas las combinaciones de despliegues, cargas de trabajo y políticas sean seguras.

### Limitaciones de L4: ¿se pueden hacer despliegues canary?

ztunnel no proporciona enrutamiento por encabezado o ruta de cada solicitud HTTP, duplicación de tráfico ni reintentos HTTP. Un gateway de entrada **gestionado por Istio** puede tomar decisiones de enrutamiento L7 antes de enviar el tráfico a backends ambient. Gateway API es una API, no necesariamente un Deployment de Envoy: el comportamiento depende de GatewayClass y del controlador.

VirtualService de Istio puede seleccionar subconjuntos de DestinationRule; los backendRefs de HTTPRoute estándar suelen seleccionar Services. No los describa como una misma API de subconjuntos.

Para enrutar solicitudes HTTP este-oeste, la decisión L7 debe producirse en la ruta real del emisor, gateway o waypoint. Añadir únicamente un sidecar al destino B no hace que un emisor ambient L4 elija entre B-v1 y B-v2 mediante una política HTTP de salida. Use el waypoint de B, un proxy adecuado del lado del emisor u otro salto L7 diseñado explícitamente. La distribución L4 por conexión y los despliegues basados en réplicas difieren del reparto HTTP por solicitud.

Revise las funciones necesarias, el comportamiento del CNI y las políticas, los reintentos de escritura y las mediciones de su propia carga de trabajo. El siguiente ejemplo de laboratorio recoge nuevas pruebas; no puede establecer retroactivamente los datos que faltan en el informe original.


## Apéndice: reproducción de las pruebas

Es un procedimiento revisado para una prueba posterior controlada, no una garantía de reproducir los resultados originales al copiarlo. Las comprobaciones locales abarcan sintaxis, generación de configuración y comportamiento del observador y cliente Python. La planificación en el clúster, la vinculación de políticas de malla, la aplicación del CNI y la integridad de las mediciones aún deben validarse en el laboratorio real.

### A. Aprovisionamiento del clúster (eksctl)

La siguiente es la **configuración archivada** descrita en el informe original. Explica las elecciones de nodos y red; esta revisión no la ejecutó:

<details>
<summary>eksctl-cluster.yaml registrado en el informe</summary>

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

Indicar solo la versión menor de Kubernetes, usar complementos sin versión fijada y seleccionar una AMI actual no recrea exactamente el parche original del plano de control ni las versiones de imagen de nodo y agente. Un laboratorio con subredes públicas y sin NAT no constituye una recomendación para producción. El uso de endpoints privados, IPv6 o salidas mediante NAT depende de los requisitos reales de red.

Para las nuevas pruebas, use un clúster de laboratorio autorizado y aislado. Registre su ARN y endpoint de API, las versiones de nodos, AMI y kernel, la configuración de CNI y agentes y el inventario de recursos. No active políticas antes inactivas ni sustituya CRD compartidos en otro clúster.

### B. Instalación de Istio (CRD de Gateway API y perfil ambient)

Obtenga estos valores del registro del clúster que pretende usar. Las funciones auxiliares seleccionan explícitamente kubeconfig y contexto y vuelven a comprobar su asociación con el servidor de API:

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

Esto evita depender del valor compartido de current-context; no protege contra todos los cambios concurrentes de clúster o credenciales. Controle el archivo dedicado y conserve la identidad verificada del clúster.

La versión indicada fue Istio 1.30.2. La afirmación de compatibilidad con Gateway API 1.1.0 del apéndice original no estaba respaldada por un archivo del paquete instalado. Las dependencias y pruebas de conformidad publicadas de 1.30.2 utilizan 1.5.1. Para los casos revisados de Gateway/HTTPRoute, use el paquete estándar correspondiente tras comprobar los demás controladores instalados. La última entrada de un catálogo no demuestra compatibilidad.

```bash
# Only for a new dedicated lab needing this compatible bundle.
kmesh apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.5.1/standard-install.yaml
imesh manifest generate -f ambient-overlay.yaml > "$RUN_DIR/istio-rendered.yaml"
# Review the render, existing ownership and installed version before installation.
imesh install -f ambient-overlay.yaml
```

Ambient L4 por sí solo no requiere un recurso waypoint. Este experimento incluye un caso L7, por lo que necesita recursos Gateway API compatibles antes de crear el waypoint. Use la CLI y versión de Istio previstas y una ruta de actualización admitida; no actualice silenciosamente una prueba histórica a otra versión.

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

La afinidad arm64 para CNI, ztunnel e Istiod de este overlay se comprobó mediante renderizado sin conexión de la versión nativa 1.30.2. Renderizar una configuración no prueba su despliegue.

### C. Manifiestos de namespaces y cargas de trabajo

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

La siguiente plantilla de aplicación corresponde a un caso. Cambie todos los campos metadata.namespace al caso seleccionado y aplíquela con `-n "$NS"` explícito, para que una discrepancia produzca un error. Mantenga equivalentes los ajustes de aplicación y registre también las diferencias de configuración de los proxies inyectados o compartidos.

<details>
<summary>Plantilla revisada de cargas de trabajo echo y Fortio</summary>

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

El nuevo ejemplo fija la versión indicada de Fortio a un digest del registro comprobado durante esta revisión y nombra explícitamente los puertos HTTP. El informe original no conservaba su digest de imagen ni todos los ajustes de protocolo; estos cambios no demuestran que la ejecución antigua usara los mismos bytes. La imagen de Fortio se basa en scratch: use su binario, sin suponer que contiene sh, curl o cat.

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

Para el namespace L7:

```bash
imesh waypoint apply -n mesh-test-ambient-l7 --enroll-namespace --wait
kmesh -n mesh-test-ambient-l7 get gateways.gateway.networking.k8s.io -o yaml
```

Antes de aplicar carga, compruebe la inyección o inscripción real de los Pods, los certificados y la ruta de tráfico del Service. Rechazar una conexión sin cifrar directa a la IP del Pod comprueba la aplicación L4; no demuestra que todas las llamadas posibles atraviesen un waypoint o una política L7.

### E. NetworkPolicy (§2)

Integre la habilitación de políticas de red en la configuración existente del complemento, **previamente revisada**, mediante la herramienta que la gestiona:

```json
{"enableNetworkPolicy":"true"}
```

Registre las versiones reales de CNI y agente y el modo de arranque estándar o estricto. No sustituya a ciegas otros ajustes del complemento mediante una actualización de un solo campo y OVERWRITE. Compruebe los endpoints de política generados y el tráfico del control negativo después de la reconciliación. Recree los Pods de prueba previstos si la configuración instalada lo requiere; la observación histórica no es una regla universal de ausencia de retroactividad.

```bash
kmesh -n "$NS" get policyendpoints.networking.k8s.aws
```

La Prueba 1 y la Prueba 2 son alternativas sucesivas para la misma carga de trabajo seleccionada y el mismo nombre de política:

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

Aplique cada política en el namespace del caso seleccionado. Estas reglas de puerto sin restricciones de origen son deliberadamente un experimento de conectividad, no un aislamiento completo de tenants. Las demás políticas seleccionadas se combinan con ellas. Pruebe los requisitos reales de DNS, plano de control, origen y puertos internos o identidad; permitir un puerto de túnel no garantiza conservar todos los límites de las políticas originales.


### F. Prueba de despliegue y 503 (T1, §4)

Para cada caso, comience con las cargas de trabajo listas y un directorio nuevo de resultados. El bucle limitado siguiente registra los intervalos de despliegue junto con los resultados reales de Fortio. Su inicio no constituye una barrera atómica con el generador de carga: use las marcas de tiempo para identificar la exposición coincidente, incluido cualquier despliegue que termine después de que cese la carga.

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

Conserve el JSON de resultados, ambos registros stderr, los intervalos de despliegue, las cronologías de Pods y endpoints y la configuración de proxy. Un tiempo de espera agotado o un despliegue fallido deja incompleta la ejecución; no considere silenciosamente un resultado parcial como una muestra válida. `SocketCount` mide los sockets del lado cliente de Fortio.

Para la prueba posterior, integre el fragmento correspondiente en el Deployment echo existente. Son **fragmentos de fusión estratégica**, no manifiestos Deployment completos: el primero contiene el cambio común de aplicación y el segundo modifica también el cierre del proxy sidecar.

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

Repita el experimento con un directorio nuevo e identifique los factores modificados. El hook de ciclo de vida sleep del kubelet se puede usar en la versión indicada de Kubernetes; compruebe por separado la compatibilidad en clústeres antiguos. El período de gracia del Pod incluye preStop. Una espera no confirma la convergencia de endpoints, y la salida del proxy al llegar a cero conexiones no garantiza un máximo fijo de drenaje de 30 segundos.

### G. Prueba de latencia (T5, §3)

Use cargas de trabajo estables sin el bucle de despliegue:

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

Informe de los recuentos reales, QPS alcanzados, códigos de error, todos los percentiles necesarios y la variación entre ejecuciones. Solicitar 200 QPS durante 60 segundos es un ajuste de carga, no una prueba de haber completado exactamente 12,000 llamadas satisfactorias.

### H. Observación de ejecuciones duplicadas (T2, §4)

El siguiente entorno de prueba revisado sustituye al cliente original sin límite de ejecución y a los fallos silenciosos del observador. Registra un `Idempotency-Key` estable para cada comando lógico del cliente; no utiliza encabezados de trazabilidad de Envoy como identificador de negocio. Deliberadamente, **no elimina duplicados** ni implementa una transacción de negocio duradera.

Guarde el ConfigMap como t2-configmap.yaml:

<details>
<summary>Cliente con ejecución limitada, servidor order y observador en memoria</summary>

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

El retraso de 0.1 segundos del servidor order ocurre **antes** del registro, por lo que no comprueba la pérdida de respuesta posterior a una transacción confirmada. Un error o tiempo de espera agotado del collector devuelve 503 y deja un resultado desconocido: el observador podría haber registrado la operación antes de perder su respuesta. El éxito del cliente significa que el observador confirmó el registro en este ejemplo, no demuestra una ejecución real de negocio exactamente una vez.

Guarde los primeros cuatro recursos siguientes como t2-servers.yaml y el Job final como order-client-job.yaml. Use un collector nuevo, sin clientes anteriores, para cada caso y cambie coherentemente todos los campos metadata.namespace. Los nombres cortos de Service mantienen las llamadas dentro del namespace seleccionado.

<details>
<summary>Deployments y Services de collector/order y Job de cliente con ejecución limitada</summary>

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

El Job no reintenta automáticamente y usa la anotación de sidecar nativo para que una inyección de sidecar seleccionada no impida su finalización. Esa anotación no inscribe un Pod ambient ni habilita por sí sola la inyección de sidecar. Verifique el Pod real del Job y la inscripción del namespace. Las plantillas revisadas añaden comprobaciones TCP de preparación y fijan la imagen Python a un digest del registro verificado durante la revisión; el informe antiguo no conservó ese digest. El comportamiento local de Python se probó con la biblioteca estándar de Python 3.9 del host. Esta revisión no ejecutó el contenedor Python 3.12 ni desplegó estos recursos.

El cliente es **secuencial**: RPS20 limita los nuevos intentos; no garantiza una carga constante de bucle abierto de 20 QPS. El retraso de 0.1 segundos del servicio y los fallos reducen el rendimiento alcanzado. DURATION_SECONDS limita el inicio de nuevas solicitudes; la última puede prolongar la ejecución hasta su tiempo de espera. El JSON final incluye attempted/succeeded/failed y achieved_rps, con attempted = succeeded + failed.

Comience con rutas explícitas sin reintentos tanto para el comando order **como para la escritura del observador**; guárdelas juntas en order-no-retry.yaml:

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

Solo para un **experimento aislado con reintentos deliberadamente inseguros**, sustituya la política de order por order-retry-experiment.yaml, que se muestra a continuación. Mantenga la política sin reintentos de collector. El experimento pretende revelar posibles entregas repetidas; no recomienda reintentar escrituras en producción.

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

Tres reintentos permiten hasta cuatro intentos. El tiempo de espera de dos segundos por intento y el de diez segundos de la ruta interactúan con el tiempo de conexión e inicialización. El tiempo de espera de doce segundos del cliente amplía la ventana de observación, pero no demuestra que se realizaran todos los intentos. Capture la configuración real del proxy y los contadores de reintentos.

En la línea Istio 1.30 indicada, el uso de VirtualService con ambient es Alpha y no se admite combinarlo con la configuración de tráfico de Gateway API. No instale un HTTPRoute que compita en este experimento. Compruebe las rutas efectivas en el sidecar real del cliente o en el waypoint de destino; ambient L4 por sí solo no puede aplicar esta política de reintentos HTTP.

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

Este procedimiento prepara los recursos y contabiliza los resultados; **no** inicia el bucle de despliegue de order. Para un experimento con reemplazos continuos, coordine una variante limitada de §F que apunte a deployment/order durante la ventana de 300 segundos del cliente y conserve ambas cronologías. Sin esa coordinación, el resultado es una prueba del observador en estado estable.

No reinicie el observador mientras se ejecuta un cliente. Compare los UID de Pods y los recuentos de reinicios de collector antes y después, conserve todos los errores de order y del observador y use retención de registros que sobreviva a la eliminación de Pods. El comando anterior solo recupera registros todavía disponibles en los Pods actuales. Un reinicio del observador, registros ausentes o un error del observador impiden afirmar una detección completa de duplicados. Para investigar la seguridad transaccional real se necesitan un registro duradero por comando y pruebas controladas de pérdida de respuesta después de confirmar la operación.

## Referencias y límites de la verificación

- [Versión Istio 1.30.2](https://github.com/istio/istio/releases/tag/1.30.2), [dependencias publicadas](https://github.com/istio/istio/blob/1.30.2/go.mod) e [implementación del cierre del proxy](https://github.com/istio/istio/blob/1.30.2/pkg/envoy/agent.go)
- [Estado de funciones L7 de ambient en Istio 1.30](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/l7-features/index.md) y [gestión de tráfico](https://github.com/istio/istio.io/blob/release-1.30/content/en/docs/ambient/usage/traffic-distribution/index.md)
- [Hooks de ciclo de vida de contenedores Kubernetes](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/) y [contenedores sidecar nativos](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/)
- [NetworkPolicy en Amazon EKS](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) y [configuración y modos de arranque](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html)
- [Compatibilidad de políticas de Cilium](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/policy/index.rst)
- [Código y uso de Fortio 1.69.4](https://github.com/fortio/fortio/tree/v1.69.4) y [compilación del contenedor](https://github.com/fortio/fortio/blob/v1.69.4/Dockerfile)

La generación de configuración, las comprobaciones de esquema, los cálculos y las pruebas HTTP locales respaldan las correcciones concretas anteriores. No reproducen las mediciones históricas de EKS ni establecen rendimiento en producción, compatibilidad con combinaciones de complementos no probadas o ejecución de operaciones de negocio exactamente una vez.
