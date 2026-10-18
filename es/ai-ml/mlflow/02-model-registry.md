# Parte 2: Registro de modelos de MLflow

> **Base de revisión**: MLflow 3.16.0; se comprobó la versión más reciente, 3.17.1 · 2026-10-16

## Configuración del entorno de laboratorio

Usa Python 3.10 o posterior y `mlflow==3.16.0`. Las API del registro también funcionan con SQLite local; no es obligatorio usar un servidor HTTP independiente. Están disponibles el parche 3.16.1 y la línea posterior 3.17.x (la versión más reciente es la 3.17.1), pero los ejemplos de este capítulo usan 3.16.0 y no se volvieron a ejecutar con ninguna versión posterior.

Consulta la [Parte 3](03-eks-deployment.md) para el despliegue del equipo y la [Parte 1](01-tracking.md) para la configuración de Tracking. Este capítulo describe MLflow OSS. Los registros gestionados, como Databricks Unity Catalog, pueden tener permisos, comportamiento de copia y políticas de retención diferentes.

## Qué es el registro de modelos

El registro administra nombres lógicos de modelos, versiones numeradas, alias y metadatos. Registrar candidatos, aprobar una promoción y desplegar un endpoint son operaciones distintas. Tener un registro no implementa automáticamente un proceso de aprobación ni el comportamiento de servicio.

## Conceptos fundamentales

| Entidad | Significado y límites de modificación |
|---|---|
| Modelo registrado | colección de versiones bajo un nombre lógico, como `fraud-detector` |
| Versión del modelo | registro numerado con información de origen; las descripciones, las etiquetas y las relaciones de etapa/alias pueden cambiar |
| Alias | nombre modificable que apunta a una versión; varios alias pueden apuntar a la misma versión |
| LoggedModel | entidad independiente de modelo de Tracking; distinta de los modelos registrados y de las versiones del modelo |

### Versión del modelo

Por lo general, los nuevos resultados de modelos deberían convertirse en versiones nuevas. Sin embargo, **no todos los campos de una versión ni los bytes de sus artefactos son inmutables**. `update_model_version` modifica las descripciones; las etiquetas de las versiones también son modificables. Alguien con acceso de escritura puede cambiar los archivos en una URI `source` externa. El número de versión del registro no garantiza la inmutabilidad del objeto ni un hash del contenido.

`run_id` y `model_id` son opcionales en `create_model_version`. El registro a partir de una URI de origen directa puede no tener un vínculo con una ejecución de entrenamiento. Que el registro sea un puntero, copie artefactos o use otra ubicación de almacenamiento depende del backend del registro y de la operación; verifica el comportamiento real.

### Alias

`models:/fraud-detector@champion` encuentra la versión del alias **cuando se resuelve o se carga**. `models:/fraud-detector/7` es una referencia explícita a una versión. Cambiar un alias no reemplaza automáticamente un modelo que ya está cargado en memoria o en una caché. Implementa por separado las políticas del controlador de despliegue para el servicio, la recarga y la caché, y registra qué versión está atendiendo realmente las solicitudes.

`champion` y `challenger` son nombres definidos por el equipo. No configuran porcentajes de tráfico en vivo o en modo sombra ni ejecutan una evaluación. Actualizar un alias no demuestra que se haya aprobado la calidad o la seguridad.

### El modelo de etapas heredado

Las etapas heredadas son `None`, `Staging`, `Production` y `Archived`. `transition_model_version_stage` está **en desuso desde la versión 2.9.0** y sigue presente en la API de la versión 3.16.0. No afirmes que se eliminó de todas las versiones actuales. Los flujos de trabajo nuevos pueden combinar alias y etiquetas con modelos registrados específicos de cada entorno y permisos explícitos. Un nombre de etapa o una etiqueta no son controles de acceso.

## Registro de un modelo

Después de registrar un modelo real de un flavor, llama a `mlflow.register_model(model_uri, name)` o pasa `registered_model_name` a la llamada `log_model` del flavor. La API de nivel inferior `MlflowClient.create_model_version` permite especificar directamente un origen. El registro y la reasignación de alias son operaciones independientes.

Este **ejercicio de metadatos del registro** no crea un modelo capaz de realizar inferencias. Se comprobó con Python 3.12, MLflow 3.16.0 y SQLite.

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

`READY` es un estado de registro. Se puede registrar un artefacto de metadatos sin un flavor de modelo ni pesos, como en el ejemplo; comprueba por separado la compatibilidad con la inferencia y los criterios de evaluación. El ejercicio deja la base de datos local y los archivos de prueba en `.registry-demo`.

## Gobernanza y flujo de traspaso

1. Registra los artefactos de origen reales, los hashes del modelo, del código y de los datos, las dependencias y las referencias a la ejecución y al modelo.
2. Evalúa la calidad, la seguridad y los criterios de negocio; conserva las pruebas de aprobación.
3. Un actor autorizado llama a `set_registered_model_alias`. Completar el entrenamiento no implica una aprobación automática.
4. Los sistemas de servicio resuelven la nueva referencia y realizan una recarga o un despliegue. Fija los números de versión y los hashes de los artefactos cuando sea necesario para la reproducibilidad y la reversión.

Separar la creación de candidatos de su promoción requiere autenticación, autorización y una canalización operativa. Una etiqueta como `review_state=approved`, por sí sola, no restringe el acceso de escritura ni convierte las pruebas de aprobación en elementos a prueba de manipulaciones. Coordina las actualizaciones simultáneas de alias realizadas por varios trabajos de despliegue.

![Un consumidor resuelve los alias champion y challenger en referencias a versiones del modelo. La resolución de alias no enruta el tráfico ni reemplaza automáticamente un modelo que ya está cargado.](../../.gitbook/assets/en-ai-ml-mlflow-02-model-registry-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-mlflow-02-model-registry-0.html)

## Linaje y reproducibilidad

El linaje solo es tan completo como la información que se registra y se conserva. El registro no puede reconstruir posteriormente los valores faltantes de `run_id`, `model_id`, las revisiones del código ni los hashes de los conjuntos de datos. Los cambios en los archivos de origen, la eliminación de ejecuciones o versiones del modelo y la limpieza de artefactos también pueden dejar vínculos incompletos.

Una auditoría necesita el ID de la versión o del modelo que realmente está en servicio, los hashes y las ubicaciones de los artefactos, el commit de origen, la instantánea del conjunto de datos, las dependencias y los registros de evaluación y aprobación. Gestiona conjuntamente las copias de seguridad y la retención de la base de datos de metadatos y del almacén de artefactos. Un alias no es un registro de auditoría permanente de todos los cambios.

## Próximos pasos

La [Parte 3: Despliegue en EKS](03-eks-deployment.md) cubre los límites de permisos del servidor, la base de datos y los artefactos.

## Fuentes principales

- [Registro de modelos](https://mlflow.org/docs/3.16.0/ml/model-registry/)
- [API del cliente del registro de la versión 3.16.0](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/tracking/client.py)
- [Campos de ModelVersion](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/entities/model_registry/model_version.py)
- [Implementación del registro SQL de OSS](https://github.com/mlflow/mlflow/blob/v3.16.0/mlflow/store/model_registry/sqlalchemy_store.py)

[Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/mlflow/02-model-registry-quiz.md)
