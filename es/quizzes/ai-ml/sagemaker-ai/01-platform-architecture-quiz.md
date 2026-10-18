# Cuestionario sobre la arquitectura de la plataforma SageMaker Qwen

## Preguntas de opción múltiple

1. ¿Qué relación existe entre la salida del modelo y el procesamiento en Python en este diseño?

   - A) El modelo elimina con certeza todos los datos personales
   - B) El modelo genera un TSV candidato y el código lo valida y reemplaza; la detección de elementos omitidos se evalúa por separado
   - C) Un ciclo de ida y vuelta demuestra el anonimato
   - D) El modelo elimina proyectos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El reemplazo determinista no recupera automáticamente las entidades que el modelo no detectó.

</details>

2. ¿Cómo deben interpretarse el diagrama y el registro de validación?

   - A) Se validaron ambas rutas de GPU
   - B) Es un diseño objetivo; distinga las pruebas locales de las observaciones históricas de AWS
   - C) Muestra el recuento actual de proyectos residuales
   - D) Informa el F1 y los costos del entrenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El registro del 1 de septiembre de 2026 se detuvo antes del entrenamiento. Las pruebas locales no demuestran el estado actual de AWS ni los resultados de GPU.

</details>

3. ¿Los mismos ID de modelo y semillas reproducen por completo los resultados en distintos entornos?

   - A) Siempre
   - B) No; también hay que verificar revisiones, hashes de datos, imágenes/dependencias, CUDA/hardware y condiciones de ejecución
   - C) Solo EKS necesita una semilla
   - D) El tokenizer no importa para QLoRA

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Fijar directamente las versiones de los paquetes no equivale a bloquear todas las dependencias transitivas, y el determinismo en GPU tiene requisitos adicionales.

</details>

4. ¿Qué se debe excluir de los registros habituales de MLflow y de los informes públicos?

   - A) Los hashes de los conjuntos de datos
   - B) La configuración de LoRA revisada
   - C) Los datos fuente y las respuestas sin procesar, las correspondencias de tokens y las URL prefirmadas
   - D) Los datos agregados no sensibles

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Distinga los ID/ARN privados de inventario que se necesitan de la divulgación pública, y verifique el registro automático y la captura de trazas.

</details>

5. ¿Qué afirmación sobre la gobernanza y el tamaño del modelo es correcta?

   - A) QLoRA siempre requiere un proyecto de Unified Studio
   - B) La gobernanza es el procedimiento elegido para este experimento; los 3.3B activos no representan la memoria total del modelo
   - C) La asignación de propietario revierte de forma atómica todos los fallos parciales
   - D) Un límite de tres horas para los trabajos limita el costo de todo el experimento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La tarjeta del modelo indica 30.5B en total y 3.3B activos. Verifique por separado la preparación y la propiedad, así como la memoria real de GPU y el costo.

</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/sagemaker-ai/01-platform-architecture.md)
