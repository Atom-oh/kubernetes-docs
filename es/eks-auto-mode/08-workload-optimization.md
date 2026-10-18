# Optimización específica para cada carga de trabajo

> **Versiones compatibles**: EKS Auto Mode GA; ejemplos revisados para EKS 1.36
> **Última actualización**: September 12, 2026

Adapte la política de ubicación y recuperación a la carga de trabajo y, luego, valide la capacidad, el rendimiento y el costo reales. Los ejemplos de web y procesamiento por lotes son configuraciones de laboratorio acotadas. Los ejemplos de GPU son **plantillas de configuración inactivas**, no aplicaciones de entrenamiento/inferencia validadas: la inferencia tiene cero réplicas y el trabajo de entrenamiento heredado está suspendido. No se ejecutaron GPU/modelos, no se implementó ningún clúster activo ni se realizó ninguna prueba de rendimiento.

Use la protección de cuenta/contexto de [Operaciones](./05-operations.md). Todos los pools son dinámicos; no reservan capacidad física. Seleccione solo los ejemplos necesarios, revise la identidad de `default`/NodeClass personalizado y el acceso a las subredes, y tenga en cuenta los costos continuos de los nodos y el almacenamiento. Las taints y los selectores controlan la ubicación, pero no constituyen un límite de seguridad entre tenants.

## Servicios web: disponibilidad y recuperación

On-Demand evita los eventos de recuperación de Spot, pero no garantiza capacidad ni disponibilidad. Siguen siendo necesarias las réplicas, la topología, la disponibilidad, las políticas de interrupción, el estado duradero y las pruebas de recuperación ante fallos.

Este ejemplo usa tres réplicas y un PDB que permite una expulsión voluntaria cuando las tres están en buen estado, en lugar de asumir que `N-1` es un valor literal de PDB. El antiguo ejemplo de diez réplicas era una decisión de dimensionamiento, no un requisito universal. La imagen/digest de nginx y la configuración sin privilegios coinciden con el ejemplo de operaciones revisado. Las sondas consultan `/` en el puerto 8080; una imagen de aplicación arbitraria no necesariamente implementa `/health`.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: workload-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 20
          failureThreshold: 3
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: web-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: web-tier
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-frontend
```

La distribución estricta entre zonas requiere al menos dos dominios aptos; la falta de capacidad puede dejar Pods en estado Pending. La distribución flexible por nombre de host es una preferencia, no garantiza una réplica por nodo ni tres zonas de disponibilidad. Compruebe las etiquetas coincidentes, la cobertura de subredes y la política ante fallos.

Una sonda de inicio protege las inicializaciones lentas frente a las comprobaciones de actividad prematuras. La disponibilidad controla si un endpoint puede recibir tráfico; la actividad reinicia un contenedor. Elija umbrales específicos para la aplicación y evite comprobaciones de actividad que reinicien todas las réplicas porque no está disponible una dependencia compartida. Los tiempos ilustrativos de las sondas aquí no constituyen un SLA de inicio medido.

## Procesamiento por lotes: los reintentos no recuperan puntos de control

Use Spot solo para trabajos que puedan tolerar interrupciones, plazos incumplidos y falta de capacidad Spot. Este pool no tiene alternativa On-Demand. `restartPolicy: OnFailure` puede reiniciar un contenedor fallido en un Pod que siga activo; no recupera la memoria del proceso perdida al terminar un nodo. `SPOT_AWARE=true` es solo una variable de entorno, a menos que una aplicación la implemente.

El siguiente Job indexado imprime un número de fragmento lógico como **ejemplo de prueba básica**. Tiene paralelismo de dos, cinco completados, un plazo y reintentos limitados, en lugar del antiguo ejemplo de dimensionamiento con 20 en paralelo/100 completados. No es una implementación de procesamiento de datos. El índice de imagen de BusyBox revisado incluye Linux amd64/arm64; no se ejecutó ninguna imagen durante esta auditoría.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-smoke
  namespace: workload-lab
spec:
  completionMode: Indexed
  parallelism: 2
  completions: 5
  backoffLimit: 2
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: indexed-smoke
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: processor
        image: busybox:1.38.0@sha256:fd7dc98638c8e305f4dc34e979f1c0fdfdcaeb0fbf8fcff77ae834b6da3d7e6e
        command:
        - /bin/sh
        - -ec
        args:
        - printf 'logical shard=%s; smoke only\n' "$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: 100m
            memory: 32Mi
          limits:
            cpu: 500m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: batch-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: batch-tier
        effect: NoSchedule
```

Los trabajos reales necesitan confirmaciones de resultados idempotentes, puntos de control duraderos y lógica para reanudar. Incluso los Jobs indexados pueden ejecutar un índice más de una vez en algunos casos de fallo; no dé por hecho que los efectos secundarios ocurren exactamente una vez. Exporte los registros/artefactos necesarios antes de la limpieza por TTL. Las cachés locales del nodo y `emptyDir` no son puntos de control duraderos.

`WhenEmpty` puede limpiar un nodo cuando ya no haya trabajo de aplicación apto; un valor de `consolidateAfter` de 30 segundos es un intervalo de espera, no una garantía de que un trabajo en ejecución finalice ni de que el nodo desaparezca tras 30 segundos. La deriva, el vencimiento y las interrupciones siguen siendo rutas de ciclo de vida independientes.

## Inferencia con GPU: compruebe la forma completa del nodo

Auto Mode gestiona los controladores de NVIDIA y la compatibilidad con dispositivos, así como las imágenes Bottlerocket. No admite los campos anteriores de NodeClass `amiFamily: AL2023` ni `blockDeviceMappings`.

| Instancia | GPU | Memoria de GPU | vCPU / RAM del host |
|----------|------|------------|-----------------|
| g5.xlarge | 1 A10G | 24 GB | 4 / 16 GiB |
| g5.2xlarge | 1 A10G | 24 GB | 8 / 32 GiB |
| g5.4xlarge | 1 A10G | 24 GB | 16 / 64 GiB |
| g5.12xlarge | 4 A10G | 96 GB en total, 24 GB cada una | 48 / 192 GiB |
| p5.48xlarge | 8 H100 | 640 GB en total, 80 GB cada una | 192 / 2 TiB |

Estos son ejemplos, no una lista de las instancias GPU más recientes ni de las que están disponibles universalmente. La memoria total de GPU no equivale a la memoria de un único dispositivo contiguo. En particular, las solicitudes anteriores del Pod de 4 CPU/16Gi no caben en una g5.xlarge después de las reservas del nodo/sistema y la sobrecarga de DaemonSet. Este pool de inferencia permite formas G5 más grandes y evita seleccionar un nodo de entrenamiento de ocho GPU para un servicio de una GPU que no se ha revisado.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 200Gi
    iops: 6000
    throughput: 250
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
  namespace: workload-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: inference
        image: registry.example.invalid/reviewed-inference:replace-me
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: gpu-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

Mantenga `replicas: 0` hasta sustituir el registro/imagen de ejemplo deliberadamente no válido por una imagen inmutable revisada y proporcionar su punto de entrada real, las rutas del modelo/de entrada, las sondas, el almacenamiento y una identidad de carga de trabajo con permisos limitados. Valide la compatibilidad del controlador/CUDA/bibliotecas y el UID sin privilegios 1000/la política de seguridad con esa imagen; esta auditoría no validó un entorno de ejecución de inferencia.

`ephemeralStorage` es una configuración de almacenamiento del nodo, no almacenamiento persistente para modelos/puntos de control ni garantía de rendimiento. Inspeccione el almacenamiento realmente asignable y los dispositivos subyacentes. El cifrado del EBS raíz/de datos del nodo no establece el cifrado de PVC arbitrarios. Un límite de cantidad de GPU restringe los recursos del pool, no el costo total en dólares, y puede superarse temporalmente durante el aprovisionamiento rápido. Los ejemplos originales de 16/20 GPU eran decisiones de dimensionamiento; el laboratorio usa un límite menor de cuatro GPU.

`WhenEmpty` con un intervalo de espera de diez minutos puede reducir la rotación después de que las cargas de trabajo se marchen. No retrasa la programación hasta que termine la inicialización de la GPU ni garantiza que haya un nodo listo. Hay NodePools estáticos disponibles cuando resulta apropiada la capacidad aprovisionada previamente deseada, con semánticas distintas de límites/consolidación y costos continuos.

## Entrenamiento distribuido y EFA

La compatibilidad con EFA en Auto Mode es actual y real. **Un comentario junto a la configuración del disco no la habilita.** El campo compatible de NodeClass es `advancedNetworking.networkInterfaces`; la ruta del complemento de dispositivos anuncia `vpc.amazonaws.com/efa`.

Revise todos estos puntos antes de activar una carga de trabajo de entrenamiento:

- Auto Mode actualmente **no** admite la ruta EFA DRA. Use el complemento de dispositivos EFA, no un ejemplo de DRANET ResourceClaim copiado de otro modo de cómputo.
- Auto Mode gestiona los controladores de host de NVIDIA/Neuron; las dependencias de host de EFA por sí solas no demuestran que el complemento de dispositivos EFA independiente esté instalado y en estado Ready.
- Las interfaces solo EFA transportan RDMA, no direcciones IP de Pod. La interfaz principal es la tarjeta 0/dispositivo 0 de tipo `interface`. El ejemplo añade cuatro dispositivos `efa-only` y un prefijo `/28` para las direcciones IP de Pod.
- La configuración estática de interfaces solo admite IPv4; no se añaden IP/prefijos/ENI adicionales después del lanzamiento. No combine la configuración de varias interfaces con `associatePublicIPAddress`. Planifique la capacidad de IP para los Pods de cargas de trabajo y del sistema.
- Use un grupo de ubicación existente compatible, con zonas de disponibilidad/subredes privadas coincidentes y un grupo de seguridad EFA revisado que permita el tráfico necesario con referencia a sí mismo. Los nombres de zona/grupo del ejemplo son marcadores de posición, no pruebas de que haya capacidad P5 disponible allí.
- Compruebe EFA/libfabric/NCCL, el inicio/reencuentro de procesos, la localidad de GPU/EFA y cualquier configuración necesaria de hugepage/bloqueo de memoria. El ejemplo de interfaz de cuatro dispositivos no afirma el ancho de banda máximo de red de P5 ni la alineación automática de GPU/EFA en los hosts Bottlerocket de Auto Mode.

El siguiente pool P5 homogéneo evita suponer que los workers P4d/P5 mixtos son intercambiables. P4d sigue siendo una alternativa que requiere validar su propio pool/entorno de ejecución compatible. Los valores anteriores de 500Gi/16.000 IOPS/1.000 de rendimiento y los 2.000Gi adicionales de disco de datos eran ilustrativos; el NodeClass compatible no crea ese dispositivo de bloque adicional arbitrario.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: reviewed-efa-security-group
  advancedNetworking:
    networkInterfaces:
    - networkCardIndex: 0
      deviceIndex: 0
      interfaceType: interface
      secondaryIPv4PrefixCount: 1
    - networkCardIndex: 0
      deviceIndex: 1
      interfaceType: efa-only
    - networkCardIndex: 1
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 2
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 3
      deviceIndex: 0
      interfaceType: efa-only
  ephemeralStorage:
    size: 500Gi
    iops: 16000
    throughput: 1000
  placementGroupSelector:
    name: reviewed-ml-training-pg
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - p
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p5.48xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: ml-training
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: ml-training
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
    budgets:
    - nodes: 10%
  limits:
    cpu: '960'
    memory: 10Ti
    nvidia.com/gpu: '40'
```

### Estructura heredada de PyTorchJob conservada

`kubeflow.org/v1 PyTorchJob` requiere **Kubeflow Training Operator V1**; se usó su CRD de la versión publicada v1.9.3 para la validación estructural. Las API TrainJob/Runtime actuales de Kubeflow Trainer son distintas. Auto Mode no instala ninguno de los operadores al crear un NodePool.

Esta plantilla está suspendida y usa una imagen de marcador de posición deliberadamente no válida. Ilustra un master y tres workers, ocho procesos de GPU locales por nodo y cuatro dispositivos EFA por Pod: **32 GPU / cuatro nodos de ocho GPU** al activarla. El límite de 40 GPU del pool permite como máximo cinco formas de nodo de este tipo como límite de planificación, incluido el margen para sustituciones; no es una reserva ni un límite estricto de facturación.

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
  namespace: workload-lab
spec:
  nprocPerNode: '8'
  runPolicy:
    suspend: true
    activeDeadlineSeconds: 3600
    backoffLimit: 1
    cleanPodPolicy: None
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
    Worker:
      replicas: 3
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
```

Antes de reanudarlo, proporcione una imagen/punto de entrada verificados que implemente el contrato de inicio distribuido del operador, las rutas reales del conjunto de datos y la exportación duradera de puntos de control/artefactos. Valide el operador, el comportamiento de la cola/planificación en grupo, la capacidad de cuatro nodos, DNS/reencuentro, las reglas de red, los permisos del entorno de ejecución y el plazo. Esta no es una receta completa para entrenamiento en producción. La plantilla de Namespace Restricted puede necesitar una política de carga de trabajo revisada por separado si el entorno de ejecución de acelerador verificado requiere permisos que no puede satisfacer; no desactive sin más la seguridad de admisión de todo el clúster.

Suspender un PyTorchJob heredado que ya está en ejecución elimina sus Pods/PodGroups activos; no es una operación de punto de control. `cleanPodPolicy: None` conserva los Pods completados para inspeccionarlos, pero no exporta artefactos. Revise la limpieza después de la exportación duradera, incluidos los PVC, los nodos y las reservas con propietario independiente.

### Observe la capacidad real de los dispositivos

Esta instantánea de solo lectura informa los valores realmente asignables y las condiciones Ready. La ausencia de un valor de GPU/EFA o un fallo de la API no debe interpretarse como una configuración correcta del dispositivo:

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[]|{name:.metadata.name,
  instanceType:.metadata.labels["node.kubernetes.io/instance-type"],
  pool:.metadata.labels["karpenter.sh/nodepool"],
  allocatable:{cpu:.status.allocatable.cpu,memory:.status.allocatable.memory,
    gpu:.status.allocatable["nvidia.com/gpu"],efa:.status.allocatable["vpc.amazonaws.com/efa"]},
  conditions:[.status.conditions[]?|select(.type=="Ready")|{type,status,reason}]}]'
```

## Decisiones sobre recursos y arquitectura

| Carga de trabajo | Política candidata | Validación pendiente |
|----------|------------------|-------------------------|
| Web / API | On-Demand o capacidad mixta con cuidado; consolidación moderada | Presupuesto de disponibilidad, réplicas, arquitectura del entorno de ejecución y latencia medida |
| Procesamiento por lotes / CI | Spot cuando lo permitan el comportamiento de reinicio y los plazos | Idempotencia, progreso duradero, reintentos y capacidad no disponible |
| Base de datos / streaming | Ubicación que tenga en cuenta el estado y política de interrupción | Quórum, topología de volúmenes, recuperación y comportamiento ante particiones |
| Inferencia con GPU | GPU/CPU/RAM ajustadas al tamaño del modelo y posible capacidad lista | Compatibilidad de imagen/controlador, sondas, inicio en frío y costo |
| Entrenamiento distribuido | Pool homogéneo de aceleradores y red/entorno de ejecución validados | Capacidad de grupo, puntos de control/exportación, dispositivos EFA y ubicación |

Los valores anteriores de vencimiento de 24h/72h/168h/336h y consolidación de 30s/1m/5m/10m/15m/30m son ejemplos de políticas, no valores predeterminados por tipo de carga de trabajo. Siguen aplicándose la vida útil máxima de Auto Mode y el período de gracia de terminación independiente.

Para las cargas de trabajo limitadas por CPU, la solicitud anterior de 2 CPU/2Gi y el límite de 4 CPU/4Gi ilustran una posible política de ráfagas, no un dimensionamiento universal. Para las cargas de trabajo limitadas por memoria, una solicitud/límite de 8Gi no proporciona por sí sola QoS Guaranteed cuando la solicitud y el límite de CPU difieren. QoS Guaranteed también depende de todos los contenedores/recursos pertinentes, y los límites de memoria aún pueden provocar OOM. Las fórmulas anteriores de uso de 1,2–1,5× y solicitudes de 2× no tienen una base de rendimiento general verificada.

Con la API del complemento de dispositivos, los recursos de GPU son recursos extendidos enteros: especifique los límites y, si lo desea, solicitudes coincidentes; las solicitudes solamente no son el patrón para GPU. Una solicitud de CPU/memoria debe dejar suficiente capacidad asignable del nodo para el trabajo requerido del sistema. Reducir solo los límites normalmente no mejora el empaquetado basado en solicitudes.

### Verificación de varias arquitecturas

Compruebe un índice de imagen fijado en lugar de buscar con grep `nginx:latest`. Un índice que contenga ambas plataformas es una comprobación necesaria del empaquetado, no una prueba de que las dependencias nativas y el comportamiento de la aplicación funcionen en ambas:

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```

Para su propio Dockerfile revisado, el siguiente comando escribe un archivo OCI local en lugar de publicar una imagen no especificada:

```bash
: "${BUILD_CONTEXT:?Set the reviewed Dockerfile directory}"
test -f "$BUILD_CONTEXT/Dockerfile"
docker buildx build --platform linux/amd64,linux/arm64 \
  --output "type=oci,dest=$WORK_DIR/app-multiarch.tar" "$BUILD_CONTEXT"
```

La compilación requiere un builder de Buildx adecuado, workers nativos o emulación/compilación cruzada configurada correctamente. Ejecute pruebas de aplicación específicas para cada arquitectura antes de publicar mediante el flujo de trabajo habitual de su registro. El ahorro anterior de ~40 % con Spot/Graviton mixto sigue siendo una estimación no verificada; compare el costo real por trabajo útil según se describe en [Gestión de costos](./06-cost-management.md).

## Referencias

- [Cómputo de IA/ML en Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [Almacenamiento de NodeClass e interfaces de red estáticas](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Administración de dispositivos EFA, incluido Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/device-management-efa.html)
- [Especificaciones de instancias G5](https://aws.amazon.com/ec2/instance-types/g5/)
- [Especificaciones de instancias P5](https://aws.amazon.com/ec2/instance-types/p5/)
- [Jobs y Jobs indexados de Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Programación de GPU en Kubernetes](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Solicitudes, límites y cantidades de recursos](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Restricciones de distribución de topología](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Sondas de inicio, disponibilidad y actividad](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [CRD PyTorchJob de Training Operator v1.9.3](https://github.com/kubeflow/training-operator/blob/v1.9.3/manifests/base/crds/kubeflow.org_pytorchjobs.yaml)
- [Kubeflow Trainer y migración de la versión heredada](https://github.com/kubeflow/trainer)
- [Compilaciones multiplataforma de Docker](https://docs.docker.com/build/building/multi-platform/)

< [Anterior: Ciclo de vida de los nodos](./07-node-lifecycle.md) | [Tabla de contenido](./README.md) | [Siguiente: Guía de migración](./09-migration-guide.md) >
