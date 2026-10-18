# Cuestionario sobre los resultados de validación factual de SageMaker Qwen

## Preguntas de opción múltiple

1. ¿Qué encontró la nueva verificación del 2 de septiembre?
   - A) No quedaban recursos
   - B) Un proyecto de Unified Studio seguía en estado `ACTIVE`
   - C) Había un clúster de GPU de EKS en ejecución
   - D) Se había completado un Training Job

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El registro histórico indicó que se recuperaron los recursos de App, S3 e IAM, pero que quedaba un proyecto. La revisión de la documentación del 12 de septiembre no volvió a consultar el estado actual de AWS.
</details>

2. ¿Cuál fue el fallo principal del intento 3?
   - A) Un ID de modelo mal escrito
   - B) Faltaba la pertenencia al proyecto
   - C) No coincidía el hash del conjunto de datos
   - D) CUDA se quedó sin memoria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El perfil del grupo de roles del invocador no estaba asignado como propietario ni como miembro.
</details>

3. ¿Qué resultados no se publicaron?
   - A) El recuento de registros
   - B) La versión de MLflow App
   - C) El F1 del modelo ajustado y el costo de GPU
   - D) El recuento de pruebas de Python

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

No se ejecutó el entrenamiento en GPU, por lo que esos valores comparativos no se midieron. Esto no implica que recursos como MLflow App y S3 tuvieran un costo total de cero.
</details>

4. ¿Cuál es el primer requisito para volver a ejecutar el proceso?
   - A) Enviar el Job completo
   - B) Conciliar el inventario y resolver los recursos del experimento que sigan existiendo o cuyo estado sea desconocido
   - C) Crear un clúster de EKS
   - D) Publicar métricas ajustadas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los errores de permisos o la ausencia de un recurso en una lista no demuestran que se haya eliminado. Un prefijo de nombre compartido no autoriza a eliminar los recursos de otra persona.
</details>

5. ¿En qué se diferencian la arquitectura objetivo y el flujo de trabajo real?
   - A) Ambos demuestran que el proceso se completó
   - B) Uno es un diseño para volver a ejecutar el proceso; el otro registra dónde se detuvo realmente
   - C) Ambos son informes de costos
   - D) El flujo real muestra un entrenamiento de GPU completado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El flujo de trabajo histórico se detiene antes del entrenamiento en GPU. No demuestra el estado actual de la cuenta ni que el costo total del experimento haya sido cero.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/sagemaker-ai/04-validation-results.md)
