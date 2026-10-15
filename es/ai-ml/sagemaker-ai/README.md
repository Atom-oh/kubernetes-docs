# Ajuste fino de Qwen para PII con SageMaker AI

> **Última actualización**: September 15, 2026

Incluye ejercicios de CPU con datos sintéticos e instrucciones de QLoRA. Las observaciones de aprovisionamiento de AWS son registros históricos del 1 de septiembre de 2026.

Esta guía enseña a entrenar y evaluar un modelo que extrae candidatos de PII de documentos. Defina el contrato de anotación, divida y aumente los datos sin filtraciones, elija la configuración de QLoRA y mida tanto las omisiones como el enmascaramiento excesivo.

El modelo emite candidatos `TYPE<TAB>ORIGINAL`. El código Python los valida y reemplaza; el modelo no reescribe todo el documento. Esta separación ayuda a distinguir los errores de detección de los fallos de reemplazo.

## Comience con la ruta práctica de aprendizaje

| Orden | Capítulo | Lo que debería poder explicar después |
| --- | --- | --- |
| 1 | [Datos sintéticos y aumento](06-data-augmentation-workshop.md) | Contratos de anotación, separación de familias, aumento solo de entrenamiento, auditorías de fuente/etiqueta |
| 2 | [Entrenamiento QLoRA y el flujo de trabajo de SageMaker](05-qlora-finetuning-workshop.md) | NF4, LoRA, máscaras de pérdida, módulos objetivo reales, presupuestos de batch/pasos, ajuste y diagnóstico |
| 3 | [Evaluación de PII y canalizaciones de enmascaramiento](07-pii-evaluation-release.md) | Recall/F1, PII residual, enmascaramiento en documentos negativos, evaluación final y aceptación |
| 4 | [Contratos de ejecución de SageMaker AI y MLflow](03-sagemaker-mlflow-execution.md) | Paquetes fuente, canales de S3, Training Jobs, artefactos y limpieza |

Comience con los datos y la evaluación si puede usar Python 3.12 y JSONL. Ninguno de los ejercicios de CPU necesita una cuenta de AWS ni pesos de modelo. El recorrido de entrenamiento y el procedimiento de comprobación de GPU son distintos de la evidencia de entrenamiento de GPU completado.

El nuevo ejercicio de aumento divide 40 familias sintéticas antes de aumentar únicamente los datos de entrenamiento. Su conjunto de datos independiente no sobrescribe el corpus histórico del generador 1.0.0 de 2.200 registros. Las puntuaciones de ejercicios pequeños o de oráculo no son afirmaciones sobre el rendimiento de modelos en el mundo real.

## Preparación para la ejecución en SageMaker

El paquete histórico propone el entrenamiento de Qwen/Qwen3-30B-A3B-Instruct-2507 mediante un SageMaker Training Job administrado o un EKS GPU Job efímero. Ninguna ruta de GPU tiene un éxito integral registrado.

El DLC fijado de PyTorch 2.8 terminó el soporte de parches el 2026-08-06, por lo que la creación de recursos y la ejecución de GPU están bloqueadas. Siga la [discusión del entorno de ejecución de QLoRA](05-qlora-finetuning-workshop.md) y el [contrato de ejecución](03-sagemaker-mlflow-execution.md) para validar conjuntamente la imagen, las dependencias y el emparejamiento con MLflow. Eliminar únicamente la comprobación de soporte no es un procedimiento de migración.

## Lea el diseño y la implementación en profundidad

| Documento | Propósito |
| --- | --- |
| [Parte 1: arquitectura de la plataforma](01-platform-architecture.md) | Responsabilidades del modelo, los datos, el procesamiento Python y MLflow |
| [Parte 2: datos y tokenización determinista](02-pii-data-tokenization.md) | Datos históricos de nueve tipos, intervalos de reemplazo y definiciones exactas de métricas |
| [Parte 3: ejecución](03-sagemaker-mlflow-execution.md) | Envío a SageMaker/EKS, persistencia, recuperación y limpieza |
| [Parte 4: gobernanza de Unified Studio](../../data-on-eks/sagemaker-unified-studio/01-domains-projects-governance.md) | Dominio/proyecto/membresía |
| [Parte 5: registros de validación factual](04-validation-results.md) | Trabajo ejecutado, trabajo no ejecutado y recursos residuales históricos |

## Interpretación de los registros de validación

- Los nuevos comandos de datos/evaluación se comprueban en CPU con entradas sintéticas. El F1 de modelos entrenados, la memoria máxima de GPU y la duración del entrenamiento requieren mediciones independientes.
- La revisión del 2026-09-12 añadió cobertura de regresión local para tokenización, evaluación, ejecución y limpieza.
- El registro de AWS del 2026-09-01 abarca cuotas y rutas de error de aprovisionamiento de la App/proyecto de MLflow; se detuvo antes del envío a GPU.
- Ese registro limpió los recursos de App/S3/IAM del experimento, pero dejó un proyecto de Unified Studio. Se necesita un inventario nuevo para establecer su estado actual.

No envíe fuentes, valores extraídos, mapeos de tokens ni finalizaciones sin procesar a registros generales ni a parámetros/etiquetas de MLflow. Compruebe también autolog/tracing y el contenido de los artefactos en el entorno de ejecución. Los mapeos reversibles, los adaptadores entrenados y los inventarios de recursos privados son artefactos distintos con requisitos independientes de retención/acceso.

Paquete de ejemplo: `examples/ai-ml/qwen-pii-finetuning/`. Cada taller proporciona su CLI exacta y un ejemplo de salida.

## Referencias

- [Qwen model card](https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507)
- [QLoRA paper](https://arxiv.org/abs/2305.14314)
- [Experiment configuration](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/config/experiment.yaml)
- [Historical provisioning result](https://github.com/Atom-oh/kubernetes-docs/blob/main/examples/ai-ml/qwen-pii-finetuning/results/provisioning-validation.json)
