# Cuestionario sobre Kubeflow Trainer y entrenamiento distribuido

Este cuestionario evalúa tu comprensión de los CRDs específicos de cada framework del antiguo Training Operator, el cambio al modelo unificado de `TrainJob`/runtime de Kubeflow Trainer v2 y la mecánica del entrenamiento distribuido en Kubernetes.

## Preguntas de opción múltiple

1. ¿Cuál era el enfoque arquitectónico fundamental del Training Operator original (v1), consolidado en 2021?
   - A) Un único CRD compartido por todos los frameworks, con detección del framework en tiempo de ejecución
   - B) Un CRD independiente (por ejemplo, `PyTorchJob`, `TFJob`, `MPIJob`) por cada framework de ML, cada uno con su propio controlador que implementa la semántica de entrenamiento distribuido de ese framework
   - C) Ningún CRD en absoluto: los trabajos se enviaban directamente mediante un contenedor con `kubectl run` con los argumentos de entrenamiento incorporados en la imagen
   - D) Un único CRD `TrainingJob` con un campo `framework` pero un solo controlador compartido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un CRD independiente (por ejemplo, `PyTorchJob`, `TFJob`, `MPIJob`) por cada framework de ML, cada uno con su propio controlador que implementa la semántica de entrenamiento distribuido de ese framework**

**Explicación:**
El Training Operator v1 proporcionaba un CRD por framework — `PyTorchJob`, `TFJob`, `MPIJob` y otros — cada uno respaldado por su propio controlador que conocía las convenciones de entrenamiento distribuido de ese framework en concreto (por ejemplo, el modelo de rank/variables de entorno de PyTorch frente a `TF_CONFIG` de TensorFlow).

</details>

2. ¿Qué variables de entorno inyectaba el controlador de `PyTorchJob` para permitir que los workers formaran un grupo de procesos de `torch.distributed`?
   - A) Solo `TF_CONFIG`
   - B) `MASTER_ADDR`, `RANK` y `WORLD_SIZE`
   - C) `KUBEFLOW_HOST` y `KUBEFLOW_PORT`
   - D) `POD_IP` y `POD_NAMESPACE`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `MASTER_ADDR`, `RANK` y `WORLD_SIZE`**

**Explicación:**
El controlador de `PyTorchJob` inyectaba `MASTER_ADDR`, `RANK` y `WORLD_SIZE` en cada Pod worker para que la maquinaria `torch.distributed` de PyTorch pudiera formar un grupo de procesos y coordinarse.

</details>

3. ¿Cuál es el cambio arquitectónico central que introduce Kubeflow Trainer v2 en comparación con el Training Operator v1?
   - A) Añade más CRDs específicos de cada framework sobre los existentes
   - B) Sustituye los CRDs por framework por una API unificada `TrainJob` más plantillas reutilizables `TrainingRuntime`/`ClusterTrainingRuntime`
   - C) Elimina por completo la necesidad de controladores, basándose únicamente en admission webhooks
   - D) Fusiona `TrainJob` y `ClusterTrainingRuntime` de nuevo en un único CRD por framework

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Sustituye los CRDs por framework por una API unificada `TrainJob` más plantillas reutilizables `TrainingRuntime`/`ClusterTrainingRuntime`**

**Explicación:**
En lugar de un CRD y un controlador por framework, Trainer v2 introduce `TrainJob` (qué ejecutar) y `TrainingRuntime`/`ClusterTrainingRuntime` (cómo ejecutarlo: una plantilla de ejecución reutilizable y específica del framework), desacoplando el envío del trabajo de la mecánica de lanzamiento distribuido.

</details>

4. En la separación entre `TrainJob` y `ClusterTrainingRuntime`, ¿qué objeto suele ser propiedad de un equipo de plataforma y se reutiliza en muchas ejecuciones de entrenamiento individuales?
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) Ambos se crean siempre de nuevo en cada ejecución
   - D) Ninguno: en su lugar se crea un `PyTorchJob`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `ClusterTrainingRuntime`**

**Explicación:**
`ClusterTrainingRuntime` (o el `TrainingRuntime` con ámbito de namespace) es la plantilla reutilizable que un equipo de plataforma define una sola vez, y que abarca la imagen del contenedor y la mecánica de lanzamiento distribuido. Los TrainJobs individuales referencian el kind/name y proporcionan los ajustes específicos de la ejecución permitidos. numNodes es el número de Pods de entrenamiento, no necesariamente el número de instancias EC2.

</details>

5. ¿A qué dos runtimes de entrenamiento adicionales añadió Kubeflow Trainer v2.2 soporte de primera clase?
   - A) TensorFlow y MXNet
   - B) JAX y XGBoost
   - C) Scikit-learn y ONNX
   - D) Spark MLlib y H2O

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) JAX y XGBoost**

**Explicación:**
Según las [notas de la versión](https://github.com/kubeflow/trainer/releases) de Kubeflow Trainer, la v2.2 (publicada el 20 de marzo de 2026) añadió runtimes de entrenamiento de primera clase para JAX y XGBoost junto al soporte existente de PyTorch, con política/integración de Flux. trainerStatus es una función alfa condicionada por TrainJobStatus, desactivada por defecto, que requiere que la aplicación informe explícitamente.

</details>

6. ¿Qué afirmación describe con mayor precisión el estado actual de la migración de v1 a Trainer v2 en la versión 26.03.1 de Kubeflow Community Distribution?
   - A) La migración está totalmente completa; el antiguo Training Operator se ha eliminado de todas las distribuciones
   - B) El antiguo Training Operator (1.9.2) sigue incluido junto a Trainer v2 en la distribución 26.03.1, y los trabajos antiguos y TrainJob requieren una migración validada por separado
   - C) Kubeflow Trainer v2 se declaró obsoleto en favor de volver a los CRDs de v1
   - D) `TrainJob` y `PyTorchJob` son simplemente dos nombres para el mismo CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El antiguo Training Operator (1.9.2) sigue incluido junto a Trainer v2 en la distribución 26.03.1, y los trabajos antiguos y TrainJob requieren una migración validada por separado**

**Explicación:**
La versión 26.03.1 de Kubeflow Community Distribution todavía distribuye el antiguo Training Operator 1.9.2 junto a Trainer v2, lo que muestra que se ofrecen ambas APIs, y no el progreso de migración de ningún equipo en particular.

</details>

7. ¿Por qué el gang scheduling opcional puede ayudar al entrenamiento distribuido sincrónico?
   - A) Kubernetes exige que todos los Pods de un namespace se planifiquen con gang scheduling por defecto
   - B) Puede reducir la asignación parcial de recursos cuando un trabajo no puede obtener todos los workers necesarios para la comunicación
   - C) El gang scheduling solo es necesario para cargas de trabajo web sin estado
   - D) Es un requisito de facturación impuesto por los proveedores de nube

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede reducir la asignación parcial de recursos cuando un trabajo no puede obtener todos los workers necesarios para la comunicación**

**Explicación:**
Los trabajos sincrónicos de tamaño fijo necesitan los procesos requeridos en el rendezvous. Trainer no habilita el gang scheduling automáticamente; el runtime de Torch por defecto no tiene podGroupPolicy. Configura el scheduler, los CRDs y la política por separado. El aprovisionamiento secuencial de nodos puede tener éxito dentro de los límites del timeout.

</details>

## Preguntas de respuesta corta

8. ¿Qué papel desempeña un Service headless en la coordinación de un trabajo de entrenamiento distribuido con múltiples workers en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Proporciona a cada Pod worker un nombre DNS estable y resoluble para que otros workers puedan descubrirlo, en lugar de depender de IPs de Pod que pueden cambiar al reprogramarse.

**Explicación:**
Los workers de entrenamiento distribuido necesitan encontrarse entre sí de forma fiable; un Service headless delante de los Pods worker permite el descubrimiento basado en DNS con una denominación de Pod, hostname/subdomain y red adecuados. No preserva el estado de los procesos ni las IPs.

</details>

9. En la referencia cruzada a Katib de este documento, ¿qué papel desempeña un `TrainJob` dentro de un Trial de Katib?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Con plantillas, runtime, condiciones de estado y recopilación de métricas compatibles, Katib puede crear un TrainJob para cada Trial, inyectando los valores de hiperparámetros elegidos para ese Trial como argumentos del script, y lee las métricas informadas para guiar la búsqueda.

**Explicación:**
Katib en sí no necesita conocer la mecánica del lanzamiento distribuido: genera un `TrainJob` por Trial contra un runtime que el equipo de plataforma ya ha definido, manteniendo la lógica de búsqueda de hiperparámetros desacoplada de la mecánica de ejecución del entrenamiento.

</details>

10. ¿Dónde deberías acudir para obtener la referencia autorizada, campo por campo, sobre la migración de manifiestos de CRDs v1 existentes (por ejemplo, `PyTorchJob`) a Kubeflow Trainer v2, en lugar de basarte en este documento?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** La guía "Migrating to Kubeflow Trainer v2" en kubeflow.org.

**Explicación:**
Este documento cubre el cambio conceptual y la mecánica a alto nivel, pero deliberadamente no reproduce cada paso de la migración; la [guía oficial fijada](https://github.com/kubeflow/trainer/blob/v2.3.0/docs/operator-guides/migration.md) proporciona un ejemplo de PyTorchJob, no una correspondencia exhaustiva para cada framework o campo. Compara los roles reales de lanzamiento, los reintentos, el almacenamiento y la red.

</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/05-training-operator.md)
