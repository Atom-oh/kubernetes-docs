# Cuestionario sobre Kubeflow Trainer y entrenamiento distribuido

Este cuestionario evalúa tu comprensión de los CRD específicos de cada framework del Training Operator heredado, el cambio al modelo unificado `TrainJob`/runtime de Kubeflow Trainer v2 y la mecánica del entrenamiento distribuido en Kubernetes.

## Preguntas de opción múltiple

1. ¿Cuál era el enfoque arquitectónico fundamental del Training Operator original (v1), consolidado en 2021?
   - A) Un único CRD compartido por todos los frameworks, con detección del framework en tiempo de ejecución
   - B) Un CRD independiente (por ejemplo, `PyTorchJob`, `TFJob`, `MPIJob`) para cada framework de ML, cada uno con su propio controller que implementa la semántica de entrenamiento distribuido de ese framework
   - C) Ningún CRD: los trabajos se enviaban directamente mediante un contenedor `kubectl run` con los argumentos de entrenamiento integrados en la imagen
   - D) Un único CRD `TrainingJob` con un campo `framework`, pero un controller compartido

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Un CRD independiente (por ejemplo, `PyTorchJob`, `TFJob`, `MPIJob`) para cada framework de ML, cada uno con su propio controller que implementa la semántica de entrenamiento distribuido de ese framework**

**Explicación:**
El Training Operator v1 proporcionaba un CRD por framework — `PyTorchJob`, `TFJob`, `MPIJob` y otros — cada uno respaldado por su propio controller que entendía las convenciones de entrenamiento distribuido de ese framework específico (por ejemplo, el modelo de rango/variables de entorno de PyTorch frente a `TF_CONFIG` de TensorFlow).

</details>

2. ¿Qué variables de entorno inyectaba el controller `PyTorchJob` para permitir que los workers formaran un grupo de procesos `torch.distributed`?
   - A) Solo `TF_CONFIG`
   - B) `MASTER_ADDR`, `RANK` y `WORLD_SIZE`
   - C) `KUBEFLOW_HOST` y `KUBEFLOW_PORT`
   - D) `POD_IP` y `POD_NAMESPACE`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `MASTER_ADDR`, `RANK` y `WORLD_SIZE`**

**Explicación:**
El controller `PyTorchJob` inyectaba `MASTER_ADDR`, `RANK` y `WORLD_SIZE` en cada Pod worker para que el mecanismo `torch.distributed` de PyTorch pudiera formar un grupo de procesos y coordinarse.

</details>

3. ¿Cuál es el cambio arquitectónico central introducido por Kubeflow Trainer v2 en comparación con el Training Operator v1?
   - A) Añade más CRD específicos de cada framework sobre los ya existentes
   - B) Reemplaza los CRD por framework con una API `TrainJob` unificada más plantillas reutilizables `TrainingRuntime`/`ClusterTrainingRuntime`
   - C) Elimina por completo la necesidad de controllers y depende únicamente de admission webhooks
   - D) Fusiona nuevamente `TrainJob` y `ClusterTrainingRuntime` en un único CRD por framework

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Reemplaza los CRD por framework con una API `TrainJob` unificada más plantillas reutilizables `TrainingRuntime`/`ClusterTrainingRuntime`**

**Explicación:**
En lugar de un CRD y un controller por framework, Trainer v2 introduce `TrainJob` (qué ejecutar) y `TrainingRuntime`/`ClusterTrainingRuntime` (cómo ejecutarlo: una plantilla de ejecución reutilizable y específica del framework), lo que desacopla el envío de trabajos de la mecánica de lanzamiento distribuido.

</details>

4. En la división entre `TrainJob` y `ClusterTrainingRuntime`, ¿qué objeto suele pertenecer a un equipo de plataforma y reutilizarse en muchas ejecuciones de entrenamiento individuales?
   - A) `TrainJob`
   - B) `ClusterTrainingRuntime`
   - C) Ambos siempre se crean de nuevo para cada ejecución
   - D) Ninguno: en su lugar se crea un `PyTorchJob`

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) `ClusterTrainingRuntime`**

**Explicación:**
`ClusterTrainingRuntime` (o el `TrainingRuntime` con ámbito de namespace) es la plantilla reutilizable que un equipo de plataforma define una vez, y cubre la imagen de contenedor y la mecánica de lanzamiento distribuido. Los `TrainJob` individuales hacen referencia a ella por nombre y proporcionan únicamente el script, los argumentos y el número de workers específicos de la ejecución.

</details>

5. ¿Qué dos runtimes de entrenamiento adicionales añadió Kubeflow Trainer v2.2 con soporte de primera clase?
   - A) TensorFlow y MXNet
   - B) JAX y XGBoost
   - C) Scikit-learn y ONNX
   - D) Spark MLlib y H2O

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) JAX y XGBoost**

**Explicación:**
Según las [notas de la versión](https://github.com/kubeflow/trainer/releases) de Kubeflow Trainer, v2.2 (lanzada aproximadamente en marzo de 2026) añadió runtimes de entrenamiento de JAX y XGBoost con soporte de primera clase junto al soporte existente de PyTorch, además de observabilidad mejorada e integración con Flux Framework para cargas de trabajo de estilo HPC.

</details>

6. ¿Qué afirmación describe con mayor precisión el estado actual de la migración de v1 a Trainer v2 a partir de la versión 26.03 de Kubeflow Community Distribution?
   - A) La migración está totalmente completada; el Training Operator heredado se eliminó de todas las distribuciones
   - B) El Training Operator heredado (1.9.2) sigue incluido junto con Trainer v2 en la distribución 26.03, y la migración de los trabajos existentes a `TrainJob` es una transición activa y en curso para muchos equipos
   - C) Kubeflow Trainer v2 quedó obsoleto en favor de volver a los CRD v1
   - D) `TrainJob` y `PyTorchJob` son simplemente dos nombres para el mismo CRD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) El Training Operator heredado (1.9.2) sigue incluido junto con Trainer v2 en la distribución 26.03, y la migración de los trabajos existentes a `TrainJob` es una transición activa y en curso para muchos equipos**

**Explicación:**
Kubeflow Community Distribution 26.03 aún incluye el Training Operator heredado 1.9.2 junto con Trainer v2, lo que refleja que ambos coexisten y que muchos equipos todavía están a mitad de la migración, en lugar de haber completado una transición total a `TrainJob`.

</details>

7. ¿Por qué los trabajos de entrenamiento distribuido suelen requerir gang scheduling?
   - A) Kubernetes requiere de forma predeterminada que todos los Pods de un namespace usen gang scheduling
   - B) Por lo general, todos los workers deben programarse y ejecutarse juntos antes de que pueda comenzar el entrenamiento; la programación parcial desperdicia capacidad de GPU y puede causar un bloqueo mutuo
   - C) Gang scheduling solo se requiere para cargas de trabajo web sin estado
   - D) Es un requisito de facturación impuesto por los proveedores de nube

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Por lo general, todos los workers deben programarse y ejecutarse juntos antes de que pueda comenzar el entrenamiento; la programación parcial desperdicia capacidad de GPU y puede causar un bloqueo mutuo**

**Explicación:**
Un trabajo de entrenamiento distribuido que solo consigue programar algunos de los workers requeridos puede esperar indefinidamente al resto, desperdiciando la capacidad de GPU reservada y pudiendo causar un bloqueo mutuo. Las primitivas de gang scheduling agrupan los Pods de un trabajo como una unidad de programación de todo o nada para evitarlo.

</details>

## Preguntas de respuesta corta

8. ¿Qué función desempeña un Service headless al coordinar un trabajo de entrenamiento distribuido con múltiples workers en Kubernetes?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Proporciona a cada Pod worker un nombre DNS estable y resoluble para que los demás workers puedan descubrirlo, en lugar de depender de direcciones IP de Pod que pueden cambiar al reprogramarse.

**Explicación:**
Los workers de entrenamiento distribuido necesitan encontrarse entre sí de forma fiable; un Service headless delante de los Pods worker proporciona descubrimiento estable basado en DNS que sobrevive a la reprogramación de Pods individuales.

</details>

9. En la referencia cruzada de Katib de este documento, ¿qué función desempeña un `TrainJob` dentro de un Trial de Katib?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** Katib normalmente usa como plantilla un `TrainJob` como trabajo de entrenamiento subyacente para cada Trial, inyecta los valores de hiperparámetros elegidos para ese Trial como argumentos del script y recupera las métricas reportadas para orientar la búsqueda.

**Explicación:**
Katib no necesita conocer la mecánica de lanzamiento distribuido: crea un `TrainJob` por Trial a partir de un runtime que el equipo de plataforma ya definió, lo que mantiene la lógica de búsqueda de hiperparámetros desacoplada de la mecánica de ejecución del entrenamiento.

</details>

10. ¿A dónde debes acudir para consultar la referencia autorizada, campo por campo, sobre la migración de manifiestos CRD v1 existentes (por ejemplo, `PyTorchJob`) a Kubeflow Trainer v2, en lugar de depender de este documento?

<details>
<summary>Mostrar respuesta</summary>

**Respuesta:** La guía "Migrating to Kubeflow Trainer v2" en kubeflow.org.

**Explicación:**
Este documento cubre el cambio conceptual y la mecánica a alto nivel, pero deliberadamente no repite cada paso de la migración; la guía de migración oficial de kubeflow.org es la fuente autorizada para la correspondencia concreta campo por campo.

</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/05-training-operator.md)
