# Cuestionario de Grafana Loki

Pon a prueba tus conocimientos sobre Grafana Loki.

---

1. ¿Cuál es la razón principal por la que Loki es más rentable que Elasticsearch?

   - A) Rendimiento de consultas más rápido
   - B) Indexa solo labels en lugar del contenido de los logs
   - C) Usa mejores algoritmos de compresión
   - D) Diseño cloud-native

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Indexa solo labels en lugar del contenido de los logs**

**Explicación:**
Loki no indexa el contenido de los logs, solo los metadatos (labels). Esto reduce significativamente el tamaño del índice y permite el uso de almacenamiento de objetos económico (como S3), lo que permite que las operaciones sean 10 veces más económicas en comparación con Elasticsearch.

</details>

---

2. ¿Qué componente de la arquitectura de Loki almacena en búfer los datos de logs en memoria y los guarda en el almacenamiento?

   - A) Distributor
   - B) Querier
   - C) Ingester
   - D) Compactor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Ingester**

**Explicación:**
El Ingester recibe datos de logs del Distributor, los almacena en búfer en memoria (creando chunks), administra WAL y descarga los chunks al almacenamiento. También atiende consultas en tiempo real.

</details>

---

3. ¿Cuál es el modo de implementación de Loki recomendado para entornos EKS de producción?

   - A) Modo monolítico
   - B) Modo Simple Scalable
   - C) Modo Microservices
   - D) Modo independiente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Modo Simple Scalable**

**Explicación:**
El modo Simple Scalable separa las rutas de lectura/escritura para lograr escalabilidad, a la vez que es más sencillo de operar que el modo Microservices. Es adecuado para la mayoría de los clusters EKS de producción con volúmenes diarios de logs de 100 GB a 10 TB.

</details>

---

4. ¿Cuál es la consulta LogQL correcta para calcular la tasa por segundo de logs de error?

   - A) `count({app="nginx"} |= "error")`
   - B) `rate({app="nginx"} |= "error" [5m])`
   - C) `sum({app="nginx"} |= "error")`
   - D) `avg({app="nginx"} |= "error" [5m])`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `rate({app="nginx"} |= "error" [5m])`**

**Explicación:**
La función `rate()` calcula el recuento de líneas de logs por segundo durante el intervalo de tiempo especificado. `[5m]` indica un intervalo de 5 minutos. `count()` no se utiliza de esta manera en las consultas de métricas, y `sum()` y `avg()` no se utilizan de forma independiente como en este caso.

</details>

---

5. ¿Cuál es un ejemplo de un label de alta cardinalidad que se debe evitar en el diseño de labels de Loki?

   - A) namespace
   - B) app
   - C) pod_name
   - D) environment

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) pod_name**

**Explicación:**
pod_name puede tener miles de valores únicos, lo que lo convierte en un label de alta cardinalidad. Los labels de alta cardinalidad incrementan drásticamente el número de streams, lo que genera tamaños de índice más grandes y un mayor uso de memoria. namespace, app y environment normalmente tienen decenas de valores o menos, lo que los hace adecuados.

</details>

---

6. ¿Cuál es el método de autenticación recomendado para el acceso al backend S3 de Loki en EKS?

   - A) Access Key ID/Secret Access Key
   - B) IAM Roles for Service Accounts (IRSA)
   - C) EC2 Instance Profile
   - D) AWS STS AssumeRole

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) IAM Roles for Service Accounts (IRSA)**

**Explicación:**
IRSA vincula roles de IAM con service accounts de Kubernetes, lo que elimina la necesidad de almacenar Access Keys en código o configuración. Es el enfoque recomendado más seguro y cuenta con soporte nativo en entornos EKS.

</details>

---

7. ¿Cuál es la sintaxis LogQL correcta para filtrar por un valor de campo específico después de analizar logs JSON?

   - A) `{app="api"} | json | level="error"`
   - B) `{app="api"} | json | filter level="error"`
   - C) `{app="api"} | json | where level="error"`
   - D) `{app="api"} | json | select level="error"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) `{app="api"} | json | level="error"`**

**Explicación:**
En LogQL, los filtros de labels después del análisis de JSON usan el formato `| field_name="value"`. `filter`, `where` y `select` no forman parte de la sintaxis de LogQL.

</details>

---

8. ¿Cuál NO es una función principal del Compactor de Loki?

   - A) Fusionar chunks pequeños en chunks más grandes
   - B) Aplicar políticas de retención (eliminación de datos)
   - C) Recibir logs de los clientes
   - D) Optimización del índice

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Recibir logs de los clientes**

**Explicación:**
Recibir logs de los clientes es la función del Distributor. El Compactor optimiza los datos almacenados en segundo plano y elimina los datos antiguos según las políticas de retención.

</details>

---

9. ¿Qué configuraciones se deben ajustar al encontrar errores de "rate limit exceeded" en Loki?

   - A) max_streams_per_user
   - B) ingestion_rate_mb, ingestion_burst_size_mb
   - C) max_query_parallelism
   - D) chunk_idle_period

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) ingestion_rate_mb, ingestion_burst_size_mb**

**Explicación:**
Los errores de "rate limit exceeded" ocurren cuando la tasa de ingestión de logs supera el límite. Esto puede resolverse aumentando `ingestion_rate_mb` (ingestión máxima por segundo) y `ingestion_burst_size_mb` (capacidad de ráfaga).

</details>

---

10. ¿Qué significa la configuración `chunk_idle_period` del Ingester en el ajuste de rendimiento de Loki?

    - A) Tiempo desde la creación de un chunk hasta su eliminación
    - B) Tiempo que espera un stream inactivo antes de descargarse
    - C) Duración del tiempo de espera de la consulta
    - D) Período de retención de logs

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Tiempo que espera un stream inactivo antes de descargarse**

**Explicación:**
`chunk_idle_period` es el tiempo de espera antes de descargar un chunk al almacenamiento cuando no llegan nuevos logs para ese stream. Reducir este valor disminuye el uso de memoria, pero puede crear muchos chunks pequeños.

</details>
