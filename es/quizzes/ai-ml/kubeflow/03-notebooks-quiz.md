# Cuestionario de Kubeflow Notebooks

Este cuestionario evalúa tu comprensión de la arquitectura de Kubeflow Notebooks, su modelo de multi-tenencia basado en Profile, el comportamiento del almacenamiento y la eliminación por inactividad, la programación de GPU en EKS y las imágenes personalizadas de notebooks.

## Preguntas de opción múltiple

1. ¿Qué mecanismo nativo de Kubernetes utiliza Kubeflow Notebooks para convertir las selecciones del spawner de un usuario (imagen, CPU/memoria/GPU, almacenamiento) en un servidor de notebooks en ejecución?
   - A) Un script de shell que el dashboard ejecuta directamente contra `kubectl`
   - B) Un recurso personalizado `Notebook` que un controlador reconcilia en un StatefulSet/pod
   - C) Un cron job que consulta la base de datos del dashboard cada minuto
   - D) Un Helm chart que el usuario instala manualmente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un recurso personalizado `Notebook` que un controlador reconcilia en un StatefulSet/pod**

**Explicación:**
El spawner del Central Dashboard crea un recurso personalizado `Notebook` que describe el entorno deseado. Un controlador observa ese recurso y lo reconcilia en objetos ordinarios de Kubernetes (un StatefulSet/pod con la imagen, los recursos y el PVC solicitados), en lugar de que el dashboard cree pods directamente.
</details>

2. A partir de Kubeflow Community Distribution 26.03, ¿cuál es el estado preciso de Kubeflow Notebooks v2?
   - A) Ya está en GA y ha reemplazado completamente a v1
   - B) Aún no existe, ni siquiera como alpha
   - C) Se acerca a su lanzamiento, con manifiestos alpha disponibles para probar los nuevos CRD `Workspace`/`WorkspaceKind`, pero aún no está en GA
   - D) Fue cancelado a favor de mantener v1 indefinidamente

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: C) Se acerca a su lanzamiento, con manifiestos alpha disponibles para probar los nuevos CRD `Workspace`/`WorkspaceKind`, pero aún no está en GA**

**Explicación:**
En el momento de la distribución 26.03, Notebooks v2 — creado en torno a los nuevos recursos personalizados `Workspace` y `WorkspaceKind` — cuenta con manifiestos alpha disponibles para pruebas, pero no ha alcanzado la disponibilidad general. El CRD `Notebook` de v1 sigue siendo la arquitectura utilizada en producción y se espera que pase a un estado de solo mantenimiento cuando v2 esté listo para GA.
</details>

3. ¿Qué es un Profile en el contexto del modelo de multi-tenencia de Kubeflow Notebooks?
   - A) El tema de UI y los atajos de teclado guardados de un usuario para notebooks
   - B) Una construcción de un namespace por usuario que aprovisiona enlaces RBAC y políticas de autorización de Istio que delimitan el acceso de ese usuario
   - C) Un registro de las imágenes que un usuario ha generado previamente
   - D) Una cuenta de facturación vinculada a la identidad de AWS IAM de un usuario

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Una construcción de un namespace por usuario que aprovisiona enlaces RBAC y políticas de autorización de Istio que delimitan el acceso de ese usuario**

**Explicación:**
Un Profile aprovisiona un namespace dedicado para un usuario (o equipo), enlaces RBAC que delimitan sus permisos a ese namespace y una `AuthorizationPolicy` de Istio que restringe qué identidades pueden llegar a los servicios dentro de él. Los notebooks siempre se crean dentro de un namespace de Profile, lo que aísla por defecto el notebook de un usuario del de otro.
</details>

4. ¿Por qué el PersistentVolumeClaim de un notebook es importante para su resiliencia ante reinicios de pods?
   - A) El PVC se elimina y se vuelve a crear automáticamente cada vez que se reinicia el pod
   - B) El claim, no el pod, es el objeto duradero: los archivos y paquetes instalados montados desde él sobreviven a los reinicios de pods, al reemplazo de nodos o a un ciclo de detención/inicio
   - C) Los PVC solo importan para las imágenes de RStudio, no para JupyterLab
   - D) El PVC solo se utiliza para almacenar logs, no archivos de usuario

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) El claim, no el pod, es el objeto duradero: los archivos y paquetes instalados montados desde él sobreviven a los reinicios de pods, al reemplazo de nodos o a un ciclo de detención/inicio**

**Explicación:**
El spawner permite a un usuario adjuntar un PVC que normalmente se monta en el directorio principal del notebook. Como el PVC persiste independientemente del ciclo de vida del pod, el trabajo de un usuario se conserva entre reinicios de pods, reemplazos de nodos o ciclos intencionales de detención/inicio; y la eliminación por inactividad, que detiene en lugar de eliminar el notebook, deja el PVC intacto.
</details>

5. ¿Por qué la eliminación por inactividad es especialmente importante para los notebooks con GPU?
   - A) Los notebooks no pueden solicitar GPU en absoluto, por lo que la eliminación es irrelevante para ellos
   - B) Un notebook pod en ejecución mantiene su asignación de GPU mientras exista, independientemente de su uso activo, por lo que un notebook de GPU inactivo puede ocupar capacidad costosa durante horas
   - C) La eliminación borra el PVC del notebook para liberar memoria de GPU
   - D) Los nodos de GPU requieren un reinicio completo del clúster para recuperar capacidad, que la eliminación activa

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Un notebook pod en ejecución mantiene su asignación de GPU mientras exista, independientemente de su uso activo, por lo que un notebook de GPU inactivo puede ocupar capacidad costosa durante horas**

**Explicación:**
Un notebook pod mantiene continuamente la asignación de CPU, memoria y GPU solicitada mientras está en ejecución, independientemente de que alguien lo esté utilizando activamente. La eliminación por inactividad detiene (sin eliminar) los notebooks inactivos tras un período configurado, lo que es especialmente valioso para los notebooks de GPU, ya que de otro modo un servidor con GPU inactivo podría retener indefinidamente una costosa capacidad de aceleración.
</details>

6. ¿Cómo solicita acceso a GPU un notebook pod en EKS y cómo interactúa esto con el escalado automático del clúster?
   - A) Utiliza un programador de GPU dedicado solo para Notebooks, separado del resto del clúster
   - B) Establece `resources.limits."nvidia.com/gpu"` como cualquier otro pod, compitiendo por los mismos node pools con capacidad de GPU (por ejemplo, NodePools administrados por Karpenter) utilizados por los trabajos de entrenamiento y las cargas de trabajo de inferencia
   - C) El acceso a GPU para notebooks debe ser asignado manualmente por un administrador mediante SSH al nodo
   - D) Los notebook pods no pueden solicitar GPU; solo los endpoints de KServe pueden hacerlo

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Establece `resources.limits."nvidia.com/gpu"` como cualquier otro pod, compitiendo por los mismos node pools con capacidad de GPU (por ejemplo, NodePools administrados por Karpenter) utilizados por los trabajos de entrenamiento y las cargas de trabajo de inferencia**

**Explicación:**
La selección de GPU del spawner se traduce en una solicitud de recursos estándar `nvidia.com/gpu` en la especificación del pod, anunciada como asignable por el plugin de dispositivos NVIDIA. No se trata de un subsistema de GPU separado: el notebook pod compite por los mismos node pools de GPU que cualquier otra carga de trabajo de GPU y, en EKS, esa capacidad se aprovisiona habitualmente de forma dinámica mediante Karpenter.
</details>

7. ¿Cuál es la razón típica por la que los equipos crean imágenes personalizadas de notebooks en lugar de utilizar las imágenes estándar del spawner tal como están?
   - A) Kubeflow requiere imágenes personalizadas y las imágenes estándar no pueden utilizarse en absoluto
   - B) Para proporcionar a cada científico de datos un entorno idéntico y reproducible con dependencias específicas del equipo preinstaladas, en lugar de instalar paquetes manualmente dentro de un contenedor en ejecución
   - C) Las imágenes estándar no admiten montajes de PVC
   - D) Las imágenes personalizadas eliminan la necesidad de un namespace de Profile

<details>

<summary>Mostrar respuesta</summary>

**Respuesta: B) Para proporcionar a cada científico de datos un entorno idéntico y reproducible con dependencias específicas del equipo preinstaladas, en lugar de instalar paquetes manualmente dentro de un contenedor en ejecución**

**Explicación:**
La mayoría de los equipos de producción crean imágenes personalizadas sobre una imagen base ascendente de Kubeflow/Jupyter, incorporando paquetes fijos de Python/R, bibliotecas internas y versiones coincidentes de frameworks de GPU; después, envían la imagen a un registry (por ejemplo, Amazon ECR en EKS) y la referencian directamente desde el spawner. Esto garantiza que dos usuarios con la misma etiqueta de imagen obtengan conjuntos de paquetes idénticos, en lugar de divergir debido a instalaciones manuales.
</details>

## Preguntas de respuesta corta

8. En una o dos frases, explica cómo interactúa la solicitud de GPU de un notebook pod con Karpenter en EKS y por qué esto importa para el costo.

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
Cuando la especificación de un notebook Pod solicita recursos `nvidia.com/gpu` y ningún nodo existente tiene capacidad, Karpenter aprovisiona una nueva instancia EC2 con GPU para satisfacer el Pod pendiente; dado que las instancias de GPU son costosas, la eliminación por inactividad y el ajuste correcto de las solicitudes de GPU de los notebooks controlan directamente cuánta capacidad de GPU no utilizada paga un equipo entre sesiones activas.
</details>

9. ¿Qué proporciona el aislamiento de Istio por namespace a un Profile de Kubeflow que RBAC de namespace de Kubernetes por sí solo no proporcionaría?

<details>

<summary>Mostrar respuesta</summary>

**Respuesta:**
RBAC controla quién puede crear/leer/modificar objetos de la API de Kubernetes en un namespace, pero no dice nada sobre el tráfico de red; la `AuthorizationPolicy` por namespace de Istio restringe adicionalmente qué servicios pueden enviar solicitudes realmente al notebook Pod de un usuario en la capa de red, proporcionando aislamiento entre los servidores de notebooks de los usuarios incluso si RBAC por sí solo hubiera permitido cierto acceso a objetos entre namespaces.
</details>

---

[Volver a los materiales de aprendizaje](../../../ai-ml/kubeflow/03-notebooks.md)
