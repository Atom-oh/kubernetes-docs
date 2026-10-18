# Parte 2: Kubeflow Pipelines

> **Versiones compatibles**: Kubeflow Pipelines 2.16.1, Kubeflow Community Distribution 26.03.1
> **Última versión independiente comprobada**: KFP 2.17.2 (4 de septiembre de 2026; el SDK `kfp` más reciente en PyPI: 2.17.0), comprobado el 12 de octubre de 2026; los ejemplos usan 2.16.1
> **Última actualización**: 12 de octubre de 2026

## Configuración del entorno del laboratorio

La compilación local requiere Python y `kfp==2.16.1`; este capítulo se comprobó con Python 3.12. KFP 2.17.2 está disponible upstream (el paquete más reciente del SDK `kfp` en PyPI es 2.17.0), pero esta versión fijada coincide con Community Distribution 26.03.1. No valida una nueva combinación de SDK y backend.

La compilación no se conecta a un clúster. La ejecución remota requiere un backend KFP compatible, un cliente autenticado y permisos de espacio de nombres. S3 también requiere identidad de carga de trabajo para el ServiceAccount de ejecución y componentes que accedan a artefactos.

## Qué es Kubeflow Pipelines

KFP conecta componentes mediante parámetros y artefactos tipados, y realiza un seguimiento de las ejecuciones. El backend de código abierto de KFP 2.16.1 que se usa aquí traduce IR a Argo Workflows. Argo administra el orden del flujo de trabajo y la creación de Pods; el planificador de Kubernetes ubica los Pods en los nodos. Las tareas almacenadas en caché, los importadores y los DAG anidados implican que no todas las tareas lógicas corresponden a una ejecución independiente de un contenedor de usuario.

## Arquitectura de KFP v2: IR YAML y ejecución del backend

Community Distribution 26.03.1 incluye KFP 2.16.1. La ruta de compilación predeterminada heredada de v1 generaba YAML de Argo Workflow; `Compiler().compile(...)` de v2 genera IR YAML basado en PipelineSpec. Subir/almacenar un pipeline y crear una ejecución son operaciones distintas. Subirlo por sí solo no lo ejecuta.

IR evita escribir objetos de Argo directamente, pero no garantiza portabilidad irrestricta a todos los backends. Las versiones de IR/SDK, las funciones compatibles, las extensiones de la plataforma Kubernetes, la autenticación y el almacenamiento deben coincidir con el destino. El paquete `kfp` también proporciona API de cliente y compatibilidad con la ejecución de componentes de Python; su función no termina con la compilación.

## Conceptos básicos

| Concepto | Función y alcance |
| --- | --- |
| Pipeline | Grafo creado con `@dsl.pipeline`; las definiciones/versiones subidas y las ejecuciones son entidades distintas |
| Componente / Tarea | Definición de componente reutilizable e invocación en un grafo; Python ligero es una modalidad, junto con contenedores, importadores y grafos |
| Run / Experiment | Ejecución con entradas y un grupo de ejecuciones relacionadas; distinto del CRD Experiment de Katib |
| Parámetro | Cadenas, números y valores de entrada/salida estructurados pequeños |
| Artefacto | Objeto de tipo Dataset/Model/Metrics con URI, tipo y metadatos; no necesariamente un solo archivo |
| MLMD | Registra ejecuciones, artefactos y relaciones; no registra automáticamente todos los efectos secundarios externos ni la integridad de los archivos |

Los registros de metadatos y los bytes de los artefactos son independientes. Registra las revisiones y los hashes del código, la imagen y los datos cuando sean importantes la reproducibilidad y la verificación del contenido.

## Cómo fluye una ejecución de pipeline por el sistema

![Flujo de ejecución de Kubeflow Pipelines: un pipeline DSL de Python se compila a IR YAML y se envía al servidor de API de KFP, se traduce a un Argo Workflow que ejecuta Pods de componentes, los cuales escriben artefactos en S3/MinIO y registran metadatos en MLMD.](../../.gitbook/assets/en-ai-ml-kubeflow-02-pipelines-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-02-pipelines-0.html)

La compilación es local. Después de crear la ejecución, colaboran el servidor de API, Argo, el driver/launcher de KFP y los contenedores de usuario. El launcher/entorno de ejecución gestiona las rutas de los artefactos, la transferencia y los metadatos. La ubicación de los nodos de Kubernetes sigue siendo independiente de la secuenciación del flujo de trabajo de Argo.

## Almacenamiento de artefactos específico de EKS

La instalación de la distribución revisada incluye MinIO de forma predeterminada, pero no todas las instalaciones de KFP ni todos los URI de artefactos lo usan. Inspecciona la raíz del pipeline, los URI importados y la configuración del proveedor. Los artefactos orientados a metadatos, como Metrics, no son necesariamente archivos de métricas.

Para S3, configura `pipeline_root`, el proveedor y la cadena de credenciales siguiendo la [guía actual de almacenamiento de objetos](https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/). S3 genera cargos por almacenamiento, solicitudes y transferencia; no es un servicio de artefactos gratuito y predeterminado.

No des por sentado que `pipeline-runner` es el ServiceAccount de ejecución en todos los entornos. Inspecciona la cuenta seleccionada para la ejecución y los Pods reales, además del acceso que necesita el servidor de API/launcher. IRSA está documentado en la guía actual. Pod Identity requiere verificar la compatibilidad del SDK, el agente, la asociación y el entorno de ejecución; en este capítulo no se ejecutó ninguna integración con AWS. [La Parte 1](01-architecture-installation.md) explica estos límites y la limitación de instalación de la distribución heredada de AWS.

## Un pipeline sencillo de dos pasos

A continuación se muestra un pipeline mínimo `data-prep -> train` que usa los decoradores del SDK de KFP v2 y pasa un artefacto `Dataset` tipado del primer componente al segundo:

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

La conexión de `Output[Dataset]` a `Input[Dataset]` registra una dependencia del grafo y el tipo de artefacto. La preparación y transferencia reales de `.path` ocurren durante la ejecución. La compilación no valida el almacenamiento ni el entrenamiento.

Estos son componentes ligeros de Python. `@dsl.component` extrae el código de la función; no crea imágenes automáticamente. `packages_to_install` instala dependencias durante la ejecución en la imagen base. El ejemplo anterior omitía pandas en prepare_data; ahora ambos componentes declaran sus dependencias y sus cuerpos de función se comprobaron localmente. Para producción, crea previamente una imagen con las dependencias, fija su digest y prueba esa imagen por separado. La etiqueta de la imagen de Python y sus dependencias transitivas no constituyen una compilación completamente bloqueada.

Carga únicamente el pickle de confianza producido por este ejercicio. Cargar un pickle externo puede ejecutar código arbitrario. Este pequeño modelo demuestra la API, no es un resultado de validación de la calidad del modelo.

## Comportamiento de la caché

En 2.16.1, la clave incluye los valores de los parámetros de entrada, los **nombres/ID** de los artefactos de entrada, las especificaciones de salida, la cadena de la imagen del contenedor, el comando/los argumentos y los nombres de los PVC. La búsqueda en caché tiene como ámbito el nombre del pipeline y el espacio de nombres. No lee ni calcula el hash de los bytes de los archivos de artefactos de entrada en cada búsqueda.

Por lo tanto, modificar un archivo asociado al mismo ID de artefacto, una etiqueta de imagen o el estado de una base de datos/API externa puede dejar la clave sin cambios. Los metadatos almacenados en caché tampoco garantizan que los objetos de salida eliminados sigan siendo legibles en etapas posteriores. Pasa las versiones/hashes de los datos como parámetros explícitos y considera desactivar la caché cuando haya estado externo mutable o efectos secundarios.

```python
# Inside the pipeline function, disable caching for this task.
prep_task.set_caching_options(enable_caching=False)
```

El argumento `create_run_from_pipeline_package(..., enable_caching=False)` de un cliente autenticado anula la configuración de caché de las tareas para la ejecución; `None` conserva la configuración compilada de las tareas. Los valores predeterminados de la CLI y `KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT` también pueden cambiar los valores predeterminados de compilación; establece la variable de entorno antes de importar KFP.

## Validación y fuentes

IR se compiló con Python 3.12 / KFP 2.16.1 y se comprobó la presencia de dependencias, tipos y configuración de caché. Los cuerpos de las funciones se ejecutaron localmente en CPU con pandas 2.3.3 / scikit-learn 1.7.2. No se probaron Docker, Argo, la reutilización de la caché del clúster, S3 ni la ejecución de Pod Identity.

- [Implementación de la clave de caché de 2.16.1](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/cacheutils/cache.go)
- [Búsqueda y reutilización de caché de 2.16.1](https://github.com/kubeflow/pipelines/blob/2.16.1/backend/src/v2/driver/cache.go)
- [Guía oficial de almacenamiento en caché](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/caching/)
- [Componentes ligeros de Python](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/)

## Próximos pasos

Una vez creados, compilados y en ejecución los pipelines, la siguiente pregunta suele ser dónde se lleva a cabo el trabajo de desarrollo interactivo que hay detrás de esos componentes. [Parte 3: Kubeflow Notebooks](./03-notebooks.md) trata los entornos de notebooks por usuario que los equipos utilizan para crear e iterar sobre el código que acaba empaquetado en componentes de pipeline. Más adelante en esta serie, [Parte 6: KServe (servicio de modelos en Kubernetes)](./06-kserve.md) trata cómo servir los modelos que esos pipelines producen.

[Volver a la página principal](./README.md)

## Cuestionario

Para poner a prueba lo que has aprendido en este capítulo, prueba el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/02-pipelines-quiz.md).
