# Entrenamiento de modelos en EKS

> **Última actualización**: September 12, 2026
> **Líneas base**: Slinky1.2.2, MPI Operator0.8.2, Volcano1.15.2, PyTorch2.14.0, Neuron SDK2.32.0

El entrenamiento distribuido requiere código de modelo compatible, fragmentación de datos, launchers, asignación de dispositivos, comunicación y checkpoints. Un manifiesto válido o un Pod en estado Running no demuestra que el entrenamiento o la recuperación funcionen.

Para QLoRA de una sola GPU y la comparación SageMaker AI/EKS, consulta la [guía de Qwen](sagemaker-ai/README.md), incluida su compatibilidad con el ciclo de vida de imágenes y sus restricciones de ejecución.

## Pipeline de entrenamiento

![Entrenamiento a partir de datos/código versionados, validación de checkpoints completos y, después, evaluación y registro. Las rutas de servidor de parámetros y colectivas dependen del algoritmo.](../.gitbook/assets/en-ai-ml-05-model-training-0.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-0.html)

## Estrategias de entrenamiento distribuido

![Comparación de los patrones de particionamiento y comunicación de DP, TP, PP y paralelismo de expertos.](../.gitbook/assets/en-ai-ml-05-model-training-1.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-1.html)

| Estrategia | Unidad particionada | Restricciones que se deben validar |
| --- | --- | --- |
| DDP | Lotes de datos distintos; réplicas del modelo | Memoria de estado de entrenamiento/activación y sincronización de gradientes |
| FSDP / ZeRO | Parámetros, gradientes y estados del optimizador | Comunicación y formatos de checkpoint específicos de cada etapa |
| TP | Operaciones de tensores dentro de las capas | Dimensiones de cabezas/ocultas, backend y topología |
| PP | Etapas de capas | Microlotes, burbujas de pipeline y transferencia de activaciones |
| Paralelismo de expertos | Expertos MoE y distribución de tokens | Desequilibrio, all-to-all y capacidad de enrutamiento |
| Combinaciones | Grupos de DP/TP/PP/contexto/expertos | Malla de dispositivos compatible y número total de ranks |

No supongas que3D siempre es mejor por encima de100B parámetros. Considera la memoria de optimizador, gradientes, activaciones y comunicación además de los pesos; después compara el rendimiento y el costo de recuperación. El all-reduce de DDP no requiere un servidor de parámetros.

TP8×PP4×DP2 significa64ranks. El lote global es **microlote × acumulación × réplicas DP**:1×32×2=64, no2048 al multiplicar de nuevo todos los ranks TP/PP. Con empaquetado de longitud variable, realiza el seguimiento de muestras y tokens por separado.

## Slurm y Slinky

El repositorio oficial es SlinkyProject/slurm-operator. Se verificaron la etiqueta1.2.2 y sus charts OCI; GitHub releases/latest devolvió404, por lo que no se describe como la última versión de GitHub. La documentación1.2 indica Kubernetes1.29 y Slurm25.11(data parser0.0.44) como mínimos. La compatibilidad mínima no es una garantía de ciclo de vida de soporte operativo.

![Roles de Slinky Controller, NodeSet, Accounting y RestApi/LoginSet, con almacenamiento externo y aprovisionamiento de nodos.](../.gitbook/assets/en-ai-ml-05-model-training-2.png)

[Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-05-model-training-2.html)

### APIs y ciclo de vida reales

La versión1.2.2 define Controller, NodeSet, Accounting, LoginSet, RestApi y Token en `slinky.slurm.net/v1beta1`. Los ejemplos anteriores de SlurmCluster/SlurmNodeSet no corresponden a esta API. NodeSet usa controllerRef y una plantilla de Pod. Su scalingMode predeterminado se comporta como StatefulSet; el modo DaemonSet crea un Pod por cada nodo de Kubernetes coincidente e ignora replicas. Estos son modos del controlador NodeSet, no una prueba de que slurmd siempre se ejecute como un recurso Kubernetes DaemonSet.

slurmctld administra el estado de trabajos/nodos/particiones y la programación; conserva su StateSaveLocation. slurmdbd gestiona el acceso y los registros de la base de datos de contabilidad, no sustituye el estado del controlador. Diseña conjuntamente las identidades de login/REST/trabajos, los permisos del sistema de archivos, las claves/JWT de Slurm y la entrega/rotación de credenciales de DB. La exposición pública de SSH mediante NLB no es un requisito predeterminado.

Primero renderiza los charts reales. Estos comandos solo generan archivos locales. Un despliegue operativo requiere por separado el orden de cert-manager/CRD/operator/Slurm, persistencia/base de datos, identidad de usuario e imágenes de Slurm compatibles.

```bash
helm template slurm-api oci://ghcr.io/slinkyproject/charts/slurm-operator-crds   --version 1.2.2 > slurm-crds.yaml
helm template slurm-control oci://ghcr.io/slinkyproject/charts/slurm-operator   --version 1.2.2 --namespace slinky > slurm-operator.yaml
helm template slurm-example oci://ghcr.io/slinkyproject/charts/slurm   --version 1.2.2 --namespace slurm   --set-json 'nodesets={"cpu-example":{}}'   --set partitions.all.enabled=true > slurm-example.yaml
```

Una Application de Argo CD debe hacer referencia a una ruta/revisión de chart real y a valores reales. La configuración inventada compute.partitions/efa.enabled no la configura. Revisa pruning, la eliminación de CRD/PVC, el drenaje/requeue de Slurm y los tiempos de espera de terminación de trabajos. El scale-in de NodeSet y la terminación de EC2 son bucles de control independientes.

### Lanzamiento de torchrun desde Slurm

Ejecuta un launcher de torchrun por nodo, permitiendo que cree procesos por GPU. Las ocho tareas anteriores de Slurm lanzaban cada una ocho procesos, produciendo64procesos por nodo. Este ejemplo pretende4nodos×8procesos; en esta auditoría no se ejecutó ninguna asignación real de Slurm/GPU.

```bash
#!/bin/bash
#SBATCH --job-name=distributed-training
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=8
#SBATCH --cpus-per-task=16
#SBATCH --time=01:00:00
set -euo pipefail

: "${SLURM_NNODES:?Run within an approved Slurm allocation}"
: "${SLURM_JOB_ID:?}"
: "${SLURM_JOB_NODELIST:?}"
export MASTER_ADDR
MASTER_ADDR=$(scontrol show hostnames "$SLURM_JOB_NODELIST" | head -n 1)
export MASTER_PORT=29500

# One torchrun launcher per Slurm node, eight training processes per launcher.
# train.py, dependencies, data, credentials and checkpoints must be prepared.
srun --ntasks="$SLURM_NNODES" --ntasks-per-node=1 bash -c '
  exec torchrun \
    --nnodes="$SLURM_NNODES" \
    --nproc-per-node=8 \
    --node-rank="$SLURM_PROCID" \
    --rdzv-id="$SLURM_JOB_ID" \
    --rdzv-backend=c10d \
    --rdzv-endpoint="$MASTER_ADDR:$MASTER_PORT" \
    /workspace/train.py
'
```

Si Slurm restringe la visibilidad de GPU por tarea, asegúrate de que cada launcher reciba las ocho GPU previstas. train.py debe implementar LOCAL_RANK/RANK/WORLD_SIZE, vinculación de dispositivos, DDP/sampler, datos/modelos versionados y reanudación. El fixture de shell verificó cuatro launchers, ranks de nodo distintos y un endpoint de rendezvous común.

## Comunicación de GPU y EFA

FI_PROVIDER=efa selecciona un proveedor de libfabric; no instala EFA, adjunta interfaces ni integra NCCL. Valida conjuntamente instancias compatibles habilitadas para EFA, driver/libfabric, aws-ofi-nccl, device plugin/asignación de Pod, grupos de seguridad y el transporte real. RAID0 o una etiqueta de subred no habilitan EFA.

Los nodos que se comunican deben compartir una AZ; se recomienda un cluster placement group para el rendimiento. Asegúrate de que los Pods de entrenamiento usen realmente el NodePool restringido. El ancho de banda y los recuentos de dispositivos EFA varían según la instancia;400Gbps no es universal. Forzar ciegamente configuraciones antiguas de Ring/Simple, IB_DISABLE, SOCKET_IFNAME o FI_EFA_USE_DEVICE_RDMA puede interferir con los plugins actuales. Verifica la documentación de la versión, los registros y las pruebas colectivas.

Karpenter budgets.nodes=0 restringe las rutas de interrupción voluntaria; no evita la reclamación de Spot, fallos de nodo, terminación forzada ni todas las expiraciones. Comprueba la interacción de do-not-disrupt/PDB con terminationGracePeriod/expireAfter y conserva la recuperación de checkpoints. Evita obtener instaladores de driver flotantes en cada bootstrap o codificar de forma rígida los relojes de GPU entre tipos de dispositivos.

## BioNeMo

La versión3.0.0 inspeccionada es **BioNeMo Recipes**, que proporciona modelos/checkpoints basados en TransformerEngine y recetas para PyTorch, Accelerate y Lightning. Comprueba la compatibilidad específica de cada receta para ESM-2, AMPLIFY, Geneformer y otros. No ejecutes un módulo MegaMolBART de BioNeMo1.5 como si fuera la API3.0. La evaluación biológica y los permisos de modelo/datos siguen siendo requisitos independientes; la asignación de GPU por sí sola no prepara la receta.

## Trainium y Neuron

Distingue entre SDK2.32.0 torch-neuronx, las implementaciones de entrenamiento/modelo de NeuronX Distributed Training y las rutas de Optimum Neuron. La compatibilidad de inferencia de transformers-neuronx no es compatibilidad general de entrenamiento. Comprueba las versiones de TensorFlow/JAX/PyTorch respecto al hardware/SDK seleccionado en lugar de agregar paquetes pip arbitrarios a un DLC2.18 antiguo.

Optimum Neuron0.4.5 incluye NeuronTrainer/NeuronTrainingArguments e implementaciones dedicadas de modelos de entrenamiento Neuron. Cargar un BertForPreTraining genérico y pasar variables de dataset/tokenizer no definidas no constituye un entrenamiento TP completo. Prepara el modelo/configuración compatibles, etiquetas/collator, tokenizer/revisiones, formatos de optimizador/checkpoint y launcher. El PyTorch2.14 del ejemplo de CPU no afirma compatibilidad con Neuron SDK.

### Trabajos multinodo y precompilación

El paralelismo de Job=4 solo inicia cuatro Pods; no configura ranks ni rendezvous. Los Jobs indexados necesitan completionMode/index y un endpoint maestro compartido. Configurar el MASTER_ADDR de cada Pod con su propio status.podIP dirige a los workers a maestros distintos. Usa una topología de coordinador/controlador y launchers compatibles, y prepara train_lora.py, datos, caché de compilación y dispositivos.

neuron_parallel_compile extrae/compila grafos; no sustituye el entrenamiento real. Ejecuta el entrenamiento por separado después y verifica los aciertos de caché, las formas y las revisiones de compilador/SDK. Consulta las [distinciones de unidades de Neuron](04-inference-frameworks.md) para cores frente a dispositivos.

## Ray Train, MPI y Volcano

Usa la [guía de Train](ray/03-ray-train-tune.md) auditada para Ray2.58/KubeRay1.7. Haz coincidir los recuentos de llamadas a report entre workers e informa objetos Checkpoint reales. get_checkpoint() recupera el estado de recuperación anterior, no un administrador de contexto para un nuevo guardado. resources_per_worker GPU8 no inicia automáticamente ocho procesos DDP dentro de un worker.

MPI Operator0.8.2 usa kubeflow.org/v2beta1. slotsPerWorker declara slots de hostfile; no determina de forma independiente mpirun -np, el mapeo ni la vinculación de GPU. Prepara el código de Launcher/Worker, la implementación de MPI/SSH, imágenes compatibles y CRD/RBAC. Cuatro workers×ocho slots no garantizan por sí mismos32procesos GPU.

Volcano1.15.2 minAvailable cuenta **Pods/miembros**, no nodos EC2. Tres nodos suficientemente aprovisionados pueden alojar cuatro Pods. El plugin gang aplica condiciones mínimas de miembros/recursos, pero no garantiza el inicio simultáneo de contenedores ni el éxito del entrenamiento. Revisa workers adicionales, la compatibilidad con runtime elástico y el comportamiento de RestartJob/requeue.

Los perfiles GPU de JupyterHub deben coincidir con las imágenes/etiquetas de dispositivo y la autorización reales. g5.xlarge es A10G, no un perfil A100. Conecta la configuración al Hub en ejecución y configura almacenamiento por usuario, cuotas, red y eliminación por inactividad.

## Almacenamiento de entrenamiento y checkpoints

Usa las rutas CSI auditadas en la [guía de GPU/almacenamiento](01-ai-ml-workloads.md). Montar un sistema de archivos FSx existente mediante PV estático difiere de crear uno nuevo mediante aprovisionamiento dinámico. No inventes campos FileSystem dataRepositoryAssociations ni mezcles SCRATCH_2 con configuraciones de rendimiento exclusivas de almacenamiento persistente. Verifica por separado las API, políticas y finalización de DRA/import/export.

Una solicitud de capacidad de PVC de EFS no es una cuota de almacenamiento físico. Valida UID/GID del access point, permisos de directorio, identidad CSI, red y mount targets. Un checkpoint local no es duradero remotamente antes de que se complete la transferencia a S3.

La recuperación necesita el modelo, optimizador, scheduler, RNG, scaler cuando se use, cursor de datos/sampler y todos los estados fragmentados. Evita que varios ranks sobrescriban un archivo; usa guardado distribuido compatible con el framework. Valida manifiestos/sumas de comprobación de finalización, transferencia remota y restauración antes de eliminar los checkpoints válidos anteriores. Una imagen inventada de checkpoint-manager o un ConfigMap auto_resume=true no implementan estas funciones.

### Ejemplo ejecutable pequeño de CPU

Este ejemplo sintético de16muestras y un hilo de CPU realiza cuatro actualizaciones del optimizador. Demuestra acumulación, un schedule coseno acotado, sustitución mediante archivo temporal y restauración de optimizador/RNG. PyTorch2.14.0+cpu produjo resultados idénticos para el entrenamiento ininterrumpido y la reanudación después de dos pasos. Esto no es una prueba de GPU, distribuida ni de durabilidad remota.

```python
from pathlib import Path
import math
import os
import tempfile
import torch


def lr_factor(step, warmup_steps, total_steps, min_ratio=0.1):
    if not 0 <= warmup_steps < total_steps or not 0 <= min_ratio <= 1:
        raise ValueError("Invalid schedule bounds")
    if step < 0:
        raise ValueError("Step must be non-negative")
    if step < warmup_steps:
        return step / max(1, warmup_steps)
    progress = min(1.0, (step - warmup_steps) / (total_steps - warmup_steps))
    return min_ratio + (1 - min_ratio) * (1 + math.cos(math.pi * progress)) / 2


def save_checkpoint(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
            temporary = output.name
            torch.save(state, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def train_toy(checkpoint_path, stop_after=4, resume=False):
    # Tiny deterministic CPU example; no GPU, dataset or model download.
    torch.set_num_threads(1)
    torch.manual_seed(17)
    model = torch.nn.Linear(2, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05, momentum=0.9)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda step: lr_factor(step, 1, 4)
    )
    inputs = torch.arange(32, dtype=torch.float32).reshape(16, 2) / 32
    targets = inputs.sum(dim=1, keepdim=True)
    start = 0
    if resume:
        saved = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        scheduler.load_state_dict(saved["scheduler"])
        torch.set_rng_state(saved["torch_rng"])
        start = saved["optimizer_step"]
    if not start <= stop_after <= 4:
        raise ValueError("Invalid stopping point")
    for step in range(start, stop_after):
        optimizer.zero_grad(set_to_none=True)
        # Two equal-sized microbatches per optimizer update.
        for microbatch in range(2):
            offset = step * 4 + microbatch * 2
            prediction = model(inputs[offset:offset + 2])
            loss = torch.nn.functional.mse_loss(prediction, targets[offset:offset + 2]) / 2
            loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        save_checkpoint(checkpoint_path, {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "optimizer_step": step + 1,
            "torch_rng": torch.get_rng_state(),
        })
    return {name: value.detach().clone() for name, value in model.state_dict().items()}


if __name__ == "__main__":
    path = Path("toy-training.pt")
    train_toy(path, stop_after=2)
    train_toy(path, stop_after=4, resume=True)
    print("Completed four CPU optimizer updates, including checkpoint resume.")
```

El ejemplo demuestra la sustitución de archivos completados en un sistema de archivos, no la durabilidad frente a fallos del sistema de archivos/metadatos de directorios, las transacciones S3 ni los protocolos de checkpoint distribuido. Su orden fijo de datos tampoco implementa la recuperación general de sampler. Elige intervalos/retención de checkpoints usando la latencia de guardado, tasa de fallos, trabajo perdido aceptable y costo, en lugar de una regla universal de500pasos/cinco copias.

## Precisión numérica y optimización de memoria

Las API actuales de PyTorch usan torch.amp.autocast y torch.amp.GradScaler. BF16 comparte el número de bits de exponente de FP32, no la precisión de mantisa ni el valor finito máximo exacto. Normalmente evita el escalado de pérdida al estilo FP16, pero verifica el hardware, las operaciones y la convergencia. Autocast no convierte todos los pesos/estados del optimizador a BF16.

El checkpointing de activaciones vuelve a calcular activaciones durante backward, intercambiando cómputo por memoria. Difiere de los checkpoints en disco y no garantiza ni ahorros de3–4x ni una ralentización del30%. Especifica use_reentrant explícitamente y valida gradientes, dropout/RNG y capas con estado.

La selección de backend de Flash Attention/SDPA depende de dtype, tamaño de cabeza, dispositivo y máscaras. Define el estado de entrenamiento y pasa dropout_p=0 durante la evaluación. Comprueba la compatibilidad de API para combinaciones de máscara explícita/causal; use_cache=False por sí solo no instala un backend de atención.

DeepSpeed0.19.6 ZeRO1 particiona el estado del optimizador;2 añade gradientes;3 añade parámetros. La descarga a CPU/NVMe se configura por separado, no se habilita automáticamente con Stage3. Distingue las integraciones de nivel superior que sustituyen valores auto de la configuración pura de DeepSpeed. Los buffers, activaciones y la capa más grande impiden una reducción de memoria ilimitada.

Avanza los schedulers por actualizaciones del optimizador en lugar de micropasos de acumulación. Limita el progreso para que el coseno no vuelva a subir después del horizonte de entrenamiento y valida los límites de warmup/pasos totales como en el ejemplo.

## Alcance de la verificación

Se revisaron toda la prosa de las guías/cuestionarios y76bloques de código originales únicos. Las comprobaciones cubren Helm/CRD oficiales de Slinky, API de MPI/Volcano y fuentes de SDK, entrenamiento/reanudación pequeño de CPU y un fixture de launcher de shell. No se ejecutó ninguna GPU/Neuron/EFA, clúster Slurm/MPI, modelo preentrenado real ni recurso en la nube. La verificación local de código/esquema difiere de la validación de despliegue en producción.

## Referencias

- [Slinky 1.2.2](https://github.com/SlinkyProject/slurm-operator/tree/v1.2.2)
- [Controlador Slurm](https://slurm.schedmd.com/slurmctld.html)
- [Daemon de contabilidad de Slurm](https://slurm.schedmd.com/slurmdbd.html)
- [MPI Operator 0.8.2](https://github.com/kubeflow/mpi-operator/tree/v0.8.2)
- [Plugin gang de Volcano 1.15.2](https://github.com/volcano-sh/volcano/blob/v1.15.2/pkg/scheduler/plugins/gang/gang.go)
- [Red EFA de EKS](https://docs.aws.amazon.com/eks/latest/best-practices/aiml-networking.html)
- [Recetas BioNeMo 3.0.0](https://github.com/NVIDIA/bionemo-framework/tree/v3.0.0)
- [Optimum Neuron 0.4.5](https://github.com/huggingface/optimum-neuron/tree/v0.4.5)
- [Neuron SDK 2.32.0](https://github.com/aws-neuron/aws-neuron-sdk/tree/v2.32.0)
- [Launcher de PyTorch 2.14](https://github.com/pytorch/pytorch/blob/v2.14.0/torch/distributed/run.py)
- [Configuración ZeRO de DeepSpeed 0.19.6](https://github.com/deepspeedai/DeepSpeed/blob/v0.19.6/deepspeed/runtime/zero/config.py)

## Cuestionario

[Cuestionario de entrenamiento de modelos](../quizzes/ai-ml/05-model-training-quiz.md)
