# Cuestionario de Grafana Tempo

Pon a prueba tus conocimientos sobre Grafana Tempo.

---

1. ¿Cuál es la característica principal de Grafana Tempo?
   - A) Indexa todos los datos para realizar búsquedas rápidas
   - B) Almacenamiento basado en TraceID que elimina los costos de indexación
   - C) Procesamiento de streaming en tiempo real
   - D) Detección automática de anomalías

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenamiento basado en TraceID que elimina los costos de indexación**

**Explicación:**
Tempo almacena y busca datos de trazas utilizando únicamente TraceID, sin indexación. Esto permite almacenar datos de trazas a gran escala a bajo costo. Otros sistemas de tracing indexan diversos campos para mejorar el rendimiento de las búsquedas, pero esto incrementa los costos de almacenamiento.

</details>

---

2. ¿Qué componente de la arquitectura de Tempo recibe y valida los datos de trazas?
   - A) Ingester
   - B) Querier
   - C) Distributor
   - D) Compactor

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Distributor**

**Explicación:**
El Distributor recibe datos de trazas en diversos formatos (Jaeger, Zipkin, OTLP, etc.) y los valida. Los datos validados se distribuyen a los Ingesters adecuados según el hashing. Los Ingesters almacenan datos en búfer y los guardan, mientras que los Queriers realizan las búsquedas.

</details>

---

3. ¿Cuál es la consulta TraceQL correcta para recuperar únicamente spans con estado de error?
   - A) `{ error = true }`
   - B) `{ status = error }`
   - C) `{ span.error = 1 }`
   - D) `{ state = "ERROR" }`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) { status = error }**

**Explicación:**
En TraceQL, utiliza la sintaxis `{ status = error }` para filtrar spans de error. El campo status puede tener los valores ok, error o unset, que se corresponden con SpanStatus de OpenTelemetry.

</details>

---

4. ¿Cuál es el método de autenticación de AWS recomendado cuando se utiliza S3 como almacenamiento de backend de Tempo?
   - A) Almacenar la Access Key en variables de entorno
   - B) Almacenar las credenciales en Secret
   - C) IRSA (IAM Roles for Service Accounts)
   - D) EC2 Instance Profile

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) IRSA (IAM Roles for Service Accounts)**

**Explicación:**
Se recomienda IRSA en entornos EKS. IRSA vincula roles de IAM con ServiceAccounts de Kubernetes, lo que permite una administración de permisos detallada a nivel de Pod. Es más seguro que almacenar credenciales estáticas y la rotación de credenciales se gestiona automáticamente.

</details>

---

5. ¿Cuál NO es un tipo de métrica generado por Metrics Generator de Tempo?
   - A) Métricas de Service Graph
   - B) Métricas de Span
   - C) Métricas de logs
   - D) Métricas RED (Rate, Error, Duration)

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Métricas de logs**

**Explicación:**
Metrics Generator de Tempo genera métricas de Service Graph y métricas de Span (incluidas las métricas RED) a partir de datos de trazas. Estas métricas se envían a Prometheus y se utilizan para la visualización de mapas de servicios y la supervisión del rendimiento. Las métricas de logs las genera Loki y están fuera del alcance de Tempo.

</details>

---

6. ¿Cómo se llama la función del modo Distributed de Tempo que mantiene réplicas en varios Ingesters para garantizar la durabilidad de los datos?
   - A) Sharding
   - B) Replication Factor
   - C) Partitioning
   - D) Mirroring

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Replication Factor**

**Explicación:**
Replication Factor determina en cuántos Ingesters se replica cada traza. Por ejemplo, replication_factor=3 significa que cada traza se almacena en 3 Ingesters, por lo que no se pierden datos aunque falle un Ingester. Esta es una configuración importante para la alta disponibilidad de Tempo.

</details>

---

7. ¿Qué configuración se necesita para implementar la correlación Trace-to-Log integrando Tempo y Loki en Grafana?
   - A) Realizar el despliegue en el mismo namespace
   - B) Configurar derivedFields para extraer TraceID
   - C) Utilizar el mismo bucket de S3
   - D) Utilizar etiquetas idénticas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar derivedFields para extraer TraceID**

**Explicación:**
Configura derivedFields en los ajustes de la fuente de datos de Loki para extraer TraceID de los logs y crear enlaces a Tempo. Al hacer coincidir TraceID con un patrón regex y vincularlo a la fuente de datos de Tempo, puedes consultar trazas relacionadas directamente desde los logs.

</details>

---

8. ¿Cuál es la función del Compactor en Tempo?
   - A) Procesamiento de consultas en tiempo real
   - B) Recepción y distribución de datos de trazas
   - C) Compresión de bloques almacenados y aplicación de políticas de retención
   - D) Gestión de búferes de memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Compresión de bloques almacenados y aplicación de políticas de retención**

**Explicación:**
El Compactor comprime y optimiza los bloques de trazas almacenados en Object Storage. También aplica políticas de retención según la configuración block_retention para eliminar datos antiguos. El Compactor normalmente se ejecuta como una única instancia, con solo una activa por clúster.

</details>

---

9. ¿Cuál es la consulta TraceQL correcta para encontrar patrones de llamadas del Service A al Service B?
   - A) `{ resource.service.name = "A" } AND { resource.service.name = "B" }`
   - B) `{ resource.service.name = "A" } >> { resource.service.name = "B" }`
   - C) `{ resource.service.name = "A" } -> { resource.service.name = "B" }`
   - D) `{ resource.service.name = "A" } | { resource.service.name = "B" }`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) { resource.service.name = "A" } >> { resource.service.name = "B" }**

**Explicación:**
En TraceQL, el operador `>>` realiza una coincidencia estructural para encontrar casos en los que el span que coincide con la primera condición es un ancestro del span que coincide con la segunda condición. Esto permite analizar patrones de llamadas entre servicios. El operador `>` coincide únicamente con relaciones directas entre padre e hijo.

</details>

---

10. ¿Cuál NO es una configuración recomendada para optimizar el rendimiento de Tempo?
    - A) Establecer max_block_duration en 30 minutos
    - B) Utilizar Memcached como caché
    - C) Indexar todos los atributos
    - D) Habilitar query sharding en Query Frontend

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Indexar todos los atributos**

**Explicación:**
El principio de diseño fundamental de Tempo es minimizar la indexación para reducir los costos. Indexar todos los atributos anularía las ventajas de Tempo e incrementaría significativamente los costos de almacenamiento. En su lugar, optimiza el rendimiento ajustando max_block_duration, usando caché y aplicando query sharding.

</details>

---
