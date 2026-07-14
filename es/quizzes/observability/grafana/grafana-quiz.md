# Cuestionario de dashboards de Grafana

Pon a prueba tu comprensión de Grafana.

---

1. ¿Cuál NO es un método utilizado para el aprovisionamiento de fuentes de datos en Grafana?
   - A) ConfigMap con sidecar
   - B) API de Grafana
   - C) Variables de entorno
   - D) directorio de aprovisionamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Variables de entorno**

**Explicación:**
Las fuentes de datos de Grafana se pueden aprovisionar mediante archivos YAML en el directorio de aprovisionamiento, el enfoque sidecar que utiliza ConfigMaps o la API de Grafana. Las variables de entorno se utilizan para la configuración de Grafana (grafana.ini), pero no para definir directamente fuentes de datos.

</details>

---

2. ¿Qué significan 'R', 'E', 'D' en el Método RED?
   - A) Resource, Error, Duration
   - B) Rate, Error, Duration
   - C) Request, Exception, Delay
   - D) Response, Event, Data

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Rate, Error, Duration**

**Explicación:**
El Método RED es una metodología para analizar métricas de nivel de servicio. Supervisa tres métricas clave: Rate (tasa de procesamiento de requests), Error (tasa de errores) y Duration (tiempo de respuesta). Es un marco eficaz para comprender el estado de los microservices.

</details>

---

3. ¿Qué configuración se necesita para implementar la correlación trace-to-log conectando Tempo y Loki en Grafana?
   - A) Usar la misma base de datos
   - B) Configurar tracesToLogs en la fuente de datos Tempo
   - C) Instalar un plugin independiente
   - D) Licencia de Grafana Enterprise

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar tracesToLogs en la fuente de datos Tempo**

**Explicación:**
Configurar la sección tracesToLogs en los ajustes de la fuente de datos Tempo permite la navegación directa desde traces hasta logs relacionados. Especifique Loki con datasourceUid y establezca labels para la conexión mediante tags. Esta es una funcionalidad integrada de Grafana que no requiere plugins adicionales.

</details>

---

4. ¿Qué significan 'U', 'S', 'E' en el Método USE?
   - A) User, Service, Event
   - B) Utilization, Saturation, Errors
   - C) Uptime, Status, Exceptions
   - D) Usage, Speed, Efficiency

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Utilization, Saturation, Errors**

**Explicación:**
El Método USE es una metodología para analizar recursos del sistema. Supervisa Utilization, Saturation y Errors. Al analizar estas tres métricas para cada recurso (CPU, memory, disk, network), puede identificar cuellos de botella.

</details>

---

5. ¿Cuál es el papel del intervalo de evaluación en Grafana Alerting?
   - A) Intervalo de entrega de mensajes de alertas
   - B) Frecuencia de evaluación de reglas de alertas
   - C) Período de retención de datos
   - D) Intervalo de actualización del dashboard

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Frecuencia de evaluación de reglas de alertas**

**Explicación:**
El intervalo de evaluación determina con qué frecuencia se evalúan las reglas de alertas. Por ejemplo, establecerlo en 1m comprueba las condiciones cada minuto. Esto afecta la sensibilidad de las alertas y el uso de recursos. Un intervalo demasiado corto aumenta el uso de recursos; uno demasiado largo retrasa la detección de problemas.

</details>

---

6. ¿Cuál NO está incluida en las 4 Golden Signals de Google SRE?
   - A) Latency
   - B) Traffic
   - C) Availability
   - D) Saturation

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Availability**

**Explicación:**
Las 4 Golden Signals son Latency, Traffic, Errors y Saturation. Availability es una métrica importante, pero no está incluida en las 4 Golden Signals. Availability está relacionada con Errors, pero es un concepto independiente.

</details>

---

7. ¿Cuál es el principal beneficio de usar variables de dashboard en Grafana?
   - A) Mayor velocidad de carga del dashboard
   - B) Mayor reutilización del dashboard mediante filtrado dinámico
   - C) Menor capacidad de almacenamiento de datos
   - D) Seguridad mejorada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Mayor reutilización del dashboard mediante filtrado dinámico**

**Explicación:**
El uso de variables de dashboard permite supervisar varios clusters, namespaces y services con un solo dashboard. Al seleccionar un valor del menú desplegable, las queries de todos los paneles se actualizan dinámicamente. Esto reduce el número de dashboards y simplifica el mantenimiento.

</details>

---

8. ¿Cuál es el papel de la funcionalidad Exemplar al integrar Grafana con Prometheus?
   - A) Compresión de datos de métricas
   - B) Vinculación de métricas y datos de traces
   - C) Almacenamiento en caché de queries
   - D) Copia de seguridad de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Vinculación de métricas y datos de traces**

**Explicación:**
Exemplar es una funcionalidad que vincula TraceIDs a las métricas de Prometheus. Al almacenar TraceIDs de muestra en métricas de histogram o counter, hacer clic en un punto específico de un gráfico de métricas en Grafana permite consultar inmediatamente los datos de traces de ese momento.

</details>

---

9. ¿Cuál es una diferencia correcta entre Grafana Cloud y Self-hosted Grafana?
   - A) Grafana Cloud es gratuito
   - B) Self-hosted no permite instalar plugins
   - C) Grafana Cloud proporciona autoescalado y SLA
   - D) Self-hosted tiene limitaciones de fuentes de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Grafana Cloud proporciona autoescalado y SLA**

**Explicación:**
Grafana Cloud es un servicio gestionado que proporciona autoescalado, SLA del 99,9 %, actualizaciones automáticas, etc. Self-hosted ofrece control completo y permite instalar todos los plugins, pero requiere gestión de infraestructura. Ambas opciones admiten varias fuentes de datos.

</details>

---

10. ¿Qué label se requiere en un ConfigMap al usar sidecar para el aprovisionamiento de dashboards de Grafana?
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) grafana_dashboard: "true"**

**Explicación:**
Al usar la funcionalidad sidecar del Helm chart de Grafana, debe añadir el label `grafana_dashboard: "true"` a los ConfigMaps que contienen JSON de dashboard. El contenedor sidecar supervisa los ConfigMaps con este label y aprovisiona automáticamente los dashboards.

</details>

---
