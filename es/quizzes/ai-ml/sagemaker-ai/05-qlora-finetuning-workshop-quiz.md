# Cuestionario del taller: ajuste fino de QLoRA para extraer PII

> **Última actualización**: 15 de septiembre de 2026

## Preguntas de opción múltiple

1. ¿Qué afirmación describe correctamente QLoRA con `load_in_4bit=True`, `bnb_4bit_quant_type="nf4"` y `bnb_4bit_compute_dtype=torch.bfloat16`?
   - A) Las activaciones y el estado del optimizador también pasan a cuatro bits, junto con los pesos base.
   - B) Los pesos base compatibles se almacenan en formato de cuatro bits y quedan congelados; la ruta lineal cuantizada calcula en BF16 y se entrenan los adaptadores.
   - C) El cálculo en BF16 anula NF4, por lo que todos los pesos base se almacenan en formato de 16 bits.
   - D) La doble cuantización consiste en entrenar dos veces los pesos base.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

El almacenamiento de pesos, el tipo de datos de cálculo y los parámetros entrenables son opciones independientes. NF4 reduce el almacenamiento de los pesos base, mientras que BF16 especifica el tipo de datos usado en los cálculos de esa ruta. La doble cuantización cuantiza las constantes de cuantización. También hay que contabilizar por separado la memoria de los adaptadores, los gradientes, el estado del optimizador, las activaciones y los módulos de mayor precisión.
</details>

2. Una capa lineal tiene un ancho de entrada de 2,048 y un ancho de salida de 768. LoRA estándar usa rango 16 y alfa 32, sin sesgos entrenables ni módulos adicionales. ¿Cuántos parámetros tiene el adaptador y cuál es la escala `alpha/r`?
   - A) 1,572,864 parámetros y 2
   - B) 45,056 parámetros y 32
   - C) 45,056 parámetros y 2
   - D) 32,768 parámetros y 0.5

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

`A` tiene la forma `(16, 2048)` y `B` tiene la forma `(768, 16)`, por lo que hay `16 × (2048 + 768) = 45,056` parámetros. LoRA estándar escala la actualización por `32 / 16 = 2`. El valor `2048 × 768 = 1,572,864` cuenta la matriz base, no el adaptador. LoRA estabilizado por rango usa una regla de escala distinta.
</details>

3. ¿Cómo debe interpretarse «30.5B total / 3.3B activos» de Qwen al planificar la memoria de entrenamiento?
   - A) El recuento activo describe el cálculo disperso para un token; los pesos totales, los adaptadores, los gradientes, el estado del optimizador y las activaciones deben contabilizarse por separado.
   - B) Solo se cargan los 3.3B de parámetros, así que los demás expertos no consumen memoria.
   - C) Como `30.5B × 4 bits = 15.25GB`, la memoria total de entrenamiento es exactamente 15.25GB.
   - D) Seleccionar ocho expertos por token significa que LoRA se inserta en solo ocho expertos de todo el modelo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

El recuento de parámetros activos se refiere a la ruta de cálculo de un token; no sustituye el presupuesto de almacenamiento del modelo completo. El cálculo de 15.25 GB decimales es una estimación idealizada de los pesos a cuatro bits y no incluye los metadatos de cuantización ni otras necesidades de memoria de entrenamiento. Los destinos donde se insertan adaptadores y los expertos que selecciona un lote concreto también son conceptos distintos.
</details>

4. Hay 1,600 registros de entrenamiento, microbatch 1, acumulación de gradiente 8, un trabajador de paralelismo de datos y 80 actualizaciones del optimizador. Si no se empaquetan secuencias y no hay lotes finales incompletos, ¿cuál es el lote efectivo, la cantidad de presentaciones de ejemplos y la fracción de época?
   - A) 1, 80 presentaciones y 0.05 épocas
   - B) 8, 1,280 presentaciones y 0.8 épocas
   - C) 80, 6,400 presentaciones y 4 épocas
   - D) 8, 640 presentaciones y 0.4 épocas

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

El lote efectivo es `1 × 8 × 1 = 8`, y las presentaciones de ejemplos son `80 × 8 = 640`. Una época requiere `1600 / 8 = 200` actualizaciones, así que 80 actualizaciones representan 0.4 épocas. La etiqueta «full» actual nombra un modo de ejecución, no una época completada ni convergencia. Las longitudes distintas de las secuencias también pueden producir cantidades distintas de tokens de entrenamiento con el mismo número de ejemplos.
</details>

5. Para un documento sin entidades y con el contenido de destino del asistente vacío, ¿qué debe comprobarse al usar pérdida solo para la finalización?
   - A) Todas las etiquetas son `-100`, así que el registro no contribuye al entrenamiento.
   - B) Se ignoran las posiciones del prompt y del relleno, pero los tokens válidos de finalización, como EOS del asistente, siguen supervisados.
   - C) Solo se ignora EOS, mientras que todo el prompt de origen se entrena como respuesta de extracción.
   - D) NF4 hace innecesarias EOS y las máscaras de pérdida, así que no hay que comprobar nada.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

Un ejemplo negativo debe enseñar al modelo a finalizar su respuesta sin extraer entidades. Este modelo usa `<|im_end|>` como EOS. Después de aplicar la plantilla real de chat y el truncamiento, compruebe que queden algunas etiquetas supervisadas. Una respuesta real puede incluir tokens adicionales, como un salto de línea; una secuencia cuyas etiquetas estén todas ignoradas no debe tratarse como un ejemplo negativo de entrenamiento normal.
</details>

6. ¿Cómo deben usarse los conjuntos de evaluación al comparar opciones de rango y aumento de datos?
   - A) Seleccionar candidatos bajo condiciones de validación coherentes, congelar la configuración y después realizar la comparación final entre referencia y candidato con el conjunto de prueba bloqueado.
   - B) Consultar la puntuación del conjunto de prueba para cada candidato y elegir la más alta.
   - C) Generar primero todos los descendientes del aumento de datos y luego dividirlos aleatoriamente entre entrenamiento, validación y prueba.
   - D) Desplegar cuando baje la pérdida en un pequeño subconjunto de datos para comprobar si hay sobreajuste, sin verificar la generalización.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A**

Ajuste el modelo usando el conjunto de validación y reserve el conjunto de prueba para la comparación final. El entrenador actual evalúa el conjunto de prueba antes y después de cada ejecución, incluso en las pruebas rápidas, por lo que todavía no ofrece un ciclo seguro de búsqueda de hiperparámetros. El flujo didáctico de ajuste requiere una modificación aparte. Divida las familias originales antes del aumento de datos y aumente solo los datos derivados del conjunto de entrenamiento; una pequeña prueba de sobreajuste sirve para diagnosticar la ruta de aprendizaje, pero no demuestra la generalización.
</details>

7. ¿Cuál es la forma correcta de comprobar los siete sufijos de destino LoRA actuales para la implementación Qwen3 MoE en Transformers 4.57.6?
   - A) Reemplazarlos por `"all-linear"` y omitir la inspección porque se seleccionan los mismos módulos.
   - B) Cambiar siempre a `target_parameters` porque todos los MoE usan parámetros sin procesar.
   - C) Inspeccionar los nombres y las cantidades reales de los módulos, y confirmar que se cubren las proyecciones de atención y `gate_proj`/`up_proj`/`down_proj` de los expertos, excluyendo el `gate` del router independiente.
   - D) Esperar que haya solo siete módulos lineales en todo el modelo porque hay siete nombres de destino.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

Esta versión implementa a los expertos como proyecciones `nn.Linear` dentro de un `ModuleList`. Un sufijo se repite en capas y expertos, por lo que la cantidad de sufijos no equivale a la cantidad de módulos. Para la configuración publicada, compare el valor esperado de `48 × (4 + 3 × 128) = 18,624` destinos lineales con el inventario real. `"all-linear"` puede agregar módulos como el router, mientras que `target_parameters` se usa para una implementación diferente con parámetros sin procesar.
</details>

8. Si encuentra en el catálogo un DLC de PyTorch para AL2023 que tiene soporte vigente, ¿cuál es el siguiente paso apropiado antes de volver a habilitar la ejecución en GPU para el ejemplo histórico?
   - A) Cambiar solo la etiqueta de imagen e instalar el archivo de bloqueo anterior, incluido `torch==2.8.0`.
   - B) Eliminar la protección de fecha y enviar una ejecución completa porque la imagen existe en ECR.
   - C) Registrar que la carga cuantizada en GPU y la retropropagación funcionaron porque se aprobaron las pruebas de CPU.
   - D) Validar el repositorio, la etiqueta o el digest de la imagen, Python/CUDA/controlador, las dependencias, el kit de herramientas y la combinación de versiones de MLflow; realizar una prueba rápida autorizada en GPU y mantener la protección existente mientras la versión sustituta no esté validada.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D**

PyTorch 2.8 llegó al fin del soporte de parches el 6 de agosto de 2026. Una entrada más reciente en el catálogo no constituye una combinación de reemplazo validada para este paquete. La nueva familia también puede usar un repositorio distinto de `pytorch-training`, y la instalación de la versión de `torch` fijada anteriormente puede revertir la migración. La prueba previa de GPU es un procedimiento de prueba futuro; las comprobaciones de CPU o la consulta de una imagen no demuestran que la ejecución en GPU haya funcionado correctamente.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/sagemaker-ai/05-qlora-finetuning-workshop.md)
