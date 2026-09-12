# Cuestionario de seguimiento de MLflow

## Preguntas de opción múltiple

1. ¿Cómo se relacionan Experiments y Runs?
   - A) Un Experiment agrupa Runs; un Run puede representar entrenamiento o evaluación
   - B) Un Experiment es una GPU
   - C) Un Run siempre es un modelo desplegado
   - D) Son la misma entidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Los Runs también pueden registrar el preprocesamiento y las tareas de comparación.
</details>

2. ¿Cuál es el backend de metadatos predeterminado en un entorno nuevo de MLflow 3.16.0?
   - A) Un bucket de S3
   - B) sqlite:///mlflow.db
   - C) localStorage del navegador
   - D) PostgreSQL obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

SQLite es el valor predeterminado; inspecciona el comportamiento de compatibilidad si ./mlruns ya existe. Los URI explícitos eliminan la ambigüedad.
</details>

3. ¿Cuál es el cambio importante de LoggedModel en MLflow 3?
   - A) model_id, estado y seguimiento de relaciones independientes
   - B) La primera capacidad de llamar a log_model sin un bloque start_run
   - C) Los artefactos ya no son necesarios
   - D) Despliegue inmediato en GPU al registrarse

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Model.log en 2.22.0 ya iniciaba un Run implícitamente cuando era necesario. La identidad independiente del modelo es distinta de omitir un contexto explícito de Run.
</details>

4. ¿Qué afirmación sobre autologging es correcta?
   - A) Captura todo en código arbitrario
   - B) Siempre elimina PII
   - C) Revisa las versiones compatibles y las entradas/salidas recopiladas de cada integración
   - D) Completa el despliegue automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El comportamiento depende del framework y de las opciones. Comprueba los ejemplos de entrada, los datos sin procesar y la recopilación de artefactos del modelo.
</details>

5. ¿Qué afirmación sobre tracing y costo es precisa?
   - A) Tracing apareció por primera vez en 3.x
   - B) Cada tool span tiene costo de LLM
   - C) El costo derivado de tokens siempre equivale a la factura
   - D) Tracing llegó en 2.14.0; la recopilación de uso depende de la integración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Distingue la expansión posterior de la introducción inicial. No se puede garantizar el costo sin información del modelo, el uso y los precios.
</details>

6. ¿Cuándo puede un cliente necesitar permisos de S3 a pesar de usar un servidor de tracking remoto?
   - A) Modo sin proxy con un URI directo de artefactos de S3
   - B) Solo al leer parámetros de SQLite
   - C) Nunca necesita permisos independientemente del modo
   - D) Cada búsqueda de nombre de alias requiere acceso a S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Las rutas de metadatos y artefactos son diferentes. El modo directo requiere permisos de almacenamiento del cliente y acceso de red.
</details>

7. ¿Cómo inspeccionas una métrica registrada en los pasos 0 y 1?
   - A) El parámetro cambia automáticamente
   - B) Solo el segundo valor se conserva para siempre
   - C) Usa get_metric_history para inspeccionar ambas observaciones
   - D) Se registran automáticamente dos modelos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Distingue el resumen actual del historial de métricas con marcas de tiempo y pasos.
</details>

8. ¿Cuál es una ruta de consulta apropiada para la interfaz web de Tracking?
   - A) El navegador se conecta directamente a PostgreSQL
   - B) El navegador llama a las API HTTP del servidor
   - C) La UI siempre lee archivos directamente de los Pods de entrenamiento
   - D) El navegador necesita una contraseña de administrador de base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El servidor accede a su backend. La configuración del proxy de artefactos es un asunto independiente.
</details>

## Preguntas de respuesta corta

9. ¿Puede un resultado PENDING de initialize_logged_model realizar inferencia de inmediato?

<details>
<summary>Mostrar respuesta</summary>

No. Puede contener solo metadatos; todavía se requieren el flavor real, los pesos, el registro de artefactos y la finalización. READY no implica calidad ni aprobación del despliegue.
</details>

10. ¿Por qué un experimento existente podría seguir accediendo directamente a S3 después de que cambien los indicadores de artefactos del servidor?

<details>
<summary>Mostrar respuesta</summary>

El URI de artefactos registrado del experimento/Run no se reescribe retroactivamente. Inspecciona ese URI, así como los permisos y la ruta de transferencia reales.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/01-tracking.md)
