# Cuestionario de Kubeflow Pipelines

Este cuestionario evalúa tu comprensión de la arquitectura de Kubeflow Pipelines, el modelo de compilación YAML de KFP v2 IR, los conceptos fundamentales (Pipeline, Component, Run, Experiment, Artifact, MLMD), las consideraciones sobre el almacenamiento de Artifact en EKS y el comportamiento de caché.

## Preguntas de opción múltiple

1. ¿Qué motor de workflow utiliza internamente el backend de Kubeflow Pipelines para programar y ejecutar realmente los Pods de los pasos de un pipeline?
   - A) Apache Airflow
   - B) Argo Workflows
   - C) Tekton Pipelines
   - D) Kubernetes CronJobs directamente, sin ningún motor de workflow subyacente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Argo Workflows**

**Explicación:**
El backend de KFP se construye sobre Argo Workflows. Una vez que un pipeline compilado llega al servidor de API de KFP, se traduce en un recurso `Workflow` de Argo, y el controlador de Argo crea y secuencia los Pods. KFP incorpora encima un SDK de Python, una UI, seguimiento de Experiment/Run y el almacén MLMD.
</details>

2. ¿Cuál es la diferencia arquitectónica clave entre el compilador del SDK de KFP v1 y el compilador del SDK de KFP v2?
   - A) v1 compila a IR YAML; v2 compila directamente a Argo Workflow YAML
   - B) v1 compila directamente a Argo Workflow YAML; v2 compila a un YAML de Intermediate Representation (IR) independiente del backend
   - C) No hay diferencia — ambos producen una salida idéntica
   - D) v2 eliminó por completo la necesidad de compilación

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) v1 compila directamente a Argo Workflow YAML; v2 compila a un YAML de Intermediate Representation (IR) independiente del backend**

**Explicación:**
El `dsl-compile` del SDK v1 producía directamente un manifiesto YAML `Workflow` específico de Argo. El SDK v2 compila a un YAML IR (`PipelineSpec`) independiente del backend que describe el DAG, los componentes y los artifacts tipados; el backend de KFP traduce ese IR a un `Workflow` de Argo en el momento del envío.
</details>

3. ¿Qué componente de Kubeflow Pipelines es responsable de registrar cada ejecución de Component, sus entradas/salidas y los artifacts que utilizó, permitiendo el rastreo de linaje en la UI de KFP?
   - A) El controlador de Argo Workflow
   - B) El almacén de ML Metadata (MLMD)
   - C) El almacén de artifacts de MinIO
   - D) El compilador del SDK de KFP

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El almacén de ML Metadata (MLMD)**

**Explicación:**
MLMD (normalmente respaldado por MySQL) registra cada ejecución de Component junto con sus entradas, salidas y artifacts utilizados. Esto permite que la UI de KFP rastree un modelo entrenado hasta el dataset y el código exactos que lo produjeron, a través de las ejecuciones.
</details>

4. En el SDK de KFP v2, ¿cómo declara un componente que produce un artifact tipado de tipo `Dataset` para que lo consuman los componentes posteriores?
   - A) Devolviendo un diccionario de Python sin formato
   - B) Declarando un parámetro tipado como `Output[Dataset]`
   - C) Escribiendo en una ruta codificada `/tmp/dataset.csv` sin declaración de tipo
   - D) Estableciendo una variable de entorno denominada `DATASET`

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Declarando un parámetro tipado como `Output[Dataset]`**

**Explicación:**
KFP v2 proporciona a los artifacts tipos de primera clase (`Dataset`, `Model`, `Metrics`, etc.). Un parámetro de componente tipado como `Output[Dataset]` indica al SDK que aprovisione una ruta de almacenamiento y conecte ese artifact con cualquier componente posterior que declare un parámetro `Input[Dataset]` coincidente.
</details>

5. ¿Cuál es el backend predeterminado de almacenamiento de artifacts de KFP si no se reconfigura nada y qué cambia respecto a él el patrón de S3 del proyecto `awslabs/kubeflow-manifests`?
   - A) El valor predeterminado es S3; el patrón lo cambia a MinIO
   - B) El valor predeterminado es un despliegue de MinIO dentro del clúster; el patrón reconfigura la raíz del pipeline y las credenciales del almacén de artifacts para usar S3 en su lugar
   - C) No hay almacén de artifacts predeterminado — siempre se debe configurar uno manualmente
   - D) El valor predeterminado es EFS; el patrón lo cambia a EBS

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El valor predeterminado es un despliegue de MinIO dentro del clúster; el patrón reconfigura la raíz del pipeline y las credenciales del almacén de artifacts para usar S3 en su lugar**

**Explicación:**
KFP se distribuye con un despliegue de MinIO dentro del clúster como almacén de artifacts predeterminado. En EKS, esto implica ejecutar un servicio con estado adicional que duplica lo que S3 ya proporciona. `awslabs/kubeflow-manifests` documenta cómo reconfigurar la raíz del pipeline y las credenciales de artifacts para que los componentes lean y escriban directamente en S3.
</details>

6. Cuando el almacén de artifacts de KFP apunta a S3 en lugar de MinIO dentro del clúster, ¿qué mecanismo de identidad pasa a ser directamente relevante para los Pods de pipeline de KFP (por ejemplo, el ServiceAccount `pipeline-runner`)?
   - A) Ninguno — el acceso a S3 funciona sin ninguna configuración de identidad de AWS
   - B) IRSA o EKS Pod Identity, que otorga al ServiceAccount permisos sobre el bucket de S3
   - C) Una clave de acceso de AWS codificada dentro de la imagen de contenedor de cada componente
   - D) Kubernetes RBAC por sí solo es suficiente para el acceso a S3

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) IRSA o EKS Pod Identity, que otorga al ServiceAccount permisos sobre el bucket de S3**

**Explicación:**
Una vez que las lecturas/escrituras de artifacts van directamente a AWS en vez de al endpoint de MinIO dentro del clúster, el ServiceAccount con el que se ejecutan los Pods de pipeline de KFP necesita un rol de IRSA o una asociación de EKS Pod Identity con permisos sobre ese bucket de S3.
</details>

7. En el pipeline de ejemplo de dos pasos (`prepare_data` -> `train_model`), ¿cómo se pasa el artifact `Dataset` del primer componente al segundo?
   - A) Escribiéndolo en una variable global compartida entre ambos componentes
   - B) Mediante `train_model(input_dataset=prep_task.outputs["output_dataset"])`, conectando la salida declarada del primer componente con la entrada tipada del segundo
   - C) Almacenándolo en una variable de entorno
   - D) Los dos componentes no pueden compartir datos; deben fusionarse en un componente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Mediante `train_model(input_dataset=prep_task.outputs["output_dataset"])`, conectando la salida declarada del primer componente con la entrada tipada del segundo**

**Explicación:**
Dentro de la función decorada con `@dsl.pipeline`, `prep_task.outputs["output_dataset"]` se refiere al parámetro declarado `Output[Dataset]` de `prepare_data`, y pasarlo al parámetro `input_dataset: Input[Dataset]` de `train_model` es cómo el SDK conecta la dependencia de artifact entre los dos Pods que se ejecutan de forma independiente.
</details>

8. ¿Cómo decide KFP si reutiliza un resultado en caché en lugar de volver a ejecutar un componente?
   - A) Siempre vuelve a ejecutar todos los componentes independientemente de las entradas
   - B) Aplica hash a las entradas del componente (valores de parámetros, contenido de artifacts de entrada y la definición propia del componente) y reutiliza las salidas en caché cuando hay un hash coincidente de una ejecución exitosa anterior
   - C) Vuelve a ejecutar componentes solo si el nombre del pipeline ha cambiado
   - D) La caché se basa exclusivamente en el tiempo transcurrido desde la última ejecución

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Aplica hash a las entradas del componente (valores de parámetros, contenido de artifacts de entrada y la definición propia del componente) y reutiliza las salidas en caché cuando hay un hash coincidente de una ejecución exitosa anterior**

**Explicación:**
KFP almacena en caché la ejecución de un componente aplicando hash a sus entradas. Una ejecución posterior que envía un componente con un hash de entrada coincidente omite la nueva ejecución y reutiliza las salidas almacenadas previamente en caché.
</details>

## Preguntas de respuesta corta

9. Nombra las dos formas descritas en este capítulo para deshabilitar el comportamiento de caché de KFP.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Por componente, mediante `set_caching_options(enable_caching=False)` en la tarea; por ejecución, mediante el interruptor de caché disponible en el cuadro de diálogo de envío de Run de la UI de KFP.**

**Explicación:**
`prep_task.set_caching_options(enable_caching=False)` deshabilita la caché para una tarea de Component específica dentro de la función del pipeline. Como alternativa, la caché de todo el envío del pipeline se puede deshabilitar en el momento de enviar el Run, en vez de hacerlo componente por componente.
</details>

10. ¿Qué produce realmente el paso de compilación del SDK de KFP y qué ocurre con esa salida cuando llega al servidor de API de KFP?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: Produce un YAML de Intermediate Representation (IR) — un `PipelineSpec` independiente del backend. Una vez en el servidor de API, el backend traduce ese YAML IR a un `Workflow` de Argo, que el controlador de Argo programa después como Pods.**

**Explicación:**
El trabajo del SDK de KFP termina al producir el YAML IR. Todo lo que ocurre desde el servidor de API en adelante —la traducción a Argo Workflow y la programación de Pods— es responsabilidad del backend, lo que hace que el YAML IR sea, en principio, independiente del backend.
</details>

## Preguntas prácticas

11. Escribe una función `@dsl.component` llamada `prepare_data` que declare un único parámetro `Output[Dataset]` y escriba un DataFrame de pandas en él como CSV.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```python
from kfp import dsl
from kfp.dsl import Dataset, Output

@dsl.component(base_image="python:3.11-slim")
def prepare_data(output_dataset: Output[Dataset]):
    import pandas as pd

    df = pd.DataFrame({"feature": [1, 2, 3, 4], "label": [0, 1, 0, 1]})
    df.to_csv(output_dataset.path, index=False)
```

**Explicación:**
`output_dataset: Output[Dataset]` declara una salida de artifact tipado; el SDK aprovisiona `output_dataset.path` como la ubicación de almacenamiento donde escribe el componente, que los componentes posteriores pueden declarar después como un `Input[Dataset]`.
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
`prep_task.outputs["output_dataset"]` hace referencia al artifact producido por el parámetro `Output[Dataset]` de `prepare_data` (llamado `output_dataset`), y pasarlo como el argumento `input_dataset` de `train_model` crea la arista del DAG entre los dos componentes.
</details>

13. Escribe el código para deshabilitar la caché en una sola tarea de pipeline llamada `prep_task`.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
```python
prep_task.set_caching_options(enable_caching=False)
```

**Explicación:**
Llamar a `set_caching_options(enable_caching=False)` en un objeto de tarea dentro de la función del pipeline deshabilita la caché para la ejecución de ese componente específico, obligándolo a ejecutarse de nuevo incluso si existe un resultado en caché coincidente de una ejecución anterior.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/02-pipelines.md) | [Siguiente cuestionario: Notebooks](./03-notebooks-quiz.md)
