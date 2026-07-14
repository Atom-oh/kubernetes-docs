# Cuestionario de comparación de recolectores de logs

Pon a prueba tus conocimientos sobre recolectores de logs (FluentBit, Promtail, Alloy, OTEL Collector).

---

1. ¿Cuál de los siguientes recolectores de logs tiene el menor uso de memoria?

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) OpenTelemetry Collector

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluentBit**

**Explicación:**
FluentBit está escrito en C y tiene el menor uso de memoria, de aproximadamente 10-50MB. Los demás están escritos en Go y utilizan aproximadamente 50-100MB de memoria.

</details>

---

2. ¿Qué FILTER de FluentBit añade metadatos de Kubernetes (namespace, pod_name, etc.) a los logs?

   - A) [FILTER] Name modify
   - B) [FILTER] Name kubernetes
   - C) [FILTER] Name parser
   - D) [FILTER] Name record_modifier

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) [FILTER] Name kubernetes**

**Explicación:**
El filtro `kubernetes` de FluentBit añade automáticamente metadatos como pod, namespace y labels a los logs mediante la API de Kubernetes.

</details>

---

3. ¿Cuál es la principal limitación de Promtail?

   - A) No admite el análisis de JSON
   - B) No puede enviar a destinos distintos de Loki
   - C) No se puede utilizar en entornos de Kubernetes
   - D) No puede gestionar logs multilínea

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No puede enviar a destinos distintos de Loki**

**Explicación:**
Promtail está diseñado como un agente dedicado para Grafana Loki y no admite el envío a otros destinos como OpenSearch o CloudWatch. Si se necesitan varios destinos, utiliza FluentBit u OTEL Collector.

</details>

---

4. ¿Qué lenguaje de configuración utiliza Grafana Alloy?

   - A) YAML
   - B) JSON
   - C) River (similar a HCL)
   - D) INI

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) River (similar a HCL)**

**Explicación:**
Grafana Alloy utiliza River, un lenguaje de configuración similar a HCL (HashiCorp Configuration Language). Es más expresivo que YAML y permite definir componentes reutilizables.

</details>

---

5. ¿Cuál es el orden de los componentes del pipeline en OpenTelemetry Collector?

   - A) Processors → Receivers → Exporters
   - B) Receivers → Exporters → Processors
   - C) Receivers → Processors → Exporters
   - D) Exporters → Processors → Receivers

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Receivers → Processors → Exporters**

**Explicación:**
Los pipelines de OTEL Collector se componen en el siguiente orden: Receivers (reciben datos) → Processors (procesan/transforman datos) → Exporters (envían datos).

</details>

---

6. ¿Qué lenguaje de scripting se puede utilizar en FluentBit para implementar lógica compleja de procesamiento de logs?

   - A) Python
   - B) JavaScript
   - C) Lua
   - D) Ruby

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Lua**

**Explicación:**
FluentBit admite scripting en Lua para implementar lógica compleja de procesamiento de logs (transformación de campos, procesamiento condicional, enmascaramiento de datos confidenciales, etc.). Utiliza el filtro `[FILTER] Name lua`.

</details>

---

7. ¿Qué ajuste de pipeline_stages en la configuración de Promtail excluye logs específicos?

   - A) stage.filter
   - B) stage.drop
   - C) stage.exclude
   - D) stage.ignore

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) stage.drop**

**Explicación:**
`stage.drop` de Promtail excluye líneas de logs que coinciden con expresiones regulares o condiciones. Ejemplo: utiliza `expression: "healthcheck|readiness"` para excluir logs de healthcheck.

</details>

---

8. ¿Qué recolector es el más adecuado cuando necesitas enviar logs tanto a CloudWatch Logs como a OpenSearch en entornos de AWS?

   - A) Promtail
   - B) FluentBit
   - C) Grafana Alloy
   - D) Logstash

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) FluentBit**

**Explicación:**
FluentBit admite de forma nativa los plugins de salida `cloudwatch_logs` y `opensearch`. Se puede desplegar fácilmente con la imagen `aws-for-fluent-bit` proporcionada por AWS. Promtail y Alloy están optimizados para Loki.

</details>

---

9. ¿Qué processor de OpenTelemetry Collector limita el uso de memoria?

   - A) batch
   - B) memory_limiter
   - C) resource
   - D) filter

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) memory_limiter**

**Explicación:**
El processor `memory_limiter` supervisa el uso de memoria de OTEL Collector y pausa temporalmente la recopilación de datos cuando se alcanza el límite configurado para evitar un OOM.

</details>

---

10. ¿Cuál es el destino de migración recomendado cuando también necesitas recopilar métricas y traces desde un entorno de Promtail existente?

    - A) FluentBit
    - B) Logstash
    - C) Grafana Alloy
    - D) Filebeat

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Grafana Alloy**

**Explicación:**
Grafana Alloy es el proyecto sucesor de Promtail, incluye toda la funcionalidad de Promtail y también puede recopilar métricas (Prometheus) y traces (Tempo). Las configuraciones de Promtail se pueden migrar fácilmente a la sintaxis de River.

</details>
