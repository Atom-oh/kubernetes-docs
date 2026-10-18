# Cuestionario de seguimiento de MLflow

## Preguntas de opción múltiple

1. ¿Cómo se relacionan los experimentos y las ejecuciones?
   - A) Un experimento agrupa ejecuciones; una ejecución puede representar entrenamiento o evaluación
   - B) Un experimento es una GPU
   - C) Una ejecución siempre es un modelo desplegado
   - D) Son la misma entidad

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Las ejecuciones también pueden registrar el preprocesamiento y las tareas de comparación.
</details>

2. ¿Cuál es el backend de metadatos predeterminado en un entorno nuevo de MLflow 3.16.0?
   - A) Un bucket de S3
   - B) sqlite:///mlflow.db
   - C) localStorage del navegador
   - D) PostgreSQL obligatorio

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

SQLite es el valor predeterminado; inspecciona el comportamiento de compatibilidad si ./mlruns ya existe. Las URI explícitas eliminan la ambigüedad.
</details>

3. ¿Cuál es el cambio importante de LoggedModel en MLflow 3?
   - A) Seguimiento independiente de model_id, el estado y las relaciones
   - B) La posibilidad inédita de llamar a log_model sin un bloque start_run
   - C) Los artefactos ya no son necesarios
   - D) Despliegue inmediato en GPU al registrarse

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Model.log en 2.22.0 ya iniciaba una ejecución de forma implícita cuando era necesario. La identidad independiente del modelo es distinta de omitir un contexto explícito de ejecución.
</details>

4. ¿Qué afirmación sobre el registro automático es correcta?
   - A) Captura todo en código arbitrario
   - B) Siempre elimina PII
   - C) Revisa las versiones compatibles y los datos de entrada y salida que recopila cada integración
   - D) Completa el despliegue automáticamente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

El comportamiento depende del framework y de las opciones. Comprueba los ejemplos de entrada, los datos sin procesar y la recopilación de artefactos del modelo.
</details>

5. ¿Qué afirmación sobre las trazas y el costo es precisa?
   - A) Las trazas aparecieron por primera vez en 3.x
   - B) Cada tramo de herramienta tiene un costo de LLM
   - C) El costo calculado a partir de los tokens siempre equivale al de la factura
   - D) Las trazas llegaron en 2.14.0; la recopilación del uso depende de la integración

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Distingue la ampliación posterior de la función de su introducción inicial. No se puede garantizar el costo sin información sobre el modelo, su uso y los precios.
</details>

6. ¿Cuándo puede un cliente necesitar permisos de S3 aunque use un servidor remoto de seguimiento?
   - A) Modo sin proxy con un URI directo a los artefactos de S3
   - B) Solo al leer parámetros de SQLite
   - C) Nunca necesita permisos independientemente del modo
   - D) Cada búsqueda de nombre de alias requiere acceso a S3

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Las rutas de acceso a metadatos y artefactos son distintas. El modo directo requiere que el cliente tenga permisos de almacenamiento y acceso de red.
</details>

7. ¿Cómo puedes consultar una métrica registrada en los pasos 0 y 1?
   - A) El parámetro cambia automáticamente
   - B) Solo el segundo valor se conserva para siempre
   - C) Usa get_metric_history para consultar ambas observaciones
   - D) Se registran automáticamente dos modelos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Distingue el resumen actual de la métrica de su historial, que incluye marcas de tiempo y pasos.
</details>

8. ¿Cuál es una ruta adecuada para que la interfaz web de seguimiento obtenga datos?
   - A) El navegador se conecta directamente a PostgreSQL
   - B) El navegador llama a las API HTTP del servidor
   - C) La UI siempre lee archivos directamente de los Pods de entrenamiento
   - D) El navegador necesita una contraseña de administrador de base de datos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El servidor accede a su backend. La configuración del proxy de artefactos es independiente.
</details>

## Preguntas de respuesta corta

9. ¿Puede un resultado PENDING de initialize_logged_model servir para hacer inferencias de inmediato?

<details>
<summary>Mostrar respuesta</summary>

No. Puede contener solo metadatos; todavía se requieren el flavor real, los pesos, el registro de artefactos y la finalización. READY no implica que el modelo tenga calidad suficiente ni que esté aprobado para su implementación.
</details>

10. ¿Por qué un experimento existente podría seguir accediendo directamente a S3 después de cambiar las opciones de artefactos del servidor?

<details>
<summary>Mostrar respuesta</summary>

El URI de artefactos registrado para el experimento o la ejecución no se reescribe retroactivamente. Inspecciona ese URI, así como los permisos y la ruta de transferencia reales.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/mlflow/01-tracking.md)
