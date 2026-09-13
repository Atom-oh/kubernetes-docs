# Cuestionario de Amazon OpenSearch Service

> **Última actualización**: September 13, 2026

Basado en los ejemplos de dominio gestionado y de recolector de la [guía](../../../observability/logging/02-opensearch.md).

---

1. ¿Qué afirmación distingue correctamente OpenSearch de Amazon OpenSearch Service?

   - A) Todos los clientes/plugins de Elasticsearch siguen siendo compatibles
   - B) AWS admite de inmediato todas las versiones upstream
   - C) OpenSearch es un proyecto Apache-2.0; el servicio gestionado admite versiones del motor seleccionadas
   - D) El servicio es únicamente un producto de alojamiento de Kibana

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El linaje de Elasticsearch 7.10 no es una garantía general de compatibilidad. Verifique el soporte de versiones de AWS y el cliente/plugin concreto. La línea base anterior 2.11 sigue con soporte estándar hasta el 7 de noviembre de 2027.

</details>

---

2. Con nodos cluster-manager dedicados configurados, ¿qué rol se encarga de gestionar el estado del clúster y la asignación de shards?

   - A) Nodos cluster-manager dedicados
   - B) Almacenamiento UltraWarm
   - C) Almacenamiento en frío (cold storage)
   - D) El recolector de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Los campos de configuración de AWS todavía usan los nombres dedicated_master. El número de managers es distinto del número de réplicas de datos, y la zone awareness por sí sola no habilita Multi-AZ with Standby.

</details>

---

3. ¿Qué afirmación es correcta para el UltraWarm tradicional y el almacenamiento en frío?

   - A) UltraWarm almacena todo únicamente en EBS
   - B) Ambos están respaldados por S3; los índices en frío deben adjuntarse a UltraWarm antes de poder consultarse
   - C) Toda carga de trabajo ahorra exactamente un 75 %
   - D) Todas las combinaciones de instancia/motor admiten ambos niveles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Una política hot→UltraWarm→cold requiere los prerrequisitos de servicio correspondientes y capacidad de migración. Los costos y la latencia de consulta dependen de la carga de trabajo; los nombres de los niveles no son garantías fijas de ahorro.

</details>

---

4. ¿Qué acción de ISM elimina un índice del almacenamiento en frío de OpenSearch Service gestionado?

   - A) delete en todos los niveles de almacenamiento
   - B) force_merge
   - C) warm_migration
   - D) cold_delete

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El almacenamiento en frío gestionado requiere cold_delete. Las políticas usan una acción por objeto de acción y se ejecutan de forma asíncrona; las edades de índice de 7/30/90 días del ejemplo no son garantías exactas de retención según la edad del evento.

</details>

---

5. ¿Cómo se deben comparar la entrega directa con Fluent Bit y Amazon Data Firehose?

   - A) Firehose es siempre la opción más económica
   - B) Fluent Bit directo no puede autenticarse ante AWS
   - C) Compare las necesidades operativas, el esquema, el buffering/retry/backup, el acceso y el costo medido
   - D) Ambos crean automáticamente metadatos de Kubernetes idénticos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Firehose ofrece una ruta de entrega gestionada, pero requiere roles, conectividad y registros compatibles. FailedDocumentsOnly selecciona su modo de backup; un prefijo llamado failed/ por sí solo no selecciona ese comportamiento.

</details>

---

6. ¿Qué afirmación describe correctamente DLS y FLS?

   - A) DLS filtra documentos; FLS controla los campos devueltos, y los roles efectivos y los metadatos de confianza siguen siendo importantes
   - B) FLS autentica automáticamente el namespace de Kubernetes
   - C) El IAM basado en URI por sí solo restringe todos los índices nombrados dentro de un cuerpo bulk
   - D) Una regla de security group otorga acceso de lectura a nivel de documento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

La guía usa metadatos de confianza kubernetes.namespace_name. Un rol restringido no cancela una concesión más amplia existente. FLS no redacta el texto sensible dentro de un mensaje permitido ni elimina los datos o backups almacenados.

</details>

---

7. ¿Qué tipo de cadena mapeado admite coincidencia exacta y las agregaciones de campo habituales?

   - A) text sin subcampo
   - B) keyword
   - C) LowCardinality como tipo de OpenSearch
   - D) Solo campos sin mapear

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Keyword se diferencia del text analizado y de LowCardinality de ClickHouse. Muchas agregaciones de keyword/numéricas usan doc values orientados a columnas, por lo que no escanean universalmente cada documento _source completo.

</details>

---

8. Con Logstash_Format On y el prefijo logs-production, ¿dónde escribe la salida de Fluent Bit que se ilustra?

   - A) Siempre en un alias de rollover
   - B) Automáticamente en una colección Serverless
   - C) Directamente en índices en frío desvinculados
   - D) En índices basados en fecha logs-production-YYYY.MM.DD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Un alias no se selecciona simplemente porque exista. La guía separa la ruta de índices diarios de rollover-logs-*, que necesita la configuración de alias de rollover, un índice numerado y el alias de escritura.

</details>

---

9. ¿Qué Query DSL filtra las líneas de log de error mapeadas de la última hora?

   - A) `{"query":{"match":{"app.level":"error","time":"1h"}}}`
   - B) `{"filter":{"app.level":"error","time":"last-hour"}}`
   - C) `{"query":{"bool":{"filter":[{"term":{"app.level":"error"}},{"range":{"@timestamp":{"gte":"now-1h"}}}]}}}`
   - D) `{"query":{"where":{"level":"error"}}}`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El mapeo del ejemplo anida los campos de la aplicación bajo app y usa @timestamp. El contexto de filtro combina la coincidencia exacta de keyword con un rango temporal sin requerir puntuación de relevancia.

</details>

---

10. ¿Cuál es una base sólida para elegir OpenSearch, Loki o ClickHouse para cargas de trabajo de logs?

   - A) Un umbral universal de cambio a los 100 GB/día
   - B) La afirmación de que todas las organizaciones tienen la misma mezcla de consultas
   - C) Reglas fijas de costo 3–5× y de ahorro del 60–80 %
   - D) Consultas representativas junto con retención, durabilidad, permisos, capacidad operativa y costo medido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Los tres tienen modelos de indexación/consulta y compromisos operativos diferentes. Compare requisitos equivalentes y valide la migración, la reconciliación y el rollback; ningún producto establece automáticamente el cumplimiento normativo ni el costo mínimo.

</details>
