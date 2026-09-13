# Kubeflow en EKS: análisis en profundidad

> **Línea base de revisión**: Kubeflow Community Distribution 26.03.1
> **Última revisión**: September 12, 2026

## Descripción general

Kubeflow proporciona herramientas basadas en Kubernetes para pipelines de ML, notebooks, ajuste (tuning), entrenamiento y serving. La Community Distribution reúne revisiones de componentes, servicios compartidos y un dashboard; los proyectos individuales también tienen sus propias versiones y requisitos de instalación.

La CNCF [anunció la graduación de Kubeflow el 17 de agosto de 2026](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/). Esto reconoce la madurez y el gobierno del proyecto, incluida una auditoría de seguridad independiente. No certifica la seguridad ni el cumplimiento normativo de un despliegue concreto en EKS.

## Mapa de componentes

| Componente | Propósito | API o concepto | Guía |
| --- | --- | --- | --- |
| Dashboard, Profiles, gestión de acceso | Navegación de la UI, propiedad y pertenencia de namespaces | `Profile` de ámbito de clúster; cuota opcional | [Parte 1](01-architecture-installation.md) |
| Pipelines | Compilar y ejecutar workflows; hacer seguimiento de ejecuciones y artefactos | APIs de Pipeline/Run/Experiment; el modo opcional Kubernetes Native API añade los CRDs `Pipeline`/`PipelineVersion` | [Parte 2](02-pipelines.md) |
| Notebooks | Cargas de trabajo de notebooks de usuario | `Notebook`; configuración de imagen y PVC | [Parte 3](03-notebooks.md) |
| Katib | Búsqueda de hiperparámetros y trials | CRDs `Experiment`, `Trial`, `Suggestion` | [Parte 4](04-katib.md) |
| Trainer | Entrenamiento distribuido con runtimes configurados | `TrainJob`, `TrainingRuntime`, `ClusterTrainingRuntime` | [Parte 5](05-training-operator.md) |
| KServe | Servicios de inferencia de modelos | `InferenceService`; dependencias específicas de cada modo | [Parte 6](06-kserve.md) |

Este mapa cubre el alcance de la guía, no la distribución completa. La versión 26.03.1 también incluye Hub/registro de modelos y Spark Operator. Un Experiment de KFP no es el CRD Experiment de Katib.

![Mapa de componentes de Kubeflow que separa la navegación del dashboard de las integraciones configuradas explícitamente para pipelines, ajuste, entrenamiento y despliegue de modelos.](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

El dashboard enlaza las UIs de los componentes. Pipelines y Katib usan Trainer solo cuando su implementación envía explícitamente un recurso de entrenamiento compatible. Conectar un artefacto entrenado con KServe requiere un paso de despliegue independiente; el diagrama no implica una promoción automática del modelo.

## Por qué ejecutarlo en EKS

Una plataforma EKS existente puede compartir con las cargas de trabajo de ML la gestión de capacidad, la integración de almacenamiento, la identidad de cargas de trabajo (workload identity) y la monitorización. La compatibilidad sigue dependiendo de la versión de Kubernetes, la arquitectura de CPU, las imágenes, la red, los drivers de almacenamiento y la autenticación. La conformidad con Kubernetes por sí sola no es suficiente; la documentación de la versión indica que la cobertura de imágenes ARM64 es incompleta.

El equipo sigue siendo responsable de las actualizaciones de componentes/CRDs, la autorización de tenants, los datos persistentes, las credenciales y la recuperación. [Amazon SageMaker AI](../sagemaker-ai/README.md) reduce algunas responsabilidades de infraestructura, mientras que el acceso a datos, la corrección de la aplicación, la calidad del modelo y el control de costes siguen necesitando responsables. Elija en función de las interfaces necesarias, la capacidad operativa y las restricciones de la carga de trabajo.

## Contenido cubierto actualmente

1. [Parte 1: Arquitectura e instalación en EKS](01-architecture-installation.md) — versión actual de la comunidad, limitaciones de la antigua distribución de AWS, Profiles, identidad y renderizado de manifests.
2. [Parte 2: Pipelines](02-pipelines.md) — SDK v2, compilación, ejecución y almacenamiento de artefactos.
3. [Parte 3: Notebooks](03-notebooks.md) — cargas de trabajo, Profiles, almacenamiento y ubicación de GPU.
4. [Parte 4: Katib](04-katib.md) — experiments, trials, búsqueda y parada temprana (early stopping).
5. [Parte 5: Trainer](05-training-operator.md) — APIs del antiguo Training Operator y de Trainer v2.
6. [Parte 6: KServe](06-kserve.md) — recursos de inferencia, modos de despliegue y rollouts.

Utilice la línea base de componentes de cada capítulo. Consulte la [versión 26.03.1](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1) y el [inventario fijado](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md) antes de seleccionar una instalación.
