# Cuestionario del laboratorio de Observabilidad, parte 6

> **Última actualización**: September 13, 2026

1. ¿Cómo se distinguen las duraciones de una traza completa y de un span individual?
   - A) Siempre son idénticas.
   - B) trace:duration and span:duration.
   - C) span.duration siempre es el intrínseco.
   - D) Contar líneas de logs.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) trace:duration and span:duration.**

Los intrínsecos explícitos usan dos puntos; span. es el ámbito de atributos.

</details>

---

2. ¿Qué consulta usa el atributo actual de estado de respuesta HTTP?
   - A) { order by status desc }
   - B) { span.http.response.status_code >= 500 }
   - C) { duration > p99 }
   - D) { select 500 }

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) { span.http.response.status_code >= 500 }**

Si un SDK aún emite http.status_code, inspecciona sus datos y usa la consulta heredada adecuada.

</details>

---

3. ¿Qué selecciona A >> B?
   - A) Todos los logs anteriores a A.
   - B) Los spans B que descienden de los spans A.
   - C) El promedio de A y B.
   - D) B es necesariamente el mismo span que A.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los spans B que descienden de los spans A.**

Coloca el selector de Service a la izquierda y el selector de DB a la derecha para encontrar trabajo de DB descendiente.

</details>

---

4. ¿Cómo deben reemplazarse order by/limit de estilo SQL en el ejemplo antiguo?
   - A) Ejecútalos sin cambios.
   - B) TraceQL válido más la configuración de ordenación/límite de búsqueda de Grafana.
   - C) Envíalos a Prometheus.
   - D) Agrega la contraseña de DB a la consulta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) TraceQL válido más la configuración de ordenación/límite de búsqueda de Grafana.**

El parser real de Tempo3.0.3 rechaza esos ejemplos antiguos de sort/order-by/limit.

</details>

---

5. ¿Qué requiere un grafo de servicios?
   - A) Solo instalar Tempo.
   - B) Spans conectados, un procesador service-graphs, un backend de metrics y vinculación de datasource.
   - C) Solo almacenar trace IDs como labels de log.
   - D) Dibujar manualmente nodos rojos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Spans conectados, un procesador service-graphs, un backend de metrics y vinculación de datasource.**

Valida por separado la ingesta de trazas y la entrega de métricas de grafos.

</details>

---

6. ¿Qué puede establecer por sí solo un span de DB de 1.8 segundos?
   - A) Definitivamente falta un índice.
   - B) La duración de la operación observada; su causa necesita más evidencia.
   - C) La red está en buen estado.
   - D) Es seguro sumarlo con todas las duraciones principales.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) La duración de la operación observada; su causa necesita más evidencia.**

Comprueba locks, pools, red y planes de consulta; evita contar dos veces spans superpuestos.

</details>

---

7. ¿Cómo debe escribirse una expresión de enlace de campo derivado en el provisioning de Grafana?
   - A) Elimina todas las variables de dólar con envsubst.
   - B) Escapa la sustitución de provisioning con $${__value.raw}.
   - C) Agrega trace IDs a cada label de stream.
   - D) Agrega límites de tiempo como una cláusula SQL de LogQL.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Escapa la sustitución de provisioning con $${__value.raw}.**

Los nombres reales de los campos de trace ID y los UID de datasource también deben coincidir.

</details>

---

8. ¿A qué solicitud conduce un exemplar?
   - A) Necesariamente a la solicitud exacta del límite p99.
   - B) A una observación representativa cuya traza aún debe conservarse.
   - C) A una copia de cada solicitud.
   - D) Siempre recuperable independientemente del sampling de trazas.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) A una observación representativa cuya traza aún debe conservarse.**

El sampling y la retención pueden hacer que los IDs de exemplar y la disponibilidad de trazas sean diferentes.

</details>

---

9. ¿Qué demuestra una consulta [30d] en el primer día del laboratorio?
   - A) Que se cumplió un SLO de 30 días.
   - B) Agrega las observaciones disponibles; no crea 30 días de historial.
   - C) Disponibilidad del 100%.
   - D) Un presupuesto de errores ilimitado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Agrega las observaciones disponibles; no crea 30 días de historial.**

Registra el período real, el denominador y los intervalos ausentes/sin tráfico.

</details>

---

10. ¿Qué combinación de atributos actuales de DB y manejo de datos es correcta?
   - A) db.statement es permanentemente el único estándar.
   - B) Inspecciona db.system.name/db.query.text para el SDK real y sanitiza las consultas.
   - C) Registra todas las contraseñas.
   - D) Renombrar una consulta transforma todos los datos antiguos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Inspecciona db.system.name/db.query.text para el SDK real y sanitiza las consultas.**

Los atributos heredados pueden permanecer en los datos; la migración y el manejo de datos sensibles son independientes.

</details>

---

[Volver a la guía](../../../labs/observability/06-distributed-tracing-lab.md)
