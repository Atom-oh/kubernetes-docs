# Laboratorio de Observabilidad Parte 5: Cuestionario sobre Alerting y AIOps

> **Última actualización**: February 22, 2026

Pon a prueba tu comprensión de los conceptos de alerting y AIOps tratados en el Laboratorio de Observabilidad End-to-End Parte 5.

---

1. ¿Qué especifica el campo `for` en un PrometheusRule de Alertmanager?
   - A) El tiempo entre evaluaciones de alertas
   - B) La duración durante la cual una condición debe permanecer verdadera antes de que se active la alerta, pasando del estado pending al estado firing
   - C) Cuánto tiempo permanece activa la alerta después de que se resuelve la condición
   - D) La duración máxima de la alerta antes de su resolución automática

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La duración durante la cual una condición debe permanecer verdadera antes de que se active la alerta, pasando del estado pending al estado firing**

**Explicación:**
El campo `for` establece un umbral de duración para activar alertas. Cuando la condición de alerta se vuelve verdadera, la alerta entra en estado "pending". Solo si la condición permanece verdadera durante toda la duración de `for`, la alerta pasa a "firing" y activa las notificaciones. Esto evita alertar por picos transitorios breves. Por ejemplo, `for: 5m` significa que la condición debe ser verdadera durante 5 minutos continuos antes de alertar, lo que reduce el ruido causado por fluctuaciones momentáneas.

</details>

---

2. ¿Cómo determina el árbol de enrutamiento de Alertmanager qué receptor gestiona una alerta?
   - A) Las alertas se distribuyen aleatoriamente entre los receptores
   - B) Las rutas se evalúan de arriba hacia abajo; las alertas coinciden según las labels y se envían al receptor de la primera ruta coincidente, con rutas secundarias para coincidencias más específicas
   - C) Todos los receptores reciben todas las alertas simultáneamente
   - D) Las rutas se seleccionan según la puntuación de gravedad de la alerta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las rutas se evalúan de arriba hacia abajo; las alertas coinciden según las labels y se envían al receptor de la primera ruta coincidente, con rutas secundarias para coincidencias más específicas**

**Explicación:**
El árbol de enrutamiento de Alertmanager es jerárquico. La ruta raíz captura todas las alertas y luego las rutas secundarias usan `match` o `match_re` en las labels de alerta para filtrar. Las rutas pueden tener elementos secundarios anidados para lograr coincidencias cada vez más específicas. De forma predeterminada, las alertas coinciden con la primera ruta que cumplen, pero `continue: true` permite coincidir con varias rutas. Esto permite un enrutamiento sofisticado: alertas críticas a PagerDuty, advertencias a Slack y alertas específicas de cada equipo a diferentes canales, todo según labels como `severity`, `team` o `service`.

</details>

---

3. ¿Cómo funciona una Cadena de Escalamiento de Grafana OnCall?
   - A) Selecciona aleatoriamente a un miembro del equipo para notificarlo
   - B) Define una secuencia de pasos de notificación con tiempos de espera, escalando entre diferentes usuarios o grupos hasta que alguien reconozca la alerta
   - C) Solo envía notificaciones por correo electrónico
   - D) Las cadenas de escalamiento son solo para la gestión de calendarios

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Define una secuencia de pasos de notificación con tiempos de espera, escalando entre diferentes usuarios o grupos hasta que alguien reconozca la alerta**

**Explicación:**
Las Cadenas de Escalamiento de Grafana OnCall definen el flujo de trabajo de respuesta a incidentes: el Paso 1 podría notificar al ingeniero de guardia mediante Slack y teléfono, esperar 5 minutos; luego el Paso 2 escala al ingeniero de respaldo, espera 10 minutos; y después el Paso 3 llama al líder del equipo. Cada paso puede usar diferentes canales de notificación (Slack, SMS, llamada telefónica, correo electrónico) y dirigirse a distintos usuarios o programaciones. La cadena se detiene cuando alguien reconoce la alerta, lo que evita la fatiga de alertas y garantiza la cobertura.

</details>

---

4. ¿Qué controlan las configuraciones de período de evaluación y datapoints en CloudWatch Alarms?
   - A) Controlan el nombre y la descripción de la alarma
   - B) El período de evaluación establece con qué frecuencia se comprueban las métricas; datapoints-to-alarm especifica cuántos períodos deben superar el umbral para activar la alarma
   - C) Solo afectan la visualización de alarmas en dashboards
   - D) Estas configuraciones están obsoletas en favor de metric math

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El período de evaluación establece con qué frecuencia se comprueban las métricas; datapoints-to-alarm especifica cuántos períodos deben superar el umbral para activar la alarma**

**Explicación:**
CloudWatch Alarms utiliza dos configuraciones clave: Period (período de evaluación) define la granularidad temporal para la agregación de métricas (por ejemplo, 1 minuto, 5 minutos), y "Datapoints to Alarm" especifica cuántos de los últimos N períodos deben superar el umbral. Por ejemplo, "3 de 5" con períodos de 1 minuto significa que la alarma se activa si 3 de los últimos 5 minutos superaron el umbral. Esta combinación permite ajustar el equilibrio entre capacidad de respuesta y reducción de ruido.

</details>

---

5. ¿Cómo realiza CloudWatch Investigations el análisis de causa raíz basado en IA?
   - A) Solo proporciona runbooks estáticos
   - B) Analiza métricas, logs y traces correlacionados mediante modelos de ML para identificar anomalías y sugerir posibles causas raíz con evidencia de respaldo
   - C) Requiere activar manualmente la investigación para cada incidente
   - D) Solo funciona con instancias EC2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Analiza métricas, logs y traces correlacionados mediante modelos de ML para identificar anomalías y sugerir posibles causas raíz con evidencia de respaldo**

**Explicación:**
CloudWatch Investigations (parte de Amazon CloudWatch Application Signals) usa machine learning para investigar problemas automáticamente. Cuando se activa mediante una alarma o de forma manual, correlaciona señales de telemetría entre métricas, logs y traces para identificar anomalías que coinciden con el incidente. Analiza recursos relacionados, detecta patrones y presenta hallazgos con puntuaciones de confianza y enlaces de evidencia. Esto acelera el tiempo medio hasta el diagnóstico al mostrar datos relevantes que las personas podrían pasar por alto al investigar manualmente.

</details>

---

6. ¿En qué orden suele recopilar telemetría un Agente AIOps basado en Lambda para el análisis de incidentes?
   - A) Primero logs, luego métricas y después traces secuencialmente
   - B) La recopilación de telemetría se realiza en paralelo para métricas, logs y traces a fin de minimizar el tiempo total de recopilación
   - C) Solo se recopilan traces; se ignoran las métricas y los logs
   - D) El orden de recopilación es aleatorio e impredecible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La recopilación de telemetría se realiza en paralelo para métricas, logs y traces a fin de minimizar el tiempo total de recopilación**

**Explicación:**
Un agente AIOps eficaz recopila telemetría en paralelo para minimizar la latencia. Cuando un incidente activa la función Lambda, consulta simultáneamente: Prometheus/AMP para métricas (tasas de error, latencia), Loki/CloudWatch para logs relevantes (mensajes de error, stack traces) y Tempo/X-Ray para traces distribuidos (flujos de solicitudes, cuellos de botella). La recopilación en paralelo garantiza que el agente tenga rápidamente un contexto completo, lo que permite un análisis y una respuesta de IA más rápidos. Esto se implementa mediante patrones async/await o llamadas API simultáneas.

</details>

---

7. ¿Cuáles son los principios clave para diseñar un system prompt al usar Bedrock Claude como experto en SRE?
   - A) Hacer que el prompt sea lo más corto posible
   - B) Definir claramente el rol, proporcionar contexto sobre la arquitectura del sistema, especificar el formato de salida e incluir conocimiento específico del dominio sobre patrones de fallos comunes
   - C) Los system prompts solo deben contener instrucciones genéricas
   - D) Evitar mencionar tecnologías específicas en el prompt

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir claramente el rol, proporcionar contexto sobre la arquitectura del sistema, especificar el formato de salida e incluir conocimiento específico del dominio sobre patrones de fallos comunes**

**Explicación:**
Los system prompts eficaces para SRE incluyen: una definición clara del rol ("Eres un experto en SRE que analiza incidentes de Kubernetes"), contexto del sistema (arquitectura, stack tecnológico, problemas típicos), formato de salida estructurado (hipótesis, evidencia, acciones recomendadas, enlaces a runbooks) y conocimiento del dominio (patrones de fallos comunes, criterios de escalamiento, dependencias de servicios). Incluir ejemplos de incidentes pasados y sus resoluciones mejora la calidad de las respuestas. El prompt debe guiar al modelo para que proporcione recomendaciones específicas y aplicables, en lugar de consejos genéricos.

</details>

---

8. ¿Cómo conecta un webhook de Alertmanager API Gateway y Lambda para una respuesta automatizada a incidentes?
   - A) Lambda recibe directamente las alertas de Alertmanager mediante SDK
   - B) Alertmanager envía solicitudes POST a un endpoint HTTP de API Gateway, que activa una función Lambda con el payload de alerta para su procesamiento
   - C) API Gateway consulta Alertmanager para obtener nuevas alertas
   - D) La conexión requiere una instancia EC2 dedicada como proxy

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Alertmanager envía solicitudes POST a un endpoint HTTP de API Gateway, que activa una función Lambda con el payload de alerta para su procesamiento**

**Explicación:**
El flujo de integración: el receptor de webhook de Alertmanager se configura con una URL de endpoint de API Gateway. Cuando se activan alertas, Alertmanager envía mediante POST payloads JSON que contienen detalles de la alerta (labels, annotations, estado, timestamps) a este endpoint. API Gateway recibe la solicitud y activa una función Lambda integrada, pasando el payload de alerta como evento. La función Lambda procesa la alerta: la enriquece con contexto, ejecuta análisis de IA, activa remediaciones o la reenvía a sistemas de gestión de incidentes.

</details>

---

9. ¿Cómo puedes activar una alerta HighLatency mediante Fault Injection para probar pipelines de alertas?
   - A) Editar manualmente el estado de la alerta en Alertmanager
   - B) Inyectar latencia artificial en las respuestas del servicio usando herramientas como Chaos Mesh, Litmus o inyección de fallos a nivel de aplicación, haciendo que las métricas de latencia superen los umbrales de alerta
   - C) Modificar directamente los valores de métricas de Prometheus
   - D) La inyección de fallos no puede activar alertas de Prometheus

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inyectar latencia artificial en las respuestas del servicio usando herramientas como Chaos Mesh, Litmus o inyección de fallos a nivel de aplicación, haciendo que las métricas de latencia superen los umbrales de alerta**

**Explicación:**
La inyección de fallos valida los pipelines de alertas de extremo a extremo. Herramientas como Chaos Mesh o Litmus pueden inyectar latencia de red a nivel de Pod o Service. La inyección a nivel de aplicación podría añadir retrasos sleep a los handlers. Cuando la latencia inyectada provoca que las métricas (por ejemplo, `histogram_quantile(0.99, http_request_duration_seconds_bucket)`) superen los umbrales definidos en PrometheusRules, las alertas se activan naturalmente a través del pipeline. Esto prueba que la recopilación de métricas, las reglas de alerta, el enrutamiento de Alertmanager y la entrega de notificaciones funcionan correctamente.

</details>

---

10. ¿Qué rol desempeña un Agente Colaborador en el patrón A2A (Agent-to-Agent) para AIOps?
    - A) Reemplaza por completo a los operadores humanos
    - B) Actúa como un agente especializado al que el agente principal puede delegar subtareas, como consultar fuentes de datos específicas, ejecutar acciones de remediación o proporcionar experiencia en el dominio
    - C) Solo gestiona logging y monitoring
    - D) Los agentes colaboradores son copias idénticas del agente principal

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Actúa como un agente especializado al que el agente principal puede delegar subtareas, como consultar fuentes de datos específicas, ejecutar acciones de remediación o proporcionar experiencia en el dominio**

**Explicación:**
En los patrones A2A, un agente principal (orquestador) se coordina con agentes colaboradores especializados. Para AIOps: un Agente de Métricas consulta Prometheus/CloudWatch, un Agente de Logs busca y analiza datos de logs, un Agente de Traces investiga traces distribuidos, un Agente de Remediación ejecuta acciones de recuperación seguras y un Agente de Conocimiento recupera runbooks y datos de incidentes pasados. El agente principal sintetiza las salidas de los colaboradores en un análisis coherente del incidente. Esta división permite prompts especializados, ejecución paralela y separación de responsabilidades, lo que mejora la capacidad general del sistema.

</details>
