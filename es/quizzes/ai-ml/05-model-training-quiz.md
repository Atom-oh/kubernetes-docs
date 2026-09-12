# Cuestionario sobre entrenamiento de modelos en EKS

15preguntas sobre las APIs actuales, los launchers y los límites de recuperación.

## 1. ¿Qué particiona el paralelismo de tensores (tensor parallelism)?

<details>
<summary>Respuesta y explicación</summary>

Las operaciones de tensores y los pesos dentro de las capas. DP particiona los datos entre réplicas, PP particiona las etapas de capas y el paralelismo de expertos particiona los expertos y el despacho de tokens; su comunicación es distinta.
</details>

## 2. ¿Cómo se debe planificar un modelo de200B y el batch global?

<details>
<summary>Respuesta y explicación</summary>

No impongas paralelismo3D solo por el tamaño; considera el estado de entrenamiento, las activaciones, la comunicación y la malla de dispositivos. TP8×PP4×DP2 son64ranks, pero un microbatch de1×acumulación32×DP2 da un batch global de64.
</details>

## 3. ¿En qué se diferencian las responsabilidades de estado de slurmctld y slurmdbd?

<details>
<summary>Respuesta y explicación</summary>

slurmctld gestiona el estado en ejecución de trabajos, nodos y particiones, la planificación y StateSaveLocation. slurmdbd se encarga de los registros de la base de datos de accounting y no sustituye al estado de recuperación del controlador.
</details>

## 4. ¿Qué es la API de compute-group de Slinky1.2.2?

<details>
<summary>Respuesta y explicación</summary>

slinky.slurm.net/v1beta1 NodeSet, usando una referencia o plantilla de Controller. Escalado predeterminado de estilo StatefulSet u opcionalmente de estilo DaemonSet; replicas se ignora en modo DaemonSet. El kind no es SlurmNodeSet.
</details>

## 5. ¿Basta FI_PROVIDER=efa para habilitar NCCL sobre EFA?

<details>
<summary>Respuesta y explicación</summary>

No. Se necesitan interfaces EFA, driver/libfabric/aws-ofi-nccl, device plugin y asignación en el Pod, security groups y colocación en la misma AZ. Verifica el transporte real con logs y pruebas de colectivas;400Gbps no es universal.
</details>

## 6. ¿Qué se debe comprobar para BioNeMo3.0.0?

<details>
<summary>Respuesta y explicación</summary>

El soporte de modelo, TransformerEngine y receta de entrenamiento en BioNeMo Recipes. No reutilices sin verificar el antiguo módulo MegaMolBART de1.5; valida las revisiones de imagen, datos y modelo, los devices, la convergencia y la evaluación biológica.
</details>

## 7. ¿Garantiza Optimum Neuron Trainer el entrenamiento de todos los modelos de HF?

<details>
<summary>Respuesta y explicación</summary>

No. Haz coincidir las implementaciones versionadas del modelo de entrenamiento, la configuración, el SDK/PyTorch, el hardware, los datos y el collator. El soporte de inferencia difiere del soporte de entrenamiento; un modelo preentrenado y un dataset indefinido no implementan entrenamiento con TP.
</details>

## 8. ¿Cómo se debe verificar la integración de FSx y S3?

<details>
<summary>Respuesta y explicación</summary>

Distingue los montajes estáticos del aprovisionamiento dinámico y verifica las políticas DRA/import/export, la finalización y los permisos. La capacidad de un PVC de EFS no es una cuota, y el almacenamiento local por sí solo no establece durabilidad en S3.
</details>

## 9. ¿Requiere minAvailable:4 de Volcano cuatro nodos?

<details>
<summary>Respuesta y explicación</summary>

No; cuenta Pods/miembros. Tres nodos pueden alojar cuatro Pods. Revisa las condiciones de miembro mínimo y de recursos y el plugin gang; no garantiza el arranque simultáneo ni el éxito del entrenamiento.
</details>

## 10. ¿En qué se diferencia BF16 de FP16?

<details>
<summary>Respuesta y explicación</summary>

Tiene8bits de exponente y7de mantisa. El número de bits de exponente coincide con FP32, no su precisión ni su valor finito máximo exacto. Normalmente no es necesario el loss scaling típico de FP16, pero valida hardware, operaciones y convergencia; autocast no convierte todo el estado de entrenamiento.
</details>

## 11. ¿En qué se diferencian los checkpoints de activaciones de los checkpoints de recuperación?

<details>
<summary>Respuesta y explicación</summary>

El activation checkpointing cambia memoria por recomputación en el backward; es distinto del estado de recuperación en disco de modelo, optimizador y RNG. Verifica use_reentrant, el estado/RNG y los gradientes sin suponer un ahorro fijo de3–4x.
</details>

## 12. ¿Descarga ZeRO Stage3 automáticamente a la CPU?

<details>
<summary>Respuesta y explicación</summary>

No. Particiona el estado del optimizador, los gradientes y los parámetros; el offload se configura por separado. La reducción de memoria depende del tamaño de DP, el estado, los buffers y las activaciones, no de un escalado ilimitado.
</details>

## 13. ¿Qué establece slotsPerWorker de MPIJob?

<details>
<summary>Respuesta y explicación</summary>

Los slots del hostfile de los workers. El número real de procesos depende de mpirun -np y del mapeo y de la configuración del launcher; el binding de un rank por GPU requiere configuración explícita. El Operator0.8.2 usa la API v2beta1.
</details>

## 14. ¿Cómo se debe verificar la frecuencia de checkpoints y la recuperación?

<details>
<summary>Respuesta y explicación</summary>

Elige los intervalos según la latencia de guardado, la tasa de fallos, el trabajo perdido aceptable y el coste de retención. Verifica el estado completo, los manifests, los checksums, la finalización remota y la reanudación real. La guía comprueba que los resultados en CPU sean idénticos entre cuatro actualizaciones sin interrupción y una reanudación después de dos.
</details>

## 15. ¿Qué significan la colocación de EFA en la misma AZ y los disruption budgets de Karpenter?

<details>
<summary>Respuesta y explicación</summary>

Conecta las restricciones de Pod y NodePool para que los workers que se comunican compartan realmente una AZ. Se recomiendan placement groups para el rendimiento. Un budget de0 limita la disrupción voluntaria, no la reclamación de Spot, los fallos ni la terminación forzada.
</details>

[Volver a la guía](../../ai-ml/05-model-training.md)
