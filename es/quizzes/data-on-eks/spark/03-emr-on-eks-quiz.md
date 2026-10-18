# Cuestionario sobre Amazon EMR en EKS

Basado en la guía revisada el 16 de octubre de 2026.

## 1. ¿Qué es un clúster virtual?

<details>
<summary>Mostrar respuesta</summary>

El registro lógico de un espacio de nombres de EKS en EMR. No crea capacidad de cómputo, aunque pueden configurarse inicialmente el rol vinculado al servicio y las entradas y políticas de acceso de CAM.

</details>

## 2. ¿En qué se diferencian el envío de trabajos mediante StartJobRun y mediante EMR Spark Operator?

<details>
<summary>Mostrar respuesta</summary>

StartJobRun es una API de AWS que se dirige a un clúster virtual. El operador, que se instala por separado, recibe recursos personalizados SparkApplication; no es una opción interna de delegación de StartJobRun.

</details>

## 3. ¿Un recurso personalizado enviado por el operador obtiene automáticamente un ID de trabajo de EMR?

<details>
<summary>Mostrar respuesta</summary>

No lo des por sentado. Observa el estado del recurso personalizado, los registros y los reintentos a través de la ruta del operador, por separado del ciclo de vida de trabajos de la API de EMR.

</details>

## 4. ¿Cuándo comenzó la compatibilidad con EMR Spark Operator y cómo se instala?

<details>
<summary>Mostrar respuesta</summary>

EMR 6.10.0 o posterior. Instala el chart de EMR documentado y el runtime compatible; luego, envía el trabajo con `kubectl apply`. No lo confundas con la misma distribución que los charts upstream actuales de la parte 2.

</details>

## 5. ¿Qué versión de Apache Spark incluye `emr-spark-8.0.0`?

<details>
<summary>Mostrar respuesta</summary>

4.0.2-amzn-0. Esta versión, publicada en mayo de 2026, ofrece Spark 4.x GA; 8.0.0 identifica la versión del runtime de EMR.

</details>

## 6. ¿En qué se diferencian `-latest` y los sufijos con fecha?

<details>
<summary>Mostrar respuesta</summary>

`-latest` incorpora las actualizaciones de seguridad de la versión y no fija exactamente los mismos bytes de imagen. Un sufijo con fecha ayuda a reproducir una versión, pero aun así hay que revisar las actualizaciones posteriores.

</details>

## 7. ¿Qué valor de la respuesta de CreateVirtualCluster se usa para los trabajos posteriores?

<details>
<summary>Mostrar respuesta</summary>

El campo `id`. Asigna ese valor a `virtualClusterId` de StartJobRun y verifica el espacio de nombres registrado y el estado RUNNING.

</details>

## 8. ¿Los permisos de datos del rol de ejecución son los mismos que los permisos de quien llama a la API?

<details>
<summary>Mostrar respuesta</summary>

No. El rol de ejecución da a la carga de trabajo acceso a S3, KMS, registros y recursos similares. Quien llama necesita permisos de API y para usar el rol permitido; revisa las condiciones de `ExecutionRoleArn` y los permisos `PassRole` aplicables.

</details>

## 9. ¿Qué hace `update-role-trust-policy`?

<details>
<summary>Mostrar respuesta</summary>

Para IRSA, actualiza la confianza del rol de ejecución para incluir el proveedor OIDC del clúster, el espacio de nombres y la identidad de cuenta de servicio administrada por EMR. No concede automáticamente permisos de S3 ni de quien llama a la API.

</details>

## 10. ¿StartJobRun puede usar Pod Identity?

<details>
<summary>Mostrar respuesta</summary>

Sí, desde EMR 7.3.0. Requiere el agente, permisos EKS Auth del nodo, confianza para `pods.eks.amazonaws.com` y asociaciones de cuentas de servicio. Una anotación de IRSA no lo reemplaza.

</details>

## 11. ¿Qué asociaciones prepara `create-role-associations`?

<details>
<summary>Mostrar respuesta</summary>

Prepara tres asociaciones entre el rol de ejecución y las cuentas de servicio de quien envía el trabajo de EMR, del driver y de los executors. Usa el helper actual de la CLI y elimina por separado las asociaciones sin uso cuando se retiren el espacio de nombres o el rol.

</details>

## 12. ¿`maxConcurrentJobRuns=2` fija el límite de CPU del espacio de nombres?

<details>
<summary>Mostrar respuesta</summary>

No. Limita la cantidad de trabajos; `maxInQueueJobRuns` limita los trabajos en cola. Las cuotas de CPU/memoria y los límites de executors por trabajo son independientes.

</details>

## 13. ¿Un trabajo terminó cuando StartJobRun devolvió un resultado correcto?

<details>
<summary>Mostrar respuesta</summary>

No. Inspecciona el estado final y los registros con el ID de trabajo aceptado. El ejemplo de prueba verifica tanto COMPLETED como `SMOKE_OK rows=10 total=45`.

</details>

## 14. ¿Reutilizar un `clientToken` garantiza que los datos se generen exactamente una vez?

<details>
<summary>Mostrar respuesta</summary>

Deduplica la solicitud de la API, no los reintentos de la aplicación ni los efectos secundarios externos. Usa un token nuevo para cada ejecución nueva prevista.

</details>

## 15. ¿Se pueden personalizar las imágenes o las plantillas de pod de EMR?

<details>
<summary>Mostrar respuesta</summary>

Sí, mediante las rutas admitidas para plantillas de pod e imágenes personalizadas. Respeta las restricciones de cada versión y no sobrescribas arbitrariamente los espacios de nombres, las cuentas de servicio ni los nombres de pod que gestiona StartJobRun.

</details>

## 16. ¿Las integraciones con CloudWatch y Step Functions están completas sin configuración?

<details>
<summary>Mostrar respuesta</summary>

No. Configura la supervisión de registros y los permisos del rol de ejecución, además de la máquina de estados y su rol. Las métricas del servicio tampoco equivalen a la telemetría completa de la JVM de Spark.

</details>

## 17. ¿Cómo ejecuta EMR Studio las cargas de trabajo interactivas?

<details>
<summary>Mostrar respuesta</summary>

Un endpoint creado mediante CreateManagedEndpoint usa Jupyter Enterprise Gateway para gestionar kernels. Es distinto de las llamadas por lotes normales de StartJobRun y requiere configurar una red privada, ALB y roles. Los usuarios y kernels del mismo endpoint comparten el rol del endpoint.

</details>

## 18. ¿Por qué eliminar el clúster virtual no completa la limpieza?

<details>
<summary>Mostrar respuesta</summary>

Primero inspecciona y limpia los trabajos y endpoints previstos. EKS, los espacios de nombres, S3, los registros, los roles de IAM y las asociaciones de Pod Identity tienen ciclos de vida independientes; inspecciona también el estado de eliminación y los errores de permisos.

</details>

[Guía](../../../data-on-eks/spark/03-emr-on-eks.md)
