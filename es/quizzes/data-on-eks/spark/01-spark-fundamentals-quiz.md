# Cuestionario sobre los fundamentos de Spark en Kubernetes

Repase los modos de implementación, los límites de responsabilidad, los recursos, la asignación dinámica y las condiciones de terminación.

## 1. ¿Qué modos de implementación de Kubernetes y requisito previo se aplican a Spark 4.2?

<details>
<summary>Mostrar respuesta</summary>

Se admiten los modos cluster y client; Spark 4.2 documenta Kubernetes 1.34 o posterior. El modo client existe desde la versión 2.4 y no es exclusivo de los entornos de notebooks. kubectl debe ser compatible con el servidor de API real.

</details>

## 2. ¿Quién solicita los pods de executor, coloca/inicia los pods y asigna las tareas de Spark?

<details>
<summary>Mostrar respuesta</summary>

El driver solicita los pods de executor a través de la API. El planificador de Kubernetes elige los nodos y los kubelets inician los contenedores. Los planificadores de Spark del driver asignan las tareas a los executors registrados. Ni el servidor de API ni el driver reemplazan la planificación de Kubernetes.

</details>

## 3. ¿Eliminar la capa de YARN elimina las operaciones de infraestructura o los permisos del driver?

<details>
<summary>Mostrar respuesta</summary>

No. Siguen existiendo los nodos, Kubernetes, las imágenes, la red, el almacenamiento y la observabilidad. Se necesitan la autenticación de API del cliente que envía la aplicación y los permisos RBAC del driver en el espacio de nombres. El ejemplo usa una cuenta de servicio independiente para los executors; los permisos de AWS para acceder a los datos y el RBAC de Kubernetes son distintos.

</details>

## 4. ¿Siempre hay que establecer explícitamente tanto las opciones de asignación dinámica como las de seguimiento de shuffle?

<details>
<summary>Mostrar respuesta</summary>

No. Habilite la asignación dinámica, pero en 4.2 el seguimiento de shuffle ya viene habilitado de forma predeterminada y existe desde la versión 3.0. El ESS estándar de Kubernetes no es compatible; la conservación de datos mediante el retiro ordenado de ejecutores (decommission) y el uso de ShuffleDataIO fiable y adecuado son alternativas sujetas a condiciones. Los mecanismos que se solapan pueden retrasar la eliminación.

</details>

## 5. ¿Qué ruta de terminación se añade al habilitar decommission?

<details>
<summary>Mostrar respuesta</summary>

Spark 4.2 inserta un hook preStop que ejecuta /opt/decom.sh. La imagen oficial incluye ese script; este envía una señal SIGPWR a la JVM del executor y espera. La migración de bloques también requiere opciones de almacenamiento para el retiro ordenado, además de destinos, tiempo y capacidad reales.

</details>

## 6. ¿Aumentar terminationGracePeriodSeconds a 60 garantiza la migración de todos los bloques?

<details>
<summary>Mostrar respuesta</summary>

No. Spark 4.2 anula el valor de la plantilla, así que también se debe establecer spark.kubernetes.executor.terminationGracePeriodSeconds=60s. Tanto el valor predeterminado de 30 segundos como los 60 configurados incluyen preStop y solo representan presupuestos de tiempo; una terminación forzada, los plazos de Spot o una capacidad de destino insuficiente pueden impedir que se complete la migración.

</details>

## 7. ¿En qué se diferencia allocation.batch.size del recuento inicial/mínimo de executors?

<details>
<summary>Mostrar respuesta</summary>

batch.size controla los lotes de solicitudes de pods. Los valores mínimo/inicial/máximo definen los límites y el recuento de inicio de executors, y también se tiene en cuenta el valor existente de executor.instances. El ejemplo con mínimo 2/inicial 3/instances 3 comienza con tres; el aprovisionamiento de nodos es independiente.

</details>

## 8. ¿Cómo se deben interpretar los cores de Spark, los límites de CPU, la memoria y las plantillas de pods?

<details>
<summary>Mostrar respuesta</summary>

Los núcleos de Spark se relacionan con las solicitudes de CPU predeterminadas y la capacidad de tareas del executor; para establecer límites de CPU se necesita limit.cores. En el ejemplo de JVM, un heap de 1 GiB más una sobrecarga mínima de 384 MiB da una solicitud y un límite de 1408 MiB. El cliente que envía la aplicación lee las plantillas y Spark las compone; no son pods incompletos que deban aplicarse con kubectl.

</details>

## 9. ¿Qué se debe verificar todavía con el seguimiento de shuffle y decommission?

<details>
<summary>Mostrar respuesta</summary>

Compruebe los tiempos de espera de seguimiento/inactividad, la terminación forzada, la capacidad de los nodos y el recálculo. El modo client también necesita endpoints del driver accesibles y, cuando corresponda, un propietario real para el pod del driver. Conservar bloques intermedios no reemplaza los checkpoints, la recuperación del driver ni la semántica de procesamiento exactamente una vez de extremo a extremo.

</details>

---

[Volver al material de aprendizaje](../../../data-on-eks/spark/01-spark-fundamentals.md)
