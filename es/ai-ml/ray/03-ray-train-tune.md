# Parte 3: Ray Train y Ray Tune

> **Versiones compatibles**: Ray 2.57.0
> **Última actualización**: August 20, 2026

## Configuración del entorno de laboratorio

Para seguir los ejemplos de este documento, necesitarás las siguientes herramientas y el siguiente entorno:

### Herramientas necesarias

* Python 3.10 o posterior
* `pip install "ray[train,tune]"`
* Acceso a un clúster de Ray (consulta [Parte 2: El operador KubeRay](02-kuberay-operator.md) para configurar uno en EKS, o ejecuta `ray.init()` localmente para los ejemplos de este documento)

## Ray Train: entrenamiento distribuido sobre las primitivas de Ray

[Parte 1](01-architecture.md) presentó las primitivas principales de Ray: tareas, actores y el almacén de objetos. Es posible escribir un trabajo de entrenamiento distribuido directamente sobre esas primitivas, pero implica implementar manualmente una gran cantidad de código repetitivo: iniciar un proceso de worker por GPU, configurar el grupo de comunicación que esos workers utilizan para sincronizar gradientes y coordinar checkpoints de forma coherente entre todos ellos.

**Ray Train** es una biblioteca, construida sobre las primitivas de tareas y actores de Ray, que gestiona ese código repetitivo. Toma una función de entrenamiento escrita con una API de framework conocida — PyTorch es el caso más común, aunque Ray Train también admite otros frameworks — y la ejecuta en tantos workers distribuidos como solicites, sin que el autor de la función de entrenamiento tenga que administrar directamente el inicio de workers, la comunicación entre workers ni la coordinación de checkpoints.

### Ray Train V2

La API pública de Ray Train ha evolucionado a lo largo de la historia del proyecto. La ruta de importación de cara al usuario sigue siendo `ray.train.torch.TorchTrainer` para el entrenamiento con PyTorch, pero la implementación detrás de esa ruta se ha reescrito — esta reescritura ("Train V2") consolidó y simplificó el funcionamiento interno de la generación anterior de clases Trainer, y ahora es la implementación predeterminada que se obtiene con esa misma importación. Si encuentras una base de código antigua fijada a una versión de Ray anterior a la llegada de esta reescritura, considera que se ejecuta sobre la implementación anterior en lugar de asumir que está rota; consulta la documentación de Ray en docs.ray.io para conocer los detalles, ya que la versión exacta en la que cambió la implementación predeterminada es el tipo de detalle que varía entre las versiones de Ray.

## Conceptos principales de Ray Train

### Trainer

Un **Trainer** — como `TorchTrainer` — encapsula una función de entrenamiento proporcionada por el usuario. La función de entrenamiento contiene la lógica habitual de entrenamiento de modelos para el framework elegido: construir el modelo, iterar sobre lotes, calcular la pérdida y actualizar el optimizador. El Trainer se encarga de iniciar esa función una vez por worker, en un grupo de procesos distribuidos que espera el entrenamiento paralelo de datos del framework subyacente (por ejemplo, un grupo de procesos PyTorch DDP), por lo que la propia función de entrenamiento no necesita configurarlo manualmente.

### ScalingConfig

Una **ScalingConfig** indica al Trainer cuántos workers debe iniciar y qué recursos necesita cada uno — por ejemplo, cuántos workers ejecutar y si cada worker requiere una GPU. El Trainer utiliza esta configuración para solicitar los recursos correspondientes al clúster de Ray subyacente, del mismo modo que cualquier otra tarea o actor de Ray.

### Checkpointing

Los workers de Ray Train pueden informar checkpoints durante el entrenamiento. Un checkpoint captura suficiente estado — normalmente los pesos del modelo y el estado del optimizador — para reanudar el entrenamiento desde ese punto en lugar de hacerlo desde cero. Esto cumple dos propósitos: permite que un trabajo de entrenamiento distribuido de larga duración se recupere después de un fallo de worker sin perder todo el progreso previo, y entrega un modelo entrenado a lo que siga en el flujo de trabajo, ya sea una decisión posterior de ajuste de hiperparámetros (que se trata a continuación) o registrar el resultado como una versión del modelo (conceptualmente similar a lo que cubre el material de MLflow Model Registry de este sitio de documentación, aunque dicho material no es específico de Ray).

## Ray Tune: búsqueda de hiperparámetros en todo el clúster

**Ray Tune** es una biblioteca de ajuste de hiperparámetros, también construida sobre Ray, que ejecuta muchos ensayos de entrenamiento en paralelo en todo el clúster y utiliza un algoritmo de búsqueda conectable para decidir qué combinaciones de hiperparámetros probar a continuación. Cada ensayo entrena un modelo con un conjunto concreto de hiperparámetros e informa un resultado que el algoritmo de búsqueda de Tune puede utilizar para decidir qué probar después.

Esto es conceptualmente paralelo a lo que describe el subárbol de Kubeflow de este sitio de documentación para Katib, excepto que Tune es una biblioteca nativa del ecosistema de Ray en lugar de un sistema independiente basado en CRD de Kubernetes.

## Combinación de Ray Train y Ray Tune

Un ensayo que ejecuta Ray Tune no tiene por qué ser una función de un solo proceso. Un patrón habitual es proporcionar a Tune un `Trainer` de Ray Train como el elemento entrenable sobre el que realiza la búsqueda: cada ensayo de hiperparámetros se convierte entonces en su propia ejecución distribuida de Ray Train, que potencialmente abarca varias GPU o varios nodos.

Esta combinación es importante siempre que entrenar un modelo sea lo suficientemente costoso como para que un único ensayo necesite entrenamiento distribuido para terminar en un tiempo razonable. Sin ella, un equipo se enfrentaría a una elección incómoda: ajustar los hiperparámetros en serie frente a un trabajo de entrenamiento distribuido, o renunciar al entrenamiento distribuido durante la fase de búsqueda. Como ambas bibliotecas comparten las mismas primitivas subyacentes de Ray, Tune puede dirigir muchas ejecuciones simultáneas de Ray Train, cada una con su propio conjunto de workers distribuidos, sin que ninguna de las bibliotecas necesite código de integración para casos especiales con la otra.

```mermaid
flowchart TB
    Driver["Ray Tune Driver<br/>(search algorithm)"]

    subgraph Trial1["Trial 1: Ray Train run"]
        T1W1["Worker Actor 1"]
        T1W2["Worker Actor 2"]
        T1OS[(("Object Store"))]
        T1W1 <--> T1OS
        T1W2 <--> T1OS
    end

    subgraph Trial2["Trial 2: Ray Train run"]
        T2W1["Worker Actor 1"]
        T2W2["Worker Actor 2"]
        T2OS[(("Object Store"))]
        T2W1 <--> T2OS
        T2W2 <--> T2OS
    end

    Driver -->|launches with hyperparameter set A| Trial1
    Driver -->|launches with hyperparameter set B| Trial2
    Trial1 -->|reports results/checkpoints| Driver
    Trial2 -->|reports results/checkpoints| Driver
    Driver -->|decides next round of trials| Driver

    style Driver fill:#4fc3f7
    style Trial1 fill:#81c784
    style Trial2 fill:#ffb74d
```

## Asignación de recursos y el escalador automático del clúster

Tanto Ray Train como Ray Tune solicitan las CPU y GPU de sus workers mediante el mecanismo normal de solicitud de recursos para tareas y actores de Ray descrito en [Parte 1](01-architecture.md) — no existe una ruta de solicitud de recursos separada específica para el entrenamiento o el ajuste. Esto es importante en EKS porque es precisamente lo que permite al escalador automático gestionado por KubeRay, tratado en [Parte 2](02-kuberay-operator.md), reaccionar a la demanda real de recursos de un trabajo de entrenamiento o ajuste. No es necesario dimensionar un clúster desde el principio para el trabajo más grande que jamás ejecutará; el escalador automático puede solicitar más nodos de worker a medida que un barrido de Ray Tune inicia más ensayos simultáneos y volver a reducir la escala cuando los ensayos finalicen.

## Nota práctica: co-programación y tiempo de aprovisionamiento de nodos GPU en EKS

Los procesos de worker distribuidos que componen una única ejecución de Ray Train normalmente deben programarse conjuntamente — todos ellos deben estar activos y tener asignadas sus GPU al mismo tiempo antes de que pueda establecerse el grupo de comunicación que forman, de forma similar a las necesidades de programación en grupo tratadas en otras partes de este sitio de documentación para otros sistemas de entrenamiento distribuido. Si el escalador automático del clúster no puede aprovisionar todos los workers de GPU solicitados dentro de un intervalo razonable, una ejecución de entrenamiento puede quedar bloqueada esperando que se inicien los últimos workers.

Esto interactúa directamente con el tiempo de aprovisionamiento de los grupos de nodos GPU: adquirir nueva capacidad de GPU de un grupo de nodos lleva tiempo, y ese tiempo suele ser mayor y menos predecible que para nodos de CPU de propósito general. La [guía de Karpenter](../../autoscaling/02-karpenter.md) de este sitio de documentación cubre en profundidad la mecánica de aprovisionamiento de nodos; el punto que debe tenerse en cuenta al planificar Ray Train/Tune es que el tiempo de inicio real de un trabajo de entrenamiento en EKS depende de la rapidez con la que el clúster pueda programar conjuntamente todos los workers que solicitó, no solo de cuándo se envió el trabajo.

## Próximos pasos

La Parte 3 cubrió el Trainer, ScalingConfig y checkpointing de Ray Train, la búsqueda de hiperparámetros basada en ensayos de Ray Tune y cómo se combinan ambos cuando un ensayo de ajuste necesita a su vez entrenamiento distribuido. [Parte 4: Ray Serve](04-ray-serve.md) pasa del entrenamiento al servicio: tomar un modelo entrenado (y posiblemente ajustado) y exponerlo detrás de un endpoint de inferencia escalable.

[Volver a la página principal](./README.md)

## Cuestionario

Pon a prueba tus conocimientos con el [cuestionario de Ray Train y Ray Tune](../../quizzes/ai-ml/ray/03-ray-train-tune-quiz.md).
