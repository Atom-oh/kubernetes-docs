# Parte 2: Kubeflow Pipelines

> **Versiones compatibles**: Kubeflow Pipelines 2.16.1, Kubeflow Community Distribution 26.03.1
> **Última actualización**: September 12, 2026

## Preparación del entorno de laboratorio

La compilación local requiere Python y `kfp==2.16.1`; este capítulo se verificó con Python 3.12. La compilación no se comunica con un clúster. La ejecución remota necesita un backend de KFP compatible, un cliente autenticado y permisos de namespace. S3 requiere además workload identity para la ServiceAccount de ejecución real y para los componentes que acceden a los artefactos.

## Qué es Kubeflow Pipelines

KFP conecta componentes mediante parámetros y artefactos tipados, y hace seguimiento de las ejecuciones (runs). El backend de KFP 2.16.1 de código abierto que se usa aquí traduce el IR a Argo Workflows. Argo gestiona el orden del workflow y la creación de Pods; el scheduler de Kubernetes coloca los Pods en los nodos. Las tareas en caché, los importers y los DAG anidados implican que no toda tarea lógica corresponde a una ejecución separada de un contenedor de usuario.

## Arquitectura de KFP v2: IR YAML y ejecución en el backend

Community Distribution 26.03.1 incluye KFP 2.16.1. La antigua ruta de compilación predeterminada de v1 producía YAML de Argo Workflow; en v2, `Compiler().compile(...)` produce IR YAML basado en PipelineSpec. Subir o almacenar un pipeline y crear un Run son operaciones distintas. La subida por sí sola no lo ejecuta.

El IR evita escribir objetos de Argo directamente, pero no garantiza una portabilidad ilimitada a cualquier backend. Las versiones de IR/SDK, las funcionalidades compatibles, las extensiones de plataforma de Kubernetes, la autenticación y el almacenamiento deben coincidir con el destino. El paquete `kfp` también proporciona APIs de cliente y soporte para la ejecución de componentes en Python; su función no termina en la compilación.

## Conceptos clave

| Concepto | Función y alcance |
| --- | --- |
| Pipeline | Grafo creado con `@dsl.pipeline`; las definiciones/versiones subidas y las ejecuciones son cosas distintas |
| Component / Task | Definición de componente reutilizable y una invocación en el grafo; el Python ligero es una forma más, junto con contenedores, importers y grafos |
| Run / Experiment | Ejecución con entradas y un grupo de ejecuciones relacionadas; distinto del CRD Experiment de Katib |
| Parameter | Cadenas, números y valores de entrada/salida estructurados pequeños |
| Artifact | Objeto de tipo Dataset/Model/Metrics con URI, tipo y metadatos; no necesariamente un único archivo |
| MLMD | Ejecuciones, artefactos y relaciones registrados; no es un registro automático de cada efecto secundario externo ni de la integridad de los archivos |

Los registros de metadatos y los bytes de los artefactos son cosas separadas. Registra las revisiones y los hashes del código, la imagen y los datos cuando importen la reproducibilidad y la verificación del contenido.

## Cómo fluye la ejecución de un pipeline por el sistema

![Flujo de ejecución de Kubeflow Pipelines: un pipeline escrito con el DSL de Python se compila a IR YAML y se envía al servidor de API de KFP, se traduce en un Argo Workflow que ejecuta los Pods de los componentes, los cuales escriben artefactos en S3/MinIO y registran metadatos en MLMD.](../../.gitbook/assets/en-ai-ml-kubeflow-02-pipelines-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-02-pipelines-0.html)

La compilación es local. Tras la creación del Run, cooperan el servidor de API, Argo, el driver/launcher de KFP y los contenedores de usuario. El launcher y el runtime se encargan de las rutas de los artefactos, la transferencia y los metadatos. La colocación en nodos de Kubernetes sigue siendo algo aparte de la secuenciación del workflow por parte de Argo.

## Almacenamiento de artefactos específico de EKS

La instalación predeterminada de la distribución revisada incluye MinIO, pero no todas las instalaciones de KFP ni todas las URI de artefactos lo usan. Inspecciona el pipeline root, las URI importadas y la configuración del proveedor. Los artefactos orientados a metadatos, como Metrics, no son necesariamente archivos de métricas.

Para S3, configura `pipeline_root`, el proveedor y la cadena de credenciales siguiendo la [guía actual de object store](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/). S3 genera cargos por almacenamiento, solicitudes y transferencia; no es un servicio de artefactos gratuito por defecto.

No asumas que `pipeline-runner` es la ServiceAccount de ejecución en todos los entornos. Inspecciona la cuenta seleccionada por el Run y los Pods reales, además de los accesos que necesitan el servidor de API y el launcher. IRSA está documentado en la guía actual. Pod Identity requiere verificar el soporte del SDK, el agente, la asociación y el runtime; este capítulo no ejecutó la integración con AWS. La [Parte 1](01-architecture-installation.md) explica estos límites y la limitación de instalación de la antigua distribución de AWS.

## Un pipeline sencillo de dos pasos

Lo siguiente ilustra un pipeline mínimo `data-prep -> train` usando los decoradores del SDK de KFP v2, con un artefacto `Dataset` tipado que se pasa del primer componente al segundo:

```python
from kfp import dsl, compiler
from kfp.dsl import Dataset, Model, Output, Input

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    # In a real pipeline this would read from S3 or another source
    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)

@dsl.component(base_image="python:3.12-slim", packages_to_install=["scikit-learn==1.7.2", "pandas==2.3.3"])
def train_model(input_dataset: Input[Dataset], output_model: Output[Model]):
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    import pickle

    df = pd.read_csv(input_dataset.path)
    clf = LogisticRegression().fit(df[["feature"]], df["label"])
    with open(output_model.path, "wb") as f:
        pickle.dump(clf, f)

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])

compiler.Compiler().compile(
    pipeline_func=data_prep_train_pipeline,
    package_path="data_prep_train_pipeline.yaml",
)
```

La conexión de `Output[Dataset]` a `Input[Dataset]` registra una dependencia en el grafo y el tipo de artefacto. La preparación real de `.path` y la transferencia ocurren en tiempo de ejecución. La compilación no valida el almacenamiento ni el entrenamiento.

Estos son componentes ligeros de Python. `@dsl.component` extrae el código de la función; no construye imágenes automáticamente. `packages_to_install` instala las dependencias en tiempo de ejecución dentro de la imagen base. El ejemplo anterior omitía pandas en prepare_data; ahora ambos componentes declaran sus dependencias y sus cuerpos de función se verificaron localmente. Para producción, precompila las dependencias en un contenedor, fija su digest y prueba ese contenedor por separado. El tag de la imagen de Python y las dependencias transitivas aquí no constituyen una build completamente bloqueada.

Carga únicamente el pickle de confianza generado por este ejercicio. Cargar un pickle externo puede ejecutar código arbitrario. Este modelo diminuto demuestra la API y no es un resultado de validación de la calidad del modelo.

## Comportamiento de la caché

En 2.16.1 la clave incluye los valores de los parámetros de entrada, los **nombres/IDs** de los artefactos de entrada, las especificaciones de salida, la cadena de la imagen del contenedor, el comando y los argumentos, y los nombres de PVC. La búsqueda en caché está delimitada por el nombre del pipeline y el namespace. No lee ni calcula el hash de los bytes de los archivos de los artefactos de entrada en cada búsqueda.

Por tanto, modificar un archivo detrás del mismo ID de artefacto, un tag de imagen o el estado de una base de datos o API externa puede dejar la clave sin cambios. Los metadatos ya existentes en caché tampoco garantizan que los objetos de salida eliminados sigan siendo legibles más adelante. Pasa las versiones o los hashes de los datos como parámetros explícitos y considera deshabilitar la caché cuando haya estado externo mutable o efectos secundarios.

```python
# Inside the pipeline function, disable caching for this task.
prep_task.set_caching_options(enable_caching=False)
```

En un cliente autenticado, `create_run_from_pipeline_package(..., enable_caching=False)` sobrescribe la configuración de caché de las tareas para ese Run; `None` conserva la configuración compilada de las tareas. Los valores predeterminados de la CLI y `KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT` también pueden cambiar los valores predeterminados de compilación; define la variable de entorno antes de importar KFP.

## Validación y fuentes

El IR se compiló con Python 3.12 / KFP 2.16.1 y se comprobaron las dependencias, los tipos y la configuración de caché. Los cuerpos de las funciones se ejecutaron localmente en CPU con pandas 2.3.3 / scikit-learn 1.7.2. No se probaron Docker, Argo, la reutilización de caché en el clúster, S3 ni la ejecución con Pod Identity.

- [Implementación de la clave de caché en 2.16.1](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/cacheutils/cache.go)
- [Búsqueda y reutilización de caché en 2.16.1](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/driver/cache.go)
- [Guía oficial de caché](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/caching/)
- [Componentes ligeros de Python](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/)

## Próximos pasos

Con los pipelines escritos, compilados y en ejecución, la siguiente pregunta suele ser dónde ocurre, en primer lugar, el trabajo de desarrollo interactivo que hay detrás de esos componentes del pipeline. La [Parte 3: Kubeflow Notebooks](./03-notebooks.md) cubre los entornos de notebook por usuario que los equipos utilizan para escribir e iterar el código que acaba empaquetado en los componentes del pipeline; y, más adelante en esta serie, la [Parte 6: KServe — Servicio de modelos en Kubernetes](./06-kserve.md) cubre el servicio de los modelos que esos pipelines producen al final.

[Volver a la página principal](./README.md)

## Cuestionario

Para poner a prueba lo aprendido en este capítulo, prueba el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/02-pipelines-quiz.md).
