# Taller: evaluación de modelos de PII y canalizaciones de enmascaramiento

> **Última actualización**: 15 de septiembre de 2026

El ejemplo ejecutable usa registros sintéticos y predicciones construidas manualmente en CPU. Sus cifras no representan el rendimiento de un modelo entrenado.

Una pérdida de entrenamiento decreciente no demuestra que la eliminación de PII sea eficaz. Un modelo puede encontrar nombres, pero pasar por alto direcciones de correo electrónico, o enmascarar números de documento que la política de anotación considera no sensibles. Este capítulo evalúa **tanto la extracción de entidades como los reemplazos resultantes** y, después, relaciona los errores con el siguiente experimento de datos.

Lee primero el [taller de QLoRA](05-qlora-finetuning-workshop.md) y el [taller de aumento de datos](06-data-augmentation-workshop.md). Los comandos parten de la raíz del repositorio y usan Python 3.12.

## 1. Separar las responsabilidades del modelo y del procesamiento

El modelo de ejemplo emite candidatos `TYPE<TAB>ORIGINAL` en vez de reescribir el documento completo.

| Etapa | Entrada → salida | Qué comprobar |
| --- | --- | --- |
| Extracción | Fuente → candidatos de tipo/valor | Omisiones, tipos incorrectos, valores inventados |
| Validación | Candidatos → candidatos permitidos que coinciden con la fuente | Sintaxis, longitud, tipos permitidos, coincidencia con la fuente |
| Reemplazo | Fuente/candidatos → texto enmascarado, asignación, segmentos | Repetición, cobertura parcial, colisiones, solapamientos |
| Comprobaciones residuales | Resultado enmascarado → aprobación o revisión | Reglas/detectores independientes, política, entradas no admitidas |
| Entrega | Documento aprobado → sistema posterior | Exclusión de asignaciones, control de acceso, alcance de los registros |

La coincidencia con la fuente confirma que un candidato aparece en ella. No confirma su tipo semántico ni que no haya otra PII. Combinar detectores tampoco hace que sus errores sean independientes.

`pseudonymize_text()` crea asignaciones de tokens reversibles. Conservar una asignación para `[PERSON_1]` tiene un propósito distinto de eliminar un valor sin ofrecer una función de restauración. Descartar una asignación por sí solo no demuestra que el contexto restante no permita identificar a alguien.

## 2. Asignar funciones a entrenamiento, validación y prueba final

1. **Entrenamiento:** actualizar los parámetros y aplicar aumento de datos de entrenamiento.
2. **Validación:** seleccionar rango, tasa de aprendizaje, épocas/pasos, mezclas de datos y reglas de salida.
3. **Prueba bloqueada:** evaluar el modelo y la política de procesamiento seleccionados.
4. **Conjunto de desafío:** examinar por separado OCR, documentos largos, plantillas desconocidas, tipos poco frecuentes, instrucciones incrustadas y otras condiciones difíciles.

Si los errores de una prueba final influyen en la siguiente selección de modelo, esa prueba ya forma parte del desarrollo. Registra el cambio y prepara otra versión de evaluación. Documenta si la separación se hace por familia de documentos, cliente, plantilla, fecha u otro eje.

**El `src/train.py` histórico evalúa las predicciones de referencia y las ajustadas en `test_records` en cada ejecución.** No uses ese comportamiento sin cambios como un ciclo de HPO repetido. Una implementación de ajuste necesita seleccionar candidatos a partir de la validación y realizar un paso final de prueba independiente y registrado. El ejercicio de CPU que aparece a continuación no ejecuta ese lanzador.

## 3. Reproducir “mayor F1, problemas persistentes” en CPU

Usa dos documentos:

- Un documento positivo con un nombre sintético y una dirección de correo `example.com` anotados.
- Un documento negativo cuyo número de documento no es PII según esta política.

La línea de base solo encuentra el nombre. El candidato encuentra el nombre y el correo, pero etiqueta incorrectamente el número del documento negativo como una cuenta. Las predicciones se construyen manualmente, sin invocar un modelo, para que se puedan verificar los cálculos de las métricas. Ambas versiones lingüísticas usan el mismo caso de prueba sintético en coreano.

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}"
export PII_EVAL_DIR="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/pii-evaluation.XXXXXX")"
python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
records = [
    {
        "id": "positive-1",
        "source_text": "담당자 김가상, 이메일 synthetic.ko.01@example.com",
        "entities": [
            {"type": "PERSON", "original": "김가상"},
            {"type": "EMAIL", "original": "synthetic.ko.01@example.com"},
        ],
        "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.ko.01@example.com",
    },
    {
        "id": "negative-1",
        "source_text": "문서번호 DOC-2026-001의 처리 상태를 확인합니다.",
        "entities": [],
        "target_tsv": "",
    },
]
baseline = [
    {"id": "positive-1", "content": "PERSON\t김가상", "parse_success": True},
    {"id": "negative-1", "content": "", "parse_success": True},
]
candidate = [
    {
        "id": "positive-1",
        "content": records[0]["target_tsv"],
        "parse_success": True,
    },
    {
        "id": "negative-1",
        "content": "ACCOUNT\tDOC-2026-001",
        "parse_success": True,
    },
]
for name, rows in (
    ("gold", records), ("baseline", baseline), ("candidate", candidate)
):
    with (out / f"{name}.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
PY

for phase in baseline candidate; do
  python3 -m src.evaluate \
    --test-jsonl "$PII_EVAL_DIR/gold.jsonl" \
    --predictions-jsonl "$PII_EVAL_DIR/$phase.jsonl" \
    --output-json "$PII_EVAL_DIR/$phase-metrics.json" \
    --environment cpu-demo --phase "$phase-demo" \
    --model-id synthetic-fixture-no-model \
    --duration-seconds 0 --hourly-usd 0
done

python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["PII_EVAL_DIR"])
for phase in ("baseline", "candidate"):
    m = json.loads((out / f"{phase}-metrics.json").read_text())["metrics"]
    print(phase, json.dumps({
        "entity": m["entity"],
        "leaked_documents": m["documents"]["leaked"],
        "extra_pairs": m["entities"]["over_redacted"],
        "round_trip": m["tokenization"]["round_trip_rate"],
    }))
PY
```

`--test-jsonl` es el nombre del argumento de la CLI de evaluación. Aquí apunta a un archivo del ejercicio escrito manualmente, no a un conjunto final de prueba reservado para producción.

Resultados esperados:

| Métrica | Línea de base | Candidato |
| --- | ---: | ---: |
| TP / FP / FN | 1 / 0 / 1 | 2 / 1 / 0 |
| Precisión | 1 | 2/3 |
| Exhaustividad | 1/2 | 1 |
| F1 de entidades | 2/3 | 0.8 |
| Documentos con elementos de referencia sin cubrir | 1 de 2 | 0 de 2 |
| Pares de extracción adicionales | 0 | 1 |
| Tasa de ida y vuelta | 1 | 1 |

El candidato mejora el F1, pero introduce el enmascaramiento del número de documento. Ambas predicciones completan correctamente el recorrido de ida y vuelta: **el éxito de la restauración no sustituye a la calidad de detección de PII.** La duración y el precio por hora en cero describen este caso de prueba manual; no implican que el entrenamiento con GPU sea gratuito.

## 4. Comprobar la unidad que mide cada métrica

Las métricas `entity` y `per_type` del paquete comparan conjuntos de pares `(TYPE, ORIGINAL)` a nivel de documento. Los pares idénticos repetidos dentro de un documento cuentan una sola vez. No se trata de un F1 de NER basado en anotaciones de segmentos independientes.

| Métrica | Uso | Limitación que hay que examinar |
| --- | --- | --- |
| Exhaustividad por tipo | Encontrar categorías de PII omitidas | Informar el número de entidades poco frecuentes evaluadas |
| Precisión por tipo | Identificar texto no sensible que se está enmascarando | Requiere una política de anotación coherente |
| Tasa de filtración de documentos | Documentos con algún elemento de referencia sin cubrir | No puede medir PII ausente de las etiquetas de referencia |
| Tasa de filtración de entidades | Cobertura de todas las apariciones coincidentes de un valor de referencia | Deduce las ubicaciones de los segmentos mediante la búsqueda por valor, en lugar de usar posiciones de referencia anotadas |
| `over_redaction_rate` | FP / pares predichos | No es la fracción de caracteres eliminados innecesariamente |
| `hallucination_rate` | Candidatos TSV permitidos que no aparecen en la fuente | Excluye del denominador los tipos no permitidos y la prosa común |
| Éxito del parseo | Estado del procesamiento del formato proporcionado por quien llama | La función auxiliar actual acepta algunas salidas aunque solo contengan un subconjunto de filas válidas |

Diseña un analizador estricto para producción que valide cada fila y devuelva fallos explícitos para filas mal formadas, respuestas truncadas y entradas que superen el límite de longitud. Descartar silenciosamente filas incorrectas no debe convertirse en “no se encontró PII”. El valor actual de `parse.success_rate` no demuestra que se haya implementado ese comportamiento estricto.

Sin anotaciones de referencia para documentos reales en producción, no se dispone de la misma tasa de filtración basada en datos de referencia. Observa muestras revisadas, detectores residuales y tasas de abstención/revisión, e identifica qué mide realmente cada uno.

## 5. Convertir los errores en el siguiente experimento de datos

Investiga los errores a nivel de documento en un espacio de trabajo de evaluación con control de acceso. Los registros generales deben incluir categorías de error, intervalos de longitud, idioma, identificadores de plantilla y agregados, en lugar del texto de origen.

| Error observado | Qué examinar primero | Siguiente experimento |
| --- | --- | --- |
| Encuentra nombres, pero omite cuentas | Recuentos por tipo y anotaciones faltantes | Añadir casos de entrenamiento con contexto de cuenta |
| Falla con nombres separados por espacios u OCR | Alineación de la forma superficial en la fuente y las etiquetas | Ampliar conjuntamente los textos fuente y sus etiquetas |
| Etiqueta números de documento como cuentas | Cobertura de casos negativos y contrastes contextuales | Añadir contextos numéricos positivos/negativos emparejados |
| Omite PII al final de documentos largos | Truncamiento del prompt y presupuesto de respuesta | Evaluar límites de fragmentos, solapamiento y reconstrucción de desplazamientos |
| Resultados deficientes con nombres desconocidos | Solapamiento de entidades entre entrenamiento y prueba | Evaluación con entidades excluidas del entrenamiento y nuevas familias de entrenamiento |
| Resultados deficientes con diseños nuevos | Separación por plantilla | Evaluación con plantillas excluidas y plantillas de entrenamiento aprobadas |
| Sigue instrucciones incrustadas en la fuente | Tratamiento de los documentos como datos | Casos sintéticos con instrucciones incrustadas y comprobaciones del esquema de salida |
| La pérdida disminuye mientras baja la exhaustividad | Validación contaminada, sobreajuste, límites de salida | Comparar puntos de control y criterios de parada temprana |

No copies ejemplos de prueba fallidos al entrenamiento y anuncies mejoras en esa misma prueba. Registra que el conjunto de análisis de errores ha influido en el desarrollo e identifica un nuevo conjunto de evaluación final.

## 6. Diseñar conjuntamente la longitud del entrenamiento y la inferencia

`max_sequence_length=1024` no significa 1.024 caracteres del documento. Las plantillas de chat, las instrucciones del sistema, el texto de origen y las respuestas objetivo consumen el presupuesto del tokenizador. El coreano, el inglés y los números no tienen la misma proporción de caracteres por token.

- Verifica que el truncamiento no elimine todos los tokens objetivo supervisados durante el entrenamiento.
- No consideres ausente durante la inferencia la PII de una región de entrada que se haya truncado.
- La división en fragmentos requiere desplazamientos en el texto original, conciliación de duplicados, tratamiento de entidades que atraviesan límites y gestión de apariciones repetidas.
- Prueba deliberadamente PII que cruce los límites; no des por sentado que el solapamiento basta.
- Informa explícitamente del desbordamiento de entrada y de las respuestas incompletas, en lugar de etiquetar como completo un resultado parcial.

## 7. Escribir una tabla de aceptación antes de medir

Lo siguiente es una **plantilla para las evidencias y los criterios de un equipo**, no un rendimiento alcanzado por el repositorio ni umbrales numéricos universales.

| Área | Evidencia | Acción si es insuficiente |
| --- | --- | --- |
| Etiquetas y separación | Versión de anotación, familia/división/hash, recuentos por subgrupo | Reconstruir la evaluación |
| Selección de candidatos | Comparaciones de validación, variable modificada, decisión | Ejecutar otro experimento controlado |
| Calidad final | Resultados y recuentos de errores por tipo en la prueba bloqueada | Detener el despliegue |
| Contrato de salida | Pruebas de respuestas vacías, mal formadas y truncadas | Corregir el análisis/abstención |
| Política de procesamiento | Segmentos de reemplazo, ciclo de vida de las asignaciones, comprobaciones residuales | Corregir la política o el procesamiento |
| Comportamiento operativo | Latencia, memoria, tiempos de espera, rendimiento por longitud | Ajustar la capacidad y los límites de longitud |
| Reproducción/recuperación | Revisión del modelo base/tokenizador, hash del adaptador, entorno, versión anterior | Completar el empaquetado |

Elige criterios específicos para la tarea de F1, exhaustividad y latencia **antes de la evaluación**. No observar errores en una muestra pequeña no demuestra que la tasa real de errores sea cero. Muestra numeradores y denominadores para los resultados por subgrupo.

## 8. De los artefactos de SageMaker a un paquete de servicio

Que un trabajo de entrenamiento de SageMaker llegue al estado `Completed` solo indica que ese trabajo terminó. La creación del endpoint, la carga del adaptador, la validación de la salida y la aprobación del resultado enmascarado son pasos independientes.

1. Conserva los adaptadores, la configuración y los resultados agregados de `/opt/ml/model` y MLflow.
2. Registra junto al adaptador la revisión exacta del modelo base/tokenizador, la plantilla de chat, la configuración de cuantización y la versión del analizador.
3. Prueba la recarga y la decodificación determinista en el entorno previsto. Un adaptador por sí solo no constituye un modelo base independiente completo.
4. Observa la longitud, el formato de salida y las tasas de error en un flujo de trabajo sombra o de canario limitado.
5. Versiona conjuntamente la combinación de **modelo + tokenizador + analizador + política** para poder revertirla como una unidad.

Este capítulo no implementa ni despliega un endpoint o un contenedor de versiones estricto. Un despliegue real también debe probar, mediante CloudWatch, la exposición del texto de origen, la respuesta y la asignación; el registro automático y las trazas de MLflow; el manejo de errores; y el trazado de solicitudes. Los adaptadores reciben la influencia de sus datos de entrenamiento y requieren su propia revisión antes de compartirlos.

## Comprueba lo que has aprendido

1. ¿Por qué no desplegar inmediatamente el candidato con mayor F1? **Añade enmascaramiento en un documento negativo, y dos documentos sintéticos no constituyen una evaluación representativa.**
2. ¿Un 100 % de ida y vuelta significa que se eliminó toda la PII? **No. Puede que solo se hayan restaurado correctamente los valores reemplazados.**
3. ¿Qué ocurre si se utilizó la misma prueba para elegir entre varios valores de rango? **Participó en la selección y ya no es una prueba final independiente.**
4. ¿Un candidato que coincide con la fuente necesariamente es PII? **No; el número de documento es un contraejemplo.**
5. ¿Se puede calcular la tasa de filtración de este evaluador solo a partir de las salidas del modelo en tráfico sin etiquetar? **No; requiere anotaciones de referencia.**

## Referencias

- [CLI de evaluación del repositorio](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/evaluate.py)
- [Implementación real de las métricas](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/metrics.py)
- [Reemplazo y reconstrucción](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/src/pii_tokens.py)
- [Formato de punto de control de PEFT](https://huggingface.co/docs/peft/v0.17.0/en/developer_guides/checkpoint)
- [Directorios de contenedores de SageMaker](https://docs.aws.amazon.com/sagemaker/latest/dg/amazon-sagemaker-toolkits.html)
- [Operaciones y restauración de Presidio Anonymizer](https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/README.md)

Anterior: [Taller de aumento de datos](06-data-augmentation-workshop.md) · [Itinerario de aprendizaje](README.md)

[Cuestionario del taller](../../quizzes/ai-ml/sagemaker-ai/07-pii-evaluation-release-quiz.md)
