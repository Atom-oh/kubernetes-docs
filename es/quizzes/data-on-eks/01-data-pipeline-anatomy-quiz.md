# Cuestionario sobre la anatomía de una canalización de datos moderna

> **Última actualización**: September 12, 2026

1. ¿Qué debe comprobarse antes de volver a procesar offsets de Kafka?
   - A) Si los registros necesarios siguen disponibles tras la retención/compactación
   - B) Si Kafka deduplica automáticamente todos los sinks externos
   - C) Si se eliminaron todas las entradas de procesamiento por lotes
   - D) Si todos los eventos permanecen siempre para siempre

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Si los registros necesarios siguen disponibles tras la retención/compactación**

Para volver a procesarlos se requieren datos de entrada retenidos y una recuperación coherente del estado. La semántica exactly-once de extremo a extremo también depende de las transacciones del sink, la idempotencia y los efectos externos.

</details>

2. ¿Qué distingue ETL de ELT?
   - A) Si se usa un data lake
   - B) ETL transforma los datos antes de cargarlos en el destino; ELT los transforma después de cargarlos
   - C) Si se usa Kafka
   - D) ELT siempre es exacto y ETL siempre es aproximado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ETL transforma los datos antes de cargarlos en el destino; ELT los transforma después de cargarlos**

Mover datos depurados a un data warehouse no convierte por sí solo el proceso en ELT. Compruebe el orden de transformación y el destino.

</details>

3. ¿Qué afirmación sobre la precisión del procesamiento por lotes y el streaming es correcta?
   - A) El streaming siempre es aproximado
   - B) El procesamiento por lotes siempre es exacto
   - C) Depende de los datos tardíos, los duplicados, el estado y los contratos de salida; los resultados provisionales rápidos pueden ir seguidos de una finalización
   - D) Los checkpoints hacen automáticamente que los efectos de una API externa sean exactly-once

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Depende de los datos tardíos, los duplicados, el estado y los contratos de salida; los resultados provisionales rápidos pueden ir seguidos de una finalización**

Diseñe el tiempo de evento, los watermarks, la latencia permitida y la semántica del sink. Spark y Flink no se limitan cada uno a un solo modo de procesamiento.

</details>

4. ¿Qué afirmación sobre las comprobaciones de compatibilidad de Schema Registry es correcta?
   - A) Bloquean automáticamente todos los cambios de DDL de bases de datos y de semántica
   - B) Validan las rutas de registro/serialización/CI donde se aplican, y aún hacen falta pruebas de consumidores
   - C) Un solo registro garantiza automáticamente la compatibilidad transitiva entre todas las versiones
   - D) Las reglas de compatibilidad eliminan la necesidad de comprobar la calidad de los datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Validan las rutas de registro/serialización/CI donde se aplican, y aún hacen falta pruebas de consumidores**

Las rutas que omiten esas comprobaciones y los cambios de semántica empresarial requieren validación aparte. Compruebe el alcance de la configuración de compatibilidad backward/forward y transitiva.

</details>

[Material de estudio](../../data-on-eks/01-data-pipeline-anatomy.md) | [Cuestionario de Kafka](./kafka/01-kafka-fundamentals-quiz.md)
