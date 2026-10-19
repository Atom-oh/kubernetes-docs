# Parte 1: Seguimiento de MLflow

> **Versión de referencia revisada**: MLflow 3.16.0; última versión 3.17.1 comprobada · 2026-10-16

## Configuración del entorno del laboratorio

Instala `mlflow==3.16.0` con Python 3.10 o posterior. El ejemplo siguiente se comprobó con Python 3.12, SQLite y un almacén local de artefactos. No requiere GPU, modelo entrenado ni servidor remoto.

Los parches 3.16.1 y la línea posterior 3.17.x (última versión: 3.17.1) están disponibles, pero este ejemplo no se ha vuelto a ejecutar con ninguna versión posterior a la 3.16.0. [La parte 3](03-eks-deployment.md) trata sobre un servidor HTTP para equipos y la operación en EKS.

## ¿Qué es MLflow Tracking?

Tracking proporciona API e interfaz de usuario para experimentos, ejecuciones, parámetros, métricas, artefactos, modelos de tipo `LoggedModel` y trazas. El SDK puede conectarse a un servidor de seguimiento HTTP o directamente a un backend local de archivos o SQL. No es necesario ejecutar un proceso de servidor aparte para cada uso.

Incluso con un servidor remoto, los metadatos y las transferencias de artefactos pueden seguir rutas distintas. Los metadatos pasan por la API de seguimiento; el servidor puede actuar como proxy de los artefactos o estos pueden transferirse directamente entre el cliente y un almacén como S3. A continuación se distinguen estas configuraciones.

## Conceptos básicos: experimentos y ejecuciones

Un **experimento** agrupa ejecuciones y resultados relacionados. Una **ejecución** puede representar evaluación, preprocesamiento o una comparación, además de entrenamiento. No se puede cambiar una clave de parámetro a un valor distinto dentro de una misma ejecución. Las métricas pueden tener varias observaciones con marca de tiempo y pasos; distingue el resumen actual del historial completo.

Los valores siguientes son **datos de prueba de la API de Tracking, no mediciones de precisión del modelo**. El ejemplo crea su propio artefacto JSON, en lugar de depender de un archivo de imagen sin definir.

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".mlflow-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'mlflow.db'}")
client = MlflowClient()
experiment = client.get_experiment_by_name("tracking-demo")
experiment_id = (
    experiment.experiment_id if experiment else
    client.create_experiment(
        "tracking-demo", artifact_location=(root / "artifacts").as_uri()
    )
)
mlflow.set_experiment(experiment_id=experiment_id)

with mlflow.start_run(run_name="demo") as run:
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("demo_score", 0.92, step=0)
    mlflow.log_metric("demo_score", 0.95, step=1)
    mlflow.log_dict({"synthetic_example": True}, "summary.json")
    run_id = run.info.run_id

assert client.get_run(run_id).info.status == "FINISHED"
assert len(client.get_metric_history(run_id, "demo_score")) == 2
```

Al salir normalmente del contexto, la ejecución termina con el estado `FINISHED`; si se produce una excepción en el bloque, termina con el estado `FAILED`. El fin de una ejecución no hace copias de seguridad de los artefactos ni verifica que todo el proceso de entrenamiento haya tenido éxito. Si se repite el ejemplo, se añade una ejecución al mismo experimento. La condición no cambia la ubicación de artefactos de un experimento existente.

### Registro automático

`mlflow.autolog()` configura las integraciones compatibles. Los valores capturados, las versiones de frameworks compatibles, el registro de modelos y la recopilación de ejemplos de entrada varían según la integración. No des por sentado que un bucle normal de PyTorch y un flujo de trabajo de Lightning reciben la misma instrumentación automática. Consulta la API y la compatibilidad de versiones específicas del framework; registra manualmente las métricas adicionales.

Antes de habilitar el registro automático, revisa dónde se almacenarán las entradas, salidas, modelos y muestras de datos. Habilitar esta función no elimina la información personal identificable ni instrumenta todas las rutas de código personalizadas.

## El cambio de MLflow 3: modelos como entidades de primer nivel

Un `LoggedModel` tiene su propio `model_id`, estado, ubicación de artefactos y metadatos. Puede hacer referencia a una ejecución de entrenamiento mediante `source_run_id` y tener relaciones con otras ejecuciones de evaluación, métricas y trazas. Es distinto de los modelos registrados y las versiones de modelo.

**Llamar a `log_model()` sin un bloque `start_run()` explícito no es una novedad de la versión 3.x.** `Model.log()` ya usaba `_get_or_start_run()` cuando era necesario en la versión 2.22.0; la ruta de registro de modelos de la 3.16.0 sigue comportándose así. El cambio importante es la identidad independiente del modelo y el seguimiento de relaciones.

Después de la configuración de seguimiento anterior, esto crea metadatos del modelo sin una ejecución activa:

```python
model = mlflow.initialize_logged_model(
    name="metadata-only", model_type="demo"
)
assert mlflow.active_run() is None
assert model.source_run_id is None
print(model.model_id, model.status)  # PENDING
```

Todavía no contiene pesos de modelo utilizables ni una variante de modelo (flavor) de MLflow. Completa el registro real del modelo, la conservación de artefactos y su finalización antes de usarlo. El estado `READY` no demuestra que el modelo tenga aprobación para su implementación ni que haya superado una revisión de calidad o seguridad.

## Observabilidad de GenAI y LLM: trazas

MLflow Tracing se presentó en la **versión 2.14.0, el 2024-06-17**. La versión 3.x amplió la integración de modelos, evaluación e interfaz de usuario de GenAI; la 3.16.0 añadió enlaces entre spans y rediseñó la interfaz de trazas. El trazado no apareció por primera vez en la versión 3.

Una traza representa pasos de una solicitud, como la recuperación, la ejecución de herramientas y las llamadas a LLM, mediante spans. Distingue la estructura padre/hijo de los enlaces entre spans. La recopilación de tokens depende de la integración y de la respuesta del proveedor; los spans de recuperación o herramientas no necesariamente tienen campos de tokens o costes de LLM. La estimación de costes requiere la identidad del modelo, el uso y la información de precios, y no equivale al total de facturación conciliado.

Combina la instrumentación automática con spans manuales cuando corresponda. Las entradas, salidas, excepciones, argumentos de herramientas y razonamientos pueden contener información sensible; define el alcance de la recopilación, el acceso, el enmascaramiento y la conservación. Instalar una integración no garantiza una cobertura completa de todas las rutas ni el cálculo de costes.

## Almacén de backend y almacén de artefactos

| Almacén o valor predeterminado | Significado |
|---|---|
| Backend | metadatos de experimentos, ejecuciones, parámetros, métricas y modelos; SQLite, PostgreSQL, MySQL y otros almacenes SQL compatibles |
| Artefactos | archivos de modelos, gráficos, JSON y otros archivos; rutas locales, S3 y otros almacenes |
| Valor predeterminado | un entorno nuevo de la versión 3.16.0 usa `sqlite:///mlflow.db`; comprueba el comportamiento de compatibilidad si ya existe `./mlruns` |
| Backend de archivos heredado | en modo de mantenimiento; para nuevas operaciones, elige un backend SQL explícito y un plan de migración |

SQLite también es una base de datos relacional. Es adecuado para ejercicios locales pequeños; el uso de escritores simultáneos, varias réplicas de servidor, copias de seguridad y alta disponibilidad requiere una evaluación aparte. Una copia de seguridad de la base de datos de metadatos no incluye automáticamente los archivos de artefactos.

### Dos rutas de artefactos con un servidor remoto

- **Modo proxy:** el cliente usa una ubicación `mlflow-artifacts:` y envía los archivos a través del servidor, que dispone de los permisos para el almacén de artefactos. Puede que los clientes no necesiten acceso propio a S3, por lo que la autenticación y autorización del servidor de seguimiento son importantes.
- **Modo directo:** con `--no-serve-artifacts` y una raíz de artefactos `s3://...` directa, los clientes acceden al almacenamiento por su cuenta. Necesitan los permisos de AWS pertinentes, acceso a la red y las bibliotecas necesarias.

Cambiar las opciones del servidor no reescribe retroactivamente los URI de artefactos existentes de los experimentos. Inspecciona el URI real del experimento o de la ejecución. La interfaz web consulta las API HTTP del servidor; no se conecta directamente a PostgreSQL.

![Los clientes y la interfaz web se conectan a la API del servidor de Tracking, que accede a los metadatos SQL y al almacenamiento de artefactos. En el modo de artefactos directos, un cliente autorizado utiliza una ruta de transferencia de archivos separada para acceder al almacenamiento.](../../.gitbook/assets/en-ai-ml-mlflow-01-tracking-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-01-tracking-0.html)

## Próximos pasos

[La parte 2](02-model-registry.md) trata sobre el registro, las versiones y los alias. [La parte 3](03-eks-deployment.md) trata sobre el almacenamiento y el control de acceso en EKS. Cambiar solo un alias no vuelve a implementar automáticamente todos los procesos de servicio.

## Fuentes principales

- [Versión 3.16.0 de MLflow](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Almacén de backend](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
- [Almacén de artefactos](https://mlflow.org/docs/3.16.0/self-hosting/architecture/artifact-store/)
- [Implementación del registro de modelos de la versión 2.22.0](https://github.com/mlflow/mlflow/blob/v2.22.0/mlflow/models/model.py)
- [Implementación de la API de Tracking de la versión 3.16.0](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/fluent.py)
- [Presentación de Tracing en la versión 2.14.0](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)

[Volver a la página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/01-tracking-quiz.md)
