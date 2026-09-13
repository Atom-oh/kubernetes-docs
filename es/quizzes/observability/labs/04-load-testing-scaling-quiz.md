# Cuestionario del laboratorio de observabilidad, parte 4

> **Última actualización**: September 13, 2026

1. ¿Cómo se relacionan los VUs de k6 con las RPS?
   - A) Un VU siempre equivale a una RPS.
   - B) Los VUs son contextos de ejecución simultánea; las RPS también dependen de las solicitudes, la latencia y las pausas.
   - C) Los VUs equivalen al número de nodos.
   - D) Las RPS son independientes del tiempo de respuesta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Los VUs son contextos de ejecución simultánea; las RPS también dependen de las solicitudes, la latencia y las pausas.**

Tener el mismo número de VUs no implica el mismo rendimiento en distintas cargas de trabajo y esperas.

</details>

---

2. ¿Cómo deben hacer que fallen las comprobaciones fallidas de k6 en CI?
   - A) Llamar a check siempre termina con el código 1.
   - B) Configure un umbral de comprobaciones/tasa de fallos e inspeccione el código de salida.
   - C) Un archivo JSON de resumen demuestra que fue exitoso.
   - D) Cuente únicamente las respuestas HTTP 200.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configure un umbral de comprobaciones/tasa de fallos e inspeccione el código de salida.**

El éxito HTTP y el éxito del negocio son diferentes; valide también JSON, IDs y el estado del pago.

</details>

---

3. ¿Qué IDs de pedidos debe leer la prueba de carga?
   - A) IDs aleatorios del 1 al 1000.
   - B) IDs creados realmente por la prueba.
   - C) IDs de clientes.
   - D) Códigos de estado HTTP.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IDs creados realmente por la prueba.**

Use los IDs de la respuesta de creación para que los 404 aleatorios no contaminen la carga de trabajo.

</details>

---

4. ¿Qué debe escalar directamente con la acumulación de SQS?
   - A) Siempre únicamente el productor de la API.
   - B) El consumidor que procesa esa cola.
   - C) Réplicas de Alertmanager.
   - D) El nombre de la cola.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El consumidor que procesa esa cola.**

KEDA lee los atributos de la cola y administra el escalado con HPA; no consume mensajes.

</details>

---

5. ¿Cuándo se aplica cooldownPeriod de KEDA?
   - A) En cada cambio de 10 a 9 réplicas.
   - B) Al escalar a cero después del último trigger activo.
   - C) En el retraso de arranque de EC2.
   - D) En la retención de logs.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Al escalar a cero después del último trigger activo.**

Inspeccione el comportamiento de HPA y las ventanas de estabilización para el escalado dentro de 1..N réplicas.

</details>

---

6. ¿Qué hace una ventana de estabilización de reducción de escala de HPA?
   - A) Congela todos los nodos.
   - B) Considera la recomendación de réplicas más alta dentro de la ventana.
   - C) Usa únicamente la CPU instantánea.
   - D) Elimina un Pod en cada intervalo configurado.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Considera la recomendación de réplicas más alta dentro de la ventana.**

No es simplemente un retraso fijo incondicional; las políticas y el historial de recomendaciones importan.

</details>

---

7. ¿Qué problema puede abordar normalmente Karpenter?
   - A) Un nombre de imagen mal escrito.
   - B) Un Pod no programable que necesita capacidad compatible con su NodePool.
   - C) Un error de sintaxis de la aplicación.
   - D) Una contraseña incorrecta de la base de datos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un Pod no programable que necesita capacidad compatible con su NodePool.**

Más nodos no solucionan las descargas de imágenes ni los errores de la aplicación; primero inspeccione los motivos de programación.

</details>

---

8. ¿Qué mide kube_deployment_status_replicas?
   - A) Réplicas siempre listas.
   - B) El total de réplicas de Deployment, distinto de las réplicas listas.
   - C) Todas las réplicas del controlador, incluidos los Rollouts.
   - D) El número de nodos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El total de réplicas de Deployment, distinto de las réplicas listas.**

Use kube_deployment_status_replicas_ready para las réplicas listas; los Rollouts necesitan su propio estado/exporter.

</details>

---

9. ¿Cómo deben contarse los Pods Running a partir de las métricas de fase?
   - A) Cuente todas las series Running sin filtrar los valores.
   - B) Sume directamente los indicadores 0/1 de la fase Running.
   - C) Sume las longitudes de los nombres de los Pods.
   - D) Devuelva siempre tres.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sume directamente los indicadores 0/1 de la fase Running.**

Las series de la fase Running pueden existir con el valor cero, por lo que un recuento sin filtrar cuenta en exceso. Sumar los indicadores devuelve cero para todos los Pods Pending y permanece ausente cuando falta la telemetría.

</details>

---

10. ¿Qué constituye evidencia de un experimento de carga exitoso?
   - A) Una tabla copiada de números esperados de la documentación.
   - B) Solicitudes, errores, latencia, cola, réplicas, nodos y estado de salida medidos.
   - C) Creación exitosa de Job.
   - D) Únicamente un menor número de nodos.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solicitudes, errores, latencia, cola, réplicas, nodos y estado de salida medidos.**

No presente como resultados un rendimiento, disponibilidad o ahorro de costes sin medir.

</details>

---

[Volver a la guía](../../../labs/observability/04-load-testing-scaling-lab.md)
