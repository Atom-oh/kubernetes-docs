# Cuestionario sobre estado, checkpoints y patrones de streaming

Distingue las combinaciones de versiones de Flink/Kafka y Flink/Iceberg del capítulo.

1. ¿Elegir RocksDB elimina las preocupaciones sobre el heap, la GC y el dimensionamiento de la memoria?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Las cachés nativas, la memoria administrada, los objetos del usuario, el estado de operadores y los búferes siguen consumiendo recursos.

**Explicación:** Los backends de operadores con claves pueden compartir un presupuesto de memoria del slot. Mide las cargas de trabajo, el estado y los checkpoints/restauraciones; no uses un umbral fijo en MB.

</details>

2. ¿Las instantáneas incrementales son exclusivas de RocksDB en Flink 2.2?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. ForSt, que es experimental, también usa instantáneas incrementales asíncronas.

**Explicación:** Comprueba su modelo de SST remoto y caché local, además de las limitaciones de API e instantáneas. El ejemplo de configuración del capítulo usa RocksDB.

</details>

3. ¿El tamaño de carga de un checkpoint incremental depende solo de los cambios lógicos en las claves?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Persiste SST y metadatos nuevos, y la compactación puede volver a escribir archivos grandes.

**Explicación:** Se hace referencia a los SST compartidos que se pueden reutilizar. Si vencen archivos a los que todavía se hace referencia, puede fallar la recuperación.

</details>

4. ¿La restauración incremental vuelve a procesar secuencialmente todos los checkpoints anteriores?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Restaura los archivos a los que hace referencia el checkpoint seleccionado.

**Explicación:** Los checkpoints completos no necesariamente son archivos únicos. La recuperación depende de la red, el número de archivos, la E/S y el costo de reconstruir el estado canónico.

</details>

5. ¿Un savepoint siempre es permanente hasta que alguien lo elimina manualmente?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. La retención/eliminación del operador y la propiedad CLAIM/NO_CLAIM afectan a su ciclo de vida.

**Explicación:** Los checkpoints también pueden tener activadores explícitos y retención externa. Comprueba el almacenamiento, las referencias y quién es responsable de la eliminación.

</details>

6. ¿El último estado del operador siempre usa un solo archivo de último checkpoint?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** La recuperación depende de que estén accesibles los metadatos de HA o el último checkpoint/savepoint, y de la ruta aplicable.

**Explicación:** Se requieren metadatos válidos, compatibilidad del estado, UID y serializadores; la etiqueta por sí sola no garantiza la recuperación ni una migración segura.

</details>

7. ¿Qué requieren las garantías EXACTLY_ONCE de Kafka de los checkpoints y consumidores?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** La confirmación de transacciones se coordina con la finalización del checkpoint, y los consumidores posteriores deben usar `read_committed`.

**Explicación:** También se necesitan fuentes reproducibles y estado recuperable. Los distintos sinks o todos los subtasks no se convierten en una transacción global única.

</details>

8. ¿Cuándo debería ser único `transactionalIdPrefix` y cuándo debería permanecer estable?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Debe ser único entre sinks/trabajos independientes y concurrentes, y estable al reiniciar la misma ejecución lógica.

**Explicación:** Las colisiones pueden provocar fencing, mientras que los cambios pueden retrasar la limpieza de transacciones persistentes y el avance de consumidores.

</details>

9. ¿Un intervalo de checkpoint de 60 segundos limita a 60 segundos la latencia añadida de Kafka?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. También influyen la duración del checkpoint, las confirmaciones, los fallos y la recuperación, y el retraso del consumidor.

**Explicación:** Ajusta el tiempo de espera de la transacción a los límites del broker y a la peor recuperación prevista. El builder 5.0.0 tiene un valor predeterminado de una hora.

</details>

10. ¿Todas las estrategias para nombrar transacciones del conector Kafka crean un ID nuevo cada vez?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. `POOLING` es una opción que reutiliza nombres; el valor predeterminado es `INCREMENTING`.

**Explicación:** `POOLING` requiere Kafka 3 o posterior, permisos adicionales de lectura de temas y comprobaciones de migración. Mide por separado la carga de confirmaciones frecuentes.

</details>

11. ¿Qué combinación real de API de DynamicIcebergSink y runtime se comprobó?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** `forInput` → `generator` → `catalogLoader` → `append`; Iceberg 1.11.0 con Flink 2.1.3.

**Explicación:** El generador emite DynamicRecords a un Collector. El JAR del runtime de Flink 2.1 no se presenta como validado con Flink 2.2.1.

</details>

12. ¿El helper de Iceberg dinámico que solo inserta puede servir sin cambios como procesador de CDC de Debezium?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Valida RowKind, los campos de igualdad, upsert, formatos de tablas y los límites de evolución de esquemas.

**Explicación:** También hay que comprobar en las alternativas administradas de Firehose/MSK Connect el origen, los permisos, las claves, los formatos, el búfer y el manejo de fallos.

</details>

13. ¿Declarar una columna `event_time TIMESTAMP` basta para la consulta SQL de ventanas?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Una ventana de tiempo de evento en streaming necesita un atributo temporal; el ejemplo declara un WATERMARK.

**Explicación:** El planificador revisado rechaza la variante con una marca de tiempo simple que no lo tenga. También se necesitan los JAR del conector/formato.

</details>

14. ¿Qué límites específicos de versión se aplican al plugin S3 y a la demostración incluida?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** El plugin incluye AWS SDK v1.12.779, que llegó al fin de soporte; `StateMachineExample` establece en el código un intervalo de checkpoint de dos segundos.

**Explicación:** No mezcles a ciegas las clases de proveedor v2. Revisa `min-pause` y las sobrescrituras de la aplicación en lugar de inferir el intervalo solo de la configuración.

</details>

15. ¿Los registros tardíos posteriores a un watermark siempre se descartan o se envían automáticamente a una salida lateral?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Los watermarks estiman el avance; las ventanas pueden volver a emitirse durante el período de tardanza permitido.

**Explicación:** Enviar a una salida lateral después de la limpieza requiere configuración explícita. Comprueba la extracción de marcas de tiempo, la inactividad y las diferencias entre SQL y DataStream.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/flink/03-state-checkpointing-streaming.md)
