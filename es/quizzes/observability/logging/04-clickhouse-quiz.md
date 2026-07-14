# Cuestionario de ClickHouse para análisis de logs

Pon a prueba tus conocimientos sobre el análisis de logs con ClickHouse.

---

1. ¿Cuál es la razón principal por la que ClickHouse muestra un alto rendimiento en el análisis de logs?

   - A) Almacenamiento basado en filas
   - B) Almacenamiento basado en columnas
   - C) Almacenamiento basado en documentos
   - D) Almacenamiento Key-Value

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenamiento basado en columnas**

**Explicación:**
ClickHouse es una base de datos basada en columnas optimizada para consultas analíticas (que escanean solo columnas específicas). Los mismos tipos de datos se almacenan de forma consecutiva, lo que permite altas tasas de compresión y la ejecución de consultas vectorizadas.

</details>

---

2. ¿Qué componente se utiliza para la replicación de datos y la coordinación de consultas distribuidas en un clúster de ClickHouse?

   - A) Kafka
   - B) Redis
   - C) ZooKeeper/ClickHouse Keeper
   - D) etcd

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) ZooKeeper/ClickHouse Keeper**

**Explicación:**
Los clústeres de ClickHouse usan ZooKeeper o ClickHouse Keeper para coordinar la sincronización de datos entre réplicas, la ejecución de DDL distribuido y la elección de líder. ClickHouse Keeper es una alternativa a ZooKeeper específica de ClickHouse.

</details>

---

3. ¿Qué motor de tablas de ClickHouse admite replicación y es el más adecuado para el almacenamiento de logs?

   - A) MergeTree
   - B) ReplicatedMergeTree
   - C) Log
   - D) Memory

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ReplicatedMergeTree**

**Explicación:**
ReplicatedMergeTree añade la funcionalidad de replicación a todas las características de MergeTree (ordenamiento, particionamiento, TTL, etc.). Se recomienda para el almacenamiento de logs de producción que requiere alta disponibilidad.

</details>

---

4. ¿Qué tipo de optimización se debe usar para columnas de cadenas de baja cardinalidad (por ejemplo, level, namespace) en ClickHouse?

   - A) String
   - B) FixedString
   - C) LowCardinality(String)
   - D) Enum

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) LowCardinality(String)**

**Explicación:**
LowCardinality(String) se utiliza para columnas de cadenas con pocos valores únicos (~10,000 o menos). Usa codificación de diccionario internamente para optimizar el espacio de almacenamiento y el rendimiento de las consultas.

</details>

---

5. ¿Cuál es el principio para especificar el orden de las columnas en la cláusula `ORDER BY` al diseñar tablas de logs de ClickHouse?

   - A) Orden alfabético
   - B) Orden por tamaño de columna (primero las más pequeñas)
   - C) Primero las columnas filtradas con frecuencia
   - D) Orden por hora de creación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Primero las columnas filtradas con frecuencia**

**Explicación:**
El ORDER BY de ClickHouse afecta el ordenamiento de datos y la creación de índices. Colocar al principio las columnas que se usan con frecuencia en las cláusulas WHERE da como resultado el escaneo de menos datos durante las consultas. Ejemplo: `ORDER BY (namespace, service, timestamp)`

</details>

---

6. ¿Cuál es la sintaxis de las técnicas de muestreo utilizadas para el análisis rápido de conjuntos de datos grandes en ClickHouse?

   - A) `LIMIT RANDOM 10%`
   - B) `SAMPLE 0.1`
   - C) `WHERE rand() < 0.1`
   - D) `TABLESAMPLE (10 PERCENT)`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `SAMPLE 0.1`**

**Explicación:**
La cláusula `SAMPLE` de ClickHouse escanea solo una parte de los datos para realizar análisis aproximados rápidos. `SAMPLE 0.1` lee solo el 10 % de los datos. Los resultados se pueden multiplicar por un factor apropiado para obtener totales estimados.

</details>

---

7. ¿Cuál es la razón principal para colocar Kafka entre las fuentes de logs y ClickHouse para la recopilación de logs?

   - A) Cifrado de datos
   - B) Almacenamiento en búfer y gestión de picos de tráfico
   - C) Compresión de datos
   - D) Optimización de consultas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenamiento en búfer y gestión de picos de tráfico**

**Explicación:**
Kafka funciona como una cola de mensajes que almacena en búfer los logs durante los picos de tráfico, lo que permite a ClickHouse consumir datos a una velocidad constante. También evita la pérdida de datos durante fallos de ClickHouse.

</details>

---

8. ¿Qué funciones se utilizan para extraer valores de campos JSON en ClickHouse SQL?

   - A) JSON_EXTRACT()
   - B) JSONExtractString(), JSONExtractFloat()
   - C) parseJSON()
   - D) getJSON()

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) JSONExtractString(), JSONExtractFloat()**

**Explicación:**
ClickHouse extrae campos JSON usando funciones como `JSONExtractString(json, 'field')` y `JSONExtractFloat(json, 'field')`. Se utilizan funciones diferentes para cada tipo.

</details>

---

9. ¿Qué característica de las tablas de ClickHouse elimina automáticamente los datos antiguos?

   - A) AUTO_DELETE
   - B) RETENTION_POLICY
   - C) TTL (Time To Live)
   - D) EXPIRE_AFTER

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) TTL (Time To Live)**

**Explicación:**
La característica TTL de ClickHouse elimina automáticamente los datos después de un período determinado o los mueve a un almacenamiento diferente (por ejemplo, S3). Ejemplo: `TTL date + INTERVAL 90 DAY DELETE`

</details>

---

10. ¿Qué plugin de fuente de datos se utiliza al integrar ClickHouse con Grafana?

    - A) grafana-mysql-datasource
    - B) grafana-clickhouse-datasource
    - C) grafana-sql-datasource
    - D) grafana-olap-datasource

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) grafana-clickhouse-datasource**

**Explicación:**
Para integrar ClickHouse con Grafana, instala el plugin `grafana-clickhouse-datasource`. Este plugin permite visualizar datos de ClickHouse mediante consultas SQL y crear dashboards.

</details>
