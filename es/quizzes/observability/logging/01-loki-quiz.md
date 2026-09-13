# Cuestionario de Grafana Loki

> **Última actualización**: September 13, 2026

Basado en los ejemplos de Loki3.7.7/chart18.12.1 de la [guía](../../../observability/logging/01-loki.md).

---

1. ¿Qué indexa principalmente Loki en el modelo TSDB/chunk?

   - A) Cada palabra en cada línea de log
   - B) Etiquetas de stream
   - C) Solo IDs de solicitud
   - D) Solo marcas de tiempo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Las etiquetas reducen los streams que se deben analizar. Esto no demuestra una ventaja de costo fija de 10× ni elimina los costos de análisis/lectura de chunks.

</details>

---

2. ¿Qué componente almacena en búfer los streams de logs, escribe el WAL cuando está habilitado y vacía los chunks?

   - A) Distributor
   - B) Query frontend
   - C) Ingester
   - D) Index gateway

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El Ingester también sirve datos recientes. WAL necesita almacenamiento persistente y, por sí solo, no garantiza la entrega sin pérdidas ni HA.

</details>

---

3. ¿Qué afirmación coincide con la guía de despliegue actual utilizada por este capítulo?

   - A) SSD es permanentemente el valor predeterminado para todos los clústeres de producción de EKS
   - B) Cualesquiera tres Pods garantizan resiliencia en tres AZ
   - C) SingleBinary es el único nombre de modo de chart18.12.1
   - D) SSD está obsoleto; la guía de escalado/HA para producción recomienda Distributed con planificación operativa explícita

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Está previsto eliminar SSD en Loki4.0. La capacidad y la disponibilidad dependen de la carga de trabajo, el almacenamiento, la topología y la gestión de fallos probada, no de una tabla fija de GB/día.

</details>

---

4. ¿Qué consulta devuelve una tasa por segundo de líneas de log de error coincidentes durante cinco minutos?

   - A) `rate({app="nginx"} |= "error" [5m])`
   - B) `count({app="nginx"} |= "error")`
   - C) `sum({app="nginx"} |= "error")`
   - D) `increase(count_over_time({app="nginx"}[5m]))`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Esta es una tasa de líneas de log por stream, no automáticamente una proporción de errores de solicitudes HTTP. La agregación de vectores de conteo de LogQL existe, pero B no proporciona la entrada de vector de métricas requerida.

</details>

---

5. Se necesita un ID de solicitud único para la investigación. ¿Cuál es un mejor punto de partida?

   - A) Indexar cada ID de solicitud para consultas más rápidas
   - B) Mantener los IDs necesarios en el contenido de los logs o en metadatos estructurados bajo controles de acceso/privacidad
   - C) Eliminar todas las etiquetas de clúster/namespace
   - D) Suponer que el total de streams siempre es igual al producto de las cardinalidades de las etiquetas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los valores de índice de alta cardinalidad pueden crear muchos streams. Los metadatos estructurados no son redacción, y el producto de cardinalidad es solo un límite superior de las combinaciones observadas.

</details>

---

6. En el ejemplo de IRSA, ¿cómo se mantiene coherente la propiedad de ServiceAccount?

   - A) eksctl y Helm crean ambos el mismo ServiceAccount
   - B) Colocar claves de acceso de S3 en los valores de Helm
   - C) Usar eksctl --role-only; Helm crea el ServiceAccount anotado correspondiente
   - D) Otorgar a todos los nodos la política del bucket y deshabilitar la autenticación

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La confianza del rol debe coincidir con el proveedor OIDC del clúster exacto, la audiencia y el sujeto de namespace/service-account. Pod Identity también es una opción cuando se cumplen los requisitos de plataforma/SDK.

</details>

---

7. ¿Qué consulta filtra un campo JSON y excluye los fallos del analizador?

   - A) `{app="api"} | json | level="error" | __error__=""`
   - B) `{app="api"} | json | where level="error"`
   - C) `{app="api"} | json | select level="error"`
   - D) `{app="api"} | json | filter level="error"`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

LogQL usa una etapa de filtro de etiquetas después del análisis. Para una métrica numérica sin envolver, coloque el filtro de errores después de unwrap para excluir también los errores de conversión.

</details>

---

8. ¿Cuál es el rol del Compactor en este despliegue de TSDB?

   - A) Autenticar usuarios del gateway
   - B) Recibir todas las solicitudes push de clientes
   - C) Garantizar que todos los logs expiren exactamente 31 días después de la ingestión
   - D) Compactar archivos de índice y eliminar de forma asíncrona los chunks marcados cuando la retención está habilitada

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

No es un combinador general de chunks pequeños de logs. La retención necesita un período de esquema/índice compatible, procesamiento habilitado, un almacén de eliminación y estado de marcadores duradero; 31 días es una política de ejemplo.

</details>

---

9. ¿Qué debería ocurrir primero después de una respuesta ingestion429?

   - A) Aumentar cada límite sin medir la capacidad
   - B) Distinguir los límites de tasa/ráfaga de bytes del tenant, de tasa por stream y de streams activos; después inspeccionar la capacidad/reintentos del cliente
   - C) Aumentar solo el tiempo de espera de consulta
   - D) Deshabilitar todos los límites permanentemente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los límites de tasa de ingestión y de ráfaga se encuentran en limits_config. Aumentar un límite puede sobrecargar el backend, y los reintentos necesitan backoff y una política limitada de pérdida/almacenamiento en búfer.

</details>

---

10. ¿Qué afirmación describe correctamente chunk_idle_period y /flush?

   - A) Ambos son endpoints de estado de solo lectura
   - B) chunk_idle_period es el período de retención de logs
   - C) chunk_idle_period controla el vaciado por inactividad; POST /flush activa el vaciado
   - D) Reducir chunk_idle_period siempre reduce el costo total

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Los tiempos de inactividad más cortos pueden producir más chunks pequeños y solicitudes de objetos. Una operación de flush no es una comprobación de estado, y la disponibilidad no demuestra la durabilidad de extremo a extremo.

</details>
