# Cuestionario sobre entrenamiento de modelos en EKS

15 preguntas sobre las API actuales, los lanzadores y los límites de recuperación.

## 1. ¿Qué particiona el paralelismo de tensores (tensor parallelism)?

<details>
<summary>Respuesta y explicación</summary>

Las operaciones tensoriales y los pesos dentro de las capas. DP particiona los datos entre réplicas, PP particiona las etapas de capas y el paralelismo de expertos particiona los expertos y el despacho de tokens; cada tipo tiene patrones de comunicación distintos.
</details>

## 2. ¿Cómo se deben planificar un modelo de 200B y el lote global?

<details>
<summary>Respuesta y explicación</summary>

No impongas paralelismo 3D solo por el tamaño; considera el estado de entrenamiento, las activaciones, la comunicación y la malla de dispositivos. TP 8 × PP 4 × DP 2 son 64 ranks, pero un microbatch de 1 × acumulación de 32 × DP 2 da un lote global de 64.
</details>

## 3. ¿En qué se diferencian las responsabilidades de estado de slurmctld y slurmdbd?

<details>
<summary>Respuesta y explicación</summary>

slurmctld gestiona el estado de los trabajos, nodos y particiones en ejecución, la planificación y StateSaveLocation. slurmdbd gestiona los registros contables de la base de datos y no sustituye el estado de recuperación del controlador.
</details>

## 4. ¿Qué es la API de compute-group de Slinky 1.2.3?

<details>
<summary>Respuesta y explicación</summary>

slinky.slurm.net/v1beta1 NodeSet, que usa una referencia o plantilla de Controller. El escalado es de tipo StatefulSet de forma predeterminada, con la opción de usar DaemonSet; replicas se ignora en modo DaemonSet. El kind no es SlurmNodeSet.
</details>

## 5. ¿Basta FI_PROVIDER=efa para habilitar NCCL sobre EFA?

<details>
<summary>Respuesta y explicación</summary>

No. Se necesitan interfaces EFA, controladores, libfabric, aws-ofi-nccl, un complemento de dispositivos, asignación al Pod, grupos de seguridad e instancias en la misma AZ. Verifica el transporte real con los registros y pruebas colectivas; 400 Gbps no es una cifra universal.
</details>

## 6. ¿Qué se debe comprobar para BioNeMo 3.0.0?

<details>
<summary>Respuesta y explicación</summary>

Comprueba en BioNeMo Recipes la compatibilidad del modelo, TransformerEngine y la receta de entrenamiento. No reutilices sin verificar el antiguo módulo MegaMolBART 1.5; valida las versiones de la imagen, los datos y el modelo, los dispositivos, la convergencia y la evaluación biológica.
</details>

## 7. ¿Garantiza Optimum Neuron Trainer el entrenamiento de todos los modelos de HF?

<details>
<summary>Respuesta y explicación</summary>

No. Comprueba que coincidan las implementaciones versionadas del modelo de entrenamiento, la configuración, el SDK/PyTorch, el hardware, los datos y el collator. La compatibilidad con inferencia difiere de la compatibilidad con entrenamiento; un modelo preentrenado y un conjunto de datos sin definir no bastan para implementar entrenamiento con TP.
</details>

## 8. ¿Cómo se debe verificar la integración de FSx y S3?

<details>
<summary>Respuesta y explicación</summary>

Distingue los montajes estáticos del aprovisionamiento dinámico y verifica las políticas de DRA e importación/exportación, que las operaciones finalicen y los permisos. La capacidad solicitada en un PVC de EFS no es una cuota, y el almacenamiento local por sí solo no garantiza la durabilidad en S3.
</details>

## 9. ¿Requiere minAvailable:4 de Volcano cuatro nodos?

<details>
<summary>Respuesta y explicación</summary>

No; cuenta Pods o miembros. Tres nodos pueden alojar cuatro Pods. Revisa las condiciones de cantidad mínima de miembros y recursos, así como el complemento gang; no garantiza el arranque simultáneo ni que el entrenamiento tenga éxito.
</details>

## 10. ¿En qué se diferencia BF16 de FP16?

<details>
<summary>Respuesta y explicación</summary>

Tiene 8 bits de exponente y 7 de mantisa. La cantidad de bits de exponente coincide con FP32, pero no su precisión ni su valor finito máximo exacto. Normalmente no se necesita el escalado de pérdidas habitual de FP16, pero valida el hardware, las operaciones y la convergencia; autocast no convierte todo el estado de entrenamiento.
</details>

## 11. ¿En qué se diferencian los checkpoints de activaciones de los checkpoints de recuperación?

<details>
<summary>Respuesta y explicación</summary>

El uso de puntos de control de activaciones ahorra memoria a costa de volver a calcularlas durante la retropropagación; es distinto del estado de recuperación en disco del modelo, el optimizador y el generador de números aleatorios (RNG). Verifica use_reentrant, el estado/RNG y los gradientes sin suponer un ahorro fijo de 3–4×.
</details>

## 12. ¿ZeRO Stage 3 descarga datos automáticamente a la CPU?

<details>
<summary>Respuesta y explicación</summary>

No. Particiona el estado del optimizador, los gradientes y los parámetros; la descarga a la CPU se configura por separado. La reducción de memoria depende del tamaño de DP, el estado, los búferes y las activaciones, no de un escalado ilimitado.
</details>

## 13. ¿Qué establece slotsPerWorker de MPIJob?

<details>
<summary>Respuesta y explicación</summary>

Los slots del hostfile de los workers. La cantidad real de procesos depende de mpirun -np, el mapeo y la configuración del lanzador; la asignación de un rank por GPU requiere configuración explícita. Operator 0.8.2 usa la API v2beta1.
</details>

## 14. ¿Cómo se debe verificar la frecuencia de checkpoints y la recuperación?

<details>
<summary>Respuesta y explicación</summary>

Elige los intervalos según la latencia de guardado, la tasa de fallos, la cantidad de trabajo perdido aceptable y el coste de retención. Verifica el estado completo, los manifiestos, las sumas de comprobación, que la copia remota haya finalizado y que la reanudación funcione. La guía comprueba que los resultados en CPU sean idénticos tras cuatro actualizaciones ininterrumpidas y al reanudar después de dos actualizaciones.
</details>

## 15. ¿Qué significan la colocación de EFA en la misma AZ y los disruption budgets de Karpenter?

<details>
<summary>Respuesta y explicación</summary>

Conecta las restricciones de Pod y NodePool para que los workers que se comunican compartan realmente una AZ. Se recomiendan los grupos de ubicación para mejorar el rendimiento. Un presupuesto de interrupciones de 0 limita las interrupciones voluntarias, no la reclamación de capacidad Spot, los fallos ni la terminación forzada.
</details>

[Volver a la guía](../../ai-ml/05-model-training.md)
