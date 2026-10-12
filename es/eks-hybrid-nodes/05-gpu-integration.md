# Integración de servidores GPU

< [Anterior: Bootstrap de Node](./04-node-bootstrap.md) | [Tabla de contenidos](./README.md) | [Siguiente: Estrategias de ubicación de Workloads](./06-workload-placement.md) >

> **Versiones compatibles**: Los ejemplos de GPU DRA requieren Kubernetes 1.34.2+ en una versión de EKS compatible. Interfaces revisadas: GPU Operator 26.7.0, controlador DRA 0.5.0, plugin de dispositivos 0.20.0.
> **Última actualización**: October 12, 2026

Este capítulo integra hosts NVIDIA GPU preparados con EKS Hybrid Nodes. Abarca asignación, propiedad de GPU Operator, MIG y time-slicing. **No se ejecutaron GPU, instalación de controladores, descarga de modelos ni benchmark de inferencia para esta auditoría.** Los ejemplos requieren una combinación aprobada de OS/kernel/controlador/toolkit/runtime/imagen y pruebas en el hardware real.

## Elija un propietario de asignación por GPU

| Ruta | Requisitos previos y asignación |
|---|---|
| Plugin de dispositivos NVIDIA independiente | Controlador de host preparado, NVIDIA Container Toolkit y runtime; anuncia recursos extendidos como `nvidia.com/gpu` |
| Controlador DRA independiente | Controlador preparado y runtime CDI; publica ResourceSlices y asigna mediante DeviceClass/ResourceClaim |
| GPU Operator con `ClusterPolicy` | Flujo de trabajo de plugin de dispositivos administrado por Operator; la propiedad de los componentes de controlador/toolkit/MIG debe coincidir con lo que ya está instalado |
| GPU Operator 26.7 con `GPUCluster` | Flujo de trabajo DRA administrado por Operator para una nueva instalación; mutuamente excluyente con `ClusterPolicy` en el cluster |

AWS recomienda DRA para nuevos despliegues de EKS 1.34+ con aprovisionamiento de capacidad estática compatible. **El controlador NVIDIA DRA no es compatible con EKS Auto Mode**, que ya administra su plugin de dispositivos GPU; AWS dirige Auto Mode y la capacidad dinámica de Karpenter al plugin de dispositivos NVIDIA (sección de Kubernetes 1.37 de las [notas de la versión de soporte estándar de EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html), consultada el October 12, 2026). Los ejemplos independientes a continuación se dirigen solo a los Nodes Hybrid GPU identificados; no instale administradores de asignación duplicados en Auto Mode ni en otros Nodes GPU.

Use labels diferentes administradas por el propietario, como `workload.example.com/gpu-allocation=device-plugin` o `dra`. Esas labels son entradas de scheduling, no un límite de seguridad ni evidencia de hardware GPU en buen estado. Verifique que ningún otro plugin/Operator publique los mismos dispositivos físicos antes de habilitar cualquiera de las rutas.

## Prepare y verifique la cohorte de hosts

- Complete [Bootstrap de Node](./04-node-bootstrap.md), incluidas la identidad Hybrid, CNI y sincronización de hora.
- Compruebe el modelo/formato de GPU, firmware, rama del controlador, OS/kernel y runtime frente a la matriz de NVIDIA y la compatibilidad de OS Hybrid de AWS. Una matriz NVIDIA más reciente no significa que EKS ofrezca todas las versiones de Kubernetes que se indican allí.
- Verifique que el controlador y toolkit NVIDIA reales estén instalados. Estar on-premises no implica que exista un controlador.
- Para el ejemplo heredado, prepare un `RuntimeClass` existente llamado `nvidia` respaldado por el handler de runtime NVIDIA de containerd configurado. El nombre de clase por sí solo no configura el handler.
- Para la asignación de GPU DRA 0.5.0, la guía de requisitos previos publicada exige Kubernetes **1.34.2+**, un controlador independiente **565+**, Toolkit **1.18+** y un runtime habilitado para CDI. El flujo de trabajo DRA de GPU Operator requiere un controlador **580+**. Estos son mínimos de compatibilidad, no recomendaciones de parches/ramas actuales.
- Prepare labels de descubrimiento mediante la instalación aprobada de NFD/GFD o el proceso de inventario de hosts. No despliegue un segundo controlador de descubrimiento solo porque un ejemplo habilita uno.

La siguiente comprobación ejecutada por Operator lee metadatos de GPU del host; no es un benchmark de CUDA ni LLM:

```bash
nvidia-smi --query-gpu=name,driver_version,uuid,memory.total --format=csv,noheader
```

Una salida que muestre `cpu: 128`, `memory: 1024Gi`, `nvidia.com/gpu: 8` en el ejemplo anterior era una **ilustración no verificada**, no una medición de esta auditoría. La capacidad GPU de Kubernetes puede representar GPUs físicas, instancias MIG o réplicas de time-slicing, según la configuración.

## Plugin de dispositivos independiente en Nodes Hybrid seleccionados

Los siguientes valores requieren el controlador/runtime preinstalado y una configuración de descubrimiento compatible existente. Las dos labels de selector de Node se combinan con la afinidad de descubrimiento de GPU del chart. Si no coincide ningún Node, corrija el inventario/labels; no elimine la afinidad solo para obtener Pods en ejecución.

```yaml
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  workload.example.com/gpu-allocation: device-plugin
runtimeClassName: nvidia
migStrategy: none
failOnInitError: true
deviceListStrategy: envvar
gfd:
  enabled: false
nfd:
  enabled: false
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

Guarde como `device-plugin-values.yaml`. El chart revisado es **0.20.0**; verifique la ruta de actualización deseada y la compatibilidad de imágenes antes del despliegue:

```bash
# Cluster write; installs a privileged infrastructure component.
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" get nodes \
  -l 'eks.amazonaws.com/compute-type=hybrid,workload.example.com/gpu-allocation=device-plugin' \
  -o json > plugin-nodes.json
jq -e '.items | length > 0 and
  all(.[]; .metadata.labels["nvidia.com/mps.capable"] != "true")' plugin-nodes.json
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update nvdp
helm install hybrid-gpu-plugin nvdp/nvidia-device-plugin \
  --version 0.20.0 --namespace gpu-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values device-plugin-values.yaml --wait --timeout 10m
```

Use un namespace y una release que pertenezcan al operador de infraestructura GPU. Revise RBAC renderizado, rutas de host, privilegios, acceso a registry y tolerations. El éxito de `--wait` de Helm no es evidencia de compatibilidad CUDA ni de rendimiento de Workload.

El chart 0.20.0 publicado también renderiza un DaemonSet de control MPS, restringido por `nvidia.com/mps.capable=true` más la cohorte Hybrid seleccionada. Este ejemplo de GPU exclusiva se detiene si esa label ya está configurada. Investigue la propiedad de MPS existente en lugar de eliminar la label sin más; no suponga que el chart contiene solo un DaemonSet.

## DRA independiente en una cohorte Hybrid GPU separada

El proyecto actual del controlador es **`kubernetes-sigs/dra-driver-nvidia-gpu`**. La estabilidad de la API DRA, la compatibilidad de EKS y la madurez de las funciones de cada proveedor son comprobaciones independientes. La documentación actual de NVIDIA 26.7 identifica la asignación de GPU completa y MIG existente como GA; MIG dinámico, MPS, algunas opciones de uso compartido y las funciones de estado de asignación NVML tienen gates Alpha independientes. No habilite todos los feature gates para que una demostración se inicie.

El texto anterior del README del repositorio etiquetado describe la asignación GPU como no compatible. La documentación publicada de requisitos previos/instalación y la tabla actual de capacidades de NVIDIA ofrecen la orientación más reciente y específica por función. Registre la versión exacta y el contrato de soporte para un despliegue de producción.

El ejemplo deshabilita ComputeDomains porque la asignación normal de H100/H200 no requiere orquestación Multi-Node NVLink. ComputeDomains tienen requisitos adicionales de Grace Blackwell/MNNVL, IMEX y descubrimiento.

```yaml
gpuResourcesEnabledOverride: true
nvidiaDriverRoot: /
resources:
  gpus:
    enabled: true
  computeDomains:
    enabled: false
featureGates: {}
kubeletPlugin:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
    workload.example.com/gpu-allocation: dra
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  containers:
    gpus:
      resources:
        requests:
          cpu: 50m
          memory: 128Mi
        limits:
          cpu: "1"
          memory: 512Mi
webhook:
  enabled: false
```

Guarde como `dra-values.yaml`. Esta ruta asume que la raíz del controlador de host es `/` y que CDI está configurado. Un controlador instalado por Operator normalmente usa una raíz diferente; no copie este valor en ese despliegue.

```bash
# Alternative cluster write, only for the separately selected DRA cohort.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}"
helm install hybrid-gpu-dra \
  oci://registry.k8s.io/dra-driver-nvidia/charts/dra-driver-nvidia-gpu \
  --version 0.5.0 --namespace gpu-dra-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values dra-values.yaml --wait --timeout 10m
```

`gpuResourcesEnabledOverride=true` sigue siendo necesario en este chart para recursos GPU. Su presencia no afirma que todas las funciones GPU sean Alpha. El webhook de admisión opcional está deshabilitado en este ejemplo mínimo; habilitarlo requiere endpoints de webhook accesibles y una configuración validada de TLS/cert-manager o secreto existente.

### Alternativa de GPU Operator y propiedad

Use el Operator cuando el ciclo de vida de sus componentes administrados coincida con la instalación prevista. `driver.enabled=false` es adecuado **solo si el controlador de host ya está verificado**. Del mismo modo, deshabilite la administración de toolkit solo después de preparar la configuración de runtime necesaria. Las actualizaciones de Operator pueden cambiar controladores, validadores, anuncio de recursos y disponibilidad de Node.

Para **DRA administrado por Operator nuevo**, los valores documentados incluyen:

```yaml
clusterPolicy:
  deployCR: false
gpuCluster:
  deployCR: true
driver:
  enabled: false
nfd:
  enabled: false
draDriver:
  computeDomains:
    enabled: false
```

Este fragmento asume un controlador preinstalado aprobado, runtime CDI e instalación de descubrimiento. GPUCluster no proporciona automáticamente el comportamiento de toolkit/administración MIG de ClusterPolicy. Revise los valores completos del chart para **26.7.0** y, a continuación, despliegue mediante el propietario GPU del cluster.

`GPUCluster` es un singleton con ámbito de cluster llamado `gpu-cluster`. No puede coexistir con `ClusterPolicy`. Una migración in situ desde ClusterPolicy o una release Helm DRA independiente a GPUCluster no es compatible con este flujo de trabajo; use la ruta documentada de nueva instalación. No instale una release DRA independiente adicional para un despliegue administrado por Operator.

Un `nodeSelector` del controlador Operator **no** restringe cada operando. La ubicación de operandos usa el descubrimiento de GPU y labels `nvidia.com/gpu.deploy.*`; revise también las GPUs cloud/Auto Mode excluidas y los Nodes futuros. Si ese límite no se puede mantener, use un cluster aislado o la ruta independiente con el ámbito adecuado.

La reconciliación de GPUCluster puede ejecutar validadores GPU y asignar claims. Su estado de preparación y telemetría DCGM no equivalen al estado de asignación de dispositivos DRA: `NVMLDeviceHealthCheck` es Alpha y está deshabilitado de forma predeterminada en esta release.

## Manifiestos DRA actuales

Estos ejemplos usan **`resource.k8s.io/v1`**. La forma alpha anterior de Kubernetes 1.31 no es un manifiesto intercambiable para clusters actuales. DRA necesita un controlador de proveedor funcional, ResourceSlices, kubelets/runtime compatibles y la API habilitada; un DeviceClass por sí solo no descubre GPUs.

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-full-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu"
---
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-large-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu" &&
          device.capacity["gpu.nvidia.com"].memory.isGreaterThan(quantity("40Gi"))
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: single-large-gpu
  namespace: ai-workloads
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: hybrid-large-gpu
            allocationMode: ExactCount
            count: 1
```

El selector `type == "gpu"` excluye dispositivos MIG y VFIO publicados bajo el mismo controlador `gpu.nvidia.com`. La segunda clase selecciona **más de 40 GiB** de memoria anunciada; no es un selector solo para H100/H200. Inspeccione el ResourceSlice para conocer la capacidad real y el `productName` de NVML. Una label de Node GFD como `NVIDIA-H200` no tiene por qué ser igual al atributo de nombre de producto DRA.

DeviceClass no tiene un campo `suitableNodes` en esta API. Restrinja Workloads con su selector/afinidad de Node y deje que DRA haga coincidir dispositivos y disponibilidad de Node. La solicitud usa `requests[].exactly`; los claims de Pod hacen referencia directamente a `resourceClaimTemplateName`, sin el wrapper `source` anterior.

## Jobs de comprobación de GPU acotados

Use un namespace aprobado (por ejemplo, `ai-workloads`) y una imagen probada **fijada por digest** que funcione con el controlador/runtime seleccionados, UID no root y sistema de archivos raíz de solo lectura. La imagen de marcador de posición a continuación es deliberadamente inutilizable. Ambos Jobs están **suspendidos de forma predeterminada**, por lo que aplicarlos no inicia trabajo de GPU.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-plugin-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      runtimeClassName: nvidia
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: device-plugin
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              nvidia.com/gpu: 1
            limits:
              cpu: 500m
              memory: 256Mi
              nvidia.com/gpu: 1
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-dra-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: dra
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
            claims:
              - name: gpu-resource
      resourceClaims:
        - name: gpu-resource
          resourceClaimTemplateName: single-large-gpu
```

El primer Job es para el ejemplo de plugin de dispositivos heredado exclusivo; el segundo es para la cohorte DRA separada. No solicite la misma GPU mediante ambos mecanismos. Un solo claim DRA es una asignación aunque varios contenedores hagan referencia a él.

Después de que el propietario reemplace la imagen, verifique ubicación/runtime/seguridad y apruebe la prueba GPU, reanude solo el Job previsto mediante el proceso de despliegue normal. Capture su resultado antes de la limpieza TTL. El plazo de 120 segundos limita el Job después de que se inicia, no la duración de la preparación de imagen ni de una operación de mantenimiento externa.

No configure `CUDA_VISIBLE_DEVICES=0,1,2,3` para un claim de un dispositivo. El administrador de dispositivos/runtime proporciona los dispositivos asignados; los índices visibles para el proceso de CUDA pueden diferir de los índices físicos de GPU. Una anulación manual puede ocultar o identificar erróneamente la asignación y no concede GPUs adicionales.

`nvidia-smi -L` confirma solo la visibilidad de dispositivos. Valide por separado una operación CUDA acotada y la aplicación real en hardware aprobado; aquí no se afirma tal ejecución ni resultado de rendimiento.

## MIG y time-slicing

MIG particiona GPUs compatibles en instancias de cómputo/memoria respaldadas por hardware. Proporciona mayor aislamiento de recursos y memoria/fallos que time-slicing, pero no convierte un host/controlador compartido en un límite de seguridad completo ni garantiza el SLO de latencia de una aplicación. Los perfiles compatibles y los límites de instancias dependen de SKU GPU y controlador.

Los perfiles comunes de **A100 40 GB** incluyen:

| Perfil | Memoria nominal del perfil | Máximo de instancias de ese perfil |
|---|---|---|
| `1g.5gb` | 5 GB | 7 |
| `2g.10gb` | 10 GB | 3 |
| `3g.20gb` | 20 GB | 2 |
| `4g.20gb` | 20 GB | 1 |
| `7g.40gb` | 40 GB | 1 |

`4g.40gb` pertenece al conjunto de perfiles de **A100 80 GB**; el cuestionario antiguo mezclaba estas tablas de SKU. `1g` se refiere al recuento de slices de cómputo GPU del perfil, no a un recuento de GPUs físicas. Las etiquetas de memoria nominal no son una garantía exacta de memoria utilizable. La ubicación de perfiles mixtos tiene restricciones geométricas adicionales.

Habilitar/reconfigurar MIG es una operación de mantenimiento controlada por el propietario y puede interrumpir Workloads GPU. Los valores del plugin independiente base anteriores usan `migStrategy: none`; cambiar una solicitud de Pod a `nvidia.com/mig-1g.5gb` no crea la instancia MIG. Prepare primero la geometría MIG real y la estrategia adecuada del plugin.

Time-slicing anuncia varios **slots de acceso lógicos**, no GPUs ni particiones de memoria físicamente separadas. Por ejemplo, una configuración de plugin de dispositivos revisada por separado podría usar:

```yaml
# Fragment of device-plugin configuration, not a Kubernetes resource.
version: v1
sharing:
  timeSlicing:
    renameByDefault: true
    failRequestsGreaterThanOne: true
    resources:
      - name: nvidia.com/gpu
        replicas: 4
```

Conecte esta configuración al plugin mediante su ConfigMap nombrado/selección de configuración y los Nodes previstos; un ConfigMap sin adjuntar no cambia nada. Con `renameByDefault: true`, el recurso anunciado es `nvidia.com/gpu.shared`. No use sin cambios la solicitud de comprobación de GPU exclusiva con ese recurso compartido.

Cuatro réplicas no reservan cuatro regiones de memoria independientes, y solicitar más tickets no garantiza cómputo proporcional. La contención, los cambios de contexto y el comportamiento de Workload pueden afectar la latencia/throughput; mida en lugar de suponer una causa fija. Time-slicing no tiene aislamiento de memoria/fallos entre réplicas. La inferencia no es automáticamente segura de sobresuscribir, y el entrenamiento no es universalmente incompatible con el uso compartido.

## Contexto de especificaciones H100/H200

| Especificación de NVIDIA | H100 **SXM** | H200 **SXM** |
|---|---|---|
| Memoria GPU | 80 GB HBM3 | 141 GB HBM3e |
| Ancho de banda de memoria publicado | 3.35 TB/s | 4.8 TB/s |
| MIG | Hasta 7, perfiles específicos del modelo | Hasta 7, perfiles específicos del modelo |

Estas son especificaciones de hardware del proveedor, no mediciones de este entorno Kubernetes. Las variantes H100 NVL/PCIe tienen distinta capacidad/ancho de banda; no generalice la fila SXM a cada H100. Una memoria mayor puede ayudar a que quepa un Workload, pero el rendimiento real de inferencia/entrenamiento también depende de modelo, precisión, batching, software, interconexión y contención.

## Inspeccione la asignación y limpie de forma segura

Use el kubeconfig/context de administrador explícito y mantenga privados los diagnósticos de hardware/Pod:

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceslices -o json > gpu-slices.json
jq '[.items[] | select(.spec.driver == "gpu.nvidia.com") |
  {name: .metadata.name, node: .spec.nodeName,
   devices: [.spec.devices[] | {name, attributes, capacity}]}]' gpu-slices.json
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceclaims -n ai-workloads -o json > gpu-claims.json
jq '[.items[] | {name: .metadata.name,
  allocation: .status.allocation.devices.results,
  reservedFor: .status.reservedFor}]' gpu-claims.json
```

Los ResourceClaims actuales no tienen un enum de fase universal almacenado `Pending → Allocated → Bound`. Compruebe los resultados de asignación, reservas, scheduling/eventos de Pod y preparación del controlador. Una reserva no es evidencia de que el contenedor usó correctamente la GPU. El ejemplo `resourceHandles` antiguo no tiene la forma actual de asignación estructurada.

Use los nombres/labels de Workload realmente renderizados por la release de controlador elegida al inspeccionar logs. DRA administrado por Operator y una release DRA independiente no comparten necesariamente el selector antiguo `app=nvidia-dra-driver`.

Elimine solo los Jobs/Pods de prueba que le pertenezcan después de capturar resultados; verifique que los claims generados se liberen y los dispositivos queden sin preparar. Los claims o finalizers retenidos pueden sobrevivir a un contenedor detenido. No elimine el plugin kubelet DRA mientras los Workloads aún lo necesiten para despreparar claims.

Para DRA administrado por Operator, siga su desmontaje ordenado de hook/finalizer de Helm. No use `helm uninstall --no-hooks` ni elimine finalizers a ciegas/fuerce la eliminación de claims compartidos. Reconcilie una limpieza fallida con el propietario del recurso antes de reutilizar el hardware.

## Referencias principales

- [Administración de dispositivos NVIDIA de AWS](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia.html)
- [Inferencia Hybrid de AWS: plugin de dispositivos con ámbito](https://aws.amazon.com/blogs/containers/run-genai-inference-across-environments-with-amazon-eks-hybrid-nodes/)
- [Matriz de plataforma/componentes de GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)
- [Flujo de trabajo DRA/GPUCluster de GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/dra-intro-install.html)
- [Requisitos previos de DRA driver 0.5.0](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [Atributos de ResourceSlice de DRA](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/reference/resourceslice-attributes.md)
- [DRA de Kubernetes](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/)
- [Plugin de dispositivos NVIDIA 0.20.0](https://github.com/NVIDIA/k8s-device-plugin/tree/v0.20.0)
- [Perfiles MIG](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html) y [time-slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [Especificaciones H100](https://www.nvidia.com/en-us/data-center/h100/) y [especificaciones H200](https://www.nvidia.com/en-us/data-center/h200/)

< [Anterior: Bootstrap de Node](./04-node-bootstrap.md) | [Tabla de contenidos](./README.md) | [Siguiente: Estrategias de ubicación de Workloads](./06-workload-placement.md) >
