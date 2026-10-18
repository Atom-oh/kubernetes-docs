# Cuestionario de ajuste de rendimiento y costos: parte 4

Base: Spark 4.2.0 / Karpenter 1.14 · septiembre de 2026.

## 1. ¿Las instancias de la serie R y NVMe son siempre la opción más rápida para el shuffle?

<details>
<summary>Mostrar respuesta</summary>

No. Mide el tiempo de las tareas y etapas, el spill, la espera al recuperar datos del shuffle, la distribución desigual y los cuellos de botella de CPU, memoria, disco y red. Compara la capacidad disponible y el costo por trabajo completado; otras familias de instancias y EBS no son inadecuados por definición.

</details>

## 2. ¿Qué se debe comprobar al evaluar Graviton?

<details>
<summary>Mostrar respuesta</summary>

Valida la compatibilidad con arm64 de la imagen de Spark, JNI, los códecs, BLAS, los paquetes de Python y los plugins; luego, compara el rendimiento de un trabajo representativo. Usar una imagen multiarquitectura ya probada puede evitar que tengas que crear la tuya.

</details>

## 3. ¿Es seguro formatear un dispositivo NVMe sin montar?

<details>
<summary>Mostrar respuesta</summary>

No. En Nitro, EBS también aparece como NVMe, y un disco sin montar puede contener datos o particiones. El nombre del dispositivo y su estado de montaje no demuestran que sea almacenamiento efímero de la instancia prescindible.

</details>

## 4. ¿Qué configura `instanceStorePolicy: RAID0` en AL2023?

<details>
<summary>Mostrar respuesta</summary>

Karpenter usa NodeConfig para configurar RAID0 en el almacenamiento efímero de la instancia que respalda el almacenamiento efímero de kubelet/containerd, y anuncia la capacidad asignable. RAID0 no es una copia de seguridad; un NodeClass completo también necesita su AMI, IAM, subred y demás parámetros.

</details>

## 5. ¿Por qué puede este laboratorio usar NVMe como almacenamiento temporal sin `hostPath`?

<details>
<summary>Mostrar respuesta</summary>

El NodeClass preparado respalda el sistema de archivos de kubelet con almacenamiento de la instancia, por lo que `emptyDir` respaldado por disco lo usa. Otra configuración de nodo o el uso de tmpfs cambia el almacenamiento subyacente.

</details>

## 6. ¿Qué nombre de volumen temporal reconoce Spark?

<details>
<summary>Mostrar respuesta</summary>

Un nombre como `spark-local-dir-scratch`, con el prefijo `spark-local-dir-` y un sufijo. El antiguo nombre `spark-local-dir` no coincide y puede crear otro `emptyDir` en la misma ruta de montaje.

</details>

## 7. ¿`emptyDir` `sizeLimit` reserva espacio en disco?

<details>
<summary>Mostrar respuesta</summary>

No. Ten en cuenta las solicitudes, la capacidad asignable del nodo, los demás pods, los registros y las capas escribibles. El nodo puede llenarse primero; tmpfs respaldado por memoria consume el presupuesto de memoria.

</details>

## 8. ¿Qué no garantiza separar el driver On-Demand de los executors Spot?

<details>
<summary>Mostrar respuesta</summary>

No elimina los fallos, las desviaciones de configuración ni el vencimiento del driver, ni hace que la pérdida de executors sea inocua. Un selector solo para Spot no permite recurrir a On-Demand y puede dejar pods en estado Pending cuando hay escasez.

</details>

## 9. ¿En qué se diferencian las taints/tolerations de los selectores de nodos?

<details>
<summary>Mostrar respuesta</summary>

Una toleration permite programar en un nodo con una taint; un selector elige nodos que coinciden. Otros pods pueden tener la misma toleration, y `NoSchedule` no expulsa los pods existentes.

</details>

## 10. ¿Las advertencias de Spot y las opciones de desmantelamiento garantizan que la migración termine?

<details>
<summary>Mostrar respuesta</summary>

No. Las advertencias son de mejor esfuerzo y la hibernación no ofrece una ventana de dos minutos. Importan EventBridge/SQS, la gestión de interrupciones, el drenaje, los hooks/señales, el tiempo, la capacidad de los pares y la red. Un período de gracia de 120 s para el pod no prolonga la vida útil de la instancia en la nube.

</details>

## 11. ¿Cualquier almacenamiento remoto se convierte automáticamente en alternativa para el shuffle?

<details>
<summary>Mostrar respuesta</summary>

No. Configura `spark.storage.decommission.fallbackStorage.path` y el sistema de archivos y los permisos correspondientes. La recuperación de la caché RDD y la del shuffle son distintas; el recálculo, los fallos de recuperación y los límites de reintentos aún pueden hacer fallar el trabajo.

</details>

## 12. ¿Qué señales controlan DRA y Karpenter?

<details>
<summary>Mostrar respuesta</summary>

DRA ajusta la cantidad de executors según la acumulación de tareas de Spark y el estado de inactividad, caché y shuffle. Karpenter aprovisiona nodos según las solicitudes de los pods y las restricciones de planificación. `metrics-server` no es obligatorio; `allocation.batch.size` controla la tasa de creación del asignador de Kubernetes.

</details>

## 13. ¿Que `consolidateAfter` sea mayor que `executorIdleTimeout` garantiza que DRA libere primero los executors?

<details>
<summary>Mostrar respuesta</summary>

No. Los temporizadores empiezan a contar a partir de eventos distintos, y la caché o el shuffle pueden retener executors. `WhenEmpty` reduce la consolidación de pods de cargas de trabajo normales, pero la desviación de configuración, el vencimiento y la terminación de Spot siguen siendo casos distintos.

</details>

## 14. ¿Un heap JVM de 4g y `cores=2` determinan todo el límite de memoria y CPU del pod?

<details>
<summary>Mostrar respuesta</summary>

No. Este ejemplo añade la sobrecarga predeterminada de 409 MiB, para un total de 4505 MiB de memoria. Los núcleos afectan a la solicitud de CPU predeterminada y a la concurrencia de Spark; establece explícitamente el límite de CPU con `spark.kubernetes.executor.limit.cores`. Revisa por separado PySpark, el uso fuera del heap y la sobrecarga explícita.

</details>

[Guía](../../../data-on-eks/spark/04-performance-tuning.md)
