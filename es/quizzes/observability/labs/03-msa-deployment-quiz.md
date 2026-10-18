# Cuestionario del laboratorio 03 de observabilidad

<span id="observability-lab-part-3-msa-deployment-and-canary-quiz"></span>

> **Última actualización**: 13 de septiembre de 2026

1. ¿Cuál es el límite transaccional entre un pedido y el outbox?
   - A) Confirmar el pedido y luego ignorar los fallos de mensajería.
   - B) Ambos se confirman o se revierten en una transacción de base de datos.
   - C) SNS y la base de datos son atómicos automáticamente.
   - D) Inicializar la base de datos en cada solicitud.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ambos se confirman o se revierten en una transacción de base de datos.**

Valide la reversión de la base de datos y la retención de los registros del outbox que aún no se hayan publicado.

</details>

---

2. ¿Quién es propietario de la carga de trabajo de pagos?
   - A) Deployment y Rollout simultáneamente.
   - B) Un único Rollout.
   - C) KEDA y Rollout compiten por las réplicas.
   - D) Grafana.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un único Rollout.**

Mantenga explícitos quién es propietario del controlador y cuál es el estado deseado en Git.

</details>

---

3. ¿Por qué separar las colas de notificaciones y analítica?
   - A) Que varios consumidores compitan por una cola es fanout.
   - B) Para que cada consumidor reciba de forma independiente el mismo evento.
   - C) SQS solo admite una cola.
   - D) Elimina todos los duplicados.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para que cada consumidor reciba de forma independiente el mismo evento.**

El fanout de SNS y la deduplicación del ID de evento de cada consumidor son responsabilidades independientes.

</details>

---

4. ¿Qué ocurre con un pago sintético idéntico repetido?
   - A) Crear siempre un nuevo pago.
   - B) Reutilizar el resultado almacenado; los valores en conflicto devuelven 409.
   - C) Cobrar una tarjeta real.
   - D) Tener éxito siempre, incluso sin un pedido.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reutilizar el resultado almacenado; los valores conflictivos devuelven 409.**

El laboratorio no implementa ninguna pasarela de pago real.

</details>

---

5. ¿Qué sucede si ocurre un fallo después de publicar en SNS, pero antes de marcarlo en la base de datos?
   - A) Exactamente una vez es automático.
   - B) Es posible una reentrega, por lo que los consumidores necesitan deduplicar.
   - C) Eliminar cada fila de outbox.
   - D) Confirmar siempre el mensaje.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es posible una nueva entrega, por lo que los consumidores necesitan deduplicación.**

Los efectos secundarios externos requieren contratos de idempotencia adicionales.

</details>

---

6. ¿Qué carga de trabajo se escala según la acumulación de mensajes en SQS?
   - A) Siempre solo el productor de API.
   - B) El consumidor de esa cola.
   - C) El administrador de la base de datos.
   - D) El NLB.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El consumidor de esa queue.**

KEDA lee los atributos de la cola; no consume mensajes.

</details>

---

7. ¿Qué debe seleccionar la consulta que evalúa el éxito del canary?
   - A) Todo el tráfico estable y canary.
   - B) Solo la nueva revisión de la plantilla del pod.
   - C) Cada espacio de nombres.
   - D) Solo el promedio previo al Deployment.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo la nueva revisión de pod-template.**

No permita que un gran volumen de tráfico estable oculte los fallos del canary.

</details>

---

8. ¿Cómo se deben tratar los resultados vacíos/NaN/Inf?
   - A) Siempre como un éxito del 100 %.
   - B) No deben cumplir la condición de éxito.
   - C) Convertirlos todos a cero y aprobarlos.
   - D) Las métricas son innecesarias.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) No deben cumplir la condición de éxito.**

Compruebe conjuntamente los recuentos mínimos de solicitudes y la observabilidad.

</details>

---

9. ¿Qué etiquetas conviene incluir en las métricas?
   - A) Cada ID de pedido.
   - B) Servicio, ruta con cardinalidad acotada, estado y revisión.
   - C) Datos de cliente/tarjeta.
   - D) El cuerpo completo de la solicitud.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Service, ruta acotada, estado y revisión.**

Los ID únicos generan problemas de cardinalidad y privacidad; correlacione mediante trazas y registros según sea necesario.

</details>

---

10. ¿Qué implica abortar un Rollout?
   - A) Git revierte los cambios automáticamente.
   - B) No revierte los cambios en Git ni restaura la imagen declarada; restaure explícitamente la fuente de verdad.
   - C) Todas las escrituras de DB se revierten.
   - D) La nueva imagen se elimina permanentemente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es independiente de la reversión de Git o la restauración de la imagen deseada; restaure explícitamente la fuente de verdad.**

No gestione el mismo recurso directamente con Helm y mediante ArgoCD a la vez.

</details>

---

[Volver a la guía](../../../labs/observability/03-msa-deployment-lab.md)
