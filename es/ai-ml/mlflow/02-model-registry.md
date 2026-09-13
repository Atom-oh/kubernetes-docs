# Parte 2: MLflow Model Registry

> **Base de revisión**: MLflow 3.16.0 · 2026-09-12

## Configuración del entorno de laboratorio

Use Python 3.10 o posterior y `mlflow==3.16.0`. Las API del Registry también funcionan con SQLite local; no es obligatorio contar con un servidor HTTP independiente. Consulte la [Parte 3](03-eks-deployment.md) para el despliegue en equipo y la [Parte 1](01-tracking.md) para la configuración de Tracking. Este capítulo describe MLflow OSS. Los Registry administrados, como Databricks Unity Catalog, pueden tener comportamientos distintos en cuanto a permisos, copia y retención.

## Qué es el Model Registry

El Registry administra nombres lógicos de modelos, versiones numeradas, alias y metadatos. Registrar candidatos, aprobar una promoción y desplegar un endpoint son operaciones independientes. Contar con un Registry no implementa automáticamente el comportamiento de aprobación o serving.

## Conceptos principales

| Entidad | Significado y límite de mutación |
|---|---|
| Registered Model | colección de versiones bajo un nombre lógico, como `fraud-detector` |
| Model Version | registro numerado con información de origen; las descripciones, etiquetas y relaciones de stage/alias pueden cambiar |
| Alias | nombre mutable que apunta a una versión; varios alias pueden apuntar a la misma versión |
| LoggedModel | entidad de modelo de Tracking independiente; distinta de Registered Models y Model Versions |

### Model Version

Los nuevos resultados de modelos normalmente deben convertirse en nuevas versiones. Sin embargo, **no todos los campos de una versión ni todos los bytes de los artefactos son inmutables**. `update_model_version` cambia las descripciones; las etiquetas de versión también son mutables. Alguien con acceso de escritura puede cambiar archivos en una URI `source` externa. Un número de versión del Registry no impone inmutabilidad de objetos ni un hash de contenido.

`run_id` y `model_id` son opcionales en `create_model_version`. El registro desde una URI de origen directa puede no tener un vínculo con la ejecución de entrenamiento. Que el registro sea un puntero, copie artefactos o use otra ubicación de almacenamiento depende del backend y de la operación del Registry; verifique el comportamiento real.

### Alias

`models:/fraud-detector@champion` encuentra la versión del alias **cuando ocurre la resolución/carga**. `models:/fraud-detector/7` es una referencia explícita de versión. Mover un alias no reemplaza automáticamente un modelo ya cargado en memoria o en una caché. Implemente por separado las políticas de despliegue, recarga y caché del controlador de serving, y registre la versión que realmente atiende las solicitudes.

`champion` y `challenger` son nombres definidos por el equipo. No configuran porcentajes de tráfico en vivo/sombra ni ejecutan una evaluación por sí mismos. Una actualización de alias no es evidencia de aprobación de calidad o seguridad.

### El modelo de stage heredado

Los stages heredados son `None`, `Staging`, `Production` y `Archived`. `transition_model_version_stage` está **obsoleto desde la versión 2.9.0** y permanece en la API 3.16.0. No lo describa como eliminado de todas las versiones actuales. Los nuevos flujos de trabajo pueden combinar alias y etiquetas con Registered Models específicos por entorno y permisos explícitos. Un nombre de stage o una etiqueta no constituye control de acceso.

## Registro de un modelo

Después de registrar un modelo de flavor real, llame a `mlflow.register_model(model_uri, name)` o pase `registered_model_name` a la llamada `log_model` del flavor. La API de nivel inferior `MlflowClient.create_model_version` puede especificar directamente un origen. El registro y la reasignación de alias son operaciones independientes.

Este **ejercicio de metadatos del Registry** no crea un modelo capaz de realizar inferencia. Se verificó con Python 3.12, MLflow 3.16.0 y SQLite.

```python
from pathlib import Path
import mlflow
from mlflow import MlflowClient

root = Path(".registry-demo").resolve()
root.mkdir(exist_ok=True)
mlflow.set_tracking_uri(f"sqlite:///{root / 'registry.db'}")
client = MlflowClient()
name = "registry-contract-demo"
# Run once in a fresh demo DB. Inspect the existing name before repeating.
client.create_registered_model(name)
versions = []
for number in (1, 2):
    source = root / f"candidate-{number}"
    source.mkdir(exist_ok=True)
    (source / "metadata.json").write_text('{"fixture": true}')
    versions.append(client.create_model_version(name, source=source.as_uri()))

first, second = versions
assert first.run_id is None
client.update_model_version(name, first.version, description="metadata fixture")
client.set_model_version_tag(name, first.version, "review_state", "demo-only")
client.set_registered_model_alias(name, "champion", first.version)
snapshot = client.get_model_version_by_alias(name, "champion")
client.set_registered_model_alias(name, "champion", second.version)
assert snapshot.version == first.version
assert client.get_model_version_by_alias(name, "champion").version == second.version
```

`READY` es un estado de registro. Como se muestra arriba, se puede registrar un fixture de metadatos sin un flavor de modelo ni pesos; pruebe por separado la compatibilidad de inferencia y los criterios de evaluación. El ejercicio deja su DB local y sus fixtures en `.registry-demo`.

## Gobernanza y el flujo de trabajo de traspaso

1. Registre los artefactos de origen reales, hashes de modelo/código/datos, dependencias y referencias de ejecución/modelo.
2. Evalúe criterios de calidad, seguridad y negocio; conserve la evidencia de aprobación.
3. Un actor autorizado llama a `set_registered_model_alias`. Completar el entrenamiento no constituye una aprobación automática.
4. Los sistemas de serving resuelven la nueva referencia y realizan la recarga o el despliegue. Fije los números de versión y los hashes de artefactos cuando sea necesario para la reproducibilidad y el rollback.

Separar la creación de candidatos de la promoción requiere autenticación, autorización y un pipeline operativo. Una etiqueta como `review_state=approved` por sí sola no restringe el acceso de escritura ni hace que la evidencia de aprobación sea resistente a manipulaciones. Coordine las actualizaciones simultáneas de alias de varios trabajos de despliegue.

![Un consumidor resuelve los alias champion y challenger en referencias de Model Version. La resolución de alias no enruta tráfico ni reemplaza automáticamente un modelo ya cargado.](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## Linaje y reproducibilidad

El linaje solo está tan completo como la información registrada y conservada. El Registry no puede reconstruir posteriormente `run_id`, `model_id`, revisiones de código o hashes de conjuntos de datos faltantes. Los archivos de origen modificados, Runs/Model Versions eliminados y la limpieza de artefactos también pueden dejar enlaces incompletos.

Una auditoría necesita la ID de versión/modelo que realmente atiende, hashes y ubicaciones de artefactos, commit de origen, snapshot del conjunto de datos, dependencias y registros de evaluación/aprobación. Opere conjuntamente las copias de seguridad y la retención de la DB de metadatos y del almacenamiento de artefactos. Un alias no es un registro de auditoría permanente de todos los cambios.

## Próximos pasos

[Parte 3: despliegue de EKS](03-eks-deployment.md) cubre los límites de permisos de servidor, base de datos y artefactos.

## Fuentes principales

- [Model Registry](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [API de cliente del Registry 3.16.0](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [Campos de ModelVersion](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [Implementación del Registry SQL de OSS](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
