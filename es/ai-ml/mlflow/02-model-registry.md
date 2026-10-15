# Parte 2: MLflow Model Registry

> **Referencia de revisión**: MLflow 3.16.0; último parche 3.16.1 verificado · 2026-10-12

## Configuración del entorno de laboratorio

Use Python 3.10 o posterior y `mlflow==3.16.0`. Las API del Registry también funcionan con SQLite local; no es obligatorio disponer de un servidor HTTP independiente. El parche 3.16.1 está disponible, pero los ejemplos de este capítulo usan 3.16.0 y no se volvieron a ejecutar con 3.16.1.

Consulte la [Parte 3](03-eks-deployment.md) para el despliegue del equipo y la [Parte 1](01-tracking.md) para la configuración de Tracking. Este capítulo describe MLflow OSS. Los registros administrados, como Databricks Unity Catalog, pueden tener comportamientos diferentes respecto a permisos, copia y retención.

## Qué es el Model Registry

El registry administra nombres lógicos de modelo, versiones numeradas, alias y metadatos. Registrar candidatos, aprobar una promoción y desplegar un endpoint son operaciones independientes. Disponer de un registry no implementa automáticamente el comportamiento de aprobación o serving.

## Conceptos principales

| Entidad | Significado y límite de mutación |
|---|---|
| Registered Model | colección de versiones bajo un nombre lógico como `fraud-detector` |
| Model Version | registro numerado con información de origen; las descripciones, etiquetas y relaciones de etapa/alias pueden cambiar |
| Alias | nombre mutable que apunta a una versión; varios alias pueden apuntar a la misma versión |
| LoggedModel | entidad de modelo de Tracking independiente; distinta de Registered Models y Model Versions |

### Model Version

Los nuevos resultados de modelos normalmente deben convertirse en nuevas versiones. Sin embargo, **no todos los campos de versión ni todos los bytes de artefactos son inmutables**. `update_model_version` cambia las descripciones; las etiquetas de versión también son mutables. Alguien con acceso de escritura puede cambiar archivos en una URI `source` externa. Un número de versión del registry no impone inmutabilidad de objetos ni un hash de contenido.

`run_id` y `model_id` son opcionales en `create_model_version`. Un registro desde una URI de origen directa puede no tener vínculo con una ejecución de entrenamiento. Que el registro sea un puntero, copie artefactos o use otra ubicación de almacenamiento depende del backend y de la operación del registry; verifique el comportamiento real.

### Alias

`models:/fraud-detector@champion` encuentra la versión del alias **cuando se produce la resolución o carga**. `models:/fraud-detector/7` es una referencia explícita a una versión. Mover un alias no reemplaza automáticamente un modelo ya cargado en memoria o en una caché. Implemente por separado las políticas de despliegue, recarga y caché del controlador de serving, y registre la versión que realmente atiende las solicitudes.

`champion` y `challenger` son nombres definidos por el equipo. No configuran porcentajes de tráfico en vivo/sombra ni ejecutan por sí mismos una evaluación. Una actualización de alias no es prueba de aprobación de calidad o seguridad.

### El modelo de etapas heredado

Las etapas heredadas son `None`, `Staging`, `Production` y `Archived`. `transition_model_version_stage` está **obsoleto desde 2.9.0** y permanece en la API 3.16.0. No lo describa como eliminado de todas las versiones actuales. Los flujos de trabajo nuevos pueden combinar alias y etiquetas con Registered Models específicos del entorno y permisos explícitos. Un nombre de etapa o etiqueta no es control de acceso.

## Registrar un modelo

Después de registrar un modelo flavor real, llame a `mlflow.register_model(model_uri, name)` o pase `registered_model_name` a la llamada `log_model` del flavor. La API de nivel inferior `MlflowClient.create_model_version` puede especificar directamente un origen. El registro y la reasignación de alias son operaciones independientes.

Este **ejercicio de metadatos del registry** no crea un modelo capaz de realizar inferencias. Se verificó con Python 3.12, MLflow 3.16.0 y SQLite.

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

`READY` es un estado de registro. Una prueba de metadatos sin un flavor de modelo ni pesos puede registrarse, como se indicó arriba; pruebe por separado la compatibilidad de inferencia y los criterios de evaluación. El ejercicio deja su base de datos local y sus pruebas en `.registry-demo`.

## Gobernanza y el flujo de trabajo de traspaso

1. Registre los artefactos de origen reales, hashes de modelo/código/datos, dependencias y referencias de ejecución/modelo.
2. Evalúe los criterios de calidad, seguridad y negocio; conserve la evidencia de aprobación.
3. Un actor autorizado llama a `set_registered_model_alias`. Completar el entrenamiento no equivale a una aprobación automática.
4. Los sistemas de serving resuelven la nueva referencia y realizan una recarga o despliegue. Fije números de versión y hashes de artefactos cuando sea necesario para la reproducibilidad y la reversión.

Separar la creación de candidatos de la promoción requiere autenticación, autorización y un pipeline operativo. Una etiqueta como `review_state=approved` por sí sola no restringe el acceso de escritura ni vuelve la evidencia de aprobación a prueba de manipulaciones. Coordine las actualizaciones simultáneas de alias de varios trabajos de despliegue.

![Un consumidor resuelve los alias champion y challenger en referencias de Model Version. La resolución de alias no enruta tráfico ni reemplaza automáticamente un modelo ya cargado.](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## Linaje y reproducibilidad

El linaje solo es tan completo como la información registrada y conservada. El registry no puede reconstruir posteriormente `run_id`, `model_id`, revisiones de código o hashes de conjuntos de datos que falten. Los archivos de origen modificados, las Runs/Model Versions eliminadas y la limpieza de artefactos también pueden dejar vínculos incompletos.

Una auditoría necesita la ID de versión/modelo que realmente está en serving, hashes y ubicaciones de artefactos, el commit de origen, la instantánea del conjunto de datos, las dependencias y los registros de evaluación/aprobación. Opere de forma conjunta las copias de seguridad y la retención de la base de datos de metadatos y del almacenamiento de artefactos. Un alias no es un registro de auditoría permanente de todos los cambios.

## Próximos pasos

[Parte 3: Despliegue de EKS](03-eks-deployment.md) cubre los límites de permisos de servidor, base de datos y artefactos.

## Fuentes principales

- [Model Registry](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [API de cliente del Registry 3.16.0](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [Campos de ModelVersion](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [Implementación del registry SQL OSS](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
