# Cuestionario de MLflow Tracking

Este cuestionario evalúa tu comprensión de los conceptos fundamentales de MLflow Tracking, el cambio en MLflow 3 hacia los modelos registrados como entidades de primera clase, autologging, tracing de GenAI y la división entre backend store y artifact store.

## Preguntas de opción múltiple

1. ¿Qué es un MLflow Experiment?
   - A) Una única ejecución de código de entrenamiento, con sus propios params y metrics
   - B) Una colección de Runs con nombre
   - C) La base de datos que almacena los metadatos de MLflow
   - D) Un archivo de modelo serializado

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una colección de Runs con nombre**

**Explicación:**
Un Experiment es una agrupación con nombre de Runs, normalmente uno por proyecto o por cada modelo en proceso de iteración. Un Run es la ejecución única de código de entrenamiento con sus propios params, metrics, tags y artifacts; ese es un concepto diferente (opción A).
</details>

2. En el modelo centrado en Runs de MLflow 1.x/2.x, ¿cómo se representaba normalmente un modelo registrado?
   - A) Como una entidad `LoggedModel` independiente de cualquier run
   - B) Como un artifact anidado bajo el Run que lo produjo
   - C) Como una fila en la tabla de metrics del backend store
   - D) Como un experiment independiente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Como un artifact anidado bajo el Run que lo produjo**

**Explicación:**
Antes de MLflow 3, un modelo registrado era simplemente otro artifact almacenado dentro del directorio de artifacts del run. Para encontrar un modelo, primero había que encontrar el run que lo produjo. MLflow 3 cambió esto al introducir `LoggedModel` como su propia entidad de primera clase.
</details>

3. ¿Qué capacidad clave habilita la entidad `LoggedModel` de MLflow 3 que el modelo anterior anidado en runs no habilitaba?
   - A) Llamar directamente a `mlflow.sklearn.log_model(...)`, sin un contexto activo de `mlflow.start_run()`
   - B) Registrar metrics sin un tracking server
   - C) Ejecutar código de entrenamiento sin Python
   - D) Almacenar artifacts sin un artifact store

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: A) Llamar directamente a `mlflow.sklearn.log_model(...)`, sin un contexto activo de `mlflow.start_run()`**

**Explicación:**
Dado que `LoggedModel` ahora es una entidad de primera clase separada de los Runs, ya no necesita estar anidada bajo un run activo para realizar el tracking. Esto desacopla el versionado y la comparación de modelos de cualquier run de entrenamiento individual.
</details>

4. ¿Qué hace `mlflow.autolog()`?
   - A) Despliega automáticamente un modelo entrenado en un endpoint de serving
   - B) Instrumenta las bibliotecas de ML compatibles para que params, metrics y artifacts se registren automáticamente durante el entrenamiento, sin llamadas manuales de logging
   - C) Elimina automáticamente runs antiguos para ahorrar almacenamiento
   - D) Convierte un Run en un LoggedModel

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Instrumenta las bibliotecas de ML compatibles para que params, metrics y artifacts se registren automáticamente durante el entrenamiento, sin llamadas manuales de logging**

**Explicación:**
Autologging captura automáticamente los datos comunes de entrenamiento para los frameworks compatibles. MLflow también proporciona funciones de autolog específicas por framework (por ejemplo, para scikit-learn o PyTorch) para habilitar autologging solo en una biblioteca, en lugar de en cada framework detectado.
</details>

5. En MLflow 3, ¿para qué se usa principalmente el "tracing"?
   - A) Registrar parámetros y metrics para runs de entrenamiento clásicos de scikit-learn
   - B) Capturar los pasos internos (spans), el uso de tokens y el costo de las llamadas de LLM/agent para la observabilidad de GenAI
   - C) Hacer tracking del uso de disco del artifact store
   - D) Reemplazar por completo la vista de Experiments/Runs

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Capturar los pasos internos (spans), el uso de tokens y el costo de las llamadas de LLM/agent para la observabilidad de GenAI**

**Explicación:**
Tracing captura una llamada de LLM o agent como un árbol de spans, cada uno de los cuales representa un paso, como una llamada de recuperación o invocación de una herramienta, junto con el uso de tokens y el costo. Extiende MLflow Tracking para cubrir la observabilidad de GenAI/agent como una funcionalidad central, en lugar de requerir una herramienta separada.
</details>

6. ¿Cuál de los siguientes es un ejemplo de un framework para el que MLflow proporciona integración de auto-tracing, junto con LangChain?
   - A) Kubernetes
   - B) PostgreSQL
   - C) PydanticAI
   - D) Terraform

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) PydanticAI**

**Explicación:**
MLflow proporciona auto-instrumentación para frameworks populares de LLM/agent, incluido LangChain, con integraciones más recientes de auto-tracing para frameworks como PydanticAI y smolagents.
</details>

7. ¿Por qué el backend store normalmente necesita una base de datos relacional real (como PostgreSQL o MySQL) a escala de equipo?
   - A) Porque almacena grandes archivos de modelo binarios que las bases de datos manejan mejor que el object storage
   - B) Porque contiene metadatos estructurados — params, metrics, tags y registros de run/experiment/model — que se benefician de una base de datos más allá de la experimentación local rápida
   - C) Porque MLflow requiere una base de datos SQL para renderizar su UI
   - D) Porque el object storage no puede almacenar ningún metadato en absoluto

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Porque contiene metadatos estructurados — params, metrics, tags y registros de run/experiment/model — que se benefician de una base de datos más allá de la experimentación local rápida**

**Explicación:**
El backend store contiene metadatos estructurados adecuados para las numerosas escrituras y consultas estructuradas pequeñas de una base de datos relacional. En cambio, el artifact store contiene objetos binarios grandes y normalmente es un object storage, como un bucket compatible con S3.
</details>

8. En el flujo de tracking (training script -> Tracking API -> tracking server -> backend store + artifact store), ¿qué hace la Tracking UI?
   - A) Escribe directamente en el disco local del training script
   - B) Lee tanto del backend store como del artifact store para renderizar experiments, runs, modelos registrados y traces
   - C) Omite el tracking server y consulta solamente el backend store
   - D) Solo muestra artifacts, nunca metadatos

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Lee tanto del backend store como del artifact store para renderizar experiments, runs, modelos registrados y traces**

**Explicación:**
El training script solo se comunica con la Tracking API; el tracking server dirige las escrituras de metadatos al backend store y las escrituras de archivos al artifact store. La UI lee de ambos stores para mostrar todo lo que necesita.
</details>

## Preguntas de respuesta corta

9. ¿Cuál es el beneficio práctico de que MLflow 3 haga tracking del lineage entre un `LoggedModel` y los runs, traces, prompts y evaluation metrics asociados con él?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Un modelo ya no queda permanentemente vinculado al único run que lo entrenó; puede vincularse al run que lo entrenó, a los runs que lo evaluaron y a cualquier trace generado al servirlo.**

**Explicación:**
Dado que `LoggedModel` es una entidad de primera clase en lugar de un archivo anidado bajo un run, MLflow 3 puede representar relaciones más enriquecidas entre un modelo y todo lo relacionado con él. Esto es más importante cuando se itera un modelo a lo largo de muchos runs o se produce fuera de un bucle de entrenamiento tradicional, por ejemplo, al encapsular un LLM existente con lógica personalizada.
</details>

10. ¿Por qué MLflow presenta el tracking de experimentos de ML clásico y la observabilidad de GenAI/agent como un solo sistema en lugar de dos herramientas independientes?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Porque MLflow 3 extendió el mismo sistema de Tracking (y su UI) para cubrir ambos: el tracing para llamadas de GenAI/agent usa el mismo tracking server, UI y modelo de lineage que los params/metrics/artifacts de los runs de entrenamiento clásicos.**

**Explicación:**
Un equipo que realiza tanto entrenamiento de ML clásico como desarrollo de LLM/agent puede usar un único despliegue de MLflow Tracking para ambos, en lugar de implementar una herramienta de observabilidad independiente solo para la parte de GenAI.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/01-tracking.md) | [Siguiente cuestionario: Model Registry](./02-model-registry-quiz.md)
