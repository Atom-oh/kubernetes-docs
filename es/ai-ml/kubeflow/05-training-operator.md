# Parte 5: Kubeflow Trainer y entrenamiento distribuido

> **Línea base de revisión**: Trainer 2.2.0 / Community Distribution 26.03.1; comparación de actualización independiente a 2.3.0
> **Última actualización**: 12 de septiembre de 2026

## Configuración del entorno de laboratorio

Usa versiones compatibles de Kubernetes, el controlador/los CRD de Trainer, los runtimes y sus dependencias, como JobSet. El uso de GPU depende de la carga de trabajo; también es posible entrenar con CPU. Las cargas de trabajo con GPU requieren además controladores, complementos de dispositivo, capacidad de nodos y redes. La validación que se realiza aquí consiste en renderizar Helm e inspeccionar esquemas, no en ejecutar entrenamientos.

## De los operadores específicos de cada framework a una API unificada

El entrenamiento distribuido en Kubernetes ha atravesado un cambio arquitectónico real dentro del proyecto Kubeflow, y es lo más importante que hay que entender antes de tocar cualquier YAML.

### El Training Operator original (v1)

El Training Operator que Kubeflow consolidó en 2021 adoptó un enfoque de **CRD específicos para cada framework**. Cada framework de ML compatible obtuvo su propia definición de recurso personalizado, cada una con su propio controlador que implementaba la semántica particular de entrenamiento distribuido de ese framework:

* **`PyTorchJob`**: el controlador entendía las convenciones de lanzamiento distribuido de PyTorch e inyectaba variables de entorno como `MASTER_ADDR`, `RANK` y `WORLD_SIZE` en cada Pod de worker para que `torch.distributed` pudiera formar un grupo de procesos.
* **`TFJob`**: en cambio, el controlador construía una variable de entorno `TF_CONFIG` (un bloque JSON que describía los roles de las tareas del clúster: chief, worker y parameter server) que esperan las estrategias de distribución de TensorFlow.
* **`MPIJob`**: el controlador se encargaba de lanzar un trabajo MPI en varios Pods y coordinar un lanzador al estilo de `mpirun` con un conjunto de Pods de worker.

Además de estos tres, el Training Operator v1 también incluía CRD para algunos otros frameworks. Cada CRD codificaba directamente en un controlador distinto la idea de cada framework sobre «cómo se encuentran los workers entre sí y acuerdan sus roles», por lo que añadir un framework requería integración, aunque se podía seguir reutilizando la infraestructura compartida del controlador de Job.

### El cambio a Kubeflow Trainer v2

Kubeflow Trainer v2 reemplaza este enfoque por una API única y unificada, basada en dos conceptos en lugar de un CRD por framework:

* **`TrainJob`**: describe *qué* ejecutar: el script/punto de entrada de entrenamiento, los argumentos, la cantidad de recursos (por ejemplo, el número de workers) y una referencia al runtime que debe ejecutarlo. Es el objeto que crea un profesional de ML para una ejecución de entrenamiento individual.
* **`TrainingRuntime` / `ClusterTrainingRuntime`**: describe *cómo* ejecutarlo: una plantilla de ejecución reutilizable y específica del framework que abarca la imagen del contenedor, los mecanismos de lanzamiento distribuido (cómo se detectan los workers entre sí y qué variables de entorno o proceso lanzador se utilizan) y la configuración predeterminada de recursos. Un equipo de plataforma define una pequeña cantidad de estos runtimes una sola vez (por ejemplo, un runtime PyTorch DDP y un runtime MPI), y muchos `TrainJob` distintos hacen referencia al mismo runtime en numerosas ejecuciones de entrenamiento.

Esto refleja un patrón que también se ve en otras partes de Kubernetes: separar un recurso de «plantilla» reutilizable de la «instancia» que lo consume, de manera similar a como un `StorageClass` es una plantilla reutilizable a la que hacen referencia muchos `PersistentVolumeClaim`. La ventaja práctica es que un equipo de plataforma puede administrar y versionar en un solo lugar los complejos mecanismos de lanzamiento distribuido (el runtime), mientras que los profesionales de ML que envían trabajos solo tienen que proporcionar su script y solicitar un runtime por nombre. El runtime reduce la configuración repetida, pero el código de entrenamiento aún debe gestionar la inicialización distribuida compatible, la fragmentación de datos, los puntos de control y la recuperación.

### Diferencias entre 2.2.0 y 2.3.0

[Trainer 2.2.0](https://github.com/kubeflow/trainer/releases/tag/v2.2.0) se publicó el 20 de marzo de 2026 y está incluido en 26.03.1. Añade runtimes de JAX/XGBoost y la política/integración de Flux; la inclusión de una función no demuestra que sea compatible con todas las configuraciones de imagen, red o acelerador.

La versión 2.2.0 también reemplaza `PodTemplateOverrides` por `RuntimePatches`, elimina `numProcPerNode` de la política Torch y elimina `ElasticPolicy`. No confundas una política Torch del runtime con `trainer.numProcPerNode` por ejecución. Los manifiestos de versiones anteriores de 2.x también pueden requerir una migración.

El progreso y las métricas del runtime en `status.trainerStatus` requieren la **feature gate alfa TrainJobStatus, deshabilitada de forma predeterminada**. El código de entrenamiento debe informar al servidor de estado y disponer de acceso funcional a TLS y al token proyectado de ServiceAccount. Los valores de entorno de token/CA inyectados son rutas de archivo, no el contenido de secretos. Imprimir solo registros no completa automáticamente las métricas de estado.

[La versión 2.3.0](https://github.com/kubeflow/trainer/releases/tag/v2.3.0), publicada el 7 de agosto de 2026, cambia los finalizadores/instantáneas del runtime y la ubicación de los CRD de Helm. Sus notas de versión exigen que las instalaciones 2.0/2.1/2.2 pasen por la versión 2.3 antes de actualizar a versiones posteriores. Revisa la propiedad de los CRD en Helm y la migración específica de la versión antes de actualizar; eliminar los CRD existentes no es una solución habitual para una actualización.

Los charts OCI publicados también difieren: 2.2 renderiza directamente ocho runtimes predeterminados, mientras que 2.3 los empaqueta en un ConfigMap runtimes.yaml que aplica un Job instalador posterior a la instalación o actualización. El hook de 2.3 instala kubectl durante la ejecución, aplica los recursos de forma forzada en el servidor y elimina los recursos según su etiqueta de administración; también existe un hook previo a la eliminación. Revisa el tratamiento de hooks en GitOps, el acceso a la red y la propiedad de los runtimes. En esta revisión se renderizaron los hooks, pero no se ejecutaron.

### Migración de las API heredadas

26.03.1 incluye Trainer 2.2.0 y el Training Operator heredado 1.9.2. Su coexistencia no revela el avance de la migración de ningún equipo. PyTorchJob/TFJob/MPIJob y TrainJob son API distintas y no se convierten automáticamente.

El [documento oficial de migración fijado a una versión](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md) ofrece un ejemplo de PyTorchJob a runtime Torch predeterminado y orientación sobre el SDK, no una correspondencia exhaustiva para cada framework/campo. Compara los roles de réplica, los comandos de lanzamiento, el entorno, los reintentos, el almacenamiento, la programación/redes y la recuperación de puntos de control para cada carga de trabajo.

## Responsabilidades de TrainJob y Runtime

`TrainingRuntime` tiene ámbito de espacio de nombres; `ClusterTrainingRuntime` tiene ámbito de clúster. Ambos contienen plantillas de ejecución y políticas de ML. `TrainJob.runtimeRef` selecciona el tipo/nombre, mientras que los campos de trainer permiten configurar el comando/los argumentos, la cantidad de Pods de entrenamiento y los recursos por Pod. Los permisos y las anulaciones permitidas deben administrarse por separado.

El runtime `torch-distributed` predeterminado tiene `mlPolicy.numNodes: 1`, `torch: {}` y una plantilla JobSet. En 2.2.0 hace referencia a `pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime`. Registra las revisiones de la imagen/runtime y verifica la arquitectura, los controladores y las bibliotecas de comunicación; en esta revisión no se ejecutó la imagen ni se entrenó un modelo.

En este caso, numNodes representa la cantidad de Pods de entrenamiento, no una correspondencia uno a uno con la cantidad de instancias EC2. Calcula por separado los procesos, las GPU por Pod y la ubicación de varios Pods.

## Mecanismos del entrenamiento distribuido en Kubernetes

JobSet y los runtimes componen Jobs/Pods y usan Service/DNS, junto con la configuración de rank/rendezvous, para detectar procesos. Un Service headless por sí solo no conserva el estado de los procesos ni las direcciones IP; la asignación de nombres estable a los Pods, el nombre de host/subdominio y las condiciones de red siguen siendo importantes.

**Instalar Trainer no habilita automáticamente la programación por grupos (gang scheduling).** El runtime Torch predeterminado de 2.2.0 no tiene podGroupPolicy. Para esas rutas de PodGroup, deben instalarse/configurarse las políticas Coscheduling/Volcano, los CRD y la integración con el scheduler. La admisión de Kueue también es distinta de la programación real de los Pods.

El entrenamiento síncrono de tamaño fijo requiere que todos los procesos necesarios estén listos para comunicarse, pero no es necesario que los nodos se creen en el mismo instante. El aprovisionamiento secuencial puede funcionar si se mantienen los tiempos de espera de rendezvous; las cargas de trabajo elásticas compatibles siguen otras reglas. La admisión por grupos reduce la asignación parcial, pero no puede resolver todas las limitaciones de capacidad de EC2 ni los bloqueos de la aplicación. Coordina la capacidad de [Karpenter](../../autoscaling/02-karpenter.md) con los tiempos de espera/reintentos de JobSet, el scheduler y el framework.

![Trainer compone TrainJob y runtime en JobSet; se muestran por separado la programación opcional de PodGroup y los informes de estado del runtime con activación explícita.](../../.gitbook/assets/en-ai-ml-kubeflow-05-training-operator-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-05-training-operator-0.html)

## Referencia cruzada: Katib y TrainJob

Katib 0.19.0 puede usar TrainJob en una plantilla Trial configurada. Haz coincidir el registro de trialResources, el runtime, las condiciones de éxito/fracaso, los Pods/contenedores principales y la recopilación de métricas. Los informes de métricas de Katib son independientes del servidor de estado de Trainer, que requiere activación explícita. Un TrainJob correcto no implementa automáticamente un modelo en KServe.

## Validación y fuentes

Se obtuvieron y renderizaron los gráficos Helm OCI oficiales de Trainer 2.2.0 y 2.3.0 con los runtimes predeterminados habilitados; se inspeccionaron los esquemas de CRD/runtime. No se ejecutaron la admisión de API/CEL, las actualizaciones reales, la creación de JobSet, el entrenamiento distribuido/con GPU ni los informes al servidor de estado.

- [API TrainJob de 2.2.0](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/apis/trainer/v1alpha1/trainjob_types.go)
- [Puerta de funciones predeterminada de TrainJobStatus](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/features/features.go)
- [Creación condicional de PodGroup para Coscheduling](https://github.com/kubeflow/trainer/blob/v2.2.0/pkg/runtime/framework/plugins/coscheduling/coscheduling.go)
- [Runtime Torch predeterminado](https://github.com/kubeflow/trainer/blob/v2.2.0/manifests/base/runtimes/torch_distributed.yaml)

## Próximos pasos

Una vez establecido el paso de los CRD específicos de cada framework al modelo unificado `TrainJob`/runtime, la [Parte 6: KServe (servicio de modelos en Kubernetes)](./06-kserve.md) explica qué ocurre con un modelo cuando termina el entrenamiento con un `TrainJob`: cómo servirlo para inferencias.

[Volver a la página principal](./README.md)

## Cuestionario

Para poner a prueba lo que has aprendido en este capítulo, prueba el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/05-training-operator-quiz.md).
