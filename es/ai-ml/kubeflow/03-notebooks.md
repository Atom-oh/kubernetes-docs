# Parte 3: Kubeflow Notebooks

> **Versiones compatibles**: Kubeflow Notebooks 1.11.0; Community Distribution 26.03.1
> **Última actualización**: September 12, 2026

## Configuración del entorno de laboratorio

Utilice un clúster de Kubernetes compatible, el controlador y la aplicación web de Notebooks 1.11.0, permisos de namespace, almacenamiento y una ruta de acceso autenticada. Consulte la [Parte 1](01-architecture-installation.md) para la compatibilidad entre distribuciones. Las cargas de trabajo con GPU necesitan drivers y device plugins compatibles, además de capacidad de nodos adecuada; Karpenter es un aprovisionador de capacidad, no un requisito previo de los notebooks.

## ¿Qué es Kubeflow Notebooks?

La aplicación web de Notebooks crea un `Notebook` con la configuración de imagen, recursos y volúmenes. Su controlador gestiona un StatefulSet, un Service y, cuando está configurado, un VirtualService de Istio. El controlador de StatefulSet crea los Pods y Kubernetes los programa. El dashboard es el punto de entrada de la aplicación web, no el creador de Pods ni un proxy de tráfico universal.

El recurso Notebook, que pertenece a un namespace, contiene un PodSpec y también puede gestionarse mediante GitOps o la API de Kubernetes. Editar directamente el StatefulSet que gestiona puede revertirse por la reconciliación.

## Contexto de versiones: Notebooks v1 y Workspaces

Este capítulo revisa **Notebooks v1.11.0** y su API `Notebook` en la distribución 26.03.1. Workspaces es un diseño v2 independiente que usa `Workspace` y `WorkspaceKind`; no es un reemplazo directo del CRD.

La descripción de la versión 26.03.1 califica Workspaces como beta, mientras que los manifiestos etiquetados del controlador, backend y frontend referencian imágenes **v2.0.0-alpha.3**. Distinga entre el texto de la release y las etiquetas de imagen desplegadas. Esta revisión no establece la disponibilidad general (GA) de v2 ni una fecha de fin de soporte de v1. Verifique las releases reales, las APIs y el soporte de migración antes de adoptarlo.

## Modelo de multi-tenancy: Profiles y políticas de aislamiento independientes

La interfaz completa de Kubeflow crea notebooks en el namespace del Profile seleccionado. Un Profile puede compartirse entre los miembros de un equipo, y el propio CRD Notebook no exige que cada namespace tenga un Profile. Los modelos de acceso de la instalación independiente y de la plataforma completa también difieren.

La propiedad y pertenencia a un Profile, RBAC y la AuthorizationPolicy de Istio proporcionan partes del control de acceso. No revocan concesiones de RBAC no relacionadas ni bloquean automáticamente todo el tráfico de los Pods, el acceso al almacenamiento o el acceso a AWS. Evalúe por separado la aplicación de NetworkPolicy, los privilegios de los Pods, los permisos de volúmenes, el IAM de las cargas de trabajo y la autorización de la aplicación.

### Almacenamiento persistente

La interfaz por defecto normalmente monta un PVC de workspace en `/home/jovyan`. **Solo los datos almacenados en ese volumen** persisten cuando se reemplaza el Pod. Los paquetes instalados en `/opt/conda`, en directorios del sistema o en la capa escribible del contenedor, así como el estado del kernel en memoria, no se conservan mediante ese PVC. Los paquetes de usuario en el directorio home pueden persistir, pero pueden volverse incompatibles con una nueva imagen.

Revise el ciclo de vida del PVC y del volumen, las copias de seguridad y la política de reclamación (reclaim policy). ReadWriteOnce en EBS significa montaje de lectura/escritura desde un **nodo**, no uso exclusivo por un único Pod. Restringirlo a un solo Pod requiere soporte adicional, como CSI ReadWriteOncePod. EBS tiene restricciones de zona de disponibilidad (AZ) y de adjuntado; el almacenamiento compartido con EFS requiere permisos POSIX y un diseño de acceso concurrente.

### Idle culling

Los valores por defecto revisados en v1.11.0 son `ENABLE_CULLING=false`, `CULL_IDLE_TIME=1440` e `IDLENESS_CHECK_PERIOD=1`; los tiempos están en minutos. La instalación por sí sola no activa el culling.

El culler utiliza el endpoint `/api/kernels` de Jupyter y la última actividad. No detecta de forma exhaustiva el cierre del navegador ni el trabajo con GPU en procesos de shell. No dé por supuesto que RStudio o code-server expongan la misma API. Una solicitud fallida o una lista de kernels vacía deja el valor de última actividad sin cambios, por lo que un valor antiguo puede llevar igualmente a la detención. Valide la detección con las imágenes y políticas de acceso reales antes de habilitarlo.

El culling añade una anotación de parada, reduciendo a cero las réplicas del StatefulSet sin eliminar los PVC. Liberar las solicitudes de los Pods no necesariamente termina un nodo EC2: otras cargas de trabajo, los PDB y las políticas y presupuestos de Karpenter siguen influyendo. Los cargos de la instancia pueden continuar hasta que el nodo se termine.

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

La marca de tiempo ilustra el formato de la anotación. Sustituya el namespace y el notebook reales, y guarde su trabajo antes de ejecutar estos comandos. La inyección del sidecar de Istio la realizan los admission webhooks configurados, no directamente el controlador de Notebook.

## Programación de GPU para notebooks en EKS

Las solicitudes de GPU utilizan recursos extendidos estándar como `resources.limits["nvidia.com/gpu"]`. El device plugin, el driver, la capacidad de los nodos, los taints/tolerations y la afinidad deben ser coherentes entre sí. Declarar un recurso de GPU por sí solo no garantiza que aparezca un nodo adecuado.

Karpenter puede aprovisionar para Pods en estado Pending que cumplan los requisitos y NodePools coincidentes, sujeto a la capacidad de EC2, las cuotas, los límites, la red y el éxito del bootstrap. Detener un notebook y reducir la escala de EC2 son operaciones distintas. Consulte [Karpenter](../../autoscaling/02-karpenter.md) para conocer las condiciones de ubicación y disrupción.

## Imágenes de notebook personalizadas

El spawner revisado establece `allowCustomImage` en `true` por defecto. Una restricción en el desplegable de la interfaz no puede, por sí sola, imponer la selección de imagen a los usuarios que pueden llamar directamente a la API de Notebook. Aplique las restricciones necesarias también mediante RBAC y admission.

Las imágenes deben cumplir con el puerto del servidor, el prefijo `/notebook/<namespace>/<name>/` o la configuración de reescritura, el UID/GID, un home escribible, las probes y las dependencias de ejecución. Una imagen de Jupyter Docker Stacks no incluye automáticamente todas las convenciones ni los SDK de Kubeflow. Compile con dependencias fijadas, referencie el digest de la imagen desde ECR u otro registro, y verifique la arquitectura de CPU y la compatibilidad con el driver de GPU.

Una etiqueta idéntica no garantiza bytes idénticos. Incluso un digest idéntico no hace que los entornos sean idénticos cuando difieren los paquetes o ajustes de usuario del PVC, los scripts de arranque o la instalación en tiempo de ejecución.

## Validación y fuentes

El overlay de notebook-controller de 26.03.1 se renderizó localmente con Kustomize. Se inspeccionaron el CRD de v1.11.0, el manejo de la parada, el culling y la configuración del spawner. No se ejecutaron notebooks reales, ejecución en GPU, recuperación de PVC, detección de inactividad ni aprovisionamiento en EKS.

- [v1.11.0 Notebook controller](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/notebook-controller/controllers/notebook_controller.go)
- [v1.11.0 culling implementation](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/notebook-controller/controllers/culling_controller.go)
- [v1.11.0 spawner defaults](https://github.com/kubeflow/notebooks/blob/v1.11.0/components/crud-web-apps/jupyter/manifests/base/configs/spawner_ui_config.yaml)
- [26.03.1 Workspaces image tag](https://github.com/kubeflow/community-distribution/blob/26.03.1/applications/workspaces/upstream/controller/base/manager/kustomization.yaml)

## Próximos pasos

Continúe con los experimentos y el ajuste de hiperparámetros en la [Parte 4: Katib](04-katib.md).

[Volver a la página principal](./README.md)

## Cuestionario

Para comprobar lo que ha aprendido en este capítulo, pruebe el [cuestionario del tema](../../quizzes/ai-ml/kubeflow/03-notebooks-quiz.md).
