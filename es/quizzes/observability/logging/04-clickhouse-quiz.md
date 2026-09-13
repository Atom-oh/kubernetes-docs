# Cuestionario de ClickHouse para análisis de logs

> **Última actualización**: September 13, 2026

1. ¿Por qué el almacenamiento columnar puede ayudar a las consultas analíticas de logs?

   - A) Siempre analiza cada campo
   - B) Puede leer columnas seleccionadas y comprimir valores repetidos
   - C) Garantiza una proporción de compresión fija
   - D) Elimina la necesidad de diseñar el esquema

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede leer columnas seleccionadas y comprimir valores repetidos**

Los beneficios dependen de los datos, la clave de ordenación y la consulta. La guía no promete una compresión de 10:1 ni un rendimiento fijo.

</details>

---

2. ¿Cuál es el rol de Keeper/ZooKeeper en este diseño?

   - A) Ejecutar cada SELECT distribuido
   - B) Almacenar cada fila de logs
   - C) Coordinar tablas replicadas y DDL distribuido
   - D) Reemplazar al colector

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Coordinar tablas replicadas y DDL distribuido**

Los iniciadores de consultas de ClickHouse y las tablas Distributed realizan consultas distribuidas. Keeper no es su enrutador de consultas.

</details>

---

3. ¿Qué motor añade replicación al almacenamiento MergeTree?

   - A) ReplicatedMergeTree
   - B) Memory
   - C) Buffer
   - D) Distributed por sí solo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) ReplicatedMergeTree**

Las réplicas aún necesitan coordinación, almacenamiento persistente independiente y un diseño adecuado de dominio de fallos. La replicación por sí sola no es una garantía incondicional de HA.

</details>

---

4. ¿Qué tipo vale la pena evaluar para valores repetidos de namespace o gravedad?

   - A) Siempre FixedString(255)
   - B) LowCardinality(String)
   - C) Un entero único para cada mensaje de log
   - D) Solo String sin comprimir

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) LowCardinality(String)**

La codificación de diccionario puede ayudar con valores repetidos; evalúe el tamaño del diccionario y el comportamiento de las consultas en lugar de asumir un límite universal de valores distintos.

</details>

---

5. ¿Cómo se debe elegir el ORDER BY de la tabla de logs?

   - A) Alfabéticamente
   - B) Por el momento de creación del campo
   - C) A partir de filtros selectivos, localidad y consultas representativas
   - D) Siempre colocar timestamp al final independientemente de las consultas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) A partir de filtros selectivos, localidad y consultas representativas**

La clave afecta la ordenación y la poda de índices. Las columnas consultadas con frecuencia por sí solas no determinan el mejor orden.

</details>

---

6. ¿Qué debe ser cierto antes de usar SAMPLE 0.1?

   - A) Cualquier tabla lo admite automáticamente
   - B) La tabla debe contener exactamente diez filas
   - C) Siempre devuelve exactamente el 10 % de las filas
   - D) Debe definirse una expresión de muestreo MergeTree compatible e incluirse en la clave primaria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Debe definirse una expresión de muestreo MergeTree compatible e incluirse en la clave primaria**

La tabla principal de logs no tiene SAMPLE BY. El sample_demo independiente muestra el diseño requerido. Un intervalo determinista de clave de muestreo no tiene por qué contener exactamente el 10 % de un conjunto finito de filas.

</details>

---

7. ¿Qué añade Kafka, sujeto a su configuración?

   - A) Entrega exactamente una vez garantizada mediante un Buffer en memoria
   - B) Búfer para ráfagas y reproducción dentro de la retención
   - C) Eliminación automática de todos los errores del parser
   - D) Almacenamiento ilimitado durante interrupciones

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Búfer para ráfagas y reproducción dentro de la retención**

Se deben probar la retención, los acknowledgements, la replicación, la capacidad, las confirmaciones de offset y el comportamiento de las inserciones posteriores. Un Buffer en memoria puede perder datos confirmados tras un fallo.

</details>

---

8. ¿Por qué usar una extracción JSON nullable para response_time_ms opcional?

   - A) Las mediciones ausentes no deben convertirse en solicitudes de latencia cero
   - B) Todos los logs son solicitudes HTTP
   - C) Elimina la necesidad de validación JSON
   - D) Cambia el reloj del servidor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) Las mediciones ausentes no deben convertirse en solicitudes de latencia cero**

Primero compruebe JSONType para excluir booleanos y cadenas numéricas, y después extraiga un número nullable. La extracción nullable por sí sola puede convertir esos valores. Las consultas de recuento y percentiles deben usar eventos medidos.

</details>

---

9. ¿Qué requiere y garantiza una cláusula TTL TO VOLUME?

   - A) Crea un bucket de S3 y un rol de IAM
   - B) Elimina cada fila en un plazo exacto de reloj de pared
   - C) Una política de almacenamiento seleccionada existente; trabajo asíncrono en segundo plano
   - D) Hace que las partes frías sean copias de seguridad Parquet independientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Una política de almacenamiento seleccionada existente; trabajo asíncrono en segundo plano**

TTL no puede crear la política ni los permisos de cloud. El almacenamiento de tablas frías y un archivo Parquet validado por separado tienen distinta propiedad y semántica de recuperación.

</details>

---

10. ¿Cómo se deben crear las alertas de Grafana respaldadas por ClickHouse?

   - A) Inventar una métrica Prometheus clickhouse_custom_query
   - B) Usar grafana-clickhouse-datasource con resultados SQL numéricos y Grafana Alerting
   - C) Dar a cada dashboard una cuenta de administrador
   - D) Considerar la ausencia de logs entrantes como prueba de estado saludable

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Usar grafana-clickhouse-datasource con resultados SQL numéricos y Grafana Alerting**

Use una cuenta restringida de solo lectura, TLS verificado y los permisos requeridos para la configuración de timeout. Supervise la ingesta por separado; un agregado puede devolver cero incluso sin entrada.

</details>

---

[Volver a la guía](../../../observability/logging/04-clickhouse.md)
