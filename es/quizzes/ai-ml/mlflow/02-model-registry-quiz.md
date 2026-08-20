# Cuestionario sobre MLflow Model Registry

Este cuestionario evalúa tu comprensión de MLflow Model Registry: Registered Models, Model Versions, alias y cómo el registro se conecta con Tracking.

## Preguntas de opción múltiple

1. ¿Qué es un Registered Model en MLflow?
   - A) Una instantánea de las métricas de un Run de entrenamiento
   - B) Una colección con nombre y versionada de versiones de modelo que proporciona a un modelo una identidad estable, independiente de cualquier ejecución individual
   - C) Una imagen de contenedor creada a partir de un artefacto de modelo
   - D) Una copia guardada de la base de datos del servidor de tracking

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una colección con nombre y versionada de versiones de modelo que proporciona a un modelo una identidad estable, independiente de cualquier ejecución individual**

**Explicación:**
Un Registered Model se identifica mediante un nombre (por ejemplo, `fraud-detector`) y acumula Model Versions, alias, etiquetas y descripciones durante su ciclo de vida. Existe precisamente para que «el modelo» tenga una identidad que perdure más allá de cualquier Run de entrenamiento o Experiment.
</details>

2. ¿Qué sucede con una Model Version una vez creada?
   - A) Puede editarse directamente a medida que el modelo mejora
   - B) Es inmutable: un nuevo resultado de entrenamiento se convierte en una nueva versión, no en una modificación de una versión anterior
   - C) Se elimina automáticamente después de 30 días
   - D) Se fusiona con la siguiente versión registrada bajo el mismo nombre

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Es inmutable: un nuevo resultado de entrenamiento se convierte en una nueva versión, no en una modificación de una versión anterior**

**Explicación:**
Cada Model Version está numerada (versión 1, versión 2, etc.) y, una vez registrada, no cambia. Un nuevo modelo candidato siempre se convierte en una nueva versión bajo el mismo nombre de Registered Model.
</details>

3. ¿Qué conserva una Model Version que la conecta de nuevo con Tracking (Parte 1)?
   - A) Una copia del conjunto de datos de entrenamiento almacenada dentro del registro
   - B) Una referencia al `LoggedModel` o Run subyacente del que proviene
   - C) Una instantánea de la configuración de nodos del clúster
   - D) Nada: las Model Versions son completamente independientes de Tracking

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una referencia al `LoggedModel` o Run subyacente del que proviene**

**Explicación:**
Cada Model Version apunta al Run (y a la entidad `LoggedModel` explicada en la Parte 1) que la produjo, lo que hace posible la trazabilidad y la reproducibilidad.
</details>

4. ¿Qué es un alias en MLflow Model Registry?
   - A) Una etiqueta permanente e inalterable asignada al crear el modelo
   - B) Un puntero mutable con nombre a una Model Version específica, como `champion` o `challenger`
   - C) Una abreviatura de la URL del servidor de tracking
   - D) Un sinónimo del nombre de un Registered Model

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un puntero mutable con nombre a una Model Version específica, como `champion` o `challenger`**

**Explicación:**
A diferencia de un número de versión, un alias puede trasladarse para apuntar a una Model Version diferente con el tiempo; por ejemplo, se puede redirigir `champion` de la versión 4 a la versión 7 después de que una nueva versión supere la evaluación.
</details>

5. ¿Por qué los alias han reemplazado al modelo de ciclo de vida anterior basado en etapas (Staging/Production/Archived) en las versiones actuales de MLflow?
   - A) Las etapas ya no son compatibles con ninguna versión de MLflow
   - B) Los alias son más flexibles: una versión puede tener varios alias o ninguno, y los nombres de alias no están restringidos a un conjunto fijo de etiquetas de ciclo de vida
   - C) Los alias requieren menos espacio en disco que las etapas
   - D) Las etapas no podían consultarse mediante la API

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Los alias son más flexibles: una versión puede tener varios alias o ninguno, y los nombres de alias no están restringidos a un conjunto fijo de etiquetas de ciclo de vida**

**Explicación:**
El modelo de etapas vinculaba cada versión a una de un conjunto fijo de etiquetas (`Staging`, `Production`, `Archived`). Los alias combinados con etiquetas permiten nombres personalizados más flexibles y permiten que una versión tenga más de un alias a la vez. Quienes lean documentación pueden seguir encontrando el modelo de etapas en implementaciones antiguas de MLflow, pero es un enfoque heredado.
</details>

6. ¿Cuál de las siguientes opciones crea una nueva Model Version al mismo tiempo que se registra un modelo?
   - A) Llamar a `mlflow.register_model(model_uri, name)` después del registro
   - B) Pasar `registered_model_name` a una llamada a `log_model` específica de un flavor
   - C) Copiar manualmente los archivos del modelo en el almacenamiento de artefactos del servidor de tracking
   - D) Establecer una etiqueta en una Model Version existente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Pasar `registered_model_name` a una llamada a `log_model` específica de un flavor**

**Explicación:**
Pasar `registered_model_name` a una llamada como `mlflow.sklearn.log_model(..., registered_model_name="fraud-detector")` registra una nueva Model Version en la misma llamada que registra el modelo. `mlflow.register_model(model_uri, name)` es la vía alternativa, usada para registrar un modelo que ya se registró en un paso anterior.
</details>

7. En el flujo de trabajo de gobernanza habitual, ¿qué traslada el alias `champion` a una nueva versión?
   - A) El script de entrenamiento, automáticamente, en cuanto finaliza una ejecución
   - B) Un proceso de evaluación o aprobación —a menudo parte de una canalización de CI/CD— solo después de que la versión candidata supera sus controles
   - C) El sistema de serving, la primera vez que resuelve `models:/fraud-detector@champion`
   - D) MLflow automáticamente, porque el número de versión es mayor

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un proceso de evaluación o aprobación —a menudo parte de una canalización de CI/CD— solo después de que la versión candidata supera sus controles**

**Explicación:**
El valor de gobernanza del registro proviene de separar «producir un candidato» de «promover un candidato». Mover el alias `champion` es una acción deliberada, normalmente automatizada en una canalización de aprobación y condicionada a superar los criterios de evaluación.
</details>

8. ¿Qué obtiene un sistema de serving al resolver `models:/fraud-detector@champion` en lugar de `models:/fraud-detector/7`?
   - A) Menor latencia de inferencia
   - B) Una referencia estable que selecciona automáticamente la versión que actualmente tiene el alias `champion`, sin cambiar el código
   - C) Acceso a un servidor de tracking diferente
   - D) Reentrenamiento automático del modelo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una referencia estable que selecciona automáticamente la versión que actualmente tiene el alias `champion`, sin cambiar el código**

**Explicación:**
Una URI basada en alias desacopla al consumidor de un modelo de cualquier número de versión específico. Cuando `champion` se redirige a una versión recién validada, la siguiente resolución de esa URI simplemente selecciona la nueva versión.
</details>

## Preguntas de respuesta corta

9. Explica la diferencia entre una Model Version y un alias, y por qué esa diferencia es importante para un sistema de serving.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Una Model Version es inmutable y está numerada: una vez creada, nunca cambia, y un nuevo resultado de entrenamiento siempre se convierte en una nueva versión en lugar de modificar una existente. Un alias es mutable: es un puntero con nombre (como `champion` o `challenger`) que puede redirigirse a una Model Version diferente en cualquier momento.

Esto es importante para un sistema de serving porque se puede escribir una vez para resolver un nombre estable como `models:/fraud-detector@champion` en lugar de un número de versión codificado de forma fija. Cuando el alias se mueve a una versión recién aprobada, el sistema de serving adopta automáticamente el cambio en su siguiente resolución, sin requerir ninguna actualización de código o configuración.
</details>

10. Describe cómo la trazabilidad de una Model Version permite responder una pregunta de auditoría como «qué código y datos exactos produjeron el modelo que actualmente está en producción».

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Cada Model Version conserva una referencia al Run (y al `LoggedModel` subyacente, como se explicó en la Parte 1) que la produjo. Seguir esa cadena —desde el alias `champion` hasta la Model Version a la que apunta, y desde esa versión de vuelta a su Run de origen— conduce a los parámetros, referencias de código e información del conjunto de datos que ese Run registró durante Tracking.

Como una Model Version es inmutable y este vínculo de trazabilidad nunca se elimina, un auditor siempre puede rastrear el modelo que actualmente tiene el alias `champion` hasta la ejecución de entrenamiento exacta que lo creó, en lugar de depender de registros separados o de la memoria del equipo.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/02-model-registry.md) | [Siguiente cuestionario: EKS Deployment](./03-eks-deployment-quiz.md)
