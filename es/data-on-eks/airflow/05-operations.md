# Parte 5: Operaciones y seguridad

> Revisado: Airflow 3.3.1, gráfico Helm 1.22.0, proveedor de Amazon 9.34.0 / proveedor de Kubernetes 10.21.0.
> Último parche upstream comprobado: 3.3.2; los ejemplos operativos siguen en 3.3.1 · 12 de octubre de 2026.

Este capítulo aborda la alta disponibilidad, las actualizaciones, los secretos, los registros, la observabilidad y la recuperación de la implementación de EKS autoadministrada de la parte 2. El criterio operativo es **poder recuperar la ejecución, los datos y los registros tras un fallo**, no limitarse a comprobar que existen determinados ajustes. Para MWAA, use los procedimientos del entorno administrado/CloudWatch de la parte 4.

## 1. Validar conjuntamente la alta disponibilidad del planificador y la base de datos

Airflow 2 ya admitía la alta disponibilidad del planificador y procesadores DAG independientes. La separación obligatoria de procesadores de Airflow 3 aclara los límites de recursos y responsabilidades, pero no elimina la contención de la base de datos ni garantiza un escalado lineal. Los planificadores usan DAG serializados y bloqueos de filas de la base de datos para coordinar la sección crítica de programación. No se necesita un servicio de elección de líder separado para el planificador.

```yaml
scheduler:
  replicas: 2
```

Este ajuste solo cambia el número de réplicas. Valide también la ubicación de nodos/AZ, la conmutación por error de la base de datos y los límites de conexiones, la disponibilidad de API/procesadores, las sondas/PDB y el estado del ejecutor/broker. Mida los retrasos de programación, los reintentos y las escrituras externas duplicadas durante fallos de nodo/AZ y la conmutación por error de la base de datos. Las notas sobre funciones SQL de la página del planificador no representan toda la matriz de bases de datos compatibles; use la guía de versiones de la parte 1. Se necesitan triggerers si se usan triggers, incluidas las tareas aplazables.

## 2. Copia de seguridad, restauración y migración

La base de datos de metadatos almacena el estado de ejecución y muchos ajustes de Airflow. Los secretos externos y los backends XCom de almacenamiento de objetos hacen que no todos los valores residan allí. Además de la base de datos, conserve las claves Fernet, el historial de DAG/bundles, las imágenes/proveedores, los datos externos, los registros y los secretos. Restaurar filas cifradas sin la clave de descifrado no basta.

Valide esta secuencia en un runbook de migración específico del entorno:

1. Compruebe la ruta de actualización compatible y los cambios incompatibles. Ensaye con una copia realista de la base de datos para medir la duración, los bloqueos, el espacio en disco y la compatibilidad de DAG/proveedores.
2. Use las garantías de coherencia de la base de datos para las copias en caliente y pruebe la restauración. Que una solicitud de instantánea tenga éxito no demuestra que se haya completado ni que sea recuperable.
3. Controle las ejecuciones nuevas y drene o termine deliberadamente el trabajo existente. Coordine todos los escritores pertinentes de la base de datos, incluidos trabajadores/tareas, servidores API y automatización externa. Detener únicamente planificadores, procesadores y triggerers no pone en pausa todas las escrituras.
4. Establezca el punto de copia de seguridad/recuperación y use un único mecanismo de migración. No permita que los Jobs/hooks de migración de Helm compitan con comandos manuales `airflow db migrate`.
5. Verifique el estado de la base de datos, las nuevas ejecuciones, los reintentos, los registros y la búsqueda de secretos antes de volver a abrir el tráfico. Volver a implementar una imagen antigua contra un esquema migrado no es un plan de reversión suficiente.

### Aplicar una política deliberada de retención del historial

No elimine incondicionalmente un número fijo de días antes de cada actualización. Compruebe primero los requisitos de auditoría/repetición/depends_on_past y las cascadas de claves externas. Este comando es una **vista previa que no elimina datos**:

```bash
# Preview only: replace the cutoff and table selection with your retention policy.
airflow db clean \
  --clean-before-timestamp '2026-07-01T00:00:00+00:00' \
  --tables dag_run,task_instance \
  --dry-run \
  --error-on-cleanup-failure
```

Ejecute la limpieza por separado solo después de revisar el límite de fecha/las tablas y la copia de seguridad. Las tablas de archivo predeterminadas ocupan espacio en la misma base de datos, así que la limpieza no garantiza que se libere espacio en disco de inmediato ni que se ejecute más rápido cada migración. En 3.3.1, algunos fallos de limpieza pueden quedar ocultos tras un estado de salida cero; la automatización debe usar `--error-on-cleanup-failure` e inspeccionar los resultados/registros.

## 3. Fernet y rutas de resolución de secretos

Las conexiones y variables no son simplemente texto sin cifrar de forma predeterminada. Cuando Fernet está configurado, se cifran los campos de contraseña/extra de las conexiones y los valores de Variable. Esto no cifra todos los campos de metadatos ni todos los registros; proteja/rote las claves y controle el acceso. AWS Secrets Manager es una opción compatible de backend externo.

```ini
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables", "config_prefix": "airflow/config"}
```

La búsqueda general del lado del servidor sigue este orden: backend personalizado → variables de entorno → metastore. No todos los valores externos aparecen en la interfaz de Airflow. Si edita en la interfaz una clave duplicada, puede seguir teniendo efecto el valor externo de mayor prioridad.

Airflow 3 admite `secrets_backend` y `secrets_backend_kwargs` específicos de los workers [workers]. Los contextos de tarea normales del SDK de tareas también pueden resolver valores del lado del servidor a través del supervisor y la API de ejecución. Por tanto, los componentes no necesitan todos los mismos prefijos ni acceso directo a la base de datos.

Documente la ruta prevista y pruebe por separado la búsqueda desde la API, las anulaciones de workers y la resolución/caché del supervisor de registros. El código revisado registra las excepciones del backend antes de probar las rutas siguientes; no todos los fallos son silenciosos. Pruebe tanto los valores alternativos inesperados como los fallos explícitos de búsqueda. No imprima el contenido de los secretos en los registros de diagnóstico.

## 4. Los registros de tareas en S3 no transmiten de inmediato todos los registros de componentes

```ini
[logging]
remote_logging = True
remote_base_log_folder = s3://my-airflow-logs-bucket/logs
remote_log_conn_id = airflow_remote_logging_conn
delete_local_logs = False
```

Nombre de secreto de ejemplo: airflow/connections/airflow_remote_logging_conn. Valor de ejemplo:

```json
{"conn_type": "aws", "extra": {"region_name": "us-east-1"}}
```

Esta conexión no contiene claves estáticas. Configure IRSA o Pod Identity y la selección de credenciales del SDK para los lectores/escritores reales de S3, junto con los permisos de prefijo del bucket/KMS y la red. Recibir metadatos de conexión mediante la API no transfiere las credenciales de AWS del servidor API. Pruebe tanto la lectura por API/interfaz como la escritura de tareas/supervisor.

El supervisor revisado de 3.3.1 carga los registros remotos después de terminar el subproceso de la tarea. El controlador de Amazon S3 también almacena objetos binarios en su ruta de cierre/carga. No se garantiza que cada línea llegue a S3 de inmediato. Pruebe tareas correctas y fallidas, la terminación forzada de workers y la recuperación desde la interfaz después de eliminar el Pod. SIGKILL o un fallo del nodo antes de la carga final pueden hacer que se pierdan los registros recientes.

La configuración `remote_logging` de S3 configura la **ruta de registros de tareas de Airflow**. No envía automáticamente todos los registros de servicio del planificador/API/procesador a la misma ubicación de S3. La recopilación separada de stdout/stderr, por ejemplo con Fluent Bit, la complementa. Si una tarea solo escribe en archivos, recopilar stdout del contenedor no recopila automáticamente esos archivos. Los PVC o recolectores independientes pueden conservar registros después de eliminar el Pod; inspeccione el almacenamiento, la retención y los límites de pérdida reales.

En KPO, el comportamiento `get_logs` de quien realiza la llamada incorpora la salida secundaria al registro de tareas de Airflow. Copiar `airflow.cfg` en una imagen secundaria arbitraria que no incluya Airflow no habilita el registro remoto.

## 5. Transporte y recopilación de métricas

Use una imagen con dependencias OTel compatibles y elija un backend de métricas. El siguiente ajuste selecciona OTel:

```ini
[metrics]
statsd_on = False
otel_on = True
```

Variables de entorno de ejemplo para cada proceso que emite métricas:

```dotenv
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector.monitoring.svc:4318/v1/metrics
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=http/protobuf
OTEL_METRIC_EXPORT_INTERVAL=30000
OTEL_SERVICE_NAME=airflow
```

En 3.3.1, los ajustes antiguos `otel_host`, `otel_port` y `otel_interval_milliseconds` están obsoletos y se sustituyen por variables de entorno estándar de OTel. Este endpoint es un ejemplo interno de OTLP/HTTP. Haga que coincidan el receptor HTTP del Collector, el puerto del Service, las políticas de red y los requisitos de TLS/autenticación.

Prometheus no extrae métricas directamente de un endpoint OTLP. Complete la canalización de métricas, por ejemplo, extrayéndolas de un exportador Prometheus del Collector o usando un exportador adecuado de remote write con autenticación. Para AMP, verifique el endpoint del espacio de trabajo y la autenticación de AWS. Con StatsD, inspeccione también la asignación del exportador y las series reales.

Observe el latido/retraso de programación del planificador, los errores/duración del análisis, la antigüedad de las tareas en cola, el estado de workers/triggerers, las conexiones/bloqueos de la base de datos, las condiciones Pending/OOM/presión de disco y los fallos de carga de registros. Compruebe los nombres/etiquetas de las métricas exportadas antes de crear alertas y pruebe la entrega de notificaciones mediante fallos controlados.

## 6. Límites de escalado automático y seguridad

Las consultas de KEDA para Celery deben distinguir colas, ejecutores y alias, y tener en cuenta la concurrencia y los límites de réplicas como en la parte 2. Los workers pueden usar Deployments o StatefulSets según la persistencia. El escalado a cero depende de las réplicas mínimas, los triggers y el periodo de enfriamiento; no elimina todos los costos de inactividad del servicio.

KubernetesExecutor crea directamente los Pods de tareas, así que no necesita el mismo patrón de escalado del pool de workers de Celery. Esto no significa que KEDA solo admita Deployments. Los autoscalers de nodos tampoco eliminan todos los nodos inmediatamente después de que terminan las tareas. Tenga en cuenta la capacidad, las cuotas, los PDB, la política de disrupción y otras cargas de trabajo.

| Límite | Qué verificar |
| --- | --- |
| Identidad de AWS | Las tareas de un worker de Celery compartido usan el mismo rol. Para el aislamiento, use límites reales de ejecución, como pools/ejecutores secundarios o Pods KPO separados |
| RBAC de Kubernetes | Conceda permisos al KubernetesExecutor o a quien llama a KPO cuando los necesite. El análisis de DAG por sí solo no requiere permisos para crear Pods |
| Espacio de nombres/admisión | La creación de Pods puede permitir seleccionar otras cuentas de servicio o especificaciones peligrosas; inspeccione los límites de confianza y los controles de admisión |
| NetworkPolicy | Verifique la aplicación del CNI y DNS, API de ejecución, DB/broker, API de Kubernetes y endpoints de credenciales/secretos/registros |

NetworkPolicy restringe la conectividad L3/L4. No sustituye la autenticación IAM/RBAC/TLS ni garantiza la prevención de todos los movimientos laterales. Permita las dependencias reales antes de aplicar la denegación predeterminada, sin ampliar innecesariamente el acceso de las tareas a la base de datos.

## 7. Aceptación operativa

- [ ] Registre los runtimes/proveedores compatibles, la elección de ejecutor y la política de entrega de DAG/repetición de versiones.
- [ ] Pruebe una base de datos de producción adecuada, la recuperación de copias de seguridad/restauraciones y Fernet/datos externos. RDS es una opción, no la única.
- [ ] Pruebe los límites de capacidad y la recuperación/fallo del planificador/API/procesador y los triggerers necesarios.
- [ ] Ensaye la migración, la admisión de nuevas ejecuciones, el drenaje y la reversión con una copia realista de la base de datos.
- [ ] Verifique las rutas previstas de resolución de secretos y los límites IAM/RBAC/admisión/red.
- [ ] Inspeccione los registros después del éxito, el fallo, la terminación forzada y la eliminación del Pod, y documente los límites de pérdida.
- [ ] Conecte las métricas, los registros de servicio/tareas y las alertas con los responsables de respuesta y los procedimientos.
- [ ] Mida la latencia, los reintentos, las escrituras externas duplicadas y la recuperación bajo la carga y los fallos objetivo.

Las casillas no garantizan la fiabilidad. Incluya los resultados medidos y los límites no resueltos frente a los SLO requeridos, los tiempos de recuperación y los objetivos de retención.

## Alcance de la validación y referencias

Se comprobaron en la documentación oficial y el código publicado la configuración, las rutas de resolución de secretos y el momento de carga. Se validaron la estructura del ejemplo y el comportamiento local de archivos del método de carga a S3. No se realizó ninguna migración real de bases de datos, llamada a AWS Secrets/S3, ingesta del Collector ni ejercicio de fallo y recuperación.


- [Alta disponibilidad del planificador y coordinación de la base de datos](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/scheduler.html)
- [Actualizaciones de bases de datos](https://airflow.apache.org/docs/apache-airflow/3.3.1/installation/upgrading.html)
- [CLI de mantenimiento de bases de datos](https://airflow.apache.org/docs/apache-airflow/3.3.1/cli-and-env-variables-ref.html)
- [Cifrado Fernet](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/fernet.html)
- [Backends de secretos y configuración de workers](https://airflow.apache.org/docs/apache-airflow/3.3.1/security/secrets/secrets-backend/index.html)
- [Registro de tareas](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/logging-tasks.html)
- [Configuración de métricas](https://airflow.apache.org/docs/apache-airflow/3.3.1/administration-and-deployment/logging-monitoring/metrics.html)
- [Implementación de registros S3 del proveedor Amazon 9.34.0](https://github.com/apache/airflow/blob/providers-amazon/9.34.0/providers/amazon/src/airflow/providers/amazon/aws/log/s3_task_handler.py)

[README](README.md)

[Cuestionario](../../quizzes/data-on-eks/airflow/05-operations-quiz.md)
