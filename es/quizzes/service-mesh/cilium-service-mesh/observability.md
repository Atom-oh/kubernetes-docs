# Cuestionario de observabilidad de Cilium Service Mesh

Revisado con Cilium 1.20.3 y Hubble CLI 1.20.2. Consulta la [guía de observabilidad](../../../service-mesh/cilium-service-mesh/04-observability.md) para ver los comandos probados, las definiciones de métricas y sus limitaciones.

### 1. ¿Cuál no es un componente principal de Hubble?

- **A.** Hubble Observer
- **B.** Hubble Relay
- **C.** Hubble Router
- **D.** Hubble UI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Hubble Router**

Observer, Relay, UI y CLI son los componentes pertinentes de Hubble. Observer y el procesamiento de métricas están integrados en Cilium; Relay agrega servidores conectados. Hubble Router no es un componente con nombre en esta arquitectura.

</details>

### 2. ¿Qué comando de Hubble CLI filtra las observaciones existentes para mostrar solo el tráfico HTTP?

- **A.** `hubble observe --type http`
- **B.** `hubble observe --protocol http`
- **C.** `hubble observe --filter http`
- **D.** `hubble observe --layer http`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `hubble observe --protocol http`**

Esto filtra observaciones HTTP existentes. No habilita la inspección L7 ni descifra TLS arbitrario. La ruta compatible de política o proxy L7 y el tráfico deben proporcionar las observaciones de antemano.

</details>

### 3. ¿Qué ajuste se debe habilitar en values.yaml para recopilar métricas de Hubble en Prometheus?

- **A.** hubble.prometheus.enabled: true
- **B.** hubble.metrics.enabled
- **C.** hubble.export.prometheus: true
- **D.** prometheus.hubble: true

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. hubble.metrics.enabled**

`hubble.metrics.enabled` selecciona los manejadores, como `dns` y `httpV2`. Para recopilar los datos en Prometheus también se necesitan el descubrimiento y el scraping operativos, las CRD y el controlador de Prometheus Operator si se usa ServiceMonitor, y selectores coincidentes. Crear el ServiceMonitor no demuestra que Prometheus esté recopilando el destino.

</details>

### 4. ¿Cuál no es una de las cuatro señales doradas de monitorización?

- **A.** Latencia
- **B.** Tráfico
- **C.** Disponibilidad
- **D.** Saturación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Disponibilidad**

Las cuatro señales se llaman latencia, tráfico, errores y saturación. La disponibilidad aún requiere una SLI explícita; no se puede inferir por completo a partir de un flujo parcial de observaciones HTTP 5xx.

</details>

### 5. ¿Qué comando selecciona primero los flujos descartados para investigar la causa?

- **A.** `hubble observe --denied`
- **B.** `hubble observe --verdict DROPPED`
- **C.** `hubble observe --blocked`
- **D.** `hubble observe --policy-denied`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `hubble observe --verdict DROPPED`**

`DROPPED` incluye varias causas. Agrega `--drop-reason-desc POLICY_DENIED` para los descartes atribuidos a políticas e investiga por separado los fallos L7 y de la aplicación. `FORWARDED` es una observación del plano de datos, no una prueba de que la operación de negocio haya tenido éxito.

</details>

### 6. ¿Qué función se usa en consultas PromQL para calcular la latencia HTTP P99?

- **A.** `avg()`
- **B.** `histogram_quantile()`
- **C.** `rate()`
- **D.** `sum()`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `histogram_quantile()`**

`histogram_quantile` calcula una estimación a partir del histograma. Para agregar una carga de trabajo, suma tasas de buckets compatibles y conserva `le` y las etiquetas elegidas de clúster, espacio de nombres y carga de trabajo; después, calcula el cuantil. Promediar percentiles por instancia no es equivalente.

</details>

### 7. ¿Cuál no es una función principal de Hubble UI?

- **A.** Mapa de servicios
- **B.** Cronología de flujos
- **C.** Escalado automático
- **D.** Filtro por espacio de nombres

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C. Escalado automático**

La interfaz muestra relaciones observadas y detalles de flujos, con filtros; no escala cargas de trabajo automáticamente. Las rutas inactivas o no admitidas y los metadatos ausentes pueden dejar vacíos en el mapa.

</details>

### 8. ¿Cómo se calcula el porcentaje observado de respuestas HTTP 5xx con httpV2?

- **A.** Dividir los contadores de errores y solicitudes acumulados desde el inicio, sin usar tasas
- **B.** Dividir las tasas de respuesta 5xx coincidentes entre las tasas totales observadas, gestionando los datos ausentes o cero con el mismo ámbito
- **C.** Contar las series de métricas
- **D.** Leer un indicador `hubble_http_error_rate` que se proporciona automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Dividir las tasas de respuesta 5xx coincidentes entre las tasas totales observadas, gestionando los datos ausentes o cero con el mismo ámbito**

Con httpV2, `hubble_http_requests_total` incluye el estado y se actualiza a partir de eventos de respuesta. Usa la misma agrupación y límite de observación en el numerador y el denominador. Sustituye un numerador 5xx ausente solo cuando existe un total; conserva el estado NoData si faltan observaciones y excluye los totales de cero al calcular porcentajes.

</details>

### 9. ¿Qué opción sirve para observar solo el tráfico destinado a un servicio específico de Hubble?

- **A.** `--destination-service`
- **B.** `--to-service`
- **C.** `--target-service`
- **D.** `--svc`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `--to-service`**

Los filtros de servicio usan prefijos de nombre con espacio de nombres y metadatos derivados del Service o ClusterIP. En general, `--from-service` no selecciona las llamadas hechas por los Pods detrás de ese Service; usa filtros de carga de trabajo, Pod o etiqueta para los clientes. Si se omite el espacio de nombres, se usa `default`.

</details>

### 10. ¿Qué métrica documentada muestra la presión de los mapas BPF instrumentados?

- **A.** `cilium_ct_usage`
- **B.** `cilium_bpf_map_pressure`
- **C.** `cilium_connections_total`
- **D.** `cilium_datapath_conntrack_active` / `cilium_datapath_conntrack_max`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `cilium_bpf_map_pressure`**

`cilium_bpf_map_pressure` informa la presión de los mapas BPF instrumentados y hay umbrales de informe para algunos mapas. No demuestra que estén representados todos los mapas de conntrack (CT). La métrica documentada de entradas de recolección de basura de CT es una instantánea del proceso de recolección, no el antiguo par inventado de métricas de valor activo/máximo.

</details>

### 11. ¿Qué opción se utiliza para recibir la salida de Hubble en formato JSON?

- **A.** `--format json`
- **B.** `-o json`
- **C.** `--json`
- **D.** `--output-type json`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. `-o json`**

`json` es un alias de `jsonpb`. JSON de Protocol Buffers codifica como cadenas los valores de 64 bits, como `latency_ns`; conviértelos a números antes de hacer comparaciones numéricas con jq. También se admiten los formatos de presentación `dict`, `compact` y `table`.

</details>

### 12. ¿Qué ruta admitida permite recopilar registros de flujo de Hubble con OpenTelemetry Collector?

- **A.** Habilitar `hubble.export.opentelemetry` en el chart
- **B.** Usar la exportación de archivos de Hubble y un receptor filelog, y luego un exportador de registros admitido
- **C.** Convertir automáticamente cada flujo en una traza distribuida
- **D.** Usar el exportador jaeger eliminado para ingerir los registros de flujo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B. Usar la exportación de archivos de Hubble y un receptor filelog, y luego un exportador de registros admitido**

Cilium 1.20.3 documenta la exportación de registros de flujo a archivos. Un receptor filelog puede recopilar esos archivos y enviar registros mediante un exportador admitido, como OTLP/HTTP a Loki. Las métricas y las trazas de aplicaciones tienen sus propias rutas de recopilación; los antiguos valores de Hubble opentelemetry y los exportadores jaeger/loki eliminados de Collector no los sustituyen.

</details>
