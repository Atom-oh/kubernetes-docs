# Parte 1: Seguimiento de MLflow

> **Base de revisión**: MLflow 3.16.0 · 2026-09-12

## Configuración del entorno de laboratorio

Instala `mlflow==3.16.0` con Python 3.10 o posterior. El ejemplo siguiente se verificó con Python 3.12, SQLite y un almacén de artefactos local. No requiere GPU, modelo entrenado ni servidor remoto. La [Parte 3](03-eks-deployment.md) cubre un servidor HTTP de equipo y la operación de EKS.

## ¿Qué es MLflow Tracking?

Tracking proporciona API y una UI para experimentos, ejecuciones, parámetros, métricas, artefactos, modelos registrados y trazas. El SDK puede conectarse a un servidor de tracking HTTP o directamente a un backend local de archivos/SQL. No se requiere un proceso de servidor independiente para cada uso.

Incluso con un servidor remoto, las transferencias de metadatos y artefactos pueden tomar rutas distintas. Los metadatos pasan por la API de tracking; los artefactos pueden ser proxyados por el servidor o transferirse directamente entre el cliente y un almacén como S3. Estas configuraciones se distinguen a continuación.

## Conceptos principales: Experimentos y ejecuciones

Un **Experiment** agrupa ejecuciones y resultados relacionados. Una **Run** puede representar evaluación, preprocesamiento o una comparación, además del entrenamiento. Una clave de parámetro no puede cambiarse a un valor distinto dentro de una ejecución. Las métricas pueden tener múltiples observaciones con marca de tiempo y pasos; diferencia el resumen actual del historial completo.

Los siguientes valores son **fixtures de la Tracking API, no precisión de modelo medida**. El ejemplo crea su artefacto JSON en lugar de depender de un archivo de imagen no definido.

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

La salida normal del contexto finaliza la ejecución como `FINISHED`; una excepción en el bloque la finaliza como `FAILED`. La finalización de una ejecución no respalda los artefactos ni verifica el éxito de un proceso completo de entrenamiento. Repetir el ejemplo agrega una ejecución al mismo experimento. La condición no cambia la ubicación de artefactos de un experimento existente.

### Autologging

`mlflow.autolog()` configura integraciones compatibles. Los valores capturados, las versiones de framework compatibles, el registro de modelos y la recopilación de ejemplos de entrada varían según la integración. No supongas que un bucle ordinario de PyTorch y un flujo de trabajo de Lightning reciben instrumentación automática idéntica. Revisa la API específica del framework y la compatibilidad de versiones; registra métricas adicionales manualmente.

Revisa dónde se almacenarán las entradas, salidas, modelos y muestras de datos antes de habilitar autologging. Habilitar la función no elimina PII ni instrumenta todas las rutas de código personalizado.

## El cambio de MLflow 3: los modelos como entidades de primera clase

Un `LoggedModel` tiene su propio `model_id`, estado, ubicación de artefactos y metadatos. Puede hacer referencia a una ejecución de entrenamiento mediante `source_run_id` y tener relaciones con otras ejecuciones de evaluación, métricas y trazas. Es distinto de Registered Models y Model Versions.

**Llamar a `log_model()` sin un bloque explícito de `start_run()` no es una novedad en 3.x por sí misma.** `Model.log()` en 2.22.0 ya usaba `_get_or_start_run()` cuando era necesario; la ruta de registro de modelos de 3.16.0 mantiene este comportamiento. El cambio importante es la identidad independiente del modelo y el seguimiento de relaciones.

Después de la configuración de tracking anterior, esto crea metadatos del modelo sin una ejecución activa:

```python
model = mlflow.initialize_logged_model(
    name="metadata-only", model_type="demo"
)
assert mlflow.active_run() is None
assert model.source_run_id is None
print(model.model_id, model.status)  # PENDING
```

Aún no contiene pesos de modelo utilizables ni un flavor de modelo. Completa el registro real del modelo, la retención de artefactos y la finalización antes de usarlo. `READY` no es evidencia de aprobación de despliegue, calidad ni revisión de seguridad.

## Observabilidad de GenAI y LLM: Tracing

MLflow Tracing se introdujo en **2.14.0 el 2024-06-17**. La versión 3.x amplió la integración de modelos, evaluación y UI de GenAI; la 3.16.0 añadió enlaces de span y una UI de trazas rediseñada. Tracing no se hizo posible por primera vez en la versión 3.

Una traza representa pasos de solicitud como recuperación, ejecución de herramientas y llamadas LLM con spans. Distingue la estructura padre/hijo de los enlaces de span. La recopilación de tokens depende de la integración y de la respuesta del proveedor; los spans de recuperación o de herramientas no necesariamente tienen campos de tokens o costes de LLM. La estimación de costes requiere identidad de modelo, uso e información de precios, y no es el total de facturación conciliado.

Combina instrumentación automática con spans manuales cuando corresponda. Las entradas, salidas, excepciones, argumentos de herramientas y razonamiento pueden contener información sensible; define el alcance de recopilación, acceso, redacción y retención. Instalar una integración no garantiza cobertura completa de rutas ni contabilización de costes.

## Backend Store frente a Artifact Store

| Almacén o valor predeterminado | Significado |
|---|---|
| Backend | metadatos de experimentos/ejecuciones/parámetros/métricas/modelos; SQLite, PostgreSQL, MySQL y otros almacenes SQL compatibles |
| Artifact | archivos de modelos, gráficos, JSON y otros archivos; rutas locales, S3 y otros almacenes |
| Default | un entorno nuevo de 3.16.0 usa `sqlite:///mlflow.db`; revisa el comportamiento de compatibilidad si ya existe `./mlruns` |
| Legacy file backend | modo de mantenimiento; elige un backend SQL explícito y un plan de migración para una operación nueva |

SQLite también es una base de datos relacional. Es adecuado para ejercicios locales pequeños; los escritores concurrentes, múltiples réplicas de servidor, copias de seguridad y alta disponibilidad requieren una evaluación independiente. Una copia de seguridad de la base de datos de metadatos no incluye automáticamente los archivos de artefactos.

### Dos rutas de artefactos con un servidor remoto

- **Modo proxy:** el cliente usa una ubicación `mlflow-artifacts:` y envía archivos a través del servidor, que posee permisos de Artifact Store. Los clientes pueden no necesitar su propio acceso a S3, lo que hace importante la autenticación y autorización del servidor de tracking.
- **Modo directo:** con `--no-serve-artifacts` y una raíz de artefactos directa `s3://...`, los clientes acceden al almacenamiento por sí mismos. Necesitan los permisos de AWS, acceso de red y bibliotecas pertinentes.

Cambiar las opciones del servidor no reescribe retroactivamente los URI de artefactos de experimentos existentes. Inspecciona el URI real del experimento/ejecución. La UI del navegador consulta las API HTTP del servidor; no se conecta directamente a PostgreSQL.

![Los clientes y la UI web se conectan a la API del servidor de Tracking, que accede a metadatos SQL y almacenamiento de artefactos. En el modo directo de artefactos, un cliente autorizado utiliza una ruta de transferencia de archivos independiente hacia el almacenamiento.](../../.gitbook/assets/en-ai-ml-mlflow-01-tracking-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-01-tracking-0.html)

## Próximos pasos

La [Parte 2](02-model-registry.md) cubre registro, versiones y alias. La [Parte 3](03-eks-deployment.md) cubre el almacenamiento y control de acceso de EKS. Cambiar un alias por sí solo no vuelve a desplegar automáticamente cada proceso de servicio.

## Fuentes principales

- [Lanzamiento de MLflow 3.16.0](https://github.com/mlflow/mlflow/releases/tag/v3.16.0)
- [Backend store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/backend-store/)
- [Artifact store](https://mlflow.org/docs/3.16.0/self-hosting/architecture/artifact-store/)
- [Implementación del registro de modelos de 2.22.0](https://github.com/mlflow/mlflow/blob/v2.22.0/mlflow/models/model.py)
- [Implementación de la Tracking API de 3.16.0](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/fluent.py)
- [Tracing introducido en 2.14.0](https://github.com/mlflow/mlflow/releases/tag/v2.14.0)

[Volver a la página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/01-tracking-quiz.md)
