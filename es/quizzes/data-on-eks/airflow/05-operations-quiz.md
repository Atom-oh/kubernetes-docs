# Cuestionario de operaciones y seguridad: parte 5

Comprueba los límites operativos y de recuperación de Airflow 3.3.1.

1. ¿Separar el procesador de DAG elimina toda contención en la base de datos del scheduler de Airflow 3?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Airflow 2 también admitía alta disponibilidad; la versión 3 aún requiere comprobar los bloqueos de la base de datos, las conexiones y la capacidad de ejecución.

**Explicación:** `replicas=2` no proporciona automáticamente diversidad de ubicación, conmutación por error de la base de datos ni alta disponibilidad del servicio completo.

</details>

2. ¿Detener los schedulers, procesadores y triggerers detiene todos los escritores de la base de datos antes de una migración?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Coordina también el tráfico de entrada, el drenaje y las escrituras de los workers, las tareas, los servidores de API y la automatización externa.

**Explicación:** Prueba la restauración de la base de datos y la recuperación de Fernet/datos externos; usa una sola ruta de migración y un plan de reversión verificado.

</details>

3. ¿Todos los componentes de Airflow deben usar el mismo prefijo de Secrets Manager?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Los backends específicos de los workers y la resolución de Execution API pueden ser intencionales.

**Explicación:** Verifica el orden de búsqueda real, los permisos, la alternativa y el almacenamiento en caché. Algunas rutas registran excepciones; no todos los fallos son silenciosos.

</details>

4. ¿`remote_logging=True` en S3 carga de inmediato cada línea de todos los componentes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Configura los registros de tareas; según el comportamiento verificado, el supervisor los carga cuando termina la ejecución de la tarea.

**Explicación:** La salida estándar/error del servicio puede requerir una recopilación aparte. Una terminación forzada antes de la carga puede hacer que se pierdan los registros recientes.

</details>

5. ¿Todos los valores de Connection/Variable en un metastore configurado con Fernet están en texto sin cifrar?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Los campos `password`/`extra` y los valores de Variable se cifran, pero no todos los metadatos ni los registros.

**Explicación:** Conserva y rota las claves de Fernet. Los backends externos son una opción; AWS Secrets Manager no es la única alternativa de producción obligatoria.

</details>

6. ¿Contar todas las tareas en cola o en ejecución basta para una consulta de KEDA para Celery?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Ten en cuenta las colas, los ejecutores, los alias, la concurrencia de los workers y los límites de réplicas.

**Explicación:** Los workers pueden usar Deployments o StatefulSets, y que escalen a cero depende de la configuración real.

</details>

7. ¿Por qué no se puede aplicar sin cambios el escalado del grupo de workers de Celery a KubernetesExecutor?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** KubernetesExecutor crea directamente pods para las tareas y no tiene un grupo fijo de workers equivalente.

**Explicación:** Esto no significa que KEDA solo admita Deployments. Comprueba por separado la capacidad del escalador de nodos, las cuotas y las restricciones de interrupción.

</details>

8. ¿Asignar un rol de IAM a un worker de Celery compartido aísla automáticamente los permisos de AWS de cada tarea?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Varias tareas que se ejecutan en ese worker pueden compartir sus permisos de ejecución.

**Explicación:** Cuando necesites límites reales, usa pools o ejecutores separados, o pods creados por KPO, e inspecciona las fuentes de credenciales.

</details>

9. ¿Cómo debería la automatización de limpieza de la base de datos obtener una vista previa de los cambios y detectar fallos?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Primero usa `--dry-run` con una fecha de corte y tablas revisadas; usa `--error-on-cleanup-failure` e inspecciona los registros.

**Explicación:** Ejecuta la eliminación por separado. Los archivos de respaldo predeterminados ocupan espacio en la base de datos y las eliminaciones en cascada importan; la limpieza no siempre libera espacio en disco ni acelera todas las migraciones.

</details>

10. ¿Basta con una NetworkPolicy y un endpoint OTLP para garantizar la seguridad y la observabilidad?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** No. Verifica la aplicación de políticas del CNI, las rutas permitidas reales, la autenticación, los receptores/exportadores del Collector, el almacenamiento y las alertas.

**Explicación:** NetworkPolicy no sustituye a IAM/RBAC/TLS. Prometheus no recopila métricas simplemente haciendo scraping de un endpoint OTLP/HTTP.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/airflow/05-operations.md) | [Airflow](../../../data-on-eks/airflow/README.md)
