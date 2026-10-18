# Taller: ajuste fino de QLoRA para la extracción de PII

> **Última actualización**: September 16, 2026

Las fuentes primarias se revisaron el 15 de septiembre de 2026.

El objetivo de este taller es explicar un experimento sobre el que se pueda razonar: qué predice el modelo, qué parámetros cambian, qué significa un paso de entrenamiento y qué evidencia justificaría conservar el adaptador resultante. Un Training Job completado es solo una parte de ese experimento.

Seguimos el [entrenador de Qwen para PII](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/train.py) del repositorio, con documentos sintéticos. Mantén a mano los [contratos de envío, propiedad, exportación y limpieza de la Parte 3](03-sagemaker-mlflow-execution.md) junto con este capítulo. Continúa con el [taller de aumento de datos](06-data-augmentation-workshop.md) y el [taller de evaluación y lanzamiento de PII](07-pii-evaluation-release.md).

**Estado de ejecución:** la ruta histórica `src/train.py` que se explica en este capítulo se detiene intencionalmente porque el DLC de PyTorch 2.8 llegó al fin de las actualizaciones de parches el 6 de agosto de 2026. Conserva intacto `src/runtime_contract.py`. Los ejercicios de CPU que aparecen a continuación no cargan pesos del modelo; los fragmentos de entrenamiento explican esa implementación fijada. Una ruta aparte con PyTorch 2.11 completó entrenamiento de prueba real en GPU y verificación de guardado y recarga el 16 de septiembre de 2026. El [registro de ejecución de la ruta de aprendizaje](README.md#sagemaker-execution-readiness) explica su pequeña muestra de validación y el envío del trabajo completo. No interpretes los fragmentos históricos que aparecen a continuación como evidencia de que la nueva ruta de ejecución tuvo éxito.

## 1. Define la predicción antes de elegir el método de entrenamiento

Considera este documento totalmente sintético:

```text
Synthetic contact Alex Example; email alex@example.com.
```

La respuesta deseada del modelo es una lista de entidades copiadas de ese documento:

```text
PERSON	Alex Example
EMAIL	alex@example.com
```

El modelo aprende **extracción estructurada**, no a reescribir todo el documento. El contrato de salida consiste en cero o más líneas `TYPE<TAB>ORIGINAL`. Los tipos permitidos son `PERSON`, `RRN`, `DOB`, `REL`, `ADDRESS`, `PHONE`, `EMAIL`, `ACCOUNT` y `CARD`. Una respuesta como «Encontré una persona y un correo electrónico» no es el formato de salida requerido, aunque su significado sea correcto.

Después de la extracción, el código determinista valida los tipos y las coincidencias con el texto de origen, y reemplaza los fragmentos seleccionados por tokens como `[PERSON_1]`. Esta separación permite observar los errores. Una entidad no detectada es un error de extracción; un límite de reemplazo incorrecto es un error de reemplazo; una respuesta con formato incorrecto es un error de formato. Reducirlo todo a «el LLM enmascara el documento» oculta estas distinciones.

### Ejercicio de CPU: de la salida de extracción a tokens reversibles

Ejecuta desde `examples/ai-ml/qwen-pii-finetuning` en el entorno Python 3.12 del paquete. Esto usa funciones auxiliares locales existentes y cadenas sintéticas; no llama a un modelo ni a AWS.

```python
from src.pii_tokens import parse_tsv, pseudonymize_text, reassemble_text

source = "Synthetic contact Alex Example; email alex@example.com."
completion = "PERSON\tAlex Example\nEMAIL\talex@example.com"

entities = parse_tsv(completion, source)
result = pseudonymize_text(source, entities)

assert result.masked_text == (
    "Synthetic contact [PERSON_1]; email [EMAIL_1]."
)
assert reassemble_text(result.masked_text, result.mapping) == source
print(result.masked_text)
```

El mapeo hace que esto sea **seudonimización reversible**. No la llames eliminación irreversible ni prueba de anonimización. En un flujo de trabajo real, el texto de origen, el mapeo, las predicciones sin procesar y el adaptador entrenado necesitan controles de acceso y retención adecuados. Una prueba de ida y vuelta verifica la reversibilidad; incluso no reemplazar nada puede superar esa prueba.

La función actual `parse_tsv()` es deliberadamente tolerante: puede descartar filas con formato incorrecto y conservar las válidas. `train.py` puede contar una respuesta vacía como analizable porque los documentos sin entidades son entradas válidas. Por lo tanto, «análisis correcto» por sí solo no demuestra una extracción correcta. El taller de evaluación de PII distingue entre la validez estricta del formato, la recuperación de entidades y la PII residual.

### Elige una referencia que se ajuste al problema

| Método | Primer experimento útil | Lo que no resuelve automáticamente |
|---|---|---|
| Expresiones regulares y reglas deterministas | Formatos estables de teléfono/correo electrónico y reglas de reemplazo exactas | Nombres dependientes del contexto, relaciones, variaciones de OCR y números ambiguos |
| Modelo de clasificación de tokens/NER | Etiquetas de fragmentos con una taxonomía de entidades estable | Cobertura de nuevos dominios, calidad de las anotaciones y política de reemplazo posterior |
| Generación solo con prompts | Establecer el comportamiento de extracción y TSV del modelo base | Formato fiable, recuperación completa o inmunidad a instrucciones dentro de los documentos |
| LoRA | Adaptar un modelo preentrenado con actualizaciones entrenables de bajo rango | Reducir el almacenamiento del modelo base sin cuantizar |
| QLoRA | Entrenar adaptadores a través de una base cuantizada y congelada cuando la memoria es limitada | Hacer que las activaciones, el estado del optimizador o todos los tensores del modelo sean de cuatro bits |

Empieza con una referencia determinista y otra basada solo en prompts. Si el modelo con prompts es adecuado para una tarea acotada, el entrenamiento podría añadir complejidad sin suficiente beneficio. Si no detecta entidades específicas del dominio o infringe repetidamente el contrato de salida, un experimento de adaptación supervisada tiene un propósito más claro.

## 2. Comprende qué cambia LoRA

Para una capa lineal con ancho de entrada `d_in` y ancho de salida `d_out`, considera que:

- `W` tiene forma `(d_out, d_in)`;
- `A` tiene forma `(r, d_in)`;
- `B` tiene forma `(d_out, r)`.

LoRA estándar usa:

```text
W_effective = W + (alpha / r) * B @ A
y = W @ x + (alpha / r) * B @ A @ x
```

La matriz base `W` está congelada. El optimizador actualiza `A` y `B`, que contienen `r × (d_in + d_out)` parámetros en lugar de `d_in × d_out`. Los gradientes siguen propagándose a través del cálculo que involucra al modelo base; «congelado» no significa que el modelo base esté ausente del cálculo hacia delante o hacia atrás. Consulta el [artículo de LoRA](https://arxiv.org/abs/2106.09685).

Para una proyección `2048 → 768` con rango 16:

```python
d_in, d_out, rank, alpha = 2048, 768, 16, 32
base_parameters = d_in * d_out
adapter_parameters = rank * (d_in + d_out)

assert base_parameters == 1_572_864
assert adapter_parameters == 45_056
assert alpha / rank == 2
print(base_parameters, adapter_parameters, alpha / rank)
```

El rango controla la capacidad de la actualización, no el número de épocas de entrenamiento. `lora_alpha` controla la escala; con esta configuración, `alpha/r` es 2. Aumentar el rango sin tener en cuenta alpha también cambia esa escala. La opción LoRA de rango estabilizado de PEFT usa una regla de escala distinta; la configuración confirmada no la activa.

En la [inicialización predeterminada de PEFT 0.17.1](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md), el adaptador inicialmente no modifica la salida porque `B` empieza en cero. No exijas que todos los tensores del adaptador tengan un gradiente distinto de cero en la primera pasada hacia atrás. En un modelo MoE, es posible que un lote tampoco seleccione algunos expertos. Un diagnóstico útil comprueba que los gradientes presentes sean finitos y que los parámetros esperados del adaptador cambien después de un paso del optimizador.

## 3. Calcula el presupuesto de memoria de QLoRA más allá de los pesos de cuatro bits

El [artículo de QLoRA](https://arxiv.org/abs/2305.14314) combina una base cuantizada y congelada con adaptadores entrenables. Las siguientes opciones del entrenador confirmado representan decisiones diferentes:

| Opción o categoría de memoria | Significado en este ejemplo |
|---|---|
| `load_in_4bit=True` | Cargar los pesos lineales compatibles de la base con cuantización de cuatro bits |
| `bnb_4bit_quant_type="nf4"` | Usar NormalFloat4, diseñado para pesos con distribución normal |
| `bnb_4bit_use_double_quant=True` | Cuantizar las constantes de cuantización para reducir el almacenamiento adicional |
| `bnb_4bit_compute_dtype=torch.bfloat16` | Usar cálculo BF16 para la ruta lineal cuantizada; no aritmética de cuatro bits en todas partes |
| Parámetros y gradientes de LoRA | Tensores entrenables con sus propios tipos de datos y requisitos de memoria |
| Estado del optimizador | Estado adicional para los parámetros entrenables; NF4 no lo convierte automáticamente a ocho bits |
| Activaciones y tensores temporales | Dependen de la longitud de secuencia, el microbatch, la implementación de atención y el checkpointing |
| Módulos sin cuantizar | Las incrustaciones, la normalización y otros tensores pueden usar mayor precisión |

La doble cuantización no significa «cuantizar el modelo a dos bits». BF16 no garantiza que todos los tensores ocupen dos bytes: la preparación para k-bit y el manejo de adaptadores pueden conservar algunos tensores en FP32 o elevarlos a ese tipo. Inspecciona los tipos de datos y los parámetros entrenables reales en lugar de inferir toda la huella de memoria a partir de un solo campo de configuración. La [guía versionada de bitsandbytes](https://github.com/huggingface/transformers/blob/v4.57.6/docs/source/en/quantization/bitsandbytes.md) explica por separado NF4, el tipo de datos de cálculo y la cuantización anidada.

El checkpointing de gradientes ahorra las activaciones seleccionadas y las vuelve a calcular durante la propagación hacia atrás. Intercambia cálculo por memoria. La acumulación de gradientes combina varios microbatches antes de una actualización del optimizador; no exige almacenar simultáneamente los grafos de activación de todos esos microbatches. Ninguna de las dos funciones elimina el estado del optimizador.

### Los parámetros totales y los parámetros activos de MoE son presupuestos distintos

La [ficha del modelo Qwen](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507) describe **30.5B parámetros totales y 3.3B parámetros activados**, con 48 capas, 128 expertos y 8 expertos seleccionados por token. Los parámetros activados describen el cálculo disperso de un token. No significan que solo haya que cargar 3.3B parámetros.

Un cálculo idealizado de `30.5 billion × 4 bits` da **15.25 GB decimales**. Es una ilustración del límite inferior para el almacenamiento de pesos, no una predicción del uso de memoria de la GPU. Excluye metadatos de cuantización, tensores sin cuantizar, adaptadores, gradientes, estado del optimizador, activaciones y sobrecarga de asignación. No puede demostrar que quepa en una instancia específica con una sola GPU.

## 4. Inspecciona los objetivos de adaptador de este modelo

El paquete histórico fija estas versiones relevantes:

| Paquete | Versión fijada |
|---|---|
| PyTorch | `2.8.0` |
| Transformers | `4.57.6` |
| PEFT | `0.17.1` |
| TRL | `0.24.0` |
| bitsandbytes | `0.48.2` |
| Accelerate | `1.10.1` |
| datasets | `3.6.0` |

En la [implementación fijada de Qwen3 MoE](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py), los expertos son una `ModuleList` de módulos con capas lineales `gate_proj`, `up_proj` y `down_proj`. La atención usa `q_proj`, `k_proj`, `v_proj` y `o_proj`. La compuerta de enrutamiento tiene el nombre independiente `gate`.

La `LoraConfig` confirmada tiene como objetivos esos siete sufijos de proyección. **No** tiene como objetivo el enrutador solo porque `gate_proj` contenga la palabra «gate». A la inversa, sustituir la lista por `"all-linear"` puede incluir módulos lineales adicionales, incluido el enrutador. Eso sería otro experimento.

```python
# Inspection hook after an authorized model load, before adapter insertion.
from collections import Counter

targets = {
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
}
matched = [
    name for name, module in model.named_modules()
    if name.rsplit(".", 1)[-1] in targets
]
counts = Counter(name.rsplit(".", 1)[-1] for name in matched)
assert set(counts) == targets
assert not any(name.endswith(".gate") for name in matched)
print(dict(sorted(counts.items())))  # Module names/counts, not training data.
```

Para la configuración de modelo publicada, el cálculo a partir del código fuente con rango 16 da aproximadamente **13.37 millones** de parámetros de adaptador para las cuatro proyecciones de atención, más **830.47 millones** para las tres proyecciones de cada experto: **843,841,536** en total. Es un cálculo basado en las dimensiones del modelo, no un resultado medido en GPU. Confirma el resultado real después de insertar el adaptador con `trainer.model.print_trainable_parameters()`.

Puedes reproducir el recuento sin importar un modelo. La [configuración del modelo](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json) indica un tamaño oculto de 2,048, una dimensión de cabeza de 128, 32 cabezas de consulta, 4 cabezas de clave/valor y un tamaño intermedio de experto de 768. Por lo tanto, Q proyecta `2048 → 4096`, K/V proyectan cada una `2048 → 512` y O proyecta `4096 → 2048`. Cada experto tiene dos proyecciones `2048 → 768` y una proyección `768 → 2048`.

```python
# CPU arithmetic from this model/version's configuration; not a GPU benchmark.
layers, experts, rank = 48, 128, 16
hidden, head_dim, q_heads, kv_heads = 2048, 128, 32, 4
expert_hidden = 768
q_width, kv_width = q_heads * head_dim, kv_heads * head_dim

attention = layers * rank * (
    (hidden + q_width)
    + 2 * (hidden + kv_width)
    + (q_width + hidden)
)
expert_adapters = layers * experts * 3 * rank * (hidden + expert_hidden)
total = attention + expert_adapters

assert attention == 13_369_344
assert expert_adapters == 830_472_192
assert total == 843_841_536
assert layers * (4 + 3 * experts) == 18_624  # Targeted linear modules.
print(attention, expert_adapters, total)
```

Este recuento presupone la estructura de expertos del modelo publicado de 48 capas y los siete sufijos de destino anteriores, sin módulos entrenables ni sesgos adicionales. Es una expectativa que se debe comparar con el inventario real del adaptador, no un sustituto de ese inventario.

Esto explica por qué «LoRA usa pocos parámetros» es una recomendación incompleta para una lista grande de objetivos MoE. Comparar objetivos solo de atención con objetivos de atención más expertos puede ser un experimento controlado útil, pero cambiar los objetivos requiere una modificación didáctica: la lista de objetivos del entrenador actual está codificada directamente.

Algunas implementaciones MoE más recientes o diferentes usan tensores `nn.Parameter` de dos o tres dimensiones en bruto, en lugar de expertos `nn.Linear`. [PEFT 0.17.1 documenta `target_parameters`](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md) para ese caso, incluidas sus limitaciones relacionadas con el eje de expertos y con varios adaptadores. Inspecciona la implementación y la versión del modelo elegido; no copies una receta de selección de parámetros en esta implementación basada en módulos.

## 5. Sigue un registro por el formato de chat y la máscara de pérdida

El [cargador de datos real](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/src/dataset.py) devuelve datos conversacionales de **prompt/respuesta**:

```python
from src.dataset import SYSTEM_INSTRUCTION

record = {
    "source_text": "Synthetic contact Alex Example.",
    "target_tsv": "PERSON\tAlex Example",
}
row = {
    "prompt": [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": record["source_text"]},
    ],
    "completion": [
        {"role": "assistant", "content": record["target_tsv"]},
    ],
}
assert row["completion"][0]["role"] == "assistant"
```

La función `format_training_text()` no utilizada en `train.py` produce texto `### Instruction`. **No** es la ruta de datos actual. No enseñes ese formato de cadena como si fuera lo que realmente recibe `SFTTrainer`.

En [TRL 0.24.0](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer), el entrenador aplica la plantilla de chat del tokenizador al prompt y a la combinación de prompt y respuesta. Crea una máscara de respuesta a partir de ese límite. Con `completion_only_loss=True`, las posiciones del prompt reciben la etiqueta `-100`; las posiciones de la respuesta contribuyen a la pérdida del modelo de lenguaje causal. El padding también se ignora.

### Un objetivo de extracción vacío no es una señal de entrenamiento vacía

Un documento sin entidades objetivo usa una cadena de contenido vacía para el asistente. Aun así, la respuesta debe terminar el turno del asistente. Para este modelo, la [configuración del tokenizador](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/tokenizer_config.json) usa `<|im_end|>` como EOS y `<|endoftext|>` como padding.

```python
# CPU-only illustration of a mask, not actual tokenizer output.
input_ids = [101, 102, 103, 104, 151645]
completion_mask = [0, 0, 0, 0, 1]
labels = [
    token if keep else -100
    for token, keep in zip(input_ids, completion_mask)
]
assert labels == [-100, -100, -100, -100, 151645]
assert sum(label != -100 for label in labels) == 1
```

El ejemplo ilustra la supervisión de EOS para un registro negativo. La plantilla real puede incluir tokens de respuesta adicionales, como un salto de línea. Verifica la fila real tokenizada; no des por hecho que los ID de prompt ilustrativos o la longitud de respuesta son fijos.

La ficha del modelo Instruct-2507 indica que es **no pensante** y que no requiere `enable_thinking=False`. El código de predicción actual pasa ese argumento, pero no convierte este checkpoint en un modelo de razonamiento. `assistant_only_loss=True` es una opción distinta que requiere compatibilidad adecuada con la máscara del asistente por parte de la plantilla; no es necesaria para este contrato de prompt/respuesta de una sola respuesta.

### Inspecciona los datos preparados antes del primer paso de entrenamiento

El siguiente punto de inspección se usa después de construir un entrenador en un entorno autorizado y compatible. Comprueba los recuentos y las máscaras sin imprimir el texto de origen ni las etiquetas decodificadas.

```python
# Instructional inspection hook; not currently present in src/train.py.
prepared = trainer.train_dataset
for example in prepared:
    mask = example["completion_mask"]
    assert len(mask) == len(example["input_ids"])
    assert any(mask), "No supervised completion survived preprocessing"

examples = [prepared[i] for i in range(min(4, len(prepared)))]
batch = trainer.data_collator(examples)
supervised = (batch["labels"] != -100).sum(dim=1)
assert bool((supervised > 0).all())
if "attention_mask" in batch:
    padding = batch["attention_mask"] == 0
    assert bool((batch["labels"][padding] == -100).all())
print({"examples": len(examples), "target_tokens": supervised.tolist()})
```

Inspecciona también las longitudes de prompt más respuesta antes del truncamiento y confirma que se conserve el EOS de la respuesta. `max_length=1024` se aplica a la secuencia de entrenamiento combinada, no solo al documento. Un prompt largo puede consumir todo el presupuesto y eliminar la respuesta. El truncamiento en inferencia también puede ocultar PII mientras la evaluación sigue esperando entidades del documento completo.

Elige una política documentada: rechazar los casos que excedan el límite, acortar solo las instrucciones no esenciales del prompt o dividir la fuente en fragmentos actualizando el contrato de anotación. Mantén los fragmentos y los descendientes del aumento de datos en la misma familia de documentos y partición. No aumentes simplemente la longitud de secuencia sin volver a evaluar la memoria de activaciones, el microbatch y la longitud de salida en inferencia.

## 6. Lee la configuración de entrenamiento fijada siguiendo el orden de ejecución

Lo siguiente es un **fragmento para leer código**, no una instrucción para iniciar el entorno de GPU bloqueado. Los nombres y argumentos corresponden a PEFT 0.17.1, Transformers 4.57.6 y TRL 0.24.0.

Primero localiza estas etapas en `run_training()`:

| Orden | Qué hace el punto de entrada confirmado |
|---|---|
| 1 | Ejecuta la comprobación de compatibilidad antes de importar la pila de entrenamiento |
| 2 | Resuelve la configuración y la semilla, prepara MLflow y lee los archivos del conjunto de datos |
| 3 | Carga el modelo/tokenizador cuantizados y evalúa la referencia con test |
| 4 | Prepara el entrenamiento k-bit y construye el adaptador y los conjuntos de datos conversacionales |
| 5 | Entrena, con evaluación intermedia en validación |
| 6 | Guarda la salida del modelo y registra los archivos finales del adaptador |
| 7 | Evalúa el modelo ajustado con test y escribe resultados agregados |

El acceso a test en las etapas 3 y 7 es el comportamiento actual, no el flujo de trabajo recomendado para seleccionar candidatos de la sección 8.

```python
import torch
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import BitsAndBytesConfig

quantization = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

# `model` has already been loaded by the reviewed loading path.
model.config.use_cache = False
model = prepare_model_for_kbit_training(
    model, use_gradient_checkpointing=True
)
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
)
```

El cargador confirmado usa `AutoModelForCausalLM.from_pretrained(..., quantization_config=..., device_map="auto", torch_dtype=torch.bfloat16)`. Hay que inspeccionar la colocación automática; la descarga a CPU o disco no sustituye demostrar que la colocación de entrenamiento sea válida. Un experimento propuesto con una sola GPU puede usar una colocación explícita después de confirmar que cabe en memoria. Este capítulo no cambia el cargador.

El código actual también establece `output_router_logits=True`. En la implementación MoE fijada, la pérdida auxiliar del enrutador puede contribuir a la pérdida informada. Eso no convierte al enrutador en un objetivo de LoRA. Registra esta decisión al comparar ejecuciones.

```python
from trl import SFTConfig, SFTTrainer

sft_args = SFTConfig(
    output_dir=str(output_dir / "checkpoints"),
    max_steps=80,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=0.0002,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=1,
    eval_strategy="steps",
    eval_steps=20,
    save_strategy="steps",
    save_steps=80,
    save_total_limit=1,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    max_length=1024,
    packing=False,
    completion_only_loss=True,
    report_to="none",
    seed=42,
    data_seed=42,
)
trainer = SFTTrainer(
    model=model,
    args=sft_args,
    train_dataset=train_dataset,
    eval_dataset=validation_dataset,
    processing_class=tokenizer,
    peft_config=lora_config,
)
```

Este fragmento muestra los valores configurados para una **ejecución completa** y presupone que ya existen el modelo, el tokenizador, los conjuntos de datos y el directorio de salida. Muestra intencionalmente `max_length` y `processing_class`; no los sustituyas por ejemplos antiguos de `max_seq_length`/`tokenizer` sin comprobar la versión. El `SFTConfig` fijado no tiene un campo `chat_template_kwargs` en su configuración. La versión 0.24.0 admite argumentos de plantilla por ejemplo.

El tokenizador real ya tiene el EOS adecuado. Este SFTConfig permite declarar explícitamente `eos_token="<|im_end|>"` si la lección quiere hacer visible ese contrato, pero omitirlo aquí no demuestra que el EOS actual del tokenizador sea incorrecto.

`config/experiment.yaml` contiene `quantization`, `double_quant` y `compute_dtype`, pero el cargador codifica actualmente NF4, doble cuantización y BF16. Cambiar solo esos valores de YAML no implementa un estudio de ablación. Mantén esos valores fijos y explica ese hecho, o realiza una modificación didáctica revisada por separado que conecte realmente la opción con el cargador.

### De la optimización a una extracción generada

Después de que se superen los requisitos previos y los puntos de inspección en un entorno de GPU validado, la secuencia confirmada llama a `trainer.train()`, guarda la salida del modelo y evalúa el modelo ajustado. El siguiente fragmento muestra esos límites; no es un ejercicio de CPU.

```python
# Code-reading excerpt: assumes an approved, constructed GPU trainer.
train_result = trainer.train()
trainer.save_model(str(output_dir))
trainer.model.config.use_cache = True
```

Para la generación, el prompt debe terminar en el prefijo de generación del asistente; no incluyas la respuesta de referencia. Elimina los tokens del prompt de los ID generados antes de analizar la respuesta. Este es un diagnóstico propuesto para un solo registro con `row` y `record` sintéticos definidos anteriormente:

```python
# Instructional inference hook; not a replacement for the committed CLI.
trainer.model.eval()
prompt = tokenizer.apply_chat_template(
    row["prompt"], tokenize=False, add_generation_prompt=True
)
inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
prompt_length = inputs["input_ids"].shape[1]
if prompt_length > 1024:
    raise ValueError("Apply the reviewed long-document policy first")
inputs = inputs.to(trainer.model.device)

with torch.inference_mode():
    generated = trainer.model.generate(
        **inputs,
        do_sample=False,
        max_new_tokens=512,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
completion = tokenizer.decode(
    generated[0, prompt_length:], skip_special_tokens=True
)
entities = parse_tsv(completion, record["source_text"])
# Evaluate aggregate metrics; do not log raw completions from real documents.
```

El `_predict_records()` actual agrupa ejemplos con padding a la izquierda y activa el truncamiento. En cambio, el punto de inspección anterior rechaza un prompt individual demasiado largo para hacer visible el límite didáctico. Su límite de 512 tokens de salida es independiente: una respuesta TSV larga aún puede quedar truncada. Comprueba la terminación y el formato de la respuesta, además de la longitud del prompt.

## 7. Cuenta ejemplos, actualizaciones del optimizador y épocas

Para el entrenamiento paralelo de datos habitual:

```text
effective batch ≈ microbatch per device × accumulation × data-parallel workers
```

En el ejemplo confirmado con una sola instancia y una sola GPU, el cálculo es `1 × 8 × 1 = 8`. La acumulación de gradientes de ocho significa que una actualización del optimizador ocurre después de ocho microbatches. No significa que cada microbatch contenga ocho ejemplos.

```python
from math import ceil

records = 1600
microbatch, accumulation, workers = 1, 8, 1
effective_batch = microbatch * accumulation * workers
updates_per_epoch = ceil(records / effective_batch)

assert effective_batch == 8
assert updates_per_epoch == 200
assert 10 * effective_batch == 80
assert 80 * effective_batch == 640
assert 80 / updates_per_epoch == 0.4
```

Por lo tanto, la ejecución de prueba configurada tiene 10 actualizaciones del optimizador, unas 80 presentaciones de ejemplos. La ejecución «completa» tiene 80 actualizaciones, unas 640 presentaciones o 0.4 de una época con 1,600 registros bajo estos supuestos divisibles y sin empaquetado. «Completa» es una etiqueta de modo, no una afirmación de convergencia ni de que se complete una época entera.

`max_steps` determina el presupuesto de actualizaciones. Con longitudes de secuencia variables, el mismo número de pasos no implica la misma cantidad de tokens supervisados ni de cálculo. Al comparar un contexto más largo o un conjunto de datos aumentado, registra los ejemplos y los tokens objetivo procesados, no solo el tiempo transcurrido y la pérdida. Los últimos lotes distribuidos y el empaquetado requieren cálculos adicionales; no forman parte de las operaciones aritméticas anteriores.

## 8. Separa un diagnóstico de sobreajuste diminuto de la selección del modelo

Antes de invertir el presupuesto de un entrenamiento completo, define un diagnóstico propuesto con 8–16 registros de **entrenamiento**. Incluye un ejemplo positivo sencillo, entidades repetidas, variación de formato y un ejemplo sin PII. Mantén este subconjunto separado de la validación y del test bloqueado.

Después de migrar el entorno de ejecución, sigue esta secuencia de comprobaciones: el modelo se carga; las máscaras de prompt/respuesta son correctas; un paso de propagación hacia delante y hacia atrás produce valores finitos; los parámetros esperados del adaptador cambian; el subconjunto pequeño resulta más fácil de ajustar; el adaptador guardado se recarga con el mismo modelo base y reproduce una decodificación determinista.

Por ejemplo, ocho registros con un lote efectivo de ocho y 20 actualizaciones del optimizador producen unas 20 pasadas por ese subconjunto diminuto. Es un presupuesto de diagnóstico deliberado, no una recomendación para el conjunto de datos completo. Compara la extracción exacta en esos ocho registros e inspecciona la terminación del registro negativo; una pérdida menor por sí sola no es el criterio de aceptación.

Esta es intencionalmente una comprobación de sobreajuste. Tener éxito indica que la ruta de entrenamiento puede aprender estos ejemplos. No demuestra generalización, recuperación de producción ni eliminación de toda la PII. El fracaso es útil: corrige las máscaras, los objetivos, la correspondencia de datos o la optimización antes de aumentar el tamaño del modelo o del conjunto de datos.

### Por qué el entrenador actual no es un ciclo de HPO seguro

El entrenador confirmado lee el archivo de test y lo evalúa **antes y después de cada ejecución**, incluida la prueba. Usa validación para la evaluación intermedia del entrenador, pero calcula las métricas finales de referencia y del modelo ajustado con test cada vez. No inspecciones repetidamente esos resultados de test mientras eliges hiperparámetros.

Para un flujo de trabajo didáctico de ajuste, realiza una modificación claramente identificada que use un subconjunto de prueba para los diagnósticos de ejecución y la validación para comparar candidatos. Mantén test inaccesible para las ejecuciones habituales de ajuste, fija la configuración elegida y solo entonces realiza una comparación final entre la referencia y el candidato con test. Esto se explica con más detalle en el [taller de evaluación y lanzamiento de PII](07-pii-evaluation-release.md).

| Experimento | Mantener fijo | Cambiar deliberadamente | Elegir usando validación |
|---|---|---|---|
| Capacidad del adaptador | Datos, objetivos, tasa de aprendizaje, presupuesto de tokens | Rango, por ejemplo 8 frente a 16, indicando la política de escala | Recuperación, PII residual, enmascaramiento excesivo y estabilidad del entrenamiento |
| Alcance de los objetivos | Datos, rango, decodificación y presupuesto | Solo atención frente a los objetivos actuales de atención más expertos | Beneficio en calidad en relación con los parámetros entrenables y la memoria medida |
| Optimización | Datos, objetivos, rango, política de secuencia | Una opción de tasa de aprendizaje a la vez | Trayectoria de pérdida y métricas de extracción, no solo la pérdida |
| Política de secuencia | Registros de evaluación y contrato de etiquetas | Política de rechazo/división en fragmentos o un presupuesto de tokens mayor justificado | Cobertura de documentos largos y tasa de truncamiento |
| Aumento de datos | Familias originales y conjuntos de evaluación | Una familia de transformaciones solo para entrenamiento | Comportamiento con tipos infrecuentes, variaciones de formato y ejemplos negativos |

Estas filas describen un diseño experimental, no opciones implementadas de la CLI ni valores ganadores recomendados. Los descendientes del aumento de datos deben permanecer con su familia de origen. La separación por familias no garantiza automáticamente la separación exacta de texto, entidades, plantillas o dominios; el [taller de aumento de datos](06-data-augmentation-workshop.md) hace explícitas esas auditorías.

El ejercicio de CPU del taller de aumento de datos usa un conjunto de datos distinto. Los cálculos de 1,600 registros aquí describen la configuración histórica de entrenamiento; no reutilices silenciosamente esos recuentos para la nueva salida del laboratorio.

## 9. Relaciona el experimento con SageMaker AI

Usa el [lanzador real](https://github.com/Atom-oh/kubernetes-docs/blob/b89fc1d3334717031227a00a894a8c0927986ba3/examples/ai-ml/qwen-pii-finetuning/launch/sagemaker_train.py) para conectar los conceptos locales con las entradas y salidas del trabajo.

| Paso | Correspondencia actual | Evidencia que inspeccionar |
|---|---|---|
| Configuración local | `config/experiment.yaml` más `requirements.lock` | Versiones de configuración, código fuente y dependencias |
| Paquete de código fuente | `generated/source.tar.gz` contiene código fuente/configuración/requisitos | Inventario del paquete y SHA-256; no incluir recursivamente credenciales/datos |
| Entradas de S3 | Prefijos separados `source/` y `dataset/` para el experimento | Hashes de objetos cargados y cuenta/bucket/prefijo previstos |
| Código fuente dentro del trabajo | `/opt/ml/code/config/experiment.yaml`; `SAGEMAKER_PROGRAM=src/train.py` | Invocación del toolkit y existencia de la configuración |
| Canal del conjunto de datos | Un canal de modo File llamado `dataset` | `/opt/ml/input/data/dataset/{train,validation,test}.jsonl` y manifiesto |
| Evaluación del entrenador | Conjunto de validación durante el entrenamiento; las comparaciones finales actuales usan test | ID/hash reales de las particiones y la distinción anterior |
| MLflow | Archivos de configuración/versión/manifiesto, métricas agregadas y archivos finales del adaptador | Identidad de la ejecución, disponibilidad de artefactos y compatibilidad entre cliente y aplicación |
| Salida del modelo de SageMaker | `output-dir=/opt/ml/model` actual | Contenido del directorio final y URI del artefacto del modelo en S3 |

Los nombres de los canales determinan las rutas de entrada. Tener un canal llamado `dataset` no convierte todo su contenido en «datos de entrenamiento»: este canal contiene tres particiones distintas. Vuelve a calcular y comparar los hashes de archivo observados antes de aprender con ellos; registrar un manifiesto no demuestra que los archivos cargados coincidieran con él.

### Comprende qué se guarda

El directorio de salida actual de SFT es `/opt/ml/model/checkpoints`, porque los checkpoints se ubican dentro de `output_dir`. SageMaker empaqueta el directorio del modelo para cargarlo, así que el artefacto del modelo resultante puede incluir esos checkpoints, además del adaptador final y los archivos JSON. La lista de permitidos de archivos de adaptador explícitos de MLflow no cambia el empaquetado del directorio de SageMaker.

Para una estructura más limpia propuesta, separa los archivos finales del adaptador bajo `/opt/ml/model`, las salidas agregadas bajo `/opt/ml/output/data` y los checkpoints recuperables bajo `/opt/ml/checkpoints`. La sincronización de checkpoints con S3 requiere la configuración de trabajo adecuada; crear un directorio local no constituye por sí solo una copia de respaldo. Consulta la [tabla de rutas de almacenamiento de AWS](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html) y el [contrato de salida de entrenamiento](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html).

Un adaptador no es un sustituto autónomo del modelo base. Para volver a cargarlo se necesitan el modelo/revisión base correctos, el tokenizador, la configuración del adaptador y un entorno de ejecución compatible. El código actual no fija una revisión del modelo; registra una en una mejora de reproducibilidad revisada por separado.

## 10. Diagnostica la etapa del trabajo antes de cambiar los hiperparámetros

El estado de SageMaker y los diagnósticos de las etapas del modelo responden preguntas distintas. `SecondaryStatus` puede indicar descarga, entrenamiento o carga; un trabajo puede seguir en estado `Training` mientras la aplicación carga pesos, evalúa una referencia o guarda un adaptador.

El siguiente comando es un diagnóstico de solo lectura para un **trabajo autorizado existente**, no un comando que se ejecute en este taller:

```bash
: "${TRAINING_JOB_NAME:?Set the existing reviewed job name}"
: "${AWS_REGION:?Set its Region}"
aws sagemaker describe-training-job \
  --region "$AWS_REGION" \
  --training-job-name "$TRAINING_JOB_NAME" \
  --query '{
    status:TrainingJobStatus,
    phase:SecondaryStatus,
    stages:SecondaryStatusTransitions,
    failure:FailureReason,
    model:ModelArtifacts.S3ModelArtifacts,
    trainingSeconds:TrainingTimeInSeconds,
    billableSeconds:BillableTimeInSeconds
  }'
```

Mantén privados los detalles de los fallos hasta que se revisen. Usa los flujos del trabajo en `/aws/sagemaker/TrainingJobs` y ventanas de registro acotadas, no un volcado de trabajos no relacionados ni ejemplos de entrenamiento. AWS documenta las [transiciones de estado secundario](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_SecondaryStatusTransition.html) y el [registro en CloudWatch](https://docs.aws.amazon.com/sagemaker/latest/dg/logging-cloudwatch.html).

Añade marcadores de etapa con datos solo agregados a una futura versión didáctica del entrenador: datos validados, modelo cargado, referencia completada, adaptadores insertados, primera pasada hacia atrás completada, optimización completada, artefactos guardados y evaluación completada. Estos marcadores permiten diagnosticar un bloqueo sin registrar documentos de origen.

| Síntoma | Primera distinción que se debe hacer | Siguiente acción útil |
|---|---|---|
| Fallo antes de cargar el modelo | Comprobación del entorno, fallo del paquete/toolkit o ruta inexistente | Lee la etapa y la correspondencia exacta de configuración/canales; no ajustes el rango |
| Falta de memoria al cargar | Pesos/colocación de la base frente a memoria del optimizador | Comprueba el tamaño total del modelo, la cuantización, los tensores sin cuantizar y la colocación real |
| Falta de memoria durante la propagación hacia atrás | Activaciones frente al estado del adaptador/optimizador | Reduce el microbatch/presupuesto de secuencia; verifica el checkpointing y el alcance de los objetivos |
| Pérdida NaN | Objetivos incorrectos frente a problemas numéricos/de optimización | Comprueba que haya etiquetas supervisadas distintas de cero, valores finitos, compatibilidad con BF16 y tasa de aprendizaje |
| La pérdida baja, pero la recuperación sigue siendo baja | Aprendizaje del formato frente a cobertura de entidades | Inspecciona la validación por tipo, idioma, longitud y registros negativos/positivos |
| La salida es prosa o TSV mal formado | Plantilla de chat/EOS/máscara frente a ambigüedad de la tarea | Verifica el ejemplo preparado real y el contrato de decodificación antes de añadir pasos de entrenamiento |
| Puntuación alta de análisis/ida y vuelta, pero queda PII | Tolerancia del analizador y reemplazo reversible | Inspecciona la PII residual y la recuperación de entidades; no consideres que el éxito del análisis equivale a privacidad |
| El trabajo se completó, pero el resultado no se puede volver a cargar | Directorio de artefactos incorrecto o modelo/revisión base no coincidente | Inspecciona el contenido del artefacto y realiza una comprobación aparte de recarga del adaptador |

El `peak_gpu_memory_bytes` actual mide el pico de memoria asignada por PyTorch en el dispositivo CUDA predeterminado, después de reiniciar la medición tras cargar el modelo. No es la memoria total de la GPU, el pico de carga ni una suma entre dispositivos. Etiqueta con precisión las mediciones futuras.

## 11. Trata la migración del entorno de ejecución como una cohorte probada

La [política de soporte de AWS DLC](https://aws.github.io/deep-learning-containers/reference/support_policy/) y el [catálogo de imágenes](https://aws.github.io/deep-learning-containers/reference/available_images/) se revisaron el 15 de septiembre de 2026. No se deben confundir la antigua familia de imágenes `pytorch-training` y la nueva familia `pytorch`.

| Entrada del catálogo | Etiqueta de SageMaker, sin el nombre del host del registro | Python / SO | Fin de las actualizaciones de parches |
|---|---|---|---|
| Ejemplo histórico actual | `pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker` | 3.12 / Ubuntu 22.04 | 2026-08-06 |
| Nueva familia 2.11 | `pytorch:2.11.0-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-04-30 |
| Nueva familia 2.12 | `pytorch:2.12.1-cu130-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-02 |
| Nueva familia 2.13 | `pytorch:2.13.0-cu133-amzn2023-sagemaker` | 3.12 / AL2023 | 2027-07-20 |

Estas son entradas del catálogo verificadas, **no una validación de un reemplazo para la ruta histórica `src/train.py`/MLflow administrado**. El entrenamiento de prueba en GPU con 2.11 de la ruta separada `src/train_execution.py` está documentado en el [registro de ejecución](README.md#sagemaker-execution-readiness); las versiones 2.12 y 2.13 siguen siendo referencias del catálogo que no se han ejecutado. AWS también advierte que PyTorch 2.8–2.10 basado en Ubuntu no se puede actualizar por completo con parches y recomienda PyTorch 2.11 o posterior en AL2023. El lanzador histórico fija tanto un nombre de repositorio antiguo como una etiqueta; sustituir solo el número de versión no es suficiente.

La migración debe alinear el repositorio/etiqueta/digest de la imagen, la disponibilidad en la región, Python, CUDA/controlador/arquitectura, PyTorch, las dependencias de HF/PEFT/TRL/bitsandbytes, el toolkit de entrenamiento y el cliente/servicio de MLflow. Instalar el lock actual `torch==2.8.0` en un DLC más reciente podría deshacer la migración prevista del framework.

Solo después de revisar esas decisiones se debe realizar una prueba previa de GPU autorizada que compruebe la compatibilidad real con CUDA/BF16, la carga cuantizada, los objetivos/tipos de datos esperados, un paso de propagación hacia delante y hacia atrás, la finitud de la pérdida, las actualizaciones del adaptador y el guardado/recarga. **Describir un procedimiento de prueba no demuestra que la ejecución haya tenido éxito.** Consulta el registro separado anterior para ver la evidencia real de 2.11 y conserva la comprobación de la ruta histórica.

## 12. Comprueba lo que has entendido

1. Con microbatch 1 y acumulación 8 en un solo worker, ¿cuántas presentaciones de ejemplos representan 80 actualizaciones? **Unas 640**, bajo los supuestos de ausencia de empaquetado y divisibilidad usados aquí.
2. ¿«3.3B activos» implica que solo se necesitan 3.3B parámetros en memoria? **No.** Describe el cálculo disperso; los pesos totales y el estado de entrenamiento siguen siendo importantes.
3. ¿Qué debe enseñar un documento negativo? **Una respuesta de extracción vacía válida que termine el turno del asistente**, no una secuencia de etiquetas totalmente ignoradas.
4. ¿Se puede seleccionar el rango usando una puntuación de test después de cada ejecución? **No.** Selecciona usando validación, fija el candidato y usa el test bloqueado para la comparación final.
5. ¿Una ida y vuelta exitosa demuestra que se eliminó la PII? **No.** Demuestra la reversibilidad de la ruta de reemplazo; la PII no detectada puede seguir intacta.
6. ¿Basta una etiqueta de DLC compatible para habilitar el lanzador actual? **No.** El repositorio, las dependencias, el toolkit, el hardware y los contratos de integración deben formar una cohorte validada.

## Referencias principales

Todas las referencias siguientes se revisaron el **15 de septiembre de 2026**. Las fuentes versionadas rigen los ejemplos de lectura de código.

- [Artículo de LoRA](https://arxiv.org/abs/2106.09685) y [artículo de QLoRA](https://arxiv.org/abs/2305.14314)
- [Guía de LoRA de PEFT 0.17.1](https://github.com/huggingface/peft/blob/v0.17.1/docs/source/developer_guides/lora.md) y [código fuente de preparación k-bit](https://github.com/huggingface/peft/blob/v0.17.1/src/peft/utils/other.py)
- [Cuantización bitsandbytes en Transformers 4.57.6](https://github.com/huggingface/transformers/blob/v4.57.6/docs/source/en/quantization/bitsandbytes.md)
- [Módulos de cuatro bits de bitsandbytes 0.48.2](https://github.com/bitsandbytes-foundation/bitsandbytes/blob/0.48.2/docs/source/reference/nn/linear4bit.mdx)
- [Guía SFT de TRL 0.24.0](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer), [SFTConfig](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_config.py) y [SFTTrainer](https://github.com/huggingface/trl/blob/v0.24.0/trl/trainer/sft_trainer.py)
- [Ficha del modelo Qwen](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507), [configuración del modelo](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507/blob/main/config.json) e [implementación fijada de Transformers](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_moe/modeling_qwen3_moe.py)
- [Soporte de AWS DLC](https://aws.github.io/deep-learning-containers/reference/support_policy/) e [imágenes disponibles](https://aws.github.io/deep-learning-containers/reference/available_images/)
- [Variables de entorno/almacenamiento de SageMaker](https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage-env-var-summary.html) y [salida de entrenamiento](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-output.html)

Siguiente: [Taller de aumento de datos](06-data-augmentation-workshop.md)

## Cuestionario

Comprueba los conceptos y cálculos en el [Cuestionario del taller de ajuste fino de QLoRA](../../quizzes/ai-ml/sagemaker-ai/05-qlora-finetuning-workshop-quiz.md).
