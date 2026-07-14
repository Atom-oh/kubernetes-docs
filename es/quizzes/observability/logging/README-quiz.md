# Cuestionario de resumen de logging

Pon a prueba tu comprensión de los conceptos básicos de logging.

---

1. ¿Cuál NO es una ventaja principal del Structured Logging?

   - A) Mayor eficiencia de búsqueda y filtrado
   - B) Tamaño reducido del archivo de log
   - C) Formato de log consistente
   - D) Compatibilidad con herramientas de análisis automatizado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tamaño reducido del archivo de log**

**Explicación:**
El logging estructurado (especialmente el formato JSON) puede generar tamaños de archivo mayores que los logs de texto no estructurado. Esto se debe a que se agregan nombres de campos y delimitadores. Las ventajas reales del logging estructurado son la eficiencia de búsqueda, la consistencia y la compatibilidad con herramientas de automatización.

</details>

---

2. ¿Cuál es el nivel de log recomendado para entornos de producción?

   - A) DEBUG
   - B) TRACE
   - C) INFO o WARN
   - D) FATAL

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) INFO o WARN**

**Explicación:**
Los niveles INFO o WARN se recomiendan para entornos de producción. DEBUG o TRACE son demasiado detallados, lo que genera un volumen excesivo de logs, y usar solo FATAL puede omitir información operativa importante.

</details>

---

3. ¿Cuál es el patrón de recopilación de logs más recomendado en Kubernetes?

   - A) Logging basado en archivos + Sidecar
   - B) stdout/stderr + agente DaemonSet
   - C) Transmisión directa a un servidor de logging remoto
   - D) Almacenamiento de archivos locales con recopilación manual

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) stdout/stderr + agente DaemonSet**

**Explicación:**
En Kubernetes, el enfoque estándar es que los contenedores envíen logs a stdout/stderr y que los agentes implementados como DaemonSet recopilen logs desde `/var/log/containers/` en el nodo. Este enfoque tiene ventajas como la compatibilidad con el comando kubectl logs, la rotación automática y no requiere un volumen independiente.

</details>

---

4. ¿Qué solución se recomienda cuando la "optimización de costos" es la máxima prioridad para seleccionar el almacenamiento de logs?

   - A) Amazon OpenSearch Service
   - B) CloudWatch Logs
   - C) Grafana Loki + S3
   - D) Elasticsearch en EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Grafana Loki + S3**

**Explicación:**
Loki reduce significativamente los costos de almacenamiento al indexar solo las etiquetas, no el contenido de los logs. El uso de S3 como backend puede lograr costos de almacenamiento de tan solo $0.023 por GB.

</details>

---

5. ¿Cuáles son los campos obligatorios que se deben incluir en el formato de log JSON para el tracing distribuido?

   - A) user_id, session_id
   - B) trace_id, span_id
   - C) request_id, response_time
   - D) level, message

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) trace_id, span_id**

**Explicación:**
Para el tracing distribuido, se requieren trace_id (seguimiento de toda la solicitud) y span_id (identificación de operaciones individuales). Estos campos permiten rastrear el flujo de solicitudes entre varios servicios.

</details>

---

6. ¿Cuál NO es una función de la "Capa de procesamiento" en un pipeline de recopilación de logs?

   - A) Análisis y normalización de logs
   - B) Adición de metadatos de Kubernetes
   - C) Almacenamiento e indexación de logs
   - D) Filtrado y muestreo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Almacenamiento e indexación de logs**

**Explicación:**
El almacenamiento y la indexación de logs son responsabilidad de la "Capa de almacenamiento". La capa de procesamiento se encarga del análisis, la adición de metadatos, el filtrado, el buffering, etc.

</details>

---

7. ¿Cuál es el período de retención de logs recomendado para el cumplimiento normativo financiero?

   - A) 30 días
   - B) 1 año
   - C) 7 años
   - D) 90 días

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) 7 años**

**Explicación:**
Para el cumplimiento normativo financiero (por ejemplo, relacionado con SOX, PCI-DSS), generalmente se recomiendan 7 años de retención de logs. El sector sanitario (HIPAA) requiere 6 años y los logs operativos generales normalmente requieren alrededor de 1 año.

</details>

---

8. ¿Cuándo se deben recopilar logs utilizando el patrón Sidecar?

   - A) Todas las cargas de trabajo estándar de Kubernetes
   - B) Cuando las aplicaciones heredadas solo envían logs a archivos
   - C) Entornos con recursos de CPU limitados
   - D) Solo pods de un único contenedor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Cuando las aplicaciones heredadas solo envían logs a archivos**

**Explicación:**
El patrón Sidecar se utiliza para aplicaciones heredadas (logging en archivos en lugar de stdout/stderr), aislamiento de logs en entornos multi-tenant y cuando se necesita procesamiento de formatos de log especiales. Dado que tiene sobrecarga de recursos, el enfoque DaemonSet es más eficiente para cargas de trabajo estándar.

</details>

---

9. ¿Qué solución de almacenamiento de logs es "excelente" tanto en rendimiento de consultas como en búsqueda de texto completo?

   - A) Grafana Loki
   - B) CloudWatch Logs
   - C) Amazon OpenSearch Service
   - D) ClickHouse

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Amazon OpenSearch Service**

**Explicación:**
OpenSearch (fork de Elasticsearch) admite tanto potentes funciones de búsqueda de texto completo basadas en Lucene como consultas de agregación complejas. Loki tiene una búsqueda de texto completo limitada, mientras que CloudWatch y ClickHouse tienen capacidades moderadas de búsqueda de texto completo.

</details>

---

10. ¿Qué tipo de log debe habilitarse para la auditoría de seguridad en el logging del control plane de EKS?

    - A) scheduler
    - B) controllerManager
    - C) audit
    - D) api

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) audit**

**Explicación:**
Los logs de auditoría registran todas las solicitudes al servidor de API de Kubernetes. Son esenciales para las auditorías de seguridad y el cumplimiento normativo porque permiten rastrear quién hizo qué y cuándo. Los logs de API también son importantes, pero audit es el más crítico para fines de auditoría de seguridad.

</details>

---
