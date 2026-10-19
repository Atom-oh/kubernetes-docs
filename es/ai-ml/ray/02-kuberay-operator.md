# Parte 2: El operador KubeRay

> **Versión de referencia para la revisión**: KubeRay 1.7.1 · Ray 2.58.0 · 2026-10-16

## Configuración del entorno de laboratorio

Prepare un Kubernetes compatible, una versión compatible de kubectl y Helm 3. El hardware GPU y Karpenter no son requisitos previos para revisar una configuración de CPU. La capacidad real de EKS puede provenir de grupos de nodos administrados existentes, Karpenter, Cluster Autoscaler o la configuración de aprovisionamiento elegida para el clúster.

La validación aquí abarca la descarga del chart oficial y su renderizado nativo con Helm, las comprobaciones del esquema de CRD y el generador de configuración de autoscaler de Ray 2.58.0. **No valida la admisión/CEL del servidor de API, la reconciliación del controlador, el autoescalado activo ni la ejecución en GPU.**

## Qué hace KubeRay

KubeRay reconcilia los CR de Ray en Pods, Services y recursos relacionados. No dé por sentado que un grupo de workers ordinario de RayCluster necesariamente es un Deployment o StatefulSet. Por lo general, un nodo de Ray corresponde a un Pod de Ray, distinto del nodo de Kubernetes/EC2 que aloja ese Pod.

Instalar el operador no inicia una carga de trabajo de Ray. Cree recursos como RayCluster, RayJob o RayService por separado. Tampoco todos los cambios en `spec` se aplican automáticamente en el Pod existente; inspeccione la ruta de actualización.

## CRD y puertas de funcionalidades

El chart 1.7.1 incluye los CRD **RayCluster, RayJob, RayService y RayCronJob**. Todos proporcionan `ray.io/v1`. Los tres primeros también conservan la versión obsoleta `v1alpha1`; los ejemplos nuevos usan `v1`.

| Recurso | Función y límites |
|---|---|
| RayCluster | administra un Pod principal y grupos de workers; son posibles las configuraciones solo con el nodo principal |
| RayJob | envíos por lotes y ciclo de vida opcional de RayCluster; distinga entre clústeres existentes y políticas de limpieza |
| RayService | administra RayCluster y aplicaciones Serve; inspeccione las condiciones de actualización y transición del tráfico |
| RayCronJob | crea RayJobs según una programación; su puerta de funcionalidad del controlador está deshabilitada de forma predeterminada, a pesar de que el CRD está instalado |

Los valores predeterminados del chart habilitan la puerta beta `RayServiceIncrementalUpgrade`. Las puertas alfa para mTLS, NetworkPolicy de RayCluster y la inyección automática del recolector de History están deshabilitadas. El estado beta de History Server es distinto de la inyección automática alfa del recolector. Que una puerta de funcionalidad esté disponible no significa que el recurso tenga esa funcionalidad configurada.

### Limpieza de RayJob

`shutdownAfterJobFinishes` tiene el valor predeterminado false. El valor predeterminado `ttlSecondsAfterFinished: 0` no la habilita. Configure explícitamente la limpieza, los reintentos y los plazos previos a la ejecución y de ejecución. La versión 1.7 también tiene `deletionStrategy`, con restricciones como no combinar las políticas heredadas onSuccess/onFailure con deletionRules.

Distinga la selección de un clúster compartido de la limpieza de un clúster creado por el controlador, y conserve primero los resultados, los checkpoints y los registros. Eliminar un RayCluster no limpia automáticamente los artefactos/PVC externos ni todos los cargos de EC2.

### Actualizaciones de RayService

`NewCluster` y `NewClusterWithIncrementalUpgrade` crean un clúster nuevo. La segunda opción usa la Kubernetes Gateway API y una implementación adecuada de GatewayClass para desplazar el tráfico progresivamente. Esto es distinto de simplemente actualizar unos pocos Pods en el mismo lugar.

Aunque la puerta de actualización incremental está habilitada de forma predeterminada en la versión 1.7, siguen siendo importantes la estrategia, la configuración de Gateway, la capacidad adicional, la preparación y los requisitos de drenaje. El tiempo de inactividad cero es un objetivo, no una garantía para todas las aplicaciones. [La parte 4](04-ray-serve.md) aborda con más detalle el comportamiento de Serve.

## Capas de autoescalado

Habilite el autoescalado de Ray con `enableInTreeAutoscaling: true`. KubeRay configura un sidecar de autoscaler en el Pod principal y los permisos necesarios. El ejemplo establece explícitamente `autoscalerOptions.version: v2` en lugar de depender de valores predeterminados sensibles a la versión.

El autoscaler de Ray examina las tareas, los actores, las solicitudes de ubicación/recursos y el tamaño deseado del grupo de workers; KubeRay ajusta los Pods. Con `numOfHosts`, una réplica de grupo puede corresponder a varios Pods de Ray, por lo que `replicas == Pod count` no es una regla universal.

Kubernetes ubica los Pods, mientras que un aprovisionador como Karpenter proporciona capacidad de EC2 para los requisitos que no se pueden programar. Un Pod en estado Pending por descargas de imágenes, PVC, permisos o cuotas no necesariamente se resuelve añadiendo un nodo. La consolidación y la gestión de desviaciones de Karpenter también son comportamientos de control independientes.

El generador de configuración de Ray 2.58.0 establece de forma predeterminada el tiempo de inactividad global en 60 segundos; los tiempos de inactividad a nivel de grupo pueden anular este comportamiento. Las condiciones de réplicas mínimas/máximas, actividad, sondeo y drenaje implican que no se garantiza eliminar un Pod exactamente 60 segundos después.

![KubeRay reconcilia el estado deseado de RayCluster en Pods, el autoscaler de Ray solicita capacidad de workers en función de la demanda de las cargas de trabajo, y la ubicación de Kubernetes y el aprovisionamiento de EC2 operan como capas independientes.](../../.gitbook/assets/en-ai-ml-ray-02-kuberay-operator-0.png)

[Diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-ray-02-kuberay-operator-0.html)

## Declaraciones de recursos de CPU/GPU

**El límite de GPU de un Pod no siempre es la única fuente de configuración.** El código revisado aplica precedencia entre `resources` del grupo estructurado, `rayStartParams` y los límites/solicitudes del primer contenedor de Ray. Un `num-gpus` explícito no se sobrescribe incondicionalmente con el límite de GPU del contenedor.

Las comprobaciones de configuración nativa de Ray 2.58.0 produjeron GPU 1 a partir del límite 1, GPU 2 con `rayStartParams.num-gpus=2` y GPU 3 con `resources.GPU=3` del grupo estructurado. Esto **no crea más GPU físicas**. Alinee los límites de Kubernetes, los complementos de dispositivos, los controladores, los recursos lógicos de Ray y el hardware visible.

Las réplicas mínimas y los requisitos de CPU/ubicación también pueden afectar el tamaño del grupo de GPU; los Pods GPU no necesariamente aparecen solo cuando hay tareas GPU pendientes. Distinga también la configuración lógica de CPU de Ray de la aplicación de límites del contenedor.

## Instalación y actualización del operador

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update kuberay
helm pull kuberay/kuberay-operator --version 1.7.1 --untar --untardir ./vendor
helm template kuberay-operator ./vendor/kuberay-operator \
  --namespace kuberay-system --include-crds > operator.rendered.yaml
```

Inspeccione los CRD, RBAC, el ámbito de observación de namespaces y las puertas de funcionalidades. Los valores predeterminados del chart habilitan la elección de líder y la observación de todo el clúster. Para limitar el ámbito, revise conjuntamente `singleNamespaceInstall`, `watchNamespace` y la configuración de RBAC relacionada.

Realice la instalación después de verificar el contexto y los permisos administrativos:

```bash
helm upgrade --install kuberay-operator kuberay/kuberay-operator \
  --version 1.7.1 --namespace kuberay-system --create-namespace
kubectl rollout status deployment/kuberay-operator -n kuberay-system
```

El mecanismo `crds/` de Helm **no actualiza ni elimina automáticamente los CRD existentes**. No dé por sentado que una actualización del chart actualizó el esquema. Compruebe los CR almacenados y la compatibilidad de versiones de API; después, realice por separado la actualización de CRD correspondiente a la versión. Eliminar un CRD puede eliminar sus recursos personalizados.

## Configuración mínima de CPU

Este ejemplo presupone que existe el namespace `ray-demo`. Se validó el esquema del CRD; no se probó la ejecución del controlador, el inicio de la imagen ni el autoescalado.

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: ray-cpu-demo
  namespace: ray-demo
spec:
  rayVersion: '2.58.0'
  enableInTreeAutoscaling: true
  autoscalerOptions:
    version: v2
    idleTimeoutSeconds: 60
  headGroupSpec:
    serviceType: ClusterIP
    rayStartParams:
      num-cpus: '0'
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.58.0-py312
            resources:
              requests:
                cpu: '1'
                memory: 2Gi
              limits:
                cpu: '1'
                memory: 2Gi
  workerGroupSpecs:
    - groupName: cpu
      replicas: 0
      minReplicas: 0
      maxReplicas: 2
      rayStartParams: {}
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.58.0-py312
              resources:
                requests:
                  cpu: '1'
                  memory: 2Gi
                limits:
                  cpu: '1'
                  memory: 2Gi
```

El fixture de esquema completo usa `rayproject/ray:2.58.0-py312` y solicitudes y límites de CPU 1/memoria 2 GiB para el nodo principal y los workers. Establecer `rayVersion` no actualiza por sí mismo las imágenes de los contenedores. Verifique también la compatibilidad del entorno de ejecución, Python y las imágenes.

Limite los puntos de entrada del dashboard, Ray Client y el envío de trabajos a actores de confianza. La autenticación por token es una configuración independiente, no equivale a TLS ni al control de acceso de todos los endpoints de la aplicación. Compruebe que la entrega de secretos cumpla las políticas de la organización y mantenga los tokens confidenciales fuera de los manifiestos públicos y los registros.

## Fuentes principales

- [Versión de KubeRay 1.7.1](https://github.com/ray-project/kuberay/releases/tag/v1.7.1)
- [Valores del chart 1.7.1](https://github.com/ray-project/kuberay/blob/v1.7.1/helm-chart/kuberay-operator/values.yaml)
- [Creación de Pods/recursos](https://github.com/ray-project/kuberay/blob/v1.7.1/ray-operator/controllers/ray/common/pod.go)
- [Configuración del autoscaler de Ray 2.58.0](https://github.com/ray-project/ray/blob/ray-2.58.0/python/ray/autoscaler/_private/kuberay/autoscaling_config.py)
- [API de RayJob](https://github.com/ray-project/kuberay/blob/v1.7.1/ray-operator/apis/ray/v1/rayjob_types.go)
- [API de RayService](https://github.com/ray-project/kuberay/blob/v1.7.1/ray-operator/apis/ray/v1/rayservice_types.go)
- [Ciclo de vida de los CRD en Helm](https://helm.sh/docs/chart_best_practices/custom_resource_definitions/)

[Siguiente: Train/Tune](03-ray-train-tune.md) · [Página principal](README.md) · [Cuestionario](../../quizzes/ai-ml/ray/02-kuberay-operator-quiz.md)
