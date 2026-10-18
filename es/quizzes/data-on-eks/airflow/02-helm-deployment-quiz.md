# Cuestionario de implementación con Helm y selección de executor

Chart 1.22.0 / Airflow 3.3.1 / KEDA 2.20.

## 1. ¿Qué chart y alias del repositorio usa esta guía?

<details>
<summary>Mostrar respuesta</summary>

El chart oficial del proyecto Apache Airflow. Si registras el repositorio como `apache-airflow`, los comandos usan `apache-airflow/airflow`. No mezcles valores de charts comunitarios independientes.

</details>

## 2. ¿Cuáles son los valores predeterminados reales de Airflow y del executor en chart 1.22.0?

<details>
<summary>Mostrar respuesta</summary>

Airflow 3.2.2 y CeleryExecutor. La guía los sobrescribe explícitamente para su perfil de KubernetesExecutor/Airflow 3.3.1.

</details>

## 3. ¿Chart.yaml hace cumplir todas las versiones mínimas documentadas?

<details>
<summary>Mostrar respuesta</summary>

No lo des por sentado. Usa Helm 3.19.0 o posterior y versiones compatibles de Kubernetes y Airflow. El README del chart 1.16 especificaba Kubernetes 1.29 o posterior; incluso las plantillas revisadas de la versión 1.22 se procesaban con la versión 1.29, pero eso no demuestra compatibilidad.

</details>

## 4. ¿El executor por sí solo determina Redis y los tipos de recursos de worker?

<details>
<summary>Mostrar respuesta</summary>

Influye, pero también importan la configuración de Redis o del broker externo y la persistencia del worker. Los workers pueden ser Deployments o StatefulSets, y Celery puede usar un broker externo.

</details>

## 5. ¿Deshabilitar PostgreSQL configura una base de datos externa?

<details>
<summary>Mostrar respuesta</summary>

No. Prepara la base de datos, los privilegios de migración, el URI/TLS y una referencia de conexión, como `metadataSecretName`. Cuando se define ese Secret, `metadataConnection` deja de ser la fuente autoritativa.

</details>

## 6. ¿Se deberían regenerar las claves de Fernet/API/JWT durante las actualizaciones?

<details>
<summary>Mostrar respuesta</summary>

Consérvalas durante las actualizaciones normales. Perder la clave Fernet puede impedir el acceso a los datos cifrados, y cambiar JWT puede afectar la autenticación de tareas activas. Planifica cuidadosamente las copias de seguridad y la rotación.

</details>

## 7. ¿Cómo evita el ejemplo las credenciales predeterminadas admin/admin?

<details>
<summary>Mostrar respuesta</summary>

Deshabilita `createUserJob` y usa el comando interactivo `airflow users create` para el gestor de autenticación FAB seleccionado; solicita dos veces la contraseña. Otros gestores de autenticación o SSO requieren sus propios procedimientos.

</details>

## 8. ¿KubernetesExecutor siempre tarda de uno a dos minutos en iniciarse?

<details>
<summary>Mostrar respuesta</summary>

No. Mide la caché y descarga de imágenes, la API y el scheduler de Kubernetes, la disponibilidad y el aprovisionamiento de nodos, las cuotas y la inicialización del runtime. Celery también tiene inicios en frío después de escalar a cero.

</details>

## 9. ¿KubernetesExecutor puede usar cualquier imagen de worker con GPU o CLI?

<details>
<summary>Mostrar respuesta</summary>

El worker necesita un runtime de tareas de Airflow compatible y las dependencias de DAG y proveedores. Esto es distinto de que KubernetesPodOperator inicie un pod secundario con una imagen de la carga de trabajo.

</details>

## 10. ¿Que no haya pods worker significa que el costo total de Airflow sea cero cuando está inactivo?

<details>
<summary>Mostrar respuesta</summary>

Pueden persistir los costos del plano de control, la base de datos, el broker, los nodos, el almacenamiento y los registros. La ejecución por pod o el escalado a cero no garantizan un costo total nulo ni un aislamiento de seguridad completo.

</details>

## 11. ¿Cuáles son los valores de temporización predeterminados de KEDA en el chart frente a los del ejemplo?

<details>
<summary>Mostrar respuesta</summary>

Los valores predeterminados son `pollingInterval=5s` y `cooldownPeriod=30s`. El ejemplo selecciona explícitamente 10 s y 300 s. Distingue el período de enfriamiento del escalado a cero del escalado/estabilización de HPA por encima de cero.

</details>

## 12. ¿Qué valor debe tomar `worker_concurrency` en la consulta SQL?

<details>
<summary>Mostrar respuesta</summary>

Un valor numérico generado por el chart (4 en este ejemplo), no una columna de base de datos llamada `worker_concurrency`. Cuenta las tareas pertinentes en ejecución o en cola para las colas y executors del worker, divide y redondea hacia arriba.

</details>

## 13. ¿Por qué un alias `k8s` puede causar errores de escalado con varios executors?

<details>
<summary>Mostrar respuesta</summary>

TaskInstance almacena `task.executor`. Si el chart excluye solo el literal `KubernetesExecutor`, las tareas almacenadas como `k8s` pueden incluirse en el recuento de Celery. Usa filtros que coincidan con los valores almacenados reales.

</details>

## 14. ¿Qué ocurre si la consulta devuelve 25 con `maxReplicaCount=20`?

<details>
<summary>Mostrar respuesta</summary>

El máximo limita la cantidad de workers, por lo que la demanda no se satisface de inmediato por completo. Inspecciona conjuntamente la acumulación de trabajo, la concurrencia, los recursos del worker, la carga de la base de datos y del broker, y la capacidad de nodos.

</details>

## 15. ¿La configuración TLS de los pods de Airflow basta para que KEDA acceda a la base de datos?

<details>
<summary>Mostrar respuesta</summary>

No. KEDA es un cliente de base de datos independiente que necesita DNS, red, permisos, un URI compatible y una CA. El archivo indicado por `sslrootcert` en un URI debe ser legible por el escalador; el chart no lo copia automáticamente.

</details>

## 16. ¿KEDA está limitado a Deployments?

<details>
<summary>Mostrar respuesta</summary>

No. El chart usa un Deployment o StatefulSet según la persistencia de Celery. Los pods de tareas de KubernetesExecutor no siguen el mismo patrón de pool de réplicas, pero eso no impide otros usos de KEDA.

</details>

## 17. ¿Una ejecución correcta de `helm --wait` completa la validación?

<details>
<summary>Mostrar respuesta</summary>

Verifica que las migraciones concluyan correctamente y que los componentes de larga duración estén Ready; además, comprueba la distribución de DAG, la ejecución de workers, Execution API, los resultados y los registros. En los perfiles de KEDA, prueba el escalado según la carga de trabajo, el regreso al estado inactivo y la recuperación.

</details>

## 18. ¿Desinstalar Helm elimina inmediatamente todos los datos de PostgreSQL?

<details>
<summary>Mostrar respuesta</summary>

La eliminación de pods y los ciclos de vida de los datos de PVC/PV son distintos. Revisa por separado la retención de PVC, la política de recuperación de StorageClass y la eliminación o las copias de seguridad de las bases de datos externas; no elimines indiscriminadamente espacios de nombres, Secrets ni bases de datos compartidos.

</details>

[Guía](../../../data-on-eks/airflow/02-helm-deployment.md)

[Cuestionario anterior](./01-architecture-quiz.md)
