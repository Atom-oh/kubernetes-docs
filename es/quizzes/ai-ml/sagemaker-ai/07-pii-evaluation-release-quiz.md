# Cuestionario sobre evaluación de PII y canalización de enmascaramiento

> **Última actualización**: September 15, 2026

## Preguntas de opción múltiple

1. El candidato de prueba mejora el F1 hasta 0.8. ¿Por qué no implementarlo de inmediato?

   - A) Su recall es cero
   - B) Enmascara como cuenta un número de documento negativo, y la evaluación solo tiene dos documentos sintéticos
   - C) Omite todas las entidades gold
   - D) Falló la restauración de ida y vuelta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

TP/FP/FN son 2/1/0. Evalúe la puntuación agregada más alta junto con el nuevo error de enmascaramiento.

</details>

2. ¿Qué demuestra una tasa de restauración de ida y vuelta de 1.0?

   - A) Se detectó toda la PII real
   - B) El origen no contenía PII
   - C) La correspondencia reconstruyó el origen NFC a partir del resultado enmascarado
   - D) El modelo se generaliza a nuevos clientes

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

La restauración puede ser correcta aunque quede PII omitida visible en el origen.

</details>

3. ¿Cómo se calcula actualmente entities.over_redaction_rate?

   - A) Caracteres enmascarados innecesariamente / todos los caracteres
   - B) Documentos con filtraciones / todos los documentos
   - C) FN / pares gold
   - D) Pares FP / pares predichos

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

A pesar de su nombre histórico, mide los pares extraídos de más, no la eliminación excesiva a nivel de caracteres.

</details>

4. ¿Qué debe hacer un parser estricto de serving?

   - A) Validar cada fila, tipo, longitud y truncamiento, y devolver fallos explícitos
   - B) Aceptar toda la respuesta si una fila es válida
   - C) Descartar las filas incorrectas e informar que no hay PII
   - D) Inventar más candidatos que falten

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Que el parser tolerante actual acepte un resultado no equivale a cumplir un contrato estricto. No marque como completos los resultados truncados.

</details>

5. ¿Qué función tiene un conjunto de prueba que se inspecciona repetidamente para seleccionar el rank?

   - A) Sigue siendo una prueba final independiente
   - B) Es un conjunto de evaluación que se usa durante el desarrollo o la selección
   - C) No se ve afectado porque no se usó para los gradientes
   - D) Es independiente porque tiene un hash fijo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

La selección puede comprometer la independencia de la prueba final incluso sin actualizaciones de gradientes. Separe la validación de la prueba bloqueada.

</details>

6. ¿Cómo debe interpretarse max_sequence_length=1024 al diseñar los datos?

   - A) Contar únicamente 1,024 caracteres del documento
   - B) El coreano y el inglés comparten la misma proporción de caracteres por token
   - C) Comprobar los presupuestos del tokenizer para la plantilla, las instrucciones, el origen y la respuesta
   - D) La configuración se ignora si el modelo admite un contexto más largo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Compruebe si se truncaron los targets o la PII del origen, y evalúe los límites y la reconstrucción de offsets al dividir en chunks.

</details>

7. ¿Qué queda por hacer cuando un SageMaker Training Job alcanza el estado Completed?

   - A) Asociar de inmediato un endpoint sin comprobaciones de calidad
   - B) Inferir usando solo un adaptador y ningún modelo base
   - C) Asociar correspondencias a todos los logs posteriores
   - D) Volver a cargar, evaluar y aprobar la combinación exacta de modelo base/tokenizer/adaptador/parser

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

La terminación del Job es distinta de la calidad del servicio y la aprobación del enmascaramiento. Versione la combinación completa necesaria para la reversión.

</details>

8. ¿Puede este evaluador calcular la misma tasa de filtración en documentos de producción sin gold?

   - A) No; distinga las anotaciones revisadas, las comprobaciones de datos residuales y su alcance de medición
   - B) Sí; usar todas las salidas del modelo como gold
   - C) Sí; el éxito de la restauración de ida y vuelta significa que no hay filtraciones
   - D) Sí; una salida vacía significa que se eliminó toda la PII

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

La métrica comprueba los valores gold que no quedaron cubiertos. Sin gold, no se puede obtener la misma medida de integridad.

</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/sagemaker-ai/07-pii-evaluation-release.md)
