# Cuestionario del laboratorio de Observability 03

<span id="observability-lab-part-3-msa-deployment-and-canary-quiz"></span>

> **Última actualización**: September 13, 2026

1. ¿Cuál es el límite de transacción de pedido/outbox?
   - A) Confirmar el pedido y luego ignorar los fallos de mensajería.
   - B) Ambos se confirman o se revierten en una transacción de DB.
   - C) SNS y DB son automáticamente atómicos.
   - D) Inicializar la DB para cada solicitud.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Ambos se confirman o se revierten en una transacción de DB.**

Valide la reversión de DB y la retención de registros de outbox no publicados.

</details>

---

2. ¿Quién es propietario de la carga de trabajo de payment?
   - A) Deployment y Rollout simultáneamente.
   - B) Un único Rollout.
   - C) KEDA y Rollout compiten por las réplicas.
   - D) Grafana.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un único Rollout.**

Mantenga explícitos la propiedad del controller y el estado deseado de Git.

</details>

---

3. ¿Por qué separar las queues de notification y analytics?
   - A) Competir en una queue es fanout.
   - B) Para que cada consumidor reciba de forma independiente el mismo evento.
   - C) SQS solo admite una queue.
   - D) Elimina todos los duplicados.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Para que cada consumidor reciba de forma independiente el mismo evento.**

El fanout de SNS y la deduplicación de event-ID de cada consumidor son responsabilidades independientes.

</details>

---

4. ¿Qué ocurre con un pago sintético idéntico repetido?
   - A) Crear siempre un nuevo pago.
   - B) Reutilizar el resultado almacenado; los valores conflictivos devuelven 409.
   - C) Cobrar una tarjeta real.
   - D) Tener éxito siempre, incluso sin un pedido.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reutilizar el resultado almacenado; los valores conflictivos devuelven 409.**

El laboratorio no implementa ninguna pasarela de pago real.

</details>

---

5. ¿Qué sucede si ocurre un fallo después de la publicación en SNS, pero antes de la marca en DB?
   - A) Exactamente una vez es automático.
   - B) Es posible una nueva entrega, por lo que los consumidores necesitan deduplicación.
   - C) Eliminar cada fila de outbox.
   - D) Confirmar siempre el mensaje.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es posible una nueva entrega, por lo que los consumidores necesitan deduplicación.**

Los efectos secundarios externos requieren contratos de idempotencia adicionales.

</details>

---

6. ¿Qué carga de trabajo se escala con el backlog de SQS?
   - A) Siempre solo el productor de API.
   - B) El consumidor de esa queue.
   - C) El administrador de la base de datos.
   - D) El NLB.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El consumidor de esa queue.**

KEDA lee atributos de la queue; no consume mensajes.

</details>

---

7. ¿Qué debe seleccionar la consulta de éxito de canary?
   - A) Todo el tráfico stable y canary.
   - B) Solo la nueva revisión de pod-template.
   - C) Cada namespace.
   - D) Solo el promedio previo al Deployment.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo la nueva revisión de pod-template.**

No permita que un gran volumen de tráfico stable oculte un canary con fallos.

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

Compruebe conjuntamente los conteos mínimos de solicitudes y la observability.

</details>

---

9. ¿Qué labels pertenecen a las métricas?
   - A) Cada ID de pedido.
   - B) Service, ruta acotada, estado y revisión.
   - C) Datos de cliente/tarjeta.
   - D) El cuerpo completo de la solicitud.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Service, ruta acotada, estado y revisión.**

Los ID únicos generan problemas de cardinalidad/privacidad; use la correlación de trace/log de forma adecuada.

</details>

---

10. ¿Qué significa abortar un Rollout?
   - A) Git revierte automáticamente.
   - B) Es independiente de la reversión de Git o la restauración de la imagen deseada; restaure explícitamente la fuente de verdad.
   - C) Todas las escrituras de DB se revierten.
   - D) La nueva imagen se elimina permanentemente.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Es independiente de la reversión de Git o la restauración de la imagen deseada; restaure explícitamente la fuente de verdad.**

No use Helm directo y ArgoCD como propietarios simultáneos.

</details>

---

[Volver a la guía](../../../labs/observability/03-msa-deployment-lab.md)
