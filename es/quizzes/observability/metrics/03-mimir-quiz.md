# Cuestionario de Grafana Mimir

Un cuestionario para poner a prueba tu comprensión de Grafana Mimir.

---

1. ¿Cuál es el backend de almacenamiento principal de Grafana Mimir?
   - A) Solo SSD local
   - B) Almacenamiento de objetos (S3, GCS, Azure Blob)
   - C) Almacenamiento compartido NFS
   - D) Solo almacenamiento en bloques

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenamiento de objetos (S3, GCS, Azure Blob)**

**Explicación:**
Grafana Mimir requiere almacenamiento de objetos. Admite S3, Google Cloud Storage, Azure Blob Storage, etc., proporcionando escalabilidad ilimitada y almacenamiento a largo plazo rentable. El almacenamiento local solo se utiliza para el WAL de Ingester y los datos temporales.

</details>

---

2. ¿Cuál es el rol de Distributor en la arquitectura de Mimir?
   - A) Almacenamiento de datos a largo plazo
   - B) Primer punto de entrada para las solicitudes de escritura, validación de tenants y distribución de samples
   - C) Caché de resultados de consultas
   - D) Compactación de bloques

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Primer punto de entrada para las solicitudes de escritura, validación de tenants y distribución de samples**

**Explicación:**
Distributor es el primer punto de entrada para las solicitudes de escritura y se encarga de la validación de ID de tenant, la validación de series temporales, la distribución de Ingester basada en hash ring y la replicación según el factor de replicación. Es un componente sin estado que se escala horizontalmente con facilidad.

</details>

---

3. ¿Cómo se implementa la multitenencia en Mimir?
   - A) Operar clusters independientes por tenant
   - B) Identificar tenants mediante el encabezado X-Scope-OrgID
   - C) Separación de tenants basada en direcciones IP
   - D) Separación de tenants basada en Namespace

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Identificar tenants mediante el encabezado X-Scope-OrgID**

**Explicación:**
Mimir identifica tenants mediante el encabezado HTTP `X-Scope-OrgID`. Agregar este encabezado a la configuración de remote_write de Prometheus aísla los datos de cada tenant. Se pueden configurar límites por tenant y los datos se separan mediante rutas de tenant en el almacenamiento de objetos.

</details>

---

4. ¿Por qué Ingester de Mimir carga bloques en el almacenamiento de objetos?
   - A) Mejorar el rendimiento de las consultas en tiempo real
   - B) Persistir los datos de la memoria en disco
   - C) Almacenar reglas de alertas
   - D) Respaldar la configuración de dashboards

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Persistir los datos de la memoria en disco**

**Explicación:**
Ingester primero almacena en memoria los datos de series temporales recibidos y, después, crea periódicamente (el valor predeterminado es 2 horas) bloques TSDB y los carga en el almacenamiento de objetos. Esto garantiza que los datos se almacenen de forma permanente y minimiza la pérdida de datos incluso si falla un Ingester.

</details>

---

5. ¿Cuál es el rol correcto de Compactor de Mimir?
   - A) Procesamiento de consultas en tiempo real
   - B) Combinar bloques pequeños en bloques grandes y eliminar duplicados
   - C) Recopilación de métricas
   - D) Transmisión de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Combinar bloques pequeños en bloques grandes y eliminar duplicados**

**Explicación:**
Compactor combina (compacta) bloques pequeños del almacenamiento de objetos en bloques más grandes, elimina los datos duplicados y borra datos antiguos según las políticas de retención. Esto mejora el rendimiento de las consultas y reduce los costos de almacenamiento.

</details>

---

6. ¿Cuál NO es una función proporcionada por Query-frontend de Mimir?
   - A) División de consultas grandes
   - B) Caché de resultados
   - C) Almacenamiento de datos
   - D) Reintentos de consultas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Almacenamiento de datos**

**Explicación:**
Query-frontend es un componente sin estado responsable de la optimización de consultas y el almacenamiento en caché. Divide las consultas grandes en consultas más pequeñas, almacena en caché los resultados y vuelve a intentar las consultas fallidas. El almacenamiento de datos es gestionado por Ingester (a corto plazo) y el almacenamiento de objetos (a largo plazo).

</details>

---

7. Al comparar Mimir con VictoriaMetrics, ¿cuál es una característica correcta de Mimir?
   - A) Solo hay disco local disponible
   - B) Menor complejidad operativa
   - C) Almacenamiento de objetos obligatorio, multitenencia de nivel empresarial
   - D) Usa el lenguaje de consultas MetricsQL

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Almacenamiento de objetos obligatorio, multitenencia de nivel empresarial**

**Explicación:**
Mimir requiere almacenamiento de objetos y proporciona multitenencia nativa, por lo que es adecuado para entornos empresariales. VictoriaMetrics también admite disco local y es más sencillo de operar, pero Mimir tiene una excelente integración con el ecosistema de Grafana.

</details>

---

8. ¿Cuál es el rol de Store-gateway en Mimir?
   - A) Recopilación de métricas
   - B) Almacenar en caché bloques del almacenamiento de objetos y procesar consultas de datos históricos
   - C) Evaluación de reglas de alertas
   - D) Autenticación de tenants

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Almacenar en caché bloques del almacenamiento de objetos y procesar consultas de datos históricos**

**Explicación:**
Store-gateway almacena en caché los índices y chunks de los bloques almacenados en el almacenamiento de objetos y procesa las consultas de datos históricos. Querier recupera los datos recientes de Ingester y los datos históricos de Store-gateway, y luego los combina.

</details>

---

9. ¿Cuál es el rol de la configuración `compactor_blocks_retention_period` en Mimir?
   - A) Período de retención de caché en memoria
   - B) Establecer el período de retención de datos de bloques
   - C) Período de retención de logs
   - D) Período de retención del historial de alertas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Establecer el período de retención de datos de bloques**

**Explicación:**
`compactor_blocks_retention_period` establece el período durante el que Compactor conserva los bloques. Por ejemplo, configurarlo en `365d` elimina los bloques con más de 1 año de antigüedad. Esta configuración ayuda a gestionar los costos de almacenamiento y a cumplir los requisitos de conformidad.

</details>

---

10. ¿Cuál NO es una recomendación para la configuración de alta disponibilidad de Mimir?
    - A) Mínimo de 3 réplicas de Ingester, replicación con reconocimiento de zona
    - B) Mínimo de 2 réplicas de Store-gateway
    - C) Implementar todos los componentes en una única zona de disponibilidad
    - D) Habilitar el almacenamiento en caché con memcached

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Implementar todos los componentes en una única zona de disponibilidad**

**Explicación:**
Para lograr alta disponibilidad, los componentes deben distribuirse entre varias zonas de disponibilidad (AZ). Mimir admite replicación con reconocimiento de zona para distribuir los Ingesters entre varias AZ. Implementar en una única AZ provoca una interrupción completa del servicio si esa AZ falla.

</details>
