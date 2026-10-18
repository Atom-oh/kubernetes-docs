# Cuestionario sobre datos sintéticos con PII y tokenización

## Preguntas de opción múltiple

1. ¿Cuál es el contrato de salida del modelo y cuál es su límite?

   - A) Generar siempre un documento anónimo correcto
   - B) Todas las cadenas de origen son PII
   - C) Filas candidatas TYPE/TAB/ORIGINAL; evaluar por separado las omisiones y clasificaciones erróneas
   - D) Devolver la pertenencia al proyecto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La coincidencia con el origen demuestra que el texto aparece en él, pero no su corrección semántica ni que se haya detectado por completo.

</details>

2. ¿Cómo se gestionan los nombres con distintos espacios y un [PERSON_1] preexistente?

   - A) Reemplazar todas las variantes ortográficas con un único valor de correspondencia
   - B) Usar tokens reversibles por variante y evitar los nombres de marcador existentes
   - C) Restaurar siempre el marcador anterior como un nombre nuevo
   - D) Acortar el origen de forma arbitraria

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Si coinciden el tipo y la grafía, se reutiliza un token; las grafías distintas reciben tokens separados, vinculados al texto real del origen.

</details>

3. ¿Qué afirmación sobre las particiones y el alcance de la validación es correcta?

   - A) Hay 1.600/200/400 registros; se pueden compartir plantillas y nombres entre particiones
   - B) Los hashes diferentes demuestran la generalización a cargas de trabajo reales
   - C) Un fallo de checksum demuestra que no hubo una asignación oficial
   - D) Todo PHONE es un número reservado oficialmente

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Se conservan los hashes existentes de generator-1.0.0; distinga las pruebas con plantillas sintéticas de la evaluación con cargas de trabajo reales.

</details>

4. ¿Cómo gestiona la evaluación corregida de filtraciones el caso en que solo se enmascara Alpha de Alpha Beta en el valor gold?

   - A) Informar siempre cero porque desapareció la cadena completa
   - B) Detectar una parte no cubierta del intervalo del texto de origen en gold
   - C) Buscar únicamente nombres de marcador
   - D) Forzar la filtración a cero después de un ciclo de ida y vuelta correcto

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Comprueba que la unión de los reemplazos cubra todo el intervalo de origen. La restauración y la detección completa son métricas distintas.

</details>

5. ¿Qué demuestra la comprobación oracle de 2.200 registros con un TSV de respuestas?

   - A) El F1 medido de un modelo ajustado
   - B) El rendimiento de GPU
   - C) La coherencia del evaluador, la restauración y los hashes, no la calidad de la salida del modelo
   - D) La detección garantizada de toda PII real

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Se aprobaron cincuenta pruebas locales y la comprobación oracle; no se ejecutó el entrenamiento en GPU ni la evaluación del modelo ajustado.

</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/sagemaker-ai/02-pii-data-tokenization.md)
