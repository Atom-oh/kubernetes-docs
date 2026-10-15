# Ajuste fino de Qwen para PII con SageMaker AI

> **Última actualización**: September 16, 2026

Incluye ejercicios de CPU con datos sintéticos e instrucciones de QLoRA. Un entorno de ejecución independiente completó una prueba de humo real con GPU el September 16, 2026. Las observaciones de aprovisionamiento del September 1 siguen siendo registros históricos.

Esta guía enseña cómo entrenar y evaluar un modelo que extrae candidatos de PII de documentos. Defina el contrato de anotación, divida y aumente los datos sin filtraciones, elija la configuración de QLoRA y mida tanto las omisiones como el enmascaramiento excesivo.

El modelo genera candidatos `TYPE<TAB>ORIGINAL`. El código de Python los valida y reemplaza; el modelo no reescribe el documento completo. Esta separación ayuda a distinguir los errores de detección de los errores de reemplazo.

## Comience con la ruta de aprendizaje práctica

| Orden | Capítulo | Lo que debería poder explicar después |
| --- | --- | --- |
| 1 | [Datos sintéticos y aumento](06-data-augmentation-workshop.md) | Contratos de anotación, separación por familia, aumento solo para entrenamiento, auditorías de fuente/etiqueta |
| 2 | [Entrenamiento QLoRA y el flujo de trabajo de SageMaker](05-qlora-finetuning-workshop.md) | NF4, LoRA, máscaras de pérdida, módulos objetivo reales, presupuestos de lotes/pasos, ajuste y diagnóstico |
| 3 | [Evaluación de PII y canalizaciones de enmascaramiento](07-pii-evaluation-release.md) | Recall/F1, PII residual, enmascaramiento en documentos negativos, evaluación final y aceptación |
| 4 | [Contratos de ejecución de SageMaker AI y MLflow](03-sagemaker-mlflow-execution.md) | Paquetes fuente, canales de S3, Training Jobs, artefactos y limpieza |

Comience con datos y evaluación si puede usar Python 3.12 y JSONL. Ninguno de los ejercicios de CPU necesita una cuenta de AWS ni pesos de modelo. El recorrido de entrenamiento y el procedimiento de comprobación de GPU son distintos de la evidencia de un entrenamiento con GPU completado.

El nuevo ejercicio de aumento divide 40 familias sintéticas antes de aumentar solo el entrenamiento. Su conjunto de datos independiente no sobrescribe el corpus histórico del generador 1.0.0 de 2,200 registros. Las puntuaciones de ejercicios pequeños u oráculo no son afirmaciones sobre el rendimiento del modelo en el mundo real.

## Preparación para la ejecución de SageMaker

El [recibo real de la prueba de humo con GPU](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/execution-smoke-20260916.json) registra una ruta independiente de PyTorch 2.11/AL2023/CUDA 13 el September 16, 2026. Carga el mismo modelo Qwen en NF4 y aplica LoRA de rango 16 a cuatro proyecciones de atención. Cuatro pasos del optimizador produjeron pesos de adaptador modificados con estados guardados/recargados coincidentes. Los 1,140 segundos facturables implican aproximadamente USD 1.46 de cómputo de GPU, sin incluir almacenamiento, registros, impuestos ni ajustes.

La generación abarcó solo cuatro documentos de validación sintéticos. La línea base tuvo F1 de entidad de 1.0000, pero solo 2/4 respuestas con formato correcto. El modelo ajustado tuvo F1 de 0.8125 y 4/4 respuestas con formato correcto, a la vez que añadió seis pares de entidades de falsos positivos. **Una ejecución exitosa no es evidencia de una calidad mejorada.** Ese día se envió un trabajo completo de 600 pasos; este recibo no contiene resultados finales de prueba. El trabajo completo selecciona un punto de control según la pérdida de validación antes de evaluar un conjunto de prueba independiente de 400 documentos. Consulte la [configuración de ejecución y retención de artefactos](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/README.md#recorded-gpu-execution-september-16-2026).

El paquete histórico propone entrenamiento de Qwen/Qwen3-30B-A3B-Instruct-2507 mediante un SageMaker Training Job administrado o un EKS GPU Job efímero. Ninguna ruta de GPU tiene registrado un éxito integral de extremo a extremo.

El DLC histórico de PyTorch 2.8 fijado de esa ruta terminó el soporte de parches el 2026-08-06, por lo que la creación de recursos y la ejecución con GPU siguen bloqueadas. Siga la [discusión sobre el entorno de ejecución de QLoRA](05-qlora-finetuning-workshop.md) y el [contrato de ejecución](03-sagemaker-mlflow-execution.md) para validar conjuntamente la imagen, las dependencias y la combinación de MLflow. Eliminar solo la comprobación de soporte no es un procedimiento de migración.

## Lea en profundidad el diseño y la implementación

| Documento | Propósito |
| --- | --- |
| [Parte 1: arquitectura de la plataforma](01-platform-architecture.md) | Responsabilidades del modelo, los datos, el procesamiento de Python y MLflow |
| [Parte 2: datos y tokenización determinista](02-pii-data-tokenization.md) | Datos históricos de nueve tipos, intervalos de reemplazo y definiciones exactas de métricas |
| [Parte 3: ejecución](03-sagemaker-mlflow-execution.md) | Envío a SageMaker/EKS, persistencia, recuperación y limpieza |
| [Parte 4: gobernanza de Unified Studio](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Dominio/proyecto/membresía |
| [Parte 5: registros de validación factual](04-validation-results.md) | Trabajo ejecutado, trabajo no ejecutado y recursos residuales históricos |

## Interpretación de los registros de validación

- Los nuevos comandos de datos/evaluación se comprueban en CPU con entradas sintéticas. El F1 del modelo entrenado, la memoria máxima de GPU y la duración del entrenamiento requieren mediciones independientes.
- La revisión del 2026-09-12 añadió cobertura de regresión local para tokenización, evaluación, ejecución y limpieza.
- El registro de AWS del 2026-09-01 cubre las rutas de fallo de cuotas y aprovisionamiento de App/proyecto de MLflow; se detuvo antes del envío a GPU.
- Ese registro limpió los recursos de experimento de App/S3/IAM, pero dejó un proyecto de Unified Studio. Se necesita un inventario nuevo para establecer su estado actual.

No envíe fuentes, valores extraídos, asignaciones de tokens ni finalizaciones sin procesar a registros generales ni a parámetros/etiquetas de MLflow. Compruebe también el contenido de autolog/tracing y de los artefactos en el entorno de ejecución. Las asignaciones reversibles, los adaptadores entrenados y los inventarios privados de recursos son artefactos distintos con requisitos independientes de retención/acceso.

Paquete de ejemplo: `examples/ai-ml/qwen-pii-finetuning/`. Cada taller proporciona su CLI exacta y un ejemplo de salida.

## Referencias

- [Tarjeta del modelo Qwen](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [Artículo de QLoRA](https://arxiv.org/abs/2305.14314)
- [Configuración del experimento](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Resultado histórico del aprovisionamiento](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
