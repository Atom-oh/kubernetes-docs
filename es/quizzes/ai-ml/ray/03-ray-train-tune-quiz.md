# Cuestionario de Ray Train y Ray Tune

Este cuestionario evalúa tu comprensión de Ray Train (Trainer, ScalingConfig, checkpointing), Ray Tune y cómo ambos se combinan para el ajuste distribuido de hiperparámetros.

## Preguntas de opción múltiple

1. ¿Qué problema resuelve principalmente Ray Train para un script de entrenamiento distribuido?
   - A) Reemplaza PyTorch y otros frameworks de entrenamiento con una nueva API de entrenamiento
   - B) Gestiona el código repetitivo de iniciar procesos de worker, configurar su grupo de comunicación y coordinar checkpoints
   - C) Etiqueta automáticamente los datos de entrenamiento antes de que comience una ejecución
   - D) Elimina la necesidad de GPUs al ejecutar el entrenamiento completamente en CPU

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Gestiona el código repetitivo de iniciar procesos de worker, configurar su grupo de comunicación y coordinar checkpoints**

**Explicación:**
Ray Train se basa en las primitivas de tareas y actores de Ray y se encarga del código repetitivo del entrenamiento distribuido: inicia un worker por cada recurso asignado, configura el grupo de comunicación entre workers (por ejemplo, un grupo de procesos PyTorch DDP) y coordina el checkpointing, de modo que un script de entrenamiento escrito con una API de framework familiar pueda escalar sin que su autor tenga que implementar esa coordinación manualmente.
</details>

2. ¿Cuál de las siguientes opciones describe mejor Ray Train V2?
   - A) Un producto completamente independiente sin relación con versiones anteriores de Ray Train
   - B) Una implementación reescrita detrás de la ruta de importación existente `ray.train.torch.TorchTrainer`, que consolida y simplifica el funcionamiento interno de una generación anterior de clases de Trainer
   - C) Una versión de Ray Train que solo admite entrenamiento basado en CPU
   - D) Una API obsoleta que Ray ya no documenta

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una implementación reescrita detrás de la ruta de importación existente `ray.train.torch.TorchTrainer`, que consolida y simplifica el funcionamiento interno de una generación anterior de clases de Trainer**

**Explicación:**
La superficie de la API de Ray Train ha evolucionado con el tiempo, pero la ruta de importación orientada al usuario (`ray.train.torch.TorchTrainer` para PyTorch) no ha cambiado; lo que cambió fue la implementación detrás de ella. El historial exacto de versiones sobre cuándo esta reescritura se convirtió en la predeterminada se consulta mejor en la documentación actual de Ray en lugar de asumirlo.
</details>

3. ¿Cuál es la función de un `ScalingConfig` en Ray Train?
   - A) Especifica cuántos workers iniciar y qué recursos (como GPUs) necesita cada uno
   - B) Define la arquitectura de red neuronal utilizada durante el entrenamiento
   - C) Establece la programación de la tasa de aprendizaje para el optimizador
   - D) Configura la región de cloud en la que se ejecuta el clúster de Ray

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Especifica cuántos workers iniciar y qué recursos (como GPUs) necesita cada uno**

**Explicación:**
Un `ScalingConfig` indica al Trainer cuántos workers iniciar y si cada uno necesita una GPU. El Trainer usa esto para solicitar los recursos correspondientes al clúster de Ray subyacente, de la misma forma que lo haría cualquier otra tarea o actor de Ray.
</details>

4. Además de permitir la recuperación después de un fallo de worker, ¿qué otro propósito tiene el checkpointing de Ray Train?
   - A) Comprime el conjunto de datos de entrenamiento para ahorrar almacenamiento
   - B) Transfiere un modelo entrenado a un paso posterior del flujo de trabajo, como una decisión de ajuste de hiperparámetros o el registro del modelo
   - C) Implementa automáticamente el modelo en un endpoint de serving de producción
   - D) Reemplaza la necesidad de un ScalingConfig

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Transfiere un modelo entrenado a un paso posterior del flujo de trabajo, como una decisión de ajuste de hiperparámetros o el registro del modelo**

**Explicación:**
Un checkpoint reportado captura suficiente estado (normalmente pesos del modelo y estado del optimizador) para reanudar el entrenamiento, pero también sirve como punto de transferencia para lo que siga; por ejemplo, una decisión de ajuste o registrar el resultado como una versión de modelo, conceptualmente similar al patrón de registro de modelos tratado en otras secciones de este sitio de documentación.
</details>

5. ¿Qué hace Ray Tune?
   - A) Ejecuta muchas pruebas de entrenamiento en paralelo en todo el clúster y utiliza un algoritmo de búsqueda conectable para decidir qué combinaciones de hiperparámetros probar después
   - B) Solo ajusta un hiperparámetro a la vez, de forma secuencial
   - C) Reemplaza por completo Ray Train para cualquier carga de trabajo de entrenamiento distribuido
   - D) Es un controlador basado en Kubernetes CRD sin relación con las primitivas principales de Ray

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Ejecuta muchas pruebas de entrenamiento en paralelo en todo el clúster y utiliza un algoritmo de búsqueda conectable para decidir qué combinaciones de hiperparámetros probar después**

**Explicación:**
Ray Tune es una biblioteca de ajuste de hiperparámetros basada en Ray. Cada prueba entrena con una combinación de hiperparámetros y reporta un resultado, que el algoritmo de búsqueda de Tune utiliza para decidir qué probar después. Esto es conceptualmente paralelo a lo que ofrece Katib en el ecosistema de Kubeflow, pero es nativo de Ray en lugar de ser un sistema independiente basado en Kubernetes CRD.
</details>

6. ¿Cómo se combina habitualmente Ray Tune con Ray Train para un modelo que necesita entrenamiento distribuido?
   - A) Tune y Train no se pueden usar juntos; un equipo debe elegir uno u otro
   - B) Tune envuelve un `Trainer` de Ray Train como el elemento entrenable sobre el que busca, de modo que cada prueba se convierte en su propia ejecución distribuida de Ray Train
   - C) Ray Train se ejecuta primero hasta completarse y solo entonces comienza Ray Tune, en un clúster independiente
   - D) Tune reemplaza el ScalingConfig del Trainer con su propio modelo de recursos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Tune envuelve un `Trainer` de Ray Train como el elemento entrenable sobre el que busca, de modo que cada prueba se convierte en su propia ejecución distribuida de Ray Train**

**Explicación:**
Un patrón común proporciona a Tune un `Trainer` de Ray Train como elemento entrenable. Cada prueba de hiperparámetros se convierte entonces en una ejecución distribuida de Ray Train, que potencialmente abarca múltiples GPUs o nodos; esto resulta útil cuando una sola prueba necesita entrenamiento distribuido para finalizar en un tiempo razonable.
</details>

7. ¿Por qué el autoscaler administrado por KubeRay en EKS reacciona a la demanda real de recursos de un trabajo de Ray Train o Ray Tune?
   - A) Porque Ray Train y Ray Tune solicitan CPUs y GPUs mediante el mecanismo normal de solicitud de recursos de tareas/actores de Ray, igual que cualquier otra carga de trabajo de Ray
   - B) Porque Ray Train y Ray Tune se comunican directamente con el servidor de la API de Kubernetes, omitiendo el scheduler de Ray
   - C) Porque el clúster siempre debe aprovisionarse con un tamaño fijo antes de ejecutar cualquier trabajo
   - D) Porque Karpenter supervisa la utilización de GPU dentro del propio proceso de entrenamiento

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Porque Ray Train y Ray Tune solicitan CPUs y GPUs mediante el mecanismo normal de solicitud de recursos de tareas/actores de Ray, igual que cualquier otra carga de trabajo de Ray**

**Explicación:**
Ambas bibliotecas solicitan recursos mediante el mecanismo habitual de solicitud de recursos de tareas/actores de Ray, sin una ruta separada específica para entrenamiento o ajuste. Esto permite al autoscaler tratado en la Parte 2 reaccionar a la demanda real: solicita más nodos de worker a medida que un barrido de Tune inicia más pruebas simultáneas y vuelve a reducir la escala cuando las pruebas finalizan, en lugar de requerir un clúster de tamaño fijo desde el principio.
</details>

8. ¿Qué problema práctico puede surgir de las necesidades de co-programación de los workers distribuidos de una ejecución de Ray Train en EKS?
   - A) Ninguno: los workers de Ray Train nunca necesitan iniciarse al mismo tiempo
   - B) Una ejecución de entrenamiento puede quedar detenida esperando que se activen los últimos workers de GPU si el autoscaler no puede aprovisionar todos los workers solicitados dentro de un plazo razonable
   - C) La co-programación solo importa para Ray Tune, nunca para Ray Train
   - D) El checkpointing resuelve automáticamente cualquier demora de co-programación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una ejecución de entrenamiento puede quedar detenida esperando que se activen los últimos workers de GPU si el autoscaler no puede aprovisionar todos los workers solicitados dentro de un plazo razonable**

**Explicación:**
Los workers de una ejecución de Ray Train normalmente deben programarse conjuntamente: todos deben estar activos y mantener sus GPUs asignadas antes de que pueda establecerse su grupo de comunicación, de forma similar a las necesidades de gang scheduling analizadas en otras secciones de este sitio de documentación. El tiempo de espera para el aprovisionamiento de un node pool de GPU suele ser más largo y menos predecible que para los nodos de CPU, por lo que el tiempo real de inicio de un trabajo de entrenamiento depende de la rapidez con que pueda programarse conjuntamente cada worker solicitado.
</details>

## Preguntas de respuesta corta

9. Explica qué hacen un `Trainer` y un `ScalingConfig` de Ray Train, y cómo trabajan juntos para ejecutar un trabajo de entrenamiento distribuido.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Un Trainer (como `TorchTrainer`) envuelve una función de entrenamiento proporcionada por el usuario que contiene la lógica habitual de entrenamiento del modelo: construir el modelo, iterar sobre lotes, calcular la pérdida y ejecutar un paso del optimizador. El Trainer se encarga de iniciar esa función una vez por worker, dentro del grupo de procesos distribuidos que espera el entrenamiento paralelo de datos del framework subyacente (por ejemplo, un grupo de procesos PyTorch DDP), de modo que la propia función de entrenamiento no necesita configurar manualmente esa coordinación.

Un `ScalingConfig` indica al Trainer cuántos workers iniciar y qué recursos necesita cada uno, como si se requiere una GPU. El Trainer utiliza el `ScalingConfig` para solicitar los recursos correspondientes al clúster de Ray subyacente mediante el mecanismo normal de solicitud de recursos de tareas/actores de Ray. En conjunto, el Trainer proporciona la lógica y la coordinación del entrenamiento, y el `ScalingConfig` proporciona la configuración de recursos sobre la que el Trainer escala esa lógica.
</details>

10. Describe por qué es útil combinar Ray Tune con Ray Train y cómo interactúan las solicitudes de recursos de esa combinación con el escalado automático del clúster en EKS.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Algunos modelos son lo suficientemente costosos de entrenar como para que una sola prueba de hiperparámetros necesite entrenamiento distribuido (multi-GPU o multinodo) a fin de finalizar en un tiempo razonable. Sin combinar las dos bibliotecas, un equipo tendría que ajustar hiperparámetros en serie con respecto a un trabajo de entrenamiento distribuido o renunciar al entrenamiento distribuido durante la fase de búsqueda. Como Ray Tune puede envolver un `Trainer` de Ray Train como elemento entrenable, cada prueba se convierte en su propia ejecución distribuida de Ray Train, y Tune puede ejecutar varias de estas ejecuciones simultáneamente mientras decide qué combinaciones de hiperparámetros probar después.

Dado que cada worker de cada prueba sigue solicitando CPUs y GPUs mediante el mecanismo normal de solicitud de recursos de tareas/actores de Ray, el autoscaler administrado por KubeRay en EKS ve la demanda de recursos combinada y en tiempo real de todas las pruebas activas, en lugar de una única configuración predeclarada. Puede aprovisionar más nodos de worker a medida que un barrido de Tune inicia más pruebas simultáneas y volver a reducir la escala cuando las pruebas finalizan, en vez de requerir que el clúster tenga desde el principio el tamaño necesario para el mayor barrido posible.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/ray/03-ray-train-tune.md) | [Siguiente cuestionario: Ray Serve](./04-ray-serve-quiz.md)
