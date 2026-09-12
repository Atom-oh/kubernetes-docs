# Cuestionario de Kubeflow Pipelines

Este cuestionario evalúa tu comprensión de la arquitectura de Kubeflow Pipelines, el modelo de compilación YAML de KFP v2 IR, los conceptos principales (Pipeline, Component, Run, Experiment, Artifact, MLMD), las consideraciones de almacenamiento de Artifact en EKS y el comportamiento de la caché.

## Preguntas de opción múltiple

1. ¿Qué motor administra la secuenciación de workflows y la creación de Pods en el backend de KFP 2.16.1 de código abierto utilizado aquí?
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) Kubernetes CronJobs directamente, sin un motor de workflow subyacente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Argo Workflows**

**Explicación:**
Este backend traduce IR para un Run en recursos de Argo Workflow. Argo administra el orden y la creación de Pods; el scheduler de Kubernetes ubica los Pods en nodos. Cargar un pipeline por sí solo no crea un Run.
</details>

2. ¿Cuál es la diferencia arquitectónica clave entre el compilador de KFP v1 SDK y el compilador de KFP v2 SDK?
   - A) v1 compila a IR YAML; v2 compila directamente a Argo Workflow YAML
   - B) v1 compila directamente a Argo Workflow YAML; v2 compila a un Intermediate Representation (IR) YAML independiente del backend
   - C) No hay diferencia — ambos producen resultados idénticos
   - D) v2 eliminó por completo la necesidad de compilación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) v1 compila directamente a Argo Workflow YAML; v2 compila a un Intermediate Representation (IR) YAML independiente del backend**

**Explicación:**
El `dsl-compile` de v1 SDK producía directamente un manifiesto YAML `Workflow` específico de Argo. v2 SDK compila a un IR YAML independiente del backend (`PipelineSpec`) que describe el DAG, los componentes y los artifacts tipados; este backend traduce IR para la creación de Run, sujeto a la compatibilidad de la versión del backend y de las extensiones de plataforma.
</details>

3. ¿Qué componente de Kubeflow Pipelines es responsable de registrar ejecuciones registradas y sus relaciones de artifact de entrada/salida, lo que permite el rastreo de linaje en la UI de KFP?
   - A) El Argo Workflow Controller
   - B) El almacén ML Metadata (MLMD)
   - C) El almacén de artifacts MinIO
   - D) El compilador de KFP SDK

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El almacén ML Metadata (MLMD)**

**Explicación:**
MLMD almacena relaciones de ejecución/artifact registradas, no todos los efectos secundarios externos ni la integridad de los bytes de los archivos. Registra las revisiones y los hashes del código y los datos para lograr reproducibilidad.
</details>

4. En KFP v2 SDK, ¿cómo declara un componente que produce un artifact tipado de tipo `Dataset` para que lo consuman los componentes posteriores?
   - A) Devolviendo un diccionario de Python simple
   - B) Declarando un parámetro tipado como `Output[Dataset]`
   - C) Escribiendo en una ruta codificada de forma fija `/tmp/dataset.csv` sin declaración de tipo
   - D) Estableciendo una variable de entorno llamada `DATASET`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Declarando un parámetro tipado como `Output[Dataset]`**

**Explicación:**
KFP v2 proporciona a los artifacts tipos de primera clase (`Dataset`, `Model`, `Metrics`, etc.). Un parámetro de componente tipado como `Output[Dataset]` declara el tipo y la conexión; el runtime prepara las rutas y transfiere ese artifact a cualquier componente posterior que declare un parámetro `Input[Dataset]` coincidente.
</details>

5. ¿Qué se necesita para usar S3 en lugar de MinIO en la instalación predeterminada revisada?
   - A) El valor predeterminado es S3; el patrón lo cambia a MinIO
   - B) Configurar el pipeline root, el proveedor y la cadena de credenciales para S3 en lugar de MinIO incluido
   - C) No hay un almacén de artifacts predeterminado — siempre se debe configurar uno manualmente
   - D) El valor predeterminado es EFS; el patrón lo cambia a EBS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Configurar el pipeline root, el proveedor y la cadena de credenciales para S3 en lugar de MinIO incluido**

**Explicación:**
El paquete predeterminado incluye MinIO, pero otras instalaciones y los URI de artifact importados pueden diferir. Usa la guía actual del object store de KFP. S3 tiene cargos de almacenamiento/solicitudes/transferencia; la guía de distribución de AWS heredada no es una receta de instalación verificada para la versión actual.
</details>

6. Cuando el almacén de artifacts de KFP apunta a S3 en lugar de MinIO dentro del clúster, ¿qué mecanismo de identidad pasa a ser directamente relevante para el ServiceAccount de ejecución de Run real y los componentes que acceden a artifacts?
   - A) Ninguno — el acceso a S3 funciona sin ninguna configuración de identidad de AWS
   - B) IRSA o Pod Identity con SDK, confianza, soporte de runtime y permisos de S3 restringidos verificados
   - C) Una clave de acceso de AWS codificada de forma fija en la imagen de contenedor de cada componente
   - D) Solo Kubernetes RBAC es suficiente para el acceso a S3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA o Pod Identity con SDK, confianza, soporte de runtime y permisos de S3 restringidos verificados**

**Explicación:**
Una vez que las lecturas/escrituras de artifacts van directamente a AWS en lugar de al endpoint de MinIO dentro del clúster, el ServiceAccount bajo el que se ejecutan los Pods del pipeline KFP necesita un rol de IRSA o una asociación de EKS Pod Identity con permisos sobre ese bucket de S3.
</details>

7. En el pipeline de ejemplo de dos pasos (`prepare_data` -> `train_model`), ¿cómo se pasa el artifact `Dataset` del primer componente al segundo?
   - A) Escribiéndolo en una variable global compartida entre ambos componentes
   - B) Mediante `train_model(input_dataset=prep_task.outputs["output_dataset"])`, conectando la salida declarada del primer componente con la entrada tipada del segundo
   - C) Almacenándolo en una variable de entorno
   - D) Los dos componentes no pueden compartir datos; deben fusionarse en un solo componente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante `train_model(input_dataset=prep_task.outputs["output_dataset"])`, conectando la salida declarada del primer componente con la entrada tipada del segundo**

**Explicación:**
Dentro de la función decorada con `@dsl.pipeline`, `prep_task.outputs["output_dataset"]` se refiere al parámetro `Output[Dataset]` declarado por `prepare_data`, y pasarlo al parámetro `input_dataset: Input[Dataset]` de `train_model` es cómo el SDK conecta la dependencia de artifact entre los dos Pods que se ejecutan de forma independiente.
</details>

8. ¿Cómo decide KFP si reutilizar un resultado en caché en lugar de volver a ejecutar un componente?
   - A) Siempre vuelve a ejecutar cada componente independientemente de las entradas
   - B) Calcula un hash de las entradas del componente (valores de parámetros, nombres/ID de artifacts de entrada y la imagen/comando del contenedor, especificaciones de salida y configuración relacionada) y reutiliza las salidas en caché ante un hash coincidente de una ejecución exitosa anterior
   - C) Vuelve a ejecutar componentes solo si el nombre del pipeline ha cambiado
   - D) El almacenamiento en caché se basa únicamente en el tiempo de reloj transcurrido desde la última ejecución

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Calcula un hash de las entradas del componente (valores de parámetros, nombres/ID de artifacts de entrada y la imagen/comando del contenedor, especificaciones de salida y configuración relacionada) y reutiliza las salidas en caché ante un hash coincidente de una ejecución exitosa anterior**

**Explicación:**
La clave 2.16.1 utiliza valores de parámetros, ID de artifact y configuración de contenedor/salida, no un hash nuevo de los bytes de los archivos. Modificar bytes o una etiqueta de imagen puede dejar la clave sin cambios. La búsqueda se limita al nombre del pipeline y al namespace.

El contenido de los archivos, las etiquetas de imagen mutables y el estado externo no invalidan automáticamente la clave. Registra las versiones/hashes de datos como entradas explícitas o deshabilita la caché.
</details>

## Preguntas de respuesta corta

9. Nombra las dos formas descritas en este capítulo para deshabilitar el comportamiento de caché de KFP.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Por componente, mediante `set_caching_options(enable_caching=False)` en la tarea; por Run, mediante un envío de cliente autenticado con `enable_caching=False`.**

**Explicación:**
`prep_task.set_caching_options(enable_caching=False)` deshabilita la caché para una tarea de componente específica dentro de la función del pipeline. Como alternativa, la caché de todo el envío del pipeline puede deshabilitarse en el momento del envío de Run, en lugar de componente por componente.
</details>

10. ¿Qué produce realmente el paso de compilación de KFP SDK y qué sucede con esa salida una vez que llega al servidor de API de KFP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Produce un Intermediate Representation (IR) YAML — un `PipelineSpec` independiente del backend. Después de la carga y la creación de Run, este backend traduce el IR YAML a un `Workflow` de Argo, cuya creación de Pods es administrada por Argo y cuya ubicación en nodos es administrada por Kubernetes.**

**Explicación:**
La compilación produce IR; el paquete también proporciona API de cliente y soporte de runtime de Python. La creación de Run activa el procesamiento de workflow del backend. Las versiones de IR del backend y las extensiones de plataforma deben ser compatibles.
</details>

## Preguntas prácticas

11. Escribe una función `@dsl.component` llamada `prepare_data` que declare un único parámetro `Output[Dataset]` y escriba un pandas DataFrame en él como CSV.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.12-slim", packages_to_install=["pandas==2.3.3"])
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**Explicación:**
`output_dataset: Output[Dataset]` declara una salida de artifact tipado; el runtime prepara `output_dataset.path` como la ubicación de almacenamiento en la que escribe el componente, que los componentes posteriores pueden declarar entonces como un `Input[Dataset]`.
</details>

12. Escribe una función `@dsl.pipeline` que conecte la salida de `prepare_data` con el parámetro `input_dataset` de un componente `train_model`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```python
from kfp import dsl

@dsl.pipeline(name="data-prep-train-pipeline")
def data_prep_train_pipeline():
    prep_task = prepare_data()
    train_task = train_model(input_dataset=prep_task.outputs["output_dataset"])
```

**Explicación:**
`prep_task.outputs["output_dataset"]` hace referencia al artifact producido por el parámetro `Output[Dataset]` de `prepare_data` (llamado `output_dataset`), y pasarlo como argumento `input_dataset` de `train_model` crea la arista del DAG entre los dos componentes.
</details>

13. Escribe el código para deshabilitar la caché en una única tarea de pipeline llamada `prep_task`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```python
prep_task.set_caching_options(enable_caching=False)
```

**Explicación:**
Llamar a `set_caching_options(enable_caching=False)` en un objeto de tarea dentro de la función del pipeline deshabilita la caché en esa tarea compilada. Un valor explícito de enable_caching en el envío de Run puede anularlo; deja esa opción en None para preservar la configuración compilada.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/02-pipelines.md) | [Siguiente cuestionario: Notebooks](./03-notebooks-quiz.md)
