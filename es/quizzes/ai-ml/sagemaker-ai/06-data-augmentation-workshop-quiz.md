# Cuestionario sobre datos PII sintéticos y aumento de datos

> **Última actualización**: 15 de septiembre de 2026

## Preguntas de opción múltiple

1. ¿Cuál es el orden correcto para las paráfrasis y las variantes de OCR de una misma fuente?

   - A) Generar todas las variantes y luego dividir los ID de registro al azar
   - B) Asignar las familias de fuentes a las particiones y luego aumentar solo los datos de entrenamiento
   - C) Asignar cada variante a una partición diferente
   - D) Copiar primero los errores de prueba a los datos de entrenamiento

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Todos los descendientes deben permanecer en la misma partición que su familia de origen para evitar filtraciones entre particiones de la fuente y sus variantes.

</details>

2. ¿Cuántos registros de entrenamiento se obtienen de 24 familias con una base y dos variantes cada una?

   - A) 24
   - B) 48
   - C) 72
   - D) 120

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

24 × 3 = 72. Cada una de las ocho familias de validación y prueba conserva solo su versión base.

</details>

3. ¿Qué se requiere al sustituir un nombre sintético?

   - A) Cambiar solo el ID del registro
   - B) Cambiar la fuente y conservar el TSV
   - C) Cambiar el TSV y conservar la fuente
   - D) Actualizar conjuntamente la fuente, las entidades y el TSV, y registrar el linaje

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Vuelve a generar las etiquetas de referencia a partir de la fuente transformada. La mera presencia de una cadena todavía no demuestra que la semántica sea correcta ni que la anotación esté completa.

</details>

4. ¿Qué demuestra el laboratorio mediante la separación por familia y por fuente exacta?

   - A) Las familias y las fuentes NFC idénticas no se distribuyen entre particiones
   - B) Todas las personas y los identificadores quedan separados entre particiones
   - C) Todas las plantillas quedan separadas entre particiones
   - D) Se valida la generalización en el mundo real

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Se comparten algunos nombres, plantillas y dominios. La exclusión de entidades, plantillas o dominios requiere un diseño aparte.

</details>

5. Después de transformar un documento negativo que solo contiene una centralita excluida por esta política, ¿cuál debería ser su objetivo?

   - A) Añadir la centralita como PHONE
   - B) Dejar vacíos las entidades y `target_tsv`
   - C) Añadir un tipo UNKNOWN
   - D) Añadir todos los números como ACCOUNT

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Los ejemplos sin entidades son importantes. Define los negativos para el dominio y verifica durante el entrenamiento real que se supervise EOS para las respuestas vacías.

</details>

6. ¿Por qué puede este laboratorio rechazar una etiqueta omitida incluso después de volver a calcular los hashes de los archivos?

   - A) Los hashes autentican al productor
   - B) Encuentra todos los datos PII en cualquier documento de cliente
   - C) También vuelve a comprobar el contenido con la semilla y la receta fija de familias
   - D) Mide automáticamente la puntuación F1 del modelo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Esto comprueba la reproducibilidad del ejercicio sintético fijo, no las anotaciones arbitrarias ni la identidad del productor.

</details>

7. ¿Qué se debe mantener constante o registrar al comparar el entrenamiento original con el aumentado?

   - A) Elegir el mejor resultado inspeccionando la prueba repetidamente
   - B) Comparar solo la cantidad de archivos
   - C) Comparar solo el éxito de generación
   - D) Usar la misma validación y decodificación, y registrar los presupuestos de ejemplos, tokens y pasos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

Incluso con el mismo número de pasos, el modelo puede recibir cantidades y longitudes de datos diferentes. Usa la validación para seleccionar candidatos.

</details>

8. ¿Por qué la suma de las intersecciones históricas por pares 22, 36 y 9 difiere de los 51 grupos de fuentes únicos que cruzan particiones?

   - A) Las fuentes que aparecen en las tres particiones se cuentan en varias intersecciones por pares
   - B) Las fuentes NFC siempre identifican documentos diferentes
   - C) Todos los ID de registro son idénticos
   - D) 51 es el recuento de errores del modelo entrenado

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

La suma de las intersecciones por pares no equivale al recuento de grupos de fuentes únicos. Estas son observaciones de datos de CPU, no métricas de rendimiento del modelo.

</details>

---

[Volver al material de aprendizaje](../../../ai-ml/sagemaker-ai/06-data-augmentation-workshop.md)
