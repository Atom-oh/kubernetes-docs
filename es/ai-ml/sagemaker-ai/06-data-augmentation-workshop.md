# Taller: datos sintéticos de PII y aumento de datos

> **Última actualización**: September 15, 2026

Este ejercicio con datos sintéticos se ejecuta con Python 3.12 y no requiere pesos de modelos, una cuenta de AWS ni GPU.

El aumento de datos debe añadir **condiciones de entrada en las que el sistema realmente falla**, en lugar de limitarse a aumentar el número de archivos. Duplicar documentos o generar etiquetas desalineadas puede aumentar el trabajo de entrenamiento y, al mismo tiempo, hacer que la evaluación sea menos fiable.

Define primero la política de anotación y divide las familias de documentos; después, aplica transformaciones que preserven las etiquetas. Empieza con el pequeño ejercicio de CPU y usa las secciones finales para planificar un conjunto de datos de dominio más amplio.

## 1. Define el objetivo de aprendizaje

El texto de origen, las anotaciones de entidades y el objetivo del modelo deben coincidir.

```json
{
  "id": "synthetic-train-example",
  "source_text": "신청인 김가상, 이메일 synthetic.01@example.com",
  "entities": [
    {"type": "PERSON", "original": "김가상"},
    {"type": "EMAIL", "original": "synthetic.01@example.com"}
  ],
  "target_tsv": "PERSON\t김가상\nEMAIL\tsynthetic.01@example.com"
}
```

`source_text` es el documento de entrada; `target_tsv` es la respuesta del asistente que se usa como objetivo de supervisión. `entities` permite realizar auditorías y evaluaciones. Esto es distinto de entrenar un modelo para que genere el documento completo con los datos enmascarados.

Primero, redacta una guía de anotación.

| Decisión | Ejemplo | Fallo si no se aclara |
| --- | --- | --- |
| Semántica de los tipos | El contacto personal es PHONE; según esta política, el número general de una empresa no lo es | Etiquetas contradictorias para cadenas similares |
| Límites exactos | Conserva los espacios de los nombres y los separadores telefónicos del origen | Desajuste entre origen y objetivo |
| Clasificación contextual | Distingue los números de documento de las cuentas | Tratar todos los números como sensibles |
| Repetición/solapamiento | Nombres repetidos, nombres dentro de direcciones | Desacuerdo entre anotación y reemplazo |
| Sin entidades | `entities=[]`, `target_tsv=""` | Aprender a extraer algo de cada documento |
| Casos inciertos | Entradas ilegibles o no compatibles, contexto ambiguo | Incorporar conjeturas como datos de referencia en el entrenamiento |

La regla sobre el número general es la política de este ejemplo, no una regla organizativa universal. Las etiquetas `(TYPE, ORIGINAL)` a nivel de documento no permiten anotar de forma independiente distintas apariciones de una misma cadena. Si las apariciones tienen significados diferentes, amplía conjuntamente el esquema de desplazamientos/segmentos, el evaluador y el código de reemplazo.

## 2. Distingue la generación sintética del aumento de datos

- **Generación sintética:** crear documentos nuevos a partir de plantillas, valores sintéticos o un modelo generativo.
- **Aumento de datos:** cambiar valores, redacción, diseño o ruido, preservando las etiquetas previstas de un ejemplo de entrenamiento aprobado.
- **Validación:** comprobar que el origen transformado y los objetivos sigan coincidiendo. Que la generación se complete correctamente no garantiza que las etiquetas sean correctas.

Trata también las salidas de modelos externos como datos candidatos. No des por sentado que debes enviar valores de origen a una API externa ni aceptar las salidas generadas como datos de referencia sin revisarlas.

## 3. Divide las familias antes de aumentar los datos

Agrupa el original y sus traducciones, variantes de OCR y paráfrasis bajo un mismo `family_id`. Asigna primero la familia a train/validation/test y, después, genera descendientes únicamente para las familias de entrenamiento.

```text
family-001 → train      → base + context + layout
family-002 → validation → base
family-003 → test       → base
```

Dividir aleatoriamente después del aumento de datos puede colocar documentos casi idénticos en entrenamiento y prueba. Una clave de agrupación requiere procedencia: asignar un ID nuevo a un registro no crea un cliente ni una familia de origen independientes.

| Eje de separación | Filtración que aborda | Evaluación adicional |
| --- | --- | --- |
| Familia | El original y sus descendientes quedan en particiones distintas | Nuevas transformaciones/ruido |
| Entidad/cliente | Las mismas personas/identificadores aparecen en ambos lados | Nombres, identificadores y clientes no vistos |
| Plantilla | Memorización de diseños | Plantillas no vistas |
| Dominio/tiempo | Dependencia de una distribución comercial/temporal | Dominios nuevos o períodos futuros |

Este ejercicio de CPU comprueba la **separación por familia y los duplicados exactos del origen en NFC**. Se comparten algunos nombres, plantillas y dominios; el ejercicio no demuestra independencia de entidades, plantillas ni dominios.

## 4. Ejecuta el pequeño ejercicio de aumento de datos

Empieza en la raíz del repositorio. El generador solo acepta un directorio de salida nuevo, así que no pases a `--output-dir` un directorio que ya hayas creado.

```bash
cd examples/ai-ml/qwen-pii-finetuning
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab"
export PII_AUG_RUN="$(mktemp -d "${XDG_CACHE_HOME:-$HOME/.cache}/qwen-pii-lab/run.XXXXXX")"
export PII_AUG_DIR="$PII_AUG_RUN/dataset"

python3 -m data.augmentation_lab --output-dir "$PII_AUG_DIR" --seed 42
python3 -m data.augmentation_lab --audit-dir "$PII_AUG_DIR"

python3 - <<'PY'
import json
import os
from collections import Counter
from pathlib import Path

root = Path(os.environ["PII_AUG_DIR"])
for split in ("train", "validation", "test"):
    rows = [
        json.loads(line)
        for line in (root / f"{split}.jsonl").read_text().splitlines()
    ]
    print(split, {
        "records": len(rows),
        "families": len({r["provenance"]["family_id"] for r in rows}),
        "negative": sum(not r["entities"] for r in rows),
        "languages": dict(Counter(r["language"] for r in rows)),
    })
PY
```

Las salidas son `train.jsonl`, `validation.jsonl`, `test.jsonl` y `augmentation-manifest.json`.

| Partición | Familias | Registros | Coreano / inglés | Registros negativos |
| --- | ---: | ---: | ---: | ---: |
| train | 24 | 72 | 36 / 36 | 36 |
| validation | 8 | 8 | 4 / 4 | 4 |
| test | 8 | 8 | 4 / 4 | 4 |

Las 40 familias se estratifican por idioma y por estado positivo/negativo; en cada estrato se asignan 6/2/2 familias. El conjunto de entrenamiento incluye un elemento base y dos variantes; validation/test conservan solo los elementos base. La proporción de 50 % de negativos y la mezcla lingüística de 50/50 hacen que el ejercicio sea comparable; no son estimaciones de la prevalencia en producción.

El ejercicio compacto abarca PERSON, EMAIL y PHONE. Tiene un propósito distinto del generador histórico de nueve tipos. No permite evaluar la calidad de RRN, CARD ni otros tipos que no estén presentes en este pequeño conjunto.

## 5. Lee la procedencia y las transformaciones

Conserva los campos del cargador existente y añade `provenance`.

| Campo | Significado |
| --- | --- |
| `id` | ID distinto para cada variante |
| `language`, `domain` | Categorías para la agregación y el análisis de errores |
| `provenance.family_id` | Familia compartida por el original y las variantes |
| `provenance.split` | Asignación realizada antes de que existan las variantes |
| `provenance.parent_id` | Registro base del que deriva una variante |
| `provenance.augmentation` | Nombre de la transformación aplicada |

La procedencia y el estado positivo/negativo son metadatos de auditoría. Al igual que en el cargador existente, incluye solo `source_text` en el prompt del usuario; no añadas la partición, la presencia de datos de referencia ni pistas sobre las etiquetas de referencia. Incluye `target_tsv` en la respuesta supervisada del asistente.

El ejecutable tiene dos tipos de variantes:

1. **Envoltura contextual:** cambia el contexto sintético circundante, conservando los valores de PII y el significado de las anotaciones.
2. **Diseño/Unicode:** cambia el orden/diseño de los campos y usa NFD para las variantes en coreano. Representa conjuntamente el origen y los originales; después, vuelve a generar TSV según el nuevo orden del origen.

NFD usa una representación descompuesta, incluidos los jamo de Hangul; NFC usa composición canónica. El texto visualmente idéntico puede tener bytes distintos, por lo que la comparación exacta del origen primero lo normaliza a NFC.

Los registros negativos conservan anotaciones y objetivos vacíos después de la transformación. Reordenar o normalizar Unicode no debe inventar entidades. Estas variantes no pretenden reproducir la distribución de ruido de un escáner o motor de OCR real.

## 6. Vuelve a generar el origen y las etiquetas al sustituir entidades

El siguiente es un patrón mínimo de sustitución sintética del mismo tipo para un nuevo candidato de entrenamiento. No es una rutina genérica de reemplazo de cadenas sin restricciones.

```python
def render_training_candidate(person, email):
    source = f"신청인: {person}\n이메일: {email}"
    entities = [
        {"type": "PERSON", "original": person},
        {"type": "EMAIL", "original": email},
    ]
    target = "\n".join(
        f"{entity['type']}\t{entity['original']}" for entity in entities
    )
    assert all(entity["original"] in source for entity in entities)
    return {"source_text": source, "entities": entities, "target_tsv": target}

base = render_training_candidate("김가상", "synthetic.base@example.com")
variant = render_training_candidate("이샘플", "synthetic.variant@example.com")
assert base["source_text"] != variant["source_text"]
```

En una canalización de aumento de datos real, usa un banco aprobado de entidades de entrenamiento y registra la familia, el elemento principal, la semilla y la versión del operador. Importar a ese banco valores o errores del conjunto reservado puede invalidar la política de separación. Este ejemplo didáctico independiente no es un tercer operador adicional que la CLI anterior ejecute automáticamente.

## 7. Amplía los operadores con comprobaciones explícitas de etiquetas

| Método | Condición de fallo que se busca | Comprobaciones necesarias |
| --- | --- | --- |
| Sustitución del mismo tipo | Nombres/números memorizados | Conservar el tipo y actualizar todas las apariciones/datos de referencia |
| Representación del diseño | Tablas, formularios y narrativas de soporte | Coincidencia entre el orden de los campos y TSV; comprobaciones de campos faltantes |
| OCR/espaciado acotados | Separadores, saltos de línea, formas Unicode | Datos de referencia y límites presentes en el origen transformado |
| Paráfrasis del contexto | Dependencia de una única plantilla de oración | PII añadida/eliminada y coherencia semántica |
| Traducción inversa | Variedad limitada de redacción | Nombres/direcciones/números cambiados y nueva anotación |
| Negativos difíciles | Clasificación errónea de números de documento/importes | Forma superficial similar con contexto distinto |
| Enriquecimiento de tipos poco frecuentes | Escasez de ejemplos de RRN/CARD | Recuentos y diversidad contextual por cada tipo compatible |
| Casos largos/de límite | Truncamiento y omisiones en límites de fragmentos | Longitudes de tokens, desplazamientos, duplicados/límites |
| Instrucciones incrustadas | Seguir el texto de origen como si fueran instrucciones | Tratar el origen como datos; conservar el contrato TSV |

Las paráfrasis y las traducciones inversas pueden conservar errores de anotación que las comprobaciones automatizadas no detecten. La presencia de una cadena en el origen no demuestra que la semántica sea correcta ni que los datos de referencia estén completos. Revisa y aprueba los candidatos antes de incluirlos en el entrenamiento.

## 8. Comprende qué rechaza la auditoría

`--audit-dir` comprueba el contrato de datos generados de este laboratorio:

- Hashes de archivos/manifest y recuentos por partición/idioma/estado negativo.
- IDs duplicados y orígenes exactos normalizados a NFC.
- Pertenencia de familias a particiones y relaciones entre elementos principales y transformaciones.
- Variantes de entrenamiento ubicadas incorrectamente en validation/test.
- Etiquetas permitidas, presencia en el origen y coincidencia entre entidades/TSV.
- Coincidencia con la regeneración determinista a partir de la semilla.

La comprobación final puede rechazar una etiqueta de referencia omitida incluso si se vuelven a calcular los hashes de los archivos. Esto es **una comprobación de reproducibilidad para un ejercicio sintético fijo**, no un validador general de datos de referencia para documentos arbitrarios de clientes. Los hashes no son firmas que autentiquen al productor de los datos.

No cumplir estas condiciones antes del entrenamiento evita atribuir erróneamente más adelante a un problema del modelo lo que en realidad es contaminación de datos. Los casi duplicados, el significado de las anotaciones, las longitudes del tokenizador y la cobertura completa de PII aún requieren comprobaciones independientes.

## 9. Interpreta el corpus histórico de 2,200 registros

[La parte 2](02-pii-data-tokenization.md) conserva el generador 1.0.0, la semilla 42 y los hashes originales de las particiones. La regeneración con CPU realizada en esta revisión reprodujo esos hashes.

La comparación de orígenes completos normalizados a NFC revela estas intersecciones exactas en el corpus histórico:

| Par de particiones | Orígenes NFC compartidos |
| --- | ---: |
| train / validation | 22 |
| train / test | 36 |
| validation / test | 9 |

Hay 51 grupos de origen únicos que abarcan dos o más particiones. Las intersecciones por pares cuentan más de una vez los orígenes presentes en las tres particiones, por lo que su suma no equivale al total de grupos únicos. Esta es una razón concreta para no volver a etiquetar el corpus histórico como un conjunto de evaluación libre de filtraciones.

El nuevo ejercicio no sobrescribe los datos históricos ni publica un rendimiento revisado del modelo. Un conjunto de datos de producción de nueve tipos necesita procedencia de familias/clientes/plantillas y una nueva versión del manifest/evaluación, en lugar de una repartición aleatoria a ciegas de los valores/plantillas antiguos.

## 10. Amplía los datos para crear una versión de entrada de SageMaker

El JSONL del laboratorio incluye campos que usan las funciones auxiliares de prompt/completion existentes de `src.dataset`. El manifest de aumento de datos no sustituye directamente al `dataset-manifest.json` del cargador.

Prepara conjuntamente lo siguiente para una versión de entrenamiento real:

1. Políticas aprobadas de train/validation/test y de anotación/aumento de datos.
2. El manifest de entrada del cargador con recuentos reales y valores SHA-256.
3. Un `config/experiment.yaml` que refleje el tamaño del conjunto de datos, el modelo y el presupuesto de entrenamiento.
4. Un paquete de origen que contenga esa configuración y una configuración de envío local correspondiente.
5. Un entorno de ejecución compatible validado y observaciones de los hashes/recuentos de entrada durante el trabajo.

El empaquetador/cargador actual usa rutas de paquete fijas. Generar el directorio `--output-dir` no conecta automáticamente ese directorio al entrenamiento de SageMaker. Integra y valida una nueva versión del conjunto de datos en una copia de trabajo aparte; después, sigue el [taller de QLoRA](05-qlora-finetuning-workshop.md) y el [contrato de ejecución](03-sagemaker-mlflow-execution.md).

Compara el entrenamiento original con el aumentado usando el mismo conjunto de validation, la misma decodificación y el mismo presupuesto de comparación. La misma cantidad de pasos aún puede exponer cantidades distintas de ejemplos o tokens cuando cambia el tamaño/la longitud de los datos; registra también los presupuestos de ejemplos/tokens.

## Comprueba lo que has aprendido

1. ¿Por qué es arriesgado dividir después del aumento de datos? **Las variantes de un mismo origen pueden quedar a ambos lados de los límites entre entrenamiento y conjuntos reservados.**
2. ¿Un ID nuevo elimina la filtración entre clientes? **No; comprueba la procedencia del cliente y del origen.**
3. ¿Se puede cambiar un nombre y dejar el TSV intacto? **No; el origen y los datos de referencia deben cambiar juntos.**
4. ¿Demuestra este laboratorio el rendimiento con plantillas no vistas? **No; se comparten plantillas y no se evalúa ningún modelo.**
5. ¿Qué ocurre si un mayor aumento de datos perjudica la calidad? **Examina las etiquetas, los duplicados, los cambios de distribución y los presupuestos de entrenamiento; compara los resultados en validation.**

## Referencias

- [Separación entre entrenamiento y prueba y filtración durante el preprocesamiento](https://scikit-learn.org/stable/common_pitfalls.html)
- [Validación cruzada agrupada](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Dai y Adel: aumento de datos para NER](https://aclanthology.org/2020.coling-main.343/)
- [CheckList: pruebas de comportamiento de modelos de NLP](https://aclanthology.org/2020.acl-main.442/)
- [Datos históricos e implementación de reemplazo](02-pii-data-tokenization.md)

Siguiente: [Entrenamiento de QLoRA](05-qlora-finetuning-workshop.md) · [Evaluación y enmascaramiento](07-pii-evaluation-release.md)

[Cuestionario del taller](../../quizzes/ai-ml/sagemaker-ai/06-data-augmentation-workshop-quiz.md)
