# Parte 3: Kubeflow Notebooks

> **Versiones compatibles**: Kubeflow Notebooks 1.11.0; Community Distribution 26.03.1
> **Última actualización**: 12 de septiembre de 2026

## Configuración del entorno de laboratorio

Utilice un clúster de Kubernetes compatible, el controlador y la aplicación web de Notebooks 1.11.0, permisos en el espacio de nombres, almacenamiento y un mecanismo de acceso autenticado. Consulte la [Parte 1](01-architecture-installation.md) para conocer la compatibilidad entre distribuciones. Las cargas de trabajo con GPU necesitan controladores y complementos de dispositivo compatibles, además de capacidad suficiente en los nodos; Karpenter es una opción para aprovisionar capacidad, no un requisito previo para usar notebooks.

## ¿Qué es Kubeflow Notebooks?

La aplicación web de Notebooks crea un `Notebook` con la configuración de imagen, recursos y volúmenes. Su controlador gestiona un StatefulSet, un Service y, cuando está configurado, un VirtualService de Istio. El controlador de StatefulSet crea los Pods y Kubernetes los programa. El dashboard es el punto de entrada de la aplicación web, no el creador de Pods ni un proxy de tráfico universal.

El recurso Notebook, que tiene ámbito de espacio de nombres, contiene un PodSpec y también puede gestionarse mediante GitOps o la API de Kubernetes. Si edita directamente el StatefulSet administrado, la reconciliación puede revertir los cambios.

## Contexto de versiones: Notebooks v1 y Workspaces

Este capítulo revisa **Notebooks v1.11.0** y su API `Notebook` en la distribución 26.03.1. Workspaces es un diseño v2 independiente que usa `Workspace` y `WorkspaceKind`; no es un reemplazo directo del CRD.

La descripción de la versión 26.03.1 califica Workspaces como beta, mientras que los manifiestos con etiqueta del controlador, el backend y el frontend hacen referencia a imágenes **v2.0.0-alpha.3**. Distinga entre lo que indica la nota de versión y las etiquetas de las imágenes desplegadas. Esta revisión no confirma que v2 tenga disponibilidad general (GA) ni establece una fecha de fin de soporte para v1. Verifique las versiones publicadas, las API y el soporte de migración antes de adoptarlo.

## Modelo multiinquilino: Profiles y políticas de aislamiento independientes

La interfaz completa de Kubeflow crea notebooks en el espacio de nombres del Profile seleccionado. Un Profile puede compartirse entre los miembros de un equipo, y el propio CRD Notebook no exige que cada espacio de nombres tenga un Profile. El modelo de acceso de una instalación independiente también difiere del de la plataforma completa.

La propiedad y la pertenencia a un Profile, RBAC y AuthorizationPolicy de Istio proporcionan partes del control de acceso. No revocan otros permisos de RBAC ni bloquean automáticamente todo el tráfico de los Pods, el acceso al almacenamiento o el acceso a AWS. Evalúe por separado la aplicación de NetworkPolicy, los privilegios de los Pods, los permisos de los volúmenes, el IAM de las cargas de trabajo y la autorización de la aplicación.

### Almacenamiento persistente

La interfaz de usuario normalmente monta un PVC del espacio de trabajo en `/home/jovyan`. **Solo los datos almacenados en ese volumen** persisten cuando se reemplaza el Pod. Los paquetes instalados en `/opt/conda`, en directorios del sistema o en la capa escribible del contenedor, así como el estado del kernel en memoria, no se conservan en ese PVC. Los paquetes del usuario en su directorio personal pueden persistir, pero volverse incompatibles con una imagen nueva.

Revise el ciclo de vida del PVC y del volumen, las copias de seguridad y la política de recuperación (reclaim policy). ReadWriteOnce en EBS permite el montaje de lectura y escritura desde un **nodo**, no el uso exclusivo por un único Pod. Para restringirlo a un solo Pod se necesita compatibilidad adicional, como CSI ReadWriteOncePod. EBS tiene restricciones de zona de disponibilidad (AZ) y de conexión; el almacenamiento compartido con EFS requiere permisos POSIX y un diseño que admita el acceso concurrente.

### Detención por inactividad

Los valores predeterminados revisados en v1.11.0 son `ENABLE_CULLING=false`, `CULL_IDLE_TIME=1440` e `IDLENESS_CHECK_PERIOD=1`; los tiempos se expresan en minutos. La instalación por sí sola no activa la detención por inactividad.

El mecanismo de inactividad consulta la API de Jupyter en `/api/kernels` y la hora de la última actividad. No detecta de forma exhaustiva si se cerró el navegador ni si hay trabajo con GPU en procesos de shell. No dé por supuesto que RStudio o code-server exponen la misma API. Si una solicitud falla o la lista de kernels está vacía, la hora de la última actividad no cambia; por tanto, un valor antiguo aún puede provocar la detención. Valide la detección con las imágenes y las políticas de acceso reales antes de habilitar esta función.

La detención por inactividad añade una anotación de parada y reduce a cero las réplicas del StatefulSet sin eliminar los PVC. Liberar las solicitudes de recursos de los Pods no necesariamente termina un nodo EC2: otras cargas de trabajo, los PDB y las políticas y presupuestos de Karpenter siguen influyendo. Los cargos de la instancia pueden continuar hasta que esta se termine.

## Flujo de reconciliación de Notebook

![La aplicación web de notebooks crea un CR; los controladores reconcilian el StatefulSet, el Service y el enrutamiento, mientras Kubernetes crea y ubica los Pods.](../../.gitbook/assets/en-ai-ml-kubeflow-03-notebooks-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-kubeflow-03-notebooks-0.html)

Notebook v1.11.0 no tiene un campo `spec.replicas`. El controlador genera cero réplicas del StatefulSet cuando `kubeflow-resource-stopped` está **presente**, y una cuando está ausente. Incluso un valor de `"false"` lo detiene. Para reanudarlo, elimine la anotación en lugar de cambiar su valor.

```bash
# Stop the selected notebook: active kernels/processes terminate.
kubectl annotate notebook -n team-a analysis \
  kubeflow-resource-stopped="2026-09-12T00:00:00Z" --overwrite
# Resume by removing the annotation.
kubectl annotate notebook -n team-a analysis kubeflow-resource-stopped-
```

La marca de tiempo ilustra el formato de la anotación. Sustituya el espacio de nombres y el notebook reales, y guarde su trabajo antes de ejecutar estos comandos. La inyección del sidecar de Istio la realizan los webhooks de admisión configurados, no directamente el controlador de Notebook.

## Programación de GPU para notebooks en EKS

Las solicitudes de GPU utilizan recursos extendidos estándar como `resources.limits["nvidia.com/gpu"]`. El complemento de dispositivo, el controlador, la capacidad de los nodos, las tolerations de taints y la afinidad deben ser coherentes entre sí. Declarar un recurso de GPU por sí solo no garantiza que aparezca un nodo adecuado.

Karpenter puede aprovisionar nodos para Pods pendientes que cumplan los requisitos y coincidan con NodePools, sujeto a la capacidad de EC2, las cuotas, los límites, la red y que la inicialización se complete correctamente. Detener un notebook y reducir la escala de EC2 son operaciones distintas. Consulte [Karpenter](../../autoscaling/02-karpenter.md) para conocer las condiciones de ubicación e interrupción.

## Imágenes de notebook personalizadas

El spawner revisado establece `allowCustomImage` en `true` de forma predeterminada. Limitar las opciones del desplegable de la interfaz no impide, por sí solo, que los usuarios que pueden llamar directamente a la API de Notebook elijan otra imagen. Aplique también las restricciones necesarias mediante RBAC y los controles de admisión.

Las imágenes deben cumplir los requisitos del puerto del servidor, el prefijo `/notebook/<namespace>/<name>/` o la configuración de reescritura, el UID/GID, un directorio personal escribible, las sondas y las dependencias de ejecución. Una imagen de Jupyter Docker Stacks no incluye automáticamente todas las convenciones ni todos los SDK de Kubeflow. Compile con dependencias fijadas, use el digest de la imagen de ECR u otro registro y verifique la arquitectura de CPU y la compatibilidad con el controlador de GPU.

Una etiqueta idéntica no garantiza que los bytes sean idénticos. Incluso con el mismo digest, los entornos pueden diferir si cambian los paquetes o ajustes del usuario almacenados en el PVC, los scripts de inicio o lo que se instala durante la ejecución.

## Validación y fuentes

El overlay de notebook-controller de 26.03.1 se renderizó localmente con Kustomize. Se inspeccionaron el CRD de v1.11.0, el manejo de la parada, la detección de inactividad y la configuración del spawner. No se probaron notebooks reales, cargas de trabajo en GPU, recuperación de PVC, detección de inactividad ni aprovisionamiento en EKS.

- [v1.11.0 Notebook controller](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/notebook-controller/controllers/notebook_controller.go)
- [v1.11.0 culling implementation](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/notebook-controller/controllers/culling_controller.go)
- [v1.11.0 spawner defaults](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/crud-web-apps/jupyter/manifests/base/configs/spawner_ui_config.yaml)
- [26.03.1 Workspaces image tag](https://github.com/kubeflow/community-distribution/blob/26.03.1/applications/workspaces/upstream/controller/base/manager/kustomization.yaml)

## Próximos pasos

Continúe con los experimentos y el ajuste de hiperparámetros en la [Parte 4: Katib](04-katib.md).

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, pruebe el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/03-notebooks-quiz.md).
