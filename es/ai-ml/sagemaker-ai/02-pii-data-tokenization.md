# Parte 2: Datos sintéticos de PII y tokenización determinista

Para una ruta de aprendizaje práctica, empieza con el [taller de aumento de datos](06-data-augmentation-workshop.md). Este capítulo documenta la implementación existente y el contrato operativo.

La regeneración de CPU del 2026-09-15 conservó los hashes históricos y también comprobó la superposición exacta de fuentes NFC: 22 fuentes compartidas entre train/validation, 36 entre train/test y 9 entre validation/test; 51 grupos de fuentes únicos abarcan al menos dos particiones. El nuevo taller divide las familias antes de aumentar solo los datos de entrenamiento en un ejemplo separado. No vuelve a etiquetar este corpus histórico como libre de filtraciones.

> Implementación y documentación revisadas: 2026-09-12. Se conservan Generator 1.0.0, la semilla 42 y los hashes existentes del conjunto de datos.

## La extracción está separada del reemplazo

El modelo emite filas candidatas `TYPE<TAB>ORIGINAL`:

```text
PERSON	Taylor Sample
EMAIL	synthetic.en.1494@example.com
```

Estos son ejemplos sintéticos. El modelo no edita el documento de origen.
Las comprobaciones del tipo y de coincidencia con el origen rechazan algunas
candidaturas no válidas, pero no demuestran que un valor sea PII, que su tipo
sea correcto ni que se hayan encontrado todas las entidades PII.
Trata el mapeo de reemplazo como información sensible.

## Alcance del conjunto de datos y de la evaluación

El conjunto de datos tiene 2,200 registros, con una división 80/20 coreano/inglés en cada partición.
La regeneración posterior a los cambios de implementación conservó todos los hashes del manifiesto.

| Partición | Registros | Coreano | Inglés | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| train | 1,600 | 1,280 | 320 | `b98429fef0b103f24e8eaded069cbd2f6def5fbf8c083a5c7baf366c9fc1d21a` |
| validation | 200 | 160 | 40 | `25ca38198d38e04be181e15b4e21a3c96d672f46f775ae1bc6c422ee4514f820` |
| test | 400 | 320 | 80 | `6f6ef9a6b42297738b292d5149f2e6e323f7bcd6f2325b6bfbc04ae6d9d0ec21` |

| Etiqueta | Significado en este experimento |
| --- | --- |
| PERSON | Nombre de persona |
| RRN | Identificador con formato de número de registro de residente coreano |
| DOB | Fecha de nacimiento |
| REL | Expresión de parentesco o relación |
| ADDRESS | Dirección |
| PHONE | Número de teléfono |
| EMAIL | Dirección de correo electrónico |
| ACCOUNT | Número de cuenta bancaria |
| CARD | Número de tarjeta de pago |

Estas son reglas de anotación específicas del experimento. Por ejemplo, las palabras que expresan relaciones pueden ser positivas, mientras que las cadenas de centralitas de empresas aparecen en documentos negativos.
No constituyen una taxonomía universal de sensibilidad.

El generador usa plantillas fijas, vocabularios pequeños de nombres y números sintéticos.
Los valores RRN/CARD no superan las funciones de suma de comprobación de ejemplo; eso, por sí solo, no demuestra la validez de los identificadores oficiales ni que no se hayan asignado.
Los valores PHONE son marcadores de posición sintéticos, no formatos nacionales validados ni rangos oficialmente reservados.
No se usan datos de clientes, pero eso no equivale a validar identificadores con fuentes autorizadas.

Que los registros y los hashes sean diferentes no garantiza la independencia de las plantillas o los vocabularios de entidades entre train/validation/test. No presentes este conjunto de datos como una referencia de generalización para cargas de trabajo reales. Para ese fin, usa conjuntos de evaluación separados y anotaciones revisadas.

## Reemplazo reversible de la grafía de origen

La implementación ahora sigue esta secuencia:

1. Normaliza el origen/los valores a NFC y recorta los espacios en blanco externos de tipo/valor.
2. Elimina los bloques completos `<think>...</think>` y, después, lee los tipos permitidos separados por tabuladores y los valores no vacíos.
3. Deduplica las candidaturas y exige que una coincidencia literal o una variante limitada coincida con el origen.
   El análisis y el reemplazo usan los mismos límites numéricos.
4. Da prioridad a las predicciones literales frente a las variantes generadas a partir de otras predicciones.
   Una prioridad de tipos fija resuelve los casos en que hay varios tipos para un mismo valor; no infiere la veracidad semántica.
5. Recorre el origen una sola vez, empezando por los patrones más largos.
6. Asigna tokens en el orden real en que aparecen en el origen, según **el tipo y la grafía NFC coincidente**.
   Las grafías idénticas reutilizan un token; las diferencias de espaciado/separadores reciben tokens distintos.
7. Omite los nombres de token que ya estén presentes en el origen original.
8. Almacena en el mapeo la grafía coincidente real y registra los tramos de reemplazo semiabiertos
   `[start, end)` en coordenadas de origen NFC.

```text
Source: 김가상 / 김 가 상 / [PERSON_1]
Candidate: PERSON	김가상
Masked: [PERSON_2] / [PERSON_3] / [PERSON_1]
```

El marcador original permanece sin cambios y se puede restaurar cada grafía de origen.
La numeración de los tokens no tiene por qué empezar en uno. La igualdad de tokens no equivale a resolver la identidad de entidades del mundo real.

Las variantes de `PERSON` abarcan formas limitadas y uniformes con espacios/tabuladores/saltos de línea para nombres de 2–6 caracteres después de quitar los espacios en blanco. Las variantes numéricas solo normalizan los caracteres permitidos de dígitos/espacios en blanco/separadores. Ya no descartan letras inventadas para fabricar una coincidencia con el origen: no se acepta `alias123456` si no está presente, simplemente porque `123456` aparezca en el origen. Un original alfanumérico aún puede coincidir literalmente. Estas reglas no validan oficialmente teléfonos/cuentas/identidades.

`reassemble_text` realiza una pasada de reemplazo para los tokens conocidos y conserva los tokens desconocidos. El evaluador comprueba los viajes de ida y vuelta. La igualdad se verifica respecto del texto de origen NFC, no de una restauración idéntica byte a byte de una representación NFD original.

## Mide los tramos de origen restantes, no el contenido de los marcadores de posición

El evaluador anterior buscaba cadenas completas de referencia en el texto enmascarado.
Esto producía dos resultados incorrectos:

- Enmascarar solo `Alpha` en la entidad de referencia `Alpha Beta` eliminaba la cadena completa e indicaba incorrectamente que no había filtración.
- Enmascarar un valor de referencia literal `PERSON` producía `[PERSON_1]`, cuya etiqueta se contabilizaba incorrectamente como texto de origen filtrado.

El evaluador corregido comprueba si la unión de los tramos de reemplazo reales cubre por completo cada aparición coincidente de cada valor de referencia o variante permitida.
También examina las apariciones repetidas. La cobertura parcial, incluida la de un separador sin cubrir, se considera sin cubrir según esta métrica conservadora. Los caracteres dentro de los nombres de tokens generados no se consideran exposición del origen.

Los registros de referencia contienen valores, no desplazamientos de anotación, por lo que estos tramos se infieren mediante la coincidencia con el origen. Esto no es una detección nueva de PII y puede coincidir con una aparición que no sea sensible en su contexto, aunque la misma cadena sí lo sea en otro. Interpreta la cobertura según la política de anotación, no como una garantía de privacidad.

## Significado exacto de las métricas

| Campo del resultado | Cálculo |
| --- | --- |
| entity/per_type precision, recall, F1 | Suma de TP/FP/FN sobre conjuntos normalizados de `(TYPE, ORIGINAL)` por documento |
| documents.leak_rate | Documentos con un tramo de referencia sin cubrir dividido por el total de documentos |
| entities.leak_rate | Pares de referencia únicos con alguna aparición sin cubrir dividido por el total de pares de referencia únicos |
| entities.over_redaction_rate | Nombre de campo heredado para la **tasa de pares predichos adicionales**: FP / pares predichos |
| entities.hallucination_rate | Filas TSV no vacías de tipos permitidos sin coincidencia con el origen dividido por esas filas |
| parse.success_rate | Fracción de documentos cuya marca parse_success proporcionada por quien realiza la llamada es True |
| tokenization.deterministic_rate | Fracción con el mismo texto enmascarado, mapeo y tramos después de invertir el orden de las candidaturas |
| tokenization.round_trip_rate | Fracción que se restaura al origen NFC |

Entity F1 no es F1 de NER a nivel de tramo. Los pares duplicados dentro de un documento se eliminan; el mismo par en documentos diferentes se contabiliza por separado. Los tipos se recortan y convierten a mayúsculas; los valores se recortan y normalizan a NFC. Una variante válida puede enmascarar por completo el origen aunque difiera de la grafía exacta de referencia y produzca FP/FN. Por lo tanto, el campo heredado de enmascaramiento excesivo no mide directamente los caracteres eliminados innecesariamente.

La alucinación usa la coincidencia con el origen independientemente de la marca de análisis. Los tipos desconocidos y el texto corriente quedan fuera del denominador de filas. La función auxiliar de inferencia actual marca como analizable una salida vacía o una salida que contenga al menos una fila utilizable que coincida con el origen; esto **no es una validación estricta de cada línea de salida**.
El evaluador excluye las predicciones de entidades cuando esa marca es False.

Los denominadores cero devuelven cero, incluido F1 para conjuntos de entidades vacíos. Se rechazan los ID duplicados de registros/predicciones, las predicciones para registros desconocidos y las anotaciones de referencia que no pueden coincidir con el origen. Los errores no repiten los valores de entidades sin enmascarar.

## Registros de entrenamiento y validación

Los registros JSONL contienen `source_text`, `entities` y `target_tsv`. El cargador construye prompts de sistema/usuario y completados del asistente. El entrenador solicita una pérdida solo para completados; valida el tokenizador/la plantilla reales, el truncamiento y la máscara de pérdida durante la ejecución. Mantén el origen, los completados y los mapeos fuera de los registros ordinarios y de los parámetros/etiquetas de MLflow.

Las pruebas de regresión reprodujeron colisiones de tokens, restauración con pérdida de variantes, aceptación excesiva de variantes numéricas y errores de evaluación antes de las correcciones.
Las 50 pruebas locales pasan. Una comprobación con oráculo de verdad de referencia sobre 2,200 registros también verifica la conservación de hashes, el determinismo, la restauración y la cobertura.
**Los resultados de comprobación de coherencia del oráculo no son predicciones del modelo ni mediciones de F1 de ajuste fino.**
No se realizó entrenamiento en GPU ni procesamiento de PII de clientes reales.

## Referencias

- [Generador sintético](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/data/generate_dataset.py)
- [Manifiesto del conjunto de datos](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/data/dataset-manifest.json)
- [Analizador y reemplazo](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [Implementación de evaluación](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)

[Anterior: Arquitectura de la plataforma](01-platform-architecture.md)

[Siguiente: Ejecución de SageMaker / MLflow](03-sagemaker-mlflow-execution.md)

[Cuestionario](../../quizzes/ai-ml/sagemaker-ai/02-pii-data-tokenization-quiz.md)
