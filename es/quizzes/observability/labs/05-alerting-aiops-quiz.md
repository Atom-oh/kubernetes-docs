# Cuestionario de la Parte 5 del laboratorio de Observabilidad: Alertas y AIOps

<span id="observability-lab-part-5-alerting-and-aiops-quiz"></span>

> **Última actualización**: September 13, 2026

1. ¿Qué componente evalúa las alertas de PrometheusRule?
   - A) Alertmanager
   - B) Prometheus
   - C) SNS
   - D) La DLQ de Lambda

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Prometheus**

Prometheus evalúa; Alertmanager se encarga de la agrupación, el enrutamiento y las notificaciones.

</details>

---

2. ¿Qué significan DatapointsToAlarm=2 y EvaluationPeriods=3?
   - A) Se requieren exactamente dos incumplimientos consecutivos.
   - B) Dos de los tres puntos de datos evaluados deben incumplir el umbral; no es necesario que sean consecutivos.
   - C) Dos notificaciones cada tres segundos.
   - D) Usar dos regiones.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Dos de los tres puntos de datos evaluados deben incumplir el umbral; no es necesario que sean consecutivos.**

Period es la granularidad de agregación de la métrica, no un sinónimo de la frecuencia de evaluación.

</details>

---

3. ¿Qué es importante al evaluar el antiguo paso de instalación de Grafana OnCall OSS?
   - A) Tiene soporte perpetuo.
   - B) Tener en cuenta el archivado y la finalización de Cloud Connection el 2026-03-24.
   - C) El soporte de SMS siempre es gratuito para siempre.
   - D) Aplicar YAML arbitrario lo deja operativo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tener en cuenta el archivado y la finalización de Cloud Connection el 2026-03-24.**

Valida una ruta de incidentes/notificaciones con soporte y la entrega real para la organización.

</details>

---

4. ¿Por qué separar los temas (topics) SNS de entrada y de salida?
   - A) Para cambiar las unidades de las métricas.
   - B) Para evitar que el generador de informes procese sus propios resultados en un bucle.
   - C) Porque SNS solo admite un tema.
   - D) Para publicar los logs de forma pública.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para evitar que el generador de informes procese sus propios resultados en un bucle.**

Limita las suscripciones y los permisos de publicación de IAM al mismo límite.

</details>

---

5. ¿Qué debe tener en cuenta el analizador con la salida `{{ . | toJson }}` de Alertmanager?
   - A) Siempre es texto plano.
   - B) Las claves en minúscula/camelCase etiquetadas para JSON difieren del acceso a campos capitalizados en las plantillas de Go.
   - C) JSON nunca necesita análisis.
   - D) Todos los mensajes de SNS tienen campos idénticos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las claves en minúscula/camelCase etiquetadas para JSON difieren del acceso a campos capitalizados en las plantillas de Go.**

Se probaron la serialización real de plantillas de la versión 0.34.0 y las cargas útiles válidas e inválidas.

</details>

---

6. ¿Cómo deben notificarse las métricas ausentes o las consultas fallidas?
   - A) Convertirlas en cero errores.
   - B) Etiquetarlas como missing/no_data/error en lugar de inventar mediciones.
   - C) Presentar las cadenas de consulta como valores medidos.
   - D) Informar siempre de un estado saludable.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Etiquetarlas como missing/no_data/error en lugar de inventar mediciones.**

La llamada al modelo puede omitirse cuando la evidencia es insuficiente.

</details>

---

7. ¿Qué aporta la idempotencia de Powertools en este ejemplo?
   - A) Entrega exactly-once de extremo a extremo en SNS.
   - B) Suprime el trabajo exitoso repetido para el mismo ID de mensaje durante 24 horas.
   - C) Cada nuevo ID de mensaje es la misma operación.
   - D) Combina de forma atómica la publicación y el commit en la base de datos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Suprime el trabajo exitoso repetido para el mismo ID de mensaje durante 24 horas.**

Distingue la ventana de duplicados de publicación/commit y las capas de reintentos de SNS/Lambda.

</details>

---

8. ¿Cómo se acepta una respuesta de diagnóstico de Converse?
   - A) Cualquier respuesta es un éxito.
   - B) Definir maxTokens y exigir end_turn con texto no vacío.
   - C) Una parada por max_tokens es un diagnóstico completado.
   - D) Ejecutar de inmediato los comandos generados por el modelo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Definir maxTokens y exigir end_turn con texto no vacío.**

El generador de informes crea hipótesis para revisión humana y no tiene herramientas de remediación.

</details>

---

9. ¿Cómo se configura una alarma para iniciar CloudWatch Investigations?
   - A) Llamar a list-dashboards.
   - B) Añadir el ARN del investigation-group preparado como acción de la alarma.
   - C) Llamar únicamente a put-insight-rule.
   - D) Habilitar únicamente el descubrimiento de Application Signals.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Añadir el ARN del investigation-group preparado como acción de la alarma.**

Prepara el grupo, los permisos, la retención, el cifrado y la acción real de la alarma.

</details>

---

10. ¿Llamar a varios módulos de análisis implementa el protocolo A2A?
   - A) Dos funciones implementan A2A automáticamente.
   - B) No; el descubrimiento, la autenticación y los contratos de tareas/mensajes requieren una implementación aparte.
   - C) SNS siempre implica A2A.
   - D) DynamoDB por sí solo es suficiente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No; el descubrimiento, la autenticación y los contratos de tareas/mensajes requieren una implementación aparte.**

La descomposición en especialistas es un patrón de diseño, distinto del cumplimiento de un protocolo de agentes.

</details>

---

[Volver a la guía](../../../labs/observability/05-alerting-aiops-lab.md)
