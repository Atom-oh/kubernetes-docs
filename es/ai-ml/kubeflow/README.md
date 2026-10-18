# Kubeflow en EKS: análisis en profundidad

> **Versión de referencia de la revisión**: Kubeflow Community Distribution 26.03.1
> **Última distribución comprobada**: Community Distribution 26.03.1; las versiones de los componentes se siguen por separado
> **Última revisión**: 12 de octubre de 2026

## Descripción general

Kubeflow proporciona herramientas basadas en Kubernetes para pipelines de ML, notebooks, ajuste de hiperparámetros, entrenamiento y serving. Community Distribution reúne revisiones de componentes, servicios compartidos y un dashboard; cada proyecto también tiene sus propias versiones y requisitos de instalación.

Esta serie usa KFP 2.16.1 y KServe 0.18.0 de la distribución como versiones de referencia para la reproducción.

KFP 2.17.2 y KServe 0.21.0 son versiones posteriores e independientes. No están incluidas en Community Distribution 26.03.1, y esta guía no establece que sean compatibles entre sí. Comprueba el inventario fijado de la distribución junto con las versiones actuales de los componentes.

CNCF [anunció la graduación de Kubeflow el 17 de agosto de 2026](https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation-solidifying-the-standard-for-cloud-native-ai-operations/). Esto reconoce la madurez y la gobernanza del proyecto, incluida una auditoría de seguridad independiente. No certifica la seguridad ni el cumplimiento normativo de una implementación concreta en EKS.

## Mapa de componentes

| Componente | Propósito | API o concepto | Guía |
| --- | --- | --- | --- |
| Dashboard, Profiles, gestión de acceso | Navegación de la interfaz de usuario, propiedad del namespace y membresía | `Profile` con ámbito de clúster; cuota opcional | [Parte 1](01-architecture-installation.md) |
| Pipelines | Compilar y ejecutar flujos de trabajo; hacer seguimiento de ejecuciones y artefactos | API de Pipeline/Run/Experiment; el modo opcional Kubernetes Native API añade CRD `Pipeline`/`PipelineVersion` | [Parte 2](02-pipelines.md) |
| Notebooks | Cargas de trabajo de notebooks de usuario | `Notebook`; configuración de imagen y PVC | [Parte 3](03-notebooks.md) |
| Katib | Búsqueda de hiperparámetros y pruebas | CRD `Experiment`, `Trial`, `Suggestion` | [Parte 4](04-katib.md) |
| Trainer | Entrenamiento distribuido con runtimes configurados | `TrainJob`, `TrainingRuntime`, `ClusterTrainingRuntime` | [Parte 5](05-training-operator.md) |
| KServe | Servicios de inferencia de modelos | `InferenceService`; dependencias específicas del modo | [Parte 6](06-kserve.md) |

Este mapa cubre el alcance de la guía, no toda la distribución. La versión 26.03.1 también incluye Hub/registro de modelos y Spark Operator. Un KFP Experiment no es el CRD Experiment de Katib.

![Mapa de componentes de Kubeflow que separa la navegación del dashboard de las integraciones configuradas explícitamente para pipelines, ajuste, entrenamiento e implementación de modelos.](../../.gitbook/assets/en-ai-ml-kubeflow-readme-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-readme-0.html)

El dashboard enlaza las interfaces de usuario de los componentes. Pipelines y Katib usan Trainer solo cuando su implementación envía explícitamente un recurso de entrenamiento compatible. Conectar un artefacto entrenado a KServe requiere un paso de implementación independiente; el diagrama no implica una promoción automática del modelo.

## Por qué ejecutar esto en EKS

Una plataforma EKS existente puede compartir la gestión de capacidad, la integración de almacenamiento, la identidad de las cargas de trabajo y la monitorización con las cargas de trabajo de ML. La compatibilidad sigue dependiendo de la versión de Kubernetes, la arquitectura de CPU, las imágenes, la red, los controladores de almacenamiento y la autenticación. La conformidad con Kubernetes por sí sola no basta; la documentación de la versión señala que la cobertura de imágenes ARM64 es incompleta.

El equipo sigue siendo responsable de las actualizaciones de componentes y CRD, la autorización de tenants, los datos persistentes, las credenciales y la recuperación. [Amazon SageMaker AI](../sagemaker-ai/README.md) reduce algunas responsabilidades de infraestructura, mientras que el acceso a los datos, la corrección de las aplicaciones, la calidad de los modelos y el control de costes siguen necesitando responsables. Elige según las interfaces necesarias, la capacidad operativa y las restricciones de las cargas de trabajo.

## Contenido actual

1. [Parte 1: Arquitectura e instalación en EKS](01-architecture-installation.md): versión comunitaria actual, limitaciones de la distribución heredada de AWS, Profiles, identidad y renderizado de manifiestos.
2. [Parte 2: Pipelines](02-pipelines.md): SDK v2, compilación, ejecución y almacenamiento de artefactos.
3. [Parte 3: Notebooks](03-notebooks.md): cargas de trabajo, Profiles, almacenamiento y asignación de GPU.
4. [Parte 4: Katib](04-katib.md): experimentos, pruebas, búsqueda y detención temprana.
5. [Parte 5: Trainer](05-training-operator.md): Training Operator heredado y API de Trainer v2.
6. [Parte 6: KServe](06-kserve.md): recursos de inferencia, modos de implementación y despliegues graduales.

Usa la versión de referencia del componente indicada en cada capítulo. Comprueba la [versión 26.03.1](https://github.com/kubeflow/community-distribution/releases/tag/26.03.1), el [inventario fijado](https://github.com/kubeflow/community-distribution/blob/26.03.1/README.md), [KFP 2.17.2](https://github.com/kubeflow/pipelines/releases/tag/2.17.2) y [KServe 0.21.0](https://github.com/kserve/kserve/releases/tag/v0.21.0) antes de elegir una instalación.
