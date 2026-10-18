# Cuestionario de Dashboards de Grafana

> **Última actualización**: 13 de septiembre de 2026

Pon a prueba tu comprensión de la configuración y operación de Grafana 13.2.1.

---

1. ¿Cuál NO es un método para aprovisionar fuentes de datos en Grafana?
   - A) ConfigMap con sidecar
   - B) API de Grafana
   - C) Variables de entorno
   - D) Directorio de aprovisionamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Variables de entorno**

**Explicación:**
Las fuentes de datos de Grafana se pueden aprovisionar mediante archivos YAML en el directorio de aprovisionamiento, con un sidecar que use ConfigMaps o a través de la API de Grafana. Las variables de entorno pueden proporcionar ajustes de grafana.ini y valores, como URL o credenciales, dentro del YAML de aprovisionamiento de fuentes de datos. Las variables por sí solas no crean un objeto de fuente de datos.

</details>

---

2. ¿Qué significan 'R', 'E' y 'D' en el Método RED?
   - A) Resource, Error, Duration
   - B) Rate, Error, Duration
   - C) Request, Exception, Delay
   - D) Response, Event, Data

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Rate, Error, Duration**

**Explicación:**
El Método RED es una metodología para analizar métricas a nivel de servicio. Monitorea tres métricas clave: Rate (tasa de procesamiento de solicitudes), Error (tasa de errores) y Duration (tiempo de respuesta). Es un marco eficaz para entender la salud de los microservicios.

</details>

---

3. ¿Qué configuración se necesita para implementar la correlación trace-to-log conectando Tempo y Loki en Grafana?
   - A) Usar la misma base de datos
   - B) Configurar tracesToLogsV2 en la fuente de datos de Tempo
   - C) Instalar un plugin aparte
   - D) Licencia de Grafana Enterprise

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar tracesToLogsV2 en la fuente de datos de Tempo**

**Explicación:**
Configurar la sección tracesToLogsV2 en los ajustes de la fuente de datos de Tempo permite navegar directamente desde las trazas hasta los logs relacionados. Se debe especificar Loki con datasourceUid y asignar los atributos reales de la traza a las etiquetas de Loki mediante tags. Los campos de log como trace_id deben coincidir con el contrato del pipeline. Esta es una funcionalidad integrada de Grafana que no requiere plugins adicionales.

</details>

---

4. ¿Qué significan 'U', 'S' y 'E' en el Método USE?
   - A) User, Service, Event
   - B) Utilization, Saturation, Errors
   - C) Uptime, Status, Exceptions
   - D) Usage, Speed, Efficiency

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Utilization, Saturation, Errors**

**Explicación:**
El Método USE es una metodología para analizar los recursos del sistema. Monitorea Utilization (utilización), Saturation (saturación) y Errors (errores). Al analizar estas tres métricas para cada recurso (CPU, memoria, disco, red), puedes identificar cuellos de botella.

</details>

---

5. ¿Cuál es la función del evaluation interval en Grafana Alerting?
   - A) Intervalo de envío de mensajes de alerta
   - B) Frecuencia de evaluación de las reglas de alerta
   - C) Período de retención de datos
   - D) Intervalo de refresco del dashboard

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Frecuencia de evaluación de las reglas de alerta**

**Explicación:**
El evaluation interval determina con qué frecuencia se evalúan las reglas de alerta. Por ejemplo, establecerlo en 1m comprueba las condiciones cada minuto. Esto afecta la sensibilidad de las alertas y el uso de recursos. Un intervalo demasiado corto incrementa el uso de recursos; uno demasiado largo retrasa la detección de problemas.

</details>

---

6. ¿Cuál NO se incluye en las 4 Golden Signals de Google SRE?
   - A) Latency
   - B) Traffic
   - C) Availability
   - D) Saturation

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Availability**

**Explicación:**
Las 4 Golden Signals son Latency (latencia), Traffic (tráfico), Errors (errores) y Saturation (saturación). Availability (disponibilidad) es una métrica importante, pero no está incluida en las 4 Golden Signals. Availability está relacionada con Errors, pero es un concepto distinto.

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
El uso de variables de dashboard permite monitorizar varios clústeres, espacios de nombres y servicios con un solo dashboard. Cuando seleccionas un valor del desplegable, todas las consultas de los paneles se actualizan dinámicamente. Esto reduce la cantidad de dashboards y simplifica el mantenimiento.

</details>

---

8. ¿Cuál es la función de la característica Exemplar al integrar Grafana con Prometheus?
   - A) Compresión de datos de métricas
   - B) Vinculación de métricas y datos de trazas
   - C) Caché de consultas
   - D) Copia de seguridad de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Vinculación de métricas y datos de trazas**

**Explicación:**
Los Exemplars vinculan observaciones seleccionadas de métricas con TraceIDs; no capturan cada solicitud. Al almacenar TraceIDs de muestra en métricas de tipo histograma o contador, hacer clic en un punto concreto de un gráfico de métricas en Grafana permite consultar inmediatamente los datos de la traza correspondiente.

</details>

---

9. ¿Cuál es una diferencia correcta entre Grafana Cloud y Grafana Self-hosted?
   - A) Grafana Cloud es gratuito
   - B) Self-hosted no puede instalar plugins
   - C) Grafana Cloud es gestionado y su SLA depende del contrato
   - D) Self-hosted tiene limitaciones de data sources

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Grafana Cloud es gestionado y su SLA depende del contrato**

**Explicación:**
Consulta el plan de Cloud real y el acuerdo de servicio para conocer su SLA, límites de uso y funcionalidades. Quienes operan una instalación autogestionada administran las bases de datos, las copias de seguridad, las actualizaciones y la compatibilidad de los plugins y sus políticas de firma. No asumas que un SLA fijo del 99,9 % se aplica a todos los planes de Cloud.

</details>

---

10. ¿Qué label de ConfigMap selecciona el perfil sidecar de este capítulo (label=grafana_dashboard, labelValue="true")?
    - A) `app: grafana`
    - B) `grafana_dashboard: "true"`
    - C) `type: dashboard`
    - D) `provisioning: enabled`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) grafana_dashboard: "true"**

**Explicación:**
Este perfil selecciona `grafana_dashboard: "true"`. Tanto label como labelValue son configurables y no son requisitos universales de Grafana. El perfil opcional observa únicamente los ConfigMaps del espacio de nombres monitoring.

</details>

---
